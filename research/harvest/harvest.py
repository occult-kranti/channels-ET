#!/usr/bin/env python3
"""Source-aware harvest queue. Public state contains metadata, never raw media/text.

init/export are offline. run refuses a denied/unsuccessful access receipt before
claiming any item. SQLite leases deduplicate concurrent processes; byte reservations
and post-validation protect the external raw directory. No alternate egress exists.
"""
from __future__ import annotations
import argparse, concurrent.futures, contextlib, datetime as dt, fcntl, hashlib, importlib.metadata
import json, math, os, pathlib, re, shutil, signal, sqlite3, subprocess, sys, threading, time
import urllib.parse

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEFAULT_RAW=pathlib.Path('/workspace/channels-et-raw')
MEDIA_EXT={'.mp4','.webm','.mkv','.m4a','.mp3','.opus','.ogg','.wav','.aac','.flac','.mov'}
DENIAL=re.compile(r'Tunnel connection failed:\s*403|proxy.?tunnel.{0,30}denied|blocked_by_policy|destination.{0,20}not allowed|egress.{0,20}denied',re.I)

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def dump(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
 return h.hexdigest()
def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+f'.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp')
 temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.replace(path)
def sanitize(value):
 value=re.sub(r'(https?://)[^/@\s]+:[^/@\s]+@',r'\1[redacted]@',str(value))
 value=re.sub(r'(https?://[^?\s]+)\?[^\s]+',r'\1?[query-redacted]',value)
 return re.sub(r'(?i)(authorization|cookie|token|password|signature)(\s*[:=]\s*)[^\s,;]+',r'\1\2[redacted]',value)[-1400:]
def inside_git(path):
 for parent in (path.resolve(),*path.resolve().parents):
  p=parent/'.git'
  if p.is_dir() and (p/'HEAD').is_file():return True
  if p.is_file() and p.read_text().strip().startswith('gitdir:'):return True
 return False
def tree_bytes(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file() and not p.is_symlink()) if path.exists() else 0
def safe_raw(path):
 if inside_git(path):raise ValueError('Raw source data must stay outside all real Git checkouts')
 path.mkdir(parents=True,exist_ok=True);return path.resolve()
@contextlib.contextmanager
def collection_lock(raw):
 path=raw/'.collection-worker.lock'
 with path.open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another collection writer holds the shared raw-directory lock')
  try:yield
  finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
def valid_id(value):return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{11}',value))
def source_rows(path,keys):
 if path.suffix=='.jsonl':return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
 data=json.loads(path.read_text())
 if isinstance(data,list):return data
 for key in keys:
  if key in data:return data[key]
 raise ValueError('Input requires a records/list field: '+str(path))
def youtube_url(url):
 p=urllib.parse.urlsplit(url)
 return p.scheme=='https' and p.hostname in {'youtube.com','www.youtube.com','m.youtube.com','youtu.be'} and not p.username and not p.password
def route_key(url):return hashlib.sha256(url.rstrip('/').encode()).hexdigest()[:24]

