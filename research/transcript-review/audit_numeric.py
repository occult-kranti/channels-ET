#!/usr/bin/env python3
"""Recalculate selected study results directly from private bytes, without author helpers."""
from __future__ import annotations
from collections import Counter,defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import unicodedata
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.decomposition import NMF,TruncatedSVD

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
TOKEN=re.compile(r"\b[a-z]+(?:'[a-z]+)?\b")
FEATURE=re.compile(r"(?u)\b[a-z][a-z']+\b")
FILLER=set("know yeah okay ok um uh gonna wanna gotta really just like sort thing things going said say says youre youve weve we're you're you've we've thats that's theres there's right".split())
STOP=(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'})|FILLER
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalized(s):return unicodedata.normalize('NFKC',s).replace('’',"'").replace('‘',"'").lower()
def get_raw():
    result={};segments={}
    for r in load(ROOT/'research/harvest/asr/summary.json')['records']+[load(ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json')]:
        result[r['sourceId']]=(Path(r['transcriptDirectory'])/'transcript.txt').read_text()
        segments[r['sourceId']]=[json.loads(x) for x in (Path(r['transcriptDirectory'])/'segments.jsonl').read_text().splitlines() if x]
    p=load(ROOT/'research/access-repair/primary-sources/expanded-metadata.json')
    for r in p['daniel']['items']:result[f"daniel-item-{r['item_index']:02d}"]=Path(r['text']['raw_local_path']).read_text()
    result['paul-birmingham-pdf']=Path(p['paul']['text']['raw_local_path']).read_text()
    return result,segments
def counter(text):
    words=[w for w in FEATURE.findall(normalized(text)) if w not in STOP]
    return Counter(words+[' '.join(pair) for pair in zip(words,words[1:])])
def fit_manual(texts):
    cs=[counter(t) for t in texts];df=Counter();frequency=Counter()
    for c in cs:df.update(c.keys());frequency.update(c)
    valid=sorted(t for t in df if 2<=df[t]<=.95*len(texts))
    if len(valid)>3000:
        order=np.argsort(-np.array([frequency[t] for t in valid]));valid=sorted(valid[i] for i in order[:3000])
    idf=np.array([1+math.log((1+len(texts))/(1+df[t])) for t in valid])
    return transform(cs,valid,idf),valid,idf,cs,df
def transform(counters,terms,idf):
    a=np.array([[c[t] for t in terms] for c in counters],dtype=float)
    nonzero=a>0;a[nonzero]=1+np.log(a[nonzero]);a*=idf
    length=np.sqrt((a*a).sum(axis=1));a/=np.where(length>0,length,1)[:,None]
    return a
def counts(text,definitions):return {key:sum(len(list(re.finditer(pattern,normalized(text)))) for pattern in patterns) for key,patterns in definitions.items()}
def selected_silhouette(distance,labels):
    result=[]
    for i,label in enumerate(labels):
        same=[j for j,l in enumerate(labels) if l==label and j!=i]
        if not same:result.append(0.0);continue
        a=float(np.mean(distance[i,same]));b=min(float(np.mean(distance[i,[j for j,l in enumerate(labels) if l==other]])) for other in set(labels) if other!=label)
        result.append((b-a)/max(a,b) if max(a,b)>0 else 0.)
    return float(np.mean(result))
def audit():
    analysis_path=ROOT/'research/transcript-analysis/analysis.json';d=load(analysis_path);raw,segs=get_raw();by_id={x['sourceId']:x for x in d['sources']}
    checks=[]
    def check(name,condition,**extra):
        checks.append({'name':name,'passed':bool(condition),**extra})
        assert condition,name
    for source in d['sources']:
        sid=source['sourceId'];check('source_sha:'+sid,hashlib.sha256(raw[sid].encode()).hexdigest()==source['transcriptSha256'])
        check('whitespace_words:'+sid,len(raw[sid].split())==source['words'])
        check('common_tokens:'+sid,len(TOKEN.findall(normalized(raw[sid])))==source['tokenCount'])
    matrices={};terms={};idf={};cs={};max_residual={};negation={}
    for modality in ('audio','authored'):
        ids=d['tfidf'][modality]['sourceIds'];x,v,weights,counters,df=fit_manual([raw[s] for s in ids]);matrices[modality]=x;terms[modality]=v;idf[modality]=weights;cs[modality]=counters
        residual=float(np.max(np.abs(x@x.T-np.array(d['tfidf'][modality]['cosine']))));max_residual[modality]=residual
        check('manual_tfidf_cosines:'+modality,residual<1e-10,max_absolute_residual=residual)
        check('feature_count:'+modality,len(v)==d['tfidf'][modality]['featureCount'])
        check('nonzero_features:'+modality,bool(np.all(np.linalg.norm(x,axis=1)>0)))
        negation[modality]={t:{'included_in_final_vocabulary':t in v,'document_frequency':df[t]} for t in ('no','not','nor','never')}
        lookup={t:i for i,t in enumerate(v)}
        global_terms=[r['term'] for r in d['tfidf'][modality]['terms']]
        for entry in d['tfidf'][modality]['terms']:
            check('mean_top_term:'+modality+':'+entry['term'],abs(float(x[:,lookup[entry['term']]].mean())-entry['weight'])<5.1e-9)
        for row,display in enumerate(d['tfidf'][modality]['displayTermWeights']):
            check('heatmap_display_weights:'+display['sourceId'],display['sourceId']==ids[row] and np.max(np.abs(x[row,[lookup[t] for t in global_terms]]-display['weights']))<1e-12)
        for row,source in enumerate(d['tfidf'][modality]['documents']):
            for term in source['topTerms']:check('top_term_weight:'+source['sourceId']+':'+term['term'],abs(x[row,lookup[term['term']]]-term['weight'])<5.1e-9)
    audio_ids=d['tfidf']['audio']['sourceIds'];authored_ids=d['tfidf']['authored']['sourceIds']
    authored_in_audio=transform([counter(raw[s]) for s in authored_ids],terms['audio'],idf['audio']);cross=matrices['audio']@authored_in_audio.T
    cross_lookup={(x['audioSourceId'],x['publisherSourceId']):x['cosine'] for x in d['tfidf']['crossModalityProjection']['rows']}
    cross_residual=max(abs(cross[i,j]-cross_lookup[(a,b)]) for i,a in enumerate(audio_ids) for j,b in enumerate(authored_ids))
    check('cross_modality_uses_audio_vocabulary_idf',cross_residual<1e-10,max_absolute_residual=float(cross_residual))
    svd=TruncatedSVD(n_components=2,random_state=11);svd.fit(matrices['audio'])
    coordinate_residual=float(np.max(np.abs(svd.transform(matrices['audio'])-np.array([[r['x'],r['y']] for r in d['clusters']['projection']['audio']]))))
    overlay_residual=float(np.max(np.abs(svd.transform(authored_in_audio)-np.array([[r['x'],r['y']] for r in d['clusters']['projection']['publisherComparison']]))))
    check('audio_svd_projection',coordinate_residual<1e-10,max_absolute_residual=coordinate_residual)
    check('authored_overlay_uses_same_audio_svd',overlay_residual<1e-10,max_absolute_residual=overlay_residual)
    definitions=d['lexicons'];counts_by={};overlap_rows=[]
    for field,definition,count_key in [('theme','themeDefinitions','themeRates'),('civilization','civilizationDefinitions','civilizationCounts'),('entity','entityNameDefinitions','entityNameCounts')]:
        by_source={r['sourceId']:r for r in definitions[count_key]};counts_by[field]={}
        for sid,row in by_source.items():
            computed=counts(raw[sid],definitions[definition]);counts_by[field][sid]=computed
            check('independent_'+field+'_counts:'+sid,computed==row['counts'])
            if 'rates' in row:
                n=len(TOKEN.findall(normalized(raw[sid])));check('independent_'+field+'_rates:'+sid,all(abs(row['rates'][k]-1000*v/n)<1e-12 for k,v in computed.items()))
            for name,patterns in definitions[definition].items():
                spans=[m.span() for p in patterns for m in re.finditer(p,normalized(raw[sid]))]
                duplicated=len(spans)-len(set(spans))
                if duplicated:overlap_rows.append({'sourceId':sid,'dictionary':field,'family':name,'duplicate_exact_match_spans':duplicated})
    zero_bins=0;chunk_count=0
    profiles={r['sourceId']:r for r in definitions['timeProfiles']}
    for sid in audio_ids:
        duration=by_id[sid]['durationSeconds'];den=[0]*10;hits=[Counter() for _ in range(10)];chunk_tokens=0
        for segment in segs[sid]:
            i=min(9,int(10*((segment['start']+segment['end'])/2)/duration));n=len(TOKEN.findall(normalized(segment['text'])));den[i]+=n
            hits[i].update(counts(segment['text'],definitions['themeDefinitions']));chunk_tokens+=n
            if chunk_tokens>=500:chunk_count+=1;chunk_tokens=0
        if chunk_tokens:chunk_count+=1
        for i,bin_ in enumerate(profiles[sid]['bins']):
            check('bin_denominator:'+sid+':'+str(i),den[i]==bin_['tokenDenominator'])
            zero_bins+=den[i]==0
            check('bin_rate:'+sid+':'+str(i),all(bin_['rates'][k] is None if den[i]==0 else abs(bin_['rates'][k]-1000*hits[i][k]/den[i])<1e-12 for k in definitions['themeDefinitions']))
    check('chunk_count',chunk_count==d['summary']['nonoverlappingSegmentChunks'])
    for group in definitions['groupRates']:
        ids=group['sourceIds'];n=sum(by_id[s]['tokenCount'] for s in ids)
        check('group_token_denominator:'+group['group'],n==group['tokens'])
        for family in definitions['themeDefinitions']:
            rates=[1000*counts_by['theme'][s][family]/by_id[s]['tokenCount'] for s in ids]
            check('equal_document_rate:'+group['group']+':'+family,abs(float(np.mean(rates))-group['equalDocumentMeanRates'][family])<1e-12)
            check('pooled_rate:'+group['group']+':'+family,abs(1000*sum(counts_by['theme'][s][family] for s in ids)/n-group['pooledTokenRates'][family])<1e-12)
    sim=matrices['audio']@matrices['audio'].T
    for row in d['networks']['documentSimilarity']['thresholdSensitivity']:
        actual=int(np.sum(np.triu(sim>=row['threshold'],1)));check('threshold_edges:'+str(row['threshold']),actual==row['edges'])
    expected_edges=set()
    for i in range(len(audio_ids)):
        for j in sorted((j for j in range(len(audio_ids)) if j!=i),key=lambda j:(-sim[i,j],j))[:2]:
            if sim[i,j]>=.2:expected_edges.add(tuple(sorted((audio_ids[i],audio_ids[j]))))
    observed={tuple(sorted((e['source'],e['target']))) for e in d['networks']['documentSimilarity']['edges']}
    check('top2_union_network',observed==expected_edges)
    authored_sim=matrices['authored']@matrices['authored'].T
    for row in d['networks']['publisherDocumentSimilarity']['thresholdSensitivity']:
        check('authored_threshold_edges:'+str(row['threshold']),int(np.sum(np.triu(authored_sim>=row['threshold'],1)))==row['edges'])
    authored_edges=set()
    for i in range(len(authored_ids)):
        for j in sorted((j for j in range(len(authored_ids)) if j!=i),key=lambda j:(-authored_sim[i,j],j))[:2]:
            if authored_sim[i,j]>=.2:authored_edges.add(tuple(sorted((authored_ids[i],authored_ids[j]))))
    check('authored_top2_union_network',authored_edges=={tuple(sorted((e['source'],e['target']))) for e in d['networks']['publisherDocumentSimilarity']['edges']})
    for modality,cohort in d['networks']['entityMention']['cohorts'].items():
        ids=audio_ids if modality=='audio_asr' else authored_ids
        check('civilization_cohort_denominator:'+modality,cohort['denominatorDocuments']==len(ids))
        for node in cohort['nodes']:
            check('civilization_node_presence:'+modality+node['id'],node['documents']==sum(counts_by['civilization'][sid][node['id']]>0 for sid in ids))
            check('civilization_node_mentions:'+modality+node['id'],node['mentions']==sum(counts_by['civilization'][sid][node['id']] for sid in ids))
        for edge in cohort['edges']:
            check('civilization_cohort_edge:'+modality+edge['source']+edge['target'],edge['documents']==sum(counts_by['civilization'][sid][edge['source']]>0 and counts_by['civilization'][sid][edge['target']]>0 for sid in ids))
    labels_by={r['sourceId']:r['cluster'] for r in d['clusters']['labels']};labels=[labels_by[s] for s in audio_ids]
    silhouette=selected_silhouette(np.maximum(0,1-sim),labels)
    reference=next(r for r in d['clusters']['candidates'] if r['k']==d['clusters']['selectedK'])['cosineSilhouette']
    check('manual_selected_silhouette',abs(silhouette-reference)<1e-12,manual=silhouette)
    # Independent fresh NMF fit on the manually constructed matrix, rather than importing build.py.
    model=NMF(n_components=3,init='random',random_state=11,max_iter=1500,solver='cd',tol=.0001);w=model.fit_transform(matrices['audio']);shares=w/np.maximum(w.sum(axis=1,keepdims=True),1e-12)
    public=np.array([r['weights'] for r in d['topics']['weights']]);nmf_residual=float(np.max(np.abs(shares-public)))
    check('independent_nmf_selected_weights',nmf_residual<1e-7,max_absolute_residual=nmf_residual)
    check('independent_nmf_reconstruction',abs(model.reconstruction_err_-next(r for r in d['topics']['candidates'] if r['k']==3)['reconstructionError'])<1e-7)
    for row in d['networks']['channelTopic']:
        indices=[i for i,sid in enumerate(audio_ids) if by_id[sid]['publisher']==row['publisher']]
        check('publisher_topic_equal_document_mean:'+row['publisher'],np.max(np.abs(shares[indices].mean(axis=0)-row['topicWeights']))<1e-10)
    authored_model=NMF(n_components=3,init='random',random_state=11,max_iter=1500,solver='cd',tol=.0001);aw=authored_model.fit_transform(matrices['authored']);aw/=np.maximum(aw.sum(axis=1,keepdims=True),1e-12)
    check('authored_nmf_separate_vocabulary',np.max(np.abs(aw-np.array([r['weights'] for r in d['tfidf']['authored']['topics']['weights']])))<1e-7)
    authored_clusters=d['tfidf']['authored']['clusters'];authored_label_by={r['sourceId']:r['cluster'] for r in authored_clusters['labels']}
    authored_labels=[authored_label_by[sid] for sid in authored_ids];authored_silhouette=selected_silhouette(np.maximum(0,1-authored_sim),authored_labels)
    check('manual_authored_selected_silhouette',abs(authored_silhouette-next(r for r in authored_clusters['candidates'] if r['k']==authored_clusters['selectedK'])['cosineSilhouette'])<1e-12)
    authored_svd=TruncatedSVD(n_components=2,random_state=11);authored_svd.fit(matrices['authored'])
    check('authored_separate_svd',np.max(np.abs(authored_svd.transform(matrices['authored'])-np.array([[r['x'],r['y']] for r in authored_clusters['projection']['publisherText']])))<1e-10)
    # Construct controls deliberately preserve dictionary triggers while denying their interpretation.
    controls=[{'name':'astronomy_is_not_verified_civilization','text':'Orion is an astronomical constellation, not an extraterrestrial civilization.'},
              {'name':'negated_claim_still_has_mentions','text':'I do not believe aliens made contact. This is not evidence of contact.'}]
    synthetic=[{'name':r['name'],'themeCounts':counts(r['text'],definitions['themeDefinitions']),'civilizationCounts':counts(r['text'],definitions['civilizationDefinitions']),'scope':'synthetic construct control, not corpus prevalence or annotated accuracy'} for r in controls]
    pairs=[('Aliens made contact.','Aliens never made contact.'),('I believe aliens made contact.','I do not believe aliens made contact.'),('Contact is real.','Contact is not real.')]
    negation_pairs=[]
    for positive,negative in pairs:
        transformed=transform([counter(positive),counter(negative)],terms['audio'],idf['audio'])
        negation_pairs.append({'affirmative_synthetic_text':positive,'negated_synthetic_text':negative,
            'cosine_in_actual_audio_fitted_space':float(transformed[0]@transformed[1]),
            'identical_feature_vectors':bool(np.array_equal(transformed[0],transformed[1])),
            'scope':'Fixed synthetic contrast; no corpus prevalence, model accuracy or claim-stance validation'})
    sizes=Counter(labels);singletons=[audio_ids[i] for i,l in enumerate(labels) if sizes[l]==1]
    return {'schema_version':1,'status':'pass','analysis_sha256':sha(analysis_path),'protocol_sha256':sha(ROOT/'research/transcript-analysis/protocol.json'),
            'method':'Private source bytes -> independent normalization/counters/manual smoothed sublinear TF-IDF/L2/cosine/silhouette; independent selected NMF refit; no author helper imports',
            'checks':len(checks),'failed_checks':[c for c in checks if not c['passed']],'manual_tfidf_max_residual':max_residual,
            'cross_modality_projection_max_residual':float(cross_residual),'selected_nmf_weight_max_residual':nmf_residual,
            'selected_cluster_sizes':dict(sizes),'singleton_source_ids':singletons,'selected_cluster_silhouette':silhouette,
            'authored_selected_cluster_k':authored_clusters['selectedK'],'authored_selected_cluster_sizes':dict(Counter(authored_labels)),
            'authored_selected_cluster_silhouette':authored_silhouette,'same_space_overlay_max_residual':overlay_residual,
            'negation_feature_diagnostics':negation,'within_dictionary_duplicate_exact_spans':overlap_rows,'zero_token_time_bins':zero_bins,
            'synthetic_construct_controls':synthetic,'synthetic_negation_pairs':negation_pairs,
            'raw_text_published':False,'network_requests':0,'new_llm_or_asr_inference':False}

if __name__=='__main__':
    result=audit();(HERE/'numeric-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
