"""Synthetic publication-boundary tests; no acquisition or real ASR is performed.

Only the upstream media decoder is substituted. Receipt, text, file and archive
hashes remain real temporary-fixture hashes. These fixtures are never released.
"""
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load('publication_boundary_under_test', HERE / 'build_public.py')
T = load('synthetic_analysis_fixture_for_publication', HERE / 'test_analyze.py')


class PublicBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture_owner = T.AnalysisTests()
        self.fixture_owner.setUp()
        self.root = self.fixture_owner.root
        self.fixture = self.fixture_owner.fixture()
        # This tests the publication boundary after the trusted media validator,
        # not whether synthetic bytes can pass the acquisition decoder.
        f = self.fixture
        source = f['receipt']['binding']['source']
        source.pop('fixture_only')
        source['source_url'] = 'https://publisher.example/library/recording'
        source['published_date'] = '2012-10-06'
        proof = json.loads(f['proof_path'].read_text())
        proof.pop('fixture_only')
        self.fixture_owner.write(f['proof_path'], proof)
        source['verification_receipt']['sha256'] = B.sha(f['proof_path'])
        self.fixture_owner.refresh_receipt(f)
        self.source = copy.deepcopy(source)
        self.media = self.root / 'media.json'
        self.selection = self.root / 'selection.json'
        self.access = self.root / 'access.json'
        self.fixture_owner.write(self.media, {'schema_version': 1, 'records': [self.source]})
        self.fixture_owner.write(self.selection, {'summary': {'unique_proposed_uploads': 2, 'proposed_context_video_associations': 2}})
        self.fixture_owner.write(self.access, {'watch_probe_status': 'not_probed_synthetic_fixture', 'stage': 'offline-test',
            'transport_diagnostic': {'connect_code': 0}, 'youtube_origin_response_received': False,
            'checked_at': '2026-11-07T00:00:00+00:00', 'root_cause': 'Synthetic offline diagnostic only'})
        self.ledger = self.root / 'ledger.sqlite'
        with sqlite3.connect(self.ledger) as db:
            db.executescript('CREATE TABLE artifacts(source_id TEXT, kind TEXT, status TEXT); CREATE TABLE bashar_slots(source_id TEXT); CREATE TABLE jobs(attempts INTEGER); INSERT INTO jobs VALUES (0);')
        self.args = types.SimpleNamespace(selection=self.selection, access=self.access, media_input=self.media,
            asr_run=[f['run_path']], youtube_ledger=self.ledger, archive_receipt=None, output=self.root / 'public.json')
        original_spec = importlib.util.spec_from_file_location

        class AudioLoader:
            def create_module(self, spec):
                return None

            def exec_module(self, module):
                original_spec(module.__name__, HERE / 'audio.py').loader.exec_module(module)
                module.validate_record = lambda raw: (raw, {'duration_seconds': raw['duration_seconds']})

        def fixture_spec(name, path, *args, **kwargs):
            if Path(path).name == 'audio.py':
                return importlib.machinery.ModuleSpec(name, AudioLoader())
            return original_spec(name, path, *args, **kwargs)

        self.patcher = patch.object(B.importlib.util, 'spec_from_file_location', side_effect=fixture_spec)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.fixture_owner.tearDown()

    def refresh_receipt_only(self):
        f = self.fixture
        self.fixture_owner.write(f['receipt_path'], f['receipt'])
        f['run']['records'][0]['receipt_sha256'] = B.sha(f['receipt_path'])
        self.fixture_owner.write(f['run_path'], f['run'])

    def archive(self):
        root = self.root / 'archive'
        root.mkdir(mode=0o700)
        records = []
        for i, artifact in enumerate(self.fixture['receipt']['verified_artifacts']):
            name = f'{i}-{Path(artifact["local_path"]).name}'
            shutil.copyfile(artifact['local_path'], root / name)
            records.append({'relative_path': name, 'bytes': artifact['bytes'], 'sha256': artifact['sha256'],
                            'md5': hashlib.md5((root / name).read_bytes(), usedforsecurity=False).hexdigest(),
                            'status': 'independent_copy_hash_verified', 'storage_mode': 'copy'})
        receipt = self.root / 'archive-receipt.json'
        self.fixture_owner.write(receipt, {'schema_version': 1, 'kind': 'batch-local-archive',
            'status': 'completed', 'exact_file_set_verified': True, 'mode': 'copy',
            'actual_root': str(root), 'records': records, 'verified_bytes': sum(r['bytes'] for r in records),
            'root_identity': [root.stat().st_dev, root.stat().st_ino]})
        self.args.archive_receipt = receipt
        return root, records

    def test_valid_chain_counts_one_source(self):
        result = B.build(self.args)
        self.assertEqual(result['execution']['independentCreatorVideos'], 1)
        self.assertEqual(result['execution']['asrCompletedSources'], 1)

    def test_failed_receipt_cannot_be_promoted_by_completed_run(self):
        self.fixture['receipt']['status'] = 'failed'
        self.refresh_receipt_only()
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_processing_binding_hash_is_checked(self):
        self.fixture['receipt']['binding_sha256'] = '0' * 64
        self.refresh_receipt_only()
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_artifact_for_other_source_is_rejected(self):
        self.fixture['receipt']['verified_artifacts'][-1]['source_id'] = 'fixture:other'
        self.refresh_receipt_only()
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_one_media_file_cannot_count_as_two_recordings(self):
        second = dict(self.source, source_id='fixture:other')
        self.fixture_owner.write(self.media, {'schema_version': 1, 'records': [self.source, second]})
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_source_url_and_metrics_do_not_leak_private_values(self):
        self.source['source_url'] = 'https://user:PRIVATE_PASSWORD@publisher.example/library?token=PRIVATE_TOKEN#PRIVATE_FRAGMENT'
        self.fixture_owner.write(self.media, {'schema_version': 1, 'records': [self.source]})
        self.fixture['receipt']['audio_metrics'] = {'rms_dbfs': -20.0, 'private_note': 'PRIVATE_TRANSCRIPT_FRAGMENT'}
        self.refresh_receipt_only()
        value = B.build(self.args)
        self.assertNotIn('PRIVATE_', json.dumps(value))

    def test_timing_repair_metadata_is_preserved_after_real_analysis_validation(self):
        self.fixture['receipt']['asr'].update(
            timestamp_policy='terminal_end_clipped_to_decoded_duration',
            timestamp_anomaly_count=1, timestamp_repaired_segment_count=1,
            timestamp_maximum_adjustment_seconds=7.3646875,
            text_changed_by_repair=False, terminal_text_alignment_unverified=True)
        self.refresh_receipt_only()
        value = B.build(self.args)
        timing = value['records'][0]['asr']['timingQuality']
        self.assertEqual(timing['timestamp_repaired_segment_count'], 1)
        self.assertAlmostEqual(timing['timestamp_maximum_adjustment_seconds'], 7.3646875)
        self.assertFalse(timing['text_changed_by_repair'])
        self.assertTrue(timing['terminal_text_alignment_unverified'])
        self.assertEqual(timing['status'], 'reported_by_processing_receipt')

    def test_verified_archive_requires_existing_exact_files(self):
        root, records = self.archive()
        (root / records[0]['relative_path']).unlink()
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_verified_archive_positive_control(self):
        self.archive()
        value = B.build(self.args)
        self.assertEqual(value['archive']['status'], 'completed')

    def test_verified_archive_requires_current_file_hashes(self):
        root, records = self.archive()
        target = root / records[0]['relative_path']
        target.write_bytes(b'X' * target.stat().st_size)
        with self.assertRaises(ValueError):
            B.build(self.args)

    def test_verified_archive_rejects_unlisted_extra_file(self):
        root, _ = self.archive()
        (root / 'unexpected.txt').write_text('not in the receipt')
        with self.assertRaises(ValueError):
            B.build(self.args)


if __name__ == '__main__':
    unittest.main()
