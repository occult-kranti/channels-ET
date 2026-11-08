import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('council_acq',Path(__file__).with_name('build_acquisition.py'));B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
class AcquisitionTests(unittest.TestCase):
 def fixture(self,root):
  audio=root/'retained.opus';audio.write_bytes(b'audio');aa={**B.C.artifact(audio),'probe':{'channels':1}}
  source={'source_id':'s','publication_id':'p','source_origin':'publisher_page','source':{'title':'Council message','source_url':'https://publisher.example/message','handle':'@test','publisher':'Test'},'audio':aa,'decoded_16k_mono':{'duration_seconds':1.0},'duration_seconds':1.006,'lineage':{'original_bytes':10,'original_sha256':'f'*64,'actual_duration_difference_seconds':.006},'duplicate_family_id':'original-sha256:'+'f'*64}
  acq=root/'receipt.json';B.C.dump(acq,source)
  text=root/'transcript.txt';text.write_text('private full text\n');norm=root/'transcript.json';B.C.dump(norm,{'text':'private full text'});srt=root/'transcript.srt';srt.write_text('private')
  asr={'status':'completed','model':{},'outputs':{'text':B.C.artifact(text),'normalized':B.C.artifact(norm),'srt':B.C.artifact(srt)},'whitespace_words':3,'segment_count':1}
  ap=root/'asr.json';B.C.dump(ap,asr)
  doc={'source_id':'doc1','publication_id':'p','title':'Council message','canonical_url':'https://publisher.example/message','council_id':'council','council_label':'Council','attribution_scope':'publisher title only','acquisition_receipt':B.C.artifact(acq),'audio_artifact':aa,'asr_receipt':B.C.artifact(ap),'text_artifact':asr['outputs']['normalized'],'plain_text_artifact':asr['outputs']['text'],'words':3,'turns':1,'decoded_audio_seconds':1.0}
  path=root/'contact.json';B.C.dump(path,{'documents':[doc]});return path,doc,source,asr
 def test_reuse_counts_and_private_text_absence(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p,doc,source,asr=self.fixture(root)
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr):out=B.build(p,root/'public.json',root/'snapshots')
   self.assertEqual(out['summary']['reused_audio_publications'],1);self.assertEqual(out['summary']['new_audio_downloads'],0);self.assertIsNone(out['summary']['upstream_total_videos'])
   self.assertNotIn('private full text',json.dumps(out));self.assertNotIn(str(root),json.dumps(out));self.assertEqual(out['records'][0]['voice_production'],'unknown_not_verified')
 def test_metadata_or_counts_swap_rejected(self):
  for key,value in [('publication_id','other'),('title','other'),('canonical_url','https://other.example'),('words',4),('turns',4),('decoded_audio_seconds',2)]:
   with self.subTest(key=key),tempfile.TemporaryDirectory() as t:
    p,doc,source,asr=self.fixture(Path(t));doc[key]=value
    with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),self.assertRaises(ValueError):B.record(doc,'reused_existing_verified_archive')
 def test_asr_artifact_swap_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p,doc,source,asr=self.fixture(Path(t));doc['text_artifact']=doc['plain_text_artifact']
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),self.assertRaises(ValueError):B.record(doc,'reused_existing_verified_archive')
 def test_duplicate_publication_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p,doc,source,asr=self.fixture(root);B.C.dump(p,{'documents':[doc,doc]})
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),self.assertRaises(ValueError):B.build(p,root/'out.json',root/'snapshots')
 def test_new_budget_does_not_limit_reused_bytes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p,doc,source,asr=self.fixture(root)
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),patch.object(B,'NEW_AUDIO_CAP',4):B.build(p,root/'reuse.json',root/'snapshots')
   new=root/'new.json';B.C.dump(new,{'documents':[doc]});B.C.dump(p,{'documents':[]})
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),patch.object(B,'NEW_AUDIO_CAP',4),self.assertRaises(ValueError):B.build(p,root/'new-public.json',root/'snapshots',new)
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr),patch.object(B,'NEW_TEXT_CAP',2),self.assertRaises(ValueError):B.build(p,root/'text-public.json',root/'snapshots',new)
 def test_empty_recognition_explicit(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p,doc,source,asr=self.fixture(root);asr.update(status='completed_empty_recognition',whitespace_words=0,segment_count=0);doc.update(words=0,turns=0)
   with patch.object(B.C,'completed',return_value=source),patch.object(B.D,'verify_existing',return_value=asr):out=B.record(doc,'new_verified_publisher_download')
   self.assertEqual(out['transcript_status'],'asr_completed_empty_recognition');self.assertFalse(out['local_asr_completed'])
if __name__=='__main__':unittest.main()
