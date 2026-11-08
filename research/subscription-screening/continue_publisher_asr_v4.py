#!/usr/bin/env python3
"""Version4 ASR continuation with auditable per-source timestamp quarantine.

Only the reviewed last-segment display-end repair is automatic. Exhausted multiple-EOF failures are quarantined without text admission.
Global integrity, resource and infrastructure errors halt with partials preserved.
"""
import argparse
import fcntl
import importlib.util
import json
import collections
import math
import wave
from pathlib import Path
import time

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
D=module('queue_audio_derivative',Path(__file__).with_name('audio_derivative_v2.py'))
R=module('queue_terminal_recovery',Path(__file__).with_name('recover_asr_terminal.py'))
C=D.C
EXECUTION_SHA=C.sha(__file__)

def inspect_attempt(folder, output, cleanup=None):
    """Recompute the complete source-local failure predicate, including PCM proof."""
    if (folder/'receipt.json').exists():raise ValueError('Admitted receipt cannot be quarantined')
    request_path=folder/'request.json';diagnostic_path=folder/'asr-diagnostic-completion.json'
    request=json.loads(request_path.read_text());diagnostic=json.loads(diagnostic_path.read_text())
    C.verify_artifact(request['acquisition_receipt']);source=C.completed(request['acquisition_receipt']['path'])
    if request['source_id']!=source['source_id'] or diagnostic['request_sha256']!=C.sha(request_path):raise ValueError('Request/source binding mismatch')
    if folder.name!=C.hashlib.sha256(source['source_id'].encode()).hexdigest()[:20]:raise ValueError('Unexpected source item path')
    if diagnostic.get('inference_stream_exhausted') is not True or diagnostic.get('status')!='diagnostic_only_not_admitted':raise ValueError('Inference not fully exhausted')
    if diagnostic['asr']['language_plan']!=request['language_plan']:raise ValueError('Diagnostic language plan differs')
    C.verify_artifact(diagnostic['raw_segments'])
    if Path(diagnostic['raw_segments']['path']).resolve()!=folder.resolve()/'asr-raw-segments.jsonl':raise ValueError('Unexpected diagnostic path')
    raw=[json.loads(x) for x in Path(diagnostic['raw_segments']['path']).read_text().splitlines() if x]
    if not raw or len(raw)!=diagnostic['raw_segment_count']:raise ValueError('Diagnostic row count mismatch')
    duration=source['decoded_16k_mono']['duration_seconds'];previous=0;overflow=[];expected_failure=None
    for i,r in enumerate(raw):
        a,b=float(r['start_repr']),float(r['end_repr'])
        if r['segment_index']!=i or not all(math.isfinite(v) for v in (a,b)) or a<0 or b<a or a<previous or not isinstance(r['text'],str):raise ValueError('Non-EOF failure requires separate review')
        if b>duration+1:
            overflow.append(i)
            if expected_failure is None:expected_failure={'segment_index':i,'start_repr':r['start_repr'],'end_repr':r['end_repr'],'previous_start_repr':repr(previous),'decoded_duration_repr':repr(float(duration)),'reason':'beyond_duration'}
        previous=a
    if len(overflow)<2 or diagnostic.get('first_timestamp_failure')!=expected_failure:raise ValueError('Not the reviewed multiple-EOF failure class')
    if D.CORE.local_model_binding(Path(request['model']['path']))!=request['model']:raise ValueError('Model changed')
    decoder=request['decoder'];proof=source['decoded_16k_mono'];wav=Path(decoder['artifact']['path'])
    expected_command=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',source['audio']['path'],'-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar','16000','-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
    if (decoder['sample_count']!=proof['sample_count'] or decoder['raw_pcm_sha256']!=proof['raw_pcm_sha256'] or decoder['duration_seconds']!=duration or decoder['sample_count']!=round(duration*16000) or decoder['natural_eof'] is not True or decoder['decoder_returncode']!=0 or decoder['cap_bytes']!=D.PCM_CAP or decoder['command']!=expected_command or decoder['artifact']['bytes']!=44+2*decoder['sample_count']):raise ValueError('PCM/source decoder proof differs')
    C.verify_artifact(decoder['stderr_artifact'])
    if diagnostic['asr']['decoder_duration_seconds']!=duration:raise ValueError('Diagnostic duration differs')
    inference=output/'executed-audio-derivative-v2.py';validator=output/'executed-collector-validator.py'
    if C.sha(inference)!=D.EXECUTION_SHA or C.sha(validator)!=C.EXECUTION_SHA:raise ValueError('Executed code differs')
    if cleanup is None:
        C.verify_artifact(decoder['artifact'])
        digest=C.hashlib.sha256();samples=0
        with wave.open(str(wav),'rb') as f:
            if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(1,2,16000):raise ValueError('Unexpected PCM format')
            while True:
                chunk=f.readframes(131072)
                if not chunk:break
                digest.update(chunk);samples+=len(chunk)//2
        if samples!=proof['sample_count'] or digest.hexdigest()!=proof['raw_pcm_sha256']:raise ValueError('Actual PCM differs from source')
    else:
        C.verify_artifact(cleanup);disposal=json.loads(Path(cleanup['path']).read_text())
        expected=Path(disposal['pcm_root']).resolve()/folder.name/'decoded.wav'
        if not expected.is_relative_to(Path('/dev/shm')) or wav.resolve()!=expected or wav.exists():raise ValueError('Cleanup path or disposition invalid')
        if disposal['status']!='removed_only_new_quarantined_pcm' or disposal['policy_code_sha256']!=EXECUTION_SHA or disposal['failed_request']!=C.artifact(request_path) or disposal['removed_artifact']!=decoder['artifact'] or disposal['verified_raw_pcm_sha256']!=proof['raw_pcm_sha256'] or disposal['verified_sample_count']!=proof['sample_count']:raise ValueError('Cleanup lineage differs')
    counts=collections.Counter(r['text'].strip() for r in raw);text,n=counts.most_common(1)[0]
    reason='repeated_output_with_timestamp_overflow' if n>=100 and n/len(raw)>=.5 else 'multiple_segments_outside_audio'
    return {'source_id':source['source_id'],'publication_id':source['publication_id'],'disposition':'held_unadmitted_asr','reason_code':reason,
            'acquisition_receipt':request['acquisition_receipt'],'failed_request':C.artifact(request_path),'exhausted_diagnostic':C.artifact(diagnostic_path),
            'raw_segments':diagnostic['raw_segments'],'original_inference_code':C.artifact(inference),'original_collector_validator':C.artifact(validator),
            'model':request['model'],'diagnostic_metrics':{'raw_segment_count':len(raw),'unique_segment_texts':len(counts),'most_repeated_text':text,'most_repeated_count':n,'ends_beyond_duration_plus_one_second':len(overflow)},
            'failed_pcm_preserved':decoder['artifact']}

