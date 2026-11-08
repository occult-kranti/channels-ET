import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('queue',Path(__file__).with_name('continue_publisher_asr_v4.py'))
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

class QuarantineTests(unittest.TestCase):
    def fixture(self, root):
        import wave, hashlib
        output=root/'out';folder=output/'items'/Q.C.hashlib.sha256(b'a').hexdigest()[:20];folder.mkdir(parents=True)
        for name,src in [('executed-audio-derivative-v2.py',Q.D.__file__),('executed-collector-validator.py',Q.C.__file__)]: (output/name).write_bytes(Path(src).read_bytes())
        pcmroot=root/'pcm';wav=pcmroot/folder.name/'decoded.wav';wav.parent.mkdir(parents=True)
        rawpcm=b'\x00\x00'*16000
        with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(rawpcm)
        log=folder/'pcm-decoder.log';log.write_bytes(b'')
        proof={'sample_count':16000,'duration_seconds':1.0,'raw_pcm_sha256':hashlib.sha256(rawpcm).hexdigest()}
        source={'source_id':'a','publication_id':'p','audio':{'path':str(root/'retained.opus')},'decoded_16k_mono':proof}
        acquisition=root/'acquisition.json';Q.C.dump(acquisition,source);ab=Q.C.artifact(acquisition)
        model={'path':str(root/'model')};lang={'effective_language_argument':'en'}
        command=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',source['audio']['path'],'-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar','16000','-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
        request={'source_id':'a','acquisition_receipt':ab,'model':model,'language_plan':lang,'decoder':{**proof,'artifact':Q.C.artifact(wav),'natural_eof':True,'decoder_returncode':0,'cap_bytes':Q.D.PCM_CAP,'stderr_artifact':Q.C.artifact(log),'command':command}}
        Q.C.dump(folder/'request.json',request)
        rows=[{'segment_index':i,'text':str(i),'start_repr':repr(a),'end_repr':repr(b)} for i,(a,b) in enumerate([(0.0,.5),(1.0,2.5),(2.0,3.0)])]
        raw=folder/'asr-raw-segments.jsonl';raw.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        diagnostic={'status':'diagnostic_only_not_admitted','inference_stream_exhausted':True,'raw_segment_count':3,'raw_segments':Q.C.artifact(raw),'request_sha256':Q.C.sha(folder/'request.json'),'asr':{'language_plan':lang,'decoder_duration_seconds':1.0},'first_timestamp_failure':{'segment_index':1,'start_repr':'1.0','end_repr':'2.5','previous_start_repr':'0.0','decoded_duration_repr':'1.0','reason':'beyond_duration'}}
        Q.C.dump(folder/'asr-diagnostic-completion.json',diagnostic)
        return output,folder,source,model,pcmroot

    def make_hold(self,root):
        output,folder,source,model,pcmroot=self.fixture(root)
        with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model):h=Q.quarantine(folder,output,pcmroot)
        return output,folder,source,model,pcmroot,h

    def test_full_attempt_and_replay(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out,folder,source,model,pcmroot,h=self.make_hold(root)
            ledger=root/'holds.json';seed=root/'seed.json';Q.C.dump(seed,{'status':'reviewed_source_specific_recognition_holds','records':[]});Q.C.dump(ledger,{'status':'policy_validated_source_specific_recognition_holds','policy_code_sha256':Q.EXECUTION_SHA,'initial_ledger':Q.C.artifact(seed),'initial_ledger_sha256':Q.C.sha(seed),'records':[h]})
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model):self.assertEqual(list(Q.validate_holds(ledger)),['a'])
            self.assertEqual(h['reason_code'],'multiple_segments_outside_audio');self.assertFalse(h['human_reviewed'])

    def test_first_row_overflow_preserves_integer_previous_start(self):
        with tempfile.TemporaryDirectory() as t:
            out,folder,source,model,pcmroot=self.fixture(Path(t));raw=folder/'asr-raw-segments.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()];rows[0]['end_repr']='2.1';raw.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            dp=folder/'asr-diagnostic-completion.json';d=json.loads(dp.read_text());d['raw_segments']=Q.C.artifact(raw);d['first_timestamp_failure']={'segment_index':0,'start_repr':'0.0','end_repr':'2.1','previous_start_repr':'0','decoded_duration_repr':'1.0','reason':'beyond_duration'};Q.C.dump(dp,d)
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model):self.assertEqual(Q.quarantine(folder,out,pcmroot)['diagnostic_metrics']['ends_beyond_duration_plus_one_second'],3)

    def test_rehashed_bad_raw_and_first_failure_never_admitted(self):
        mutations=[lambda rows:rows[0].update(start_repr='nan'),lambda rows:rows[2].update(start_repr='0.0'),lambda rows:rows[0].update(segment_index=4),lambda rows:rows[1].update(end_repr='1.5')]
        for mutation in mutations:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as t:
                root=Path(t);out,folder,source,model,pcmroot=self.fixture(root);raw=folder/'asr-raw-segments.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()];mutation(rows);raw.write_text(''.join(json.dumps(x)+'\n' for x in rows))
                dp=folder/'asr-diagnostic-completion.json';d=json.loads(dp.read_text());d['raw_segments']=Q.C.artifact(raw);Q.C.dump(dp,d)
                with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model),self.assertRaises(ValueError):Q.quarantine(folder,out,pcmroot)

    def test_rehashed_decoder_and_incomplete_inference_rejected(self):
        for field,value in [('sample_count',15999),('natural_eof',False),('decoder_returncode',1),('raw_pcm_sha256','0'*64),('command',[])]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as t:
                out,folder,source,model,pcmroot=self.fixture(Path(t));rp=folder/'request.json';r=json.loads(rp.read_text());r['decoder'][field]=value;Q.C.dump(rp,r);dp=folder/'asr-diagnostic-completion.json';d=json.loads(dp.read_text());d['request_sha256']=Q.C.sha(rp);Q.C.dump(dp,d)
                with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model),self.assertRaises(ValueError):Q.quarantine(folder,out,pcmroot)
        with tempfile.TemporaryDirectory() as t:
            out,folder,source,model,pcmroot=self.fixture(Path(t));dp=folder/'asr-diagnostic-completion.json';d=json.loads(dp.read_text());d['inference_stream_exhausted']=False;Q.C.dump(dp,d)
            with patch.object(Q.C,'completed',return_value=source),self.assertRaises(ValueError):Q.quarantine(folder,out,pcmroot)

    def test_hold_policy_markers_and_actual_pcm_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out,folder,source,model,pcmroot,h=self.make_hold(root);ledger=root/'holds.json';seed=root/'seed.json';Q.C.dump(seed,{'status':'reviewed_source_specific_recognition_holds','records':[]})
            for key,value in [('quarantine_policy_sha256','changed'),('human_reviewed',True),('diagnostic_metrics',{}),('review_status','pending')]:
                bad={**h,key:value};Q.C.dump(ledger,{'status':'policy_validated_source_specific_recognition_holds','policy_code_sha256':Q.EXECUTION_SHA,'initial_ledger':Q.C.artifact(seed),'initial_ledger_sha256':Q.C.sha(seed),'records':[bad]})
                with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model),self.assertRaises(ValueError):Q.validate_holds(ledger)
            wav=Path(h['failed_pcm_preserved']['path']);wav.write_bytes(b'broken')
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model),self.assertRaises(ValueError):Q.quarantine(folder,out,pcmroot)

    def test_old_pcm_protected_and_new_tmpfs_cleanup_replay(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
            root=Path(t);out,folder,source,model,pcmroot,h=self.make_hold(root);wav=Path(h['failed_pcm_preserved']['path'])
            Q.dispose_new_failed_pcm(h,folder,pcmroot,{'a'});self.assertTrue(wav.exists());self.assertNotIn('pcm_cleanup',h)
            with patch.object(Q.C,'completed',return_value=source),patch.object(Q.D.CORE,'local_model_binding',return_value=model):
                Q.dispose_new_failed_pcm(h,folder,pcmroot,set());self.assertFalse(wav.exists());Q.inspect_attempt(folder,out,h['pcm_cleanup'])
                cp=Path(h['pcm_cleanup']['path']);d=json.loads(cp.read_text());d['verified_sample_count']=1;Q.C.dump(cp,d);h['pcm_cleanup']=Q.C.artifact(cp)
                with self.assertRaises(ValueError):Q.inspect_attempt(folder,out,h['pcm_cleanup'])

    def test_automatic_failure_continues_other_sources(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=QueueTests().fixture(root,'frame_complete',[{'source_id':'bad'},{'source_id':'good','caption_link':{}}]);args.output.mkdir()
            (args.output/'manifest.json').write_text(json.dumps({'status':'halted','failed_source_id':'bad'}))
            h={'source_id':'bad','publication_id':'p','disposition':'held_unadmitted_asr','reason_code':'multiple_segments_outside_audio','acquisition_receipt':{'path':'fake'}}
            def fake_main(argv):
                selected=json.loads(Path(argv[argv.index('--acquisition')+1]).read_text());self.assertEqual([r['source_id'] for r in selected['records']],['good'])
                folder=args.output/'items'/Q.C.hashlib.sha256(b'good').hexdigest()[:20];folder.mkdir(parents=True,exist_ok=True);(folder/'receipt.json').write_text('{}')
                Q.C.dump(args.output/'manifest.json',{'status':'selected_snapshot_complete','records':[]})
            with patch.object(Q,'validate_holds',return_value={}),patch.object(Q.R,'validate_diagnostic',side_effect=ValueError('multiple EOF')),patch.object(Q,'quarantine',return_value=h),patch.object(Q,'dispose_new_failed_pcm'),patch.object(Q.C,'completed',return_value={'source_id':'bad'}),patch.object(Q.D,'main',side_effect=fake_main):Q.run(args)
            status=json.loads((args.output/'queue-status.json').read_text());self.assertEqual(status['status'],'selected_frame_complete_with_recognition_holds');self.assertEqual(status['recognition_hold_count'],1)

if __name__=='__main__':unittest.main()
