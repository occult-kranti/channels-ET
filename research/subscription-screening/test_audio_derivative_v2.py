import importlib.util
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('derivative',Path(__file__).with_name('audio_derivative_v2.py'))
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)

class DerivativeTests(unittest.TestCase):
    def fixture(self,root):
        p=root/'fixture.opus'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2.1',
                        '-ac','2','-c:a','libopus',str(p)],check=True)
        proof=D.C.decode_measure(p,root/'measurement.log')
        return p,proof

    def test_full_decode_matches_hash_sample_count_and_header(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);audio,proof=self.fixture(root)
            r=D.capped_pcm(audio,root/'decoded.wav',proof)
            self.assertEqual(r['sample_count'],proof['sample_count'])
            self.assertEqual(r['raw_pcm_sha256'],proof['raw_pcm_sha256'])
            self.assertEqual(r['artifact']['bytes'],proof['sample_count']*2+44)
            with wave.open(str(root/'decoded.wav'),'rb') as w:
                self.assertEqual(w.getnframes(),proof['sample_count']);self.assertEqual(w.getnchannels(),1)

    def test_planned_cap_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);audio,proof=self.fixture(root)
            with self.assertRaises(D.C.ResourceStop):D.capped_pcm(audio,root/'decoded.wav',proof,cap=1000)
            self.assertFalse((root/'decoded.partial.wav').exists())

    def test_streaming_cap_rejects_lying_small_proof(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);audio,proof=self.fixture(root);proof['sample_count']=10
            with self.assertRaises(D.C.ResourceStop):D.capped_pcm(audio,root/'decoded.wav',proof,cap=1000)
            self.assertFalse((root/'decoded.wav').exists());self.assertTrue((root/'decoded.partial.wav').exists())

    def test_same_length_wrong_hash_never_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);audio,proof=self.fixture(root);proof['raw_pcm_sha256']='0'*64
            with self.assertRaises(ValueError):D.capped_pcm(audio,root/'decoded.wav',proof)
            self.assertFalse((root/'decoded.wav').exists());self.assertTrue((root/'decoded.partial.wav').exists())

    def test_decoder_error_preserves_partial(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);audio=root/'bad.opus';audio.write_bytes(b'not media')
            with self.assertRaises(ValueError):D.capped_pcm(audio,root/'decoded.wav',{'sample_count':100,'raw_pcm_sha256':'0'*64})
            self.assertTrue((root/'decoded.partial.wav').exists())

    def test_receipt_semantics_and_empty_recognition(self):
        for empty in (False,True):
            with self.subTest(empty=empty),tempfile.TemporaryDirectory() as t:
                root=Path(t);audio,_=self.fixture(root);collection=root/'collection';collection.mkdir()
                item={'source_id':'test:s','publication_id':'test:p','source_origin':'publisher_rss',
                      'audio_url':'https://publisher.example/a.opus','duration_seconds_publisher':2.1,
                      'guid':'g','language':'en','source_url':'https://publisher.example/e'}
                def download(url,path,dest):
                    shutil.copyfile(audio,path)
                    return {'enclosure_url':url,'final_url':url,'sha256':D.C.sha(path),'bytes':Path(path).stat().st_size}
                with patch.object(D.C,'download',side_effect=download):source,_=D.C.acquire(item,collection,0,[])
                output=root/'asr';output.mkdir();model={'language_mode':'english-only'}
                segments=[] if empty else [{'text':'Test recognized words.','start_seconds':0.1,'end_seconds':1.5}]
                with patch.object(D.CORE,'run_asr',return_value=(segments,{'human_reviewed':False})),patch.object(D.CORE,'local_model_binding',return_value=model),patch.object(D.CORE,'versions',return_value={'test_only':True}):
                    r=D.process(source,output,root/'model',model,root/'pcm' if not empty else None)
                self.assertEqual(r['status'],'completed_empty_recognition' if empty else 'completed')
                receipt=Path(r['outputs']['normalized']['path']).parent/'receipt.json'
                source_receipt=Path(source['audio']['path']).parent/'receipt.json'
                D.verify_existing(receipt,source_receipt,model)
                for key,value in [('source_id','swapped'),('publication_id','swapped'),('whitespace_words',99),('segment_count',99),('collector_validator_sha256','0'*64)]:
                    altered=copy.deepcopy(r);altered[key]=value;D.C.dump(receipt,altered)
                    with self.assertRaises(ValueError):D.verify_existing(receipt,source_receipt,model)
                D.C.dump(receipt,r)
                self.assertFalse((receipt.parent/'decoded.wav').exists())
                # Rehashing an altered normalized artifact still cannot swap source identity.
                normalized=Path(r['outputs']['normalized']['path']);data=json.loads(normalized.read_text());data['source_id']='swapped'
                D.C.dump(normalized,data);r['outputs']['normalized']=D.C.artifact(normalized);D.C.dump(receipt,r)
                with self.assertRaises(ValueError):D.verify_existing(receipt,source_receipt,model)

if __name__=='__main__':unittest.main()
