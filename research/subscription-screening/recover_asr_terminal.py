#!/usr/bin/env python3
"""Explicit last-segment display-time recovery of an exhausted ASR diagnostic.

No inference or recognized-word edits. This cannot validate terminal recognition
or alignment: it only bounds a single final displayed end to existing audio.
"""
import argparse
import importlib.util
import json
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('asr_derivative_bound',Path(__file__).with_name('audio_derivative_v2.py'))
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)
C=D.C
EXECUTION_SHA=C.sha(__file__)

def validate_diagnostic(folder):
    request_path=folder/'request.json';completion_path=folder/'asr-diagnostic-completion.json'
    request=json.loads(request_path.read_text());completion=json.loads(completion_path.read_text())
    if completion['status']!='diagnostic_only_not_admitted' or completion['inference_stream_exhausted'] is not True:
        raise ValueError('Only an exhausted, unadmitted inference diagnostic can be recovered')
    if completion['request_sha256']!=C.sha(request_path):raise ValueError('Diagnostic request binding mismatch')
    C.verify_artifact(completion['raw_segments'])
    raw=[json.loads(line) for line in Path(completion['raw_segments']['path']).read_text().splitlines() if line]
    if len(raw)!=completion['raw_segment_count']:raise ValueError('Raw diagnostic segment count mismatch')
    failure=completion.get('first_timestamp_failure') or {}
    if failure.get('reason')!='beyond_duration' or failure.get('segment_index')!=len(raw)-1:
        raise ValueError('Only the final-segment end-overrun failure is eligible')
    C.verify_artifact(request['acquisition_receipt'])
    source=C.completed(request['acquisition_receipt']['path'])
    if request['source_id']!=source['source_id']:raise ValueError('Request source identity mismatch')
    if request['decoder']['sample_count']!=source['decoded_16k_mono']['sample_count'] or request['decoder']['raw_pcm_sha256']!=source['decoded_16k_mono']['raw_pcm_sha256']:
        raise ValueError('Failed-attempt decoder differs from acquisition proof')
    rows,quality=D.CORE.repair_terminal_end(raw,source['decoded_16k_mono']['duration_seconds'],max_overrun_seconds=30)
    if [r['text'] for r in rows]!=[r['text'].strip() for r in raw if r['text'].strip()]:
        raise ValueError('Recovery changed recognized text')
    return request,completion,source,rows,quality

def recover(folder):
    D.check_code();folder=folder.resolve()
    inference_copy=folder.parent.parent/'executed-audio-derivative-v2.py'
    validator_copy=folder.parent.parent/'executed-collector-validator.py'
    if C.sha(inference_copy)!=D.EXECUTION_SHA or C.sha(validator_copy)!=C.EXECUTION_SHA:
        raise ValueError('Original failed-phase executed code differs from bound inference helpers')
    if (folder/'receipt.json').exists():raise ValueError('An admitted receipt already exists; never overwrite it')
    request,completion,source,segments,quality=validate_diagnostic(folder)
    model_path=Path(request['model']['path'])
    if D.CORE.local_model_binding(model_path)!=request['model']:raise ValueError('Inference model binding changed')
    C.verify_artifact(request['decoder']['artifact'])
    out=folder/'terminal-recovery';out.mkdir(exist_ok=False)
    copied=out/'executed-recovery.py';copied.write_bytes(Path(__file__).read_bytes())
    text='\n'.join(s['text'] for s in segments)
    turns=[{'turn_id':f'segment-{i+1}','role':'unknown','text':s['text'],'start_seconds':s['start_seconds'],
            'end_seconds':s['end_seconds'],**({'original_end_seconds':s['original_end_seconds'],'timestamp_repair':s['timestamp_repair']}
                                            if 'timestamp_repair' in s else {})} for i,s in enumerate(segments)]
    normalized={'source_id':source['source_id']+':asr:tiny-en-v2','publication_id':source['publication_id'],
                'text':text,'turns':turns,'no_answer_identified':True,'speaker_identity_verified':False,
                'audio_representation':'full_duration_lossy_opus_derivative',
                'normalization_status':'terminal_end_display_repair_text_unchanged','timestamp_quality':quality,
                'scope':'One final displayed end clipped to actual audio EOF; terminal recognized text and alignment remain unverified.'}
    C.dump(out/'transcript.json',normalized);(out/'transcript.txt').write_text(text+'\n')
    (out/'transcript.srt').write_text('\n\n'.join(f"{i+1}\n{D.CORE.timestamp(s['start_seconds'],srt=True)} --> {D.CORE.timestamp(s['end_seconds'],srt=True)}\n{s['text']}" for i,s in enumerate(segments))+'\n')
    receipt={'status':'completed','source_id':normalized['source_id'],'publication_id':source['publication_id'],
             'source':source['source'],'acquisition_receipt':request['acquisition_receipt'],'model':request['model'],
             'asr':completion['asr'],'decoder':request['decoder'],
             'outputs':{kind:C.artifact(out/name) for kind,name in [('normalized','transcript.json'),('text','transcript.txt'),('srt','transcript.srt')]},
             'whitespace_words':len(text.split()),'segment_count':len(segments),'created_at':C.now(),
             'versions':D.CORE.versions(True),'successor_sha256':D.EXECUTION_SHA,'legacy_helper_sha256':C.FROZEN_CORE_SHA,
             'collector_validator_sha256':C.EXECUTION_SHA,'normalization_status':'terminal_end_display_repair_text_unchanged',
             'normalization_recovery':{'executed_recovery':C.artifact(copied),'original_failed_request':C.artifact(folder/'request.json'),
                                       'original_inference_code':C.artifact(inference_copy),'original_collector_validator':C.artifact(validator_copy),
                                       'original_exhausted_diagnostic':C.artifact(folder/'asr-diagnostic-completion.json'),
                                       'raw_segments':completion['raw_segments'],'quality':quality,
                                       'new_inference_performed':False,'terminal_alignment_verified':False}}
    D.check_code()
    if C.sha(__file__)!=EXECUTION_SHA or C.sha(copied)!=EXECUTION_SHA:raise ValueError('Recovery code changed during normalization')
    C.dump(folder/'receipt.json',receipt)
    D.verify_existing(folder/'receipt.json',Path(request['acquisition_receipt']['path']),request['model'])
    pcm=Path(request['decoder']['artifact']['path']);C.verify_artifact(request['decoder']['artifact'])
    pcm.unlink()
    C.dump(folder/'pcm-cleanup-after-terminal-recovery.json',{'removed_only_failed_attempt_new_pcm':request['decoder']['artifact'],
                                                            'accepted_recovery_receipt':C.artifact(folder/'receipt.json'),'at':C.now()})
    print(json.dumps({'source_id':source['source_id'],'words':len(text.split()),'segments':len(segments),
                      'timestamp_adjustment_seconds':quality['timestamp_maximum_adjustment_seconds']}))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);a=p.parse_args();recover(a.folder)
