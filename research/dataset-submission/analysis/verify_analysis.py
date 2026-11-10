#!/usr/bin/env python3
"""Check analysis joins, denominators and numerical witnesses without rerunning fits."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import numpy as np
from scipy import sparse
from sklearn.metrics import adjusted_rand_score, silhouette_score


def main(args):
    f=json.loads(args.frame.read_text());records=f['records'];public=json.loads((args.public/'analysis.json').read_text())
    results=json.loads((args.public/'results.json').read_text());ids=[r['source_id'] for r in records]
    source={r['source_id']:r for r in records};by={r['source_id']:r for r in public['documents']}
    witness=np.load(args.private/'numerical-witness.npz',allow_pickle=False);X=sparse.load_npz(args.private/'tfidf.npz')
    checks=[]
    def check(name,value):
        if not value:raise AssertionError(name)
        checks.append(name)
    check('exact_frame_sha256',public['frame_sha256']==results['frame_sha256']==hashlib.sha256(args.frame.read_bytes()).hexdigest())
    check('ordered_source_identity',ids==witness['source_ids'].tolist()==[r['source_id'] for r in public['documents']])
    check('document_word_denominators',public['summary']['documents']==len(ids) and public['summary']['words']==sum(r['words'] for r in records))
    check('body_hash_and_source_profile_join',all(by[k]['body_sha256']==source[k]['body_sha256'] and by[k]['words']==source[k]['words'] and by[k]['channel_id']==source[k]['channel_id'] for k in ids))
    count=Counter(r['channel_id'] for r in records)
    check('each_context_exact_partition',all(p['documents']==count[p['channel_id']] and set(p['source_ids'])=={r['source_id'] for r in records if r['channel_id']==p['channel_id']} for p in public['channel_profiles']))
    check('origin_partition',dict(Counter(r['text_origin'] for r in records))==public['summary']['text_origins'])
    check('source_context_account_units',len(count)==public['summary']['publisher_contexts'] and all(p['uploaded_total'] is None for p in public['channel_profiles']))
    check('nonempty_unit_lexical_rows',X.shape[0]==len(ids) and np.allclose(np.asarray(X.multiply(X).sum(axis=1)).ravel(),1,atol=1e-12))
    L=witness['lexical_cosine'];independent=(X@X.T).toarray()
    check('all_lexical_dot_products',np.allclose(np.clip(independent,-1,1),L,atol=1e-12))
    check('finite_symmetric_cosine',np.isfinite(L).all() and np.allclose(L,L.T,atol=1e-12) and np.allclose(np.diag(L),1))
    check('projection_source_binding',np.allclose(witness['coordinates'],[[by[i]['x'],by[i]['y']] for i in ids]))
    W=witness['topic_weights_11'];H=witness['topic_components_11'];M=W/W.sum(axis=1)[:,None]
    check('topic_components_nonnegative_and_unit',np.all(H>=0) and np.allclose(np.linalg.norm(H,axis=1),1,atol=1e-12))
    check('topic_document_normalization',np.allclose(M,[by[i]['topic_mixture'] for i in ids],atol=1e-12))
    groups=[r['channel_id'] for r in records]
    for p in public['channel_profiles']:
        ix=[i for i,g in enumerate(groups) if g==p['channel_id']]
        check('topic_context_mean:'+p['channel_id'],np.allclose(M[ix].mean(axis=0),[t['weight'] for t in p['topics']],atol=1e-12))
    for a,ga in enumerate(public['channel_similarity']['order']):
        for b,gb in enumerate(public['channel_similarity']['order']):
            pairs=[(i,j) for i,g in enumerate(groups) if g==ga for j,h in enumerate(groups) if h==gb and i!=j and (ga!=gb or i<j)]
            value=public['channel_similarity']['values'][a][b]
            if len(pairs)!=public['channel_similarity']['pair_counts'][a][b]:raise AssertionError('Context pair count')
            if not pairs:
                if value is not None:raise AssertionError('Missing pair average must remain null')
            elif abs(np.mean([L[i,j] for i,j in pairs])-value)>1e-12:raise AssertionError('Context pair mean')
    checks.append('all_context_pair_means_denominators_and_singleton_nulls')
    nearest={ids[i]:sorted((j for j in range(len(ids)) if j!=i),key=lambda j:(-L[i,j],ids[j]))[:5] for i in range(len(ids))}
    expected={(ids[i],ids[j]) for i in range(len(ids)) for j in nearest[ids[i]] if i<j and i in nearest[ids[j]]}
    actual={(e['source'],e['target']) for e in public['graph']['edges']}
    check('all_mutual5_edges',actual==expected and len(actual)==len(public['graph']['edges']))
    check('graph_node_identity',set(ids)=={r['source_id'] for r in public['graph']['nodes']})
    label=witness['k8_seed11'];check('main_cluster_assignments',all(by[i]['cluster_id']==int(label[j])+1 for j,i in enumerate(ids)))
    for r in public['sensitivity']['cluster_trials']:
        labels=witness[f"k{r['k']}_seed{r['seed']}"]
        if abs(adjusted_rand_score(groups,labels)-r['publisher_context_ari'])>1e-12:raise AssertionError('Cluster ARI differs')
        if abs(silhouette_score(witness['cluster_features'],labels,metric='cosine')-r['cosine_silhouette_svd50'])>1e-12:raise AssertionError('Cluster silhouette differs')
    checks.append('all_cluster_diagnostics_recomputed_from_features')
    if 'bounded_semantic_vectors' in witness:
        check('semantic_unit_vectors_and_cosine',np.allclose(np.linalg.norm(witness['bounded_semantic_vectors'],axis=1),1,atol=1e-10) and np.allclose(np.clip(witness['bounded_semantic_vectors']@witness['bounded_semantic_vectors'].T,-1,1),witness['bounded_semantic_cosine'],atol=1e-10))
    docs={}
    for r in records:
        raw=Path(r['text_artifact']['path']).read_bytes()
        check('text_artifact_hash:'+r['source_id'],hashlib.sha256(raw).hexdigest()==r['text_artifact']['sha256'])
        text=json.loads(raw)['text'] if r['body_transform'].startswith('json_text') else raw.decode()
        if r['body_transform'].endswith('_html_clean'):
            import html;text=html.unescape(re.sub(r'<[^>]*>','',text))
        import unicodedata;text=unicodedata.normalize('NFKC',text).strip();docs[r['source_id']]=text
        if hashlib.sha256(text.encode()).hexdigest()!=r['body_sha256']:raise AssertionError('Body transform hash differs')
    qs=json.loads((args.private/'question-cues-private.json').read_text())['records'];qcount=Counter()
    for q in qs:
        t=docs[q['source_id']];qcount[q['source_id']]+=1
        if t[q['char_start']:q['char_end']]!=q['question_cue'] or t[q['char_end']:q['char_end']+1000]!=q['following_context']:
            raise AssertionError('Question-cue provenance mismatch')
        if q['body_sha256']!=source[q['source_id']]['body_sha256']:raise AssertionError('Question-cue edition mismatch')
    check('all_question_cue_offsets_and_denominators',len(qs)==public['summary']['punctuation_question_cues'] and all(by[i]['question_cues']==qcount[i] for i in ids))
    forbidden={'text','full_text','question_cue','following_context','body','text_artifact','media_artifact'}
    def safe(value):
        if isinstance(value,dict):return not (forbidden & set(value)) and all(safe(v) for v in value.values())
        if isinstance(value,list):return all(safe(v) for v in value)
        if isinstance(value,str):return not any(p in value for p in ('/workspace/','/dev/shm/','/tmp/'))
        return True
    check('public_allowlist_no_private_bodies_or_paths',all(safe(json.loads(p.read_text())) for p in args.public.glob('*.json')))
    for f in public['figures']:
        check('figure_exists:'+f['file'],all((args.public/f[k]).stat().st_size>1000 for k in ('file','pdf','png')))
    report={'status':'passed','check_count':len(checks),'checks':checks,'scope':'Source transforms, hashes, joins, aggregation, matrix dot products, topics, complete graph, all cluster scores, semantic norms and punctuation-cue offsets; independent model refit is separately reviewed.'}
    (args.private/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.public/'verification.json').write_text(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frame',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--public',type=Path,required=True)
    main(p.parse_args())
