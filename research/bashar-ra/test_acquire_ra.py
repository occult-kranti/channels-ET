import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

spec=importlib.util.spec_from_file_location('acquire_ra',Path(__file__).with_name('acquire_ra.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def page(number=1,body=None,edition='Lightly Edited'):
    if body is None:body=f'<p class="ra" id="0"><a>{number}</a>.<a>0</a> <b>Ra:</b> Opening words.</p><p class=" elkins" id="1">{number}.1 <b>Questioner:</b> A question?<span class="optional">*</span></p><p class="ra"><b>Ra:</b> First answer.<br><br>[Inaudible] More words.</p>'
    return (f'<meta name="description" content="The Law of One Session {number}. January 15, 1981"><nav>Unrelated navigation.</nav>'+body+f'<ul>Version (<a>?</a>): {edition}</ul><footer>Copyright unrelated.</footer>').encode()

class ParseTests(unittest.TestCase):
    def test_preserves_roles_qids_and_excludes_layout(self):
        d=a.parse_session(page(),1)
        self.assertEqual([t['role'] for t in d['turns']],['response','questioner','response'])
        self.assertEqual([t['question_id'] for t in d['turns']],['1.0','1.1','1.1'])
        self.assertEqual(d['text'],'\n'.join(t['text'] for t in d['turns']))
        self.assertNotIn('navigation',d['text']);self.assertNotIn('Copyright',d['text']);self.assertNotIn('*',d['text'])
        self.assertIn('[Inaudible]',d['text']);self.assertNotIn('Questioner:',d['text'])
    def test_wrong_session_refused(self):
        with self.assertRaisesRegex(ValueError,'identity'):a.parse_session(page(2),1)
    def test_wrong_edition_refused(self):
        with self.assertRaisesRegex(ValueError,'edition'):a.parse_session(page(edition='Original'),1)
    def test_error_page_refused(self):
        with self.assertRaises(ValueError):a.parse_session(b'<h1>404</h1>',1)
    def test_missing_response_refused(self):
        with self.assertRaisesRegex(ValueError,'response'):a.parse_session(page(body='<p class="elkins" id="1">1.1 Questioner: Question?</p>'),1)
    def test_duplicate_prompt_refused(self):
        body='<p class="elkins" id="1">1.1 Questioner: A?</p><p class="ra">Ra: B.</p>'*2
        with self.assertRaisesRegex(ValueError,'Duplicate'):a.parse_session(page(body=body),1)
    def test_out_of_order_refused(self):
        body='<p class="ra" id="2">1.2 Ra: A.</p><p class="elkins" id="1">1.1 Questioner: B?</p>'
        with self.assertRaisesRegex(ValueError,'ordering'):a.parse_session(page(body=body),1)
    def test_real_numbered_response_without_prompt_preserved(self):
        body='<p class="ra" id="3">1.3 Ra: Published answer with missing question.</p>'
        d=a.parse_session(page(body=body),1);self.assertEqual(d['turns'][0]['question_id'],'1.3');self.assertEqual(d['turns'][0]['role'],'response')
    def test_lost_tape_notice_preserved_and_selected(self):
        body='<p class="ra" id="0">1.0 Ra: [The audiotape was reused for another purpose.]</p>'
        d=a.parse_session(page(body=body),1);self.assertEqual(d['audio_gap_notices'],['1.0']);self.assertIn('reused',d['text'])
    def test_permission_rendered_text_handles_linked_words(self):
        self.assertIn('with permission from L/L Research',a.rendered_text('with permission from <a href="x">L/L Research</a> to republish'))
    def test_unauthorized_source_bounds(self):
        for n in (0,107):
            with self.assertRaises(ValueError):a.parse_session(page(),n)
    def test_private_path_rejects_git_and_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'.git').mkdir();(p/'.git/HEAD').write_text('ref: refs/heads/main')
            with self.assertRaisesRegex(ValueError,'Git'):a.private_root(p/'raw')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'real').mkdir();(p/'link').symlink_to(p/'real',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):a.private_root(p/'link'/'raw')
    def test_retained_cache_hash_and_status_checked(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f=p/'session-001.html';f.write_bytes(page());r=p/'session-001.retrieval.json'
            row={'status':200,'url':a.BASE+'/s/1','sha256':a.sha(f),'bytes':f.stat().st_size};r.write_text(json.dumps(row))
            with patch.object(a,'urlopen',side_effect=AssertionError('No network for cache')):a.fetch(1,p,a.RateGate(0))
            row['status']=403;r.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError,'status'):a.fetch(1,p,a.RateGate(0))
            row['status']=200;r.write_text(json.dumps(row));f.write_bytes(page()+b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):a.fetch(1,p,a.RateGate(0))



