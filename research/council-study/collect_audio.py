#!/usr/bin/env python3
"""One explicit long-form Council audio pilot, isolated from the old229 frame.

Full original is verified before22kbps mono Opus;240MB full PCM/oneCPU ASR.
No old helper or previous successful edition is modified.
"""
import argparse,fcntl,gzip,hashlib,importlib.util,json,math,os,shutil,subprocess,time,wave
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
def module(name,path,sha):
 if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise RuntimeError('Frozen helper changed: '+str(path))
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
D_SHA='70754e0aeef744f3bd04cb14013e7e4bb67ef778bb4b8b515945d0a816147c99'
F_SHA='4b15573d8a52a62fedbe9344a9184d6f88ff1beb096b90061fb52588b7679c88'
D=module('council_frozen_decoder',ROOT/'research/subscription-screening/audio_derivative_v2.py',D_SHA)
F=module('council_frozen_recognition_policy',ROOT/'research/subscription-screening/retry_publisher_asr_v2.py',F_SHA)
C=D.C;CORE=D.CORE;EXECUTION_SHA=C.sha(__file__)
GUID='d075f187-a23e-47a1-9fb2-308f3250d57f'
SOURCE_ID='council:inspire:'+GUID
AUDIO_CAP=20_000_000;TEXT_CAP=2_000_000;RAW_CAP=500_000;PCM_CAP=240_000_000;MAX_SECONDS=7200
RAM_CAP=1_000_000_000;MIN_HEADROOM=2*1024**3
DISK_RESERVE=128*1024**2;OLD_FIT_RESERVE=64*1024**2
OLD_RAM=[Path('/dev/shm/channels-et-publisher-asr-v2'),Path('/dev/shm/channels-et-interrupted-20261108T1558')]

def check_code():
 D.check_code();F.check_code()
 if C.sha(__file__)!=EXECUTION_SHA:raise ValueError('Council pilot code changed')

def guard(output,ram,additional_ram=0,additional_disk=0):
 asr_folder=Path(output)/'asr'
 written=sum(p.stat().st_size for p in asr_folder.iterdir() if p.is_file()) if asr_folder.exists() else 0
 if written>TEXT_CAP:raise C.ResourceStop('New Council ASR directory exceeds2MBcap')
 free=shutil.disk_usage(output).free;needed=C.FLOOR+DISK_RESERVE+OLD_FIT_RESERVE+max(0,TEXT_CAP-written)+additional_disk
 if free<needed:raise C.ResourceStop('Council pilot protects2GiBfloor+128MiBoperations+64MiBoldfit+remaining2MBtext')
 maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip();current=int(Path('/sys/fs/cgroup/memory.current').read_text())
 if maximum=='max' or int(maximum)-current<MIN_HEADROOM:raise C.ResourceStop('Council pilot requires2GiBcgroupheadroom')
 used=sum(p.stat().st_size for root in [*OLD_RAM,ram] if root.exists() for p in root.rglob('*') if p.is_file())
 if used+additional_ram>RAM_CAP:raise C.ResourceStop('Shared old/new RAM scratch exceeds explicit1GBenvelope')
 if shutil.disk_usage(ram).free<C.FLOOR+additional_ram:raise C.ResourceStop('Tmpfs freefloor insufficient')
 return {'disk_free_bytes':free,'disk_required_bytes':needed,'cgroup_maximum_bytes':int(maximum),'cgroup_current_bytes':current,'cgroup_headroom_bytes':int(maximum)-current,'shared_scratch_bytes':used,'prospective_scratch_bytes':additional_ram}

def freeze(path,target):
 body=Path(path).read_bytes()
 if target.exists():
  if target.read_bytes()!=body:raise ValueError('Frozen input changed')
 else:target.write_bytes(body)
 return C.artifact(target)

