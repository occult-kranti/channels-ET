#!/usr/bin/env python3
"""Validate the public contextual-token projection and its finite denominators."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def require(value,message):
    if not value:raise ValueError(message)


def verify(root):
    root=Path(root);raw=(root/'contextual-terms.json').read_bytes();r=json.loads(raw)
    baseline_raw=(root/'analysis.json').read_bytes();baseline=json.loads(baseline_raw)
    require(r['status']=='executed_contextual_token_exploration','Unexecuted token study')
    require(r['bindings']['baseline_analysis_sha256']==hashlib.sha256(baseline_raw).hexdigest(),'Wrong baseline binding')
    require(b'/workspace/' not in raw and b'channels-et-private' not in raw,'Private path leaked')
    ids={d['source_id']:d for d in baseline['documents']};terms=r['terms'];names=[t['term'] for t in terms]
    require(len(terms)==len(set(names))==24 and len(ids)==25,'Wrong frame denominator')
    pairs=r['source_contexts'];keys=[(p['term'],p['source_id']) for p in pairs]
    require(len(keys)==len(set(keys)),'Duplicate source-term pair')
    for row in pairs:
        require(row['source_id'] in ids and row['term'] in names,'Unknown source/term')
        require(row['medium_id']==ids[row['source_id']]['medium_id'],'Medium join differs')
        require(row['sampled_occurrences']==min(2,row['occurrences_available']) and row['sampled_occurrences']>0,'Sampling coverage differs')
        require(all(math.isfinite(row[k]) for k in ('x','y','cosine_to_term_centroid')),'Nonfinite source coordinates')
        require(-1.00000001<=row['cosine_to_term_centroid']<=1.00000001,'Invalid centroid cosine')
    for row in terms:
        require(row['document_frequency']==sum(p['term']==row['term'] for p in pairs)>=3,'Document frequency differs')
        require(row['mean_tfidf']>0 and all(math.isfinite(row[k]) for k in ('x','y','mean_tfidf')),'Invalid selected term')
    require(names==[t['term'] for t in sorted(terms,key=lambda t:(-t['mean_tfidf'],t['term']))],'Selection order differs')
    c=r['coverage'];require(c['source_editions']==25 and c['terms']==24 and c['source_term_pairs']==len(pairs),'Coverage denominator differs')
    require(c['sampled_occurrences']==sum(p['sampled_occurrences'] for p in pairs),'Sample count differs')
    require(c['available_occurrences']==sum(p['occurrences_available'] for p in pairs),'Occurrence count differs')
    require(abs(sum(t['x'] for t in terms))<1e-8 and abs(sum(t['y'] for t in terms))<1e-8,'Term coordinates not centered')
    require(abs(sum(t['x']**2+t['y']**2 for t in terms)/24-1)<1e-8,'Term RMS radius differs')
    matrix=r['term_cosine_matrix'];require(len(matrix)==24 and all(len(x)==24 for x in matrix),'Matrix shape differs')
    for i in range(24):
        require(abs(matrix[i][i]-1)<1e-8,'Cosine diagonal differs')
        for j in range(24):require(math.isfinite(matrix[i][j]) and -1.00000001<=matrix[i][j]<=1.00000001 and abs(matrix[i][j]-matrix[j][i])<1e-8,'Invalid matrix cell')
    for run in r['clusters']['runs']:
        require([a['term'] for a in run['assignments']]==names,'Cluster order differs')
        labels=[a['cluster'] for a in run['assignments']];require(set(labels)=={1,2,3},'Wrong fixed cluster count')
        silhouettes=[]
        for i,label in enumerate(labels):
            same=[j for j in range(24) if j!=i and labels[j]==label]
            if not same:silhouettes.append(0);continue
            a=sum(max(0,1-matrix[i][j]) for j in same)/len(same)
            alternatives=[sum(max(0,1-matrix[i][j]) for j in range(24) if labels[j]==other)/labels.count(other) for other in {1,2,3}-{label}]
            b=min(alternatives);silhouettes.append((b-a)/max(a,b) if max(a,b)>0 else 0)
        require(abs(sum(silhouettes)/24-run['cosine_silhouette'])<1e-8,'Silhouette differs')
    require(r['projection']['overlay_terms']==names[:4],'Fixed overlay selection differs')
    require(len(r['figures'])==3,'Expected one three-format figure family')
    for ref in r['figures']:
        name=Path(ref['file']);require(len(name.parts)==1 and not name.is_absolute(),'Unsafe figure name')
        path=root/name
        if not path.exists():path=root/'figures'/name
        body=path.read_bytes();require(len(body)==ref['bytes'] and hashlib.sha256(body).hexdigest()==ref['sha256'],'Figure hash differs')
    return {'status':'passed','terms':24,'source_term_pairs':len(pairs),'sampled_occurrences':c['sampled_occurrences'],
            'sha256':hashlib.sha256(raw).hexdigest(),'scope':'Public identity/count/matrix/cluster arithmetic and hashes; neural extraction and source span audits are separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-dir',type=Path,required=True)
    print(json.dumps(verify(p.parse_args().public_dir)))