def validate_holds(path):
    ledger=json.loads(path.read_text());holds={}
    if ledger.get('status') not in ('reviewed_source_specific_recognition_holds','policy_validated_source_specific_recognition_holds'):raise ValueError('Unrecognized hold ledger')
    initial=None
    if ledger['status']=='policy_validated_source_specific_recognition_holds':
        if ledger.get('policy_code_sha256')!=EXECUTION_SHA:raise ValueError('Unknown quarantine policy')
        C.verify_artifact(ledger['initial_ledger'])
        if ledger['initial_ledger']['sha256']!=ledger['initial_ledger_sha256']:raise ValueError('Initial ledger SHA differs')
        seed=json.loads(Path(ledger['initial_ledger']['path']).read_text())
        if seed['status']!='reviewed_source_specific_recognition_holds':raise ValueError('Initial source review ledger required')
        initial={h['source_id']:h for h in seed['records']}
    for h in ledger['records']:
        for key in ('acquisition_receipt','failed_request','exhausted_diagnostic','raw_segments','original_inference_code','original_collector_validator'):C.verify_artifact(h[key])
        folder=Path(h['failed_request']['path']).parent;output=folder.parent.parent
        expected=inspect_attempt(folder,output,h.get('pcm_cleanup'))
        for k,v in expected.items():
            if h.get(k)!=v:raise ValueError('Hold repeated metadata differs: '+k)
        automatic=h.get('review_status')=='automatic_reviewed_policy_not_manual_source_review'
        if initial is not None:
            if h['source_id'] in initial and h!=initial[h['source_id']]:raise ValueError('Initial hold was changed')
            if h['source_id'] not in initial and not automatic:raise ValueError('New automatic hold lacks policy markers')
        if automatic and (h.get('quarantine_policy_sha256')!=EXECUTION_SHA or h.get('human_reviewed') is not False or h.get('audio_content_listened') is not False):raise ValueError('Automatic hold review markers differ')
        if h.get('pcm_cleanup') and not automatic:raise ValueError('Old failed PCM cannot be disposed by automatic policy')
        if h['source_id'] in holds:raise ValueError('Duplicate hold source')
        holds[h['source_id']]=h
    if initial is not None and not set(initial).issubset(holds):raise ValueError('Initial hold history was removed')
    return holds

def quarantine(folder,output,pcm_root):
    result=inspect_attempt(folder,output)
    result.update({'review_status':'automatic_reviewed_policy_not_manual_source_review','quarantine_policy_sha256':EXECUTION_SHA,'human_reviewed':False,'audio_content_listened':False,
                   'scope':'This exact exhausted recognition attempt has multiple segment ends beyond decoded audio; no transcript admitted and no text/timestamps changed.'})
    return result

