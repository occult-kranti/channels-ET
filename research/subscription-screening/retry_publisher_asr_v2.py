#!/usr/bin/env python3
"""One experimental, nonconditioning multilingual-tiny ASR retry.

The original failed English-only edition remains held. A successful result is a
different recognition edition; structural checks and repetition diagnostics do
not establish word accuracy or prove that repeated words were absent in audio.
"""
from __future__ import annotations
import argparse
import collections
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

DERIVATIVE_SHA='70754e0aeef744f3bd04cb14013e7e4bb67ef778bb4b8b515945d0a816147c99'
DERIVATIVE_PATH=Path(__file__).with_name('audio_derivative_v2.py')
if hashlib.sha256(DERIVATIVE_PATH.read_bytes()).hexdigest()!=DERIVATIVE_SHA:
    raise RuntimeError('Frozen decoder/helper version changed')
SPEC=importlib.util.spec_from_file_location('retry_bound_derivative',DERIVATIVE_PATH)
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)
C=D.C;CORE=D.CORE
EXECUTION_SHA=C.sha(__file__)
SOURCE_ID='publisher-rss:akanksshaa:rss:b9fd4b8c29ce9611'
EDITION_SUFFIX=':asr:tiny-multilingual-no-conditioning-retry1'
MODEL_REVISION='d90ca5fe260221311c53c58e660288d3deb8d356'
DEFAULT_MODEL=Path('/workspace/channels-et-private/bashar-ra-2026-11/model-cache/whisper-tiny-multilingual-d90ca5fe')
MAX_RAW_SEGMENTS=10000
MAX_RAW_BYTES=20*1024**2
MAX_INFERENCE_SECONDS=1800
SETTINGS={'language':'en','beam_size':5,'temperature':0,'vad_filter':True,
          'vad_parameters':{'min_silence_duration_ms':500},'condition_on_previous_text':False}

def check_code():
    D.check_code()
    if C.sha(__file__)!=EXECUTION_SHA or C.sha(DERIVATIVE_PATH)!=DERIVATIVE_SHA:
        raise ValueError('Retry implementation or bound decoder changed')

def raw_namespace(row):
    return SimpleNamespace(start=float(row['start_repr']),end=float(row['end_repr']),text=row['text'],
        avg_logprob=None if row.get('avg_logprob_repr') in (None,'None') else float(row['avg_logprob_repr']),
        no_speech_prob=None if row.get('no_speech_prob_repr') in (None,'None') else float(row['no_speech_prob_repr']))

def output_metrics(raw,duration):
    counts=collections.Counter(r['text'].strip() for r in raw if r['text'].strip())
    most_text,most_count=counts.most_common(1)[0] if counts else ('',0)
    longest=current=0;last=None;strict_over=guard_over=invalid=0
    for i,r in enumerate(raw):
        text=r['text'].strip()
        current=current+1 if text and text==last else int(bool(text));last=text
        longest=max(longest,current)
        a,b=float(r['start_repr']),float(r['end_repr'])
        if math.isfinite(b):strict_over+=int(b>duration);guard_over+=int(b>duration+1)
        invalid+=int(not all(math.isfinite(v) for v in (a,b)) or a<0 or b<a)
    nonempty=sum(counts.values())
    return {'raw_segment_count':len(raw),'nonempty_segment_count':nonempty,
            'unique_nonempty_texts':len(counts),'most_repeated_text':most_text,
            'most_repeated_count':most_count,'most_repeated_fraction':most_count/nonempty if nonempty else 0,
            'longest_identical_nonempty_run':longest,'ends_beyond_strict_audio_eof':strict_over,
            'ends_beyond_frozen_validator_eof_plus_one_second':guard_over,'invalid_endpoint_pairs':invalid,
            'scope':'Recognition-output diagnostics; no human comparison with spoken content or word error rate.'}