class Store:
 def __init__(self,path,raw=DEFAULT_RAW,quota=20*1024**3,reserve=6*1024**3):
  self.path=path;self.raw=safe_raw(raw);self.quota=quota;self.reserve=reserve
  path.parent.mkdir(parents=True,exist_ok=True)
  with self.connect() as c:
   c.executescript('''PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS videos(video_id TEXT PRIMARY KEY,source_url TEXT NOT NULL,title TEXT,duration_seconds REAL,input_json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS video_sources(video_id TEXT NOT NULL REFERENCES videos(video_id),input_sha256 TEXT NOT NULL,input_json TEXT NOT NULL,
      PRIMARY KEY(video_id,input_sha256));
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,target_id TEXT NOT NULL,source_url TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued',attempt_count INTEGER NOT NULL DEFAULT 0,next_attempt REAL NOT NULL DEFAULT 0,
      lease_owner TEXT,lease_until REAL,child_pid INTEGER,child_start TEXT,reservation_bytes INTEGER NOT NULL DEFAULT 0,
      cursor_start INTEGER NOT NULL DEFAULT 1,listing_end INTEGER NOT NULL DEFAULT 0,input_json TEXT NOT NULL DEFAULT '{}',
      result_json TEXT,error_class TEXT,error TEXT,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),attempt_no INTEGER NOT NULL,
      started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,error_class TEXT,error TEXT,result_json TEXT,
      UNIQUE(job_id,attempt_no));
    CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),video_id TEXT,
      type TEXT NOT NULL,raw_relative_path TEXT NOT NULL UNIQUE,bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,
      complete INTEGER NOT NULL,language_code TEXT,is_generated INTEGER,details_json TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS channel_edges(parent_job_id TEXT NOT NULL,child_job_id TEXT NOT NULL,
      PRIMARY KEY(parent_job_id,child_job_id));
    CREATE TABLE IF NOT EXISTS discovery(route_job_id TEXT NOT NULL,video_id TEXT NOT NULL,metadata_json TEXT NOT NULL,
      PRIMARY KEY(route_job_id,video_id));
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS job_queue ON jobs(status,next_attempt,kind);
   ''')
   columns={r[1] for r in c.execute('PRAGMA table_info(artifacts)')}
   if 'mtime_ns' not in columns:c.execute('ALTER TABLE artifacts ADD COLUMN mtime_ns INTEGER')
 def connect(self):
  c=sqlite3.connect(self.path,timeout=60);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
 def put(self,key,value):
  with self.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,dump(value)))
 def get(self,key,default=None):
  with self.connect() as c:r=c.execute('SELECT value_json FROM settings WHERE key=?',(key,)).fetchone()
  return json.loads(r[0]) if r else default
 def add_job(self,c,kind,target,url,meta=None):
  key=kind+':'+target
  c.execute('INSERT OR IGNORE INTO jobs(id,kind,target_id,source_url,input_json,updated_at) VALUES(?,?,?,?,?,?)',
            (key,kind,target,url,dump(meta or {}),now()));return key
 def add_video(self,c,row):
  vid=row.get('video_id',row.get('id'))
  if not valid_id(vid):return False
  url='https://www.youtube.com/watch?v='+vid
  duration=row.get('duration_seconds',row.get('durationSeconds'))
  if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:duration=None
  c.execute('INSERT OR IGNORE INTO videos VALUES(?,?,?,?,?)',(vid,url,row.get('title'),duration,dump(row)))
  c.execute('INSERT OR IGNORE INTO video_sources VALUES(?,?,?)',(vid,hashlib.sha256(dump(row).encode()).hexdigest(),dump(row)))
  for kind in ('metadata','captions','video'):self.add_job(c,kind,vid,url,row)
  return True
 def initialize(self,videos,channels=None,playlists=None):
  with self.connect() as c:
   for row in source_rows(videos,('videos','records','captions')):self.add_video(c,row)
   if channels:
    for row in source_rows(channels,('records','channels','routes','accounts')):
     url=row.get('url',row.get('source_url'))
     if url and youtube_url(url):self.add_job(c,'channel',route_key(url),url,row)
   if playlists:
    for row in source_rows(playlists,('records','playlists')):
     url=row.get('url') or row.get('source_url')
     if url and youtube_url(url):self.add_job(c,'playlist',route_key(url),url,row)
  self.put('inventory_sources',{'videos':str(videos),'videos_sha256':sha(videos),'channels':str(channels) if channels else None,
                                'channels_sha256':sha(channels) if channels else None,'playlists':str(playlists) if playlists else None,
                                'playlists_sha256':sha(playlists) if playlists else None,'imported_at':now()})
 def job_dir(self,job):return self.raw/job['kind']/job['target_id']
 def capacity(self,c,cap,job=None):
  running=c.execute("SELECT * FROM jobs WHERE status='running'").fetchall()
  physical=tree_bytes(self.raw)
  outstanding=sum(max(0,r['reservation_bytes']-tree_bytes(self.job_dir(r))) for r in running)
  existing=tree_bytes(self.job_dir(job)) if job else 0
  needed=max(0,cap-existing)
  return existing<=cap and physical+outstanding+needed<=self.quota and shutil.disk_usage(self.raw).free-outstanding-needed>=self.reserve
 def claim(self,owner,kind,caps,timeout,max_attempts=3):
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   parent_filter=" AND EXISTS(SELECT 1 FROM jobs AS parent WHERE parent.id='metadata:'||jobs.target_id AND parent.status='succeeded')" if kind=='video' else ''
   candidates=c.execute("SELECT * FROM jobs WHERE kind=? AND status IN ('queued','retryable','disk_wait','partial') AND next_attempt<=? AND attempt_count<?"+parent_filter+" ORDER BY attempt_count,id LIMIT 100",(kind,time.time(),max_attempts)).fetchall()
   for job in candidates:
    if kind=='video':
     parent=c.execute('SELECT status FROM jobs WHERE id=?',('metadata:'+job['target_id'],)).fetchone()
     if not parent or parent[0]!='succeeded':continue
    cap=caps[kind]
    if not self.capacity(c,cap,job):
     c.execute("UPDATE jobs SET status='disk_wait',error_class='storage_reservation_unavailable',updated_at=? WHERE id=?",(now(),job['id']));continue
    attempt=job['attempt_count']+1
    c.execute("UPDATE jobs SET status='running',attempt_count=?,lease_owner=?,lease_until=?,reservation_bytes=?,child_pid=NULL,child_start=NULL,updated_at=? WHERE id=?",
              (attempt,owner,time.time()+timeout+60,cap,now(),job['id']))
    c.execute("INSERT INTO attempts(job_id,attempt_no,started_at,status) VALUES(?,?,?,'running')",(job['id'],attempt,now()))
    return dict(c.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone())
  return None
 def child(self,job,pid):
  try:start=pathlib.Path('/proc')/str(pid)/'stat';start=start.read_text().split()[21]
  except (OSError,IndexError):start=None
  with self.connect() as c:c.execute('UPDATE jobs SET child_pid=?,child_start=? WHERE id=? AND lease_owner=?',(pid,start,job['id'],job['lease_owner']))
 def renew(self,job,timeout):
  with self.connect() as c:c.execute("UPDATE jobs SET lease_until=? WHERE id=? AND lease_owner=? AND status='running'",(time.time()+timeout+60,job['id'],job['lease_owner']))
 def finish(self,job,result,artifacts=()):
  status=result['status'];retry=time.time()+min(1800,60*2**min(job['attempt_count']-1,4)) if status in ('retryable','partial') else 0
  required={'metadata':'metadata','video':'video','audio':'audio','captions':'caption'}.get(job['kind'])
  if status=='succeeded' and required and not any(a.get('type')==required and a.get('complete') for a in artifacts):
   raise ValueError('Successful source job requires an actual complete artifact of the correct type')
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   owner=c.execute('SELECT lease_owner,status FROM jobs WHERE id=?',(job['id'],)).fetchone()
   if not owner or owner['lease_owner']!=job['lease_owner'] or owner['status']!='running':raise RuntimeError('Lease owner changed; refusing stale completion')
   for a in artifacts:
    path=pathlib.Path(a['path']).resolve()
    if not path.is_relative_to(self.raw) or not path.is_file():raise ValueError('Artifact absent/outside external raw root')
    c.execute('INSERT OR REPLACE INTO artifacts(job_id,video_id,type,raw_relative_path,bytes,sha256,complete,language_code,is_generated,details_json,created_at,mtime_ns) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
      (job['id'],job['target_id'] if valid_id(job['target_id']) else None,a['type'],str(path.relative_to(self.raw)),path.stat().st_size,sha(path),
       int(a.get('complete',False)),a.get('language_code'),a.get('is_generated'),dump(a.get('details',{})),now(),path.stat().st_mtime_ns))
   c.execute("UPDATE jobs SET status=?,next_attempt=?,lease_owner=NULL,lease_until=NULL,child_pid=NULL,child_start=NULL,reservation_bytes=0,result_json=?,error_class=?,error=?,updated_at=? WHERE id=?",
             (status,retry,dump(result),result.get('error_class'),result.get('error'),now(),job['id']))
   c.execute('UPDATE attempts SET status=?,finished_at=?,error_class=?,error=?,result_json=? WHERE job_id=? AND attempt_no=?',
             (status,now(),result.get('error_class'),result.get('error'),dump(result),job['id'],job['attempt_count']))
   if job['kind'] in ('channel','playlist') and status=='succeeded':
    consumed=result['returned_slots'];end=result['listing_end']
    c.execute('UPDATE jobs SET cursor_start=cursor_start+?,listing_end=?,status=? WHERE id=?',(consumed,int(end),'succeeded' if end else 'queued',job['id']))
    for item in result.get('videos',[]):
     self.add_video(c,item);c.execute('INSERT OR IGNORE INTO discovery VALUES(?,?,?)',(job['id'],item['video_id'],dump(item)))
    for url in result.get('containers',[]):
     kind='playlist' if urllib.parse.urlsplit(url).path.rstrip('/')=='/playlist' else 'channel'
     child=self.add_job(c,kind,route_key(url),url,{'parent_job':job['id'],'relation':'returned_nested_public_container'})
     if child!=job['id']:c.execute('INSERT OR IGNORE INTO channel_edges VALUES(?,?)',(job['id'],child))
   if job['kind']=='video' and result.get('fallback_audio'):
    self.add_job(c,'audio',job['target_id'],job['source_url'],{'fallback_for':job['id'],'reason':result.get('error_class')})
 def recover(self):
  recovered=[];held=[]
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   for job in c.execute("SELECT * FROM jobs WHERE status='running' AND lease_until<?",(time.time(),)).fetchall():
    alive=False
    owner=(job['lease_owner'] or '').split(':')
    if len(owner)>=2:
     try:alive=(pathlib.Path('/proc')/owner[0]/'stat').read_text().split()[21]==owner[1]
     except (OSError,IndexError):pass
    if job['child_pid']:
     try:alive=alive or (pathlib.Path('/proc')/str(job['child_pid'])/'stat').read_text().split()[21]==job['child_start']
     except (OSError,IndexError):pass
    if alive:held.append(job['id']);continue
    c.execute("UPDATE jobs SET status='retryable',lease_owner=NULL,lease_until=NULL,reservation_bytes=0,child_pid=NULL,child_start=NULL,error_class='recovered_expired_lease',updated_at=? WHERE id=?",(now(),job['id']))
    c.execute("UPDATE attempts SET status='interrupted',finished_at=? WHERE job_id=? AND attempt_no=?",(now(),job['id'],job['attempt_count']));recovered.append(job['id'])
  return {'recovered':recovered,'held_live_children':held}
 def reconcile_artifacts(self,full_hash=False):
  invalid=[]
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   for a in c.execute('SELECT * FROM artifacts WHERE complete=1').fetchall():
    path=self.raw/a['raw_relative_path'];reason=None
    if not path.is_file() or path.is_symlink():reason='missing_or_symlinked_artifact'
    elif path.stat().st_size!=a['bytes']:reason='artifact_size_changed'
    elif full_hash or a['mtime_ns']!=path.stat().st_mtime_ns:
     if sha(path)!=a['sha256']:reason='artifact_hash_changed'
     else:c.execute('UPDATE artifacts SET mtime_ns=? WHERE id=?',(path.stat().st_mtime_ns,a['id']))
    if reason:
     details=json.loads(a['details_json']);details['revalidation']={'status':reason,'checked_at':now()}
     c.execute('UPDATE artifacts SET complete=0,details_json=? WHERE id=?',(dump(details),a['id']))
     c.execute("UPDATE jobs SET status='retryable',next_attempt=0,error_class=?,updated_at=? WHERE id=? AND status IN ('succeeded','partial')",(reason,now(),a['job_id']))
     invalid.append({'job_id':a['job_id'],'path':a['raw_relative_path'],'reason':reason})
  return invalid
 def export(self,out):
  self.reconcile_artifacts()
  with self.connect() as c:
   jobs=[dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY kind,id')]
   attempts=[dict(r) for r in c.execute('SELECT * FROM attempts ORDER BY id')]
   artifacts=[dict(r) for r in c.execute('SELECT * FROM artifacts ORDER BY id')]
   edges=[dict(r) for r in c.execute('SELECT * FROM channel_edges')]
   video_count=c.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
  counts={}
  for j in jobs:
   counts.setdefault(j['kind'],{}).setdefault(j['status'],0);counts[j['kind']][j['status']]+=1
  children={}
  for edge in edges:children.setdefault(edge['parent_job_id'],[]).append(edge['child_job_id'])
  byid={j['id']:dict(j) for j in jobs}
  def complete(key,seen=None):
   seen=set() if seen is None else seen
   if key in seen:return True
   result=json.loads(byid[key]['result_json']) if byid[key]['result_json'] else {}
   return bool(byid[key]['listing_end']) and not result.get('unresolved_inline_containers') and all(complete(child,seen|{key}) for child in children.get(key,[]))
  for j in jobs:
   j['actual_speaker_status']='unknown_not_audio_verified'
   if j['kind'] in ('channel','playlist'):j['complete_returned_public_listing_tree']=complete(j['id'])
   for k in ('input_json','result_json'):
    j[k.removesuffix('_json')]=json.loads(j.pop(k)) if j[k] else None
  summary={'schema_version':1,'updated_at':now(),'access_gate':self.get('access_gate',{'status':'not_checked'}),
    'inventory':{'videos':video_count,'channel_jobs':sum(j['kind']=='channel' for j in jobs),'playlist_jobs':sum(j['kind']=='playlist' for j in jobs)},'counts_by_kind':counts,
    'attempts_total':len(attempts),'artifacts_by_type':{t:sum(a['type']==t and (a['complete'] or t in ('partial','quarantine')) for a in artifacts) for t in ('video','audio','caption','metadata','partial','quarantine')},
    'raw_bytes':tree_bytes(self.raw),'quota_bytes':self.quota,'reserve_free_bytes':self.reserve,'filesystem_free_bytes':shutil.disk_usage(self.raw).free,
    'channel_listing_trees_complete':sum(j['kind']=='channel' and j.get('complete_returned_public_listing_tree',False) for j in jobs),
    'playlist_listing_trees_complete':sum(j['kind']=='playlist' and j.get('complete_returned_public_listing_tree',False) for j in jobs),
    'completeness_scope':'Returned public listing and expanded containers only, not private/deleted/uploads absent from response or verified original sessions',
    'run_status':self.get('run_status','prepared_not_executed')}
  save(out/'summary.json',summary)
  for name,rows in [('jobs',jobs),('attempts',attempts),('artifacts',artifacts)]:save(out/(name+'.json'),{'schema_version':1,'records':rows})
  return summary

def access_gate(path):
 if path is None:return {'status':'not_checked','reason':'A current successful ordinary watch probe is required'}
 data=json.loads(path.read_text());error=str(data.get('error',''))
 if data.get('proxyTunnelDenied') or DENIAL.search(error):return {'status':'blocked','reason':'explicit_proxy_tunnel_denial','probe_path':str(path),'probe_sha256':sha(path),'probe':data}
 rows=data.get('records',[data]);success=bool(rows) and all(r.get('status')=='success' and r.get('http_status',r.get('httpStatus',200))==200 for r in rows)
 if not success:return {'status':'blocked','reason':'ordinary_access_not_successful','probe_path':str(path),'probe_sha256':sha(path),'probe':data}
 timestamp=data.get('checkedAt') or data.get('finished_at') or rows[0].get('retrieved_at')
 try:age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(timestamp)).total_seconds()
 except (TypeError,ValueError):age=math.inf
 if age< -300 or age>24*3600:return {'status':'not_checked','reason':'probe_timestamp_missing_or_stale','probe_path':str(path)}
 return {'status':'ready_for_bounded_pilot','reason':'ordinary_public_watch_probe_succeeded_not_all_routes','probe_path':str(path),'probe_sha256':sha(path),'observed_at_epoch':dt.datetime.fromisoformat(timestamp).timestamp()}

