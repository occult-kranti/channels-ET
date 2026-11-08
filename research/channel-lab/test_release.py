"""Public-boundary tests; numerical tests belong to each producing module."""
import json
from pathlib import Path
import tempfile
import unittest
import hashlib
import copy

from build_public import safe_path, inspect_public_json
from verify_release import publication_checks, batch_checks, cross_bindings


class PublicBoundaryTests(unittest.TestCase):
    def test_nested_public_path(self):
        root = Path('/tmp/example-release')
        self.assertEqual(safe_path(root, 'details/recording-1.json'), root / 'details/recording-1.json')

    def test_rejects_path_traversal_and_external_paths(self):
        root = Path('/tmp/example-release')
        for path in ('../secret.json', '/workspace/secret.json', 'https://example.org/a', 'a\\b'):
            with self.subTest(path=path), self.assertRaises(ValueError): safe_path(root, path)

    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'release'; root.mkdir()
            (root / 'outside').symlink_to(Path(tmp), target_is_directory=True)
            with self.assertRaises(ValueError): safe_path(root, 'outside/source.json')

    def test_accepts_bounded_paraphrase_and_public_hash(self):
        value = {'paraphrase': 'The source describes preparation as conditional.', 'body_sha256': '0' * 64}
        self.assertEqual(inspect_public_json(json.dumps(value).encode()), value)

    def test_rejects_nested_raw_body(self):
        with self.assertRaises(ValueError):
            inspect_public_json(b'{"records":[{"source_body":"unreleased full source"}]}')

    def test_rejects_private_paths(self):
        with self.assertRaises(ValueError):
            inspect_public_json(b'{"url":"/workspace/channels-et-private/source.json"}')

    def test_missing_numbers_must_be_null_in_json(self):
        self.assertEqual(inspect_public_json(b'{"similarity":null}'), {'similarity': None})
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            inspect_public_json(b'{"similarity":NaN}')

    def test_unlisted_stale_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); modules = {}; artifacts = []
            for key in ('registry', 'coverage', 'analysis', 'batch_asr', 'readings', 'asr_effects'):
                raw = b'{"scope":"isolated publication-boundary test fixture"}'
                name = key + '.json'; (root / name).write_bytes(raw)
                ref = {'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                modules[key] = ref; artifacts.append(ref)
            for name in ('index.html', 'app.js', 'styles.css'): (root / name).write_text('test')
            (root / 'manifest.json').write_text(json.dumps({'modules': modules, 'artifacts': artifacts}))
            publication_checks(root)
            (root / 'old-unlisted-data.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'unexpected'):
                publication_checks(root)


class ExecutedReleaseRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2] / 'dist/channel-lab'
        cls.manifest = json.loads((root / 'manifest.json').read_text())
        cls.modules = {key: json.loads((root / ref['file']).read_text())
                       for key, ref in cls.manifest['modules'].items()}

    def test_executed_batch_and_bindings_pass(self):
        self.assertEqual(batch_checks(self.modules['batch_asr'], self.modules['registry'])['windows'], 269)
        self.assertEqual(cross_bindings(self.manifest, self.modules)['paired_editions'], 9)

    def test_missing_last_audio_window_is_rejected(self):
        batch = copy.deepcopy(self.modules['batch_asr'])
        batch['records'][0]['timeline'].pop()
        with self.assertRaisesRegex(ValueError, 'window count'):
            batch_checks(batch, self.modules['registry'])

    def test_gap_preserving_aggregate_duration_is_rejected(self):
        batch = copy.deepcopy(self.modules['batch_asr'])
        batch['records'][0]['timeline'][1]['start_seconds'] += 0.1
        with self.assertRaisesRegex(ValueError, 'gap or overlap'):
            batch_checks(batch, self.modules['registry'])

    def test_sensitivity_bound_to_different_edition_is_rejected(self):
        modules = copy.deepcopy(self.modules)
        modules['asr_effects']['pairs'][0]['new_asr_artifact_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'transcript artifact'):
            cross_bindings(self.manifest, modules)

    def test_same_count_different_frame_is_rejected(self):
        modules = copy.deepcopy(self.modules)
        modules['asr_effects']['bindings']['frame_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'canonical frame'):
            cross_bindings(self.manifest, modules)


if __name__ == '__main__': unittest.main()
