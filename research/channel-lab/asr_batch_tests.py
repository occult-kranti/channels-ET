#!/usr/bin/env python3
"""Focused boundary, cache, atomic-finalization and owned-process regressions."""
import copy
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock
import wave

import asr_batch as B
import asr_batch_worker as W


def sleeper():
    time.sleep(30)


class BatchTests(unittest.TestCase):
    def fixture(self):
        source = {'source_id': 'test:one', 'publication_id': 'pub:one', 'recording_id': 'audio-sha256:source',
                  'audio_artifact': {'path': '/example/source', 'bytes': 4, 'sha256': 'source'},
                  'canonical_s16_pcm': {'sample_count': 4}, 'planned_chunks': 2,
                  'worker_sha256': 'worker', 'model_revision': 'revision'}
        def chunk(start, text):
            return {'status': 'completed', 'edition_id': 'edition', 'protocol_sha256': 'protocol',
                    'source_id': source['source_id'], 'source_audio_sha256': 'source', 'speaker_role': 'unknown',
                    'worker_script_sha256': 'worker', 'model_revision': 'revision', 'encoder_exhausted': True,
                    'start_sample': start, 'end_sample': start+2, 'words': 1, 'text': text,
                    'generation_frame_durations': [[1]], 'encoder_frame_advances': [1],
                    'encoder_valid_frames': [1], 'token_ids': [[2]], 'job_id': f'chunk-{start:012d}',
                    's16_sha256': f'pcm{start}'}
        return source, [chunk(0, 'one'), chunk(2, 'two')]

    def test_raw_duration_evidence_must_not_be_empty_or_mismatched(self):
        source, values = self.fixture()
        B.validate_chunk(values[0], source, 'edition', 'protocol')
        for field, replacement in [('encoder_valid_frames', []), ('token_ids', [[]]),
                                   ('generation_frame_durations', [[]]), ('encoder_frame_advances', []),
                                   ('generation_frame_durations', [[-1]])]:
            value = copy.deepcopy(values[0]); value[field] = replacement
            with self.assertRaises(ValueError):
                B.validate_chunk(value, source, 'edition', 'protocol')

    def test_cache_binds_model_worker_protocol_and_pcm(self):
        source, values = self.fixture()
        for field in ['model_revision', 'worker_script_sha256', 'protocol_sha256', 'source_audio_sha256']:
            value = copy.deepcopy(values[0]); value[field] = 'changed'
            with self.assertRaises(ValueError):
                B.validate_chunk(value, source, 'edition', 'protocol')
        expected = {k: values[0][k] for k in ['job_id', 'start_sample', 'end_sample', 's16_sha256']}
        expected['s16_sha256'] = 'changed'
        with self.assertRaises(ValueError):
            B.validate_chunk(values[0], source, 'edition', 'protocol', expected)

    def test_exact_partial_tail_and_decode_hash(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            path = Path(tmp)/'source.wav'; raw = b'\x00\x00'*480001
            with wave.open(str(path), 'wb') as f:
                f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(raw)
            source = {'audio_artifact': {'path': str(path)}, 'canonical_s16_pcm':
                      {'sample_count': 480001, 'sha256': hashlib.sha256(raw).hexdigest()}}
            rows = list(B.pcm_windows(source, lambda: None))
            self.assertEqual([(start, len(x)//2) for start, x in rows], [(0, 480000), (480000, 1)])
            source['canonical_s16_pcm']['sha256'] = 'wrong'
            with self.assertRaises(ValueError):
                list(B.pcm_windows(source, lambda: None))

    def test_finalize_interruption_preserves_staging_and_can_resume(self):
        source, values = self.fixture()
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            root = Path(tmp); private = root/'private'; private.mkdir(); ram = root/'ram'
            for value in values:
                W.atomic(ram/'cache/edition'/(value['job_id']+'.json'), value)
            original = B.shutil.copyfile; calls = []
            def interrupted(a, b):
                calls.append(a)
                if len(calls) == 2:
                    raise OSError('simulated copy interruption')
                return original(a, b)
            with mock.patch.object(B, 'PRIVATE', private), mock.patch.object(B, 'RAM', ram):
                with mock.patch.object(B.shutil, 'copyfile', side_effect=interrupted):
                    with self.assertRaises(OSError):
                        B.finalize(source, 'edition', 'protocol', {}, {'repo': 'm', 'revision': 'revision'}, {})
                self.assertFalse((private/'editions/edition').exists())
                self.assertEqual(len(list((private/'editions').glob('*.pending-*'))), 1)
                receipt = B.finalize(source, 'edition', 'protocol', {}, {'repo': 'm', 'revision': 'revision'}, {})
                self.assertEqual(receipt['coverage']['covered_samples'], 4)
                self.assertEqual(B.verify_edition(private/'editions/edition/receipt.json', source,
                                                 'edition', 'protocol')['edition_id'], 'edition')

    def test_completed_normalized_turns_are_not_trusted(self):
        source, values = self.fixture()
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            root = Path(tmp); private = root/'private'; private.mkdir(); ram = root/'ram'
            for value in values:
                W.atomic(ram/'cache/edition'/(value['job_id']+'.json'), value)
            with mock.patch.object(B, 'PRIVATE', private), mock.patch.object(B, 'RAM', ram):
                B.finalize(source, 'edition', 'protocol', {}, {'repo': 'm', 'revision': 'revision'}, {})
                p = private/'editions/edition/transcript.json'; changed = json.loads(p.read_text())
                changed['turns'][0]['end'] = 99; W.atomic(p, changed)
                receipt_path = private/'editions/edition/receipt.json'; receipt = json.loads(receipt_path.read_text())
                receipt['text_artifact'] = B.artifact(p); W.atomic(receipt_path, receipt)
                with self.assertRaises(ValueError):
                    B.verify_edition(receipt_path, source, 'edition', 'protocol')

    def test_stop_only_passed_owned_processes(self):
        context = mp.get_context('spawn'); owned = context.Process(target=sleeper); other = context.Process(target=sleeper)
        owned.start(); other.start()
        try:
            B.owned_stop([owned]); self.assertFalse(owned.is_alive()); self.assertTrue(other.is_alive())
        finally:
            B.owned_stop([owned, other])


if __name__ == '__main__':
    unittest.main()
