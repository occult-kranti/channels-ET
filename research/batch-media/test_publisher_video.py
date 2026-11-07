"""Independent-publisher transfer guard fixtures; no remote requests."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('publisher_video', Path(__file__).with_name('publisher_video.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = {'content-type': 'video/mp4', 'content-length': str(len(body)), 'etag': '"fixture-v1"', **(headers or {})}


class Opener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, **kwargs):
        self.requests.append(request)
        return self.response


class PublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory()
        cls.media = Path(cls.shared.name) / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=64x36:rate=1',
                        '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', '-t', '301', '-c:v', 'libx264',
                        '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(cls.media)], check=True)
        cls.body = cls.media.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.page = self.root / 'page.html'
        self.url = 'https://cdn.example.org/official.mp4'
        self.page.write_text(f'<a href="{self.url}" download>Download</a>')
        self.args = dict(source_page=self.page, source_sha256=MODULE.digest(self.page), source_url='https://example.org/library',
                         media_url=self.url, target=self.root / 'recording.mp4', source_id='creator:1',
                         medium_id='test-person-context', channel_id='test-publisher', reserve_free=0)

    def call(self, body=None, **kwargs):
        opener = Opener(Response(self.body if body is None else body))
        result = MODULE.download(**{**self.args, **kwargs}, opener=opener)
        return result, opener

    def test_real_video_stream_and_complete_receipt(self):
        result, opener = self.call()
        self.assertEqual(result['status'], 'verified')
        self.assertGreaterEqual(result['validation']['ffprobe_duration_seconds'], 300)
        self.assertEqual(result['bytes'], len(self.body))
        self.assertEqual(result['sha256'], MODULE.digest(self.args['target']))
        self.assertEqual(opener.requests[0].get_header('Referer'), 'https://example.org/')
        self.assertEqual(result['new_youtube_downloads'], 0)

    def test_verified_resume_is_no_network_and_corruption_rejected(self):
        first, _ = self.call()
        opener = Opener(None)
        result = MODULE.download(**self.args, resume=True, opener=opener)
        self.assertEqual(result['sha256'], first['sha256'])
        self.assertEqual(opener.requests, [])
        self.args['target'].write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            MODULE.download(**self.args, resume=True, opener=opener)
        self.assertEqual(opener.requests, [])

    def test_html_error_body_does_not_become_media(self):
        with self.assertRaises(ValueError):
            self.call(b'<html>Not video</html>')
        self.assertFalse(self.args['target'].exists())
        self.assertTrue(self.args['target'].with_name('recording.mp4.partial').exists())

    def test_nonvideo_content_type_stops_before_writing(self):
        opener = Opener(Response(b'error', headers={'content-type': 'text/html'}))
        with self.assertRaisesRegex(ValueError, 'not video'):
            MODULE.download(**self.args, opener=opener)
        self.assertFalse(self.args['target'].exists())

    def test_size_reserve_and_height_bounds(self):
        for patch in ({'max_bytes': len(self.body) - 1}, {'reserve_free': 10**15}):
            with self.subTest(patch=patch):
                args = {**self.args, **patch, 'target': self.root / ('size.mp4' if 'max_bytes' in patch else 'reserve.mp4')}
                with self.assertRaises(ValueError):
                    MODULE.download(**args, opener=Opener(Response(self.body)))
        for height in [True, 0, 1080]:
            with self.assertRaises(ValueError):
                MODULE.download(**self.args, max_height=height, opener=Opener(Response(self.body)))

    def test_changed_predeclared_length_stops_before_body(self):
        opener = Opener(Response(self.body))
        with self.assertRaisesRegex(ValueError, 'finite batch reservation'):
            MODULE.download(**self.args, expected_bytes=len(self.body)-1, opener=opener)
        self.assertFalse(self.args['target'].exists())
        self.assertFalse(self.args['target'].with_name('recording.mp4.partial').exists())

    def test_source_hash_and_exact_download_link(self):
        for page in ['<a href="https://cdn.example.org/official.mp4">Play</a>', '<a href="https://cdn.example.org/other.mp4" download>Download</a>']:
            self.page.write_text(page)
            with self.assertRaises(ValueError):
                self.call(source_sha256=MODULE.digest(self.page))
        self.page.write_text('<a href="https://cdn.example.org/official.mp4" download>Download</a>changed')
        with self.assertRaisesRegex(ValueError, 'page changed'):
            self.call()

    def test_youtube_credentials_http_redirect_and_public_output_rejected(self):
        for url in ['http://cdn.example.org/video.mp4', 'https://u:p@cdn.example.org/video.mp4',
                    'https://www.youtube.com/watch?v=abcdefghijk', 'https://r1.googlevideo.com/file.mp4']:
            with self.assertRaises(ValueError):
                MODULE.https_url(url)
        redirect = MODULE.SameHostRedirect('cdn.example.org')
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, '', {}, 'https://evil.example.org/file.mp4')
        repo = self.root / 'repo'
        repo.mkdir()
        (repo / '.git').mkdir()
        (repo / '.git' / 'HEAD').write_text('ref: refs/heads/main\n')
        with self.assertRaisesRegex(ValueError, 'outside Git'):
            self.call(target=repo / 'recording.mp4')

    def test_empty_platform_marker_is_not_a_repository(self):
        (self.root / '.git').mkdir()
        self.assertEqual(MODULE.private_path(self.root / 'private' / 'recording.mp4'), self.root / 'private' / 'recording.mp4')
        marker = self.root / 'worktree'
        marker.mkdir()
        (marker / '.git').write_text('gitdir: /tmp/actual-git-metadata')
        with self.assertRaisesRegex(ValueError, 'outside Git'):
            MODULE.private_path(marker / 'recording.mp4')

    def seed_partial(self):
        # Use a successful transfer to obtain the precise request binding, then
        # retain an interrupted first half and its explicit validator/checkpoint.
        first, _ = self.call()
        self.args['target'].unlink()
        self.args['target'].with_name('recording.mp4.receipt.json').unlink()
        partial = self.args['target'].with_name('recording.mp4.partial')
        half = len(self.body) // 2
        partial.write_bytes(self.body[:half])
        state = {'binding': first['binding'], 'status': 'failed_no_automatic_retry', 'validator': '"fixture-v1"',
                 'total_bytes': len(self.body), 'partial_bytes': half, 'partial_sha256': MODULE.digest(partial)}
        MODULE.atomic_json(self.args['target'].with_name('recording.mp4.transfer.json'), state)
        return partial, half

    def test_validator_bound_range_resume(self):
        partial, half = self.seed_partial()
        opener = Opener(Response(self.body[half:], status=206,
                                headers={'content-range': f'bytes {half}-{len(self.body)-1}/{len(self.body)}'}))
        result = MODULE.download(**self.args, resume=True, opener=opener)
        self.assertEqual(result['sha256'], MODULE.digest(self.media))
        self.assertEqual(opener.requests[0].get_header('Range'), f'bytes={half}-')
        self.assertEqual(opener.requests[0].get_header('If-range'), '"fixture-v1"')
        self.assertFalse(partial.exists())

    def test_ignored_range_changed_validator_and_partial_tampering_stop(self):
        partial, half = self.seed_partial()
        original = partial.read_bytes()
        for response in [Response(self.body), Response(self.body[half:], status=206, headers={
            'content-range': f'bytes {half}-{len(self.body)-1}/{len(self.body)}', 'etag': '"different"'})]:
            with self.assertRaises(ValueError):
                MODULE.download(**self.args, resume=True, opener=Opener(response))
            self.assertEqual(partial.read_bytes(), original)
        partial.write_bytes(original + b'tampered')
        opener = Opener(None)
        with self.assertRaisesRegex(ValueError, 'changed'):
            MODULE.download(**self.args, resume=True, opener=opener)
        self.assertEqual(opener.requests, [])


if __name__ == '__main__':
    unittest.main()
