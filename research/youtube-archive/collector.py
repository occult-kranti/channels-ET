#!/usr/bin/env python3
"""Private, resumable YouTube account enumeration and audio/caption collection.

Uses ordinary configured networking only. A failed shared CONNECT gate prevents
per-account and per-video attempts. No relay, proxy override or authentication
workaround is implemented. Completed files are admitted only after byte/media
checks, never because a download-archive entry exists.
"""
from __future__ import annotations
import argparse
import concurrent.futures
from collections import Counter,defaultdict
import contextlib
import datetime as dt
import fcntl
import hashlib
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid

VIDEO=re.compile(r'^[A-Za-z0-9_-]{11}$')
CHANNEL=re.compile(r'^UC[A-Za-z0-9_-]{22}$')
ACCOUNT=re.compile(r'^[A-Za-z0-9_-]{1,120}$')
RESERVED_ROUTES={'watch','playlist','playlists','videos','shorts','streams','live','embed','clip','clips',
    'feed','results','redirect','channel','c','user','account','gaming','premium','music','hashtag',
    'search','api','about','t','s','reporthistory','upload','logout','signin','youtubei','oembed',
    'attribution_link','get_video_info','timedtext','subscriptions','history','settings'}
TABS=('videos','shorts','streams')
FLOOR=2*1024**3
GATEWAY=re.compile(r'CONNECT tunnel failed.*403|Tunnel connection failed:\s*403|proxy.?tunnel.{0,40}(denied|403)',re.I)
POLICY={'item_count_cap':None,'date_cap':None,'bashar_minimum_seconds':300,
    'other_minimum_seconds':0,'shorts_included_for_non_bashar':True,
    'media_preference':'original bestaudio; combined fallback only if audio-only is absent',
    'live_policy':'currently live/upcoming deferred; completed streams eligible',
    'listing_claim':'extractor_completed_accessible_tab is not an independently verified total-upload census',
    'storage':'full media/captions/transcripts private; public status contains metadata only'}


def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def require(value,message):
    if not value:raise ValueError(message)
