#!/usr/bin/env python3
"""Stdlib accounting and numerical consistency check for the knowledge comparison."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path


def close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-7)
def require(condition,message):
    if not condition:raise ValueError(message)


def verify(directory):
    directory=Path(directory);raw=(directory/'analysis.json').read_bytes();r=json.loads(raw)
    require(b'/workspace/' not in raw and b'channels-et-private' not in raw,'Private path in public analysis')
    docs=r['documents'];ids=[d['source_id'] for d in docs];n=len(ids);positions={s:i for i,s in enumerate(ids)}
    require(n==25 and len(positions)==n,'Fixed25source frame required')
    require(sum(d['words'] for d in docs)==r['totals']['words']==47280,'Word count differs')
    require(r['totals']['selected_documents']==n,'Document total differs')
    require(len({d['medium_id'] for d in docs})==r['totals']['mediums']==6,'Medium count differs')
    require(r['totals']['new_source_downloads']==0 and r['totals']['new_model_training'] is False,'Reuse or training misrepresented')
    matrices={}
    for kind,keys in [('lexical',['matrix','window_300_matrix','unmasked_matrix']),
            ('semantic',['matrix','window_300_matrix','unmasked_matrix','equal_chunk_matrix'])]:
        require(r[kind]['source_ids']==ids,'Matrix order differs')
        for key in keys:
            matrix=r[kind][key];require(len(matrix)==n and all(len(row)==n for row in matrix),'Matrix shape differs')
            for i,row in enumerate(matrix):
                for j,value in enumerate(row):
                    require(isinstance(value,(int,float)) and math.isfinite(value) and -1.00000001<=value<=1.00000001,'Invalid cosine')
                    require(close(value,matrix[j][i]),'Matrix not symmetric')
                require(close(row[i],1),'Matrix diagonal differs')
            matrices[kind+'/'+key]=matrix
    pairs=r['pairs'];require(len(pairs)==n*(n-1)//2,'Pair count differs');seen=set()
    binding={'lexical_cosine':'lexical/matrix','semantic_cosine':'semantic/matrix',
        'window_lexical_cosine':'lexical/window_300_matrix','window_semantic_cosine':'semantic/window_300_matrix',
        'equal_chunk_cosine':'semantic/equal_chunk_matrix','unmasked_lexical_cosine':'lexical/unmasked_matrix',
        'unmasked_semantic_cosine':'semantic/unmasked_matrix'}
    for p in pairs:
        i,j=positions[p['source']],positions[p['target']];require(i<j and (i,j) not in seen,'Duplicate/unordered pair');seen.add((i,j))
        require(p['same_medium']==(docs[i]['medium_id']==docs[j]['medium_id']),'Medium pair label changed')
        require(p['same_label']==(docs[i]['comparison_label']==docs[j]['comparison_label']),'Comparison label changed')
        for key,matrix in binding.items():require(close(p[key],matrices[matrix][i][j]),'Pair value differs')
    for summary in r['pair_summary']:
        pp=[p for p in pairs if p['kind']==summary['kind']];require(len(pp)==summary['pairs'],'Pair stratum count differs')
        for key in ('lexical_cosine','semantic_cosine','window_lexical_cosine','window_semantic_cosine'):
            require(close(summary[key],sum(p[key] for p in pp)/len(pp)),'Pair mean differs')
    require(sum(s['pairs'] for s in r['pair_summary'])==len(pairs),'Pair strata incomplete')
    k=r['neighbors']['k'];require(k==5,'Unexpected neighbor contract')
    neighbor_matrices={'lexical_ids':'lexical/matrix','semantic_ids':'semantic/matrix',
        'window_ids':'semantic/window_300_matrix','lexical_window_ids':'lexical/window_300_matrix',
        'unmasked_lexical_ids':'lexical/unmasked_matrix','unmasked_semantic_ids':'semantic/unmasked_matrix'}
    jaccards={'jaccard':('lexical_ids','semantic_ids'),'window_jaccard':('semantic_ids','window_ids'),
        'lexical_window_jaccard':('lexical_ids','lexical_window_ids'),
        'name_mask_lexical_jaccard':('lexical_ids','unmasked_lexical_ids'),
        'name_mask_semantic_jaccard':('semantic_ids','unmasked_semantic_ids')}
    require([x['source_id'] for x in r['neighbors']['rows']]==ids,'Neighbor identities/order differ')
    for row in r['neighbors']['rows']:
        i=positions[row['source_id']]
        for key,mkey in neighbor_matrices.items():
            m=matrices[mkey];expected=[ids[j] for j in sorted((j for j in range(n) if j!=i),key=lambda j:(-m[i][j],ids[j]))[:k]]
            require(row[key]==expected,'Nearest neighbors differ')
        for metric,(left,right) in jaccards.items():
            a,b=set(row[left]),set(row[right]);require(close(row[metric],len(a&b)/len(a|b)),'Neighbor Jaccard differs')
    for row in r['semantic']['coverage']+r['semantic']['window_coverage']:
        require(row['processed_content_wordpieces']==row['content_wordpieces'] and row['truncated_content_wordpieces']==0,'Incomplete embedding coverage')
    require(r['semantic']['model']['training_or_weight_update'] is False,'Unexecuted training claim')
    for key in ('lexical','semantic','semantic_aligned'):
        rows=r['projections'][key];require([x['source_id'] for x in rows]==ids,'Projection identities differ')
        require(all(math.isfinite(x[a]) for x in rows for a in ('x','y')),'Invalid projection coordinate')
    for representation in r['clusters'].values():
        for run in representation['runs']:
            require([x['source_id'] for x in run['assignments']]==ids,'Cluster source identities differ')
            require(all(1<=x['cluster']<=representation['k'] for x in run['assignments']),'Cluster ID out of range')
            require(-1<=run['cosine_silhouette']<=1,'Invalid silhouette')
    synthetic=r['synthetic_controls'];require(synthetic['synthetic_fixture'] and synthetic['included_in_corpus_counts'] is False,'Synthetic controls not separated')
    require(len(synthetic['statements'])==5 and len(synthetic['pairs'])==4,'Synthetic control scope changed')
    require(len(r['figures'])==15,'Expected five figure families in three formats')
    for fig in r['figures']:
        name=Path(fig['file']);require(not name.is_absolute() and len(name.parts)==1,'Unsafe figure path')
        path=directory/name
        if not path.exists():path=directory/'figures'/name
        body=path.read_bytes();require(len(body)==fig['bytes'] and hashlib.sha256(body).hexdigest()==fig['sha256'],'Figure artifact differs')
    return {'status':'passed','documents':n,'words':r['totals']['words'],'pairs':len(pairs),'figures':len(r['figures']),
        'analysis_sha256':hashlib.sha256(raw).hexdigest(),'scope':'Public accounting, matrix/neighbor arithmetic and artifact integrity; independent source reading/refits are separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-dir',type=Path,required=True)
    args=p.parse_args();print(json.dumps(verify(args.public_dir)))
