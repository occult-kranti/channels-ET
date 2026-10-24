#!/usr/bin/env python3
"""Independent storage/group arithmetic and retained-copy byte audit; no author imports."""
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def load(p):
    p=Path(p)
    return [json.loads(x) for x in p.read_text().splitlines() if x] if p.suffix=='.jsonl' else json.loads(p.read_text())
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()
def audit():
    paths={k:ROOT/v for k,v in {'distribution':'research/storage-distributions/distributions.json','plan':'research/storage-drive/archive-plan.json',
        'videos':'research/harvest/inventory/videos.jsonl','routes':'research/harvest/inventory/channel-routes.json',
        'people':'research/harvest/inventory/practitioner-candidates.json','selection':'research/collection-policy/selection.jsonl',
        'audio19':'research/harvest/publisher_sources/publisher-summary.json','audio1':'research/access-repair/athina/publisher_sources/publisher-summary.json',
        'archive':'research/cloud-archive/archive-receipt.json','archiveState':'research/cloud-archive/archive-state.json'}.items()}
    d=load(paths['distribution']);plan=load(paths['plan']);videos={x['video_id']:x for x in load(paths['videos'])};selection={x['video_id']:x for x in load(paths['selection'])}
    people={x['id']:x for x in load(paths['people'])['records']};audio=[x for p in ('audio19','audio1') for x in load(paths[p])['records'] if x['status']=='completed'];by_audio={x['source_id']:x for x in audio}
    checks=0
    def check(ok,label):
        nonlocal checks
        checks+=1;assert ok,label
    def close(a,b):return math.isclose(a,b,abs_tol=1e-7,rel_tol=1e-12)
    summary=d['summary'];check(set(videos)==set(selection),'selection universe')
    check(summary['indexedYouTubeIds']==len(videos),'indexed IDs');check(summary['selectedYouTubeIds']==sum(x['selected_default'] for x in selection.values()),'selected IDs')
    check(summary['actualIndependentAudioFiles']==len(by_audio)==len(audio),'unique recordings')
    check(summary['actualIndependentAudioBytes']==sum(x['bytes'] for x in audio),'audio bytes')
    check(close(summary['actualIndependentAudioSeconds'],sum(x['duration_seconds'] for x in audio)),'unique audio seconds')
    check(all(summary[x]==0 for x in ('actualYouTubeVideos','actualYouTubeCaptions','actualYouTubeBytes')),'no RSS bytes imputed to YouTube')
    mappings={
        'byRoute':lambda r:r['channel_route_ids'],'byPublisherGroup':lambda r:r['publisher_account_ids'],
        'byPractitionerAssociation':lambda r:r['person_ids'],'byEntityLabel':lambda r:r['entity_labels'],
        'byPublisherDeclaredCivilization':lambda r:[v for person in r['person_ids'] if person in people for v in people[person].get('civilizations',[])]}
    overlaps={}
    for view,fn in mappings.items():
        groups=defaultdict(set)
        for vid,row in videos.items():
            for key in set(fn(row)):
                if isinstance(key,str) and key:groups[key].add(vid)
        observed=d['youtube'][view]
        if view=='byRoute':check({r['id'] for r in observed}=={r['route_id'] for r in load(paths['routes'])['records']},'all literal routes including zero')
        else:check({r['id'] for r in observed}==set(groups),'complete group keys:'+view)
        for row in observed:
            ids=groups[row['id']];check(set(row['video_ids'])==ids,'group membership:'+view+row['id'])
            check(row['indexed_ids']==len(ids),'distinct group count')
            chosen=[selection[i] for i in ids];measured=[x for x in chosen if x['duration_state'] in ('eligible_duration','under_minimum')]
            for key,state in [('unknown_duration_ids','unknown'),('conflicting_duration_ids','conflicting'),('under_minimum_ids','under_minimum')]:check(row[key]==sum(x['duration_state']==state for x in chosen),'duration states')
            check(row['eligible_ids']==sum(x['eligible_on_inherited_metadata'] for x in chosen),'eligible count')
            check(row['selected_ids']==sum(x['selected_default'] for x in chosen),'selected group count')
            check(close(row['unconflicted_measured_upload_seconds'],sum(x['duration_seconds'] for x in measured)),'unconflicted duration')
            check(row['measured_upload_ids']==len(measured),'measured duration denominator')
            check(row['youtube_downloaded_bytes']==row['youtube_downloaded_video_files']==row['youtube_downloaded_caption_files']==0,'group YouTube zeros')
        union=set().union(*groups.values()) if groups else set()
        memberships=sum(len(x) for x in groups.values())
        overlaps[view]={'groups':len(observed),'nonempty_groups':sum(bool(x) for x in groups.values()),'sum_memberships':memberships,
                        'unique_ids_covered':len(union),'unassigned_ids':len(videos)-len(union),
                        'membership_disjoint_within_covered_ids':memberships==len(union),
                        'partitions_all_indexed_ids':memberships==len(union)==len(videos)}
    files=plan['files'];check(len(files)==summary['canonicalSourceArtifacts'],'canonical artifacts')
    check(sum(x['bytes'] for x in files)==summary['canonicalSourceBytes']==plan['canonical_bytes'],'canonical bytes')
    for source in files:
        path=Path(source['local_path']);check(path.is_file() and not path.is_symlink() and path.stat().st_size==source['bytes'],'actual source stat')
        check(digest(path)==source['sha256'],'actual source SHA256')
    groups_by_key={'byPublisher':'uploader','byPractitionerContext':'practitioner','byProvider':'provider'}
    for view,field in groups_by_key.items():
        groups=defaultdict(list)
        for row in files:groups[row[field]].append(row)
        observed={r['label']:r for r in d['sourceStorage'][view]};check(set(groups)==set(observed),'storage partition labels')
        for label,members in groups.items():
            row=observed[label];ids={x['source_id'] for x in members};recordings=ids&set(by_audio)
            check(row['canonical_source_artifacts']==len(members),'partition artifact counts')
            check(row['canonical_source_bytes']==sum(x['bytes'] for x in members),'partition byte counts')
            check(set(row['source_ids'])==ids and row['source_recordings']==len(recordings),'source-level duration denominator')
            check(close(row['recorded_audio_seconds'],sum(by_audio[i]['duration_seconds'] for i in recordings)),'unique recording duration not ASR-format sum')
        check(sum(r['canonical_source_bytes'] for r in observed.values())==summary['canonicalSourceBytes'],'partition byte total')
    contexts=d['sourceStorage']['bySourceContext'];feed=[x for x in contexts if 'athina-feed' in x['source_ids']]
    check(len(feed)==1 and feed[0]['source_recordings']==0 and 'not episode speech' in feed[0]['label'] and 'Paul' not in feed[0]['label'],'feed is not Paul or speech')
    check(sorted(x['canonical_source_artifacts'] for x in contexts)==[1,3,4,15,76],'five source-context partition')
    check(sum(x['canonical_source_artifacts'] for x in contexts)==len(files),'source-context file partition')
    check(sum(x['canonical_source_bytes'] for x in contexts)==summary['canonicalSourceBytes'],'source-context byte partition')
    archive=load(paths['archive']);state=load(paths['archiveState']);archive_root=Path(archive['archive_path']);source_by_relative={r['relative_path']:r for r in files}
    check(d['localArchive']==state,'current archive state exact binding');check(archive['status']=='completed' and state['actual_local_archive_completed'] is True,'archive completion')
    archive_files=[p for p in archive_root.rglob('*') if p.is_file()];check(len(archive_files)==len(archive['records'])==state['actual_local_files'],'actual archive count')
    check(sum(p.stat().st_size for p in archive_files)==state['actual_local_bytes']==archive['copied_bytes'],'actual archive bytes')
    for record in archive['records']:
        path=archive_root/record['relative_path'];check(path.resolve().is_relative_to(archive_root.resolve()) and not path.is_symlink(),'archive boundary')
        check(path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],'independent archive hash')
        check(path.stat().st_nlink==1 and path.stat().st_mode&0o077==0,'private independent copy')
        if record['origin']=='source_artifact':
            original=source_by_relative[record['relative_path']];check(record['bytes']==original['bytes'] and record['sha256']==original['sha256'],'archive/source join')
            a=path.stat();b=Path(original['local_path']).stat();check((a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino),'independent copy inode')
    check(state['actual_drive_uploaded_files']==state['actual_drive_upload_attempts']==0,'not a Drive upload')
    return {'schema_version':1,'status':'pass','method':'Independent direct input joins, physical file stats/SHA256, unique source durations and archive-copy verification; no builder import',
            'checks':checks,'pins':{str(v.relative_to(ROOT)):digest(v) for v in paths.values()},'summary':summary,'membership_diagnostics':overlaps,
            'canonical_source_files_hashed':len(files),'actual_archive_files_hashed':len(archive_files),'actual_archive_bytes':state['actual_local_bytes'],
            'athina_feed_context_regression':'pass: independent catalog metadata, no voice duration, not Paul',
            'raw_text_published':False,'network_requests':0}

if __name__=='__main__':
    result=audit();(HERE/'storage-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
