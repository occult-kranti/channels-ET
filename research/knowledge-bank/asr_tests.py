#!/usr/bin/env python3
"""Focused tests for ASR metric boundaries, provenance and bounded supervision."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import asr_download as D
import asr_orchestrate as O
import asr_summarize as S
import asr_worker as W


class ASRTests(unittest.TestCase):
    def test_normalization_preserves_negation(self):
        self.assertEqual(S.words('CAN’T deny ＲＡ.'),["can't",'deny','ra'])
        value=S.compare('There is no contact.','There is contact.')
        self.assertEqual(value['baseline_negation_cues'],1)
        self.assertEqual(value['upgraded_negation_cues'],0)
        self.assertEqual(value['symmetric_normalized_word_edit_distance'],.25)

    def test_word_order_is_not_set_agreement(self):
        x=S.compare('A follows B','B follows A')
        self.assertEqual(x['token_set_jaccard'],1)
        self.assertGreater(x['symmetric_normalized_word_edit_distance'],0)

    def test_empty_and_symmetric_distance(self):
        self.assertEqual(S.compare('','')['symmetric_normalized_word_edit_distance'],0)
        self.assertEqual(S.compare('','')['token_set_jaccard'],1)
        for a,b in [('one two','one'),('never contact','contact now'),('','word')]:
            self.assertEqual(S.compare(a,b)['symmetric_normalized_word_edit_distance'],S.compare(b,a)['symmetric_normalized_word_edit_distance'])

    def test_repetition_retained_as_diagnostic(self):
        x=S.compare('yes '*112,'contact remains uncertain')
        self.assertEqual(x['baseline_longest_identical_token_run'],112)
        self.assertEqual(x['baseline_longest_identical_token_run_ratio'],1)
        self.assertEqual(x['baseline_analysis_tokens'],112)

    def test_same_size_tampering_rejected(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as name:
            p=Path(name)/'a';p.write_bytes(b'old')
            ref={'path':str(p),'bytes':3,'sha256':hashlib.sha256(b'old').hexdigest()}
            p.write_bytes(b'new')
            with self.assertRaisesRegex(ValueError,'changed'):S.checked(ref)

    def test_download_guard_before_network(self):
        with self.assertRaisesRegex(ValueError,'RAM|/dev/shm'):
            D.download('nvidia/parakeet-tdt-0.6b-v3','a'*40,Path('/workspace/invalid-model-output'),Path('/tmp/unused-receipt'))

    def test_empty_model_and_unsafe_clip_rejected(self):
        for clips,needle in [([{'clip_id':'a'}],'Required model'),([{'clip_id':'../a'}],'path-safe'),([{'clip_id':'a'},{'clip_id':'a'}],'unique')]:
            with tempfile.TemporaryDirectory(dir=O.PRIVATE) as name:
                root=Path(name);request=root/'request.json'
                request.write_text(json.dumps({'clips':clips,'cpu_threads':1,'engine':'parakeet_transformers','model_files':[]}))
                with self.assertRaisesRegex(ValueError,needle):W.run(request,root/'out')

    def test_stage_deadline_terminates_only_owned_worker(self):
        class Process:
            pid=42424242
            returncode=None
            terminated=False
            def poll(self):return self.returncode
            def terminate(self):self.terminated=True;self.returncode=-15
            def kill(self):self.returncode=-9
            def wait(self,timeout=None):return self.returncode
        process=Process()
        with tempfile.TemporaryDirectory(dir='/dev/shm') as ramname,tempfile.TemporaryDirectory(dir=O.PRIVATE) as name:
            root=Path(name);ram=Path(ramname)
            with patch.object(O,'RAM',ram),patch.object(O.subprocess,'Popen',return_value=process),patch.object(O.time,'time',side_effect=[0,0,10,10]):
                with self.assertRaisesRegex(TimeoutError,'stage hard'):
                    O.supervise([{'engine':'parakeet_transformers','clips':[{'clip_id':'x'}]}],root/'stage',private_budget_root=root,max_stage_seconds=1)
            self.assertTrue(process.terminated)
            receipt=json.loads((root/'stage/stage-receipt.json').read_text())
            self.assertEqual(receipt['status'],'failed')


if __name__=='__main__':unittest.main()
