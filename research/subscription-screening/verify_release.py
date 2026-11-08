#!/usr/bin/env python3
"""Verify the public screening and publisher-text release without private sources."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(site):
    root = site / 'dist/subscription-audit'
    raw = (root / 'data.json').read_text()
    data = json.loads(raw)
    assert not any(s in raw for s in ('/workspace/', '/tmp/', 'access_token=', 'X-Amz-Signature='))
    channels = data['channels']
    assert len(channels) == len({c['id'] for c in channels}) == 28
    assert {s: sum(c['status'] == s for c in channels) for s in ('include', 'exclude', 'uncertain')} == {'include': 12, 'exclude': 16, 'uncertain': 0}
    assert data['selection']['minimum_duration_seconds'] == 0
    assert data['selection']['bashar_minimum_duration_seconds'] == 300
    assert data['selection']['per_channel_count_cap'] is None
    assert len({v['video_id'] for v in data['videos']}) == 86
    lookup = {c['id']: c for c in channels}
    assert lookup['jamiebutlermedium']['user_excluded'] is True
    for c in channels:
        assert c['public_uploads_total'] is None and not c['observed_uploads_are_total']
        observed = [v for v in data['videos'] if v['channel_id'] == c['id']]
        legacy = sum(isinstance(v['duration_seconds'], (int, float)) and v['duration_seconds'] >= 300 and not v['duration_conflict_values'] for v in observed)
        eligible = sum(v['eligible_from_historical_metadata'] for v in observed)
        assert c['counts']['eligible_5min_observed'] == (legacy if observed else None)
        assert c['counts']['eligible_current_policy_observed'] == (eligible if observed else None)
        assert c['minimum_duration_seconds'] == (300 if c['id'] == 'divinelightvibes' else 0)
    path = root / data['supplementary_studies']['publisher_texts']
    assert path.name == 'source-topics.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == data['publisher_text_study_sha256']
    study = json.loads(path.read_text())
    figures = study['figures']
    for f in figures:
        assert Path(f['file']).name == f['file']
        p = root / 'text-figures' / f['file']
        assert p.stat().st_size == f['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == f['sha256']
    if data.get('publisher_video_inventory'):
        item = data['publisher_video_inventory']
        assert item['file'] == 'publisher-video-index.json'
        p = root / item['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
        index = json.loads(p.read_text())
        assert len({v['video_id'] for v in index['videos']}) == len(index['videos']) == index['counts']['unique_youtube_ids_linked']
        assert index['counts']['youtube_uploads_total'] is None
        assert index['counts']['youtube_media_downloaded_this_crawl'] == 0
        assert all(v['youtube_uploader_reverified'] is False for v in index['videos'])
        assert index['counts']['archive_pages_retrieved'] == sum(s['status'] == 'retrieved' for s in index['source_pages'])
    if data.get('publisher_audio_acquisition'):
        item = data['publisher_audio_acquisition']
        assert item['file'] == 'acquisition.json'
        p = root / item['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
        audio = json.loads(p.read_text())
        records = audio['records']
        assert len({r['publication_id'] for r in records}) == len(records) == audio['summary']['completed_publications']
        assert sum(r['retained_bytes'] for r in records) == audio['summary']['retained_bytes']
        assert sum(r['local_asr_completed'] for r in records) == audio['summary']['local_asr_completed']
        assert all(r['youtube_edition_equivalence'] == 'unverified' for r in records)
        assert not any(s in p.read_text() for s in ('/workspace/', '/tmp/', 'access_token=', 'X-Amz-Signature='))
    for p in root.rglob('*'):
        if p.is_file():
            assert p.suffix.lower() not in {'.mp3', '.mp4', '.opus', '.wav', '.srt', '.vtt', '.sqlite', '.jsonl'}, p
    return {'status': 'passed', 'screened_accounts': len(channels), 'historical_video_ids': 86,
            'figures_verified': len(figures), 'current_policy': 'Bashar >=300 seconds; no minimum for other material',
            'scope': 'Public accounting, policy and artifact integrity; no claim of a complete YouTube crawl.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.site), indent=2))
