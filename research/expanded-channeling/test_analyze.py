import importlib.util,json,tempfile,unittest
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('expanded',Path(__file__).with_name('analyze.py'));M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Contract(unittest.TestCase):
    def test_mask_preserves_contractions_and_negation(self):
        self.assertEqual(M.mask_tokens("Don and Ra don't know what we'll never believe"),['and',"don't",'what',"we'll",'never','believe'])
    def test_centered_window_does_not_pad_short_texts(self):
        self.assertIsNone(M.centered('one two three',4));self.assertEqual(M.centered('a b c d e f',4),'b c d e')
    def test_within_diagonal_excludes_self_and_symmetric_duplicates(self):
        docs=[{'summary':{'group_id':'ra_published'}},{'summary':{'group_id':'ra_published'}},{'summary':{'group_id':'bashar_context'}}]
        r=M.grouped(np.array([[1,.4,.2],[.4,1,.6],[.2,.6,1]]),docs)
        self.assertEqual(r['pair_counts'],[[1,2],[2,0]]);self.assertEqual(r['matrix'],[[.4,.4],[.4,None]])
    def test_missing_question_remains_unavailable(self):
        d={'summary':{'source_id':'x','group_id':'ra_published','source_kind':'publisher_transcript','source_url':'https://example.test/s'},'turns':[{'turn_id':'q','role':'questioner','text':'[Question missing]','question_id':'1.6'},{'turn_id':'a','role':'response','text':'A printed answer.','question_id':'1.6'}]}
        q=M.qa_items([d])[0];self.assertFalse(q['question_available']);self.assertTrue(q['answer_identified'])
    def test_unknown_speaker_cannot_become_response(self):
        d={'summary':{'source_id':'x','group_id':'tracy_kumbera','source_url':'https://example.test'},'turns':[{'turn_id':'t1','text':'What is healing? Why this body?'},{'turn_id':'t2','text':'Following words are not automatically an answer.'}]}
        q=M.qa_items([d]);self.assertEqual(len(q),2)
        self.assertTrue(all(x['response'] is None and not x['answer_identified'] and x['role']=='unverified_punctuation_unknown_speaker' for x in q))
    def test_fixture_and_changed_binding_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.json';p.write_text('{"fixture_only":true}')
            with self.assertRaisesRegex(ValueError,'Synthetic'):M.bound(p)
            p.write_text('{"ok":true}')
            with self.assertRaisesRegex(ValueError,'hash differs'):M.bound(p,'0'*64)
    def test_private_output_rejects_git_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.git').mkdir();(root/'.git'/'HEAD').write_text('main')
            with self.assertRaisesRegex(ValueError,'outside Git'):M.A.safe_path(root/'qa.json',private=True,exists=False)
    def test_generic_fragment_has_no_retrieval_eligibility(self):
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
        tokens=set(M.mask_tokens('But how did, when were we first?'))-set(ENGLISH_STOP_WORDS)-{'did'}
        self.assertLess(len(tokens),4)

if __name__=='__main__':unittest.main()
