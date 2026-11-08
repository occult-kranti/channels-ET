#!/usr/bin/env python3
"""Verify retained Bashar-context ASR and acquire explicit official handout PDFs.

Raw audio/text stay outside Git. A publisher interview is not a verified Bashar
channeling session, and an official handout is not a video transcript.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
import html as html_module
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=Path('/workspace/channels-et-private/bashar-ra-2026-11/bashar')
MIN_RESERVE=6*1024**3
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
    return h.hexdigest()

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')

def private_path(value,exists=True):
    p=Path(value)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('Private path must be absolute without traversal')
    for part in (p,*p.parents):
        if part.is_symlink():raise ValueError('Symlink routes are not admitted')
        marker=part/'.git'
        if marker.exists() and not(marker.is_dir() and not any(marker.iterdir())):
            raise ValueError('Raw sources must remain outside Git')
    if exists and not p.is_file():raise ValueError('Retained file is missing')
    return p

def artifact(path,role):
    p=Path(path);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'role':role}

def verify_artifact(path,binding):
    p=private_path(path)
    if isinstance(binding.get('bytes'),bool) or not isinstance(binding.get('bytes'),int) or binding['bytes']<1:
        raise ValueError('Invalid artifact byte binding')
    if p.stat().st_size!=binding['bytes'] or sha(p)!=binding.get('sha256'):
        raise ValueError('Retained artifact bytes changed')
    return p

def safe_url(value):
    p=urlsplit(str(value or ''))
    if p.scheme!='https' or not p.hostname or p.username or p.password:return None
    return urlunsplit((p.scheme,p.netloc,p.path,'',''))

def published_date(value):
    try:return parsedate_to_datetime(value).isoformat()
    except (TypeError,ValueError,OverflowError):return None

def probe_audio(path):
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
        '-show_entries','format=duration:stream=codec_type,codec_name','-of','json',str(path)],
        check=True,capture_output=True,text=True,timeout=60)
    value=json.loads(result.stdout);duration=float(value['format']['duration'])
    if not math.isfinite(duration) or duration<300 or not any(s.get('codec_type')=='audio' for s in value['streams']):
        raise ValueError('Retained long-form audio does not validate')
    return duration

def verify_pair(publisher,summary,*,allow_fixtures=False):
    sid=summary.get('sourceId')
    if not isinstance(sid,str) or not ID.fullmatch(sid) or publisher.get('source_id')!=sid:
        raise ValueError('Publisher/ASR source identity differs')
    if not allow_fixtures and (publisher.get('fixture_only') or summary.get('fixture_only')):
        raise ValueError('Synthetic data cannot enter an actual corpus')
    if publisher.get('status')!='completed' or summary.get('status')!='completed':
        raise ValueError('Only completed retained sources are admitted')
    if publisher.get('source_kind')!='independent_original_publisher_rss_audio' or summary.get('sourceKind')!='publisher_original_audio':
        raise ValueError('Metadata/digests/reference texts are not publisher-audio ASR')
    folder=private_path(summary['transcriptDirectory'],False)
    receipt_path=private_path(folder/'receipt.json');receipt=read(receipt_path)
    if not allow_fixtures and receipt.get('fixture_only'):raise ValueError('Synthetic receipt is not an actual source')
    expected={k:v for k,v in summary.items() if k!='transcriptDirectory'}
    if receipt!=expected:raise ValueError('Summary differs from retained ASR receipt')
    if receipt.get('transcribedScope')!='full_decoded_audio' or receipt.get('clipSeconds') is not None:
        raise ValueError('Diagnostic or partial ASR is not a full source')
    protocol=receipt.get('executionProtocol',{})
    if hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()!=receipt.get('executionSignature'):
        raise ValueError('ASR execution binding changed')
    if protocol.get('sourceId')!=sid or protocol.get('audioSha256')!=publisher.get('sha256') or protocol.get('sourceUrl')!=publisher.get('enclosure_url'):
        raise ValueError('ASR protocol does not bind this publisher edition')
    if receipt.get('sourceAudioSha256')!=publisher.get('sha256') or receipt.get('sourceUrl')!=publisher.get('enclosure_url'):
        raise ValueError('Source URL/hash differs')
    if Path(receipt['sourceAudioPath'])!=Path(publisher['raw_local_path']):raise ValueError('Source audio path differs')
    audio=verify_artifact(publisher['raw_local_path'],publisher)
    duration=probe_audio(audio)
    if abs(duration-receipt['sourceAudioDurationSeconds'])>.05 or abs(duration-publisher['duration_seconds'])>.05:
        raise ValueError('Retained measured duration differs')
    outputs=receipt.get('outputs',[])
    if len(outputs)!=3 or {x.get('name') for x in outputs}!={'segments.jsonl','transcript.txt','transcript.srt'}:
        raise ValueError('Full ASR artifact set is missing or duplicated')
    for row in outputs:verify_artifact(folder/row['name'],row)
    segments=[json.loads(line) for line in (folder/'segments.jsonl').read_text().splitlines() if line]
    texts=[];previous=-1.0
    for row in segments:
        start,end=row.get('start'),row.get('end')
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (start,end)):
            raise ValueError('Invalid ASR timestamp')
        if start<0 or start<previous or end<start or end>duration+2:
            raise ValueError('Unreviewed ASR timestamp anomaly')
        if not isinstance(row.get('text'),str):raise ValueError('ASR segment lacks text')
        previous=start;texts.append(row['text'])
    text='\n'.join(texts)
    if (folder/'transcript.txt').read_text()!=text+'\n':raise ValueError('Segments and full text differ')
    if len(segments)!=receipt.get('segments') or len(text.split())!=receipt.get('words'):
        raise ValueError('ASR counts differ from actual text')
    return {'source_id':sid,'publisher':publisher,'receipt':receipt,'receipt_path':receipt_path,
        'audio':audio,'folder':folder,'segments':segments,'text':text,'duration':duration}

def inventory(output,publisher_path=None,asr_path=None):
    output=private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh output directory')
    publisher_path=Path(publisher_path or ROOT/'research/harvest/publisher_sources/publisher-summary.json')
    asr_path=Path(asr_path or ROOT/'research/harvest/asr/summary.json')
    pub=read(publisher_path);asr=read(asr_path)
    by_id={r['source_id']:r for r in pub['records']}
    if len(by_id)!=len(pub['records']):raise ValueError('Duplicate publisher source IDs')
    ids=[r['sourceId'] for r in asr['records']]
    if len(set(ids))!=len(ids) or set(ids)!=set(by_id):raise ValueError('ASR/publisher cohort sets differ')
    verified=[verify_pair(by_id[r['sourceId']],r) for r in asr['records']]
    if len({v['publisher']['sha256'] for v in verified})!=len(verified):raise ValueError('Duplicate exact media needs explicit reconciliation')
    output.mkdir(parents=True,mode=0o700);records=[]
    for v in verified:
        sid=v['source_id'];p=v['publisher'];r=v['receipt']
        normalized={'source_id':sid,'text':v['text'],'turns':[{'turn_id':f'{sid}:asr:{i+1}',
            'role':'unknown','text':x['text'],'start_seconds':x['start'],'end_seconds':x['end']} for i,x in enumerate(v['segments'])],
            'speaker_scope':'All segments retain unknown speaker roles; no diarization or verified Bashar voice.',
            'normalization':'Exact segment text/order; newline joining only. Original TXT has one final newline.'}
        dest=output/(sid+'.json');write(dest,normalized)
        evidence=[artifact(publisher_path,'publisher_acquisition_manifest'),artifact(asr_path,'asr_summary'),
            artifact(v['audio'],'source_audio'),artifact(v['receipt_path'],'asr_receipt')]
        evidence.extend(artifact(v['folder']/x['name'],'asr_output') for x in r['outputs'])
        records.append({'source_id':sid,'corpus':'bashar','session_id':sid,
            'session_id_basis':'RSS publication unit; original channeling-session identity unresolved',
            'duplicate_family_id':'exact-media:'+p['sha256'],'duplicate_family_basis':'exact_media_bytes_only',
            'original_session_identity':'unresolved','edition_id':p['sha256'],'source_kind':'machine_asr',
            'source_format':p['source_format'],'publisher':p['publisher_name'],'title':p['episode_title'],
            'source_url':safe_url(p['feed_url']),'audio_source_url':safe_url(p['enclosure_url']),
            'published_at':published_date(p.get('episode_publication_date')),'language':'en',
            'language_basis':'English model configuration and reported language; not human verification',
            'speaker_attribution_status':'unknown_mixed_speakers_publisher_labels_darryl_anka_or_bashar_context',
            'collection_status':'retrieved','coverage_status':'full','coverage_scope':'full_decoded_audio_ASR_not_recognition_completeness',
            'text_artifact':artifact(dest,'normalized_text'),'evidence':evidence,
            'audio_bytes':p['bytes'],'audio_duration_seconds':v['duration'],
            'asr_words':len(v['text'].split()),'asr_segments':len(v['segments']),
            'asr_model':{k:r.get(k) for k in ('modelId','modelRevision','device','computeType','executionSignature')},
            'acquisition_warning':p.get('warning'),'source_format_basis':'Retained publisher/index screening, not newly assigned voice identity',
            'human_reviewed':False,'youtube_video_edition_verified':False,
            'rights_and_access_basis':p.get('license_status'),
            'interpretation_limits':['This publication is not automatically a direct channeling session.',
                'Guest/host/advertisements are not separated; punctuation is not verified Q&A.',
                'The corpus is an available publisher sample, not all Bashar recordings.']})
    manifest={'schema_version':1,'kind':'bashar-retained-context-corpus','created_at':now(),'records':records,
        'source_inputs':[artifact(publisher_path,'publisher_summary'),artifact(asr_path,'asr_summary')],
        'summary':{'retained_recordings':len(records),'audio_bytes':sum(r['audio_bytes'] for r in records),
            'audio_seconds':sum(r['audio_duration_seconds'] for r in records),'asr_words':sum(r['asr_words'] for r in records),
            'asr_segments':sum(r['asr_segments'] for r in records),'source_formats':dict(Counter(r['source_format'] for r in records)),
            'new_audio_downloads':0,'new_ASR_runs':0,'verified_direct_channeling_recordings':0,'youtube_video_edition_verified_count':0},
        'script_sha256':sha(Path(__file__)),
        'scope':'Revalidated retained publisher-audio ASR; no YouTube request, no source media copying and no inference.'}
    write(output/'manifest.json',manifest)
    return manifest

class Links(HTMLParser):
    def __init__(self):super().__init__();self.current=None;self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.current=[dict(attrs).get('href'),'']
    def handle_data(self,data):
        if self.current:self.current[1]+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.current:self.rows.append(self.current);self.current=None

def handout_links(body):
    parser=Links();parser.feed(body);seen=set();rows=[]
    for url,title in parser.rows:
        if not url:continue
        parsed=urlsplit(url)
        if parsed.scheme=='https' and parsed.hostname=='d11n7da8rpqbjy.cloudfront.net' and parsed.path.startswith('/basharet/') and parsed.path.lower().endswith('.pdf') and not parsed.username and not parsed.password:
            if url not in seen:rows.append({'source_url':url,'title':' '.join(title.split())});seen.add(url)
    return rows

class VisibleText(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','head'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','head'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())

def official_body(html,title):
    parser=VisibleText();parser.feed(html);lines=parser.parts
    positions=[i for i,line in enumerate(lines) if line==title]
    if not positions:raise ValueError('Expected official body heading is absent')
    start=positions[-1]
    end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('©')),None)
    if end is None or end<=start+1:raise ValueError('Expected official body/footer boundary is absent')
    return '\n'.join(lines[start:end]),{'visible_text_start_index':start,'visible_text_end_index_exclusive':end,
        'extraction':'Last exact body heading to first copyright footer; script/style/head and repeated navigation excluded.'}

def official_pages(receipt_paths,output,headings):
    output=private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh official-reference output')
    indexed={}
    for receipt_path in receipt_paths:
        for row in read(receipt_path)['records']:
            if row.get('retrieval_status')=='retrieved':indexed[row.get('final_url')]=(row,Path(receipt_path))
    items=[]
    for url,title in headings.items():
        source,receipt_path=indexed[url]
        if source['status']!=200 or urlsplit(url).hostname!='www.bashar.org':raise ValueError('Unverified official reference source')
        html=verify_artifact(source['local_path'],source)
        text,method=official_body(html.read_text(),title)
        slug=urlsplit(url).path.strip('/');sid='bashar:official:'+slug
        items.append((source,receipt_path,html,text,method,sid,title))
    output.mkdir(parents=True,mode=0o700);records=[]
    for source,receipt_path,html,text,method,sid,title in items:
        dest=output/(sid+'.json');write(dest,{'source_id':sid,'text':text,'turns':[{'turn_id':sid+':body','role':'unknown','text':text}],
            'extraction':method,'scope':'Official written body; no audio/session equivalence established.'})
        records.append({'source_id':sid,'corpus':'bashar','session_id':sid,
            'session_id_basis':'Authored reference page, not a dated channeling session',
            'duplicate_family_id':sid,'edition_id':source['sha256'],'source_kind':'authored_reference',
            'source_format':'official_written_teaching','title':title,'publisher':'Bashar Communications',
            'source_url':source['final_url'],'published_at':None,'retrieved_at':source['retrieved_at'],'language':'en',
            'speaker_attribution_status':'publisher_attributed_written_teaching_not_verified_recorded_voice',
            'original_session_identity':'unresolved','collection_status':'retrieved','coverage_status':'full',
            'coverage_scope':'Full visible main text; webpage navigation/footer excluded, no linked audio represented',
            'text_artifact':artifact(dest,'normalized_text'),'evidence':[artifact(html,'source_html'),artifact(receipt_path,'retrieval_receipt')],
            'human_reviewed':False,'youtube_video_edition_verified':False,
            'rights_and_access_basis':'Official public reference page; publisher copyright retained. Private research retention only; no open republication or model-training license established.'})
    manifest={'schema_version':1,'kind':'bashar-official-written-references','created_at':now(),'records':records,
        'script_sha256':sha(Path(__file__)),'scope':'Separate doctrinal reference stratum; these pages are not newly downloaded speech or verified session transcripts.'}
    write(output/'manifest.json',manifest);return manifest

def download_handouts(plan_path,output,*,reserve=MIN_RESERVE,cap=128*1024**2):
    output=private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh handout output directory')
    plan=read(plan_path);source=plan['source_page'];body=verify_artifact(source['local_path'],source)
    if source.get('final_url')!='https://www.bashar.org/handouts' or source.get('status')!=200:
        raise ValueError('A verified official handout listing is required')
    links=handout_links(body.read_text())
    if {(r['source_url'],r['title']) for r in links}!={(r['source_url'],r['title']) for r in plan['records']}:
        raise ValueError('Plan is not the exact linked PDF frame')
    rows=plan['records']
    if len(rows)>100 or not rows or any(r.get('head_status')!=200 or not isinstance(r.get('declared_bytes'),int) or not 0<r['declared_bytes']<=4*1024**2 for r in rows):
        raise ValueError('Each planned PDF needs a bounded observed size')
    total=sum(r['declared_bytes'] for r in rows)
    if total>cap or shutil.disk_usage(output.parent).free<reserve+total+64*1024**2:
        raise ValueError('Declared PDF corpus and extraction reserve do not fit')
    output.mkdir(parents=True,mode=0o700);lock=threading.Lock();outcomes=[]
    def fetch(row):
        ident=hashlib.sha256(row['source_url'].encode()).hexdigest()[:16]
        folder=output/ident;folder.mkdir();path=folder/'source.pdf';part=folder/'source.pdf.partial'
        result=dict(row,source_id='bashar:handout:'+ident,retrieved_at=now(),status='failed')
        try:
            with urlopen(Request(row['source_url'],headers={'User-Agent':'Channels-ET-research-source-inventory/1.0'}),timeout=30) as response:
                if response.status!=200 or urlsplit(response.url).scheme!='https':raise ValueError('Expected complete HTTPS PDF response')
                result.update(http_status=response.status,content_type=response.headers.get('Content-Type'))
                written=0
                with part.open('xb') as stream:
                    while block:=response.read(64*1024):
                        written+=len(block)
                        if written>row['declared_bytes'] or shutil.disk_usage(output).free<reserve+len(block):raise ValueError('Response size/reserve changed')
                        stream.write(block)
            if written!=row['declared_bytes'] or not part.read_bytes().startswith(b'%PDF-'):raise ValueError('Not the complete declared PDF')
            info=subprocess.run(['pdfinfo',str(part)],check=True,capture_output=True,text=True,timeout=30).stdout
            match=re.search(r'^Pages:\s+(\d+)',info,re.M)
            if not match or not 1<=int(match.group(1))<=50:raise ValueError('PDF page count outside extraction bound')
            part.rename(path);result.update(status='downloaded',path=str(path),bytes=written,sha256=sha(path),pages=int(match.group(1)))
        except Exception as exc:result.update(error_type=type(exc).__name__,error=str(exc)[:180])
        with lock:outcomes.append(result);write(output/'download-progress.json',{'records':outcomes})
        return result
    with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(fetch,rows))
    records=[]
    for row in outcomes:
        if row['status']!='downloaded':continue
        pdf=Path(row['path']);folder=pdf.parent;native=folder/'native-text.txt'
        subprocess.run(['pdftotext','-layout',str(pdf),str(native)],check=True,timeout=45)
        text=native.read_text();extraction='pdftotext_layout';ocr_pages=0
        if len(text.split())<30:
            extracted=[]
            with tempfile.TemporaryDirectory(prefix='handout-ocr-',dir=output) as tmp:
                for number in range(1,row['pages']+1):
                    prefix=Path(tmp)/('page-'+str(number))
                    subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-r','160','-singlefile','-png',str(pdf),str(prefix)],check=True,capture_output=True,timeout=90)
                    image=prefix.with_suffix('.png')
                    import os
                    result=subprocess.run(['tesseract',str(image),'stdout','-l','eng','--psm','3'],env=dict(os.environ,OMP_THREAD_LIMIT='1'),check=True,capture_output=True,text=True,timeout=120)
                    extracted.append(result.stdout);image.unlink();ocr_pages+=1
            text='\n\f\n'.join(extracted);extraction='tesseract_eng_psm3_160dpi'
        extracted_path=folder/'extracted-text.txt';extracted_path.write_text(text)
        normalized=folder/'normalized.json';sid=row['source_id']
        write(normalized,{'source_id':sid,'text':text,'turns':[{'turn_id':sid+':text-layer','role':'unknown','text':text}],
            'extraction':extraction,'scope':'Text extraction does not preserve graphical/diagram relationships; OCR may be inaccurate.'})
        row.update(extraction=extraction,ocr_pages=ocr_pages,words=len(text.split()),status='completed_reference')
        write(folder/'receipt.json',row)
        records.append({'source_id':sid,'corpus':'bashar','session_id':sid,'session_id_basis':'Official session handout; no complete recording equivalence',
            'duplicate_family_id':'official-pdf:'+row['sha256'],'duplicate_family_basis':'exact_pdf_bytes_only','edition_id':row['sha256'],
            'source_kind':'authored_reference','source_format':'official_session_handout','title':row['title'],'publisher':'Bashar Communications',
            'source_url':row['source_url'],'published_at':None,'retrieved_at':row['retrieved_at'],'language':'en',
            'speaker_attribution_status':'official_publisher_handout_not_verified_recorded_voice','original_session_identity':'unresolved',
            'collection_status':'retrieved','coverage_status':'partial','coverage_scope':'Entire PDF retained; text-only extraction omits visual relationships',
            'text_artifact':artifact(normalized,'normalized_text'),'evidence':[artifact(pdf,'source_pdf'),artifact(body,'source_listing'),
                artifact(plan_path,'source_size_plan'),artifact(native,'native_pdf_text'),artifact(extracted_path,'extracted_text'),artifact(folder/'receipt.json','reference_receipt')],
            'text_extraction_method':extraction,'pdf_pages':row['pages'],'ocr_pages':ocr_pages,'human_reviewed':False,
            'rights_and_access_basis':'Explicit official public handout download link. Publisher copyright retained; private research copy, not full-text republication or training license.'})
    manifest={'schema_version':1,'kind':'bashar-official-handout-references','created_at':now(),'records':records,
        'source_frame_count':len(rows),'completed_pdf_count':len(records),'downloaded_bytes':sum(r.get('bytes',0) for r in outcomes if r.get('path')),
        'outcomes':outcomes,'script_sha256':sha(Path(__file__)),'new_audio_downloads':0,
        'scope':'Official written/diagram references, not speech transcripts; graphical meaning and OCR accuracy unverified.'}
    write(output/'manifest.json',manifest);return manifest

def validate_vimeo_pilot(info,profile,oembed):
    """Require three agreeing public publisher records; metadata is not speech."""
    vid=str(info.get('id',''))
    if vid!='392834325':raise ValueError('This bounded pilot is reviewed only for the Mind Body Meditation excerpt')
    if not vid.isdecimal() or vid not in {str(x.get('id')) for x in profile.get('entries',[])}:
        raise ValueError('Pilot is not in the retained publisher profile')
    if info.get('uploader_id')!='basharcommunications' or oembed.get('author_url')!='https://vimeo.com/basharcommunications':
        raise ValueError('Official publisher identity does not agree')
    duration=info.get('duration')
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<300:
        raise ValueError('Pilot does not meet the five-minute minimum')
    if oembed.get('video_id')!=int(vid) or abs(oembed.get('duration',0)-duration)>1:
        raise ValueError('Player and oEmbed editions do not agree')
    if f'https://player.vimeo.com/video/{vid}?' not in oembed.get('html',''):
        raise ValueError('Public oEmbed does not link the inspected player')
    fmt=next((r for r in info.get('formats',[]) if r.get('vcodec')=='none' and r.get('format_id')=='hls-fastly_skyfire-audio-high-Original'),None)
    if not fmt:raise ValueError('Expected original audio-only format is unavailable')
    return vid,fmt['format_id']

def vimeo_pilot(info_path,profile_path,oembed_path,output,limit=100*1024**2):
    """Download one public publisher excerpt with verified TLS and bounded bytes.

    Inputs are retained yt-dlp player/profile metadata and Vimeo's public oEmbed.
    This does not obtain paid VOD or bypass an authentication requirement.
    """
    if not isinstance(limit,int) or isinstance(limit,bool) or not 0<limit<=100*1024**2:raise ValueError('Invalid pilot byte budget')
    paths=[private_path(p) for p in (info_path,profile_path,oembed_path)]
    info,profile,oembed=map(read,paths);vid,fmt=validate_vimeo_pilot(info,profile,oembed)
    output=private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh pilot directory')
    output.mkdir(parents=True,mode=0o700)
    if shutil.disk_usage(output).free<MIN_RESERVE+limit:raise ValueError('Pilot disk reserve is insufficient')
    import yt_dlp
    from yt_dlp.version import __version__
    def progress(row):
        retained=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        if row.get('downloaded_bytes',0)>limit or retained>limit:raise RuntimeError('Pilot byte budget exceeded')
        if shutil.disk_usage(output).free<MIN_RESERVE:raise RuntimeError('Pilot disk reserve reached')
    options={'format':fmt,'outtmpl':str(output/'audio.%(ext)s'),'compat_opts':{'no-certifi'},
        'hls_prefer_native':True,'skip_unavailable_fragments':False,'concurrent_fragment_downloads':1,'retries':0,'fragment_retries':0,
        'extractor_retries':0,'socket_timeout':20,'max_filesize':limit,'progress_hooks':[progress],
        'overwrites':False,'noprogress':True,'quiet':True,'no_warnings':False}
    started=now()
    with yt_dlp.YoutubeDL(options) as ydl:ydl.download_with_info_file(str(paths[0]))
    files=[p for p in output.iterdir() if p.name.startswith('audio.') and p.suffix in ('.mp4','.m4a')]
    if len(files)!=1:raise ValueError('Pilot output did not complete as one audio file')
    audio=files[0];duration=probe_audio(audio)
    if audio.stat().st_size>limit or abs(duration-info['duration'])>3:raise ValueError('Pilot output byte/duration check failed')
    receipt={'schema_version':1,'source_id':'vimeo:'+vid,'status':'completed','source_kind':'official_publisher_audio_excerpt',
        'source_format':'official_channeling_qa_excerpt','publisher':'Bashar Communications','title':info['title'],
        'source_url':'https://vimeo.com/'+vid,'player_url':'https://player.vimeo.com/video/'+vid,
        'started_at':started,'completed_at':now(),'audio':artifact(audio,'source_audio'),'duration_seconds':duration,
        'published_at':None,'source_date_status':'Unresolved; description copyright is not a publication date',
        'speaker_attribution_status':'Publisher identifies Bashar and Alan Steinfeld; no independent identity verification or diarization',
        'recording_scope':'Public 422-second Q&A excerpt; NOT the advertised complete Mind Body Meditation session',
        'captions_available':bool(info.get('subtitles')),'automatic_captions_available':bool(info.get('automatic_captions')),
        'format_id':fmt,'tool':{'name':'yt-dlp','version':__version__,'script_sha256':sha(Path(__file__))},
        'configuration':{'tls_verification':True,'certificate_store':'system_CA_no_certifi','proxy_inherited':True,
            'authentication':'none','concurrent_fragments':1,'max_bytes':limit,'disk_reserve_bytes':MIN_RESERVE},
        'evidence':[artifact(p,role) for p,role in zip(paths,('public_player_metadata','public_profile_inventory','public_oembed'))],
        'rights_and_access_basis':'Public original-publisher preview/player; private research copy, not full-session access or republication license',
        'source_coverage_status':'partial_original_session','transcription_status':'not_started'}
    write(output/'receipt.json',receipt);return receipt

def parse_vtt(raw,duration):
    """Retain ordered cue text/timing; do not infer speakers or human authorship."""
    text=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    if not text.startswith('WEBVTT'):raise ValueError('Expected a WebVTT caption document')
    def seconds(value):
        parts=value.split(':')
        if len(parts) not in (2,3):raise ValueError('Invalid WebVTT timestamp')
        nums=list(map(float,parts));total=nums[-1]+60*nums[-2]+(3600*nums[0] if len(nums)==3 else 0)
        if not math.isfinite(total):raise ValueError('Nonfinite caption time')
        return total
    cues=[];previous=-1.
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines()
        if not lines or lines[0].startswith(('WEBVTT','NOTE','STYLE','REGION')):continue
        timing=next((i for i,line in enumerate(lines[:2]) if '-->' in line),None)
        if timing is None:raise ValueError('Unknown WebVTT block')
        match=re.fullmatch(r'(\d{2,}:)?\d{2}:\d{2}\.\d{3}\s+-->\s+((?:\d{2,}:)?\d{2}:\d{2}\.\d{3})(?:\s+.*)?',lines[timing])
        if not match:raise ValueError('Invalid caption timing line')
        left,right=lines[timing].split('-->',1);start=seconds(left.strip());end=seconds(right.strip().split()[0])
        if start<0 or start<previous or end<start or end>duration+2:raise ValueError('Caption time outside the public excerpt')
        body=html_module.unescape(re.sub(r'<[^>]*>','','\n'.join(lines[timing+1:]))).strip()
        if body:cues.append({'start_seconds':start,'end_seconds':end,'text':body})
        previous=start
    if not cues:raise ValueError('No caption text retained')
    return cues

def vimeo_captions(census_path,output):
    census_path=private_path(census_path);census=read(census_path);output=private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh caption directory')
    rows=[r for r in census['records'] if r.get('status')=='retrieved' and 'en-x-autogen' in r.get('captions_languages',[])]
    output.mkdir(parents=True,mode=0o700);records=[]
    for row in rows:
        bound=row['metadata_artifact'];meta=verify_artifact(bound['path'],bound);info=read(meta);vid=row['video_id']
        if str(info.get('id'))!=vid or info.get('uploader_id')!='basharcommunications' or info['duration']<300:
            raise ValueError('Caption source identity or duration changed')
        choices=info.get('subtitles',{}).get('en-x-autogen',[])
        selected=next((x for x in choices if x.get('ext')=='vtt' and x.get('protocol')!='m3u8_native' and urlsplit(x.get('url','')).hostname=='captions.vimeo.com'),None)
        if not selected or urlsplit(selected['url']).scheme!='https':raise ValueError('No direct official caption track')
        with urlopen(Request(selected['url'],headers={'User-Agent':'Mozilla/5.0 source-research/1.0'}),timeout=25) as response:
            if response.status!=200:raise ValueError('Caption request did not succeed')
            raw=response.read(2*1024**2+1);final_url=response.url
        if len(raw)>2*1024**2:raise ValueError('Caption exceeds 2MiB budget')
        folder=output/vid;folder.mkdir(mode=0o700);vtt=folder/'source.en-x-autogen.vtt';vtt.write_bytes(raw)
        cues=parse_vtt(raw,row['duration_seconds']);sid='vimeo:'+vid+':captions:en-x-autogen';text='\n'.join(x['text'] for x in cues)
        normalized=folder/'normalized.json';write(normalized,{'source_id':sid,'text':text,'turns':[{'turn_id':sid+':cue:'+str(i+1),'role':'unknown',**x} for i,x in enumerate(cues)],
            'normalization':'Ordered WebVTT cue text; markup removed and HTML entities decoded; no deduplication, speaker attribution or correction.'})
        receipt=folder/'receipt.json';write(receipt,{'source_id':sid,'retrieved_at':now(),'source_url':row['source_url'],'caption_url':selected['url'],'final_url':final_url,
            'http_status':200,'caption_artifact':artifact(vtt,'source_caption'),'player_metadata':artifact(meta,'source_player_metadata'),
            'caption_language_label':'en-x-autogen','caption_origin':'Vimeo automatically generated label; unknown model and accuracy',
            'script_sha256':sha(Path(__file__)),'cues':len(cues),'words':len(text.split()),'duration_seconds':row['duration_seconds']})
        records.append({'source_id':sid,'corpus':'bashar','session_id':'vimeo:'+vid,'session_id_basis':'Public excerpt publication, not historical full-session identity',
            'duplicate_family_id':'vimeo-publication:'+vid,'duplicate_family_basis':'same_publication_only; cross-upload overlap unresolved',
            'original_session_identity':'unresolved','edition_id':sha(vtt),'source_kind':'machine_asr','source_format':'official_session_excerpt_platform_asr',
            'title':row['title'],'publisher':'Bashar Communications','source_url':row['source_url'],'published_at':None,'language':'en',
            'language_basis':'Platform en-x-autogen caption label; not a human audit of spoken language',
            'speaker_attribution_status':'Unknown mixed speaker roles; publisher context does not independently verify voices',
            'collection_status':'retrieved','coverage_status':'partial','coverage_scope':'Available auto-caption track of public excerpt; no full historical-session or recognition-completeness claim',
            'text_artifact':artifact(normalized,'normalized_text'),'evidence':[artifact(vtt,'source_caption'),artifact(meta,'player_metadata'),artifact(receipt,'caption_acquisition_receipt'),artifact(census_path,'source_frame')],
            'caption_cues':len(cues),'asr_words':len(text.split()),'asr_model':'Unknown platform model; no local inference performed',
            'human_reviewed':False,'youtube_video_edition_verified':False,'audio_downloaded':False,
            'rights_and_access_basis':'Public original-publisher player caption track; private research copy, no full-text redistribution license'})
    manifest={'schema_version':1,'kind':'bashar-official-public-excerpt-platform-captions','records':records,'created_at':now(),
        'script_sha256':sha(Path(__file__)),'summary':{'recordings_with_captions':len(records),'caption_cues':sum(x['caption_cues'] for x in records),
            'asr_words':sum(x['asr_words'] for x in records),'new_audio_downloads':0,'new_local_ASR_runs':0}}
    write(output/'manifest.json',manifest);return manifest


def validate_vimeo_frame(census,plan,budget_bytes):
    """Check the finite ID set and byte caps before any directories or network."""
    frame={};planned={}
    for row in census['records']:
        vid=row.get('video_id');duration=row.get('duration_seconds')
        if not isinstance(vid,str) or not re.fullmatch(r'[0-9]{1,16}',vid) or vid in frame:
            raise ValueError('Publisher frame requires unique numeric Vimeo IDs')
        if row.get('status')!='retrieved' or isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<300:
            raise ValueError('Publisher frame contains unavailable or short metadata')
        frame[vid]=row
    for row in plan['records']:
        vid=row.get('video_id');cap=row.get('planning_max_bytes')
        if vid not in frame or vid in planned:raise ValueError('Plan IDs must equal the inspected frame')
        if isinstance(cap,bool) or not isinstance(cap,int) or cap<=0 or cap>budget_bytes:
            raise ValueError('Each source needs a positive bounded byte cap')
        planned[vid]=row
    if not frame or set(frame)!=set(planned):raise ValueError('Plan IDs must equal the inspected frame')
    if sum(row['planning_max_bytes'] for row in planned.values())>budget_bytes:
        raise ValueError('Frame planning caps exceed authorized total budget')
    return frame,planned

def collect_vimeo_frame(census_path,plan_path,output,reuse_paths,*,min_free_bytes,budget_bytes):
    """Acquire the exact inspected public-player frame, never paid sessions.

    Two media workers, original publisher audio encodings, zero retries. A separate
    caller runs one local ASR worker; this function never installs models.
    """
    import time
    for n in (min_free_bytes,budget_bytes):
        if isinstance(n,bool) or not isinstance(n,int) or n<=0:raise ValueError('Positive byte bounds required')
    census_path=private_path(census_path);plan_path=private_path(plan_path)
    census=read(census_path);plan=read(plan_path);output=private_path(output,False)
    frame,planned=validate_vimeo_frame(census,plan,budget_bytes)
    import yt_dlp
    from yt_dlp.version import __version__
    reused={}
    for path in reuse_paths:
        path=private_path(path);receipt=read(path);vid=receipt['source_id'].removeprefix('vimeo:')
        if vid not in frame or vid in reused or receipt.get('status')!='completed':raise ValueError('Invalid reused edition')
        verify_artifact(receipt['audio']['path'],receipt['audio'])
        if abs(probe_audio(receipt['audio']['path'])-frame[vid]['duration_seconds'])>3:raise ValueError('Reused media duration differs')
        reused[vid]={'video_id':vid,'status':'completed','reused':True,'receipt':artifact(path,'acquisition_receipt'),
            'audio':receipt['audio'],'duration_seconds':receipt['duration_seconds'],'source_format':frame[vid]['source_format']}
    if output.exists():raise ValueError('Choose a fresh frame acquisition directory')
    output.mkdir(parents=True,mode=0o700)
    lock=threading.Lock();stop=threading.Event();charged={vid:r['audio']['bytes'] for vid,r in reused.items()};results=dict(reused)
    execution={'started_at':now(),'script_sha256':sha(Path(__file__)),'tool_version':__version__,'workers':2,
        'min_free_bytes':min_free_bytes,'budget_bytes':budget_bytes,'source_frame':artifact(census_path,'source_frame'),
        'size_plan':artifact(plan_path,'size_plan'),'reuse_receipts':[artifact(p,'reused_acquisition') for p in reuse_paths]}
    write(output/'execution.json',execution)
    def save_progress():
        write(output/'progress.json',{'completed':len(results),'frame_count':len(frame),
            'statuses':dict(Counter(r['status'] for r in results.values())),
            'retained_audio_bytes':sum(r.get('audio',{}).get('bytes',0) for r in results.values()),
            'records':list(results.values()),'updated_at':now()})
    save_progress()
    def job(vid):
        if stop.is_set():return {'video_id':vid,'status':'not_requested_after_stop'}
        row=frame[vid];selected=planned[vid];folder=output/vid;folder.mkdir(mode=0o700)
        log=folder/'download.log';meta=verify_artifact(row['metadata_artifact']['path'],row['metadata_artifact']);info=read(meta)
        if info.get('uploader_id')!='basharcommunications' or str(info.get('id'))!=vid or info['duration']<300 or abs(info['duration']-row['duration_seconds'])>1:
            return {'video_id':vid,'status':'source_metadata_rejected'}
        fmt=next((f for f in info.get('formats',[]) if f.get('format_id')==selected['format_id'] and f.get('vcodec')=='none'),None)
        if not fmt:return {'video_id':vid,'status':'selected_audio_format_missing'}
        cap=selected['planning_max_bytes']
        if isinstance(cap,bool) or not isinstance(cap,int) or cap<=0 or cap>budget_bytes:return {'video_id':vid,'status':'invalid_source_cap'}
        def guard(progress):
            actual=sum(p.stat().st_size for p in folder.iterdir() if p.is_file() and p.name.startswith('audio.'))
            actual=max(actual,progress.get('downloaded_bytes',0))
            with lock:
                charged[vid]=max(charged.get(vid,0),actual)
                if actual>cap or sum(charged.values())>budget_bytes:
                    stop.set();raise RuntimeError('Media byte budget reached')
            if stop.is_set():raise RuntimeError('Shared collection stop set')
            if shutil.disk_usage(output).free<min_free_bytes:
                stop.set();raise RuntimeError('Shared disk reserve reached')
        class Logger:
            def debug(self,msg):pass
            def warning(self,msg):
                with log.open('a') as f:f.write(str(msg)+'\n')
            def error(self,msg):
                with log.open('a') as f:f.write(str(msg)+'\n')
                if re.search(r'HTTP Error (403|429)|CONNECT.*403|timed out|Network is unreachable|Unable to connect',str(msg),re.I):stop.set()
        try:
            if shutil.disk_usage(output).free<min_free_bytes+cap:stop.set();raise RuntimeError('Insufficient shared disk reserve')
            opts={'format':selected['format_id'],'outtmpl':str(folder/'audio.%(ext)s'),'compat_opts':{'no-certifi'},
                'hls_prefer_native':True,'skip_unavailable_fragments':False,'concurrent_fragment_downloads':1,'retries':0,'fragment_retries':0,'extractor_retries':0,
                'socket_timeout':20,'max_filesize':cap,'progress_hooks':[guard],'overwrites':False,'noprogress':True,'quiet':True,'logger':Logger()}
            began=now()
            with yt_dlp.YoutubeDL(opts) as ydl:ydl.download_with_info_file(str(meta))
            audio=folder/'audio.mp4';duration=probe_audio(audio)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','json',str(audio)]))
            if any(x['codec_type']!='audio' for x in probe['streams']) or abs(duration-info['duration'])>3 or audio.stat().st_size>cap:
                raise ValueError('Audio-only full-excerpt verification failed')
            receipt={'schema_version':1,'source_id':'vimeo:'+vid,'status':'completed','source_kind':'official_publisher_audio_excerpt',
                'source_format':row['source_format'],'title':row['title'],'publisher':'Bashar Communications','source_url':row['source_url'],
                'audio':artifact(audio,'source_audio'),'duration_seconds':duration,'published_at':None,'started_at':began,'completed_at':now(),
                'format_id':selected['format_id'],'encoding':'Lowest inspected original-language publisher audio track; no local reencoding',
                'explicit_translation_label':row['explicit_translation_label'],'source_language_status':'mixed_label' if row['explicit_translation_label'] else 'unverified',
                'configuration':{'tls_verification':True,'certificate_store':'system_CA_no_certifi','proxy_inherited':True,'authentication':'none',
                    'source_byte_cap':cap,'frame_byte_budget':budget_bytes,'min_free_bytes':min_free_bytes,'media_workers':2,'fragment_workers':1},
                'evidence':[artifact(meta,'public_player_metadata'),artifact(census_path,'source_frame'),artifact(plan_path,'size_plan')],
                'script_sha256':sha(Path(__file__)),'tool_version':__version__,
                'scope':'Complete available public excerpt/publication; original historical full-session identity and completeness unresolved'}
            write(folder/'receipt.json',receipt)
            return {'video_id':vid,'status':'completed','reused':False,'receipt':artifact(folder/'receipt.json','acquisition_receipt'),
                'audio':receipt['audio'],'duration_seconds':duration,'source_format':row['source_format']}
        except Exception as exc:
            return {'video_id':vid,'status':'failed_not_admitted','error_type':type(exc).__name__,'shared_stop':stop.is_set()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(job,vid):vid for vid in frame if vid not in reused}
        from concurrent.futures import as_completed
        for future in as_completed(futures):
            vid=futures[future]
            try:result=future.result()
            except Exception as exc:result={'video_id':vid,'status':'failed_not_admitted','error_type':type(exc).__name__}
            with lock:results[vid]=result;save_progress()
            print(json.dumps({'stage':'audio_collection','video_id':vid,'status':result['status'],'completed':len(results),'total':len(frame)}),flush=True)
    manifest={**execution,'completed_at':now(),'records':[results[vid] for vid in frame],
        'retained_audio_bytes':sum(r.get('audio',{}).get('bytes',0) for r in results.values()),
        'completed_sources':sum(r['status']=='completed' for r in results.values()),'reused_sources':len(reused),
        'scope':'Finite public Vimeo publisher frame only; audio-only encoded source editions, not full paid sessions or verified voices.'}
    write(output/'manifest.json',manifest);return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    inv=sub.add_parser('inventory');inv.add_argument('--output',type=Path,default=PRIVATE/'corpus')
    handouts=sub.add_parser('handouts');handouts.add_argument('--plan',type=Path,required=True);handouts.add_argument('--output',type=Path,required=True)
    handouts.add_argument('--reserve-bytes',type=int,default=MIN_RESERVE)
    pilot=sub.add_parser('vimeo-pilot')
    for name in ('info','profile','oembed','output'):pilot.add_argument('--'+name,type=Path,required=True)
    captions=sub.add_parser('vimeo-captions');captions.add_argument('--census',type=Path,required=True);captions.add_argument('--output',type=Path,required=True)
    bulk=sub.add_parser('vimeo-frame')
    for name in ('census','plan','output'):bulk.add_argument('--'+name,type=Path,required=True)
    bulk.add_argument('--reuse',type=Path,action='append',default=[])
    bulk.add_argument('--min-free-bytes',type=int,required=True);bulk.add_argument('--budget-bytes',type=int,required=True)
    args=p.parse_args()
    if args.command=='inventory':print(json.dumps(inventory(args.output)['summary'],indent=2))
    elif args.command=='handouts':
        result=download_handouts(args.plan,args.output,reserve=args.reserve_bytes)
        print(json.dumps({k:result[k] for k in ('source_frame_count','completed_pdf_count','downloaded_bytes','new_audio_downloads')},indent=2))
    elif args.command=='vimeo-pilot':
        result=vimeo_pilot(args.info,args.profile,args.oembed,args.output)
        print(json.dumps({k:result[k] for k in ('source_id','status','duration_seconds','audio','captions_available')},indent=2))
    elif args.command=='vimeo-captions':print(json.dumps(vimeo_captions(args.census,args.output)['summary'],indent=2))
    elif args.command=='vimeo-frame':
        result=collect_vimeo_frame(args.census,args.plan,args.output,args.reuse,min_free_bytes=args.min_free_bytes,budget_bytes=args.budget_bytes)
        print(json.dumps({k:result[k] for k in ('completed_sources','reused_sources','retained_audio_bytes')}))

if __name__=='__main__':main()
