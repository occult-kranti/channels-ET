import concurrent.futures
import fcntl
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('collector3',Path(__file__).with_name('acquire_publisher_audio_v3.py'))
V=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(V)

class V3Tests(unittest.TestCase):
    def test_shared_concurrent_budget_cap(self):
        with tempfile.TemporaryDirectory() as t,patch.object(V.C,'OUTPUT_CAP',100_000):
            budget=V.Budget(t)
            def admit(i):
                try:budget.admit({'source_id':str(i),'duration_seconds_publisher':1});return True
                except V.C.ResourceStop:return False
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(admit,range(2)))
            self.assertEqual(sum(r),1);self.assertEqual(len(budget.reserved),1)

    def test_actual_above_reservation_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            b=V.Budget(t);item={'source_id':'a','duration_seconds_publisher':1};b.admit(item)
            with self.assertRaises(V.C.ResourceStop):b.completed(item,b.reserved['a']+1)
            self.assertEqual(b.retained,0)

    def test_exclusive_prior_lock(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'lock'
            with p.open('a') as first,p.open('a') as second:
                fcntl.flock(first,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):fcntl.flock(second,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_two_worker_real_conversion_and_partial_preservation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'source.mp3';output=root/'out';ram=root/'ram';output.mkdir();ram.mkdir()
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2.1','-ac','2','-c:a','libmp3lame',str(source)],check=True)
            def download(url,path,dest):
                shutil.copyfile(source,path)
                return {'enclosure_url':url,'final_url':url,'sha256':V.C.sha(path),'bytes':Path(path).stat().st_size}
            items=[{'source_id':f'test:{i}','publication_id':f'testpub:{i}','source_origin':'publisher_rss',
                    'audio_url':f'https://publisher.example/{i}.mp3','duration_seconds_publisher':2.1,'guid':str(i)} for i in range(2)]
            b=V.Budget(output)
            with patch.object(V.C,'download',side_effect=download),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(V.acquire,item,output,ram,b,[]) for item in items];records=[f.result() for f in futures]
            self.assertEqual(b.retained,sum(r['audio']['bytes'] for r in records));self.assertFalse(b.reserved)
            for r in records:
                folder=Path(r['audio']['path']).parent;V.C.completed(folder/'receipt.json')
                self.assertEqual(r['audio']['probe']['channels'],2);self.assertTrue((folder/'cleanup.json').exists())
            item={'source_id':'partial','duration_seconds_publisher':1}
            key=V.hashlib.sha256(item['source_id'].encode()).hexdigest()[:20];folder=output/'items'/key;folder.mkdir()
            (folder/'prior').write_bytes(b'keep')
            with self.assertRaises(ValueError):V.acquire(item,output,ram,b,[])
            self.assertEqual((folder/'prior').read_bytes(),b'keep');self.assertTrue(source.exists())

if __name__=='__main__':unittest.main()
