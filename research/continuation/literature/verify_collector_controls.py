#!/usr/bin/env python3
"""Independent adversarial pagination/quota mocks; no external request or download."""
import argparse,datetime,hashlib,importlib.util,json,pathlib,subprocess,tempfile,types,unittest.mock as mock
HERE=pathlib.Path(__file__).resolve().parent;P=HERE.parent/'acquisition/channel_pipeline.py';s=importlib.util.spec_from_file_location('independent_pipeline',P);c=importlib.util.module_from_spec(s);s.loader.exec_module(c);checks=[]
def ck(ok,label,actual=None,expected=None):checks.append({'check':label,'passed':bool(ok),'actual':actual,'expected':expected})
with tempfile.TemporaryDirectory(prefix='channels-et-independent-') as t:
 d=pathlib.Path(t)
 # Accepted ID aliases must be normalized for caption/media consumers.
 aliases=d/'id-aliases.json';aliases.write_text(json.dumps({'records':[{'id':'abcdefghijk','duration_seconds':1},{'video_id':'abcdefghijk','duration_seconds':2}]}))
 normalized=c.video_inputs(types.SimpleNamespace(input=aliases));ck(len(normalized)==1,'ID aliases deduplicate into one upload',len(normalized),1)
 ck(normalized[0].get('video_id')=='abcdefghijk','ID-only input normalized for caption/media consumers',normalized[0].get('video_id'),'abcdefghijk')
 normalized_plan=c.media_plan(normalized,d/'alias-raw',1024*1024,0,1024*1024);ck(normalized_plan['records'][0]['eligible'] and normalized_plan['records'][0]['estimated_bytes']==25000,'normalized ID-only row supports no-network media planning',normalized_plan['records'][0],{'eligible':True,'estimated_bytes':25000})
 plan=d/'plan.json';plan.write_text(json.dumps({'accounts':[{'id':'a','url':'https://www.youtube.com/@mock/videos','person_ids':['p']}]}));out=d/'enum';args=types.SimpleNamespace(access_receipt=None,plan=plan,output=out,person_id=[],max_jobs=1,batch_entries=3,timeout=5,delay=0)
 response=types.SimpleNamespace(returncode=0,stdout=json.dumps({'entries':[{'id':'abcdefghijk'},None,{'id':'lmnopqrstuv'}]}),stderr='')
 with mock.patch.object(c,'require_access',return_value=None),mock.patch.object(c,'packages',return_value={'yt-dlp':'mock','youtube-transcript-api':'mock'}),mock.patch.object(c.subprocess,'run',return_value=response),mock.patch.object(c.time,'sleep',return_value=None):c.enumerate_channels(args)
 state=json.loads((out/'state.json').read_text())['channels']['a'];ck(state['complete_listing'] is False,'full batch with unavailable slot must not mark end',state['complete_listing'],False);ck(state['next_start']==4,'resume cursor consumes all returned playlist slots',state['next_start'],4)
 # Ordinary zero exit with a fast oversize artifact must not be called success.
 inputs=d/'vids.json';inputs.write_text(json.dumps([{'video_id':'abcdefghijk','duration_seconds':1}]));raw=d/'raw';mediaout=d/'media';args=types.SimpleNamespace(raw_dir=raw,input=inputs,max_jobs=1,quota_gib=.02,reserve_gib=0,max_file_mib=1,output=mediaout,execute=True,access_receipt=None,timeout=5,delay=0)
 class Finished:
  def __init__(self,*a,**kw):
   target=raw/'media/abcdefghijk.webm';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'x'*(1024*1024+1))
  def poll(self):return 0
  def wait(self,timeout=None):return 0
  def terminate(self):pass
  def kill(self):pass
 with mock.patch.object(c,'require_access',return_value=None),mock.patch.object(c,'packages',return_value={'yt-dlp':'mock','youtube-transcript-api':'mock'}),mock.patch.object(c.subprocess,'Popen',Finished),mock.patch.object(c.time,'sleep',return_value=None):c.media(args)
 state=json.loads((mediaout/'state.json').read_text())['media']['abcdefghijk'];ck(state['status']!='success','fast completed oversize download rejected by post-exit validation',state['status'],'not success')
 # Actual access guard rejects failed/stale/wrong-response receipts.
 for name,data in [('blocked',{'blocked':True,'records':[{'status':'blocked'}]}),('wrong_type',{'records':[{'status':'success','operation':'other','http_status':200,'matching_video_id':True}]}),('stale',{'records':[{'status':'success','operation':'watch_metadata_preflight','http_status':200,'matching_video_id':True,'retrieved_at':(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=2)).isoformat()}]})]:
  p=d/(name+'.json');p.write_text(json.dumps(data));rejected=False
  try:c.require_access(p)
  except (ValueError,TypeError):rejected=True
  ck(rejected,'guard rejects '+name)
 # A matching recent successful *mock receipt* validates fields only.
 p=d/'recent.json';p.write_text(json.dumps({'records':[{'status':'success','operation':'watch_metadata_preflight','http_status':200,'matching_video_id':True,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}]}));ok=True
 try:c.require_access(p)
 except Exception:ok=False
 ck(ok,'guard accepts valid current fixture fields (not proof network access)')
 secret=c.sanitized('https://user:pass@example.com/path?token=secret Authorization=abc');ck('secret' not in secret and 'pass@' not in secret and 'abc' not in secret,'error sanitizer excludes userinfo/query/authorization fixture')
fail=[x for x in checks if not x['passed']];r={'round':11,'collector_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'status':'PASS' if not fail else 'FAIL','checks':len(checks),'failures':fail,'network_requests':0,'scope':'Mock outcomes are control tests, not actual source retrieval. Temporary artifacts deleted.','all_checks':checks};(HERE/'independent-collector-controls.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));raise SystemExit(bool(fail))
