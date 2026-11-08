#!/usr/bin/env python3
"""Join researched account identities to the preserved, explicitly partial inventory."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def read(path):
    return json.loads(path.read_text())


def identity(url):
    p = urlsplit(url)
    if p.hostname not in {'youtube.com', 'www.youtube.com'} or not p.path.startswith('/@'):
        raise ValueError(f'Expected an exact public YouTube handle route: {url}')
    return p.path.split('/')[1][1:].lower()


def build(repo, research, output, acquisition=None):
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs = repo / 'research/subscription-screening/input-channels.json'
    requested = read(inputs)['channels']
    policy_path = repo / 'research/subscription-screening/collection-policy.json'
    policy = read(policy_path)
    classified = {}
    for path in research:
        for row in read(path)['channels']:
            key = identity(row['channel_url'])
            if key in classified:
                raise ValueError('Duplicate researched channel')
            classified[key] = row
    expected = {r['id'] for r in requested}
    if set(classified) != expected:
        raise ValueError(f'Classification frame mismatch: missing={expected-set(classified)}, extra={set(classified)-expected}')
    routes_path = repo / 'research/harvest/inventory/channel-routes.json'
    videos_path = repo / 'research/harvest/inventory/videos.jsonl'
    analysis_path = repo / 'dist/analysis/data.json'
    routes = read(routes_path)['records']
    videos = [json.loads(line) for line in videos_path.read_text().splitlines() if line.strip()]
    historical = read(analysis_path)
    caption_rows = historical.get('transcripts', {}).get('rows', [])
    historical_videos = {v['id']: v for v in historical['videos']}
    new = read(acquisition) if acquisition else {'channels': []}
    new_rows = {r['id']: r for r in new['channels']}
    publisher_inventory_path = repo / 'research/subscription-screening/second14-source-inventory.json'
    publisher_texts_path = repo / 'research/subscription-screening/second14-text-acquisition.json'
    publisher_videos_path = repo / 'research/subscription-screening/magenta-publisher-video-index.json'
    publisher_inventory = read(publisher_inventory_path) if publisher_inventory_path.exists() else None
    publisher_texts = read(publisher_texts_path) if publisher_texts_path.exists() else None
    publisher_videos = read(publisher_videos_path) if publisher_videos_path.exists() else None
    publisher_accounts = {r['handle'].lstrip('@').lower(): r for r in publisher_inventory['channels']} if publisher_inventory else {}
    medium_handles = {'tracy_kumbera': 'tracykumbera', 'magenta_pixie': 'magentapixie'}
    channels, inventory = [], []
    for item in requested:
        row = dict(classified[item['id']])
        row.update(id=item['id'], name=item['name'], handle=item['handle'], channel_url=item['channel_url'])
        if item['user_excluded']:
            row.update(status='exclude', status_reason='Explicit user exclusion; researched category is recorded separately.', user_excluded=True)
        assert row['status'] in {'include', 'exclude', 'uncertain'}
        matched = []
        for route in routes:
            try:
                same = identity(route['url']) == item['id']
            except ValueError:
                same = False
            if same:
                matched.append(route)
        route_ids = {r['route_id'] for r in matched}
        ids = {v for r in matched for v in r['known_video_ids']}
        ids |= {v['video_id'] for v in videos if route_ids.intersection(v['channel_route_ids'])}
        observed = [v for v in videos if v['video_id'] in ids]
        if len({v['video_id'] for v in observed}) != len(observed):
            raise ValueError('Duplicate inventory video IDs')
        legacy_eligible = [v for v in observed if isinstance(v.get('duration_seconds'), (int, float))
            and v['duration_seconds'] >= 300 and not v.get('duration_conflict_values')]
        # The screenshot's Divine Light Vibes account is a Bashar repost lead.
        # A mixed account needs per-record attribution before applying this rule.
        bashar_account = item['id'] == 'divinelightvibes'
        minimum = policy['bashar_minimum_duration_seconds'] if bashar_account else policy['minimum_duration_seconds']
        eligible = [v for v in observed if isinstance(v.get('duration_seconds'), (int, float))
            and v['duration_seconds'] > 0 and v['duration_seconds'] >= minimum
            and not v.get('duration_conflict_values')]
        prior_captions = [r for r in caption_rows if r['videoId'] in ids]
        prior_titles = [historical_videos[v] for v in ids if v in historical_videos and historical_videos[v].get('titleEligible')]
        row['counts'] = {
            'public_uploads_observed': len(observed) if observed else None,
            'eligible_5min_observed': len(legacy_eligible) if observed else None,
            'eligible_current_policy_observed': len(eligible) if observed else None,
            'audio_sources_retained': None, 'video_sources_retained': None,
            'transcribed_sources': None, 'analyzed_sources': None,
            'historical_caption_analyses': len(prior_captions),
            'historical_title_analyses': len(prior_titles),
        }
        row['observed_uploads_are_total'] = False
        row['minimum_duration_seconds'] = minimum
        row['duration_policy_basis'] = 'Bashar repost lead; per-video speaker confirmation required.' if bashar_account else 'No minimum for non-Bashar material; Bashar items encountered on mixed accounts still require 300 seconds.'
        row['inventory_checked_at'] = historical['meta']['checkedAt'] if observed else None
        row['inventory_basis'] = 'Historical purposive index joined by exact case-insensitive handle routes and unique video IDs; not a fresh channel crawl or total uploads.'
        row['public_uploads_total'] = None
        row['uploader_identity_reverified_this_run'] = False
        row['historical_caption_records'] = [{k: c.get(k) for k in ('videoId', 'url', 'wordCount', 'language', 'captionArtifactSha256', 'textSha256')} for c in prior_captions]
        row['historical_caption_retention_status'] = 'Prior numerical analysis recorded; current full-text availability requires separate artifact reconciliation.' if prior_captions else 'No matching caption record in this historical pilot; this is not proof that platform captions are unavailable.'
        row['inventory_route_ids'] = sorted(route_ids)
        row['duration_unknown_or_conflicted'] = sum(v.get('duration_seconds') is None or bool(v.get('duration_conflict_values')) for v in observed)
        if item['id'] in publisher_accounts:
            discovered = publisher_accounts[item['id']]
            text_rows = [r for r in publisher_texts['records'] if medium_handles.get(r['medium_id']) == item['id']] if publisher_texts else []
            feed = discovered.get('feed', {})
            row['related_publisher_material'] = {
                'finding': discovered['finding'], 'is_youtube_download_count': False,
                'audio_feed_entries': feed.get('audio_enclosure_entries'),
                'legacy_5min_eligible_audio_entries': feed.get('eligible_by_publisher_duration_ge_300'),
                'metadata_duration_eligible_audio_entries': feed.get('audio_enclosure_entries'),
                'feed_url': feed.get('feed_url'), 'audio_files_newly_retained': 0,
                'text_files_retained': len(text_rows),
                'transcript_publications_retained': sum(r['source_kind'] in {'publisher_hosted_caption_origin_unverified', 'publisher_labeled_transcript_pdf'} for r in text_rows),
                'reference_publications_retained': sum(r['source_kind'] not in {'publisher_hosted_caption_origin_unverified', 'publisher_labeled_transcript_pdf'} for r in text_rows),
                'text_words_retained': sum(r['whitespace_words'] for r in text_rows),
                'unique_text_hashes': len({r['text_content_sha256'] for r in text_rows}),
                'source_kinds': dict(Counter(r['source_kind'] for r in text_rows)),
                'new_text_analysis_units': None,
                'scope': 'Direct publisher sources; original video duration/edition equivalence and recognition accuracy are not inferred from text. Audio acquisition in the proposed RSS phase has not yet run.'}
        if publisher_videos and item['id'] == publisher_videos['channel_id']:
            row.setdefault('related_publisher_material', {}).update({
                'publisher_linked_video_ids': publisher_videos['counts']['unique_youtube_ids_linked'],
                'publisher_video_archive_pages': publisher_videos['counts']['archive_pages_retrieved'],
                'publisher_video_archive_url': publisher_videos['seed_url'],
                'publisher_video_inventory': 'publisher-video-index.json',
                'publisher_index_overlap_with_historical_ids': len(ids & {v['video_id'] for v in publisher_videos['videos']}),
                'publisher_video_scope': 'Explicit publisher archive links; YouTube availability, uploader, duration and upload total are unverified. Not downloaded videos.'})
        for v in observed:
            inventory.append({'channel_id': item['id'], 'video_id': v['video_id'], 'url': v['source_url'],
                'title': v['title'], 'duration_seconds': v.get('duration_seconds'),
                'duration_conflict_values': v.get('duration_conflict_values', []),
                'collection_status': 'historical_metadata_only', 'speaker_status': v['actual_speaker_status'],
                'eligible_from_historical_metadata': v in eligible,
                'channel_included': row['status'] == 'include'})
        if item['id'] in new_rows:
            acquired = new_rows[item['id']]
            row['counts'].update(acquired.get('counts', {}))
            for key in ('acquisition_status', 'acquisition_evidence', 'related_publisher_material', 'current_transcript_retention_status'):
                if key in acquired:
                    row[key] = {**row.get(key, {}), **acquired[key]} if isinstance(acquired[key], dict) else acquired[key]
        channels.append(row)
    out = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Source-screened public accounts selected by the user. Relevant channel classification does not establish that every upload is channeling. Counts distinguish historical metadata, actual retained media, full text and completed analysis.',
        'channels': channels, 'videos': inventory,
        'selection': policy,
        'inventory_limits': ['Observed video IDs are a purposive historical sample, not total channel uploads.',
            'Unknown totals and unreconciled current retention stay null; zero prior pilot records does not imply no available transcripts.',
            'Independent publisher recordings are not counted as downloaded YouTube videos without an exact edition match.'],
        'source_bindings': {str(p.relative_to(repo)) if p.is_relative_to(repo) else p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [inputs, policy_path, *research, routes_path, videos_path, analysis_path] + ([acquisition] if acquisition else [])
            + ([publisher_inventory_path] if publisher_inventory else []) + ([publisher_texts_path] if publisher_texts else [])
            + ([publisher_videos_path] if publisher_videos else [])}}
    if publisher_videos:
        public_video_path = output.parent / 'publisher-video-index.json'
        public_video_path.write_bytes(publisher_videos_path.read_bytes())
        out['publisher_video_inventory'] = {'file': public_video_path.name,
            'sha256': hashlib.sha256(public_video_path.read_bytes()).hexdigest(),
            'channel_id': publisher_videos['channel_id'], 'counts': publisher_videos['counts'],
            'scope': 'Publisher-linked video IDs; separate from historical inventory and actual media acquisition.'}
    if acquisition:
        public_audio_path = output.parent / 'acquisition.json'
        public_audio_path.write_bytes(acquisition.read_bytes())
        out['publisher_audio_acquisition'] = {'file': public_audio_path.name,
            'sha256': hashlib.sha256(public_audio_path.read_bytes()).hexdigest(),
            'summary': new.get('summary', {}), 'frame': new.get('frame', {}),
            'status': new.get('status'), 'scope': new.get('scope')}
    if publisher_texts:
        out['publisher_text_records'] = publisher_texts['records']
        out['publisher_text_summary'] = {'files': len(publisher_texts['records']),
            'whitespace_words': publisher_texts['counts']['whitespace_words'],
            'raw_bytes': publisher_texts['raw_bytes'],
            'scope': 'Publisher-hosted captions and extracted PDF text, not downloaded YouTube video editions.'}
    study_path = output.parent / 'source-topics.json'
    if study_path.is_file():
        out['supplementary_studies'] = {'publisher_texts': study_path.name}
        out['publisher_text_study_sha256'] = hashlib.sha256(study_path.read_bytes()).hexdigest()
    raw = json.dumps(out, indent=2, ensure_ascii=False) + '\n'
    if any(x in raw for x in ['/workspace/', '/tmp/', 'X-Amz-Signature=', 'access_token=']):
        raise ValueError('Private path or signed URL entered public audit')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(raw)
    print(json.dumps({'channels': len(channels), 'historical_video_ids': len({r['video_id'] for r in inventory}),
        'statuses': {s: sum(r['status']==s for r in channels) for s in ['include', 'exclude', 'uncertain']}}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--research', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--acquisition', type=Path)
    a = p.parse_args()
    build(a.repo.resolve(), [x.resolve() for x in a.research], a.output, a.acquisition.resolve() if a.acquisition else None)
