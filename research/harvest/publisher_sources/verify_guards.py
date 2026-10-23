#!/usr/bin/env python3
"""No-network adversarial fixtures for publisher download guards; not research data."""
import contextlib
import email.message
import fcntl
import hashlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import types
import unittest.mock as mock
import urllib.request

H = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('publisher_guards', H / 'download.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
checks = []


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


with tempfile.TemporaryDirectory(prefix='publisher-guard-fixtures-') as temp:
    t = pathlib.Path(temp)
    fixture = t / 'synthetic-fixture.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono', '-t', '0.3', '-c:a', 'libmp3lame', str(fixture)], check=True)
    blob = fixture.read_bytes()
    actual_duration = float(d.probe(fixture)['format']['duration'])
    ck(actual_duration > 0, 'synthetic local MP3 exercises actual ffprobe')

    def run_case(name, change=None, existing=False, prior=None, content_type='audio/mpeg', amendment=None):
        case = t / name
        case.mkdir()
        raw = case / 'raw'
        raw.mkdir()
        d.H = case
        d.R = case
        d.RAW = d.RAW_ROOT = raw
        d.RESULTS.clear()
        d.IN_FLIGHT.clear()
        d.PRIOR.clear()
        d.PLANNED_IDS.clear()
        d.PLANNED_IDS.add('fixture')
        row = {'source_id': 'fixture', 'enclosure_url': 'https://publisher.example/fixture.mp3',
               'rss_enclosure_length_bytes': len(blob), 'rss_duration_seconds': actual_duration}
        row.update(change or {})
        if existing:
            (raw / 'fixture.mp3').write_bytes(blob)
        if prior:
            d.PRIOR['fixture'] = prior
        if amendment:
            (case / 'warning-amendment.json').write_text(json.dumps(amendment))

        class Response(io.BytesIO):
            status = 200
            url = row['enclosure_url']
            headers = email.message.Message()
        Response.headers['Content-Type'] = content_type
        Response.headers['Content-Length'] = str(len(blob))
        opener = mock.Mock()
        opener.open.return_value = Response(blob)
        with mock.patch.object(d.urllib.request, 'build_opener', return_value=opener), contextlib.redirect_stdout(io.StringIO()):
            record = d.download(row, 'fixture-plan-not-a-research-source')
        return record, opener, raw

    r, op, raw = run_case('valid')
    ck(r['status'] == 'completed' and (raw / 'fixture.mp3').is_file(), 'valid synthetic audio promoted after transport/hash/probe/integrity checks')
    ck(r['sha256'] == hashlib.sha256(blob).hexdigest(), 'promoted synthetic bytes independently hashed')
    r, op, raw = run_case('generic-binary', content_type='binary/octet-stream')
    ck(r['status'] == 'completed' and r['content_type'] == 'binary/octet-stream', 'generic binary media requires actual hash/probe/integrity before completion')
    r, op, raw = run_case('size-mismatch', {'rss_enclosure_length_bytes': len(blob) + 1})
    ck(r['status'] == 'validation_mismatch' and not (raw / 'fixture.mp3').exists(), 'known RSS size mismatch cannot count complete')
    r, op, raw = run_case('duration-mismatch', {'rss_duration_seconds': 100})
    ck(r['status'] == 'validation_mismatch' and not (raw / 'fixture.mp3').exists(), 'known RSS duration mismatch cannot count complete')
    r, op, raw = run_case('http-source', {'enclosure_url': 'http://publisher.example/fixture.mp3'})
    ck(r['status'] == 'failed' and not op.open.called, 'HTTP source refused before any network call')
    r, op, raw = run_case('unknown-existing', existing=True)
    ck(r['status'] == 'failed' and not op.open.called, 'unmanifested existing file is not reused as source evidence')
    valid_prior = {'status': 'completed', 'enclosure_url': 'https://publisher.example/fixture.mp3',
                   'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob), 'finished_at': 'fixture'}
    r, op, raw = run_case('known-existing', existing=True, prior=valid_prior)
    ck(r['status'] == 'completed' and r['reused_existing_file'] and not op.open.called, 'matching prior source/hash reuses artifact with no GET')
    r, op, raw = run_case('changed-existing', existing=True, prior={**valid_prior, 'sha256': '0' * 64})
    ck(r['status'] == 'failed' and not op.open.called, 'changed artifact hash prevents reuse')
    warning_prior = {**valid_prior, 'source_id': 'fixture', 'rss_enclosure_length_bytes': len(blob) + 1,
                     'rss_duration_seconds': actual_duration, 'started_at': 'original-start', 'finished_at': 'original-finish',
                     'elapsed_seconds': 12.5, 'collector_sha256': 'original-executed-source-pin',
                     'validation_outcome': 'saved_complete_publisher_response_with_rss_metadata_warning',
                     'strict_validation_status': 'validation_mismatch', 'strict_validation_error': 'rss_enclosure_size_differs_from_actual',
                     'rss_size_matches_actual': False, 'rss_size_delta_bytes': -1,
                     'content_or_youtube_edition_equivalence_verified': False,
                     'review_amendment': {'path': 'warning-amendment.json', 'human_review': False}}
    approved = {'status': 'applied', 'source_id': 'fixture', 'final_audio_sha256': hashlib.sha256(blob).hexdigest(),
                'final_audio_bytes': len(blob), 'final_audio_duration_seconds': actual_duration}
    r, op, raw = run_case('reviewed-warning-reuse', {'rss_enclosure_length_bytes': len(blob) + 1}, existing=True,
                         prior=warning_prior, amendment=approved)
    preserved = ['validation_outcome', 'strict_validation_status', 'strict_validation_error', 'rss_size_matches_actual',
                 'rss_size_delta_bytes', 'content_or_youtube_edition_equivalence_verified', 'review_amendment',
                 'started_at', 'finished_at', 'elapsed_seconds', 'collector_sha256']
    ck(r['status'] == 'completed' and not op.open.called and all(r.get(k) == warning_prior[k] for k in preserved)
       and r['reuse_verification']['source_warning_amendment_revalidated'],
       'no-GET replay preserves source/hash-bound warning, strict flags, amendment, original timing and executed-source lineage')
    r, op, raw = run_case('unbound-warning-reuse', {'rss_enclosure_length_bytes': len(blob) + 1}, existing=True,
                         prior=warning_prior, amendment={**approved, 'final_audio_sha256': '0' * 64})
    ck(r['status'] == 'failed' and not op.open.called, 'warning exception cannot transfer to an unbound artifact amendment')
    with mock.patch.object(d, 'CAP', len(blob) - 1):
        r, op, raw = run_case('oversize')
    ck(r['status'] == 'quota_stopped' and not (raw / 'fixture.mp3').exists(), 'declared per-file oversize never promoted')
    handler = d.HTTPSOnlyRedirect()
    rejected = False
    try:
        handler.redirect_request(urllib.request.Request('https://publisher.example/a'), None, 302, 'Found', {}, 'http://cdn.example/a')
    except RuntimeError:
        rejected = True
    ck(rejected, 'HTTPS-to-HTTP redirect refused')
    endpoint = d.safe_endpoint('https://cdn.example/validation=123,uuid,signature/episodes/source.mp3?Signature=secret&Expires=123')
    ck(endpoint['origin'] == 'https://cdn.example' and endpoint['path_redacted'] and 'validation=' not in json.dumps(endpoint) and 'secret' not in json.dumps(endpoint), 'CDN signed path and query values omitted from public endpoint metadata')
    lockfile = t / 'shared-lock'
    with lockfile.open('a+') as first, lockfile.open('a+') as second:
        fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rejected = False
        try:
            fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            rejected = True
        ck(rejected, 'separate file handles cannot hold exclusive writer lock together')

failed = [c for c in checks if not c['passed']]
report = {'status': 'FAIL' if failed else 'PASS', 'checks': len(checks), 'failures': failed,
          'collector_sha256': hashlib.sha256((H / 'download.py').read_bytes()).hexdigest(),
          'external_network_requests': 0, 'synthetic_fixture_not_corpus_data': True,
          'all_checks': checks}
(H / 'guard-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(bool(failed))
