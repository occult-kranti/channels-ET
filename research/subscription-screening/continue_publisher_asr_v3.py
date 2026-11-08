#!/usr/bin/env python3
"""Version3 ASR continuation with source-bound recognition holds.

Only the reviewed last-segment display-end repair is automatic. Any other
diagnostic or resource failure halts the queue with all partials preserved.
"""
import argparse
import fcntl
import importlib.util
import json
import collections
from pathlib import Path
import time

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
D=module('queue_audio_derivative',Path(__file__).with_name('audio_derivative_v2.py'))
R=module('queue_terminal_recovery',Path(__file__).with_name('recover_asr_terminal.py'))
C=D.C
EXECUTION_SHA=C.sha(__file__)

def validate_holds(path):
    ledger=json.loads(path.read_text())
    if ledger.get('status')!='reviewed_source_specific_recognition_holds':raise ValueError('Unrecognized hold ledger')
    holds={}
    for h in ledger['records']:
        if h['disposition']!='held_unadmitted_asr' or h['reason_code']!='repeated_output_with_timestamp_overflow':raise ValueError('Unsupported source hold reason')
        for key in ('acquisition_receipt','failed_request','exhausted_diagnostic','raw_segments','original_inference_code','original_collector_validator'):
            C.verify_artifact(h[key])
        if h['original_inference_code']['sha256']!=D.EXECUTION_SHA or h['original_collector_validator']['sha256']!=C.EXECUTION_SHA:
            raise ValueError('Hold belongs to a different inference/validator version')
        source=C.completed(h['acquisition_receipt']['path']);request=json.loads(Path(h['failed_request']['path']).read_text())
        diagnostic=json.loads(Path(h['exhausted_diagnostic']['path']).read_text())
        if source['source_id']!=h['source_id'] or source['publication_id']!=h['publication_id'] or request['source_id']!=h['source_id']:
            raise ValueError('Hold source identity mismatch')
        if request['acquisition_receipt']!=h['acquisition_receipt'] or request['model']!=h['model']:
            raise ValueError('Hold input/model request differs')
        if D.CORE.local_model_binding(Path(h['model']['path']))!=h['model']:
            raise ValueError('Hold cannot automatically apply after model change')
        if diagnostic['request_sha256']!=h['failed_request']['sha256'] or diagnostic['raw_segments']!=h['raw_segments'] or diagnostic['inference_stream_exhausted'] is not True:
            raise ValueError('Hold diagnostic lineage differs')
        if not diagnostic.get('first_timestamp_failure'):raise ValueError('Hold lacks a timestamp failure')
        raw=[json.loads(line) for line in Path(h['raw_segments']['path']).read_text().splitlines() if line]
        counts=collections.Counter(r['text'].strip() for r in raw)
        repeated_text,repeated_count=counts.most_common(1)[0]
        duration=source['decoded_16k_mono']['duration_seconds']
        metrics={'raw_segment_count':len(raw),'unique_segment_texts':len(counts),'most_repeated_text':repeated_text,
                 'most_repeated_count':repeated_count,'ends_beyond_duration_plus_one_second':sum(float(r['end_repr'])>duration+1 for r in raw)}
        if metrics!=h['diagnostic_metrics'] or repeated_count<100 or repeated_count/len(raw)<.5 or metrics['ends_beyond_duration_plus_one_second']<2:
            raise ValueError('Observed diagnostic does not match reviewed repetition/overflow hold')
        if h['source_id'] in holds:raise ValueError('Duplicate hold source')
        holds[h['source_id']]=h
    return holds

