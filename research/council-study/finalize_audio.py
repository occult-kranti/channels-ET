#!/usr/bin/env python3
"""Finalize this one preserved Council pilot after a disk-admission resource stop.

No network or re-encoding. Frozen acquisition code, original bytes, retained
bytes, fresh full decode, and the exact ResourceStop evidence are all bound.
"""
import argparse,fcntl,hashlib,importlib.util,json,shutil
from pathlib import Path
PILOT_SHA='81aa0c51707b93ab0c3131747cb2265bfd0afdede27fcfb949b3a9571a9283c8'
path=Path(__file__).with_name('collect_audio.py')
if hashlib.sha256(path.read_bytes()).hexdigest()!=PILOT_SHA:raise RuntimeError('Frozen pilot code changed')
s=importlib.util.spec_from_file_location('finalize_bound_pilot',path);P=importlib.util.module_from_spec(s);s.loader.exec_module(P);C=P.C
EXECUTION_SHA=C.sha(__file__)

def run(output,ram,failed_log,independent_staged):
 output=output.resolve();ram=ram.resolve()
 if not ram.is_relative_to(Path('/dev/shm')) or output.is_relative_to(P.ROOT):raise ValueError('Explicit private paths required')
 with (output/'.collector.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);P.check_code()
  receipt=output/'receipt.json'
  if receipt.exists():return P.verify_audio(receipt)
  if C.sha(output/'executed-council-pilot.py')!=PILOT_SHA:raise ValueError('Original executed pilot differs')
  log=failed_log.read_text()
  if 'staged=C.artifact(compact);guard(output,ram,additional_disk=staged[' not in log or 'ResourceStop: Council pilot protects2GiBfloor+128MiBoperations+64MiBoldfit+remaining2MBtext' not in log:raise ValueError('Not the reviewed post-conversion disk-admission failure')
  frame=json.loads((output/'frame.json').read_text());original=json.loads((output/'original-source.json').read_text());plan=json.loads((output/'resource-plan.json').read_text())
  if frame['source_id']!=P.SOURCE_ID or frame['guid']!=P.GUID or original['source']!=frame or plan['code_sha256']!=PILOT_SHA or plan['ram_root']!=str(ram):raise ValueError('Preserved pilot frame/source/resource differs')
  C.verify_artifact(original['resource_plan']);C.verify_artifact(original['executed_code'])
  selected,feed=P.feed_item(Path(frame['selection_binding']['path']),Path(frame['feed_binding']['compressed_feed']['path']))
  if feed!=frame['feed_binding'] or selected['enclosure']['url']!=frame['audio_url']:raise ValueError('Primary source differs')
  original_path=ram/'original.mp3';compact=ram/'retained.opus';C.verify_artifact({k:original['original'][k] for k in ('path','bytes','sha256')})
  if original['original']['path']!=str(original_path):raise ValueError('Original staging path differs')
  staged=C.artifact(compact)
  if staged['bytes']>P.AUDIO_CAP:raise C.ResourceStop('Staged compact exceeds20MBcap')
  review=json.loads(independent_staged.read_text())
  if review.get('status')!='staged_media_bytes_independently_decoded_not_yet_admitted' or review['artifact_bytes']!=staged['bytes'] or review['artifact_sha256']!=staged['sha256'] or review['natural_eof'] is not True or review['returncode']!=0:raise ValueError('Independent staged-byte proof differs')
  # The reviewer receipt is preserved as external evidence; exact retained bytes
  # are independently rehashed and fully decoded below before admission.
  gate=P.guard(output,ram,additional_disk=staged['bytes'])
  rp=P.probe(compact);rd=P.measure(compact,output/'retained-finalization-decode.log');od=original['decoded_16k_mono']
  if review['decoded_samples_16k_mono']!=rd['sample_count'] or review['decoded_seconds']!=rd['duration_seconds'] or review['raw_pcm_sha256']!=rd['raw_pcm_sha256']:raise ValueError('Fresh full decode differs from independent staged proof')
  if rp['channels']!=1 or abs(rd['duration_seconds']-od['duration_seconds'])>.1:raise ValueError('Full mono/source duration differs')
  copied=P.freeze(__file__,output/'executed-finalizer.py')
  staging_log=C.artifact(ram/'retained.ffmpeg.log');durable_log=output/'retained-conversion.ffmpeg.log'
  if durable_log.exists():raise ValueError('Prior finalization log copy requires explicit review')
  shutil.copyfile(staging_log['path'],durable_log);log_copy=C.artifact(durable_log)
  if any(log_copy[k]!=staging_log[k] for k in ('bytes','sha256')):raise ValueError('Durable conversion log copy differs')
  finalization={'status':'verified_preserved_stage_after_disk_resource_stop','code':copied,'original_pilot_sha256':PILOT_SHA,'failed_log':C.artifact(failed_log),'independent_staged_review':C.artifact(independent_staged),'staged_compact':staged,'conversion_log_original':staging_log,'conversion_log_durable':log_copy,'resource_gate':gate,'at':C.now(),'scope':'Copy-only resumption; no network, re-encoding, clipping or old-resource-guard changes.'}
  C.dump(output/'finalization-plan.json',finalization)
  retained=output/'retained.opus'
  with compact.open('rb') as inp,retained.open('xb') as dest:
   while True:
    b=inp.read(128*1024)
    if not b:break
    P.guard(output,ram,additional_disk=len(b));dest.write(b)
  durable=C.artifact(retained)
  if any(durable[k]!=staged[k] for k in ('bytes','sha256')):raise ValueError('Durable compact copy differs')
  command=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(original_path),'-map','0:a:0','-vn','-sn','-dn','-ac','1','-c:a','libopus','-b:a','22000','-vbr','off','-threads','1','-f','opus','pipe:1']
  conversion={'command':command,'stderr_artifact':log_copy,'returncode':0,'codec':'libopus','target_bitrate_bps':22000,'vbr':False,'mono_downmix':True,'channels_preserved':False,'trimmed':False,'silence_removed':False,'code_sha256':PILOT_SHA,
              'provenance_basis':'Reconstructed exact conversion descriptor from the frozen executed pilot reaching its post-conversion resource guard; retained bytes independently rehashed and fully decoded before copy-only finalization.','finalization':C.artifact(output/'finalization-plan.json')}
  r={'status':'completed','provider':'council_audio_v1','source_id':P.SOURCE_ID,'publication_id':frame['publication_id'],'source_origin':'publisher_rss','input_representation':'full_duration_lossy_22kbps_mono_opus_derivative','source':frame,'audio':{**durable,'probe':rp},'duration_seconds':rp['duration_seconds'],'decoded_16k_mono':rd,'duplicate_family_id':'original-sha256:'+original['original']['sha256'],'caption_link':None,'collector_sha256':PILOT_SHA,'resource_plan':C.artifact(output/'resource-plan.json'),'source_frame':C.artifact(output/'frame.json'),'executed_code':C.artifact(output/'executed-council-pilot.py'),'created_at':C.now(),'lineage':{'original_source_receipt':C.artifact(output/'original-source.json'),'original_bytes':original['original']['bytes'],'original_sha256':original['original']['sha256'],'original_channels':original['original']['probe']['channels'],'retained_channels':1,'actual_duration_difference_seconds':abs(od['duration_seconds']-rd['duration_seconds']),'original_decoded_16k_mono':od,'retained_decoded_16k_mono':rd,'conversion':conversion}}
  if C.sha(__file__)!=EXECUTION_SHA:raise ValueError('Finalizer changed during execution')
  P.check_code();C.dump(receipt,r);P.verify_audio(receipt);C.verify_artifact(staged);C.verify_artifact({k:original['original'][k] for k in ('path','bytes','sha256')})
  original_path.unlink();compact.unlink();C.dump(output/'original-cleanup.json',{'removed_only_new_original':str(original_path),'bytes':original['original']['bytes'],'sha256':original['original']['sha256'],'removed_new_compact_staging':staged,'retained_compact':durable,'verified_audio_receipt':C.artifact(receipt),'at':C.now()})
  P.verify_audio(receipt);return r

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['output','ram','failed-log','independent-staged']:p.add_argument('--'+name,required=True,type=Path)
 a=p.parse_args();r=run(a.output,a.ram,a.failed_log,a.independent_staged);print(json.dumps({'status':r['status'],'bytes':r['audio']['bytes'],'decoded_seconds':r['decoded_16k_mono']['duration_seconds']}))
