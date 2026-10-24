#!/usr/bin/env python3
"""Independent source joins for the storage tables; never acquires source data."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(condition, label):
    assert condition, label
    checks.append(label)

j = read(HERE/'distributions.json')
videos = [json.loads(line) for line in (ROOT/'research/harvest/inventory/videos.jsonl').read_text().splitlines()]
decisions = {r['video_id']:r for r in [json.loads(line) for line in (ROOT/'research/collection-policy/selection.jsonl').read_text().splitlines()]}
people = {r['id']:r for r in read(ROOT/'research/harvest/inventory/practitioner-candidates.json')['records']}
check(len(videos) == len({r['video_id'] for r in videos}) == j['summary']['indexedYouTubeIds'], 'Unique indexed ID denominator')
check(sum(r['selected_default'] for r in decisions.values()) == j['summary']['selectedYouTubeIds'], 'Selected count joins current policy')
fields = {'byRoute':'channel_route_ids','byPublisherGroup':'publisher_account_ids',
          'byPractitionerAssociation':'person_ids','byEntityLabel':'entity_labels'}
for name, rows in j['youtube'].items():
    for row in rows:
        if name == 'byPublisherDeclaredCivilization':
            wanted = {v['video_id'] for v in videos if any(row['id'] in people[p].get('civilizations',[]) for p in v['person_ids'] if p in people)}
        else:
            wanted = {v['video_id'] for v in videos if row['id'] in v[fields[name]]}
        check(set(row['video_ids']) == wanted and len(row['video_ids']) == row['indexed_ids'], name+' membership '+row['id'])
        check(row['selected_ids'] == sum(decisions[v]['selected_default'] for v in wanted), name+' selected join '+row['id'])
        check(row['youtube_downloaded_bytes'] == row['youtube_downloaded_video_files'] == row['youtube_downloaded_caption_files'] == 0, name+' zero actual YouTube artifacts '+row['id'])
    coverage = j['attributionCoverage'][name]
    assigned = set().union(*(set(r['video_ids']) for r in rows))
    check(coverage['assignedUniqueIds']==len(assigned), name+' attributed unique coverage')
    check(coverage['unassignedUniqueIds']==len(videos)-len(assigned), name+' missing attribution count')
    check(set(coverage['unassignedVideoIds'])==set(decisions)-assigned, name+' explicit missing attribution IDs')
    check(coverage['groupMemberships']==sum(r['indexed_ids'] for r in rows), name+' overlapping group memberships')
check(len(j['youtube']['byRoute']) == len(read(ROOT/'research/harvest/inventory/channel-routes.json')['records']) == 362, 'All literal routes including zero-indexed routes')
plan = read(ROOT/'research/storage-drive/archive-plan.json')
audio = read(ROOT/'research/harvest/publisher_sources/publisher-summary.json')['records'] + read(ROOT/'research/access-repair/athina/publisher_sources/publisher-summary.json')['records']
audio = {r['source_id']:r for r in audio if r['status']=='completed'}
for view, rows in j['sourceStorage'].items():
    check(sum(r['canonical_source_artifacts'] for r in rows) == len(plan['files']) == 99, view+' artifact partition')
    check(sum(r['canonical_source_bytes'] for r in rows) == sum(r['bytes'] for r in plan['files']), view+' byte partition')
    check(sum(r['source_recordings'] for r in rows) == len(audio) == 20, view+' unique recording count')
    check(math.isclose(sum(r['recorded_audio_seconds'] for r in rows), sum(r['duration_seconds'] for r in audio.values()), abs_tol=1e-6), view+' unique recording durations')
    kinds = Counter()
    for row in rows:
        kinds.update(row['artifacts_by_kind'])
    check(kinds == Counter(r['kind'] for r in plan['files']), view+' artifact kinds')
paul = [r for r in j['sourceStorage']['bySourceContext'] if r['label'].startswith('Paul')]
feed = [r for r in j['sourceStorage']['bySourceContext'] if 'catalog metadata' in r['label']]
check(len(paul)==1 and paul[0]['canonical_source_artifacts']==3 and 'athina-feed' not in paul[0]['source_ids'], 'Athina feed is never attributed to Paul Selig')
check(len(feed)==1 and feed[0]['canonical_source_artifacts']==1 and feed[0]['source_recordings']==0, 'Creator feed metadata is not speech')
state = read(ROOT/'research/cloud-archive/archive-state.json')
check(j['localArchive']==state and state['actual_local_archive_completed'] and state['hash_verified'], 'Actual source-bound archive state')
check(state['actual_local_files']==200 and state['actual_local_bytes']==1703879268, 'Archive includes99 sources and101 metadata files')
check(state['actual_drive_uploaded_files']==0 and state['chat_attachment_created'] is False, 'Storage backend distinctions remain explicit')
manifest = read(HERE/'source-manifest.json')
for row in manifest['inputs']:
    path = ROOT/row['path']
    check(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'], 'Input pin '+row['path'])
check(sha(HERE/'distributions.json')==manifest['outputSha256'], 'Output content hash')
receipt = {'status':'PASS','checkedAt':datetime.now(timezone.utc).isoformat(),'checks':len(checks),
           'scope':'Independent JSON source joins, partition counts, retained durations and storage backend semantics',
           'networkRequests':0,'sourceBodiesPublished':False,'distributionsSha256':sha(HERE/'distributions.json'),
           'builderSha256':sha(HERE/'build_distributions.py'),'verifierSha256':sha(Path(__file__)),
           'labelsAreOverlappingMetadataAssociations':True,'wholeChannelLifetimeCountsKnown':False}
(HERE/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