def classify(error,attempt,max_attempts):
 text=str(error);clean=sanitize(text)
 if DENIAL.search(text):return {'status':'blocked','error_class':'network_policy_or_proxy_tunnel_denial','error':clean,'global_stop':True}
 if re.search(r'429|Too Many Requests',text,re.I):return {'status':'retryable' if attempt<max_attempts else 'blocked','error_class':'rate_limited','error':clean,'reduce_concurrency':True}
 if re.search(r'403|Forbidden|RequestBlocked|IpBlocked|CAPTCHA|sign in to confirm',text,re.I):return {'status':'blocked','error_class':'source_access_denied','error':clean,'global_stop':True}
 if re.search(r'exceeds? max.filesize|larger than|file is larger|Requested format is not available|no suitable formats',text,re.I):return {'status':'unavailable','error_class':'media_size_or_format_limit','error':clean,'fallback_audio':True}
 if re.search(r'private video|video unavailable|members.only|not available|copyright|not found|subtitlesdisabled|notranscriptfound|transcriptsdisabled',text,re.I):return {'status':'unavailable','error_class':'source_unavailable','error':clean}
 if isinstance(error,subprocess.TimeoutExpired) or re.search(r'timed out|timeout|HTTP Error 50[234]|temporar',text,re.I):return {'status':'retryable' if attempt<max_attempts else 'failed','error_class':'transient_transport_or_timeout','error':clean}
 return {'status':'failed','error_class':type(error).__name__,'error':clean}

