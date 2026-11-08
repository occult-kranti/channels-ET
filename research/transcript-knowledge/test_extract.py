import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import contextlib
import io

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import extract as E
import verify_extraction as V


def record():return {'source_id':'test-source','selected_edition_id':'test-edition','body_sha256':'a'*64,'text_origin':'machine_asr','document_kind':'machine_transcript'}


class ExtractionTests(unittest.TestCase):
    def test_candidate_context_never_becomes_answer(self):
        text='What do you mean? I do not know who is speaking now.'
        records,_=E.punctuation_records(record(),text,{})
        self.assertEqual(len(records),1);r=records[0]
        self.assertIsNone(r['answer_text']);self.assertEqual(r['answer_spans'],[])
        self.assertEqual(r['context_text'],'I do not know who is speaking now.')
        self.assertEqual(r['speaker_status'],'unknown')

    def test_quoted_question_remains_unverified(self):
        rows,_=E.punctuation_records(record(),'He asked, “What is a thought?” She paused.',{})
        self.assertEqual(rows[0]['type'],'unverified_question_candidate')
        self.assertIn('quotation_characters_present_not_speaker_identification',rows[0]['flags'])

    def test_wrapped_question_is_not_truncated(self):
        text='What were your human expectations\nof enlightenment? The answer is unclear.'
        rows,_=E.punctuation_records(record(),text,{})
        self.assertEqual(rows[0]['question_text'],'What were your human expectations\nof enlightenment?')
        self.assertIn('source_line_wrap_preserved',rows[0]['flags'])

    def test_one_word_question_is_retained(self):
        rows,_=E.punctuation_records(record(),'Why? Nobody knows.',{})
        self.assertEqual(rows[0]['question_text'],'Why?')

    def test_documentary_pair_requires_same_printed_id(self):
        turns=[{'text':'What is this?','role':'questioner','question_id':'1','turn_id':'q'},
               {'text':'I cannot answer.','role':'response','question_id':'2','turn_id':'a'}]
        text='\n'.join(t['text'] for t in turns)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.json';p.write_text(json.dumps({'turns':turns}));r={**record(),'text_artifact':{'path':str(p)}}
            rows,stats=E.documentary_records(r,text,{})
        self.assertEqual(rows[0]['type'],'unverified_question_candidate');self.assertIsNone(rows[0]['answer_text'])
        self.assertEqual(stats['unpaired_printed_prompts'],1)

    def test_documentary_refusal_is_preserved_exactly(self):
        turns=[{'text':'Will you tell us?','role':'questioner','question_id':'1','turn_id':'q'},
               {'text':'We cannot answer unless the context is given.','role':'response','question_id':'1','turn_id':'a'}]
        text='\n'.join(t['text'] for t in turns)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.json';p.write_text(json.dumps({'turns':turns}));r={**record(),'text_artifact':{'path':str(p)}}
            rows,_=E.documentary_records(r,text,{})
        self.assertEqual(rows[0]['answer_text'],turns[1]['text'])
        self.assertIn('response_contains_refusal_or_uncertainty_cue',rows[0]['flags'])

    def test_digest_is_bound_and_within_budget(self):
        text=' '.join(f'Condition {i} may change unless we specify context.' for i in range(90))
        spans=E.extractive_digest(text,{'condition':.5,'context':.3})
        self.assertLessEqual(sum(s['words'] for s in spans),180)
        self.assertEqual(len(spans),3)
        for s in spans:self.assertEqual(E.sha(text[s['start_character']:s['end_character']].encode()),s['span_sha256'])
        self.assertTrue(all(s['omitted_context'] for s in spans))
        self.assertTrue(all(not s['standalone_faithfulness_validated'] for s in spans))

    def test_long_unpunctuated_source_is_explicit_window(self):
        spans=E.extractive_digest(' '.join(['word']*500),{'word':.4})
        self.assertTrue(all(not s['complete_sentence_or_paragraph'] for s in spans))

    def test_stable_id_changes_with_edition_or_span(self):
        r=record();text='What do you mean?';s=E.span(text,0,len(text),'question')
        a=E.identifier('unverified_question_candidate',r,[s])
        self.assertEqual(a,E.identifier('unverified_question_candidate',r,[s]))
        self.assertNotEqual(a,E.identifier('unverified_question_candidate',{**r,'selected_edition_id':'another'},[s]))

    def test_public_projection_removes_raw_source_content(self):
        rows,_=E.punctuation_records(record(),'What happened? Nobody knows.',{})
        result=E.public_record(rows[0]);V.check_public(result)
        self.assertNotIn('question_text',result);self.assertNotIn('supports',result)

    def test_public_gate_rejects_raw_text_and_private_path(self):
        with self.assertRaises(ValueError):V.check_public({'answer_text':'raw'})
        with self.assertRaises(ValueError):V.check_public({'url':'/workspace/private.txt'})

    def test_completed_resume_rejects_private_bank_tamper(self):
        ram=Path('/dev/shm/transcript-knowledge-2026-11');ram.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-resume-',dir=ram) as tmp:
            root=Path(tmp);frame=root/'fixture-frame.json';analysis=root/'fixture-analysis.json'
            E.save(frame,{'fixture_only':True});E.save(analysis,{'bindings':{'frame_sha256':E.sha(frame.read_bytes())}})
            E.save(root/'contract-private.json',{'policy':E.POLICY,'script_sha256':E.sha(Path(E.__file__).read_bytes()),
                'frame_sha256':E.sha(frame.read_bytes()),'analysis_sha256':E.sha(analysis.read_bytes()),'selected_source_ids':['fixture-source']})
            public=root/'fixture-public.json';bank=root/'private/question-bank.jsonl';profiles=root/'private/profiles-private.json'
            E.save(public,{'fixture_only':True});E.save(bank,{'fixture_only':True});E.save(profiles,{'fixture_only':True})
            pm=root/'private-manifest.json';E.save(pm,{'question_bank':E.ref(bank,root),'profiles':E.ref(profiles,root)})
            E.save(root/'output-manifest.json',{'public_allowlist':[E.ref(public,root)],'private_manifest':E.ref(pm,root)})
            fake=SimpleNamespace(load_frame=lambda path:[{'record':{'source_id':'fixture-source'},'text':''}])
            with patch.object(E,'source_loader',return_value=fake),contextlib.redirect_stdout(io.StringIO()):
                E.run(frame,analysis,root,resume=True)
                bank.write_bytes(bank.read_bytes()+b'corrupt')
                with self.assertRaisesRegex(ValueError,'Completed private bank changed'):E.run(frame,analysis,root,resume=True)


if __name__=='__main__':unittest.main()
