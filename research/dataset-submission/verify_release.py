#!/usr/bin/env python3
"""Independently reconcile the public research release without accessing raw bodies."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('release_builder',HERE/'build_public.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def verify(site):
    result=builder.verify(site);root=Path(site)/'dist/dataset-submission'
    def read(name): return json.loads((root/name).read_text())
    def rows(name): return [json.loads(line) for line in (root/name).read_text().splitlines() if line.strip()]
    dataset=read('dataset.json');summary=dataset['summary']
    docs=rows('documents.jsonl');editions=rows('editions.jsonl');media=rows('media.jsonl')
    accounts=rows('youtube-accounts.jsonl');videos=rows('youtube-videos.jsonl');links=rows('youtube-account-video-links.jsonl')
    assert docs==dataset['documents'],'JSONL document view differs from dashboard'
    assert editions==dataset['text_editions'],'JSONL edition view differs from dashboard'
    assert media==dataset['media'],'JSONL media view differs from dashboard'
    ids={d['source_id'] for d in docs};assert len(ids)==len(docs)==summary['documents']
    assert sum(d['words'] for d in docs)==summary['words']
    assert len(editions)==summary['text_editions']
    edition_ids={e['edition_id'] for e in editions};assert len(edition_ids)==len(editions)
    selected={e['source_id']:e for e in editions if e['selected']}
    assert len(selected)==len(docs)==sum(e['selected'] for e in editions)
    assert {e['source_id'] for e in editions}<=ids
    for doc in docs:
        e=selected[doc['source_id']]
        assert (e['edition_id'],e['body_sha256'],e['words'])==(doc['selected_edition_id'],doc['body_sha256'],doc['words'])
    assert Counter(d['text_origin'] for d in docs)==summary['text_origin_counts']
    assert sum(d.get('publication_date') is None for d in docs)==summary['date_missing_documents']
    channels={c['channel_id']:c for c in dataset['channels']}
    assert len(channels)==summary['publisher_contexts']
    assert len({d['creator_id'] for d in docs})==summary['creator_contexts']
    assert sum(c['selected_publications'] for c in channels.values())==len(docs)
    assert sum(c['selected_words'] for c in channels.values())==summary['words']
    for key,c in channels.items():
        group=[d for d in docs if d['channel_id']==key]
        assert set(c['source_ids'])=={d['source_id'] for d in group}
        assert len(group)==c['selected_publications']
        assert sum(d['words'] for d in group)==c['selected_words']
        assert c['youtube_uploaded_total'] is None
        assert c['youtube_downloaded_videos']==0
    assert len(media)==summary['selected_linked_media_rows']
    assert len({m['sha256'] for m in media})==summary['selected_unique_encoded_media']
    assert {m['source_id'] for m in media}<=ids
    assert len(videos)==len({v['video_id'] for v in videos})==summary['youtube_observed_video_ids']
    assert len(accounts)==len({a['account_id'] for a in accounts})==summary['youtube_account_references']
    account_ids={a['account_id'] for a in accounts};video_ids={v['video_id'] for v in videos}
    assert all(e['account_id'] in account_ids and e['video_id'] in video_ids for e in links)
    assert all(a['uploaded_total'] is None for a in accounts)
    assert summary['youtube_uploaded_total'] is None and summary['youtube_downloads']==0
    table=list(csv.DictReader((root/'channels.csv').open()))
    assert len(table)==len(channels)
    manifest=read('manifest.json')
    if 'analysis' in manifest['modules']:
        analysis=read('analysis.json')
        assert analysis['frame_sha256']==dataset['frame_sha256'],'Analysis frame differs or absent'
    if 'collection_plan' in manifest['modules']:
        plan=read('collection-plan.json')
        assert plan['schema_version']==1 and plan['phase']=='plan_published_execution_pending'
        bindings={'documents':'documents','editions':'text_editions','words':'words',
                  'publisher_contexts':'publisher_contexts','observed_youtube_ids':'youtube_observed_video_ids',
                  'account_references':'youtube_account_references'}
        for key,other in bindings.items(): assert plan['baseline'][key]==summary[other]
        assert plan['baseline']['lifetime_uploaded_total'] is None
        for key in ('new_queries_executed','new_youtube_downloads','new_transcripts','new_analysis_runs'):
            assert type(plan['execution'][key]) is int and plan['execution'][key]==0
        assert plan['policy']['count_cap'] is None
        assert plan['policy']['bashar_minimum_seconds']==300 and plan['policy']['other_minimum_seconds']==0
        assert all(x['status']=='planned' for x in plan['query_families'])
        assert all(x['status']=='planned' and x['acceptance'] for x in plan['stages'])
        assert all(x['status']=='refresh_planned' for x in plan['tool_review'])
        assert len({x['id'] for x in plan['query_families']})==len(plan['query_families'])
    if 'archive' in manifest['modules']:
        archive=read('archive.json')
        transfer=archive['transfer'];destination=archive['destination']
        for key in ('verified_assets','verified_remote_bytes'):
            assert type(transfer[key]) is int and transfer[key]>=0
        assert type(transfer['complete']) is bool
        if transfer['complete']:
            assert transfer['verified_assets']>0 and transfer['verified_remote_bytes']>0
            assert destination['visibility_verified'] is True
            assert destination['intended_visibility'] in ('private','public_for_redistribution_cleared_assets')
            if destination['intended_visibility']=='public_for_redistribution_cleared_assets':
                assert archive['rights_review']['status']=='verified_for_all_published_assets'
        else:
            assert archive.get('status') not in ('complete','uploaded','verified_complete')
        if 'public_object_inventory' in archive:
            objects=rows(archive['public_object_inventory']['file'])
            stats=read(archive['public_object_inventory']['summary_file'])
            assert len(objects)==len({o['sha256'] for o in objects})==stats['objects']==archive['closure']['unique_content_objects']
            assert sum(o['bytes'] for o in objects)==stats['unique_bytes']==archive['closure']['unique_content_bytes']
            assert sum(o['logical_path_count'] for o in objects)==stats['logical_paths']==archive['closure']['logical_file_paths']
            assert all(o['retained'] is True and o['remote_transfer_verified'] is False for o in objects)
    return {**result,'status':'passed_dataset_integrity_and_unit_reconciliation',
            'documents':len(docs),'words':summary['words'],'editions':len(editions),
            'contexts':len(channels),'joined_media':len(media),'youtube_observed_ids':len(videos),
            'youtube_upload_totals':'unknown','direct_youtube_downloads':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.site)))