class Worker:
 def __init__(self,store,args):self.store=store;self.args=args;self.stop=threading.Event();self.reduce=False
 def base(self):return [sys.executable,'-m','yt_dlp','--ignore-config','--no-cache-dir','--no-warnings','--retries','0','--fragment-retries','0','--extractor-retries','0','--socket-timeout','25','--js-runtimes','node']
 def run_child(self,job,command,limit):
  raw=self.store.job_dir(job);raw.mkdir(parents=True,exist_ok=True)
  output=raw/'stdout.log';error=raw/'stderr.log';started=time.monotonic();reason=None
  with output.open('wb') as o,error.open('wb') as e:
   child=subprocess.Popen(command,stdout=o,stderr=e,start_new_session=True);self.store.child(job,child.pid)
   try:
    while child.poll() is None:
     if self.stop.is_set():reason='stopped_after_access_denial'
     elif tree_bytes(self.store.raw)>self.store.quota or shutil.disk_usage(self.store.raw).free<self.store.reserve or tree_bytes(raw)>limit:reason='storage_limit'
     elif time.monotonic()-started>self.args.timeout:reason='operation_timeout'
     if reason:
      os.killpg(child.pid,signal.SIGTERM);break
     time.sleep(.25)
    try:code=child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
   finally:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
  if tree_bytes(self.store.raw)>self.store.quota or shutil.disk_usage(self.store.raw).free<self.store.reserve or tree_bytes(raw)>limit:reason='storage_limit'
  message=sanitize(error.read_text(errors='replace'))
  if reason=='storage_limit':raise RuntimeError('HARVEST_STORAGE_LIMIT: '+str(raw))
  if reason=='stopped_after_access_denial':raise RuntimeError('HARVEST_CIRCUIT_STOP')
  if reason=='operation_timeout':raise subprocess.TimeoutExpired(command,self.args.timeout)
  if code:raise RuntimeError(message or 'yt-dlp exit '+str(code))
  return output
 def execute(self,job):
  artifacts=[];finished=threading.Event()
  def heartbeat():
   while not finished.wait(10):
    try:self.store.renew(job,self.args.timeout)
    except sqlite3.Error:pass
  pulse=threading.Thread(target=heartbeat,daemon=True);pulse.start()
  try:
   if self.stop.is_set():result={'status':'queued','error_class':'not_attempted_after_circuit_stop'}
   elif job['kind'] in ('channel','playlist'):result=self.channel(job)
   elif job['kind']=='metadata':result,artifacts=self.metadata(job)
   elif job['kind']=='captions':result,artifacts=self.captions(job)
   else:result,artifacts=self.media(job)
  except Exception as error:
   if 'HARVEST_STORAGE_LIMIT' in str(error):result={'status':'disk_wait','error_class':'storage_limit','error':sanitize(error),'fallback_audio':job['kind']=='video'}
   elif 'HARVEST_CIRCUIT_STOP' in str(error):result={'status':'retryable','error_class':'interrupted_after_other_request_denial'}
   else:result=classify(error,job['attempt_count'],self.args.max_attempts)
  if result.get('global_stop'):
   self.stop.set();self.store.put('last_access_denial',{'at_epoch':time.time(),'job_id':job['id'],'error_class':result.get('error_class'),'error':result.get('error')})
  if result.get('reduce_concurrency'):self.reduce=True
  if result['status'] not in ('succeeded','queued') and job['kind'] in ('video','audio'):
   raw=self.store.job_dir(job)
   artifacts.extend({'path':p,'type':'partial','complete':False,'details':{'not_certified_complete':True,'reason':result.get('error_class')}}
                    for p in raw.glob('*') if p.is_file() and p.suffix not in ('.log',) and not any(a['path']==p for a in artifacts))
  try:self.store.finish(job,result,artifacts)
  finally:finished.set();pulse.join(timeout=1)
  return result
 def metadata(self,job):
  command=self.base()+['--no-playlist','--skip-download','--dump-single-json',job['source_url']]
  output=self.run_child(job,command,job['reservation_bytes']);data=json.loads(output.read_text())
  if data.get('id')!=job['target_id']:raise ValueError('Metadata does not match requested upload ID')
  if data.get('is_live') or data.get('live_status') in ('is_live','is_upcoming'):return {'status':'unavailable','error_class':'live_or_upcoming_not_finite_media'},[]
  path=output.parent/'info.json';output.replace(path)
  selected={k:data.get(k) for k in ('id','title','duration','channel_id','channel','upload_date','timestamp','availability','live_status')}
  selected.update(status='succeeded',actual_speaker_status='unknown_not_audio_verified')
  return selected,[{'path':path,'type':'metadata','complete':True,'details':{'raw_info_contains_ephemeral_URLs':'external_only'}}]
 def channel(self,job):
  start=job['cursor_start'];size=self.args.channel_batch
  command=self.base()+['--skip-download','--flat-playlist','--dump-single-json','--playlist-start',str(start)]
  if size:command+=['--playlist-end',str(start+size-1)]
  output=self.run_child(job,command+[job['source_url']],job['reservation_bytes']);data=json.loads(output.read_text())
  slots=data.get('entries')
  if not isinstance(slots,list):raise ValueError('Channel response lacks returned entry slots')
  videos=[];containers=[];unresolved=[]
  def inspect(items,context,pointer):
   for index,item in enumerate(items):
    if not isinstance(item,dict):continue
    vid=item.get('id');url=item.get('url') or item.get('webpage_url')
    nested=item.get('entries');location=pointer+'/'+str(index)
    if isinstance(nested,list):
     child_context=url if isinstance(url,str) and youtube_url(url) else context
     inspect(nested,child_context,location+'/entries')
     if size and (not isinstance(url,str) or not youtube_url(url)):unresolved.append(location)
    if valid_id(vid):videos.append({'video_id':vid,'title':item.get('title'),'duration_seconds':item.get('duration'),'source_route':job['source_url'],
                                  'source_container':context,'response_pointer':location,'actual_speaker_status':'unknown_not_audio_verified'})
    elif isinstance(url,str) and youtube_url(url) and url.rstrip('/')!=job['source_url'].rstrip('/'):containers.append(url)
  inspect(slots,job['source_url'],'/entries')
  result={'status':'succeeded','returned_slots':len(slots),'usable_videos':len(videos),
    'unusable_or_container_slots':sum(not isinstance(s,dict) or not valid_id(s.get('id')) for s in slots),'unresolved_inline_containers':unresolved,
    'listing_end':size==0 or len(slots)<size,'videos':videos,'containers':sorted(set(containers)),
    'response_sha256':sha(output),'scope':'End of returned public listing only; inline and URL containers retained/expanded separately, not private/deleted/all-world channel completeness'}
  output.unlink();return result
 def captions(self,job):
  from requests import Session
  from youtube_transcript_api import YouTubeTranscriptApi
  class LimitedSession(Session):
   def request(self,*a,**kw):kw.setdefault('timeout',25);self.cookies.clear();return super().request(*a,**kw)
  started=time.monotonic();tracks=list(YouTubeTranscriptApi(http_client=LimitedSession()).list(job['target_id']));artifacts=[];failures=[];raw=self.store.job_dir(job);raw.mkdir(parents=True,exist_ok=True);reused=0;fetched=0
  with self.store.connect() as c:existing=[dict(a) for a in c.execute("SELECT * FROM artifacts WHERE job_id=? AND type='caption' AND complete=1",(job['id'],))]
  for i,track in enumerate(tracks):
   if self.stop.is_set():failures.append({'status':'retryable','error_class':'interrupted_after_other_request_denial'});break
   if time.monotonic()-started>self.args.timeout:failures.append({'status':'retryable','error_class':'caption_operation_timeout'});break
   try:
    old=next((a for a in existing if a['language_code']==track.language_code and bool(a['is_generated'])==track.is_generated and json.loads(a['details_json']).get('source_track_index')==i),None)
    if old and not getattr(self.args,'refresh_captions',False):
     oldpath=self.store.raw/old['raw_relative_path']
     if oldpath.is_file() and sha(oldpath)==old['sha256']:
      artifacts.append({'path':oldpath,'type':'caption','complete':True,'language_code':old['language_code'],'is_generated':bool(old['is_generated']),
                        'details':{**json.loads(old['details_json']),'reused_verified_local_track':True,'not_a_fresh_track_body_request':True}});reused+=1;continue
    data=track.fetch();document={'video_id':job['target_id'],'source_url':job['source_url'],'language_code':data.language_code,'is_generated':data.is_generated,'segments':data.to_raw_data(),'actual_speaker_status':'unknown_not_audio_verified'}
    fetched+=1;blob=json.dumps(document,ensure_ascii=False).encode()
    language=re.sub('[^A-Za-z0-9_-]','_',data.language_code);path=raw/f"{i:03d}-{language}-{'auto' if data.is_generated else 'manual'}-{hashlib.sha256(blob).hexdigest()[:12]}.json"
    incremental=0 if path.is_file() and sha(path)==hashlib.sha256(blob).hexdigest() else len(blob)
    if tree_bytes(raw)+incremental>job['reservation_bytes'] or tree_bytes(self.store.raw)+incremental>self.store.quota or shutil.disk_usage(self.store.raw).free-incremental<self.store.reserve:raise RuntimeError('HARVEST_STORAGE_LIMIT')
    if incremental:path.write_bytes(blob)
    artifacts.append({'path':path,'type':'caption','complete':True,'language_code':data.language_code,'is_generated':data.is_generated,'details':{'segments':len(document['segments']),'source_track_index':i}})
   except Exception as error:
    if 'HARVEST_STORAGE_LIMIT' in str(error):failures.append({'status':'disk_wait','error_class':'storage_limit'})
    else:failures.append(classify(error,job['attempt_count'],self.args.max_attempts))
    if failures[-1].get('global_stop'):self.stop.set()
    if failures[-1].get('global_stop') or failures[-1]['status']=='disk_wait':break
  status='succeeded' if tracks and len(artifacts)==len(tracks) else ('partial' if artifacts else ('unavailable' if not tracks else (failures[0]['status'] if failures else 'retryable')))
  result={'status':status,'offered_tracks':len(tracks),'saved_tracks':len(artifacts),'reused_verified_tracks':reused,'fresh_track_body_requests':fetched,
          'all_offered_tracks_saved':bool(tracks) and len(artifacts)==len(tracks),'track_coverage_scope':'Current offered descriptor slots covered by original retrieved or verified cached versions, not audio-verified or necessarily refetched bodies','failures':failures}
  if failures:
   dominant=next((f for f in failures if f.get('global_stop')),failures[0])
   result.update({k:v for k,v in dominant.items() if k!='status'})
  return result,artifacts
 def media(self,job):
  raw=self.store.job_dir(job);raw.mkdir(parents=True,exist_ok=True);audio=job['kind']=='audio'
  # yt-dlp can skip an existing completed filename. Only previously source-bound,
  # hash-verified artifacts may survive that shortcut; retain all others as audit
  # bytes outside the active job directory before the downloader can see them.
  verified={};quarantined=[]
  with self.store.connect() as c:
   for path in list(raw.iterdir()):
    if not path.is_file() or path.suffix.lower() not in MEDIA_EXT:continue
    relative=str(path.relative_to(self.store.raw));actual=sha(path)
    prior=c.execute('SELECT * FROM artifacts WHERE raw_relative_path=? AND job_id=?',(relative,job['id'])).fetchone()
    if prior and prior['complete'] and prior['type']==('audio' if audio else 'video') and prior['sha256']==actual and prior['bytes']==path.stat().st_size:
     verified[relative]=actual;continue
    reason='prior_media_integrity_changed' if prior else 'unbound_completed_media_file'
    destination=self.store.raw/'quarantine'/job['kind']/job['target_id']/str(time.time_ns())/path.name
    destination.parent.mkdir(parents=True,exist_ok=True);path.replace(destination)
    details={'reason':reason,'original_raw_relative_path':relative,'prior_sha256':prior['sha256'] if prior else None,
             'observed_sha256':actual,'source_url':job['source_url'],'not_a_fresh_download':True,'quarantined_at':now()}
    save(destination.with_name(destination.name+'.receipt.json'),details)
    if prior:c.execute('UPDATE artifacts SET complete=0 WHERE id=?',(prior['id'],))
    c.execute('INSERT INTO artifacts(job_id,video_id,type,raw_relative_path,bytes,sha256,complete,details_json,created_at,mtime_ns) VALUES(?,?,?,?,?,?,0,?,?,?)',
      (job['id'],job['target_id'],'quarantine',str(destination.relative_to(self.store.raw)),destination.stat().st_size,actual,dump(details),now(),destination.stat().st_mtime_ns))
    quarantined.append(details)
   capacity_ok=self.store.capacity(c,0)
  if not capacity_ok:raise RuntimeError('HARVEST_STORAGE_LIMIT: quarantine preserved bytes leave insufficient reservation capacity')
  fmt='bestaudio[abr<=128]/bestaudio' if audio else 'best[height<=360]/best[height<=480]'
  command=self.base()+['--no-playlist','--abort-on-unavailable-fragments','--continue','--write-info-json','--format',fmt,'--max-filesize',str(job['reservation_bytes']),
    '--limit-rate',self.args.rate,'--no-progress','--output',str(raw/(job['target_id']+'.%(ext)s'))]
  metadata=self.store.raw/'metadata'/job['target_id']/'info.json'
  cache_usable=metadata.exists() and time.time()-metadata.stat().st_mtime<600
  if cache_usable:
   cached=json.loads(metadata.read_text())
   for form in cached.get('formats',[]):
    url=form.get('url','');expiry=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('expire',[])
    if expiry and expiry[0].isdigit() and int(expiry[0])<time.time()+self.args.timeout+60:cache_usable=False;break
  if cache_usable:command+=['--load-info-json',str(metadata)]
  else:command+=[job['source_url']]
  self.run_child(job,command,job['reservation_bytes'])
  files=[p for p in raw.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXT and p.stat().st_size>0]
  if not files:raise RuntimeError('No complete media file written; source may exceed max-filesize')
  artifacts=[]
  expected=None
  fresh=raw/(job['target_id']+'.info.json')
  if fresh.exists():expected=json.loads(fresh.read_text()).get('duration')
  elif metadata.exists():expected=json.loads(metadata.read_text()).get('duration')
  for path in files:
   probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height:stream_disposition=attached_pic','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,timeout=30)
   if probe.returncode:raise ValueError('ffprobe rejected resulting media')
   info=json.loads(probe.stdout);types={s['codec_type'] for s in info.get('streams',[])};duration=float(info.get('format',{}).get('duration',0))
   real_video=any(s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic',0) for s in info.get('streams',[]))
   if duration<=0 or ('audio' not in types) or (not audio and not real_video):raise ValueError('Media lacks required finite audio/video streams; attached cover art is not audiovisual video')
   if isinstance(expected,(int,float)) and expected>0 and abs(duration-expected)>max(3,expected*.03):raise ValueError('Media duration differs materially from fresh metadata; do not certify complete')
   reused=verified.get(str(path.relative_to(self.store.raw)))==sha(path)
   artifacts.append({'path':path,'type':'audio' if audio else 'video','complete':True,'details':{'ffprobe':info,'expected_duration_seconds':expected,
                    'reused_verified_local_media':reused,'actual_speaker_status':'unknown_not_audio_verified'}})
  reused=sum(a['details']['reused_verified_local_media'] for a in artifacts)
  return {'status':'succeeded','saved_media_files':len(artifacts),'fresh_media_files':len(artifacts)-reused,'reused_verified_media_files':reused,
          'quarantined_prior_files':len(quarantined),'media_type':'audio' if audio else 'video','used_cached_metadata':cache_usable,'actual_speaker_status':'unknown_not_audio_verified'},artifacts

def execute(store,args):
 out=args.output_dir
 gate=access_gate(args.access_receipt);store.put('access_gate',gate)
 denial=store.get('last_access_denial')
 if gate['status']=='ready_for_bounded_pilot' and denial and gate['observed_at_epoch']<=denial['at_epoch']:
  gate={**gate,'status':'blocked','reason':'new_successful_probe_required_after_observed_denial'};store.put('access_gate',gate)
 if gate['status']!='ready_for_bounded_pilot':store.put('run_status','not_executed_access_gate');return store.export(out)
 try:
  with collection_lock(store.raw):return execute_allowed(store,args)
 except RuntimeError as error:
  if 'shared raw-directory lock' not in str(error):raise
  store.put('run_status','waiting_for_other_collection_writer');return store.export(out)

def execute_allowed(store,args):
 out=args.output_dir
 store.reconcile_artifacts(full_hash=True);store.recover();worker=Worker(store,args)
 owner=str(os.getpid())+':'+(pathlib.Path('/proc')/str(os.getpid())/'stat').read_text().split()[21]+':'+str(time.time_ns());kinds=args.kinds.split(',')
 if set(kinds)-{'metadata','captions','video','audio','channel','playlist'}:raise ValueError('Unknown worker kind')
 caps={'metadata':4*1024**2,'captions':getattr(args,'caption_mib',64)*1024**2,'channel':16*1024**2,'playlist':16*1024**2,'video':args.video_mib*1024**2,'audio':args.audio_mib*1024**2}
 store.put('run_status','running');submitted=0;limit=args.workers;active={};cursor=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  while not worker.stop.is_set() and (active or submitted<args.max_jobs):
   added=False
   while len(active)<limit and submitted<args.max_jobs:
    job=None
    for _ in kinds:
     kind=kinds[cursor%len(kinds)];cursor+=1;job=store.claim(owner,kind,caps,args.timeout,args.max_attempts)
     if job:break
    if not job:break
    future=pool.submit(worker.execute,job);active[future]=job;submitted+=1;added=True
   if not active:break
   done,_=concurrent.futures.wait(active,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
   for future in done:
    job=active.pop(future)
    try:future.result()
    except Exception as error:worker.stop.set();store.put('runner_error',{'job_id':job['id'],'error':sanitize(error)})
   if worker.reduce:limit=max(1,limit//2);worker.reduce=False
   store.export(out)
  if worker.stop.is_set():
   for future in active:
    try:future.result()
    except Exception:pass
 store.put('run_status','stopped_after_access_denial' if worker.stop.is_set() else 'batch_complete_or_waiting_capacity_or_retry');return store.export(out)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('init','run','export','recover'))
 p.add_argument('--db',type=pathlib.Path,default=HERE/'state.sqlite');p.add_argument('--raw-dir',type=pathlib.Path,default=DEFAULT_RAW)
 p.add_argument('--videos',type=pathlib.Path,default=ROOT/'dist/analysis/data.json');p.add_argument('--channels',type=pathlib.Path);p.add_argument('--playlists',type=pathlib.Path)
 p.add_argument('--access-receipt',type=pathlib.Path);p.add_argument('--workers',type=int,default=4);p.add_argument('--max-jobs',type=int,default=12)
 p.add_argument('--output-dir',type=pathlib.Path,default=HERE)
 p.add_argument('--quota-gib',type=float,default=20);p.add_argument('--reserve-gib',type=float,default=6);p.add_argument('--video-mib',type=int,default=256);p.add_argument('--audio-mib',type=int,default=128)
 p.add_argument('--channel-batch',type=int,default=100);p.add_argument('--timeout',type=int,default=900);p.add_argument('--max-attempts',type=int,default=3)
 p.add_argument('--caption-mib',type=int,default=64);p.add_argument('--refresh-captions',action='store_true',help='Fetch track bodies again instead of reusing hash-verified resume artifacts')
 p.add_argument('--rate',default='4M');p.add_argument('--kinds',default='metadata,captions,video,channel,playlist,audio');args=p.parse_args()
 if not 1<=args.workers<=12 or args.max_jobs<1 or args.reserve_gib<6 or args.quota_gib<=0 or args.video_mib<1 or args.audio_mib<1 or args.caption_mib<1 or args.channel_batch<0 or args.timeout<1:p.error('Invalid parallelism/job/quota/reserve/cap values; reserve must be>=6GiB')
 store=Store(args.db,args.raw_dir,int(args.quota_gib*1024**3),int(args.reserve_gib*1024**3))
 if args.mode=='init':store.initialize(args.videos,args.channels,args.playlists);result=store.export(args.output_dir)
 elif args.mode=='run':result=execute(store,args)
 elif args.mode=='recover':result=store.recover();store.export(args.output_dir)
 else:result=store.export(args.output_dir)
 print(json.dumps(result,ensure_ascii=False));return 2 if args.mode=='run' and result.get('access_gate',{}).get('status')=='blocked' else 0

if __name__=='__main__':raise SystemExit(main())
