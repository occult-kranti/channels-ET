"""Regression checks for publication boundaries and exact static artifact sets."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sqlite3
import copy

from build_public import MODULES, REQUIRED, inspect_public_json, inspect_public_sqlite, safe_path
from verify_release import publication_checks, source_checks, cross_bindings


class ReleaseBoundaryTests(unittest.TestCase):
    def test_paths_cannot_escape(self):
        root = Path('/tmp/knowledge-test')
        for name in ('../private.json', '/tmp/private.json', 'https://example.org/a', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError): safe_path(root, name)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'public'; root.mkdir(); (root / 'elsewhere').symlink_to(Path(tmp))
            with self.assertRaises(ValueError): safe_path(root, 'elsewhere/source.json')

    def test_raw_private_evidence_rejected(self):
        for value in ({'raw_answer': 'private body'}, {'rows': [{'evidence_text': 'private body'}]},
                      {'source': '/workspace/channels-et-private/transcript.json'}, {'value': float('nan')}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspect_public_json(json.dumps(value).encode())

    def test_scoped_paraphrase_and_null_are_accepted(self):
        value = {'paraphrase': 'The bounded passage distinguishes preparation from certainty.',
                 'speaker_identity_verified': False, 'answer': None}
        self.assertEqual(inspect_public_json(json.dumps(value).encode()), value)

    def test_private_database_filename_rejected(self):
        with self.assertRaisesRegex(ValueError, 'declared public'):
            inspect_public_sqlite(Path('/tmp/database-private.sqlite'))

    def test_renamed_private_body_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'database-public.sqlite'
            with sqlite3.connect(path) as con:
                con.executescript('CREATE TABLE sources(body TEXT);CREATE TABLE records(question_text TEXT);'
                                  'CREATE TABLE evidence(text TEXT);CREATE TABLE public_search(text TEXT);'
                                  "INSERT INTO sources VALUES('unreleased transcript body');")
            with self.assertRaisesRegex(ValueError, 'Raw evidence'):
                inspect_public_sqlite(path)

    def make_release(self, root):
        artifacts = []; modules = {}
        for file, key in MODULES.items():
            if key not in REQUIRED: continue
            raw = b'{"scope":"isolated publication-boundary fixture"}'
            (root / file).write_bytes(raw)
            ref = {'file': file, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            artifacts.append(ref); modules[key] = ref
        for file in ('index.html', 'app.js', 'styles.css', 'vendor/minisearch.js'):
            p = root / file; p.parent.mkdir(exist_ok=True); p.write_bytes(b'fixture')
            artifacts.append({'file': file, 'bytes': 7, 'sha256': hashlib.sha256(b'fixture').hexdigest()})
        manifest = {'schema_version': 1, 'modules': modules, 'artifacts': artifacts}
        (root / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_unlisted_stale_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_release(root); publication_checks(root)
            (root / 'old-evidence.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'unexpected'): publication_checks(root)

    def test_changed_ui_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_release(root); (root / 'app.js').write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'bytes/hash'): publication_checks(root)

    def test_missing_promised_module_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = self.make_release(root); del manifest['modules']['curated']
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'modules missing'): publication_checks(root)


class ExecutedJoinRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2] / 'dist/transcript-knowledge'
        cls.manifest = json.loads((cls.root / 'manifest.json').read_text())
        cls.modules = {key: json.loads((cls.root / ref['file']).read_text())
                       for key, ref in cls.manifest['modules'].items()}
        raw = (cls.root.parent / 'channel-lab/registry.json').read_bytes()
        cls.registry = json.loads(raw); cls.registry_hash = hashlib.sha256(raw).hexdigest()

    def test_actual_canonical_joins_pass(self):
        self.assertEqual(source_checks(self.modules['profiles'], self.registry, self.registry_hash)['source_profiles'], 493)
        self.assertEqual(cross_bindings(self.root, self.manifest, self.modules, self.registry)['database_record_ids'], 9424)

    def test_same_count_wrong_source_edition_rejected(self):
        profiles = copy.deepcopy(self.modules['profiles'])
        profiles['profiles'][0]['body_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Canonical profile field'):
            source_checks(profiles, self.registry, self.registry_hash)

    def test_database_bound_to_different_curated_version_rejected(self):
        modules = copy.deepcopy(self.modules)
        modules['database']['bindings']['curated']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Downstream annotation binding'):
            cross_bindings(self.root, self.manifest, modules, self.registry)

    def test_retrieval_frame_swap_rejected(self):
        modules = copy.deepcopy(self.modules)
        modules['retrieval']['bindings']['frame']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Downstream canonical input'):
            cross_bindings(self.root, self.manifest, modules, self.registry)


if __name__ == '__main__': unittest.main()
