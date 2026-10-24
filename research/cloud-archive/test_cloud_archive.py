"""Offline small fixtures; no media, remote login or network request."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import archive_local as archive


class LocalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        self.source = self.raw / 'audio.mp3'
        self.source.write_bytes(b'fixture source bytes')
        self.original = self.source.read_bytes()
        actual = archive.hash_source(self.source, self.raw)
        self.file = {'source_path': str(self.source), 'relative_path': 'provider/practitioner/uploader/id/audio/a.mp3',
                     **actual, 'kind': 'audio', 'origin': 'source_artifact', 'source_id': 'fixture'}
        self.plan = {'archive_name': 'source-plan', 'raw_root': str(self.raw)}

    def test_actual_copy_independent_regular_file_and_exact_verified_set(self):
        receipt, state = archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                                name='cloud-local-fixture', budget=1_000_000, reserve=0)
        copied = Path(receipt['archive_path']) / self.file['relative_path']
        self.assertEqual(copied.read_bytes(), self.original)
        self.assertNotEqual(copied.stat().st_ino, self.source.stat().st_ino)
        self.assertEqual(copied.stat().st_nlink, 1)
        self.assertFalse(copied.is_symlink())
        self.assertTrue(state['actual_local_archive_completed'])
        self.assertEqual(state['actual_local_files'], 1)
        self.assertEqual(state['actual_drive_uploaded_files'], 0)
        self.assertFalse(state['environment_retention_guaranteed'])
        self.assertTrue(receipt['verification']['sha256_and_md5_verified'])
        self.assertFalse(Path(receipt['partial_path']).exists())
        self.assertEqual(self.source.read_bytes(), self.original)
        # Source mutation afterward does not mutate the copied snapshot.
        self.source.write_bytes(b'later source bytes')
        self.assertEqual(copied.read_bytes(), self.original)

    def test_source_hash_failure_retains_source_and_partial_without_publication(self):
        row = {**self.file, 'sha256': '0' * 64}
        with self.assertRaisesRegex(archive.ArchiveError, 'differs from planned bytes'):
            archive.create_archive([row], self.plan, self.root / 'proof', self.raw,
                                   name='cloud-local-bad-source', budget=1_000_000, reserve=0)
        receipt = json.loads((self.root / 'proof/archive-receipt.json').read_text())
        self.assertEqual(receipt['status'], 'failed_partial_retained')
        self.assertFalse(receipt['published'])
        self.assertFalse(Path(receipt['archive_path']).exists())
        self.assertTrue(Path(receipt['partial_path']).is_dir())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_existing_final_archive_is_never_overwritten(self):
        final = self.raw / 'cloud-archive/cloud-local-existing'
        final.mkdir(parents=True)
        (final / 'unrelated.txt').write_bytes(b'unrelated')
        with self.assertRaisesRegex(archive.ArchiveError, 'already exists'):
            archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                   name=final.name, budget=1_000_000, reserve=0)
        self.assertEqual((final / 'unrelated.txt').read_bytes(), b'unrelated')
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_atomic_publish_does_not_replace_racing_destination(self):
        source, destination = self.root / 'partial', self.root / 'final'
        source.write_bytes(b'partial bytes')
        destination.write_bytes(b'existing bytes')
        with self.assertRaisesRegex(archive.ArchiveError, 'no overwrite'):
            archive.rename_no_replace(source, destination)
        self.assertEqual(source.read_bytes(), b'partial bytes')
        self.assertEqual(destination.read_bytes(), b'existing bytes')

    def test_budget_failure_does_not_start_copy(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'budget'):
            archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                   name='cloud-local-budget', budget=1, reserve=0)
        self.assertFalse((self.raw / 'cloud-archive').exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_free_reserve_failure_does_not_start_copy(self):
        with patch.object(archive.shutil, 'disk_usage', return_value=archive.shutil._ntuple_diskusage(100, 99, 1)):
            with self.assertRaisesRegex(archive.ArchiveError, 'reserve'):
                archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                       name='cloud-local-reserve', budget=1_000_000, reserve=100)
        self.assertFalse((self.raw / 'cloud-archive').exists())

    def test_shared_worker_lock_prevents_second_collection_copy(self):
        with archive.worker_lock(self.raw):
            with self.assertRaisesRegex(archive.ArchiveError, 'shared lock'):
                archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                       name='cloud-local-locked', budget=1_000_000, reserve=0)
        self.assertFalse((self.raw / 'cloud-archive').exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_output_collision_cannot_overwrite_source(self):
        output = self.raw / 'source-output'
        output.mkdir()
        target = output / 'archive-receipt.json'
        os.link(self.source, target)
        with self.assertRaises(archive.ArchiveError):
            archive.create_archive([self.file], self.plan, output, self.raw, name='cloud-local-output')
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse((self.raw / 'cloud-archive').exists())

    def test_output_symlink_parent_rejected_before_copy(self):
        target = self.root / 'outside'
        target.mkdir()
        output = self.root / 'proof'
        output.symlink_to(target, target_is_directory=True)
        with self.assertRaises(archive.ArchiveError):
            archive.create_archive([self.file], self.plan, output, self.raw, name='cloud-local-output')
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse((self.raw / 'cloud-archive').exists())

    def test_source_symlink_rejected(self):
        linked = self.raw / 'linked.mp3'
        linked.symlink_to(self.source)
        with self.assertRaisesRegex(archive.ArchiveError, 'Symlink'):
            archive.create_archive([{**self.file, 'source_path': str(linked)}], self.plan, self.root / 'proof', self.raw,
                                   name='cloud-local-symlink', budget=1_000_000, reserve=0)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_archive_parent_symlink_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.raw / 'cloud-archive').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(archive.ArchiveError, 'symlink'):
            archive.create_archive([self.file], self.plan, self.root / 'proof', self.raw,
                                   name='cloud-local-parent', budget=1_000_000, reserve=0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_unexpected_archive_file_and_missing_file_fail_verification(self):
        snapshot = self.root / 'snapshot'
        snapshot.mkdir()
        with self.assertRaisesRegex(archive.ArchiveError, 'missing'):
            archive.verify_snapshot(snapshot, [self.file])
        (snapshot / 'unexpected').write_bytes(b'unexpected')
        with self.assertRaisesRegex(archive.ArchiveError, 'Unexpected'):
            archive.verify_snapshot(snapshot, [self.file])

    def test_target_traversal_rejected(self):
        partial = self.root / 'partial'
        partial.mkdir()
        with self.assertRaises(archive.ArchiveError):
            archive.copy_verified({**self.file, 'relative_path': '../escape'}, self.raw, partial)
        self.assertFalse((self.root / 'escape').exists())

    def test_no_replace_target_symlink_rejected_without_touching_target(self):
        partial = self.root / 'partial'
        target = partial / self.file['relative_path']
        target.parent.mkdir(parents=True)
        target.symlink_to(self.source)
        with self.assertRaisesRegex(archive.ArchiveError, 'already exists'):
            archive.copy_verified(self.file, self.raw, partial)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_collection_manifest_and_checksum_binding(self):
        row = archive.G['source_row'](self.source, self.file['sha256'], self.file['bytes'],
                                      'publisher-rss', 'Practitioner', 'Uploader', 'source-1', 'audio', {})
        plan = archive.G['build_plan']([row], self.raw, 'source-plan')
        stage = self.raw / 'drive-staging/source-plan'
        entries = []
        for row in plan['files']:
            relative = row['relative_path']
            entries.append({'relative_path':relative, 'sha256':row['sha256']})
            sidecar = {k:v for k,v in row.items() if k!='local_path'} | {'schema_version':1}
            path = stage / (relative + '.provenance.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(sidecar)+'\n')
            entries.append({'relative_path':relative+'.provenance.json','sha256':archive.sha(path)})
        manifest = {'archive_name':plan['archive_name'],'plan_sha256':archive.G['digest_json'](plan),
                    'source_artifact_count':plan['source_artifact_count'],
                    'files':[{k:v for k,v in r.items() if k!='local_path'} for r in plan['files']],
                    'byte_identical_aliases':[]}
        path = stage / 'manifests/archive-manifest.json'
        path.parent.mkdir()
        path.write_text(json.dumps(manifest)+'\n')
        entries.append({'relative_path':'manifests/archive-manifest.json','sha256':archive.sha(path)})
        (stage/'manifests/SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['relative_path']}\n" for r in entries))
        plan_path = self.root/'plan.json'
        plan_path.write_text(json.dumps(plan)+'\n')
        loaded, files = archive.collect_files(plan_path,self.raw,archive.sha(plan_path))
        self.assertEqual(len(files),4)  # One source, sidecar, manifest, SHA256SUMS.
        self.assertEqual(loaded,plan)
        path.write_text('{}\n')
        with self.assertRaises(archive.ArchiveError):
            archive.collect_files(plan_path,self.raw,archive.sha(plan_path))


if __name__ == '__main__':
    unittest.main()