def classify(raw,duration):
    """Return an admission decision without deleting words or broadening timing."""
    metrics=output_metrics(raw,duration)
    if not raw or metrics['nonempty_segment_count']==0:
        return {'admitted':False,'reason':'empty_recognition','metrics':metrics,'segments':[],'normalization_status':None,'quality':None}
    if any(r.get('segment_index')!=i or not isinstance(r.get('text'),str) for i,r in enumerate(raw)):
        raise ValueError('Raw segment indices/text are invalid')
    first_failure=None;quality=None;normalization='unadjusted'
    try:segments=CORE.normalize_segments([raw_namespace(r) for r in raw],duration)
    except CORE.TimestampValidationError as exc:
        first_failure=exc.diagnostic
        if first_failure['reason']!='beyond_duration' or first_failure['segment_index']!=len(raw)-1:
            return {'admitted':False,'reason':'invalid_nonterminal_or_multiple_timestamps','metrics':metrics,
                    'segments':[],'normalization_status':None,'quality':None,'first_timestamp_failure':first_failure}
        try:segments,quality=CORE.repair_terminal_end(raw,duration,max_overrun_seconds=30)
        except ValueError:
            return {'admitted':False,'reason':'terminal_timestamp_outside_reviewed_policy','metrics':metrics,
                    'segments':[],'normalization_status':None,'quality':None,'first_timestamp_failure':first_failure}
        normalization='terminal_end_display_repair_text_unchanged'
    if [s['text'] for s in segments]!=[r['text'].strip() for r in raw if r['text'].strip()]:
        raise ValueError('Recognition words changed during normalization')
    # Conservative corpus-quality hold. Repetition may be real speech; no such claim is inferred.
    if (metrics['most_repeated_count']>=100 and metrics['most_repeated_fraction']>=.5) or metrics['longest_identical_nonempty_run']>=100:
        return {'admitted':False,'reason':'repetition_quality_hold_pending_audio_review','metrics':metrics,'segments':[],
                'normalization_status':normalization,'quality':quality,'first_timestamp_failure':first_failure}
    return {'admitted':True,'reason':'structural_checks_passed_accuracy_unverified','metrics':metrics,
            'segments':segments,'normalization_status':normalization,'quality':quality,'first_timestamp_failure':first_failure}

def bind_model(model_path):
    provenance=model_path/'manifest.json';m=json.loads(provenance.read_text())
    if m.get('model')!='Systran/faster-whisper-tiny' or m.get('revision')!=MODEL_REVISION or m.get('status')!='downloaded_and_upstream_hash_verified':
        raise ValueError('Only the existing pinned multilingual-tiny checkpoint is permitted')
    for f in m['files']:
        if Path(f['path']).name!=f['path']:raise ValueError('Unsafe checkpoint manifest filename')
        C.verify_artifact({'path':str(model_path/f['path']),'sha256':f['sha256'],'bytes':f['bytes']})
    binding=CORE.local_model_binding(model_path)
    if binding['language_mode']!='multilingual':raise ValueError('Fallback requires multilingual checkpoint')
    indexed={f['path']:f for f in m['files']}
    for f in binding['files']:
        if f['path'] not in indexed or any(f[k]!=indexed[f['path']][k] for k in ('sha256','bytes')):
            raise ValueError('Loaded checkpoint files differ from pinned download manifest')
    return binding,{'model':'Systran/faster-whisper-tiny','revision':MODEL_REVISION,'license':m['license'],
                    'pinned_download_manifest':C.artifact(provenance)}

