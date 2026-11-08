#!/usr/bin/env python3
"""Acquire Ra's 106 published transcripts and linked recording segments privately.

Original recordings and edited text are distinct evidence types. Audio mode is
for user-requested private retention of the publisher's explicitly offered free
original recordings; it is not a search index or public media mirror. It requires
a source-bound complete player frame and exact successful HEAD inventory. It
never bypasses a proxy or origin denial, checks out a cart, or authenticates a
claimed speaker. See RA-SOURCES.md for edition, access, and completeness limits.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError

BASE='https://www.lawofone.info'
EDITION='lawofone-info-lightly-edited'
MAX_HTML=2*1024**2
MIN_FREE=6*1024**3
SCHEMA=1


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def urlopen(request,timeout):
    """Ordinary configured HTTPS; reject redirects before contacting another URL."""
    return build_opener(NoRedirect()).open(request,timeout=timeout)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def artifact(path,role):
    return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size,'role':role}


def private_root(path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts:raise ValueError('Private absolute path required')
    for p in (path,*path.parents):
        if p.is_symlink():raise ValueError('Symlink routes are not supported')
        marker=p/'.git'
        if marker.exists() and not (marker.is_dir() and not any(marker.iterdir())):
            raise ValueError('Source text must remain outside Git')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    return path


def write_json(path,obj):
    with path.open('x',encoding='utf8') as stream:
        os.chmod(path,0o600);json.dump(obj,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')


def rendered_text(raw):
    class TextParser(HTMLParser):
        def __init__(self):super().__init__();self.parts=[]
        def handle_data(self,data):self.parts.append(data)
    parser=TextParser();parser.feed(raw)
    return ' '.join(' '.join(parser.parts).split())


class SessionParser(HTMLParser):
    def __init__(self,number):
        super().__init__(convert_charrefs=True)
        self.number=number;self.turns=[];self.current=None;self.skip_depth=0
        self.description=None;self.page_text=[];self.current_question=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);classes=set(a.get('class','').split())
        if tag=='meta' and a.get('name')=='description':self.description=a.get('content','')
        if tag=='p' and classes.intersection({'ra','elkins'}):
            if self.current is not None:raise ValueError('Nested transcript paragraphs')
            role='response' if 'ra' in classes else 'questioner'
            ident=a.get('id')
            if ident is not None:
                if not re.fullmatch(r'\d+',ident):raise ValueError('Unrecognized printed question identifier')
                self.current_question=f'{self.number}.{ident}'
            if self.current_question is None:raise ValueError('Transcript turn lacks a printed question context')
            self.current={'role':role,'printed_role':'Ra' if role=='response' else 'Questioner',
                          'question_id':self.current_question,'parts':[],'printed_paragraph_id':ident}
        if self.current is not None:
            if self.skip_depth:self.skip_depth+=1
            elif classes.intersection({'optional','qnum','play','noprint'}):self.skip_depth=1
            elif tag=='br':self.current['parts'].append('\n')
    def handle_endtag(self,tag):
        if self.current is not None and self.skip_depth:
            self.skip_depth-=1;return
        if tag=='p' and self.current is not None:
            r=self.current;self.current=None
            text=''.join(r.pop('parts'))
            text=re.sub(r'^\s*'+re.escape(r['question_id'])+r'\s*','',text)
            text=re.sub(r'^\s*(?:Questioner|Ra):\s*','',text)
            text=re.sub(r'[ \t\r\f\v]+',' ',text)
            text=re.sub(r' *\n *','\n',text);text=re.sub(r'\n{3,}','\n\n',text).strip()
            if not text:raise ValueError('Empty published turn')
            r['text']=text;r['turn_id']=f"ra:{self.number:03d}:{len(self.turns)+1:04d}"
            self.turns.append(r)
    def handle_data(self,data):
        self.page_text.append(data)
        if self.current is not None and not self.skip_depth:self.current['parts'].append(data)


def parse_session(raw,number):
    if not 1<=number<=106:raise ValueError('Canonical session number out of scope')
    p=SessionParser(number);p.feed(raw.decode('utf8'));p.close()
    if p.current is not None or p.skip_depth:raise ValueError('Unclosed transcript markup')
    if not p.description or not p.description.startswith(f'The Law of One Session {number}. '):
        raise ValueError('Source identity does not match canonical session')
    date=dt.datetime.strptime(p.description.split('. ',1)[1],'%B %d, %Y').date().isoformat()
    page=' '.join(p.page_text)
    if not re.search(r'Version\s*\(\s*\?\s*\)\s*:\s*Lightly Edited',page):
        raise ValueError('Expected explicit default Lightly Edited edition')
    if not p.turns or not any(t['role']=='response' for t in p.turns):raise ValueError('No published response text')
    qids=[t['question_id'] for t in p.turns if t['role']=='questioner']
    if len(set(qids))!=len(qids):raise ValueError('Duplicate numbered question paragraphs')
    sequence=[int(t['question_id'].split('.')[1]) for t in p.turns]
    if sequence!=sorted(sequence):raise ValueError('Printed question ordering changed')
    text='\n'.join(t['text'] for t in p.turns)
    sid=f'ra:session:{number:03d}:lightly-edited'
    return {'schema_version':SCHEMA,'source_id':sid,'session_number':number,'edition_id':EDITION,
            'text':text,'turns':p.turns,'published_at':date,'whitespace_words':len(text.split()),
            'audio_gap_notices':[t['question_id'] for t in p.turns if re.search(r'audiotape was reused|audio recording.*not available|tape.*lost|tape.*missing|question was lost',t['text'],re.I|re.S)]}


class RateGate:
    def __init__(self,interval=.4):self.interval=interval;self.lock=threading.Lock();self.last=0.
    def wait(self):
        with self.lock:
            wait=max(0,self.interval-(time.monotonic()-self.last))
            if wait:time.sleep(wait)
            self.last=time.monotonic()


def fetch(number,raw_root,gate):
    url=f'{BASE}/s/{number}'
    path=raw_root/f'session-{number:03d}.html';receipt_path=raw_root/f'session-{number:03d}.retrieval.json'
    if path.exists() or receipt_path.exists():
        if not path.is_file() or not receipt_path.is_file():raise ValueError('Incomplete prior retrieval must be inspected')
        r=json.loads(receipt_path.read_text())
        if r.get('status')!=200 or r.get('url')!=url:raise ValueError('Retained retrieval status or source identity differs')
        if r['sha256']!=sha(path) or r['bytes']!=path.stat().st_size:raise ValueError('Retained source changed')
        return path,receipt_path
    if shutil.disk_usage(raw_root).free<MIN_FREE+MAX_HTML:raise ValueError('6 GiB free-space floor prevents transcript retrieval')
    gate.wait()
    with urlopen(Request(url,headers={'User-Agent':'Channels-ET-source-research/1.0'}),timeout=45) as response:
        if response.status!=200 or response.url!=url:raise ValueError('Unexpected source status or redirect')
        data=response.read(MAX_HTML+1);ctype=response.headers.get('Content-Type','')
    if len(data)>MAX_HTML or 'text/html' not in ctype:raise ValueError('Unexpected source size/type')
    parse_session(data,number)
    with path.open('xb') as stream:os.chmod(path,0o600);stream.write(data)
    receipt={'schema_version':SCHEMA,'url':url,'status':200,'content_type':ctype,'bytes':len(data),
        'sha256':sha(path),'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'method':'ordinary HTTPS using configured proxy and verified TLS; canonical public page',
        'scope':'Retained publisher-authorized edited transcript, not authentication of claimed speaker.'}
    write_json(receipt_path,receipt)
    return path,receipt_path


def collect(output,discovery,sessions,workers=2):
    output=private_root(output);raw_root=output/'raw';raw_root.mkdir(mode=0o700,exist_ok=True)
    norm_root=output/'normalized'
    if norm_root.exists() and any(norm_root.iterdir()):raise ValueError('Use a fresh normalized output; never overwrite final extraction')
    norm_root.mkdir(mode=0o700,exist_ok=True)
    discovery=Path(discovery)
    evidence_paths=[discovery/'page-7.html',discovery/'versions.html',discovery/'audio.html',discovery/'robots.html',discovery/'sessions.html']
    if not all(p.is_file() for p in evidence_paths):raise ValueError('Retained frame, edition, access and permission evidence required')
    frame=(discovery/'sessions.html').read_text()
    found={int(x) for x in re.findall(r'href=[\"\']/s/(\d+)[\"\']',frame)}
    if found!=set(range(1,107)):raise ValueError('Canonical source frame no longer contains exactly sessions1–106')
    if 'with permission from L/L Research' not in rendered_text((discovery/'page-7.html').read_text()):raise ValueError('Authorized-edition statement is missing')
    gate=RateGate();records=[];failures=[];lock=threading.Lock();halt=threading.Event()
    def one(number):
        try:
            if halt.is_set():raise ValueError('Not attempted after source-wide access/rate denial')
            raw,rp=fetch(number,raw_root,gate);parsed=parse_session(raw.read_bytes(),number)
            target=norm_root/f'session-{number:03d}.json';write_json(target,parsed)
            textpath=norm_root/f'session-{number:03d}.txt'
            with textpath.open('x',encoding='utf8') as stream:os.chmod(textpath,0o600);stream.write(parsed['text']+'\n')
            ex={'schema_version':SCHEMA,'source_id':parsed['source_id'],'source':artifact(raw,'source'),
                'normalized':artifact(target,'normalized_text'),'plain_text':artifact(textpath,'plain_text'),
                'extractor_sha256':sha(Path(__file__)),'turns':len(parsed['turns']),
                'whitespace_words':parsed['whitespace_words'],'edition_id':EDITION,
                'method':'Extract only published p.ra/p.elkins turns; omit optional footnote asterisks; preserve stage/gap notices; join turns with newline.',
                'speaker_attribution':'Printed role labels; no independent voice or entity authentication.'}
            ep=norm_root/f'session-{number:03d}.extraction.json';write_json(ep,ex)
            record={'source_id':parsed['source_id'],'corpus':'ra','session_id':f'ra:session:{number:03d}',
                'duplicate_family_id':f'ra:session:{number:03d}','edition_id':EDITION,'source_kind':'publisher_transcript',
                'title':f'The Law of One — Session {number}','source_url':f'{BASE}/s/{number}',
                'published_at':parsed['published_at'],'language':'en','speaker_attribution_status':'publisher_printed_roles_unverified',
                'collection_status':'retrieved','coverage_status':'full','coverage_basis':'Complete canonical page in the selected Lightly Edited published edition, not completeness of surviving audio.',
                'text_artifact':{k:v for k,v in artifact(target,'normalized_text').items() if k!='role'},
                'evidence':[artifact(raw,'source'),artifact(rp,'retrieval_receipt'),artifact(ep,'extraction_receipt'),*[artifact(p,'frame_edition_permission') for p in evidence_paths]],
                'source_editing_notes':'Lightly Edited: minimally edited questions, relistened answers except documented edits, original-book text substitutes for audio gaps; distinct from2018RaContact.',
                'audio_completeness_notice':{'scope':'No audio downloaded by this transcript collector; surviving tape may have gaps.','printed_notice_question_ids':parsed['audio_gap_notices']},
                'rights_and_access_basis':'lawofone.info explicitly reports L/L Research permission to republish. User-authorized private research retention; no full-text public redistribution.',
                'printed_turns':len(parsed['turns']),'whitespace_words':parsed['whitespace_words']}
            with lock:records.append(record)
        except Exception as e:
            if isinstance(e,HTTPError) and e.code in (401,403,429):halt.set()
            with lock:failures.append({'session_number':number,'status':'failed','error_type':type(e).__name__,'message':str(e)[:220]})
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(one,sessions))
    records.sort(key=lambda r:r['session_id']);failures.sort(key=lambda r:r['session_number'])
    manifest={'schema_version':SCHEMA,'kind':'source-bound-published-transcript-corpus','corpus':'ra','edition_id':EDITION,
        'canonical_session_count':106,'requested_session_count':len(sessions),'retrieved_session_count':len(records),
        'collection_cutoff':dt.datetime.now(dt.timezone.utc).isoformat(),'records':records,'failures':failures,
        'audio_downloads':0,'video_downloads':0,'human_transcript_review':False,'claims_authenticated':False,
        'extractor_sha256':sha(Path(__file__))}
    write_json(output/'transcript-manifest.json',manifest)
    return manifest



def audio_url_parts(url):
    match=re.fullmatch(r'https://www\.lawofone\.info/audio/(\d+)-(\d+)\.mp3',str(url))
    if not match:raise ValueError('Only source-published canonical Ra audio URLs are supported')
    session,segment=map(int,match.groups())
    if not 1<=session<=106 or not 0<=segment<=500:raise ValueError('Audio source identity is out of bounds')
    return session,segment


def audio_probe(path):
    import subprocess
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries',
        'format=duration,size,format_name,bit_rate:stream=index,codec_name,codec_type,sample_rate,channels',
        '-of','json',str(path)],capture_output=True,text=True,check=True,timeout=30)
    value=json.loads(result.stdout);fmt=value.get('format',{});streams=value.get('streams',[])
    duration=float(fmt.get('duration',0))
    if not 0<duration<=6*3600 or fmt.get('format_name')!='mp3' or not streams or any(s.get('codec_type')!='audio' for s in streams):
        raise ValueError('Downloaded source is not a finite MP3 audio recording')
    return {'duration_seconds':duration,'format_name':fmt['format_name'],'bit_rate':int(fmt.get('bit_rate',0)),
        'streams':streams,'scope':'Container/codec verification, not listening or speaker/entity authentication.'}


def parse_audio_links(raw,number):
    parse_session(raw,number)
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.urls=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a' and a.get('href','').startswith('/audio/') and a['href'].endswith('.mp3'):
                self.urls.append(BASE+a['href'])
    parser=Links();parser.feed(raw.decode('utf8'))
    for url in parser.urls:
        n,q=audio_url_parts(url)
        if n!=number:raise ValueError('Player contains audio assigned to another session')
    return sorted(set(parser.urls),key=lambda u:audio_url_parts(u)[1])


def inventory_audio(output,discovery,sessions,workers=2):
    """Inspect normal publisher play pages; transfer no audio bodies."""
    output=private_root(output);discovery=Path(discovery)
    if not sessions or len(set(sessions))!=len(sessions) or min(sessions)<1 or max(sessions)>106:raise ValueError('Canonical unique sessions 1–106 required')
    if workers not in (1,2):raise ValueError('One or two workers required')
    if any(output.iterdir()):raise ValueError('Use fresh inventory output to preserve earlier evidence')
    permission=discovery/'page-7.html';offer=discovery/'audio.html';robots=discovery/'robots.html'
    if not all(p.is_file() for p in (permission,offer,robots)):raise ValueError('Retained permission, original-audio offer, and robots evidence required')
    if 'with permission from L/L Research' not in rendered_text(permission.read_text()):raise ValueError('Publisher-permission statement missing')
    if 'original' not in rendered_text(offer.read_text()).lower():raise ValueError('Original-audio offer missing')
    raw_root=output/'audio-pages';raw_root.mkdir(mode=0o700)
    lock=threading.Lock();halt=threading.Event();gate=RateGate(.4);records=[];failures=[]
    def one(number):
        url=f'{BASE}/s/{number}?au=1';attempted=False
        try:
            if halt.is_set():raise ValueError('Deferred after source-wide failure')
            if shutil.disk_usage(output).free<1024**3+MAX_HTML:raise ValueError('Inventory requires at least 1 GiB free reserve')
            gate.wait()
            if halt.is_set():raise ValueError('Deferred after another worker reported a source-wide failure')
            attempted=True
            with urlopen(Request(url,headers={'User-Agent':'Channels-ET-personal-research-archive/1.0'}),timeout=45) as response:
                if response.status!=200 or response.url!=url:raise ValueError('Unexpected player response status or redirect')
                content_type=response.headers.get('Content-Type','');data=response.read(MAX_HTML+1)
            if len(data)>MAX_HTML or 'text/html' not in content_type:raise ValueError('Unexpected player size/type')
            urls=parse_audio_links(data,number);path=raw_root/f'session-{number:03d}.html'
            with path.open('xb') as stream:os.chmod(path,0o600);stream.write(data)
            record={'session_number':number,'session_id':f'ra:session:{number:03d}','source_page':url,'http_status':200,
                'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'path':str(path),'bytes':len(data),'sha256':sha(path),'audio_urls':urls}
            with lock:records.append(record)
        except Exception as error:
            code=error.code if isinstance(error,HTTPError) else None
            global_failure=code in (401,403,407,429,451) or (isinstance(error,URLError) and not isinstance(error,HTTPError)) or isinstance(error,TimeoutError)
            if global_failure:halt.set()
            record={'session_number':number,'url':url,'http_status':code,'attempted':attempted,'error_type':type(error).__name__,'message':str(error)[:220]}
            with lock:
                failures.append(record)
                if global_failure and not (output/'source-halt.json').exists():write_json(output/'source-halt.json',record)
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(one,sessions))
    records.sort(key=lambda r:r['session_number']);failures.sort(key=lambda r:r['session_number'])
    manifest={'schema_version':1,'kind':'publisher-original-audio-segment-frame','records':records,'failures':failures,
        'source_page_count':len(records),'published_audio_segments':sum(len(r['audio_urls']) for r in records),
        'evidence':[artifact(p,'permission_audio_offer_and_indexing_context') for p in (permission,offer,robots)],'script_sha256':sha(Path(__file__)),
        'scope':'Original recording segments explicitly linked by authorized edition, not continuous tape masters. User-requested private inventory, not public search indexing. No audio bodies, checkout, or access circumvention.'}
    write_json(output/'audio-inventory.json',manifest)
    return manifest


def validate_audio_inputs(frame_path,sizes_path):
    frame=json.loads(Path(frame_path).read_text());sizes=json.loads(Path(sizes_path).read_text())
    if frame.get('source_page_count')!=106 or frame.get('failures') or len(frame.get('records',[]))!=106 or {r.get('session_number') for r in frame.get('records',[])}!=set(range(1,107)):
        raise ValueError('Complete canonical audio source-page frame required')
    source_by_url={}
    for page in frame.get('records',[]):
        if page.get('http_status')!=200 or page.get('source_page')!=f'{BASE}/s/{page["session_number"]}?au=1':raise ValueError('Player source identity/status differs')
        raw=Path(page['path'])
        if raw.stat().st_size!=page['bytes'] or sha(raw)!=page['sha256']:raise ValueError('Frozen player source page changed')
        if set(parse_audio_links(raw.read_bytes(),page['session_number']))!=set(page['audio_urls']):raise ValueError('Audio frame differs from actual published links')
        for url in page['audio_urls']:
            n,q=audio_url_parts(url)
            if n!=page['session_number'] or url in source_by_url:raise ValueError('Duplicate/misassigned source URL')
            source_by_url[url]=page
    rows=sizes.get('records',sizes.get('results'))
    if not isinstance(rows,list):raise ValueError('Per-URL HEAD records are required')
    by_url={}
    for row in rows:
        url=row.get('url');n,q=audio_url_parts(url)
        if url in by_url or url not in source_by_url:raise ValueError('HEAD input has a duplicate or extraneous source')
        if row.get('status')!=200 or row.get('retrieval_status')!='head_verified':raise ValueError('Every chosen audio source needs a successful size/type audit')
        size=row.get('content_length')
        if isinstance(size,bool) or not isinstance(size,int) or not 0<size<=256*1024**2:raise ValueError('Audio byte length is missing or out of bounds')
        if row.get('content_type','').split(';')[0].strip().lower() not in {'audio/mpeg','audio/mp3'}:raise ValueError('HEAD result is not MP3 audio')
        if row.get('source_page_sha256')!=source_by_url[url]['sha256']:raise ValueError('HEAD result has different source-page provenance')
        by_url[url]=dict(row,session_number=n,segment_number=q)
    if set(by_url)!=set(source_by_url):raise ValueError('Size inventory does not cover every published audio URL')
    return sorted(by_url.values(),key=lambda r:(r['session_number'],r['segment_number'])),source_by_url


def atomic_progress(path,value):
    temporary=path.with_suffix(path.suffix+'.new')
    with temporary.open('w',encoding='utf8') as stream:
        os.chmod(temporary,0o600);json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
    os.replace(temporary,path)


def download_audio(frame_path,sizes_path,output,max_bytes,reserve_bytes,workers=2,reuse_pilot=None,retry_transient=False):
    output=private_root(output)
    if (output/'source-halt.json').exists():raise ValueError('A prior source-wide denial requires an inspected, supported repair before further media requests')
    if workers not in (1,2):raise ValueError('Only one or two transfer workers are supported')
    if isinstance(reserve_bytes,bool) or not isinstance(reserve_bytes,int) or reserve_bytes<1024**3:raise ValueError('Explicit reserve must be at least1GiB')
    if isinstance(max_bytes,bool) or not isinstance(max_bytes,int) or max_bytes<=0:raise ValueError('Positive integer byte budget required')
    rows,pages=validate_audio_inputs(frame_path,sizes_path);total=sum(r['content_length'] for r in rows)
    if total>max_bytes:raise ValueError('Exact source byte total exceeds the explicitly authorized batch budget')
    configuration={'schema_version':1,'frame_sha256':sha(frame_path),'head_inventory_sha256':sha(sizes_path),
        'max_bytes':max_bytes,'reserve_bytes':reserve_bytes,'workers':workers,'source_count':len(rows),
        'expected_original_bytes':total,'script_sha256':sha(Path(__file__)),
        'method':'User-requested private retrieval of explicitly published original-audio segments; no concatenation, ASR, decoded PCM, checkout, or alternate egress.'}
    config_path=output/'configuration.json'
    if config_path.exists():
        if json.loads(config_path.read_text())!=configuration:raise ValueError('Resume configuration differs; do not silently change frozen inputs or code')
    else:write_json(config_path,configuration)
    pilot=None
    if reuse_pilot:
        pilot=json.loads(Path(reuse_pilot).read_text());pp=Path(pilot['path'])
        if pilot.get('status')!=200 or pp.stat().st_size!=pilot['bytes'] or sha(pp)!=pilot['sha256'] or pilot['url'] not in pages:
            raise ValueError('Pilot source bytes/proof are invalid')
        if next(r['content_length'] for r in rows if r['url']==pilot['url'])!=pilot['bytes']:raise ValueError('Pilot differs from frozen size audit')
    existing=0
    for row in rows:
        n,q=row['session_number'],row['segment_number'];p=output/f'session-{n:03d}'/f'{n:03d}-{q:03d}.mp3';rp=p.with_suffix('.receipt.json')
        if p.exists() and rp.exists():
            old=json.loads(rp.read_text())
            if old.get('status')!='verified' or old.get('url')!=row['url'] or old.get('bytes')!=p.stat().st_size or old.get('sha256')!=sha(p):raise ValueError('Existing admitted audio changed')
            existing+=p.stat().st_size
        elif p.exists():raise ValueError('Unadmitted existing audio file requires inspection')
    if pilot:
        pn,pq=audio_url_parts(pilot['url']);pilot_target=output/f'session-{pn:03d}'/f'{pn:03d}-{pq:03d}.mp3'
    pilot_reuse=pilot['bytes'] if pilot and not pilot_target.exists() else 0
    required=max(0,total-existing-pilot_reuse)
    if shutil.disk_usage(output).free<reserve_bytes+required+32*1024**2:raise ValueError('Exact pending bytes would consume the explicitly reserved free space')
    attempts=output/'attempts';attempts.mkdir(exist_ok=True,mode=0o700)
    attempt_number=1+max([int(p.stem) for p in attempts.glob('*.json')],default=0)
    write_json(attempts/f'{attempt_number:03d}.json',{'attempt_number':attempt_number,'retry_transient':retry_transient,
        'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'configuration_sha256':sha(config_path)})
    suffix='' if attempt_number==1 else '-retry' if attempt_number==2 and retry_transient else f'-attempt-{attempt_number:03d}'
    gate=RateGate(.2);halt=threading.Event();lock=threading.Lock();completed=[];failed=[];events=output/'events.jsonl'
    def progress():
        atomic_progress(output/'progress.json',{'status':'running','completed':len(completed),'failed':len(failed),
            'expected_sources':len(rows),'verified_bytes':sum(x['bytes'] for x in completed),
            'free_bytes':shutil.disk_usage(output).free,'reserve_bytes':reserve_bytes,'source_wide_halt':halt.is_set(),
            'updated_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    def one(row):
        n,q=row['session_number'],row['segment_number'];folder=output/f'session-{n:03d}';folder.mkdir(exist_ok=True,mode=0o700)
        path=folder/f'{n:03d}-{q:03d}.mp3';rp=path.with_suffix('.receipt.json');failure=path.with_suffix('.failure.json');partial=path.with_suffix('.mp3.partial')
        latest_failure=path.with_suffix('.latest-failure.json')
        attempted=False
        try:
            if halt.is_set():raise ValueError('Deferred after source-wide denial or resource failure')
            if rp.exists():
                rec=json.loads(rp.read_text())
                if rec.get('status')!='verified' or rec.get('url')!=row['url'] or rec.get('bytes')!=path.stat().st_size or rec.get('sha256')!=sha(path):raise ValueError('Retained audio or proof changed')
            else:
                if failure.exists():
                    prior=json.loads((latest_failure if latest_failure.exists() else failure).read_text())
                    deferred=prior.get('attempted') is False and prior.get('http_status') is None and not prior.get('partial_retained')
                    if not deferred and (not retry_transient or prior.get('http_status') not in (500,502,503,504)):raise ValueError('Prior failure is not eligible for this explicit transient retry')
                if partial.exists():raise ValueError('Existing partial bytes require inspection; no implicit restart or range recovery')
                if shutil.disk_usage(output).free<reserve_bytes+row['content_length']+32*1024**2:
                    halt.set();raise ValueError('Free-space reserve prevents another media transfer')
                reused=pilot is not None and row['url']==pilot['url']
                if reused:
                    if row.get('etag') and pilot['headers'].get('ETag') and row['etag']!=pilot['headers']['ETag']:raise ValueError('Pilot ETag differs from frozen HEAD audit')
                    os.link(pilot['path'],partial);headers=pilot['headers'];http_status=200
                else:
                    gate.wait()
                    if halt.is_set():raise ValueError('Deferred after another worker reported a source-wide failure')
                    attempted=True
                    with urlopen(Request(row['url'],headers={'User-Agent':'Channels-ET-personal-research-archive/1.0'}),timeout=90) as response:
                        http_status=response.status
                        if http_status!=200 or response.url!=row['url']:raise ValueError('Unexpected media response status or redirect')
                        headers={k:response.headers.get(k) for k in ('Content-Type','Content-Length','Last-Modified','ETag')}
                        if int(headers.get('Content-Length') or 0)!=row['content_length']:raise ValueError('Media length changed after frozen HEAD audit')
                        if (headers.get('Content-Type') or '').split(';')[0].lower() not in {'audio/mpeg','audio/mp3'}:raise ValueError('Response is not declared audio')
                        if row.get('etag') and headers.get('ETag') and row['etag']!=headers['ETag']:raise ValueError('Media ETag changed after frozen HEAD audit')
                        count=0
                        with partial.open('xb') as stream:
                            os.chmod(partial,0o600)
                            while True:
                                chunk=response.read(1024**2)
                                if not chunk:break
                                count+=len(chunk)
                                if count>row['content_length']:raise ValueError('Transfer exceeded declared bytes')
                                if shutil.disk_usage(output).free<reserve_bytes+len(chunk):halt.set();raise ValueError('Free-space reserve changed during transfer')
                                stream.write(chunk)
                        if count!=row['content_length']:raise ValueError('Incomplete media response')
                if partial.stat().st_size!=row['content_length']:raise ValueError('Stored byte count differs from frozen source')
                probe=audio_probe(partial);digest=sha(partial)
                if path.exists():raise ValueError('Target appeared during transfer')
                os.rename(partial,path)
                rec={'schema_version':1,'status':'verified','source_id':f'ra:audio:{n:03d}:{q:03d}',
                    'session_id':f'ra:session:{n:03d}','session_number':n,'question_id':f'{n}.{q}','segment_number':q,
                    'provider':'lawofone-info-authorized-edition','source_kind':'publisher_original_audio_segment',
                    'url':row['url'],'source_page':pages[row['url']]['source_page'],'source_page_sha256':pages[row['url']]['sha256'],
                    'path':str(path),'bytes':path.stat().st_size,'sha256':digest,'probe':probe,'http_status':http_status,
                    'headers':headers,'reused_pilot_hardlink':reused,'head_inventory_sha256':configuration['head_inventory_sha256'],
                    'script_sha256':configuration['script_sha256'],'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                    'scope':'Publisher-provided original recording segment; not a full continuous tape or independently authenticated voice/entity.'}
                write_json(rp,rec)
            with lock:
                completed.append(rec)
                with events.open('a',encoding='utf8') as log:log.write(json.dumps({'source_id':rec['source_id'],'status':'verified','bytes':rec['bytes']})+'\n')
                if len(completed)%20==0:progress()
        except Exception as error:
            code=error.code if isinstance(error,HTTPError) else None
            global_failure=code in (401,403,407,429,451) or (isinstance(error,URLError) and not isinstance(error,HTTPError)) or isinstance(error,TimeoutError)
            if global_failure:halt.set()
            rec={'source_id':f'ra:audio:{n:03d}:{q:03d}','url':row['url'],'http_status':code,
                'error_type':type(error).__name__,'message':str(error)[:220],'partial_retained':partial.exists(),
                'attempted':attempted,'attempt_number':attempt_number,
                'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
            with lock:
                failed.append(rec)
                if global_failure and not (output/'source-halt.json').exists():write_json(output/'source-halt.json',rec)
                if not failure.exists():write_json(failure,rec)
                else:write_json(path.with_suffix(f'.failure-attempt-{attempt_number:03d}.json'),rec)
                atomic_progress(latest_failure,rec)
                with events.open('a',encoding='utf8') as log:log.write(json.dumps(rec)+'\n')
                progress()
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(one,rows))
    completed.sort(key=lambda r:(r['session_number'],r['segment_number']))
    if sha(Path(__file__))!=configuration['script_sha256']:raise ValueError('Downloader source changed during execution')
    playlists=[]
    for n in range(1,107):
        clips=[r for r in completed if r['session_number']==n]
        if not clips:continue
        text='#EXTM3U\n'+''.join(f'#EXTINF:{r["probe"]["duration_seconds"]:.6f},Ra {r["question_id"]}\n{Path(r["path"]).name}\n' for r in clips)
        p=output/f'session-{n:03d}'/f'session{suffix}.m3u'
        if p.exists():
            if p.read_text()!=text:raise ValueError('Existing playlist differs; preserve partial edition and choose a distinct release index')
        else:
            with p.open('x',encoding='utf8') as stream:os.chmod(p,0o600);stream.write(text)
        playlists.append(artifact(p,'ordered_session_playlist'))
    manifest={'schema_version':1,'kind':'verified-ra-published-original-audio-segments',
        'status':'completed' if len(completed)==len(rows) and not failed else 'partial',
        'records':completed,'failures':failed,'source_count':len(rows),'verified_segments':len(completed),'attempt_number':attempt_number,
        'verified_bytes':sum(r['bytes'] for r in completed),'duration_seconds':sum(r['probe']['duration_seconds'] for r in completed),
        'playlists':playlists,'configuration':configuration,'free_bytes_at_end':shutil.disk_usage(output).free,
        'scope':'Complete means every explicitly published segment in the frozen player-page frame; historical audio gaps and tape-master editions are separate.'}
    target=output/f'audio-manifest{suffix}.json'
    write_json(target,manifest);atomic_progress(output/'progress.json',{k:manifest[k] for k in ('status','source_count','verified_segments','verified_bytes','duration_seconds','free_bytes_at_end')})
    return manifest


def decoded_duration(path):
    """Decode to a null sink: retain no PCM; report actual emitted audio time."""
    import subprocess
    result=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(path),
        '-map','0:a:0','-vn','-threads','1','-f','null','-','-progress','pipe:1','-nostats'],
        capture_output=True,text=True,check=True,timeout=1800)
    values=[int(x) for x in re.findall(r'^out_time_us=(\d+)$',result.stdout,re.M)]
    if not values or values[-1]<=0 or 'progress=end' not in result.stdout:raise ValueError('Full audio decode did not report completion')
    return values[-1]/1_000_000


def encode_compact(source,target,channels):
    import subprocess
    if channels not in (1,2):raise ValueError('Source channel count requires explicit codec review')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(source),
        '-map','0:a:0','-map_metadata','-1','-vn','-ac',str(channels),'-c:a','libopus','-b:a','48k',
        '-vbr','off','-compression_level','5','-application','audio','-frame_duration','20','-threads','1',
        '-f','opus',str(target)],capture_output=True,text=True,check=True,timeout=1800)


def compact_probe(path):
    import subprocess
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries',
        'format=duration,size,format_name:stream=codec_name,codec_type,sample_rate,channels',
        '-of','json',str(path)],capture_output=True,text=True,check=True,timeout=30)
    value=json.loads(result.stdout);fmt=value.get('format',{});streams=value.get('streams',[])
    if fmt.get('format_name')!='ogg' or len(streams)!=1 or streams[0].get('codec_name')!='opus' or streams[0].get('codec_type')!='audio':
        raise ValueError('Retained copy is not one Opus audio stream in Ogg')
    return {'format_name':'ogg','codec':'opus','streams':streams,'duration_seconds':float(fmt['duration'])}


def download_compact_audio(frame_path,sizes_path,output,max_bytes,reserve_bytes,max_retained_bytes,
                           scratch_bytes=256*1024**2,workers=2,reuse_pilot=None,retry_transient=False):
    """Retain full-length lossy 48 kbps CBR Opus copies, not the original MP3s."""
    import math
    output=private_root(output)
    if any((output/p).exists() for p in ('source-halt.json','review-halt.json')):raise ValueError('Prior source/resource/verification halt requires inspection before resuming')
    if workers not in (1,2) or reserve_bytes<3*1024**3 or scratch_bytes!=256*1024**2 or not 0<max_retained_bytes<=4*1024**3:
        raise ValueError('Compact mode requires 1–2 workers, >=3 GiB reserve, 256 MiB scratch, and <=4 GiB retained ceiling')
    rows,pages=validate_audio_inputs(frame_path,sizes_path);total=sum(r['content_length'] for r in rows)
    if total!=max_bytes:raise ValueError('Compact original transfer budget must equal the inspected complete HEAD total')
    per_worker_scratch=scratch_bytes//workers
    if any(r['content_length']>=per_worker_scratch for r in rows):raise ValueError('A source cannot fit its bounded worker staging share')
    if shutil.disk_usage(output).free<reserve_bytes+scratch_bytes:raise ValueError('Free-space floor plus scratch reserve unavailable')
    config={'schema_version':1,'frame_sha256':sha(frame_path),'head_inventory_sha256':sha(sizes_path),'script_sha256':sha(Path(__file__)),
        'max_original_transfer_bytes':max_bytes,'max_retained_bytes':max_retained_bytes,'reserve_bytes':reserve_bytes,'scratch_bytes':scratch_bytes,
        'workers':workers,'source_count':len(rows),'format':'Ogg Opus','target_bitrate_bps':48000,'vbr':False,
        'audio_selection':'entire first audio stream; preserve source channel count; no trimming or silence removal',
        'encoder_threads_per_worker':1,'decoded_duration_tolerance_seconds':0.050}
    cp=output/'configuration.json'
    if cp.exists():
        if json.loads(cp.read_text())!=config:raise ValueError('Frozen compact configuration differs')
    else:write_json(cp,config)
    pilot=None
    if reuse_pilot:
        pilot=json.loads(Path(reuse_pilot).read_text());pp=Path(pilot['path'])
        if pilot.get('status')!=200 or pilot.get('url') not in pages or pp.stat().st_size!=pilot['bytes'] or sha(pp)!=pilot['sha256']:raise ValueError('Pilot proof does not match retained original')
        expected=next(r for r in rows if r['url']==pilot['url'])
        if expected['content_length']!=pilot['bytes'] or (expected.get('etag') and pilot['headers'].get('ETag') and expected['etag']!=pilot['headers']['ETag']):raise ValueError('Pilot differs from final HEAD evidence')
    existing_retained=0;existing_sources=0
    for row in rows:
        n,q=row['session_number'],row['segment_number'];folder=output/f'session-{n:03d}';stem=f'{n:03d}-{q:03d}'
        rp=folder/f'{stem}.receipt.json';path=folder/f'{stem}.opus';sp=folder/f'{stem}.original-source.json';source=folder/f'{stem}.source.mp3'
        if rp.exists():
            r=json.loads(rp.read_text())
            if r.get('status')!='verified_compact_copy' or r.get('url')!=row['url'] or not path.is_file() or path.stat().st_size!=r['retained']['bytes'] or sha(path)!=r['retained']['sha256']:raise ValueError('Retained compact copy/proof changed')
            existing_retained+=path.stat().st_size
        elif path.exists():raise ValueError('Unadmitted existing compact copy requires inspection')
        if sp.exists():
            s=json.loads(sp.read_text())
            if s.get('url')!=row['url'] or s.get('bytes')!=row['content_length']:raise ValueError('Retained original-source proof differs')
            existing_sources+=s['bytes']
            unfinished_input=Path(pilot['path']) if pilot and s.get('reused_existing_pilot') and row['url']==pilot['url'] else source
            if not rp.exists() and (not unfinished_input.exists() or unfinished_input.stat().st_size!=s['bytes'] or sha(unfinished_input)!=s['sha256']):raise ValueError('Unfinished original source is unavailable or changed')
        elif source.exists():raise ValueError('Unadmitted original staging bytes require inspection')
    if existing_retained>max_retained_bytes or existing_sources>max_bytes:raise ValueError('Existing corpus exceeds frozen budget')
    attempts=output/'attempts';attempts.mkdir(exist_ok=True,mode=0o700)
    attempt_number=1+max([int(p.stem) for p in attempts.glob('*.json')],default=0)
    write_json(attempts/f'{attempt_number:03d}.json',{'attempt_number':attempt_number,'retry_transient':retry_transient,'started_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    suffix='' if attempt_number==1 else f'-attempt-{attempt_number:03d}'
    gate=RateGate(.2);halt=threading.Event();lock=threading.Lock();completed=[];failures=[]
    totals={'retained':existing_retained,'reserved_output':0,'source_verified':existing_sources,'transferred_this_attempt':0}
    def progress():
        atomic_progress(output/'progress.json',{'status':'running','completed':len(completed),'failed':len(failures),'expected_sources':len(rows),
            **totals,'free_bytes':shutil.disk_usage(output).free,'halted':halt.is_set(),'updated_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    def one(row):
        n,q=row['session_number'],row['segment_number'];folder=output/f'session-{n:03d}';folder.mkdir(exist_ok=True,mode=0o700);stem=f'{n:03d}-{q:03d}'
        source=folder/f'{stem}.source.mp3';sp=folder/f'{stem}.original-source.json';target=folder/f'{stem}.opus';temporary=folder/f'{stem}.opus.partial'
        rp=folder/f'{stem}.receipt.json';latest=folder/f'{stem}.latest-failure.json';attempted=False;body_bytes=0;reserved=0
        try:
            if rp.exists():
                rec=json.loads(rp.read_text())
                if source.exists():
                    original=json.loads(sp.read_text())
                    if source.stat().st_size!=original['bytes'] or sha(source)!=original['sha256']:raise ValueError('Pending original cleanup bytes changed')
                    source.unlink();write_json(folder/f'{stem}.cleanup-resume-{attempt_number:03d}.json',{'deleted_only_new_task_temporary_original':str(source),'source_sha256':original['sha256']})
            else:
                if halt.is_set():raise ValueError('Deferred after source/resource/verification halt')
                if latest.exists():
                    prior=json.loads(latest.read_text());deferred=not prior.get('attempted') and not prior.get('source_staging_exists') and not prior.get('output_staging_exists')
                    if not deferred and (not retry_transient or prior.get('http_status') not in (500,502,503,504)):raise ValueError('Failure is not eligible for explicit transient retry')
                if temporary.exists():raise ValueError('Existing compact partial requires inspection')
                if shutil.disk_usage(output).free<reserve_bytes+scratch_bytes:raise ValueError('Free-space floor plus scratch unavailable')
                reused=pilot is not None and row['url']==pilot['url']
                input_path=Path(pilot['path']) if reused else source
                if sp.exists():original=json.loads(sp.read_text())
                else:
                    if source.exists():raise ValueError('Unadmitted source staging requires inspection')
                    if reused:headers=pilot['headers']
                    else:
                        gate.wait()
                        if halt.is_set():raise ValueError('Deferred after another worker halted')
                        attempted=True
                        with urlopen(Request(row['url'],headers={'User-Agent':'Channels-ET-personal-research-archive/1.0'}),timeout=90) as response:
                            if response.status!=200 or response.url!=row['url']:raise ValueError('Unexpected original response or redirect')
                            headers={k:response.headers.get(k) for k in ('Content-Type','Content-Length','ETag','Last-Modified')}
                            if int(headers.get('Content-Length') or 0)!=row['content_length'] or (headers.get('Content-Type') or '').split(';')[0].lower() not in {'audio/mpeg','audio/mp3'}:raise ValueError('Original headers differ from final size/type audit')
                            if row.get('etag') and headers.get('ETag') and row['etag']!=headers['ETag']:raise ValueError('Original ETag changed')
                            with source.open('xb') as stream:
                                os.chmod(source,0o600)
                                while True:
                                    chunk=response.read(1024**2)
                                    if not chunk:break
                                    body_bytes+=len(chunk)
                                    if body_bytes>row['content_length']:raise ValueError('Original exceeded authorized per-source bytes')
                                    with lock:totals['transferred_this_attempt']+=len(chunk)
                                    if shutil.disk_usage(output).free<reserve_bytes+len(chunk):raise ValueError('Free-space floor changed during original transfer')
                                    stream.write(chunk)
                            if body_bytes!=row['content_length']:raise ValueError('Original transfer truncated')
                    if input_path.stat().st_size!=row['content_length']:raise ValueError('Original stored byte length differs')
                    probe=audio_probe(input_path);original={'url':row['url'],'bytes':row['content_length'],'sha256':sha(input_path),'probe':probe,'headers':headers,
                        'reused_existing_pilot':reused,'source_page_sha256':pages[row['url']]['sha256'],'head_inventory_sha256':config['head_inventory_sha256'],
                        'script_sha256':config['script_sha256'],'verified_at':dt.datetime.now(dt.timezone.utc).isoformat()}
                    write_json(sp,original)
                    with lock:
                        totals['source_verified']+=original['bytes']
                        if totals['source_verified']>max_bytes:raise ValueError('Original verified bytes exceeded exact cumulative budget')
                channels=original['probe']['streams'][0]['channels'];input_duration=decoded_duration(input_path)
                bound=math.ceil(input_duration*6000*1.02)+128*1024
                if row['content_length']+bound>per_worker_scratch:raise ValueError('Source plus compact output exceeds bounded worker scratch')
                with lock:
                    if totals['retained']+totals['reserved_output']+bound>max_retained_bytes:raise ValueError('Retained-copy budget cannot reserve this output')
                    if shutil.disk_usage(output).free<reserve_bytes+scratch_bytes+totals['reserved_output']+bound:raise ValueError('Output reservation would consume floor or scratch')
                    totals['reserved_output']+=bound;reserved=bound
                encode_compact(input_path,temporary,channels)
                os.chmod(temporary,0o600)
                if not 0<temporary.stat().st_size<=bound:raise ValueError('Encoded copy exceeds bounded output allowance')
                probe=compact_probe(temporary)
                if probe['streams'][0]['channels']!=channels:raise ValueError('Encoding changed channel count')
                output_duration=decoded_duration(temporary);delta=output_duration-input_duration
                if abs(delta)>config['decoded_duration_tolerance_seconds']:raise ValueError('Decoded duration differs beyond explicit 50 ms padding tolerance')
                retained={'path':str(target),'bytes':temporary.stat().st_size,'sha256':sha(temporary),'probe':probe,
                    'decoded_duration_seconds':output_duration,'format':'Ogg Opus','target_bitrate_bps':48000,'vbr':False,'lossy_derivative':True}
                os.rename(temporary,target)
                rec={'schema_version':1,'status':'verified_compact_copy','source_id':f'ra:audio:{n:03d}:{q:03d}','session_id':f'ra:session:{n:03d}',
                    'session_number':n,'segment_number':q,'question_id':f'{n}.{q}','url':row['url'],'retained':retained,'original':original,
                    'original_source_receipt':artifact(sp,'verified_original_bytes_before_transcoding'),'input_decoded_duration_seconds':input_duration,
                    'decoded_duration_difference_seconds':delta,'decoded_duration_tolerance_seconds':0.050,'channels_preserved':channels,
                    'original_mp3_retained':reused,'existing_pilot_path':pilot['path'] if reused else None,'script_sha256':config['script_sha256'],
                    'scope':'Full-length lossy compact copy of publisher original-recording segment; original MP3 hash/bytes verified before transcoding. No listening or speaker/entity authentication.'}
                write_json(rp,rec)
                if not reused:
                    if source.stat().st_size!=original['bytes'] or sha(source)!=original['sha256']:raise ValueError('Source changed before authorized temporary cleanup')
                    source.unlink();write_json(folder/f'{stem}.cleanup.json',{'deleted_only_new_task_temporary_original':str(source),'source_sha256':original['sha256'],'verified_retained_receipt_sha256':sha(rp)})
                with lock:
                    totals['retained']+=retained['bytes'];totals['reserved_output']-=reserved;reserved=0
            with lock:
                completed.append(rec)
                if len(completed)%10==0:progress()
        except Exception as error:
            code=error.code if isinstance(error,HTTPError) else None
            global_source=code in (401,403,407,429,451) or (isinstance(error,URLError) and not isinstance(error,HTTPError)) or isinstance(error,TimeoutError)
            transient=code in (500,502,503,504) and not source.exists() and not temporary.exists()
            deferred=not attempted and not source.exists() and not temporary.exists() and halt.is_set()
            if not transient:halt.set()
            failure={'url':row['url'],'session_number':n,'segment_number':q,'http_status':code,'attempted':attempted,'attempt_number':attempt_number,
                'body_bytes_read':body_bytes,'source_staging_exists':source.exists(),'output_staging_exists':temporary.exists(),'error_type':type(error).__name__,'message':str(error)[:250]}
            with lock:
                if reserved:totals['reserved_output']-=reserved
                failures.append(failure);write_json(folder/f'{stem}.failure-attempt-{attempt_number:03d}.json',failure);atomic_progress(latest,failure)
                halt_path=output/('source-halt.json' if global_source else 'review-halt.json')
                if not transient and not deferred and not halt_path.exists():write_json(halt_path,failure)
                progress()
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(one,rows))
    if sha(Path(__file__))!=config['script_sha256']:raise ValueError('Compact downloader source changed during execution')
    completed.sort(key=lambda r:(r['session_number'],r['segment_number']));playlists=[]
    for n in range(1,107):
        clips=[r for r in completed if r['session_number']==n]
        if not clips:continue
        p=output/f'session-{n:03d}'/f'session{suffix}.m3u'
        with p.open('x') as stream:
            os.chmod(p,0o600);stream.write('#EXTM3U\n'+''.join(f'#EXTINF:{r["retained"]["decoded_duration_seconds"]:.6f},Ra {r["question_id"]}\n{Path(r["retained"]["path"]).name}\n' for r in clips))
        playlists.append(artifact(p,'ordered_compact_session_playlist'))
    result={'schema_version':1,'kind':'verified-ra-published-recording-compact-copies','status':'completed' if len(completed)==len(rows) and not failures else 'partial',
        'records':completed,'failures':failures,'source_count':len(rows),'verified_segments':len(completed),'retained_bytes':sum(r['retained']['bytes'] for r in completed),
        'original_verified_bytes':sum(r['original']['bytes'] for r in completed),'original_mp3s_retained':sum(r['original_mp3_retained'] for r in completed),
        'duration_seconds':sum(r['retained']['decoded_duration_seconds'] for r in completed),'playlists':playlists,'configuration':config,'attempt_number':attempt_number,
        'free_bytes_at_end':shutil.disk_usage(output).free,'scope':'Full-length 48 kbps CBR Opus derivatives of published original-recording segments. Completeness means frozen linked segment frame, not continuous tape masters.'}
    write_json(output/f'audio-manifest{suffix}.json',result);atomic_progress(output/'progress.json',{k:result[k] for k in ('status','source_count','verified_segments','retained_bytes','duration_seconds','free_bytes_at_end')})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=['transcripts','audio-inventory','audio','compact-audio'],default='transcripts')
    p.add_argument('--discovery',type=Path);p.add_argument('--sessions',default='1-106');p.add_argument('--workers',type=int,choices=[1,2],default=2)
    p.add_argument('--audio-frame',type=Path);p.add_argument('--sizes',type=Path)
    p.add_argument('--max-bytes',type=int);p.add_argument('--reserve-bytes',type=int)
    p.add_argument('--max-retained-bytes',type=int);p.add_argument('--scratch-bytes',type=int,default=256*1024**2)
    p.add_argument('--reuse-pilot',type=Path);p.add_argument('--retry-transient',action='store_true')
    a=p.parse_args();sessions=[]
    if a.mode in ('audio','compact-audio'):
        if any(v is None for v in (a.audio_frame,a.sizes,a.max_bytes,a.reserve_bytes)):
            p.error('Audio mode requires frozen frame/sizes plus explicit byte budget and free-space reserve')
        if a.mode=='compact-audio':
            if a.max_retained_bytes is None:p.error('Compact mode requires an explicit retained-byte ceiling')
            result=download_compact_audio(a.audio_frame,a.sizes,a.output,a.max_bytes,a.reserve_bytes,a.max_retained_bytes,a.scratch_bytes,a.workers,a.reuse_pilot,a.retry_transient)
        else:result=download_audio(a.audio_frame,a.sizes,a.output,a.max_bytes,a.reserve_bytes,a.workers,a.reuse_pilot,a.retry_transient)
        print(json.dumps({k:result[k] for k in ('status','verified_segments','duration_seconds','free_bytes_at_end')}))
        if result['status']!='completed':raise SystemExit(1)
        return
    if not a.discovery:p.error('Transcript and inventory modes require retained discovery/edition evidence')
    for part in a.sessions.split(','):
        if '-' in part:
            lo,hi=map(int,part.split('-'));sessions.extend(range(lo,hi+1))
        else:sessions.append(int(part))
    if len(sessions)!=len(set(sessions)) or not sessions or min(sessions)<1 or max(sessions)>106:raise ValueError('Unique canonical session numbers1–106 required')
    if a.mode=='audio-inventory':
        result=inventory_audio(a.output,a.discovery,sessions,a.workers)
        print(json.dumps({k:result[k] for k in ('source_page_count','published_audio_segments','failures')}))
        if result['failures']:raise SystemExit(1)
        return
    result=collect(a.output,a.discovery,sessions,a.workers)
    print(json.dumps({'retrieved':len(result['records']),'failures':result['failures'],'words':sum(r['whitespace_words'] for r in result['records'])}))
    if result['failures']:raise SystemExit(1)
if __name__=='__main__':main()
