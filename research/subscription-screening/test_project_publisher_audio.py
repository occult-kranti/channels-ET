import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import hashlib

SPEC=importlib.util.spec_from_file_location('projection',Path(__file__).with_name('project_publisher_audio.py'))
P=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(P)

def artifact(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def write(path,data):path.write_text(json.dumps(data));return artifact(path)

class ProjectionTests(unittest.TestCase):
    def fixture(self,root):
        r={'source_id':'s','publication_id':'p','source_origin':'publisher_rss','source':{
            'handle':'@publisher','publisher':'Publisher','title':'Title','source_url':'https://publisher.example/episode'},
            'audio':{'bytes':5,'sha256':'a'*64,'probe':{'channels':1}},
            'lineage':{'original_bytes':10,'original_sha256':'b'*64,'actual_duration_difference_seconds':0},
            'decoded_16k_mono':{'duration_seconds':1},'duration_seconds':1,'duplicate_family_id':'original-sha256:'+'b'*64}
        acq=root/'acq.json';write(acq,{'status':'running','frame_count':229,'records':[r]})
        source=write(root/'source.json',r);model={'files_sha256':'c'*64}
        request=write(root/'request.json',{'source_id':'s','model':model,'acquisition_receipt':source})
        raw=write(root/'raw.jsonl',{'text':'DO NOT PUBLISH RAW TEXT'})
        diag=write(root/'diag.json',{'request_sha256':request['sha256'],'raw_segments':raw,'inference_stream_exhausted':True})
        code=write(root/'code.json',{'test':'codebinding'})
        hold={'source_id':'s','publication_id':'p','disposition':'held_unadmitted_asr','reason_code':'repeated_output_with_timestamp_overflow',
              'acquisition_receipt':source,'failed_request':request,'exhausted_diagnostic':diag,'raw_segments':raw,
              'original_inference_code':code,'original_collector_validator':code,'model':model,
              'diagnostic_metrics':{'raw_segment_count':2244,'unique_segment_texts':92,'most_repeated_count':2152,'ends_beyond_duration_plus_one_second':16}}
        holds=root/'holds.json';write(holds,{'status':'reviewed_source_specific_recognition_holds','records':[hold]})
        return acq,holds,source

    def test_pending_held_and_private_text_separation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,holds,_=self.fixture(root)
            before=P.project(acq,root/'public1.json',snapshot_dir=root/'snapshots')
            self.assertEqual(before['summary']['pending_local_asr'],1)
            after=P.project(acq,root/'public2.json',snapshot_dir=root/'snapshots',holds=holds)
            self.assertEqual(after['summary']['recognition_holds'],1);self.assertEqual(after['summary']['pending_local_asr'],0)
            self.assertEqual(after['summary']['retained_bytes'],5);self.assertEqual(after['summary']['asr_failed_editions'],1)
            self.assertEqual(after['records'][0]['collection_status'],'retained_full_duration_lossy_opus')
            text=(root/'public2.json').read_text();self.assertNotIn('DO NOT PUBLISH',text);self.assertNotIn(str(root),text)
            self.assertIn('recognition_holds',{s['kind'] for s in after['input_snapshots']})

    def test_valid_alternate_text_keeps_failed_edition_history(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,holds,source=self.fixture(root)
            output=write(root/'normalized.json',{'text':'alternate'})
            asr=root/'asr.json';write(asr,{'status':'selected_snapshot_complete','records':[{
                'status':'completed','publication_id':'p','acquisition_receipt':source,'outputs':{'normalized':output},
                'whitespace_words':1,'segment_count':1}]})
            d=P.project(acq,root/'public.json',asr=asr,snapshot_dir=root/'snapshots',holds=holds)
            self.assertEqual(d['summary']['local_asr_completed'],1);self.assertEqual(d['summary']['recognition_holds'],0)
            self.assertEqual(d['summary']['asr_failed_editions'],1);self.assertEqual(d['records'][0]['transcript_status'],'local_asr_completed')

    def test_empty_recognition_not_pending(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,_,source=self.fixture(root);output=write(root/'empty.json',{'text':''})
            asr=root/'asr.json';write(asr,{'records':[{'status':'completed_empty_recognition','publication_id':'p',
                'acquisition_receipt':source,'outputs':{'normalized':output},'whitespace_words':0,'segment_count':0}]})
            d=P.project(acq,root/'public.json',asr=asr,snapshot_dir=root/'snapshots')
            self.assertEqual(d['summary']['local_asr_empty_recognition'],1);self.assertEqual(d['summary']['pending_local_asr'],0)
            self.assertEqual(d['summary']['local_asr_completed'],0)

    def test_tampered_hold_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,holds,_=self.fixture(root);(root/'raw.jsonl').write_text('changed')
            with self.assertRaises(ValueError):P.project(acq,root/'public.json',snapshot_dir=root/'snapshots',holds=holds)

    def test_second_reason_and_review_provenance_are_explicit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,holds,_=self.fixture(root);ledger=json.loads(holds.read_text())
            ledger['records'][0].update(reason_code='multiple_segments_outside_audio',review_status='pending_independent_source_review',human_reviewed=False)
            write(holds,ledger)
            d=P.project(acq,root/'public.json',snapshot_dir=root/'snapshots',holds=holds)
            failed=d['records'][0]['asr_failed_editions'][0]
            self.assertEqual(failed['reason_code'],'multiple_segments_outside_audio');self.assertFalse(failed['human_reviewed'])
            self.assertEqual(failed['review_status'],'pending_independent_source_review');self.assertIsNone(failed['quarantine_policy_sha256'])
            del ledger['records'][0]['human_reviewed'];write(holds,ledger)
            d=P.project(acq,root/'public2.json',snapshot_dir=root/'snapshots',holds=holds)
            self.assertIsNone(d['records'][0]['asr_failed_editions'][0]['human_reviewed'])

    def test_unknown_automatic_policy_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);acq,holds,_=self.fixture(root);ledger=json.loads(holds.read_text())
            ledger.update(status='policy_validated_source_specific_recognition_holds',policy_code_sha256='not-reviewed')
            write(holds,ledger)
            with self.assertRaises(ValueError):P.project(acq,root/'public.json',snapshot_dir=root/'snapshots',holds=holds)

if __name__=='__main__':unittest.main()
