#!/usr/bin/env python3
"""Offline source/selection reconciliation for the current dashboard supplement."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'dist/research'
read=lambda p:json.loads(p.read_text())
data=read(OUT/'data.json');sources=data['harvest']['currentSupplement']['sources']
manifest=read(HERE/'input-manifest.json');checks=[]
def check(ok,label):
    assert ok,label
    checks.append(label)
for item in manifest['inputs']:
    raw=(ROOT/item['source']).read_bytes()
    check(hashlib.sha256(raw).hexdigest()==item['sha256'],'Reviewed input hash: '+item['source'])
    check(raw==(OUT/item['target']).read_bytes(),'Public metadata byte equality: '+item['target'])
    if item.get('key'):check(sources[item['key']]==json.loads(raw),'Interactive metadata binding: '+item['key'])
p=sources['policy'];g=p['all_upload_ids'];default=p['default'];alt=p['conservative_all_materials_alternative']
check(sum(g[k]for k in ['eligible','under_minimum','unknown_duration','conflicting_duration'])==g['indexed'],'Disjoint screening outcomes reconcile indexed denominator')
check(p['explicit_bashar_association']['eligible']+p['other_not_bashar_labeled']['eligible']==g['eligible'],'Eligible source-label split reconciles')
check(default['new_bashar_selected']+default['other_selected']==default['total_new_youtube_ids_selected'],'Default selection reconciles')
check(default['podcasts_consume_youtube_cap']is False,'Independent podcasts do not consume default video cap')
check(default['new_bashar_selected']+default['eligible_bashar_held_by_cap']==p['explicit_bashar_association']['eligible'],'Bashar selected and cap-held reconcile eligible pool')
check(alt['new_bashar_selected']+alt['reserved_existing_bashar_podcast_materials']==100,'Optional all-material cap is separate and reconciled')
inventory={json.loads(x)['video_id']for x in (ROOT/'research/harvest/inventory/videos.jsonl').read_text().splitlines()}
for name,total,flag in [('selected-default.jsonl',default['total_new_youtube_ids_selected'],'selected_default'),('selected-conservative-all-materials.jsonl',alt['total_new_youtube_ids_selected'],'selected_conservative_all_materials')]:
    rows=[json.loads(x)for x in (ROOT/'research/collection-policy'/name).read_text().splitlines()]
    check(len(rows)==len({r['video_id']for r in rows})==total,'Unique selected ID count: '+name)
    check(all(r['video_id']in inventory for r in rows),'Selected IDs join authoritative inventory: '+name)
    check(all(r[flag]and r['eligible_on_inherited_metadata']and r['duration_seconds']>=300 and not r['shorts_evidence']for r in rows),'Selected rows pass inherited duration/Shorts gates: '+name)
check(p['whole_channel_lifetime_bashar_upload_count']is None and p['whole_channel_lifetime_all_practitioner_upload_count']is None,'Whole-channel lifetime counts remain unknown')
check(p['bashar_ids_with_any_route']+p['bashar_ids_without_route']==p['explicit_bashar_association']['indexed'],'Bashar routed/unrouted unique IDs reconcile')
check(data['harvest']['run']['attempts_total']==0 and data['harvest']['saved']['records']==[],'Historical YouTube worker attempts/artifacts remain zero')
b=sources['braveWatch'];check(b['ordinaryWatchNavigations']==b['targetConnectRequestsObserved']==1 and b['proxyConnectStatus']==403 and b['responses']==[],'Brave source diagnostic remains one target CONNECT403 without origin response')
d=sources['drive'];check(d['apps_connection_choice_received']and not d['oauth_completion_observed']and not d['authorized_drive_identity_observed'],'Apps choice does not establish Drive authentication')
check(all(d[k]==0 for k in ['callable_drive_tool_count','configured_rclone_remotes','actual_drive_folder_count','actual_drive_upload_attempts','actual_drive_uploaded_files']),'Drive tool/remote/folder/upload states remain zero')
check(not d['actual_quota_checked']and d['actual_quota']is None,'Reported storage allowance is not a quota observation')
check(d.get('output_safety_guard_verified')is True,'Refreshed storage workflow includes reviewed output-collision guard')
runner=sources['runnerSummary'];dry=sources['runnerDryRun'];blocked=sources['runnerBlocked']
check(runner['jobs']==sum(runner['by_kind'].values())and runner['items']==g['indexed'],'Runner job kinds and indexed item denominator reconcile')
check(runner['by_kind']['video']==runner['by_kind']['captions']==default['total_new_youtube_ids_selected'],'Runner paired media jobs join exact default selected-ID denominator')
check(runner['policy']['policy_sha256']==hashlib.sha256((ROOT/'research/collection-policy/policy.json').read_bytes()).hexdigest()and runner['policy']['selection_sha256']==hashlib.sha256((ROOT/'research/collection-policy/selection.jsonl').read_bytes()).hexdigest(),'Runner binds exact reviewed policy and source decisions')
check(dry['plan']==runner and dry['gate']['ready']is False,'Dry-run source plan matches current runner and gate is blocked')
check(blocked['status']=='blocked_before_claim_or_network'and blocked['gate']==dry['gate'],'Bounded controller blocks before claims under the same runtime fingerprint')
check(runner['attempts']==runner['bashar_unique_youtube_slots_used']==runner['verified_quarantine_artifacts']==dry['network_collection_requests']==blocked['network_collection_requests']==0,'Runner attempts, slots, artifacts and collection requests remain zero')
audio=data['harvest']['publisherAudio']['records']+data['harvest']['accessRepair']['athinaPublisher']['records'];asr=data['harvest']['asr']['records']+[data['harvest']['accessRepair']['athinaAsr']]
check(len(audio)==len({r['sha256']for r in audio})==20,'Independent20audio files remain distinct source branch')
check(all(any(a['source_id']==t['sourceId']and a['sha256']==t['sourceAudioSha256']for a in audio)for t in asr),'All20ASR receipts join exact original publisher sourceID/audioSHA')
frozen={'baseline':'3d34ecf47e837d0c4714d9413eb52ea36428510d626f5d0c8d23da1cc300f3be','analysis':'a19af07f091df62f0c9a8e6e5b222d97b0363d1687ab678bde90981dd86a69b8','models':'76fc6171f0451062e8cc66ce3c25ceecbe50574e04b389beeee21e7075383485','predictions':'58ca9b91ecdef18ecb27b7ae6d36207a17b3929d4d70c7b1fd7979f6eb3e97bc'}
for key,expected in frozen.items():check(hashlib.sha256(json.dumps(data[key],sort_keys=True).encode()).hexdigest()==expected,'Frozen scientific payload unchanged: '+key)
for name,expected in [('paper.pdf','590460ca284cd1a3de98eefff71a5dbb2bbdf76296f8b2a868fba3a9d7e00cda'),('source.zip','497f8a05bc3fde86cff3c2d86a630711fbdc9068062c49cbbfab14ad12b12326')]:check(hashlib.sha256((OUT/name).read_bytes()).hexdigest()==expected,'Frozen manuscript bytes unchanged: '+name)
receipt={'status':'PASS','scope':'Offline metadata and scientific-freeze reconciliation; no source collection or storage authorization','checks':checks,'sourceInputs':len(manifest['inputs'])}
(HERE/'source-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks)}))
