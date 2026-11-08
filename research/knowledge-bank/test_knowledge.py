import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from knowledge_sources import body_from_artifact, digest, read_artifact
from knowledge_build import checked_support, sql_database
from question_query import query


class KnowledgeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='knowledge-integrity-')
        self.root=Path(self.temp.name)
        self.text='A private source says that a voluntary exercise is optional.\nThis is a second recorded turn.'
        self.turns=[{'turn_id':'segment-1','text':self.text.split('\n')[0],'start_seconds':0.0,'end_seconds':4.0,'role':'unknown'},
                    {'turn_id':'segment-2','text':self.text.split('\n')[1],'start_seconds':4.0,'end_seconds':7.0,'role':'unknown'}]
        self.path=self.root/'transcript.json';self.path.write_text(json.dumps({'text':self.text,'turns':self.turns}))
        self.ref={'path':str(self.path),'bytes':self.path.stat().st_size,'sha256':digest(self.path.read_bytes())}
        self.r={'source_id':'fixture','text_artifact':self.ref,'body_sha256':digest(self.text.encode()),'document_kind':'machine_transcript'}
        self.docs={'fixture':{'record':self.r,'text':self.text}}
        self.support={'source_id':'fixture','body_sha256':self.r['body_sha256'],'text_artifact_sha256':self.ref['sha256'],'start_character':0,'end_character':len(self.turns[0]['text']),'span_sha256':digest(self.turns[0]['text'].encode()),'words':len(self.turns[0]['text'].split()),'audio_alignment_verified':False,'role':'unknown','turn_ids':['segment-1'],'start_seconds':0.0,'end_seconds':4.0}

    def tearDown(self):self.temp.cleanup()

    def test_source_mutation_rejected(self):
        self.assertEqual(body_from_artifact(self.ref),self.text)
        self.path.write_text(self.path.read_text()+' ')
        with self.assertRaises(ValueError):read_artifact(self.ref)

    def test_evidence_mutation_rejected(self):
        self.assertEqual(checked_support(self.support,self.docs),self.turns[0]['text'])
        for field,value in [('span_sha256','0'*64),('words',999),('body_sha256','1'*64),('end_character',len(self.text)+1)]:
            bad=copy.deepcopy(self.support);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):checked_support(bad,self.docs)

    def test_inferred_role_or_time_change_rejected(self):
        for field,value in [('role','council'),('turn_ids',['segment-2']),('end_seconds',5.0),('audio_alignment_verified',True)]:
            bad=copy.deepcopy(self.support);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):checked_support(bad,self.docs)

    def test_partial_turn_boundary_rejected_even_with_matching_hash(self):
        bad=copy.deepcopy(self.support);bad['end_character']-=2
        shortened=self.text[:bad['end_character']];bad['span_sha256']=digest(shortened.encode());bad['words']=len(shortened.split())
        with self.assertRaises(ValueError):checked_support(bad,self.docs)

    def public_fixture(self):
        s={'source_id':'fixture','title':'Synthetic test source','medium':'Fixture medium','claimed_label':'Fixture printed label','source_url':'https://example.org/fixture','document_kind':'machine_transcript','body_sha256':self.r['body_sha256']}
        q={'question_id':'question','question_type':'analyst_constructed','question':'Is a practice compulsory?','topic_id':'practice'}
        c={'card_id':'card','question_id':'question','source_id':'fixture','paraphrase':'The described exercise is voluntary.','conditions':'No universal obligation is asserted.','time_scope':'Undated fixture.','qualifying_note':'This is synthetic test data, not a research observation.','supports':[self.support]}
        return {'schema_version':1,'sources':[s],'topics':[{'topic_id':'practice','title':'Practice'}],'questions':[q],'cards':[c],'comparisons':[],'graph':{'nodes':[{'id':'source','type':'source','label':'Fixture'}],'edges':[]},'coverage':{'fixtures':1},'limitations':['Fixture only.'],'input_bindings':[],'annotation_provenance':{'synthetic_fixture':True},'reading_coverage':[],'hypotheses':[]}

    def test_public_private_database_boundary(self):
        p=self.public_fixture();public=self.root/'public.sqlite';private=self.root/'private.sqlite'
        sql_database(public,p);sql_database(private,p,self.docs,{'source_id':'fixture','turns':[]})
        with sqlite3.connect(public) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn('source_bodies',tables);self.assertNotIn('evidence_text',tables)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        with sqlite3.connect(private) as db:self.assertEqual(db.execute('SELECT text FROM source_bodies').fetchone()[0],self.text)
        self.assertNotIn(self.text.encode(),public.read_bytes())

    def test_readonly_search_and_parameter_boundary(self):
        path=self.root/'public.sqlite';sql_database(path,self.public_fixture())
        self.assertEqual(len(query(path,text='voluntary')),1)
        self.assertEqual(query(path,source="fixture' OR 1=1 --"),[])
        self.assertEqual(query(path,text='compulsory'),[])  # Question text is not card evidence.
        with self.assertRaises(ValueError):query(path,limit=10000)

    def test_database_orphan_rejected(self):
        p=self.public_fixture();p['cards'][0]['source_id']='missing'
        with self.assertRaises(sqlite3.IntegrityError):sql_database(self.root/'bad.sqlite',p)


if __name__=='__main__':unittest.main()
