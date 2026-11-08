#!/usr/bin/env python3
"""Resume the verified publisher ASR queue as acquisition snapshots advance.

Only the reviewed last-segment display-end repair is automatic. Any other
diagnostic or resource failure halts the queue with all partials preserved.
"""
import argparse
import fcntl
import importlib.util
import json
from pathlib import Path
import time

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
D=module('queue_audio_derivative',Path(__file__).with_name('audio_derivative_v2.py'))
R=module('queue_terminal_recovery',Path(__file__).with_name('recover_asr_terminal.py'))
C=D.C
EXECUTION_SHA=C.sha(__file__)

def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    with (output/'.queue.lock').open('a') as queue_lock:
        fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        copied=output/'executed-asr-queue.py'
        if copied.exists() and C.sha(copied)!=EXECUTION_SHA:raise ValueError('Queue execution code changed; use explicit successor')
        if not copied.exists():copied.write_bytes(Path(__file__).read_bytes())
        recovery_copy=output/'executed-terminal-recovery-policy.py'
        if recovery_copy.exists() and C.sha(recovery_copy)!=R.EXECUTION_SHA:raise ValueError('Recovery policy changed')
        if not recovery_copy.exists():recovery_copy.write_bytes(Path(R.__file__).read_bytes())
        def event(status,**kwargs):
            record={'at':C.now(),'status':status,**kwargs}
            with (output/'queue-events.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            C.dump(output/'queue-status.json',record)
            print(json.dumps(record),flush=True)
        last_snapshot=None
        while True:
            if C.sha(__file__)!=EXECUTION_SHA or C.sha(R.__file__)!=R.EXECUTION_SHA:raise ValueError('Queue/recovery code changed')
            # Wait for a prior manually started ASR run rather than overlap its lock.
            with (output/'.asr.lock').open('a') as lock:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    time.sleep(15);continue
                raw=args.acquisition.read_bytes();acquisition=json.loads(raw)
                snapshot=C.hashlib.sha256(raw).hexdigest()
                manifest_path=output/'manifest.json'
                existing=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                # Hold the ASR lock through diagnostic recovery and source checks.
                if existing.get('status')=='halted':
                    sid=existing.get('failed_source_id')
                    if not sid:raise ValueError('Halted ASR has no explicit failed source')
                    key=C.hashlib.sha256(sid.encode()).hexdigest()[:20];folder=output/'items'/key
                    if (folder/'receipt.json').exists():
                        event('halted_existing_receipt_validation_failure',source_id=sid)
                        raise ValueError('Existing admitted receipt failed validation; explicit independent review required')
                    try:
                        R.validate_diagnostic(folder)
                        repaired=R.recover(folder)
                    except Exception as exc:
                        event('halted_unrecoverable_diagnostic',source_id=sid,error=str(exc))
                        raise
                    event('terminal_display_end_repaired',source_id=sid,
                          receipt=C.artifact(folder/'receipt.json'),quality=repaired['normalization_recovery']['quality'])
                candidates=[r for r in acquisition['records'] if not r.get('caption_link')]
                complete=0
                for r in candidates:
                    key=C.hashlib.sha256(r['source_id'].encode()).hexdigest()[:20]
                    if (output/'items'/key/'receipt.json').exists():complete+=1
                before_manifest=manifest_path.read_bytes() if manifest_path.exists() else None
            final_snapshot=complete==len(candidates) and acquisition['status']=='frame_complete'
            if complete==len(candidates) and snapshot==last_snapshot and not final_snapshot:
                if acquisition['status'] in ('halted','halting'):
                    event('acquisition_halted_current_text_snapshot_complete',acquisition_status=acquisition['status'],
                          source_count=len(acquisition['records']));return
                time.sleep(15);continue
            workers=2 if acquisition['status']=='frame_complete' else 1
            event('snapshot_started',audio_sources=len(acquisition['records']),asr_candidates=len(candidates),
                  existing_receipts=complete,workers=workers,acquisition_sha256=snapshot)
            try:
                D.main(['--acquisition',str(args.acquisition),'--output',str(output),'--pcm-root',str(args.pcm_root),'--workers',str(workers)])
            except Exception as exc:
                after_manifest=manifest_path.read_bytes() if manifest_path.exists() else None
                if isinstance(exc,BlockingIOError) and after_manifest==before_manifest:
                    event('waiting_for_asr_lock');time.sleep(1);continue
                event('snapshot_halted_for_diagnostic_review',error=str(exc))
                failed=json.loads(after_manifest) if after_manifest else {}
                if after_manifest==before_manifest or failed.get('status')!='halted' or not failed.get('failed_source_id'):
                    event('halted_without_bound_source_diagnostic',error=str(exc))
                    raise
                key=C.hashlib.sha256(failed['failed_source_id'].encode()).hexdigest()[:20]
                if (output/'items'/key/'receipt.json').exists():
                    event('halted_existing_receipt_validation_failure',source_id=failed['failed_source_id'],error=str(exc))
                    raise
                # The next iteration validates the precise failed diagnostic before any recovery.
                continue
            if final_snapshot:
                event('frame_complete',source_count=len(acquisition['records']),asr_candidate_count=len(candidates),
                      exact_caption_linked_count=sum(bool(r.get('caption_link')) for r in acquisition['records']),
                      asr_manifest=C.artifact(manifest_path));return
            last_snapshot=snapshot

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquisition',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pcm-root',type=Path,required=True)
    run(p.parse_args())
