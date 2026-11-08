#!/usr/bin/env python3
"""Compare fixed text editions in lexical and pinned neural representation spaces."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import time
import unicodedata

import numpy as np
from knowledge_sources import load_frame

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
FRAME_SHA = '95131882eaed23b9429d3beb6cdffcda3fa62b32569d36412cd013c206008aae'
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
PRIVATE = Path('/workspace/channels-et-private/knowledge-bank-2026-11')


def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def tokens(text):
    return [x.replace('’', "'").casefold() for x in TOKEN.findall(unicodedata.normalize('NFKC', text))]


def mask_text(text, phrases):
    result = unicodedata.normalize('NFKC', text)
    for phrase in sorted(set(phrases), key=lambda x: (-len(x), x.casefold())):
        pattern = r'(?<!\w)' + r'[\s\-]+'.join(re.escape(x) for x in phrase.split()) + r'(?!\w)'
        result = re.sub(pattern, ' ', result, flags=re.I)
    return result


def centered(text, count=300):
    text = unicodedata.normalize('NFKC', text)
    matches = list(TOKEN.finditer(text))
    if len(matches) < count: return None
    start = (len(matches)-count)//2
    return text[matches[start].start():matches[start+count-1].end()]


class FrozenMiniLM:
    """Pinned complete-chunk CPU encoder; model files verified, no disk cache."""
    def __init__(self, directory):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        directory = Path(directory)
        self.manifest = json.loads((directory/'manifest.json').read_text())
        if (self.manifest.get('model'), self.manifest.get('revision')) != (MODEL, REVISION):
            raise ValueError('Pinned MiniLM model required')
        for ref in self.manifest['files']:
            name = Path(ref['path'])
            if name.is_absolute() or '..' in name.parts: raise ValueError('Unsafe model path')
            raw = (directory/name).read_bytes()
            if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
                raise ValueError('Model artifact changed')
        options = ort.SessionOptions(); options.intra_op_num_threads=1; options.inter_op_num_threads=1
        self.session = ort.InferenceSession(str(directory/'onnx/model.onnx'), sess_options=options,
            providers=['CPUExecutionProvider'])
        self.tokenizer = Tokenizer.from_file(str(directory/'tokenizer.json'))
        self.tokenizer.no_padding(); self.tokenizer.no_truncation()
        if [self.tokenizer.token_to_id(t) for t in ('[PAD]','[CLS]','[SEP]')] != [0,101,102]:
            raise ValueError('Unexpected tokenizer special IDs')
        self.input_names = {x.name for x in self.session.get_inputs()}
        self.binding = {'model': MODEL, 'revision': REVISION,
            'model_manifest_sha256': sha(directory/'manifest.json'),
            'encoder_script_sha256': sha(Path(__file__)), 'onnxruntime': ort.__version__,
            'intra_op_threads': 1, 'inter_op_threads': 1, 'batch_size': 16,
            'chunk_content_wordpieces': 240, 'wordpiece_truncation': False,
            'token_pooling': 'Attention-mask mean including CLS/SEP, then chunk L2 normalization',
            'document_pooling': 'Content-wordpiece-weighted mean of normalized chunks, then document L2 normalization',
            'equal_chunk_sensitivity': True, 'training_or_weight_update': False,
            'cache': 'No disk cache; vectors retained in memory during execution'}

    def encode(self, records):
        if len({rid for rid,_ in records}) != len(records): raise ValueError('Duplicate record ID')
        inputs, owners, rows = [], [], []
        for index,(rid,text) in enumerate(records):
            ids = self.tokenizer.encode(text, add_special_tokens=False).ids
            chunks = [ids[i:i+240] for i in range(0,len(ids),240)]
            if not chunks: raise ValueError('Empty semantic input')
            rows.append({'id':rid,'lengths':[len(c) for c in chunks],'vectors':[]})
            for chunk in chunks:
                inputs.append([101]+chunk+[102]); owners.append(index)
        for start in range(0,len(inputs),16):
            batch = inputs[start:start+16]; width=max(map(len,batch))
            ids=np.zeros((len(batch),width),dtype=np.int64); mask=np.zeros_like(ids)
            for i,values in enumerate(batch): ids[i,:len(values)]=values; mask[i,:len(values)]=1
            data={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
            hidden=self.session.run(None,{k:v for k,v in data.items() if k in self.input_names})[0]
            vectors=(hidden*mask[:,:,None]).sum(axis=1)/mask.sum(axis=1)[:,None]
            vectors/=np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-12)
            for owner,vector in zip(owners[start:start+16],vectors): rows[owner]['vectors'].append(vector)
        result={}
        for row in rows:
            v=np.asarray(row['vectors']); weighted=np.average(v,axis=0,weights=row['lengths']); equal=v.mean(axis=0)
            weighted/=max(np.linalg.norm(weighted),1e-12); equal/=max(np.linalg.norm(equal),1e-12)
            result[row['id']] = (weighted,equal,{'content_wordpieces':sum(row['lengths']),
                'processed_content_wordpieces':sum(row['lengths']), 'chunks':len(row['lengths']),
                'truncated_content_wordpieces':0,'input_text_sha256':digest(dict(records)[row['id']].encode())})
        return result


def nearest(matrix, ids, k=5):
    return [[ids[j] for j in sorted((j for j in range(len(ids)) if i!=j),
        key=lambda j:(-float(matrix[i,j]),ids[j]))[:k]] for i in range(len(ids))]


def jaccard(a,b):
    return len(set(a)&set(b))/len(set(a)|set(b)) if set(a)|set(b) else None


def norm_coords(values):
    values=np.asarray(values,dtype=float); values=values-values.mean(axis=0)
    return values/max(float(np.sqrt(np.mean(np.sum(values**2,axis=1)))),1e-12)


def pair_kind(left,right):
    same_medium=left['medium_id']==right['medium_id']; same_label=left['comparison_label']==right['comparison_label']
    return ('same_medium' if same_medium else 'cross_medium')+('_same_comparison_label' if same_label else '_other_label')


def cluster_result(X, cosine, docs):
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    k=3; runs=[]; labels=[]
    for seed in (11,23,47):
        groups=KMeans(n_clusters=k,n_init=10,random_state=seed).fit_predict(X)
        labels.append(groups)
        runs.append({'seed':seed,'assignments':[{'source_id':d['source_id'],'cluster':int(c)+1} for d,c in zip(docs,groups)],
            'cosine_silhouette':float(silhouette_score(np.clip(1-cosine,0,2),groups,metric='precomputed')),
            'medium_adjusted_rand':float(adjusted_rand_score([d['medium_id'] for d in docs],groups)),
            'text_origin_adjusted_rand':float(adjusted_rand_score([d['text_origin'] for d in docs],groups)),
            'comparison_label_adjusted_rand':float(adjusted_rand_score([d['comparison_label'] for d in docs],groups))})
    return {'k':k,'selection':'Fixed exploratory display choice; not selected as optimal or validated doctrine count',
        'algorithm':'KMeans on L2-normalized document representations; n_init10', 'runs':runs,
        'seed_pair_adjusted_rand':[{'left':runs[i]['seed'],'right':runs[j]['seed'],
            'value':float(adjusted_rand_score(labels[i],labels[j]))} for i in range(3) for j in range(i+1,3)]}


def sanitize(record):
    return {'source_id':record['source_id'],'title':record['title'],'source_url':record['source_url'],
        'medium_id':record['medium_id'],'medium_name':record['medium'],'label':record['claimed_label'],
        'comparison_label':record['comparison_label'],'comparison_level':record['comparison_level'],
        'cohort':record['prior_frame'],'text_origin':record['document_kind'],'words':record['words'],
        'text_sha256':record['body_sha256'],'text_artifact_sha256':record['text_artifact']['sha256'],
        'attribution_scope':record['attribution_scope'],'speaker_role':record['speaker_role'],
        'speaker_identity_verified':False,'audio_alignment_verified':False,
        'publication_date':record['published_at']}


def study(frame_path, model_path, output):
    from scipy.linalg import orthogonal_procrustes
    from scipy.stats import spearmanr
    from sklearn.decomposition import PCA,TruncatedSVD,NMF
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.manifold import trustworthiness
    started=time.monotonic(); output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(PRIVATE): raise ValueError('Fresh private study path required')
    if sha(frame_path)!=FRAME_SHA: raise ValueError('Only the explicitly frozen25-edition frame is admitted')
    frame_docs,frame=load_frame(frame_path)
    if len({d['record']['source_id'] for d in frame_docs})!=len(frame_docs): raise ValueError('Duplicate source IDs')
    docs=[sanitize(d['record']) for d in frame_docs]; ids=[d['source_id'] for d in docs]
    phrases=sorted({x for d in docs for x in (d['medium_name'],d['label'])})
    texts=[d['text'] for d in frame_docs]; masked=[mask_text(t,phrases) for t in texts]
    spans=[centered(t) for t in texts]
    if any(t is None for t in spans): raise ValueError('This fixed frame requires complete300-token spans')
    windows=[mask_text(t,phrases) for t in spans]
    lexical_options={'tokenizer':str.split,'preprocessor':None,'token_pattern':None,'lowercase':False,
        'ngram_range':(1,2),'sublinear_tf':True,'min_df':1,'max_features':12000,
        'stop_words':sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'})}
    vec=TfidfVectorizer(**lexical_options); X=vec.fit_transform(' '.join(tokens(t)) for t in masked)
    LX=cosine_similarity(X); np.fill_diagonal(LX,1.0)
    XW=vec.transform([' '.join(tokens(t)) for t in windows]); LW=cosine_similarity(XW);np.fill_diagonal(LW,1.0)
    rawvec=TfidfVectorizer(**lexical_options); XR=rawvec.fit_transform(' '.join(tokens(t)) for t in texts)
    LR=cosine_similarity(XR);np.fill_diagonal(LR,1.0)
    encoder=FrozenMiniLM(model_path)
    print(json.dumps({'stage':'encoding','documents':len(ids),'model':MODEL}),flush=True)
    encoded=encoder.encode(list(zip(ids,masked)))
    encwin=encoder.encode([('window:'+sid,t) for sid,t in zip(ids,windows)])
    encraw=encoder.encode([('raw:'+sid,t) for sid,t in zip(ids,texts)])
    S=np.stack([encoded[sid][0] for sid in ids]); E=np.stack([encoded[sid][1] for sid in ids])
    SW=np.stack([encwin['window:'+sid][0] for sid in ids]); SR=np.stack([encraw['raw:'+sid][0] for sid in ids])
    SM,SE,SWM,SRM=[np.clip(cosine_similarity(v),-1,1) for v in (S,E,SW,SR)]
    for m in (SM,SE,SWM,SRM):np.fill_diagonal(m,1.0)
    lexical_neighbors,semantic_neighbors,window_neighbors,lexical_window_neighbors,raw_l_neighbors,raw_s_neighbors = [nearest(m,ids) for m in (LX,SM,SWM,LW,LR,SRM)]
    neighbor_rows=[{'source_id':sid,'lexical_ids':lexical_neighbors[i],'semantic_ids':semantic_neighbors[i],
        'jaccard':jaccard(lexical_neighbors[i],semantic_neighbors[i]),'window_ids':window_neighbors[i],
        'window_jaccard':jaccard(semantic_neighbors[i],window_neighbors[i]),
        'lexical_window_ids':lexical_window_neighbors[i],
        'lexical_window_jaccard':jaccard(lexical_neighbors[i],lexical_window_neighbors[i]),
        'unmasked_lexical_ids':raw_l_neighbors[i],'unmasked_semantic_ids':raw_s_neighbors[i],
        'name_mask_lexical_jaccard':jaccard(lexical_neighbors[i],raw_l_neighbors[i]),
        'name_mask_semantic_jaccard':jaccard(semantic_neighbors[i],raw_s_neighbors[i])} for i,sid in enumerate(ids)]
    pairs=[]
    for i,left in enumerate(docs):
        for j in range(i+1,len(docs)):
            right=docs[j]
            pairs.append({'source':left['source_id'],'target':right['source_id'],
                'same_medium':left['medium_id']==right['medium_id'],
                'same_label':left['comparison_label']==right['comparison_label'],
                'same_exact_printed_label':left['label'].casefold()==right['label'].casefold(),
                'kind':pair_kind(left,right),'comparison_level':left['comparison_level'] if left['comparison_label']==right['comparison_label'] else 'different_comparison_labels',
                'lexical_cosine':float(LX[i,j]),'semantic_cosine':float(SM[i,j]),
                'window_lexical_cosine':float(LW[i,j]),'window_semantic_cosine':float(SWM[i,j]),
                'equal_chunk_cosine':float(SE[i,j]),'unmasked_lexical_cosine':float(LR[i,j]),
                'unmasked_semantic_cosine':float(SRM[i,j])})
    pair_summary=[]
    for kind in sorted({p['kind'] for p in pairs}):
        chosen=[p for p in pairs if p['kind']==kind]
        pair_summary.append({'kind':kind,'pairs':len(chosen),**{name:float(np.mean([p[name] for p in chosen]))
            for name in ('lexical_cosine','semantic_cosine','window_lexical_cosine','window_semantic_cosine')},
            'inferential_test':None,'scope':'Dependent descriptive pair mean; broadlabels and namedpersonalities are not equivalent identity claims'})
    svd=TruncatedSVD(n_components=2,random_state=11); lc=norm_coords(svd.fit_transform(X))
    pca=PCA(n_components=2,svd_solver='full'); sc=norm_coords(pca.fit_transform(S))
    rotation,_=orthogonal_procrustes(sc,lc); aligned=sc@rotation
    coords=lambda arr:[{'source_id':sid,'x':float(v[0]),'y':float(v[1])} for sid,v in zip(ids,arr)]
    projection={'lexical':coords(lc),'semantic':coords(sc),'semantic_aligned':coords(aligned),
        'method':'Lexical uncentered TruncatedSVD2 and neural centered PCA2, independently fitted. Coordinates centered and scaled to RMSradius1.',
        'alignment':'Orthogonal Procrustes rotation/reflection of the displayed neural2D points toward lexical2D points. Display orientation only, not alignment of latent meanings.',
        'variance':{'lexical_svd_explained':svd.explained_variance_ratio_.tolist(),'semantic_pca_explained':pca.explained_variance_ratio_.tolist()},
        'trustworthiness_k5':{'lexical':float(trustworthiness(np.clip(1-LX,0,2),lc,n_neighbors=5,metric='precomputed')),
            'semantic':float(trustworthiness(np.clip(1-SM,0,2),sc,n_neighbors=5,metric='precomputed'))},
        'alignment_rms_residual':float(np.sqrt(np.mean(np.sum((aligned-lc)**2,axis=1)))),
        'scope':'2Dpositions are lossy visualization coordinates. Use fullspacecosines for retrieval; no belief, historical, or physical geometry is inferred.'}
    groups=sorted({d['medium_id'] for d in docs}); group_names={d['medium_id']:d['medium_name'] for d in docs}
    means=np.stack([np.asarray(X[[i for i,d in enumerate(docs) if d['medium_id']==g]].mean(axis=0)).ravel() for g in groups])
    terms=vec.get_feature_names_out(); contrast=means/(means.mean(axis=0)+1e-9)
    chosen=[]
    for row in means:
        for j in np.argsort(row)[-6:][::-1]:
            if int(j) not in chosen:chosen.append(int(j))
    chosen=chosen[:30]
    term_overlay={'terms':[str(terms[j]) for j in chosen],
        'groups':[{'id':g,'label':group_names[g],'documents':sum(d['medium_id']==g for d in docs)} for g in groups],
        'matrix':means[:,chosen].tolist(),'relative_to_unweighted_group_mean':contrast[:,chosen].tolist(),
        'selection':'Union of top6meanTFIDFfeatures per medium in alphabeticmediumID order, capped30; displayeddescriptively, nottestedbiomarkers.',
        'scope':'Mean L2documentTFIDF weights per source context. These are lexicalterm vectors across documents, not neural word embeddings or evidence of entity identity.'}
    nmf=NMF(n_components=3,init='nndsvdar',max_iter=800,random_state=11); W=nmf.fit_transform(X)
    W=W/np.maximum(W.sum(axis=1,keepdims=True),1e-12)
    topics={'k':3,'selection':'Fixed exploratory display choice, notvalidatedtopiccount','iterations':int(nmf.n_iter_),
        'components':[{'id':i+1,'terms':[str(terms[j]) for j in c.argsort()[-12:][::-1]]} for i,c in enumerate(nmf.components_)],
        'weights':[{'source_id':sid,'weights':W[i].tolist()} for i,sid in enumerate(ids)]}
    clusters={'lexical':cluster_result(X,LX,docs),'semantic':cluster_result(S,SM,docs)}
    controls=[('positive','Contact will happen this year.'),('negated','Contact will not happen this year.'),
        ('paraphrase','An encounter is going to take place during this year.'),('conditional','Contact may happen this year if conditions change.'),
        ('unrelated','The wooden table stands beside the kitchen window.')]
    cv=encoder.encode(controls); cmat=cosine_similarity(np.stack([cv[x[0]][0] for x in controls]))
    synthetic={'synthetic_fixture':True,'included_in_corpus_counts':False,
        'scope':'Constructed stress cases, not observed channeling passages, notanaccuracybenchmark. Highcosine cancoexist withoppositepolarity orconditionalmeaning.',
        'statements':[{'id':rid,'text':text} for rid,text in controls], 'semantic_matrix':cmat.tolist(),
        'pairs':[{'left':'positive','right':rid,'intended_relation':relation,'semantic_cosine':float(cmat[0,j])} for j,rid,relation in
            [(1,'negated','explicit_negation'),(2,'paraphrase','approximate_paraphrase'),(3,'conditional','condition_changes_scope'),(4,'unrelated','unrelated_control')]]}
    upper=np.triu_indices(len(ids),1)
    sensitivity={'pair_rank_spearman_lexical_vs_semantic':float(spearmanr(LX[upper],SM[upper]).statistic),
        'mean_neighbor_jaccard':float(np.mean([x['jaccard'] for x in neighbor_rows])),
        'mean_semantic_window_jaccard':float(np.mean([x['window_jaccard'] for x in neighbor_rows])),
        'mean_lexical_window_jaccard':float(np.mean([x['lexical_window_jaccard'] for x in neighbor_rows])),
        'mean_name_mask_lexical_jaccard':float(np.mean([x['name_mask_lexical_jaccard'] for x in neighbor_rows])),
        'mean_name_mask_semantic_jaccard':float(np.mean([x['name_mask_semantic_jaccard'] for x in neighbor_rows])),
        'max_equal_vs_weighted_pair_change':float(np.abs(SE[upper]-SM[upper]).max()),
        'inferential_p_values':None}
    result={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256':sha(Path(__file__)),'source_loader_sha256':sha(Path(__file__).with_name('knowledge_sources.py')),
        'scope':'Separate fixed25-edition knowledge-bank comparison; earliercorpora/weights unchanged. Similarity describes representation-dependent language proximity, never answer agreement.',
        'input_bindings':[{'kind':'frozen_source_frame','sha256':sha(frame_path),'bytes':Path(frame_path).stat().st_size}],
        'totals':{'candidate_documents':len(docs)+len(frame['excluded_aliases']),'selected_documents':len(docs),
            'words':sum(d['words'] for d in docs),'mediums':len(groups),'labels':len({d['comparison_label'] for d in docs}),
            'exact_printed_labels':len({d['label'] for d in docs}),'excluded_aliases':len(frame['excluded_aliases']),
            'new_source_downloads':0,'new_model_training':False},'documents':docs,'excluded_aliases':frame['excluded_aliases'],
        'transformations':{'exact_name_phrases':phrases,'negation_preserved':True,'window_tokens_before_mask':300,
            'lexical':'Unicodeletter/apostrophetokens; unigram/bigram;sublinearTF;smoothedIDF;L2;min_df1;max12000;Englishstoplistretainsno/not/nor/never',
            'semantic':'Exactsamephrase-mask; modeltokenizer retainsfunctionwords andallnonoverlapping240wordpiecechunks'},
        'lexical':{'source_ids':ids,'matrix':LX.tolist(),'window_300_matrix':LW.tolist(),'unmasked_matrix':LR.tolist(),'features':X.shape[1],
            'top_terms':[{'source_id':sid,'terms':[str(terms[j]) for j in X[i].toarray().ravel().argsort()[-12:][::-1]]} for i,sid in enumerate(ids)]},
        'semantic':{'source_ids':ids,'matrix':SM.tolist(),'equal_chunk_matrix':SE.tolist(),'window_300_matrix':SWM.tolist(),
            'unmasked_matrix':SRM.tolist(),'model':encoder.binding,
            'coverage':[{'source_id':sid,**encoded[sid][2]} for sid in ids],
            'window_coverage':[{'source_id':sid,**encwin['window:'+sid][2]} for sid in ids]},
        'pairs':pairs,'pair_summary':pair_summary,'neighbors':{'k':5,'rows':neighbor_rows},'sensitivity':sensitivity,
        'projections':projection,'term_overlay':term_overlay,'topics':topics,'clusters':clusters,'synthetic_controls':synthetic,
        'hypotheses':[{'id':'H1','question':'Does language proximity track medium more than shared comparison labels?',
            'status':'exploratory_descriptive','operationalization':'Inspect dependent pair means and cluster adjustedRand withmedium/comparisonlabels; noidentifiedcausalcontrast.',
            'result_reference':'pair_summary;clusters','limitation':'Unequal6mediumframe, singlemediumforseverallabels, mixedwritten/ASRformats anddates.'},
            {'id':'H2','question':'Do lexical and neural representations retrieve the same neighboring source editions?',
            'status':'executed_sensitivity','operationalization':'Top5Jaccard andall300pairSpearman withfixedsourceIDs.',
            'result_reference':'neighbors;sensitivity','limitation':'Neighboragreement ismodelconsistency, notansweraccuracy.'},
            {'id':'H3','question':'Do length, identity wording and chunk pooling change the neighborhood?',
            'status':'executed_sensitivity','operationalization':'Wholetextversuscentered300tokens;maskedversusunmasked;weightedversusequalchunkmeans.',
            'result_reference':'sensitivity','limitation':'Centeredspans arenotrandomorrepresentative excerpts; nocausal isolationoflength fromcontent.'},
            {'id':'H4','question':'Can a high neural similarity coexist with negation or conditional scope?',
            'status':'executed_synthetic_stress_case','operationalization':'Fiveconstructedstatements; separatefrom25observedsources.',
            'result_reference':'synthetic_controls','limitation':'Illustrativecontrol only, notmeasured contradiction-detectionaccuracy.'}],
        'limitations':['Purposive English accessible-source editions, not a representative sample of religions, all channels or authenticated beings.',
            'All25text editions reuse previously retained material; overlapping older frame counts cannot be added as new observations.',
            'Four ASRs have unknown utterance roles and unmeasured recognition accuracy. Full mixedinterview text is not pureCouncil speech.',
            'Written and machine-text formats, medium, date, length and shared vocabulary are confounded.',
            'Pair observations are dependent; descriptive means and exploratory clusters are not statistical significance or probabilities.',
            'Broadcivilization comparisons and identical printedpersonality names are different sourceclaims; neither verifies identity or independent origin.',
            'PinnedMiniLM is a lightweight reproducible baseline, not a currentSOTA claim. No newweights or neuralwordembeddings aretrained.',
            'Cosines, coordinates and nearestneighbors are not commonanswers or contradictions; source-reading questions/cards supply that separate layer.',
            'Constructedcontrol statements are explicitly synthetic and excluded from corpus/reading denominators.'],
        'runtime':{'wall_seconds':time.monotonic()-started,'cpu_threads':1,'packages':{p:importlib.metadata.version(p) for p in ('numpy','scikit-learn','onnxruntime','tokenizers')}},'figures':[]}
    output.mkdir(parents=True,mode=0o700)
    (output/'executed-analyze.py').write_bytes(Path(__file__).read_bytes())
    (output/'source-frame-private.json').write_bytes(Path(frame_path).read_bytes())
    write(output/'provenance-private.json',{'frame_path':str(frame_path),'frame_sha256':sha(frame_path),
        'model_path':str(model_path),'model_manifest_sha256':sha(Path(model_path)/'manifest.json')})
    make_figures(result,output)
    write(output/'analysis.json',result)
    write(output/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'analysis.json','sha256':sha(output/'analysis.json'),
        'bytes':(output/'analysis.json').stat().st_size}]+result['figures']})
    print(json.dumps({'totals':result['totals'],'sensitivity':sensitivity,'output':str(output),'sha256':sha(output/'analysis.json')}),flush=True)
    return result


def make_figures(r,out):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups=sorted({d['medium_id'] for d in r['documents']}); palette=['#176d80','#ae5837','#6555a5','#438b68','#a5781d','#ae4f7a']
    colors={g:palette[i%len(palette)] for i,g in enumerate(groups)}; names={d['medium_id']:d['medium_name'] for d in r['documents']}
    def save(fig,stem,title,alt):
        for ext in ('png','svg','pdf'):
            p=out/(stem+'.'+ext);fig.savefig(p,dpi=160,bbox_inches='tight')
            r['figures'].append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'title':title,'alt':alt})
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,key,title in zip(axes,['lexical','semantic_aligned'],['Lexical SVD (2D)','Neural PCA (2D), display orientation aligned']):
        points={d['source_id']:d for d in r['projections'][key]}
        for g in groups:
            ds=[d for d in r['documents'] if d['medium_id']==g]
            ax.scatter([points[d['source_id']]['x'] for d in ds],[points[d['source_id']]['y'] for d in ds],s=45,color=colors[g],label=names[g])
        for i,d in enumerate(r['documents']):
            p=points[d['source_id']];ax.annotate(str(i+1),(p['x'],p['y']),xytext=(3,3),textcoords='offset points',fontsize=7)
        ax.set_title(title);ax.set_xlabel('Normalized display coordinate1');ax.set_ylabel('Normalized display coordinate2');ax.set_aspect('equal',adjustable='datalim')
    axes[1].legend(fontsize=8,loc='upper left',bbox_to_anchor=(1,1));fig.suptitle('25 text editions across two representation spaces; numbers follow JSON source order')
    fig.text(.5,-.02,'Rotation/reflection aligns display orientation only. Projections are lossy; full-space similarity is not agreement.',ha='center',fontsize=9)
    fig.tight_layout();save(fig,'representation-maps','Lexical and neural source-context maps','Two separately fitted lossy2Dmaps, same25sourceIDs; neural display rotated/reflected toward lexicalmap. Colorsidentify6medium contexts, notverifiedentities.')
    fig,ax=plt.subplots(figsize=(8,6))
    for flag,color,label in [(True,'#176d80','Same medium'),(False,'#ae5837','Different medium')]:
        p=[p for p in r['pairs'] if p['same_medium']==flag]
        ax.scatter([x['lexical_cosine'] for x in p],[x['semantic_cosine'] for x in p],s=24,alpha=.6,c=color,label=f'{label} ({len(p)} dependent pairs)')
    ax.set(xlim=(0,1),ylim=(-.05,1.05),xlabel='Whole-text TF-IDF cosine',ylabel='Whole-text pinned MiniLM cosine',title='Representation-dependent language proximity');ax.legend(fontsize=9);ax.grid(alpha=.12)
    save(fig,'lexical-neural-pairs','Lexical versus neural pair similarities','All300unordered source-edition pairs; fixedcosine scales; colorindicates sourcecontext. Highvalues arenotcommonanswers orsourceindependence.')
    fig,ax=plt.subplots(figsize=(12,5));x=np.arange(len(r['documents']));rows=r['neighbors']['rows']
    ax.plot(x,[v['jaccard'] for v in rows],'o-',label='Lexical ↔ neural',color='#176d80')
    ax.plot(x,[v['window_jaccard'] for v in rows],'s-',label='Neural whole ↔ centered300tokens',color='#ae5837')
    ax.plot(x,[v['name_mask_semantic_jaccard'] for v in rows],'^-',label='Neural masked ↔ unmasked',color='#6555a5')
    ax.set_xticks(x,[str(i+1) for i in x]);ax.set(ylim=(-.05,1.05),xlabel='Source edition number, JSON source order',ylabel='Top5neighbor-set Jaccard',title='Retrieval neighborhoods change with representation and text selection');ax.legend(fontsize=9);ax.grid(alpha=.15)
    save(fig,'neighbor-stability','Neighbor stability across representation choices','Per-source top5Jaccard acrosslexical/neural,full/span andname-maskcontrols; setoverlap ismodelstability, notanswerretrievalaccuracy.')
    t=r['term_overlay'];fig,ax=plt.subplots(figsize=(15,5));im=ax.imshow(t['matrix'],aspect='auto',cmap='viridis',vmin=0)
    ax.set_xticks(range(len(t['terms'])),t['terms'],rotation=60,ha='right');ax.set_yticks(range(len(t['groups'])),[g['label']+' (n='+str(g['documents'])+')' for g in t['groups']]);ax.set_title('Source-context overlay of observed lexical features');fig.colorbar(im,ax=ax,label='Mean L2documentTF-IDFweight');fig.tight_layout()
    save(fig,'term-source-overlay','Lexical features across source contexts','Selectedobserved unigram/bigram features; meanTFIDF permedium. Notneuralwordembeddings, uniqueentityvocabulary orvalidatedbelief prevalence.')
    fig,axes=plt.subplots(1,2,figsize=(12,5));summary=r['pair_summary'];x=np.arange(len(summary))
    for j,(key,title) in enumerate([('lexical_cosine','TF-IDF'),('semantic_cosine','MiniLM')]):
        axes[j].bar(x-.18,[s[key] for s in summary],.36,label='Whole text',color='#176d80')
        w='window_lexical_cosine' if j==0 else 'window_semantic_cosine'
        axes[j].bar(x+.18,[s[w] for s in summary],.36,label='Centered300tokens',color='#ae5837')
        axes[j].set_xticks(x,[s['kind'].replace('_',' ')+'\n'+str(s['pairs'])+' pairs' for s in summary],rotation=20,ha='right',fontsize=8)
        axes[j].set_title(title);axes[j].set_ylim(0,1);axes[j].set_ylabel('Descriptive mean cosine');axes[j].legend(fontsize=8)
    fig.suptitle('Source context, printed comparison labels and length sensitivity');fig.tight_layout()
    save(fig,'source-label-contrast','Source versus comparison-label contrasts','Dependent pairmeans onfixed25editions. Broadcivilizationgroups andnamedlabels aredistinct; format,medium,dateandlength remainconfounded. No inferentialconfidenceintervals.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frame',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();study(args.frame,args.model,args.output)
