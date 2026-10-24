"""Offline tests only. No real rclone remote, login or upload is used."""
import copy
import hashlib
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

import archive


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        self.raw_patch = patch.object(archive, 'RAW_ROOT', self.raw)
        self.raw_patch.start()
        self.addCleanup(self.raw_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def row(self, name='recording.mp3', data=b'source audio', source_id='upload-01', **updates):
        path = self.raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row = archive.source_row(path, hashlib.sha256(data).hexdigest(), len(data),
                                 'publisher-rss', 'Practitioner', 'Uploader', source_id, 'audio',
                                 {'source_url': 'https://example.org/source'})
        row.update(updates)
        return row

    def plan(self, rows=None):
        return archive.build_plan(rows or [self.row()], self.raw, 'test-archive')

    def test_real_local_hashes_and_size(self):
        plan = self.plan()
        self.assertEqual(plan['canonical_bytes'], 12)
        self.assertEqual(plan['files'][0]['md5'], hashlib.md5(b'source audio').hexdigest())
        self.assertTrue(archive.validate_plan(plan))

    def test_source_hash_mismatch(self):
        row = self.row(sha256='0' * 64)
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            self.plan([row])

    def test_source_size_mismatch(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            self.plan([self.row(bytes=1000)])

    def test_rehash_detects_source_change(self):
        plan = self.plan()
        Path(plan['files'][0]['local_path']).write_bytes(b'changed audio')
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            archive.validate_plan(plan)

    def test_source_root_cannot_be_widened(self):
        plan = self.plan()
        plan['raw_root'] = '/'
        with self.assertRaisesRegex(archive.ArchiveError, 'raw root differs'):
            archive.validate_plan(plan)

    def test_source_outside_root(self):
        path = self.root / 'outside.mp3'
        path.write_bytes(b'outside')
        with self.assertRaisesRegex(archive.ArchiveError, 'outside'):
            archive.hash_source(path, self.raw)

    def test_source_path_traversal(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'traversal'):
            archive.hash_source(self.raw / '../outside', self.raw)

    def test_final_symlink_rejected(self):
        row = self.row()
        (self.raw / 'link.mp3').symlink_to(row['local_path'])
        with self.assertRaisesRegex(archive.ArchiveError, 'Symlink'):
            archive.hash_source(self.raw / 'link.mp3', self.raw)

    def test_intermediate_symlink_rejected(self):
        folder = self.raw / 'real'
        folder.mkdir()
        (folder / 'a.mp3').write_bytes(b'a')
        (self.raw / 'link').symlink_to(folder, target_is_directory=True)
        with self.assertRaisesRegex(archive.ArchiveError, 'Symlink'):
            archive.hash_source(self.raw / 'link/a.mp3', self.raw)

    def test_special_file_rejected(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'regular file'):
            archive.hash_source(self.raw, self.raw)

    def test_identity_traversal_rejected(self):
        for value in ['../account', 'a/b', 'a\\b', '\x01bad']:
            with self.subTest(value=value), self.assertRaises(archive.ArchiveError):
                archive.safe_component(value)

    def test_slug_collisions_keep_distinct_identities(self):
        self.assertNotEqual(archive.safe_component('A B'), archive.safe_component('A-B'))

    def test_exact_same_bytes_dedup_retains_alias(self):
        rows = [self.row('one.mp3'), self.row('two.mp3', source_id='upload-02')]
        plan = self.plan(rows)
        self.assertEqual(plan['canonical_file_count'], 1)
        self.assertEqual(plan['byte_identical_alias_count'], 1)
        self.assertEqual(plan['byte_identical_aliases'][0]['source_id'], 'upload-02')
        self.assertTrue(archive.validate_plan(plan))

    def test_similar_titles_do_not_deduplicate_bytes(self):
        plan = self.plan([self.row('one.mp3', b'one'), self.row('two.mp3', b'two')])
        self.assertEqual(plan['canonical_file_count'], 2)

    def test_destination_collision_rejected(self):
        row = self.row()
        with self.assertRaisesRegex(archive.ArchiveError, 'Duplicate destination'):
            self.plan([row, copy.deepcopy(row)])

    def test_tampered_destination_rejected(self):
        plan = self.plan()
        plan['files'][0]['relative_path'] = '../escape'
        with self.assertRaises(archive.ArchiveError):
            archive.validate_plan(plan)

    def test_tampered_counts_rejected(self):
        plan = self.plan()
        plan['canonical_bytes'] += 1
        with self.assertRaisesRegex(archive.ArchiveError, 'byte total'):
            archive.validate_plan(plan)

    def test_youtube_short_unknown_or_missing_policy_rejected(self):
        base = self.row(provider='youtube', selection_eligible=True, is_short=False,
                        duration_seconds=300, selection_policy_receipt='receipt-sha256')
        for updates in [{'duration_seconds': 299}, {'duration_seconds': None}, {'duration_seconds': float('nan')},
                        {'duration_seconds': float('inf')}, {'duration_seconds': True},
                        {'is_short': True}, {'selection_eligible': False}, {'selection_policy_receipt': None}]:
            with self.subTest(updates=updates), self.assertRaises(archive.ArchiveError):
                self.plan([{**base, **updates}])

    def test_youtube_accepted_only_with_pinned_selected_policy_and_refreshed_metadata(self):
        selected = Path(archive.__file__).parent / 'unused-test-policy'
        # The receipt is mocked at its fixed repository location, never written to a real policy file.
        repo = self.root / 'repo'
        policy = repo / 'research/collection-policy/selected-default.jsonl'
        policy.parent.mkdir(parents=True)
        policy.write_text(json.dumps({'source_id': 'youtube:test-video', 'selected_default': True}) + '\n')
        row = self.row(provider='youtube', source_id='youtube:test-video', selection_eligible=True,
                       is_short=False, duration_seconds=300, metadata_refreshed_at_acquisition=True,
                       selection_policy_receipt={'path': 'research/collection-policy/selected-default.jsonl',
                                                 'sha256': hashlib.sha256(policy.read_bytes()).hexdigest()})
        with patch.object(archive, 'REPO', repo):
            plan = self.plan([row])
            self.assertTrue(archive.validate_plan(plan))
            plan['files'][0]['metadata_refreshed_at_acquisition'] = False
            with self.assertRaisesRegex(archive.ArchiveError, 'refreshed at acquisition'):
                archive.validate_plan(plan)

    def test_alias_local_bytes_rechecked(self):
        plan = self.plan([self.row('one.mp3'), self.row('two.mp3', source_id='upload-02')])
        (self.raw / 'two.mp3').write_bytes(b'changed bytes')
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            archive.validate_plan(plan)

    def test_metadata_staging_contains_no_media(self):
        plan = self.plan()
        stage, files = archive.stage_manifests(plan, self.root / 'staging')
        self.assertEqual(len(files), 3)  # provenance + archive manifest + SHA256SUMS
        self.assertFalse(any(p.suffix == '.mp3' for p in stage.rglob('*')))
        manifest = json.loads((stage / 'manifests/archive-manifest.json').read_text())
        self.assertNotIn('local_path', manifest['files'][0])
        self.assertEqual(archive.stage_manifests(plan, self.root / 'staging')[1], files)

    def test_stage_symlink_rejected_before_write(self):
        plan = self.plan()
        outside = self.root / 'outside'
        outside.mkdir()
        staging = self.root / 'staging'
        staging.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(archive.ArchiveError, 'symlink'):
            archive.stage_manifests(plan, staging)
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_different_staged_metadata_rejected(self):
        plan = self.plan()
        stage, files = archive.stage_manifests(plan, self.root / 'staging')
        Path(files[0]['local_path']).write_text('different')
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            archive.stage_manifests(plan, self.root / 'staging')

    def test_missing_remote_fails_without_network_or_upload(self):
        calls = []
        def fake(args):
            calls.append(args)
            return CompletedProcess(args, 0, '', '')
        with self.assertRaisesRegex(archive.ArchiveError, 'No explicitly selected authorized remote'):
            archive.remote_status('selected_remote', fake)
        self.assertEqual(calls, [['listremotes', '--long']])

    def test_non_drive_alias_rejected(self):
        def fake(args):
            return CompletedProcess(args, 0, 'selected_remote: alias\n', '')
        with self.assertRaisesRegex(archive.ArchiveError, 'direct Google Drive'):
            archive.remote_status('selected_remote', fake)

    def test_remote_selector_cannot_be_path_or_connection_string(self):
        for remote in ['drive:', ':drive:', 'account:folder', '../account']:
            with self.subTest(remote=remote), self.assertRaises(archive.ArchiveError):
                archive.existing_drive_remote(remote, lambda args: self.fail('must not invoke rclone'))

    def test_unknown_auth_error_is_not_treated_as_missing(self):
        def fake(args):
            return CompletedProcess(args, 1, '', 'sensitive error not forwarded')
        with self.assertRaisesRegex(archive.ArchiveError, 'listing failed'):
            archive.remote_listing('fake:path', fake, missing_ok=True)

    def test_remote_duplicate_names_rejected(self):
        def fake(args):
            return CompletedProcess(args, 0, json.dumps([{'Name': 'a'}, {'Name': 'a'}]), '')
        with self.assertRaisesRegex(archive.ArchiveError, 'Duplicate Drive names'):
            archive.remote_listing('fake:path', fake)

    def test_remote_size_hash_collision_rejects_copy(self):
        row = self.plan()['files'][0]
        calls = []
        def fake(args):
            calls.append(args)
            return CompletedProcess(args, 0, json.dumps([{'Name': 'recording.mp3', 'Size': row['bytes'],
                                                          'Hashes': {'MD5': '0' * 32}, 'IsDir': False}]), '')
        with self.assertRaisesRegex(archive.ArchiveError, 'no overwrite'):
            archive.transfer_one(row, self.raw, 'selected_remote:path/recording.mp3', fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'lsjson')

    def test_verified_existing_bytes_skip_copy(self):
        row = self.plan()['files'][0]
        def fake(args):
            self.assertEqual(args[0], 'lsjson')
            return CompletedProcess(args, 0, json.dumps([{'Name': 'recording.mp3', 'Size': row['bytes'],
                                                          'Hashes': {'MD5': row['md5']}, 'IsDir': False}]), '')
        self.assertEqual(archive.transfer_one(row, self.raw, 'selected_remote:path/recording.mp3', fake),
                         'verified_existing')

    def test_copy_is_immutable_and_post_verified(self):
        row = self.plan()['files'][0]
        calls = []
        def fake(args):
            calls.append(args)
            if len(calls) == 1:
                return CompletedProcess(args, 3, '', '')
            if args[0] == 'copyto':
                self.assertIn('--immutable', args)
                self.assertIn('--checksum', args)
                self.assertIn('--drive-team-drive=', args)
                return CompletedProcess(args, 0, '', '')
            return CompletedProcess(args, 0, json.dumps([{'Name': 'recording.mp3', 'Size': row['bytes'],
                                                          'Hashes': {'MD5': row['md5']}, 'IsDir': False}]), '')
        self.assertEqual(archive.transfer_one(row, self.raw, 'selected_remote:path/recording.mp3', fake),
                         'uploaded_size_md5_verified')
        self.assertEqual([c[0] for c in calls], ['lsjson', 'copyto', 'lsjson'])

    def test_post_copy_missing_hash_fails(self):
        row = self.plan()['files'][0]
        calls = []
        def fake(args):
            calls.append(args)
            if len(calls) == 1:
                return CompletedProcess(args, 3, '', '')
            if args[0] == 'copyto':
                return CompletedProcess(args, 0, '', '')
            return CompletedProcess(args, 0, json.dumps([{'Name': 'recording.mp3', 'Size': row['bytes'],
                                                          'Hashes': {}, 'IsDir': False}]), '')
        with self.assertRaisesRegex(archive.ArchiveError, 'unavailable size/MD5'):
            archive.transfer_one(row, self.raw, 'selected_remote:path/recording.mp3', fake)

    def test_missing_private_destination_confirmation_prevents_all_calls(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'Explicit confirmation'):
            archive.upload(self.plan(), 'selected_remote', self.root / 'stage', False,
                           lambda args: self.fail('must not invoke rclone'))

    def test_receipt_cannot_overwrite_source_before_any_remote_call(self):
        plan = self.plan()
        source = Path(plan['files'][0]['local_path'])
        original = source.read_bytes()
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), source)
        self.assertEqual(source.read_bytes(), original)

    def test_receipt_cannot_overwrite_existing_unrelated_file(self):
        plan = self.plan()
        unrelated = self.root / 'unrelated.json'
        unrelated.write_bytes(b'original unrelated bytes')
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), unrelated)
        self.assertEqual(unrelated.read_bytes(), b'original unrelated bytes')

    def test_receipt_final_symlink_cannot_overwrite_target(self):
        plan = self.plan()
        source = Path(plan['files'][0]['local_path'])
        original = source.read_bytes()
        link = self.root / 'receipt-link.json'
        link.symlink_to(source)
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), link)
        self.assertTrue(link.is_symlink())
        self.assertEqual(source.read_bytes(), original)

    def test_receipt_dangling_symlink_is_not_an_absent_output(self):
        link = self.root / 'receipt-link.json'
        target = self.root / 'missing.json'
        link.symlink_to(target)
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.OwnedJsonOutput(link, 'receipt')
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_receipt_parent_symlink_rejected_before_any_write_or_remote_call(self):
        plan = self.plan()
        outside = self.root / 'outside'
        outside.mkdir()
        linked_parent = self.root / 'linked-parent'
        linked_parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(archive.ArchiveError, 'Output parent'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), linked_parent / 'receipt.json')
        self.assertEqual(list(outside.iterdir()), [])

    def test_receipt_new_raw_source_tree_path_rejected(self):
        plan = self.plan()
        target = self.raw / 'publisher-audio/new-receipt.json'
        with self.assertRaisesRegex(archive.ArchiveError, 'source raw tree'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), target)
        self.assertFalse(target.parent.exists())

    def test_receipt_staging_overlap_rejected_before_any_write(self):
        plan = self.plan()
        stage_root = self.root / 'stage'
        with self.assertRaisesRegex(archive.ArchiveError, 'overlap staging'):
            archive.upload(plan, 'selected_remote', stage_root, True,
                           lambda args: self.fail('no rclone command is permitted'), stage_root / 'receipt.json')
        self.assertFalse(stage_root.exists())

    def test_receipt_parent_of_staging_cannot_become_an_output_file(self):
        plan = self.plan()
        target = self.root / 'stage-parent'
        with self.assertRaisesRegex(archive.ArchiveError, 'overlap staging'):
            archive.upload(plan, 'selected_remote', target / 'child', True,
                           lambda args: self.fail('no rclone command is permitted'), target)
        self.assertFalse(target.exists())

    def test_existing_source_hardlink_is_not_a_new_output(self):
        plan = self.plan()
        source = Path(plan['files'][0]['local_path'])
        hardlink = self.root / 'receipt-hardlink.json'
        os.link(source, hardlink)
        original = source.read_bytes()
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'), hardlink)
        self.assertEqual(source.read_bytes(), original)

    def test_dedicated_raw_receipt_directory_is_supported_without_auth(self):
        plan = self.plan()
        receipt = self.raw / 'drive-receipts/test-archive/receipt.json'
        calls = []
        def missing_remote(args):
            calls.append(args)
            return CompletedProcess(args, 0, '', '')
        with self.assertRaisesRegex(archive.ArchiveError, 'No explicitly selected authorized remote'):
            archive.upload(plan, 'selected_remote', self.raw / 'drive-staging', True, missing_remote, receipt)
        self.assertEqual(calls, [['listremotes', '--long']])
        recorded = json.loads(receipt.read_text())
        self.assertEqual(recorded['uploaded_files'], 0)
        self.assertFalse(recorded['folder_creation_attempted'])
        self.assertEqual(recorded['status'], 'failed_no_rollback')
        self.assertFalse((self.raw / 'drive-staging').exists())

    def test_receipt_output_is_required_before_any_remote_call(self):
        with self.assertRaisesRegex(archive.ArchiveError, 'receipt output is required'):
            archive.upload(self.plan(), 'selected_remote', self.root / 'stage', True,
                           lambda args: self.fail('no rclone command is permitted'))

    def test_stage_raw_source_tree_overlap_rejected_before_any_write(self):
        plan = self.plan()
        with self.assertRaisesRegex(archive.ArchiveError, 'dedicated drive-staging'):
            archive.upload(plan, 'selected_remote', self.raw, True,
                           lambda args: self.fail('no rclone command is permitted'), self.root / 'receipt.json')
        self.assertFalse((self.root / 'receipt.json').exists())

    def test_stage_receipt_tree_overlap_rejected(self):
        with self.assertRaises(archive.ArchiveError):
            archive.stage_manifests(self.plan(), self.raw / 'drive-receipts')
        self.assertFalse((self.raw / 'drive-receipts').exists())

    def test_plan_output_cannot_overwrite_source_or_existing_file(self):
        plan = self.plan()
        for target in [Path(plan['files'][0]['local_path']), self.root / 'existing.json']:
            if not target.exists():
                target.write_bytes(b'original unrelated bytes')
            original = target.read_bytes()
            with self.subTest(target=target), patch.object(archive, 'collect_existing',
                                                          side_effect=AssertionError('must fail before collection')):
                self.assertEqual(archive.main(['plan', '--output', str(target)]), 2)
            self.assertEqual(target.read_bytes(), original)

    def test_plan_output_new_raw_path_rejected(self):
        target = self.raw / 'drive-receipts/not-a-receipt.json'
        with patch.object(archive, 'collect_existing', side_effect=AssertionError('must fail before collection')):
            self.assertEqual(archive.main(['plan', '--output', str(target)]), 2)
        self.assertFalse(target.parent.exists())

    def test_new_plan_output_is_exclusive(self):
        path = self.root / 'plans/new-plan.json'
        archive.write_new_json(path, {'first': True})
        before = path.read_bytes()
        with self.assertRaisesRegex(archive.ArchiveError, 'Output already exists'):
            archive.write_new_json(path, {'second': True})
        self.assertEqual(path.read_bytes(), before)

    def test_owned_receipt_updates_atomically_replace_only_owned_inode(self):
        path = self.root / 'receipt.json'
        with archive.OwnedJsonOutput(path, 'receipt') as output:
            output.update({'first': True})
            first_inode = path.stat().st_ino
            output.update({'second': True})
            self.assertNotEqual(path.stat().st_ino, first_inode)
            self.assertEqual(json.loads(path.read_text()), {'second': True})
        self.assertEqual(list(self.root.glob('.drive-archive-output-*.tmp')), [])

    def test_owned_receipt_replaced_by_symlink_is_never_followed_or_overwritten(self):
        path = self.root / 'receipt.json'
        target = self.root / 'unrelated.json'
        target.write_bytes(b'unrelated original bytes')
        with archive.OwnedJsonOutput(path, 'receipt') as output:
            output.update({'first': True})
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(archive.ArchiveError, 'replaced, symlinked or hardlinked'):
                output.update({'second': True})
        self.assertTrue(path.is_symlink())
        self.assertEqual(target.read_bytes(), b'unrelated original bytes')

    def test_owned_receipt_replaced_by_unrelated_regular_file_is_never_overwritten(self):
        path = self.root / 'receipt.json'
        replacement = self.root / 'replacement.json'
        replacement.write_bytes(b'unrelated replacement bytes')
        with archive.OwnedJsonOutput(path, 'receipt') as output:
            output.update({'first': True})
            os.replace(replacement, path)
            with self.assertRaisesRegex(archive.ArchiveError, 'replaced, symlinked or hardlinked'):
                output.update({'second': True})
        self.assertEqual(path.read_bytes(), b'unrelated replacement bytes')

    def test_owned_receipt_new_hardlink_prevents_update(self):
        path = self.root / 'receipt.json'
        linked = self.root / 'linked.json'
        with archive.OwnedJsonOutput(path, 'receipt') as output:
            output.update({'first': True})
            os.link(path, linked)
            original = linked.read_bytes()
            with self.assertRaisesRegex(archive.ArchiveError, 'hardlinked'):
                output.update({'second': True})
        self.assertEqual(linked.read_bytes(), original)
        self.assertEqual(path.read_bytes(), original)

    def upload_fake(self, mode='success'):
        plan = self.plan()
        calls, remote_files = [], {}
        def fake(args):
            calls.append(args)
            cmd = args[0]
            if cmd == 'listremotes':
                return CompletedProcess(args, 0, 'selected_remote: drive\n', '')
            if cmd == 'about':
                quota = {} if mode == 'unknown-quota' else {'free': 10_000_000, 'total': 5_000_000_000_000}
                return CompletedProcess(args, 0, json.dumps(quota), '')
            if cmd == 'mkdir':
                return CompletedProcess(args, 1 if mode == 'mkdir-error' else 0, '', '')
            if cmd == 'copyto':
                if mode == 'copy-error':
                    return CompletedProcess(args, 1, '', '')
                p = Path(args[1])
                remote_files[args[2]] = {'Name': args[2].rsplit('/', 1)[1], 'IsDir': False,
                                       'Size': p.stat().st_size,
                                       'Hashes': {'MD5': hashlib.md5(p.read_bytes()).hexdigest()}}
                return CompletedProcess(args, 0, '', '')
            if cmd == 'lsjson':
                if args[1] == 'selected_remote:':
                    rows = [{'Name': 'test-archive', 'IsDir': True}] if mode == 'existing-root' else []
                else:
                    rows = [row for path, row in remote_files.items() if path.rsplit('/', 1)[0] == args[1]]
                return CompletedProcess(args, 0, json.dumps(rows), '')
            self.fail('Unexpected command ' + cmd)
        receipt = self.root / 'upload-receipt.json'
        return plan, fake, receipt, calls

    def test_full_mock_upload_has_four_verified_files_and_no_sharing_or_deletes(self):
        plan, fake, receipt_path, calls = self.upload_fake()
        receipt = archive.upload(plan, 'selected_remote', self.root / 'stage', True, fake, receipt_path)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['uploaded_files'], 4)
        self.assertEqual(receipt['attempted_files'], 4)
        self.assertFalse(receipt['effective_acl_verified'])
        self.assertFalse(receipt['unverified_remote_state_possible'])
        self.assertEqual(set(c[0] for c in calls), {'listremotes', 'about', 'lsjson', 'mkdir', 'copyto'})
        self.assertEqual(json.loads(receipt_path.read_text()), receipt)

    def test_unknown_quota_prevents_remote_folder_creation(self):
        plan, fake, receipt_path, calls = self.upload_fake('unknown-quota')
        with self.assertRaisesRegex(archive.ArchiveError, 'quota is unknown'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True, fake, receipt_path)
        self.assertNotIn('mkdir', [c[0] for c in calls])

    def test_existing_archive_never_merged_or_overwritten(self):
        plan, fake, receipt_path, calls = self.upload_fake('existing-root')
        with self.assertRaisesRegex(archive.ArchiveError, 'root already exists'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True, fake, receipt_path)
        self.assertNotIn('mkdir', [c[0] for c in calls])
        self.assertNotIn('copyto', [c[0] for c in calls])

    def test_failed_mkdir_receipt_retains_uncertain_remote_state(self):
        plan, fake, receipt_path, calls = self.upload_fake('mkdir-error')
        with self.assertRaisesRegex(archive.ArchiveError, 'mkdir failed'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True, fake, receipt_path)
        receipt = json.loads(receipt_path.read_text())
        self.assertTrue(receipt['folder_creation_attempted'])
        self.assertFalse(receipt['drive_folder_created'])
        self.assertTrue(receipt['unverified_remote_state_possible'])
        self.assertEqual(receipt['status'], 'failed_no_rollback')

    def test_failed_copy_receipt_retains_uncertain_remote_state(self):
        plan, fake, receipt_path, calls = self.upload_fake('copy-error')
        with self.assertRaisesRegex(archive.ArchiveError, 'copy failed'):
            archive.upload(plan, 'selected_remote', self.root / 'stage', True, fake, receipt_path)
        receipt = json.loads(receipt_path.read_text())
        self.assertTrue(receipt['drive_folder_created'])
        self.assertEqual(receipt['uploaded_files'], 0)
        self.assertEqual(receipt['attempted_files'], 1)
        self.assertTrue(receipt['unverified_remote_state_possible'])
        self.assertEqual(receipt['records'][0]['status'], 'attempt_started_remote_state_unknown')


if __name__ == '__main__':
    unittest.main()
