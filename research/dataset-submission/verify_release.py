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
    if 'archive' in manifest['modules']:
        archive=read('archive.json')
        transfer=archive['transfer'];destination=archive['destination']
        for key in ('verified_assets','verified_remote_bytes'):
            assert type(transfer[key]) is int and transfer[key]>=0
        assert type(transfer['complete']) is bool
        if transfer['complete']:
            assert transfer['verified_assets']>0 and transfer['verified_remote_bytes']>0
            assert destination['visibility_verified'] is True
            assert destination['intended_visibility']=='private'
        else:
            assert archive.get('status') not in ('complete','uploaded','verified_complete')
    return {**result,'status':'passed_dataset_integrity_and_unit_reconciliation',
            'documents':len(docs),'words':summary['words'],'editions':len(editions),
            'contexts':len(channels),'joined_media':len(media),'youtube_observed_ids':len(videos),
            'youtube_upload_totals':'unknown','direct_youtube_downloads':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.site)))
