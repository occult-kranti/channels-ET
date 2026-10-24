#!/usr/bin/env python3
"""Isolated, fail-closed long-form queue. All commands except probe/run-one are offline."""
from __future__ import annotations
import argparse
from collections import Counter
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import ssl
import subprocess
import sys
import time
import concurrent.futures
import threading
from urllib.parse import urlsplit, parse_qs
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINNED_YTDLP = '2026.10.21'
CAPS = {'metadata': 4*1024**2, 'captions': 8*1024**2, 'video': 512*1024**2, 'audio': 128*1024**2}
BASHAR = re.compile(r'\bbashar\b|\bdarryl\s+anka\b', re.I)
ID = re.compile(r'[A-Za-z0-9_-]{11}')

def canonical_watch(url,video_id):
    try:
        p=urlsplit(url)
        return p.scheme=='https' and p.hostname in {'www.youtube.com','youtube.com'} and p.port in (None,443) and not p.username and not p.password and p.path=='/watch' and parse_qs(p.query).get('v')==[video_id]
    except ValueError: return False
class HTTPSWatchRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,video_id): super().__init__(); self.video_id=video_id
    def redirect_request(self,request,response,code,message,headers,target):
        if not canonical_watch(target,self.video_id) or urllib.request.proxy_bypass(urlsplit(target).hostname): raise ValueError('Redirect left pinned HTTPS watch identity/proxy; not followed')
        return super().redirect_request(request,response,code,message,headers,target)
def watch_payload(body,video_id):
    text=body.decode('utf-8',errors='replace'); found=re.search(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*',text)
    if not found: raise ValueError('Actual player response is absent')
    data,_=json.JSONDecoder().raw_decode(text[found.end():])
    if data.get('videoDetails',{}).get('videoId')!=video_id or data.get('playabilityStatus',{}).get('status')!='OK': raise ValueError('Player response is not playable requested identity')
    return data
@contextlib.contextmanager
def collection_lock(root):
    with (Path(root)/'.collection-worker.lock').open('a+') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Shared old/new collection writer lock is already held')
        try: yield
        finally: fcntl.flock(lock,fcntl.LOCK_UN)

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def encoded(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n'); temp.replace(path)
def valid_id(value): return isinstance(value, str) and ID.fullmatch(value) is not None
def inside_git(path):
    for parent in (Path(path).resolve(), *Path(path).resolve().parents):
        marker = parent/'.git'
        if marker.is_dir() and (marker/'HEAD').is_file(): return True
        if marker.is_file() and marker.read_text().startswith('gitdir:'): return True
    return False
def tree_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file() and not p.is_symlink())
def config(runtime):
    # Proxy credentials are used through supported environment bindings, never emitted.
    values = {k: os.environ.get(k, '') for k in ('HTTPS_PROXY','https_proxy','HTTP_PROXY','ALL_PROXY','NO_PROXY','no_proxy','SSL_CERT_FILE','REQUESTS_CA_BUNDLE')}
    certs = {k: sha(v) for k,v in values.items() if k in ('SSL_CERT_FILE','REQUESTS_CA_BUNDLE') and v and Path(v).is_file()}
    observed=json.loads(Path(runtime).read_text())
    if not isinstance(observed,dict): raise ValueError('Runtime observation must be an object')
    fixture=observed.get('fixture_only') is True
    if observed.get('source')!='cloud_environment.environment_status' and not fixture: raise ValueError('A supported cloud runtime observation is required, not a package/runtime-install receipt')
    def revision_value(value):
        if isinstance(value,bool) or not isinstance(value,(str,int)) or not str(value).strip(): raise ValueError('Runtime revisions must be nonempty strings or integers, never booleans/null/objects')
        return str(value).strip()
    revision=revision_value(observed.get('spec_revision')); observed_revision=revision_value(observed.get('observed_spec_revision'))
    policy=observed.get('network_policy',{})
    if not isinstance(policy,dict) or revision!=observed_revision or observed.get('observations_current') is not True or policy.get('mode') not in ('disabled','restricted','unrestricted') or not isinstance(policy.get('state'),str) or not policy['state']: raise ValueError('Matching current configuration revision and typed network mode/state are required')
    for field in ('allowed_hosts','allowed_domains','presets'):
        if field in policy and (not isinstance(policy[field],list) or not all(isinstance(v,str) for v in policy[field])): raise ValueError('Network set-like policy fields must be lists of strings')
    if not isinstance(observed.get('checkedAt'),str): raise ValueError('Dated runtime observation required')
    try: age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(observed['checkedAt'].replace('Z','+00:00'))).total_seconds()
    except (KeyError,TypeError,ValueError): raise ValueError('Dated runtime observation required')
    if not -60<=age<=24*3600: raise ValueError('Runtime observation is stale')
    # Bind the supported mode/state observation; timestamps/serialization do not create a new configuration.
    semantics={'revision':revision,'mode':policy['mode'],'state':policy['state'],
               **{k:sorted(set(policy[k])) for k in ('allowed_hosts','allowed_domains','presets') if k in policy}}
    record = {'values': values, 'cert_hashes': certs, 'runtime_semantics':semantics, 'python': sys.version, 'tls': True}
    return {'fingerprint': hashlib.sha256(encoded(record).encode()).hexdigest(), 'runtime_receipt_sha256': sha(runtime),
            'runtime_semantics':semantics,'fixture_only':fixture,
            'proxy_configured': bool(values['HTTPS_PROXY'] or values['https_proxy']), 'tls_verification': True}
