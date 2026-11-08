#!/usr/bin/env python3
"""Project independently bound Council audio metadata without copying private media.

The current edition reuses three completed Contact recordings. Optional new
receipts belong to a distinct finite publisher frame, never the old229 frame.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
D_PATH=ROOT/'research/subscription-screening/audio_derivative_v2.py'
D_SHA='70754e0aeef744f3bd04cb14013e7e4bb67ef778bb4b8b515945d0a816147c99'
if hashlib.sha256(D_PATH.read_bytes()).hexdigest()!=D_SHA:raise RuntimeError('Frozen audio validator changed')
spec=importlib.util.spec_from_file_location('council_derivative_validator',D_PATH)
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);C=D.C
EXECUTION_SHA=C.sha(__file__)
NEW_AUDIO_CAP=20_000_000
NEW_TEXT_CAP=2_000_000

def snapshot(path,private):
    path=Path(path);raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    private=Path(private).resolve()
    if private.is_relative_to(ROOT):raise ValueError('Full private snapshots cannot enter the public repository')
    private.mkdir(parents=True,exist_ok=True)
    target=private/(path.stem+'-'+digest+'.json')
    if target.exists():
        if target.read_bytes()!=raw:raise ValueError('Immutable input snapshot differs')
    else:
        with target.open('xb') as f:f.write(raw)
    return json.loads(raw),{'sha256':digest,'bytes':len(raw)},C.artifact(target)

def record(document,origin):
    for key in ('acquisition_receipt','audio_artifact'):C.verify_artifact(document[key])
    raw_source=json.loads(Path(document['acquisition_receipt']['path']).read_text())
    pilot=None
    if raw_source.get('provider')=='council_audio_v1':
        spec=importlib.util.spec_from_file_location('council_pilot_verifier',Path(__file__).with_name('collect_audio.py'))
        pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
        source=pilot.verify_audio(document['acquisition_receipt']['path'])
    else:source=C.completed(document['acquisition_receipt']['path'])
    if source['publication_id']!=document['publication_id'] or source['audio']!=document['audio_artifact']:
        raise ValueError('Council publication/audio edition differs from receipt')
    if document['title']!=source['source']['title'] or document['canonical_url']!=source['source']['source_url']:
        raise ValueError('Council title or primary URL differs from acquired publication')
    asr=None
    if document.get('asr_receipt'):
        C.verify_artifact(document['asr_receipt'])
        binding=json.loads(Path(document['asr_receipt']['path']).read_text())
        asr=(pilot.verify_asr(document['asr_receipt']['path']) if pilot else
             D.verify_existing(Path(document['asr_receipt']['path']),Path(document['acquisition_receipt']['path']),binding['model']))
        for key,target in [('text_artifact','normalized'),('plain_text_artifact','text')]:
            C.verify_artifact(document[key])
            if document[key]!=asr['outputs'][target]:raise ValueError('Council text artifact differs from completed ASR')
        if document['words']!=asr['whitespace_words'] or document['turns']!=asr['segment_count']:
            raise ValueError('Council word/turn totals differ from ASR receipt')
    if document.get('decoded_audio_seconds')!=source['decoded_16k_mono']['duration_seconds']:
        raise ValueError('Council duration differs from measured audio')
    named=source['source'];caption=bool(source.get('caption_link'))
    status=('local_asr_completed' if asr and asr['status']=='completed' else 'publisher_caption_linked' if caption
            else 'asr_completed_empty_recognition' if asr and asr['status']=='completed_empty_recognition' else 'pending_local_asr')
    return {'publication_id':source['publication_id'],'source_id':source['source_id'],'document_source_id':document['source_id'],
            'primary_source_id':document.get('primary_source_id',source['source_id']),
            'publication_family_id':document.get('publication_family_id',source['publication_id']),
            'publisher_handle':named['handle'],'publisher':named['publisher'],'title':named['title'],'source_url':named['source_url'],
            'source_origin':source['source_origin'],'collection_status':'retained_full_duration_lossy_opus',
            'acquisition_origin':origin,'council_id':document['council_id'],'council_label':document['council_label'],
            'medium_id':document.get('medium_id'),'medium_name':document.get('medium_name'),
            'attribution_scope':document['attribution_scope'],'voice_production':document.get('voice_production','unknown_not_verified'),
            'retained_bytes':source['audio']['bytes'],'retained_sha256':source['audio']['sha256'],
            'retained_bitrate_bps':source['lineage'].get('conversion',{}).get('target_bitrate_bps'),
            'channel_transform':'mono_downmix' if source['lineage'].get('conversion',{}).get('mono_downmix') else 'original_channel_count_preserved',
            'original_bytes_verified_then_removed':source['lineage']['original_bytes'],'original_sha256':source['lineage']['original_sha256'],
            'decoded_duration_seconds':source['decoded_16k_mono']['duration_seconds'],'container_duration_seconds':source['duration_seconds'],
            'decoded_duration_difference_seconds':source['lineage']['actual_duration_difference_seconds'],'channels':source['audio']['probe']['channels'],
            'exact_original_family_id':source['duplicate_family_id'],'publisher_caption_linked':caption,
            'publisher_written_message_linked':bool(named.get('linked_written_text')),'audio_text_alignment_verified':False,
            'local_asr_completed':bool(asr and asr['status']=='completed'),'local_asr_empty_recognition':bool(asr and asr['status']=='completed_empty_recognition'),
            'transcript_status':status,'asr_words':asr['whitespace_words'] if asr else None,'asr_segments':asr['segment_count'] if asr else None,
            'asr_normalization_status':asr.get('normalization_status','unadjusted') if asr else None,
            'acquisition_receipt_sha256':document['acquisition_receipt']['sha256'],
            'asr_receipt_sha256':document['asr_receipt']['sha256'] if asr else None,
            'youtube_edition_equivalence':'unverified','analyzed_in_existing_frozen_fits':False}

def build(contact,output,snapshots,new_documents=None):
    data,public_binding,private_binding=snapshot(contact,snapshots)
    documents=[(d,'reused_existing_verified_archive') for d in data['documents']]
    inputs=[{'kind':'contact_manifest',**public_binding}]
    if new_documents:
        new,binding,_=snapshot(new_documents,snapshots)
        documents.extend((d,'new_verified_publisher_download') for d in new['documents'])
        inputs.append({'kind':'new_publisher_manifest',**binding})
    rows=[record(d,origin) for d,origin in documents]
    if len({r['publication_id'] for r in rows})!=len(rows):raise ValueError('Duplicate Council publication')
    new_rows=[r for r in rows if r['acquisition_origin']=='new_verified_publisher_download']
    if sum(r['retained_bytes'] for r in new_rows)>NEW_AUDIO_CAP:raise ValueError('New audio exceeds separate20MBcap')
    text_bytes=sum(a['bytes'] for d,origin in documents if origin=='new_verified_publisher_download' and d.get('asr_receipt') for a in json.loads(Path(d['asr_receipt']['path']).read_text())['outputs'].values())
    if text_bytes>NEW_TEXT_CAP:raise ValueError('New ASR outputs exceed2MBcap')
    result={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'status':'completed_available_source_subset',
            'scope':'Explicit Council publisher editions; reused archive media is referenced without redownload or duplication. No YouTube upload census.',
            'input_snapshots':inputs,'builder_sha256':EXECUTION_SHA,
            'new_acquisition_policy':{'maximum_retained_audio_bytes':NEW_AUDIO_CAP,'maximum_asr_output_bytes':NEW_TEXT_CAP,'bashar_minimum_duration_seconds':300,'other_minimum_duration_seconds':0},
            'summary':{'completed_publications':len(rows),'reused_audio_publications':len(rows)-len(new_rows),'new_audio_downloads':len(new_rows),
                'decoded_duration_seconds':sum(r['decoded_duration_seconds'] for r in rows),'retained_bytes':sum(r['retained_bytes'] for r in rows),
                'new_retained_bytes':sum(r['retained_bytes'] for r in new_rows),'local_asr_completed':sum(r['local_asr_completed'] for r in rows),
                'publisher_caption_linked':sum(r['publisher_caption_linked'] for r in rows),'upstream_total_videos':None},'records':rows,
            'limitations':['Attribution follows each exact publisher edition; Council names do not establish entity identity.',
                           'Automatic text is unverified recognition, and publisher written messages are not automatically audio-aligned.',
                           'Machine speech versus human-medium voice remains unknown unless a specific publisher source documents it.',
                           'The original229-publication frame and its frozen fitted analyses remain separate.']}
    if C.sha(__file__)!=EXECUTION_SHA:raise ValueError('Builder changed during execution')
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contact',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--snapshots',required=True,type=Path);p.add_argument('--new-documents',type=Path)
    a=p.parse_args();print(json.dumps(build(a.contact,a.output,a.snapshots,a.new_documents)['summary']))
