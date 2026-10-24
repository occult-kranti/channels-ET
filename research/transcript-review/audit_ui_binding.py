#!/usr/bin/env python3
"""Check actual exported dashboard bytes and nested data against source-owner files."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(directory):
    directory=Path(directory);data=json.loads((directory/'data.json').read_text());inputs=json.loads((ROOT/'research/transcript-dashboard/inputs.json').read_text());checks=0
    artifacts={x['path']:x for x in data['artifacts']}
    for row in inputs['inputs']:
        source=ROOT/row['source'];target=directory/row['target'];value=source.read_bytes()
        assert hashlib.sha256(value).hexdigest()==row['sha256']==artifacts[row['target']]['sha256'],row['source'];checks+=1
        assert target.read_bytes()==value and artifacts[row['target']]['bytes']==len(value),row['target'];checks+=1
        if row.get('key'):
            item=data
            for key in row['key'].split('.'):item=item[key]
            assert item==json.loads(value),row['key'];checks+=1
    assert len(artifacts)==len(inputs['inputs']);checks+=1
    a=data['analysis'];reading=data['reading']['summary'];storage=data['distributions'];archive=data['archive']['state']
    assert a['summary']['audioDocuments']==20 and a['summary']['authoredDocuments']==16;checks+=1
    assert sorted(x['documents'] for x in a['clusters']['clusterSizes'])==[1,19];checks+=1
    assert reading['qaCandidateRecords']==37 and reading['qaCandidateKinds']['authored_comparison_prompt']==16;checks+=1
    assert reading['uniqueAsrWordsRead']==11992 and reading['uniquePublisherTextWordsRead']==6319;checks+=1
    commercial={x['cohort']:x for x in a['sensitivities'] if x['name']=='commercial_vocabulary_excluded'}
    assert set(commercial)=={'audio_asr','publisher_text'} and commercial['audio_asr']['nearestNeighborPreservedFraction']==.9 and commercial['publisher_text']['nearestNeighborPreservedFraction']==1.;checks+=1
    assert storage['summary']['actualYouTubeBytes']==storage['summary']['actualYouTubeVideos']==0;checks+=1
    assert storage['summary']['canonicalSourceArtifacts']==99 and archive['actual_local_files']==200;checks+=1
    return {'schema_version':1,'status':'pass','checks':checks,'export_directory':str(directory),'release_status':data['releaseStatus'],
            'data_sha256':sha(directory/'data.json'),'inputs_sha256':sha(ROOT/'research/transcript-dashboard/inputs.json'),
            'artifact_bindings':len(artifacts),'scope':'Independent direct source/public-byte/nested-data equality; interactive rendered review is separately owned',
            'network_requests':0,'raw_text_published':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);args=p.parse_args();r=audit(args.directory)
    (HERE/'ui-binding-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
