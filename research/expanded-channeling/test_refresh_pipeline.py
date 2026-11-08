"""Guard tests use local fixtures; no downloads, live commits or publication."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('refresh',Path(__file__).with_name('refresh_pipeline.py'))
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)

def artifact(path):
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':R.sha(path)}

class StateGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.private=patch.object(R,'PRIVATE',self.root);self.private.start()
        self.a=self.root/'acquisition.json';self.q=self.root/'queue.json';self.f=self.root/'fallback.json';self.r=self.root/'review.json';self.h=self.root/'hold-review.json'
        self.rows=[{'publication_id':str(i),'source_id':'source-'+str(i),'status':'completed','source':{'source_id':'source-'+str(i)}} for i in range(229)]
        frame=self.root/'frame.json';R.dump(frame,[r['source'] for r in self.rows])
        R.dump(self.a,{'status':'frame_complete','completed_count':229,'frame_count':229,'records':self.rows,'source_frame':artifact(frame)})
        h={'publication_id':'0','source_id':'source-0','disposition':'held_unadmitted_asr','reason_code':'multiple_segments_outside_audio'}
        hold=self.root/'holds.json';R.dump(hold,{'status':'reviewed_source_specific_recognition_holds','records':[h]})
        R.dump(self.h,{'status':'accepted_for_continuation_with_explicit_hold','hold_ledger_sha256':R.sha(hold)})
        selected=self.root/'selected.json';R.dump(selected,{'unfiltered_acquisition_sha256':R.sha(self.a),'records':self.rows[1:],'completed_count':228,'recognition_hold_ledger':artifact(hold)})
        self.asr=self.root/'asr.json';R.dump(self.asr,{'status':'selected_snapshot_complete','records':self.rows[1:],'input':artifact(selected),'candidate_count':228})
        R.dump(self.q,{'queue_version':3,'status':'selected_frame_complete_with_recognition_holds','asr_manifest':artifact(self.asr),'hold_ledger':artifact(hold),'source_count':229,'asr_candidate_count':228,'exact_caption_linked_count':0,'recognition_hold_count':1,'recognition_holds':[h]})
        R.dump(self.f,{'status':'single_experimental_retry_failed','records':[]})
        self.review()
    def tearDown(self):self.private.stop();self.tmp.cleanup()
    def review(self):R.dump(self.r,{'schema_version':1,'status':'accepted_unadmitted_hold','manifest_sha256':R.sha(self.f),'receipt_sha256':None,'publication_id':'0','decision':'Fixture reviewed failure remains held.'})
    def load(self):return R.read_state(self.a,self.q,self.f,self.r,self.h)
    def edit(self,p,**changes):
        d=json.loads(p.read_bytes());d.update(changes);R.dump(p,d)
    def test_terminal_hold_partition_is_frozen(self):
        state=self.load();self.assertEqual(len(json.loads(state['merged-asr.json'])['records']),228)
        self.edit(self.a,status='running');self.assertEqual(json.loads(state['acquisition.json'])['status'],'frame_complete')
    def test_running_waits_and_failed_queue_stops(self):
        self.edit(self.q,status='snapshot_started');self.assertIsNone(self.load())
        self.edit(self.q,status='halted_unrecoverable_diagnostic')
        with self.assertRaisesRegex(R.ReviewRequired,'queue_requires_review'):self.load()
    def test_stale_asr_snapshot_rejected(self):
        self.edit(self.a,new_generation=True)
        with self.assertRaisesRegex(R.ReviewRequired,'stale_selected'):self.load()
    def test_frame_and_partition_counts_checked(self):
        self.edit(self.q,asr_candidate_count=227)
        with self.assertRaisesRegex(R.ReviewRequired,'terminal_counts'):self.load()
    def test_incomplete_or_error_collection_rejected(self):
        self.edit(self.a,completed_count=228)
        with self.assertRaisesRegex(R.ReviewRequired,'finite_frame'):self.load()
    def test_pending_fallback_not_admitted_from_completed_row(self):
        self.edit(self.f,status='single_experimental_retry_completed_pending_review',records=[{'status':'completed'}]);self.r.unlink()
        self.assertIsNone(self.load())
    def test_stale_review_rejected(self):
        self.edit(self.f,new_generation=True)
        with self.assertRaisesRegex(R.ReviewRequired,'fallback_review_stale'):self.load()
    def test_rejected_fallback_needs_explicit_bound_review(self):
        self.edit(self.r,status='pending')
        with self.assertRaisesRegex(R.ReviewRequired,'fallback_requires_review'):self.load()
    def test_successful_fallback_needs_exact_receipt_review(self):
        folder=self.root/'alternate';folder.mkdir();normalized=folder/'transcript.json';R.dump(normalized,{'fixture':True})
        row={'status':'completed','publication_id':'0','source_id':'0:alternate','outputs':{'normalized':artifact(normalized)}}
        receipt=folder/'receipt.json';R.dump(receipt,row)
        R.dump(self.f,{'status':'single_experimental_retry_completed_pending_review','records':[row]})
        R.dump(self.r,{'schema_version':1,'status':'accepted_for_analysis','manifest_sha256':R.sha(self.f),'receipt_sha256':R.sha(receipt),'publication_id':'0'})
        merged=json.loads(self.load()['merged-asr.json']);self.assertEqual(len(merged['records']),229)
        self.assertEqual(merged['accepted_recognition_receipt_count'],229);self.assertEqual(merged['standard_edition']['candidate_count'],228)
        self.assertNotIn('input',merged);self.assertEqual(merged['unadmitted_publications'],[])
        self.edit(self.r,receipt_sha256='0'*64)
        with self.assertRaisesRegex(R.ReviewRequired,'fallback_receipt_review'):self.load()
    def test_duplicate_publications_rejected(self):
        self.rows[-1]=self.rows[-2];self.edit(self.a,records=self.rows)
        with self.assertRaisesRegex(R.ReviewRequired,'invalid_acquisition_rows'):self.load()
    def v4_setup(self):
        hs=[{'publication_id':str(i),'source_id':'source-'+str(i),'disposition':'held_unadmitted_asr','reason_code':'multiple_segments_outside_audio'} for i in (0,1)]
        hold=self.root/'holds.json';R.dump(hold,{'status':'policy_validated_source_specific_recognition_holds','records':hs})
        selected=self.root/'selected.json';R.dump(selected,{'unfiltered_acquisition_sha256':R.sha(self.a),'records':self.rows[2:],'completed_count':227,'recognition_hold_ledger':artifact(hold)})
        self.edit(self.asr,records=self.rows[2:],input=artifact(selected),candidate_count=227)
        self.edit(self.q,queue_version=4,asr_manifest=artifact(self.asr),hold_ledger=artifact(hold),recognition_hold_count=2,asr_candidate_count=227,recognition_holds=hs)
        f2=self.root/'fallback2.json';r2=self.root/'review2.json';R.dump(f2,{'status':'single_experimental_retry_failed','records':[]})
        R.dump(r2,{'schema_version':1,'status':'accepted_unadmitted_hold','manifest_sha256':R.sha(f2),'receipt_sha256':None,'publication_id':'1'})
        return f2,r2
    def test_v4_two_fallbacks_remain_explicit_and_failed_editions_unadmitted(self):
        f2,r2=self.v4_setup()
        with patch.object(R,'FALLBACK_PUBLICATIONS',('0','1')),patch.object(R,'validate_v4_policy',return_value={'hold-review.json':self.h.read_bytes()}):
            state=R.read_state(self.a,self.q,self.f,self.r,self.h,[(f2,r2,'1')],self.h)
            merged=json.loads(state['merged-asr.json']);self.assertEqual(len(merged['records']),227);self.assertEqual(merged['unadmitted_publications'],['0','1'])
            self.assertEqual(len(merged['alternate_editions']),2)
            r2.unlink();self.assertIsNone(R.read_state(self.a,self.q,self.f,self.r,self.h,[(f2,r2,'1')],self.h))
    def test_v4_rejects_undeclared_retry(self):
        f2,r2=self.v4_setup()
        with patch.object(R,'FALLBACK_PUBLICATIONS',('0','1')),patch.object(R,'validate_v4_policy',return_value={'hold-review.json':self.h.read_bytes()}):
            with self.assertRaisesRegex(R.ReviewRequired,'finite_fallback_scope'):
                R.read_state(self.a,self.q,self.f,self.r,self.h,[(f2,r2,'1'),(f2,r2,'2')],self.h)

class PublicationGuards(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_private_content_and_raw_turns_rejected_numeric_counts_allowed(self):
        p=self.root/'data.json'
        for obj in ({'source':'/workspace/private'},{'turns':[{'text':'transcript'}]},{'text':'full transcript'}):
            R.dump(p,obj)
            with self.assertRaises(R.ReviewRequired):R.privacy_check(p)
        R.dump(p,{'turns':42,'title':'Public publication title'});R.privacy_check(p)
    def test_duplicate_and_unapproved_destinations(self):
        p=self.root/'data.json';R.dump(p,{'count':2})
        name='dist/channeling-network/acquisition.json'
        with self.assertRaisesRegex(R.ReviewRequired,'duplicate_or_unapproved'):R.copy_plan([(p,name),(p,name)])
        with self.assertRaisesRegex(R.ReviewRequired,'duplicate_or_unapproved'):R.copy_plan([(p,'../unapproved')])
    def test_symlink_and_parent_traversal_rejected(self):
        p=self.root/'data.json';p.write_text('{}');link=self.root/'link.json';link.symlink_to(p)
        with self.assertRaisesRegex(R.ReviewRequired,'symlink'):R.safe_file(link)
        with self.assertRaisesRegex(R.ReviewRequired,'parent_traversal'):R.safe_file(self.root/'..'/self.root.name/'data.json')
    def test_disk_reserve(self):
        with patch.object(R.shutil,'disk_usage',return_value=type('Disk',(),{'free':R.FLOOR+3})()):
            with self.assertRaisesRegex(R.ReviewRequired,'insufficient_disk'):R.disk_guard(self.root,4)
    def test_inherited_execution_overrides_removed(self):
        with patch.dict(os.environ,{'PYTHONOPTIMIZE':'1','GIT_DIR':'elsewhere','GIT_INDEX_FILE':'bad','GIT_TRACE':'1'}):
            e=R.env();self.assertNotIn('PYTHONOPTIMIZE',e);self.assertNotIn('GIT_DIR',e);self.assertNotIn('GIT_INDEX_FILE',e);self.assertNotIn('GIT_TRACE',e)
    def test_closed_schema_rejects_disguised_transcript_field(self):
        with self.assertRaisesRegex(R.ReviewRequired,'unknown_public_field'):
            R.closed_public_shape({'documents':[{'title':'known','body_copy':'transcript'}]},[{'documents':[{'title':'known'}]}])
        R.closed_public_shape({'excluded_and_aliases':[{'source_id':'x','selected_source_id':'y','reason':'duplicate'}]},[{'excluded_and_aliases':[]}])
    def test_declared_v4_public_markers_without_human_review_claim(self):
        before={'records':[{'asr_failed_editions':[{'reason_code':'failure'}]}]}
        row={'reason_code':'multiple_segments_outside_audio','review_status':'automatic_reviewed_policy_not_manual_source_review','human_reviewed':False,'quarantine_policy_sha256':'a'*64}
        R.closed_public_shape({'records':[{'asr_failed_editions':[row]}]},[before])
        row['human_reviewed']=True
        with self.assertRaisesRegex(R.ReviewRequired,'human_review_claim'):R.closed_public_shape({'records':[{'asr_failed_editions':[row]}]},[before])
    def test_private_audit_projection_binding_is_canonicalized(self):
        projection=self.root/'acquisition.json';R.dump(projection,{'count':229})
        audit=self.root/'data.json';R.dump(audit,{'source_bindings':{'acquisition.json':R.sha(projection)}})
        R.canonical_audit_binding(audit,projection)
        value=json.loads(audit.read_bytes());canonical='research/subscription-screening/publisher-audio-acquisition.json'
        self.assertEqual(value['source_bindings'],{canonical:R.sha(projection)})
        R.closed_public_shape(value,[{'source_bindings':{canonical:'old hash'}}])
    def test_actual_audit_builder_private_projection_preserves_public_shape(self):
        spec=importlib.util.spec_from_file_location('audit_builder',R.ROOT/'research/subscription-screening/build_audit.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        stage=self.root/'audit';stage.mkdir()
        shutil.copyfile(R.ROOT/'dist/subscription-audit/source-topics.json',stage/'source-topics.json')
        projection=self.root/'acquisition.json';shutil.copyfile(R.ROOT/'research/subscription-screening/publisher-audio-acquisition.json',projection)
        builder.build(R.ROOT,[R.ROOT/'research/subscription-screening/first14.json',R.ROOT/'research/subscription-screening/second14.json'],stage/'data.json',projection)
        R.canonical_audit_binding(stage/'data.json',projection);R.privacy_check(stage/'data.json')
        R.closed_public_shape(json.loads((stage/'data.json').read_bytes()),[json.loads((R.ROOT/'dist/subscription-audit/data.json').read_bytes())])
    def test_dry_run_never_calls_publish(self):
        out=self.root/'fresh'
        def fake_stage(*args,**kwargs):out.mkdir();return {}
        with patch.object(R,'PRIVATE',self.root),patch.object(R,'git_guard'),patch.object(R,'disk_guard'),patch.object(R,'read_state',return_value={}),patch.object(R,'stage',side_effect=fake_stage),patch.object(R,'publish') as publisher:
            R.main(['--expected-head','a'*40,'--output',str(out),'--dry-run'])
            publisher.assert_not_called();self.assertTrue(json.loads((out/'completion.json').read_bytes())['dry_run'])

class GitGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)
        self.cmd('init','-b','main');self.cmd('config','user.name','Fixture');self.cmd('config','user.email','fixture@example.invalid')
        (self.repo/'file').write_text('original');self.cmd('add','file');self.cmd('commit','-m','fixture');self.head=self.cmd('rev-parse','HEAD')
    def tearDown(self):self.tmp.cleanup()
    def cmd(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,stderr=subprocess.DEVNULL,text=True).strip()
    def test_clean_head_passes(self):R.git_guard(self.head,self.repo,remote=False)
    def test_dirty_untracked_and_index_rejected(self):
        (self.repo/'new').write_text('user change')
        with self.assertRaisesRegex(R.ReviewRequired,'worktree_not_clean'):R.git_guard(self.head,self.repo,remote=False)
        self.cmd('add','new')
        with self.assertRaisesRegex(R.ReviewRequired,'worktree_not_clean'):R.git_guard(self.head,self.repo,remote=False)
    def test_changed_head_rejected(self):
        self.cmd('commit','--allow-empty','-m','user commit')
        with self.assertRaisesRegex(R.ReviewRequired,'head_changed'):R.git_guard(self.head,self.repo,remote=False)
    def test_advanced_remote_rejected(self):
        with patch.object(R,'remote_head',return_value='f'*40):
            with self.assertRaisesRegex(R.ReviewRequired,'remote_main_changed'):R.git_guard(self.head,self.repo)
    def test_no_push_makes_only_local_reviewed_commit(self):
        p='file';source=Path(self.tmp.name).parent/(self.repo.name+'-source');source.write_text('approved change')
        plan={p:{'source':source,'sha256':R.sha(source)}}
        calls=[];real=R.git
        def tracked(args,repo=R.ROOT):calls.append(args);return real(args,repo)
        try:
            with patch.object(R,'remote_head',return_value=self.head),patch.object(R,'disk_guard'),patch.object(R,'git',side_effect=tracked):
                result=R.publish(plan,self.head,True,self.repo)
            self.assertFalse(result['pushed']);self.assertFalse(any(args[0]=='push' for args in calls));self.assertEqual((self.repo/p).read_text(),'approved change')
        finally:source.unlink()
    def test_concurrent_commit_blob_change_stops_before_push(self):
        source=Path(self.tmp.name).parent/(self.repo.name+'-source');source.write_text('approved')
        plan={'file':{'source':source,'sha256':R.sha(source)}};real=R.git;calls=[]
        def raced(args,repo=R.ROOT):
            calls.append(args)
            if 'commit' in args:
                (self.repo/'file').write_text('unapproved concurrent edit');self.cmd('add','file')
            return real(args,repo)
        try:
            with patch.object(R,'remote_head',return_value=self.head),patch.object(R,'disk_guard'),patch.object(R,'git',side_effect=raced):
                with self.assertRaisesRegex(R.ReviewRequired,'committed_blob_changed'):R.publish(plan,self.head,False,self.repo)
            self.assertFalse(any(args[0]=='push' for args in calls))
        finally:source.unlink()
    def test_foreign_change_during_copy_stops(self):
        source=Path(self.tmp.name).parent/(self.repo.name+'-source');source.write_text('approved')
        try:
            with patch.object(R,'remote_head',return_value=self.head),patch.object(R,'disk_guard'),patch.object(R,'changed_paths',return_value={'foreign.txt'}):
                with self.assertRaisesRegex(R.ReviewRequired,'worktree_changed_during_copy'):
                    R.publish({'file':{'source':source,'sha256':R.sha(source)}},self.head,True,self.repo)
            self.assertEqual((self.repo/'file').read_text(),'original')
        finally:source.unlink()

if __name__=='__main__':unittest.main()
