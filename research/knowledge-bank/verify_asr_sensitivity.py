#!/usr/bin/env python3
"""Check the separate paired-ASR projection without modifying baseline documents."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def require(condition,message):
    if not condition:raise ValueError(message)


def close(a,b):return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-10)


def verify(root):
    root=Path(root);raw=(root/'asr-sensitivity.json').read_bytes();r=json.loads(raw)
    baseline_raw=(root/'analysis.json').read_bytes();baseline=json.loads(baseline_raw)
    knowledge_raw=(root/'knowledge.json').read_bytes();knowledge=json.loads(knowledge_raw)
    require(b'/workspace/' not in raw and b'channels-et-private' not in raw,'Private paths in public sensitivity output')
    require(r['bindings']['baseline_analysis_sha256']==hashlib.sha256(baseline_raw).hexdigest(),'Baseline analysis binding differs')
    require(r['bindings']['knowledge_sha256']==hashlib.sha256(knowledge_raw).hexdigest(),'Question bank binding differs')
    require(r['status']=='executed_paired_edition_sensitivity','No executed sensitivity study')
    ids=baseline['lexical']['source_ids'];positions={sid:i for i,sid in enumerate(ids)};n=len(ids)
    require(r['source_ids']==ids and n==25,'Baseline source identity differs')
    documents={d['source_id']:d for d in baseline['documents']}
    expected={sid for sid,d in documents.items() if d['text_origin']=='machine_transcript'}
    records=r['records'];changed={d['source_id'] for d in records}
    require(len(records)==4 and changed==expected,'Not the four source-bound ASR counterparts')
    for row in records:
        d=documents[row['source_id']]
        require(row['new_edition_id']!=row['source_id'],'Alternative ASR overwrites a source ID')
        require(row['old_words']==d['words'] and row['old_text_sha256']==d['text_sha256'],'Old edition changed')
        require(row['old_text_artifact_sha256']==d['text_artifact_sha256'],'Old artifact changed')
        require(row['new_words']>0 and row['chunk_count']>0,'Missing new recognition')
        require(close(row['duration_seconds'],row['sample_count']/16000),'Decoded duration differs')
        require(0<=row['token_edit_distance']<=max(row['old_recognition_tokens'],row['new_recognition_tokens']),'Invalid token edit distance')
        require(close(row['normalized_token_disagreement'],row['token_edit_distance']/max(row['old_recognition_tokens'],row['new_recognition_tokens'])),'Token disagreement rate differs')
        require(0<=row['paired_lexical_cosine']<=1.00000001 and -1.00000001<=row['paired_semantic_cosine']<=1.00000001,'Invalid paired cosine')
    coverage=r['coverage']
    require(coverage['paired_recordings']==4 and coverage['baseline_source_editions']==25 and coverage['unchanged_source_editions']==21,'Edition denominator differs')
    require(coverage['baseline_words']==47280==baseline['totals']['words'],'Baseline word denominator differs')
    require(coverage['old_paired_words']==sum(x['old_words'] for x in records),'Old paired words differ')
    require(coverage['new_paired_words']==sum(x['new_words'] for x in records),'New paired words differ')
    require(coverage['counterfactual_words']==47280-coverage['old_paired_words']+coverage['new_paired_words'],'Counterfactual word arithmetic differs')
    require(close(coverage['audio_seconds'],sum(x['duration_seconds'] for x in records)),'Audio seconds differ')
    require(coverage['new_input_samples']==sum(x['sample_count'] for x in records) and coverage['new_chunks']==sum(x['chunk_count'] for x in records),'Input coverage differs')
    matrices={'lexical':r['counterfactual_lexical_matrix'],'semantic':r['counterfactual_semantic_matrix']}
    for kind,m in matrices.items():
        require(len(m)==n and all(len(row)==n for row in m),'Matrix shape differs')
        for i,row in enumerate(m):
            for j,value in enumerate(row):
                require(math.isfinite(value) and -1.00000001<=value<=1.00000001 and close(value,m[j][i]),'Invalid matrix cell')
                if ids[i] not in changed and ids[j] not in changed:require(close(value,baseline[kind]['matrix'][i][j]),'Unchanged source pair was altered')
            require(close(row[i],1),'Matrix diagonal differs')
    require(r['neighbors']['k']==5 and [x['source_id'] for x in r['neighbors']['rows']]==ids,'Neighbor order differs')
    for row in r['neighbors']['rows']:
        i=positions[row['source_id']]
        require(row['text_edition_changed']==(row['source_id'] in changed),'Changed-source flag differs')
        for kind in ('lexical','semantic'):
            neighbors=[]
            for prefix,m in [('old',baseline[kind]['matrix']),('new',matrices[kind])]:
                expected_ids=[ids[j] for j in sorted((j for j in range(n) if j!=i),key=lambda j:(-m[i][j],ids[j]))[:5]]
                require(row[prefix+'_'+kind+'_ids']==expected_ids,'Neighbor ranking differs');neighbors.append(set(expected_ids))
            require(close(row[kind+'_jaccard'],len(neighbors[0]&neighbors[1])/len(neighbors[0]|neighbors[1])),'Neighbor Jaccard differs')
    by_source={x['source_id']:x for x in r['neighbors']['rows']}
    for row in records:
        for kind in ('lexical','semantic'):
            require(close(row[kind+'_neighbor_jaccard'],by_source[row['source_id']][kind+'_jaccard']),'Record/neighbor cross-reference differs')
    for kind in ('lexical','semantic'):
        require(close(r['summary']['mean_paired_'+kind+'_cosine'],sum(x['paired_'+kind+'_cosine'] for x in records)/4),'Paired mean differs')
        require(close(r['summary']['mean_all_source_'+kind+'_neighbor_jaccard'],sum(x[kind+'_jaccard'] for x in r['neighbors']['rows'])/25),'Neighbor summary differs')
        maximum=max(abs(matrices[kind][i][j]-baseline[kind]['matrix'][i][j]) for i in range(n) for j in range(n))
        require(close(r['summary']['max_'+kind+'_pair_change'],maximum),'Maximum pair change differs')
    affected=sorted(c['card_id'] for c in knowledge['cards'] if ({c['source_id']}|{s['source_id'] for s in c['supports']})&changed)
    reannotation=r['card_reannotation']
    require(reannotation['cards_rewritten']==0 and reannotation['affected_cards']==len(affected),'Annotation counts differ')
    require(sorted(c['card_id'] for c in reannotation['records'])==affected,'Affected card identities differ')
    cards={c['card_id']:c for c in knowledge['cards']}
    for row in reannotation['records']:
        card=cards[row['card_id']]
        expected_sources=sorted(({card['source_id']}|{s['source_id'] for s in card['supports']})&changed)
        require(row['source_ids']==expected_sources and row['question_id']==card['question_id'],'Affected card source/question join differs')
    require(len(r['figures'])==3,'Expected one three-format figure family')
    for ref in r['figures']:
        name=Path(ref['file']);require(not name.is_absolute() and len(name.parts)==1,'Unsafe figure path')
        path=root/name
        if not path.exists():path=root/'figures'/name
        data=path.read_bytes();require(len(data)==ref['bytes'] and hashlib.sha256(data).hexdigest()==ref['sha256'],'Figure changed')
    return {'status':'passed','paired_recordings':4,'baseline_sources':25,'new_words':coverage['new_paired_words'],
        'affected_cards':len(affected),'analysis_sha256':hashlib.sha256(raw).hexdigest(),
        'scope':'Public paired-edition joins, unchanged baseline pairs, matrix/neighborhood arithmetic and artifact hashes; source audio/recognition validation is separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-dir',type=Path,required=True)
    args=p.parse_args();print(json.dumps(verify(args.public_dir)))