def probe_request_allowed(prior,at):
    return prior is None or (prior['status']=='success' and at-prior['checked_at']>300)
def rows(path):
    path=Path(path)
    if path.suffix == '.jsonl': return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    data=json.loads(path.read_text())
    if isinstance(data,list): return data
    for key in ('records','videos','entries'):
        if isinstance(data.get(key),list): return data[key]
    raise ValueError('Expected JSONL or records/videos/entries list')
def fresh_classification(policy, metadata):
    fields=('title','uploader','uploader_id','channel','channel_id','description','tags','creator','artists')
    matched=[k for k in fields if BASHAR.search(encoded(metadata.get(k,'')))]
    inherited=policy.get('classification')
    provenance=BASHAR.search(encoded(policy.get('classification_evidence',[]))) is not None
    if inherited=='explicit_bashar_association' or matched or provenance: return 'bashar', matched
    if inherited!='not_bashar_labeled_in_available_metadata': return 'ambiguous', matched
    if not metadata.get('title') or not (metadata.get('channel') or metadata.get('uploader')): return 'ambiguous', matched
    return 'other_not_bashar_labeled', matched

class Store:
    def __init__(self, database, raw, quota=20*1024**3, reserve_free=6*1024**3,budget_root=None):
        self.database=Path(database); self.raw=Path(raw).resolve(); self.quota=quota; self.reserve_free=reserve_free
        self.budget_root=Path(budget_root).resolve() if budget_root else self.raw
        if not self.raw.is_relative_to(self.budget_root) or not self.database.resolve().is_relative_to(self.raw): raise ValueError('Database must be beneath private raw root and raw root beneath shared budget root')
        if inside_git(self.raw): raise ValueError('Raw/quarantine data must be outside real Git checkouts')
        if inside_git(self.database.parent): raise ValueError('Mutable state with raw metadata must stay outside Git')
        self.raw.mkdir(parents=True,exist_ok=True); self.database.parent.mkdir(parents=True,exist_ok=True)
        authority=self.raw/'.runner-authority.json'
        identity={'database':str(self.database.resolve()),'scope':'single_global_Bashar_YouTube_cap_authority'}
        try:
            with authority.open('x') as f: f.write(encoded(identity))
        except FileExistsError:
            if json.loads(authority.read_text())!=identity: raise ValueError('This raw root already belongs to another cap ledger; migrate its existing state, never reset it')
        with self.connect() as c:
            c.executescript('''PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS items(source_id TEXT PRIMARY KEY,video_id TEXT UNIQUE NOT NULL,policy_json TEXT NOT NULL,
              selected INTEGER NOT NULL,classification TEXT NOT NULL DEFAULT 'ambiguous',metadata_json TEXT,metadata_sha256 TEXT,
              metadata_path TEXT,metadata_verified_at REAL,duration REAL,format_verified INTEGER NOT NULL DEFAULT 0,review_json TEXT);
            CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES items(source_id),kind TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'queued',attempts INTEGER NOT NULL DEFAULT 0,owner TEXT,lease_until REAL,
              reservation_bytes INTEGER NOT NULL DEFAULT 0,child_pid INTEGER,child_start TEXT,error TEXT,
              UNIQUE(source_id,kind));
            CREATE TABLE IF NOT EXISTS bashar_slots(source_id TEXT PRIMARY KEY,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS probes(fingerprint TEXT PRIMARY KEY,status TEXT NOT NULL,checked_at REAL NOT NULL,
              receipt_json TEXT NOT NULL,body_path TEXT,body_sha256 TEXT);
            CREATE TABLE IF NOT EXISTS artifacts(path TEXT PRIMARY KEY,source_id TEXT NOT NULL,kind TEXT NOT NULL,bytes INTEGER NOT NULL,
              sha256 TEXT NOT NULL,validation_json TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,source_id TEXT,kind TEXT NOT NULL,record_json TEXT NOT NULL);
            ''')
    def connect(self):
        c=sqlite3.connect(self.database,timeout=30); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
    def setting(self,c,key,default=None):
        r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone(); return json.loads(r[0]) if r else default
    def initialize(self, selection, policy, conservative=False, blocked_probe=None, runtime=None):
        spec=json.loads(Path(policy).read_text())
        selection_key='selected_conservative_all_materials' if conservative else 'selected_default'
        limit=spec['conservative_new_bashar_youtube_limit'] if conservative else spec['default_new_bashar_youtube_limit']
        if not isinstance(limit,int) or limit<0 or limit>100: raise ValueError('Bashar YouTube limit must be at most100')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=self.setting(c,'policy')
            pinned={'policy_sha256':sha(policy),'selection_sha256':sha(selection),'selection_key':selection_key,'bashar_limit':limit}
            if old and old!=pinned: raise ValueError('Policy already pinned; use a new isolated database for a changed policy')
            c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',('policy',encoded(pinned)))
            for row in rows(selection): self.import_item(c,row,selection_key)
            if blocked_probe:
                observed=json.loads(Path(blocked_probe).read_text())
                # Import can only create a denial; successful access must come from probe().
                current=config(runtime);fingerprint=current['fingerprint']
                receipt={'source':'inherited_current_denial','source_sha256':sha(blocked_probe),'status':'blocked',
                         'reason':'No runner-created successful current-configuration watch probe','observed_record_status':observed.get('status'),
                         'runtime_receipt_sha256':current['runtime_receipt_sha256'],'runtime_semantics':current['runtime_semantics']}
                for previous in c.execute('SELECT * FROM probes WHERE fingerprint<>?',(fingerprint,)).fetchall():
                    old_receipt=json.loads(previous['receipt_json'])
                    if old_receipt.get('source')=='inherited_current_denial' and 'runtime_semantics' not in old_receipt:
                        c.execute('INSERT INTO events(source_id,kind,record_json) VALUES(?,?,?)',(None,'legacy_package_runtime_binding_preserved_not_authoritative',encoded(dict(previous))))
                c.execute('INSERT OR IGNORE INTO probes VALUES(?,?,?,?,?,?)',(fingerprint,'blocked',time.time(),encoded(receipt),None,None))
        return self.export()
    def import_item(self,c,row,selection_key=None):
        vid=row.get('video_id',row.get('id')); source='youtube:'+str(vid)
        if not valid_id(vid): raise ValueError('Invalid YouTube video ID')
        if row.get('source_id',source)!=source: raise ValueError('Source ID must be canonical youtube:VIDEO_ID')
        selected=bool(row.get(selection_key,False)) if selection_key else False
        if not selection_key:
            row={'video_id':vid,'source_id':source,'source_url':'https://www.youtube.com/watch?v='+vid,
                 'classification':'ambiguous_bashar_context','duration_state':'unknown','shorts_evidence':[],
                 'metadata_refresh_required':True,'discovery_provenance':row,'imported_metadata_only':True}
        c.execute('INSERT OR IGNORE INTO items(source_id,video_id,policy_json,selected) VALUES(?,?,?,?)',(source,vid,encoded(row),int(selected)))
        c.execute('INSERT OR IGNORE INTO jobs(job_id,source_id,kind) VALUES(?,?,?)',('metadata:'+vid,source,'metadata'))
        if selected:
            for kind in ('captions','video'): c.execute('INSERT OR IGNORE INTO jobs(job_id,source_id,kind) VALUES(?,?,?)',(kind+':'+vid,source,kind))
    def import_discovery(self,path):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            before=c.execute('SELECT COUNT(*) FROM items').fetchone()[0]
            for row in rows(path): self.import_item(c,row)
            return {'new_ids':c.execute('SELECT COUNT(*) FROM items').fetchone()[0]-before,'input_sha256':sha(path),'state':'metadata_only'}
    def metadata_result(self,source_id,metadata,path,review=None):
        path=Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.raw) or encoded(json.loads(path.read_text()))!=encoded(metadata): raise ValueError('Parsed metadata must match its actual private hashed source file')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); item=c.execute('SELECT * FROM items WHERE source_id=?',(source_id,)).fetchone()
            if not item or metadata.get('id')!=item['video_id']: raise ValueError('Metadata output ID mismatch')
            duration=metadata.get('duration')
            if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0: duration=None
            policy=json.loads(item['policy_json']); classification,matched=fresh_classification(policy,metadata)
            previous_review=json.loads(item['review_json'] or '{}'); current_sha=sha(path)
            valid_review=previous_review.get('metadata_sha256')==current_sha
            if classification=='ambiguous' and valid_review: classification=previous_review.get('identity_resolution',classification)
            positive_short=metadata.get('is_short') is True or metadata.get('media_type')=='short' or any('/shorts/' in str(metadata.get(k,'')) for k in ('webpage_url','original_url')) or bool(re.search(r'(?i)#shorts?\b',str(metadata.get('title',''))))
            extractor_video=metadata.get('media_type')=='video' or (metadata.get('media_type')=='livestream' and metadata.get('live_status') in ('was_live','not_live'))
            nonshort=not positive_short and canonical_watch(metadata.get('webpage_url',''),item['video_id']) and (metadata.get('is_short') is False or extractor_video or (valid_review and previous_review.get('non_shorts_verified') is True))
            c.execute('UPDATE items SET metadata_json=?,metadata_sha256=?,metadata_path=?,metadata_verified_at=?,duration=?,classification=?,format_verified=? WHERE source_id=?',
                      (encoded(metadata),sha(path),str(Path(path).resolve()),time.time(),duration,classification,int(nonshort),source_id))
            return {'classification':classification,'fresh_bashar_context_fields':matched,'duration':duration,'non_shorts_verified':nonshort}
    def review(self,source_id,evidence_path):
        review=json.loads(Path(evidence_path).read_text()); proof=review.get('evidence_source_ref',{}); proofpath=Path(proof.get('path',''))
        if not review.get('reason') or not proofpath.is_file() or sha(proofpath)!=proof.get('sha256'): raise ValueError('Source-hashed review evidence required')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); item=c.execute('SELECT * FROM items WHERE source_id=?',(source_id,)).fetchone()
            if not item or review.get('metadata_sha256')!=item['metadata_sha256']: raise ValueError('Review must bind current verified metadata')
            decision=review.get('identity_resolution',item['classification'])
            if decision not in ('bashar','other_not_bashar_labeled','ambiguous'): raise ValueError('Invalid identity resolution')
            if item['classification']=='bashar' and decision!='bashar': raise ValueError('Positive Bashar context cannot be overridden into uncapped other')
            metadata=json.loads(item['metadata_json'] or '{}')
            if review.get('non_shorts_verified') is True and (metadata.get('is_short') is True or metadata.get('media_type')=='short' or any('/shorts/' in str(metadata.get(k,'')) for k in ('webpage_url','original_url'))): raise ValueError('Positive Shorts evidence cannot be overridden')
            c.execute('UPDATE items SET review_json=?,classification=?,format_verified=?,selected=? WHERE source_id=?',
                      (encoded(review),decision,int(item['format_verified'] or review.get('non_shorts_verified') is True),int(item['selected'] or review.get('admit_assets') is True),source_id))
            if item['selected'] or review.get('admit_assets') is True:
                for kind in ('captions','video'): c.execute('INSERT OR IGNORE INTO jobs(job_id,source_id,kind) VALUES(?,?,?)',(kind+':'+item['video_id'],source_id,kind))
    def reasons(self,item):
        p=json.loads(item['policy_json']); review=json.loads(item['review_json'] or '{}'); reasons=[]
        if review.get('metadata_sha256')!=item['metadata_sha256']: review={}
        metadata=json.loads(item['metadata_json'] or '{}')
        if not item['selected']: reasons.append('not_selected_or_discovery_requires_explicit_admission')
        if item['metadata_verified_at'] is None or not item['metadata_path'] or not Path(item['metadata_path']).is_file() or sha(item['metadata_path'])!=item['metadata_sha256']: reasons.append('fresh_verified_metadata_required')
        elif not 0<=time.time()-item['metadata_verified_at']<=300: reasons.append('verified_metadata_stale_max300seconds')
        if item['duration'] is None or item['duration']<300: reasons.append('verified_duration_below300_or_unknown')
        if p.get('duration_state')=='conflicting' and review.get('duration_conflict_resolved') is not True: reasons.append('inherited_duration_conflict_unresolved')
        if p.get('shorts_evidence') or '/shorts/' in str(p.get('source_url','')): reasons.append('historical_shorts_or_title_marker_hold')
        if metadata.get('is_short') is True or metadata.get('media_type')=='short' or any('/shorts/' in str(metadata.get(k,'')) for k in ('webpage_url','original_url')) or re.search(r'(?i)#shorts?\b',str(metadata.get('title',''))): reasons.append('fresh_positive_shorts_evidence')
        if metadata.get('is_live') is True or metadata.get('live_status') in ('is_live','post_live'): reasons.append('ongoing_or_not_final_live_duration')
        if not item['format_verified']: reasons.append('non_shorts_format_not_verified')
        if item['classification']=='ambiguous': reasons.append('bashar_identity_ambiguous')
        return reasons
    def refresh_metadata(self,source_id,reason):
        if not reason.strip(): raise ValueError('An explicit single-item refresh reason is required')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            item=c.execute('SELECT * FROM items WHERE source_id=?',(source_id,)).fetchone()
            if not item: raise ValueError('Unknown source; import metadata-only first')
            if c.execute("SELECT 1 FROM jobs WHERE source_id=? AND status IN ('running','expired_held')",(source_id,)).fetchone(): raise ValueError('Active/expired lease must be resolved first')
            c.execute('INSERT INTO events(source_id,kind,record_json) VALUES(?,?,?)',(source_id,'explicit_metadata_refresh',encoded({'reason':reason,'at':now()})))
            # Preserve total attempts in events; this opens one explicit refresh, never an automatic retry loop.
            job=c.execute("SELECT * FROM jobs WHERE source_id=? AND kind='metadata'",(source_id,)).fetchone()
            c.execute('INSERT INTO events(source_id,kind,record_json) VALUES(?,?,?)',(source_id,'previous_metadata_job',encoded(dict(job))))
            c.execute("UPDATE jobs SET status='queued',attempts=0,error=NULL WHERE source_id=? AND kind='metadata'",(source_id,))
    def gate(self,runtime):
        current=config(runtime)
        if current['fixture_only']: return {'ready':False,'reason':'synthetic_runtime_cannot_authorize_network','fingerprint':current['fingerprint']}
        if not current['proxy_configured']: return {'ready':False,'reason':'explicit_inherited_proxy_required'}
        with self.connect() as c: row=c.execute('SELECT * FROM probes WHERE fingerprint=?',(current['fingerprint'],)).fetchone()
        if not row or row['status']!='success': return {'ready':False,'reason':'successful_same_current_configuration_real_watch_probe_missing_or_blocked','fingerprint':current['fingerprint']}
        if not 0<=time.time()-row['checked_at']<=300: return {'ready':False,'reason':'watch_probe_stale_max300seconds'}
        path=Path(row['body_path'] or '')
        if not path.is_file() or sha(path)!=row['body_sha256']: return {'ready':False,'reason':'saved_watch_response_missing_or_changed'}
        return {'ready':True,'reason':'runner_live_watch_response_same_configuration','fingerprint':current['fingerprint']}
    def block_gate(self,runtime,reason):
        with self.connect() as c:c.execute("UPDATE probes SET status='blocked',receipt_json=? WHERE fingerprint=?",(encoded({'source':'collection_failure_global_pause','reason':reason,'at':now()}),config(runtime)['fingerprint']))
    def probe(self,runtime,video_id):
        if not valid_id(video_id): raise ValueError('Invalid watch probe ID')
        current=config(runtime)
        if current['fixture_only']: raise ValueError('Synthetic runtime cannot authorize a real probe')
        if not current['proxy_configured']: raise ValueError('Explicit inherited proxy required')
        with self.connect() as c:
            prior=c.execute('SELECT * FROM probes WHERE fingerprint=?',(current['fingerprint'],)).fetchone()
            if not probe_request_allowed(prior,time.time()):
                raise ValueError('Recorded denial or unexpired success: no unchanged-configuration bulk retries')
        proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if urllib.request.proxy_bypass('www.youtube.com'): raise ValueError('YouTube proxy bypass is not permitted')
        opener=urllib.request.build_opener(HTTPSWatchRedirect(video_id),urllib.request.ProxyHandler({'https':proxy}),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        bodypath=self.raw/'probes'/f'{video_id}-{uuid.uuid4().hex}.html'; bodypath.parent.mkdir(parents=True,exist_ok=True)
        receipt={'source':'runner_live_verified_tls_watch_probe','checked_at':now(),'configuration':current,'video_id':video_id,'tls_verification':True}
        try:
            with opener.open('https://www.youtube.com/watch?v='+video_id,timeout=25) as r:
                body=r.read(4*1024**2+1)
                if r.status!=200 or len(body)>4*1024**2 or not canonical_watch(r.geturl(),video_id): raise ValueError('Not a bounded actual HTTPS watch response for requested ID')
                watch_payload(body,video_id)
                bodypath.write_bytes(body)
            status='success'; receipt['http_status']=200
        except Exception as error:
            status='blocked'; receipt['error_type']=type(error).__name__; receipt['reason']='ordinary_watch_probe_failed_no_collection'
        receipt['status']=status
        with self.connect() as c:
            if prior:c.execute('INSERT INTO events(source_id,kind,record_json) VALUES(?,?,?)',('youtube:'+video_id,'previous_probe_before_explicit_renewal',encoded(dict(prior))))
            c.execute('INSERT OR REPLACE INTO probes VALUES(?,?,?,?,?,?)',(current['fingerprint'],status,time.time(),encoded(receipt),str(bodypath) if status=='success' else None,sha(bodypath) if status=='success' else None))
        return receipt
    def claim(self,kind,owner,gate_fingerprint,lease_seconds=600,source_id=None):
        if kind not in CAPS: raise ValueError('Unknown job kind')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); limit=self.setting(c,'policy',{})['bashar_limit']
            probe=c.execute('SELECT * FROM probes WHERE fingerprint=?',(gate_fingerprint,)).fetchone()
            if not probe or probe['status']!='success' or not 0<=time.time()-probe['checked_at']<=300: return None
            active=c.execute("SELECT COALESCE(SUM(reservation_bytes),0) FROM jobs WHERE status IN ('running','expired_held')").fetchone()[0]
            physical=tree_bytes(self.budget_root); free=shutil.disk_usage(self.budget_root).free
            if physical+active+CAPS[kind]>self.quota or free-active-CAPS[kind]<self.reserve_free: return None
            for job in c.execute("SELECT * FROM jobs WHERE kind=? AND status='queued' AND attempts=0 ORDER BY job_id",(kind,)).fetchall():
                if source_id and job['source_id']!=source_id: continue
                item=c.execute('SELECT * FROM items WHERE source_id=?',(job['source_id'],)).fetchone()
                if c.execute("SELECT 1 FROM jobs WHERE source_id=? AND status IN ('running','expired_held')",(item['source_id'],)).fetchone(): continue
                if kind!='metadata':
                    if self.reasons(item): continue
                    if item['classification']=='bashar' and not c.execute('SELECT 1 FROM bashar_slots WHERE source_id=?',(item['source_id'],)).fetchone():
                        if c.execute('SELECT COUNT(*) FROM bashar_slots').fetchone()[0]>=limit: continue
                        c.execute('INSERT INTO bashar_slots VALUES(?,?)',(item['source_id'],now()))
                c.execute("UPDATE jobs SET status='running',attempts=attempts+1,owner=?,lease_until=?,reservation_bytes=? WHERE job_id=?",(owner,time.time()+lease_seconds,CAPS[kind],job['job_id']))
                return dict(c.execute('SELECT * FROM jobs WHERE job_id=?',(job['job_id'],)).fetchone())
        return None
    def expire_leases(self):
        # Never reclaim a possibly live process/reservation automatically.
        with self.connect() as c:
            c.execute("UPDATE jobs SET status='expired_held',error='expired_lease_requires_operator_process_and_quarantine_review' WHERE status='running' AND lease_until<?",(time.time(),))
    def finish(self,job,owner,artifacts,error=None):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); current=c.execute('SELECT * FROM jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            if current['status']!='running' or current['owner']!=owner or current['lease_until']<time.time(): raise ValueError('Stale/foreign worker cannot finalize')
            if not error and not artifacts: raise ValueError('Successful completion requires verified output files')
            if not error and (sum(Path(a['path']).stat().st_size for a in artifacts)>current['reservation_bytes'] or tree_bytes(self.budget_root)>self.quota or shutil.disk_usage(self.budget_root).free<self.reserve_free): raise ValueError('Final artifact/shared-budget reservation check failed')
            for artifact in artifacts:
                path=Path(artifact['path']).resolve()
                if not path.is_relative_to(self.raw/'quarantine') or path.is_symlink() or not path.is_file(): raise ValueError('Output must remain inside private quarantine')
                c.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',(str(path.relative_to(self.raw)),job['source_id'],job['kind'],path.stat().st_size,sha(path),encoded(artifact['validation']),'verified_quarantine'))
            c.execute("UPDATE jobs SET status=?,error=?,owner=NULL,lease_until=NULL,reservation_bytes=0 WHERE job_id=?",('failed_no_retry' if error else 'verified_quarantine',error,job['job_id']))
    def export(self):
        with self.connect() as c:
            jobs=[dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY job_id')]; items={r['source_id']:r for r in c.execute('SELECT * FROM items')}
            slots=c.execute('SELECT COUNT(*) FROM bashar_slots').fetchone()[0]; policy=self.setting(c,'policy',{})
            artifacts=c.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]
        plan=[]
        for job in jobs:
            reasons=[] if job['kind']=='metadata' else self.reasons(items[job['source_id']])
            plan.append({'job_id':job['job_id'],'source_id':job['source_id'],'kind':job['kind'],'status':job['status'],
                         'attempts':job['attempts'],'reservation_bytes':job['reservation_bytes'],'asset_holds':reasons,
                         'network_release':'requires_successful_real_same_current_configuration_watch_probe'})
        return {'summary':{'schema_version':1,'policy':policy,'items':len(items),'jobs':len(jobs),'by_kind':dict(Counter(j['kind'] for j in jobs)),
                           'by_status':dict(Counter(j['status'] for j in jobs)),'attempts':sum(j['attempts'] for j in jobs),
                           'bashar_unique_youtube_slots_used':slots,'verified_quarantine_artifacts':artifacts,'automatic_retries':0},'jobs':plan}

def tool_version(python):
    version=subprocess.check_output([str(python),'-I','-c','import importlib.metadata;print(importlib.metadata.version("yt-dlp"))'],text=True).strip()
    if version!=PINNED_YTDLP: raise ValueError('yt-dlp version differs from pinned '+PINNED_YTDLP)
    return version
def execute_one(store,args):
    gate=store.gate(args.runtime_receipt)
    if not gate['ready']: return {'status':'blocked_before_claim_or_network','gate':gate,'network_collection_requests':0}
    tool_version(args.yt_python)
    owner=uuid.uuid4().hex; job=store.claim(args.kind,owner,gate['fingerprint'],source_id=getattr(args,'source_id',None))
    if not job: return {'status':'no_eligible_or_capacity_available_job','gate':gate}
    vid=job['source_id'].split(':',1)[1]; folder=store.raw/'quarantine'/vid/args.kind/owner; folder.mkdir(parents=True)
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    command=[str(args.yt_python),'-m','yt_dlp','--ignore-config','--no-cache-dir','--no-playlist','--proxy',proxy,
             '--compat-options','no-certifi','--retries','0','--fragment-retries','0','--extractor-retries','0',
             '--socket-timeout','25','--max-filesize',str(CAPS[args.kind]),'--write-info-json','-o',str(folder/(vid+'.%(ext)s'))]
    if args.kind=='metadata': command+=['--skip-download']
    elif args.kind=='captions': command+=['--skip-download','--write-subs','--write-auto-subs','--sub-langs','en.*','--sub-format','vtt']
    else: command+=['--match-filter','duration >= 300','-f','ba/b' if args.kind=='audio' else 'bv*[height<=720]+ba/b[height<=720]/b']
    if args.kind=='metadata': command+=['https://www.youtube.com/watch?v='+vid]
    else:
        # Freeze the exact freshly checked metadata, including title/description/tags and source ID,
        # before the cap reservation. Do not silently re-extract changed identity during media acquisition.
        with store.connect() as c:item=c.execute('SELECT * FROM items WHERE source_id=?',(job['source_id'],)).fetchone()
        command+=['--load-info-json',item['metadata_path']]
    error=None; artifacts=[]; child=None
    try:
        with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
            with store.connect() as c:c.execute('UPDATE jobs SET child_pid=? WHERE job_id=? AND owner=?',(child.pid,job['job_id'],owner))
            start=time.monotonic()
            while child.poll() is None:
                if time.monotonic()-start>480 or tree_bytes(folder)>CAPS[args.kind] or shutil.disk_usage(store.raw).free<store.reserve_free:
                    os.killpg(child.pid,signal.SIGTERM)
                    try: child.wait(timeout=10)
                    except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=10)
                    raise ValueError('Runtime/byte/free-space limit')
                time.sleep(.2)
            if child.returncode: raise ValueError('yt-dlp failed; private stderr retained, no automatic retry')
        if tree_bytes(folder)>CAPS[args.kind] or tree_bytes(store.budget_root)>store.quota or shutil.disk_usage(store.budget_root).free<store.reserve_free: raise ValueError('Final folder/shared-byte/free-space limit')
        info=folder/(vid+'.info.json'); metadata=json.loads(info.read_text())
        if metadata.get('id')!=vid: raise ValueError('Output ID mismatch')
        update=store.metadata_result(job['source_id'],metadata,info)
        if args.kind!='metadata':
            with store.connect() as c:item=c.execute('SELECT * FROM items WHERE source_id=?',(job['source_id'],)).fetchone()
            if store.reasons(item): raise ValueError('Post-acquisition metadata changed eligibility; quarantine retained')
            # Reclassified-other -> Bashar must never bypass global cap at output validation.
            if update['classification']=='bashar':
                with store.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if not c.execute('SELECT 1 FROM bashar_slots WHERE source_id=?',(job['source_id'],)).fetchone():
                        limit=store.setting(c,'policy')['bashar_limit']
                        if c.execute('SELECT COUNT(*) FROM bashar_slots').fetchone()[0]>=limit: raise ValueError('Fresh output reclassified Bashar and cap full; quarantine retained')
                        c.execute('INSERT INTO bashar_slots VALUES(?,?)',(job['source_id'],now()))
        outputs=[info] if args.kind=='metadata' else [p for p in folder.iterdir() if p.suffix=='.vtt'] if args.kind=='captions' else [p for p in folder.iterdir() if p.suffix.lower() in {'.mp4','.webm','.mkv','.m4a','.opus','.mp3'}]
        if not outputs: raise ValueError('No requested complete output; missing captions are not a success')
        for path in outputs:
            validation={'source_video_id':vid,'metadata_sha256':sha(info),'tls_verification':True,'proxy':'explicit_inherited','quarantine_only':True}
            if args.kind=='captions':
                if not path.read_bytes().lstrip().startswith(b'WEBVTT'): raise ValueError('Invalid WebVTT')
                if not re.search(rb'\d{2}:\d{2}(?::\d{2})?\.\d{3}\s+-->\s+\d{2}:\d{2}(?::\d{2})?\.\d{3}',path.read_bytes()): raise ValueError('WebVTT has no timestamped cues')
            elif args.kind in ('video','audio'):
                parsed=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(path)],text=True))
                duration=float(parsed['format']['duration'])
                if not math.isfinite(duration) or duration<300 or not math.isclose(duration,float(metadata['duration']),abs_tol=5,rel_tol=.02): raise ValueError('Measured output duration fails >=300s/source-metadata match')
                expected_stream='video' if args.kind=='video' else 'audio'
                if not any(s.get('codec_type')==expected_stream for s in parsed.get('streams',[])): raise ValueError('Requested media stream is absent')
                validation['ffprobe_duration_seconds']=duration
            artifacts.append({'path':str(path),'validation':validation})
    except Exception as caught:
        error=type(caught).__name__+': '+str(caught)
        # Public errors contain no downloader logs, proxy URI or signed source endpoints.
        if proxy: error=error.replace(proxy,'[proxy-redacted]')
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=10)
        # A changed access/extractor failure pauses all future claims, not just this source.
        store.block_gate(args.runtime_receipt,'bounded_operation_failed_requires_diagnosis_not_bulk_retry')
    store.finish(job,owner,artifacts if not error else [],error)
    return {'status':'failed_no_retry' if error else 'verified_quarantine','job_id':job['job_id'],'error':error,'artifact_count':len(artifacts) if not error else 0}

