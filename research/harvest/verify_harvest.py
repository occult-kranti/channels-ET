#!/usr/bin/env python3
"""Adversarial queue/control fixtures. No network or empirical media is used."""
import argparse, concurrent.futures, importlib.util, json, os, pathlib, tempfile, time, types, unittest
from unittest.mock import patch

HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('harvest_worker',HERE/'harvest.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
CAPS={kind:1000 for kind in ('metadata','captions','video','audio','channel','playlist')}

def fixture(root,quota=100000):
 source=root/'videos.json';h.save(source,{'records':[{'video_id':'abcdefghijk','title':'Synthetic fixture only'}]})
 store=h.Store(root/'state.sqlite',root/'raw',quota,0);store.initialize(source);return store

def completed_metadata(store):
 job=store.claim('fixture','metadata',CAPS,30);raw=store.job_dir(job);raw.mkdir(parents=True,exist_ok=True)
 path=raw/'info.json';path.write_text(json.dumps({'id':'abcdefghijk','duration':1}))
 store.finish(job,{'status':'succeeded'},[{'path':path,'type':'metadata','complete':True}]);return job,path

class Controls(unittest.TestCase):
 def test_access_denial_claims_nothing(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root);receipt=root/'denial.json';h.save(receipt,{'status':'request_failed','proxyTunnelDenied':True,'error':'Tunnel connection failed:403Forbidden'})
   args=argparse.Namespace(access_receipt=receipt,output_dir=root/'exports')
   with patch.object(h.Worker,'execute',side_effect=AssertionError('No request may be made')):summary=h.execute(store,args)
   self.assertEqual(summary['attempts_total'],0);self.assertEqual(summary['access_gate']['status'],'blocked')
   self.assertEqual(sum(v.get('queued',0) for v in summary['counts_by_kind'].values()),3)
 def test_transactional_claim_deduplicates_concurrent_workers(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d))
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:claimed=list(pool.map(lambda i:store.claim(str(i),'metadata',CAPS,30),range(4)))
   self.assertEqual(sum(j is not None for j in claimed),1)
 def test_success_requires_correct_actual_artifact(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d));job=store.claim('fixture','metadata',CAPS,30)
   with self.assertRaises(ValueError):store.finish(job,{'status':'succeeded'},[])
 def test_deleted_and_hash_changed_artifacts_reopen_work(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d));job,path=completed_metadata(store);path.unlink()
   summary=store.export(pathlib.Path(d)/'exports')
   self.assertEqual(summary['artifacts_by_type']['metadata'],0)
   self.assertEqual(store.claim('new','metadata',CAPS,30)['id'],job['id'])
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d));job,path=completed_metadata(store);before=path.stat();blob=path.read_bytes();path.write_bytes(b'x'*len(blob));os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
   invalid=store.reconcile_artifacts(full_hash=True)
   self.assertEqual(invalid[0]['reason'],'artifact_hash_changed')
 def test_partial_caption_is_resumable_with_artifact_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d));job=store.claim('fixture','captions',CAPS,30);raw=store.job_dir(job);raw.mkdir(parents=True);path=raw/'fixture.json';path.write_text('{}')
   store.finish(job,{'status':'partial','offered_tracks':2,'saved_tracks':1},[{'path':path,'type':'caption','complete':True,'language_code':'en','is_generated':True}])
   with store.connect() as c:c.execute('UPDATE jobs SET next_attempt=0 WHERE id=?',(job['id'],))
   again=store.claim('resume','captions',CAPS,30);self.assertEqual(again['id'],job['id']);self.assertEqual(again['attempt_count'],2);self.assertTrue(path.exists())
 def test_individual_outstanding_reservations_cannot_cancel(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d),300);caps={k:100 for k in CAPS};a=store.claim('a','metadata',caps,30);store.claim('b','captions',caps,30)
   directory=store.job_dir(a);directory.mkdir(parents=True);(directory/'overshoot').write_bytes(b'x'*150)
   with store.connect() as c:self.assertFalse(store.capacity(c,100))
 def test_atomic_exports_do_not_share_temporary_name(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'out.json'
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda i:h.save(path,{'fixture':i}),range(40)))
   self.assertIn('fixture',json.loads(path.read_text()))
 def test_specific_format_and_size_errors_schedule_audio_fallback(self):
  for error in ['Requested format is not available','No complete media file written; source may exceed max-filesize']:
   result=h.classify(RuntimeError(error),1,3);self.assertTrue(result['fallback_audio']);self.assertEqual(result['error_class'],'media_size_or_format_limit')
  self.assertNotIn('fallback_audio',h.classify(RuntimeError('This is a private video'),1,3))
 def test_nested_channel_containers_and_pointer_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root)
   with store.connect() as c:store.add_job(c,'channel','fixture-route','https://www.youtube.com/@fixture')
   job=store.claim('fixture','channel',CAPS,30);response=root/'response.json'
   h.save(response,{'entries':[{'_type':'playlist','url':None,'webpage_url':'https://www.youtube.com/@fixture/shorts','entries':[{'id':'bcdefghijkl'},{'id':'cdefghijklm'}]}]})
   worker=h.Worker(store,argparse.Namespace(channel_batch=100,timeout=30))
   with patch.object(worker,'run_child',return_value=response):result=worker.channel(job)
   self.assertEqual(result['usable_videos'],2);self.assertEqual(result['unusable_or_container_slots'],1)
   self.assertIn('https://www.youtube.com/@fixture/shorts',result['containers'])
   self.assertEqual(result['videos'][0]['response_pointer'],'/entries/0/entries/0')
   store.finish(job,result);summary=store.export(root/'exports');self.assertEqual(summary['channel_listing_trees_complete'],0)
 def test_explicit_playlists_are_separate_resumable_deduplicated_routes(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root);source=root/'playlists.jsonl';url='https://www.youtube.com/playlist?list=PL_fixture_only'
   source.write_text(json.dumps({'playlist_id':'PL_fixture_only','url':url})+'\n')
   store.initialize(root/'videos.json',playlists=source);store.initialize(root/'videos.json',playlists=source)
   job=store.claim('fixture','playlist',CAPS,30);self.assertEqual(job['source_url'],url)
   store.finish(job,{'status':'succeeded','returned_slots':2,'listing_end':False,'videos':[{'video_id':'abcdefghijk'}],'containers':[]})
   resumed=store.claim('resume','playlist',CAPS,30);self.assertEqual(resumed['cursor_start'],3)
   store.finish(resumed,{'status':'succeeded','returned_slots':0,'listing_end':True,'videos':[],'containers':[]})
   summary=store.export(root/'exports');self.assertEqual(summary['inventory'],{'videos':1,'channel_jobs':0,'playlist_jobs':1})
   self.assertEqual(summary['channel_listing_trees_complete'],0);self.assertEqual(summary['playlist_listing_trees_complete'],1)
 def test_live_owner_prevents_expired_lease_reclaim(self):
  with tempfile.TemporaryDirectory() as d:
   store=fixture(pathlib.Path(d));start=(pathlib.Path('/proc')/str(os.getpid())/'stat').read_text().split()[21];owner=f'{os.getpid()}:{start}:fixture'
   job=store.claim(owner,'captions',CAPS,1)
   with store.connect() as c:c.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
   result=store.recover();self.assertIn(job['id'],result['held_live_children']);self.assertEqual(result['recovered'],[])
 def test_unresolved_bounded_inline_container_is_not_complete(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root)
   with store.connect() as c:store.add_job(c,'channel','fixture','https://www.youtube.com/@fixture')
   job=store.claim('fixture','channel',CAPS,30);response=root/'response.json';h.save(response,{'entries':[{'_type':'playlist','entries':[{'id':'bcdefghijkl'}]}]})
   worker=h.Worker(store,argparse.Namespace(channel_batch=100,timeout=30))
   with patch.object(worker,'run_child',return_value=response):result=worker.channel(job)
   self.assertTrue(result['listing_end']);self.assertEqual(len(result['unresolved_inline_containers']),1)
   store.finish(job,result);self.assertEqual(store.export(root/'exports')['channel_listing_trees_complete'],0)
 def test_attached_cover_art_cannot_be_video(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root);completed_metadata(store);job=store.claim('fixture','video',CAPS,30)
   raw=store.job_dir(job);raw.mkdir(parents=True)
   worker=h.Worker(store,argparse.Namespace(timeout=30,rate='4M'))
   probe=types.SimpleNamespace(returncode=0,stdout=json.dumps({'streams':[{'codec_type':'audio'},{'codec_type':'video','disposition':{'attached_pic':1}}],'format':{'duration':'1'}}))
   def synthetic_write(*args):(raw/'abcdefghijk.mp4').write_bytes(b'fixture-not-media')
   with patch.object(worker,'run_child',side_effect=synthetic_write),patch.object(h.subprocess,'run',return_value=probe):
    with self.assertRaisesRegex(ValueError,'attached cover art'):worker.media(job)
 def test_invalidated_media_is_quarantined_and_not_recertified_without_new_write(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root);completed_metadata(store);job=store.claim('first','video',CAPS,30)
   raw=store.job_dir(job);raw.mkdir(parents=True);path=raw/'abcdefghijk.mp4';path.write_bytes(b'original-valid-looking-fixture')
   prior=h.sha(path);store.finish(job,{'status':'succeeded'},[{'path':path,'type':'video','complete':True}])
   path.write_bytes(b'changed-valid-looking-fixture');changed=h.sha(path);store.reconcile_artifacts(full_hash=True)
   resumed=store.claim('resume','video',CAPS,30);worker=h.Worker(store,argparse.Namespace(timeout=30,rate='4M'))
   with patch.object(worker,'run_child'),patch.object(h.subprocess,'run',side_effect=AssertionError('No new media to probe')):
    with self.assertRaisesRegex(RuntimeError,'No complete media'):worker.media(resumed)
   self.assertFalse(path.exists());quarantine=list((store.raw/'quarantine').rglob('*.mp4'));self.assertEqual(len(quarantine),1)
   self.assertEqual(h.sha(quarantine[0]),changed);receipt=json.loads(quarantine[0].with_name(quarantine[0].name+'.receipt.json').read_text())
   self.assertEqual(receipt['prior_sha256'],prior);self.assertEqual(receipt['observed_sha256'],changed)
   self.assertEqual(store.export(root/'exports')['artifacts_by_type']['video'],0)
 def test_unbound_completed_media_quarantines_but_part_is_resumable(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);store=fixture(root);completed_metadata(store);job=store.claim('fixture','video',CAPS,30)
   raw=store.job_dir(job);raw.mkdir(parents=True);path=raw/'abcdefghijk.mp4';path.write_bytes(b'unbound-completed-fixture');part=raw/'abcdefghijk.mp4.part';part.write_bytes(b'resumable')
   worker=h.Worker(store,argparse.Namespace(timeout=30,rate='4M'))
   with patch.object(worker,'run_child'):
    with self.assertRaisesRegex(RuntimeError,'No complete media'):worker.media(job)
   self.assertTrue(part.exists());self.assertFalse(path.exists());self.assertEqual(store.export(root/'exports')['artifacts_by_type']['quarantine'],1)
 def test_shared_collection_lock_excludes_other_writer(self):
  with tempfile.TemporaryDirectory() as d:
   raw=pathlib.Path(d)
   with h.collection_lock(raw):
    with self.assertRaisesRegex(RuntimeError,'shared raw-directory lock'):
     with h.collection_lock(raw):pass

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 receipt={'checked_at':h.now(),'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
          'network_requests':0,'worker_sha256':h.sha(HERE/'harvest.py'),'scope':'Temporary synthetic metadata/control artifacts only; no source download, caption accuracy or actual video completeness evidence.'}
 h.save(HERE/'verification.json',receipt);raise SystemExit(not result.wasSuccessful())
