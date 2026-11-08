#!/usr/bin/env python3
"""Finite publisher-enclosure collector; original provenance + full-length Opus.

No YouTube client, cookie handling, proxy changes, or paid-resource discovery.
Raw media and manifests must be written outside the public repository.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

FLOOR = 2 * 1024**3
RESERVE = 448 * 1024**2
ORIGINAL_CAP = 160_000_000
COMPACT_CAP = 26_000_000
OUTPUT_CAP = 1_620_000_000
SAMPLE_RATE = 16_000
MAX_DECODE_SECONDS = 4_000
DURATION_TOLERANCE = .1
FROZEN_CORE_SHA = '7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64'
EXECUTION_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
EXECUTED_COPY = None

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def artifact(path):
    p = Path(path).resolve()
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}

def dump(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.partial')
    with tmp.open('w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)

class ResourceStop(RuntimeError):
    pass

def free_guard(root, *, original_written=0, compact_written=0, additional=0):
    """Previously staged bytes consume their earmarked transient reservation."""
    remaining = max(0, RESERVE - original_written - compact_written)
    needed = FLOOR + remaining + additional
    free = shutil.disk_usage(root).free
    if free < needed:
        raise ResourceStop(f'free bytes {free} below required {needed}; no new work admitted')
    return free

def safe_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Publisher media URL must be ordinary HTTPS without credentials')
    return url

class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.chain = []
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        self.chain.append({'from': req.full_url, 'to': newurl, 'status': code})
        if len(self.chain) > 10:
            raise ValueError('Publisher delivery redirect limit exceeded')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def download(url, path, root):
    safe_url(url)
    redirects = Redirects()
    opener = urllib.request.build_opener(redirects)
    request = urllib.request.Request(url, headers={'User-Agent': 'ChannelsET-Research/1.0', 'Accept-Encoding': 'identity'})
    response = opener.open(request, timeout=60)
    with response:
        if response.status != 200 or response.headers.get('Content-Range'):
            raise ValueError('Expected complete HTTP 200 response')
        if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('Unexpected encoded transfer')
        length = response.headers.get('Content-Length')
        declared = int(length) if length else None
        if declared is not None and (declared <= 0 or declared > ORIGINAL_CAP):
            raise ResourceStop(f'Original Content-Length outside cap: {declared}')
        count = 0
        digest = hashlib.sha256()
        with Path(path).open('xb') as out:
            while True:
                b = response.read(1024 * 1024)
                if not b:
                    break
                if count + len(b) > ORIGINAL_CAP:
                    raise ResourceStop('Original streaming byte cap exceeded; partial preserved')
                free_guard(root, original_written=count, additional=len(b))
                out.write(b)
                digest.update(b)
                count += len(b)
        if count == 0 or (declared is not None and count != declared):
            raise ValueError('Incomplete original response; partial preserved')
        return {'enclosure_url': url, 'final_url': response.url, 'redirects': redirects.chain,
                'http_status': response.status, 'headers': dict(response.headers),
                'bytes': count, 'sha256': digest.hexdigest(), 'retrieved_at': now()}

def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                       check=True, text=True, capture_output=True, timeout=90)
    data = json.loads(p.stdout)
    streams = [s for s in data['streams'] if s['codec_type'] == 'audio']
    if not streams:
        raise ValueError('No audio stream')
    seconds = float(data['format']['duration'])
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_DECODE_SECONDS:
        raise ResourceStop('Media duration outside measured phase envelope')
    channels = int(streams[0]['channels'])
    if channels not in (1, 2):
        raise ValueError('Unexpected channel count; explicit plan revision needed')
    return {'duration_seconds': seconds, 'channels': channels,
            'first_audio_codec': streams[0]['codec_name'], 'raw': data}

def decode_measure(path, evidence):
    """Decode to a bounded pipe, never retain a full PCM file in acquisition."""
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1', '-i', str(path),
            '-map', '0:a:0', '-vn', '-sn', '-dn', '-ac', '1', '-ar', str(SAMPLE_RATE),
            '-c:a', 'pcm_s16le', '-threads', '1', '-f', 's16le', 'pipe:1']
    digest, count = hashlib.sha256(), 0
    with Path(evidence).open('xb') as errors:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                b = process.stdout.read(1024 * 1024)
                if not b:
                    break
                count += len(b)
                if count > MAX_DECODE_SECONDS * SAMPLE_RATE * 2:
                    raise ResourceStop('Full-decoder PCM sample envelope exceeded')
                digest.update(b)
            code = process.wait(timeout=30)
            if code or count <= 0 or count % 2:
                raise ValueError(f'Full decoder did not complete cleanly: exit {code}, bytes {count}')
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            process.stdout.close()
    return {'sample_count': count // 2, 'duration_seconds': count / (SAMPLE_RATE * 2),
            'raw_pcm_sha256': digest.hexdigest(), 'sample_rate': SAMPLE_RATE,
            'channels': 1, 'natural_eof': True, 'decoder_returncode': code, 'command': args,
            'stderr_artifact': artifact(evidence)}

def convert(original, target, root, original_bytes):
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1', '-i', str(original),
            '-map', '0:a:0', '-vn', '-sn', '-dn', '-c:a', 'libopus', '-b:a', '48000',
            '-vbr', 'off', '-threads', '1', '-f', 'opus', 'pipe:1']
    errors_path = Path(target).with_suffix('.ffmpeg.log')
    count = 0
    with errors_path.open('xb') as errors, Path(target).open('xb') as out:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                b = process.stdout.read(256 * 1024)
                if not b:
                    break
                if count + len(b) > COMPACT_CAP:
                    raise ResourceStop('Compact streaming output cap exceeded; partial preserved')
                free_guard(root, original_written=original_bytes, compact_written=count, additional=len(b))
                out.write(b)
                count += len(b)
            code = process.wait(timeout=30)
            if code or count <= 0:
                raise ValueError(f'Encoder failed: {code}')
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            process.stdout.close()
    return {'command': args, 'stderr_artifact': artifact(errors_path), 'returncode': code,
            'codec': 'libopus', 'target_bitrate_bps': 48000, 'vbr': False,
            'channels_preserved': True, 'trimmed': False, 'silence_removed': False,
            'mode': 'full_first_audio_stream'}

def verify_artifact(a):
    p = Path(a['path'])
    if not p.is_file() or p.stat().st_size != a['bytes'] or sha(p) != a['sha256']:
        raise ValueError(f'Artifact binding mismatch: {p}')

def completed(receipt_path):
    data = json.loads(Path(receipt_path).read_text())
    if data['status'] != 'completed':
        raise ValueError('Receipt is not completed')
    verify_artifact(data['audio'])
    verify_artifact(data['lineage']['original_source_receipt'])
    original = json.loads(Path(data['lineage']['original_source_receipt']['path']).read_text())
    for key in ('source_id', 'publication_id', 'source_origin'):
        if data[key] != original[key]:
            raise ValueError('Source identity lineage mismatch')
    if data['source'] != original['source']:
        raise ValueError('Source frame lineage mismatch')
    if original['original']['sha256'] != data['lineage']['original_sha256']:
        raise ValueError('Original hash lineage mismatch')
    if abs(data['decoded_16k_mono']['duration_seconds'] - original['decoded_16k_mono']['duration_seconds']) > DURATION_TOLERANCE:
        raise ValueError('Decoded duration mismatch')
    if data['audio']['probe']['channels'] != original['original']['probe']['channels']:
        raise ValueError('Channel mismatch')
    if data['audio']['bytes'] <= 0 or data['lineage']['original_bytes'] != original['original']['bytes']:
        raise ValueError('Invalid source byte lineage')
    for measured in (data['decoded_16k_mono'], original['decoded_16k_mono']):
        n = measured['sample_count']
        d = measured['duration_seconds']
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0 or not math.isfinite(d) or abs(n / SAMPLE_RATE - d) > 1 / SAMPLE_RATE:
            raise ValueError('Invalid decoded sample count/duration')
        if measured['sample_rate'] != SAMPLE_RATE or measured['channels'] != 1 or measured['natural_eof'] is not True or measured['decoder_returncode'] != 0:
            raise ValueError('Invalid full-decoder completion proof')
    for left, right in (('original_decoded_16k_mono', original['decoded_16k_mono']),
                        ('retained_decoded_16k_mono', data['decoded_16k_mono'])):
        if data['lineage'][left] != right:
            raise ValueError('Repeated decoded lineage mismatch')
    if data['lineage']['original_channels'] != original['original']['probe']['channels'] or data['lineage']['retained_channels'] != data['audio']['probe']['channels']:
        raise ValueError('Repeated channel lineage mismatch')
    if data['source']['audio_url'] != original['enclosure_url'] or data['lineage']['original_enclosure_url'] != original['enclosure_url']:
        raise ValueError('Enclosure lineage mismatch')
    return data

def load_frame(inventory, extra=None):
    d = json.loads(Path(inventory).read_text())
    feeds = {f['handle']: f for f in d['feeds']}
    items = []
    if extra:
        for x in json.loads(Path(extra).read_text())['items']:
            if sha(x['html_path']) != x['html_sha256']:
                raise ValueError('Publisher page binding changed')
            items.append({'publication_id': x['id'], 'source_id': 'publisher-page:' + x['id'],
                          'handle': 'Natalie Glasson / OmNa', 'source_origin': 'publisher_download_page',
                          'title': x['title'], 'source_url': x['publisher_page'], 'audio_url': x['audio_url'],
                          'medium_context_id': x['medium_id'], 'publisher': 'OmNa',
                          'language': x['language'], 'language_basis': x['language_basis'],
                          'duration_seconds_publisher': None, 'declared_bytes': None,
                          'source_binding': artifact(extra), 'linked_written_text': artifact(x['text_path']),
                          'page_binding': artifact(x['html_path']), 'claimed_entity_id': x['channellee_id'],
                          'audio_text_alignment': x['audio_text_alignment']})
    groups = {}
    for x in d['feed_entries']:
        handle = x['handle']
        item = {'publication_id': x['source_id'], 'source_id': 'publisher-rss:' + x['source_id'].lstrip('@'),
                'handle': handle, 'source_origin': 'publisher_rss', 'title': x['title'],
                'source_url': x['source_url'], 'audio_url': x['audio_enclosure']['url'],
                'guid': x['guid'], 'published_at': x.get('published_at'),
                'medium_context_id': 'tracy_kumbera_publisher' if handle == '@TracyKumbera' else 'akanksshaa_publisher',
                'publisher': feeds[handle]['feed_title'], 'language': 'en',
                'language_basis': 'publisher_feed_declares_en_not_detection',
                'duration_seconds_publisher': x['duration_seconds_publisher'],
                'declared_bytes': int(x['audio_enclosure']['length']),
                'source_binding': artifact(inventory), 'feed_sha256': x['feed_sha256'],
                'transcript_links': x['transcript_links']}
        # There is no minimum duration for these non-Bashar publishers.
        groups.setdefault(handle, []).append(item)
    while any(groups.values()):
        for group in groups.values():
            if group:
                items.append(group.pop(0))
    ids = [x['source_id'] for x in items]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate processing IDs')
    return items

def acquire(item, output, retained_bytes, caption_records):
    if sha(__file__) != EXECUTION_SHA:
        raise ValueError('Collector source changed during execution')
    key = hashlib.sha256(item['source_id'].encode()).hexdigest()[:20]
    folder = output / 'items' / key
    receipt_path = folder / 'receipt.json'
    if receipt_path.exists():
        result = completed(receipt_path)
        if result['source'] != item:
            raise ValueError('Source frame changed for existing receipt')
        return result, False
    if folder.exists():
        raise ValueError('Previous partial item exists; preserve and inspect before retry')
    estimate = min(COMPACT_CAP, math.ceil((item.get('duration_seconds_publisher') or 4000) * 6000 * 1.035))
    if retained_bytes + estimate > OUTPUT_CAP:
        raise ResourceStop('Retained audio output budget would be exceeded')
    free_guard(output, additional=estimate)
    folder.mkdir(parents=True)
    original_path, compact_path = folder / 'original.partial', folder / 'retained.opus'
    retrieval = download(item['audio_url'], original_path, output)
    dump(folder / 'retrieval.json', retrieval)
    original_probe = probe(original_path)
    original_decoded = decode_measure(original_path, folder / 'original-decode.log')
    original_receipt = {'status': 'original_source_verified', 'source_id': item['source_id'],
                        'publication_id': item['publication_id'], 'source_origin': item['source_origin'],
                        'enclosure_url': item['audio_url'], 'retrieval': retrieval,
                        'original': {'sha256': retrieval['sha256'], 'bytes': retrieval['bytes'], 'probe': original_probe},
                        'decoded_16k_mono': original_decoded, 'source': item,
                        'collector_sha256': EXECUTION_SHA, 'created_at': now()}
    dump(folder / 'original-source.json', original_receipt)
    conversion = convert(original_path, compact_path, output, retrieval['bytes'])
    retained_probe = probe(compact_path)
    retained_decoded = decode_measure(compact_path, folder / 'retained-decode.log')
    if original_probe['channels'] != retained_probe['channels']:
        raise ValueError('Encoded channel count changed')
    delta = abs(original_decoded['duration_seconds'] - retained_decoded['duration_seconds'])
    if delta > DURATION_TOLERANCE:
        raise ValueError(f'Full decoded duration mismatch: {delta}')
    current = artifact(compact_path)
    if retained_bytes + current['bytes'] > OUTPUT_CAP:
        raise ResourceStop('Actual retained audio exceeds total output cap')
    current['probe'] = retained_probe
    result = {'status': 'completed', 'provider': 'publisher_audio', 'source_id': item['source_id'],
              'publication_id': item['publication_id'], 'source_origin': item['source_origin'],
              'input_representation': 'full_duration_lossy_opus_derivative', 'source': item,
              'duration_seconds': retained_probe['duration_seconds'], 'audio': current,
              'decoded_16k_mono': retained_decoded,
              'duplicate_family_id': 'original-sha256:' + retrieval['sha256'],
              'family_basis': 'exact_original_encoded_bytes_not_session_identity',
              'lineage': {'original_source_receipt': artifact(folder / 'original-source.json'),
                         'original_sha256': retrieval['sha256'], 'original_bytes': retrieval['bytes'],
                         'original_channels': original_probe['channels'], 'retained_channels': retained_probe['channels'],
                         'original_enclosure_url': item['audio_url'],
                         'original_decoded_16k_mono': original_decoded,
                         'retained_decoded_16k_mono': retained_decoded,
                         'max_duration_difference_seconds': DURATION_TOLERANCE, 'actual_duration_difference_seconds': delta,
                         'conversion': conversion},
              'caption_link': None, 'created_at': now(), 'collector_sha256': EXECUTION_SHA}
    result['lineage']['conversion']['ffmpeg_version'] = subprocess.run(
        ['ffmpeg', '-version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    result['lineage']['conversion']['code_sha256'] = EXECUTION_SHA
    matches = [c for c in caption_records if c.get('episode_source_id') == item['publication_id']
               and c.get('episode_guid') == item.get('guid')
               and c.get('audio_enclosure', {}).get('url') == item['audio_url']]
    if matches:
        for c in matches:
            verify_artifact(c['text_artifact'])
        result['caption_link'] = {'status': 'exact_guid_enclosure_link_not_audio_accuracy_validation',
                                  'records': [{'source_id': c['source_id'], 'text_artifact': c['text_artifact'],
                                               'raw_artifact': c['raw_artifact']} for c in matches]}
    if sha(__file__) != EXECUTION_SHA:
        raise ValueError('Collector source changed before admission')
    dump(receipt_path, result)
    completed(receipt_path)
    free_guard(output, original_written=retrieval['bytes'], compact_written=current['bytes'])
    # Only the newly created staging original is removed, after both receipt checks.
    if sha(original_path) != retrieval['sha256']:
        raise ValueError('Original changed before cleanup; preserved')
    original_path.unlink()
    dump(folder / 'cleanup.json', {'removed_only_new_staging_original': str(original_path),
                                 'original_sha256': retrieval['sha256'], 'original_bytes': retrieval['bytes'],
                                 'verified_receipt': artifact(receipt_path), 'at': now()})
    free_guard(output, compact_written=current['bytes'])
    return result, True

def summary(records, frame, status, stop=None):
    return {'schema_version': 1, 'generated_at': now(), 'status': status,
            'frame_count': len(frame), 'completed_count': len(records),
            'retained_bytes': sum(r['audio']['bytes'] for r in records),
            'original_source_bytes_verified': sum(r['lineage']['original_bytes'] for r in records),
            'decoded_duration_seconds': sum(r['decoded_16k_mono']['duration_seconds'] for r in records),
            'records': records, 'stop': stop,
            'scope': 'Explicit publisher enclosure frame; not a YouTube upload census or all historical sessions',
            'limits': {'free_floor_bytes': FLOOR, 'operational_reserve_bytes': RESERVE,
                       'original_cap_bytes': ORIGINAL_CAP, 'compact_cap_bytes': COMPACT_CAP,
                       'output_cap_bytes': OUTPUT_CAP, 'non_bashar_minimum_seconds': 0},
            'collector': artifact(EXECUTED_COPY or __file__)}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--extra-frame', type=Path)
    parser.add_argument('--captions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pilot-new-items', type=int, help='Explicit feasibility checkpoint; omission processes full remaining frame')
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    if sha(repo / 'research/batch-media/audio.py') != FROZEN_CORE_SHA:
        raise ValueError('Legacy core changed; stop for provenance review')
    output = args.output.resolve()
    if output.is_relative_to(repo):
        raise ValueError('Raw media output must be private, outside the public repository')
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(args, output)

def run(args, output):
    global EXECUTED_COPY
    EXECUTED_COPY = output / 'executed-collector.py'
    if EXECUTED_COPY.exists():
        if sha(EXECUTED_COPY) != EXECUTION_SHA:
            raise ValueError('Collector version changed; preserve prior phase and explicitly migrate')
    else:
        with EXECUTED_COPY.open('xb') as copy:
            copy.write(Path(__file__).read_bytes())
    frame = load_frame(args.inventory, args.extra_frame)
    frame_path = output / 'frame.json'
    if frame_path.exists() and json.loads(frame_path.read_text()) != frame:
        raise ValueError('Frozen acquisition frame changed')
    dump(frame_path, frame)
    captions = json.loads(args.captions.read_text())['records']
    records, new = [], 0
    try:
        for item in frame:
            result, created = acquire(item, output, sum(x['audio']['bytes'] for x in records), captions)
            records.append(result)
            new += int(created)
            dump(output / 'manifest.json', summary(records, frame, 'running'))
            print(json.dumps({'completed': len(records), 'frame': len(frame), 'publication_id': item['publication_id'],
                              'retained_bytes': result['audio']['bytes'], 'decoded_seconds': result['decoded_16k_mono']['duration_seconds'],
                              'new': created}), flush=True)
            if args.pilot_new_items and new >= args.pilot_new_items:
                dump(output / 'manifest.json', summary(records, frame, 'pilot_checkpoint'))
                return
        dump(output / 'manifest.json', summary(records, frame, 'frame_complete'))
    except Exception as exc:
        stop = {'type': type(exc).__name__, 'message': str(exc), 'source_id': item['source_id'], 'at': now()}
        dump(output / 'manifest.json', summary(records, frame, 'halted', stop))
        raise

if __name__ == '__main__':
    main()