def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def ref(path):
    p=Path(path);return {'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
def read(path):return json.loads(Path(path).read_text())
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(encoded(value)+'\n');os.chmod(temp,0o600);os.replace(temp,path)
def private_root(path):
    path=Path(path).expanduser().absolute()
    for part in (path,*path.parents):
        require(not part.is_symlink(),'Private archive paths cannot traverse symlinks')
        marker=part/'.git'
        if marker.exists():require(marker.is_dir() and not any(marker.iterdir()),'Raw archive must be outside Git checkouts')
    path.mkdir(parents=True,exist_ok=True);return path
def runtime():
    versions={}
    for name in ('yt-dlp','yt-dlp-ejs'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    for name in ('node','ffmpeg','ffprobe'):
        command=shutil.which(name)
        versions[name]=subprocess.run([command,'--version' if name=='node' else '-version'],capture_output=True,text=True,timeout=10).stdout.splitlines()[0] if command else None
    return {'python':sys.version,'packages_and_tools':versions,'collector_sha256':sha(__file__),'js_runtimes':{'node':{}},'remote_components':[]}


def classify_error(message):
    text=str(message)
    if GATEWAY.search(text):return 'gateway_connect_denied',True
    if re.search(r'HTTP Error 429|Too Many Requests',text,re.I):return 'origin_rate_limit',True
    if re.search(r'sign in to confirm.*not a bot|captcha|bot detection',text,re.I):return 'origin_bot_challenge',True
    if re.search(r'private video|video unavailable|has been removed|members.only|not available in your country|copyright|age.restricted',text,re.I):return 'source_restricted_or_unavailable',False
    if re.search(r'requested tab is not available|does not have a .* tab|no uploads',text,re.I):return 'tab_absent_or_unavailable',False
    if 'resource_floor' in text:return 'resource_floor',True
    if 'shared_stop' in text:return 'held_after_shared_failure',True
    if re.search(r'HTTP Error 403|Forbidden',text,re.I):return 'origin_or_media_access_denied',False
    return 'extractor_or_network_failure',False


def gate_from_receipt(path):
    r=read(path);c=r.get('curl',{});connect=int(c.get('http_connect',0) or 0);origin=int(c.get('http_code',0) or 0)
    require(urllib.parse.urlsplit(r.get('url','')).hostname in ('youtube.com','www.youtube.com'),'Gate is not a YouTube route observation')
    for binding in r.get('files',[]):
        name=Path(binding['file']);require(len(name.parts)==1 and not name.is_absolute(),'Unsafe route receipt artifact')
        artifact=Path(path).parent/name;require(artifact.stat().st_size==binding['bytes'] and sha(artifact)==binding['sha256'],'Route evidence bytes differ')
    error=r.get('stderr','');status='passed' if r.get('returncode')==0 and 200<=origin<400 else 'failed'
    if connect==403 and origin==0 or GATEWAY.search(error):status='gateway_connect_denied'
    return {'status':status,'scope':'shared_configured_route_before_collection','http_connect':connect,
        'origin_http_status':origin,'checked_at':r.get('at'),'probe_sha256':sha(path),
        'source_url':r.get('url'),'origin_reached':origin>0,'proxy_override':False,
        'cause_scope':'Pre-origin CONNECT denial; not evidence of a YouTube bot challenge.' if status=='gateway_connect_denied' else 'Transport probe only; successful media access is not implied.'}


def probe(root,url):
    require(url.startswith('https://www.youtube.com/'),'Probe must use ordinary YouTube HTTPS URL')
    folder=root/'probes'/uuid.uuid4().hex;folder.mkdir(parents=True)
    command=['curl','--silent','--show-error','--connect-timeout','10','--max-time','25','--retry','0',
        '--max-filesize','2097152','--dump-header',str(folder/'headers'),'--output',str(folder/'body'),
        '--write-out','%{json}',url]
    started=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,timeout=30)
    try:details=json.loads(p.stdout)
    except ValueError:details={}
    value={'at':now(),'url':url,'command':command,'returncode':p.returncode,'curl':details,
        'stderr':p.stderr,'seconds':time.monotonic()-started,'files':[ref(x) for x in (folder/'headers',folder/'body') if x.exists()]}
    save(folder/'receipt.json',value);return folder/'receipt.json'


SCHEMA='''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value_json TEXT);
CREATE TABLE IF NOT EXISTS accounts(account_id TEXT PRIMARY KEY,channel_id TEXT,display_name TEXT,inclusion_status TEXT,minimum_seconds REAL,input_json TEXT);
CREATE TABLE IF NOT EXISTS tabs(account_id TEXT,tab TEXT,status TEXT,enumeration_kind TEXT,returned_unique_ids INTEGER DEFAULT0,unresolved_slots INTEGER DEFAULT0,error_class TEXT,receipt_path TEXT,PRIMARY KEY(account_id,tab));
CREATE TABLE IF NOT EXISTS videos(video_id TEXT PRIMARY KEY,status TEXT DEFAULT'pending',metadata_status TEXT DEFAULT'not_attempted',owner_channel_id TEXT,duration_seconds REAL,minimum_seconds REAL DEFAULT0,eligibility_status TEXT DEFAULT'pending_fresh_metadata',media_status TEXT DEFAULT'not_attempted',caption_status TEXT DEFAULT'not_attempted',asr_status TEXT DEFAULT'not_queued',analysis_status TEXT DEFAULT'not_analyzed',last_run TEXT,last_error TEXT,metadata_path TEXT,scope_status TEXT DEFAULT'indexed_or_accepted');
CREATE TABLE IF NOT EXISTS membership(account_id TEXT,tab TEXT,video_id TEXT,origin TEXT,PRIMARY KEY(account_id,tab,video_id));
CREATE TABLE IF NOT EXISTS attempts(attempt_id TEXT PRIMARY KEY,run_id TEXT,video_id TEXT,started_at TEXT,finished_at TEXT,status TEXT,error_class TEXT,receipt_path TEXT);
CREATE TABLE IF NOT EXISTS artifacts(artifact_id TEXT PRIMARY KEY,video_id TEXT,edition_id TEXT,kind TEXT,path TEXT,bytes INTEGER,sha256 TEXT,details_json TEXT);
CREATE TABLE IF NOT EXISTS asr_queue(video_id TEXT,edition_id TEXT,audio_artifact_id TEXT,status TEXT,reason TEXT,PRIMARY KEY(video_id,edition_id));
'''.replace('DEFAULT0','DEFAULT 0')


class Store:
    def __init__(self,root):
        self.root=private_root(root);self.path=self.root/'archive.sqlite'
        with self.connect() as c:c.executescript(SCHEMA)
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30);c.row_factory=sqlite3.Row;return c
    def set(self,key,value):
        with self.connect() as c:c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,encoded(value)))
    def get(self,key,default=None):
        with self.connect() as c:r=c.execute('SELECT value_json FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default
    def initialize(self,path):
        source=read(path);rows=source['accounts'];seen=set()
        with self.connect() as c:
            for account in rows:
                aid=account['account_id'];require(isinstance(aid,str) and ACCOUNT.fullmatch(aid),'Unsafe account ID');require(aid not in seen,'Repeated account ID');seen.add(aid)
                cid=account.get('channel_id');require(cid is None or CHANNEL.fullmatch(cid),'Invalid channel ID')
                included=account.get('inclusion_status','unresolved')
                minimum=account.get('duration_policy',{}).get('minimum_seconds',0)
                require(not isinstance(minimum,bool) and minimum in (0,300),'Only the declared Bashar 300-second policy is supported')
                if any('jamiebutlermedium' in str(x).casefold() for x in account.get('handles',[])):require(included=='excluded','Jamie Butler is explicitly excluded by user')
                old=c.execute('SELECT channel_id,input_json FROM accounts WHERE account_id=?',(aid,)).fetchone()
                if old and old['channel_id'] and cid:require(old['channel_id']==cid,'Conflicting exact account identity')
                c.execute('INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?)',(aid,cid or (old['channel_id'] if old else None),account.get('display_name',aid),included,minimum,encoded(account)))
                for tab in TABS:c.execute("INSERT OR IGNORE INTO tabs(account_id,tab,status,enumeration_kind) VALUES (?,?,'not_attempted','unknown')",(aid,tab))
                observed=account.get('observed_video_ids',[x['video_id'] for x in account.get('observed_videos',[])])
                for vid in observed:
                    require(VIDEO.fullmatch(vid),'Invalid historical video ID')
                    c.execute('INSERT OR IGNORE INTO videos(video_id,minimum_seconds) VALUES (?,?)',(vid,minimum))
                    c.execute('UPDATE videos SET minimum_seconds=MAX(minimum_seconds,?) WHERE video_id=?',(minimum,vid))
                    c.execute('INSERT OR IGNORE INTO membership VALUES (?,?,?,?)',(aid,'historical',vid,'metadata_inventory_only'))
            for item in source.get('videos',[]):
                vid=item['video_id'];require(VIDEO.fullmatch(vid),'Invalid indexed video ID');decision=item.get('policy_decision',{})
                minimum=decision.get('minimum_seconds',0);require(not isinstance(minimum,bool) and minimum in (0,300),'Invalid per-video duration policy')
                c.execute('INSERT OR IGNORE INTO videos(video_id,minimum_seconds) VALUES (?,?)',(vid,minimum))
                scope='indexed_or_accepted' if decision.get('status') in ('eligible','duration_probe_required') else'held_historical_duration' if decision.get('status')=='excluded_duration' else'pending_relevance_review'
                c.execute('UPDATE videos SET minimum_seconds=MAX(minimum_seconds,?),scope_status=? WHERE video_id=?',(minimum,scope,vid))
        self.set('inventory_binding',ref(path));self.set('policy',POLICY)
    def claim(self,run_id):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT v.* FROM videos v WHERE status IN ('pending','retryable','held_shared_route','held_resource','interrupted') AND scope_status='indexed_or_accepted' AND COALESCE(last_run,'')!=? AND EXISTS(SELECT1 FROM membership m JOIN accounts a USING(account_id) WHERE m.video_id=v.video_id AND a.inclusion_status!='excluded') ORDER BY video_id LIMIT1".replace('SELECT1','SELECT 1').replace('LIMIT1','LIMIT 1'),(run_id,)).fetchone()
            if row:c.execute("UPDATE videos SET status='running',last_run=? WHERE video_id=?",(run_id,row['video_id']))
            return dict(row) if row else None
    def add_artifact(self,vid,edition,kind,path,details):
        artifact={'artifact_id':'artifact:'+uuid.uuid4().hex,'video_id':vid,'edition_id':edition,'kind':kind,
            'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'details':details}
        with self.connect() as c:c.execute('INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)',tuple(artifact[k] for k in ('artifact_id','video_id','edition_id','kind','path','bytes','sha256'))+(encoded(details),))
        return artifact
    def reconcile(self):
        bad=[]
        with self.connect() as c:
            for a in c.execute('SELECT * FROM artifacts').fetchall():
                p=Path(a['path'])
                if not p.is_file() or p.is_symlink() or p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:
                    bad.append(a['artifact_id']);c.execute("UPDATE videos SET status='artifact_review_required',last_error='retained_artifact_changed' WHERE video_id=?",(a['video_id'],))
        return bad


class Budget:
    def __init__(self,root,floor=FLOOR):self.root=Path(root);self.floor=floor;self.reserved=0;self.lock=threading.Lock()
    def acquire(self,amount):
        with self.lock:
            if shutil.disk_usage(self.root).free-self.reserved-amount<self.floor+8*1024**2:raise RuntimeError('resource_floor: insufficient reserved headroom')
            self.reserved+=amount
    def release(self,amount):
        with self.lock:self.reserved-=amount
    def check(self):
        if shutil.disk_usage(self.root).free<self.floor+8*1024**2:raise RuntimeError('resource_floor: shared low disk guard')


class CaptureLogger:
    def __init__(self):self.rows=[]
    def debug(self,value):self.rows.append({'level':'debug','message':str(value)})
    def warning(self,value):self.rows.append({'level':'warning','message':str(value)})
    def error(self,value):self.rows.append({'level':'error','message':str(value)})


def ydl_options(logger):
    return {'logger':logger,'quiet':True,'no_warnings':False,'cachedir':False,'retries':0,'fragment_retries':0,
        'extractor_retries':0,'socket_timeout':25,'js_runtimes':{'node':{}},'remote_components':set(),
        'ignoreerrors':False,'noplaylist':True,'format':'bestaudio/best','overwrites':False,'continuedl':True}


def choose_caption(info):
    original=(info.get('language') or '').lower();candidates=[]
    for generated,key in ((False,'subtitles'),(True,'automatic_captions')):
        for language,tracks in (info.get(key) or {}).items():
            tracks=[t for t in tracks if not urllib.parse.parse_qs(urllib.parse.urlsplit(t.get('url','')).query).get('tlang')]
            if not tracks or language=='live_chat':continue
            preference=0 if original and language.lower()==original else 1 if language.lower().startswith('en') else 2
            candidates.append((generated,preference,language,tracks))
    if not candidates:return None
    generated,_,language,tracks=min(candidates,key=lambda x:(x[0],x[1],x[2]))
    return {'language':language,'is_generated':generated,'tracks':tracks,'translation_requested':False}


def restrict_caption_tracks(info,selected):
    out=dict(info);out.pop('requested_subtitles',None);out['subtitles']={};out['automatic_captions']={}
    if selected:
        key='automatic_captions' if selected['is_generated'] else'subtitles'
        out[key]={selected['language']:selected['tracks']}
    return out


def duration_floor(row,info):
    minimum=row['minimum_seconds'];basis=['source_inventory_policy']
    explicit=bool(re.search(r'(?<!\w)bashar(?!\w)',str(info.get('title','')),re.I))
    explicit=explicit or bool(re.search(r'channel(?:ed|led|ing|ling)\s+(?:by|through)\s+darryl\s+anka',str(info.get('description','')),re.I))
    if explicit:minimum=max(300,minimum);basis.append('fresh_title_or_explicit_Darryl_Anka_attribution_cue_not_verified_speaker_identity')
    return minimum,basis


def supported_account_route(url):
    """Normalize an inventory-listed account route, never a watch/search URL."""
    try:parsed=urllib.parse.urlsplit(url)
    except ValueError:return None
    if parsed.scheme not in ('http','https') or parsed.hostname not in ('www.youtube.com','youtube.com') or parsed.username or parsed.password:return None
    path=parsed.path.rstrip('/')
    named=bool(re.fullmatch(r'/(?:c/|user/)[A-Za-z0-9_.-]{1,100}',path))
    handle=bool(re.fullmatch(r'/@[A-Za-z0-9_.-]{1,100}',path))
    channel=path.startswith('/channel/') and bool(CHANNEL.fullmatch(path[len('/channel/'):]))
    legacy=bool(re.fullmatch(r'/[A-Za-z0-9_-]{1,100}',path)) and path[1:].casefold() not in RESERVED_ROUTES
    if named or handle or channel or legacy:return 'https://www.youtube.com'+path
    return None


def caption_segments(path):
    if path.suffix=='.json3':
        obj=read(path);rows=[]
        for event in obj.get('events',[]):
            text=''.join(s.get('utf8','') for s in event.get('segs',[])).strip()
            if text:rows.append({'start':event.get('tStartMs',0)/1000,'duration':event.get('dDurationMs',0)/1000,'text':text})
        return rows
    raw=path.read_text(encoding='utf-8-sig');require(raw.startswith('WEBVTT'),'Unrecognized offered caption syntax')
    rows=[]
    def seconds(value):
        parts=value.split(':');return sum(float(x)*60**i for i,x in enumerate(reversed(parts)))
    for block in re.split(r'\n\s*\n',raw):
        lines=block.splitlines();index=next((i for i,s in enumerate(lines) if '-->' in s),None)
        if index is None:continue
        match=re.match(r'([\d:.]+)\s*-->\s*([\d:.]+)',lines[index])
        if not match:continue
        text=html.unescape(re.sub(r'<[^>]+>','',' '.join(lines[index+1:]))).strip()
        if text:rows.append({'start':seconds(match[1]),'duration':max(0,seconds(match[2])-seconds(match[1])),'text':text})
    return rows


def verify_media(path,folder):
    command=['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries',
        'format=duration,format_name:stream=codec_type,codec_name,sample_rate,channels','-of','json',str(path)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=60);require(p.returncode==0,'ffprobe rejected media')
    info=json.loads(p.stdout);duration=float(info['format']['duration'])
    require(math.isfinite(duration) and duration>0 and any(s['codec_type']=='audio' for s in info['streams']),'Missing finite audio stream')
    decode=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-xerror','-err_detect','explode','-protocol_whitelist','file,pipe','-i',str(path),'-map','0:a:0','-vn','-ac','1','-ar','16000','-f','s16le','-']
    digest=hashlib.sha256();count=0;started=time.monotonic()
    with (folder/'decode.stderr').open('wb') as log:
        process=subprocess.Popen(decode,stdout=subprocess.PIPE,stderr=log)
        try:
            os.set_blocking(process.stdout.fileno(),False)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while True:
                    if time.monotonic()-started>max(120,duration*2):raise RuntimeError('Local decode time budget exceeded; artifact not admitted')
                    if not selector.select(timeout=.5):continue
                    chunk=os.read(process.stdout.fileno(),1024**2)
                    if not chunk:break
                    digest.update(chunk);count+=len(chunk)
            code=process.wait(timeout=30)
        finally:
            process.stdout.close()
            if process.poll() is None:process.kill()
            process.wait(timeout=30)
    require(code==0 and count>0 and count%2==0 and (folder/'decode.stderr').stat().st_size==0,'Strict full PCM decode failed or emitted an error')
    decoded=count/2/16000;require(abs(decoded-duration)<=max(.25,.02*duration),'Container/decode duration differs')
    return {'ffprobe':info,'duration_seconds':duration,'decoded_pcm':{'sha256':digest.hexdigest(),'sample_count':count//2,
        'sample_rate':16000,'channels':1,'format':'s16le','duration_seconds':decoded,'coverage':'full first audio stream'},
        'kind':'video' if any(s['codec_type']=='video' for s in info['streams']) else'audio'}


def validate_media_policy(check,minimum,metadata_duration):
    require(check['decoded_pcm']['duration_seconds']>=minimum,'Decoded media below source duration policy')
    require(abs(check['duration_seconds']-metadata_duration)<=max(2,.02*metadata_duration),'Fresh metadata and media duration differ')


class Runner:
    def __init__(self,store,run_id):
        self.store=store;self.run_id=run_id;self.stop=threading.Event();self.budget=Budget(store.root)
        self.counts=Counter();self.count_lock=threading.Lock();self.runtime=runtime()
        self.failure_lock=threading.Lock();self.failure_class=None;self.failure_jobs=set();self.breaker=None
    def increment(self,key):
        with self.count_lock:self.counts[key]+=1
    def outcome(self,job,error=None):
        # A small descriptive circuit breaker prevents thousands of identical
        # failed jobs; it does not diagnose a platform-wide outage.
        repeated={'origin_or_media_access_denied','extractor_or_network_failure'}
        with self.failure_lock:
            if error not in repeated:self.failure_class=None;self.failure_jobs=set();return
            if self.failure_class!=error:self.failure_class=error;self.failure_jobs=set()
            self.failure_jobs.add(job)
            if len(self.failure_jobs)>=3:
                self.breaker={'status':'held_repeated_stage_failure','error_class':error,'distinct_jobs':len(self.failure_jobs),
                    'threshold':3,'scope':'Three distinct consecutive completed jobs shared this error class; cause remains unresolved.'}
                self.stop.set()
    def enumerate_tab(self,account,tab):
        import yt_dlp
        aid=account['account_id'];raw=json.loads(account['input_json']);cid=account['channel_id']
        if self.stop.is_set():return
        if cid:base='https://www.youtube.com/channel/'+cid
        else:
            handles=raw.get('handles',[])
            if handles:
                handle=handles[0];handle=handle if handle.startswith('@') else'@'+handle
                base='https://www.youtube.com/'+urllib.parse.quote(handle,safe='@')
            else:
                urls=[route for u in raw.get('urls',[]) if (route:=supported_account_route(u))]
                if not urls:
                    with self.store.connect() as c:c.execute("UPDATE tabs SET status='unresolved_route',error_class='missing_supported_account_route' WHERE account_id=? AND tab=?",(aid,tab))
                    return
                base=urls[0]
        url=base+'/'+tab;folder=self.store.root/'enumeration'/aid/tab/(self.run_id+'-'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
        logger=CaptureLogger();options=ydl_options(logger);options.update(extract_flat='in_playlist',lazy_playlist=True,noplaylist=False,skip_download=True)
        status='failed';kind='unknown';error=None;seen=set();unresolved=0;started=now();meta={}
        try:
            self.increment('tab_requests_this_run')
            with yt_dlp.YoutubeDL(options) as ydl:
                info=ydl.extract_info(url,download=False);require(isinstance(info,dict),'No account tab result')
                returned=info.get('channel_id') or (info.get('id') if CHANNEL.fullmatch(str(info.get('id',''))) else None)
                require(returned and CHANNEL.fullmatch(returned),'Tab response lacks a stable channel ID')
                if cid:require(returned==cid,'Tab identity conflicts with accepted channel ID')
                with self.store.connect() as c:
                    stored=c.execute('SELECT channel_id FROM accounts WHERE account_id=?',(aid,)).fetchone()[0]
                    require(stored is None or stored==returned,'Tab identity conflicts with an earlier exact account resolution')
                    c.execute('UPDATE accounts SET channel_id=? WHERE account_id=?',(returned,aid))
                meta={k:info.get(k) for k in ('id','channel_id','channel','channel_url','webpage_url','extractor_key','title','playlist_count')}
                with (folder/'entries.jsonl').open('x') as stream:
                    for index,item in enumerate(info.get('entries') or []):
                        if self.stop.is_set():raise RuntimeError('shared_stop')
                        vid=item.get('id') if isinstance(item,dict) else None
                        if not vid or not VIDEO.fullmatch(vid):unresolved+=1;stream.write(encoded({'slot':index,'unresolved':True,'type':type(item).__name__})+'\n');continue
                        row={k:item.get(k) for k in ('id','url','title','channel_id','channel','duration','live_status','availability','_type')};row['slot']=index
                        stream.write(encoded(row)+'\n');stream.flush();seen.add(vid)
                        with self.store.connect() as c:
                            scope='indexed_or_accepted' if account['inclusion_status'].startswith('included') else'pending_relevance_review'
                            c.execute('INSERT OR IGNORE INTO videos(video_id,minimum_seconds,scope_status) VALUES (?,?,?)',(vid,account['minimum_seconds'],scope))
                            c.execute('UPDATE videos SET minimum_seconds=MAX(minimum_seconds,?) WHERE video_id=?',(account['minimum_seconds'],vid))
                            c.execute('INSERT OR IGNORE INTO membership VALUES (?,?,?,?)',(aid,tab,vid,'fresh_extractor_tab'))
            status='completed' if not unresolved else'partial_unresolved_slots';kind='extractor_completed_accessible_tab'
        except Exception as exc:
            error,shared=classify_error(exc)
            if shared:self.stop.set()
            status='tab_absent_or_unavailable' if error=='tab_absent_or_unavailable' else'partial' if seen else'failed'
        self.outcome('tab:'+aid+':'+tab,error)
        receipt={'account_id':aid,'tab':tab,'source_url':url,'started_at':started,'finished_at':now(),'status':status,
            'enumeration_kind':kind,'terminal_continuation_independently_observed':False,'returned_unique_ids':len(seen),
            'unresolved_slots':unresolved,'metadata':meta,'runtime':self.runtime,
            'options':{'extract_flat':'in_playlist','lazy_playlist':True,'ignoreerrors':False,'playlist_end':None,'playlist_items':None,'date_filter':None},
            'error_class':error,'logs':logger.rows,'raw_entries':ref(folder/'entries.jsonl') if (folder/'entries.jsonl').exists() else None}
        save(folder/'receipt.json',receipt)
        with self.store.connect() as c:c.execute('UPDATE tabs SET status=?,enumeration_kind=?,returned_unique_ids=?,unresolved_slots=?,error_class=?,receipt_path=? WHERE account_id=? AND tab=?',(status,kind,len(seen),unresolved,error,str(folder/'receipt.json'),aid,tab))

    def acquire(self,row):
        import yt_dlp
        vid=row['video_id'];edition=uuid.uuid4().hex;folder=self.store.root/'media'/vid/edition;folder.mkdir(parents=True)
        logger=CaptureLogger();opts=ydl_options(logger);opts.update(outtmpl=str(folder/'%(id)s.%(ext)s'),writeinfojson=False)
        started=now();reserved=0;reservation_acquired=False;status='retryable';error=None;metadata=None;audio=None;text_artifact=None;caption=None
        with self.store.connect() as c:c.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',(edition,self.run_id,vid,started,None,'running',None,None))
        try:
            if self.stop.is_set():raise RuntimeError('shared_stop')
            self.increment('metadata_requests_this_run')
            with yt_dlp.YoutubeDL(opts) as ydl:info=ydl.extract_info('https://www.youtube.com/watch?v='+vid,download=False)
            require(info.get('id')==vid,'Fresh metadata video identity mismatch')
            owner=info.get('channel_id');require(owner and CHANNEL.fullmatch(owner),'Fresh metadata lacks exact owner channel ID')
            effective_minimum,policy_basis=duration_floor(row,info);row={**row,'minimum_seconds':effective_minimum}
            duration=info.get('duration');valid_duration=isinstance(duration,(int,float)) and not isinstance(duration,bool) and math.isfinite(duration) and duration>0
            metadata=folder/'metadata.json';metadata_value=yt_dlp.YoutubeDL.sanitize_info(info)
            if not valid_duration:
                metadata_value=dict(metadata_value);metadata_value['duration']=None
                metadata_value['_collector_invalid_duration']={'type':type(duration).__name__,'representation':repr(duration)}
            save(metadata,metadata_value)
            with self.store.connect() as c:
                c.execute("UPDATE videos SET metadata_status='verified_current',owner_channel_id=?,duration_seconds=?,minimum_seconds=?,metadata_path=? WHERE video_id=?",(owner,duration if valid_duration else None,effective_minimum,str(metadata),vid))
                accepted={r[0] for r in c.execute("SELECT channel_id FROM accounts WHERE inclusion_status!='excluded' AND channel_id IS NOT NULL")}
            if owner not in accepted:status='owner_review_required';raise ValueError('Actual owner is outside accepted exact channel IDs')
            if info.get('is_live') or info.get('live_status') in ('is_live','is_upcoming','post_live'):
                status='deferred_live_or_upcoming';raise ValueError('Live/upcoming or unfinalized stream deferred')
            if not valid_duration:
                status='pending_duration';raise ValueError('Finite positive duration not established')
            if duration<row['minimum_seconds']:status='excluded_duration';raise ValueError('Below this source-specific duration floor')
            with self.store.connect() as c:c.execute("UPDATE videos SET eligibility_status='eligible' WHERE video_id=?",(vid,))
            caption=choose_caption(info)
            estimate=info.get('filesize') or info.get('filesize_approx') or math.ceil(duration*max(float(info.get('abr') or 0),256)*1000/8)
            reserved=int(estimate*1.15)+16*1024**2;self.budget.acquire(reserved);reservation_acquired=True
            def progress(event):
                self.budget.check()
                if self.stop.is_set():raise RuntimeError('shared_stop')
                if event.get('downloaded_bytes',0)>reserved:raise RuntimeError('resource_floor: artifact exceeded reserved estimate')
            opts.update(progress_hooks=[progress],writesubtitles=bool(caption and not caption['is_generated']),
                writeautomaticsub=bool(caption and caption['is_generated']),subtitleslangs=[caption['language']] if caption else[],subtitlesformat='json3/vtt')
            self.increment('media_requests_this_run')
            if caption:self.increment('caption_requests_this_run')
            selected_info=restrict_caption_tracks(info,caption)
            with yt_dlp.YoutubeDL(opts) as ydl:completed=ydl.process_ie_result(selected_info,download=True)
            if caption:
                accepted_urls={t['url'] for t in caption['tracks']}
                for selected in (completed.get('requested_subtitles') or {}).values():
                    require(selected.get('url') in accepted_urls,'Extractor selected a caption track outside the untranslated allowlist')
            files=[p for p in folder.iterdir() if p.suffix.lower() in ('.m4a','.webm','.mp4','.opus','.ogg','.mp3','.aac','.flac','.wav','.mkv')]
            require(len(files)==1,'Expected one finalized original media file')
            check=verify_media(files[0],folder);validate_media_policy(check,row['minimum_seconds'],duration)
            audio=self.store.add_artifact(vid,edition,check['kind'],files[0],{'validation':check,'metadata_sha256':sha(metadata),'owner_channel_id':owner})
            if caption:
                captions=[p for p in folder.iterdir() if p.suffix in ('.json3','.vtt')]
                if captions:
                    chosen=next((p for p in captions if p.suffix=='.json3'),captions[0]);segments=caption_segments(chosen)
                    if segments:
                        raw=self.store.add_artifact(vid,edition,'caption',chosen,{'language':caption['language'],'is_generated':caption['is_generated'],'audio_alignment_verified':False})
                        transcript={'source_video_id':vid,'source_url':'https://www.youtube.com/watch?v='+vid,'language':caption['language'],
                            'is_generated':caption['is_generated'],'origin':'offered_youtube_caption','translation_requested':False,
                            'caption_sha256':raw['sha256'],'segments':segments,'text':' '.join(s['text'] for s in segments),
                            'speaker_identity_verified':False,'audio_alignment_verified':False}
                        save(folder/'transcript.json',transcript);(folder/'transcript.txt').write_text(transcript['text']+'\n')
                        text_artifact=self.store.add_artifact(vid,edition,'transcript',folder/'transcript.json',{'origin':'offered_youtube_caption','words':len(transcript['text'].split()),'caption_sha256':raw['sha256']})
                        self.store.add_artifact(vid,edition,'text',folder/'transcript.txt',{'origin':'offered_youtube_caption','transcript_sha256':text_artifact['sha256']})
            with self.store.connect() as c:
                c.execute('UPDATE videos SET media_status=?,caption_status=?,asr_status=? WHERE video_id=?',('verified',
                    'verified_text' if text_artifact else'offered_track_failed_or_missing' if caption else'no_offered_original_track',
                    'not_needed_for_text_coverage' if text_artifact else'queued',vid))
                if not text_artifact:c.execute('INSERT INTO asr_queue VALUES (?,?,?,?,?)',(vid,edition,audio['artifact_id'],'pending','No verified offered-caption transcript; ASR not yet executed'))
            status='complete' if text_artifact else'audio_complete_asr_pending'
        except Exception as exc:
            error,shared=classify_error(exc)
            if shared:self.stop.set()
            if status=='retryable':status='held_shared_route' if shared and error!='resource_floor' else'held_resource' if error=='resource_floor' else'unavailable' if error=='source_restricted_or_unavailable' else'retryable'
        finally:
            if reservation_acquired:self.budget.release(reserved)
        if audio and not text_artifact:
            with self.store.connect() as c:
                c.execute("UPDATE videos SET media_status='verified',asr_status='queued',caption_status='no_verified_caption_text' WHERE video_id=?",(vid,))
                c.execute('INSERT OR IGNORE INTO asr_queue VALUES (?,?,?,?,?)',(vid,edition,audio['artifact_id'],'pending','No verified offered-caption transcript; ASR not yet executed'))
            if status=='retryable':status='audio_complete_asr_pending'
        receipt={'run_id':self.run_id,'video_id':vid,'edition_id':edition,'started_at':started,'finished_at':now(),
            'status':status,'error_class':error,'runtime':self.runtime,'metadata':ref(metadata) if metadata and metadata.is_file() else None,
            'effective_minimum_seconds':row['minimum_seconds'],
            'media_verified':audio is not None,'text_verified':text_artifact is not None,'logs':logger.rows,
            'resumption_scope':'Verified completed jobs are skipped after hash checks. Failed-attempt partials remain in their immutable edition; a fresh attempt does not overwrite them.'}
        save(folder/'receipt.json',receipt)
        self.outcome('video:'+vid,error)
        with self.store.connect() as c:
            c.execute('UPDATE videos SET status=?,last_error=?,eligibility_status=CASE WHEN ? IN (\'excluded_duration\',\'pending_duration\',\'owner_review_required\',\'deferred_live_or_upcoming\') THEN ? ELSE eligibility_status END WHERE video_id=?',(status,error,status,status,vid))
            c.execute('UPDATE attempts SET finished_at=?,status=?,error_class=?,receipt_path=? WHERE attempt_id=?',(now(),status,error,str(folder/'receipt.json'),edition))
        return bool(audio and status in ('complete','audio_complete_asr_pending'))

    def worker(self):
        while not self.stop.is_set():
            row=self.store.claim(self.run_id)
            if not row:return
            self.acquire(row)


def export(store,output):
    invalid=set(store.reconcile())
    with store.connect() as c:
        accounts=[dict(r) for r in c.execute('SELECT * FROM accounts ORDER BY account_id')]
        videos=[dict(r) for r in c.execute('SELECT * FROM videos ORDER BY video_id')]
        members=[dict(r) for r in c.execute('SELECT * FROM membership')];tabs=[dict(r) for r in c.execute('SELECT * FROM tabs')]
        artifacts=[dict(r) for r in c.execute('SELECT * FROM artifacts')];attempts=[dict(r) for r in c.execute('SELECT * FROM attempts')]
    valid=[a for a in artifacts if a['artifact_id'] not in invalid];by_kind=defaultdict(set)
    for a in valid:by_kind[a['kind']].add(a['video_id'])
    index={r['video_id']:r for r in videos};account_rows=[]
    for a in accounts:
        ids={m['video_id'] for m in members if m['account_id']==a['account_id']}
        owned={v for v in ids if a['channel_id'] and index[v]['owner_channel_id']==a['channel_id']}
        sets={'retained_video_ids':owned&by_kind['video'],'retained_audio_ids':owned&by_kind['audio'],
            'retained_caption_ids':owned&by_kind['caption'],'retained_transcript_ids':owned&by_kind['transcript'],
            'asr_queued_ids':{v for v in owned if index[v]['asr_status']=='queued'},'asr_completed_ids':set(),'analyzed_ids':set()}
        account_rows.append({'account_id':a['account_id'],'channel_id':a['channel_id'],'display_name':a['display_name'],
            'inclusion_status':a['inclusion_status'],'minimum_duration_seconds':a['minimum_seconds'],'observed_video_ids':sorted(ids),
            'uploaded_total':None,'tab_states':[{k:r[k] for k in ('tab','status','enumeration_kind','returned_unique_ids','unresolved_slots','error_class')} for r in tabs if r['account_id']==a['account_id']],
            **{k:sorted(v) for k,v in sets.items()}})
    video_rows=[]
    for v in videos:
        row={k:v[k] for k in ('video_id','status','scope_status','metadata_status','duration_seconds','eligibility_status','media_status','caption_status','asr_status','analysis_status')}
        row.update(verified_owner_channel_id=v['owner_channel_id'],listed_account_ids=sorted({m['account_id'] for m in members if m['video_id']==v['video_id']}),
            source_url='https://www.youtube.com/watch?v='+v['video_id'],last_error_class=v['last_error'],
            artifacts=[{'artifact_id':a['artifact_id'],'kind':a['kind'],'bytes':a['bytes'],'sha256':a['sha256'],'storage_kind':'private_managed_workspace'} for a in valid if a['video_id']==v['video_id']])
        video_rows.append(row)
    state={'schema_version':1,'run_id':store.get('last_run_id'),'updated_at':now(),'network_gate':store.get('network_gate',{'status':'not_checked'}),
        'inventory_binding':store.get('inventory_binding'),'last_runtime':store.get('last_runtime'),
        'collection_hold':store.get('collection_hold'),
        'policy':POLICY,'coverage':{'accounts':len(accounts),'included_accounts':sum(a['inclusion_status'].startswith('included') for a in accounts),
            'distinct_observed_video_ids':len(videos),'attempts_total':len(attempts),**store.get('last_run_counts',{}),
            'attempt_count_scope':'Logical extractor/acquisition operations, not a count of all HTTP subrequests.'},
        'accounts':account_rows,'videos':video_rows,
        'artifacts_summary':{'verified_files':len(valid),'verified_bytes':sum(a['bytes'] for a in valid),
            'distinct_video_ids_by_kind':{k:len(v) for k,v in sorted(by_kind.items())},'changed_artifacts':len(invalid)},
        'storage':{'kind':'private_managed_workspace','raw_publication':False,'permanent_chatgpt_account_storage':False,
            'free_bytes':shutil.disk_usage(store.root).free,'minimum_free_bytes':FLOOR},
        'limitations':['Observed IDs are not complete uploaded totals. No account identity is inferred from claimed beings or publisher-context names.',
            'Tab completion means the extractor generator ended without a declared count/date bound; it does not independently prove the last platform continuation.',
            'Retained artifacts are hash/media checked; captions/ASR accuracy, identities and claims remain unverified.',
            'Historical publisher audio and other cohorts are not counted as YouTube acquisitions here. ASR queued is not ASR completed or analyzed.',
            'A shared CONNECT failure holds collection globally; it does not mark individual videos deleted or inaccessible at YouTube.']}
    output=Path(output);output.mkdir(parents=True,exist_ok=True);save(output/'collector-status.json',state)
    save(output/'output-manifest.json',{'complete':True,'public_allowlist':[ref(output/'collector-status.json')]});return state


def run(store,gate_receipt,workers=2,enumerate_channels=True):
    require(1<=workers<=4,'Workers must be1–4');run_id=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    lock=(store.root/'run.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('Another collector run owns this archive')
    try:
        store.set('last_run_id',run_id);store.set('last_runtime',runtime());store.set('collection_hold',None)
        with store.connect() as c:c.execute("UPDATE videos SET status='interrupted' WHERE status='running'")
        store.reconcile();gate=gate_from_receipt(gate_receipt);store.set('network_gate',gate)
        counts={'tab_requests_this_run':0,'metadata_requests_this_run':0,'media_requests_this_run':0,'caption_requests_this_run':0}
        store.set('last_run_counts',counts)
        if gate['status']!='passed':
            with store.connect() as c:c.execute("UPDATE videos SET status='held_shared_route' WHERE status IN ('pending','retryable','interrupted') AND scope_status='indexed_or_accepted'")
            return {'run_id':run_id,'status':'held_before_extraction','network_gate':gate,'requests':counts}
        # A successful gate may be reused briefly; blocked receipts always retain their honest hold.
        stamp=dt.datetime.fromisoformat(gate['checked_at']);age=(dt.datetime.now(dt.timezone.utc)-stamp).total_seconds()
        require(0<=age<=3600,'Passed gate is future-dated or older than one hour; run a fresh ordinary probe')
        runner=Runner(store,run_id);store.set('collection_hold',None)
        if enumerate_channels:
            with store.connect() as c:accounts=[dict(r) for r in c.execute("SELECT * FROM accounts WHERE inclusion_status!='excluded' ORDER BY account_id")]
            for account in accounts:
                for tab in TABS:
                    if runner.stop.is_set():break
                    runner.enumerate_tab(account,tab)
                if runner.stop.is_set():break
        pilot=store.get('verified_parallel_pilot',False)
        if pilot:
            with store.connect() as c:
                row=c.execute('SELECT status,asr_status FROM videos WHERE video_id=?',(pilot['video_id'],)).fetchone()
                kinds={r[0] for r in c.execute('SELECT kind FROM artifacts WHERE video_id=?',(pilot['video_id'],))}
            pilot=bool(row and row['status'] in ('complete','audio_complete_asr_pending') and ('transcript' in kinds or row['asr_status']=='queued') and {'audio','video'}&kinds
                and pilot.get('collector_sha256')==runner.runtime['collector_sha256'])
        while not pilot and not runner.stop.is_set():
            item=store.claim(run_id)
            if not item:break
            if runner.acquire(item):pilot=True;store.set('verified_parallel_pilot',{'video_id':item['video_id'],'run_id':run_id,'collector_sha256':runner.runtime['collector_sha256']})
        if pilot and not runner.stop.is_set():
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(lambda _:runner.worker(),range(workers)))
        counts.update(runner.counts);store.set('last_run_counts',counts);store.set('collection_hold',runner.breaker)
        return {'run_id':run_id,'status':'stopped_shared_failure' if runner.stop.is_set() else'finished_available_queue','requests':counts,
            'parallel_pilot_verified':bool(pilot),'scope':'Queue completion does not establish a complete channel upload census.'}
    finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    commands=p.add_subparsers(dest='command',required=True)
    init=commands.add_parser('init');init.add_argument('--accounts',type=Path,required=True)
    network=commands.add_parser('probe');network.add_argument('--url',default='https://www.youtube.com/')
    collect=commands.add_parser('run');collect.add_argument('--gate-receipt',type=Path,required=True);collect.add_argument('--workers',type=int,default=2);collect.add_argument('--no-enumeration',action='store_true')
    publish=commands.add_parser('export');publish.add_argument('--output',type=Path,required=True)
    commands.add_parser('runtime')
    a=p.parse_args();store=Store(a.root)
    if a.command=='init':store.initialize(a.accounts);print(encoded({'status':'initialized','input':ref(a.accounts)}))
    elif a.command=='probe':print(encoded({'receipt':str(probe(store.root,a.url))}))
    elif a.command=='run':print(encoded(run(store,a.gate_receipt,a.workers,not a.no_enumeration)))
    elif a.command=='export':result=export(store,a.output);print(encoded({'coverage':result['coverage'],'network_gate':result['network_gate']}))
    elif a.command=='runtime':print(encoded(runtime()))


if __name__=='__main__':main()
