#!/usr/bin/env python3
"""Validate source-bound cards and create public/private question databases."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata
from urllib.parse import urlsplit

from knowledge_sources import digest, load_frame, read_artifact

RELATIONS = {'shared_proposition', 'compatible', 'different_focus', 'conditional_tension', 'explicit_contradiction', 'unresolved'}
SOURCE_FIELDS = ['source_id','title','source_url','medium_id','medium','claimed_label','comparison_label','comparison_level','document_kind','prior_frame','published_at','words','body_sha256','body_normalization','attribution_scope','text_scope','speaker_role','speaker_identity_verified','audio_alignment_verified']


def merged(ranges):
    result=[]
    for a,b in sorted(ranges):
        if result and a <= result[-1][1]: result[-1][1]=max(b,result[-1][1])
        else: result.append([a,b])
    return result


def checked_support(support, documents):
    d=documents[support['source_id']];r=d['record'];text=d['text']
    a,b=support['start_character'],support['end_character']
    if not (isinstance(a,int) and isinstance(b,int) and 0 <= a < b <= len(text)): raise ValueError('Invalid source span')
    body=text[a:b]
    if support['body_sha256']!=r['body_sha256'] or support['text_artifact_sha256']!=r['text_artifact']['sha256']:
        raise ValueError('Source hash mismatch')
    if digest(body.encode())!=support['span_sha256'] or len(body.split())!=support['words']: raise ValueError('Evidence changed')
    if support.get('audio_alignment_verified') is not False: raise ValueError('Unverified alignment must stay explicit')
    if r['document_kind']=='machine_transcript':
        turns=json.loads(read_artifact(r['text_artifact'])[1])['turns'];pos=0;overlaps=[];bounds=[]
        for t in turns:
            v=unicodedata.normalize('NFKC',t['text']).strip();i=text.find(v,pos)
            if i<0: raise ValueError('Turn/body join failed')
            if i<b and i+len(v)>a: overlaps.append(t);bounds.append((i,i+len(v)))
            pos=i+len(v)
        if [t['turn_id'] for t in overlaps]!=support['turn_ids']: raise ValueError('Turn IDs differ')
        if bounds[0][0]!=a or bounds[-1][1]!=b: raise ValueError('ASR support must bind complete turn boundaries')
        if support['start_seconds']!=overlaps[0]['start_seconds'] or support['end_seconds']!=overlaps[-1]['end_seconds']:
            raise ValueError('Turn timing differs')
        if support['role']!='unknown': raise ValueError('ASR role was inferred')
    return body


def sql_database(path, public, documents=None, documentary=None):
    if path.exists(): raise ValueError('Database exists')
    with sqlite3.connect(path) as db:
        db.executescript('''PRAGMA foreign_keys=ON;
        CREATE TABLE sources(source_id TEXT PRIMARY KEY,title TEXT NOT NULL,medium TEXT NOT NULL,claimed_label TEXT NOT NULL,source_url TEXT NOT NULL,document_kind TEXT NOT NULL,body_sha256 TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE topics(topic_id TEXT PRIMARY KEY,title TEXT NOT NULL);
        CREATE TABLE questions(question_id TEXT PRIMARY KEY,question_type TEXT NOT NULL CHECK(question_type IN ('analyst_constructed','documentary_printed_paraphrase')),question TEXT NOT NULL,topic_id TEXT NOT NULL REFERENCES topics,metadata_json TEXT NOT NULL);
        CREATE TABLE cards(card_id TEXT PRIMARY KEY,question_id TEXT NOT NULL REFERENCES questions,source_id TEXT NOT NULL REFERENCES sources,paraphrase TEXT NOT NULL,conditions TEXT NOT NULL,time_scope TEXT NOT NULL,qualifying_note TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE supports(support_id TEXT PRIMARY KEY,card_id TEXT NOT NULL REFERENCES cards,source_id TEXT NOT NULL REFERENCES sources,start_character INTEGER NOT NULL,end_character INTEGER NOT NULL,span_sha256 TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE comparisons(comparison_id TEXT PRIMARY KEY,question_id TEXT NOT NULL REFERENCES questions,left_card_id TEXT NOT NULL REFERENCES cards,right_card_id TEXT NOT NULL REFERENCES cards,relation TEXT NOT NULL,reason TEXT NOT NULL,qualification TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE graph_nodes(node_id TEXT PRIMARY KEY,node_type TEXT NOT NULL,label TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE graph_edges(edge_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES graph_nodes(node_id),target_id TEXT NOT NULL REFERENCES graph_nodes(node_id),relation TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
        CREATE VIRTUAL TABLE card_search USING fts5(card_id UNINDEXED,paraphrase,conditions,qualifying_note);
        CREATE VIRTUAL TABLE question_search USING fts5(question_id UNINDEXED,question);
        ''')
        for r in public['sources']:
            db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)',(r['source_id'],r['title'],r['medium'],r['claimed_label'],r['source_url'],r['document_kind'],r['body_sha256'],json.dumps(r,ensure_ascii=False)))
        db.executemany('INSERT INTO topics VALUES(?,?)',[(r['topic_id'],r['title']) for r in public['topics']])
        for r in public['questions']:
            db.execute('INSERT INTO questions VALUES(?,?,?,?,?)',(r['question_id'],r['question_type'],r['question'],r['topic_id'],json.dumps(r,ensure_ascii=False)))
            db.execute('INSERT INTO question_search VALUES(?,?)',(r['question_id'],r['question']))
        for r in public['cards']:
            db.execute('INSERT INTO cards VALUES(?,?,?,?,?,?,?,?)',(r['card_id'],r['question_id'],r['source_id'],r['paraphrase'],r['conditions'],r['time_scope'],r['qualifying_note'],json.dumps(r,ensure_ascii=False)))
            db.execute('INSERT INTO card_search VALUES(?,?,?,?)',(r['card_id'],r['paraphrase'],r['conditions'],r['qualifying_note']))
            for i,s in enumerate(r['supports']):
                db.execute('INSERT INTO supports VALUES(?,?,?,?,?,?,?)',(r['card_id']+':'+str(i+1),r['card_id'],r['source_id'],s['start_character'],s['end_character'],s['span_sha256'],json.dumps(s,ensure_ascii=False)))
        for r in public['comparisons']:
            db.execute('INSERT INTO comparisons VALUES(?,?,?,?,?,?,?,?)',(r['comparison_id'],r['question_id'],r['left_card_id'],r['right_card_id'],r['relation'],r['reason'],r['qualification'],json.dumps(r,ensure_ascii=False)))
        for r in public['graph']['nodes']: db.execute('INSERT INTO graph_nodes VALUES(?,?,?,?)',(r['id'],r['type'],r['label'],json.dumps(r,ensure_ascii=False)))
        for r in public['graph']['edges']: db.execute('INSERT INTO graph_edges VALUES(?,?,?,?,?)',(r['id'],r['source'],r['target'],r['relation'],json.dumps(r,ensure_ascii=False)))
        for key in ('schema_version','coverage','limitations','input_bindings','annotation_provenance','reading_coverage','hypotheses'):
            db.execute('INSERT INTO metadata VALUES(?,?)',(key,json.dumps(public[key],ensure_ascii=False)))
        if documents is not None:
            db.executescript('''CREATE TABLE source_bodies(source_id TEXT PRIMARY KEY REFERENCES sources,text TEXT NOT NULL);
            CREATE TABLE evidence_text(support_id TEXT PRIMARY KEY REFERENCES supports,text TEXT NOT NULL);
            CREATE TABLE documentary_turns(turn_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources,question TEXT NOT NULL,response TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE VIRTUAL TABLE body_search USING fts5(source_id UNINDEXED,text);''')
            for sid,d in documents.items():
                db.execute('INSERT INTO source_bodies VALUES(?,?)',(sid,d['text']));db.execute('INSERT INTO body_search VALUES(?,?)',(sid,d['text']))
            for r in public['cards']:
                for i,s in enumerate(r['supports']):
                    db.execute('INSERT INTO evidence_text VALUES(?,?)',(r['card_id']+':'+str(i+1),documents[r['source_id']]['text'][s['start_character']:s['end_character']]))
            for t in documentary['turns']:
                db.execute('INSERT INTO documentary_turns VALUES(?,?,?,?,?)',(t['id'],documentary['source_id'],t['question'],t['response'],json.dumps(t,ensure_ascii=False)))
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()


def build(frame_path, annotation_path, output):
    if output.exists() or not output.resolve().is_relative_to(Path('/workspace/channels-et-private')): raise ValueError('Use a fresh private output directory')
    docs,frame=load_frame(frame_path);documents={d['record']['source_id']:d for d in docs}
    annotation_raw=annotation_path.read_bytes();a=json.loads(annotation_raw)
    if a['source_frame_sha256']!=digest(frame_path.read_bytes()): raise ValueError('Annotation source frame differs')
    qmap={q['question_id']:q for q in a['questions']};cmap={c['card_id']:c for c in a['cards']}
    if len(qmap)!=len(a['questions']) or len(cmap)!=len(a['cards']): raise ValueError('Repeated card/question ID')
    read=[];read_ranges={}
    for sid,spans in a['reading_spans'].items():
        for s in spans: checked_support(s,documents)
        ranges=merged([(s['start_character'],s['end_character']) for s in spans]);read_ranges[sid]=ranges
        text=documents[sid]['text'];words=sum(len(text[x:y].split()) for x,y in ranges)
        read.append({'source_id':sid,'words_read':words,'source_words':documents[sid]['record']['words'],'full_body_read':ranges==[[0,len(text)]],'spans':[{'start_character':x,'end_character':y,'span_sha256':digest(text[x:y].encode()),'words':len(text[x:y].split())} for x,y in ranges], 'human_annotation':False,'audio_listened':False})
    for c in a['cards']:
        if c['question_id'] not in qmap or c['source_id'] not in documents or not c['supports']: raise ValueError('Orphan or unsupported card')
        for s in c['supports']:
            checked_support(s,documents)
            if s['source_id']!=c['source_id']: raise ValueError('Card/source join differs')
            if not any(x<=s['start_character'] and y>=s['end_character'] for x,y in read_ranges[c['source_id']]): raise ValueError('Card evidence lies outside declared reading')
    for c in a['comparisons']:
        if c['relation'] not in RELATIONS: raise ValueError('Unknown comparison type')
        if any(cmap[c[k]]['question_id']!=c['question_id'] for k in ['left_card_id','right_card_id']): raise ValueError('Comparison question differs')
        if c['relation']=='explicit_contradiction' and not c.get('same_proposition_conditions_time_verified'): raise ValueError('Contradiction lacks required scope audit')
    qa_ref=a['documentary_qa_source']['artifact'];_,qa_raw=read_artifact(qa_ref);qa=json.loads(qa_raw);qa['source_id']=a['documentary_qa_source']['source_id'];turns={r['id']:r for r in qa['turns']}
    for q in a['questions']:
        if q['question_type']=='documentary_printed_paraphrase':
            b=q['documentary_binding'];t=turns[b['turn_id']]
            if b['artifact_sha256']!=qa_ref['sha256'] or digest(t['question'].encode())!=b['question_sha256']: raise ValueError('Documentary question binding changed')
            responses=[c for c in a['cards'] if c['question_id']==q['question_id']]
            if len(responses)!=1: raise ValueError('Documentary turn requires one bounded response')
            c=responses[0];s=c['supports'][0]
            if documents[c['source_id']]['text'][s['start_character']:s['end_character']]!=unicodedata.normalize('NFKC',t['response']).strip(): raise ValueError('Documentary response body differs')
    sources=[]
    for d in docs:
        r=d['record'];p={k:r.get(k) for k in SOURCE_FIELDS};p['text_artifact_sha256']=r['text_artifact']['sha256']
        if urlsplit(p['source_url']).scheme not in ('https','http'): raise ValueError('Invalid source URL')
        sources.append(p)
    public={k:a[k] for k in ['schema_version','topics','questions','cards','comparisons','hypotheses','annotation_provenance']}
    public['annotation_revision']=a.get('annotation_revision',{'status':'initial_source_informed_annotation'})
    public.update(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),sources=sources,reading_coverage=read,
        coverage={'source_frame_documents':len(docs),'source_frame_words':sum(d['record']['words'] for d in docs),'mediums':len({d['record']['medium_id'] for d in docs}),'read_sources':len(read),'read_full_bodies':sum(r['full_body_read'] for r in read),'unique_body_words_read':sum(r['words_read'] for r in read),'documentary_question_words_read':sum(len(t['question'].split()) for t in qa['turns']),'questions':len(a['questions']),'analyst_questions':sum(q['question_type']=='analyst_constructed' for q in a['questions']),'documentary_questions':sum(q['question_type']=='documentary_printed_paraphrase' for q in a['questions']),'cards':len(a['cards']),'comparisons':len(a['comparisons']),'relation_counts':{k:Counter(c['relation'] for c in a['comparisons'])[k] for k in sorted(RELATIONS)},'hypotheses':len(a['hypotheses'])},
        input_bindings=[{'kind':'source_frame','sha256':digest(frame_path.read_bytes())},{'kind':'annotations','sha256':digest(annotation_raw)},{'kind':'builder','sha256':digest(Path(__file__).read_bytes())},{'kind':'source_loader','sha256':digest(Path(__file__).with_name('knowledge_sources.py').read_bytes())}],
        limitations=['Purposeful source-informed AI annotations; no human ground truth, inter-annotator reliability or population inference.','Source-frame modeling and bounded close reading have different denominators. ASR is unverified and may change across recognition editions.','The eight analyst questions were constructed after source reading; they are not matched audience questions or held-out evaluation items. Five separate printed documentary questions have publisher-layout provenance.','Named-person and broad-civilization groups do not authenticate a shared entity. Different referents, dates or conditions can prevent meaningful contradiction tests.','No explicit scoped contradiction was established in this selected comparison set; this does not show universal agreement or absence of contradictions elsewhere.','Paraphrase retrieval and cross-field connections are navigation or methodological experiments, not weight training, verified spiritual mechanisms or advice.'])
    nodes={};edges=[]
    def node(i,t,label,**extra): nodes.setdefault(i,{'id':i,'type':t,'label':label,**extra})
    def edge(src,dst,relation,**extra): edges.append({'id':'edge-'+str(len(edges)+1),'source':src,'target':dst,'relation':relation,**extra})
    for s in sources:
        node('source:'+s['source_id'],'source',s['title'],source_id=s['source_id']);node(s['medium_id'],'medium',s['medium']);edge(s['medium_id'],'source:'+s['source_id'],'publisher_attributed_context')
        lid='printed-label:'+digest((s['medium_id']+'|'+s['claimed_label']).encode())[:16];node(lid,'printed_label',s['claimed_label'],medium_id=s['medium_id']);edge('source:'+s['source_id'],lid,'source_local_attribution',identity_verified=False)
    for t in a['topics']: node('topic:'+t['topic_id'],'topic',t['title'])
    for q in a['questions']: node(q['question_id'],'question',q['question'],question_type=q['question_type']);edge(q['question_id'],'topic:'+q['topic_id'],'analyst_topic_assignment')
    for c in a['cards']:
        node(c['card_id'],'card',c['paraphrase'],source_id=c['source_id']);edge(c['card_id'],'source:'+c['source_id'],'supported_by_source_span');edge(c['card_id'],c['question_id'],'addresses_analyst_prompt' if qmap[c['question_id']]['question_type']=='analyst_constructed' else 'paraphrases_printed_response')
    for c in a['comparisons']: edge(c['left_card_id'],c['right_card_id'],c['relation'],comparison_id=c['comparison_id'],annotation='AI close reading')
    for h in a['hypotheses']:
        node(h['hypothesis_id'],'hypothesis',h['title'],status=h['type'])
        for cid in h['source_card_ids']: edge(h['hypothesis_id'],cid,'motivated_by_methodological_example',empirical_mechanism=False)
    public['graph']={'nodes':list(nodes.values()),'edges':edges,'scope':'Typed source, annotation and hypothesis links; not a graph of verified spiritual entities or causal effects.'}
    output.mkdir(parents=True,mode=0o700)
    (output/'knowledge.json').write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n')
    sql_database(output/'questions.sqlite',public)
    sql_database(output/'knowledge-private.sqlite',public,documents,qa)
    (output/'executed-knowledge-build.py').write_bytes(Path(__file__).read_bytes())
    (output/'provenance-private.json').write_text(json.dumps({'frame_path':str(frame_path),'annotation_path':str(annotation_path),'input_bindings':public['input_bindings'],'source_records':[d['record'] for d in docs]},indent=2,ensure_ascii=False)+'\n')
    report=['# Source-bound question and claim bank','',f"{len(docs)} source editions; {len(a['questions'])} questions; {len(a['cards'])} answer/claim cards; {len(a['comparisons'])} bounded comparisons.",'','Eight questions are analyst-constructed. Five are public paraphrases of explicit printed questions from one publisher excerpt. These are not matched audience questions across mediums.','']
    for q in a['questions']:
        report += ['## '+q['question'],'',q['question_type'].replace('_',' '),'']
        for c in [c for c in a['cards'] if c['question_id']==q['question_id']]:
            s=next(s for s in sources if s['source_id']==c['source_id']);report += [f"- **{s['medium']} · {s['claimed_label']}**: {c['paraphrase']} {c['qualifying_note']} [Publisher]({s['source_url']})",'']
    (output/'question-bank.md').write_text('\n'.join(report)+'\n')
    allow=[]
    for name in ('knowledge.json','questions.sqlite','question-bank.md'):
        raw=(output/name).read_bytes();allow.append({'file':name,'bytes':len(raw),'sha256':digest(raw)})
    (output/'output-manifest.json').write_text(json.dumps({'status':'complete','public_allowlist':allow,'coverage':public['coverage']},indent=2)+'\n')
    print(json.dumps({'coverage':public['coverage'],'files':allow}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frame',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.frame,a.annotations,a.output)
