#!/usr/bin/env python3
"""Independent synthetic harvest regressions; never contact a source service."""
from __future__ import annotations
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / 'harvest.py'
WORKER_SHA = hashlib.sha256(WORKER.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('independent_harvest', WORKER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
checks = []
CAPS = {k: 1024 * 1024 for k in ('metadata', 'captions', 'video', 'audio', 'channel')}


def case(name, fn):
    try:
        detail = fn()
        checks.append({'name': name, 'status': 'PASS', 'detail': detail})
    except Exception as error:
        checks.append({'name': name, 'status': 'FAIL', 'error': type(error).__name__ + ': ' + str(error)})


def store(root, quota=100 * 1024 ** 2):
    return h.Store(root / 'state.sqlite', root / 'raw', quota=quota, reserve=0)


def add_video(s, ident='abcdefghijk'):
    with s.connect() as c:
        s.add_video(c, {'video_id': ident, 'title': 'Synthetic regression fixture'})


def metadata(s, ident='abcdefghijk'):
    j = s.claim('fixture-owner', 'metadata', CAPS, 30)
    d = s.job_dir(j)
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'info.json'
    p.write_text(json.dumps({'id': ident, 'duration': 2}))
    s.finish(j, {'status': 'succeeded'}, [{'path': p, 'type': 'metadata', 'complete': True}])
    return p


with tempfile.TemporaryDirectory(prefix='harvest-independent-final-', dir='/tmp') as scratch:
    scratch = Path(scratch)

    def missing():
        s = store(scratch / 'missing'); add_video(s); p = metadata(s); p.unlink()
        report = s.export(scratch / 'missing-export')
        assert report['artifacts_by_type']['metadata'] == 0
        assert s.claim('fixture-next', 'metadata', CAPS, 30) is not None
        return 'Deleted output invalidated and source job became claimable.'
    case('missing completed artifact is not trusted', missing)

    def altered():
        s = store(scratch / 'altered'); add_video(s); p = metadata(s)
        stat = p.stat(); original = p.read_bytes(); p.write_bytes(original.replace(b'2', b'3'))
        os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        invalid = s.reconcile_artifacts(full_hash=True)
        assert invalid and invalid[0]['reason'] == 'artifact_hash_changed'
        return 'Same-sized, timestamp-preserved corruption detected by full resume hash.'
    case('resume full hash catches same-size corruption', altered)

    def partial():
        s = store(scratch / 'partial'); add_video(s)
        j = s.claim('fixture-owner', 'captions', CAPS, 30)
        s.finish(j, {'status': 'partial', 'failures': [{'status': 'retryable'}]})
        with s.connect() as c: c.execute('UPDATE jobs SET next_attempt=0 WHERE id=?', (j['id'],))
        assert s.claim('fixture-next', 'captions', CAPS, 30) is not None
        return 'Partial captions remain resumable after backoff.'
    case('partial caption jobs resume', partial)

    def reservation():
        s = store(scratch / 'reservation', quota=300)
        add_video(s); add_video(s, 'bcdefghijkl')
        a = s.claim('A', 'captions', {'captions': 100}, 30)
        s.claim('B', 'captions', {'captions': 100}, 30)
        d = s.job_dir(a); d.mkdir(parents=True); (d / 'overrun').write_bytes(b'x' * 150)
        with s.connect() as c: assert s.capacity(c, 100) is False
        return '150 actual + 100 remaining + 100 proposed exceeds quota 300.'
    case('one overrun cannot consume another reservation', reservation)

    def tmp_race():
        target = scratch / 'concurrent.json'; barrier = threading.Barrier(2)
        original = Path.replace
        def coordinated(path, destination):
            if Path(destination) == target: barrier.wait(timeout=5)
            return original(path, destination)
        with mock.patch.object(Path, 'replace', coordinated):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(h.save, target, {'writer': i}) for i in range(2)]
                for f in futures: f.result()
        assert json.loads(target.read_text())['writer'] in (0, 1)
        return 'Two coordinated atomic replacements complete without a shared-temp collision.'
    case('concurrent JSON exports use unique temporary paths', tmp_race)

    def claims():
        s = store(scratch / 'claims')
        for n in range(12): add_video(s, f'fixture{n:04d}')
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(lambda n: s.claim(f'fixture-{n}', 'captions', CAPS, 30), range(16)))
        ids = [r['id'] for r in rows if r]
        assert len(ids) == len(set(ids)) == 12
        return 'Sixteen simultaneous claim calls lease exactly twelve distinct jobs.'
    case('transactional concurrent claims deduplicate jobs', claims)

    def stale_owner():
        s = store(scratch / 'stale'); add_video(s); j = s.claim('old', 'captions', CAPS, 30)
        with s.connect() as c: c.execute("UPDATE jobs SET lease_owner='new' WHERE id=?", (j['id'],))
        try: s.finish(j, {'status': 'failed', 'error_class': 'synthetic_stale_completion'})
        except RuntimeError: return 'Stale owner refused before state finalization.'
        raise AssertionError('Stale owner finalized another lease')
    case('stale lease cannot finalize another owner', stale_owner)

    def live_lease():
        s = store(scratch / 'live'); add_video(s)
        start = (Path('/proc') / str(os.getpid()) / 'stat').read_text().split()[21]
        j = s.claim(f'{os.getpid()}:{start}:fixture', 'captions', CAPS, 30)
        with s.connect() as c: c.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (j['id'],))
        result = s.recover()
        assert j['id'] not in result['recovered'] and j['id'] in result['held_live_children']
        return 'Expired wall-clock lease does not reclaim a live matching owner process.'
    case('live inline work survives lease recovery', live_lease)

    for label, text in [('format unavailable', 'Requested format is not available'),
                        ('size-skipped zero-exit artifact', 'No complete media file written; source may exceed max-filesize')]:
        def fallback(text=text):
            result = h.classify(RuntimeError(text), 1, 3)
            assert result.get('fallback_audio') is True, result
            return result['error_class']
        case(label + ' schedules typed audio fallback', fallback)

    def nested():
        s = store(scratch / 'nested')
        with s.connect() as c: key = s.add_job(c, 'channel', 'fixture-route', 'https://www.youtube.com/@fixture')
        j = s.claim('fixture-owner', 'channel', CAPS, 30)
        payload = {'entries': [{'_type': 'playlist', 'url': None, 'webpage_url': 'https://www.youtube.com/@fixture/videos',
                               'entries': [{'id': 'abcdefghijk'}, {'id': 'bcdefghijkl'}, {'id': 'cdefghijklm'}]}, None]}
        d = s.job_dir(j); d.mkdir(parents=True); output = d / 'stdout.log'; output.write_text(json.dumps(payload))
        w = h.Worker(s, SimpleNamespace(channel_batch=100))
        with mock.patch.object(w, 'run_child', return_value=output): result = w.channel(j)
        assert {v['video_id'] for v in result['videos']} == {'abcdefghijk', 'bcdefghijkl', 'cdefghijklm'}
        assert 'https://www.youtube.com/@fixture/videos' in result['containers']
        assert result['unusable_or_container_slots'] >= 0
        s.finish(j, result)
        report = s.export(scratch / 'nested-export')
        assert report['channel_listing_trees_complete'] == 0
        return 'Inline IDs retained; tab URL queued; parent not complete before child.'
    case('nested channel containers retain IDs and pending children', nested)

    def unresolved_container():
        s = store(scratch / 'unresolved')
        with s.connect() as c: s.add_job(c, 'channel', 'fixture-route', 'https://www.youtube.com/@fixture')
        j = s.claim('fixture-owner', 'channel', CAPS, 30)
        payload = {'entries': [{'_type': 'playlist', 'entries': [{'id': f'fixture{i:04d}'} for i in range(100)]}]}
        d = s.job_dir(j); d.mkdir(parents=True); output = d/'stdout.log'; output.write_text(json.dumps(payload))
        w = h.Worker(s, SimpleNamespace(channel_batch=100))
        with mock.patch.object(w, 'run_child', return_value=output): result = w.channel(j)
        s.finish(j, result)
        report = s.export(scratch / 'unresolved-export')
        assert report['channel_listing_trees_complete'] == 0
        return 'A bounded unresolved inline listing cannot certify a complete public listing tree.'
    case('unresolved bounded inline container prevents completion', unresolved_container)

    def cached_track():
        import youtube_transcript_api
        s = store(scratch / 'cached-track'); add_video(s)
        j = s.claim('fixture-owner', 'captions', CAPS, 30)
        d = s.job_dir(j); d.mkdir(parents=True); path = d/'verified.json'
        path.write_text(json.dumps({'video_id': 'abcdefghijk', 'segments': [{'text': 'Synthetic regression fixture'}]}))
        s.finish(j, {'status': 'partial'}, [{'path': path, 'type': 'caption', 'complete': True, 'language_code': 'en', 'is_generated': True, 'details': {'source_track_index': 0}}])
        with s.connect() as c: c.execute('UPDATE jobs SET next_attempt=0 WHERE id=?', (j['id'],))
        j = s.claim('fixture-next', 'captions', {'captions': path.stat().st_size+5}, 30)
        def forbidden_fetch(): raise AssertionError('Already verified near-cap track was unnecessarily fetched')
        track = SimpleNamespace(language_code='en', is_generated=True, fetch=forbidden_fetch)
        api = SimpleNamespace(list=lambda _vid: [track])
        w = h.Worker(s, SimpleNamespace(timeout=30, max_attempts=3))
        with mock.patch.object(youtube_transcript_api, 'YouTubeTranscriptApi', return_value=api): result, artifacts = w.captions(j)
        assert result['status'] == 'succeeded' and result['reused_verified_tracks'] == 1 and result['fresh_track_body_requests'] == 0
        assert len(artifacts) == 1
        return 'Verified existing near-cap track uses zero new body requests and zero extra bytes.'
    case('verified partial caption body is reused within reservation', cached_track)

    def stopped_captions():
        import youtube_transcript_api
        s = store(scratch / 'stopped'); add_video(s); j = s.claim('fixture-owner', 'captions', CAPS, 30)
        w = h.Worker(s, SimpleNamespace(timeout=30, max_attempts=3)); w.stop.set()
        api = SimpleNamespace(list=lambda _vid: [object()])
        with mock.patch.object(youtube_transcript_api, 'YouTubeTranscriptApi', return_value=api): result, artifacts = w.captions(j)
        assert result['status'] == 'retryable' and not artifacts
        return 'Circuit-cancelled caption work remains retryable without an IndexError.'
    case('caption circuit cancellation is not a failed parse', stopped_captions)

    def cover_art():
        s = store(scratch / 'cover'); add_video(s); metadata(s)
        j = s.claim('fixture-owner', 'video', CAPS, 30)
        d = s.job_dir(j); d.mkdir(parents=True)
        w = h.Worker(s, SimpleNamespace(rate='4M', timeout=30))
        response = SimpleNamespace(returncode=0, stdout=json.dumps({'streams': [{'codec_type': 'audio'}, {'codec_type': 'video', 'disposition': {'attached_pic': 1}}], 'format': {'duration': '2'}}))
        def write_cover(*_args):
            (d / 'abcdefghijk.mp3').write_bytes(b'synthetic-fixture')
            return d/'stdout.log'
        with mock.patch.object(w, 'run_child', side_effect=write_cover), mock.patch.object(h.subprocess, 'run', return_value=response):
            try: w.media(j)
            except ValueError: return 'An audio stream plus attached cover image is not certified as audiovisual.'
        raise AssertionError('Attached image incorrectly fulfilled video stream requirement')
    case('attached album art cannot count as a video', cover_art)

    def changed_media():
        s = store(scratch / 'changed-media'); add_video(s); metadata(s)
        old = s.claim('fixture-old', 'video', CAPS, 30)
        d = s.job_dir(old); d.mkdir(parents=True); media = d/'abcdefghijk.mp4'; media.write_bytes(b'original-synthetic-media')
        s.finish(old, {'status': 'succeeded'}, [{'path': media, 'type': 'video', 'complete': True}])
        changed = b'changed-synthetic-media!'; media.write_bytes(changed)
        s.reconcile_artifacts(full_hash=True)
        job = s.claim('fixture-next', 'video', CAPS, 30)
        w = h.Worker(s, SimpleNamespace(rate='4M', timeout=30))
        response = SimpleNamespace(returncode=0, stdout=json.dumps({'streams': [{'codec_type': 'audio'}, {'codec_type': 'video'}], 'format': {'duration': '2'}}))
        with mock.patch.object(w, 'run_child', return_value=d/'stdout.log'), mock.patch.object(h.subprocess, 'run', return_value=response):
            try: w.media(job)
            except RuntimeError:
                assert not media.exists(), 'Invalidated completed-looking file remains at skip-existing path'
                assert any(p.is_file() and p.read_bytes() == changed for p in s.raw.rglob('*')), 'Quarantine discarded bytes'
                return 'Changed media retained in quarantine; a zero-output client cannot re-certify it.'
        raise AssertionError('Changed existing filename was re-certified without a fresh output')
    case('invalidated completed media cannot be silently re-certified', changed_media)

    def deny_gate():
        p = scratch / 'blocked.json'; p.write_text(json.dumps({'proxyTunnelDenied': True, 'error': 'Tunnel connection failed: 403 Forbidden'}))
        assert h.access_gate(p)['status'] == 'blocked'
        return 'Known denial rejected; no downstream client or source call was made.'
    case('explicit proxy denial remains a hard run stop', deny_gate)

checks.append({'name': 'worker bytes remained unchanged during audit', 'status': 'PASS' if WORKER_SHA == hashlib.sha256(WORKER.read_bytes()).hexdigest() else 'FAIL'})
report = {'status': 'PASS' if all(x['status'] == 'PASS' for x in checks) else 'FAIL',
          'worker_sha256': WORKER_SHA,
          'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'checks_passed': sum(x['status'] == 'PASS' for x in checks), 'checks_total': len(checks),
          'checks': checks, 'source_network_requests': 0,
          'scope': 'Independent synthetic control regressions; not successful live collection, source interpretation or human validation.'}
(HERE / 'worker-independent-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(report['status'] != 'PASS')
