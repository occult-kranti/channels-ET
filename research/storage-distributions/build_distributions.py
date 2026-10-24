#!/usr/bin/env python3
"""Source-bound storage and indexed-video distributions; never acquires media."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = {
    'videos': 'research/harvest/inventory/videos.jsonl',
    'routes': 'research/harvest/inventory/channel-routes.json',
    'practitioners': 'research/harvest/inventory/practitioner-candidates.json',
    'selection': 'research/collection-policy/selection.jsonl',
    'policy': 'research/collection-policy/summary.json',
    'originalAudio': 'research/harvest/publisher_sources/publisher-summary.json',
    'athinaAudio': 'research/access-repair/athina/publisher_sources/publisher-summary.json',
    'archivePlan': 'research/storage-drive/archive-plan.json',
    'oldArtifacts': 'research/harvest/artifacts.json',
    'runner': 'research/collection-runner/plan-summary.json',
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    if path.suffix == '.jsonl':
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return json.loads(path.read_text())

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def csv_rows(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k,v in row.items()})

def build(output=HERE, archive_state=None):
    output.mkdir(parents=True, exist_ok=True)
    data = {key: load(ROOT / name) for key,name in INPUTS.items()}
    pins = [{'key': k, 'path': p, 'bytes': (ROOT/p).stat().st_size, 'sha256': digest(ROOT/p)} for k,p in INPUTS.items()]
    if archive_state is not None:
        local = load(archive_state)
        pins.append({'key': 'actualArchive', 'path': str(archive_state.relative_to(ROOT)),
                     'bytes': archive_state.stat().st_size, 'sha256': digest(archive_state)})
    else:
        local = {'status': 'archive_state_not_loaded', 'actual_local_archive_created': None}
    # Nonzero future YouTube collections require artifact-level attribution; never guess it from RSS titles.
    assert not data['oldArtifacts']['records'], 'Reconcile new actual YouTube artifacts before rebuilding distributions'
    assert data['runner']['verified_quarantine_artifacts'] == 0, 'Require actual per-ID artifact export'
    videos = {r['video_id']: r for r in data['videos']}
    decisions = {r['video_id']: r for r in data['selection']}
    assert set(videos) == set(decisions)
    people = {r['id']: r for r in data['practitioners']['records']}

    def group_rows(assignments, labels=None):
        groups = defaultdict(set)
        for vid,record in videos.items():
            for key in set(assignments(record)):
                if isinstance(key, str) and key:
                    groups[key].add(vid)
        result = []
        for key, ids in sorted(groups.items()):
            chosen = [decisions[i] for i in ids]
            measured = [r['duration_seconds'] for r in chosen if r['duration_state'] in ('eligible_duration','under_minimum')]
            result.append({'id': key, 'label': labels.get(key,key) if labels else key,
                           'indexed_ids': len(ids), 'eligible_ids': sum(r['eligible_on_inherited_metadata'] for r in chosen),
                           'selected_ids': sum(r['selected_default'] for r in chosen),
                           'under_minimum_ids': sum(r['duration_state']=='under_minimum' for r in chosen),
                           'unknown_duration_ids': sum(r['duration_state']=='unknown' for r in chosen),
                           'conflicting_duration_ids': sum(r['duration_state']=='conflicting' for r in chosen),
                           'unconflicted_measured_upload_seconds': sum(measured),
                           'measured_upload_ids': len(measured), 'youtube_downloaded_video_files': 0,
                           'youtube_downloaded_caption_files': 0, 'youtube_downloaded_bytes': 0,
                           'video_ids': sorted(ids), 'membership': 'overlapping_inherited_metadata_association'})
        return result

    by_route = {r['id']:r for r in group_rows(lambda r:r['channel_route_ids'])}
    routes = []
    for route in data['routes']['records']:
        row = by_route.get(route['route_id'], {'id':route['route_id'], 'label':route['url'],
            'indexed_ids':0,'eligible_ids':0,'selected_ids':0,'under_minimum_ids':0,'unknown_duration_ids':0,
            'conflicting_duration_ids':0,'unconflicted_measured_upload_seconds':0,'measured_upload_ids':0,
            'youtube_downloaded_video_files':0,'youtube_downloaded_caption_files':0,'youtube_downloaded_bytes':0,
            'video_ids':[],'membership':'overlapping_inherited_metadata_association'})
        row.update({'label':route['url'], 'url':route['url'], 'whole_channel_lifetime_count':None,
                    'enumeration_status':route['enumeration_status']})
        routes.append(row)
    accounts = group_rows(lambda r:r['publisher_account_ids'])
    for account in accounts:
        labels=sorted({label for vid in account['video_ids'] for label in videos[vid]['publisher_labels']})
        readable=[label for label in labels if not label.startswith('@')]
        account['publisher_labels']=labels
        account['label']=' / '.join((readable or labels)[:2]) or account['id']
    practitioners = group_rows(lambda r:r['person_ids'], {k:v['name'] for k,v in people.items()})
    entities = group_rows(lambda r:r['entity_labels'])
    civilizations = group_rows(lambda r:[label for p in r['person_ids'] if p in people for label in people[p].get('civilizations',[])])

    audio = data['originalAudio']['records'] + data['athinaAudio']['records']
    audio = [r for r in audio if r['status']=='completed']
    audio_by_id = {r['source_id']:r for r in audio}
    original_ids = {r['source_id'] for r in data['originalAudio']['records']}
    def context(row):
        if row['source_id'] in original_ids:
            return 'Bashar-related interviews, promotion and commentary; speakers unverified'
        if row['source_id'] in audio_by_id:
            return 'Athina Król creator episode; publisher-attributed Ashtar context'
        if row['practitioner']=='Athina Król':
            return 'Athina Król creator-feed catalog metadata; not episode speech'
        if row['practitioner']=='Daniel Scranton':
            return 'Daniel Scranton authored messages; entity labels require textual evidence'
        if row['practitioner']=='Paul Selig':
            return 'Paul Selig spiritual-Guides authored transcript comparison'
        raise ValueError('Unresolved source context; add source-linked attribution before reporting it')

    files = data['archivePlan']['files']
    def storage_groups(key):
        grouped = defaultdict(list)
        for row in files:
            grouped[key(row)].append(row)
        result = []
        for label, records in sorted(grouped.items()):
            ids = {r['source_id'] for r in records}
            audio_ids = {i for i in ids if i in audio_by_id}
            result.append({'label':label,'canonical_source_artifacts':len(records),
                'canonical_source_bytes':sum(r['bytes'] for r in records),
                'artifacts_by_kind':dict(Counter(r['kind'] for r in records)),
                'source_recordings':len(audio_ids),
                'recorded_audio_seconds':sum(audio_by_id[i]['duration_seconds'] for i in audio_ids),
                'source_ids':sorted(ids),'speaker_attribution':'source_context_only_not_verified_speaker_turns',
                'youtube_edition_equivalence_verified':False})
        return result
    storage = {'byPublisher':storage_groups(lambda r:r['uploader']),
               'byPractitionerContext':storage_groups(lambda r:r['practitioner']),
               'bySourceContext':storage_groups(context),
               'byProvider':storage_groups(lambda r:r['provider'])}
    youtube_views = {'byRoute':routes,'byPublisherGroup':accounts,'byPractitionerAssociation':practitioners,
                     'byEntityLabel':entities,'byPublisherDeclaredCivilization':civilizations}
    coverage = {}
    for name, rows in youtube_views.items():
        assigned = set().union(*(set(r['video_ids']) for r in rows))
        memberships = sum(r['indexed_ids'] for r in rows)
        coverage[name] = {'indexedDenominator':len(videos), 'assignedUniqueIds':len(assigned),
            'unassignedUniqueIds':len(videos)-len(assigned), 'groupMemberships':memberships,
            'extraOverlappingMemberships':memberships-len(assigned),
            'unassignedVideoIds':sorted(set(videos)-assigned),
            'meaning':'Available inherited associations; unassigned does not mean no practitioner/entity/civilization'}
    result = {'schemaVersion':1, 'scope':'Inherited YouTube metadata and actual independent-publisher source artifacts; overlapping labels',
        'summary':{'indexedYouTubeIds':len(videos),'selectedYouTubeIds':sum(r['selected_default'] for r in decisions.values()),
            'literalRoutes':len(routes),'publisherGroupsWithIndexedIds':len(accounts),
            'practitionerAssociationsWithIndexedIds':len(practitioners),'entityLabelsWithIndexedIds':len(entities),
            'civilizationLabelsWithIndexedIds':len(civilizations),
            'actualYouTubeVideos':0,'actualYouTubeCaptions':0,'actualYouTubeBytes':0,
            'actualIndependentAudioFiles':len(audio),'actualIndependentAudioBytes':sum(r['bytes'] for r in audio),
            'actualIndependentAudioSeconds':sum(r['duration_seconds'] for r in audio),
            'canonicalSourceArtifacts':len(files),'canonicalSourceBytes':sum(r['bytes'] for r in files),
            'wholeChannelLifetimeCountsKnown':False},
        'youtube':youtube_views, 'attributionCoverage':coverage,
        'sourceStorage':storage, 'localArchive':local,
        'limits':['Group memberships overlap; sums across groups are not global unique totals.',
                  'YouTube route bytes remain zero; independent RSS bytes are never imputed to a YouTube account.',
                  'Claimed entity/civilization labels are inherited publisher associations, not verified speakers or populations.',
                  'Measured upload time can include repeated original sessions and excludes unknown/conflicting durations.',
                  'The managed cloud local archive depends on environment retention, not permanent chat attachments.']}
    assert result['summary']['canonicalSourceBytes']==data['archivePlan']['canonical_bytes']
    for rows in storage.values():
        assert sum(r['canonical_source_bytes'] for r in rows)==result['summary']['canonicalSourceBytes']
    for name,rows in result['youtube'].items():
        csv_rows(output/(name+'.csv'),rows)
    for name,rows in storage.items():
        csv_rows(output/('storage-'+name+'.csv'),rows)
    csv_rows(output/'attribution-coverage.csv',[{'view':name,**row} for name,row in coverage.items()])
    write(output/'distributions.json',result)
    write(output/'source-manifest.json',{'inputs':pins,'builderSha256':digest(Path(__file__)),
        'outputSha256':digest(output/'distributions.json'),'networkRequests':0,'rawSourceTextPublished':False})
    print(json.dumps(result['summary']))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=HERE)
    p.add_argument('--archive-state',type=Path)
    args=p.parse_args()
    build(args.output,args.archive_state.resolve() if args.archive_state else None)
