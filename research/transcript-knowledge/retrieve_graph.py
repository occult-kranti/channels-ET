#!/usr/bin/env python3
"""Source-bound SQLite search, typed provenance graph and frozen retrieval audit.

Builds run privately; only their explicit public allowlist may be published.
Semantic similarity never assigns answer agreement or claimed-entity identity.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict, deque
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = {'passage_words':500, 'passage_overlap':0, 'bm25_source_pooling':'maximum passage score',
    'rrf_constant':60, 'rrf_candidate_cutoff':50, 'rrf_inputs':['bm25','tfidf','minilm'],
    'rrf_tail':'unchanged MiniLM order outside the candidate union', 'report_k':[1,3,5,10],
    'published_top_results':10, 'corpus_embedding_refit':False,
    'scope':'Source-informed, partially judged retrieval diagnostic; no answer accuracy or calibrated abstention.'}
RECORD_TYPES = {'observed_question_answer','unverified_question_candidate','generated_reading_prompt','curated_comparison'}
RELATIONS = {
    'published_by':{'origin':'source_metadata','meaning':'Publication belongs to this publishing context; no complete upload census.'},
    'attributed_context':{'origin':'source_metadata','meaning':'Source-level attribution context, not verified utterance identity.'},
    'observed_label':{'origin':'source_metadata','meaning':'Exact source-supplied claimed label, not an authenticated shared entity.'},
    'factor_weight':{'origin':'derived_fixed_model','meaning':'Existing canonical normalized NMF contribution; not doctrine prevalence.','weight_units':'normalized NMF contribution'},
    'asks':{'origin':'curated_annotation','meaning':'The bounded analyst or documentary question belongs to its explicitly labeled origin.'},
    'responds_to':{'origin':'curated_annotation','meaning':'A qualified source-reading card addresses an analyst or documentary question.'},
    'supported_by':{'origin':'checked_source_locator','meaning':'Paraphrase is tied to inspected source spans; truth and recognition accuracy remain unverified.'},
    'derived_semantic_neighbor':{'origin':'derived_fixed_model','meaning':'Existing mutual-three nearest neighbor; not agreement, identity or causality.','weight_units':'original-space MiniLM cosine'},
}
FROZEN_QUERY_SHA256 = '27f6917ea6c2a52569b7ec8ec4b6d9ba06be583342822ecfa24de63ea70d4da8'


def public_check(value):
    raw=json_text(value)
    require(not any(x in raw for x in ('/workspace/','/dev/shm/','channels-et-private','"full_text"','"extractive_summary"')),'Private source/path field in public metadata')
    return value


def safe_question(row):
    value={k:row[k] for k in ('question_id','question_type','question','topic_id','selection_basis',
        'informed_by_answer_reading','question_origin','origin','role_uncertainty','source_id',
        'documentary_question_id','conditions','qualification','extracted_question_id') if k in row}
    binding=row.get('documentary_binding')
    if binding:value['documentary_binding']={k:binding[k] for k in ('source_id','body_sha256','selected_edition_id','question_id','turn_ids','start_character','end_character','span_sha256') if k in binding}
    return public_check(value)


def safe_card(row):
    value={k:row[k] for k in ('card_id','question_id','source_id','paraphrase','claim_type','conditions',
        'time_scope','qualifying_note','legacy_card_id','legacy_question_id','index_text_policy','selected_edition_id','body_sha256') if k in row}
    if 'annotation' in row:value['annotation']={k:row['annotation'][k] for k in ('annotator_type','role','human_validated',
        'audio_listened','identity_verified','source_inspection_scope') if k in row['annotation']}
    return public_check(value)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(Path(path).read_text())
def dump(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def reference(path):
    path=Path(path);return {'file':path.name,'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def require(condition,message):
    if not condition: raise ValueError(message)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
def json_text(value): return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def json_lines(path):
    with Path(path).open() as stream:
        for line in stream:
            if line.strip():yield json.loads(line)


def source_frame(path):
    return module('transcript_source_frame',ROOT/'research/channel-lab/sources.py').load_frame(path)


def public_metadata(record):
    fields=('source_id','title','source_url','channel_id','channel_name','creator_id','creator_name',
        'publisher_id','publisher_name','publication_date','text_origin','document_kind','selected_edition_id',
        'body_sha256','words','claimed_labels','attribution_scope','speaker_role','language_eligible')
    out={key:record.get(key) for key in fields}
    out['text_artifact_sha256']=record['text_artifact']['sha256']
    return out


def passage_rows(docs):
    for doc in docs:
        r,text=doc['record'],doc['text'];parts=list(re.finditer(r'\S+',text))
        require(len(parts)==r['words'],'Source word accounting differs')
        for start in range(0,len(parts),SETTINGS['passage_words']):
            selected=parts[start:start+SETTINGS['passage_words']];a,b=selected[0].start(),selected[-1].end()
            yield {'passage_id':'passage:'+r['source_id']+':'+str(start),'source_id':r['source_id'],
                'start_character':a,'end_character':b,'word_start':start,'word_end':start+len(selected),
                'span_sha256':sha(text[a:b].encode()),'text':text[a:b]}


def safe_record(row):
    blocked={'question_text','answer_text','context_text','text','supports','text_artifact','private_path'}
    allowed={'record_id','type','source_id','selected_edition_id','body_sha256','question_origin',
        'answer_status','speaker_status','topic_terms','conditions_status','time_scope_status',
        'extraction_rule','extraction_method','question_kind','answer_boundary_status','question_id',
        'question_number','session_number','documentary_question_id','turn_ids','flags','reading_status',
        'context_words','answer_words','question_words'}
    allowed.update({'display_question','question_text_available','answer_paraphrase','addressed_to_claimed_entity_verified',
        'printed_question_id','question_span','answer_spans','context_span','question_boundary_scope','context_boundary_scope'})
    return {k:v for k,v in row.items() if k in allowed and k not in blocked}


def evidence_row(support,source,body):
    a=support.get('start_character',support.get('char_start'));b=support.get('end_character',support.get('char_end'))
    require(isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(body),'Invalid evidence character span')
    require(support.get('source_id',source['source_id'])==source['source_id'],'Evidence source mismatch')
    require(support.get('body_sha256',source['body_sha256'])==source['body_sha256'],'Evidence edition mismatch')
    require(sha(body[a:b].encode())==support['span_sha256'],'Evidence span hash differs')
    if 'text' in support: require(support['text']==body[a:b],'Evidence quoted slice differs')
    if 'words' in support: require(support['words']==len(body[a:b].split()),'Evidence word count differs')
    if 'text_artifact_sha256' in support:require(support['text_artifact_sha256']==source['text_artifact']['sha256'],'Evidence artifact differs')
    role=support.get('role','unknown')
    identity=[source['source_id'],source['body_sha256'],a,b,support['span_sha256'],role]
    return {'evidence_id':support.get('evidence_id') or 'evidence:'+sha(json_text(identity).encode())[:24],
        'source_id':source['source_id'],'body_sha256':source['body_sha256'],
        'start_character':a,'end_character':b,'span_sha256':support['span_sha256'],
        'words':len(body[a:b].split()),'role':role,'text':body[a:b],
        'metadata':public_check({'text_artifact_sha256':source['text_artifact']['sha256'],
            **{k:support[k] for k in ('turn_ids','start_seconds','end_seconds','audio_alignment_verified') if k in support}})}


SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE meta(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE sources(source_id TEXT PRIMARY KEY,title TEXT,source_url TEXT,channel_id TEXT,creator_id TEXT,
 publication_date TEXT,text_origin TEXT,body_sha256 TEXT NOT NULL,selected_edition_id TEXT,words INTEGER,
 metadata_json TEXT NOT NULL,body TEXT);
CREATE TABLE profiles(source_id TEXT PRIMARY KEY REFERENCES sources(source_id),profile_json TEXT NOT NULL);
CREATE TABLE records(record_id TEXT PRIMARY KEY,type TEXT NOT NULL,source_id TEXT REFERENCES sources(source_id),
 question_origin TEXT,answer_status TEXT,speaker_status TEXT,question_text TEXT,answer_text TEXT,context_text TEXT,
 metadata_json TEXT NOT NULL);
CREATE TABLE questions(question_id TEXT PRIMARY KEY,question_type TEXT,question TEXT,metadata_json TEXT NOT NULL);
CREATE TABLE cards(card_id TEXT PRIMARY KEY,question_id TEXT REFERENCES questions(question_id),source_id TEXT REFERENCES sources(source_id),
 paraphrase TEXT,conditions TEXT,time_scope TEXT,qualifying_note TEXT,metadata_json TEXT NOT NULL);
CREATE TABLE evidence(evidence_id TEXT PRIMARY KEY,source_id TEXT REFERENCES sources(source_id),body_sha256 TEXT NOT NULL,
 start_character INTEGER,end_character INTEGER,span_sha256 TEXT NOT NULL,words INTEGER,role TEXT,text TEXT,metadata_json TEXT NOT NULL);
CREATE TABLE record_evidence(record_id TEXT REFERENCES records(record_id),evidence_id TEXT REFERENCES evidence(evidence_id),PRIMARY KEY(record_id,evidence_id));
CREATE TABLE card_evidence(card_id TEXT REFERENCES cards(card_id),evidence_id TEXT REFERENCES evidence(evidence_id),PRIMARY KEY(card_id,evidence_id));
CREATE TABLE passages(passage_id TEXT PRIMARY KEY,source_id TEXT REFERENCES sources(source_id),start_character INTEGER,
 end_character INTEGER,word_start INTEGER,word_end INTEGER,span_sha256 TEXT,text TEXT);
CREATE INDEX records_source ON records(source_id,type);
CREATE INDEX evidence_source ON evidence(source_id);
CREATE INDEX source_filters ON sources(channel_id,creator_id,text_origin,publication_date);
CREATE VIRTUAL TABLE public_search USING fts5(item_id UNINDEXED,item_type UNINDEXED,source_id UNINDEXED,text,tokenize='unicode61 remove_diacritics 2');
'''


def init_database(path,private):
    require(not Path(path).exists(),'Refusing to overwrite a database edition')
    db=sqlite3.connect(path);db.executescript(SCHEMA)
    if private:db.execute("CREATE VIRTUAL TABLE passage_search USING fts5(passage_id UNINDEXED,source_id UNINDEXED,text,tokenize='unicode61 remove_diacritics 2')")
    db.execute('INSERT INTO meta VALUES (?,?)',('scope',json_text('private_exact_evidence' if private else 'public_annotations_only')))
    return db


def insert_evidence(dbs,row):
    for db,private in dbs:
        previous=db.execute('SELECT source_id,body_sha256,start_character,end_character,span_sha256,role FROM evidence WHERE evidence_id=?',(row['evidence_id'],)).fetchone()
        if previous:require(tuple(previous)==tuple(row[k] for k in ('source_id','body_sha256','start_character','end_character','span_sha256','role')),'Evidence ID reused for different support')
        db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)',(
            row['evidence_id'],row['source_id'],row['body_sha256'],row['start_character'],row['end_character'],
            row['span_sha256'],row['words'],row['role'],row['text'] if private else None,json_text(row['metadata'])))


def build_databases(docs,profiles,records_path,curated,out,bindings):
    bodies={d['record']['source_id']:d['text'] for d in docs};sources={d['record']['source_id']:d['record'] for d in docs}
    dbs=[(init_database(out/'database-private.sqlite',True),True),(init_database(out/'database-public.sqlite',False),False)]
    counts=Counter();card_evidence=defaultdict(list)
    for db,private in dbs:
        db.execute('INSERT INTO meta VALUES (?,?)',('bindings',json_text(bindings)))
        for doc in docs:
            r=doc['record'];db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(
                r['source_id'],r['title'],r['source_url'],r['channel_id'],r['creator_id'],r.get('publication_date'),
                r['text_origin'],r['body_sha256'],r['selected_edition_id'],r['words'],json_text(public_metadata(r)),doc['text'] if private else None))
    seen_profiles=set()
    for p in profiles['profiles']:
        sid=p['source_id'];require(sid in sources and p['body_sha256']==sources[sid]['body_sha256'],'Profile selected edition differs')
        require(sid not in seen_profiles,'Duplicate profile');seen_profiles.add(sid)
        approved=' '.join([sources[sid]['title'],p.get('summary',''),
            *[x['term'] for x in p.get('top_terms',[])],*[x['label'] for x in p.get('topic_profile',[])]])
        require(not any(x in json_text(p) for x in ('/workspace/','/dev/shm/','"extractive_summary"','"full_text"')),'Private profile field')
        for db,_ in dbs:
            db.execute('INSERT INTO profiles VALUES (?,?)',(sid,json_text(p)))
            db.execute('INSERT INTO public_search VALUES (?,?,?,?)',('profile:'+sid,'source_profile',sid,approved))
    require(seen_profiles==set(sources),'Profiles do not cover the exact source universe')
    for row in json_lines(records_path):
        sid=row['source_id'];require(sid in sources,'Unknown extracted-record source')
        require(row['type'] in RECORD_TYPES,'Unknown extracted record type')
        require(row['body_sha256']==sources[sid]['body_sha256'] and row['selected_edition_id']==sources[sid]['selected_edition_id'],'Record selected edition differs')
        safe=public_check(safe_record(row));counts[row['type']]+=1
        for db,private in dbs:
            db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)',(
                row['record_id'],row['type'],sid,row.get('question_origin'),row.get('answer_status'),row.get('speaker_status'),
                row.get('question_text') if private else None,row.get('answer_text') if private else None,
                row.get('context_text') if private else None,json_text(safe)))
        for support in row.get('supports',[]):
            proof=evidence_row(support,sources[sid],bodies[sid]);insert_evidence(dbs,proof)
            for db,_ in dbs:db.execute('INSERT OR IGNORE INTO record_evidence VALUES (?,?)',(row['record_id'],proof['evidence_id']))
    questions={q['question_id']:safe_question(q) for q in curated['questions']}
    require(len(questions)==len(curated['questions']),'Duplicate curated question')
    for q in questions.values():
        for db,_ in dbs:db.execute('INSERT INTO questions VALUES (?,?,?,?)',(q['question_id'],q['question_type'],q['question'],json_text(q)))
    for support in curated.get('evidence',[]):
        sid=support['source_id'];require(sid in sources,'Curated evidence source missing')
        proof=evidence_row(support,sources[sid],bodies[sid]);insert_evidence(dbs,proof)
    indexed_questions=set()
    for card in curated['cards']:
        sid=card['source_id'];require(sid in sources and card['question_id'] in questions,'Curated source/question missing')
        require(card.get('supports'),'Curated card lacks source evidence')
        metadata=safe_card(card)
        text=' '.join(str(card.get(k,'')) for k in ('paraphrase','conditions','time_scope','qualifying_note'))
        # Curated question wording is indexed as a separate public item, never appended to answer text.
        for db,_ in dbs:
            db.execute('INSERT INTO cards VALUES (?,?,?,?,?,?,?,?)',(card['card_id'],card['question_id'],sid,
                card['paraphrase'],card.get('conditions',''),card.get('time_scope',''),card.get('qualifying_note',''),json_text(metadata)))
            db.execute('INSERT INTO public_search VALUES (?,?,?,?)',('card:'+card['card_id'],'qualified_answer_card',sid,text))
            if (card['question_id'],sid) not in indexed_questions:
                db.execute('INSERT INTO public_search VALUES (?,?,?,?)',('question:'+card['question_id']+':'+sid,'curated_question',sid,questions[card['question_id']]['question']))
        indexed_questions.add((card['question_id'],sid))
        for support in card['supports']:
            require(support.get('body_sha256')==sources[sid]['body_sha256'],'Curated card cannot transfer across editions')
            proof=evidence_row(support,sources[sid],bodies[sid]);insert_evidence(dbs,proof)
            card_evidence[card['card_id']].append(proof['evidence_id'])
            for db,_ in dbs:db.execute('INSERT OR IGNORE INTO card_evidence VALUES (?,?)',(card['card_id'],proof['evidence_id']))
    passage_count=0
    for row in passage_rows(docs):
        db=dbs[0][0];db.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?)',tuple(row[k] for k in (
            'passage_id','source_id','start_character','end_character','word_start','word_end','span_sha256','text')))
        db.execute('INSERT INTO passage_search VALUES (?,?,?)',(row['passage_id'],row['source_id'],row['text']));passage_count+=1
    accounting={}
    for db,private in dbs:
        db.commit();require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity check failed')
        require(db.execute('PRAGMA foreign_key_check').fetchall()==[],'SQLite foreign-key check failed')
        tables=('sources','profiles','records','questions','cards','evidence','record_evidence','card_evidence','passages','public_search')
        tally={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in tables}
        if not private:
            for table,fields in [('sources',['body']),('records',['question_text','answer_text','context_text']),('evidence',['text'])]:
                for field in fields:require(db.execute('SELECT COUNT(*) FROM '+table+' WHERE '+field+' IS NOT NULL').fetchone()[0]==0,'Raw source content leaked into public database')
            require(tally['passages']==0,'Private passages leaked')
        accounting['private' if private else 'public']=tally;db.close()
    return {'records_by_type':dict(counts),'passages':passage_count,'tables':accounting},dict(card_evidence)


def make_graph(docs,analysis,curated,card_evidence,counts,bindings,evidence_map=None):
    nodes={};edges=[]
    def node(identifier,kind,label,**extra):
        value={'id':identifier,'type':kind,'label':label,**extra}
        if identifier in nodes:require(nodes[identifier]==value,'Graph node identity collision')
        else:nodes[identifier]=value
    def edge(a,b,relation,evidence_ids=None,weight=None):
        value={'id':'edge:'+sha(json_text([a,b,relation]).encode())[:24],
            'source':a,'target':b,'relation':relation,'origin':RELATIONS[relation]['origin'],
            'evidence_ids':sorted(set(evidence_ids or []))}
        if weight is not None:value['weight']=float(weight)
        edges.append(value)
    for topic in analysis['topics']:node('topic:'+topic['topic_id'],'lexical_factor',topic['label'],topic_id=topic['topic_id'])
    features={d['source_id']:d for d in analysis['documents']}
    for d in docs:
        r=d['record'];sid=r['source_id'];source='source:'+sid
        node(source,'source',r['title'],source_id=sid,channel_id=r['channel_id'],creator_id=r['creator_id'],
            publication_date=r.get('publication_date'),text_origin=r['text_origin'])
        channel='channel:'+r['channel_id'];creator='creator:'+r['creator_id']
        node(channel,'publisher_context',r['channel_name'],channel_id=r['channel_id'])
        node(creator,'creator_context',r['creator_name'],creator_id=r['creator_id'])
        edge(source,channel,'published_by');edge(source,creator,'attributed_context')
        for label in sorted(set(r.get('claimed_labels',[]))):
            label_id='label:'+sha(label.encode())[:16];node(label_id,'observed_claimed_label',label);edge(source,label_id,'observed_label')
        for topic,weight in zip(analysis['topics'],features[sid]['topic_weights']):
            if weight>0:edge(source,'topic:'+topic['topic_id'],'factor_weight',weight=weight)
    sources_by_question=defaultdict(set)
    for card in curated['cards']:sources_by_question[card['question_id']].add(card['source_id'])
    for q in curated['questions']:
        node('question:'+q['question_id'],'question',q['question'],question_id=q['question_id'],source_ids=sorted(sources_by_question[q['question_id']]),status=q['question_type'])
    for card in curated['cards']:
        sid=card['source_id'];cid='card:'+card['card_id'];qid='question:'+card['question_id']
        node(cid,'answer_card',card['paraphrase'],source_id=sid,record_id=card['card_id'],card_id=card['card_id'],status=card.get('claim_type','curated_source_reading'))
        edge(cid,qid,'responds_to');edge(cid,'source:'+sid,'supported_by',card_evidence[card['card_id']])
    for e in analysis['graph']['semantic']['edges']:
        edge('source:'+e['source'],'source:'+e['target'],'derived_semantic_neighbor',weight=e['similarity'])
    require(len({e['id'] for e in edges})==len(edges),'Duplicate graph edge')
    require(all(e['source'] in nodes and e['target'] in nodes for e in edges),'Dangling graph edge')
    return {'schema_version':1,'status':'source_bound_typed_graph','bindings':bindings,
        'coverage':{'nodes':len(nodes),'edges':len(edges),'nodes_by_type':dict(Counter(n['type'] for n in nodes.values())),
            'edges_by_relation':dict(Counter(e['relation'] for e in edges)),
            'eligible_record_types':[],'included_annotation_types':['curated_question','qualified_answer_card'],
            'omitted_record_counts':counts['records_by_type'],
            'omission_scope':'All extraction records remain queryable in the database and source shards; compact primary graph contains only curated question/card interpretations.'},
        'node_types':sorted({n['type'] for n in nodes.values()}),'relation_types':RELATIONS,
        'nodes':sorted(nodes.values(),key=lambda x:x['id']),'edges':sorted(edges,key=lambda x:x['id']),
        'evidence':evidence_map or {},
        'limitations':['Shared labels, factor paths and cosine edges do not establish agreement, shared identity or causality.',
            'Creator IDs are attribution contexts, not unique verified people. Publisher contexts are not independent mediums.',
            'Question/card links retain their annotation origin. Extracted punctuation candidates are not asserted answers.',
            'Semantic neighbors are derived from the existing frozen fit and excluded from default provenance traversal.']}


def build(frame_path,analysis_path,profiles_path,records_path,curated_path,output):
    out=Path(output);require(not out.exists(),'Use a new immutable build directory');out.mkdir(parents=True)
    docs=source_frame(frame_path);analysis=load(analysis_path);profiles=load(profiles_path);curated=load(curated_path)
    require(analysis['bindings']['frame_sha256']==sha(Path(frame_path).read_bytes()),'Analysis frame binding differs')
    require([x['record']['source_id'] for x in docs]==[x['source_id'] for x in analysis['documents']],'Analysis source order differs')
    bindings={key:reference(path) for key,path in [('frame',frame_path),('analysis',analysis_path),('profiles',profiles_path),('records',records_path),('curated',curated_path)]}
    bindings['registry']=reference(Path(frame_path).parent/'registry.json')
    bindings['script_sha256']=sha(Path(__file__).read_bytes())
    counts,proofs=build_databases(docs,profiles,records_path,curated,out,bindings)
    with open_readonly(out/'database-public.sqlite') as db:
        evidence_map={}
        for row in db.execute('SELECT DISTINCT e.* FROM evidence e JOIN card_evidence c USING(evidence_id)'):
            value=dict(row);value.pop('text');value.update(json.loads(value.pop('metadata_json')));evidence_map[value['evidence_id']]=value
    graph=make_graph(docs,analysis,curated,proofs,counts,bindings,evidence_map);public_check(graph);dump(out/'graph.json',graph)
    graphml(graph,out/'graph.graphml')
    metadata={'schema_version':1,'status':'verified_source_bound_databases','bindings':bindings,
        'coverage':{'sources':len(docs),'words':sum(d['record']['words'] for d in docs),**counts},
        'tables':list(counts['tables']['public']),'public_database':reference(out/'database-public.sqlite'),
        'search_scope':{'public':'Source metadata, explicitly automated lexical outlines and curated questions/qualified cards; no original transcript bodies.',
            'private':'Exact selected source bodies,500-word source-position passages, extracted question/answer text and checked evidence.'},
        'limitations':['FTS candidates are lexical matches, not verified answers. Conditions and exact evidence must be inspected.',
            'Public extraction records carry statuses and locators; their raw documentary text is private.',
            'Text-position passages are not audio timestamps. Source claims and machine recognition are unverified.']}
    dump(out/'database.json',metadata)
    dump(out/'output-manifest.json',{'complete':True,'public_allowlist':[reference(out/name) for name in ('database.json','graph.json','graph.graphml','database-public.sqlite')]})
    print(json_text(metadata['coverage']))


def graphml(graph,path):
    import xml.etree.ElementTree as ET
    namespace='http://graphml.graphdrawing.org/xmlns';ET.register_namespace('',namespace)
    tag=lambda name:'{'+namespace+'}'+name
    root=ET.Element(tag('graphml'))
    for key,scope,name,kind in [('node_type','node','type','string'),('node_label','node','label','string'),
        ('node_metadata','node','metadata_json','string'),('edge_relation','edge','relation','string'),
        ('edge_origin','edge','origin','string'),('edge_evidence','edge','evidence_ids_json','string'),('edge_weight','edge','weight','double')]:
        ET.SubElement(root,tag('key'),{'id':key,'for':scope,'attr.name':name,'attr.type':kind})
    body=ET.SubElement(root,tag('graph'),{'id':'source-bound-provenance','edgedefault':'directed'})
    for node in graph['nodes']:
        out=ET.SubElement(body,tag('node'),{'id':node['id']})
        for key,value in [('node_type',node['type']),('node_label',node['label']),('node_metadata',json_text(node))]:
            ET.SubElement(out,tag('data'),{'key':key}).text=value
    for edge in graph['edges']:
        out=ET.SubElement(body,tag('edge'),{'id':edge['id'],'source':edge['source'],'target':edge['target'],
            'directed':'false' if edge['relation']=='derived_semantic_neighbor' else 'true'})
        for key,value in [('edge_relation',edge['relation']),('edge_origin',edge['origin']),('edge_evidence',json_text(edge['evidence_ids']))]:
            ET.SubElement(out,tag('data'),{'key':key}).text=value
        if 'weight' in edge:ET.SubElement(out,tag('data'),{'key':'edge_weight'}).text=str(edge['weight'])
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def open_readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db


def fts_expression(text):
    terms=list(dict.fromkeys(re.findall(r'[^\W_]+',text.casefold(),flags=re.UNICODE)))[:64]
    return ' OR '.join('"'+term.replace('"','""')+'"' for term in terms)


def source_filter(db,channel=None,creator=None,origin=None,after=None,before=None):
    for value in (after,before):
        if value is not None:require(dt.date.fromisoformat(value).isoformat()==value,'Dates must be ISO YYYY-MM-DD')
    where=[];args=[]
    for field,value,operator in [('channel_id',channel,'='),('creator_id',creator,'='),('text_origin',origin,'='),('substr(publication_date,1,10)',after,'>='),('substr(publication_date,1,10)',before,'<=')]:
        if value is not None:where.append(field+operator+'?');args.append(value)
    sql='SELECT source_id FROM sources'+(' WHERE '+' AND '.join(where) if where else '')
    return {row[0] for row in db.execute(sql,args)}


def bm25_sources(db,text,allowed=None):
    expression=fts_expression(text)
    if not expression:return []
    best={}
    sql='''SELECT f.source_id,f.passage_id,bm25(passage_search) AS distance,
      p.start_character,p.end_character,p.span_sha256,p.word_start,p.word_end
      FROM passage_search f JOIN passages p ON p.passage_id=f.passage_id
      WHERE passage_search MATCH ? ORDER BY distance,f.passage_id'''
    for row in db.execute(sql,(expression,)):
        sid=row['source_id']
        if allowed is not None and sid not in allowed:continue
        if sid not in best:
            value=dict(row);value['score']=-value.pop('distance');best[sid]=value
    return sorted(best.values(),key=lambda x:(-x['score'],x['source_id']))


def search(database,text,scope='public',limit=20,**filters):
    require(1<=limit<=200,'Limit must be between1 and200')
    with open_readonly(database) as db:
        allowed=source_filter(db,**filters)
        if scope=='private':
            require(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='passage_search'").fetchone()[0]==1,'Full-transcript search requires the private database')
            rows=bm25_sources(db,text,allowed)[:limit]
            for row in rows:
                source=db.execute('SELECT title,source_url,body_sha256 FROM sources WHERE source_id=?',(row['source_id'],)).fetchone();row.update(dict(source))
            return {'scope':'private_passage_BM25','matches':rows,'eligible_sources':len(allowed),'query_expression':fts_expression(text)}
        expression=fts_expression(text)
        rows=[]
        if expression:
            sql='SELECT item_id,item_type,source_id,bm25(public_search) AS distance FROM public_search WHERE public_search MATCH ? ORDER BY distance,item_id'
            for row in db.execute(sql,(expression,)):
                if row['source_id'] not in allowed:continue
                value=dict(row);value['score']=-value.pop('distance');rows.append(value)
                if len(rows)>=limit:break
        return {'scope':'public_metadata_and_annotations_only','matches':rows,'eligible_sources':len(allowed),'query_expression':expression}


def exact_evidence(database,evidence_id):
    with open_readonly(database) as db:
        row=db.execute('SELECT e.*,s.title,s.source_url FROM evidence e JOIN sources s USING(source_id) WHERE evidence_id=?',(evidence_id,)).fetchone()
        require(row is not None,'Unknown evidence ID');value=dict(row)
        if value['text'] is not None:require(sha(value['text'].encode())==value['span_sha256'],'Stored exact evidence changed')
        value['access_scope']='exact_private_slice' if value['text'] is not None else 'public_locator_only'
        return value


def graph_paths(graph,start,hops=2,relations=None,channel=None,source_ids=None,limit=200,creator=None,origin=None,after=None,before=None):
    require(hops in (1,2) and 1<=limit<=2000,'Graph paths require1–2 hops and limit1–2000')
    nodes={n['id']:n for n in graph['nodes']};require(start in nodes,'Unknown graph start node')
    allowed_relations=set(relations) if relations else set(RELATIONS)-{'derived_semantic_neighbor'}
    require(allowed_relations<=set(RELATIONS),'Unknown graph relation filter')
    for value in (after,before):
        if value is not None:require(dt.date.fromisoformat(value).isoformat()==value,'Dates must be ISO YYYY-MM-DD')
    def source_selected(n):
        date=(n.get('publication_date') or '')[:10]
        return (n['type']=='source' and (channel is None or n['channel_id']==channel)
            and (creator is None or n.get('creator_id')==creator) and (origin is None or n.get('text_origin')==origin)
            and (after is None or bool(date) and date>=after) and (before is None or bool(date) and date<=before))
    allowed_sources={n['source_id'] for n in nodes.values() if source_selected(n)}
    if source_ids is not None:allowed_sources&=set(source_ids)
    def eligible(n):
        if n.get('source_id'):return n['source_id'] in allowed_sources
        if n['type']=='question':return bool(set(n.get('source_ids',[]))&allowed_sources)
        return True
    eligible_nodes={key for key,n in nodes.items() if eligible(n)}
    require(start in eligible_nodes,'Start node is outside selected source filters')
    edges=[e for e in graph['edges'] if e['relation'] in allowed_relations and e['source'] in eligible_nodes and e['target'] in eligible_nodes]
    adjacent=defaultdict(list)
    for e in edges:adjacent[e['source']].append(e);adjacent[e['target']].append(e)
    queue=deque([(start,[start],[])]);paths=[];truncated=False
    while queue:
        current,visited,steps=queue.popleft()
        if len(steps)==hops:continue
        for edge in sorted(adjacent[current],key=lambda e:e['id']):
            other=edge['target'] if edge['source']==current else edge['source']
            if other in visited:continue
            path={'nodes':visited+[other],'edges':[x['id'] for x in steps]+[edge['id']],
                'relations':[x['relation'] for x in steps]+[edge['relation']],
                'evidence_ids':sorted({p for x in steps+[edge] for p in x['evidence_ids']})}
            chain=visited+[other]
            path['traversals']=[{'edge_id':e['id'],'from':chain[i],'to':chain[i+1],
                'direction':'undirected_derived' if e['relation']=='derived_semantic_neighbor' else 'forward' if e['source']==chain[i] else 'reverse'} for i,e in enumerate(steps+[edge])]
            if len(paths)>=limit:truncated=True;queue.clear();break
            paths.append(path);queue.append((other,visited+[other],steps+[edge]))
    return {'start':start,'hops':hops,'paths':paths,'truncated':truncated,'limit':limit,
        'eligible_sources':len(allowed_sources),'relations':sorted(allowed_relations),
        'scope':'Typed undirected navigation paths preserve directed edge relations; they are provenance/navigation, not causal or answer inference.'}


def rank_metrics(ranking,known):
    ids=[x['source_id'] for x in ranking];require(len(ids)==len(set(ids)),'Repeated ranked source')
    ranks={sid:ids.index(sid)+1 if sid in ids else None for sid in known}
    present=[x for x in ranks.values() if x is not None];first=min(present) if present else None
    return {'known_support_ranks':ranks,'first_known_support_rank':first,
        'reciprocal_rank':1/first if first else 0.,
        'hit_at_k':{str(k):int(any(s in known for s in ids[:k])) for k in SETTINGS['report_k']},
        'known_support_recall_at_k':{str(k):sum(s in known for s in ids[:k])/len(known) if known else None for k in SETTINGS['report_k']}}


def rrf(conditions):
    scores=defaultdict(float)
    for name in SETTINGS['rrf_inputs']:
        for rank,row in enumerate(conditions[name][:SETTINGS['rrf_candidate_cutoff']],1):
            scores[row['source_id']]+=1/(SETTINGS['rrf_constant']+rank)
    ranked=[{'source_id':sid,'score':score,'rank_origin':'candidate_fusion'} for sid,score in sorted(scores.items(),key=lambda x:(-x[1],x[0]))]
    ranked.extend({'source_id':r['source_id'],'score':None,'rank_origin':'minilm_tail_fallback'} for r in conditions['minilm'] if r['source_id'] not in scores)
    return ranked


def validate_audit(audit,docs,frame_sha):
    require(audit['frame_sha256']==frame_sha,'Query frame differs')
    require(len(audit['queries'])==16 and Counter(q['query_type'] for q in audit['queries'])=={'supported':12,'control':4},'Frozen query scope differs')
    source={d['record']['source_id']:d for d in docs};seen=set()
    for q in audit['queries']:
        require(q['query_id'] not in seen and q['query'].strip(),'Repeated/empty query');seen.add(q['query_id'])
        known=q['known_relevant_source_ids'];require(len(known)==len(set(known)) and set(known)<=set(source),'Unknown support source')
        if q['query_type']=='supported':require(known,'Supported query needs inspected positive support')
        else:require(not known,'Control query must not have fabricated gold negatives/positives')
        supported=set()
        for span in q['supports']:
            doc=source[span['source_id']];evidence_row(span,doc['record'],doc['text']);supported.add(span['source_id'])
        require(set(known)<=supported,'Relevance source lacks checked exact evidence')


def retrieval_figures(result,out):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    queries=[q for q in result['queries'] if q['query_type']=='supported'];methods=['bm25','tfidf','minilm','rrf']
    labels=['Passage BM25','Full TF-IDF','Full MiniLM','Top50 RRF']
    values=np.array([[q['conditions'][m]['metrics']['first_known_support_rank'] or np.nan for m in methods] for q in queries])
    fig,(ax,summary)=plt.subplots(1,2,figsize=(15,8),gridspec_kw={'width_ratios':[1.8,1]})
    image=ax.imshow(values,aspect='auto',cmap='viridis_r',norm=LogNorm(vmin=1,vmax=493))
    ax.set_xticks(range(4),labels,rotation=22,ha='right')
    ax.set_yticks(range(len(queries)),[q['query_id']+' · '+q['question_family'].replace('_',' ') for q in queries])
    ax.set_title('First inspected support source rank · lower is better')
    for i,row in enumerate(values):
        for j,value in enumerate(row):
            ax.text(j,i,'No match' if not np.isfinite(value) else str(int(value)),ha='center',va='center',
                color='black' if not np.isfinite(value) or value<20 else 'white',fontsize=9)
    fig.colorbar(image,ax=ax,fraction=.045,pad=.04,label='Rank, logarithmic color scale')
    mrr=[result['summaries'][m]['mean_reciprocal_rank'] for m in methods]
    hit=[result['summaries'][m]['hit_at_k']['5'] for m in methods]
    y=np.arange(4);summary.barh(y-.18,mrr,.34,label='Mean reciprocal rank',color='#287a94')
    summary.barh(y+.18,hit,.34,label='Known-support Hit@5',color='#c28a32')
    summary.set_yticks(y,labels);summary.set_xlim(0,1);summary.invert_yaxis();summary.legend(loc='lower right')
    summary.set_xlabel('Descriptive score across 12 source-informed questions')
    summary.set_title('Known support only · unjudged ≠ irrelevant')
    fig.suptitle('Frozen retrieval diagnostic on 493 canonical source editions',fontsize=15)
    fig.text(.5,.015,'No blind human gold labels or answer-accuracy test. Four ambiguity controls are shown separately in the dashboard.\nBM25 passage input, full-document vectors and source lengths differ; all methods retain exact source citations.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.07,1,.95));directory=out/'figures';directory.mkdir()
    refs=[]
    for extension in ('png','svg','pdf'):
        path=directory/('retrieval-diagnostic.'+extension);fig.savefig(path,dpi=135,bbox_inches='tight')
        refs.append({**reference(path),'file':'figures/'+path.name,'title':'Frozen source-retrieval diagnostic',
            'alt':'Twelve per-query known-support ranks and aggregate reciprocal rank/Hit@5 for BM25, frozen TF-IDF, frozen MiniLM and fixed top50 fusion. This is not answer accuracy.'})
    plt.close(fig);return refs


def evaluate(database,frame_path,analysis_path,witness,model_path,query_path,output):
    """Encode only the frozen questions; reuse all existing document representations."""
    import numpy as np
    from scipy.sparse import load_npz
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    out=Path(output);require(not out.exists(),'Use a fresh evaluation directory');out.mkdir(parents=True)
    require(sha(Path(query_path).read_bytes())==FROZEN_QUERY_SHA256,'Frozen independent questions required')
    code_sha=sha(Path(__file__).read_bytes());docs=source_frame(frame_path);analysis=load(analysis_path);audit=load(query_path)
    frame_sha=sha(Path(frame_path).read_bytes());validate_audit(audit,docs,frame_sha)
    require(analysis['bindings']['frame_sha256']==frame_sha,'Evaluation analysis frame differs')
    ids=[d['record']['source_id'] for d in docs];records={d['record']['source_id']:d['record'] for d in docs}
    body_lengths={d['record']['source_id']:len(d['text']) for d in docs}
    core=np.load(Path(witness)/'core-vectors.npz',allow_pickle=False)
    require(core['source_ids'].tolist()==ids,'Frozen vector row identity differs')
    semantic=core['semantic'];require(semantic.shape==(493,384) and np.isfinite(semantic).all(),'Invalid frozen document embeddings')
    require(np.allclose(np.linalg.norm(semantic,axis=1),1,atol=1e-10),'Frozen semantic norms differ')
    lexical=load_npz(Path(witness)/'lexical.npz');features=core['features'].tolist();idf=core['idf']
    require(lexical.shape==(493,len(features)) and len(features)==24000,'Frozen lexical witness shape differs')
    # The existing analysis helper is loaded unchanged; source-code SHA is checked.
    lab=ROOT/'research/channel-lab';require(sha((lab/'analyze_corpus.py').read_bytes())==analysis['bindings']['script_sha256'],'Frozen analysis helper changed')
    sys.path.insert(0,str(lab));helper=module('transcript_frozen_analysis_helper',lab/'analyze_corpus.py')
    encoder=helper.LabEncoder(model_path)
    require(encoder.binding['model_manifest_sha256']==analysis['bindings']['model_manifest_sha256'],'Query/document model differs')
    masked=[helper.masked(q['query'],analysis['methods']['identity_mask_phrases']) for q in audit['queries']]
    query_vectors,_,encoding=encoder.encode_all([('audit:'+q['query_id'],t) for q,t in zip(audit['queries'],masked)],out/'query-cache',batch_size=8)
    vectorizer=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,
        ngram_range=(1,2),sublinear_tf=True,min_df=2,max_features=24000,
        stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}),vocabulary={t:i for i,t in enumerate(features)})
    vectorizer.idf_=idf
    query_lexical=vectorizer.transform(' '.join(helper.words(t)) for t in masked)
    lexical_scores=cosine_similarity(query_lexical,lexical).astype('<f4').astype(float)
    semantic_scores=np.clip(cosine_similarity(query_vectors,semantic),-1,1).astype('<f4').astype(float)
    rows=[];private_rankings=[]
    with open_readonly(database) as db:
        db_sources=db.execute('SELECT source_id,body_sha256 FROM sources ORDER BY source_id').fetchall()
        require([(r[0],r[1]) for r in db_sources]==sorted((sid,records[sid]['body_sha256']) for sid in ids),'Database selected source editions differ')
        db_binding=json.loads(db.execute('SELECT value_json FROM meta WHERE key=?',('bindings',)).fetchone()[0])
        require(db_binding['frame']['sha256']==frame_sha,'Database frame hash differs')
        passage_counts=dict(db.execute('SELECT source_id,COUNT(*) FROM passages GROUP BY source_id').fetchall())
        for index,q in enumerate(audit['queries']):
            conditions={'bm25':bm25_sources(db,q['query'])}
            conditions['tfidf']=[{'source_id':ids[j],'score':float(lexical_scores[index,j])} for j in sorted(range(len(ids)),key=lambda j:(-lexical_scores[index,j],ids[j])) if lexical_scores[index,j]>0]
            conditions['minilm']=[{'source_id':ids[j],'score':float(semantic_scores[index,j])} for j in sorted(range(len(ids)),key=lambda j:(-semantic_scores[index,j],ids[j])) if np.linalg.norm(query_vectors[index])>0]
            conditions['rrf']=rrf(conditions)
            best_passages={r['source_id']:r for r in conditions['bm25']}
            value={k:q[k] for k in ('query_id','query','query_type','question_family','source_family_ids','known_relevant_source_ids',
                'other_sources','control_expectation','control_status','judgment_origin') if k in q}
            value['supports']=[{k:s[k] for k in ('source_id','body_sha256','selected_edition_id','start_character','end_character','span_sha256','words','support_role') if k in s} for s in q['supports']]
            value['candidate_union_size']=sum(r.get('rank_origin')=='candidate_fusion' for r in conditions['rrf'])
            value['lexical_matches']={'bm25':len(conditions['bm25']),'tfidf':len(conditions['tfidf'])}
            value['conditions']={}
            for name,ranking in conditions.items():
                top=[]
                for rank,result in enumerate(ranking[:SETTINGS['published_top_results']],1):
                    sid=result['source_id'];source=records[sid]
                    citation={'source_id':sid,'title':source['title'],'source_url':source['source_url'],
                        'body_sha256':source['body_sha256'],'selected_edition_id':source['selected_edition_id'],
                        'text_artifact_sha256':source['text_artifact']['sha256'],'channel_id':source['channel_id'],
                        'passage_count':passage_counts[sid]}
                    if sid in best_passages:
                        citation['locator']={k:best_passages[sid][k] for k in ('passage_id','start_character','end_character','span_sha256','word_start','word_end')}
                        citation['locator_kind']='highest_BM25_passage_not_judged_answer_evidence'
                    else:
                        citation['locator']={'start_character':0,'end_character':body_lengths[sid],'span_sha256':source['body_sha256']}
                        citation['locator_kind']='whole_selected_document_not_judged_answer_evidence'
                    top.append({'rank':rank,'source_id':sid,'score':result['score'],'citation':citation,
                        **({'rank_origin':result['rank_origin']} if 'rank_origin' in result else {})})
                metrics=rank_metrics(ranking,q['known_relevant_source_ids']) if q['query_type']=='supported' else None
                value['conditions'][name]={'ranked_sources':len(ranking),'top_results':top,'metrics':metrics}
                private_rankings.append({'query_id':q['query_id'],'condition':name,'ranking':ranking})
            rows.append(value)
    supported=[r for r in rows if r['query_type']=='supported'];summaries={}
    for name in ('bm25','tfidf','minilm','rrf'):
        metrics=[r['conditions'][name]['metrics'] for r in supported]
        families=defaultdict(list)
        for row in supported:
            for family in row['source_family_ids']:families[family].append(row['conditions'][name]['metrics']['reciprocal_rank'])
        summaries[name]={'supported_queries':len(metrics),
            'mean_reciprocal_rank':sum(m['reciprocal_rank'] for m in metrics)/len(metrics),
            'hit_at_k':{str(k):sum(m['hit_at_k'][str(k)] for m in metrics)/len(metrics) for k in SETTINGS['report_k']},
            'known_support_recall_at_k':{str(k):sum(m['known_support_recall_at_k'][str(k)] for m in metrics)/len(metrics) for k in SETTINGS['report_k']},
            'source_family_mean_reciprocal_rank':{f:sum(v)/len(v) for f,v in sorted(families.items())},
            'source_family_macro_reciprocal_rank':sum(sum(v)/len(v) for v in families.values())/len(families),
            'family_scope':'Descriptive publisher/source-family grouping; sources and queries are not independent and no model was trained on a split.'}
    bindings={name:reference(path) for name,path in [('database',database),('frame',frame_path),('analysis',analysis_path),('queries',query_path),('vector_witness',Path(witness)/'core-vectors.npz'),('lexical_witness',Path(witness)/'lexical.npz')]}
    bindings['registry']=reference(Path(frame_path).parent/'registry.json')
    bindings.update(script_sha256=code_sha,model_manifest_sha256=encoder.binding['model_manifest_sha256'])
    result={'schema_version':1,'status':'executed_frozen_source_retrieval_diagnostic','bindings':bindings,'settings':SETTINGS,
        'coverage':{'eligible_sources':493,'supported_queries':12,'control_queries':4,'new_document_encodings':0,
            'new_query_encodings':len(audit['queries']),'source_families':len({f for r in supported for f in r['source_family_ids']})},
        'queries':rows,'summaries':summaries,
        'controls':{'count':4,'automatic_answer_generation':False,'calibrated_abstention':False,
            'scope':'Ambiguity/evidence-sufficiency probes retain ranked candidates; retrieval alone cannot satisfy their requested proof.'},
        'limitations':['Queries are independently frozen before these rankings but informed by inspected source answers; they are not blind human labels.',
            'Known-support retrieval is only source-level. Unjudged sources are not negative, and returned passage adequacy is not established by a source hit.',
            'Private BM25 searches original500-word passages; vector methods use masked whole documents. Input extent, masking and length/card multiplicity differ.',
            'Maximum passage pooling offers long sources more candidate matches. The passage counts remain beside each citation.',
            'No trained source split, parameter search, human gold answers, answer-generation accuracy or learned abstention threshold is claimed.',
            'Public browser annotation search uses a different index/scorer and is not the evaluated private transcript BM25 arm.',
            'Typed graph navigation exposes provenance but does not participate in these retrieval conditions; this is not a GraphRAG performance experiment.']}
    require(sha(Path(__file__).read_bytes())==code_sha,'Retrieval code changed during execution')
    result['figures']=retrieval_figures(result,out)
    public_check(result);dump(out/'retrieval.json',result)
    dump(out/'rankings-private.json',{'bindings':bindings,'rankings':private_rankings,'query_encoding':encoding})
    np.savez(out/'retrieval-vectors-private.npz',query_vectors=query_vectors,lexical_scores=lexical_scores,semantic_scores=semantic_scores,source_ids=np.asarray(ids))
    dump(out/'output-manifest.json',{'complete':True,'public_allowlist':[reference(out/'retrieval.json'),*result['figures']]})
    print(json_text({'coverage':result['coverage'],'summaries':summaries}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    build_parser=sub.add_parser('build')
    for name in ('frame','analysis','profiles','records','curated','output'):build_parser.add_argument('--'+name,type=Path,required=True)
    query=sub.add_parser('search');query.add_argument('--database',type=Path,required=True);query.add_argument('--query',required=True)
    query.add_argument('--scope',choices=['public','private'],default='public');query.add_argument('--limit',type=int,default=20)
    for name in ('channel','creator','origin','after','before'):query.add_argument('--'+name)
    evidence=sub.add_parser('evidence');evidence.add_argument('--database',type=Path,required=True);evidence.add_argument('--evidence-id',required=True)
    graph=sub.add_parser('paths');graph.add_argument('--graph',type=Path,required=True);graph.add_argument('--start',required=True)
    graph.add_argument('--hops',type=int,default=2);graph.add_argument('--relation',action='append');graph.add_argument('--channel');graph.add_argument('--limit',type=int,default=200)
    for name in ('creator','origin','after','before'):graph.add_argument('--'+name)
    graph.add_argument('--source-id',action='append')
    evaluation=sub.add_parser('evaluate')
    for name in ('database','frame','analysis','witness','model','queries','output'):evaluation.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.command=='build':build(args.frame,args.analysis,args.profiles,args.records,args.curated,args.output)
    elif args.command=='search':print(json_text(search(args.database,args.query,args.scope,args.limit,**{k:getattr(args,k) for k in ('channel','creator','origin','after','before')})))
    elif args.command=='evidence':print(json_text(exact_evidence(args.database,args.evidence_id)))
    elif args.command=='paths':print(json_text(graph_paths(load(args.graph),args.start,args.hops,args.relation,args.channel,args.source_id,args.limit,
        **{k:getattr(args,k) for k in ('creator','origin','after','before')})))
    elif args.command=='evaluate':evaluate(args.database,args.frame,args.analysis,args.witness,args.model,args.queries,args.output)


if __name__=='__main__':main()
