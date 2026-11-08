#!/usr/bin/env python3
"""Prepare and supervise bounded same-window ASR comparisons with two CPU workers."""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

PRIVATE=Path('/workspace/channels-et-private/knowledge-bank-2026-11/asr')
RAM=Path('/dev/shm/channels-et-knowledge-2026-11/asr')
MODEL=RAM/'parakeet-541d1f99'
BASELINE=Path('/workspace/channels-et-asr-cache/tiny-en')
VENV={'parakeet_transformers':'/workspace/channels-et-modern-venv/bin/python',
      'faster_whisper':'/workspace/channels-et-asr-venv/bin/python'}


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.writing');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)


def tree_bytes(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def request(clips,engine,frame_binding):
    if engine=='parakeet_transformers':
        receipt=json.loads((PRIVATE/'model-download.json').read_text())
        if receipt['status']!='downloaded_and_hash_verified':raise ValueError('Pinned model is not complete')
        files=[{k:r[k] for k in ('file','bytes','sha256')} for r in receipt['files']]
        model=MODEL;repo=receipt['repo'];revision=receipt['revision']
    else:
        model=BASELINE;repo='Systran/faster-whisper-tiny.en';revision=None
        files=[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(model.iterdir()) if p.is_file()]
    return {'engine':engine,'model_path':str(model),'model_id':repo,'model_revision':revision,
        'model_files':files,'cpu_threads':1,'frame_binding':frame_binding,'clips':clips,
        'transcribe_options':{'beam_size':5,'language':'en','task':'transcribe','temperature':0.0,
            'condition_on_previous_text':False,'vad_filter':False,'word_timestamps':False},
        'scope':'Independent thirty-second windows on identical PCM. The controlled tiny.en rerun differs from historical full-recording inference settings and is not a reference transcript.'}


def supervise(requests,stage,worker_filename='asr_worker.py',private_budget_root=PRIVATE,max_stage_seconds=None):
    if stage.exists():raise ValueError('Use a fresh stage directory')
    if not 1<=len(requests)<=2:raise ValueError('At most two one-thread workers')
    if shutil.disk_usage('/workspace').free<2*1024**3:raise ValueError('Durable disk floor unavailable')
    if tree_bytes(private_budget_root)>5_000_000:raise ValueError('Durable ASR output budget exceeded')
    stage.mkdir(parents=True);handles=[];processes=[]
    worker=stage/'executed-asr_worker.py'
    worker_source=Path(__file__).with_name(worker_filename)
    worker.write_bytes(worker_source.read_bytes())
    (stage/'executed-asr_orchestrate.py').write_bytes(Path(__file__).read_bytes())
    started=time.time();receipt={'status':'running','started_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'orchestrator_sha256':sha(__file__),'worker_sha256':sha(worker_source),
        'limits':{'workers':2,'cpu_threads_per_worker':1,'clip_hard_seconds':180,
            'setup_hard_seconds':240,'conservative_asr_memory_bytes':18*1024**3,'private_byte_cap':5_000_000},
        'workers':[],'resource_samples':[],'memory_scope':'ASR temporary-file bytes plus sum of worker resident bytes, conservatively double counting mapped RAM-backed model pages. Cgroup file cache is recorded separately; it is not treated as nonreclaimable heap.'}
    try:
        for i,req in enumerate(requests):
            req_path=stage/f'request-{i+1}.json';dump(req_path,req)
            out=stage/f'worker-{i+1}';log=RAM/f'{stage.name}-worker-{i+1}.log';log.parent.mkdir(parents=True,exist_ok=True)
            stream=log.open('wb');handles.append(stream)
            env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',
                     HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(RAM/'hf-cache'),XDG_CACHE_HOME=str(RAM/'cache'),
                     TORCH_HOME=str(RAM/'torch-cache'),TMPDIR=str(RAM))
            env['PYTHONPYCACHEPREFIX']=str(RAM/'pycache')
            env['NUMBA_CACHE_DIR']=str(RAM/'numba-cache')
            if req['engine']=='parakeet_transformers':
                env['PYTHONPATH']=str(RAM/'python-deps')
            command=[VENV[req['engine']],str(worker),'--request',str(req_path),'--output',str(out)]
            proc=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            processes.append(proc);receipt['workers'].append({'pid':proc.pid,'request':{'path':str(req_path),'sha256':sha(req_path)},
                'command':command,'output':str(out),'log':str(log),'launched_at_unix':time.time()})
        dump(stage/'stage-receipt.json',receipt)
        while any(p.poll() is None for p in processes):
            now=time.time();rss=0
            if max_stage_seconds is not None and now-started>max_stage_seconds:raise TimeoutError('Complete stage hard deadline exceeded')
            for p,info in zip(processes,receipt['workers']):
                if p.poll() is not None:continue
                status=Path(f'/proc/{p.pid}/status')
                try:
                    for line in status.read_text().splitlines():
                        if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
                except FileNotFoundError:pass
                wp=Path(info['output'])/'receipt.json'
                wr=json.loads(wp.read_text()) if wp.exists() else {}
                current=wr.get('current_clip')
                if current and now-current['started_at_unix']>180:raise TimeoutError('Per-window hard deadline exceeded')
                if not wr.get('records') and not current and now-info['launched_at_unix']>240:raise TimeoutError('Worker setup hard deadline exceeded')
                if now-info['launched_at_unix']>240+180*len(json.loads(Path(info['request']['path']).read_text())['clips']):
                    raise TimeoutError('Worker total hard deadline exceeded')
            temporary=tree_bytes(RAM)
            stats=dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
            sample={'at_unix':now,'worker_rss_bytes':rss,'temporary_bytes':temporary,'conservative_asr_bytes':rss+temporary,
                'cgroup_current_bytes':int(Path('/sys/fs/cgroup/memory.current').read_text()),
                'cgroup_anon_bytes':int(stats.get('anon',0)),'cgroup_file_bytes':int(stats.get('file',0)),
                'cgroup_shmem_bytes':int(stats.get('shmem',0))}
            receipt['resource_samples'].append(sample)
            if rss+temporary>18*1024**3:raise MemoryError('Conservative ASR memory budget exceeded')
            if tree_bytes(private_budget_root)>5_000_000:raise ValueError('Durable ASR output budget exceeded')
            dump(stage/'stage-receipt.json',receipt)
            time.sleep(2)
        for p,info in zip(processes,receipt['workers']):
            info['exit_code']=p.returncode
            rp=Path(info['output'])/'receipt.json'
            info['receipt']={'path':str(rp),'sha256':sha(rp)} if rp.exists() else None
            if p.returncode or not rp.exists() or json.loads(rp.read_text())['status']!='completed':raise ValueError('Worker did not complete')
        receipt['status']='completed'
    except Exception as exc:
        receipt['status']='failed';receipt['failure_type']=type(exc).__name__;receipt['failure_message']=str(exc)[:300]
        for proc in processes:
            if proc.poll() is None:proc.terminate()
        for proc in processes:
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        raise
    finally:
        for handle in handles:handle.close()
        receipt['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();receipt['end_to_end_wall_seconds']=time.time()-started
        dump(stage/'stage-receipt.json',receipt)
    print(json.dumps({'stage':stage.name,'status':receipt['status'],'end_to_end_wall_seconds':receipt['end_to_end_wall_seconds']}))


def main(frame,stage_name,engine,pilot):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',stage_name):raise ValueError('Stage must be a path-safe identifier')
    raw=frame.read_bytes();f=json.loads(raw)
    binding={'path':str(frame),'sha256':hashlib.sha256(raw).hexdigest()}
    clips=f['clips'][:1] if pilot else f['clips']
    groups=[clips] if pilot else [clips[::2],clips[1::2]]
    requests=[request(g,engine,binding) for g in groups]
    supervise(requests,PRIVATE/stage_name)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frame',type=Path,required=True)
    p.add_argument('--stage',required=True);p.add_argument('--engine',choices=VENV,required=True);p.add_argument('--pilot',action='store_true')
    a=p.parse_args();main(a.frame,a.stage,a.engine,a.pilot)
