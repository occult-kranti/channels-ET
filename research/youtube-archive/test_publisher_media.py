#!/usr/bin/env python3
"""Synthetic parser/media-failure controls. These fixtures are not acquisitions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('publisher_media_under_test',
                                             Path(__file__).with_name('publisher_media.py'))
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class PublisherMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='publisher-media-synthetic-', dir='/dev/shm')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.url = 'https://omna-shop.s3.eu-west-2.amazonaws.com/synthetic.mp3'
        self.raw = ('<html><nav>Exclude navigation</nav><a href="'+self.url+'">Audio</a>'
                    '<div data-id="body"><div><p>Hello <i>world</i>.</p><p>'+('word '*101)+
                    '</p></div></div><div data-id="closing"><h4>Closing.</h4></div>'
                    '<div data-id="credit"><p>Credit.</p></div><footer>Exclude footer</footer></html>').encode()
        self.path = self.root/'page.html'; self.path.write_bytes(self.raw)
        self.c = {'page_artifact': str(self.path), 'page_sha256': M.sha(self.raw),
                  'audio_url': self.url, 'body_block_ids': ['body', 'closing'],
                  'attribution_block_ids': ['credit']}

    def test_selected_text_inline_punctuation_and_exclusions(self):
        _, body, attribution = M.extract_page(self.c)
        self.assertTrue(body.startswith('Hello world.\n\n'))
        self.assertTrue(body.endswith('Closing.\n'))
        self.assertNotIn('navigation', body); self.assertNotIn('footer', body)
        self.assertNotIn('Credit', body); self.assertEqual(attribution, 'Credit.\n')

    def test_changed_page_hash_rejected(self):
        self.path.write_bytes(self.raw+b' ')
        with self.assertRaisesRegex(ValueError, 'hash differs'): M.extract_page(self.c)

    def test_unlinked_audio_rejected(self):
        self.c['audio_url'] = self.url.replace('synthetic', 'different')
        with self.assertRaisesRegex(ValueError, 'href not present'): M.extract_page(self.c)

    def test_audio_only_requires_explicit_status_and_creates_no_text(self):
        self.c.update(body_block_ids=[], attribution_block_ids=[])
        with self.assertRaisesRegex(ValueError, 'audio-only status'): M.extract_page(self.c)
        self.c['allow_audio_only'] = True
        raw, body, attribution = M.extract_page(self.c)
        self.assertEqual(raw, self.raw)
        self.assertIsNone(body); self.assertIsNone(attribution)

    def test_missing_duplicate_and_overlapping_blocks_rejected(self):
        variants = [self.raw.replace(b'data-id="body"', b'data-id="absent"'),
                    self.raw+b'<div data-id="body">Duplicate</div>',
                    self.raw.replace(b'<i>world</i>', b'<i data-id="closing">world</i>')]
        for raw in variants:
            with self.subTest(raw_sha=M.sha(raw)):
                self.path.write_bytes(raw); self.c['page_sha256'] = M.sha(raw)
                with self.assertRaises(ValueError): M.extract_page(self.c)

    def test_invalid_audio_urls_rejected_without_network(self):
        for url in ('https://www.youtube.com/watch?v=not-requested',
                    'https://example.com/audio.mp3', self.url+'?token=synthetic',
                    self.url.replace('https://', 'http://')):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, 'Unsupported'):
                    M.download_audio(url, self.root/'never-created.mp3')
                self.assertFalse((self.root/'never-created.mp3').exists())

    def test_empty_html_and_corrupt_media_rejected(self):
        for raw in (b'', b'<html>Not audio</html>', b'ID3syntheticbroken'):
            with self.subTest(raw=raw):
                path = self.root/'invalid.mp3'; path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'ffprobe rejected'): M.validate_audio(path)

    def test_real_decoder_accepts_synthetic_tone_and_counts_samples(self):
        path = self.root/'synthetic.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=0.25:sample_rate=16000',
                        '-c:a', 'pcm_s16le', str(path)], check=True)
        _, result = M.validate_audio(path)
        self.assertEqual(result['decoded_pcm_samples'], 4000)
        self.assertEqual(result['decoded_duration_seconds'], 0.25)
        self.assertFalse(result['decoded_pcm_retained'])

    def test_verified_opus_output_preserves_synthetic_duration(self):
        path = self.root/'synthetic.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=0.25:sample_rate=16000',
                        '-c:a', 'pcm_s16le', str(path)], check=True)
        output = self.root/'synthetic.opus'
        _, result = M.transcode_opus(path, output)
        self.assertEqual(result['codec'], 'opus')
        self.assertAlmostEqual(result['decoded_duration_seconds'], 0.25, places=3)
        self.assertTrue(path.exists())  # Helper alone never removes its source.

    def test_failed_candidate_has_no_public_private_path_or_success_count(self):
        c = dict(self.c, record_id='synthetic-failure', title='Synthetic', page_url='https://example.com')
        c['page_artifact'] = '/workspace/synthetic-nonexistent-file-not-real'
        selection = self.root/'selection.json'; selection.write_text(json.dumps({'candidates':[c]}))
        result = M.run(selection, self.root/'output')
        self.assertEqual(result['summary']['retained_publisher_audio_files'], 0)
        self.assertEqual(result['summary']['failed_candidates'], 1)
        public = (self.root/'output/public/publisher-media.json').read_text()
        self.assertNotIn('/workspace/', public)
        self.assertNotIn('page_artifact', public)

    def test_resource_guard_override_is_explicit_and_recorded(self):
        c = dict(self.c, record_id='synthetic-guard', title='Synthetic', page_url='https://example.com')
        c['page_artifact'] = '/workspace/synthetic-nonexistent-file-not-real'
        selection = self.root/'selection.json'; selection.write_text(json.dumps({'candidates':[c]}))
        self.addCleanup(setattr, M, 'FLOOR', 2*1024**3)
        with self.assertRaisesRegex(ValueError, 'resource policy'):
            M.run(selection, self.root/'invalid-policy', minimum_free_gib=0.5)
        self.assertFalse((self.root/'invalid-policy').exists())
        result = M.run(selection, self.root/'explicit-policy', minimum_free_gib=1.5)
        self.assertEqual(result['execution']['minimum_free_bytes'], int(1.5*1024**3))
        self.assertGreater(result['execution']['initial_free_bytes'], 0)
        self.assertEqual(result['summary']['retained_publisher_audio_files'], 0)

    def test_release_resolves_historical_hold_and_rejects_changed_artifact(self):
        held = self.root/'synthetic-held-run'; held.mkdir()
        M.write(held/'manifest.json', {'records': [], 'failures': [
            {'record_id': 'synthetic-record', 'status': 'deferred_resource_budget'}],
            'pending_queue': [{'record_id': 'synthetic-record', 'status': 'deferred_resource_budget'}]})
        completed = self.root/'synthetic-completed-run'; completed.mkdir()
        folder = completed/'synthetic-record'; folder.mkdir()
        # Deliberately synthetic byte fixtures exercise binding/accounting only,
        # not decoder acceptance. Real decoder controls are separate above.
        audio = b'SYNTHETIC AUDIO BINDING FIXTURE'; body = b'Synthetic written fixture.\n'; page = b'<p>Synthetic page.</p>'
        (folder/'publisher-original.mp3').write_bytes(audio)
        (folder/'publisher-written.txt').write_bytes(body)
        (folder/'publisher-page.html').write_bytes(page)
        record = {'record_id': 'synthetic-record', 'page_sha256': M.sha(page),
                  'audio': {'bytes': len(audio), 'sha256': M.sha(audio), 'decoded_duration_seconds': 0.25},
                  'written': {'bytes': len(body), 'sha256': M.sha(body), 'words': 3,
                              'status': 'retained_publisher_written_edition', 'manual_read_by_ai': False}}
        M.write(completed/'manifest.json', {'records': [record], 'failures': []})
        result = M.combine_runs([held, completed], self.root/'synthetic-release')
        self.assertEqual(result['summary']['candidate_frame'], 1)
        self.assertEqual(result['summary']['resource_deferred_candidates'], 0)
        self.assertEqual(result['summary']['resolved_historical_failed_or_deferred_attempts'], 1)
        self.assertEqual(result['pending_queue'], [])
        (folder/'publisher-original.mp3').write_bytes(audio+b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            M.combine_runs([held, completed], self.root/'rejected-release')


if __name__ == '__main__': unittest.main(verbosity=2)
