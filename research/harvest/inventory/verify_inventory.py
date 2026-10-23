#!/usr/bin/env python3
"""Independent source/grain/duration/database checks plus isolated reproduction."""
import collections
import hashlib
import json
import math
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
checks = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


def rows(name):
    return [json.loads(line) for line in (HERE / name).read_text().splitlines() if line]


manifest = json.loads((HERE / 'source-manifest.json').read_text())
sources = {s['source_id']: s for s in manifest['files']}
for item in sources.values():
    check(sha(HERE / item['snapshot_path']) == item['sha256'], 'Pinned source: ' + item['source_id'])
videos = rows('videos.jsonl'); routes = json.loads((HERE / 'channel-routes.json').read_text())['records']; edges = rows('edges.jsonl'); podcasts = rows('podcast-sources.jsonl')
summary = json.loads((HERE / 'summary.json').read_text())
identifiers = {v['video_id'] for v in videos}; routeids = {r['route_id'] for r in routes}
check(len(identifiers) == len(videos) == summary['counts']['unique_video_ids'], 'Unique video-ID grain')
check(all(re.fullmatch(r'[A-Za-z0-9_-]{11}', i) for i in identifiers), 'Every exported video ID is syntactically valid')
check(len(routeids) == len(routes) == len({r['url'] for r in routes}), 'Unique literal-route grain')
check(not any(r['url'].endswith(('/playlist', '/channel', '/podcast', '/watch', '/results')) for r in routes), 'Navigation and query templates are not channel jobs')
check(all(v['availability'] == 'not_checked' and v['status'] == 'indexed_not_checked' for v in videos), 'Inventory does not claim acquisition or current availability')
check(all(r['enumeration_status'] == 'not_enumerated' for r in routes), 'Inventory does not claim channel enumeration')

# Independent raw-link extraction uses a separate regular expression, not producer code.
found = set(); original = set()
raw_pattern = re.compile(r'(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?[^\s<>"\']*?\bv=|(?:embed|shorts|live|v)/))([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])', re.I)
for item in sources.values():
    ids = set(raw_pattern.findall((HERE / item['snapshot_path']).read_text()))
    found.update(ids)
    if item['repository'] == 'bashar-index':
        original.update(ids)
check(found == identifiers, 'Independent complete raw-link extraction matches exported IDs')
check(len(original) == summary['counts']['original_bashar_root_video_ids'], 'Original root source count independently reproduced')
analysis_source = sources['channels-ET:dist/analysis/data.json']; analysis = json.loads((HERE / analysis_source['snapshot_path']).read_text())
expected = {v['id']: v for v in analysis['videos']}; by_id = {v['video_id']: v for v in videos}
check(set(expected) <= identifiers and len(expected) == 925, 'Complete current925 retained')
check(len(original & set(expected)) == summary['counts']['original_analysis_overlap'], 'Original/current intersection count')
check(len(identifiers - set(expected)) == summary['counts']['inventory_beyond_current_analysis'], 'Additional ID count')
known = [v for v in videos if isinstance(v['duration_seconds'], (int, float)) and v['duration_seconds'] > 0]
check(len(known) == summary['counts']['videos_with_duration'], 'Positive duration denominator')
check(len(videos) - len(known) == summary['counts']['videos_missing_duration'], 'Missing duration denominator')
seconds = math.fsum(v['duration_seconds'] for v in known)
check(seconds == summary['duration']['known_seconds'], 'Duration sum')
for video_id, record in expected.items():
    duration = record.get('durationSeconds')
    if isinstance(duration, (int, float)) and duration > 0:
        check(by_id[video_id]['duration_seconds'] == duration, 'Measured analysis duration preferred: ' + video_id)
for scenario in summary['storage_scenarios']:
    check(scenario['known_duration_payload_bytes'] == math.ceil(seconds * scenario['assumed_total_bits_per_second'] / 8), 'Storage arithmetic: ' + scenario['scenario'])
    check(abs(scenario['known_duration_payload_gib'] - scenario['known_duration_payload_bytes'] / 1024**3) < 1e-12, 'GiB conversion: ' + scenario['scenario'])

