#!/usr/bin/env python3
"""Bounded, source-bound direct downloads of publisher RSS audio enclosures.

No YouTube extraction, cookies, alternate proxy routes or TLS override. Raw
media remain outside Git; public files contain provenance and derived metadata.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
RAW_ROOT = pathlib.Path('/workspace/channels-et-raw')
RAW = RAW_ROOT / 'publisher-audio'
CAP = 256 * 1024 ** 2
RESERVE = 6 * 1024 ** 3
BUDGET = 20 * 1024 ** 3
LOCK = threading.RLock()
RESULTS = []
IN_FLIGHT = {}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def tree_bytes(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file() and not p.is_symlink()) if path.exists() else 0


def real_git_ancestor(path):
    for parent in [path.resolve(), *path.resolve().parents]:
        meta = parent / '.git'
        if meta.is_dir() and (meta / 'HEAD').is_file():
            return True
        if meta.is_file() and meta.read_text().strip().startswith('gitdir:'):
            return True
    return False


def safe_endpoint(url):
    p = urllib.parse.urlsplit(url)
    return {'url_without_query': urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, '', '')),
            'query_keys_only': sorted({k for k, v in urllib.parse.parse_qsl(p.query)}),
            'reason': 'Do not retain expiring signed CDN query values; use original RSS enclosure URL.'}


def capacity(additional=0):
    used = tree_bytes(RAW_ROOT)
    free = shutil.disk_usage(RAW).free
    if used + additional > BUDGET or free - additional < RESERVE:
        raise RuntimeError('raw_budget_or_free_space_reserve_reached')
    return {'total_raw_bytes': used, 'filesystem_free_bytes': free}


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size,format_name:stream=codec_type,codec_name,sample_rate,channels',
                        '-of', 'json', str(path)], capture_output=True, text=True, timeout=45, check=True)
    d = json.loads(p.stdout)
    duration = float(d['format']['duration'])
    if not math.isfinite(duration) or duration <= 0 or not any(s.get('codec_type') == 'audio' for s in d['streams']):
        raise RuntimeError('invalid_audio_stream_or_duration')
    return d


def snapshot(plan_hash):
    s = {'schema_version': 1, 'updated_at': now(), 'plan_sha256': plan_hash,
         'source_kind': 'independent_original_publisher_rss_audio',
         'not_youtube_downloads': True, 'youtube_requests': 0,
         'concurrency_limit': 2, 'per_file_cap_bytes': CAP, 'free_space_reserve_bytes': RESERVE, 'total_raw_budget_bytes': BUDGET,
         'planned_jobs': len(IN_FLIGHT) + len(RESULTS), 'in_flight': sorted(IN_FLIGHT),
         'completed_audio_files': sum(r['status'] == 'completed' for r in RESULTS),
         'completed_audio_bytes': sum(r.get('bytes', 0) for r in RESULTS if r['status'] == 'completed'),
         'completed_audio_seconds': sum(r.get('duration_seconds', 0) for r in RESULTS if r['status'] == 'completed'),
         'records': RESULTS,
         'limitations': ['Independent podcast editions are not automatically byte-equivalent to indexed YouTube uploads.',
                        'RSS identity and public availability do not grant an open redistribution license.',
                        'Raw media are local-only; generated ASR text requires separate validation.']}
    save(H / 'publisher-summary.json', s)


def download(row, plan_hash):
    ident = row['source_id']
    path = RAW / (ident + '.mp3')
    part = path.with_suffix(path.suffix + '.part')
    sidecar = part.with_suffix(part.suffix + '.meta.json')
    record = {**row, 'started_at': now(), 'status': 'in_flight', 'raw_local_path': str(path), 'tls_verified': True,
              'proxy': 'inherited_session_configuration', 'audio_rehosted_publicly': False}
    start = time.monotonic()
    try:
        with LOCK:
            # Reserve the maximum permitted bytes for each in-flight file.
            capacity(sum(IN_FLIGHT.values()) + CAP)
            IN_FLIGHT[ident] = CAP
            snapshot(plan_hash)
        if path.is_file():
            media = probe(path)
            record.update(status='completed', reused_existing_file=True, bytes=path.stat().st_size,
                          sha256=sha(path), duration_seconds=float(media['format']['duration']), ffprobe=media)
        else:
            offset = 0
            headers = {'User-Agent': 'channels-ET-research/1.0 independent public RSS collection'}
            # Resume only a source-bound partial with an HTTP validator.
            if part.is_file() and sidecar.is_file():
                prior = json.loads(sidecar.read_text())
                validator = prior.get('etag') or prior.get('last_modified')
                if prior.get('enclosure_url') == row['enclosure_url'] and validator:
                    offset = part.stat().st_size
                    if offset > CAP:
                        raise RuntimeError('existing_partial_exceeds_per_file_cap')
                    headers.update({'Range': 'bytes=' + str(offset) + '-', 'If-Range': validator})
            request = urllib.request.Request(row['enclosure_url'], headers=headers)
            with urllib.request.urlopen(request, timeout=45) as response:
                code = response.status
                if offset and code == 206:
                    content_range = response.headers.get('Content-Range', '')
                    if not content_range.startswith('bytes ' + str(offset) + '-'):
                        raise RuntimeError('resume_content_range_mismatch')
                    mode = 'ab'
                elif code == 200:
                    offset = 0
                    mode = 'wb'
                else:
                    raise RuntimeError('unexpected_media_http_status_' + str(code))
                content_type = response.headers.get_content_type()
                if not (content_type.startswith('audio/') or content_type == 'application/octet-stream'):
                    raise RuntimeError('unexpected_media_content_type_' + content_type)
                declared = response.headers.get('Content-Length')
                declared = int(declared) if declared is not None else None
                if declared is not None and offset + declared > CAP:
                    raise RuntimeError('declared_media_exceeds_per_file_cap')
                record.update(http_status=code, content_type=content_type, resumed_from_bytes=offset,
                              final_endpoint=safe_endpoint(response.url), response_declared_remaining_bytes=declared)
                save(sidecar, {'enclosure_url': row['enclosure_url'], 'etag': response.headers.get('ETag'),
                               'last_modified': response.headers.get('Last-Modified')})
                count = offset
                with part.open(mode) as stream:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        if count + len(chunk) > CAP:
                            raise RuntimeError('stream_media_exceeds_per_file_cap')
                        with LOCK:
                            capacity(len(chunk))
                            stream.write(chunk)
                            stream.flush()
                            count += len(chunk)
                            IN_FLIGHT[ident] = max(0, CAP - count)
                if declared is not None and count - offset != declared:
                    raise RuntimeError('incomplete_declared_media_body')
            if not part.stat().st_size:
                raise RuntimeError('empty_media_artifact')
            media = probe(part)
            measured = float(media['format']['duration'])
            expected = row.get('rss_duration_seconds')
            record.update(duration_seconds=measured, duration_delta_from_rss_seconds=measured - expected if expected else None,
                          rss_duration_within_tolerance=abs(measured - expected) <= max(10, expected * .01) if expected else None,
                          bytes=part.stat().st_size, sha256=sha(part), ffprobe=media)
            if row.get('rss_enclosure_length_bytes'):
                record['rss_size_matches_actual'] = row['rss_enclosure_length_bytes'] == part.stat().st_size
            with LOCK:
                capacity()
                if part.stat().st_size > CAP:
                    raise RuntimeError('post_exit_per_file_cap')
                part.replace(path)
                sidecar.unlink(missing_ok=True)
                record['status'] = 'completed'
    except Exception as error:
        message = str(error)
        record.update(status='failed', error_type=type(error).__name__,
                      error=('HTTPError_' + str(error.code)) if isinstance(error, urllib.error.HTTPError) else re.sub(r'https?://\S+', '[endpoint omitted]', message)[:350],
                      partial_bytes=part.stat().st_size if part.exists() else 0)
        if 'Tunnel connection failed' in message:
            record['failure_layer'] = 'proxy_connect_before_origin_tls'
        elif isinstance(error, urllib.error.HTTPError):
            record['failure_layer'] = 'http_response_after_connection'
    finally:
        record.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - start, 6))
        with LOCK:
            IN_FLIGHT.pop(ident, None)
            RESULTS.append(record)
            with (H / 'publisher-attempts.jsonl').open('a') as f:
                f.write(json.dumps(record) + '\n')
            snapshot(plan_hash)
            print(json.dumps({'source_id': ident, 'status': record['status'], 'raw_local_path': record.get('raw_local_path'),
                              'bytes': record.get('bytes'), 'duration_seconds': record.get('duration_seconds'), 'sha256': record.get('sha256'),
                              'error': record.get('error')}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=pathlib.Path, default=H / 'pilot-plan.json')
    args = parser.parse_args()
    if real_git_ancestor(RAW):
        raise RuntimeError('raw_directory_inside_real_git_checkout')
    RAW.mkdir(parents=True, exist_ok=True)
    data = args.plan.read_bytes()
    rows = json.loads(data)['records']
    if any(not re.fullmatch(r'[a-z0-9-]+', x['source_id']) for x in rows):
        raise RuntimeError('unsafe_source_id')
    if len({x['source_id'] for x in rows}) != len(rows):
        raise RuntimeError('duplicate_source_id')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda row: download(row, hashlib.sha256(data).hexdigest()), rows))
    return int(any(r['status'] != 'completed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
