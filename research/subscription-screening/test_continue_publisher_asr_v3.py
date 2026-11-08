import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('queue',Path(__file__).with_name('continue_publisher_asr_v3.py'))
Q=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(Q)

class QueueTests(unittest.TestCase):
    def fixture(self,root,status='running',records=None):
        acquisition=root/'audio.json';acquisition.write_text(json.dumps({'status':status,'records':records or []}))
        holds=root/'holds.json';holds.write_text(json.dumps({'status':'reviewed_source_specific_recognition_holds','records':[]}))
        return argparse.Namespace(acquisition=acquisition,output=root/'out',pcm_root=root/'pcm',holds=holds)

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

    def test_held_source_excluded_with_incomplete_recognition_status(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);held={'source_id':'held','publication_id':'p','caption_link':None};other={'source_id':'other','caption_link':{'records':[1]}}
            args=self.fixture(root,'frame_complete',[held,other]);args.output.mkdir()
            (args.output/'manifest.json').write_text(json.dumps({'status':'halted','failed_source_id':'held'}))
            hold={'source_id':'held','publication_id':'p','disposition':'held_unadmitted_asr','reason_code':'repeated_output_with_timestamp_overflow','acquisition_receipt':{'path':'fake'}}
            selected=[]
            def fake_main(argv):
                data=json.loads(Path(argv[argv.index('--acquisition')+1]).read_text());selected.extend(data['records'])
                (args.output/'manifest.json').write_text(json.dumps({'status':'selected_snapshot_complete','records':[]}))
            with patch.object(Q,'validate_holds',return_value={'held':hold}),patch.object(Q.C,'completed',return_value=held),patch.object(Q.D,'main',side_effect=fake_main):Q.run(args)
            self.assertEqual(selected,[other]);status=json.loads((args.output/'queue-status.json').read_text())
            self.assertEqual(status['status'],'selected_frame_complete_with_recognition_holds');self.assertEqual(status['recognition_hold_count'],1)

    def test_hold_binds_source_model_and_diagnostic_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);model={'path':str(root/'model')};source={'source_id':'a','publication_id':'p','decoded_16k_mono':{'duration_seconds':50}}
            acquisition=root/'acquisition.json';acquisition.write_text('{}');ab=Q.C.artifact(acquisition)
            request=root/'request.json';Q.C.dump(request,{'source_id':'a','acquisition_receipt':ab,'model':model})
            raw=root/'raw.jsonl';raw.write_text('\n'.join(json.dumps({'text':'repeat','end_repr':str(i+1)}) for i in range(100))+'\n')
            rb=Q.C.artifact(raw);diagnostic=root/'diagnostic.json'
            Q.C.dump(diagnostic,{'request_sha256':Q.C.sha(request),'raw_segments':rb,'inference_stream_exhausted':True,'first_timestamp_failure':{'reason':'beyond_duration'}})
            hold={'source_id':'a','publication_id':'p','disposition':'held_unadmitted_asr','reason_code':'repeated_output_with_timestamp_overflow',
                  'acquisition_receipt':ab,'failed_request':Q.C.artifact(request),'exhausted_diagnostic':Q.C.artifact(diagnostic),'raw_segments':rb,
                  'original_inference_code':Q.C.artifact(Q.D.__file__),'original_collector_validator':Q.C.artifact(Q.C.__file__),'model':model,
                  'diagnostic_metrics':{'raw_segment_count':100,'unique_segment_texts':1,'most_repeated_text':'repeat','most_repeated_count':100,'ends_beyond_duration_plus_one_second':49}}
            ledger=root/'holds.json';Q.C.dump(ledger,{'status':'reviewed_source_specific_recognition_holds','records':[hold]})
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model):self.assertEqual(list(Q.validate_holds(ledger)),['a'])
            with patch.object(Q.C,'completed',return_value={**source,'source_id':'swapped'}),patch.object(Q.D.CORE,'local_model_binding',return_value=model),self.assertRaises(ValueError):Q.validate_holds(ledger)
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value={'path':'changed'}),self.assertRaises(ValueError):Q.validate_holds(ledger)
            raw.write_text('tampered')
            with patch.object(Q.C,'completed',return_value=source),self.assertRaises(ValueError):Q.validate_holds(ledger)

if __name__=='__main__':unittest.main()
