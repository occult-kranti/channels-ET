#!/usr/bin/env python3
"""Separate new publisher-message pilot. Never extends a frozen older model."""
import argparse,collections,datetime as dt,hashlib,importlib.util,json,re
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import NMF,TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score,adjusted_rand_score
spec=importlib.util.spec_from_file_location('joint',Path(__file__).with_name('analyze.py'));J=importlib.util.module_from_spec(spec);spec.loader.exec_module(J)
A=J.A

def load(paths):
    records=[];bindings=[];seen=set();seen_text=set()
    for path in paths:
        manifest,ref=J.bound(path);bindings.append(ref)
        if manifest.get('schema_version')!=1:raise ValueError('Version1manifest required')
        for r in manifest['records']:
            r=dict(r);r.setdefault('medium',r.get('medium_name',r['medium_id']));r.setdefault('boundary',r.get('body_boundary'));r.setdefault('text_origin',r.get('document_role'));r.setdefault('audio_alignment_verified',False)
            r['speaker_role']='publisher_printed_layout_response_attribution' if r.get('qa_artifact') else 'publisher_attributed_written_message'
            sid=r['source_id']
            if sid in seen:raise ValueError('Repeated source ID')
            seen.add(sid)
            if r.get('language')!='en' or not r.get('attribution_scope') or not r.get('comparison_label'):raise ValueError('English message and direct local attribution required')
            p=A.artifact(r['text_artifact'],private=True)
            if r['text_artifact']['sha256'] in seen_text:raise ValueError('Duplicate exact text requires an explicit alias disposition')
            seen_text.add(r['text_artifact']['sha256']);text=p.read_text(encoding='utf-8');words=len(text.split())
            if r.get('words') is not None and words!=r['words']:raise ValueError('Message words differ')
            if words<50:raise ValueError('Too little message body for this pilot')
            if r.get('html_artifact'):A.artifact(r['html_artifact'],private=True)
            if r.get('raw_artifact') and A.sha(Path(r['raw_artifact']['path']))!=r['raw_artifact']['sha256']:raise ValueError('Original source hash differs')
            records.append({'record':r,'text':text,'words':words})
    return sorted(records,key=lambda x:x['record']['source_id']),bindings

