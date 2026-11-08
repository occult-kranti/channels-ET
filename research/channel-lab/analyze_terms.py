"""Bounded contextual token-state overlay; no sentence cosine is called agreement."""
import collections
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import trustworthiness
from sklearn.metrics.pairwise import cosine_similarity


def unit(v):
    norm=float(np.linalg.norm(v))
    if not np.isfinite(v).all() or norm<1e-12:raise ValueError('Invalid contextual token vector')
    return v/norm


def build(docs,masked_texts,terms,encoder,word_pattern,ram):
    selected=[];candidates=collections.defaultdict(list)
    for i,(d,text) in enumerate(zip(docs,masked_texts)):
        matches=collections.defaultdict(list)
        for m in word_pattern.finditer(text):
            term=m.group().casefold().replace('’',"'")
            if term in terms:matches[term].append((m.start(),m.end()))
        for term,spans in matches.items():
            r=d['record'];key=(term,r['channel_id'])
            candidates[key].append({'owner':i,'source_id':r['source_id'],'occurrences':len(spans),'span':spans[(len(spans)-1)//2]})
    for key,rows in sorted(candidates.items()):
        rows.sort(key=lambda r:hashlib.sha256((key[0]+'|'+r['source_id']).encode()).hexdigest())
        for row in rows[:2]:selected.append({**row,'term':key[0],'channel_id':key[1],'available_documents':len(rows)})
    encoded={};windows=[];locators=[]
    for row in selected:
        owner=row['owner']
        if owner not in encoded:encoded[owner]=encoder.tokenizer.encode(masked_texts[owner],add_special_tokens=False)
        e=encoded[owner];start,end=row['span'];hit=[i for i,(a,b) in enumerate(e.offsets) if b>start and a<end]
        if not hit:raise ValueError('Missing target wordpiece span')
        lo=max(0,hit[0]-24);hi=min(len(e.ids),hit[-1]+25);target_start=hit[0]-lo+1;target_end=hit[-1]-lo+2
        windows.append(([101]+e.ids[lo:hi]+[102],target_start,target_end))
        a=e.offsets[lo][0];b=e.offsets[hi-1][1];r=docs[owner]['record'];text=docs[owner]['text']
        locators.append({'term':row['term'],'source_id':r['source_id'],'body_sha256':r['body_sha256'],
            'term_char_start':start,'term_char_end':end,'term_sha256':hashlib.sha256(text[start:end].encode()).hexdigest(),
            'context_char_start':a,'context_char_end':b,'original_context_sha256':hashlib.sha256(text[a:b].encode()).hexdigest(),
            'masked_context_sha256':hashlib.sha256(masked_texts[owner][a:b].encode()).hexdigest(),
            'wordpiece_start':lo,'wordpiece_end':hi,'target_input_start':target_start,'target_input_end':target_end,
            'input_ids_sha256':hashlib.sha256(np.asarray(windows[-1][0],dtype='<i8').tobytes()).hexdigest()})
    vectors=[]
    for offset in range(0,len(windows),8):
        batch=windows[offset:offset+8];width=max(len(x[0]) for x in batch)
        ids=np.zeros((len(batch),width),dtype=np.int64);mask=np.zeros_like(ids)
        for i,(values,_,_) in enumerate(batch):ids[i,:len(values)]=values;mask[i,:len(values)]=1
        inputs={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
        hidden=encoder.session.run(None,{k:v for k,v in inputs.items() if k in encoder.input_names})[0]
        vectors.extend(unit(hidden[i,a:b].astype(float).mean(axis=0)) for i,(_,a,b) in enumerate(batch))
    grouped=collections.defaultdict(list)
    for i,row in enumerate(selected):grouped[(row['term'],row['channel_id'])].append(i)
    keys=sorted(grouped);channel_vectors=np.stack([unit(np.asarray([vectors[i] for i in grouped[key]]).mean(axis=0)) for key in keys])
    term_vectors=np.stack([unit(channel_vectors[[i for i,key in enumerate(keys) if key[0]==term]].mean(axis=0)) for term in terms])
    pca=PCA(n_components=2,svd_solver='full');xy=pca.fit_transform(term_vectors);center=xy.mean(axis=0)
    radius=float(np.sqrt(np.mean(np.sum((xy-center)**2,axis=1))));xy=(xy-center)/radius;cx=(pca.transform(channel_vectors)-center)/radius
    similarities=cosine_similarity(term_vectors);np.fill_diagonal(similarities,1)
    ram=Path(ram);np.savez(ram/'term-vectors.npz',sample_vectors=np.asarray(vectors),channel_vectors=channel_vectors,term_vectors=term_vectors,
                         pca_components=pca.components_,pca_mean=pca.mean_,terms=np.asarray(terms))
    (ram/'term-locators-private.json').write_text(json.dumps({'selected':selected,'locators':locators,'channel_keys':keys},separators=(',',':'))+'\n')
    return {'status':'executed_contextual_token_exploration','terms':[{'term':t,'x':float(x),'y':float(y)} for t,(x,y) in zip(terms,xy)],
        'channel_contexts':[{'term':term,'channel_id':channel,'x':float(x),'y':float(y),'available_documents':len(candidates[(term,channel)]),
            'sampled_documents':len(grouped[(term,channel)]),'sample_source_ids':[selected[j]['source_id'] for j in grouped[(term,channel)]]}
            for (term,channel),(x,y) in zip(keys,cx)],
        'coverage':{'selected_terms':len(terms),'available_document_term_pairs':sum(len(v) for v in candidates.values()),
            'sampled_document_term_pairs':len(selected),'channel_term_pairs':len(keys),'max_input_wordpieces':max(len(w[0]) for w in windows)},
        'term_cosine_matrix':similarities.tolist(),'projection':{'explained_variance':pca.explained_variance_ratio_.tolist(),
            'trustworthiness_at5':float(trustworthiness(np.clip(1-similarities,0,2),xy,n_neighbors=5,metric='precomputed')),
            'scope':'One PCA on normalized term vectors transforms every channel-term mean. A normalized term prototype need not sit at the plotted source-point average.'},
        'sampling':'At most two documents per publisher context/term, selected by SHA256(term|canonical source ID); one middle ordinal occurrence per document. Mean target subwords in ±24-wordpiece contexts; normalize occurrence, mean within context, then equal-context term mean and normalize.',
        'limitations':['Sentence-trained MiniLM target-token states are exploratory, not validated word senses or new trained word embeddings.',
            'The bounded deterministic sample is not representative of every use. Spelling, grammar and source style can dominate proximity.',
            'Balancing is by publisher context, not independently authenticated people; guest-publisher contexts are not new mediums.',
            'Shared coordinates and token cosines do not imply common answers, contradictions or identity of claimed entities.']}