def feed_item(selection,feed_gzip):
 data=json.loads(selection.read_text());matches=[r for r in data['records'] if r['guid']==GUID]
 if len(matches)!=1:raise ValueError('Exactly the authorized Council9 interview required')
 item=matches[0];C.verify_artifact(data['source_frame']['artifact'])
 if data['source_frame']['artifact']!=C.artifact(feed_gzip):raise ValueError('Primary gzip source binding differs')
 raw=gzip.decompress(feed_gzip.read_bytes())
 if data['source_frame']['decoded_content']!={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:raise ValueError('Decoded RSS content binding differs')
 tree=ET.fromstring(raw);entries=tree.findall('./channel/item')
 found=[e for e in entries if e.findtext('guid')==GUID]
 if len(found)!=1:raise ValueError('Selected GUID missing or duplicated in primary feed')
 e=found[0];enclosure=e.find('enclosure')
 if e.findtext('title')!=item['title'] or e.findtext('link')!=item['link'] or enclosure is None or enclosure.attrib!=item['enclosure']:raise ValueError('Selected title/link/enclosure differs from exact RSS item')
 language=tree.findtext('./channel/language')
 if not language or not language.lower().startswith('en'):raise ValueError('English publisher metadata required for this pilot')
 return item,{'compressed_feed':C.artifact(feed_gzip),'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'uncompressed_bytes':len(raw),'feed_items':len(entries),'language':language}

def probe(path):
 p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True,timeout=90)
 d=json.loads(p.stdout);streams=[s for s in d['streams'] if s['codec_type']=='audio'];seconds=float(d['format']['duration'])
 if not streams or not math.isfinite(seconds) or not 0<seconds<=MAX_SECONDS:raise C.ResourceStop('Pilot media outside explicit7200second envelope')
 channels=int(streams[0]['channels'])
 if channels not in (1,2):raise ValueError('Only mono or stereo original supported')
 return {'duration_seconds':seconds,'channels':channels,'first_audio_codec':streams[0]['codec_name'],'raw':d}

def measure(path,log):
 args=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(path),'-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar','16000','-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
 digest=hashlib.sha256();count=0
 with log.open('xb') as errors:
  process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=errors)
  try:
   while True:
    b=process.stdout.read(256*1024)
    if not b:break
    count+=len(b)
    if count>MAX_SECONDS*32000:raise C.ResourceStop('Long-source decode envelope exceeded')
    digest.update(b)
   code=process.wait(timeout=30)
   if code or not count or count%2:raise ValueError('Full decoder failed or incomplete')
  except BaseException:process.kill();process.wait();raise
  finally:process.stdout.close()
 return {'sample_count':count//2,'duration_seconds':count/32000,'raw_pcm_sha256':digest.hexdigest(),'sample_rate':16000,'channels':1,'natural_eof':True,'decoder_returncode':code,'command':args,'stderr_artifact':C.artifact(log)}

def convert(original,target,output,ram):
 args=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(original),'-map','0:a:0','-vn','-sn','-dn','-ac','1','-c:a','libopus','-b:a','22000','-vbr','off','-threads','1','-f','opus','pipe:1']
 log=target.with_suffix('.ffmpeg.log');count=0
 with log.open('xb') as errors,target.open('xb') as dest:
  process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=errors)
  try:
   while True:
    b=process.stdout.read(128*1024)
    if not b:break
    if count+len(b)>AUDIO_CAP:raise C.ResourceStop('20MBretainedpilotcap reached; partialunadmitted')
    guard(output,ram,additional_ram=len(b));dest.write(b);count+=len(b)
   code=process.wait(timeout=30)
   if code or not count:raise ValueError('Compact encoder failed')
  except BaseException:process.kill();process.wait();raise
  finally:process.stdout.close()
 return {'command':args,'stderr_artifact':C.artifact(log),'returncode':code,'codec':'libopus','target_bitrate_bps':22000,'vbr':False,'mono_downmix':True,'channels_preserved':False,'trimmed':False,'silence_removed':False,'code_sha256':EXECUTION_SHA}