def execute_bounded(store,args):
    gate=store.gate(args.runtime_receipt)
    if not gate['ready']: return {'status':'blocked_before_claim_or_network','gate':gate,'network_collection_requests':0}
    if not 1<=args.workers<=2 or not 1<=args.max_jobs<=3000: raise ValueError('Bounded run requires1-2workers and1-3000maximum job invocations')
    with store.connect() as c:
        sources=[r[0] for r in c.execute("SELECT source_id FROM jobs WHERE kind='metadata' AND status='queued' AND attempts=0 ORDER BY source_id")]
    lock=threading.Lock(); stop=threading.Event(); remaining=args.max_jobs; results=[]
    def per_source(source):
        nonlocal remaining
        for kind in ('metadata','captions','video'):
            with lock:
                if stop.is_set() or remaining<=0: return
                remaining-=1
            local=argparse.Namespace(**vars(args)); local.kind=kind; local.source_id=source
            result=execute_one(store,local)
            with lock: results.append(result)
            if result['status'] in ('failed_no_retry','blocked_before_claim_or_network'): stop.set(); return
    # Per-source metadata->assets scheduling avoids a942-metadata-first stale-cache phase.
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for _ in pool.map(per_source,sources): pass
    return {'status':'bounded_execution_stopped' if stop.is_set() else 'bounded_execution_finished',
            'max_job_invocations':args.max_jobs,'workers':args.workers,'results':results,'summary':store.export()['summary']}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--database',type=Path,default=Path('/workspace/channels-et-raw/collection-runner/state.sqlite'))
    p.add_argument('--raw',type=Path,default=Path('/workspace/channels-et-raw/collection-runner')); p.add_argument('--budget-root',type=Path,default=Path('/workspace/channels-et-raw')); p.add_argument('--quota-bytes',type=int,default=20*1024**3)
    p.add_argument('--reserve-free-bytes',type=int,default=6*1024**3)
    sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init'); init.add_argument('--selection',type=Path,default=ROOT/'research/collection-policy/selection.jsonl'); init.add_argument('--policy',type=Path,default=ROOT/'research/collection-policy/policy.json'); init.add_argument('--conservative-all-materials',action='store_true'); init.add_argument('--blocked-probe',type=Path); init.add_argument('--runtime-receipt',type=Path)
    plan=sub.add_parser('plan'); plan.add_argument('--output',type=Path,default=HERE)
    dry=sub.add_parser('dry-run'); dry.add_argument('--runtime-receipt',type=Path,required=True)
    discovery=sub.add_parser('import-discovery'); discovery.add_argument('--input',type=Path,required=True)
    review=sub.add_parser('review'); review.add_argument('--source-id',required=True); review.add_argument('--evidence',type=Path,required=True)
    refresh=sub.add_parser('refresh-metadata'); refresh.add_argument('--source-id',required=True); refresh.add_argument('--reason',required=True)
    probe=sub.add_parser('probe'); probe.add_argument('--runtime-receipt',type=Path,required=True); probe.add_argument('--video-id',required=True)
    run=sub.add_parser('run-one'); run.add_argument('--runtime-receipt',type=Path,required=True); run.add_argument('--kind',choices=tuple(CAPS),required=True); run.add_argument('--yt-python',type=Path,default=Path('/workspace/channels-et-harvest-venv/bin/python'))
    batch=sub.add_parser('run-bounded'); batch.add_argument('--runtime-receipt',type=Path,required=True); batch.add_argument('--max-jobs',type=int,required=True); batch.add_argument('--workers',type=int,default=2); batch.add_argument('--yt-python',type=Path,default=Path('/workspace/channels-et-harvest-venv/bin/python'))
    sub.add_parser('expire-leases')
    args=p.parse_args(); store=Store(args.database,args.raw,args.quota_bytes,args.reserve_free_bytes,args.budget_root)
    if args.command=='init': result=store.initialize(args.selection,args.policy,args.conservative_all_materials,args.blocked_probe,args.runtime_receipt)['summary']
    elif args.command=='plan':
        result=store.export(); save(args.output/'plan-summary.json',result['summary']); (args.output/'plan.jsonl').write_text(''.join(encoded(r)+'\n' for r in result['jobs'])); result=result['summary']
    elif args.command=='dry-run': result={'status':'offline_only','gate':store.gate(args.runtime_receipt),'plan':store.export()['summary'],'network_collection_requests':0}
    elif args.command=='import-discovery': result=store.import_discovery(args.input)
    elif args.command=='review': store.review(args.source_id,args.evidence); result={'status':'source_bound_review_recorded'}
    elif args.command=='refresh-metadata': store.refresh_metadata(args.source_id,args.reason); result={'status':'single_metadata_refresh_queued_no_network'}
    elif args.command=='probe': result=store.probe(args.runtime_receipt,args.video_id)
    elif args.command=='expire-leases': store.expire_leases(); result={'status':'expired_reservations_held_not_retried'}
    else:
        with collection_lock(store.budget_root): result=execute_bounded(store,args) if args.command=='run-bounded' else execute_one(store,args)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
