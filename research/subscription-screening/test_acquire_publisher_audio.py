import importlib.util
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('acquire_publisher_audio.py'))
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)

class CollectorTests(unittest.TestCase):
    def test_https_and_credentials(self):
        self.assertEqual(C.safe_url('https://publisher.example/a.mp3'), 'https://publisher.example/a.mp3')
        for url in ['http://publisher.example/a', 'https://user:pass@example.com/a', 'file:///a', '/a']:
            with self.assertRaises(ValueError): C.safe_url(url)

    def test_dynamic_guard_reservation(self):
        mock = type('Usage', (), {'free': C.FLOOR + C.RESERVE - 100})()
        with patch.object(C.shutil, 'disk_usage', return_value=mock):
            with self.assertRaises(C.ResourceStop): C.free_guard('/tmp')
            C.free_guard('/tmp', original_written=100)
            with self.assertRaises(C.ResourceStop): C.free_guard('/tmp', original_written=100, additional=1)

    def test_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'a'; p.write_bytes(b'a'); a = C.artifact(p)
            C.verify_artifact(a); p.write_bytes(b'b')
            with self.assertRaises(ValueError): C.verify_artifact(a)

    def test_non_bashar_short_duration_kept(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'inventory.json'
            p.write_text(json.dumps({'feeds':[{'handle':'@TracyKumbera','feed_title':'Tracy'}], 'feed_entries':[
                {'handle':'@TracyKumbera','source_id':'@tracy:rss:short','title':'Short',
                 'source_url':'https://publisher.example/episode','guid':'g','duration_seconds_publisher':299,
                 'audio_enclosure':{'url':'https://publisher.example/a.mp3','length':'100'},
                 'feed_sha256':'f'*64,'transcript_links':[]}]}))
            frame=C.load_frame(p)
            self.assertEqual(len(frame),1);self.assertEqual(frame[0]['duration_seconds_publisher'],299)

    def test_full_conversion_duration_and_channels_and_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); original=root/'fixture.mp3'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2.1',
                            '-ac','2','-c:a','libmp3lame',str(original)], check=True)
            output=root/'output';output.mkdir()
            item={'source_id':'test:s','publication_id':'test:p','source_origin':'publisher_rss',
                  'audio_url':'https://publisher.example/a.mp3','duration_seconds_publisher':2.1,
                  'guid':'g','source_url':'https://publisher.example/episode'}
            def download(url,path,dest):
                shutil.copyfile(original,path)
                return {'enclosure_url':url,'final_url':url,'sha256':C.sha(path),'bytes':Path(path).stat().st_size}
            with patch.object(C,'download',side_effect=download):
                record,new=C.acquire(item,output,0,[])
            self.assertTrue(new)
            self.assertEqual(record['audio']['probe']['channels'],2)
            self.assertLessEqual(record['lineage']['actual_duration_difference_seconds'],.1)
            self.assertEqual(record['input_representation'],'full_duration_lossy_opus_derivative')
            folder=Path(record['audio']['path']).parent
            self.assertFalse((folder/'original.partial').exists())
            self.assertTrue(original.exists())
            self.assertTrue((folder/'cleanup.json').exists())
            again,new=C.acquire(item,output,record['audio']['bytes'],[])
            self.assertFalse(new);self.assertEqual(again['audio']['sha256'],record['audio']['sha256'])
            # Replay validates repeated identity, sample accounting and lineage fields.
            for mutate in (
                lambda r:r.update(source_id='swapped'),
                lambda r:r.update(publication_id='swapped'),
                lambda r:r['source'].update(guid='swapped'),
                lambda r:r['decoded_16k_mono'].update(sample_count=1),
                lambda r:r['lineage'].update(original_channels=1),
                lambda r:r['lineage'].update(original_bytes=1),
                lambda r:r['lineage']['retained_decoded_16k_mono'].update(duration_seconds=99),
            ):
                changed=copy.deepcopy(record);mutate(changed);C.dump(folder/'receipt.json',changed)
                with self.assertRaises(ValueError):C.completed(folder/'receipt.json')
            C.dump(folder/'receipt.json',record)
            # An altered compact recording can never be silently reused.
            Path(record['audio']['path']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):C.completed(folder/'receipt.json')

    def test_partial_item_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);sid='test:s';key=C.hashlib.sha256(sid.encode()).hexdigest()[:20]
            folder=root/'items'/key;folder.mkdir(parents=True);(folder/'original.partial').write_bytes(b'partial')
            with self.assertRaises(ValueError):C.acquire({'source_id':sid},root,0,[])
            self.assertEqual((folder/'original.partial').read_bytes(),b'partial')

    def test_original_streaming_cap_preserves_partial(self):
        class Response:
            status=200;headers={};url='https://publisher.example/a'
            def __init__(self):self.n=0
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):self.n+=1;return b'123456' if self.n<3 else b''
        class Opener:
            def open(self,*args,**kwargs):return Response()
        with tempfile.TemporaryDirectory() as t,patch.object(C.urllib.request,'build_opener',return_value=Opener()),patch.object(C,'ORIGINAL_CAP',10):
            p=Path(t)/'part'
            with self.assertRaises(C.ResourceStop):C.download('https://publisher.example/a',p,t)
            self.assertEqual(p.read_bytes(),b'123456')

    def test_original_length_mismatch_rejected(self):
        class Response:
            status=200;headers={'Content-Length':'20'};url='https://publisher.example/a'
            def __init__(self):self.n=0
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):self.n+=1;return b'123456' if self.n==1 else b''
        class Opener:
            def open(self,*args,**kwargs):return Response()
        with tempfile.TemporaryDirectory() as t,patch.object(C.urllib.request,'build_opener',return_value=Opener()):
            with self.assertRaises(ValueError):C.download('https://publisher.example/a',Path(t)/'part',t)

if __name__=='__main__':unittest.main()