def verify_audio(path):
 r=json.loads(Path(path).read_text())
 if r['status']!='completed' or r['provider']!='council_audio_v1' or r['source_id']!=SOURCE_ID or r['collector_sha256']!=EXECUTION_SHA:raise ValueError('Pilot audio identity/code differs')
 for a in [r['audio'],r['lineage']['original_source_receipt'],r['resource_plan'],r['source_frame'],r['executed_code']]:C.verify_artifact(a)
 original=json.loads(Path(r['lineage']['original_source_receipt']['path']).read_text());plan=json.loads(Path(r['resource_plan']['path']).read_text());frame=json.loads(Path(r['source_frame']['path']).read_text())
 C.verify_artifact(frame['selection_binding']);C.verify_artifact(frame['feed_binding']['compressed_feed'])
 selected,feed=feed_item(Path(frame['selection_binding']['path']),Path(frame['feed_binding']['compressed_feed']['path']))
 if feed!=frame['feed_binding'] or selected['title']!=frame['title'] or selected['link']!=frame['source_url'] or selected['enclosure']['url']!=frame['audio_url']:raise ValueError('Bound primary publisher metadata differs')
 if r['source']!=frame or original['source']!=frame or r['source_id']!=original['source_id'] or r['publication_id']!=original['publication_id']:raise ValueError('Pilot source frame differs')
 if r['resource_plan']!=original['resource_plan'] or r['executed_code']['sha256']!=EXECUTION_SHA or plan['code_sha256']!=EXECUTION_SHA:raise ValueError('Pilot resource/code binding differs')
 expected_plan={'new_audio_cap':AUDIO_CAP,'new_text_cap':TEXT_CAP,'pcm_cap':PCM_CAP,'original_cap':C.ORIGINAL_CAP,'max_decoded_seconds':MAX_SECONDS,'retained_bitrate':22000,'retained_channels':1,'full_source_not_trimmed':True,'shared_old_new_ram_cap':RAM_CAP,'minimum_cgroup_headroom':MIN_HEADROOM,'disk_floor':C.FLOOR,'disk_operational_reserve':DISK_RESERVE,'old_final_fit_reserve':OLD_FIT_RESERVE,'source_frame':r['source_frame'],'executed_code':r['executed_code'],'reused_download_helper_sha256':C.EXECUTION_SHA}
 if any(plan.get(k)!=v for k,v in expected_plan.items()):raise ValueError('Resource plan policy differs')
 if r['source']['guid']!=GUID or r['source']['audio_url']!=original['retrieval']['enclosure_url']:raise ValueError('Pilot GUID/enclosure differs')
 if r['audio']['bytes']>AUDIO_CAP or r['audio']['probe']['channels']!=1 or r['lineage']['original_bytes']!=original['original']['bytes'] or r['lineage']['original_sha256']!=original['original']['sha256']:raise ValueError('Pilot byte/channel lineage differs')
 if r['lineage']['original_channels']!=original['original']['probe']['channels'] or r['lineage']['retained_channels']!=1 or r['lineage']['original_decoded_16k_mono']!=original['decoded_16k_mono'] or r['lineage']['retained_decoded_16k_mono']!=r['decoded_16k_mono']:raise ValueError('Repeated pilot channel/sample lineage differs')
 if r['duplicate_family_id']!='original-sha256:'+original['original']['sha256'] or original['retrieval']['sha256']!=original['original']['sha256'] or original['retrieval']['bytes']!=original['original']['bytes']:raise ValueError('Original retrieval/family binding differs')
 for measured in [r['decoded_16k_mono'],original['decoded_16k_mono']]:
  if measured['natural_eof'] is not True or measured['decoder_returncode']!=0 or measured['sample_count']<=0 or measured['sample_count']!=round(measured['duration_seconds']*16000) or not 0<measured['duration_seconds']<=MAX_SECONDS:raise ValueError('Invalid full decoder proof')
  C.verify_artifact(measured['stderr_artifact'])
 if abs(r['decoded_16k_mono']['duration_seconds']-original['decoded_16k_mono']['duration_seconds'])>.1:raise ValueError('Full source duration differs')
 if r['duration_seconds']!=r['audio']['probe']['duration_seconds'] or r['lineage']['actual_duration_difference_seconds']!=abs(r['decoded_16k_mono']['duration_seconds']-original['decoded_16k_mono']['duration_seconds']):raise ValueError('Repeated duration metadata differs')
 conversion=r['lineage']['conversion'];C.verify_artifact(conversion['stderr_artifact'])
 if conversion['target_bitrate_bps']!=22000 or conversion['mono_downmix'] is not True or conversion['trimmed'] is not False or conversion['returncode']!=0:raise ValueError('Derivative policy differs')
 expected=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',original['original']['path'],'-map','0:a:0','-vn','-sn','-dn','-ac','1','-c:a','libopus','-b:a','22000','-vbr','off','-threads','1','-f','opus','pipe:1']
 if conversion['command']!=expected or conversion['code_sha256']!=EXECUTION_SHA:raise ValueError('Exact mono encoding command differs')
 original_path=Path(original['original']['path'])
 if not Path(plan['ram_root']).is_relative_to(Path('/dev/shm')) or original_path!=Path(plan['ram_root'])/'original.mp3':raise ValueError('Original staging path differs from explicit RAM plan')
 if original_path.exists():C.verify_artifact({k:original['original'][k] for k in ('path','bytes','sha256')})
 else:
  disposal=json.loads((Path(path).parent/'original-cleanup.json').read_text())
  if disposal['verified_audio_receipt']!=C.artifact(path) or disposal['removed_only_new_original']!=str(original_path) or disposal['sha256']!=original['original']['sha256'] or disposal['bytes']!=original['original']['bytes']:raise ValueError('New original cleanup provenance differs')
  if disposal['retained_compact']!={k:r['audio'][k] for k in ('path','bytes','sha256')} or disposal['removed_new_compact_staging']['path']!=str(Path(plan['ram_root'])/'retained.opus') or any(disposal['removed_new_compact_staging'][k]!=r['audio'][k] for k in ('bytes','sha256')):raise ValueError('Compact staging/durable copy proof differs')
 return r