def validate_hold(holds,acquisition):
    if holds.get('status')!='reviewed_source_specific_recognition_holds':raise ValueError('Reviewed hold ledger required')
    matches=[h for h in holds['records'] if h['source_id']==SOURCE_ID]
    if len(matches)!=1:raise ValueError('Exactly the one specified failed source must be held')
    h=matches[0]
    if h['disposition']!='held_unadmitted_asr' or h['reason_code']!='multiple_segments_outside_audio':
        raise ValueError('Unrecognized held-edition reason')
    for key in ('acquisition_receipt','failed_request','exhausted_diagnostic','raw_segments','original_inference_code','original_collector_validator'):
        C.verify_artifact(h[key])
    if h['original_inference_code']['sha256']!=DERIVATIVE_SHA or h['original_collector_validator']['sha256']!=C.EXECUTION_SHA:
        raise ValueError('Original failed-edition code binding differs')
    source=C.completed(h['acquisition_receipt']['path'])
    if source['source_id']!=SOURCE_ID or source['publication_id']!=h['publication_id']:
        raise ValueError('Held source/publication identity differs')
    actual=[r for r in acquisition['records'] if r['source_id']==SOURCE_ID]
    if len(actual)!=1 or actual[0]!=source:raise ValueError('Current collection source differs from exact held audio edition')
    if acquisition.get('status')!='frame_complete':raise ValueError('Collection must finish before this RAM-bound retry')
    request=json.loads(Path(h['failed_request']['path']).read_text());diag=json.loads(Path(h['exhausted_diagnostic']['path']).read_text())
    if request['source_id']!=SOURCE_ID or request['acquisition_receipt']!=h['acquisition_receipt'] or request['model']!=h['model']:
        raise ValueError('Failed request lineage differs')
    if CORE.local_model_binding(Path(h['model']['path']))!=h['model']:
        raise ValueError('Original failed-model file binding changed')
    if diag['request_sha256']!=h['failed_request']['sha256'] or diag['raw_segments']!=h['raw_segments'] or diag['inference_stream_exhausted'] is not True:
        raise ValueError('Original diagnostic is not an exact exhausted inference stream')
    raw=[json.loads(line) for line in Path(h['raw_segments']['path']).read_text().splitlines() if line]
    if len(raw)!=diag['raw_segment_count']:raise ValueError('Original diagnostic segment count differs')
    if source['source']['language']!='en':raise ValueError('The trial requires explicit English source metadata')
    return h,source,output_metrics(raw,source['decoded_16k_mono']['duration_seconds'])

def resource_gate(output,pcm_root):
    if shutil.disk_usage(output.parent).free<C.FLOOR+32*1024**2:
        raise C.ResourceStop('Retry disk admission would consume2GiBfloor+32MiBtext reserve')
    if shutil.disk_usage(pcm_root.parent).free<C.FLOOR+D.PCM_CAP:
        raise C.ResourceStop('Retry tmpfs admission would consume its free floor and PCM allowance')
    maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip()
    current=int(Path('/sys/fs/cgroup/memory.current').read_text())
    if maximum=='max' or int(maximum)-current<D.PCM_CAP+512*1024**2:
        raise C.ResourceStop('Insufficient finite cgroup memory headroom for retry PCM/model')
    return {'disk_free_bytes':shutil.disk_usage(output.parent).free,'tmpfs_free_bytes':shutil.disk_usage(pcm_root.parent).free,
            'cgroup_maximum_bytes':int(maximum),'cgroup_current_bytes':current,'pcm_cap_bytes':D.PCM_CAP,
            'additional_model_headroom_bytes':512*1024**2}

