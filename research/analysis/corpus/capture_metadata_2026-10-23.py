import json,pathlib,re,urllib.request,urllib.error,zipfile,concurrent.futures,hashlib,threading,time,datetime
BASE=pathlib.Path(__file__).parent
src=json.load(open('/workspace/sites/channeling-atlas/dist/data.json'))['discovery']['records']
z=zipfile.ZipFile('/workspace/scratch/9ec421627a96/upload/et-channelers-draft.zip');zipdata=json.loads(z.read('et-channelers-draft/data/youtube_index_merged.json'))
ids={}
for r in src:
 if r['kind']=='video':
  m=re.search(r'(?:[?&]v=|youtu.be/)([\w-]{11})(?:[?&#]|$)',r['url'])
  if m:ids.setdefault(m[1],{'video_id':m[1],'source_families':[]})['source_families'].append('atlas-discovery')
for c in zipdata['channels']:
 for v in c.get('videos',[]):
  id=v.get('video_id')
  if id and re.fullmatch('[\w-]{11}',id):ids.setdefault(id,{'video_id':id,'source_families':[]})['source_families'].append('claude-zip')
lock=threading.Lock();stop=threading.Event();outpath=BASE/'metadata_incremental.jsonl'
outpath.write_text('');total=len(ids)
def one(r):
 id=r['video_id'];o=dict(r);o['source_url']='https://www.youtube.com/watch?v='+id;o['retrieved_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();o['access_type']='public_watch_page_metadata';o['source_families']=sorted(set(o['source_families']))
 if stop.is_set():o.update({'status':'not_attempted_after_block','error':'Batch stopped after HTTP403/429; no retry or evasion'})
 else:
  try:
   b=urllib.request.urlopen(o['source_url'],timeout=20).read();s=b.decode('utf-8');meta={}
   for marker in ['var ytInitialPlayerResponse = ','ytInitialPlayerResponse = ']:
    if marker in s:
     try:meta=json.JSONDecoder().raw_decode(s[s.index(marker)+len(marker):])[0];break
     except Exception:pass
   vd=meta.get('videoDetails',{});mf=meta.get('microformat',{}).get('playerMicroformatRenderer',{})
   if vd.get('videoId')!=id:raise ValueError('Matching videoDetails unavailable: '+str(meta.get('playabilityStatus',{}).get('status','unknown')))
   o.update({'status':'success','title':vd.get('title'),'channel_id':vd.get('channelId'),'publisher':vd.get('author'),'channel_url':mf.get('ownerProfileUrl'),'duration_seconds':int(vd['lengthSeconds']) if vd.get('lengthSeconds') else None,'published_at':mf.get('publishDate'),'uploaded_at':mf.get('uploadDate'),'view_count_observed':int(vd['viewCount']) if vd.get('viewCount') else None,'html_sha256':hashlib.sha256(b).hexdigest()})
  except Exception as e:
   o.update({'status':'failed','error_type':type(e).__name__,'error':str(e)[:500]})
   if isinstance(e,urllib.error.HTTPError) and e.code in [403,429]:stop.set()
 with lock:
  with outpath.open('a') as f:f.write(json.dumps(o,ensure_ascii=False)+'\n')
 return o
print('BATCH',total,flush=True)
res=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for o in ex.map(one,ids.values()):
  res.append(o)
  if len(res)%50==0:print('PROGRESS',len(res),'/',total,'success',sum(x['status']=='success' for x in res),'blocked',stop.is_set(),flush=True)
(BASE/'metadata.json').write_text(json.dumps({'method':'Ordinary unauthenticated public YouTube watch pages; no cookies, credentials, proxies, or bypass; five concurrent requests; no retry; stop on HTTP403/429. Metadata only; no media downloads.','attempted_union':total,'records':res},ensure_ascii=False,indent=2))
print('COMPLETE',total,'success',sum(x['status']=='success' for x in res),flush=True)
