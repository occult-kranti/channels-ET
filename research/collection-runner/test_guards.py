#!/usr/bin/env python3
"""Offline adversarial guards; synthetic access rows never establish real access."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.request
import runner


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='et-runner-guard-'); self.root=Path(self.temp.name)
        self.raw=self.root/'raw'; self.store=runner.Store(self.raw/'state.sqlite',self.raw,reserve_free=0)
        self.policy=self.root/'policy.json'; runner.save(self.policy,{'default_new_bashar_youtube_limit':100,'conservative_new_bashar_youtube_limit':81})
        self.runtime=self.root/'runtime.json'; runner.save(self.runtime,{'fixture_only':True,'source':'offline_synthetic_fixture',
            'checkedAt':runner.now(),'spec_revision':'fixture6','observed_spec_revision':'fixture6','observations_current':True,'network_policy':{'mode':'unrestricted','state':'unknown'}})
    def tearDown(self): self.temp.cleanup()
    def seed(self,count=1,classification='explicit_bashar_association',duration_state='eligible_duration'):
        records=[{'video_id':f'{i:011d}','source_id':f'youtube:{i:011d}','classification':classification,
                  'duration_state':duration_state,'shorts_evidence':[],'selected_default':True,'selected_conservative_all_materials':i<81} for i in range(count)]
        selection=self.root/'selection.jsonl'; selection.write_text(''.join(json.dumps(r)+'\n' for r in records))
        self.store.initialize(selection,self.policy)
        # An impossible runtime fingerprint marks these direct queue-transaction fixtures, not a real watch gate.
        with self.store.connect() as c:c.execute('INSERT INTO probes VALUES(?,?,?,?,?,?)',('offline-fixture','success',time.time(),'{}',None,None))
        for row in records: self.metadata(row['source_id'])
        return records
    def metadata(self,source,**updates):
        vid=source.split(':')[1]; value={'id':vid,'title':'A discussion','channel':'Independent channel','duration':600,
                                        'webpage_url':'https://www.youtube.com/watch?v='+vid,'media_type':'video'}
        value.update(updates); path=self.raw/'quarantine'/vid/'fixture.info.json'; runner.save(path,value)
        return self.store.metadata_result(source,value,path)
    def getitem(self,source):
        with self.store.connect() as c:return c.execute('SELECT * FROM items WHERE source_id=?',(source,)).fetchone()
    def claim(self,kind='captions',source=None): return self.store.claim(kind,'owner','offline-fixture',source_id=source)
    def test_atomic_global100_across_workers_and_accounts(self):
        self.seed(110)
        def one(_):return self.store.claim('captions',str(_),'offline-fixture')
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: result=list(pool.map(one,range(120)))
        self.assertEqual(sum(r is not None for r in result),100)
        self.assertEqual(self.store.export()['summary']['bashar_unique_youtube_slots_used'],100)
    def test_same_id_two_formats_one_slot_and_failure_never_reopens_slot(self):
        self.seed(); first=self.claim(); self.store.finish(first,'owner',[],error='offline simulated failure')
        second=self.claim('video'); self.assertIsNotNone(second)
        self.assertEqual(self.store.export()['summary']['bashar_unique_youtube_slots_used'],1)
    def test_new_bashar_in_description_reclassified_before_asset_claim(self):
        records=self.seed(classification='not_bashar_labeled_in_available_metadata'); source=records[0]['source_id']
        for field in ('title','uploader','channel','description','tags'):
            self.metadata(source,**{field:['Bashar'] if field=='tags' else 'Bashar'})
            self.assertEqual(self.getitem(source)['classification'],'bashar')
        self.assertIsNotNone(self.claim()); self.assertEqual(self.store.export()['summary']['bashar_unique_youtube_slots_used'],1)
    def test_duration_boundary_nan_unknown_conflict_and_short_guards(self):
        source=self.seed()[0]['source_id']
        for value in (299,None,float('nan'),float('inf'),True):
            self.metadata(source,duration=value); self.assertIn('verified_duration_below300_or_unknown',self.store.reasons(self.getitem(source)))
        self.metadata(source,duration=300); self.assertEqual(self.store.reasons(self.getitem(source)),[])
        for update in ({'media_type':'short'},{'is_short':True},{'webpage_url':'https://www.youtube.com/shorts/00000000000'},{'title':'Discussion #shorts'}):
            self.metadata(source,**update); self.assertIn('fresh_positive_shorts_evidence',self.store.reasons(self.getitem(source)))
    def test_conflict_review_is_bound_to_exact_metadata_hash(self):
        source=self.seed(duration_state='conflicting')[0]['source_id']; item=self.getitem(source)
        self.assertIn('inherited_duration_conflict_unresolved',self.store.reasons(item))
        proof=self.root/'proof.json';runner.save(proof,{'basis':'offline fixture evidence only'})
        review=self.root/'review.json';runner.save(review,{'metadata_sha256':item['metadata_sha256'],'reason':'fixture','duration_conflict_resolved':True,'evidence_source_ref':{'path':str(proof),'sha256':runner.sha(proof)}})
        self.store.review(source,review); self.assertNotIn('inherited_duration_conflict_unresolved',self.store.reasons(self.getitem(source)))
        self.metadata(source,duration=601); self.assertIn('inherited_duration_conflict_unresolved',self.store.reasons(self.getitem(source)))
    def test_review_cannot_override_fresh_shorts_or_positive_bashar(self):
        source=self.seed()[0]['source_id'];self.metadata(source,is_short=True);item=self.getitem(source)
        proof=self.root/'proof';proof.write_text('fixture');review=self.root/'review.json'
        runner.save(review,{'metadata_sha256':item['metadata_sha256'],'reason':'fixture','non_shorts_verified':True,'evidence_source_ref':{'path':str(proof),'sha256':runner.sha(proof)}})
        with self.assertRaises(ValueError):self.store.review(source,review)
        self.metadata(source);item=self.getitem(source)
        runner.save(review,{'metadata_sha256':item['metadata_sha256'],'reason':'fixture','identity_resolution':'other_not_bashar_labeled','evidence_source_ref':{'path':str(proof),'sha256':runner.sha(proof)}})
        with self.assertRaises(ValueError):self.store.review(source,review)
    def test_discovery_import_is_metadata_only_and_pins_canonical_id(self):
        self.seed(); path=self.root/'discovery.json';runner.save(path,{'entries':[{'id':'newVIDEO001','title':'Unreviewed','url':'https://evil.invalid/'}]})
        self.assertEqual(self.store.import_discovery(path)['new_ids'],1)
        with self.store.connect() as c:
            jobs=c.execute("SELECT kind FROM jobs WHERE source_id='youtube:newVIDEO001'").fetchall()
        self.assertEqual([r[0] for r in jobs],['metadata'])
        with self.assertRaises(ValueError):self.metadata('youtube:00000000000',id='wrongID0001')
    def test_redirect_and_playability_controls(self):
        vid='00000000000'; handler=runner.HTTPSWatchRedirect(vid); request=urllib.request.Request('https://www.youtube.com/watch?v='+vid)
        for target in ('http://www.youtube.com/watch?v='+vid,'https://evil.invalid/watch?v='+vid,'https://www.youtube.com/watch?v=11111111111','https://www.youtube.com/shorts/'+vid):
            with self.assertRaises(ValueError):handler.redirect_request(request,None,302,'',{},target)
        payload={'videoDetails':{'videoId':vid},'playabilityStatus':{'status':'OK'}}
        body=('var ytInitialPlayerResponse = '+json.dumps(payload)+';').encode();self.assertEqual(runner.watch_payload(body,vid),payload)
        for change in ({'videoDetails':{'videoId':'11111111111'}},{'playabilityStatus':{'status':'LOGIN_REQUIRED'}}):
            with self.assertRaises(ValueError):runner.watch_payload(('var ytInitialPlayerResponse = '+json.dumps({**payload,**change})).encode(),vid)
    def test_failed_gate_and_expired_lease_never_claim_queued_jobs(self):
        self.seed()
        with self.store.connect() as c:c.execute("UPDATE probes SET status='blocked'")
        self.assertIsNone(self.claim());self.assertEqual(self.store.export()['summary']['attempts'],0)
        with self.store.connect() as c:c.execute("UPDATE probes SET status='success'")
        job=self.claim();
        with self.store.connect() as c:c.execute('UPDATE jobs SET lease_until=? WHERE job_id=?',(time.time()-1,job['job_id']))
        self.store.expire_leases();self.assertIsNone(self.claim('video'))
        with self.assertRaises(ValueError):self.store.finish(job,'owner',[],error='fixture')
    def test_quota_reservations_and_final_fast_oversize_fail_closed(self):
        self.seed();self.store.quota=runner.tree_bytes(self.raw)+runner.CAPS['captions']-1;self.assertIsNone(self.claim())
        self.store.quota=20*1024**3;job=self.claim();path=self.raw/'quarantine'/'oversize.vtt';path.parent.mkdir(exist_ok=True);path.write_bytes(b'x'*(runner.CAPS['captions']+1))
        with self.assertRaises(ValueError):self.store.finish(job,'owner',[{'path':str(path),'validation':{}}])
    def test_shared_writer_lock_and_cap_database_binding(self):
        with runner.collection_lock(self.raw):
            with self.assertRaises(ValueError):
                with runner.collection_lock(self.raw):pass
        with self.assertRaises(ValueError):runner.Store(self.raw/'another.sqlite',self.raw,reserve_free=0)
    def test_blocked_cli_transport_never_starts(self):
        self.seed()
        args=type('Args',(),{'runtime_receipt':self.runtime,'kind':'video','yt_python':Path('/missing')})()
        with patch('runner.subprocess.Popen',side_effect=AssertionError('Network child must not start')):
            self.assertEqual(runner.execute_one(self.store,args)['status'],'blocked_before_claim_or_network')
        self.assertEqual(self.store.export()['summary']['attempts'],0)
    def test_metadata_object_must_match_hashed_file(self):
        source=self.seed()[0]['source_id'];item=self.getitem(source);metadata=json.loads(item['metadata_json']);metadata['duration']=900
        with self.assertRaises(ValueError):self.store.metadata_result(source,metadata,Path(item['metadata_path']))
    def test_expired_healthy_probe_can_renew_but_denial_cannot(self):
        at=time.time()
        self.assertFalse(runner.probe_request_allowed({'status':'blocked','checked_at':at-900},at))
        self.assertFalse(runner.probe_request_allowed({'status':'success','checked_at':at-30},at))
        self.assertTrue(runner.probe_request_allowed({'status':'success','checked_at':at-900},at))
        with patch('runner.urllib.request.build_opener',side_effect=AssertionError('Fixture cannot start transport')):
            with self.assertRaises(ValueError):self.store.probe(self.runtime,'00000000000')
        self.assertFalse(self.store.gate(self.runtime)['ready'])
    def test_runtime_requires_cloud_schema_and_semantic_fingerprint(self):
        original=json.loads(self.runtime.read_text());one=runner.config(self.runtime)
        original['checkedAt']=runner.now();self.runtime.write_text(json.dumps(original,indent=4))
        two=runner.config(self.runtime);self.assertEqual(one['fingerprint'],two['fingerprint']);self.assertNotEqual(one['runtime_receipt_sha256'],two['runtime_receipt_sha256'])
        original['spec_revision']=original['observed_spec_revision']='fixture7';runner.save(self.runtime,original)
        self.assertNotEqual(two['fingerprint'],runner.config(self.runtime)['fingerprint'])
        runner.save(self.runtime,{'package':'brave','status':'ready'})
        with self.assertRaises(ValueError):runner.config(self.runtime)
    def test_runtime_revision_and_policy_types_fail_closed(self):
        original=json.loads(self.runtime.read_text())
        for invalid in (None,False,{},[]):
            bad={**original,'spec_revision':invalid,'observed_spec_revision':invalid};runner.save(self.runtime,bad)
            with self.assertRaises(ValueError):runner.config(self.runtime)
        runner.save(self.runtime,{**original,'network_policy':[]})
        with self.assertRaises(ValueError):runner.config(self.runtime)
    def test_runtime_set_lists_have_stable_semantics(self):
        observed=json.loads(self.runtime.read_text());observed['network_policy']['allowed_hosts']=['b.example','a.example'];runner.save(self.runtime,observed)
        one=runner.config(self.runtime);observed['network_policy']['allowed_hosts']=['a.example','b.example','a.example'];runner.save(self.runtime,observed)
        self.assertEqual(one['fingerprint'],runner.config(self.runtime)['fingerprint'])

if __name__=='__main__': unittest.main()
