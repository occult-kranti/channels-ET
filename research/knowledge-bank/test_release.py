"""Exercise release guards against cross-edition and coverage corruption."""
import copy
import json
from pathlib import Path
import unittest

from verify_release import full_asr_checks


class FullReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2] / 'dist/knowledge-bank'
        cls.full = json.loads((root / 'asr-full.json').read_text())
        cls.sensitivity = json.loads((root / 'asr-sensitivity.json').read_text())
        cls.analysis = json.loads((root / 'analysis.json').read_text())

    def test_completed_release(self):
        result = full_asr_checks(self.full, self.sensitivity, self.analysis)
        self.assertEqual(result['recordings'], 4)
        self.assertEqual(result['empty_text_chunks'], 2)
        self.assertFalse(result['accuracy_measured'])

    def test_rejects_missing_tail_even_when_summary_is_unchanged(self):
        full = copy.deepcopy(self.full)
        full['documents'][0]['coverage']['covered_samples'] -= 1
        with self.assertRaisesRegex(ValueError, 'sample coverage'):
            full_asr_checks(full, self.sensitivity, self.analysis)

    def test_rejects_same_counts_but_different_transcript_edition(self):
        sensitivity = copy.deepcopy(self.sensitivity)
        sensitivity['records'][0]['new_text_artifact_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'edition mismatch'):
            full_asr_checks(self.full, sensitivity, self.analysis)

    def test_rejects_different_producer_manifest(self):
        sensitivity = copy.deepcopy(self.sensitivity)
        sensitivity['bindings']['new_manifest_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'producer binding'):
            full_asr_checks(self.full, sensitivity, self.analysis)

    def test_rejects_hidden_empty_windows(self):
        full = copy.deepcopy(self.full)
        full['summary']['empty_text_chunks'] = 0
        with self.assertRaisesRegex(ValueError, 'empty_text_chunks'):
            full_asr_checks(full, self.sensitivity, self.analysis)

    def test_rejects_unsupported_accuracy_assertion(self):
        full = copy.deepcopy(self.full)
        full['documents'][0]['accuracy_verified'] = True
        with self.assertRaisesRegex(ValueError, 'accuracy/speaker'):
            full_asr_checks(full, self.sensitivity, self.analysis)


if __name__ == '__main__':
    unittest.main()
