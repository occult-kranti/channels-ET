#!/usr/bin/env python3
"""Incrementally bind final coverage fields while preserving prior raw-byte audit."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def audit():
    prior=load(HERE/'storage-audit.json');current_path=ROOT/'research/storage-distributions/distributions.json';current=load(current_path)
    checked=0
    for path,expected in prior['pins'].items():
        if path=='research/storage-distributions/distributions.json':continue
        assert sha(ROOT/path)==expected,'Previously byte-audited source input changed; rerun full audit'
        checked+=1
    assert current['summary']==prior['summary'],'Source totals changed, not only coverage metadata'
    videos={r['video_id']:r for r in (json.loads(x) for x in (ROOT/'research/harvest/inventory/videos.jsonl').read_text().splitlines() if x)}
    rows=[]
    for view,groups in current['youtube'].items():
        covered=set().union(*(set(r['video_ids']) for r in groups));memberships=sum(len(set(r['video_ids'])) for r in groups)
        record=current['attributionCoverage'][view]
        expected={'indexedDenominator':len(videos),'assignedUniqueIds':len(covered),'unassignedUniqueIds':len(videos)-len(covered),
                  'groupMemberships':memberships,'extraOverlappingMemberships':memberships-len(covered),'unassignedVideoIds':sorted(set(videos)-covered)}
        for key,value in expected.items():assert record[key]==value,(view,key);checked+=1
        rows.append({'view':view,**{k:v for k,v in expected.items() if k!='unassignedVideoIds'}})
    return {'schema_version':1,'status':'pass','checks':checked,'final_distribution_sha256':sha(current_path),
            'reused_full_raw_audit_path':'research/transcript-review/storage-audit.json','reused_full_raw_audit_sha256':sha(HERE/'storage-audit.json'),
            'reuse_reason':'All nine non-output input hashes and source totals are unchanged; prior99source+200archive byte hashes are preserved, not claimed freshly repeated',
            'coverage':rows,'network_requests':0,'raw_text_published':False}
if __name__=='__main__':
    r=audit();(HERE/'storage-binding-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
