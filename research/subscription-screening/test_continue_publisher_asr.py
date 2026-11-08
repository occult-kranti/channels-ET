import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('queue',Path(__file__).with_name('continue_publisher_asr.py'))
Q=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(Q)

class QueueTests(unittest.TestCase):
    def fixture(self,root,status='running',records=None):
        acquisition=root/'audio.json';acquisition.write_text(json.dumps({'status':status,'records':records or []}))
        return argparse.Namespace(acquisition=acquisition,output=root/'out',pcm_root=root/'pcm')

    def test_completed_caption_only_frame_finalizes_once(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root,'frame_complete',[{'source_id':'a','caption_link':{'records':[1]}}])
            def fake_main(argv):
                (args.output/'manifest.json').write_text(json.dumps({'status':'selected_snapshot_complete','records':[]}))
            with patch.object(Q.D,'main',side_effect=fake_main) as call:Q.run(args)
            self.assertEqual(call.call_count,1)
            status=json.loads((args.output/'queue-status.json').read_text())
            self.assertEqual(status['status'],'frame_complete');self.assertEqual(status['exact_caption_linked_count'],1)

    def test_missing_source_diagnostic_halts_without_retry_loop(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root,records=[{'source_id':'a'}])
            with patch.object(Q.D,'main',side_effect=ValueError('preflight failure')) as call,self.assertRaises(ValueError):Q.run(args)
            self.assertEqual(call.call_count,1)
            self.assertEqual(json.loads((args.output/'queue-status.json').read_text())['status'],'halted_without_bound_source_diagnostic')

    def test_unrecoverable_bound_failure_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root);args.output.mkdir()
            (args.output/'manifest.json').write_text(json.dumps({'status':'halted','failed_source_id':'a','records':[]}))
            with self.assertRaises(FileNotFoundError):Q.run(args)
            self.assertEqual(json.loads((args.output/'queue-status.json').read_text())['status'],'halted_unrecoverable_diagnostic')

    def test_existing_receipt_failure_does_not_retry(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root,records=[{'source_id':'a'}]);args.output.mkdir()
            folder=args.output/'items'/Q.C.hashlib.sha256(b'a').hexdigest()[:20];folder.mkdir(parents=True);(folder/'receipt.json').write_text('{}')
            def fake_main(argv):
                (args.output/'manifest.json').write_text(json.dumps({'status':'halted','failed_source_id':'a','created_at':'new'}))
                raise ValueError('tampered receipt')
            with patch.object(Q.D,'main',side_effect=fake_main) as call,self.assertRaises(ValueError):Q.run(args)
            self.assertEqual(call.call_count,1)
            self.assertEqual(json.loads((args.output/'queue-status.json').read_text())['status'],'halted_existing_receipt_validation_failure')

    def test_new_final_snapshot_is_validated_then_terminates(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root,'frame_complete',[{'source_id':'a'}])
            def fake_main(argv):
                folder=args.output/'items'/Q.C.hashlib.sha256(b'a').hexdigest()[:20];folder.mkdir(parents=True,exist_ok=True)
                (folder/'receipt.json').write_text('{}');(args.output/'manifest.json').write_text(json.dumps({'status':'selected_snapshot_complete','records':[]}))
            with patch.object(Q.D,'main',side_effect=fake_main) as call:Q.run(args)
            self.assertEqual(call.call_count,2)
            self.assertEqual(json.loads((args.output/'queue-status.json').read_text())['status'],'frame_complete')

    def test_stale_halted_manifest_cannot_authorize_retry(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=self.fixture(root,records=[{'source_id':'a'}]);args.output.mkdir()
            (args.output/'manifest.json').write_text(json.dumps({'status':'halted','failed_source_id':'a','created_at':'old'}))
            folder=args.output/'items'/Q.C.hashlib.sha256(b'a').hexdigest()[:20];folder.mkdir(parents=True)
            def fake_recover(path):
                (path/'receipt.json').write_text('{}')
                return {'normalization_recovery':{'quality':{}}}
            with patch.object(Q.R,'validate_diagnostic'),patch.object(Q.R,'recover',side_effect=fake_recover),patch.object(Q.D,'main',side_effect=ValueError('preflight')) as call,self.assertRaises(ValueError):Q.run(args)
            self.assertEqual(call.call_count,1)
            self.assertEqual(json.loads((args.output/'queue-status.json').read_text())['status'],'halted_without_bound_source_diagnostic')

if __name__=='__main__':unittest.main()
