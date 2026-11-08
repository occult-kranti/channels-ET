#!/usr/bin/env python3
"""Local ASR of verified, full-duration lossy publisher Opus derivatives.

The legacy core is imported only after its immutable hash is checked. This
successor adds compact-source receipt verification and a hard-capped PCM writer;
it does not change old core behavior, old manifests or old model results.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[2]
PCM_CAP = 120_000_000
FLOOR = 2 * 1024**3
RATE = 16000
EXECUTION_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

C = module('publisher_acquisition_v2', Path(__file__).with_name('acquire_publisher_audio.py'))
CORE_PATH = ROOT / 'research/batch-media/audio.py'
if C.sha(CORE_PATH) != C.FROZEN_CORE_SHA:
    raise RuntimeError('Legacy validation/model helper changed')
CORE = module('publisher_frozen_audio_core', CORE_PATH)

def check_code():
    if (C.sha(__file__) != EXECUTION_SHA or C.sha(C.__file__) != C.EXECUTION_SHA
            or C.sha(CORE_PATH) != C.FROZEN_CORE_SHA):
        raise ValueError('Bound successor, collector validator or legacy helper changed')

def capped_pcm(audio, target, proof, *, cap=PCM_CAP):
    """No truncated success: hard byte cap, natural EOF, exact decoded hash."""
    expected = proof['sample_count'] * 2 + 44
    if expected > cap:
        raise C.ResourceStop(f'Expected WAV {expected} exceeds explicit {cap}-byte cap')
    if shutil.disk_usage(target.parent).free < FLOOR + cap:
        raise C.ResourceStop('PCM admission would consume free floor')
    partial = target.with_suffix('.partial.wav')
    error_path = target.with_suffix('.ffmpeg.log')
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1', '-i', str(audio),
            '-map', '0:a:0', '-vn', '-sn', '-dn', '-ac', '1', '-ar', str(RATE),
            '-c:a', 'pcm_s16le', '-threads', '1', '-f', 's16le', 'pipe:1']
    count, digest = 0, hashlib.sha256()
    with partial.open('xb') as handle, wave.open(handle, 'wb') as output, error_path.open('xb') as errors:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(RATE)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                b = process.stdout.read(256 * 1024)
                if not b: break
                if count + len(b) + 44 > cap:
                    raise C.ResourceStop('PCM streaming byte cap reached; partial preserved, not admitted')
                if shutil.disk_usage(target.parent).free < FLOOR + len(b):
                    raise C.ResourceStop('Concurrent writes reached free floor; partial preserved')
                output.writeframesraw(b)
                digest.update(b);count += len(b)
            code = process.wait(timeout=30)
            if code or count <= 0 or count % 2:
                raise ValueError('PCM decoder failed or did not end naturally')
        except BaseException:
            process.kill();process.wait();raise
        finally:
            process.stdout.close()
    if count // 2 != proof['sample_count'] or digest.hexdigest() != proof['raw_pcm_sha256']:
        raise ValueError('Full PCM differs from acquisition decoded sample/hash proof')
    if partial.stat().st_size != count + 44:
        raise ValueError('Unexpected WAV byte accounting')
    os.replace(partial, target)
    return {'artifact': C.artifact(target), 'raw_pcm_sha256': digest.hexdigest(),
            'sample_count': count // 2, 'duration_seconds': count / (RATE * 2),
            'cap_bytes': cap, 'decoder_returncode': code, 'natural_eof': True,
            'stderr_artifact': C.artifact(error_path), 'command': args}

def verify_existing(path, source_receipt, model_binding):
    d=json.loads(path.read_text())
    if d['status'] not in ('completed','completed_empty_recognition') or d['acquisition_receipt'] != C.artifact(source_receipt) or d['model'] != model_binding:
        raise ValueError('Existing ASR receipt input/model mismatch')
    if d['successor_sha256'] != EXECUTION_SHA or d['collector_validator_sha256'] != C.EXECUTION_SHA or d['legacy_helper_sha256'] != C.FROZEN_CORE_SHA:
        raise ValueError('Existing ASR code bindings differ')
    for a in d['outputs'].values(): C.verify_artifact(a)
    acquisition=C.completed(source_receipt)
    normalized=json.loads(Path(d['outputs']['normalized']['path']).read_text())
    expected_id=acquisition['source_id']+':asr:tiny-en-v2'
    if normalized['source_id'] != expected_id or d['source_id'] != expected_id:
        raise ValueError('ASR normalized source identity mismatch')
    if normalized['publication_id'] != acquisition['publication_id'] or d['publication_id'] != acquisition['publication_id'] or d['source'] != acquisition['source']:
        raise ValueError('ASR publication identity mismatch')
    turns=normalized['turns'];text='\n'.join(t['text'] for t in turns)
    if normalized['text'] != text or Path(d['outputs']['text']['path']).read_text() != text+'\n':
        raise ValueError('Normalized text differs from turns/text artifact')
    if d['whitespace_words'] != len(text.split()) or d['segment_count'] != len(turns):
        raise ValueError('ASR word/segment accounting mismatch')
    if (len(turns)==0) != (d['status']=='completed_empty_recognition'):
        raise ValueError('Empty recognition status mismatch')
    previous=0;duration=acquisition['decoded_16k_mono']['duration_seconds']
    for i,t in enumerate(turns):
        a,b=t['start_seconds'],t['end_seconds']
        if not all(math.isfinite(v) for v in (a,b)) or not 0<=a<=b<=duration+1 or a<previous or t['role']!='unknown' or t['turn_id']!=f'segment-{i+1}':
            raise ValueError('ASR normalized timing/role/index mismatch')
        previous=a
    expected_srt='\n\n'.join(f"{i+1}\n{CORE.timestamp(t['start_seconds'],srt=True)} --> {CORE.timestamp(t['end_seconds'],srt=True)}\n{t['text']}" for i,t in enumerate(turns))+'\n'
    if Path(d['outputs']['srt']['path']).read_text()!=expected_srt:raise ValueError('SRT differs from normalized turns')
    return d

def process(source, output, model_path, model_binding, pcm_root=None):
    check_code()
    audio_path=Path(source['audio']['path'])
    acquisition_receipt=audio_path.parent/'receipt.json'
    verified=C.completed(acquisition_receipt)
    if verified != source: raise ValueError('Acquisition manifest differs from bound source receipt')
    key=hashlib.sha256(source['source_id'].encode()).hexdigest()[:20]
    folder=output/'items'/key;receipt_path=folder/'receipt.json'
    if receipt_path.exists(): return verify_existing(receipt_path,acquisition_receipt,model_binding)
    if folder.exists(): raise ValueError('Prior ASR partial preserved; explicit review required')
    if source['source']['language'] != 'en': raise ValueError('This English-only batch requires explicit English source metadata')
    folder.mkdir(parents=True)
    pcm_folder=folder
    if pcm_root is not None:
        pcm_folder=Path(pcm_root)/key
        pcm_folder.mkdir(parents=True,exist_ok=False)
    wav=pcm_folder/'decoded.wav'
    decode=capped_pcm(audio_path,wav,source['decoded_16k_mono'])
    if pcm_folder != folder:
        saved_log=folder/'pcm-decoder.log'
        shutil.copyfile(decode['stderr_artifact']['path'],saved_log)
        if C.sha(saved_log)!=decode['stderr_artifact']['sha256']:raise ValueError('PCM decoder log copy changed')
        decode['stderr_artifact']=C.artifact(saved_log)
        decode['temporary_storage']='explicit_separate_pcm_root'
    else:decode['temporary_storage']='same_private_filesystem'
    languages=CORE.language_plan({'source_language':'en','source_language_status':'declared'},model_binding,'en')
    C.dump(folder/'request.json',{'acquisition_receipt':C.artifact(acquisition_receipt),'source_id':source['source_id'],
                                'model':model_binding,'language_plan':languages,'decoder':decode,
                                'input_representation':source['input_representation']})
    segments,asr=CORE.run_asr(wav,model_path,decode['duration_seconds'],languages,diagnostics=folder)
    text='\n'.join(s['text'] for s in segments)
    turns=[{'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],
            'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds']} for i,s in enumerate(segments)]
    normalized={'source_id':source['source_id']+':asr:tiny-en-v2','publication_id':source['publication_id'],
                'text':text,'turns':turns,'no_answer_identified':True,
                'speaker_identity_verified':False,'audio_representation':'full_duration_lossy_opus_derivative',
                'scope':'Full decoded audio submitted; VAD/recognition may omit or hallucinate speech; no human accuracy audit'}
    C.dump(folder/'transcript.json',normalized)
    (folder/'transcript.txt').write_text(text+'\n')
    (folder/'transcript.srt').write_text('\n\n'.join(f"{i+1}\n{CORE.timestamp(s['start_seconds'],srt=True)} --> {CORE.timestamp(s['end_seconds'],srt=True)}\n{s['text']}" for i,s in enumerate(segments))+'\n')
    result={'status':'completed' if turns else 'completed_empty_recognition','source_id':normalized['source_id'],'publication_id':source['publication_id'],
            'source':source['source'],'acquisition_receipt':C.artifact(acquisition_receipt),
            'model':model_binding,'asr':asr,'decoder':decode,
            'outputs':{kind:C.artifact(folder/name) for kind,name in [('normalized','transcript.json'),('text','transcript.txt'),('srt','transcript.srt')]},
            'whitespace_words':len(text.split()),'segment_count':len(segments),'created_at':C.now(),
            'versions':CORE.versions(True),'successor_sha256':EXECUTION_SHA,'legacy_helper_sha256':C.FROZEN_CORE_SHA,
            'collector_validator_sha256':C.EXECUTION_SHA}
    check_code()
    if CORE.local_model_binding(model_path)!=model_binding:
        raise ValueError('Model/code changed during inference')
    C.dump(receipt_path,result);verify_existing(receipt_path,acquisition_receipt,model_binding)
    if C.sha(wav)!=decode['artifact']['sha256']: raise ValueError('PCM changed before cleanup')
    wav.unlink()
    C.dump(folder/'pcm-cleanup.json',{'removed_only_new_pcm':decode['artifact'],
                                    'retained_transcript_receipt':C.artifact(receipt_path),'at':C.now()})
    print(json.dumps({'stage':'asr_completed','publication_id':source['publication_id'],
                      'words':len(text.split()),'segments':len(segments)}),flush=True)
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',type=Path,default=Path('/workspace/channels-et-asr-cache/tiny-en'))
    p.add_argument('--workers',type=int,choices=(1,2),default=1)
    p.add_argument('--pcm-root',type=Path,help='Optional separate temporary PCM directory, e.g. bounded tmpfs; no prior files removed')
    p.add_argument('--pilot-items',type=int)
    args=p.parse_args(argv);out=args.output.resolve()
    if out.is_relative_to(ROOT):raise ValueError('ASR raw output must remain private')
    if args.pcm_root:
        args.pcm_root=args.pcm_root.resolve()
        if args.pcm_root.is_relative_to(ROOT):raise ValueError('Temporary PCM must remain private')
        args.pcm_root.mkdir(parents=True,exist_ok=True)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'.asr.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        copied=out/'executed-audio-derivative-v2.py'
        if copied.exists() and C.sha(copied)!=EXECUTION_SHA:raise ValueError('ASR code revision requires explicit new phase')
        if not copied.exists():copied.write_bytes(Path(__file__).read_bytes())
        validator_copy=out/'executed-collector-validator.py'
        if validator_copy.exists() and C.sha(validator_copy)!=C.EXECUTION_SHA:raise ValueError('Collector validator revision requires explicit new phase')
        if not validator_copy.exists():validator_copy.write_bytes(Path(C.__file__).read_bytes())
        check_code()
        # Bind exactly the bytes read while the collector may atomically advance.
        raw=args.acquisition.read_bytes()
        snapshot=out/('acquisition-snapshot-'+hashlib.sha256(raw).hexdigest()[:20]+'.json')
        if not snapshot.exists():
            with snapshot.open('xb') as f:f.write(raw)
        if snapshot.read_bytes()!=raw:raise ValueError('Acquisition snapshot collision')
        acquisition=json.loads(raw)
        input_artifact=C.artifact(snapshot)
        # Exact RSS-caption linkage avoids duplicating an existing text edition; it does not validate it.
        candidates=[r for r in acquisition['records'] if not r.get('caption_link')]
        if args.pilot_items:candidates=candidates[:args.pilot_items]
        model=CORE.local_model_binding(args.model)
        records=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            # A bounded submission window preserves fail-stop behavior.
            pending={};iterator=iter(candidates)
            for _ in range(args.workers):
                item=next(iterator,None)
                if item:pending[pool.submit(process,item,out,args.model,model,args.pcm_root)]=item
            while pending:
                done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                failures=[f for f in done if f.exception() is not None]
                if failures:
                    # Admit finished successes but schedule nothing after any observed failure.
                    for f in done:
                        if f not in failures:records.append(f.result())
                    failed=failures[0];item=pending[failed]
                    C.dump(out/'manifest.json',{'status':'halted','records':records,'failed_source_id':item['source_id'],
                                              'error':str(failed.exception()),'created_at':C.now()})
                    raise failed.exception()
                for future in done:
                    item=pending.pop(future)
                    try:records.append(future.result())
                    except Exception as exc:
                        C.dump(out/'manifest.json',{'status':'halted','records':records,'failed_source_id':item['source_id'],
                                                  'error':str(exc),'created_at':C.now()})
                        raise
                    C.dump(out/'manifest.json',{'status':'running','records':records,'input':input_artifact,
                                              'candidate_count':len(candidates),'created_at':C.now()})
                    item=next(iterator,None)
                    if item:pending[pool.submit(process,item,out,args.model,model,args.pcm_root)]=item
        C.dump(out/'manifest.json',{'status':'selected_snapshot_complete','records':records,
                                  'candidate_count':len(candidates),'input':input_artifact,
                                  'collector_completed_at_snapshot':len(acquisition['records']),
                                  'exact_publisher_caption_linked_count':sum(bool(r.get('caption_link')) for r in acquisition['records']),
                                  'created_at':C.now(),'successor':C.artifact(copied),
                                  'scope':'Selected acquisition snapshot; not all future arrivals. ASR is unreviewed.'})

if __name__=='__main__':main()
