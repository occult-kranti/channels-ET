#!/usr/bin/env python3
"""No-network control tests; mock artifacts are removed and never research data."""
import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
import pathlib
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pipeline', HERE / 'channel_pipeline.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


def successful_fixture(path):
    p.save(path, {'records': [{'operation': 'watch_metadata_preflight', 'status': 'success', 'matching_video_id': True,
                              'http_status': 200, 'retrieved_at': p.now()}], 'blocked': False, 'fixture_only': True})


class Controls(unittest.TestCase):
    def test_blocked_and_stale_receipts_rejected_without_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'access.json'
            p.save(path, {'records': [{'status': 'blocked'}], 'blocked': True})
            with self.assertRaises(ValueError): p.require_access(path)
            successful_fixture(path); x=p.load(path);x['records'][0]['retrieved_at']='2020-01-01T00:00:00+00:00';p.save(path,x)
            with self.assertRaises(ValueError): p.require_access(path)

    def test_channels_resume_offset_and_complete_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);receipt=root/'access.json';successful_fixture(receipt)
            plan=root/'plan.json';p.save(plan,{'accounts':[{'id':'fixture-channel','url':'https://www.youtube.com/@fixture/videos','person_ids':['fixture-person']}]})
            args=argparse.Namespace(access_receipt=receipt,plan=plan,output=root/'output',person_id=[],max_jobs=1,batch_entries=2,timeout=10,delay=0)
            first=types.SimpleNamespace(returncode=0,stdout=json.dumps({'entries':[{'id':'abcdefghijk','title':'Fixture1'},{'id':'bcdefghijkl','title':'Fixture2'}]}),stderr='')
            second=types.SimpleNamespace(returncode=0,stdout=json.dumps({'entries':[{'id':'cdefghijklm','title':'Fixture3'}]}),stderr='')
            with patch.object(p.subprocess,'run',side_effect=[first,second]) as client:
                p.enumerate_channels(args);p.enumerate_channels(args)
            calls=[c.args[0] for c in client.call_args_list]
            self.assertEqual(calls[0][calls[0].index('--playlist-start')+1],'1')
            self.assertEqual(calls[1][calls[1].index('--playlist-start')+1],'3')
            self.assertTrue(p.state(args.output/'state.json')['channels']['fixture-channel']['complete_listing'])
            rows=[json.loads(line) for line in (args.output/'discovered-videos.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),3)
            self.assertTrue(all(r['actual_speaker_status']=='unknown_not_audio_verified' for r in rows))

    def test_channel_block_stops_next_job_and_is_not_zero_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);receipt=root/'access.json';successful_fixture(receipt)
            plan=root/'plan.json';p.save(plan,{'accounts':[{'id':str(i),'url':'https://www.youtube.com/@fixture/videos'} for i in range(2)]})
            args=argparse.Namespace(access_receipt=receipt,plan=plan,output=root/'output',person_id=[],max_jobs=2,batch_entries=2,timeout=10,delay=0)
            with patch.object(p.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout='',stderr='Fixture403Forbidden')) as client:
                result=p.enumerate_channels(args)
            self.assertEqual(client.call_count,1)
            self.assertTrue(result['has_failed_or_blocked_history'])
            self.assertEqual(p.state(args.output/'state.json')['channels']['0']['status'],'blocked')

    def test_unavailable_playlist_slots_do_not_fake_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);receipt=root/'access.json';successful_fixture(receipt)
            plan=root/'plan.json';p.save(plan,{'accounts':[{'id':'fixture','url':'https://www.youtube.com/@fixture/videos'}]})
            args=argparse.Namespace(access_receipt=receipt,plan=plan,output=root/'output',person_id=[],max_jobs=1,batch_entries=3,timeout=10,delay=0)
            response=types.SimpleNamespace(returncode=0,stdout=json.dumps({'entries':[{'id':'abcdefghijk'},None,{'id':'bcdefghijkl'}]}),stderr='')
            with patch.object(p.subprocess,'run',return_value=response):p.enumerate_channels(args)
            record=p.state(args.output/'state.json')['channels']['fixture']
            self.assertEqual(record['next_start'],4)
            self.assertFalse(record['complete_listing'])
            self.assertEqual(record['listed_entries'],3)
            self.assertEqual(record['usable_video_entries'],2)
            self.assertEqual(record['unusable_returned_slots'],1)

    def test_real_git_guard_and_reserved_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);(root/'.git').mkdir()
            self.assertFalse(p.inside_git(root/'raw'))
            (root/'.git/HEAD').write_text('ref: refs/heads/main\n')
            self.assertTrue(p.inside_git(root/'raw'))
            with self.assertRaises(ValueError):p.raw_directory(root/'raw')

    def test_quota_plan_unknown_durations_and_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            rows=[{'video_id':'abcdefghijk','duration_seconds':60},{'video_id':'bcdefghijkl','duration_seconds':float('nan')},
                  {'video_id':'cdefghijklm','duration_seconds':None},{'video_id':'defghijklmn','duration_seconds':10000}]
            with patch.object(p.subprocess,'Popen') as execute:
                result=p.media_plan(rows,pathlib.Path(directory),5_000_000,0,2_000_000)
                execute.assert_not_called()
            self.assertEqual([r['eligible'] for r in result['records']],[True,False,False,False])
            self.assertTrue(result['dry_run'])

    def test_full_channel_and_media_command_controls(self):
        full=p.channel_command('https://www.youtube.com/@fixture/videos',12,0)
        self.assertNotIn('--playlist-end',full);self.assertIn('--skip-download',full)
        command=p.download_command({'video_id':'abcdefghijk','source_url':'https://www.youtube.com/watch?v=abcdefghijk'},pathlib.Path('/tmp/fixture'),100)
        self.assertIn('--max-filesize',command);self.assertIn('--limit-rate',command)
        self.assertNotIn('--cookies',command);self.assertNotIn('--proxy',command)

    def test_local_corpus_index_does_not_invent_text(self):
        con=sqlite3.connect(HERE/'corpus-index.sqlite')
        self.assertEqual(con.execute('SELECT COUNT(*) FROM videos').fetchone()[0],925)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM transcript_artifacts').fetchone()[0],0)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM videos WHERE actual_speaker_status != ?',('unknown_not_audio_verified',)).fetchone()[0],0)
        self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok');con.close()

    def test_error_sanitization(self):
        text=p.sanitized('https://user:password@example.com/media?sig=secret-value authorization=secret')
        self.assertNotIn('secret-value',text);self.assertNotIn('authorization=secret',text);self.assertNotIn('user:password',text)

    def test_video_input_normalizes_id_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            source=pathlib.Path(directory)/'videos.json'
            p.save(source,{'records':[{'id':'abcdefghijk','duration_seconds':1},{'video_id':'abcdefghijk','duration_seconds':1}]})
            rows=p.video_inputs(argparse.Namespace(input=source))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['video_id'],'abcdefghijk')
            plan=p.media_plan(rows,pathlib.Path(directory)/'raw',1_000_000,0,1_000_000)
            self.assertEqual(plan['records'][0]['video_id'],'abcdefghijk')

    def test_fast_finished_download_still_checks_actual_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);receipt=root/'access.json';successful_fixture(receipt)
            source=root/'videos.json';p.save(source,{'records':[{'video_id':'abcdefghijk','duration_seconds':1}]})
            args=argparse.Namespace(raw_dir=root/'raw',input=source,max_jobs=1,quota_gib=1,reserve_gib=0,max_file_mib=1,
                                    execute=True,access_receipt=receipt,output=root/'output',timeout=10,delay=0)
            class Finished:
                def __init__(self,*unused,**kwargs):
                    media=root/'raw/media';media.mkdir(parents=True,exist_ok=True)
                    (media/'abcdefghijk.webm').write_bytes(b'x'*(1024*1024+1))
                def poll(self):return 0
                def wait(self,timeout=None):return 0
            with patch.object(p.subprocess,'Popen',Finished):result=p.media(args)
            record=p.state(args.output/'state.json')['media']['abcdefghijk']
            self.assertEqual(record['status'],'quota_stopped')
            self.assertEqual(record['reason'],'post_exit_disk_or_file_limit')
            self.assertNotIn('artifacts',record)
            self.assertFalse(record['post_exit_validation']['within_storage_limits'])
            self.assertEqual(len(record['observed_local_files']),1)
            self.assertEqual(result['media_videos_success'],0)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    p.save(HERE/'pipeline-verification.json',{'checked_at':p.now(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'status':'PASS' if result.wasSuccessful() else 'FAIL','network_requests':0,
            'basis':'Mock collection controls and local metadata integrity only; not empirical source acquisition or media download.'})
    raise SystemExit(not result.wasSuccessful())