def acquire(selection,feed_gzip,output,ram):
 output=output.resolve();ram=ram.resolve()
 if output.is_relative_to(ROOT) or not ram.is_relative_to(Path('/dev/shm')):raise ValueError('Private output and explicit tmpfs required')
 output.mkdir(parents=True,exist_ok=True);ram.mkdir(parents=True,exist_ok=True)
 with (output/'.collector.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);check_code()
  receipt=output/'receipt.json'
  if receipt.exists():return verify_audio(receipt)
  if (output/'frame.json').exists():raise ValueError('Prior partial pilot preserved; explicit review required')
  selected,feed=feed_item(selection,feed_gzip)
  gate=guard(output,ram,additional_ram=C.ORIGINAL_CAP+AUDIO_CAP)
  freeze(selection,output/'selected-source-input.json')
  frame={'source_id':SOURCE_ID,'publication_id':'inspire:'+GUID,'publication_family_id':'inspire:'+GUID,'guid':GUID,'handle':'@InspireNation','publisher':'Inspire Nation / Michael Sandler','source_origin':'publisher_rss','title':selected['title'],'source_url':selected['link'],'audio_url':selected['enclosure']['url'],'language':'en','language_basis':'primary_publisher_RSS_declares_'+feed['language'],'duration_seconds_publisher':sum(int(v)*60**i for i,v in enumerate(reversed(selected['duration'].split(':')))),'declared_bytes':int(selected['enclosure']['length']),'feed_binding':feed,'selection_binding':C.artifact(output/'selected-source-input.json'),'medium_context_id':'inspire_nation_interview_pamela_aaralyn','claimed_medium':'Pamela Aaralyn','claimed_council':'Galactic Council of 9','attribution_scope':'publisher episode title and description; individual speaker roles and claimed entities unverified','voice_production':'unknown_not_verified'}
  C.dump(output/'frame.json',frame);executed=freeze(__file__,output/'executed-council-pilot.py')
  plan={'code_sha256':EXECUTION_SHA,'new_audio_cap':AUDIO_CAP,'new_text_cap':TEXT_CAP,'pcm_cap':PCM_CAP,'original_cap':C.ORIGINAL_CAP,'max_decoded_seconds':MAX_SECONDS,'retained_bitrate':22000,'retained_channels':1,'full_source_not_trimmed':True,'shared_old_new_ram_cap':RAM_CAP,'minimum_cgroup_headroom':MIN_HEADROOM,'disk_floor':C.FLOOR,'disk_operational_reserve':DISK_RESERVE,'old_final_fit_reserve':OLD_FIT_RESERVE,'ram_root':str(ram),'gate':gate,'source_frame':C.artifact(output/'frame.json'),'executed_code':executed,'reused_download_helper_sha256':C.EXECUTION_SHA}
  C.dump(output/'resource-plan.json',plan);plan_binding=C.artifact(output/'resource-plan.json')
  original=ram/'original.mp3';retrieval=C.download(frame['audio_url'],original,ram);guard(output,ram)
  op=probe(original);od=measure(original,output/'original-decode.log')
  original_receipt={'status':'original_source_verified','source_id':SOURCE_ID,'publication_id':frame['publication_id'],'source':frame,'retrieval':retrieval,'original':{'path':str(original),'bytes':retrieval['bytes'],'sha256':retrieval['sha256'],'probe':op},'decoded_16k_mono':od,'resource_plan':plan_binding,'executed_code':executed}
  C.dump(output/'original-source.json',original_receipt)
  compact=ram/'retained.opus';conversion=convert(original,compact,output,ram);rp=probe(compact);rd=measure(compact,output/'retained-decode.log')
  if rp['channels']!=1 or abs(od['duration_seconds']-rd['duration_seconds'])>.1:raise ValueError('Full mono derivative validation failed')
  staged=C.artifact(compact);guard(output,ram,additional_disk=staged['bytes'])
  retained=output/'retained.opus'
  with compact.open('rb') as inp,retained.open('xb') as dest:
   while True:
    b=inp.read(128*1024)
    if not b:break
    guard(output,ram,additional_disk=len(b));dest.write(b)
  durable=C.artifact(retained)
  if any(durable[k]!=staged[k] for k in ('bytes','sha256')):raise ValueError('RAM to durable compact copy differs')
  audio={**durable,'probe':rp};delta=abs(od['duration_seconds']-rd['duration_seconds'])
  result={'status':'completed','provider':'council_audio_v1','source_id':SOURCE_ID,'publication_id':frame['publication_id'],'source_origin':'publisher_rss','input_representation':'full_duration_lossy_22kbps_mono_opus_derivative','source':frame,'audio':audio,'duration_seconds':rp['duration_seconds'],'decoded_16k_mono':rd,'duplicate_family_id':'original-sha256:'+retrieval['sha256'],'caption_link':None,'collector_sha256':EXECUTION_SHA,'resource_plan':plan_binding,'source_frame':C.artifact(output/'frame.json'),'executed_code':executed,'created_at':C.now(),'lineage':{'original_source_receipt':C.artifact(output/'original-source.json'),'original_bytes':retrieval['bytes'],'original_sha256':retrieval['sha256'],'original_channels':op['channels'],'retained_channels':1,'actual_duration_difference_seconds':delta,'original_decoded_16k_mono':od,'retained_decoded_16k_mono':rd,'conversion':conversion}}
  check_code();C.dump(receipt,result);verify_audio(receipt)
  if C.sha(original)!=retrieval['sha256']:raise ValueError('Original changed before cleanup')
  C.verify_artifact(staged);original.unlink();compact.unlink();C.dump(output/'original-cleanup.json',{'removed_only_new_original':str(original),'bytes':retrieval['bytes'],'sha256':retrieval['sha256'],'removed_new_compact_staging':staged,'retained_compact':durable,'verified_audio_receipt':C.artifact(receipt),'at':C.now()})
  return result

def verify_asr(path):
 r=json.loads(Path(path).read_text())
 if r['status']!='completed' or r['source_id']!=SOURCE_ID+':asr:tiny-multilingual-council-v1' or r['code_sha256']!=EXECUTION_SHA:raise ValueError('Council ASR identity/code differs')
 if sum(p.stat().st_size for p in Path(path).parent.iterdir() if p.is_file())>TEXT_CAP:raise ValueError('Council complete ASR outputs exceed2MBcap')
 for a in [r['acquisition_receipt'],r['request'],r['raw_diagnostic'],r['diagnostic_completion'],*r['outputs'].values()]:C.verify_artifact(a)
 source=verify_audio(r['acquisition_receipt']['path']);request=json.loads(Path(r['request']['path']).read_text());raw=[json.loads(x) for x in Path(r['raw_diagnostic']['path']).read_text().splitlines() if x]
 model,provenance=F.bind_model(Path(r['model']['path']))
 if r['model']!=model or r['model_provenance']!=provenance or request['model']!=model or request['acquisition_receipt']!=r['acquisition_receipt'] or request['source_id']!=SOURCE_ID or request['code_sha256']!=EXECUTION_SHA:raise ValueError('Council ASR source/model/request differs')
 languages=CORE.language_plan({'source_language':'en','source_language_status':'declared'},model,'en')
 if request['model_provenance']!=provenance or request['settings']!=F.SETTINGS or request['cpu_threads']!=1 or request['num_workers']!=1 or request['language_plan']!=languages or r['asr']['language_plan']!=languages or request['input_representation']!=source['input_representation']:raise ValueError('Council repeated model/settings/language plan differs')
 if r['publication_id']!=source['publication_id'] or r['asr']['settings']!=F.SETTINGS or r['asr']['cpu_threads']!=1 or r['asr']['language_requested']!='en' or r['asr']['language_reported']!='en':raise ValueError('Council ASR settings/language differs')
 decoder=r['decoder'];proof=source['decoded_16k_mono']
 if decoder!=request['decoder'] or decoder['sample_count']!=proof['sample_count'] or decoder['raw_pcm_sha256']!=proof['raw_pcm_sha256'] or decoder['duration_seconds']!=proof['duration_seconds'] or decoder['cap_bytes']!=PCM_CAP or decoder['natural_eof'] is not True or decoder['decoder_returncode']!=0 or decoder['artifact']['bytes']!=44+2*proof['sample_count']:raise ValueError('Council fullPCM proof differs')
 C.verify_artifact(decoder['stderr_artifact']);decision=F.classify(raw,proof['duration_seconds']);completion=json.loads(Path(r['diagnostic_completion']['path']).read_text())
 expected_decode=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',source['audio']['path'],'-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar','16000','-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
 if decoder['command']!=expected_decode or abs(r['asr']['decoder_duration_seconds']-proof['duration_seconds'])>.1 or r['asr']['device']!='cpu' or r['asr']['compute_type']!='int8' or r['asr']['num_workers']!=1:raise ValueError('Council decoder or inference runtime differs')
 if completion['inference_stream_exhausted'] is not True or completion['raw_segments']!=r['raw_diagnostic'] or completion['request']!=r['request'] or completion['raw_segment_count']!=len(raw):raise ValueError('Council exhausted stream proof differs')
 if not decision['admitted'] or r['normalization_status']!=decision['normalization_status'] or r['recognition_metrics']!=decision['metrics']:raise ValueError('Council recognition decision differs')
 if completion['asr']!=r['asr'] or completion['decision']!={k:v for k,v in decision.items() if k!='segments'}:raise ValueError('Council exhausted decision/report differs')
 normalized=json.loads(Path(r['outputs']['normalized']['path']).read_text());expected=[]
 for i,s in enumerate(decision['segments']):expected.append({'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds'],**({'timestamp_repair':s['timestamp_repair'],'original_end_seconds':s['original_end_seconds']} if 'timestamp_repair' in s else {})})
 text='\n'.join(t['text'] for t in expected)
 if normalized['source_id']!=r['source_id'] or normalized['publication_id']!=r['publication_id'] or normalized['turns']!=expected or normalized['text']!=text or normalized['speaker_identity_verified'] is not False or normalized['no_answer_identified'] is not True or r['whitespace_words']!=len(text.split()) or r['segment_count']!=len(expected):raise ValueError('Council normalized identity/text/counts differ')
 if normalized['normalization_status']!=decision['normalization_status'] or normalized['timestamp_quality']!=decision['quality'] or normalized['audio_representation']!=source['input_representation']:raise ValueError('Council normalized quality/representation differs')
 if Path(r['outputs']['text']['path']).read_text()!=text+'\n':raise ValueError('Council plain text differs')
 srt='\n\n'.join(f"{i+1}\n{CORE.timestamp(t['start_seconds'],srt=True)} --> {CORE.timestamp(t['end_seconds'],srt=True)}\n{t['text']}" for i,t in enumerate(expected))+'\n'
 if Path(r['outputs']['srt']['path']).read_text()!=srt:raise ValueError('Council SRT differs')
 pcm=Path(decoder['artifact']['path'])
 if pcm.exists():C.verify_artifact(decoder['artifact'])
 else:
  cleanup=json.loads((Path(path).parent/'pcm-cleanup.json').read_text())
  if cleanup['removed_only_new_pcm']!=decoder['artifact'] or cleanup['verified_receipt']!=C.artifact(path):raise ValueError('Council PCM cleanup proof differs')
 return r