def dispose_new_failed_pcm(hold,folder,pcm_root,protected):
    """Only new failed tmpfs PCM: durable bound record before removal, never old PCM."""
    if hold['source_id'] in protected:return
    expected=Path(pcm_root).resolve()/folder.name/'decoded.wav';artifact=hold['failed_pcm_preserved']
    if not expected.is_relative_to(Path('/dev/shm')) or Path(artifact['path']).resolve()!=expected:raise ValueError('Cleanup restricted to expected new tmpfs PCM')
    # Reverify all bytes immediately before recording and removing this new derivative.
    inspect_attempt(folder,folder.parent.parent);C.verify_artifact(artifact)
    request=json.loads(Path(hold['failed_request']['path']).read_text())
    disposal={'status':'removed_only_new_quarantined_pcm','policy_code_sha256':EXECUTION_SHA,'pcm_root':str(Path(pcm_root).resolve()),'failed_request':hold['failed_request'],'removed_artifact':artifact,
              'verified_raw_pcm_sha256':request['decoder']['raw_pcm_sha256'],'verified_sample_count':request['decoder']['sample_count'],'at':C.now()}
    target=folder/'quarantined-pcm-cleanup.json'
    if target.exists():raise ValueError('Existing cleanup receipt requires explicit recovery')
    C.dump(target,disposal);expected.unlink();hold['pcm_cleanup']=C.artifact(target)

def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    with (output/'.queue.lock').open('a') as queue_lock:
        fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        copied=output/'executed-asr-queue-v4.py'
        if copied.exists() and C.sha(copied)!=EXECUTION_SHA:raise ValueError('Queue execution code changed; use explicit successor')
        if not copied.exists():copied.write_bytes(Path(__file__).read_bytes())
        recovery_copy=output/'executed-terminal-recovery-policy.py'
        if recovery_copy.exists() and C.sha(recovery_copy)!=R.EXECUTION_SHA:raise ValueError('Recovery policy changed')
        if not recovery_copy.exists():recovery_copy.write_bytes(Path(R.__file__).read_bytes())
        initial_hold_sha=C.sha(args.holds)
        protected=set(validate_holds(args.holds))
        current_ledger=output/'recognition-holds-v4-current.json'
        if current_ledger.exists():
            current=json.loads(current_ledger.read_text())
            if current.get('initial_ledger_sha256')!=initial_hold_sha:raise ValueError('Different initial hold ledger requires an explicit continuation')
            hold_bytes=current_ledger.read_bytes()
        else:hold_bytes=args.holds.read_bytes()
        hold_sha=C.hashlib.sha256(hold_bytes).hexdigest()
        hold_copy=output/('recognition-holds-'+hold_sha[:20]+'.json')
        if not hold_copy.exists():hold_copy.write_bytes(hold_bytes)
        if hold_copy.read_bytes()!=hold_bytes:raise ValueError('Hold snapshot changed')
        holds=validate_holds(hold_copy)
        def save_holds():
            nonlocal hold_sha,hold_copy
            value={'schema_version':1,'status':'policy_validated_source_specific_recognition_holds','created_at':C.now(),
                   'initial_ledger_sha256':initial_hold_sha,'initial_ledger':C.artifact(args.holds),'policy_code_sha256':EXECUTION_SHA,'records':list(holds.values())}
            body=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode();hold_sha=C.hashlib.sha256(body).hexdigest()
            hold_copy=output/('recognition-holds-'+hold_sha[:20]+'.json')
            if not hold_copy.exists():hold_copy.write_bytes(body)
            validate_holds(hold_copy);C.dump(current_ledger,value)
        def event(status,**kwargs):
            record={'at':C.now(),'status':status,'queue_version':4,'recognition_hold_count':len(holds),
                    'recognition_holds':[{k:h[k] for k in ('source_id','publication_id','disposition','reason_code')} for h in holds.values()],
                    'hold_ledger':C.artifact(hold_copy),**kwargs}
            with (output/'queue-v4-events.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
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
                            try:
                                h=quarantine(folder,output,args.pcm_root)
                            except Exception as hold_error:
                                event('halted_unrecoverable_diagnostic',source_id=sid,error=str(hold_error),terminal_repair_error=str(exc));raise
                            holds[sid]=h;save_holds()
                            dispose_new_failed_pcm(h,folder,args.pcm_root,protected);save_holds();event('source_specific_recognition_quarantined',source_id=sid,reason_code=h['reason_code'])
                            # Rebuild the selected snapshot with the newly held source excluded.
                            continue
                        else:
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
