#!/usr/bin/env python3
"""Publish metadata-only counts from private, receipt-backed publisher media."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def project(acquisition,output,asr=None,snapshot_dir=None):
    raw=Path(acquisition).read_bytes();data=json.loads(raw)
    asr_raw=Path(asr).read_bytes() if asr and Path(asr).exists() else None
    rows=data['records'];asr_data=json.loads(asr_raw) if asr_raw else {'records':[]}
    snapshot_root=Path(snapshot_dir) if snapshot_dir else Path(acquisition).resolve().parent/'publication-snapshots'
    if snapshot_root.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError('Full input snapshots must remain outside the public repository')
    snapshot_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    snapshots=[]
    for label,body in [('acquisition',raw),('asr',asr_raw)]:
        if body is None:continue
        sha=hashlib.sha256(body).hexdigest();path=snapshot_root/(label+'-'+sha+'.json')
        if path.exists():
            if path.read_bytes()!=body:raise ValueError('Existing immutable snapshot differs')
        else:
            with path.open('xb') as f:f.write(body)
        snapshots.append({'kind':label,'sha256':sha,'bytes':len(body)})
    recognized={r['publication_id']:r for r in asr_data['records'] if r.get('status')=='completed'}
    if len(recognized)!=sum(r.get('status')=='completed' for r in asr_data['records']):
        raise ValueError('Duplicate completed ASR publication IDs')
    records=[]
    for r in rows:
        source=r['source'];a=recognized.get(r['publication_id'])
        if a:
            proof=a['acquisition_receipt'];body=Path(proof['path']).read_bytes()
            if len(body)!=proof['bytes'] or hashlib.sha256(body).hexdigest()!=proof['sha256'] or json.loads(body)!=r:
                raise ValueError('ASR does not bind this exact acquisition receipt')
            for artifact in a['outputs'].values():
                p=Path(artifact['path'])
                if p.stat().st_size!=artifact['bytes'] or digest(p)!=artifact['sha256']:
                    raise ValueError('Completed ASR output changed')
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
                        'publisher_caption_linked':bool(r.get('caption_link')),
                        'publisher_written_message_linked':bool(source.get('linked_written_text')),
                        'audio_text_alignment_verified':False,
                        'local_asr_completed':bool(a),'asr_words':a['whitespace_words'] if a else None,
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
                       'normalization_repaired':sum(r['local_asr_completed'] and r['asr_normalization_status'] not in (None,'unadjusted') for r in records),
                       'publisher_caption_linked':sum(r['publisher_caption_linked'] for r in records),
                       'publisher_written_message_linked':sum(r['publisher_written_message_linked'] for r in records)},
            'channels':channels,'records':records,
            'limitations':['Publisher text links do not validate audio alignment or recognition accuracy.',
                           'Account context does not identify every speaker or claimed entity in a mixed recording.',
                           'Byte identity defines an encoded-media family, not an independent historical session.',
                           'These downloads do not modify the frozen125-document baseline or other existing fitted analyses.']}
    if data.get('stop'):public['stop']={'type':data['stop']['type'],'source_id':data['stop']['source_id']}
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n')
    return public

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquisition',required=True);p.add_argument('--output',required=True);p.add_argument('--asr');p.add_argument('--snapshot-dir')
    a=p.parse_args();r=project(a.acquisition,a.output,a.asr,a.snapshot_dir);print(json.dumps(r['summary']))
