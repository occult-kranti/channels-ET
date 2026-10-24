#!/usr/bin/env python3
"""Independent offline transport review; all gh/API calls are replaced by mocks."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('publish_git_objects.py')
SOURCE = SCRIPT.read_bytes()
SOURCE_SHA256 = hashlib.sha256(SOURCE).hexdigest()
PUBLISHER = types.ModuleType('reviewed_publisher')
PUBLISHER.__file__ = str(SCRIPT)
exec(compile(SOURCE, str(SCRIPT), 'exec'), PUBLISHER.__dict__)
REAL_COMMIT = '0a20688c500ec6b0761f28340590c6beee58941e'


def object_sha(kind, value):
    return hashlib.sha1(kind.encode() + b' ' + str(len(value)).encode() + b'\0' + value).hexdigest()


class TransportReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.base, self.commit, self.tree = 'a'*40, 'b'*40, 'c'*40
        self.bodies = {object_sha('blob', body): body for body in [b'fixture alpha\n', b'fixture beta\n']}
        self.edits = [{'path': f'fixture-{i}.txt', 'mode':'100644', 'type':'blob', 'sha':sha}
                      for i, sha in enumerate(self.bodies)]
        self.inspected = self.commit,self.base,self.tree,self.edits,{'message':'fixture\n','tree':self.tree,'parents':[self.base]}
        self.calls = []
        self.remote = self.base
        self.mode = 'success'
        self.remote_gets = 0

    def fake_git(self, *args):
        if args[:2] == ('cat-file','blob'):
            return self.bodies[args[2]]
        if args == ('rev-parse',self.base+'^{tree}'):
            return b'dddddddddddddddddddddddddddddddddddddddd\n'
        self.fail('Unexpected Git command: '+repr(args))

    def fake_api(self, method, endpoint, body=None):
        self.calls.append((method,endpoint,body))
        if (method,endpoint)==('GET','ref/heads/main'):
            self.remote_gets += 1
            if self.mode=='remote_advanced_before' or (self.mode=='remote_advanced_during' and self.remote_gets==2):
                return {'object':{'sha':'e'*40}}
            return {'object':{'sha':self.remote}}
        if (method,endpoint)==('POST','blobs'):
            data=base64.b64decode(body['content']) if body['encoding']=='base64' else body['content'].encode()
            sha=object_sha('blob',data)
            self.assertIn(sha,self.bodies)
            return {'sha':'f'*40 if self.mode=='blob_mismatch' else sha}
        if (method,endpoint)==('POST','trees'):
            self.assertEqual(body['tree'],self.edits)
            return {'sha':'f'*40 if self.mode=='tree_mismatch' else self.tree}
        if (method,endpoint)==('POST','commits'):
            return {'sha':'f'*40 if self.mode=='commit_mismatch' else self.commit}
        if (method,endpoint)==('PATCH','refs/heads/main'):
            self.assertEqual(body,{'sha':self.commit,'force':False})
            self.remote=self.commit
            if self.mode=='ambiguous_ref_failure':
                raise RuntimeError('Mock timeout after remote accepted the write')
            return {'object':{'sha':self.commit}}
        self.fail('Unexpected API call '+repr((method,endpoint)))

    @property
    def receipt(self):
        return self.state/('git-data-publish-'+self.commit+'.json')

    def invoke(self, *extra):
        with patch.object(PUBLISHER,'STATE',self.state), patch.object(PUBLISHER,'inspect',return_value=self.inspected), \
             patch.object(PUBLISHER,'git',side_effect=self.fake_git), patch.object(PUBLISHER,'api',side_effect=self.fake_api), \
             patch.object(sys,'argv',[str(SCRIPT),'--commit',self.commit,'--workers','1',*extra]), \
             contextlib.redirect_stdout(io.StringIO()):
            PUBLISHER.main()

    def test_real_deployed_commit_inspects_without_api_or_receipt_mutation(self):
        with patch.object(PUBLISHER,'api',side_effect=AssertionError('No API call permitted')):
            result=PUBLISHER.inspect(REAL_COMMIT)
        self.assertEqual(result[0],REAL_COMMIT)
        self.assertEqual(len(result[4]['parents']),1)
        self.assertGreater(len(result[3]),0)

    def test_remote_advanced_before_publication_stops_all_posts(self):
        self.mode='remote_advanced_before'
        with self.assertRaisesRegex(ValueError,'Remote advanced'):
            self.invoke('--publish')
        self.assertEqual([(a,b) for a,b,_ in self.calls],[('GET','ref/heads/main')])

    def test_no_ref_before_all_verified_objects_tree_and_commit(self):
        self.invoke('--publish')
        operations=[(method,endpoint) for method,endpoint,_ in self.calls]
        patch_index=operations.index(('PATCH','refs/heads/main'))
        self.assertEqual(sum(op==('POST','blobs') for op in operations[:patch_index]),len(self.bodies))
        self.assertLess(operations.index(('POST','trees')),operations.index(('POST','commits')))
        self.assertLess(operations.index(('POST','commits')),patch_index)
        report=json.loads(self.receipt.read_text())
        self.assertEqual(report['status'],'published_exact_local_commit')
        self.assertTrue(report['main_ref_write_attempted'])
        self.assertTrue(report['ref_updated'])

    def test_blob_hash_mismatch_prevents_tree_commit_and_ref(self):
        self.mode='blob_mismatch'
        with self.assertRaisesRegex(RuntimeError,'blob identity mismatch'):
            self.invoke('--publish')
        self.assertFalse(any(endpoint in {'trees','commits','refs/heads/main'} for _,endpoint,_ in self.calls))

    def test_tree_hash_mismatch_prevents_commit_and_ref(self):
        self.mode='tree_mismatch'
        with self.assertRaisesRegex(ValueError,'Remote tree differs'):
            self.invoke('--publish')
        self.assertFalse(any(endpoint in {'commits','refs/heads/main'} for _,endpoint,_ in self.calls))

    def test_commit_hash_mismatch_prevents_ref(self):
        self.mode='commit_mismatch'
        with self.assertRaisesRegex(ValueError,'commit identity differs'):
            self.invoke('--publish')
        self.assertFalse(any(method=='PATCH' for method,_,_ in self.calls))

    def test_remote_advanced_during_upload_prevents_nonforced_ref_attempt(self):
        self.mode='remote_advanced_during'
        with self.assertRaisesRegex(ValueError,'Remote advanced during upload'):
            self.invoke('--publish')
        report=json.loads(self.receipt.read_text())
        self.assertFalse(report.get('main_ref_write_attempted',False))
        self.assertFalse(any(method=='PATCH' for method,_,_ in self.calls))

    def test_ambiguous_ref_write_is_marked_attempted_without_false_confirmation(self):
        self.mode='ambiguous_ref_failure'
        with self.assertRaisesRegex(RuntimeError,'Mock timeout'):
            self.invoke('--publish')
        report=json.loads(self.receipt.read_text())
        self.assertTrue(report['main_ref_write_attempted'])
        self.assertFalse(report['ref_updated'])
        self.assertEqual(self.remote,self.commit)  # Mock write succeeded before timeout.
        self.assertEqual(report['status'],'stopped_check_recorded_ref_write_state')

    def test_resume_rejects_unexpected_cached_git_id_before_any_api(self):
        self.receipt.write_text(json.dumps({'local_commit':self.commit,'target_tree':self.tree,
                                          'uploaded_blobs':[{'sha':'9'*40,'bytes':1}]}))
        with self.assertRaisesRegex(ValueError,'Unexpected cached object'):
            self.invoke('--publish','--resume')
        self.assertEqual(self.calls,[])

    def test_resume_reuses_matching_verified_immutable_id(self):
        known=next(iter(self.bodies))
        self.receipt.write_text(json.dumps({'local_commit':self.commit,'target_tree':self.tree,
                                          'uploaded_blobs':[{'sha':known,'bytes':len(self.bodies[known])}]}))
        self.invoke('--publish','--resume')
        self.assertEqual(sum((method,endpoint)==('POST','blobs') for method,endpoint,_ in self.calls),1)
        report=json.loads(self.receipt.read_text())
        self.assertEqual(report['resumed_verified_objects'],1)
        self.assertEqual(set(row['sha'] for row in report['uploaded_blobs']),set(self.bodies))

    def test_offline_inspection_preserves_existing_success_receipt_and_resume_cache(self):
        original=json.dumps({'status':'published_exact_local_commit','uploaded_blobs':[{'sha':next(iter(self.bodies))}],
                             'local_commit':self.commit,'target_tree':self.tree,'ref_updated':True}).encode()
        self.receipt.write_bytes(original)
        self.invoke()
        self.assertEqual(self.receipt.read_bytes(),original)
        self.assertEqual(self.calls,[])

    def test_offline_inspection_does_not_create_execution_receipt(self):
        self.invoke()
        self.assertFalse(self.receipt.exists())
        self.assertEqual(self.calls,[])

    def test_offline_resume_does_not_read_or_replace_invalid_existing_receipt(self):
        original=b'not JSON; an offline inspection must leave this alone\n'
        self.receipt.write_bytes(original)
        self.invoke('--resume')
        self.assertEqual(self.receipt.read_bytes(),original)
        self.assertEqual(self.calls,[])

    def test_existing_receipt_without_resume_is_preserved_before_any_api(self):
        original=json.dumps({'preserve':'existing ledger'}).encode()
        self.receipt.write_bytes(original)
        with self.assertRaisesRegex(ValueError,'receipt already exists'):
            self.invoke('--publish')
        self.assertEqual(self.receipt.read_bytes(),original)
        self.assertEqual(self.calls,[])

    def completed_receipt(self):
        original=json.dumps({'status':'published_exact_local_commit','local_commit':self.commit,
                             'target_tree':self.tree,'ref_updated':True,'publication_marker':'preserve exact bytes',
                             'uploaded_blobs':[{'sha':sha,'bytes':len(body)} for sha,body in self.bodies.items()]},
                            indent=3).encode()
        self.receipt.write_bytes(original)
        return original

    def test_completed_resume_reads_exact_remote_head_and_preserves_receipt(self):
        original=self.completed_receipt()
        self.remote=self.commit
        self.invoke('--publish','--resume')
        self.assertEqual(self.receipt.read_bytes(),original)
        self.assertEqual([(method,endpoint) for method,endpoint,_ in self.calls],[('GET','ref/heads/main')])

    def test_completed_resume_with_changed_remote_preserves_receipt_and_stops(self):
        original=self.completed_receipt()
        self.mode='remote_advanced_before'
        with self.assertRaisesRegex(ValueError,'Completed receipt preserved but remote changed'):
            self.invoke('--publish','--resume')
        self.assertEqual(self.receipt.read_bytes(),original)
        self.assertEqual([(method,endpoint) for method,endpoint,_ in self.calls],[('GET','ref/heads/main')])

    def fake_inspect(self, extra_headers='', mode='100644', kind='blob', parent_count=1):
        parents=''.join('parent '+self.base+'\n' for _ in range(parent_count))
        raw=('tree '+self.tree+'\n'+parents+'author Fixture <fixture@example.invalid> 1000000000 +0000\n'
             +'committer Fixture <fixture@example.invalid> 1000000000 +0000\n'+extra_headers+'\nfixture\n').encode()
        commit=object_sha('commit',raw)
        def git(*args):
            if args[:2]==('rev-parse','--verify'):
                return (commit+'\n').encode()
            if args==('cat-file','commit',commit):return raw
            if args[:3]==('ls-tree','-r','-z'):
                if args[3]==self.base:return b''
                return (mode+' '+kind+' '+next(iter(self.bodies))+'\tfixture\0').encode()
            self.fail('Unexpected synthetic inspect command '+repr(args))
        with patch.object(PUBLISHER,'git',side_effect=git):
            return PUBLISHER.inspect(commit)

    def test_signed_encoded_or_multiline_commit_is_rejected(self):
        for extra in ['encoding ISO-8859-1\n','gpgsig -----BEGIN PGP SIGNATURE-----\n signature\n']:
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError,'different transport'):
                self.fake_inspect(extra_headers=extra)

    def test_merge_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'single-parent'):
            self.fake_inspect(parent_count=2)

    def test_changed_symlink_or_submodule_is_rejected(self):
        for mode,kind in [('120000','blob'),('160000','commit')]:
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError,'symlink/submodule'):
                self.fake_inspect(mode=mode,kind=kind)


if __name__=='__main__':
    unittest.main(verbosity=2)
