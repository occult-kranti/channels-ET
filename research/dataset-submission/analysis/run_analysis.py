#!/usr/bin/env python3
"""Reproducible descriptive analyses of a reconciled, private source frame.

Public exports contain derived measures and source identifiers, never body text.
All statistical exploration is conditional on this finite convenience corpus.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import resource
import sys
import time
import warnings

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np
from scipy import sparse
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/channel-lab'))
from analyze_corpus import (STOP, ORIGIN_STRATA, load_inputs, masked, bounded, words,
                           sensitivity, enrichment, group_matrix, coordinates,
                           graph_summary, canonicalize_factors, mixture)
from analyze_encoder import LabEncoder


def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    def scalar(x):
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False,default=scalar) + '\n')
def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def top_terms(v, terms, n=12):
    if sparse.issparse(v):
        v=v.tocsr(); candidates=zip(v.indices,v.data)
    else: candidates=enumerate(np.asarray(v).ravel())
    return [{'term':str(terms[i]),'score':float(x)} for i,x in sorted(candidates,key=lambda x:(-x[1],terms[x[0]]))[:n] if x>0]
def fit_nmf(X, seed, n=8):
    model=NMF(n_components=n, init='random', random_state=seed, max_iter=2000, tol=1e-4)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning); W=model.fit_transform(X)
    canonicalize_factors(model.components_,W)
    return model,W,{'seed':seed,'components':n,'iterations':int(model.n_iter_),
        'reconstruction_error':float(model.reconstruction_err_),
        'convergence_warning':any(issubclass(x.category,ConvergenceWarning) for x in caught)}
def compare_topics(base, base_w, other, other_w):
    sim=cosine_similarity(base.components_,other.components_); a,b=linear_sum_assignment(-sim)
    aligned=np.zeros_like(other_w); aligned[:,a]=other_w[:,b]
    return {'matched_topic_cosines':sim[a,b].tolist(),'mean_matched_topic_cosine':float(sim[a,b].mean()),
        'dominant_topic_ari':float(adjusted_rand_score(np.argmax(base_w,axis=1),np.argmax(aligned,axis=1))),
        'mixture_mean_absolute_change':float(np.abs(mixture(base_w)-mixture(aligned)).mean())}


def main(args):
    start=time.monotonic(); public=args.public.resolve(); private=args.private.resolve()
    public.mkdir(parents=True,exist_ok=True); private.mkdir(parents=True,exist_ok=True)
    (public/'tables').mkdir(exist_ok=True); (public/'figures').mkdir(exist_ok=True)
    docs=load_inputs(args.frame); records=[d['record'] for d in docs]
    ids=[r['source_id'] for r in records]; texts=[d['text'] for d in docs]
    if len(ids)!=len(set(ids)): raise ValueError('Repeated selected source ID')
    if len({r['body_sha256'] for r in records})!=len(records): raise ValueError('Repeated selected body hash')
    groups=[r['channel_id'] for r in records]; origins=[r['text_origin'] for r in records]
    strata=[ORIGIN_STRATA.get(x,x) for x in origins]; creators=[r['creator_id'] for r in records]
    order=sorted(set(groups)); membership={g:[i for i,x in enumerate(groups) if x==g] for g in order}
    phrases=sorted({p for r in records for p in r.get('mask_phrases',[]) if p and p.lower() not in ('unknown','unresolved')})
    if not phrases: raise ValueError('Identity masking registry required')
    full=[masked(t,phrases) for t in texts]; spans=[bounded(t,300) for t in texts]
    window=[masked(x[0],phrases) for x in spans]
    opts={'tokenizer':str.split,'preprocessor':None,'token_pattern':None,'lowercase':False,
          'ngram_range':(1,2),'sublinear_tf':True,'min_df':2,'max_features':24000,'stop_words':STOP}
    V=TfidfVectorizer(**opts); X=V.fit_transform(' '.join(words(t)) for t in full)
    XW=V.transform(' '.join(words(t)) for t in window)
    VR=TfidfVectorizer(**opts); XR=VR.fit_transform(' '.join(words(t)) for t in texts)
    terms=V.get_feature_names_out(); n=len(ids)
    # Fit the same vocabulary with context-balanced IDF, then transform ALL sources.
    # This changes corpus weighting, not the common comparison universe.
    chosen=sorted(i for g in order for i in sorted(membership[g],key=lambda j:hashlib.sha256(ids[j].encode()).hexdigest())[:10])
    VB=TfidfVectorizer(**{**opts,'vocabulary':V.vocabulary_})
    VB.fit([' '.join(words(full[i])) for i in chosen]); XB=VB.transform([' '.join(words(t)) for t in full])
    L=np.clip(cosine_similarity(X),-1,1); LW=np.clip(cosine_similarity(XW),-1,1)
    LR=np.clip(cosine_similarity(XR),-1,1); LB=np.clip(cosine_similarity(XB),-1,1)
    if any(np.asarray(z.multiply(z).sum(axis=1)).ravel().min()<=0 for z in (X,XW,XR,XB)):
        raise ValueError('Zero lexical row: comparisons require an explicit common eligible subset')
    print(json.dumps({'stage':'lexical','sources':n,'features':X.shape[1],'balanced_fit_documents':len(chosen)}),flush=True)
    topic_model,W,trial=fit_nmf(X,11); trials=[trial]; witnesses={'topic_components_11':topic_model.components_,'topic_weights_11':W}
    for seed in (23,47):
        model,w,trial=fit_nmf(X,seed);trial.update(compare_topics(topic_model,W,model,w));trials.append(trial)
        witnesses['topic_components_'+str(seed)]=model.components_;witnesses['topic_weights_'+str(seed)]=w
    balanced,bw,bt=fit_nmf(X[chosen],11); bw_all=balanced.transform(X)
    bt.update(compare_topics(topic_model,W,balanced,bw_all));bt['fit_documents']=len(chosen)
    witnesses['balanced_topic_components']=balanced.components_;witnesses['balanced_topic_weights']=bw_all
    topics=[{'topic_id':f'T{k+1:02d}','label':' / '.join(x['term'] for x in top_terms(c,terms,3)),
             'terms':[{'term':t['term'],'weight':t['score']} for t in top_terms(c,terms,15)]}
            for k,c in enumerate(topic_model.components_)]
    mix=mixture(W)
    print(json.dumps({'stage':'topics','seed_trials':len(trials),'balanced_topic_match':bt['mean_matched_topic_cosine']}),flush=True)
    svd=TruncatedSVD(n_components=min(50,n-2),random_state=11); Z=normalize(svd.fit_transform(X))
    cluster_trials=[]; main_labels=None; clusters={}
    for k in (4,6,8,10):
        for seed in (11,23,47):
            labels=KMeans(n_clusters=k,n_init=10,random_state=seed).fit_predict(Z)
            clusters[f'k{k}_seed{seed}']=labels
            cluster_trials.append({'k':k,'seed':seed,'cosine_silhouette_svd50':float(silhouette_score(Z,labels,metric='cosine')),
                'publisher_context_ari':float(adjusted_rand_score(groups,labels)),
                'creator_context_ari':float(adjusted_rand_score(creators,labels)),
                'text_origin_ari':float(adjusted_rand_score(strata,labels))})
            if (k,seed)==(8,11): main_labels=labels
    cluster_stability=[{'k':k,'seed_left':a,'seed_right':b,'ari':float(adjusted_rand_score(clusters[f'k{k}_seed{a}'],clusters[f'k{k}_seed{b}']))}
        for k in (4,6,8,10) for a,b in ((11,23),(11,47),(23,47))]
    xy,projection=coordinates(X,L)
    diagnostics={'rows':[], 'topic_seeds':trials,'balanced_topic_fit':bt,
                 'cluster_trials':cluster_trials,'cluster_seed_stability':cluster_stability,
                 'projection':projection,'cluster_rule':'Fixed illustrative k=8, seed11 on unit-normalized 50D TF-IDF SVD; k=4,6,10 are diagnostics, not a selected optimum.'}
    for label,a,b in [('identity_mask',L,LR),('centered_300_word_window',L,LW),('balanced_idf',L,LB)]:
        d=sensitivity(a,b,ids,groups);d['analysis']=label;diagnostics['rows'].append(d)
    enrichment_data={label:enrichment(L,ids,values) for label,values in [('publisher_context',groups),('creator_context',creators),('text_origin',strata)]}
    semantic=None
    if args.model:
        encoder=LabEncoder(args.model); vectors,equal,receipt=encoder.encode_all(list(zip(ids,window)),private/'semantic-cache',8)
        SM=np.clip(cosine_similarity(vectors),-1,1)
        d=sensitivity(LW,SM,ids,groups);d['analysis']='bounded_lexical_vs_MiniLM';diagnostics['rows'].append(d)
        binding={**encoder.binding,'batch_size':8,'cache':'Exact input/model/encoder-contract cache; private vectors and hashes retained.',
                 'equal_chunk_sensitivity':False}
        semantic={'binding':binding,'sources':n,'chunks':receipt['chunks'],
                  'content_wordpieces':receipt['content_wordpieces'],'invocation_encoding_seconds':receipt['invocation_encoding_seconds'],
                  'original_encoding_seconds':receipt['original_encoding_seconds'],'reused_exact_cache':receipt['reused_exact_cache'],
                  'input':'Centered maximum300 lexical-word spans, masked with exactly the same phrase registry as TF-IDF.',
                  'scope':'Pinned pretrained CPU baseline. No weight update, model distillation or claim of current SOTA accuracy.',
                  'truncated_wordpieces':sum(x['truncated_wordpieces'] for x in receipt['coverage'])}
        witnesses['bounded_semantic_vectors']=vectors;witnesses['bounded_semantic_cosine']=SM
        save(private/'semantic-receipt.json',receipt)
    print(json.dumps({'stage':'profiles','sources':n}),flush=True)
    profiles=[]; publication_dates=[]; qa=[]; cue_counts=Counter()
    for i,(text,r) in enumerate(zip(texts,records)):
        # Punctuation only: neither a true question label nor an answered turn.
        for m in re.finditer(r'[^.!?\n]{4,500}\?',text):
            q=m.group().strip()
            if len(q.split())<3: continue
            qa.append({'source_id':ids[i],'body_sha256':r['body_sha256'],'char_start':m.start(),'char_end':m.end(),
                       'question_cue':m.group(),'following_context':text[m.end():m.end()+1000],
                       'status':'unvalidated_punctuation_question_cue_not_verified_QA'})
            cue_counts[groups[i]]+=1
    means=np.stack([np.asarray(X[membership[g]].mean(axis=0)).ravel() for g in order])
    values, pair_counts=group_matrix(L,groups,order)
    for gi,g in enumerate(order):
        ix=membership[g]; rr=[records[i] for i in ix]; lengths=[r['words'] for r in rr]
        dates=sorted(str(r['publication_date'])[:10] for r in rr if re.match(r'^\d{4}-\d{2}-\d{2}',str(r.get('publication_date'))))
        contrast=means[gi]-np.delete(means,gi,axis=0).mean(axis=0)
        p={'channel_id':g,'channel_name':rr[0]['channel_name'],'creator_context_ids':sorted({r['creator_id'] for r in rr}),
           'documents':len(ix),'words':sum(lengths),'origins':dict(Counter(r['text_origin'] for r in rr)),
           'origin_strata':dict(Counter(strata[i] for i in ix)), 'median_words':float(np.median(lengths)),
           'min_words':min(lengths),'max_words':max(lengths),'date_range':[dates[0],dates[-1]] if dates else None,
           'dated_documents':len(dates),'date_basis':'Publisher/source metadata dates, not verified speech/event dates.',
           'topics':[{'topic_id':t['topic_id'],'weight':float(mix[ix,j].mean())} for j,t in enumerate(topics)],
           'top_terms':top_terms(means[gi],terms),'contrast_terms':top_terms(contrast,terms),
           'small_context_warning': 'Fewer than five admitted documents; descriptive profile only, no within-context clustering or generalization.' if len(ix)<5 else None,
           'source_ids':[ids[i] for i in ix], 'question_cue_count':cue_counts[g],
           'question_cue_status':'Unvalidated punctuation cues, not verified questions or answers.',
           'uploaded_total':None,'uploaded_total_basis':'No complete YouTube channel census is available.'}
        profiles.append(p)
    doc_rows=[]
    for i,r in enumerate(records):
        cross=sorted((j for j in range(n) if groups[j]!=groups[i]),key=lambda j:(-L[i,j],ids[j]))[:5]
        doc_rows.append({'source_id':ids[i],'body_sha256':r['body_sha256'],'channel_id':groups[i],
            'words':r['words'],'text_origin':origins[i],'topic_id':topics[int(mix[i].argmax())]['topic_id'],
            'topic_mixture':mix[i].tolist(),'cluster_id':int(main_labels[i])+1,'x':float(xy[i,0]),'y':float(xy[i,1]),
            'top_terms':top_terms(X[i],terms,8),'nearest_cross_context':[{'source_id':ids[j],'cosine':float(L[i,j])} for j in cross],
            'question_cues':sum(q['source_id']==ids[i] for q in qa)})
    graph=graph_summary(L,ids)
    # Existing helper provides mutual3 witness; use mutual5 for exported display.
    near=[sorted((j for j in range(n) if j!=i),key=lambda j:(-L[i,j],ids[j]))[:5] for i in range(n)]
    sets=list(map(set,near)); edges=[{'source':ids[i],'target':ids[j],'cosine':float(L[i,j])}
        for i in range(n) for j in near[i] if i<j and i in sets[j]]
    graph.update({'edges':edges,'nodes':[{'source_id':r['source_id'],'channel_id':r['channel_id'],'x':r['x'],'y':r['y']} for r in doc_rows],
                  'rule':'Undirected mutual5 nearest neighbors by full masked TF-IDF cosine, no minimum threshold; ties by source ID.'})
    concentration=sorted(Counter(groups).items(),key=lambda x:(-x[1],x[0]))
    summary={'documents':n,'words':sum(r['words'] for r in records),'publisher_contexts':len(order),
        'creator_contexts':len(set(creators)),'text_origins':dict(Counter(origins)),'origin_strata':dict(Counter(strata)),
        'largest_contexts':[{'channel_id':g,'documents':c,'fraction':c/n} for g,c in concentration[:5]],
        'top_two_context_fraction':sum(c for _,c in concentration[:2])/n,
        'singleton_contexts':sum(len(membership[g])==1 for g in order),'contexts_under_five':sum(len(membership[g])<5 for g in order),
        'punctuation_question_cues':len(qa),'unique_selected_body_hashes':len(set(r['body_sha256'] for r in records)),
        'exact_pairwise_similarities':n*(n-1)//2,'vocabulary_terms':len(terms),
        'near_duplicate_review_pairs_cosine_ge_095':sum(L[i,j]>=.95 for i in range(n) for j in range(i+1,n)),
        'scope':'Selected text editions of finite observed publication/source units, not a YouTube census or random sample.'}
    settings={'tfidf':{k:v for k,v in opts.items() if k not in ('tokenizer','stop_words')},
        'stop_words':STOP,'tokenizer':'Unicode alphabetic tokens; apostrophes retained; casefold; straight apostrophe normalization.',
        'mask_phrases':phrases,'mask_scope':'Exact declared phrase registry only. Residual names/attributions may remain; masking is a sensitivity, not anonymization.',
        'balanced_fit_cap':10,'balanced_fit_sources':[ids[i] for i in chosen],
        'balanced_fit_selection':'Per-context source-ID SHA256 ascending; up to10 selected source units, no minimum quota.',
        'topic_count':8,'topic_init':'random','topic_seeds':[11,23,47],'topic_max_iter':2000,
        'topic_scale':'UnitL2 components and reciprocally rescaled W; document L1 mixture.',
        'topic_scope':'Exploratory factors of this corpus. Labels concatenate top terms, not validated interpretive categories.',
        'clustering':diagnostics['cluster_rule'],'svd_dimensions':50,'svd_explained_variance':float(svd.explained_variance_ratio_.sum()),
        'document_weight':'Each selected source unit receives equal weight; no independence or representative-sampling claim.',
        'pair_weight':'Similarity cells average all source pairs excluding self pairs; within-context uses unordered distinct pairs.',
        'top_term_scores':'Document scores are L2-normalized TF-IDF weights; context scores are source means; contrast scores subtract the equally weighted mean of other context means. These are not counts.',
        'runtime':'CPU only; one OpenMP/BLAS/ONNX intra/inter thread; shared cloud quota4CPUs and32GiB, noGPU.'}
    limitations=[
        'Corpus and publisher coverage are opportunistic, incomplete and strongly imbalanced; uploaded lifetime totals are unknown.',
        'Source units, publisher contexts, creator contexts, accounts, recordings, claimed beings and text editions are different units.',
        'Publisher-written bodies are not verbatim audio transcripts or proof of alignment; ASR accuracy is unvalidated.',
        'Word/phrase cosine measures lexical or representation proximity, never agreement, truth, contradiction or shared origin.',
        'Context, language style, text origin, date and length are confounded; controls are descriptive, not causal identification.',
        'No inferential pairwise p-values: source pairs overlap and publisher episodes are not independent samples.',
        'NMF factors and KMeans labels are illustrative choices; instability and component-count diagnostics remain visible.',
        'Alphabetic tokenization can fragment alphanumeric labels (for example3D becomes d); factors may capture formatting or conversational register such as yeah instead of distinct doctrines.',
        'Two-dimensional source layout is lossy; distances shown on screen are not authoritative original-space cosine.',
        'Question punctuation cues and following context are unvalidated; no automatic common-answer/conflict labels are claimed.',
        'Claimed-entity names are publisher/speaker attributions; sparse unharmonized labels do not justify civilization-level pooled inference.'
    ]
    output={'schema_version':'dataset-analysis-1','frame_sha256':digest(args.frame),'summary':summary,
        'channel_profiles':profiles,'topics':topics,'documents':doc_rows,'graph':graph,
        'channel_similarity':{'order':order,'values':values,'pair_counts':pair_counts,'metric':'Mean full masked TF-IDF cosine',
            'scope':'Dependent descriptive pairs; null within singleton context; no agreement or independent sample-size claim.'},
        'sensitivity':diagnostics,'enrichment':enrichment_data,'semantic':semantic,'settings':settings,'limitations':limitations,'figures':[]}
    table_rows=[{k:p[k] for k in ('channel_id','channel_name','documents','words','median_words','dated_documents','question_cue_count')} for p in profiles]
    write_csv(public/'tables/channel-profile.csv',table_rows)
    write_csv(public/'tables/text-origins.csv',[{'text_origin':o,'documents':v,'words':sum(records[i]['words'] for i,x in enumerate(origins) if x==o)} for o,v in sorted(Counter(origins).items())])
    write_csv(public/'tables/cluster-diagnostics.csv',cluster_trials)
    write_csv(public/'tables/topic-terms.csv',[{'topic_id':t['topic_id'],'rank':j+1,**r} for t in topics for j,r in enumerate(t['terms'])])
    write_csv(public/'tables/context-similarity.csv',[{'left':a,'right':b,'mean_cosine':values[i][j],'source_pairs':pair_counts[i][j]}
        for i,a in enumerate(order) for j,b in enumerate(order) if i<=j])
    write_csv(public/'tables/source-analysis.csv',[{k:r[k] for k in ('source_id','channel_id','words','text_origin','topic_id','cluster_id','x','y','question_cues')} for r in doc_rows])
    save(public/'analysis.json',output)
    save(private/'question-cues-private.json',{'scope':'Punctuation cues + following1000characters, not verified Q&A. Reuse needs annotation.','records':qa})
    save(private/'ordered-inputs.json',{'frame_sha256':digest(args.frame),'records':[{'source_id':r['source_id'],'body_sha256':r['body_sha256'],'words':r['words']} for r in records],
         'centered_spans':[{'source_id':ids[i],**x[1]} for i,x in enumerate(spans)]})
    sparse.save_npz(private/'tfidf.npz',X); sparse.save_npz(private/'bounded-tfidf.npz',XW)
    save(private/'vocabulary.json',{'features':terms.tolist(),'idf':V.idf_.tolist(),'balanced_idf':VB.idf_.tolist()})
    np.savez_compressed(private/'numerical-witness.npz',source_ids=np.asarray(ids),lexical_cosine=L,bounded_lexical_cosine=LW,
        raw_lexical_cosine=LR,balanced_idf_cosine=LB,coordinates=xy,cluster_features=Z,**witnesses,**clusters)
    from plot_analysis import plot_all
    output['figures']=plot_all(output,public,records)
    save(public/'analysis.json',output)
    result={'status':'executed_descriptive_analysis','frame_sha256':digest(args.frame),'summary':summary,
        'representation_sensitivity':[{k:r[k] for k in ('analysis','eligible_sources','mean_jaccard','channel_macro_jaccard','pair_spearman')} for r in diagnostics['rows']],
        'topic_seed_diagnostics':trials,'balanced_topic_fit':bt,'cluster_trials':cluster_trials,'cluster_seed_stability':cluster_stability,
        'group_enrichment':{k:{'macro_group_excess':v['macro_group_excess'],'eligible_sources':v['eligible_sources']} for k,v in enrichment_data.items()},
        'projection':projection,'semantic':semantic,'settings':{k:v for k,v in settings.items() if k not in ('stop_words','mask_phrases','balanced_fit_sources')},
        'wall_seconds':time.monotonic()-start,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packages':{k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','matplotlib','onnxruntime')},
        'code':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),Path(__file__).with_name('plot_analysis.py'),ROOT/'research/channel-lab/analyze_corpus.py',ROOT/'research/channel-lab/analyze_encoder.py',ROOT/'research/channel-lab/sources.py']},
        'figures':output['figures'],'limitations':limitations}
    save(public/'results.json',result)
    save(private/'analysis-receipt.json',{'public_files':[{'path':str(p.relative_to(public)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(public.rglob('*')) if p.is_file()],
         'private_files':[{'path':str(p.relative_to(private)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(private.rglob('*')) if p.is_file()]})
    print(json.dumps({'status':'complete','sources':n,'words':summary['words'],'seconds':result['wall_seconds']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frame',type=Path,required=True);p.add_argument('--private',type=Path,required=True)
    p.add_argument('--public',type=Path,required=True);p.add_argument('--model',type=Path)
    main(p.parse_args())
