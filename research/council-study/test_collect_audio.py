import gzip,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('pilot',Path(__file__).with_name('collect_audio.py'));P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
class PilotTests(unittest.TestCase):
 def fixture(self,root):
  original=root/'fixture.mp3'
  subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-ac','2','-c:a','libmp3lame','-b:a','128k',str(original)],check=True)
  title='Galactic Council of9 fixture';url='https://publisher.example/audio.mp3';link='https://publisher.example/episode'
  xml=f'<rss><channel><language>en</language><item><guid>{P.GUID}</guid><title>{title}</title><link>{link}</link><enclosure url="{url}" length="{original.stat().st_size}" type="audio/mpeg"/></item></channel></rss>'.encode()
  feed=root/'feed.xml.gz';feed.write_bytes(gzip.compress(xml,mtime=0));selection=root/'selected.json'
  P.C.dump(selection,{'records':[{'guid':P.GUID,'title':title,'link':link,'duration':'00:00:02','enclosure':{'url':url,'length':str(original.stat().st_size),'type':'audio/mpeg'}}],'source_frame':{'artifact':P.C.artifact(feed),'decoded_content':{'bytes':len(xml),'sha256':hashlib.sha256(xml).hexdigest()}}})
  output=root/'output';ram=root/'ram';output.mkdir();ram.mkdir()
  def download(url,path,ram):
   shutil.copyfile(original,path);return {'enclosure_url':url,'bytes':path.stat().st_size,'sha256':P.C.sha(path),'http_status':200,'test_fixture_transport':True}
  return original,selection,feed,output,ram,download
 def produce(self,root):
  args=self.fixture(root);original,selection,feed,output,ram,download=args
  with patch.object(P.C,'download',side_effect=download),patch.object(P,'guard',return_value={'test_guard':True}):result=P.acquire(selection,feed,output,ram)
  return args,result
 def test_full_stereo_to_mono_conversion_and_replay(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   args,r=self.produce(Path(t));_,_,_,output,ram,_=args
   self.assertEqual(r['lineage']['original_channels'],2);self.assertEqual(r['audio']['probe']['channels'],1)
   self.assertEqual(r['lineage']['conversion']['target_bitrate_bps'],22000);self.assertLessEqual(r['lineage']['actual_duration_difference_seconds'],.1)
   self.assertFalse((ram/'original.mp3').exists());self.assertFalse((ram/'retained.opus').exists());self.assertEqual(P.verify_audio(output/'receipt.json'),r)
   measured=P.measure(Path(r['audio']['path']),output/'independent-test-decode.log');self.assertEqual(measured['raw_pcm_sha256'],r['decoded_16k_mono']['raw_pcm_sha256'])
 def test_encoded_byte_cap_preserves_unadmitted_partial(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);original,selection,feed,output,ram,download=self.fixture(root)
   with patch.object(P.C,'download',side_effect=download),patch.object(P,'guard',return_value={}),patch.object(P,'AUDIO_CAP',100),self.assertRaises(P.C.ResourceStop):P.acquire(selection,feed,output,ram)
   self.assertTrue((ram/'original.mp3').exists());self.assertTrue((ram/'retained.opus').exists());self.assertFalse((output/'receipt.json').exists())
 def test_decode_envelope_aborts_not_truncates(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   original,_,_,output,_,_=self.fixture(Path(t))
   with patch.object(P,'MAX_SECONDS',1),self.assertRaises(P.C.ResourceStop):P.measure(original,output/'capped.log')
 def test_primary_source_join_rejects_changed_guid_or_enclosure(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   _,selection,feed,_,_,_=self.fixture(Path(t));d=json.loads(selection.read_text());d['records'][0]['enclosure']['url']='https://elsewhere.example';P.C.dump(selection,d)
   with self.assertRaises(ValueError):P.feed_item(selection,feed)
 def test_rehashed_repeated_metadata_and_resource_policy_rejected(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   args,r=self.produce(Path(t));output=args[3];path=output/'receipt.json';saved=path.read_bytes()
   for key,value in [('original_channels',9),('actual_duration_difference_seconds',1.0)]:
    bad=json.loads(saved);bad['lineage'][key]=value;P.C.dump(path,bad)
    with self.subTest(key=key),self.assertRaises(ValueError):P.verify_audio(path)
   path.write_bytes(saved);plan=output/'resource-plan.json';d=json.loads(plan.read_text());d['old_final_fit_reserve']=0;P.C.dump(plan,d);bad=json.loads(saved);bad['resource_plan']=P.C.artifact(plan);P.C.dump(path,bad)
   with self.assertRaises(ValueError):P.verify_audio(path)
 def test_mock_asr_semantics_full_pcm_and_rehashed_tamper(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);args,source=self.produce(root);output=args[3];ram=args[4];model={'path':str(root/'model'),'language_mode':'multilingual','files_sha256':'f'*64};prov={'test':'fixture'}
   duration=source['decoded_16k_mono']['duration_seconds']
   class Engine:
    def __init__(self,*args,**kwargs):self.model=SimpleNamespace(is_multilingual=True);self.kwargs=kwargs;assert kwargs['cpu_threads']==1
    def transcribe(self,*args,**kwargs):
     assert kwargs==P.F.SETTINGS
     return iter([SimpleNamespace(start=0.0,end=1.0,text=' Test fixture words.',avg_logprob=-.1,no_speech_prob=.1)]),SimpleNamespace(language='en',duration=duration,duration_after_vad=duration)
   with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=Engine)}),patch.object(P.F,'bind_model',return_value=(model,prov)),patch.object(P,'guard',return_value={}):
    r=P.transcribe(output,ram);self.assertEqual(r['whitespace_words'],3);self.assertEqual(r['decoder']['cap_bytes'],240000000);self.assertFalse((ram/'decoded.wav').exists());self.assertEqual(P.verify_asr(output/'asr/receipt.json'),r)
    path=output/'asr/receipt.json';bad=json.loads(path.read_text());bad['decoder']['sample_count']+=1;P.C.dump(path,bad)
    with self.assertRaises(ValueError):P.verify_asr(path)
 def test_resource_gate_fails_closed(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t)
   with patch.object(P.shutil,'disk_usage',return_value=SimpleNamespace(free=P.C.FLOOR)),self.assertRaises(P.C.ResourceStop):P.guard(root,root)
if __name__=='__main__':unittest.main()