class AudioTests(unittest.TestCase):
    def test_redirect_handler_refuses_before_following(self):
        self.assertIsNone(a.NoRedirect().redirect_request(None,None,302,'Found',{},'https://other.test/'))
    def fixture(self,folder):
        root=Path(folder);frame=root/'frame.json';sizes=root/'sizes.json';frame.write_text('{}');sizes.write_text('{}')
        url=a.BASE+'/audio/1-0.mp3';row={'url':url,'session_number':1,'segment_number':0,'content_length':4,'content_type':'audio/mpeg','etag':'"same"'}
        pages={url:{'source_page':a.BASE+'/s/1?au=1','sha256':'a'*64}}
        return frame,sizes,row,pages
    def response(self,row,data=b'fake',length='4',ctype='audio/mpeg',etag='"same"'):
        class Response:
            status=200;url=row['url'];headers={'Content-Length':length,'Content-Type':ctype,'ETag':etag,'Last-Modified':None}
            def __init__(self):self.done=False
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):
                if self.done:return b''
                self.done=True;return data
        return Response()
    def run_fixture(self,root,change=None):
        frame,sizes,row,pages=self.fixture(root)
        probe={'duration_seconds':1.0,'format_name':'mp3','bit_rate':128000,'streams':[{'codec_type':'audio','codec_name':'mp3'}]}
        return frame,sizes,row,pages,probe
    def test_exact_audio_identity_only(self):
        self.assertEqual(a.audio_url_parts(a.BASE+'/audio/106-2.mp3'),(106,2))
        for url in ('https://other.test/audio/1-0.mp3',a.BASE+'/audio/107-0.mp3',a.BASE+'/audio/1-0.mp3?token=x',a.BASE+'/audio/../secret'):
            with self.assertRaises(ValueError):a.audio_url_parts(url)
    def test_player_links_match_source_identity_and_numeric_order(self):
        html=page()+b'<a href="/audio/1-10.mp3">play</a><a href="/audio/1-2.mp3">play</a><a href="/audio/1-2.mp3">play</a>'
        self.assertEqual(a.parse_audio_links(html,1),[a.BASE+'/audio/1-2.mp3',a.BASE+'/audio/1-10.mp3'])
        with self.assertRaisesRegex(ValueError,'another session'):a.parse_audio_links(page()+b'<a href="/audio/2-0.mp3">play</a>',1)
        with self.assertRaisesRegex(ValueError,'identity'):a.parse_audio_links(page(2),1)
    def test_published_frame_count_cannot_be_faked(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'frame.json';h=Path(t)/'heads.json';f.write_text(json.dumps({'source_page_count':106,'records':[],'failures':[]}));h.write_text('{}')
            with self.assertRaisesRegex(ValueError,'frame'):a.validate_audio_inputs(f,h)
    def test_budget_refuses_before_network(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,_=self.run_fixture(t)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'budget'):a.download_audio(frame,sizes,Path(t)/'out',3,1024**3,1)
                network.assert_not_called()
    def test_explicit_minimum_reserve(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,_=self.run_fixture(t)
            with self.assertRaisesRegex(ValueError,'reserve'):a.download_audio(frame,sizes,Path(t)/'out',10,10,1)
    def test_success_receipt_playlist_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row)) as network,patch.object(a,'audio_probe',return_value=probe),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,out,10,1024**3,1);self.assertEqual(result['status'],'completed');self.assertEqual(network.call_count,1)
            self.assertEqual((out/'session-001/session.m3u').read_text(),'#EXTM3U\n#EXTINF:1.000000,Ra 1.0\n001-000.mp3\n')
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',side_effect=AssertionError('No network on completed-source retry')):
                second=a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
            self.assertEqual(second['verified_segments'],1);self.assertEqual(second['verified_bytes'],4)
    def test_changed_head_length_not_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row,length='5')),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,Path(t)/'out',10,1024**3,1)
            self.assertEqual(result['status'],'partial');self.assertEqual(result['verified_segments'],0)
    def test_truncated_transfer_preserved_unadmitted(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row,data=b'no')),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,out,10,1024**3,1)
            self.assertEqual(result['verified_segments'],0);self.assertTrue((out/'session-001/001-000.mp3.partial').exists());self.assertFalse((out/'session-001/001-000.mp3').exists())
    def test_nonmedia_rejected_despite_audio_header(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row)),patch.object(a,'audio_probe',side_effect=ValueError('Invalid media')),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,Path(t)/'out',10,1024**3,1)
            self.assertEqual(result['verified_segments'],0)
    def test_policy_denial_latches_and_prevents_new_requests(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',side_effect=HTTPError(row['url'],403,'Forbidden',{},None)),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,out,10,1024**3,1)
            self.assertEqual(result['verified_segments'],0);self.assertTrue((out/'source-halt.json').exists())
            with patch.object(a,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'source-wide denial'):a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
                network.assert_not_called()
    def test_transport_failure_latches(self):
        from urllib.error import URLError
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',side_effect=URLError('transport')),patch.object(a.RateGate,'wait'):
                result=a.download_audio(frame,sizes,out,10,1024**3,1)
            self.assertEqual(result['verified_segments'],0);self.assertTrue((out/'source-halt.json').exists())
    def test_transient_retry_preserves_attempts_and_latest_failure(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',side_effect=HTTPError(row['url'],503,'Unavailable',{},None)),patch.object(a.RateGate,'wait'):
                first=a.download_audio(frame,sizes,out,10,1024**3,1)
                second=a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row)),patch.object(a,'audio_probe',return_value=probe),patch.object(a.RateGate,'wait'):
                third=a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
            self.assertEqual([first['status'],second['status'],third['status']],['partial','partial','completed'])
            self.assertTrue((out/'audio-manifest.json').exists());self.assertTrue((out/'audio-manifest-retry.json').exists());self.assertTrue((out/'audio-manifest-attempt-003.json').exists())
            self.assertEqual(json.loads((out/'session-001/001-000.failure.json').read_text())['attempt_number'],1)
            self.assertEqual(json.loads((out/'session-001/001-000.latest-failure.json').read_text())['attempt_number'],2)
    def test_transient_retry_does_not_reclassify_new_nontransient_failure(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe=self.run_fixture(t);out=Path(t)/'out'
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',side_effect=HTTPError(row['url'],503,'Unavailable',{},None)),patch.object(a.RateGate,'wait'):
                a.download_audio(frame,sizes,out,10,1024**3,1)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen',return_value=self.response(row,length='5')),patch.object(a.RateGate,'wait'):
                a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen') as network:
                result=a.download_audio(frame,sizes,out,10,1024**3,1,retry_transient=True)
                network.assert_not_called();self.assertEqual(result['verified_segments'],0)

class CompactTests(unittest.TestCase):
    def fixtures(self,root):
        frame,sizes,row,pages,probe=AudioTests().run_fixture(root)
        probe['streams'][0]['channels']=1
        compact={'format_name':'ogg','codec':'opus','streams':[{'codec_type':'audio','codec_name':'opus','channels':1}],'duration_seconds':1.0}
        return frame,sizes,row,pages,probe,compact
    def run_compact(self,root,out=None,response=None,durations=None,channels=1,encoded_bytes=b'opus',limit=1024**2,retry=False,pilot=None,network_error=None):
        from contextlib import ExitStack
        frame,sizes,row,pages,probe,compact=self.fixtures(root);compact['streams'][0]['channels']=channels
        out=out or Path(root)/'out'
        def encoder(source,target,source_channels):target.write_bytes(encoded_bytes)
        with ExitStack() as stack:
            stack.enter_context(patch.object(a,'validate_audio_inputs',return_value=([row],pages)))
            network=stack.enter_context(patch.object(a,'urlopen',return_value=response or AudioTests().response(row),side_effect=network_error))
            stack.enter_context(patch.object(a,'audio_probe',return_value=probe))
            stack.enter_context(patch.object(a,'compact_probe',return_value=compact))
            stack.enter_context(patch.object(a,'decoded_duration',side_effect=durations or [1.0,1.0]))
            encode=stack.enter_context(patch.object(a,'encode_compact',side_effect=encoder))
            stack.enter_context(patch.object(a.RateGate,'wait'))
            result=a.download_compact_audio(frame,sizes,out,4,3*1024**3,limit,workers=1,reuse_pilot=pilot,retry_transient=retry)
        return result,network.call_count,encode.call_count
    def test_verified_compact_retains_proof_and_deletes_only_new_original(self):
        with tempfile.TemporaryDirectory() as t:
            result,network,encode=self.run_compact(t);out=Path(t)/'out/session-001'
            self.assertEqual(result['status'],'completed');self.assertEqual((network,encode),(1,1));self.assertEqual(result['retained_bytes'],4)
            self.assertEqual(result['original_verified_bytes'],4);self.assertEqual(result['original_mp3s_retained'],0)
            self.assertFalse((out/'001-000.source.mp3').exists());self.assertTrue((out/'001-000.original-source.json').exists());self.assertTrue((out/'001-000.cleanup.json').exists())
            self.assertTrue((out/'001-000.opus').exists());self.assertIn('001-000.opus',(out/'session.m3u').read_text())
    def test_duration_mismatch_preserves_original_and_halts(self):
        with tempfile.TemporaryDirectory() as t:
            result,_,_=self.run_compact(t,durations=[1.0,.5]);out=Path(t)/'out'
            self.assertEqual(result['verified_segments'],0);self.assertTrue((out/'review-halt.json').exists())
            self.assertTrue((out/'session-001/001-000.source.mp3').exists());self.assertTrue((out/'session-001/001-000.opus.partial').exists());self.assertFalse((out/'session-001/001-000.receipt.json').exists())
    def test_channel_mismatch_is_not_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            result,_,_=self.run_compact(t,channels=2)
            self.assertEqual(result['verified_segments'],0);self.assertTrue((Path(t)/'out/session-001/001-000.source.mp3').exists())
    def test_output_byte_overrun_preserves_original(self):
        with tempfile.TemporaryDirectory() as t:
            result,_,_=self.run_compact(t,encoded_bytes=b'x'*150000)
            self.assertEqual(result['verified_segments'],0);self.assertTrue((Path(t)/'out/session-001/001-000.source.mp3').exists())
    def test_retained_budget_prevents_encode(self):
        with tempfile.TemporaryDirectory() as t:
            result,network,encode=self.run_compact(t,limit=10)
            self.assertEqual((network,encode),(1,0));self.assertEqual(result['verified_segments'],0)
    def test_resume_uses_completed_copy_without_network_or_encode(self):
        with tempfile.TemporaryDirectory() as t:
            self.run_compact(t);result,network,encode=self.run_compact(t)
            self.assertEqual(result['status'],'completed');self.assertEqual((network,encode),(0,0));self.assertEqual(result['original_verified_bytes'],4)
    def test_pilot_is_never_deleted_or_downloaded_again(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);frame,sizes,row,pages,probe,compact=self.fixtures(t);original=root/'pilot.mp3';original.write_bytes(b'fake');receipt=root/'pilot.json'
            receipt.write_text(json.dumps({'url':row['url'],'status':200,'path':str(original),'bytes':4,'sha256':a.sha(original),'headers':{'ETag':'"same"','Content-Type':'audio/mpeg','Content-Length':'4'}}))
            result,network,encode=self.run_compact(t,pilot=receipt)
            self.assertEqual(result['status'],'completed');self.assertEqual((network,encode),(0,1));self.assertTrue(original.exists());self.assertEqual(result['original_mp3s_retained'],1)
    def test_truncated_original_cannot_be_encoded(self):
        with tempfile.TemporaryDirectory() as t:
            _,_,row,_,_,_=self.fixtures(t);result,_,encode=self.run_compact(t,response=AudioTests().response(row,data=b'x'))
            self.assertEqual(encode,0);self.assertEqual(result['verified_segments'],0);self.assertTrue((Path(t)/'out/review-halt.json').exists())
    def test_exact_cumulative_budget_required_before_network(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe,compact=self.fixtures(t)
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'exact|equal'):a.download_compact_audio(frame,sizes,Path(t)/'out',5,3*1024**3,1024**2,workers=1)
                network.assert_not_called()
    def test_worker_staging_share_checked_before_network(self):
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe,compact=self.fixtures(t);row['content_length']=129*1024**2
            with patch.object(a,'validate_audio_inputs',return_value=([row],pages)),patch.object(a,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'staging'):a.download_compact_audio(frame,sizes,Path(t)/'out',row['content_length'],3*1024**3,1024**2,workers=2)
                network.assert_not_called()
    def test_isolated_503_can_be_explicitly_retried_without_replacing_history(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as t:
            _,_,row,_,_,_=self.fixtures(t)
            first,_,_=self.run_compact(t,network_error=HTTPError(row['url'],503,'Unavailable',{},None))
            self.assertEqual(first['status'],'partial');self.assertFalse((Path(t)/'out/review-halt.json').exists())
            second,network,encode=self.run_compact(t,retry=True)
            self.assertEqual(second['status'],'completed');self.assertEqual((network,encode),(1,1))
            self.assertTrue((Path(t)/'out/audio-manifest.json').exists());self.assertTrue((Path(t)/'out/audio-manifest-attempt-002.json').exists())
    def test_policy_denial_blocks_any_new_attempt(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as t:
            frame,sizes,row,pages,probe,compact=self.fixtures(t)
            first,_,_=self.run_compact(t,network_error=HTTPError(row['url'],403,'Forbidden',{},None))
            self.assertEqual(first['verified_segments'],0)
            with patch.object(a,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'halt'):a.download_compact_audio(frame,sizes,Path(t)/'out',4,3*1024**3,1024**2,workers=1,retry_transient=True)
                network.assert_not_called()

if __name__=='__main__':unittest.main()
