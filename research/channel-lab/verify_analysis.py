#!/usr/bin/env python3
"""Stdlib-only release verification for compact channel-lab analytical artifacts."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct


def require(test,message):
    if not test:raise ValueError(message)


def close(a,b,tol=2e-6):return abs(a-b)<=tol
def average(values):return sum(values)/len(values) if values else None


def artifact(root,ref):
    name=Path(ref['file']);require(not name.is_absolute() and '..' not in name.parts,'Unsafe artifact name')
    path=root/name
    if not path.exists() and len(name.parts)==1:path=root/'figures'/name
    raw=path.read_bytes();require(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'Changed analytical artifact: '+str(name))
    return raw


def finite_json(value):
    if isinstance(value,dict):
        for v in value.values():finite_json(v)
    elif isinstance(value,list):
        for v in value:finite_json(v)
    elif isinstance(value,float):require(math.isfinite(value),'Nonfinite scalar JSON')


def top(matrix,ids,index,k=5,allowed=None):
    allowed=range(len(ids)) if allowed is None else allowed
    return [ids[j] for j in sorted((j for j in allowed if j!=index and math.isfinite(matrix[index][j])),
            key=lambda j:(-matrix[index][j],ids[j]))[:k]]


def component_counts(valid,edges):
    parent={i:i for i in valid};degree=collections.Counter()
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for i,j in edges:parent[find(i)]=find(j);degree[i]+=1;degree[j]+=1
    sizes=collections.Counter(find(i) for i in valid)
    return {'edges':len(edges),'components':len(sizes),'isolated_nodes':sum(degree[i]==0 for i in valid),
            'largest_component':max(sizes.values(),default=0)}


def verify_contextual_terms(r,docs,order):
    lexical=r['term_overlay'];terms=lexical['terms'];n=len(terms)
    require(n==24 and len(set(terms))==n,'Contextual term selection differs')
    require(lexical['channel_ids']==order and len(lexical['matrix'])==len(order),'Lexical term context order differs')
    require(all(len(row)==n and all(x>=0 for x in row) for row in lexical['matrix']),'Invalid lexical term weights')
    require(len(lexical['document_frequencies'])==n and all(3<=x<=len(docs) for x in lexical['document_frequencies']),'Invalid term document frequency')
    t=r['contextual_terms'];require(t['status']=='executed_contextual_token_exploration','Contextual experiment not executed')
    require([x['term'] for x in t['terms']]==terms,'Contextual term order differs')
    pairs=t['channel_contexts'];keys=[(x['term'],x['channel_id']) for x in pairs]
    require(len(keys)==len(set(keys)),'Repeated contextual term/context pair')
    source_groups={d['source_id']:d['channel_id'] for d in docs}
    frequencies=collections.Counter();sampled=0
    for row in pairs:
        require(row['term'] in terms and row['channel_id'] in order,'Unknown contextual term/context')
        selected=row['sample_source_ids'];count=row['sampled_documents'];available=row['available_documents']
        require(count==len(selected)==len(set(selected))==min(2,available) and available>0,'Contextual sampling count differs')
        require(all(source_groups.get(s)==row['channel_id'] for s in selected),'Contextual source/context join differs')
        frequencies[row['term']]+=available;sampled+=count
    require([frequencies[x] for x in terms]==lexical['document_frequencies'],'Lexical and contextual term availability differs')
    c=t['coverage'];require(c['selected_terms']==n and c['channel_term_pairs']==len(pairs),'Contextual coverage differs')
    require(c['sampled_document_term_pairs']==sampled and c['available_document_term_pairs']==sum(frequencies.values()),'Contextual sample denominator differs')
    require(3<=c['max_input_wordpieces']<=242,'Contextual input width invalid')
    matrix=t['term_cosine_matrix'];require(len(matrix)==n and all(len(row)==n for row in matrix),'Contextual matrix shape differs')
    for i,row in enumerate(matrix):
        require(close(row[i],1),'Contextual cosine diagonal differs')
        for j,value in enumerate(row):require(-1.000001<=value<=1.000001 and close(value,matrix[j][i]),'Contextual cosine symmetry/range differs')
    projection=t['projection'];variance=projection['explained_variance']
    require(len(variance)==2 and all(0<=x<=1 for x in variance) and sum(variance)<=1.000001,'Contextual explained variance invalid')
    require(0<=projection['trustworthiness_at5']<=1,'Contextual trustworthiness invalid')
    return {'terms':n,'context_pairs':len(pairs),'sampled_document_term_pairs':sampled}


def verify(root):
    root=Path(root);raw=(root/'analysis.json').read_bytes();r=json.loads(raw);finite_json(r)
    require(not any(s in raw for s in (b'/workspace/',b'/dev/shm/',b'channels-et-private',b'"full_text"')),'Private path or source text marker')
    registry_raw=(root/'registry.json').read_bytes();registry=json.loads(registry_raw)
    require(r['bindings']['registry_sha256']==hashlib.sha256(registry_raw).hexdigest(),'Registry binding differs')
    docs=r['documents'];ids=[d['source_id'] for d in docs];index={sid:i for i,sid in enumerate(ids)};n=len(ids)
    registry_docs={d['source_id']:d for d in registry['documents']}
    require(ids==[d['source_id'] for d in registry['documents']] and len(set(ids))==n,'Canonical source order differs')
    require(r['coverage']['documents']==n==registry['coverage']['documents'],'Document denominator differs')
    require(sum(d['words'] for d in docs)==r['coverage']['words']==registry['coverage']['words'],'Word denominator differs')
    require(len(r['topics'])==8 and len({t['topic_id'] for t in r['topics']})==8,'Fixed topic count differs')
    total_windows=0
    for d in docs:
        source=registry_docs[d['source_id']]
        require(d['words']==source['words'] and d['channel_id']==source['channel_id'] and d['creator_id']==source['creator_id'],'Source metadata join differs')
        require(d['published_at']==source['publication_date'] and d['text_origin']==source['text_origin'],'Date/origin join differs')
        weights=d['topic_weights'];require(len(weights)==8 and all(x>=0 for x in weights),'Invalid topic mixture')
        require(close(sum(weights),1 if d['topic_available'] else 0),'Document topic mixture sum differs')
        detail=json.loads(artifact(root,d['detail']));finite_json(detail)
        require(detail['source_id']==d['source_id'] and detail['body_sha256']==source['body_sha256'],'Detail edition differs')
        position=0
        for j,window in enumerate(detail['topic_progression']):
            require(window['ordinal']==j and window['word_start']==position,'Topic progression gap or ordinal mismatch')
            require(0<window['words']<=500 and window['word_end']-position==window['words'],'Invalid topic window length')
            require(close(window['start_fraction'],position/d['words']) and close(window['end_fraction'],window['word_end']/d['words']),'Progress fractions differ')
            require(close(window['normalized_position'],(position+window['word_end'])/(2*d['words'])),'Progress midpoint differs')
            require(len(window['topic_weights'])==8 and all(x>=0 for x in window['topic_weights']),'Invalid progression mixture')
            require(close(sum(window['topic_weights']),1 if sum(window['topic_weights'])>0 else 0),'Progress mixture normalization differs')
            position=window['word_end'];total_windows+=1
        require(position==d['words'],'Topic progression omits final words')
        coverage=detail['encoding'];require(coverage['content_wordpieces']==coverage['processed_content_wordpieces'] and coverage['truncated_wordpieces']==0,'Incomplete neural input coverage')
        require(coverage['available']==d['semantic_available'],'Semantic availability differs')
    require(total_windows==r['coverage']['topic_progression_windows'],'Progression denominator differs')
    matrices={};require(r['matrices']['source_ids']==ids,'Matrix source order differs')
    for name in ('lexical','semantic'):
        binding=r['matrices'][name];require(binding['shape']==[n,n] and binding['dtype']=='float32-le','Matrix layout differs')
        body=artifact(root,binding);require(len(body)==n*n*4,'Matrix byte length differs')
        flat=struct.unpack('<'+str(n*n)+'f',body);m=[flat[i*n:(i+1)*n] for i in range(n)];matrices[name]=m
        valid=[i for i,d in enumerate(docs) if d[name+'_available']]
        require(binding['valid_source_ids']==[ids[i] for i in valid] and len(valid)==r['coverage'][name+'_available'],'Matrix availability differs')
        valid=set(valid)
        for i in range(n):
            for j,value in enumerate(m[i]):
                if i not in valid or j not in valid:require(math.isnan(value),'Unavailable representation became a numerical cosine')
                else:require(math.isfinite(value) and -1.000001<=value<=1.000001 and close(value,m[j][i]),'Invalid cosine cell')
            if i in valid:require(close(m[i][i],1),'Available cosine diagonal differs')
    channels=r['channels'];order=[c['channel_id'] for c in channels];require(order==r['channel_comparisons']['channel_ids'],'Channel matrix order differs')
    require(len(channels)==r['coverage']['channels']==len({d['channel_id'] for d in docs}),'Channel count differs')
    for c in channels:
        members=[d for d in docs if d['channel_id']==c['channel_id']]
        require(c['documents']==len(members) and c['words']==sum(d['words'] for d in members),'Channel coverage differs')
        require(c['text_origins']==dict(collections.Counter(d['text_origin'] for d in members)),'Channel origin counts differ')
        years=collections.Counter(str(d['published_at'])[:4] for d in members if d['published_at'] is not None)
        require(c['year_counts']==dict(years) and c['unknown_dates']==sum(d['published_at'] is None for d in members),'Channel date counts differ')
        selected=[d for d in members if d['topic_available']]
        require(c['topic_available_documents']==len(selected),'Channel topic denominator differs')
        for k in range(8):require(close(c['topic_weights'][k],average([d['topic_weights'][k] for d in selected]) if selected else 0),'Channel topic mean differs')
    for name,m in matrices.items():
        for i,left in enumerate(order):
            for j,right in enumerate(order):
                values=[m[a][b] for a,d in enumerate(docs) if d['channel_id']==left for b,e in enumerate(docs)
                        if e['channel_id']==right and a!=b and (left!=right or a<b) and math.isfinite(m[a][b])]
                require(r['channel_comparisons'][name+'_pair_counts'][i][j]==len(values),'Channel pair count differs')
                expected=average(values);actual=r['channel_comparisons'][name][i][j]
                require(actual is None if expected is None else actual is not None and close(actual,expected),'Channel cosine mean differs')
    for name,control in r['diagnostics'].items():
        if not isinstance(control,dict) or 'same_source_universe' not in control:continue
        rows=control['rows'];require([x['source_id'] for x in rows]==ids,'Sensitivity source order differs')
        common=[i for i,x in enumerate(rows) if x['eligible']];require(len(common)==control['eligible_sources'],'Sensitivity denominator differs')
        by=collections.defaultdict(list);values=[]
        for i,row in enumerate(rows):
            if not row['eligible']:require(row['jaccard'] is None and not row['full_ids'] and not row['control_ids'],'Ineligible source has stability score');continue
            a=set(row['full_ids']);b=set(row['control_ids']);require(len(a)==len(row['full_ids']) and len(b)==len(row['control_ids']),'Duplicate neighbor')
            require(a|b<={ids[j] for j in common}-{ids[i]},'Sensitivity neighbor outside common universe')
            expected=len(a&b)/len(a|b) if a|b else None
            require(row['jaccard'] is None if expected is None else close(row['jaccard'],expected),'Jaccard differs')
            if expected is not None:values.append(expected);by[docs[i]['channel_id']].append(expected)
            if name=='lexical_vs_semantic':
                require(row['full_ids']==top(matrices['lexical'],ids,i,allowed=common) and row['control_ids']==top(matrices['semantic'],ids,i,allowed=common),'Public matrix neighbors differ')
        require(close(control['mean_jaccard'],average(values)) and close(control['channel_macro_jaccard'],average([average(v) for v in by.values()])),'Sensitivity summary differs')
    for name,m in matrices.items():
        valid=[i for i in range(n) if math.isfinite(m[i][i])];g=r['graph'][name]
        require(g['available_nodes']==len(valid),'Graph denominator differs')
        for trial in g['threshold_trials']:
            edges=[(i,j) for pos,i in enumerate(valid) for j in valid[pos+1:] if m[i][j]>=trial['threshold']]
            expected=component_counts(valid,edges)
            require(all(trial[k]==v for k,v in expected.items()),'Threshold graph count differs')
        for trial in g['knn_trials']:
            lists=[set(top(m,ids,i,trial['k'])) for i in range(n)]
            edges=[(i,index[s]) for i in valid for s in lists[i] if i<index[s] and ids[i] in lists[index[s]]]
            expected=component_counts(valid,edges)
            require(all(trial[k]==v for k,v in expected.items()),'Mutual-k graph count differs')
            if trial['k']==3:require({(e['source'],e['target']) for e in g['edges']}=={(ids[i],ids[j]) for i,j in edges},'Reference graph edges differ')
    for figure in r['figures']:artifact(root,figure)
    contextual=verify_contextual_terms(r,docs,order)
    require(r['status']=='executed_canonical_frame_analysis','No executed analysis')
    return {'status':'passed','documents':n,'words':r['coverage']['words'],'channels':len(channels),
        'details':n,'matrix_cells_checked':2*n*n,'topic_windows':total_windows,'figure_files':len(r['figures']),
        'contextual_terms':contextual,
        'analysis_sha256':hashlib.sha256(raw).hexdigest(),
        'scope':'Public source/count/matrix/neighbor/topic-mixture/group/graph/hash verification. Independent model refit, hidden-state pooling and source-reading checks are separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public-dir',type=Path,required=True);print(json.dumps(verify(p.parse_args().public_dir)))
