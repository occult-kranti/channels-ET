"""Offline adversarial storage fixtures; no Google credentials or network calls."""
import copy
import errno
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote

SPEC = importlib.util.spec_from_file_location('batch_storage_tested', Path(__file__).with_name('storage.py'))
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class FakeDrive:
    def __init__(self):
        self.nodes = {'root': {'Name': '', 'ID': 'root', 'IsDir': True, 'parent': None}}
        self.commands = []
        self.free = 10 ** 12
        self.remotes = 'archive: drive\n'
        self.fail_auth = False
        self.fail_copy_after_write = False
        self.partial_copy = False
        self.fail_mkdir_after_write = False

    def add(self, parent, name, *, directory=False, data=b''):
        ident = 'node' + str(len(self.nodes))
        self.nodes[ident] = {'ID': ident, 'Name': name, 'parent': parent, 'IsDir': directory,
                             'Size': 0 if directory else len(data),
                             'Hashes': {} if directory else {'MD5': hashlib.md5(data, usedforsecurity=False).hexdigest()}}
        return ident

    def __call__(self, args):
        self.commands.append(list(args))
        command = args[0]
        root = next((x.split('=', 1)[1] for x in args if x.startswith('--drive-root-folder-id=')), 'root')
        code, value = 0, ''
        if command == 'listremotes':
            value = self.remotes
        elif command == 'about':
            code, value = (1, '') if self.fail_auth else (0, json.dumps({'free': self.free, 'total': 10 ** 12}))
        elif root not in self.nodes:
            code = 3
        elif command == 'lsjson':
            value = json.dumps([{k: v for k, v in row.items() if k != 'parent'} for row in self.nodes.values() if row['parent'] == root])
        elif command == 'mkdir':
            name = args[1].split(':', 1)[1].strip('/')
            self.add(root, name, directory=True)
            code = 1 if self.fail_mkdir_after_write else 0
        elif command == 'copyto':
            data = Path(args[1]).read_bytes()
            if self.partial_copy:
                data = data[:1]
            self.add(root, args[2].split(':', 1)[1].strip('/'), data=data)
            code = 1 if self.fail_copy_after_write or self.partial_copy else 0
        else:
            raise AssertionError('Unexpected command ' + command)
        return subprocess.CompletedProcess(args, code, value, '')

    def copies(self):
        return sum(c[0] == 'copyto' for c in self.commands)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.raw = self.base / 'raw'
        self.private = self.base / 'private'
        self.raw.mkdir(); self.private.mkdir()
        self.patches = [patch.object(S, 'RAW_ROOT', self.raw), patch.object(S, 'PRIVATE_ROOT', self.private), patch.object(S.guards, 'RAW_ROOT', self.raw)]
        for item in self.patches:
            item.start()
        self.counter = 0

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def artifact(self, name='recording.mp3', data=b'fixture audio bytes', provider='publisher_rss', kind='audio'):
        path = self.raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        item = {'local_path': str(path), 'sha256': sha, 'bytes': len(data), 'provider': provider,
                'medium_id': 'medium-one', 'channel_id': 'publisher-one',
                'source_id': 'youtube:AbCdEfGhI12' if provider == 'youtube' else 'publisher:episode-1', 'kind': kind}
        if provider == 'youtube':
            item.update(duration_seconds=600, duration_scope='source_video', is_short=False, metadata_refreshed_at_acquisition=True)
        proof = self.private / (name.replace('/', '-') + '.proof.json')
        proof.write_text(json.dumps({'verified_artifacts': [{k: item[k] for k in ['local_path', 'sha256', 'bytes', 'source_id', 'kind']} | {'status': 'verified'}]}))
        item['verification_receipt'] = {'path': str(proof), 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}
        return item

    def plan(self, artifacts=None):
        return S.build_plan({'schema_version': 1, 'batch_id': 'pilot', 'artifacts': artifacts or [self.artifact()]}, 'channels-ET-pilot-fixture')

    def receipt(self):
        self.counter += 1
        return self.private / f'receipt-{self.counter}.json'

    def upload(self, plan, drive, **kw):
        path = self.receipt()
        value = S.upload(plan, 'archive', path, self.raw / 'drive-staging', private_root_confirmed=True,
                         runner=drive, lock_root=self.private / 'locks', **kw)
        return path, value

    def local(self, plan, **kw):
        path = self.receipt()
        value = S.local_archive(plan, path, budget=10 ** 9, reserve=0, **kw)
        return path, value

    def test_explicit_only_plan_and_reverification(self):
        plan = self.plan()
        self.assertEqual(plan['file_count'], 1)
        self.assertTrue(S.validate_plan(plan))
        self.assertNotIn('canonical_file_count', plan)

    def test_invalid_input_families(self):
        item = self.artifact()
        for changes in [{'bytes': True}, {'bytes': -1}, {'sha256': 'bad'}, {'provider': 'unknown'}, {'kind': 'unknown'},
                        {'medium_id': '../parent'}, {'channel_id': ''}]:
            with self.subTest(changes=changes), self.assertRaises(S.ArchiveError):
                S.build_plan({'schema_version': 1, 'batch_id': 'pilot', 'artifacts': [{**item, **changes}]})
        for artifacts in [[], None, 'not-list']:
            with self.assertRaises(S.ArchiveError):
                S.build_plan({'schema_version': 1, 'batch_id': 'pilot', 'artifacts': artifacts})

    def test_receipt_must_prove_exact_verified_bytes(self):
        item = self.artifact()
        proof = Path(item['verification_receipt']['path'])
        for change in ['failed-status', 'different-hash', 'duplicate']:
            row = {k: item[k] for k in ['local_path', 'sha256', 'bytes', 'source_id', 'kind']} | {'status': 'verified'}
            if change == 'failed-status': row['status'] = 'failed_media_validation'
            if change == 'different-hash': row['sha256'] = '0' * 64
            proof.write_text(json.dumps({'verified_artifacts': [row, row] if change == 'duplicate' else [row]}))
            item['verification_receipt']['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
            with self.subTest(change=change), self.assertRaises(S.ArchiveError): self.plan([item])

    def test_changed_receipt_source_and_plan_rejected(self):
        item = self.artifact(); plan = self.plan([item])
        Path(item['local_path']).write_bytes(b'changed')
        with self.assertRaises(S.ArchiveError): S.validate_plan(plan)
        item = self.artifact(); plan = self.plan([item])
        Path(item['verification_receipt']['path']).write_text('{}')
        with self.assertRaises(S.ArchiveError): S.validate_plan(plan)
        item = self.artifact(); plan = self.plan([item]); plan['source_bytes'] += 1
        with self.assertRaises(S.ArchiveError): S.validate_plan(plan)

    def test_source_symlink_and_receipt_symlink_rejected(self):
        item = self.artifact()
        source = Path(item['local_path']); moved = source.with_suffix('.original'); source.rename(moved); source.symlink_to(moved)
        with self.assertRaises(S.ArchiveError): self.plan([item])
        source.unlink(); moved.rename(source)
        proof = Path(item['verification_receipt']['path']); moved = proof.with_suffix('.original'); proof.rename(moved); proof.symlink_to(moved)
        with self.assertRaises(S.ArchiveError): self.plan([item])

    def test_youtube_gate_and_duration_scope(self):
        item = self.artifact(provider='youtube')
        self.assertTrue(S.validate_plan(self.plan([item])))
        for change in [{'duration_seconds': 299}, {'duration_seconds': True}, {'duration_seconds': float('nan')},
                       {'is_short': True}, {'metadata_refreshed_at_acquisition': False}, {'duration_scope': 'transcript'},
                       {'source_id': 'youtube:bad'}]:
            with self.subTest(change=change), self.assertRaises(S.ArchiveError): self.plan([{**item, **change}])

    def test_publisher_video_is_separate_provider(self):
        item = self.artifact(provider='publisher_video', kind='video')
        self.assertEqual(self.plan([item])['files'][0]['provider'], 'publisher_video')

    def test_private_source_root_is_explicit_and_escape_is_rejected(self):
        item = self.artifact(); original = Path(item['local_path']); target = self.private / original.name
        original.rename(target); item['local_path'] = str(target)
        proof = Path(item['verification_receipt']['path']); value = json.loads(proof.read_text())
        value['verified_artifacts'][0]['local_path'] = str(target); proof.write_text(json.dumps(value))
        item['verification_receipt']['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
        plan = self.plan([item]); self.assertEqual(plan['files'][0]['source_root'], str(self.private))
        _, done = self.local(plan); self.assertEqual(done['status'], 'completed')
        with self.assertRaises(S.ArchiveError): S.source_root_for(self.base / 'outside.mp3')

    def test_provenance_comes_from_bound_receipt_and_original_is_archived(self):
        item = self.artifact(); proof = Path(item['verification_receipt']['path']); value = json.loads(proof.read_text())
        value['verified_artifacts'][0].update(provider='publisher_rss', medium_id='medium-one', channel_id='publisher-one',
                                            actual_speaker_status='unknown_not_audio_verified', context_associations=[{'context_id': 'medium-one'}, {'context_id': 'guest-two'}])
        proof.write_text(json.dumps(value)); item['verification_receipt']['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
        item['actual_speaker_status'] = 'caller-incorrectly-verified'
        plan = self.plan([item]); row = plan['files'][0]
        self.assertEqual(row['bound_provenance']['actual_speaker_status'], 'unknown_not_audio_verified')
        self.assertEqual(len(row['bound_provenance']['context_associations']), 2)
        _, done = self.local(plan)
        archived = Path(done['actual_root']) / 'manifests/verification' / (item['verification_receipt']['sha256'] + '.json')
        self.assertEqual(archived.read_bytes(), proof.read_bytes())
        with self.assertRaises(S.ArchiveError): self.plan([{**item, 'medium_id': 'changed-medium'}])

    def test_metadata_budget_is_checked_before_staging(self):
        plan = self.plan()
        with self.assertRaises(S.ArchiveError): S.stage_metadata(plan, self.raw / 'drive-staging', budget=1, reserve=0)
        self.assertFalse((self.raw / 'drive-staging').exists())
        with patch.object(S, 'MAX_METADATA_BYTES', 1), self.assertRaises(S.ArchiveError): S.metadata_payloads(plan)

    def test_local_directory_replacement_during_copy_cannot_complete(self):
        plan = self.plan(); original = S.local_guards.copy_verified; replaced = False
        def swap_after_copy(row, raw_root, active):
            nonlocal replaced
            result = original(row, raw_root, active)
            if not replaced:
                replaced = True
                active.rename(active.with_name(active.name + '-moved'))
                active.mkdir(mode=0o700)
            return result
        receipt = self.receipt()
        with patch.object(S.local_guards, 'copy_verified', swap_after_copy), self.assertRaises(S.ArchiveError):
            S.local_archive(plan, receipt, budget=10 ** 9, reserve=0)
        self.assertEqual(json.loads(receipt.read_text())['status'], 'failed_no_rollback')

    def test_custom_local_archive_root_stays_inside_raw_tree(self):
        plan = self.plan(); receipt = self.receipt(); root = self.raw / 'batch-2026-11/cloud-archive'
        done = S.local_archive(plan, receipt, archive_root=root, budget=10 ** 9, reserve=0)
        self.assertEqual(Path(done['actual_root']).parent, root)
        with self.assertRaises(S.ArchiveError): S.local_archive(plan, self.receipt(), archive_root=self.base / 'outside', budget=10 ** 9, reserve=0)

    def test_hardlink_mode_shares_source_but_copies_metadata_and_resumes(self):
        plan = self.plan(); first, done = self.local(plan, mode='hardlink')
        self.assertFalse(done['independent_copies']); self.assertEqual(done['linked_files'], 1)
        self.assertEqual(done['copied_files'], 5); self.assertIn('not an independent media backup', done['shared_inode_semantics'])
        source = Path(plan['files'][0]['local_path']); target = Path(done['actual_root']) / plan['files'][0]['relative_path']
        self.assertEqual(source.stat().st_ino, target.stat().st_ino); self.assertGreaterEqual(target.stat().st_nlink, 2)
        self.assertEqual(S.guards.hash_source(target, Path(done['actual_root']))['sha256'], plan['files'][0]['sha256'])
        before = S.storage_used_bytes()
        _, resumed = self.local(plan, mode='hardlink', resume_from=first)
        self.assertEqual(resumed['linked_files'], 0); self.assertEqual(resumed['copied_files'], 0); self.assertEqual(resumed['reused_files'], 6)
        self.assertEqual(resumed['new_unique_file_bytes'], 0)
        self.assertGreaterEqual(S.storage_used_bytes(), before)  # New receipt only, never another media allocation.

    def test_hardlink_cross_device_failure_never_falls_back_to_copy(self):
        plan = self.plan(); receipt = self.receipt()
        with patch.object(S.os, 'link', side_effect=OSError(errno.EXDEV, 'different filesystem')), patch.object(S.local_guards, 'copy_verified', wraps=S.local_guards.copy_verified) as copier:
            with self.assertRaisesRegex(S.ArchiveError, 'no copy fallback'):
                S.local_archive(plan, receipt, mode='hardlink', budget=10 ** 9, reserve=0)
            self.assertEqual(copier.call_count, 0)
        self.assertEqual(json.loads(receipt.read_text())['status'], 'failed_no_rollback')

    def test_hardlink_tamper_affects_both_paths_but_resume_detects_it(self):
        plan = self.plan(); first, done = self.local(plan, mode='hardlink')
        source = Path(plan['files'][0]['local_path']); target = Path(done['actual_root']) / plan['files'][0]['relative_path']
        source.write_bytes(b'changed shared contents')
        self.assertEqual(target.read_bytes(), b'changed shared contents')
        with self.assertRaises(S.ArchiveError): self.local(plan, mode='hardlink', resume_from=first)

    def test_resume_mode_and_original_mtime_are_bound(self):
        plan = self.plan(); first, _ = self.local(plan, mode='hardlink')
        with self.assertRaises(S.ArchiveError): self.local(plan, mode='copy', resume_from=first)
        source = Path(plan['files'][0]['local_path']); info = source.stat()
        os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
        with self.assertRaises(S.ArchiveError): self.local(plan, mode='hardlink', resume_from=first)

    def test_hardlink_collision_is_preserved_and_storage_counts_unique_inodes(self):
        plan = self.plan(); row = {'source_path': plan['files'][0]['local_path'], 'storage_mode': 'hardlink',
                                 **{k: plan['files'][0][k] for k in ['relative_path', 'bytes', 'sha256', 'md5']}}
        root = self.raw / 'hardlink-fixture'; root.mkdir(mode=0o700)
        before = S.storage_used_bytes(); S.local_hardlink(row, root); after = S.storage_used_bytes()
        self.assertEqual(before, after)
        with self.assertRaisesRegex(S.ArchiveError, 'no overwrite'): S.local_hardlink(row, root)
        target = root / row['relative_path']; self.assertEqual(target.read_bytes(), Path(row['source_path']).read_bytes())

    def test_corpus_derivatives_keep_lineage_and_are_not_media(self):
        item = self.artifact('analysis.json', b'{"summary":"fixture"}', provider='derived_analysis', kind='analysis')
        item['source_id'] = 'corpus:crimson-circle:freedom-series:first10:2026-11-07'
        proof = Path(item['verification_receipt']['path']); value = json.loads(proof.read_text()); row = value['verified_artifacts'][0]
        row.update(source_id=item['source_id'], provider='derived_analysis', medium_id=item['medium_id'], channel_id=item['channel_id'],
                   parent_source_ids=['publisher:episode-1', 'publisher:episode-2'], scope='Derived corpus file; byte and lineage verification only.',
                   limitations=['No independent scientific validation'], human_reviewed=False)
        proof.write_text(json.dumps(value)); item['verification_receipt']['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
        plan = self.plan([item]); bound = plan['files'][0]['bound_provenance']
        self.assertEqual(len(bound['parent_source_ids']), 2); self.assertFalse(bound['human_reviewed'])
        self.assertEqual(plan['files'][0]['kind'], 'analysis')
        extracted = self.artifact('publisher.txt', b'fixture publication text', provider='publisher_reference', kind='reference_text')
        self.assertEqual(self.plan([extracted])['files'][0]['provider'], 'publisher_reference')

    def test_index_escapes_titles_and_every_local_link_exists(self):
        item = self.artifact(); proof = Path(item['verification_receipt']['path']); value = json.loads(proof.read_text())
        value['verified_artifacts'][0].update(title='<script>unsafe()</script>', source_url='javascript:alert(1)')
        proof.write_text(json.dumps(value)); item['verification_receipt']['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
        plan = self.plan([item]); _, done = self.local(plan, mode='hardlink'); root = Path(done['actual_root'])
        class Parse(HTMLParser):
            def __init__(self): super().__init__(); self.links = []; self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
                if tag == 'a': self.links.extend(v for k, v in attrs if k == 'href')
        parser = Parse(); text = (root / 'index.html').read_text(); parser.feed(text)
        self.assertIn('&lt;script&gt;', text); self.assertNotIn('script', parser.tags)
        self.assertNotIn('javascript:', text); self.assertNotIn('video', parser.tags); self.assertNotIn('iframe', parser.tags)
        for target in parser.links:
            if not target.startswith(('http:', 'https:')):
                self.assertTrue((root / unquote(target)).is_file(), target)

    def test_generated_provenance_has_disjoint_paths(self):
        first = self.artifact('x'); second = self.artifact('x.provenance.json', b'different')
        plan = self.plan([first, second]); _, metadata = S.stage_metadata(plan, self.raw / 'drive-staging')
        paths = [r['relative_path'] for r in [*plan['files'], *metadata]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(r['relative_path'].startswith('manifests/') or r['relative_path'] == 'index.html' for r in metadata))

    def test_local_archive_independent_complete_copy_and_resume(self):
        plan = self.plan(); first, receipt = self.local(plan)
        self.assertEqual(receipt['status'], 'completed'); self.assertEqual(receipt['copied_files'], 6)
        root = Path(receipt['actual_root']); self.assertEqual(len(list(p for p in root.rglob('*') if p.is_file())), 6)
        source = Path(plan['files'][0]['local_path']); target = root / plan['files'][0]['relative_path']
        self.assertNotEqual(source.stat().st_ino, target.stat().st_ino); self.assertEqual(target.stat().st_nlink, 1)
        _, replay = self.local(plan, resume_from=first)
        self.assertEqual(replay['copied_files'], 0); self.assertEqual(replay['reused_files'], 6)
        self.assertEqual(replay['verified_bytes'], receipt['planned_bytes'])

    def test_local_resume_between_completed_files(self):
        plan = self.plan(); original = S.local_guards.copy_verified; count = 0
        def interrupted(*args):
            nonlocal count
            count += 1
            if count == 2: raise S.ArchiveError('simulated interruption between files')
            return original(*args)
        first = self.receipt()
        with patch.object(S.local_guards, 'copy_verified', interrupted), self.assertRaises(S.ArchiveError):
            S.local_archive(plan, first, budget=10 ** 9, reserve=0)
        _, resumed = self.local(plan, resume_from=first)
        self.assertEqual(resumed['reused_files'], 1); self.assertEqual(resumed['copied_files'], 5)

    def test_local_bad_existing_bytes_and_hardlinks_stop(self):
        plan = self.plan(); first, done = self.local(plan); path = Path(done['actual_root']) / plan['files'][0]['relative_path']
        original = path.read_bytes(); path.write_bytes(b'bad')
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=first)
        path.unlink(); os.link(plan['files'][0]['local_path'], path)
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=first)
        self.assertEqual(Path(plan['files'][0]['local_path']).read_bytes(), original)

    def test_local_missing_published_object_is_not_repaired_silently(self):
        plan = self.plan(); first, done = self.local(plan)
        (Path(done['actual_root']) / plan['files'][0]['relative_path']).unlink()
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=first)

    def test_local_partial_or_extra_file_preserved(self):
        plan = self.plan(); first, done = self.local(plan)
        path = Path(done['actual_root']) / '.unfinished.partial'; path.write_bytes(b'incomplete')
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=first)
        self.assertEqual(path.read_bytes(), b'incomplete')

    def test_local_wrong_plan_receipt_and_replaced_root_stop(self):
        plan = self.plan(); first, done = self.local(plan)
        wrong = json.loads(first.read_text()); wrong['plan_sha256'] = '0' * 64; p = self.receipt(); p.write_text(json.dumps(wrong))
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=p)
        root = Path(done['actual_root']); old = root.with_name(root.name + '-old'); root.rename(old); root.mkdir(mode=0o700)
        with self.assertRaises(S.ArchiveError): self.local(plan, resume_from=first)

    def test_local_existing_destination_without_receipt_rejected(self):
        plan = self.plan(); self.local(plan)
        with self.assertRaises(S.ArchiveError): self.local(plan)

    def test_budget_and_shared_lock_stop(self):
        plan = self.plan()
        with self.assertRaises(S.ArchiveError): S.local_archive(plan, self.receipt(), budget=1, reserve=0)
        # A failed first copy leaves its own bound partial directory; another
        # distinct plan checks shared lock before creating further archive data.
        plan['archive_name'] = 'different-pilot'
        with S.local_guards.worker_lock(self.raw), self.assertRaises(S.ArchiveError): self.local(plan)

    def test_output_collision_rejected_before_network(self):
        plan = self.plan(); drive = FakeDrive(); source = Path(plan['files'][0]['local_path']); original = source.read_bytes()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', source, self.raw / 'drive-staging', private_root_confirmed=True, runner=drive)
        self.assertEqual(drive.commands, []); self.assertEqual(source.read_bytes(), original)
        with self.assertRaises(S.ArchiveError): S.local_archive(plan, source, reserve=0)

    def test_drive_complete_and_file_level_resume(self):
        plan = self.plan(); drive = FakeDrive(); first, done = self.upload(plan, drive)
        self.assertEqual(done['uploaded_files'], 6); copies = drive.copies()
        _, resumed = self.upload(plan, drive, resume_from=first)
        self.assertEqual(resumed['uploaded_files'], 0); self.assertEqual(resumed['verified_existing_files'], 6)
        self.assertEqual(drive.copies(), copies)
        self.assertTrue(all(c[0] not in {'delete', 'sync', 'move'} for c in drive.commands))

    def test_drive_unknown_completed_copy_is_reused(self):
        plan = self.plan(); drive = FakeDrive(); drive.fail_copy_after_write = True; first = self.receipt()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', first, self.raw / 'drive-staging', private_root_confirmed=True, runner=drive)
        failed = json.loads(first.read_text()); self.assertTrue(failed['unverified_remote_state_possible'])
        drive.fail_copy_after_write = False
        _, resumed = self.upload(plan, drive, resume_from=first)
        self.assertEqual(resumed['verified_existing_files'], 1); self.assertFalse(resumed['unverified_remote_state_possible'])

    def test_drive_partial_copy_preserved_and_rejected(self):
        plan = self.plan(); drive = FakeDrive(); drive.partial_copy = True; first = self.receipt()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', first, self.raw / 'drive-staging', private_root_confirmed=True, runner=drive)
        before = copy.deepcopy(drive.nodes); drive.partial_copy = False
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)
        self.assertEqual(drive.nodes, before)

    def test_drive_missing_parent_id_stops_before_recreation(self):
        plan = self.plan(); drive = FakeDrive(); first, done = self.upload(plan, drive)
        node_id = next(iter(done['directory_ids'].values())); drive.nodes.pop(node_id)
        before = copy.deepcopy(drive.nodes)
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)
        self.assertEqual(drive.nodes, before)

    def test_drive_duplicate_root_and_intermediate_names_stop(self):
        plan = self.plan(); drive = FakeDrive(); first, done = self.upload(plan, drive)
        drive.add('root', plan['archive_name'], directory=True)
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)
        drive.nodes.pop(next(reversed(drive.nodes)))
        first_prefix = next(iter(done['directory_ids'])); drive.add(done['root_folder_id'], first_prefix, directory=True)
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)

    def test_drive_missing_hash_rejected(self):
        plan = self.plan(); drive = FakeDrive(); first, _ = self.upload(plan, drive)
        next(r for r in drive.nodes.values() if not r['IsDir'])['Hashes'] = {}
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)

    def test_invalid_free_quota_and_no_remote_have_zero_writes(self):
        plan = self.plan()
        for free in [None, True, -1, 0, float('nan')]:
            drive = FakeDrive(); drive.free = free
            with self.subTest(free=free), self.assertRaises(S.ArchiveError): self.upload(plan, drive)
            self.assertFalse(any(c[0] in {'mkdir', 'copyto'} for c in drive.commands))
        drive = FakeDrive(); drive.remotes = ''
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive)
        self.assertFalse(any(c[0] in {'mkdir', 'copyto'} for c in drive.commands))

    def test_uncertain_parent_then_auth_failure_retains_prior_uncertainty(self):
        plan = self.plan(); drive = FakeDrive(); drive.fail_copy_after_write = True; first = self.receipt()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', first, self.raw / 'drive-staging', private_root_confirmed=True, runner=drive)
        drive.fail_auth = True; second = self.receipt()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', second, self.raw / 'drive-staging', resume_from=first, private_root_confirmed=True, runner=drive)
        self.assertTrue(json.loads(second.read_text())['unverified_remote_state_possible'])

    def test_unknown_root_creation_cannot_infer_resume(self):
        plan = self.plan(); drive = FakeDrive(); drive.fail_mkdir_after_write = True; first = self.receipt()
        with self.assertRaises(S.ArchiveError):
            S.upload(plan, 'archive', first, self.raw / 'drive-staging', private_root_confirmed=True, runner=drive)
        self.assertIsNone(json.loads(first.read_text())['root_folder_id'])
        with self.assertRaises(S.ArchiveError): self.upload(plan, drive, resume_from=first)

    def test_remote_lock_prevents_competing_local_writes(self):
        plan = self.plan(); drive = FakeDrive()
        with S.remote_lock('archive', self.private / 'locks'), self.assertRaises(S.ArchiveError): self.upload(plan, drive)
        self.assertEqual(drive.commands, [])


if __name__ == '__main__':
    unittest.main()
