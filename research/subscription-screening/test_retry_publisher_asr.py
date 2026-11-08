import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('fallback',Path(__file__).with_name('retry_publisher_asr.py'))
F=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(F)

def rows(values):
    return [{'segment_index':i,'start_repr':str(a),'end_repr':str(b),'text':text,
             'avg_logprob_repr':'None','no_speech_prob_repr':'None'} for i,(a,b,text) in enumerate(values)]

def held_fixture(root,source):
    failed=root/'failed';failed.mkdir();audio_receipt=failed/'source.json';audio_receipt.write_text('{}')
    ab=F.C.artifact(audio_receipt);old_model={'path':str(root/'old-model')}
    request={'source_id':F.SOURCE_ID,'acquisition_receipt':ab,'model':old_model}
    F.C.dump(failed/'request.json',request)
    raw=rows([(i,i+1,'repeat') for i in range(100)]);(failed/'raw.jsonl').write_text('\n'.join(json.dumps(x) for x in raw)+'\n')
    diagnostic={'request_sha256':F.C.sha(failed/'request.json'),'raw_segments':F.C.artifact(failed/'raw.jsonl'),
                'inference_stream_exhausted':True,'raw_segment_count':100}
    F.C.dump(failed/'diagnostic.json',diagnostic)
    hold={'source_id':F.SOURCE_ID,'publication_id':source['publication_id'],'disposition':'held_unadmitted_asr',
          'reason_code':'repeated_output_with_timestamp_overflow','acquisition_receipt':ab,
          'failed_request':F.C.artifact(failed/'request.json'),'exhausted_diagnostic':F.C.artifact(failed/'diagnostic.json'),
          'raw_segments':F.C.artifact(failed/'raw.jsonl'),'original_inference_code':F.C.artifact(F.DERIVATIVE_PATH),
          'original_collector_validator':F.C.artifact(F.C.__file__),'model':old_model}
    return {'status':'reviewed_source_specific_recognition_holds','records':[hold]},hold,old_model

