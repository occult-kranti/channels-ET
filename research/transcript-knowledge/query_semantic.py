#!/usr/bin/env python3
"""Arbitrary local, filtered retrieval over frozen Channel Lab representations.

This additive CLI does not modify the frozen sixteen-query diagnostic. It returns
source candidates and exact locator references, not generated or verified answers.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import retrieve_graph as R


def rank_values(ids,values,allowed,positive=False,available=True):
    if not available:return []
    eligible=[i for i,sid in enumerate(ids) if sid in allowed and math.isfinite(float(values[i])) and (not positive or values[i]>0)]
    return [{'source_id':ids[i],'score':float(values[i])} for i in sorted(eligible,key=lambda i:(-float(values[i]),ids[i]))]


def query(database,text,method,analysis_path,witness,contract_path,model=None,limit=20,**filters):
    R.require(text.strip(),'Query must contain text');R.require(1<=limit<=200,'Limit must be between1 and200')
    R.require(method in {'bm25','tfidf','minilm','rrf'},'Unknown retrieval method')
    contract=R.load(contract_path)
    for name,path in [('database',database),('analysis',analysis_path),('vector_witness',Path(witness)/'core-vectors.npz')]:
        R.require(R.sha(Path(path).read_bytes())==contract['bindings'][name]['sha256'],'Frozen '+name+' artifact differs')
    if method=='bm25':
        result=R.search(database,text,'private',limit,**filters)
        result['status']='candidates_returned' if result['matches'] else 'empty_filtered_universe' if not result['eligible_sources'] else 'no_lexical_match'
        return result
    import numpy as np
    from scipy.sparse import load_npz
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    analysis=R.load(analysis_path);core=np.load(Path(witness)/'core-vectors.npz',allow_pickle=False)
    ids=core['source_ids'].tolist();R.require(ids==[d['source_id'] for d in analysis['documents']],'Frozen representation row order differs')
    with R.open_readonly(database) as db:
        binding=json.loads(db.execute('SELECT value_json FROM meta WHERE key=?',('bindings',)).fetchone()[0])
        R.require(binding['analysis']['sha256']==R.sha(Path(analysis_path).read_bytes()),'Database/analysis binding differs')
        allowed=R.source_filter(db,**filters);sources={r['source_id']:dict(r) for r in db.execute('SELECT source_id,title,source_url,body_sha256,length(body) AS characters FROM sources')}
        if not allowed:return {'method':method,'status':'empty_filtered_universe','eligible_sources':0,'ranked_sources':0,'matches':[],
            'scope':'No eligible sources match these filters. No model query was encoded or answer generated.'}
        lab=R.ROOT/'research/channel-lab';R.require(R.sha((lab/'analyze_corpus.py').read_bytes())==analysis['bindings']['script_sha256'],'Frozen analysis helper changed')
        sys.path.insert(0,str(lab));helper=R.module('local_query_frozen_analysis',lab/'analyze_corpus.py')
        masked=helper.masked(text,analysis['methods']['identity_mask_phrases']);conditions={'bm25':R.bm25_sources(db,text,allowed)}
        if method in {'tfidf','rrf'}:
            R.require(R.sha((Path(witness)/'lexical.npz').read_bytes())==contract['bindings']['lexical_witness']['sha256'],'Frozen lexical witness differs')
            features=core['features'].tolist();v=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,
                ngram_range=(1,2),sublinear_tf=True,min_df=2,max_features=24000,
                stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}),vocabulary={t:i for i,t in enumerate(features)})
            v.idf_=core['idf'];q=v.transform([' '.join(helper.words(masked))]);x=load_npz(Path(witness)/'lexical.npz')
            scores=cosine_similarity(q,x)[0].astype('<f4').astype(float)
            conditions['tfidf']=rank_values(ids,scores,allowed,positive=True)
        if method in {'minilm','rrf'}:
            R.require(model is not None,'MiniLM or fusion requires the pinned local model directory')
            encoder=helper.LabEncoder(model);R.require(encoder.binding['model_manifest_sha256']==analysis['bindings']['model_manifest_sha256'],'Query/document model mismatch')
            q,_,_=encoder.encode_all([('query:'+R.sha(masked.encode()),masked)],Path('/dev/shm/transcript-knowledge-local-query-cache'),batch_size=8)
            scores=np.clip(cosine_similarity(q,core['semantic'])[0],-1,1).astype('<f4').astype(float)
            conditions['minilm']=rank_values(ids,scores,allowed,available=np.linalg.norm(q[0])>0)
        ranking=R.rrf(conditions) if method=='rrf' else conditions[method]
        component_scores={name:{r['source_id']:r['score'] for r in rows} for name,rows in conditions.items()}
        best={r['source_id']:r for r in conditions['bm25']};matches=[]
        for rank,row in enumerate(ranking[:limit],1):
            source=sources[row['source_id']];value={**row,'rank':rank,'title':source['title'],'source_url':source['source_url'],'body_sha256':source['body_sha256']}
            value['component_scores']={name:component_scores.get(name,{}).get(row['source_id']) for name in ('bm25','tfidf','minilm')}
            if row['source_id'] in best:
                value['locator']={k:best[row['source_id']][k] for k in ('passage_id','start_character','end_character','span_sha256','word_start','word_end')}
                value['locator_kind']='highest_BM25_passage_not_judged_answer_evidence'
            else:
                value['locator']={'start_character':0,'end_character':source['characters'],'span_sha256':source['body_sha256']}
                value['locator_kind']='whole_selected_document_not_judged_answer_evidence'
            matches.append(value)
        return {'method':method,'status':'candidates_returned' if ranking else 'no_matching_representation','query':text,'eligible_sources':len(allowed),'ranked_sources':len(ranking),'matches':matches,
            'computed_components':sorted(conditions),'component_match_counts':{name:len(rows) for name,rows in conditions.items()},
            'scope':'Local private source retrieval with global frozen index statistics and selected-source ranking. Candidate matches are not verified answers or calibrated probabilities.',
            'fusion':R.SETTINGS if method=='rrf' else None,'corpus_refitted':False,'public_browser_search':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('database','analysis','witness','contract'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--model',type=Path);p.add_argument('--query',required=True);p.add_argument('--method',choices=['bm25','tfidf','minilm','rrf'],default='rrf');p.add_argument('--limit',type=int,default=20)
    for name in ('channel','creator','origin','after','before'):p.add_argument('--'+name)
    a=p.parse_args();print(json.dumps(query(a.database,a.query,a.method,a.analysis,a.witness,a.contract,a.model,a.limit,
        **{k:getattr(a,k) for k in ('channel','creator','origin','after','before')}),ensure_ascii=False,indent=2))
