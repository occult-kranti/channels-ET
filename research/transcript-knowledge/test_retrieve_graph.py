import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import retrieve_graph as R


def fixture():
    bodies=['Alpha contact is not a guaranteed public event. '+('attention '*510),
            'Beta guidance is optional. It does not require buying a service.']
    docs=[]
    for i,text in enumerate(bodies):
        sid='doc-'+str(i);record={'source_id':sid,'title':'Source '+str(i),'source_url':'https://example.org/'+sid,
            'channel_id':'channel-'+str(i),'channel_name':'Publisher '+str(i),'creator_id':'creator-'+str(i),
            'creator_name':'Attribution '+str(i),'publisher_id':'publisher-'+str(i),'publisher_name':'Publisher '+str(i),
            'publication_date':'2026-11-08T12:30:00Z','text_origin':'publisher_written','document_kind':'written_message',
            'selected_edition_id':sid+'-edition','body_sha256':R.sha(text.encode()),'words':len(text.split()),
            'claimed_labels':['Printed label'],'text_artifact':{'sha256':R.sha(text.encode())},
            'attribution_scope':'unverified','speaker_role':'unknown'}
        docs.append({'record':record,'text':text})
    profiles={'profiles':[{'source_id':d['record']['source_id'],'body_sha256':d['record']['body_sha256'],
        'summary':'Automatic lexical outline only.','top_terms':[{'term':'guidance','weight':.2}],
        'topic_profile':[{'label':'attention','topic_id':'T01','weight':1.}]} for d in docs]}
    text=bodies[1];support={'evidence_id':'curated-e1','source_id':'doc-1','body_sha256':docs[1]['record']['body_sha256'],
        'start_character':0,'end_character':len(text),'span_sha256':R.sha(text.encode()),'words':len(text.split()),'role':'answer','text':text}
    records=[{'record_id':'r1','type':'unverified_question_candidate','source_id':'doc-1',
        'selected_edition_id':'doc-1-edition','body_sha256':docs[1]['record']['body_sha256'],
        'question_origin':'punctuation_candidate','answer_status':'unverified_adjacent_context','speaker_status':'unknown',
        'question_text':'SECRET_RAW_QUESTION','answer_text':text,'context_text':text,'supports':[support],
        'private_path':'/workspace/private-ignore'}]
    curated={'questions':[{'question_id':'q1','question_type':'analyst_constructed','question':'Must assistance be purchased?',
        'informed_by_answer_reading':True,'internal_notes':{'full_text':'PRIVATE OMIT'}}],
        'cards':[{'card_id':'c1','question_id':'q1','source_id':'doc-1','paraphrase':'This source describes optional guidance.',
        'conditions':'The passage does not require paid help.','time_scope':'The printed passage.',
        'qualifying_note':'A bounded source reading.','supports':[support],'claim_type':'qualified_paraphrase',
        'annotation':{'human_validated':False,'private_path':'/workspace/private-ignore'}}]}
    analysis={'topics':[{'topic_id':'T01','label':'attention'}],
        'documents':[{'source_id':d['record']['source_id'],'topic_weights':[1.]} for d in docs],
        'graph':{'semantic':{'edges':[{'source':'doc-0','target':'doc-1','similarity':.7}]}}}
    return docs,profiles,records,curated,analysis