def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    with (output/'.queue.lock').open('a') as queue_lock:
        fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        copied=output/'executed-asr-queue-v3.py'
        if copied.exists() and C.sha(copied)!=EXECUTION_SHA:raise ValueError('Queue execution code changed; use explicit successor')
        if not copied.exists():copied.write_bytes(Path(__file__).read_bytes())
        recovery_copy=output/'executed-terminal-recovery-policy.py'
        if recovery_copy.exists() and C.sha(recovery_copy)!=R.EXECUTION_SHA:raise ValueError('Recovery policy changed')
        if not recovery_copy.exists():recovery_copy.write_bytes(Path(R.__file__).read_bytes())
        hold_bytes=args.holds.read_bytes();hold_sha=C.hashlib.sha256(hold_bytes).hexdigest()
        hold_copy=output/('recognition-holds-'+hold_sha[:20]+'.json')
        if not hold_copy.exists():hold_copy.write_bytes(hold_bytes)
        if hold_copy.read_bytes()!=hold_bytes:raise ValueError('Hold snapshot changed')
        holds=validate_holds(hold_copy)
        def event(status,**kwargs):
            record={'at':C.now(),'status':status,'queue_version':3,'recognition_hold_count':len(holds),
                    'recognition_holds':[{k:h[k] for k in ('source_id','publication_id','disposition','reason_code')} for h in holds.values()],
                    'hold_ledger':C.artifact(hold_copy),**kwargs}
            with (output/'queue-v3-events.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            C.dump(output/'queue-status.json',record)
            print(json.dumps(record),flush=True)
        last_snapshot=None
        while True:
            if C.sha(__file__)!=EXECUTION_SHA or C.sha(R.__file__)!=R.EXECUTION_SHA or C.sha(hold_copy)!=hold_sha:
                raise ValueError('Queue/recovery code or hold ledger changed')
            # Wait for a prior manually started ASR run rather than overlap its lock.
            with (output/'.asr.lock').open('a') as lock:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    time.sleep(15);continue
                raw=args.acquisition.read_bytes();acquisition=json.loads(raw)
                snapshot=C.hashlib.sha256(raw).hexdigest()
                original_sources={r['source_id']:r for r in acquisition['records']}
                for sid,h in holds.items():
                    if sid not in original_sources or original_sources[sid]!=C.completed(h['acquisition_receipt']['path']):
                        raise ValueError('Held source/audio edition changed; hold cannot be inherited')
                selected={**acquisition,'records':[r for r in acquisition['records'] if r['source_id'] not in holds],
                          'original_completed_count':len(acquisition['records']),
                          'processing_exclusions':[{k:h[k] for k in ('source_id','publication_id','disposition','reason_code')} for h in holds.values()],
                          'unfiltered_acquisition_sha256':snapshot,'recognition_hold_ledger':C.artifact(hold_copy)}
                selected['completed_count']=len(selected['records'])
                selected_path=output/('selected-acquisition-'+snapshot[:20]+'-'+hold_sha[:20]+'.json')
                encoded=json.dumps(selected,indent=2,ensure_ascii=False)+'\n'
                if selected_path.exists() and selected_path.read_text()!=encoded:raise ValueError('Selected snapshot changed')
                if not selected_path.exists():selected_path.write_text(encoded)
                manifest_path=output/'manifest.json'
                existing=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                # Hold the ASR lock through diagnostic recovery and source checks.
                if existing.get('status')=='halted':
                    sid=existing.get('failed_source_id')
                    if not sid:raise ValueError('Halted ASR has no explicit failed source')
                    key=C.hashlib.sha256(sid.encode()).hexdigest()[:20];folder=output/'items'/key
                    if sid in holds:
                        if (folder/'receipt.json').exists():raise ValueError('Held source unexpectedly has an admitted receipt')
                        event('source_specific_recognition_hold_applied',source_id=sid)
                    elif (folder/'receipt.json').exists():
                        event('halted_existing_receipt_validation_failure',source_id=sid)
                        raise ValueError('Existing admitted receipt failed validation; explicit independent review required')
                    else:
                        try:
                            R.validate_diagnostic(folder)
                            repaired=R.recover(folder)
                        except Exception as exc:
                            event('halted_unrecoverable_diagnostic',source_id=sid,error=str(exc))
                            raise
                        event('terminal_display_end_repaired',source_id=sid,
                              receipt=C.artifact(folder/'receipt.json'),quality=repaired['normalization_recovery']['quality'])
                candidates=[r for r in selected['records'] if not r.get('caption_link')]
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
                D.main(['--acquisition',str(selected_path),'--output',str(output),'--pcm-root',str(args.pcm_root),'--workers',str(workers)])
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
                event('selected_frame_complete_with_recognition_holds' if holds else 'frame_complete',source_count=len(acquisition['records']),asr_candidate_count=len(candidates),
                      exact_caption_linked_count=sum(bool(r.get('caption_link')) for r in acquisition['records']),
                      asr_manifest=C.artifact(manifest_path));return
            last_snapshot=snapshot

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquisition',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pcm-root',type=Path,required=True)
    p.add_argument('--holds',type=Path,required=True)
    run(p.parse_args())