people = json.loads((HERE / 'practitioner-candidates.json').read_text())['records']; personids = {p['id'] for p in people}
accounts = json.loads((HERE / 'publisher-accounts.json').read_text())['records']; accountids = {a['publisher_account_id'] for a in accounts}
profiles = json.loads((HERE / 'practitioner-profiles.json').read_text())['records']
domain = {'video': identifiers, 'channel_route': routeids, 'practitioner_candidate': personids, 'publisher_account': accountids, 'practitioner_profile': {p['id'] for p in profiles}}
for item in edges:
    check(item['subject_id'] in domain[item['subject_type']] and item['object_id'] in domain[item['object_type']], 'Relationship has no orphan: ' + item['edge_id'])
for channel in routes:
    associated = {e['subject_id'] for e in edges if e['subject_type'] == 'video' and e['object_type'] == 'channel_route' and e['object_id'] == channel['route_id']}
    check(associated == set(channel['known_video_ids']) and len(associated) == channel['known_video_count'], 'Explicit route membership count: ' + channel['route_id'])
for video in videos:
    for r in video['source_refs']:
        check(r['source_id'] in sources, 'Video source reference exists: ' + video['video_id'])

podcast_original = json.loads((HERE / sources['bashar-index:data/podcasts.json']['snapshot_path']).read_text())
check(len(podcasts) == len(podcast_original) == 48, 'All48 original podcast rows preserved')
for i, (episode, original_record) in enumerate(zip(podcasts, podcast_original)):
    check(episode['original_record'] == original_record, 'Podcast original row preserved: ' + str(i))
    own_yt = set(raw_pattern.findall(original_record.get('youtube_url') or ''))
    check(own_yt == set(episode['linked_youtube_video_ids']), 'Podcast explicit same-row YouTube relation only: ' + str(i))
    check(not episode['rss_url'] and not episode['enclosure_url'] and episode['primary_publisher_identity'] == 'not_resolved_by_this_offline_inventory', 'Podcast inventory makes no primary-source inference: ' + str(i))

with sqlite3.connect(HERE / 'inventory.sqlite') as db:
    check(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity')
    for table, n in [('sources', len(sources)), ('videos', len(videos)), ('channel_routes', len(routes)), ('edges', len(edges)), ('podcast_sources', len(podcasts)), ('practitioner_profiles', len(profiles))]:
        check(db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == n, 'SQLite row count: ' + table)
    check(db.execute('SELECT sum(duration_seconds) FROM videos').fetchone()[0] == seconds, 'SQLite duration sum')

with tempfile.TemporaryDirectory(prefix='channels-et-inventory-reproduce-') as scratch:
    temp = pathlib.Path(scratch)
    subprocess.run([sys.executable, str(HERE / 'build_inventory.py'), '--output', str(temp)], check=True, capture_output=True, text=True)
    reproduced = []
    for other in sorted(temp.iterdir()):
        current = HERE / other.name
        same = current.read_bytes() == other.read_bytes()
        check(same, 'Fresh-directory byte reproduction: ' + other.name)
        reproduced.append({'path': other.name, 'sha256': sha(current), 'reproduced_sha256': sha(other), 'identical': same})

receipt = {'status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL', 'checks': len(checks), 'passed': sum(c['passed'] for c in checks),
           'failed': [c for c in checks if not c['passed']], 'summary_sha256': sha(HERE / 'summary.json'), 'source_manifest_sha256': sha(HERE / 'source-manifest.json'),
           'source_files_verified': len(sources), 'numerical_and_database_reproduction': reproduced,
           'scope': 'Offline source inventory, grain, joins, explicit attribution, durations, storage arithmetic and reproducibility only; no network or semantic/speaker validation.'}
(HERE / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'numerical_and_database_reproduction'}))
raise SystemExit(receipt['status'] != 'PASS')