class RetrievalGraphTest(unittest.TestCase):
    def test_evidence_hash_and_edition_are_required(self):
        docs,_,_,curated,_=fixture();s=dict(curated['cards'][0]['supports'][0]);d=docs[1]
        self.assertEqual(R.evidence_row(s,d['record'],d['text'])['evidence_id'],'curated-e1')
        s['body_sha256']='wrong'
        with self.assertRaises(ValueError):R.evidence_row(s,d['record'],d['text'])
        s['body_sha256']=d['record']['body_sha256'];s['span_sha256']='wrong'
        with self.assertRaises(ValueError):R.evidence_row(s,d['record'],d['text'])

    def test_passages_cover_partial_tail_without_overlap(self):
        docs,*_=fixture();rows=list(R.passage_rows(docs));self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['word_start'],0);self.assertEqual(rows[0]['word_end'],rows[1]['word_start'])
        self.assertEqual(sum(r['word_end']-r['word_start'] for r in rows),sum(d['record']['words'] for d in docs))
        for r in rows:
            text=next(d['text'] for d in docs if d['record']['source_id']==r['source_id'])
            self.assertEqual(R.sha(text[r['start_character']:r['end_character']].encode()),r['span_sha256'])

    def test_public_private_database_search_and_exact_evidence(self):
        docs,profiles,records,curated,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'records.jsonl';source.write_text('\n'.join(json.dumps(r) for r in records)+'\n')
            counts,links=R.build_databases(docs,profiles,source,curated,root,{})
            public=root/'database-public.sqlite';private=root/'database-private.sqlite'
            self.assertEqual(counts['tables']['public']['passages'],0);self.assertEqual(counts['passages'],3)
            with sqlite3.connect(public) as db:
                self.assertIsNone(db.execute('SELECT question_text FROM records').fetchone()[0])
                self.assertNotIn('private_path',db.execute('SELECT metadata_json FROM cards').fetchone()[0])
                self.assertNotIn('internal_notes',db.execute('SELECT metadata_json FROM questions').fetchone()[0])
                self.assertFalse(db.execute("SELECT text FROM public_search WHERE text LIKE '%SECRET_RAW_QUESTION%'").fetchall())
            self.assertEqual(len(R.search(private,'attention','private')['matches']),1)
            self.assertEqual(R.search(private,'attention','private',channel='channel-1')['matches'],[])
            self.assertEqual(R.search(private,'attention','private',before='2026-11-08')['eligible_sources'],2)
            self.assertTrue(R.search(public,'guidance')['matches'])
            self.assertIsNone(R.exact_evidence(public,'curated-e1')['text'])
            self.assertEqual(R.exact_evidence(private,'curated-e1')['text'],docs[1]['text'])
            with self.assertRaises(ValueError):R.search(public,'guidance','private')

    def test_fts_user_operators_are_literal_terms(self):
        expression=R.fts_expression('NEAR(alpha OR beta) "quote"; DROP TABLE sources;')
        self.assertNotIn('NEAR(',expression);self.assertIn('"or"',expression)
        self.assertEqual(R.fts_expression('!!!'),'')

    def test_graph_preserves_question_origin_and_excludes_semantics_by_default(self):
        docs,_,_,curated,analysis=fixture()
        graph=R.make_graph(docs,analysis,curated,{'c1':['curated-e1']},{'records_by_type':{'unverified_question_candidate':1}},{})
        self.assertFalse(any(e['relation']=='asks' for e in graph['edges']))
        result=R.graph_paths(graph,'source:doc-1',2)
        self.assertTrue(any('question:q1' in p['nodes'] for p in result['paths']))
        self.assertFalse(any('derived_semantic_neighbor' in p['relations'] for p in result['paths']))
        selected=R.graph_paths(graph,'source:doc-1',2,channel='channel-1')
        self.assertFalse(any('source:doc-0' in p['nodes'] for p in selected['paths']))
        capped=R.graph_paths(graph,'source:doc-1',2,limit=1);self.assertTrue(capped['truncated'])

    def test_rrf_only_fuses_bounded_candidates_then_keeps_raw_tail(self):
        rows=[{'source_id':'s'+str(i),'score':1/(i+1)} for i in range(70)]
        result=R.rrf({'bm25':[rows[60]],'tfidf':rows[:3],'minilm':rows})
        self.assertEqual(len(result),70);self.assertEqual(len({x['source_id'] for x in result}),70)
        self.assertEqual([r['source_id'] for r in result if r['rank_origin']=='minilm_tail_fallback'],
            [r['source_id'] for r in rows[50:] if r['source_id']!='s60'])

    def test_metrics_use_known_support_and_do_not_label_unjudged_negatives(self):
        rows=[{'source_id':'unjudged'},{'source_id':'known'}]
        result=R.rank_metrics(rows,['known']);self.assertEqual(result['reciprocal_rank'],.5)
        self.assertEqual(result['hit_at_k']['1'],0);self.assertEqual(result['known_support_recall_at_k']['3'],1)
        self.assertNotIn('accuracy',result)

    def test_public_metadata_rejects_private_nested_values(self):
        with self.assertRaises(ValueError):R.safe_card({'card_id':'c','paraphrase':'bad /workspace/private'})


if __name__=='__main__':unittest.main()
