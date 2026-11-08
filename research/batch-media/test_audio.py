"""Local synthetic signal/receipt tests; none are empirical source downloads."""
import copy
from array import array
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

SPEC = importlib.util.spec_from_file_location('batch_audio', Path(__file__).with_name('audio.py'))
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def write_wav(path, values, *, rate=16000, channels=1):
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(array('h', values).tobytes())


class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix='channels-audio-fixtures-')
        cls.base = Path(cls.root.name)
        cls.video = cls.base / 'synthetic-300-second-video.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=16x16:r=1',
                        '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono', '-t', '300',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-b:a', '16k',
                        '-shortest', str(cls.video)], capture_output=True, check=True, timeout=30)
        cls.video_duration = A.probe_media(cls.video)['duration_seconds']

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='channels-audio-case-')
        self.folder = Path(self.temp.name)
        self.wave = self.folder / 'synthetic-wave.wav'
        write_wav(self.wave, [0] * 16000 + [8192, -8192] * 8000)

    def tearDown(self):
        self.temp.cleanup()

    def record(self, *, youtube=False):
        source = self.video if youtube else self.wave
        source_id = 'youtube:abcdefghijk' if youtube else 'synthetic-fixture:audio'
        row = {'provider': 'youtube' if youtube else 'publisher_rss', 'source_id': source_id,
               'medium_id': 'synthetic-context', 'channel_id': 'synthetic-publisher',
               'kind': 'video' if youtube else 'audio', 'local_path': str(source),
               'sha256': A.sha256(source), 'bytes': source.stat().st_size,
               'source_language': 'en', 'fixture_scope': 'Generated signal; not actual publisher or YouTube evidence'}
        validation = {'ffprobe_duration_seconds': self.video_duration if youtube else 2.0}
        if youtube:
            row.update(video_id='abcdefghijk', duration_seconds=self.video_duration, is_short=False,
                       duration_scope='source_video', metadata_refreshed_at_acquisition=True)
            validation.update(source_video_id='abcdefghijk', metadata_sha256='1' * 64)
        proof = self.folder / 'source-proof.json'
        A.atomic_json(proof, {'fixture_only': True, 'verified_artifacts': [A.artifact(source, source_id, row['kind'], validation=validation)]})
        row['verification_receipt'] = {'path': str(proof), 'sha256': A.sha256(proof)}
        return row

    def test_known_rms_and_sample_weighted_quiet_duration(self):
        result = A.audio_metrics(self.wave)
        self.assertEqual(result['sample_count'], 32000)
        self.assertAlmostEqual(result['rms_fraction_full_scale'], .25 / math.sqrt(2), places=12)
        self.assertAlmostEqual(result['rms_dbfs'], 20 * math.log10(.25 / math.sqrt(2)), places=10)
        self.assertEqual(result['sample_peak_fraction_full_scale'], .25)
        self.assertEqual(result['quiet_duration_seconds'], 1)
        self.assertEqual(result['quiet_sample_fraction'], .5)
        self.assertEqual(result['longest_contiguous_quiet_seconds'], 1)
        self.assertEqual(result['quiet_runs_at_least_half_second'], 1)
        self.assertEqual(result['dc_offset_fraction_full_scale'], 0)

    def test_partial_final_window_uses_samples_not_windows(self):
        write_wav(self.wave, [1000] * 320 + [0] * 160)
        result = A.audio_metrics(self.wave)
        self.assertEqual(result['total_windows'], 2)
        self.assertEqual(result['quiet_windows'], 1)
        self.assertEqual(result['quiet_sample_fraction'], 1 / 3)
        self.assertEqual(result['quiet_duration_seconds'], .01)
        self.assertEqual(result['quiet_runs_at_least_half_second'], 0)

    def test_exact_zero_is_finite_json_with_null_dbfs(self):
        write_wav(self.wave, [0] * 8000)
        result = A.audio_metrics(self.wave)
        self.assertIsNone(result['rms_dbfs'])
        self.assertIsNone(result['sample_peak_dbfs'])
        self.assertEqual(result['quiet_sample_fraction'], 1)
        self.assertEqual(result['quiet_runs_at_least_half_second'], 1)
        json.dumps(result, allow_nan=False)

    def test_near_full_scale_count_includes_both_polarities(self):
        write_wav(self.wave, [32767, -32768, 32000, -32000])
        result = A.audio_metrics(self.wave)
        self.assertEqual(result['near_full_scale_samples'], 2)
        self.assertEqual(result['near_full_scale_sample_fraction'], .5)
        self.assertEqual(result['sample_peak_fraction_full_scale'], 1)

    def test_quiet_threshold_is_inclusive_and_window_based(self):
        write_wav(self.wave, [327] * 320 + [328] * 320)
        result = A.audio_metrics(self.wave)
        self.assertEqual(result['quiet_windows'], 1)
        self.assertEqual(result['quiet_samples'], 320)

    def test_metrics_refuse_unconverted_sample_rate(self):
        write_wav(self.wave, [1] * 8000, rate=8000)
        with self.assertRaises(ValueError):
            A.audio_metrics(self.wave)

    def test_metrics_refuse_empty_audio(self):
        write_wav(self.wave, [])
        with self.assertRaises(ValueError):
            A.audio_metrics(self.wave)

    def test_decode_resamples_actual_audio_without_source_mutation(self):
        write_wav(self.wave, [1000, -1000] * 4000, rate=8000)
        original = A.sha256(self.wave)
        target = self.folder / 'decoded.wav'
        duration = A.decode_audio(self.wave, target, 1, reserve_bytes=0)
        self.assertEqual(duration, 1)
        self.assertEqual(A.audio_metrics(target)['sample_count'], 16000)
        self.assertEqual(A.sha256(self.wave), original)

    def test_decode_enforces_space_reserve_and_no_overwrite(self):
        with patch.object(A.shutil, 'disk_usage', return_value=SimpleNamespace(free=1024)):
            with self.assertRaisesRegex(ValueError, 'Insufficient disk'):
                A.decode_audio(self.wave, self.folder / 'decoded.wav', 2)
        target = self.folder / 'decoded.wav'
        A.decode_audio(self.wave, target, 2, reserve_bytes=0)
        before = A.sha256(target)
        with self.assertRaises(ValueError):
            A.decode_audio(self.wave, target, 2, reserve_bytes=0)
        self.assertEqual(A.sha256(target), before)

    def test_html_response_is_not_media(self):
        bad = self.folder / 'html-disguised-as-video.mp4'
        bad.write_text('<html>Access unavailable</html>')
        with self.assertRaises(ValueError):
            A.probe_media(bad)

    def test_source_hash_and_size_both_required(self):
        row = self.record()
        for key, value in [('sha256', 'f' * 64), ('bytes', row['bytes'] + 1), ('bytes', True)]:
            changed = {**row, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                A.validate_record(changed)

    def publisher_audio_record(self, duration=300):
        row=self.record();row.update(provider='publisher_audio',duration_seconds=duration)
        proof=Path(row['verification_receipt']['path']);data=json.loads(proof.read_text())
        acquired=self.folder/'acquisition.json'
        acquired.write_text(json.dumps({'status':'completed','source_id':row['source_id'],'duration_seconds':duration,
            'audio':{'path':row['local_path'],'sha256':row['sha256'],'bytes':row['bytes']},'fixture_only':True}))
        data['acquisition_receipt']={'path':str(acquired),'sha256':A.sha256(acquired)}
        item=data['verified_artifacts'][0];item['provider']='publisher_audio'
        item['validation'].update(source_id=row['source_id'],acquisition_receipt_sha256=A.sha256(acquired),ffprobe_duration_seconds=duration)
        proof.write_text(json.dumps(data));row['verification_receipt']['sha256']=A.sha256(proof)
        return row

    def test_publisher_audio_is_distinct_from_rss_and_video(self):
        row=self.publisher_audio_record()
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'}]}):
            self.assertEqual(A.validate_record(row)[0]['provider'],'publisher_audio')

    def test_publisher_audio_rejects_short_actual_audio_despite_long_declared_duration(self):
        row=self.publisher_audio_record()
        with self.assertRaisesRegex(ValueError,'short or its source'):
            A.validate_record(row)

    def test_publisher_audio_rejects_missing_acquisition_binding(self):
        row=self.publisher_audio_record();proof=Path(row['verification_receipt']['path']);data=json.loads(proof.read_text())
        del data['verified_artifacts'][0]['validation']['acquisition_receipt_sha256']
        proof.write_text(json.dumps(data));row['verification_receipt']['sha256']=A.sha256(proof)
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'}]}):
            with self.assertRaisesRegex(ValueError,'original acquisition'):
                A.validate_record(row)

    def test_publisher_audio_rejects_changed_provider_or_kind(self):
        row=self.publisher_audio_record();proof=Path(row['verification_receipt']['path']);data=json.loads(proof.read_text())
        del data['verified_artifacts'][0]['provider']
        proof.write_text(json.dumps(data));row['verification_receipt']['sha256']=A.sha256(proof)
        with self.assertRaisesRegex(ValueError,'proof-bound audio provider'):
            A.validate_record(row)

    def test_publisher_audio_rejects_a_video_stream(self):
        row=self.publisher_audio_record()
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'},{'codec_type':'video'}]}):
            with self.assertRaisesRegex(ValueError,'audio-only track'):
                A.validate_record(row)

    def test_publisher_audio_rejects_invented_acquisition_sha(self):
        row=self.publisher_audio_record();proof=Path(row['verification_receipt']['path']);data=json.loads(proof.read_text())
        data['verified_artifacts'][0]['validation']['acquisition_receipt_sha256']='2'*64
        proof.write_text(json.dumps(data));row['verification_receipt']['sha256']=A.sha256(proof)
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'}]}):
            with self.assertRaisesRegex(ValueError,'missing or contradictory'):
                A.validate_record(row)

    def test_publisher_audio_rejects_changed_acquisition_bytes(self):
        row=self.publisher_audio_record();p=self.folder/'acquisition.json';p.write_text(p.read_text()+' ')
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'}]}):
            with self.assertRaisesRegex(ValueError,'acquisition receipt bytes differ'):
                A.validate_record(row)

    def test_publisher_audio_rejects_acquisition_of_another_source(self):
        row=self.publisher_audio_record();p=self.folder/'acquisition.json';acquired=json.loads(p.read_text());acquired['source_id']='another:source';p.write_text(json.dumps(acquired))
        proof=Path(row['verification_receipt']['path']);data=json.loads(proof.read_text());data['acquisition_receipt']['sha256']=A.sha256(p)
        data['verified_artifacts'][0]['validation']['acquisition_receipt_sha256']=A.sha256(p)
        proof.write_text(json.dumps(data));row['verification_receipt']['sha256']=A.sha256(proof)
        with patch.object(A,'probe_media',return_value={'duration_seconds':300,'streams':[{'codec_type':'audio'}]}):
            with self.assertRaisesRegex(ValueError,'this completed original audio'):
                A.validate_record(row)

    def test_custom_reserve_is_passed_to_decode_and_bound_in_receipt(self):
        row=self.record();output=self.folder/'reserve-output'
        with patch.object(A,'decode_audio',wraps=A.decode_audio) as decoder:
            path,receipt,_=A.process_record(row,output,min_free_bytes=12345)
        self.assertEqual(decoder.call_args.kwargs['reserve_bytes'],12345)
        self.assertEqual(receipt['binding']['storage']['min_free_bytes'],12345)
        self.assertTrue(receipt['binding']['storage']['retain_decoded_audio'])

    def test_discarded_new_derivative_is_audited_and_result_reuses(self):
        row=self.record();original=A.sha256(self.wave);output=self.folder/'compact-output'
        path,receipt,_=A.process_record(row,output,min_free_bytes=0,retain_decoded_audio=False)
        discarded=[x for x in receipt['verified_artifacts'] if x.get('retained') is False]
        self.assertEqual(len(discarded),1);self.assertFalse(Path(discarded[0]['local_path']).exists())
        self.assertEqual(discarded[0]['derived_from_sha256'],original)
        self.assertEqual(A.sha256(self.wave),original)
        self.assertNotIn(discarded[0]['local_path'],[x['local_path'] for x in A.final_artifacts(row,path,receipt)])
        with patch.object(A,'decode_audio',side_effect=AssertionError('No repeat decode')):
            _,again,reused=A.process_record(row,output,min_free_bytes=0,retain_decoded_audio=False)
        self.assertTrue(reused)

    def test_retention_flag_cannot_hide_missing_original(self):
        row=self.record();path,receipt,_=A.process_record(row,self.folder/'bad-retention',min_free_bytes=0,retain_decoded_audio=False)
        receipt['verified_artifacts'][0]['retained']=False
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'Only the explicitly discarded'):
            A.verify_completed(path,receipt['binding'])

    def test_failed_processing_does_not_remove_derivative(self):
        row=self.record();output=self.folder/'failure-retention'
        with patch.object(A,'audio_metrics',side_effect=RuntimeError('Synthetic output failure')):
            with self.assertRaises(RuntimeError):
                A.process_record(row,output,min_free_bytes=0,retain_decoded_audio=False)
        self.assertEqual(len(list(output.glob('sources/*/*/audio-16khz-mono.wav'))),1)
        self.assertTrue(self.wave.exists())

    def test_invalid_disk_reserve_is_rejected_before_processing(self):
        for reserve in (-1,True,1.5):
            with self.subTest(reserve=reserve),self.assertRaisesRegex(ValueError,'nonnegative integer'):
                A.process_record({},self.folder/'invalid',min_free_bytes=reserve)

    def test_receipt_must_bind_matching_source(self):
        row = self.record()
        proof = Path(row['verification_receipt']['path'])
        data = json.loads(proof.read_text())
        data['verified_artifacts'][0]['source_id'] = 'different-source'
        proof.write_text(json.dumps(data))
        row['verification_receipt']['sha256'] = A.sha256(proof)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            A.validate_record(row)

    def test_receipt_mutation_or_duplicate_binding_fails(self):
        row = self.record()
        proof = Path(row['verification_receipt']['path'])
        proof.write_text(proof.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            A.validate_record(row)
        data = json.loads(proof.read_text())
        data['verified_artifacts'].append(copy.deepcopy(data['verified_artifacts'][0]))
        proof.write_text(json.dumps(data))
        row['verification_receipt']['sha256'] = A.sha256(proof)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            A.validate_record(row)

    def test_proof_bound_language_provider_and_context_cannot_be_erased(self):
        row = self.record()
        proof = Path(row['verification_receipt']['path'])
        data = json.loads(proof.read_text())
        data['verified_artifacts'][0].update(provider='publisher_rss', medium_id='synthetic-context',
                                             channel_id='synthetic-publisher', source_language='ja',
                                             source_language_status='declared')
        proof.write_text(json.dumps(data))
        row['verification_receipt']['sha256'] = A.sha256(proof)
        row.update(source_language='ja', source_language_status='declared')
        A.validate_record(row)
        for key, value in [('source_language', 'unknown'), ('source_language_status', 'missing'),
                           ('provider', 'publisher_video'), ('medium_id', 'other-context'), ('channel_id', 'other-channel')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'proof-bound'):
                A.validate_record({**row, key: value})
        omitted = dict(row)
        del omitted['source_language']
        with self.assertRaisesRegex(ValueError, 'proof-bound'):
            A.validate_record(omitted)

    def test_source_paths_reject_symlinks_traversal_and_git(self):
        link = self.folder / 'linked.wav'
        link.symlink_to(self.wave)
        with self.assertRaises(ValueError):
            A.private_path(link, exists=True)
        with self.assertRaises(ValueError):
            A.private_path(str(self.folder) + '/../private.wav')
        repo = self.folder / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        with self.assertRaises(ValueError):
            A.private_path(repo / 'hidden-transcript.txt')
        with self.assertRaises(ValueError):
            A.private_path('relative.mp3')

    def test_youtube_requires_video_identity_fresh_metadata_and_long_form(self):
        row = self.record(youtube=True)
        accepted, media = A.validate_record(row)
        self.assertEqual(accepted['provider'], 'youtube')
        self.assertGreaterEqual(media['duration_seconds'], 300)
        for key, value in [('video_id', 'xxxxxxxxxxx'), ('is_short', True), ('is_short', 0),
                           ('metadata_refreshed_at_acquisition', False), ('duration_seconds', 299),
                           ('duration_scope', 'clip')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                A.validate_record({**row, key: value})

    def test_video_with_only_audio_is_rejected(self):
        row = self.record()
        row['kind'] = 'video'
        proof = Path(row['verification_receipt']['path'])
        data = json.loads(proof.read_text())
        data['verified_artifacts'][0]['kind'] = 'video'
        proof.write_text(json.dumps(data))
        row['verification_receipt']['sha256'] = A.sha256(proof)
        with self.assertRaisesRegex(ValueError, 'both video and audio'):
            A.validate_record(row)

    def test_publisher_video_stays_distinct(self):
        row = self.record(youtube=True)
        row['provider'] = 'publisher_video'
        row['source_id'] = 'publisher:synthetic-video'
        row.pop('video_id')
        proof = Path(row['verification_receipt']['path'])
        data = json.loads(proof.read_text())
        data['verified_artifacts'][0]['source_id'] = row['source_id']
        proof.write_text(json.dumps(data))
        row['verification_receipt']['sha256'] = A.sha256(proof)
        accepted, _ = A.validate_record(row)
        self.assertEqual(accepted['provider'], 'publisher_video')
        self.assertNotIn('video_id', accepted)

    def test_timestamp_rollover_and_srt_format(self):
        self.assertEqual(A.timestamp(59.9996), '00:01:00.000')
        self.assertEqual(A.timestamp(3661.025, srt=True), '01:01:01,025')
        for bad in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                A.timestamp(bad)

    def test_segment_timing_rejects_regression_or_out_of_range(self):
        good = SimpleNamespace(start=.5, end=1.3, text=' synthetic text ', avg_logprob=-.1, no_speech_prob=.02)
        self.assertEqual(A.normalize_segments([good], 2)[0]['text'], 'synthetic text')
        for bad in [SimpleNamespace(start=1.5, end=1.4, text='bad'),
                    SimpleNamespace(start=0, end=10, text='bad'),
                    SimpleNamespace(start=float('nan'), end=1, text='bad')]:
            with self.assertRaises(ValueError):
                A.normalize_segments([bad], 2)
        with self.assertRaises(ValueError):
            A.normalize_segments([good, SimpleNamespace(start=.1, end=.4, text='out of order')], 2)

    def test_timestamp_failure_retains_exact_numeric_reason(self):
        values = [SimpleNamespace(start=.5, end=1, text='first'),
                  SimpleNamespace(start=.499999999999, end=1.2, text='regression')]
        with self.assertRaises(A.TimestampValidationError) as caught:
            A.normalize_segments(values, 2)
        self.assertEqual(caught.exception.diagnostic['reason'], 'start_regression')
        self.assertEqual(caught.exception.diagnostic['start_repr'], '0.499999999999')
        self.assertEqual(caught.exception.diagnostic['segment_index'], 1)

    def test_diagnostic_inference_exhausts_failed_stream_without_admission(self):
        source = [SimpleNamespace(start=.5, end=1, text='first'),
                  SimpleNamespace(start=.4, end=1.2, text='bad ordering'),
                  SimpleNamespace(start=1.3, end=1.8, text='retained after failure')]
        info = SimpleNamespace(language='en', language_probability=1, duration=2, duration_after_vad=2)
        engine = SimpleNamespace(model=SimpleNamespace(is_multilingual=False),
                                 transcribe=lambda *args, **kwargs: (iter(source), info))
        fake = SimpleNamespace(WhisperModel=lambda *args, **kwargs: engine)
        A.atomic_json(self.folder / 'request.json', {'fixture': 'synthetic mocked ASR'})
        with patch.dict('sys.modules', {'faster_whisper': fake}), self.assertRaises(A.TimestampValidationError):
            A.run_asr(self.wave, self.folder, 2, A.language_plan({'source_language': 'en'},
                      {'language_mode': 'english-only'}, 'en'), diagnostics=self.folder)
        report = json.loads((self.folder / 'asr-diagnostic-completion.json').read_text())
        self.assertTrue(report['inference_stream_exhausted'])
        self.assertEqual(report['raw_segment_count'], 3)
        self.assertEqual(report['status'], 'diagnostic_only_not_admitted')
        self.assertEqual(report['raw_segments']['sha256'], A.sha256(self.folder / 'asr-raw-segments.jsonl'))
        self.assertFalse((self.folder / 'receipt.json').exists())

    def test_explicit_terminal_recovery_preserves_words_order_and_original_times(self):
        raw = [{'segment_index': 0, 'start_repr': '1.0', 'end_repr': '2.0', 'text': 'first fixture'},
               {'segment_index': 1, 'start_repr': '94.73', 'end_repr': '110.01', 'text': 'last fixture'}]
        original = copy.deepcopy(raw)
        rows, quality = A.repair_terminal_end(raw, 102.6453125)
        self.assertEqual(raw, original)
        self.assertEqual([r['text'] for r in rows], ['first fixture', 'last fixture'])
        self.assertEqual(rows[0]['end_seconds'], 2)
        self.assertEqual(rows[-1]['end_seconds'], 102.6453125)
        self.assertEqual(rows[-1]['original_end_seconds'], 110.01)
        self.assertAlmostEqual(quality['timestamp_maximum_adjustment_seconds'], 7.3646875)
        self.assertFalse(quality['text_changed_by_repair'])
        self.assertTrue(quality['terminal_text_alignment_unverified'])

    def test_terminal_recovery_rejects_other_anomalies_and_broad_clamping(self):
        good = {'segment_index': 0, 'start_repr': '1', 'end_repr': '2', 'text': 'first'}
        terminal = {'segment_index': 1, 'start_repr': '94', 'end_repr': '110', 'text': 'last'}
        for changed in [dict(terminal, start_repr='101'), dict(terminal, start_repr='69'),
                        dict(terminal, end_repr='131'), dict(terminal, end_repr='99'),
                        dict(terminal, end_repr='nan'), dict(terminal, text=''),
                        dict(terminal, segment_index=2)]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                A.repair_terminal_end([good, changed], 100)
        with self.assertRaises(ValueError):
            A.repair_terminal_end([dict(good, start_repr='97', end_repr='98'), terminal], 100)
        with self.assertRaises(ValueError):
            A.repair_terminal_end([dict(good, end_repr='105'), terminal], 100)
        with self.assertRaises(ValueError):
            A.repair_terminal_end([dict(good, end_repr='100.5'), terminal], 100)
        with self.assertRaises(ValueError):
            A.repair_terminal_end([good, terminal], 100, max_overrun_seconds=31)

    def test_english_model_rejects_non_english_and_auto(self):
        model = {'language_mode': 'english-only'}
        self.assertEqual(A.language_plan({'source_language': 'en'}, model, 'en')['source_language'], 'en')
        for row, requested in [({'source_language': 'ja'}, 'en'), ({'source_language': 'en'}, 'auto'), ({}, 'es')]:
            with self.assertRaises(ValueError):
                A.language_plan(row, model, requested)
        self.assertIn('unknown', A.language_plan({}, model, 'en')['assumption'])

    def test_multilingual_model_accepts_explicit_auto_and_discloses_it(self):
        model = {'language_mode': 'multilingual'}
        plan = A.language_plan({'source_language': 'ja'}, model, 'auto')
        self.assertIsNone(plan['effective_language_argument'])
        self.assertTrue(plan['automatic_language_detection'])
        with self.assertRaises(ValueError):
            A.language_plan({'source_language': 'ja'}, model, 'en')

    def test_invalid_or_conflicting_language_is_not_english_assumption(self):
        for status in ('invalid', 'conflicting'):
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, 'Resolve'):
                A.language_plan({'source_language': 'unknown', 'source_language_status': status},
                                {'language_mode': 'english-only'}, 'en')
        plan = A.language_plan({'source_language': 'unknown', 'source_language_status': 'conflicting'},
                               {'language_mode': 'multilingual'}, 'auto')
        self.assertEqual(plan['source_language_status'], 'conflicting')
        self.assertTrue(plan['automatic_language_detection'])

    def test_local_model_required_no_download_name(self):
        with self.assertRaises(ValueError):
            A.local_model_binding('tiny.en')
        missing = self.folder / 'missing-model'
        with self.assertRaises(ValueError):
            A.local_model_binding(missing)

    def test_model_contract_hashes_and_added_tokens(self):
        folder = self.folder / 'model'
        folder.mkdir()
        for name, text in [('config.json', '{}'), ('model.bin', 'fixture-not-real-weights'),
                           ('vocabulary.txt', 'fixture'), ('tokenizer.json', json.dumps({'model': {'vocab': {'<|endoftext|>': 50256}},
                            'added_tokens': [{'content': '<|startoftranscript|>', 'id': 50257}]}))]:
            (folder / name).write_text(text)
        binding = A.local_model_binding(folder)
        self.assertEqual(binding['language_mode'], 'english-only')
        self.assertEqual(len(binding['files']), 4)
        (folder / 'model.bin').write_text('changed-fixture')
        self.assertNotEqual(A.local_model_binding(folder)['files_sha256'], binding['files_sha256'])

    def test_actual_metrics_result_and_completed_resume(self):
        row = self.record()
        output = self.folder / 'results'
        output.mkdir()
        receipt_path, receipt, reused = A.process_record(row, output)
        self.assertFalse(reused)
        self.assertEqual(receipt['status'], 'completed_metrics_only')
        self.assertEqual(receipt['network_requests'], 0)
        self.assertEqual(len(receipt['verified_artifacts']), 4)
        before = A.sha256(receipt_path)
        with patch.object(A, 'decode_audio', side_effect=AssertionError('A verified resume must not decode again')):
            again_path, again, reused = A.process_record(row, output)
        self.assertTrue(reused)
        self.assertEqual(A.sha256(again_path), before)
        self.assertEqual(again, receipt)
        storage = A.final_artifacts(row, receipt_path, receipt)
        self.assertEqual(len(storage), 4)
        for item in storage:
            self.assertEqual(item['verification_receipt']['sha256'], before)
            self.assertEqual(item['provider'], 'publisher_rss')

    def test_mutated_completed_output_is_not_silently_rebuilt(self):
        row = self.record()
        output = self.folder / 'results'
        output.mkdir()
        path, receipt, _ = A.process_record(row, output)
        generated = Path(receipt['verified_artifacts'][2]['local_path'])
        generated.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            A.process_record(row, output)
        self.assertEqual(generated.read_text(), 'changed')

    def test_incomplete_attempt_is_not_silently_reused(self):
        row = self.record()
        output = self.folder / 'results'
        output.mkdir()
        with patch.object(A, 'decode_audio', side_effect=ValueError('synthetic interruption')):
            with self.assertRaises(ValueError):
                A.process_record(row, output)
        with self.assertRaisesRegex(ValueError, 'Incomplete prior attempt'):
            A.process_record(row, output)

    def test_changed_proof_during_processing_prevents_completed_receipt(self):
        row = self.record()
        proof = Path(row['verification_receipt']['path'])
        original_metrics = A.audio_metrics
        def changed_proof(path):
            result = original_metrics(path)
            proof.write_text(proof.read_text() + ' ')
            return result
        output = self.folder / 'results'
        output.mkdir()
        with patch.object(A, 'audio_metrics', side_effect=changed_proof):
            with self.assertRaisesRegex(ValueError, 'proof changed'):
                A.process_record(row, output)
        self.assertEqual(list(output.rglob('receipt.json')), [])

    def test_empty_batch_exports_empty_artifacts_not_successful_downloads(self):
        manifest = self.folder / 'input.json'
        A.atomic_json(manifest, {'schema_version': 1, 'batch_id': 'empty-fixture', 'records': []})
        result = A.run_batch(manifest, self.folder / 'output')
        self.assertEqual(result['artifacts'], 0)
        self.assertEqual(result['records'], [])
        self.assertEqual(json.loads((self.folder / 'output/final-artifacts.json').read_text())['artifacts'], [])

    def test_batch_duplicate_is_reported_and_does_not_duplicate_artifacts(self):
        row = self.record()
        manifest = self.folder / 'input.json'
        A.atomic_json(manifest, {'schema_version': 1, 'batch_id': 'duplicate-fixture', 'records': [row, row]})
        result = A.run_batch(manifest, self.folder / 'output')
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['artifacts'], 4)
        self.assertIn('Duplicate', result['records'][1]['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
