import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0,str(Path(__file__).parent))
SPEC=importlib.util.spec_from_file_location('head_ra_review',Path(__file__).with_name('head_ra_audio.py'))
H=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(H)

class Response:
    def __init__(self,status=200,length='1234',kind='audio/mpeg'):
        self.code=status;self.headers={'Content-Length':length,'Content-Type':kind,'ETag':'"test"'};self.closed=False
    def read(self,*args):raise AssertionError('HEAD auditor must never read a response body')
    def close(self):self.closed=True

class HeaderTests(unittest.TestCase):
    def fetch(self,response=None,error=None):
        event=threading.Event();gate=H.Gate(6,event)
        with patch.object(H,'build_opener') as build:
            if error:build.return_value.open.side_effect=error
            else:build.return_value.open.return_value=response
            result=H.fetch_head({'url':'https://www.lawofone.info/audio/1-0.mp3'},gate,event)
            request=build.return_value.open.call_args.args[0]
        self.assertEqual(request.get_method(),'HEAD')
        return result,event
    def test_valid_audio_headers_without_body_read(self):
        response=Response();r,event=self.fetch(response)
        self.assertEqual(r['retrieval_status'],'head_verified');self.assertEqual(r['content_length'],1234)
        self.assertEqual(r['body_bytes_read'],0);self.assertTrue(response.closed);self.assertFalse(event.is_set())
    def test_non_audio_and_missing_size_not_admitted(self):
        for response in [Response(kind='text/html'),Response(length=None),Response(length='-1'),Response(length='0')]:
            with self.subTest(headers=response.headers):self.assertNotEqual(self.fetch(response)[0]['retrieval_status'],'head_verified')
    def test_rate_or_auth_denial_sets_global_pause(self):
        for status in [401,403,407,429,451]:
            r,event=self.fetch(Response(status));self.assertEqual(r['retrieval_status'],'global_pause_http');self.assertTrue(event.is_set())
            self.assertFalse(H.Gate(6,event).before())
    def test_isolated_503_is_recorded_without_retry_or_global_pause(self):
        r,event=self.fetch(Response(503,kind='text/plain'))
        self.assertEqual(r['retrieval_status'],'isolated_503_no_retry');self.assertFalse(event.is_set())
    def test_transport_failure_does_not_log_raw_exception(self):
        r,event=self.fetch(error=URLError('secret-like test string'))
        self.assertTrue(event.is_set());self.assertEqual(r['error_type'],'URLError')
        self.assertNotIn('secret-like',json.dumps(r))
    def test_redirect_handler_refuses_followup(self):
        self.assertIsNone(H.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.example/'))
        r,event=self.fetch(Response(302));self.assertEqual(r['retrieval_status'],'redirect_not_followed')
    def test_invalid_worker_and_rate_settings_fail_before_network(self):
        for workers,rate in [(3,5),(2,7),(1,0)]:
            with self.assertRaises(ValueError):H.audit('/missing','/missing-output',workers,rate)

class FrameTests(unittest.TestCase):
    def test_every_page_hash_session_and_link_checked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rows=[]
            for n in range(1,107):
                p=root/f'{n}.html';p.write_text(f'fixture {n}')
                rows.append({'session_number':n,'http_status':200,'source_page':f'https://www.lawofone.info/s/{n}?au=1',
                    'path':str(p),'bytes':p.stat().st_size,'sha256':H.sha(p),'audio_urls':[f'https://www.lawofone.info/audio/{n}-0.mp3']})
            frame=root/'frame.json';frame.write_text(json.dumps({'source_page_count':106,'records':rows,'published_audio_segments':106,'failures':[]}))
            with patch.object(H,'parse_audio_links',side_effect=lambda raw,n:[f'https://www.lawofone.info/audio/{n}-0.mp3']):
                self.assertEqual(len(H.frame_items(frame)),106)
                (root/'13.html').write_text('changed')
                with self.assertRaisesRegex(ValueError,'bytes changed'):H.frame_items(frame)
    def test_partial_frame_cannot_claim_complete_audio_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'frame.json';p.write_text(json.dumps({'source_page_count':105,'records':[]}))
            with self.assertRaisesRegex(ValueError,'complete canonical'):H.frame_items(p)

if __name__=='__main__':unittest.main()
