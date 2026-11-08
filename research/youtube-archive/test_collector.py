import json
import functools
import http.server
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).parent))
import collector as C

CID='UC'+'a'*22
OTHER='UC'+'b'*22
VID='AbCdEfGhI_1'


def inventory(path):
    value={'accounts':[{'account_id':'a','channel_id':CID,'display_name':'A','inclusion_status':'included_screened',
        'duration_policy':{'minimum_seconds':0},'handles':['@a'],'observed_video_ids':[VID]},
        {'account_id':'b','channel_id':OTHER,'display_name':'B','inclusion_status':'candidate_unreviewed',
        'duration_policy':{'minimum_seconds':0},'handles':['@b'],'observed_video_ids':[VID]}],
        'videos':[{'video_id':VID,'policy_decision':{'status':'eligible','minimum_seconds':0}}]}
    C.save(path,value);return value


class CollectorTest(unittest.TestCase):
    def test_gateway_denial_is_preorigin_not_source_unavailable(self):
        self.assertEqual(C.classify_error('CONNECT tunnel failed, response 403'),('gateway_connect_denied',True))
        self.assertEqual(C.classify_error('HTTP Error 403: Forbidden'),('origin_or_media_access_denied',False))
        self.assertEqual(C.classify_error('This video is unavailable')[1],False)

    def test_gate_prevents_all_extractor_and_download_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            gate=root/'gate.json';C.save(gate,{'url':'https://www.youtube.com/watch?v='+VID,'at':C.now(),'returncode':56,
                'curl':{'http_connect':403,'http_code':0},'stderr':'CONNECT tunnel failed, response 403','files':[]})
            with mock.patch.object(C,'runtime',return_value={'collector_sha256':'fixture'}),mock.patch.object(C,'Runner',side_effect=AssertionError('must not start')):
                result=C.run(store,gate)
            self.assertEqual(result['status'],'held_before_extraction');self.assertEqual(sum(result['requests'].values()),0)
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT status FROM videos').fetchone()[0],'held_shared_route')

    def test_exact_owner_receives_asset_credit_not_weak_listing_account(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            artifact=store.root/'synthetic-test-bytes';artifact.write_bytes(b'fixture-only-not-media')
            store.add_artifact(VID,'fixture','audio',artifact,{'fixture':True})
            with store.connect() as db:db.execute('UPDATE videos SET owner_channel_id=? WHERE video_id=?',(CID,VID))
            out=C.export(store,root/'public');by={a['account_id']:a for a in out['accounts']}
            self.assertEqual(by['a']['retained_audio_ids'],[VID]);self.assertEqual(by['b']['retained_audio_ids'],[])
            self.assertEqual(by['b']['observed_video_ids'],[VID])
            artifact.write_bytes(b'changed');out=C.export(store,root/'public2')
            self.assertEqual(out['artifacts_summary']['verified_files'],0)

    def test_duration_floor_is_per_video_and_fresh_bashar_cue_conservative(self):
        self.assertEqual(C.duration_floor({'minimum_seconds':0},{'title':'A short other-source message'})[0],0)
        self.assertEqual(C.duration_floor({'minimum_seconds':0},{'title':'Bashar — reposted answer'})[0],300)
        self.assertEqual(C.duration_floor({'minimum_seconds':300},{'title':'Unspecified source'})[0],300)
        self.assertEqual(C.duration_floor({'minimum_seconds':0},{'description':'Channeled through Darryl Anka'})[0],300)

    def test_decoded_duration_not_container_duration_enforces_bashar_floor(self):
        check={'duration_seconds':300.,'decoded_pcm':{'duration_seconds':299.99}}
        with self.assertRaisesRegex(ValueError,'Decoded media below'):C.validate_media_policy(check,300,300.)
        C.validate_media_policy(check,0,300.)

    def test_repeated_errors_break_after_three_distinct_jobs_but_unavailable_does_not(self):
        with tempfile.TemporaryDirectory() as temp,mock.patch.object(C,'runtime',return_value={}):
            runner=C.Runner(C.Store(Path(temp)),'fixture')
            runner.outcome('one','origin_or_media_access_denied');runner.outcome('one','origin_or_media_access_denied')
            self.assertFalse(runner.stop.is_set())
            runner.outcome('two','origin_or_media_access_denied');runner.outcome('three','source_restricted_or_unavailable')
            runner.outcome('four','origin_or_media_access_denied');self.assertFalse(runner.stop.is_set())
            runner.outcome('five','origin_or_media_access_denied');runner.outcome('six','origin_or_media_access_denied')
            self.assertTrue(runner.stop.is_set());self.assertEqual(runner.breaker['distinct_jobs'],3)

    def test_account_path_and_cross_tab_identity_cannot_change_silently(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';value=inventory(path);store=C.Store(root/'raw')
            value['accounts'][0]['account_id']='../escape';C.save(path,value)
            with self.assertRaisesRegex(ValueError,'Unsafe account'):store.initialize(path)
            value=inventory(path);value['accounts'][0]['channel_id']=None;C.save(path,value);store.initialize(path)
            with store.connect() as db:
                stale=dict(db.execute("SELECT * FROM accounts WHERE account_id='a'").fetchone())
                db.execute("UPDATE accounts SET channel_id=? WHERE account_id='a'",(CID,))
            class FakeYDL:
                def __init__(self,options):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def extract_info(self,*args,**kwargs):return {'channel_id':OTHER,'entries':[]}
            with mock.patch.object(C,'runtime',return_value={}):runner=C.Runner(store,'fixture')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}):runner.enumerate_tab(stale,'shorts')
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT channel_id FROM accounts WHERE account_id='a'").fetchone()[0],CID)
                self.assertEqual(db.execute("SELECT status FROM tabs WHERE account_id='a' AND tab='shorts'").fetchone()[0],'failed')

    def test_legacy_bashar_route_constructs_tab_without_accepting_nonaccount_paths(self):
        literal='https://www.youtube.com/BasharChanneledbyDarrylAnka'
        self.assertEqual(C.supported_account_route(literal),literal)
        for unsupported in ('https://www.youtube.com/watch?v='+VID,'https://www.youtube.com/playlist?list=fixture',
                'https://www.youtube.com/results','https://www.youtube.com/feed/subscriptions',
                'https://www.youtube.com/shorts/'+VID,'https://www.youtube.com/youtubei',
                'https://www.youtube.com/../escape','https://www.youtube.com/%77atch',
                'https://example.org/BasharChanneledbyDarrylAnka'):
            with self.subTest(url=unsupported):self.assertIsNone(C.supported_account_route(unsupported))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';value=inventory(path)
            value['accounts'][0].update(channel_id=None,handles=[],urls=[literal]);C.save(path,value)
            store=C.Store(root/'raw');store.initialize(path);seen=[]
            class FakeYDL:
                def __init__(self,options):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def extract_info(self,url,download):seen.append(url);return {'channel_id':CID,'entries':[]}
            with store.connect() as db:account=dict(db.execute("SELECT * FROM accounts WHERE account_id='a'").fetchone())
            with mock.patch.object(C,'runtime',return_value={}):runner=C.Runner(store,'fixture')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}):runner.enumerate_tab(account,'videos')
            self.assertEqual(seen,[literal+'/videos'])
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT channel_id FROM accounts WHERE account_id='a'").fetchone()[0],CID)

    def test_zero_exit_decoder_with_error_is_rejected_and_timeout_process_reaped(self):
        original_popen=subprocess.Popen;children=[]
        info={'format':{'duration':'1'},'streams':[{'codec_type':'audio'}]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def launch_error(command,**kwargs):
                self.assertIn('-xerror',command);self.assertIn('explode',command)
                child=original_popen([sys.executable,'-c','import sys;sys.stdout.buffer.write(bytes(32000));sys.stderr.write("decoder error")'],**kwargs)
                children.append(child);return child
            with mock.patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(info))),mock.patch.object(C.subprocess,'Popen',side_effect=launch_error):
                with self.assertRaisesRegex(ValueError,'Strict full PCM'):C.verify_media(root/'fixture',root)
            self.assertIsNotNone(children[-1].poll());self.assertTrue(children[-1].stdout.closed)
            def launch_sleeper(command,**kwargs):
                child=original_popen([sys.executable,'-c','import time;time.sleep(60)'],**kwargs)
                children.append(child);return child
            with mock.patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(info))),mock.patch.object(C.subprocess,'Popen',side_effect=launch_sleeper),mock.patch.object(C.time,'monotonic',side_effect=[0,121]):
                with self.assertRaisesRegex(RuntimeError,'time budget'):C.verify_media(root/'fixture',root)
            self.assertIsNotNone(children[-1].poll());self.assertTrue(children[-1].stdout.closed)

    def test_boolean_duration_is_pending_and_never_downloaded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            class FakeYDL:
                def __init__(self,options):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                @staticmethod
                def sanitize_info(info):return info
                def extract_info(self,*args,**kwargs):return {'id':VID,'channel_id':CID,'duration':True,'title':'Fixture'}
                def process_ie_result(self,*args,**kwargs):raise AssertionError('Invalid duration cannot download')
            with mock.patch.object(C,'runtime',return_value={}):runner=C.Runner(store,'fixture')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}):self.assertFalse(runner.acquire(store.claim('fixture')))
            with store.connect() as db:
                row=db.execute('SELECT status,duration_seconds FROM videos').fetchone()
                self.assertEqual(tuple(row),('pending_duration',None))

    def test_caption_filter_controls_actual_passed_tracks(self):
        translated={'url':'https://example.org/sub?lang=es&tlang=en','ext':'json3'}
        original={'url':'https://example.org/sub?lang=en','ext':'vtt'}
        info={'subtitles':{'en':[translated,original]},'automatic_captions':{'en':[translated]},
            'requested_subtitles':{'en':translated}}
        selected=C.choose_caption(info);self.assertEqual(selected['tracks'],[original])
        passed=C.restrict_caption_tracks(info,selected)
        self.assertEqual(passed['subtitles'],{'en':[original]});self.assertEqual(passed['automatic_captions'],{})
        self.assertNotIn('requested_subtitles',passed);self.assertIn(translated,info['subtitles']['en'])

    def test_no_failed_reservation_release_when_acquire_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            class FakeYDL:
                def __init__(self,options):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                @staticmethod
                def sanitize_info(info):return info
                def extract_info(self,*args,**kwargs):return {'id':VID,'channel_id':CID,'duration':1,'title':'Other source'}
            with mock.patch.object(C,'runtime',return_value={'collector_sha256':'fixture'}):runner=C.Runner(store,'fixture-run')
            row=store.claim('fixture-run')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}),mock.patch.object(C.shutil,'disk_usage',return_value=SimpleNamespace(free=C.FLOOR+1)):
                runner.acquire(row)
            self.assertEqual(runner.budget.reserved,0);self.assertTrue(runner.stop.is_set())
            with store.connect() as db:self.assertEqual(db.execute('SELECT status FROM videos').fetchone()[0],'held_resource')

    def test_concurrent_reservations_preserve_shared_disk_floor(self):
        with tempfile.TemporaryDirectory() as temp:
            budget=C.Budget(Path(temp));amount=16*1024**2;barrier=threading.Barrier(2);results=[]
            def attempt():
                barrier.wait()
                try:budget.acquire(amount);results.append(True)
                except RuntimeError:results.append(False)
            with mock.patch.object(C.shutil,'disk_usage',return_value=SimpleNamespace(free=C.FLOOR+8*1024**2+amount+1)):
                workers=[threading.Thread(target=attempt) for _ in range(2)]
                for thread in workers:thread.start()
                for thread in workers:thread.join()
            self.assertEqual(sorted(results),[False,True]);self.assertEqual(budget.reserved,amount)
            budget.release(amount);self.assertEqual(budget.reserved,0)

    def test_enumeration_generator_failure_is_partial_not_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            def entries():
                yield {'id':VID,'title':'Fixture'}
                raise RuntimeError('continuation parse failed')
            class FakeYDL:
                def __init__(self,options):
                    assert options['ignoreerrors'] is False
                    assert not any(k in options for k in ('playlistend','playlist_items','daterange'))
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def extract_info(self,*args,**kwargs):return {'channel_id':CID,'entries':entries()}
            with store.connect() as db:account=dict(db.execute("SELECT * FROM accounts WHERE account_id='a'").fetchone())
            with mock.patch.object(C,'runtime',return_value={'collector_sha256':'fixture'}):runner=C.Runner(store,'fixture-run')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}):runner.enumerate_tab(account,'videos')
            with store.connect() as db:
                result=db.execute("SELECT * FROM tabs WHERE account_id='a' AND tab='videos'").fetchone()
                self.assertEqual(result['status'],'partial');self.assertEqual(result['returned_unique_ids'],1)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Local media tools unavailable')
    def test_full_decode_accepts_one_second_nonbashar_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'fixture.wav'
            subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000','-ac','1',str(path)],check=True)
            check=C.verify_media(path,root)
            self.assertEqual(check['decoded_pcm']['sample_count'],16000);self.assertAlmostEqual(check['duration_seconds'],1.)
            self.assertEqual(check['kind'],'audio')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Local media tools unavailable')
    def test_captionless_verified_media_unlocks_parallel_pilot_and_queues_asr(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            fixture=root/'fixture.wav'
            subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000','-ac','1',str(fixture)],check=True)
            class FakeYDL:
                def __init__(self,options):self.options=options
                def __enter__(self):return self
                def __exit__(self,*args):pass
                @staticmethod
                def sanitize_info(info):return info
                def extract_info(self,*args,**kwargs):return {'id':VID,'channel_id':CID,'duration':1,'title':'Other source'}
                def process_ie_result(self,info,download):
                    shutil.copyfile(fixture,Path(self.options['outtmpl']).parent/(VID+'.wav'));return info
            with mock.patch.object(C,'runtime',return_value={'collector_sha256':'fixture'}):runner=C.Runner(store,'fixture-run')
            with mock.patch.dict(sys.modules,{'yt_dlp':SimpleNamespace(YoutubeDL=FakeYDL)}):success=runner.acquire(store.claim('fixture-run'))
            self.assertTrue(success)
            with store.connect() as db:
                row=db.execute('SELECT status,asr_status FROM videos').fetchone()
                self.assertEqual(tuple(row),('audio_complete_asr_pending','queued'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM asr_queue').fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='transcript'").fetchone()[0],0)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Local media tools unavailable')
    def test_real_yt_dlp_local_http_audio_and_caption_pipeline(self):
        try:import yt_dlp
        except ImportError:self.skipTest('Optional yt-dlp runtime unavailable')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'inventory.json';inventory(path);store=C.Store(root/'raw');store.initialize(path)
            served=root/'served';served.mkdir();fixture=served/'fixture.wav'
            subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000','-ac','1',str(fixture)],check=True)
            C.save(served/'caption.json3',{'events':[{'tStartMs':0,'dDurationMs':1000,'segs':[{'utf8':'Local caption fixture.'}]}]})
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(served)))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            base='http://127.0.0.1:'+str(server.server_port)
            info={'id':VID,'title':'Local source fixture','channel_id':CID,'duration':1,'language':'en',
                'extractor':'Generic','extractor_key':'Generic','webpage_url':'https://www.youtube.com/watch?v='+VID,
                'formats':[{'format_id':'fixture','url':base+'/fixture.wav','ext':'wav','vcodec':'none','acodec':'pcm_s16le'}],
                'subtitles':{'en':[{'url':base+'/caption.json3','ext':'json3'}]}}
            try:
                with mock.patch.object(C,'runtime',return_value={}):runner=C.Runner(store,'fixture')
                # Only metadata extraction is replaced. The real installed
                # downloader, subtitle selection and processor use loopback HTTP.
                with mock.patch.object(yt_dlp.YoutubeDL,'extract_info',return_value=info):self.assertTrue(runner.acquire(store.claim('fixture')))
                with store.connect() as db:
                    self.assertEqual(db.execute('SELECT status FROM videos').fetchone()[0],'complete')
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM asr_queue').fetchone()[0],0)
                    artifact=db.execute("SELECT path FROM artifacts WHERE kind='transcript'").fetchone()
                    self.assertEqual(C.read(artifact[0])['text'],'Local caption fixture.')
            finally:server.shutdown();server.server_close();worker.join()


if __name__=='__main__':unittest.main()
