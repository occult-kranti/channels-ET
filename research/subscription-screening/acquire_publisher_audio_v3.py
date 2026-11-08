#!/usr/bin/env python3
"""Two-worker publisher acquisition with bounded RAM originals and shared admission.

This is an explicit new execution phase. It reuses verified v2 receipts without
changing them, retains interrupted v2 staging, and binds both executed code
versions. Full lossy copies and all durable provenance remain on disk.
"""
import argparse
import concurrent.futures
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import threading

BASE_SHA='2663bef91d36ecb2ce1b9e7ba13edcb958716c6faa000ec90f77450d98a59165'
BASE_PATH=Path(__file__).with_name('acquire_publisher_audio.py')
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest()!=BASE_SHA:raise RuntimeError('Frozen v2 helper mismatch')
spec=importlib.util.spec_from_file_location('collector_v2_bound',BASE_PATH)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
EXECUTION_SHA=C.sha(__file__)
DISK_RESERVE=128*1024**2
RAM_PHASE_CAP=600_000_000
MODEL_HEADROOM=512*1024**2

def code_check():
    if C.sha(__file__)!=EXECUTION_SHA or C.sha(BASE_PATH)!=BASE_SHA:raise ValueError('Collector code changed during phase')

def memory_guard():
    maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip()
    current=int(Path('/sys/fs/cgroup/memory.current').read_text().strip())
    if maximum=='max':raise ValueError('Finite cgroup memory limit required for this plan')
    available=int(maximum)-current
    if available<RAM_PHASE_CAP+MODEL_HEADROOM:raise C.ResourceStop('Cgroup RAM headroom below600MBstaging+512MiBmodel/worker reserve')
    return {'maximum_bytes':int(maximum),'current_bytes':current,'headroom_bytes':available}

class Budget:
    def __init__(self,output,retained=0):
        self.output=Path(output);self.retained=retained;self.reserved={};self.lock=threading.Lock();self.plan_binding=None
    def guard(self,additional=0):
        free=shutil.disk_usage(self.output).free
        if free<C.FLOOR+DISK_RESERVE+additional:
            raise C.ResourceStop('V3 disk free floor plus explicit128MiB reserve would be consumed')
        return free
    def admit(self,item):
        estimate=min(C.COMPACT_CAP,math.ceil((item.get('duration_seconds_publisher') or 4000)*6000*1.035)+65536)
        with self.lock:
            if self.retained+sum(self.reserved.values())+estimate>C.OUTPUT_CAP:
                raise C.ResourceStop('Shared retained audio cap would be exceeded')
            self.guard(sum(self.reserved.values())+estimate)
            self.reserved[item['source_id']]=estimate
    def completed(self,item,actual):
        with self.lock:
            estimate=self.reserved[item['source_id']]
            if actual>estimate or self.retained+sum(self.reserved.values())-estimate+actual>C.OUTPUT_CAP:
                raise C.ResourceStop('Actual output exceeded reserved size/cap')
            self.retained+=actual;del self.reserved[item['source_id']]
            self.guard()

