#!/usr/bin/env python3
"""Bounded contextual token-state exploration; separate from the accepted document fit."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.manifold import trustworthiness
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from analyze import FrozenMiniLM, TOKEN, tokens
from asr_sensitivity import BASELINE_SHA, FRAME_SHA, PRIVATE
from knowledge_sources import load_frame


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def unit(v):return v/max(float(np.linalg.norm(v)),1e-12)


def positioned_mask(text,phrases):
    """Preserve original normalized character coordinates while removing exact names."""
    for phrase in sorted(set(phrases),key=lambda x:(-len(x),x.casefold())):
        pattern=r'(?<!\w)'+r'[\s\-]+'.join(re.escape(w) for w in phrase.split())+r'(?!\w)'
        text=re.sub(pattern,lambda m:' '*len(m.group()),text,flags=re.I)
    return text


def occurrence_indices(count):
    if count<1:return []
    if count==1:return [0]
    return [(count-1)//3,(2*(count-1)+2)//3]


def target_window(encoding,start,end,radius=24):
    hits=[i for i,(a,b) in enumerate(encoding.offsets) if b>start and a<end]
    if not hits or hits!=list(range(hits[0],hits[-1]+1)):
        raise ValueError('Target term has no contiguous wordpiece support')
    lower=max(0,hits[0]-radius);upper=min(len(encoding.ids),hits[-1]+1+radius)
    return lower,upper,hits[0]-lower+1,hits[-1]-lower+2


def study(frame_path,baseline_path,model_path,out):
    code_sha=digest(Path(__file__).read_bytes())
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(PRIVATE):raise ValueError('Fresh private output required')
    if digest(Path(frame_path).read_bytes())!=FRAME_SHA or digest(Path(baseline_path).read_bytes())!=BASELINE_SHA:
        raise ValueError('Frozen frame and accepted analysis required')
    docs,_=load_frame(frame_path);baseline=json.loads(Path(baseline_path).read_text())
    phrases=baseline['transformations']['exact_name_phrases']
    masked=[positioned_mask(d['text'],phrases) for d in docs]
    vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,
        ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=12000,
        stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}))
    X=vec.fit_transform(' '.join(tokens(t)) for t in masked)
    if not np.allclose(cosine_similarity(X),baseline['lexical']['matrix'],atol=1e-10,rtol=0):
        raise ValueError('Baseline lexical fit differs')
    features=vec.get_feature_names_out();df=np.asarray((X>0).sum(axis=0)).ravel();means=np.asarray(X.mean(axis=0)).ravel()
    excluded={t for phrase in phrases for t in tokens(phrase)}
    eligible=[i for i,t in enumerate(features) if ' ' not in t and t not in excluded and df[i]>=3]
    chosen=sorted(eligible,key=lambda i:(-means[i],features[i]))[:24]
    if len(chosen)!=24:raise ValueError('Insufficient fixed-rule term coverage')
    terms=[str(features[i]) for i in chosen];encoder=FrozenMiniLM(model_path)
    if encoder.binding['model_manifest_sha256']!=baseline['semantic']['model']['model_manifest_sha256']:
        raise ValueError('Pinned model differs')
    windows=[];locators=[];pairs=[]
    for d,text in zip(docs,masked):
        sid=d['record']['source_id'];encoded=encoder.tokenizer.encode(text,add_special_tokens=False)
        matches={term:[] for term in terms}
        for match in TOKEN.finditer(text):
            token=match.group().replace('’',"'").casefold()
            if token in matches:matches[token].append(match)
        for term in terms:
            occurrences=matches[term]
            if not occurrences:continue
            pair={'term':term,'source_id':sid,'medium_id':d['record']['medium_id'],
                  'occurrences_available':len(occurrences),'sample_indices':[]}
            for occurrence in occurrence_indices(len(occurrences)):
                match=occurrences[occurrence];lo,hi,target_lo,target_hi=target_window(encoded,match.start(),match.end())
                index=len(windows);pair['sample_indices'].append(index)
                windows.append(([101]+encoded.ids[lo:hi]+[102],target_lo,target_hi))
                start=encoded.offsets[lo][0];end=encoded.offsets[hi-1][1]
                locators.append({'sample_index':index,'term':term,'source_id':sid,
                    'source_body_sha256':d['record']['body_sha256'],'occurrence_index':occurrence,
                    'term_char_start':match.start(),'term_char_end':match.end(),
                    'term_text_sha256':digest(d['text'][match.start():match.end()].encode()),
                    'context_char_start':start,'context_char_end':end,
                    'original_context_sha256':digest(d['text'][start:end].encode()),
                    'masked_context_sha256':digest(text[start:end].encode()),
                    'wordpiece_start':lo,'wordpiece_end':hi,
                    'input_ids_sha256':digest(np.asarray(windows[-1][0],dtype='<i8').tobytes()),
                    'target_input_start':target_lo,'target_input_end':target_hi})
            pairs.append(pair)
    samples=[]
    for offset in range(0,len(windows),16):
        batch=windows[offset:offset+16];width=max(len(w[0]) for w in batch)
        ids=np.zeros((len(batch),width),dtype=np.int64);attention=np.zeros_like(ids)
        for i,(values,_,_) in enumerate(batch):ids[i,:len(values)]=values;attention[i,:len(values)]=1
        inputs={'input_ids':ids,'attention_mask':attention,'token_type_ids':np.zeros_like(ids)}
        hidden=encoder.session.run(None,{k:v for k,v in inputs.items() if k in encoder.input_names})[0]
        for i,(_,start,end) in enumerate(batch):samples.append(unit(hidden[i,start:end].astype(float).mean(axis=0)))
    vectors=np.stack([unit(np.mean([samples[i] for i in p['sample_indices']],axis=0)) for p in pairs])
    centroids=np.stack([unit(vectors[[i for i,p in enumerate(pairs) if p['term']==t]].mean(axis=0)) for t in terms])
    matrix=cosine_similarity(centroids);np.fill_diagonal(matrix,1)
    pca=PCA(n_components=2,svd_solver='full');coords=pca.fit_transform(centroids)
    center=coords.mean(axis=0);radius=float(np.sqrt(np.mean(np.sum((coords-center)**2,axis=1))))
    coords=(coords-center)/radius;context_coords=(pca.transform(vectors)-center)/radius
    runs=[];labels=[]
    for seed in (11,23,47):
        group=KMeans(n_clusters=3,n_init=10,random_state=seed).fit_predict(centroids);labels.append(group)
        runs.append({'seed':seed,'assignments':[{'term':t,'cluster':int(c)+1} for t,c in zip(terms,group)],
            'cosine_silhouette':float(silhouette_score(np.clip(1-matrix,0,2),group,metric='precomputed'))})
    out.mkdir(parents=True,mode=0o700)
    private={'source_frame_sha256':FRAME_SHA,'sampling':'Two occurrences at floor first-third and ceiling second-third ordinal indices; one if only one occurrence.',
             'locators':locators,'source_term_pairs':pairs}
    save(out/'locators-private.json',private)
    vector_path=Path('/dev/shm/channels-et-knowledge-2026-11/methods')/('contextual-terms-'+out.name+'-vectors.npz')
    vector_path.parent.mkdir(parents=True,exist_ok=True)
    if vector_path.exists():raise ValueError('Fresh private vector witness required')
    np.savez(vector_path,terms=np.asarray(terms),source_vectors=vectors,term_vectors=centroids,
             sample_vectors=np.asarray(samples),pca_components=pca.components_,pca_mean=pca.mean_)
    save(out/'vectors-private.json',{'path':str(vector_path),'bytes':vector_path.stat().st_size,
        'sha256':digest(vector_path.read_bytes()),'source_vectors_shape':list(vectors.shape),
        'scope':'Executed representation witness; arithmetic verification is not independent neural re-encoding.'})
    result={'schema_version':1,'status':'executed_contextual_token_exploration',
        'bindings':{'frame_sha256':FRAME_SHA,'baseline_analysis_sha256':BASELINE_SHA,
                    'model_manifest_sha256':encoder.binding['model_manifest_sha256'],'script_sha256':code_sha,
                    'private_locators_sha256':digest((out/'locators-private.json').read_bytes())},
        'coverage':{'source_editions':25,'terms':24,'source_term_pairs':len(pairs),'sampled_occurrences':len(samples),
                    'available_occurrences':sum(p['occurrences_available'] for p in pairs),'eligible_terms':len(eligible)},
        'selection':{'criterion':'Top 24 unigrams by mean baseline L2 TF-IDF weight, document frequency at least 3, excluding every component of exact medium/printed-label names; ties lexical.',
                     'context_sampling':private['sampling'],'context_radius_wordpieces':24,
                     'pooling':'Mean final-layer target subword states, L2 normalization; equal occurrence mean within each source, normalize; equal source mean for each term, normalize.'},
        'terms':[{'term':t,'document_frequency':int(df[index]),'mean_tfidf':float(means[index]),
                  'x':float(x),'y':float(y)} for t,index,(x,y) in zip(terms,chosen,coords)],
        'source_contexts':[{k:v for k,v in p.items() if k!='sample_indices'}|{
                    'sampled_occurrences':len(p['sample_indices']),'x':float(x),'y':float(y),
                    'cosine_to_term_centroid':float(np.dot(vectors[i],centroids[terms.index(p['term'])]))}
                    for i,(p,(x,y)) in enumerate(zip(pairs,context_coords))],
        'term_cosine_matrix':matrix.tolist(),
        'projection':{'method':'PCA fitted to 24 normalized term centroids; the exact same transform projects all source-term means. Both use one centering and RMS-radius scale.',
                      'coordinate_scope':'Shared within this contextual-token experiment only; not aligned to document maps or independent latent dimensions.',
                      'explained_variance':pca.explained_variance_ratio_.tolist(),
                      'trustworthiness':float(trustworthiness(np.clip(1-matrix,0,2),coords,n_neighbors=5,metric='precomputed')),
                      'trustworthiness_k':5,'overlay_terms':terms[:4]},
        'clusters':{'k':3,'selection':'Fixed exploratory k=3; not an estimated number of meanings or civilizations.',
                    'runs':runs,'seed_pair_adjusted_rand':[{'left':runs[i]['seed'],'right':runs[j]['seed'],
                    'value':float(adjusted_rand_score(labels[i],labels[j]))} for i in range(3) for j in range(i+1,3)]},
        'limitations':['MiniLM is sentence-embedding trained. Target-token hidden states are an exploratory representation, not validated word-sense embeddings.',
          'Selected terms favor frequent shared English vocabulary. Sparse terms, untranslated material and nonselected concepts are outside this display.',
          'At most two ordinally sampled occurrences cannot represent every use, sense or claim. Token states still encode spelling, local context and source style.',
          'Source means receive equal weight, but sources and mediums are not equally represented for every term. Names are masked only by the documented exact phrases; other variants can remain.',
          'PCA is lossy and fixed-k clusters are exploratory. Spatial proximity and token cosine do not imply common answers, agreement, contradiction, verified speakers or entities.'],
        'figures':[]}
    figure(result,out)
    if digest(Path(__file__).read_bytes())!=code_sha:raise ValueError('Code changed during execution')
    save(out/'contextual-terms.json',result)
    (out/'executed-contextual-terms.py').write_bytes(Path(__file__).read_bytes())
    save(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'contextual-terms.json',
        'sha256':digest((out/'contextual-terms.json').read_bytes()),'bytes':(out/'contextual-terms.json').stat().st_size}]+result['figures']})
    print(json.dumps({'coverage':result['coverage'],'projection':result['projection'],'terms':terms}))


def figure(r,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,6));terms=r['terms'];colors=['#176d80','#ae5837','#6555a5']
    assignments={x['term']:x['cluster'] for x in r['clusters']['runs'][0]['assignments']}
    for row in terms:
        axes[0].scatter(row['x'],row['y'],c=colors[assignments[row['term']]-1],s=35)
    overlay=r['projection']['overlay_terms'];palette=['#176d80','#ae5837','#6555a5','#6a7830']
    for term,color in zip(overlay,palette):
        rows=[x for x in r['source_contexts'] if x['term']==term]
        axes[1].scatter([x['x'] for x in rows],[x['y'] for x in rows],c=color,s=20,alpha=.55,label=f'{term} ({len(rows)} sources)')
        center=next(x for x in terms if x['term']==term)
        axes[1].scatter(center['x'],center['y'],c=color,marker='X',s=100,edgecolors='black',linewidths=.5)
    axes[0].set_title('Term centroids · color = fixed k=3, seed 11')
    axes[1].set_title('Source-context overlay · X = term centroid');axes[1].legend(fontsize=8)
    for ax in axes:ax.set(xlabel='Shared term PCA coordinate 1',ylabel='Shared term PCA coordinate 2');ax.grid(alpha=.15)
    variance=sum(r['projection']['explained_variance']);trust=r['projection']['trustworthiness']
    fig.suptitle('Contextual token states from the same 25-source frame')
    fig.text(.5,.035,f'PCA variance {variance:.1%} · term trustworthiness@5 {trust:.3f} · sentence-trained MiniLM token states, not validated word senses',ha='center',fontsize=8)
    fig.text(.5,.01,'At most two occurrences per source/term; equal source means. Proximity does not imply agreement or a shared entity.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,.95))
    # Move only text labels; preserve every fitted coordinate and point position.
    fig.canvas.draw();renderer=fig.canvas.get_renderer();used=[]
    for row in terms:
        placed=False
        for distance in (8,16,24,36,50,70):
            for angle in (45,-45,135,-135,0,90,180,-90):
                dx=distance*np.cos(np.radians(angle));dy=distance*np.sin(np.radians(angle))
                label=axes[0].annotate(row['term'],(row['x'],row['y']),xytext=(dx,dy),
                    textcoords='offset points',fontsize=8,ha='center',va='center',
                    bbox={'facecolor':'white','edgecolor':'none','alpha':.75,'pad':.3},
                    arrowprops={'arrowstyle':'-','color':'#999','lw':.4} if distance>16 else None)
                box=label.get_window_extent(renderer).expanded(1.08,1.12)
                area=axes[0].get_window_extent(renderer)
                if area.contains(box.x0,box.y0) and area.contains(box.x1,box.y1) and not any(box.overlaps(old) for old in used):
                    used.append(box);placed=True;break
                label.remove()
            if placed:break
        if not placed:raise ValueError('Unable to place a term label without collisions')
    for ext in ('png','svg','pdf'):
        p=out/('contextual-token-overlay.'+ext);fig.savefig(p,dpi=160)
        r['figures'].append({'file':p.name,'bytes':p.stat().st_size,'sha256':digest(p.read_bytes()),
            'title':'Contextual token centroids and source-context overlay',
            'alt':'Twenty-four selected term centroids and source means for the first four terms, projected by one PCA. Fixed-k colors are exploratory; token proximity is not answer agreement.'})
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frame','baseline','model','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();study(a.frame,a.baseline,a.model,a.output)