def study(paths,out,review):
    out=A.safe_path(out,private=True,exists=False)
    if out.exists():raise ValueError('Choose new run; prior outputs immutable')
    out.mkdir(parents=True,mode=0o700);code=A.sha(Path(__file__));(out/'executed-analyze-pilot.py').write_bytes(Path(__file__).read_bytes())
    if review:(out/'pilot-reading.json').write_bytes(review.read_bytes())
    docs,bindings=load(paths);mask=J.MASK|{'natalie','glasson','pamela','kribbe','sam','daniel','scranton','mary','magdalene','michael','metatron','jeshua','isis','archangel','quanyin','quan','yin','arcturian','arcturians','pleiadian','pleiadians','kryon','sasha','lyssa','royal','holt','andromedan','andromedans','ashanti'}
    tokenized=[[t for t in A.tokens(d['text']) if t not in mask and t not in A.FILLERS] for d in docs]
    vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=12000,stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}));X=vec.fit_transform(' '.join(t) for t in tokenized);cos=cosine_similarity(X)
    spans=[]
    for d in docs:
        tt=A.tokens(d['text']);start=max(0,(len(tt)-300)//2)
        if len(tt)<300:raise ValueError('300token control requires all admitted pilot messages')
        spans.append(' '.join(t for t in tt[start:start+300] if t not in mask and t not in A.FILLERS))
    window=cosine_similarity(vec.transform(spans));pairs=[]
    for i,a in enumerate(docs):
        for j in range(i+1,len(docs)):
            b=docs[j];ra,rb=a['record'],b['record'];same_medium=ra['medium_id']==rb['medium_id'];same_label=ra['comparison_label']==rb['comparison_label']
            pairs.append({'source':ra['source_id'],'target':rb['source_id'],'source_medium':ra['medium_id'],'target_medium':rb['medium_id'],'source_label':ra['comparison_label'],'target_label':rb['comparison_label'],'same_medium':same_medium,'same_comparison_label':same_label,'comparison_kind':'same_label_cross_medium' if same_label and not same_medium else ('different_label_same_medium' if same_medium and not same_label else 'other'),'cosine':float(cos[i,j]),'window_300_cosine':float(window[i,j]),'identity_equivalence':False,'comparison_level':'broad_civilization_label' if ra['comparison_label'] in {'pleiadian','arcturian','andromedan','sassani'} else 'named_label'})
    label_summaries=[]
    for label in sorted(set(p['source_label'] for p in pairs if p['comparison_kind']=='same_label_cross_medium')):
        pp=[p for p in pairs if p['comparison_kind']=='same_label_cross_medium' and p['source_label']==label]
        label_summaries.append({'comparison_label':label,'comparison_level':pp[0]['comparison_level'],'pairs':len(pp),'mean_cosine':float(np.mean([p['cosine'] for p in pp])),'mean_window_cosine':float(np.mean([p['window_300_cosine'] for p in pp]))})
    summaries=[]
    for kind in sorted({p['comparison_kind'] for p in pairs}):
        group=[p for p in pairs if p['comparison_kind']==kind];summaries.append({'kind':kind,'pairs':len(group),'mean_cosine':float(np.mean([p['cosine'] for p in group])),'mean_window_cosine':float(np.mean([p['window_300_cosine'] for p in group])),'inferential_test':None})
    k=min(3,len(docs)-1);fit=NMF(n_components=k,init='nndsvdar',random_state=11,max_iter=800);W=fit.fit_transform(X);shares=W/np.maximum(W.sum(axis=1,keepdims=True),1e-20);names=vec.get_feature_names_out();topicrows=[]
    for i,weights in enumerate(fit.components_):topicrows.append({'id':i+1,'terms':[str(names[j]) for j in weights.argsort()[-10:][::-1]],'scope':'Exploratory factor; not validated doctrine.'})
    models=[KMeans(n_clusters=k,n_init=10,random_state=seed).fit(X) for seed in [11,23,47]];svd=TruncatedSVD(n_components=2,random_state=11);xy=svd.fit_transform(X);labels=models[0].labels_;clusters={'k':k,'silhouette':float(silhouette_score(X,labels,metric='cosine')),'source_medium_ARI':float(adjusted_rand_score([d['record']['medium_id'] for d in docs],labels)),'seed_ARI_mean':float(np.mean([adjusted_rand_score(models[a].labels_,models[b].labels_) for a,b in [(0,1),(0,2),(1,2)]])),'selection':'k3 declared for a small exploratory display, not optimal or validated.','assignments':[{'source_id':d['record']['source_id'],'cluster':int(labels[i])+1,'x':float(xy[i,0]),'y':float(xy[i,1])} for i,d in enumerate(docs)]}
    publicdocs=[]
    for i,d in enumerate(docs):
        r=d['record'];publicdocs.append({k:r.get(k) for k in ['source_id','medium_id','medium','label_id','label','comparison_label','source_url','title','attribution_scope','text_origin','audio_alignment_verified','boundary','speaker_role','publisher_date']}|{'words':d['words'],'text_sha256':r['text_artifact']['sha256'],'topic_weights':shares[i].tolist()})
    reading={'status':'not_reviewed','comparisons':[]}
    if review:
        reading=json.loads(review.read_text());lookup={x['record']['source_id']:x for x in docs}
        for row in reading['sources']:
            if lookup[row['source_id']]['record']['text_artifact']['sha256']!=row['text_sha256']:raise ValueError('Manual reading source changed')
    r={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':code,'scope':'New purposive publisher-written-message pilot, separate from292accepted-source joint fit. Direct page-local named-speaker attribution, not physicalidentity or spokenaudio verification.','coverage':{'documents':len(docs),'words':sum(d['words'] for d in docs),'mediums':len(set(d['record']['medium_id'] for d in docs)),'comparison_labels':len(set(d['record']['comparison_label'] for d in docs))},'documents':publicdocs,'source_ids':[d['record']['source_id'] for d in docs],'matrix':cos.tolist(),'window_300_matrix':window.tolist(),'pairs':pairs,'pair_summary':summaries,'label_summary':label_summaries,'transformations':{'source_name_mask_tokens':sorted(mask),'exact_text_hashes_unique':len(docs),'min_df':1,'window_tokens':300,'idf_basis':'full pilot corpus, fixed for windows','documentary_QA_response_only_sources':[d['record']['source_id'] for d in docs if d['record'].get('qa_artifact')]} ,'topics':topicrows,'clusters':clusters,'reading':reading,'reading_binding':{'sha256':A.sha(review),'file':'pilot-reading.json'} if review else None,'limitations':['Small purposive feasibility frame; few messages per label, no census and no held-out labels or mediums.','Same named label is not an authenticated identity. Broad Pleiadian/Arcturian group labels do not equate councils or speakers.','Publisher style, selection, source genre, translation and date confound cross-medium comparisons. Single messages cannot characterize a personality.','Question marks in authored messages are often rhetorical; no questioner/response dialogue is invented.','No inferential significance, causal influence or physical origin probabilities; TF-IDF is lexical overlap.','These bodies exclude source navigation and comments by recorded extraction boundaries; audio alignment is unverified.'],'figures':[]}
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(18,10));short=[(d['record'].get('medium','').split()[0]+' · '+d['record']['comparison_label'].replace('_',' ')) for d in docs]
    for ax,m,title in zip(axes,[cos,window],['Complete message body','Centered300-token span']):
        im=ax.imshow(m,cmap='viridis',vmin=0,vmax=1);ax.set_xticks(range(len(docs)),range(1,len(docs)+1));ax.set_yticks(range(len(docs)),[str(i+1)+' '+s for i,s in enumerate(short)]);ax.set_title(title)
    fig.subplots_adjust(wspace=.9,left=.17,right=.88);cax=fig.add_axes([.92,.27,.012,.5]);fig.colorbar(im,cax=cax,label='TF-IDF cosine; diagonal self-similarity=1')
    for ext in ['svg','png','pdf']:
        p=out/('pilot-similarity.'+ext);fig.savefig(p,dpi=160);r['figures'].append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'title':'Named-message pilot: source style versus shared labels','alt':'Pairwise name-masked lexical cosine, full text versus fixed-IDF300token control. Named-label identity is not authenticated.'})
    plt.close(fig);A.write_json(out/'provenance-private.json',{'inputs':bindings,'records':[d['record'] for d in docs],'reading_review_sha256':A.sha(review) if review else None})
    if A.sha(Path(__file__))!=code:raise ValueError('Code changed while executing')
    A.write_json(out/'new-message-pilot.json',r);A.write_json(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'new-message-pilot.json','sha256':A.sha(out/'new-message-pilot.json') }]+r['figures']});print(json.dumps({'coverage':r['coverage'],'pair_summary':summaries,'sha256':A.sha(out/'new-message-pilot.json')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--review',type=Path);a=p.parse_args();study(a.manifest,a.output,a.review)