def reserve_once(hold,output,request_binding):
    marker=Path(hold['failed_request']['path']).parent/'experimental-retry1-reservation.json'
    reservation={'status':'single_experimental_retry_reserved','source_id':SOURCE_ID,'attempt':1,'output':str(output),
                 'retry_code_sha256':EXECUTION_SHA,'request_binding':request_binding,'reserved_at':C.now()}
    with marker.open('x') as f:json.dump(reservation,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return C.artifact(marker)

def recognize(wav,folder,model_path,language_plan,cpu_threads):
    from faster_whisper import WhisperModel
    engine=WhisperModel(str(model_path),device='cpu',compute_type='int8',cpu_threads=cpu_threads,num_workers=1,local_files_only=True)
    if not engine.model.is_multilingual:raise ValueError('Loaded fallback engine is not multilingual')
    stream,info=engine.transcribe(str(wav),**SETTINGS)
    raw=[];raw_path=folder/'asr-raw-segments.jsonl';started=time.monotonic();size=0
    with raw_path.open('x') as target:
        for index,s in enumerate(stream):
            r={'segment_index':index,'start_repr':repr(float(s.start)),'end_repr':repr(float(s.end)),'text':s.text,
               'avg_logprob_repr':repr(getattr(s,'avg_logprob',None)),'no_speech_prob_repr':repr(getattr(s,'no_speech_prob',None))}
            line=json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n';size+=len(line.encode())
            if index>=MAX_RAW_SEGMENTS or size>MAX_RAW_BYTES or time.monotonic()-started>MAX_INFERENCE_SECONDS:
                raise C.ResourceStop('Single retry recognition diagnostic limit reached; unadmitted partial preserved')
            target.write(line);target.flush();raw.append(r)
            if len(raw)%100==0:print(json.dumps({'stage':'fallback_progress','segments':len(raw),'last_end':r['end_repr']}),flush=True)
        os.fsync(target.fileno())
    report={'language_requested':'en','language_reported':info.language,'language_plan':language_plan,
            'reported_language_probability':info.language_probability,'decoder_duration_seconds':info.duration,
            'duration_after_vad_seconds':info.duration_after_vad,'settings':SETTINGS,'device':'cpu','compute_type':'int8',
            'cpu_threads':cpu_threads,'num_workers':1,'local_files_only':True,'human_reviewed':False,
            'speaker_diarization_performed':False,'named_entities_verified':False,'model_probabilities_calibrated':False,
            'scope':'Full decoded audio submitted; recognition/VAD may omit or invent speech. This is one experimental alternate edition.'}
    return raw,report

def verify_result(receipt_path):
    r=json.loads(receipt_path.read_text())
    if r['status']!='completed' or r['source_id']!=SOURCE_ID+EDITION_SUFFIX:raise ValueError('Fallback identity/status differs')
    if (r['retry_code_sha256']!=EXECUTION_SHA or r['decoder_helper_sha256']!=DERIVATIVE_SHA
            or r['collector_validator_sha256']!=C.EXECUTION_SHA or r['legacy_helper_sha256']!=C.FROZEN_CORE_SHA):
        raise ValueError('Fallback code bindings differ')
    expected_codes={'executed-retry.py':EXECUTION_SHA,'executed-decoder-helper.py':DERIVATIVE_SHA,
                    'executed-collector-validator.py':C.EXECUTION_SHA,'executed-legacy-helper.py':C.FROZEN_CORE_SHA}
    for name,digest in expected_codes.items():
        a=r['executed_code'][name];C.verify_artifact(a)
        if a['sha256']!=digest:raise ValueError('Fallback executed-code snapshot differs')
    C.verify_artifact(r['acquisition_receipt']);source=C.completed(r['acquisition_receipt']['path'])
    if source['source_id']!=SOURCE_ID or r['source']!=source['source'] or r['publication_id']!=source['publication_id']:
        raise ValueError('Fallback source lineage differs')
    for a in r['outputs'].values():C.verify_artifact(a)
    C.verify_artifact(r['raw_diagnostic']);C.verify_artifact(r['request'])
    request=json.loads(Path(r['request']['path']).read_text())
    if request['source_id']!=SOURCE_ID or request['edition_source_id']!=SOURCE_ID+EDITION_SUFFIX or request['attempt']!=1:
        raise ValueError('Fallback request source/edition/attempt differs')
    if request['model']!=r['model'] or request['settings']!=SETTINGS or request['acquisition_receipt']!=r['acquisition_receipt']:
        raise ValueError('Fallback model/settings/input request differs')
    if request['executed_code']!=r['executed_code']:raise ValueError('Fallback request executed-code bindings differ')
    model,provenance=bind_model(Path(r['model']['path']))
    if model!=r['model'] or provenance!=r['model_provenance'] or request['model_provenance']!=provenance:
        raise ValueError('Fallback checkpoint/provenance binding differs')
    languages=CORE.language_plan({'source_language':'en','source_language_status':'declared'},model,'en')
    if request['language_plan']!=languages or r['asr']['language_plan']!=languages:
        raise ValueError('Fallback language plan differs')
    runtime={'device':'cpu','compute_type':'int8','num_workers':1,'local_files_only':True}
    if any(request[k]!=v or r['asr'][k]!=v for k,v in runtime.items()):raise ValueError('Fallback runtime settings differ')
    if request['cpu_threads'] not in (1,2) or r['asr']['cpu_threads']!=request['cpu_threads']:
        raise ValueError('Fallback CPU thread binding differs')
    if r['asr']['settings']!=SETTINGS or r['asr']['language_reported']!='en' or r['asr']['language_requested']!='en':
        raise ValueError('Fallback inference settings/language differ')
    decoder=r['decoder'];proof=source['decoded_16k_mono']
    if decoder!=request['decoder']:raise ValueError('Fallback repeated decoder proof differs')
    count=decoder['sample_count'];duration=decoder['duration_seconds']
    if (isinstance(count,bool) or not isinstance(count,int) or count<=0 or count!=proof['sample_count']
            or not math.isfinite(duration) or abs(duration-count/D.RATE)>1/D.RATE
            or duration!=proof['duration_seconds'] or decoder['raw_pcm_sha256']!=proof['raw_pcm_sha256']):
        raise ValueError('Fallback PCM hash/sample/duration differs from retained-source decode')
    if (decoder['natural_eof'] is not True or decoder['decoder_returncode']!=0 or decoder['cap_bytes']!=D.PCM_CAP
            or decoder['artifact']['bytes']!=count*2+44 or decoder['artifact']['bytes']>D.PCM_CAP):
        raise ValueError('Fallback decoder completion/cap/WAV accounting differs')
    C.verify_artifact(decoder['stderr_artifact'])
    expected_decode=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',source['audio']['path'],
                     '-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar',str(D.RATE),
                     '-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
    if decoder['command']!=expected_decode or abs(r['asr']['decoder_duration_seconds']-duration)>.1:
        raise ValueError('Fallback decoder command/reported inference duration differs')
    for key in ('acquisition_snapshot','hold_snapshot','reservation','resource_plan'):C.verify_artifact(request[key])
    acquisition=json.loads(Path(request['acquisition_snapshot']['path']).read_text())
    holds=json.loads(Path(request['hold_snapshot']['path']).read_text())
    h,held_source,original_metrics=validate_hold(holds,acquisition)
    if held_source!=source or request['original_failed_hold']!=h or r['original_failed_edition_retained'] is not True:
        raise ValueError('Fallback failed-edition history differs')
    reservation=json.loads(Path(request['reservation']['path']).read_text())
    expected_reservation_path=Path(h['failed_request']['path']).parent/'experimental-retry1-reservation.json'
    expected_binding={'acquisition_sha256':request['acquisition_snapshot']['sha256'],'hold_ledger_sha256':request['hold_snapshot']['sha256'],
                      'model_files_sha256':model['files_sha256'],'condition_on_previous_text':False,'cpu_threads':request['cpu_threads']}
    if (Path(request['reservation']['path'])!=expected_reservation_path or reservation['status']!='single_experimental_retry_reserved'
            or reservation['source_id']!=SOURCE_ID or reservation['attempt']!=1 or reservation['output']!=str(receipt_path.parent)
            or reservation['retry_code_sha256']!=EXECUTION_SHA or reservation['request_binding']!=expected_binding):
        raise ValueError('Fallback one-trial reservation differs')
    raw=[json.loads(line) for line in Path(r['raw_diagnostic']['path']).read_text().splitlines() if line]
    decision=classify(raw,source['decoded_16k_mono']['duration_seconds'])
    if not decision['admitted'] or decision['metrics']!=r['comparison']['retry_output_metrics']:
        raise ValueError('Fallback no longer passes its recorded structural/quality checks')
    if (r['comparison']['original_failed_output_metrics']!=original_metrics
            or r['comparison']['accuracy_comparison_performed'] is not False or r['comparison']['original_audio_listened'] is not False):
        raise ValueError('Fallback comparison/human-review scope differs')
    if (r['normalization_status']!=decision['normalization_status']
            or r['normalization_recovery']!=({'quality':decision['quality']} if decision['quality'] else {})):
        raise ValueError('Fallback normalization status/provenance differs')
    C.verify_artifact(r['diagnostic_completion']);completion=json.loads(Path(r['diagnostic_completion']['path']).read_text())
    if (completion['inference_stream_exhausted'] is not True or completion['raw_segments']!=r['raw_diagnostic']
            or completion['request']!=r['request'] or completion['raw_segment_count']!=len(raw) or completion['asr']!=r['asr']):
        raise ValueError('Fallback exhausted diagnostic lineage differs')
    if completion['decision']!={k:v for k,v in decision.items() if k!='segments'} or completion['comparison']!=r['comparison']:
        raise ValueError('Fallback diagnostic decision/comparison differs')
    n=json.loads(Path(r['outputs']['normalized']['path']).read_text());turns=n['turns']
    if n['source_id']!=r['source_id'] or n['publication_id']!=r['publication_id'] or n['speaker_identity_verified'] is not False or n['no_answer_identified'] is not True:
        raise ValueError('Fallback normalized identity/role contract differs')
    if n['normalization_status']!=decision['normalization_status'] or n['timestamp_quality']!=decision['quality'] or n['audio_representation']!=source['input_representation']:
        raise ValueError('Fallback normalized timing-quality/representation differs')
    if len(turns)!=len(decision['segments']):raise ValueError('Fallback turn count differs')
    for i,(t,s) in enumerate(zip(turns,decision['segments'])):
        expected_turn={'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds'],
                       **({'timestamp_repair':s['timestamp_repair'],'original_end_seconds':s['original_end_seconds']} if 'timestamp_repair' in s else {})}
        if t!=expected_turn:
            raise ValueError('Fallback normalized text/timings differ from raw diagnostic')
    text='\n'.join(t['text'] for t in turns)
    if n['text']!=text or Path(r['outputs']['text']['path']).read_text()!=text+'\n' or r['whitespace_words']!=len(text.split()) or r['segment_count']!=len(turns):
        raise ValueError('Fallback text/word/segment accounting differs')
    srt='\n\n'.join(f"{i+1}\n{CORE.timestamp(t['start_seconds'],srt=True)} --> {CORE.timestamp(t['end_seconds'],srt=True)}\n{t['text']}" for i,t in enumerate(turns))+'\n'
    if Path(r['outputs']['srt']['path']).read_text()!=srt:raise ValueError('Fallback SRT differs')
    return r

