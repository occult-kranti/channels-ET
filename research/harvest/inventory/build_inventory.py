#!/usr/bin/env python3
"""Offline inventory from pinned sources. Standard library only; no network calls."""
import argparse
import collections
import csv
import hashlib
import html
import json
import math
import pathlib
import re
import sqlite3
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
VID = re.compile(r'[A-Za-z0-9_-]{11}\Z')
URLS = re.compile(r'(?:https?://)?(?:[A-Za-z0-9-]+\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/[^\s<>"\'\\]+', re.I)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows))


def route(raw):
    raw = html.unescape(raw).rstrip('.,);]}')
    if not raw.startswith(('http://', 'https://')):
        raw = 'https://' + raw
    p = urllib.parse.urlsplit(raw)
    host = (p.hostname or '').lower()
    if host not in ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be', 'www.youtu.be', 'youtube-nocookie.com', 'www.youtube-nocookie.com']:
        return None
    path = urllib.parse.unquote(p.path).rstrip('/')
    q = urllib.parse.parse_qs(p.query)
    if host.endswith('youtu.be'):
        value = path.lstrip('/').split('/')[0]
        return ('video', value) if VID.fullmatch(value) else ('invalid_video', raw)
    if path == '/watch' or path.startswith(('/embed/', '/shorts/', '/live/', '/v/')):
        value = q.get('v', [''])[0] if path == '/watch' else path.split('/')[2]
        return ('video', value) if VID.fullmatch(value) else ('invalid_video', raw)
    if path == '/results':
        return ('query', q.get('search_query', [''])[0])
    if path == '/playlist' and q.get('list'):
        return ('playlist', q['list'][0])
    parts = path.strip('/').split('/')
    if not parts[0] or parts[0] in ['feed', 'redirect', 'attribution_link', 'clip', 'oembed', 'account', 'premium', 'about', 't', 'playlist', 'channel', 'podcast', 'podcasts'] and len(parts) == 1:
        return ('other', raw)
    if parts[0].startswith('@'):
        normalized = '/' + parts[0]
    elif parts[0] in ['channel', 'c', 'user'] and len(parts) >= 2:
        normalized = '/' + '/'.join(parts[:2])
    elif len(parts) == 1 or (len(parts) == 2 and parts[1] in ['videos', 'shorts', 'streams', 'featured', 'about', 'playlists', 'community']):
        normalized = '/' + parts[0]
    else:
        return ('other', raw)
    return ('channel', 'https://www.youtube.com' + normalized)


