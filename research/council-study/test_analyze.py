import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
A=module('council_analysis','analyze.py');V=module('council_verify','verify_release.py')


class AnalysisTests(unittest.TestCase):
    def test_complete_phrase_mask_preserves_substantive_words_and_negation(self):
        text="The Galactic Council of Light says contact is not rescue. Light and contact remain topics. We'll choose."
        masked=A.mask_text(text,['Galactic Council of Light'])
        self.assertNotIn('Galactic Council of Light',masked)
        self.assertIn('Light and contact remain topics',masked)
        self.assertIn('not',A.tokens(masked));self.assertIn("we'll",A.tokens(masked))
        self.assertIn('Council of Contactless',A.mask_text('Council of Contactless',['Council of Contact']))

    def test_centered_window_preserves_numeric_label_for_phrase_mask(self):
        text='opening '*160+'Galactic Council of 12 '+'closing '*160
        span=A.centered_span(text)
        self.assertEqual(len(A.tokens(span)),300)
        self.assertIn('Galactic Council of 12',span)
        self.assertNotIn('Galactic',A.mask_text(span,['Galactic Council of 12']))
        self.assertIsNone(A.centered_span('short source',300))

    def test_hash_mismatch_and_public_output_path_rejected(self):
        with tempfile.TemporaryDirectory() as t,patch.object(A,'PRIVATE',Path(t)):
            p=Path(t)/'source.txt';p.write_text('retained source');ref={'path':str(p),'bytes':p.stat().st_size,'sha256':A.sha(p)}
            self.assertEqual(A.checked(ref),p)
            p.write_text('changed source')
            with self.assertRaises(ValueError):A.checked(ref)
            with self.assertRaises(ValueError):A.private_path('/workspace/channels-ET/dist/new.json',exists=False)

    def test_exact_text_alias_is_not_an_independent_observation(self):
        with tempfile.TemporaryDirectory() as t,patch.object(A,'PRIVATE',Path(t)):
            root=Path(t);p=root/'text.txt';p.write_text('The same complete body is published twice.')
            ref={'path':str(p),'bytes':p.stat().st_size,'sha256':A.sha(p)}
            rows=[{'source_id':x,'title':x,'canonical_url':'https://example.org/'+x,'medium_id':'m','medium_name':'Test Medium','council_label':'Council A','text_artifact':ref} for x in ['a','b']]
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'documents':rows}));out=root/'out';out.mkdir()
            docs,bindings,excluded=A.load([manifest],out)
            self.assertEqual(len(docs),1);self.assertEqual(excluded[0]['selected_source_id'],'a');self.assertEqual(excluded[0]['reason'],'exact_normalized_text_alias')
            rows[1]['source_id']='a';manifest.write_text(json.dumps({'documents':rows}))
            with self.assertRaises(ValueError):A.load([manifest],out)

    def test_same_label_is_not_automatically_same_medium_or_identity(self):
        def doc(sid,medium,label,text):return {'summary':{'source_id':sid,'medium_id':medium,'medium':medium,'council_label_exact':label},'text':text}
        first='contact consent choice listening community attention curiosity peace practice learning '*10
        second='ships telescope observations evidence communication timing science public inquiry confirmation '*10
        third='heart compassion meditation inner emotions care anxiety body awareness nature '*10
        lex,topics,clusters=A.fit([doc('a','medium-a','Council A',first),doc('b','medium-b','Council A',second),doc('c','medium-a','Council B',third)])
        self.assertEqual(lex['status'],'fitted');self.assertEqual(len(lex['pairs']),3)
        pairs={(x['source'],x['target']):x for x in lex['pairs']}
        self.assertEqual(pairs['a','b']['category'],'different_medium_same_label')
        self.assertEqual(pairs['a','c']['category'],'same_medium_different_label')
        self.assertEqual(topics['status'],'insufficient_documents');self.assertEqual(clusters['status'],'insufficient_documents')
        self.assertEqual(lex['window_300_source_ids'],[])

    def test_matrix_and_privacy_guards(self):
        V.matrix([[1,.2],[.2,1]],['a','b'])
        with self.assertRaises(ValueError):V.matrix([[1,.2],[.3,1]],['a','b'])
        with self.assertRaises(ValueError):V.matrix([[1,1],[1,1]],['a','a'])
        with self.assertRaises(ValueError):V.privacy({'text':'full body'})
        with self.assertRaises(ValueError):V.privacy({'artifact':'/workspace/private/source.txt'})
        with self.assertRaises(ValueError):V.privacy({'value':float('nan')})

    def test_paired_audio_written_editions_are_not_double_counted(self):
        def doc(sid,kind,family,digest):
            return {'summary':{'source_id':sid,'source_format':kind,'publication_family_id':family,'text_content_sha256':digest,'words':50,'text_origin':kind}}
        audio=doc('a-asr','normalized_asr','publisher-page-1','a'*64)
        written=doc('z-written','publisher_written_message','publisher-page-1','b'*64)
        independent=doc('separate','normalized_asr',None,'c'*64)
        selected,excluded=A.select_editions([audio,independent,written])
        self.assertEqual([x['summary']['source_id'] for x in selected],['separate','z-written'])
        self.assertEqual(excluded[0]['source_id'],'a-asr');self.assertEqual(excluded[0]['selected_source_id'],'z-written')

    def test_source_reading_must_bind_exact_hash_and_unknown_role_locator(self):
        source={'summary':{'source_id':'a','source_url':'https://example.org/a','text_artifact_sha256':'a'*64,'words':3,'title':'A'},'turns':[{'turn_id':'segment-1','start_seconds':0,'end_seconds':2,'role':'unknown'}]}
        support={'source_id':'a','canonical_url':'https://example.org/a','text_artifact_sha256':'a'*64,'turn_ids':['segment-1'],'start_seconds':0,'end_seconds':2,'role':'unknown','audio_alignment_verified':False}
        reading={'source_manifest_sha256':'b'*64,'readings':[{'question_type':'analyst_constructed_comparison_not_a_verified_spoken_question','supports':[support]}],'coverage':{'documents_read_in_full':1,'asr_words_read':3,'human_annotation':False,'audio_content_listened':False}}
        with tempfile.TemporaryDirectory() as t,patch.object(A,'PRIVATE',Path(t)):
            p=Path(t)/'reading.json';p.write_text(json.dumps(reading));self.assertIn('artifact_binding',A.reviewed_reading(p,[source],[{'sha256':'b'*64}]))
            for key,value in [('text_artifact_sha256','c'*64),('end_seconds',3),('role','claimed_entity')]:
                mutated=copy.deepcopy(reading);mutated['readings'][0]['supports'][0][key]=value;p.write_text(json.dumps(mutated))
                with self.assertRaises(ValueError):A.reviewed_reading(p,[source],[{'sha256':'b'*64}])

    def test_supplemental_paraphrase_binds_actual_read_span(self):
        body='First paragraph.\nSecond paragraph.'
        source={'summary':{'source_id':'a','title':'A','source_url':'https://example.org/a','text_artifact_sha256':'a'*64},'text':body,'turns':[]}
        span={'start_character':0,'end_character':16,'span_sha256':A.sha_bytes(body[:16].encode()),'words':2}
        support={**span,'role':'unknown','audio_alignment_verified':False}
        reading={'source_id':'a','title':'A','text_artifact_sha256':'a'*64,'coverage':{'spans':[span],'words_read':2,'full_document_read':False,'human_annotation':False,'audio_listened':False},'observations':[{'supports':[support]}]}
        with tempfile.TemporaryDirectory() as t,patch.object(A,'PRIVATE',Path(t)):
            p=Path(t)/'reading.json';p.write_text(json.dumps(reading));self.assertIn('artifact_binding',A.supplemental_reading(p,[source]))
            mutated=copy.deepcopy(reading);mutated['coverage']['full_document_read']=True;p.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError):A.supplemental_reading(p,[source])
            for key,value in [('span_sha256','b'*64),('role','claimed_entity'),('words',3)]:
                mutated=copy.deepcopy(reading);mutated['observations'][0]['supports'][0][key]=value;p.write_text(json.dumps(mutated))
                with self.assertRaises(ValueError):A.supplemental_reading(p,[source])


if __name__=='__main__':unittest.main()
