#!/usr/bin/env python3
"""Stdlib-only verification of the public retrieval, SQLite and graph modules."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET


def require(value,message):
    if not value:raise ValueError(message)
def close(a,b,tol=1e-10):return abs(a-b)<=tol
def read(path):return json.loads(Path(path).read_text())
def average(values):return sum(values)/len(values)


def finite_public(value):
    if isinstance(value,dict):
        for key,item in value.items():
            require(key not in {'full_text','extractive_summary','private_path','question_text','answer_text','context_text'},'Private field in public JSON')
            finite_public(item)
    elif isinstance(value,list):
        for item in value:finite_public(item)
    elif isinstance(value,float):require(math.isfinite(value),'Nonfinite public JSON')
    elif isinstance(value,str):require(not any(x in value for x in ('/workspace/','/dev/shm/','channels-et-private')),'Private path in public JSON')


def verify_database(root,meta):
    binding=meta['public_database'];require(binding['file']=='database-public.sqlite','Unexpected public DB filename')
    path=root/binding['file'];raw=path.read_bytes()
    require(len(raw)==binding['bytes'] and hashlib.sha256(raw).hexdigest()==binding['sha256'],'Public database hash differs')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Public DB integrity failed')
    require(db.execute('PRAGMA foreign_key_check').fetchall()==[],'Public DB foreign key failed')
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    allowed={'meta','sources','profiles','records','questions','cards','evidence','record_evidence','card_evidence','passages','public_search',
        'public_search_data','public_search_idx','public_search_content','public_search_docsize','public_search_config'}
    require(names==allowed,'Unexpected public DB table')
    for name,count in meta['coverage']['tables']['public'].items():
        require(name in allowed and db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]==count,'Database table count differs')
    for table,columns in [('sources',['body']),('records',['question_text','answer_text','context_text']),('evidence',['text'])]:
        for column in columns:require(db.execute('SELECT COUNT(*) FROM '+table+' WHERE '+column+' IS NOT NULL').fetchone()[0]==0,'Raw source field exposed')
    require(db.execute('SELECT COUNT(*) FROM passages').fetchone()[0]==0,'Private passages exposed')
    sources={r['source_id']:dict(r) for r in db.execute('SELECT * FROM sources')}
    require(len(sources)==meta['coverage']['sources']==493,'Source denominator differs')
    require(sum(r['words'] for r in sources.values())==meta['coverage']['words']==1411446,'Word denominator differs')
    for table in ('sources','records','questions','cards','evidence'):
        for row in db.execute('SELECT metadata_json FROM '+table):finite_public(json.loads(row[0]))
    profiles={r['source_id']:json.loads(r['profile_json']) for r in db.execute('SELECT * FROM profiles')}
    require(set(profiles)==set(sources),'Profile/source universe differs')
    expected=[]
    for sid,p in profiles.items():
        finite_public(p);require(p['body_sha256']==sources[sid]['body_sha256'],'Profile body hash differs')
        text=' '.join([sources[sid]['title'],p.get('summary',''),*[x['term'] for x in p.get('top_terms',[])],*[x['label'] for x in p.get('topic_profile',[])]])
        expected.append(('profile:'+sid,'source_profile',sid,text))
    questions={r['question_id']:dict(r) for r in db.execute('SELECT * FROM questions')}
    cards={r['card_id']:dict(r) for r in db.execute('SELECT * FROM cards')};question_sources=set()
    for cid,c in cards.items():
        sid=c['source_id'];require(sid in sources and c['question_id'] in questions,'Curated source/question join differs')
        text=' '.join(c[k] or '' for k in ('paraphrase','conditions','time_scope','qualifying_note'))
        expected.append(('card:'+cid,'qualified_answer_card',sid,text));question_sources.add((c['question_id'],sid))
        proofs=db.execute('SELECT e.* FROM evidence e JOIN card_evidence l USING(evidence_id) WHERE l.card_id=?',(cid,)).fetchall()
        require(proofs,'Card lacks evidence')
        for p in proofs:require(p['source_id']==sid and p['body_sha256']==sources[sid]['body_sha256'],'Card source/evidence edition differs')
    for qid,sid in question_sources:expected.append(('question:'+qid+':'+sid,'curated_question',sid,questions[qid]['question']))
    actual=[tuple(r) for r in db.execute('SELECT item_id,item_type,source_id,text FROM public_search')]
    require(Counter(actual)==Counter(expected),'Public FTS contains text beyond the exact approved composition')
    require(dict(db.execute('SELECT type,COUNT(*) FROM records GROUP BY type').fetchall())==meta['coverage']['records_by_type'],'Extraction type counts differ')
    for row in db.execute('SELECT * FROM evidence'):
        require(row['source_id'] in sources and row['body_sha256']==sources[row['source_id']]['body_sha256'],'Evidence selected edition differs')
        require(0<=row['start_character']<row['end_character'] and row['words']>0,'Invalid evidence locator')
    return db,sources,cards,questions


def verify_graph(root,graph,db,sources,cards,questions):
    nodes={n['id']:n for n in graph['nodes']};edges=graph['edges']
    require(len(nodes)==len(graph['nodes'])==graph['coverage']['nodes'],'Duplicate/miscounted graph node')
    require(len({e['id'] for e in edges})==len(edges)==graph['coverage']['edges'],'Duplicate/miscounted graph edge')
    require(dict(Counter(n['type'] for n in nodes.values()))==graph['coverage']['nodes_by_type'],'Graph node types differ')
    require(dict(Counter(e['relation'] for e in edges))==graph['coverage']['edges_by_relation'],'Graph relation counts differ')
    require({n['source_id'] for n in nodes.values() if n['type']=='source'}==set(sources),'Graph source universe differs')
    require({n['card_id'] for n in nodes.values() if n['type']=='answer_card'}==set(cards),'Graph curated-card coverage differs')
    require({n['question_id'] for n in nodes.values() if n['type']=='question'}==set(questions),'Graph question coverage differs')
    require(not any(e['relation']=='asks' for e in edges),'Graph falsely asserts source asked an analyst question')
    factor_sums=defaultdict(float)
    for e in edges:
        require(e['source'] in nodes and e['target'] in nodes,'Dangling graph edge')
        require(e['relation'] in graph['relation_types'],'Unknown graph relation')
        require(e['origin']==graph['relation_types'][e['relation']]['origin'],'Graph relation origin differs')
        if e['relation']=='factor_weight':
            require(nodes[e['source']]['type']=='source' and nodes[e['target']]['type']=='lexical_factor','Factor edge types differ')
            require(0<e['weight']<=1,'Factor contribution invalid');factor_sums[e['source']]+=e['weight']
        if e['relation']=='derived_semantic_neighbor':require(-1<=e['weight']<=1,'Cosine edge range differs')
        for eid in e['evidence_ids']:
            require(eid in graph['evidence'],'Unresolved JSON graph evidence')
            locator=graph['evidence'][eid];row=db.execute('SELECT * FROM evidence WHERE evidence_id=?',(eid,)).fetchone()
            require(row is not None,'Graph evidence absent from database')
            for field in ('source_id','body_sha256','start_character','end_character','span_sha256','words','role'):
                require(locator[field]==row[field],'Graph/database evidence differs')
        if e['relation']=='supported_by':
            require(nodes[e['source']]['type']=='answer_card' and nodes[e['target']]['type']=='source','Support edge types differ')
            cid=nodes[e['source']]['card_id'];sid=nodes[e['target']]['source_id']
            require(cards[cid]['source_id']==sid,'Support edge source differs')
            expected={r[0] for r in db.execute('SELECT evidence_id FROM card_evidence WHERE card_id=?',(cid,))}
            require(set(e['evidence_ids'])==expected,'Support edge evidence differs')
    require(all(close(v,1,1e-8) for v in factor_sums.values()),'Graph factor contribution sums differ')
    xml=ET.parse(root/'graph.graphml').getroot();ns={'g':'http://graphml.graphdrawing.org/xmlns'}
    require({n.attrib['id'] for n in xml.findall('g:graph/g:node',ns)}==set(nodes),'GraphML node IDs differ')
    exported={e.attrib['id']:(e.attrib['source'],e.attrib['target']) for e in xml.findall('g:graph/g:edge',ns)}
    require(exported=={e['id']:(e['source'],e['target']) for e in edges},'GraphML edge endpoints differ')


def verify_metrics(result,sources):
    require(result['coverage']['eligible_sources']==len(sources)==493,'Retrieval source denominator differs')
    require(result['bindings']['queries']['sha256']=='27f6917ea6c2a52569b7ec8ec4b6d9ba06be583342822ecfa24de63ea70d4da8','Frozen query edition differs')
    settings=result['settings'];require(settings['rrf_constant']==60 and settings['rrf_candidate_cutoff']==50,'Frozen fusion differs')
    require(settings['rrf_inputs']==['bm25','tfidf','minilm'],'Fusion methods differ')
    rows=result['queries'];require(Counter(q['query_type'] for q in rows)=={'supported':12,'control':4},'Query denominator differs')
    require(len({q['query_id'] for q in rows})==16,'Repeated query')
    for q in rows:
        known=set(q['known_relevant_source_ids']);require(known<=set(sources),'Unknown judged support source')
        require(set(q['conditions'])=={'bm25','tfidf','minilm','rrf'},'Retrieval condition differs')
        require(0<=q['candidate_union_size']<=150,'RRF candidate union exceeds frozen cutoff')
        for support in q['supports']:
            require(support['body_sha256']==sources[support['source_id']]['body_sha256'],'Query support edition differs')
        for name,c in q['conditions'].items():
            top=c['top_results'];require(len(top)==min(10,c['ranked_sources']),'Top result count differs')
            require(len({r['source_id'] for r in top})==len(top),'Repeated retrieved source')
            for rank,row in enumerate(top,1):
                sid=row['source_id'];require(sid in sources and row['rank']==rank,'Retrieval source/rank differs')
                require(row['citation']['source_id']==sid and row['citation']['body_sha256']==sources[sid]['body_sha256'],'Retrieved citation edition differs')
                require(row['citation']['locator_kind'] in {'highest_BM25_passage_not_judged_answer_evidence','whole_selected_document_not_judged_answer_evidence'},'Unsupported citation adequacy claim')
            m=c['metrics']
            if q['query_type']=='control':require(m is None,'Control given fabricated accuracy metric');continue
            ranks=m['known_support_ranks'];require(set(ranks)==known,'Judged support rank map differs')
            available=[v for v in ranks.values() if v is not None]
            require(all(isinstance(v,int) and 1<=v<=c['ranked_sources'] for v in available),'Known support rank out of range')
            first=min(available) if available else None
            require(m['first_known_support_rank']==first and close(m['reciprocal_rank'],1/first if first else 0),'Reciprocal rank differs')
            topids=[r['source_id'] for r in top]
            for sid,rank in ranks.items():
                if rank is not None and rank<=10:require(topids[rank-1]==sid,'Known support rank contradicts published top results')
            for k in settings['report_k']:
                hit=int(any(v is not None and v<=k for v in ranks.values()));recall=sum(v is not None and v<=k for v in ranks.values())/len(known)
                require(m['hit_at_k'][str(k)]==hit and close(m['known_support_recall_at_k'][str(k)],recall),'Known support metric differs')
    positive=[q for q in rows if q['query_type']=='supported']
    for name,summary in result['summaries'].items():
        metrics=[q['conditions'][name]['metrics'] for q in positive]
        require(summary['supported_queries']==12 and close(summary['mean_reciprocal_rank'],average([m['reciprocal_rank'] for m in metrics])),'MRR summary differs')
        for k in settings['report_k']:
            require(close(summary['hit_at_k'][str(k)],average([m['hit_at_k'][str(k)] for m in metrics])),'Hit summary differs')
            require(close(summary['known_support_recall_at_k'][str(k)],average([m['known_support_recall_at_k'][str(k)] for m in metrics])),'Support recall summary differs')
        families=defaultdict(list)
        for q in positive:
            for family in q['source_family_ids']:families[family].append(q['conditions'][name]['metrics']['reciprocal_rank'])
        require(set(families)==set(summary['source_family_mean_reciprocal_rank']),'Source-family grouping differs')
        for key,values in families.items():require(close(summary['source_family_mean_reciprocal_rank'][key],average(values)),'Family MRR differs')
        require(close(summary['source_family_macro_reciprocal_rank'],average([average(v) for v in families.values()])),'Family macro differs')


def verify(root):
    root=Path(root);meta=read(root/'database.json');graph=read(root/'graph.json');result=read(root/'retrieval.json')
    for value in (meta,graph,result):finite_public(value)
    require(meta['status']=='verified_source_bound_databases' and result['status']=='executed_frozen_source_retrieval_diagnostic','Unexecuted module')
    for key in ('frame','analysis','registry'):
        require(meta['bindings'][key]['sha256']==graph['bindings'][key]['sha256']==result['bindings'][key]['sha256'],'Cross-module input binding differs')
    db,sources,cards,questions=verify_database(root,meta)
    try:verify_graph(root,graph,db,sources,cards,questions);verify_metrics(result,sources)
    finally:db.close()
    for figure in result.get('figures',[]):
        path=Path(figure['file']);require(not path.is_absolute() and '..' not in path.parts,'Unsafe figure filename')
        raw=(root/path).read_bytes();require(len(raw)==figure['bytes'] and hashlib.sha256(raw).hexdigest()==figure['sha256'],'Retrieval plot hash differs')
    return {'status':'passed','sources':len(sources),'records':meta['coverage']['tables']['public']['records'],
        'cards':len(cards),'questions':len(questions),'graph_nodes':graph['coverage']['nodes'],'graph_edges':graph['coverage']['edges'],
        'retrieval_queries':16,'retrieval_conditions':4,'public_fts_exact_composition':True,
        'scope':'Public source/DB/privacy/graph/FTS-composition/metric verification. Private source-span and neural-vector arithmetic checks remain separate.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--public-dir',type=Path,required=True)
    print(json.dumps(verify(parser.parse_args().public_dir)))