def transcribe(output,ram):
 from faster_whisper import WhisperModel
 output=output.resolve();ram=ram.resolve();folder=output/'asr';receipt=folder/'receipt.json'
 with (output/'.asr.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);check_code();source=verify_audio(output/'receipt.json')
  if receipt.exists():return verify_asr(receipt)
  if folder.exists():raise ValueError('Prior Council recognition partial preserved')
  folder.mkdir();guard(output,ram,additional_ram=PCM_CAP);model,provenance=F.bind_model(F.DEFAULT_MODEL)
  pcm=ram/'decoded.wav';decoder=D.capped_pcm(Path(source['audio']['path']),pcm,source['decoded_16k_mono'],cap=PCM_CAP)
  log=folder/'pcm-decoder.log';shutil.copyfile(decoder['stderr_artifact']['path'],log);decoder['stderr_artifact']=C.artifact(log)
  languages=CORE.language_plan({'source_language':'en','source_language_status':'declared'},model,'en')
  request={'source_id':SOURCE_ID,'acquisition_receipt':C.artifact(output/'receipt.json'),'code_sha256':EXECUTION_SHA,'model':model,'model_provenance':provenance,'decoder':decoder,'language_plan':languages,'settings':F.SETTINGS,'cpu_threads':1,'num_workers':1,'input_representation':source['input_representation']}
  C.dump(folder/'request.json',request);engine=WhisperModel(str(F.DEFAULT_MODEL),device='cpu',compute_type='int8',cpu_threads=1,num_workers=1,local_files_only=True)
  if not engine.model.is_multilingual:raise ValueError('Expected cached multilingual model')
  stream,info=engine.transcribe(str(pcm),**F.SETTINGS);raw=[];size=0;started=time.monotonic();rawpath=folder/'asr-raw-segments.jsonl'
  with rawpath.open('x') as f:
   for index,s in enumerate(stream):
    row={'segment_index':index,'start_repr':repr(float(s.start)),'end_repr':repr(float(s.end)),'text':s.text,'avg_logprob_repr':repr(s.avg_logprob),'no_speech_prob_repr':repr(s.no_speech_prob)}
    line=json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n';size+=len(line.encode())
    if size>RAW_CAP or index>=10000 or time.monotonic()-started>1800:raise C.ResourceStop('Bounded Council recognition diagnostic limit; partialunadmitted')
    guard(output,ram);f.write(line);f.flush();raw.append(row)
    if len(raw)%100==0:print(json.dumps({'stage':'council_asr_progress','segments':len(raw),'last_end':row['end_repr']}),flush=True)
   os.fsync(f.fileno())
  report={'settings':F.SETTINGS,'cpu_threads':1,'num_workers':1,'device':'cpu','compute_type':'int8','language_requested':'en','language_reported':info.language,'language_plan':languages,'decoder_duration_seconds':info.duration,'duration_after_vad_seconds':info.duration_after_vad,'human_reviewed':False,'speaker_diarization_performed':False}
  decision=F.classify(raw,source['decoded_16k_mono']['duration_seconds']);completion={'inference_stream_exhausted':True,'raw_segment_count':len(raw),'raw_segments':C.artifact(rawpath),'request':C.artifact(folder/'request.json'),'asr':report,'decision':{k:v for k,v in decision.items() if k!='segments'}}
  if sum(p.stat().st_size for p in folder.iterdir() if p.is_file())+len((json.dumps(completion,indent=2,ensure_ascii=False)+'\n').encode())+100_000>TEXT_CAP:raise C.ResourceStop('Council diagnostic provenance would exceed2MBcap')
  C.dump(folder/'diagnostic-completion.json',completion)
  if not decision['admitted']:raise ValueError('Council recognition held: '+decision['reason'])
  turns=[{'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds'],**({'timestamp_repair':s['timestamp_repair'],'original_end_seconds':s['original_end_seconds']} if 'timestamp_repair' in s else {})} for i,s in enumerate(decision['segments'])]
  text='\n'.join(t['text'] for t in turns);sid=SOURCE_ID+':asr:tiny-multilingual-council-v1'
  normalized={'source_id':sid,'publication_id':source['publication_id'],'text':text,'turns':turns,'no_answer_identified':True,'speaker_identity_verified':False,'audio_representation':source['input_representation'],'normalization_status':decision['normalization_status'],'timestamp_quality':decision['quality']}
  rendered={'transcript.json':json.dumps(normalized,indent=2,ensure_ascii=False)+'\n','transcript.txt':text+'\n','transcript.srt':'\n\n'.join(f"{i+1}\n{CORE.timestamp(t['start_seconds'],srt=True)} --> {CORE.timestamp(t['end_seconds'],srt=True)}\n{t['text']}" for i,t in enumerate(turns))+'\n'}
  existing=sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
  if existing+sum(len(v.encode()) for v in rendered.values())+100_000>TEXT_CAP:raise C.ResourceStop('Council ASR output2MBcap; full output retained privately or unadmitted, never truncated')
  for name,body in rendered.items():(folder/name).write_text(body)
  result={'status':'completed','provider':'council_asr_v1','source_id':sid,'publication_id':source['publication_id'],'source':source['source'],'acquisition_receipt':C.artifact(output/'receipt.json'),'code_sha256':EXECUTION_SHA,'model':model,'model_provenance':provenance,'decoder':decoder,'asr':report,'request':C.artifact(folder/'request.json'),'raw_diagnostic':C.artifact(rawpath),'diagnostic_completion':C.artifact(folder/'diagnostic-completion.json'),'outputs':{k:C.artifact(folder/n) for k,n in [('normalized','transcript.json'),('text','transcript.txt'),('srt','transcript.srt')]},'whitespace_words':len(text.split()),'segment_count':len(turns),'normalization_status':decision['normalization_status'],'recognition_metrics':decision['metrics'],'created_at':C.now()}
  check_code();C.dump(receipt,result);verify_asr(receipt)
  C.verify_artifact(decoder['artifact']);pcm.unlink();C.dump(folder/'pcm-cleanup.json',{'removed_only_new_pcm':decoder['artifact'],'verified_receipt':C.artifact(receipt),'at':C.now()});return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['acquire','asr']);p.add_argument('--selection',type=Path);p.add_argument('--feed-gzip',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--ram',required=True,type=Path)
 a=p.parse_args();r=acquire(a.selection,a.feed_gzip,a.output,a.ram) if a.mode=='acquire' else transcribe(a.output,a.ram);print(json.dumps({'status':r['status'],'source_id':r['source_id'],'words':r.get('whitespace_words'),'audio_bytes':r.get('audio',{}).get('bytes')}))
