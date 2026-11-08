#!/usr/bin/env python3
"""Publish metadata-only counts from private, receipt-backed publisher media."""
import argparse
import hashlib
import json
import importlib.util
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def checked_artifact(artifact):
    p=Path(artifact['path']);body=p.read_bytes()
    if len(body)!=artifact['bytes'] or hashlib.sha256(body).hexdigest()!=artifact['sha256']:
        raise ValueError('Bound private artifact changed')
    return body

def project(acquisition,output,asr=None,snapshot_dir=None,holds=None):
    raw=Path(acquisition).read_bytes();data=json.loads(raw)
    asr_raw=Path(asr).read_bytes() if asr and Path(asr).exists() else None
    hold_raw=Path(holds).read_bytes() if holds else None
    rows=data['records'];asr_data=json.loads(asr_raw) if asr_raw else {'records':[]}
    snapshot_root=Path(snapshot_dir) if snapshot_dir else Path(acquisition).resolve().parent/'publication-snapshots'
    if snapshot_root.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError('Full input snapshots must remain outside the public repository')
    snapshot_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    snapshots=[]
    for label,body in [('acquisition',raw),('asr',asr_raw),('recognition_holds',hold_raw)]:
        if body is None:continue
        sha=hashlib.sha256(body).hexdigest();path=snapshot_root/(label+'-'+sha+'.json')
        if path.exists():
            if path.read_bytes()!=body:raise ValueError('Existing immutable snapshot differs')
        else:
            with path.open('xb') as f:f.write(body)
        snapshots.append({'kind':label,'sha256':sha,'bytes':len(body)})
    recognized={r['publication_id']:r for r in asr_data['records'] if r.get('status') in ('completed','completed_empty_recognition')}
    if len(recognized)!=sum(r.get('status') in ('completed','completed_empty_recognition') for r in asr_data['records']):
        raise ValueError('Duplicate completed ASR publication IDs')
    held={};by_id={r['source_id']:r for r in rows}
    if hold_raw:
        ledger=json.loads(hold_raw)
        if ledger.get('status') not in ('reviewed_source_specific_recognition_holds','policy_validated_source_specific_recognition_holds'):raise ValueError('Unsupported recognition hold ledger')
        if ledger['status']=='policy_validated_source_specific_recognition_holds':
            policy_path=Path(__file__).with_name('continue_publisher_asr_v4.py')
            if digest(policy_path)!=ledger.get('policy_code_sha256'):raise ValueError('Automatic quarantine policy changed')
            spec=importlib.util.spec_from_file_location('projection_quarantine_policy',policy_path)
            policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
            policy.validate_holds(Path(holds))
        for h in ledger['records']:
            if h['disposition']!='held_unadmitted_asr' or h['reason_code'] not in ('repeated_output_with_timestamp_overflow','multiple_segments_outside_audio'):
                raise ValueError('Unsupported failed recognition edition')
            for key in ('acquisition_receipt','failed_request','exhausted_diagnostic','raw_segments','original_inference_code','original_collector_validator'):
                checked_artifact(h[key])
            source=json.loads(checked_artifact(h['acquisition_receipt']))
            request=json.loads(checked_artifact(h['failed_request']));diagnostic=json.loads(checked_artifact(h['exhausted_diagnostic']))
            if h['source_id'] not in by_id or source!=by_id[h['source_id']] or h['publication_id']!=source['publication_id']:
                raise ValueError('Recognition hold does not bind this acquired source edition')
            if request['source_id']!=h['source_id'] or request['model']!=h['model'] or request['acquisition_receipt']!=h['acquisition_receipt']:
                raise ValueError('Recognition hold request/model binding differs')
            if diagnostic['request_sha256']!=h['failed_request']['sha256'] or diagnostic['raw_segments']!=h['raw_segments'] or diagnostic['inference_stream_exhausted'] is not True:
                raise ValueError('Recognition hold diagnostic binding differs')
            if h['publication_id'] in held:raise ValueError('Duplicate recognition hold publication')
            held[h['publication_id']]=h
    records=[]
    for r in rows:
        source=r['source'];a=recognized.get(r['publication_id']);h=held.get(r['publication_id'])
        if a:
            proof=a['acquisition_receipt'];body=Path(proof['path']).read_bytes()
            if len(body)!=proof['bytes'] or hashlib.sha256(body).hexdigest()!=proof['sha256'] or json.loads(body)!=r:
                raise ValueError('ASR does not bind this exact acquisition receipt')
            for artifact in a['outputs'].values():
                p=Path(artifact['path'])
                if p.stat().st_size!=artifact['bytes'] or digest(p)!=artifact['sha256']:
                    raise ValueError('Completed ASR output changed')
        nonempty=bool(a and a['status']=='completed');empty=bool(a and a['status']=='completed_empty_recognition')
        caption=bool(r.get('caption_link'));active_hold=bool(h and not nonempty and not caption)
        transcript_status=('local_asr_completed' if nonempty else 'publisher_caption_linked' if caption
                           else 'asr_completed_empty_recognition' if empty else 'asr_held_after_recognition_failure' if active_hold
                           else 'pending_local_asr')
        records.append({'publication_id':r['publication_id'],'source_id':r['source_id'],
                        'publisher_handle':source['handle'],'publisher':source['publisher'],
                        'title':source['title'],'source_url':source['source_url'],
                        'source_origin':r['source_origin'],'collection_status':'retained_full_duration_lossy_opus',
                        'retained_bytes':r['audio']['bytes'],'retained_sha256':r['audio']['sha256'],
                        'original_bytes_verified_then_removed':r['lineage']['original_bytes'],
                        'original_sha256':r['lineage']['original_sha256'],
                        'decoded_duration_seconds':r['decoded_16k_mono']['duration_seconds'],
                        'container_duration_seconds':r['duration_seconds'],
                        'decoded_duration_difference_seconds':r['lineage']['actual_duration_difference_seconds'],
                        'channels':r['audio']['probe']['channels'],
                        'exact_original_family_id':r['duplicate_family_id'],
                        'publisher_caption_linked':caption,
                        'publisher_written_message_linked':bool(source.get('linked_written_text')),
                        'audio_text_alignment_verified':False,
                        'local_asr_completed':nonempty,'local_asr_empty_recognition':empty,
                        'transcript_status':transcript_status,'recognition_hold_active':active_hold,
                        'asr_failed_edition_count':int(bool(h)),
                        'asr_failed_editions':([{'status':h['disposition'],'reason_code':h['reason_code'],
                                                'review_status':h.get('review_status','not_recorded_in_original_ledger'),
                                                'quarantine_policy_sha256':h.get('quarantine_policy_sha256'),
                                                'human_reviewed':h.get('human_reviewed'),
                                                'request_sha256':h['failed_request']['sha256'],
                                                'diagnostic_sha256':h['exhausted_diagnostic']['sha256'],
                                                'model_files_sha256':h['model'].get('files_sha256'),
                                                'raw_segment_count':h['diagnostic_metrics']['raw_segment_count'],
                                                'unique_segment_texts':h['diagnostic_metrics']['unique_segment_texts'],
                                                'most_repeated_count':h['diagnostic_metrics']['most_repeated_count'],
                                                'ends_beyond_duration_plus_one_second':h['diagnostic_metrics']['ends_beyond_duration_plus_one_second']}] if h else []),
                        'asr_words':a['whitespace_words'] if a else None,
                        'asr_segments':a['segment_count'] if a else None,
                        'asr_normalization_status':a.get('normalization_status','unadjusted') if a else None,
                        'youtube_edition_equivalence':'unverified','analyzed_in_existing_frozen_fits':False})
    channels=[]
    for handle in sorted({r['publisher_handle'] for r in records}):
        selected=[r for r in records if r['publisher_handle']==handle]
        channels.append({'id':handle.lstrip('@').lower(),'related_publisher_material':{
            'current_new_audio_sources_retained':len(selected),
            'current_new_audio_retained_bytes':sum(r['retained_bytes'] for r in selected),
            'current_new_audio_decoded_seconds':sum(r['decoded_duration_seconds'] for r in selected),
            'current_new_audio_exact_original_families':len({r['original_sha256'] for r in selected}),
            'current_new_audio_caption_linked':sum(r['publisher_caption_linked'] for r in selected),
            'current_new_audio_local_asr':sum(r['local_asr_completed'] for r in selected),
            'current_new_audio_asr_failed_editions':sum(r['asr_failed_edition_count'] for r in selected),
            'current_new_audio_recognition_holds':sum(r['recognition_hold_active'] for r in selected),
            'current_new_audio_asr_pending':sum(r['transcript_status']=='pending_local_asr' for r in selected),
            'current_new_audio_written_message_linked':sum(r['publisher_written_message_linked'] for r in selected),
            'scope':'Direct publisher audio retained as verified full-duration lossy48kbpsOpus; original bytes hashed before newly staged originals removed. YouTube edition equivalence and text accuracy are unverified.',
            'acquisition_status':data['status']}})
    public={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Explicit finite publisher sources, not a YouTube upload census; raw audio and full text retained privately.',
            'status':data['status'],'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),
            'input_snapshots':snapshots,'asr_status':asr_data.get('status','not_available'),
            'frame':{'publisher_rss_entries':224,'publisher_download_page_entries':5,'total_entries':data['frame_count'],
                     'upstream_total_videos':None,'all_historical_publisher_episodes':None,
                     'non_bashar_minimum_duration_seconds':0,'bashar_minimum_duration_seconds':300},
            'summary':{'completed_publications':len(records),'retained_bytes':sum(r['retained_bytes'] for r in records),
                       'decoded_duration_seconds':sum(r['decoded_duration_seconds'] for r in records),
                       'local_asr_completed':sum(r['local_asr_completed'] for r in records),
                       'local_asr_empty_recognition':sum(r['local_asr_empty_recognition'] for r in records),
                       'asr_failed_editions':sum(r['asr_failed_edition_count'] for r in records),
                       'recognition_holds':sum(r['recognition_hold_active'] for r in records),
                       'pending_local_asr':sum(r['transcript_status']=='pending_local_asr' for r in records),
                       'normalization_repaired':sum(r['local_asr_completed'] and r['asr_normalization_status'] not in (None,'unadjusted') for r in records),
                       'publisher_caption_linked':sum(r['publisher_caption_linked'] for r in records),
                       'publisher_written_message_linked':sum(r['publisher_written_message_linked'] for r in records)},
            'channels':channels,'records':records,
            'limitations':['Publisher text links do not validate audio alignment or recognition accuracy.',
                           'Account context does not identify every speaker or claimed entity in a mixed recording.',
                           'Byte identity defines an encoded-media family, not an independent historical session.',
                           'A held failed recognition edition is separate from retained audio and from sources still pending transcription.',
                           'These downloads do not modify the frozen125-document baseline or other existing fitted analyses.']}
    if data.get('stop'):public['stop']={'type':data['stop']['type'],'source_id':data['stop']['source_id']}
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n')
    return public

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquisition',required=True);p.add_argument('--output',required=True);p.add_argument('--asr');p.add_argument('--snapshot-dir');p.add_argument('--holds')
    a=p.parse_args();r=project(a.acquisition,a.output,a.asr,a.snapshot_dir,a.holds);print(json.dumps(r['summary']))