class FallbackTests(unittest.TestCase):
    def test_valid_structural_output_and_exact_words(self):
        raw=rows([(0,1,' First words '),(1,2,'Different words.')]);r=F.classify(raw,2.1)
        self.assertTrue(r['admitted']);self.assertEqual(r['normalization_status'],'unadjusted')
        self.assertEqual([x['text'] for x in r['segments']],['First words','Different words.'])

    def test_only_bounded_terminal_end_normalized(self):
        raw=rows([(0,10,'First'),(95,105,'Last')]);r=F.classify(raw,100)
        self.assertTrue(r['admitted']);self.assertEqual(r['segments'][-1]['end_seconds'],100)
        self.assertEqual(r['quality']['timestamp_maximum_adjustment_seconds'],5)
        self.assertFalse(r['quality']['text_changed_by_repair'])

    def test_invalid_or_multiple_timestamps_never_admitted(self):
        candidates=[rows([(0,105,'First'),(95,106,'Last')]),rows([(0,10,'First'),(95,135,'Last')]),
                    rows([(10,11,'First'),(5,12,'Last')]),rows([(0,1,'First'),('nan',2,'Last')])]
        for raw in candidates:
            with self.subTest(raw=raw):self.assertFalse(F.classify(raw,100)['admitted'])

    def test_repetition_quality_hold_does_not_delete_words(self):
        raw=rows([(i/10,(i+1)/10,'same') for i in range(110)]);before=copy.deepcopy(raw)
        r=F.classify(raw,12)
        self.assertFalse(r['admitted']);self.assertEqual(r['reason'],'repetition_quality_hold_pending_audio_review')
        self.assertEqual(r['metrics']['most_repeated_count'],110);self.assertEqual(raw,before)
        self.assertFalse(F.classify([],12)['admitted'])

    def test_one_retry_reservation_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'request.json';p.write_text('{}');h={'failed_request':{'path':str(p)}}
            F.reserve_once(h,root/'new',{'attempt':'test'})
            with self.assertRaises(FileExistsError):F.reserve_once(h,root/'different-output',{'attempt':'test'})
            self.assertTrue(p.exists())

    def test_pinned_model_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);F.C.dump(root/'manifest.json',{'model':'wrong'})
            with self.assertRaises(ValueError):F.bind_model(root)
            F.C.dump(root/'manifest.json',{'model':'Systran/faster-whisper-tiny','revision':F.MODEL_REVISION,'status':'downloaded_and_upstream_hash_verified','files':[],'license':'mit'})
            with patch.object(F.CORE,'local_model_binding',return_value={'language_mode':'multilingual','files':[{'path':'model.bin','sha256':'0'*64,'bytes':1}]}),self.assertRaises(ValueError):F.bind_model(root)

    def test_hold_audio_source_model_and_collection_gate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source={'source_id':F.SOURCE_ID,'publication_id':'pub','source':{'language':'en'},'decoded_16k_mono':{'duration_seconds':100}}
            ledger,h,old=held_fixture(root,source);acq={'status':'frame_complete','records':[source]}
            with patch.object(F.C,'completed',return_value=source),patch.object(F.CORE,'local_model_binding',return_value=old):
                self.assertEqual(F.validate_hold(ledger,acq)[1],source)
                with self.assertRaises(ValueError):F.validate_hold(ledger,{**acq,'status':'running'})
                with self.assertRaises(ValueError):F.validate_hold(ledger,{**acq,'records':[{**source,'publication_id':'other'}]})
            with patch.object(F.C,'completed',return_value=source),patch.object(F.CORE,'local_model_binding',return_value={'path':'changed'}),self.assertRaises(ValueError):F.validate_hold(ledger,acq)
            Path(h['raw_segments']['path']).write_text('tampered')
            with patch.object(F.C,'completed',return_value=source),self.assertRaises(ValueError):F.validate_hold(ledger,acq)

    def test_real_pcm_mock_recognition_output_lineage(self):
        # The model is mocked; actual FFmpeg/Opus and exact full-PCM verification run.
        with tempfile.TemporaryDirectory() as t,tempfile.TemporaryDirectory(dir='/dev/shm') as ram:
            root=Path(t);fixture=root/'source.mp3'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2.1','-ac','2','-c:a','libmp3lame',str(fixture)],check=True)
            collection=root/'collection';collection.mkdir()
            item={'source_id':F.SOURCE_ID,'publication_id':'pub','source_origin':'publisher_rss','audio_url':'https://publisher.example/a.mp3',
                  'duration_seconds_publisher':2.1,'language':'en','guid':'g'}
            def download(url,path,dest):
                shutil.copyfile(fixture,path)
                return {'enclosure_url':url,'final_url':url,'sha256':F.C.sha(path),'bytes':Path(path).stat().st_size}
            with patch.object(F.C,'download',side_effect=download):source,_=F.C.acquire(item,collection,0,[])
            ledger,h,old=held_fixture(root,source)
            # Replace synthetic source receipt binding with the real complete source.
            h['acquisition_receipt']=F.C.artifact(Path(source['audio']['path']).parent/'receipt.json')
            req=Path(h['failed_request']['path']);F.C.dump(req,{'source_id':F.SOURCE_ID,'acquisition_receipt':h['acquisition_receipt'],'model':old});h['failed_request']=F.C.artifact(req)
            diag=Path(h['exhausted_diagnostic']['path']);data=json.loads(diag.read_text());data['request_sha256']=h['failed_request']['sha256'];F.C.dump(diag,data);h['exhausted_diagnostic']=F.C.artifact(diag)
            acq=root/'acquisition.json';F.C.dump(acq,{'status':'frame_complete','records':[source]});holds=root/'holds.json';F.C.dump(holds,ledger)
            model={'path':str(root/'model'),'language_mode':'multilingual','files_sha256':'test-only','files':[]}
            provenance={'revision':F.MODEL_REVISION,'test_only':True}
            def recognize(wav,out,path,languages,threads):
                raw=rows([(0.1,1,'Different words'),(1.1,4.2,'Another phrase')])
                (out/'asr-raw-segments.jsonl').write_text('\n'.join(json.dumps(r) for r in raw)+'\n')
                return raw,{'language_requested':'en','language_reported':'en','language_plan':languages,'decoder_duration_seconds':2.1,
                            'settings':F.SETTINGS,'human_reviewed':False,'cpu_threads':threads,'device':'cpu','compute_type':'int8','num_workers':1,'local_files_only':True}
            args=argparse.Namespace(acquisition=acq,holds=holds,output=root/'retry',pcm_root=Path(ram)/'retry-pcm',model=root/'model',cpu_threads=1)
            with patch.object(F,'bind_model',return_value=(model,provenance)),patch.object(F.CORE,'local_model_binding',return_value=old),patch.object(F,'recognize',side_effect=recognize),patch.object(F.CORE,'versions',return_value={'test_only':True}):
                F.run(args);receipt=args.output/'receipt.json';r=F.verify_result(receipt)
                self.assertEqual(r['source_id'],F.SOURCE_ID+F.EDITION_SUFFIX);self.assertFalse((args.pcm_root/'decoded.wav').exists())
                for key,value in [('source_id','swapped'),('whitespace_words',99),('publication_id','swapped')]:
                    changed=copy.deepcopy(r);changed[key]=value;F.C.dump(receipt,changed)
                    with self.assertRaises(ValueError):F.verify_result(receipt)
                F.C.dump(receipt,r)
                request_path=Path(r['request']['path']);completion_path=Path(r['diagnostic_completion']['path'])
                normalized_path=Path(r['outputs']['normalized']['path'])
                base_request=json.loads(request_path.read_text());base_completion=json.loads(completion_path.read_text());base_normalized=json.loads(normalized_path.read_text())
                saved={p:p.read_bytes() for p in (receipt,request_path,completion_path,normalized_path)}
                def assert_semantic_rejection(mutate):
                    rr=copy.deepcopy(r);rq=copy.deepcopy(base_request);nn=copy.deepcopy(base_normalized);cc=copy.deepcopy(base_completion)
                    mutate(rr,rq,nn,cc)
                    F.C.dump(request_path,rq);rr['request']=F.C.artifact(request_path)
                    F.C.dump(normalized_path,nn);rr['outputs']['normalized']=F.C.artifact(normalized_path)
                    cc['request']=rr['request'];cc['asr']=rr['asr'];cc['comparison']=rr['comparison']
                    F.C.dump(completion_path,cc);rr['diagnostic_completion']=F.C.artifact(completion_path)
                    F.C.dump(receipt,rr)
                    with self.assertRaises(ValueError):F.verify_result(receipt)
                    for p,b in saved.items():p.write_bytes(b)
                def wrong_pcm(rr,rq,nn,cc):
                    rr['decoder']['sample_count']=1;rq['decoder']=copy.deepcopy(rr['decoder'])
                def wrong_eof(rr,rq,nn,cc):
                    rr['decoder']['natural_eof']=False;rq['decoder']=copy.deepcopy(rr['decoder'])
                def relabel_repaired(rr,rq,nn,cc):
                    rr['normalization_status']='unadjusted';rr['normalization_recovery']={}
                    nn['normalization_status']='unadjusted';nn['timestamp_quality']=None
                    cc['decision']['normalization_status']='unadjusted';cc['decision']['quality']=None
                def wrong_provenance(rr,rq,nn,cc):
                    rr['model_provenance']['revision']='changed';rq['model_provenance']=copy.deepcopy(rr['model_provenance'])
                for mutate in (wrong_pcm,wrong_eof,relabel_repaired,wrong_provenance,
                               lambda rr,rq,nn,cc:rq.update(source_id='swapped'),
                               lambda rr,rq,nn,cc:rr['asr'].update(cpu_threads=2),
                               lambda rr,rq,nn,cc:nn['turns'][-1].pop('original_end_seconds'),
                               lambda rr,rq,nn,cc:cc['decision'].update(reason='invented reason')):
                    assert_semantic_rejection(mutate)
                raw_path=Path(r['raw_diagnostic']['path']);raw_path.write_text('tampered')
                with self.assertRaises(ValueError):F.verify_result(receipt)
            self.assertTrue(Path(h['failed_request']['path']).exists());self.assertTrue(fixture.exists())

if __name__=='__main__':unittest.main()
