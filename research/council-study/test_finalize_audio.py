import importlib.util,json,tempfile,traceback,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('finish',Path(__file__).with_name('finalize_audio.py'));F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
spec2=importlib.util.spec_from_file_location('fixture_source',Path(__file__).with_name('test_collect_audio.py'));T=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(T)
class FinalizeTests(unittest.TestCase):
 def staged(self,root):
  args=T.PilotTests().fixture(root);original,selection,feed,output,ram,download=args
  def gate(out,tmp,additional_ram=0,additional_disk=0):
   if additional_disk:raise F.C.ResourceStop('Council pilot protects2GiBfloor+128MiBoperations+64MiBoldfit+remaining2MBtext')
   return {}
  log=root/'failed.log'
  with patch.object(F.P.C,'download',side_effect=download),patch.object(F.P,'guard',side_effect=gate):
   try:F.P.acquire(selection,feed,output,ram)
   except F.C.ResourceStop:log.write_text(traceback.format_exc())
  self.assertFalse((output/'receipt.json').exists());self.assertTrue((ram/'retained.opus').exists())
  a=F.C.artifact(ram/'retained.opus');d=F.P.measure(ram/'retained.opus',root/'independent.log');review=root/'review.json'
  F.C.dump(review,{'status':'staged_media_bytes_independently_decoded_not_yet_admitted','artifact_bytes':a['bytes'],'artifact_sha256':a['sha256'],'decoded_samples_16k_mono':d['sample_count'],'decoded_seconds':d['duration_seconds'],'raw_pcm_sha256':d['raw_pcm_sha256'],'natural_eof':True,'returncode':0})
  return output,ram,log,review,a
 def test_copy_only_finalization_matches_staged_bytes(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   output,ram,log,review,a=self.staged(Path(t))
   with patch.object(F.P,'guard',return_value={}),patch.object(F.P.C,'download',side_effect=AssertionError('network forbidden')),patch.object(F.P,'convert',side_effect=AssertionError('reencode forbidden')):r=F.run(output,ram,log,review)
   self.assertEqual(r['audio']['sha256'],a['sha256']);self.assertEqual(F.P.verify_audio(output/'receipt.json'),r);self.assertFalse((ram/'original.mp3').exists());self.assertFalse((ram/'retained.opus').exists())
   self.assertEqual(Path(r['lineage']['conversion']['stderr_artifact']['path']).parent,output)
   (ram/'retained.ffmpeg.log').unlink();self.assertEqual(F.P.verify_audio(output/'receipt.json'),r)
 def test_wrong_review_or_resource_rejection_preserves_everything(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   output,ram,log,review,a=self.staged(Path(t));d=json.loads(review.read_text());d['artifact_sha256']='0'*64;F.C.dump(review,d)
   with patch.object(F.P,'guard',return_value={}),self.assertRaises(ValueError):F.run(output,ram,log,review)
   self.assertTrue((ram/'original.mp3').exists());self.assertTrue((ram/'retained.opus').exists());self.assertFalse((output/'receipt.json').exists())
if __name__=='__main__':unittest.main()