def run(args):
    check_code();output=args.output.resolve();pcm_root=args.pcm_root.resolve();repo=Path(__file__).resolve().parents[2]
    if output.is_relative_to(repo) or not str(pcm_root).startswith('/dev/shm/'):
        raise ValueError('Fallback output must be private and PCM must use a separate /dev/shm directory')
    if output.exists() or pcm_root.exists():raise ValueError('Fallback output/PCM phase already exists; single trial cannot overwrite it')
    raw_acq=args.acquisition.read_bytes();acquisition=json.loads(raw_acq);raw_hold=args.holds.read_bytes();holds=json.loads(raw_hold)
    hold,source,baseline_metrics=validate_hold(holds,acquisition)
    model,model_provenance=bind_model(args.model.resolve())
    languages=CORE.language_plan({'source_language':'en','source_language_status':'declared'},model,'en')
    output.parent.mkdir(parents=True,exist_ok=True);pcm_root.parent.mkdir(parents=True,exist_ok=True)
    resources=resource_gate(output,pcm_root)
    request_binding={'acquisition_sha256':hashlib.sha256(raw_acq).hexdigest(),'hold_ledger_sha256':hashlib.sha256(raw_hold).hexdigest(),
                     'model_files_sha256':model['files_sha256'],'condition_on_previous_text':False,'cpu_threads':args.cpu_threads}
    reservation=reserve_once(hold,output,request_binding)
    output.mkdir();pcm_root.mkdir()
    with (output/'.retry.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        snapshots={}
        for path,name in [(Path(__file__),'executed-retry.py'),(DERIVATIVE_PATH,'executed-decoder-helper.py'),(Path(C.__file__),'executed-collector-validator.py'),(D.CORE_PATH,'executed-legacy-helper.py')]:
            dest=output/name;dest.write_bytes(path.read_bytes());snapshots[name]=C.artifact(dest)
        (output/'acquisition-snapshot.json').write_bytes(raw_acq);(output/'hold-snapshot.json').write_bytes(raw_hold)
        C.dump(output/'resource-plan.json',resources)
        wav=pcm_root/'decoded.wav'
        C.dump(output/'manifest.json',{'status':'single_experimental_retry_running','records':[],'source_id':SOURCE_ID,
                'reservation':reservation,'independent_review_status':'pending','original_failed_edition_hold_remains':True,'created_at':C.now()})
        try:
            decoder=D.capped_pcm(Path(source['audio']['path']),wav,source['decoded_16k_mono'])
            log=output/'pcm-decoder.log';shutil.copyfile(decoder['stderr_artifact']['path'],log)
            if C.sha(log)!=decoder['stderr_artifact']['sha256']:raise ValueError('PCM decoder log copy mismatch')
            decoder['stderr_artifact']=C.artifact(log)
            request={'source_id':SOURCE_ID,'edition_source_id':SOURCE_ID+EDITION_SUFFIX,'attempt':1,
                     'acquisition_receipt':hold['acquisition_receipt'],'original_failed_hold':hold,
                     'acquisition_snapshot':C.artifact(output/'acquisition-snapshot.json'),'hold_snapshot':C.artifact(output/'hold-snapshot.json'),
                     'model':model,'model_provenance':model_provenance,'language_plan':languages,'settings':SETTINGS,
                     'cpu_threads':args.cpu_threads,'device':'cpu','compute_type':'int8','num_workers':1,'local_files_only':True,
                     'decoder':decoder,'executed_code':snapshots,'reservation':reservation,'resource_plan':C.artifact(output/'resource-plan.json'),
                     'limits':{'max_raw_segments':MAX_RAW_SEGMENTS,'max_raw_bytes':MAX_RAW_BYTES,'max_inference_seconds':MAX_INFERENCE_SECONDS},
                     'created_at':C.now()}
            C.dump(output/'request.json',request)
            raw,asr=recognize(wav,output,args.model.resolve(),languages,args.cpu_threads)
            decision=classify(raw,decoder['duration_seconds'])
            if asr['language_reported']!='en' or abs(asr['decoder_duration_seconds']-decoder['duration_seconds'])>.1:
                decision.update(admitted=False,reason='reported_language_or_decoder_duration_mismatch',segments=[])
            check_code()
            if bind_model(args.model.resolve())[0]!=model:raise ValueError('Fallback checkpoint changed during inference')
            comparison={'original_failed_output_metrics':baseline_metrics,'retry_output_metrics':decision['metrics'],
                        'accuracy_comparison_performed':False,'original_audio_listened':False,
                        'scope':'Two recognition editions; different model and conditioning confounded. Repetition reduction is not measured accuracy.'}
            completion={'status':'inference_exhausted','inference_stream_exhausted':True,'raw_segment_count':len(raw),
                        'raw_segments':C.artifact(output/'asr-raw-segments.jsonl'),'request':C.artifact(output/'request.json'),
                        'asr':asr,'decision':{k:v for k,v in decision.items() if k!='segments'},'comparison':comparison,'created_at':C.now()}
            C.dump(output/'diagnostic-completion.json',completion)
            if not decision['admitted']:
                C.dump(output/'manifest.json',{'status':'experimental_retry_unadmitted','records':[],'source_id':SOURCE_ID,
                    'reason':decision['reason'],'diagnostic':C.artifact(output/'diagnostic-completion.json'),
                    'original_hold_retained':True,'independent_review_status':'pending','created_at':C.now()})
                return
            segments=decision['segments'];text='\n'.join(s['text'] for s in segments)
            turns=[{'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds'],
                    **({'timestamp_repair':s['timestamp_repair'],'original_end_seconds':s['original_end_seconds']} if 'timestamp_repair' in s else {})} for i,s in enumerate(segments)]
            normalized={'source_id':SOURCE_ID+EDITION_SUFFIX,'publication_id':source['publication_id'],'text':text,'turns':turns,
                        'no_answer_identified':True,'speaker_identity_verified':False,'audio_representation':source['input_representation'],
                        'normalization_status':decision['normalization_status'],'timestamp_quality':decision['quality'],
                        'scope':'Distinct one-off multilingual, nonconditioning recognition edition; accuracy and speaker identities remain unverified.'}
            C.dump(output/'transcript.json',normalized);(output/'transcript.txt').write_text(text+'\n')
            (output/'transcript.srt').write_text('\n\n'.join(f"{i+1}\n{CORE.timestamp(s['start_seconds'],srt=True)} --> {CORE.timestamp(s['end_seconds'],srt=True)}\n{s['text']}" for i,s in enumerate(segments))+'\n')
            result={'status':'completed','source_id':normalized['source_id'],'publication_id':source['publication_id'],'source':source['source'],
                    'acquisition_receipt':hold['acquisition_receipt'],'model':model,'model_provenance':model_provenance,'asr':asr,'decoder':decoder,
                    'outputs':{kind:C.artifact(output/name) for kind,name in [('normalized','transcript.json'),('text','transcript.txt'),('srt','transcript.srt')]},
                    'raw_diagnostic':C.artifact(output/'asr-raw-segments.jsonl'),'request':C.artifact(output/'request.json'),
                    'diagnostic_completion':C.artifact(output/'diagnostic-completion.json'),'comparison':comparison,
                    'whitespace_words':len(text.split()),'segment_count':len(segments),'normalization_status':decision['normalization_status'],
                    'normalization_recovery':{'quality':decision['quality']} if decision['quality'] else {},
                    'retry_code_sha256':EXECUTION_SHA,'decoder_helper_sha256':DERIVATIVE_SHA,'collector_validator_sha256':C.EXECUTION_SHA,
                    'legacy_helper_sha256':C.FROZEN_CORE_SHA,'executed_code':snapshots,'original_failed_edition_retained':True,
                    'versions':CORE.versions(True),'created_at':C.now()}
            C.dump(output/'receipt.json',result);verify_result(output/'receipt.json')
            C.verify_artifact(decoder['artifact']);wav.unlink()
            C.dump(output/'pcm-cleanup.json',{'removed_only_new_retry_pcm':decoder['artifact'],'retained_retry_receipt':C.artifact(output/'receipt.json'),'at':C.now()})
            C.dump(output/'manifest.json',{'status':'single_experimental_retry_completed_pending_review','records':[result],
                    'independent_review_status':'pending',
                    'original_failed_edition_hold_remains':True,'scope':'A distinct completed alternate edition; no word-accuracy validation or replacement of the original hold.',
                    'created_at':C.now()})
            print(json.dumps({'status':'completed','source_id':normalized['source_id'],'words':len(text.split()),'segments':len(segments),
                              'normalization_status':decision['normalization_status'],'repeated_fraction':decision['metrics']['most_repeated_fraction']}),flush=True)
        except BaseException as exc:
            C.dump(output/'manifest.json',{'status':'single_experimental_retry_failed','records':[],
                    'error_type':type(exc).__name__,'error':str(exc),'independent_review_status':'pending',
                    'attempt_reserved_and_not_repeatable':True,'created_at':C.now()})
            raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--holds',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pcm-root',type=Path,required=True)
    p.add_argument('--model',type=Path,default=DEFAULT_MODEL);p.add_argument('--cpu-threads',type=int,choices=(1,2),default=1)
    run(p.parse_args(argv))

if __name__=='__main__':main()