def convert(original,target,budget):
    args=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(original),
          '-map','0:a:0','-vn','-sn','-dn','-c:a','libopus','-b:a','48000','-vbr','off',
          '-threads','1','-f','opus','pipe:1']
    errors_path=target.with_suffix('.ffmpeg.log');count=0
    with errors_path.open('xb') as errors,target.open('xb') as out:
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=errors)
        try:
            while True:
                b=process.stdout.read(256*1024)
                if not b:break
                if count+len(b)>C.COMPACT_CAP:raise C.ResourceStop('V3 compact streaming byte cap exceeded')
                budget.guard(len(b));out.write(b);count+=len(b)
            code=process.wait(timeout=30)
            if code or count<=0:raise ValueError('V3 encoder failed')
        except BaseException:
            process.kill();process.wait();raise
        finally:process.stdout.close()
    return {'command':args,'stderr_artifact':C.artifact(errors_path),'returncode':code,
            'codec':'libopus','target_bitrate_bps':48000,'vbr':False,'channels_preserved':True,
            'trimmed':False,'silence_removed':False,'mode':'full_first_audio_stream',
            'code_sha256':EXECUTION_SHA,'helper_sha256':BASE_SHA,
            'ffmpeg_version':subprocess.run(['ffmpeg','-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]}

def acquire(item,output,ram,budget,captions):
    code_check();memory_guard();budget.admit(item)
    key=hashlib.sha256(item['source_id'].encode()).hexdigest()[:20]
    folder=output/'items'/key;staging=ram/key
    if folder.exists() or staging.exists():raise ValueError('Previous v3 partial preserved; explicit review required')
    if shutil.disk_usage(ram).free<C.FLOOR+RAM_PHASE_CAP:raise C.ResourceStop('RAM staging admission fails explicit600MB envelope')
    folder.mkdir(parents=True);staging.mkdir(parents=True)
    original=staging/'original.partial';compact=folder/'retained.opus'
    retrieval=C.download(item['audio_url'],original,ram)
    memory_guard()
    C.dump(folder/'retrieval.json',retrieval)
    op=C.probe(original);od=C.decode_measure(original,folder/'original-decode.log')
    original_receipt={'status':'original_source_verified','source_id':item['source_id'],'publication_id':item['publication_id'],
                      'source_origin':item['source_origin'],'enclosure_url':item['audio_url'],'retrieval':retrieval,
                      'original':{'sha256':retrieval['sha256'],'bytes':retrieval['bytes'],'probe':op},
                      'decoded_16k_mono':od,'source':item,'collector_sha256':EXECUTION_SHA,'helper_sha256':BASE_SHA,
                      'temporary_original_storage':'explicit_bounded_ram_directory','resource_plan':budget.plan_binding,'created_at':C.now()}
    C.dump(folder/'original-source.json',original_receipt)
    conversion=convert(original,compact,budget)
    rp=C.probe(compact);rd=C.decode_measure(compact,folder/'retained-decode.log')
    if op['channels']!=rp['channels']:raise ValueError('V3 channel count changed')
    delta=abs(od['duration_seconds']-rd['duration_seconds'])
    if delta>C.DURATION_TOLERANCE:raise ValueError('V3 full decoded duration mismatch')
    audio=C.artifact(compact);audio['probe']=rp
    result={'status':'completed','provider':'publisher_audio','source_id':item['source_id'],'publication_id':item['publication_id'],
            'source_origin':item['source_origin'],'input_representation':'full_duration_lossy_opus_derivative','source':item,
            'duration_seconds':rp['duration_seconds'],'audio':audio,'decoded_16k_mono':rd,
            'duplicate_family_id':'original-sha256:'+retrieval['sha256'],'family_basis':'exact_original_encoded_bytes_not_session_identity',
            'lineage':{'original_source_receipt':C.artifact(folder/'original-source.json'),'original_sha256':retrieval['sha256'],
                       'original_bytes':retrieval['bytes'],'original_channels':op['channels'],'retained_channels':rp['channels'],
                       'original_enclosure_url':item['audio_url'],'original_decoded_16k_mono':od,'retained_decoded_16k_mono':rd,
                       'max_duration_difference_seconds':C.DURATION_TOLERANCE,'actual_duration_difference_seconds':delta,'conversion':conversion},
            'caption_link':None,'created_at':C.now(),'collector_sha256':EXECUTION_SHA,'helper_sha256':BASE_SHA,
            'resource_plan':budget.plan_binding}
    matches=[c for c in captions if c.get('episode_source_id')==item['publication_id'] and c.get('episode_guid')==item.get('guid')
             and c.get('audio_enclosure',{}).get('url')==item['audio_url']]
    if matches:
        for c in matches:C.verify_artifact(c['text_artifact'])
        result['caption_link']={'status':'exact_guid_enclosure_link_not_audio_accuracy_validation',
                                'records':[{'source_id':c['source_id'],'text_artifact':c['text_artifact'],'raw_artifact':c['raw_artifact']} for c in matches]}
    code_check();C.dump(folder/'receipt.json',result);C.completed(folder/'receipt.json')
    budget.completed(item,audio['bytes'])
    if C.sha(original)!=retrieval['sha256']:raise ValueError('New RAM original changed before cleanup')
    original.unlink()
    C.dump(folder/'cleanup.json',{'removed_only_new_ram_original':str(original),'original_sha256':retrieval['sha256'],
                                 'original_bytes':retrieval['bytes'],'verified_receipt':C.artifact(folder/'receipt.json'),'at':C.now()})
    print(json.dumps({'stage':'v3_audio_completed','publication_id':item['publication_id'],'bytes':audio['bytes'],
                      'decoded_seconds':rd['duration_seconds']}),flush=True)
    return result

def run(args):
    out=args.output.resolve();ram=args.ram.resolve();previous=args.previous.resolve();repo=Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo) or ram.is_relative_to(repo):raise ValueError('Raw output/staging must remain private')
    if not str(ram).startswith('/dev/shm/'):raise ValueError('V3 plan requires explicit /dev/shm directory')
    out.mkdir(parents=True,exist_ok=True);ram.mkdir(parents=True,exist_ok=True)
    with (out/'.collector.lock').open('a') as own_lock,(previous.parent/'.collector.lock').open('a') as prior_lock:
        # No active overlap: the old phase cannot be running or resumed concurrently.
        fcntl.flock(own_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(prior_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        code_check();memory=memory_guard()
        transition=json.loads(args.transition.read_text())
        if transition['status']!='previous_phase_stopped_and_inventoried':raise ValueError('Previous phase transition is incomplete')
        C.verify_artifact(transition['inherited_manifest']);C.verify_artifact(transition['frame'])
        if previous!=Path(transition['inherited_manifest']['path']):raise ValueError('Transition manifest differs from requested previous phase')
        for source,name,digest in [(Path(__file__),'executed-collector-v3.py',EXECUTION_SHA),(BASE_PATH,'executed-validator-v2.py',BASE_SHA)]:
            dest=out/name
            if dest.exists() and C.sha(dest)!=digest:raise ValueError('Execution phase code changed')
            if not dest.exists():dest.write_bytes(source.read_bytes())
        inherited=out/'inherited-v2-manifest.json'
        if not inherited.exists():inherited.write_bytes(previous.read_bytes())
        if C.sha(inherited)!=transition['inherited_manifest']['sha256']:raise ValueError('Inherited phase snapshot changed')
        prior=json.loads(inherited.read_text());frame_bytes=Path(transition['frame']['path']).read_bytes();frame=json.loads(frame_bytes)
        frozen_frame=out/'frame.json'
        if frozen_frame.exists() and frozen_frame.read_bytes()!=frame_bytes:raise ValueError('Frozen v3 source frame changed')
        if not frozen_frame.exists():frozen_frame.write_bytes(frame_bytes)
        records={r['source_id']:r for r in prior['records']}
        if (out/'manifest.json').exists():
            for r in json.loads((out/'manifest.json').read_text())['records']:records[r['source_id']]=r
        byid={r['source_id']:r for r in frame}
        for r in records.values():
            if C.completed(Path(r['audio']['path']).parent/'receipt.json')!=r or r['source']!=byid[r['source_id']]:
                raise ValueError('Reused receipt differs from frame or actual files')
        budget=Budget(out,sum(r['audio']['bytes'] for r in records.values()))
        captions=json.loads(args.captions.read_text())['records']
        remaining=[item for item in frame if item['source_id'] not in records]
        if args.pilot_new_items:remaining=remaining[:args.pilot_new_items]
        plan={'schema_version':1,'created_at':C.now(),'phase':'v3_parallel_ram_originals',
              'disk_floor_bytes':C.FLOOR,'disk_operational_reserve_bytes':DISK_RESERVE,
              'reserve_basis':'Two bounded26MB compact streams plus32MiB provenance allowance and remaining margin; originals and PCM now separately RAM-bound.',
              'retained_audio_cap_bytes':C.OUTPUT_CAP,'original_cap_per_worker':C.ORIGINAL_CAP,'compact_cap_per_worker':C.COMPACT_CAP,
              'ram_phase_envelope_bytes':RAM_PHASE_CAP,'ram_basis':'Two160MB originals plus two120MB ASR PCM plus40MB overhead; ASR scheduling independent but bounded.',
              'additional_cgroup_headroom_bytes':MODEL_HEADROOM,'cgroup_at_start':memory,
              'download_transcode_workers':args.workers,'v2_items_reused':len(records),'frame_entries':len(frame),
              'v2_manifest':C.artifact(inherited),'source_frame':C.artifact(frozen_frame),
              'transition':C.artifact(args.transition),'new_output':str(out),'new_ram_staging':str(ram),
              'no_v2_files_removed':True}
        plan_path=out/('resource-plan-'+C.now().replace(':','').replace('.','').replace('+','')+'.json')
        C.dump(plan_path,plan);budget.plan_binding=C.artifact(plan_path)
        def write(status,errors=None):
            values=[records[item['source_id']] for item in frame if item['source_id'] in records]
            data=C.summary(values,frame,status)
            data.update(collector=C.artifact(out/'executed-collector-v3.py'),helper=C.artifact(out/'executed-validator-v2.py'),
                        inherited_v2_manifest=C.artifact(inherited),resource_plan=budget.plan_binding,source_frame=C.artifact(frozen_frame))
            data['limits']['operational_reserve_bytes']=DISK_RESERVE
            data['limits']['ram_phase_envelope_bytes']=RAM_PHASE_CAP
            data['errors']=errors or []
            if errors:data['stop']={'type':errors[0]['type'],'source_id':errors[0]['source_id']}
            C.dump(out/'manifest.json',data)
        write('running')
        errors=[];iterator=iter(remaining);pending={}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for _ in range(args.workers):
                item=next(iterator,None)
                if item:pending[pool.submit(acquire,item,out,ram,budget,captions)]=item
            while pending:
                done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                # First consume every completed result. A failure stops all new admissions.
                for future in done:
                    item=pending.pop(future)
                    try:
                        r=future.result();records[r['source_id']]=r
                    except Exception as exc:
                        errors.append({'source_id':item['source_id'],'type':type(exc).__name__,'message':str(exc),'at':C.now()})
                write('halting' if errors else 'running',errors)
                if not errors:
                    for _ in done:
                        item=next(iterator,None)
                        if item:pending[pool.submit(acquire,item,out,ram,budget,captions)]=item
        write('halted' if errors else 'frame_complete' if len(records)==len(frame) else 'pilot_checkpoint',errors)
        if errors:raise RuntimeError('V3 halted; partials and errors preserved in private manifest')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--previous',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--transition',type=Path,required=True)
    p.add_argument('--ram',type=Path,required=True);p.add_argument('--captions',type=Path,required=True);p.add_argument('--workers',type=int,choices=(1,2),default=2)
    p.add_argument('--pilot-new-items',type=int);run(p.parse_args())
