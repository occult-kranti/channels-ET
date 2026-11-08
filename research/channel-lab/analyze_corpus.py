#!/usr/bin/env python3
"""Shared source-bound lexical, topic and complete neural analysis for Channel Lab."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import time
import warnings
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF,PCA,TruncatedSVD
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS,TfidfVectorizer
from sklearn.manifold import trustworthiness
from sklearn.metrics import adjusted_rand_score,silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from analyze_encoder import LabEncoder

RAM=Path('/dev/shm/channel-lab-2026-11')
TOKEN=re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*",re.UNICODE)
STOP=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'})
ORIGIN_STRATA={'local_asr':'local_machine_transcript','machine_asr':'local_machine_transcript',
    'retained_local_asr':'local_machine_transcript','linked_publisher_caption':'publisher_caption_unknown_origin',
    'platform_auto_caption':'platform_automatic_caption','publisher_labeled_transcript_pdf':'publisher_labeled_transcript',
    'publisher_transcript':'publisher_transcript','publisher_written':'publisher_written_message'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def ref(path):path=Path(path);return {'file':path.name,'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def finite(value):return float(value) if np.isfinite(value) else None
def mean(values):return finite(np.mean(values)) if len(values) else None
def words(text):return [m.group().casefold().replace('’',"'") for m in TOKEN.finditer(text)]


def masked(text,phrases):
    for phrase in sorted(set(phrases),key=lambda p:(-len(p),p.casefold())):
        pattern=r'(?<!\w)'+r'[\s\-]+'.join(re.escape(w) for w in phrase.split())+r'(?!\w)'
        text=re.sub(pattern,lambda m:' '*len(m.group()),text,flags=re.I)
    return text


def bounded(text,count=300):
    matches=list(TOKEN.finditer(text))
    if len(matches)<=count:return text,{'start':0,'end':len(text),'tokens':len(matches),'short_body_retained':True}
    offset=(len(matches)-count)//2;start=matches[offset].start();end=matches[offset+count-1].end()
    return text[start:end],{'start':start,'end':end,'tokens':count,'short_body_retained':False}


def matrix_for(vectors):
    norms=np.asarray(vectors.multiply(vectors).sum(axis=1)).ravel() if hasattr(vectors,'multiply') else np.linalg.norm(vectors,axis=1)
    available=norms>1e-12;matrix=cosine_similarity(vectors).astype(float)
    matrix=np.clip(matrix,-1,1);matrix[~available,:]=np.nan;matrix[:,~available]=np.nan
    for i in np.flatnonzero(available):matrix[i,i]=1.
    return matrix.astype('<f4').astype(float),available


def neighbors(matrix,ids,k=5,universe=None):
    allowed=set(range(len(ids))) if universe is None else set(universe)
    return [[j for j in sorted((j for j in allowed if i!=j and np.isfinite(matrix[i,j])),key=lambda j:(-matrix[i,j],ids[j]))[:k]] if i in allowed else [] for i in range(len(ids))]


def overlap(a,b):return len(set(a)&set(b))/len(set(a)|set(b)) if a or b else None


def sensitivity(left,right,ids,groups):
    common=np.flatnonzero(np.isfinite(np.diag(left))&np.isfinite(np.diag(right))).tolist()
    first=neighbors(left,ids,universe=common);second=neighbors(right,ids,universe=common)
    rows=[{'source_id':ids[i],'eligible':i in common,'jaccard':overlap(first[i],second[i]) if i in common else None,
           'full_ids':[ids[j] for j in first[i]],'control_ids':[ids[j] for j in second[i]]} for i in range(len(ids))]
    by=collections.defaultdict(list)
    for i,row in enumerate(rows):
        if row['jaccard'] is not None:by[groups[i]].append(row['jaccard'])
    upper=[(left[i,j],right[i,j]) for pos,i in enumerate(common) for j in common[pos+1:]]
    rank=finite(spearmanr(np.asarray(upper)[:,0],np.asarray(upper)[:,1]).statistic) if len(upper)>2 else None
    return {'eligible_sources':len(common),'same_source_universe':True,'k':5,'rows':rows,
            'mean_jaccard':mean([r['jaccard'] for r in rows if r['jaccard'] is not None]),
            'channel_macro_jaccard':mean([np.mean(v) for v in by.values()]),'pair_spearman':rank,
            'scope':'Dependent descriptive stability; full and control neighbors use the identical available-source subset.'}


def group_matrix(matrix,groups,order):
    values=[];counts=[]
    for left in order:
        v=[];c=[]
        for right in order:
            entries=[matrix[i,j] for i,g in enumerate(groups) if g==left for j,h in enumerate(groups)
                     if h==right and i!=j and (left!=right or i<j) and np.isfinite(matrix[i,j])]
            v.append(mean(entries));c.append(len(entries))
        values.append(v);counts.append(c)
    return values,counts


def enrichment(matrix,ids,groups):
    valid=np.flatnonzero(np.isfinite(np.diag(matrix))).tolist();near=neighbors(matrix,ids,universe=valid)
    count=collections.Counter(groups[i] for i in valid);rows=[];by=collections.defaultdict(list)
    for i in valid:
        if not near[i]:continue
        observed=sum(groups[i]==groups[j] for j in near[i])/len(near[i]);expected=(count[groups[i]]-1)/(len(valid)-1)
        delta=observed-expected;by[groups[i]].append(delta)
        rows.append({'source_id':ids[i],'same_group_fraction':observed,'availability_baseline':expected,'excess':delta})
    return {'eligible_sources':len(valid),'rows':rows,'macro_group_excess':mean([np.mean(x) for x in by.values()]),
            'groups':[{'group_id':g,'documents':len(v),'mean_excess':mean(v)} for g,v in sorted(by.items())],
            'scope':'Availability-adjusted neighbor enrichment, descriptively macro-averaged over groups; no independent-pair p-value.'}


def coordinates(vectors,matrix,semantic=False):
    valid=np.flatnonzero(np.isfinite(np.diag(matrix)));xy=np.full((len(matrix),2),np.nan)
    if len(valid)<3:return xy,{'available_sources':len(valid),'explained_variance':[],'trustworthiness':None}
    model=PCA(n_components=2,svd_solver='full') if semantic else TruncatedSVD(n_components=2,random_state=11)
    z=model.fit_transform(vectors[valid]);z-=z.mean(axis=0);radius=np.sqrt(np.mean(np.sum(z*z,axis=1)))
    z/=max(float(radius),1e-12);xy[valid]=z
    k=min(5,(len(valid)-1)//2)
    trust=float(trustworthiness(np.clip(1-matrix[np.ix_(valid,valid)],0,2),z,n_neighbors=k,metric='precomputed'))
    return xy,{'available_sources':len(valid),'explained_variance':model.explained_variance_ratio_.tolist(),
              'trustworthiness':trust,'trustworthiness_k':k,'scope':'Lossy centered/RMS-scaled 2D display; original-space cosines are authoritative.'}


def graph_summary(matrix,ids):
    n=len(ids);valid=np.flatnonzero(np.isfinite(np.diag(matrix))).tolist()
    def count(edges):
        parent=list(range(n))
        def find(x):
            while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
            return x
        degree=collections.Counter()
        for i,j in edges:parent[find(i)]=find(j);degree[i]+=1;degree[j]+=1
        sizes=collections.Counter(find(i) for i in valid)
        return {'edges':len(edges),'components':len(sizes),'isolated_nodes':sum(degree[i]==0 for i in valid),'largest_component':max(sizes.values(),default=0)}
    knn=[];reference=[]
    for k in (3,5,10):
        near=neighbors(matrix,ids,k);sets=[set(x) for x in near]
        edges=[(i,j) for i in valid for j in near[i] if i<j and i in sets[j]]
        knn.append({'k':k,'rule':'mutual k-nearest neighbors',**count(edges)})
        if k==3:reference=[{'source':ids[i],'target':ids[j],'similarity':float(matrix[i,j]),'mutual_knn_3':True} for i,j in edges]
    thresholds=[]
    for threshold in (.3,.5,.7,.85):
        edges=[(i,j) for pos,i in enumerate(valid) for j in valid[pos+1:] if matrix[i,j]>=threshold]
        thresholds.append({'threshold':threshold,**count(edges)})
    return {'available_nodes':len(valid),'knn_trials':knn,'threshold_trials':thresholds,'edges':reference,
            'scope':'Similarity network, not a causal/social/contact graph. Thresholds and k are exploratory display settings.'}


def nmf_fit(X,seed):
    model=NMF(n_components=8,init='random',random_state=seed,max_iter=500,tol=1e-4)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning);weights=model.fit_transform(X)
    norms=canonicalize_factors(model.components_,weights);active=norms>1e-12
    return model,weights,{'seed':seed,'iterations':int(model.n_iter_),'reconstruction_error':float(model.reconstruction_err_),
        'convergence_warning':any(issubclass(w.category,ConvergenceWarning) for w in caught),
        'original_component_l2_norms':norms.tolist(),'active_components':int(active.sum()),
        'scale_rule':'Unit L2 topic-term components with reciprocal document-weight rescaling preserve W@H; mixtures and chunk transforms use this fixed scale.'}


def canonicalize_factors(components,weights):
    norms=np.linalg.norm(components,axis=1);active=norms>1e-12
    components[active]/=norms[active,None];weights[:,active]*=norms[active];weights[:,~active]=0
    return norms


def mixture(weights):
    totals=weights.sum(axis=1,keepdims=True);return np.divide(weights,totals,out=np.zeros_like(weights),where=totals>0)


def load_inputs(frame_path):
    path=Path(__file__).parent/'sources.py';spec=importlib.util.spec_from_file_location('channel_lab_sources',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    loaded=module.load_frame(frame_path)
    return loaded[0] if isinstance(loaded,tuple) else loaded


def run(frame_path,model_path,out,batch_size=8):
    started=time.monotonic();code_sha=sha(Path(__file__).read_bytes());out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(RAM):raise ValueError('Fresh RAM analysis output required')
    frame_path=Path(frame_path);frame=json.loads(frame_path.read_text());docs=load_inputs(frame_path)
    records=[d['record'] for d in docs];ids=[r['source_id'] for r in records];texts=[d['text'] for d in docs]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate canonical source ID')
    groups=[r['channel_id'] for r in records];creators=[r['creator_id'] for r in records]
    origins=[r['text_origin'] for r in records];strata=[ORIGIN_STRATA.get(x,'other_declared_origin') for x in origins]
    order=sorted(set(groups));names={r['channel_id']:r['channel_name'] for r in records}
    phrases=sorted({p for r in records for p in r.get('mask_phrases',[]) if p and p.lower() not in ('unknown','unresolved')})
    if not phrases:raise ValueError('Explicit source-bound identity mask registry required')
    full=[masked(t,phrases) for t in texts];span_info=[bounded(t) for t in texts]
    raw_windows=[x[0] for x in span_info];windows=[masked(t,phrases) for t in raw_windows]
    encoder=LabEncoder(model_path)
    S,E,encoding=encoder.encode_all(list(zip(ids,full)),RAM/'encoder-cache',batch_size)
    SW,_,window_encoding=encoder.encode_all(list(zip(ids,windows)),RAM/'encoder-cache',batch_size)
    SU,_,unmasked_encoding=encoder.encode_all(list(zip(ids,raw_windows)),RAM/'encoder-cache',batch_size)
    print(json.dumps({'stage':'lexical','documents':len(ids)}),flush=True)
    opts={'tokenizer':str.split,'preprocessor':None,'token_pattern':None,'lowercase':False,
          'ngram_range':(1,2),'sublinear_tf':True,'min_df':2,'max_features':24000,'stop_words':STOP}
    vectorizer=TfidfVectorizer(**opts);X=vectorizer.fit_transform(' '.join(words(t)) for t in full)
    XW=vectorizer.transform(' '.join(words(t)) for t in windows)
    raw_vectorizer=TfidfVectorizer(**opts);XR=raw_vectorizer.fit_transform(' '.join(words(t)) for t in texts)
    L,la=matrix_for(X);LW,lwa=matrix_for(XW);LR,_=matrix_for(XR)
    M,ma=matrix_for(S);MW,mwa=matrix_for(SW);MU,_=matrix_for(SU);ME,_=matrix_for(E)
    feature_names=vectorizer.get_feature_names_out();features=len(feature_names)
    print(json.dumps({'stage':'topics','features':features}),flush=True)
    topic_model,W,first_run=nmf_fit(X,11);topic_runs=[first_run];topic_mixtures=mixture(W)
    topic_witness={'components_11':topic_model.components_.copy(),'weights_11':W.copy()}
    for seed in (23,47):
        other,otherW,trial=nmf_fit(X,seed);cross=cosine_similarity(topic_model.components_,other.components_)
        left,right=linear_sum_assignment(-cross);aligned=np.zeros_like(otherW);aligned[:,left]=otherW[:,right]
        trial.update(matched_topic_term_cosines=cross[left,right].tolist(),mean_matched_topic_term_cosine=float(np.mean(cross[left,right])),
                     dominant_topic_adjusted_rand=float(adjusted_rand_score(np.argmax(W,axis=1),np.argmax(aligned,axis=1))),
                     mixture_mean_absolute_change=float(np.abs(mixture(W)-mixture(aligned)).mean()))
        topic_runs.append(trial)
        topic_witness['components_'+str(seed)]=other.components_.copy();topic_witness['weights_'+str(seed)]=otherW.copy()
    topics=[]
    for i,component in enumerate(topic_model.components_):
        top=sorted(range(features),key=lambda j:(-component[j],feature_names[j]))[:14]
        topics.append({'topic_id':f'T{i+1:02d}','label':' / '.join(feature_names[j] for j in top[:3]),
                       'terms':[{'term':str(feature_names[j]),'weight':float(component[j])} for j in top]})
    chunk_texts=[];chunk_rows=[];private_locators=[]
    for index,text in enumerate(texts):
        positions=list(re.finditer(r'\S+',text))
        for start in range(0,len(positions),500):
            end=min(start+500,len(positions));a=positions[start].start();b=positions[end-1].end()
            chunk_rows.append({'owner':index,'ordinal':sum(c['owner']==index for c in chunk_rows),
                'word_start':start,'word_end':end,'words':end-start,'start_fraction':start/len(positions),'end_fraction':end/len(positions),
                'normalized_position':(start+end)/(2*len(positions))})
            chunk_texts.append(' '.join(words(full[index][a:b])))
            private_locators.append({'source_id':ids[index],'body_sha256':records[index]['body_sha256'],
                'char_start':a,'char_end':b,'span_sha256':sha(text[a:b].encode()),'word_start':start,'word_end':end})
    CX=vectorizer.transform(chunk_texts);chunk_weights=topic_model.transform(CX);chunk_mix=mixture(chunk_weights)
    Lxy,Lproj=coordinates(X,L);Mxy,Mproj=coordinates(S,M,True)
    diagnostics={'lexical_vs_semantic':sensitivity(L,M,ids,groups),
        'lexical_bounded_window':sensitivity(L,LW,ids,groups),'semantic_bounded_window':sensitivity(M,MW,ids,groups),
        'lexical_name_mask':sensitivity(L,LR,ids,groups),'semantic_window_name_mask':sensitivity(MW,MU,ids,groups),
        'semantic_weighted_vs_equal_chunks':sensitivity(M,ME,ids,groups),
        'channel_enrichment':{'lexical':enrichment(L,ids,groups),'semantic':enrichment(M,ids,groups)},
        'creator_enrichment':{'lexical':enrichment(L,ids,creators),'semantic':enrichment(M,ids,creators)},
        'topic_seeds':topic_runs,'projections':{'lexical':Lproj,'semantic':Mproj}}
    cluster_runs=[];valid=np.flatnonzero(ma);distance=np.clip(1-M[np.ix_(valid,valid)],0,2)
    for seed in (11,23,47):
        labels=KMeans(n_clusters=8,n_init=10,random_state=seed).fit_predict(S[valid])
        cluster_runs.append({'seed':seed,'k':8,'cosine_silhouette':float(silhouette_score(distance,labels,metric='precomputed')),
            'channel_adjusted_rand':float(adjusted_rand_score([groups[i] for i in valid],labels)),
            'creator_adjusted_rand':float(adjusted_rand_score([creators[i] for i in valid],labels)),
            'origin_adjusted_rand':float(adjusted_rand_score([origins[i] for i in valid],labels)),
            'origin_stratum_adjusted_rand':float(adjusted_rand_score([strata[i] for i in valid],labels)),
            'assignments':[{'source_id':ids[i],'cluster':int(label)+1} for i,label in zip(valid,labels)]})
    diagnostics['clusters']={'k':8,'runs':cluster_runs,'scope':'Fixed separate KMeans display partition of document embeddings, not NMF factors or a doctrine count.',
        'seed_pair_adjusted_rand':[{'left':cluster_runs[i]['seed'],'right':cluster_runs[j]['seed'],
            'value':float(adjusted_rand_score([x['cluster'] for x in cluster_runs[i]['assignments']],[x['cluster'] for x in cluster_runs[j]['assignments']]))}
            for i in range(3) for j in range(i+1,3)]}
    for name in ('lexical_vs_semantic','lexical_bounded_window','semantic_bounded_window','lexical_name_mask','semantic_window_name_mask','semantic_weighted_vs_equal_chunks'):
        by_creator=collections.defaultdict(list)
        for i,row in enumerate(diagnostics[name]['rows']):
            if row['jaccard'] is not None:by_creator[creators[i]].append(row['jaccard'])
        diagnostics[name]['creator_macro_jaccard']=mean([np.mean(v) for v in by_creator.values()])
    channel_rows=[];channel_comparisons={'channel_ids':order};means=np.stack([np.asarray(X[[i for i,g in enumerate(groups) if g==c]].mean(axis=0)).ravel() for c in order])
    for channel_index,channel in enumerate(order):
        selected=[i for i,g in enumerate(groups) if g==channel];contrast=means[channel_index]-np.mean(np.delete(means,channel_index,axis=0),axis=0)
        topic_selected=[i for i in selected if W[i].sum()>0]
        top=sorted(range(features),key=lambda j:(-contrast[j],feature_names[j]))[:12]
        years=collections.Counter(str(records[i].get('publication_date'))[:4] for i in selected if re.match(r'^\d{4}',str(records[i].get('publication_date'))))
        channel_rows.append({'channel_id':channel,'name':names[channel],'documents':len(selected),'words':sum(records[i]['words'] for i in selected),
            'text_origins':dict(collections.Counter(origins[i] for i in selected)),
            'text_strata':dict(collections.Counter(strata[i] for i in selected)),'creator_ids':sorted(set(creators[i] for i in selected)),
            'topic_weights':topic_mixtures[topic_selected].mean(axis=0).tolist() if topic_selected else [0.]*8,
            'topic_available_documents':len(topic_selected),'year_counts':dict(sorted(years.items())),
            'unknown_dates':len(selected)-sum(years.values()),'contrast_terms':[{'term':str(feature_names[j]),'difference':float(contrast[j])} for j in top]})
    for name,matrix in [('lexical',L),('semantic',M),('window_lexical',LW),('window_semantic',MW)]:
        channel_comparisons[name],counts=group_matrix(matrix,groups,order);channel_comparisons[name+'_pair_counts']=counts
    channel_comparisons['scope']='Each cell weights its admitted canonical documents equally. Overall cross-channel summaries weight channel pairs equally; pair counts are dependent, not independent sample sizes.'
    out.mkdir(parents=True);(out/'details').mkdir();public_docs=[];detail_refs=[]
    for i,r in enumerate(records):
        sparse_row=X.getrow(i);top=sorted(zip(sparse_row.indices,sparse_row.data),key=lambda x:(-x[1],feature_names[x[0]]))[:10]
        progress=[{k:v for k,v in c.items() if k!='owner'}|{'topic_weights':chunk_mix[j].tolist(),
                   'lexical_available':bool(CX[j].nnz)} for j,c in enumerate(chunk_rows) if c['owner']==i]
        detail={'source_id':ids[i],'body_sha256':r['body_sha256'],'topic_progression':progress,
                'timeline_scope':'Nonoverlapping500-word source-text positions, not video timestamps or verified utterance boundaries.',
                'bounded_window':span_info[i][1],'encoding':{k:v for k,v in encoding['coverage'][i].items() if k!='body_sha256'}}
        path=out/'details'/(sha(ids[i].encode())[:20]+'.json');save(path,detail);binding={**ref(path),'file':'details/'+path.name};detail_refs.append(binding)
        public_docs.append({'source_id':ids[i],'channel_id':groups[i],'creator_id':creators[i],
            'words':r['words'],'published_at':r.get('publication_date'),'text_origin':origins[i],'origin_stratum':strata[i],'document_kind':r['document_kind'],
            'lexical_available':bool(la[i]),'semantic_available':bool(ma[i]),'topic_available':bool(W[i].sum()>0),'topic_weights':topic_mixtures[i].tolist(),
            'keywords':[{'term':str(feature_names[j]),'weight':float(v)} for j,v in top],
            'lexical_xy':{'x':finite(Lxy[i,0]),'y':finite(Lxy[i,1])},'semantic_xy':{'x':finite(Mxy[i,0]),'y':finite(Mxy[i,1])},
            'detail':binding})
    matrix_refs={'source_ids':ids}
    for name,matrix,available in [('lexical',L,la),('semantic',M,ma)]:
        path=out/(name+'-cosines.f32');path.write_bytes(matrix.astype('<f4').tobytes())
        matrix_refs[name]={**ref(path),'dtype':'float32-le','shape':[len(ids),len(ids)],
            'valid_source_ids':[ids[i] for i in np.flatnonzero(available)],'missing_cell':'NaN when either source lacks this representation; never zero similarity.'}
    upper=np.triu_indices(len(ids),1)
    origin_matrix,origin_counts=group_matrix(M,strata,sorted(set(strata)))
    near_duplicates=[{'left':ids[i],'right':ids[j],'lexical':finite(L[i,j]),'semantic':finite(M[i,j])}
                     for i,j in zip(*upper) if np.isfinite(L[i,j]) and L[i,j]>=.95]
    result={'schema_version':1,'status':'executed_canonical_frame_analysis','created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'bindings':{'frame_sha256':sha(frame_path.read_bytes()),'registry_sha256':sha((frame_path.parent/'registry.json').read_bytes()),
            'script_sha256':code_sha,'encoder_script_sha256':sha((Path(__file__).parent/'analyze_encoder.py').read_bytes()),
            'model_manifest_sha256':encoder.binding['model_manifest_sha256'],
            'terms_script_sha256':sha((Path(__file__).parent/'analyze_terms.py').read_bytes())},
        'coverage':{'documents':len(ids),'words':sum(r['words'] for r in records),'channels':len(order),'creators':len(set(creators)),
            'creator_contexts':len(set(creators)),'creator_scope':'Attribution-context IDs, not a census of unique people or verified speakers.',
            'lexical_available':int(la.sum()),'semantic_available':int(ma.sum()),'topic_progression_windows':len(chunk_rows),
            'unknown_dates':sum(not re.match(r'^\d{4}',str(r.get('publication_date'))) for r in records),'all_channel_upload_totals_verified':False},
        'methods':{'lexical':'Shared masked unigram/bigram TF-IDF; log TF, smoothed IDF, L2, min_df2, max24,000 features; negation retained.',
            'neural':{**encoder.binding,'batch_size':batch_size,'batch_order':'Content length descending, then original chunk ordinal',
                'inherited_model_loader_script_sha256':encoder.binding['encoder_script_sha256'],
                'encoder_script_sha256':sha((Path(__file__).parent/'analyze_encoder.py').read_bytes()),
                'cache':'Exact ordered input/model/pooling/code bindings in private RAM; no model weight updates'},
            'topic_model':'Fixed eight-factor NMF, random starts at seeds11/23/47, max500 iterations. Topic-term components scaled to unit L2 with compensating W columns; mixtures and progression use this fixed factor scale. Labels are top lexical terms.',
            'identity_mask_phrases':phrases,'identity_mask_scope':'Exact source-bound creator/channel/claimed-label phrases. Unlisted names, aliases, wording and style remain.',
            'bounded_window':'Centered up to300 lexical tokens; shorter sources remain intact. Each neighbor sensitivity uses the same common available-source universe.',
            'contrast_terms':'Channel mean L2 TF-IDF minus equally weighted mean of other channel means; compositional lexical contrast, not word prevalence or significance.',
            'matrix_precision':'Original-space cosines are rounded to Float32 before matrix-derived rankings and summaries, matching the lazy binary exports. NaN denotes unavailable source rows.',
            'fit_filtering':'Displayed filters reuse this frozen common fit. No browser refit or predictive holdout is implied.'},
        'channels':channel_rows,'documents':public_docs,'topics':topics,'matrices':matrix_refs,'channel_comparisons':channel_comparisons,
        'graph':{'lexical':graph_summary(L,ids),'semantic':graph_summary(M,ids)},'diagnostics':diagnostics,
        'origin_comparison':{'origins':sorted(set(strata)),'raw_origin_to_stratum':ORIGIN_STRATA,'semantic':origin_matrix,'pair_counts':origin_counts,
            'scope':'Text origin, creator, channel, length and publication date are confounded; this is descriptive stratification, not a causal contrast.'},
        'near_duplicate_review':{'threshold':.95,'pairs':near_duplicates,'automatically_merged':0,'scope':'High lexical similarity only flags review. Canonical source admission is owned by the source registry.'},
        'hypotheses':[
            {'id':'H1','question':'Do lexical and neural neighborhoods agree under one canonical frame?',
             'result':diagnostics['lexical_vs_semantic']['channel_macro_jaccard'],'metric':'Channel-macro top-five Jaccard','limitation':'Agreement between representations is not agreement between answers.'},
            {'id':'H2','question':'How stable are neural neighborhoods under a bounded text window?',
             'result':diagnostics['semantic_bounded_window']['channel_macro_jaccard'],'metric':'Channel-macro top-five Jaccard','limitation':'Windowing changes content and length together; no causal length effect.'},
            {'id':'H3','question':'Does source context remain enriched among neighbors after availability correction?',
             'result':diagnostics['channel_enrichment']['semantic']['macro_group_excess'],'metric':'Channel-macro excess same-channel neighbor fraction','limitation':'Channels, formats, creators and themes are confounded.'},
            {'id':'H4','question':'Do fixed-eight lexical factors remain stable across numerical seeds?',
             'result':[t.get('mean_matched_topic_term_cosine') for t in topic_runs[1:]],'metric':'Matched factor-term cosine','limitation':'Stability does not validate a topic ontology or justify eight factors.'}],
        'limitations':['Purposive retained English-source frame; missing historical captions and undiscovered uploads are outside the denominator.',
            'Canonical publications, text editions, recordings, creators, channels and claimed entities are distinct. Exact deduplication does not establish independent ideas.',
            'Machine transcripts have unverified word accuracy and speaker roles. Source selection and format can dominate similarities.',
            'Document pairs are dependent; no pairwise p-values, real-world probabilities, predictive forecasts or automatic agreement labels are reported.',
            'Name masking is incomplete. Frequent terms, repeated introductions, paraphrases, spelling and writing style remain possible explanations.',
            'Pretrained MiniLM is a reproducible lightweight baseline, not a new SOTA or trained model. Topics, embeddings and graphs describe text representations.'],
        'figures':[]}
    result['execution']={'full_content_wordpieces':encoding['content_wordpieces'],'full_chunks':encoding['chunks'],
        'full_original_encoding_seconds':encoding['original_encoding_seconds'],'full_cache_reused':encoding['reused_exact_cache'],
        'bounded_content_wordpieces':window_encoding['content_wordpieces'],'bounded_original_encoding_seconds':window_encoding['original_encoding_seconds'],
        'unmasked_bounded_content_wordpieces':unmasked_encoding['content_wordpieces'],'threads':1,
        'scope':'Measured runtime and input coverage, not a recognition/semantic accuracy benchmark or causal speedup estimate.'}
    creator_order=sorted(set(creators));creator_values,creator_counts=group_matrix(M,creators,creator_order)
    result['creator_comparison']={'creator_ids':creator_order,'semantic':creator_values,'pair_counts':creator_counts,
        'scope':'Equal canonical-document weights within named-creator contexts. Creator attribution does not identify every interview utterance; 13 guest-publisher contexts do not become 13 independent mediums.'}
    result['balancing']={}
    for name,matrix in [('lexical',L),('semantic',M)]:
        channel_values,_=group_matrix(matrix,groups,order);creator_values,_=group_matrix(matrix,creators,creator_order)
        channel_pairs=[channel_values[i][j] for i in range(len(order)) for j in range(i+1,len(order)) if channel_values[i][j] is not None]
        creator_pairs=[creator_values[i][j] for i in range(len(creator_order)) for j in range(i+1,len(creator_order)) if creator_values[i][j] is not None]
        document_pairs=[matrix[i,j] for i,j in zip(*upper) if groups[i]!=groups[j] and np.isfinite(matrix[i,j])]
        result['balancing'][name]={'publisher_context_pair_macro':mean(channel_pairs),'creator_context_pair_macro':mean(creator_pairs),
            'cross_publisher_document_pair_mean':mean(document_pairs),'publisher_context_pairs':len(channel_pairs),
            'creator_context_pairs':len(creator_pairs),'cross_publisher_document_pairs':len(document_pairs),
            'scope':'Different declared balancing units, not alternative estimates of an authenticated-medium population. Pairs remain dependent.'}
    aliases={old:i for i,r in enumerate(records) for old in [r['source_id'],*r.get('legacy_source_ids',[])]}
    planned=['tr-source-omna-mary','tr-source-omna-magdalene','tr-source-jeshua-mary-full','tr-source-jeshua-magdalene-full']
    control={'planned_legacy_sources':planned,'scope':'Four sources selected before these rankings: same printed label across creators versus different labels within creator. Descriptive source-style contrast, not entity authentication.'}
    if all(x in aliases for x in planned):
        a,b,c,d=[aliases[x] for x in planned];cross=[(a,c),(b,d)];within=[(a,b),(c,d)];trials=[]
        for name,matrix in [('lexical_full',L),('semantic_full',M),('lexical_bounded',LW),('semantic_bounded',MW)]:
            pairs=[{'left':ids[i],'right':ids[j],'kind':kind,'cosine':finite(matrix[i,j])}
                   for kind,rows in [('same_label_cross_creator',cross),('different_label_within_creator',within)] for i,j in rows]
            cross_mean=mean([matrix[i,j] for i,j in cross]);within_mean=mean([matrix[i,j] for i,j in within])
            trials.append({'representation':name,'pairs':pairs,'cross_creator_same_label_mean':cross_mean,
                'within_creator_other_label_mean':within_mean,
                'within_minus_cross':within_mean-cross_mean if cross_mean is not None and within_mean is not None else None})
        control.update(status='executed',canonical_sources=[ids[i] for i in (a,b,c,d)],trials=trials)
    else:control.update(status='source_join_unavailable',missing=[x for x in planned if x not in aliases])
    result['diagnostics']['shared_name_control']=control
    result['hypotheses'].append({'id':'H5','question':'Do same-name cross-creator messages outrank different-name within-creator messages in the four preselected Mary/Magdalene texts?',
        'result':[t['within_minus_cross'] for t in control.get('trials',[])],'metric':'Within-context minus cross-context mean cosine across full/bounded lexical/neural views',
        'limitation':'Two dependent pairs per side; source style, length and topic are confounded. Names are printed attributions, not authenticated beings.'})
    witness=RAM/'witness';witness.mkdir(exist_ok=True)
    np.savez(witness/'core-vectors.npz',source_ids=np.asarray(ids),semantic=S,equal=E,bounded_semantic=SW,unmasked_bounded_semantic=SU,
             topic_components=topic_model.components_,topic_weights=W,chunk_topic_weights=chunk_weights,
             lexical_xy=Lxy,semantic_xy=Mxy,idf=vectorizer.idf_,features=feature_names)
    np.savez(witness/'topic-seeds.npz',**topic_witness)
    from scipy.sparse import save_npz
    import pickle
    (witness/'vectorizer-private.pkl').write_bytes(pickle.dumps(vectorizer,protocol=5))
    save_npz(witness/'lexical.npz',X);save_npz(witness/'bounded-lexical.npz',XW);save_npz(witness/'chunk-lexical.npz',CX)
    save(witness/'locators-private.json',private_locators)
    save(witness/'execution-private.json',{'frame_path':str(frame_path),'frame_sha256':result['bindings']['frame_sha256'],
        'full_encoding':encoding,'bounded_encoding':window_encoding,'unmasked_bounded_encoding':unmasked_encoding,
        'source_ids':ids,'chunk_rows':chunk_rows,'elapsed_seconds':time.monotonic()-started})
    document_frequency=np.asarray((X>0).sum(axis=0)).ravel();channel_frequency=(means>0).sum(axis=0)
    name_components={word for phrase in phrases for word in words(phrase)};balanced_mean=means.mean(axis=0)
    eligible=[j for j,t in enumerate(feature_names) if ' ' not in t and t not in name_components and document_frequency[j]>=3 and channel_frequency[j]>=2]
    term_indices=sorted(eligible,key=lambda j:(-balanced_mean[j],feature_names[j]))[:24]
    selected_terms=[str(feature_names[j]) for j in term_indices]
    result['term_overlay']={'terms':selected_terms,'channel_ids':order,'matrix':means[:,term_indices].tolist(),
        'document_frequencies':[int(document_frequency[j]) for j in term_indices],
        'selection':'Top24 non-name unigrams by equal-publisher-context mean TF-IDF; document frequency≥3 and context frequency≥2. Exact name-component terms excluded; fixed alphabetical ties.',
        'units':'Mean L2-normalized document TF-IDF weight within each publisher context, not topic prevalence.'}
    from analyze_terms import build as build_terms
    print(json.dumps({'stage':'contextual_token_overlay','terms':len(selected_terms)}),flush=True)
    result['contextual_terms']=build_terms(docs,full,selected_terms,encoder,TOKEN,witness)
    figures(result,out)
    if sha(Path(__file__).read_bytes())!=code_sha:raise ValueError('Analysis code changed during execution')
    save(out/'analysis.json',result);(out/'executed-analyze.py').write_bytes(Path(__file__).read_bytes())
    allowlist=[ref(out/'analysis.json')]+[matrix_refs[k] for k in ('lexical','semantic')]+detail_refs+result['figures']
    save(out/'output-manifest.json',{'complete':True,'public_allowlist':allowlist})
    print(json.dumps({'coverage':result['coverage'],'seconds':time.monotonic()-started,'public_bytes':sum(x['bytes'] for x in allowlist)}),flush=True)


def figures(r,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    channels=r['channels'];labels=[c['name'] for c in channels]
    def finish(fig,stem,title,alt):
        for ext in ('png','svg','pdf'):
            path=out/(stem+'.'+ext);fig.savefig(path,dpi=125,bbox_inches='tight');r['figures'].append({**ref(path),'title':title,'alt':alt})
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,max(5,len(channels)*.3)));y=np.arange(len(channels))
    axes[0].barh(y,[c['documents'] for c in channels],color='#176d80');axes[0].set_yticks(y,labels,fontsize=8);axes[0].set_xlabel('Canonical text publications')
    axes[1].barh(y,[c['words']/1000 for c in channels],color='#ae5837');axes[1].set_yticks(y,labels,fontsize=8);axes[1].set_xlabel('Retained body words (thousands)')
    fig.suptitle('Unequal source coverage in the verified canonical frame');fig.tight_layout()
    finish(fig,'source-coverage','Canonical source coverage','Publication and word counts by publisher/channel context, not YouTube upload totals or verified speakers.')
    fig,ax=plt.subplots(figsize=(11,max(5,len(channels)*.3)));matrix=np.asarray([c['topic_weights'] for c in channels])
    im=ax.imshow(matrix,aspect='auto',cmap='viridis',vmin=0);ax.set_yticks(y,labels,fontsize=8)
    ax.set_xticks(range(8),[t['topic_id']+' '+t['label'] for t in r['topics']],rotation=45,ha='right',fontsize=8)
    fig.colorbar(im,ax=ax,label='Mean normalized NMF weight per publication');ax.set_title('Common lexical factors across source contexts');fig.tight_layout()
    finish(fig,'topic-source-mix','Source-context topic mixtures','Eight fixed exploratory NMF factors in one shared fit; mixtures are model weights, not observed belief prevalence.')
    fig,axes=plt.subplots(1,2,figsize=(13,6));colors=plt.get_cmap('tab20')
    for c,channel in enumerate(channels):
        selected=[d for d in r['documents'] if d['channel_id']==channel['channel_id']]
        for ax,kind in zip(axes,('lexical','semantic')):
            rows=[d[kind+'_xy'] for d in selected if d[kind+'_available']]
            ax.scatter([p['x'] for p in rows],[p['y'] for p in rows],s=12,alpha=.6,color=colors(c%20),label=channel['name'])
    for ax,kind in zip(axes,('lexical','semantic')):
        p=r['diagnostics']['projections'][kind];ax.set(title=kind.title()+f" · variance {sum(p['explained_variance']):.1%}",xlabel='Normalized display coordinate1',ylabel='Normalized display coordinate2')
    axes[1].legend(fontsize=6,loc='upper left',bbox_to_anchor=(1,1));fig.suptitle('Lossy document maps · use original-space matrices for comparisons');fig.tight_layout()
    finish(fig,'document-maps','Lexical and neural document maps','Separate lossy SVD/PCA coordinates colored by source context. They are not common latent axes or measures of answer agreement.')
    keys=['lexical_vs_semantic','lexical_bounded_window','semantic_bounded_window','lexical_name_mask','semantic_window_name_mask']
    fig,ax=plt.subplots(figsize=(10,5));values=[[x['jaccard'] for x in r['diagnostics'][k]['rows'] if x['jaccard'] is not None] for k in keys]
    ax.boxplot(values,tick_labels=['Lexical / neural','Lexical full / window','Neural full / window','Lexical name mask','Neural window mask'],showfliers=False)
    ax.set(ylim=(-.03,1.03),ylabel='Top-five neighbor-set Jaccard',title='Representation and sampling sensitivity · identical available-source subsets');ax.tick_params(axis='x',rotation=15);fig.tight_layout()
    finish(fig,'neighbor-stability','Neighbor stability under representation controls','Descriptive document-level Jaccard distributions; each comparison uses the same available source universe and does not measure retrieval accuracy.')
    overlay=r['term_overlay'];context=r['contextual_terms'];fig,axes=plt.subplots(1,2,figsize=(16,max(7,len(channels)*.3)))
    im=axes[0].imshow(overlay['matrix'],aspect='auto',cmap='viridis',vmin=0)
    axes[0].set_xticks(range(len(overlay['terms'])),overlay['terms'],rotation=60,ha='right',fontsize=7)
    axes[0].set_yticks(y,labels,fontsize=7);axes[0].set_title('Observed lexical weights by publisher context');fig.colorbar(im,ax=axes[0],label='Mean document TF-IDF weight',shrink=.65)
    rows=context['terms'];axes[1].scatter([x['x'] for x in rows],[x['y'] for x in rows],color='#176d80',s=26)
    axes[1].set(xlabel='Shared contextual-token PCA1',ylabel='Shared contextual-token PCA2',title='Exploratory target-token prototypes');axes[1].margins(.15)
    fig.suptitle('Two distinct term views: lexical weights and contextual hidden states')
    fig.tight_layout(rect=(0,.06,1,.96));fig.canvas.draw();renderer=fig.canvas.get_renderer();used=[]
    for row in rows:
        placed=False
        for radius in (8,16,24,36,50,70):
            for angle in (45,-45,135,-135,0,90,180,-90):
                dx=radius*np.cos(np.radians(angle));dy=radius*np.sin(np.radians(angle))
                text=axes[1].annotate(row['term'],(row['x'],row['y']),xytext=(dx,dy),textcoords='offset points',fontsize=8,ha='center',va='center',
                    bbox={'facecolor':'white','edgecolor':'none','alpha':.8,'pad':.3},arrowprops={'arrowstyle':'-','color':'#999','lw':.4} if radius>16 else None)
                box=text.get_window_extent(renderer).expanded(1.05,1.1)
                if not any(box.overlaps(old) for old in used):used.append(box);placed=True;break
                text.remove()
            if placed:break
    variance=sum(context['projection']['explained_variance']);trust=context['projection']['trustworthiness_at5']
    fig.text(.5,.015,f'Contextual map variance {variance:.1%}; trustworthiness@5 {trust:.3f}. Sentence-trained token states are not validated word senses or answer agreement.',ha='center',fontsize=8)
    finish(fig,'term-context-overlay','Lexical and contextual-token overlays','A source-context TF-IDF heatmap and separate bounded target-token PCA. They use different quantities; source sampling, spelling and ordinary language can dominate proximity.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frame','model','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--batch-size',type=int,default=8);a=p.parse_args();run(a.frame,a.model,a.output,a.batch_size)
