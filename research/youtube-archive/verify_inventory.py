#!/usr/bin/env python3
"""Standard-library validation of the public, source-bound inventory contract."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys


def verify(root):
    root=Path(root);path=root/'inventory.json';data=json.loads(path.read_text())
    assert data['schema_version']=='youtube-archive-inventory/1'
    accounts=data['accounts'];videos=data['videos'];am={x['account_id']:x for x in accounts};vm={x['video_id']:x for x in videos};inputs={x['input_id']:x for x in data['inputs']}
    assert len(am)==len(accounts) and len(vm)==len(videos)
    assert all(re.fullmatch('[A-Za-z0-9_-]{11}',v) for v in vm)
    assert data['policy']['count_cap'] is None and data['policy']['minimum_duration_seconds']==0 and data['policy']['bashar_minimum_duration_seconds']==300 and data['policy']['jamie_butler_excluded']
    observed=collections.defaultdict(set);uploaded=collections.defaultdict(set);associations=collections.defaultdict(set);uploaders=collections.defaultdict(set)
    for edge in data['account_video_links']:
        a,v=edge['account_id'],edge['video_id'];assert a in am and v in vm
        observed[a].add(v);associations[v].add(a)
        assert edge['attribution'] in {'historical_watch_uploader','inherited_route_association','publisher_embed','screening_route_association','research_route_association'}
        if edge['attribution']=='historical_watch_uploader':uploaded[a].add(v);uploaders[v].add(a)
    for a in accounts:
        aid=a['account_id'];assert a['uploaded_total'] is None
        assert a['channel_id'] is None or re.fullmatch('UC[A-Za-z0-9_-]{22}',a['channel_id'])
        assert set(a['observed_video_ids'])==observed[aid]
        assert a['counts']['observed_associated_video_ids']==len(observed[aid])
        assert a['counts']['historically_verified_uploader_video_ids']==len(uploaded[aid])
        assert a['counts']['policy_eligible_associated_video_ids']==sum(vm[v]['policy_decision']['status']=='eligible' for v in observed[aid])
        assert a['duration_policy']['count_cap'] is None and a['duration_policy']['bashar_item_minimum_seconds']==300
        assert set(a['tabs'])=={'videos','shorts','streams'}
        for t in a['tabs'].values(): assert t=={'enumeration_status':'not_enumerated','continuation_exhausted':False,'reported_total':None}
        if any(h.lower()=='@jamiebutlermedium' for h in a['handles']):assert a['inclusion_status']=='excluded'
    for v in videos:
        vid=v['video_id'];assert set(v['associated_account_ids'])==associations[vid]
        expected=next(iter(uploaders[vid])) if len(uploaders[vid])==1 else None
        assert v['verified_uploader_account_id']==expected
        assert v['current_access_status']=='not_attempted_by_inventory'
        assert v['policy_decision']['count_cap'] is None
        assert v['policy_decision']['minimum_seconds']==(300 if v['policy_decision']['bashar_attribution'] else 0)
    def walk(value):
        if isinstance(value,dict):
            if 'input_id' in value and 'locator' in value:assert value['input_id'] in inputs
            for k,x in value.items():
                assert k not in {'audio_path','local_path','workspace_path','transcript_text','full_text'}
                walk(x)
        elif isinstance(value,list):
            for x in value:walk(x)
        elif isinstance(value,str):assert '/workspace/' not in value and '/dev/shm/' not in value
    walk(data)
    cov=data['coverage'];assert cov['accounts']==len(accounts) and cov['unique_observed_video_ids']==len(videos)
    assert cov['historically_verified_uploader_video_ids']==sum(v['verified_uploader_account_id'] is not None for v in videos)
    assert cov['accounts_by_inclusion']==dict(collections.Counter(a['inclusion_status'] for a in accounts))
    assert cov['videos_by_policy']==dict(collections.Counter(v['policy_decision']['status'] for v in videos))
    assert cov['observed_lifetime_upload_total'] is None and cov['new_downloads_by_inventory']==0
    return {'accounts':len(accounts),'videos':len(videos),'historical_verified_uploader_videos':cov['historically_verified_uploader_video_ids'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':print(json.dumps(verify(sys.argv[1])))