def duration(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if math.isfinite(value) and value > 0 else None
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if re.fullmatch(r'\d+(?::\d{1,2}){1,2}', value):
        result = 0
        for number in value.split(':'):
            result = result * 60 + int(number)
        return float(result) if result else None
    units = re.findall(r'(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)(?![a-z])', value)
    if units:
        return sum(float(n) * (3600 if u.startswith('h') else 60 if u.startswith('m') else 1) for n, u in units) or None
    return None


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    sources = {row['source_id']: row for row in manifest['files']}
    for row in sources.values():
        if sha(HERE / row['snapshot_path']) != row['sha256']:
            raise ValueError('Pinned source checksum mismatch: ' + row['source_id'])
    videos = {}; channels = {}; queries = {}; playlists = {}; invalid = {}; edges = {}; observations = collections.defaultdict(list)

    def ref(source, pointer):
        return {'source_id': source, 'locator': pointer}

    def remember(table, key, source, pointer, **fields):
        row = table.setdefault(key, {**fields, 'source_refs': []})
        r = ref(source, pointer)
        if r not in row['source_refs']:
            row['source_refs'].append(r)
        return row

    def mention(raw, source, pointer):
        parsed = route(raw)
        if parsed is None:
            return None
        kind, key = parsed
        if kind == 'video':
            remember(videos, key, source, pointer, video_id=key, source_url='https://www.youtube.com/watch?v=' + key)
        elif kind == 'channel':
            if any(part.lower() in ['query', 'queries', 'discoveryquery'] for part in pointer.split('/')):
                return ('query_embedded_route_mention', key)
            kindname = 'handle' if '/@' in key else 'platform_channel_id' if '/channel/' in key else 'legacy_custom_route'
            remember(channels, key, source, pointer, route_id='route-' + digest(key), url=key, route_type=kindname)
        elif kind == 'query':
            remember(queries, key, source, pointer, query_id='query-' + digest(key), query=key,
                     url='https://www.youtube.com/results?' + urllib.parse.urlencode({'search_query': key}))
        elif kind == 'playlist':
            remember(playlists, key, source, pointer, playlist_id=key, url='https://www.youtube.com/playlist?list=' + key)
        elif kind == 'invalid_video':
            remember(invalid, key, source, pointer, url=key, reason='YouTube video route has no valid eleven-character ID')
        return parsed

    def edge(left_type, left_id, relation, right_type, right_id, source, pointer, **extra):
        key = json.dumps([left_type, left_id, relation, right_type, right_id, extra], sort_keys=True)
        remember(edges, key, source, pointer, edge_id='edge-' + digest(key), subject_type=left_type, subject_id=left_id,
                 relation=relation, object_type=right_type, object_id=right_id, **extra)

    def scan_string(value, source, pointer):
        for match in URLS.finditer(value):
            mention(match.group(), source, pointer)

    def walk(value, source, pointer=''):
        if isinstance(value, dict):
            ids = set()
            for k in ['video_id', 'videoId']:
                if VID.fullmatch(str(value.get(k, ''))):
                    ids.add(value[k]); mention('https://www.youtube.com/watch?v=' + value[k], source, pointer + '/' + k)
            for k in ['url', 'source_url', 'youtube_url', 'watch_url']:
                if isinstance(value.get(k), str):
                    parsed = mention(value[k], source, pointer + '/' + k)
                    if parsed and parsed[0] == 'video':
                        ids.add(parsed[1])
            if source == 'channels-ET:dist/analysis/data.json' and pointer.startswith('/videos/') and VID.fullmatch(str(value.get('id', ''))):
                ids.add(value['id']); mention('https://www.youtube.com/watch?v=' + value['id'], source, pointer + '/id')
            for video_id in ids:
                title = next((value[k] for k in ['title', 'episode_title', 'raw_title'] if isinstance(value.get(k), str) and value[k]), None)
                measured = next(((k, duration(value[k])) for k in ['durationSeconds', 'duration_seconds', 'duration'] if duration(value.get(k)) is not None), (None, None))
                publisher = [value[k] for k in ['publisher', 'observedPublisher', 'channel', 'uploader'] if isinstance(value.get(k), str) and value[k]]
                observation = {'source_ref': ref(source, pointer), 'title': title, 'duration_seconds': measured[1], 'duration_field': measured[0],
                               'publisher_labels': sorted(set(publisher)), 'historical_metadata_status': value.get('retrievalStatus'),
                               'entity_labels': value.get('entityLabels', value.get('entities', [])), 'practitioner_labels': value.get('people', value.get('personNames', []))}
                if observation not in observations[video_id]:
                    observations[video_id].append(observation)
            for k, child in value.items():
                walk(child, source, pointer + '/' + str(k).replace('~', '~0').replace('/', '~1'))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, source, pointer + '/' + str(i))
        elif isinstance(value, str):
            scan_string(value, source, pointer)

    parsed_sources = {}
    for source, row in sorted(sources.items()):
        path = HERE / row['snapshot_path']; text = path.read_text()
        if path.suffix == '.json':
            value = json.loads(text); parsed_sources[source] = value; walk(value, source)
        elif path.suffix == '.html':
            for match in re.finditer(r'<script\b[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', text, re.S | re.I):
                tag = text[match.start():text.index('>', match.start())]
                name = re.search(r'\bid=["\']([^"\']+)', tag)
                walk(json.loads(match.group(1)), source, 'embedded-json:' + (name.group(1) if name else str(match.start())))
            scan_string(text, source, 'html-text')
        elif path.suffix == '.csv':
            with path.open(newline='') as stream:
                for i, cells in enumerate(csv.reader(stream)):
                    walk(cells, source, '/csv-row/' + str(i))
        else:
            scan_string(text, source, 'text')

    atlas_source = 'channels-ET:dist/data.json'; atlas = parsed_sources[atlas_source]
    analysis_source = 'channels-ET:dist/analysis/data.json'; analysis = parsed_sources[analysis_source]
    plan_source = 'channels-ET:research/expansion/acquisition/collection-plan.json'; plan = parsed_sources[plan_source]
    account_rows = []
    def channel_url(url, source, pointer):
        if isinstance(url, str):
            parsed = mention(url, source, pointer)
            if parsed and parsed[0] == 'channel':
                return parsed[1]
        return None
    def connect_video_route(video_id, url, relation, source, pointer):
        normalized = channel_url(url, source, pointer)
        if normalized and video_id in videos:
            edge('video', video_id, relation, 'channel_route', channels[normalized]['route_id'], source, pointer,
                 evidence_status='inherited_metadata_not_audio_or_current_platform_verified')
    for i, account in enumerate(analysis['channels']):
        ident = 'atlas_analysis:' + account['id']; urls = sorted(set([account['url'], *account.get('aliases', [])])); routeids = []
        for u in urls:
            c = channel_url(u, analysis_source, '/channels/' + str(i))
            if c:
                routeids.append(channels[c]['route_id']); edge('publisher_account', ident, 'has_inherited_route', 'channel_route', channels[c]['route_id'], analysis_source, '/channels/' + str(i))
        account_rows.append({'publisher_account_id': ident, 'source_account_id': account['id'], 'name': account['name'], 'channel_route_ids': sorted(set(routeids)),
                             'identity_status': 'analysis_account_group_not_verified_unique_practitioner', 'source_ref': ref(analysis_source, '/channels/' + str(i))})
    account_by_id = {x['source_account_id']: x for x in account_rows}
    for i, v in enumerate(analysis['videos']):
        account = account_by_id.get(v.get('channelId'))
        if account:
            edge('video', v['id'], 'publisher_account_in_analysis_metadata', 'publisher_account', account['publisher_account_id'], analysis_source, '/videos/' + str(i))
            for route_id in account['channel_route_ids']:
                edge('video', v['id'], 'publisher_route_via_explicit_account_id', 'channel_route', route_id, analysis_source, '/videos/' + str(i), evidence_status='inherited_metadata_not_audio_or_current_platform_verified')
    discovery = atlas['discovery']; persons = discovery['people']
    for i, person in enumerate(persons):
        for u in person.get('videoUrls', []):
            parsed = route(u)
            if parsed and parsed[0] == 'video':
                edge('practitioner_candidate', person['id'], 'associated_video_in_discovery', 'video', parsed[1], atlas_source, '/discovery/people/' + str(i), actual_speaker_status='unknown_not_audio_verified')
        for u in person.get('accountUrls', []):
            normalized = channel_url(u, atlas_source, '/discovery/people/' + str(i))
            if normalized:
                edge('practitioner_candidate', person['id'], 'associated_route_in_discovery', 'channel_route', channels[normalized]['route_id'], atlas_source, '/discovery/people/' + str(i), actual_speaker_status='unknown_not_audio_verified')
    for i, item in enumerate(discovery['records']):
        parsed = route(item.get('url', ''))
        own_routes = [item.get('accountUrl'), *item.get('accountUrls', [])]
        if parsed and parsed[0] == 'video':
            for u in own_routes:
                connect_video_route(parsed[1], u, 'associated_route_in_discovery_record', atlas_source, '/discovery/records/' + str(i))
        if parsed and parsed[0] == 'channel':
            canonical = channels[parsed[1]]['route_id']
            for alias in item.get('aliases', []):
                normalized = channel_url(alias, atlas_source, '/discovery/records/' + str(i) + '/aliases')
                if normalized and channels[normalized]['route_id'] != canonical:
                    edge('channel_route', canonical, 'explicit_alias_in_inherited_record', 'channel_route', channels[normalized]['route_id'], atlas_source, '/discovery/records/' + str(i), current_platform_resolution='not_checked')
    official_accounts = {a['id']: a for a in atlas['youtube']['accounts']}
    for i, account in enumerate(atlas['youtube']['accounts']):
        normalized = channel_url(account['url'], atlas_source, '/youtube/accounts/' + str(i))
        for profile_id in account.get('profileIds', []):
            if normalized:
                edge('practitioner_profile', profile_id, 'associated_route_in_youtube_layer', 'channel_route', channels[normalized]['route_id'], atlas_source, '/youtube/accounts/' + str(i), actual_speaker_status='unknown_not_audio_verified')
    for i, v in enumerate(atlas['youtube']['videos']):
        account = official_accounts.get(v.get('accountId'))
        parsed = route(v.get('url', ''))
        if account and parsed and parsed[0] == 'video':
            connect_video_route(parsed[1], account['url'], 'associated_account_in_youtube_layer', atlas_source, '/youtube/videos/' + str(i))
        if parsed and parsed[0] == 'video':
            for profile_id in v.get('profileIds', []):
                edge('practitioner_profile', profile_id, 'associated_video_in_youtube_layer', 'video', parsed[1], atlas_source, '/youtube/videos/' + str(i), actual_speaker_status='unknown_not_audio_verified')
    for i, account in enumerate(plan['accounts']):
        normalized = channel_url(account['url'], plan_source, '/accounts/' + str(i))
        if normalized:
            for person_id in account.get('person_ids', []):
                edge('practitioner_candidate', person_id, 'associated_route_in_collection_plan', 'channel_route', channels[normalized]['route_id'], plan_source, '/accounts/' + str(i), actual_speaker_status='unknown_not_audio_verified')
    divine_source = 'bashar-index:data/divine_light_vibes_channel.json'
    divine = parsed_sources[divine_source]
    for i, item in enumerate(divine['videos']):
        if VID.fullmatch(item.get('video_id', '')):
            for u in [divine.get('channel_url'), divine.get('channel_id_url')]:
                connect_video_route(item['video_id'], u, 'listed_video_in_explicit_channel_source', divine_source, '/videos/' + str(i))

    edge_rows = sorted(edges.values(), key=lambda x: x['edge_id'])
    by_video = collections.defaultdict(list); by_route = collections.defaultdict(list)
    for item in edge_rows:
        if item['subject_type'] == 'video':
            by_video[item['subject_id']].append(item)
        if item['object_type'] == 'channel_route':
            by_route[item['object_id']].append(item)
        if item['object_type'] == 'video':
            by_video[item['object_id']].append(item)
    def priority(observation):
        source = observation['source_ref']['source_id']
        return (0 if source == analysis_source else 1 if source == 'bashar-index:data/podcasts.json' else 2 if source.startswith('bashar-index:') else 3, source, observation['source_ref']['locator'])
    for video_id, row in videos.items():
        obs = sorted(observations[video_id], key=priority); measured = [o for o in obs if o['duration_seconds'] is not None]
        row.update(title=next((o['title'] for o in obs if o['title']), None), duration_seconds=measured[0]['duration_seconds'] if measured else None,
                   duration_source_ref=measured[0]['source_ref'] if measured else None,
                   duration_conflict_values=sorted({o['duration_seconds'] for o in measured}) if len({o['duration_seconds'] for o in measured}) > 1 else [],
                   publisher_labels=sorted({label for o in obs for label in o['publisher_labels']}),
                   publisher_account_ids=sorted({e['object_id'] for e in by_video[video_id] if e['object_type'] == 'publisher_account'}),
                   channel_route_ids=sorted({e['object_id'] for e in by_video[video_id] if e['object_type'] == 'channel_route'}),
                   person_ids=sorted({e['subject_id'] for e in by_video[video_id] if e['subject_type'] == 'practitioner_candidate'}),
                   profile_ids=sorted({e['subject_id'] for e in by_video[video_id] if e['subject_type'] == 'practitioner_profile'}),
                   entity_labels=sorted({label for o in obs for label in (o['entity_labels'] if isinstance(o['entity_labels'], list) else []) if isinstance(label, str)}),
                   metadata_observations=obs, historical_metadata_statuses=sorted({o['historical_metadata_status'] for o in obs if o['historical_metadata_status']}),
                   source_kind='youtube_video', source_id='youtube:' + video_id,
                   status='indexed_not_checked', availability='not_checked', actual_speaker_status='unknown_not_audio_verified')
    video_rows = sorted(videos.values(), key=lambda x: x['video_id'])
    route_rows = sorted(channels.values(), key=lambda x: x['route_id'])
    historical_plan_urls = {route(a['url'])[1] for a in plan['accounts']}
    for row in route_rows:
        es = by_route[row['route_id']]
        row.update(person_ids=sorted({e['subject_id'] for e in es if e['subject_type'] == 'practitioner_candidate'}),
                   profile_ids=sorted({e['subject_id'] for e in es if e['subject_type'] == 'practitioner_profile'}),
                   known_video_ids=sorted({e['subject_id'] for e in es if e['subject_type'] == 'video'}),
                   known_video_count=len({e['subject_id'] for e in es if e['subject_type'] == 'video'}),
                   explicit_aliases=sorted({e['object_id'] for e in edge_rows if e['subject_type'] == 'channel_route' and e['subject_id'] == row['route_id'] and e['relation'] == 'explicit_alias_in_inherited_record'}),
                   enumeration_status='not_enumerated', identity_status='literal_inherited_route_not_current_platform_identity_or_speaker_verification',
                   in_historical_157_route_plan=row['url'] in historical_plan_urls)
    podcast_source = 'bashar-index:data/podcasts.json'
    podcast_rows = []
    for i, item in enumerate(parsed_sources[podcast_source]):
        linked = route(item.get('youtube_url') or '')
        links = [{'source_kind': kind, 'source_id': 'youtube:' + route(item[key])[1] if kind == 'youtube_video' and route(item[key]) and route(item[key])[0] == 'video' else kind + ':' + digest(item[key]), 'source_url': item[key], 'status': 'indexed_not_checked'}
                 for key, kind in [('apple_url', 'apple_podcast_episode'), ('spotify_url', 'spotify_episode'), ('youtube_url', 'youtube_video')]
                 if isinstance(item.get(key), str) and item[key]]
        podcast_rows.append({'source_kind': 'podcast_episode_index_record', 'source_id': 'bashar-podcast-row-' + str(i).zfill(3),
                             'show': item.get('show'), 'host': item.get('host'), 'episode_title': item.get('episode_title'), 'date': item.get('date'),
                             'duration_seconds': duration(item.get('duration')), 'source_links': links,
                             'linked_youtube_video_ids': [linked[1]] if linked and linked[0] == 'video' else [],
                             'youtube_association_basis': 'explicit_same_row_link_not_independently_verified_edition_identity',
                             'primary_publisher_identity': 'not_resolved_by_this_offline_inventory', 'rss_url': None, 'enclosure_url': None,
                             'status': 'indexed_not_checked', 'source_ref': ref(podcast_source, '/' + str(i)),
                             'source_sha256': sources[podcast_source]['sha256'], 'original_record': item})
    # Reference ordering is canonical, independent of traversal/insertion order.
    for rows in [video_rows, route_rows, list(queries.values()), list(playlists.values()), list(invalid.values()), edge_rows]:
        for row in rows:
            row['source_refs'].sort(key=lambda r: (r['source_id'], r['locator']))
    original_ids = {v['video_id'] for v in video_rows if any(r['source_id'].startswith('bashar-index:') for r in v['source_refs'])}
    analysis_ids = {v['id'] for v in analysis['videos']}
    seconds = sum(v['duration_seconds'] or 0 for v in video_rows); known = sum(v['duration_seconds'] is not None for v in video_rows)
    storage = []
    for name, bps in [('audio_64kbps', 64000), ('audio_128kbps', 128000), ('audio_192kbps', 192000), ('av_512kbps', 512000), ('av_1500kbps', 1500000), ('av_3500kbps', 3500000)]:
        size = math.ceil(seconds * bps / 8)
        storage.append({'scenario': name, 'assumed_total_bits_per_second': bps, 'known_duration_payload_bytes': size, 'known_duration_payload_gib': size / 1024**3,
                        'ideal_transfer_hours_at_50mbps': size * 8 / 50000000 / 3600})
    summary = {'schema_version': 1, 'source_manifest_sha256': sha(HERE / 'source-manifest.json'), 'source_captured_at': manifest['captured_at'],
               'inventory_status': 'offline_source_inventory_complete_not_a_platform_crawl',
               'counts': {'unique_video_ids': len(video_rows), 'original_bashar_root_video_ids': len(original_ids), 'current_analysis_video_ids': len(analysis_ids),
                          'original_analysis_overlap': len(original_ids & analysis_ids), 'original_only_video_ids': len(original_ids - analysis_ids),
                          'inventory_beyond_current_analysis': len(set(videos) - analysis_ids), 'channel_routes': len(route_rows), 'historical_plan_channel_routes': len(historical_plan_urls),
                          'routes_in_historical_plan_present': sum(x['in_historical_157_route_plan'] for x in route_rows), 'keyword_queries': len(queries), 'playlists': len(playlists),
                          'practitioner_candidates_from_discovery': len(persons), 'publisher_account_groups_from_analysis': len(account_rows), 'explicit_relationship_edges': len(edge_rows),
                          'practitioner_profiles_from_earlier_atlas': len(atlas['profiles']),
                          'videos_with_explicit_route_association': sum(bool(v['channel_route_ids']) for v in video_rows), 'videos_with_no_explicit_route_association': sum(not v['channel_route_ids'] for v in video_rows),
                          'videos_with_duration': known, 'videos_missing_duration': len(video_rows) - known, 'duration_conflict_video_ids': sum(bool(v['duration_conflict_values']) for v in video_rows),
                          'malformed_video_url_mentions': len(invalid)},
               'auxiliary_media_counts': {'podcast_index_rows': len(podcast_rows), 'podcast_rows_with_explicit_youtube_link': sum(bool(x['linked_youtube_video_ids']) for x in podcast_rows),
                                          'podcast_rows_with_apple_link': sum(bool(x.get('apple_url')) for x in parsed_sources[podcast_source]),
                                          'podcast_rows_with_spotify_link': sum(bool(x.get('spotify_url')) for x in parsed_sources[podcast_source]),
                                          'primary_rss_enclosures_verified_by_this_inventory': 0},
               'duration': {'known_seconds': seconds, 'known_hours': seconds / 3600, 'coverage_fraction': known / len(video_rows), 'selection_rule': 'Prefer positive measured current-analysis duration, then explicit podcast duration, then other positive recorded duration; preserve alternatives and conflicts. Never estimate from word count.'},
               'storage_scenarios': storage,
               'download_state': {'attempted': 0, 'saved': 0, 'failed': 0, 'queued': 0, 'inventory_only': len(video_rows), 'bytes_saved': 0, 'scope': 'This offline inventory; acquisition run ledger is authoritative for executed downloads.'},
               'scheduling': {'recommended_order': ['Public-access preflight', 'Enumerate every inherited channel route and playlist without a total-channel completeness claim', 'Refresh metadata and unavailable/private/deleted outcomes for unique video IDs', 'Save offered captions for all eligible IDs with per-ID outcomes', 'Download media in resumable byte-quota batches with stable IDs and one shared download archive'],
                              'initial_media_concurrency': 1, 'caption_metadata_concurrency': 2, 'quota_reserve_fraction': 0.15, 'deduplication_unit': 'YouTube video ID; recording/session duplicates remain unresolved',
                              'no_total_size_claim': 'Full channel expansion and missing durations are unknown. These bitrate scenarios cover known indexed duration only; overhead, separate redundant encodes and future discoveries add bytes.'},
               'limitations': ['Indexed links do not establish current availability, permission, playback, a completed download or exhaustive channel coverage.', 'Channel routes, account groups, publisher labels, practitioner candidates and actual speakers are distinct units.', 'Literal route normalization removes listing suffixes and transport/query variation only; names and undocumented numeric/handle aliases are not merged.', 'Explicit route/video associations retain their inherited relation type and may be weaker than a platform-verified uploader identity.', 'Original session catalogue rows without YouTube IDs remain catalogue records; 684 sessions is not 684 downloadable YouTube videos.', 'Storage estimates use hypothetical constant combined payload bitrates and known durations only, not observed encodings or a bound on all channels.']}
    jsonl(output / 'videos.jsonl', video_rows); dump(output / 'channel-routes.json', {'schema_version': 1, 'records': route_rows})
    jsonl(output / 'edges.jsonl', edge_rows); jsonl(output / 'queries.jsonl', sorted(queries.values(), key=lambda x: x['query_id']))
    jsonl(output / 'playlists.jsonl', sorted(playlists.values(), key=lambda x: x['playlist_id'])); jsonl(output / 'rejected-video-mentions.jsonl', sorted(invalid.values(), key=lambda x: x['url']))
    jsonl(output / 'podcast-sources.jsonl', podcast_rows)
    dump(output / 'publisher-accounts.json', {'schema_version': 1, 'records': account_rows}); dump(output / 'practitioner-candidates.json', {'schema_version': 1, 'records': persons}); dump(output / 'practitioner-profiles.json', {'schema_version': 1, 'records': atlas['profiles']}); dump(output / 'summary.json', summary)
    dbpath = output / 'inventory.sqlite'
    if dbpath.exists(): dbpath.unlink()
    db = sqlite3.connect(dbpath)
    db.executescript('CREATE TABLE sources(source_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, record_json TEXT NOT NULL); CREATE TABLE videos(video_id TEXT PRIMARY KEY, source_url TEXT NOT NULL, title TEXT, duration_seconds REAL, status TEXT NOT NULL, record_json TEXT NOT NULL); CREATE TABLE channel_routes(route_id TEXT PRIMARY KEY,url TEXT UNIQUE NOT NULL,known_video_count INTEGER NOT NULL,record_json TEXT NOT NULL); CREATE TABLE edges(edge_id TEXT PRIMARY KEY,subject_type TEXT,subject_id TEXT,relation TEXT,object_type TEXT,object_id TEXT,record_json TEXT); CREATE TABLE queries(query_id TEXT PRIMARY KEY,query TEXT,record_json TEXT); CREATE TABLE playlists(playlist_id TEXT PRIMARY KEY,record_json TEXT); CREATE TABLE podcast_sources(source_id TEXT PRIMARY KEY,source_kind TEXT,record_json TEXT); CREATE TABLE practitioner_profiles(profile_id TEXT PRIMARY KEY,record_json TEXT); CREATE INDEX edges_subject ON edges(subject_type,subject_id); CREATE INDEX edges_object ON edges(object_type,object_id);')
    for row in sources.values(): db.execute('INSERT INTO sources VALUES(?,?,?)', (row['source_id'], row['sha256'], json.dumps(row, ensure_ascii=False)))
    for row in video_rows: db.execute('INSERT INTO videos VALUES(?,?,?,?,?,?)', (row['video_id'], row['source_url'], row['title'], row['duration_seconds'], row['status'], json.dumps(row, ensure_ascii=False)))
    for row in route_rows: db.execute('INSERT INTO channel_routes VALUES(?,?,?,?)', (row['route_id'], row['url'], row['known_video_count'], json.dumps(row, ensure_ascii=False)))
    for row in edge_rows: db.execute('INSERT INTO edges VALUES(?,?,?,?,?,?,?)', tuple(row[k] for k in ['edge_id','subject_type','subject_id','relation','object_type','object_id']) + (json.dumps(row, ensure_ascii=False),))
    for row in queries.values(): db.execute('INSERT INTO queries VALUES(?,?,?)', (row['query_id'], row['query'], json.dumps(row, ensure_ascii=False)))
    for row in playlists.values(): db.execute('INSERT INTO playlists VALUES(?,?)', (row['playlist_id'], json.dumps(row, ensure_ascii=False)))
    for row in podcast_rows: db.execute('INSERT INTO podcast_sources VALUES(?,?,?)', (row['source_id'], row['source_kind'], json.dumps(row, ensure_ascii=False)))
    for row in atlas['profiles']: db.execute('INSERT INTO practitioner_profiles VALUES(?,?)', (row['id'], json.dumps(row, ensure_ascii=False)))
    db.commit(); db.close()
    print(json.dumps(summary['counts']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=pathlib.Path, default=HERE)
    main(parser.parse_args().output)
