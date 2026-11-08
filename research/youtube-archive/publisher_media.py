#!/usr/bin/env python3
"""Retain explicitly linked publisher audio and manually bounded written editions.

This is not a YouTube downloader. Each candidate binds a saved publisher page,
an exact audio href, and manually inspected Elementor block IDs. Private bodies
and raw media stay outside the repository; only metadata is published.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

FLOOR = 2 * 1024**3
MAX_AUDIO_BYTES = 64 * 1024**2
USER_AGENT = 'ChannelingAtlasResearch/1.0 (+https://github.com/occult-kranti/channels-ET)'
IO_LOCK = threading.Lock()
IO_STATE = {'derivative_reserved_bytes': 0}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def binding(path):
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PageBlocks(HTMLParser):
    """Extract selected block text with nesting; inline tags do not add spaces."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
            'param', 'source', 'track', 'wbr'}
    BREAKS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'br'}
    def __init__(self, block_ids):
        super().__init__(convert_charrefs=True)
        self.wanted = set(block_ids)
        self.blocks = {k: [] for k in block_ids}
        self.matches = {k: 0 for k in block_ids}
        self.stack = []
        self.links = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('href'): self.links.add(attrs['href'])
        active = self.stack[-1][1] if self.stack else None
        key = attrs.get('data-id')
        if key in self.wanted:
            if active is not None: raise ValueError('Selected blocks overlap')
            self.matches[key] += 1
            active = key
        if active and tag in self.BREAKS: self.blocks[active].append('\n')
        if tag not in self.VOID: self.stack.append((tag, active))
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        if not self.stack: return
        active = self.stack[-1][1]
        if active and tag in self.BREAKS: self.blocks[active].append('\n')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
    def handle_data(self, text):
        if self.stack and self.stack[-1][1]:
            self.blocks[self.stack[-1][1]].append(text)
    def texts(self):
        if any(v != 1 for v in self.matches.values()):
            raise ValueError('Each manually selected block must occur exactly once')
        result = {}
        for key, parts in self.blocks.items():
            paragraphs = [' '.join(p.split()) for p in ''.join(parts).split('\n')]
            result[key] = '\n\n'.join(p for p in paragraphs if p)
            if not result[key]: raise ValueError('Empty selected publisher block')
        return result


def extract_page(candidate):
    path = Path(candidate['page_artifact'])
    raw = path.read_bytes()
    if sha(raw) != candidate['page_sha256']: raise ValueError('Publisher page hash differs')
    ids = candidate['body_block_ids'] + candidate.get('attribution_block_ids', [])
    if len(ids) != len(set(ids)): raise ValueError('Duplicate selected block')
    parser = PageBlocks(ids)
    parser.feed(raw.decode('utf-8', errors='strict'))
    blocks = parser.texts()
    if candidate['audio_url'] not in parser.links:
        raise ValueError('Exact audio href not present in bound publisher page')
    if not candidate['body_block_ids']:
        if candidate.get('allow_audio_only') is not True:
            raise ValueError('No selected body; audio-only status must be explicit')
        return raw, None, None
    body = '\n\n'.join(blocks[k] for k in candidate['body_block_ids']) + '\n'
    attribution = '\n\n'.join(blocks[k] for k in candidate.get('attribution_block_ids', [])) + '\n'
    if len(body.split()) < 100: raise ValueError('Selected message is unexpectedly short')
    return raw, body, attribution


def download_audio(url, target, limit=MAX_AUDIO_BYTES):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname != 'omna-shop.s3.eu-west-2.amazonaws.com'
            or parts.username or parts.password or parts.query or parts.fragment
            or not parts.path.lower().endswith('.mp3')):
        raise ValueError('Unsupported publisher audio URL; no relay or signed query accepted')
    if target.exists(): raise ValueError('Refusing to overwrite a retained audio artifact')
    if shutil.disk_usage(target.parent).free - limit < FLOOR:
        raise ValueError('Insufficient disk reserve for bounded audio request')
    temporary = target.with_suffix('.partial')
    start = time.monotonic()
    receipt = {'requested_at': now(), 'url': url, 'ordinary_configured_route': True,
               'proxy_override': False, 'redirects_allowed': False, 'request_attempts': 1}
    try:
        with build_opener(NoRedirect).open(Request(url, headers={
                'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'}), timeout=45) as response:
            if response.status != 200: raise ValueError('Audio response must be HTTP 200')
            size = response.headers.get('Content-Length')
            declared = int(size) if size is not None else None
            if declared is not None and (declared <= 0 or declared > limit):
                raise ValueError('Declared audio size exceeds bounded budget or is empty')
            receipt.update(http_status=response.status, content_type=response.headers.get('Content-Type'),
                           content_length=declared, final_url=response.geturl())
            total = 0
            with temporary.open('xb') as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    with IO_LOCK:
                        if total > limit or shutil.disk_usage(target.parent).free - len(chunk) - IO_STATE['derivative_reserved_bytes'] < FLOOR:
                            raise ValueError('Audio or disk budget exceeded')
                        out.write(chunk)
            if total == 0 or (declared is not None and total != declared):
                raise ValueError('Empty or truncated audio response')
        temporary.replace(target)
        receipt.update(status='retained_pending_decode', elapsed_seconds=time.monotonic()-start,
                       **binding(target))
        return receipt
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def validate_audio(path):
    probe_command = ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]
    result = subprocess.run(probe_command, capture_output=True, timeout=60)
    if result.returncode != 0: raise ValueError('ffprobe rejected publisher audio')
    probe = json.loads(result.stdout)
    audios = [x for x in probe.get('streams', []) if x.get('codec_type') == 'audio']
    if len(audios) != 1 or any(x.get('codec_type') == 'video' for x in probe.get('streams', [])):
        raise ValueError('Expected one audio stream and no video stream')
    duration = float(probe['format']['duration'])
    if duration <= 0: raise ValueError('Invalid audio duration')
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-err_detect', 'explode',
               '-i', str(path), '-map', '0:a:0', '-ac', '1', '-ar', '16000',
               '-f', 's16le', '-acodec', 'pcm_s16le', 'pipe:1']
    digest = hashlib.sha256(); count = 0; start = time.monotonic()
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk: break
                count += len(chunk); digest.update(chunk)
                if time.monotonic() - start > 600:
                    process.kill(); raise ValueError('Full audio validation exceeded time budget')
            code = process.wait(timeout=30)
        finally:
            process.stdout.close()
            if process.poll() is None: process.kill(); process.wait()
        errors.seek(0); stderr = errors.read()
    if code != 0 or stderr or count == 0 or count % 2:
        raise ValueError('Full audio decode failed or emitted errors')
    decoded_seconds = (count // 2) / 16000
    if abs(decoded_seconds - duration) > 1:
        raise ValueError('Decoded duration differs materially from container duration')
    stream = audios[0]
    return probe, {'status': 'full_audio_decode_verified', 'ffprobe_exit': 0,
        'ffmpeg_exit': code, 'ffmpeg_error_bytes': len(stderr), 'format': probe['format']['format_name'],
        'codec': stream['codec_name'], 'sample_rate': int(stream['sample_rate']),
        'channels': int(stream['channels']), 'container_duration_seconds': duration,
        'decoded_duration_seconds': decoded_seconds, 'decoded_pcm_format': 's16le_mono_16000Hz',
        'decoded_pcm_samples': count // 2, 'decoded_pcm_sha256': digest.hexdigest(),
        'decoded_pcm_retained': False, 'validation_seconds': time.monotonic()-start}


def transcode_opus(original, target, expected_duration=None):
    if expected_duration is None:
        _, validation = validate_audio(original)
        expected_duration = validation['decoded_duration_seconds']
    # A finite output bound is enforced, not assumed from target bitrate. VBR
    # beyond this conservative estimate is deferred rather than growing freely.
    bound = int(expected_duration * 6000 * 1.5) + 1024**2
    with IO_LOCK:
        if shutil.disk_usage(target.parent).free - IO_STATE['derivative_reserved_bytes'] - bound < FLOOR:
            raise ValueError('Insufficient derivative disk reserve')
        IO_STATE['derivative_reserved_bytes'] += bound
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(original),
               '-map', '0:a:0', '-vn', '-c:a', 'libopus', '-b:a', '48k', '-vbr', 'on',
               '-application', 'audio', str(target)]
    start = time.monotonic()
    try:
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors)
            try:
                while process.poll() is None:
                    current = target.stat().st_size if target.exists() else 0
                    if current > bound or shutil.disk_usage(target.parent).free < FLOOR + 8*1024**2:
                        raise ValueError('Derivative output or disk budget reached')
                    if time.monotonic() - start > 600:
                        raise ValueError('Opus transcode exceeded execution time budget')
                    time.sleep(0.2)
            finally:
                if process.poll() is None: process.kill(); process.wait()
            errors.seek(0); stderr = errors.read()
        if process.returncode != 0 or stderr:
            raise ValueError('Opus transcode failed or emitted errors')
        if target.stat().st_size > bound: raise ValueError('Derivative output budget exceeded')
        return validate_audio(target)
    finally:
        with IO_LOCK: IO_STATE['derivative_reserved_bytes'] -= bound


def run(spec_path, output, workers=1, retain_opus=False, output_budget=600*1024**2,
        minimum_free_gib=2.0):
    global FLOOR
    if minimum_free_gib not in {1.5, 2.0}:
        raise ValueError('Minimum free space must use an explicitly supported resource policy')
    FLOOR = int(minimum_free_gib*1024**3)
    producer_raw = Path(__file__).read_bytes()
    spec_raw = spec_path.read_bytes(); spec = json.loads(spec_raw)
    candidates = spec['candidates']
    if not candidates: raise ValueError('Candidate frame is empty')
    if workers not in {1, 2}: raise ValueError('Worker count must be one or two')
    if len({c['record_id'] for c in candidates}) != len(candidates): raise ValueError('Duplicate candidate ID')
    if len({c['audio_url'] for c in candidates}) != len(candidates): raise ValueError('Duplicate audio URL')
    if output.exists(): raise ValueError('Use a new edition directory; output already exists')
    initial_free_bytes = shutil.disk_usage(output.parent).free
    reserve = workers*MAX_AUDIO_BYTES + 16*1024**2
    if shutil.disk_usage(output.parent).free - reserve < FLOOR:
        raise ValueError('Insufficient disk reserve for bounded staging')
    if output_budget <= 0: raise ValueError('Output byte budget must be positive')
    output.mkdir(parents=True)
    (output/'producer.py').write_bytes(producer_raw)
    shutil.copyfile(spec_path, output/'selection.json')
    records = []; failures = []
    allocation = {'retained_bytes': 0, 'exhausted': False}
    budget_lock = threading.Lock()
    batch_start = time.monotonic()
    def process_candidate(c):
        started = now()
        record_id = c['record_id']
        if not re.fullmatch(r'[a-z0-9-]+', record_id): raise ValueError('Unsafe record ID')
        directory = output / record_id; directory.mkdir()
        try:
            with budget_lock:
                if allocation['exhausted'] or allocation['retained_bytes'] >= output_budget:
                    raise ValueError('Retained output budget exhausted; candidate remains pending')
            raw, body, attribution = extract_page(c)
            (directory/'publisher-page.html').write_bytes(raw)
            if body is not None:
                (directory/'publisher-written.txt').write_text(body)
                (directory/'publisher-attribution.txt').write_text(attribution)
            receipt = download_audio(c['audio_url'], directory/'publisher-original.mp3')
            write(directory/'download-receipt.json', receipt)
            probe, audio = validate_audio(directory/'publisher-original.mp3')
            write(directory/'ffprobe.json', probe)
            audio.update(bytes=receipt['bytes'], sha256=receipt['sha256'], url=c['audio_url'])
            if retain_opus:
                original_audio = dict(audio)
                opus = directory/'publisher-retained.opus'
                opus_probe, audio = transcode_opus(directory/'publisher-original.mp3', opus,
                                                  original_audio['decoded_duration_seconds'])
                if abs(audio['decoded_duration_seconds'] - original_audio['decoded_duration_seconds']) > 0.1:
                    raise ValueError('Opus output duration differs from verified source audio')
                write(directory/'ffprobe-opus.json', opus_probe)
                audio.update(bytes=opus.stat().st_size, sha256=sha(opus.read_bytes()), url=c['audio_url'],
                             retention='verified_lossy_opus_48kbps_target_vbr',
                             source_original=original_audio, source_original_retained=False,
                             source_original_deleted_after_verified_output=True)
                # Only the newly staged original for this candidate is removed;
                # both its exact hash and full-decode witness remain in receipts.
                (directory/'publisher-original.mp3').unlink()
            else:
                audio['retention'] = 'original_publisher_bytes'
            with budget_lock:
                allocation['retained_bytes'] += audio['bytes']
                # At most the already running second worker can finish after the
                # cap is reached. Record that bounded overshoot rather than hide it.
                allocation['exhausted'] = allocation['retained_bytes'] >= output_budget
            manually_read = c.get('full_body_manually_read_by_ai', False)
            written = {'status': 'retained_publisher_written_edition' if body is not None else 'not_retained_template_pending',
                       'origin': 'publisher_written' if body is not None else None,
                       'bytes': len(body.encode()) if body is not None else 0,
                       'sha256': sha(body.encode()) if body is not None else None,
                       'words': len(body.split()) if body is not None else 0,
                       'block_ids': c['body_block_ids'], 'asr_generated': False,
                       'word_aligned_to_audio': False,
                       'manual_read_by_ai': manually_read if body is not None else False,
                       'reading_scope': ('Selected complete message blocks inspected by an AI agent before extraction.' if manually_read
                                         else 'Automatic extraction from previously validated page-template blocks; this body was not manually read.') if body is not None else 'No written edition retained; page template needs separate review.',
                       'public_stage_name': 'written_message' if body is not None else 'written_message_pending', 'human_validated': False}
            record = {'record_id': record_id, 'publisher_id': 'natalie-glasson-omna',
                      'title': c['title'], 'page_url': c['page_url'], 'page_sha256': c['page_sha256'],
                      'linked_youtube_ids': c.get('youtube_ids', []), 'audio': audio, 'written': written,
                      'association': {'kind': 'cooccurring_links_and_written_message_on_exact_publisher_page',
                                      'youtube_content_equivalence_verified': False,
                                      'audio_written_word_alignment_verified': False},
                      'attribution': 'Channeled Message by Natalie Glasson at OmNa Sanctuary — https://omna.org',
                      'status': 'publisher_audio_and_written_edition_retained' if body is not None else 'publisher_audio_retained_written_pending',
                      'started_at': started, 'completed_at': now()}
            write(directory/'record.json', record)
            return record, None
        except Exception as exc:
            resource_deferred = any(x in str(exc) for x in ('budget', 'reserve', 'Declared audio size'))
            failure = {'record_id': record_id, 'status': 'deferred_resource_budget' if resource_deferred else 'failed_not_counted',
                       'error_type': type(exc).__name__, 'error': str(exc)[:500]}
            write(directory/'failure.json', failure)
            # The detailed exception can contain private filesystem paths.
            return None, {k: failure[k] for k in ('record_id', 'status', 'error_type')}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for record, failure in pool.map(process_candidate, candidates):
            if record is not None: records.append(record)
            if failure is not None: failures.append(failure)
    completed_ids = {r['record_id'] for r in records}
    unfinished = [c for c in candidates if c['record_id'] not in completed_ids]
    write(output/'remaining-queue.json', {'scope': 'Unacquired candidates; a new run must recheck storage and preserve completed editions.',
                                         'candidates': unfinished})
    failure_by_id = {f['record_id']: f for f in failures}
    public_queue = [{'record_id': c['record_id'], 'page_url': c['page_url'], 'title': c['title'],
                     'audio_url': c['audio_url'], 'status': failure_by_id[c['record_id']]['status'],
                     'text_stage': 'template_bounded' if c['body_block_ids'] else 'written_message_pending'} for c in unfinished]
    summary = {'retained_publisher_audio_files': len(records),
               'retained_publisher_written_editions': sum(r['written']['status'] == 'retained_publisher_written_edition' for r in records),
               'pending_written_editions': sum(r['written']['status'] != 'retained_publisher_written_edition' for r in records),
               'retained_audio_bytes': sum(r['audio']['bytes'] for r in records),
               'retained_audio_seconds': sum(r['audio']['decoded_duration_seconds'] for r in records),
               'publisher_written_words': sum(r['written']['words'] for r in records),
               'failed_candidates': sum(f['status'] == 'failed_not_counted' for f in failures),
               'resource_deferred_candidates': sum(f['status'] == 'deferred_resource_budget' for f in failures),
               'candidate_frame': len(candidates), 'youtube_media_downloads': 0,
               'youtube_caption_downloads': 0, 'new_asr_editions': 0}
    module = {'schema_version': 1, 'study': 'first-party-publisher-media', 'generated_at': now(),
              'selection_sha256': sha(spec_raw), 'summary': summary, 'records': records,
              'execution': {'workers': workers, 'elapsed_seconds': time.monotonic()-batch_start,
                            'producer_sha256': sha(producer_raw),
                            'retained_audio_budget_bytes': output_budget,
                            'minimum_free_bytes': FLOOR,
                            'initial_free_bytes': initial_free_bytes,
                            'final_free_bytes': shutil.disk_usage(output).free,
                            'planned_maximum_original_staging_bytes': workers*MAX_AUDIO_BYTES,
                            'planned_metadata_headroom_bytes': 16*1024**2,
                            'budget_overrun_bytes': max(0, allocation['retained_bytes']-output_budget),
                            'budget_policy': 'Stop launching after budget reaches cap; at most one already running second worker may finish.',
                            'retain_opus': retain_opus,
                            'ffmpeg_version': subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True).stdout.splitlines()[0],
                            'ffprobe_version': subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]},
              'failures': failures, 'pending_queue': public_queue, 'limits': [
                  'Publisher-linked media acquisition is separate from YouTube downloads and channel enumeration.',
                  'A cooccurring YouTube link does not establish byte, duration or content equivalence.',
                  'Written publisher messages are independent text editions, not ASR or word-aligned transcripts.',
                  'Audio decode validation establishes container/stream readability, not listening verification or truth of claims.']}
    write(output/'manifest.json', module)
    public = output/'public'; public.mkdir(); write(public/'publisher-media.json', module)
    write(public/'output-manifest.json', {'schema_version': 1, 'public_allowlist': [binding(public/'publisher-media.json')]})
    print(json.dumps(summary))
    return module


def combine_runs(run_paths, output):
    """Validate retained artifact bindings and aggregate metadata without media copies."""
    if output.exists(): raise ValueError('Use a new public release directory')
    records = []; failures = []; editions = []; seen = set(); pending_queue = []
    for folder in run_paths:
        raw = (folder/'manifest.json').read_bytes(); module = json.loads(raw)
        editions.append({'run_id': folder.name, 'manifest_sha256': sha(raw),
                         'execution': module.get('execution'),
                         'candidate_attempts': len(module['records'])+len(module.get('failures', [])),
                         'successful_record_ids': [r['record_id'] for r in module['records']],
                         'failed_or_deferred_attempts': module.get('failures', [])})
        for source in module['records']:
            record = json.loads(json.dumps(source))
            identity = record['record_id']
            if identity in seen: raise ValueError('Duplicate release record')
            seen.add(identity)
            directory = folder/identity
            record['audio'].setdefault('retention', 'original_publisher_bytes')
            audio = directory/('publisher-retained.opus' if record['audio'].get('retention', '').startswith('verified_lossy_opus')
                               else 'publisher-original.mp3')
            pairs = [(audio, record['audio'])]
            if record['written']['status'] == 'retained_publisher_written_edition':
                pairs.append((directory/'publisher-written.txt', record['written']))
            for path, expected in pairs:
                actual = binding(path)
                if any(actual[k] != expected[k] for k in ('bytes', 'sha256')):
                    raise ValueError('Retained artifact changed before publication')
            if sha((directory/'publisher-page.html').read_bytes()) != record['page_sha256']:
                raise ValueError('Bound publisher page changed before publication')
            # The initial manually read pilot predates this explicit field. Its
            # exact body was independently reread; preserve that documented scope.
            if 'manual_read_by_ai' not in record['written']:
                record['written']['manual_read_by_ai'] = bool(record['written'].get('manual_read'))
            record['written']['public_stage_name'] = ('written_message' if record['written']['status'] == 'retained_publisher_written_edition'
                                                       else 'written_message_pending')
            record['written']['human_validated'] = False
            records.append(record)
        failures.extend(module.get('failures', []))
        pending_queue.extend(module.get('pending_queue', []))
    historical_failure_events = len(failures)
    resolved_failure_events = sum(f['record_id'] in seen for f in failures)
    # Continuations can complete a previously deferred item. Preserve earlier
    # run manifests, but do not expose historical holds as current missing files.
    failures = list({f['record_id']: f for f in failures if f['record_id'] not in seen}.values())
    pending_queue = list({q['record_id']: q for q in pending_queue if q['record_id'] not in seen}.values())
    summary = {'retained_publisher_audio_files': len(records),
               'unique_retained_audio_sha256': len({r['audio']['sha256'] for r in records}),
               'unique_source_original_sha256': len({r['audio'].get('source_original', r['audio'])['sha256'] for r in records}),
               'retained_original_mp3_files': sum(r['audio'].get('retention') != 'verified_lossy_opus_48kbps_target_vbr' for r in records),
               'retained_opus_derivative_files': sum(r['audio'].get('retention') == 'verified_lossy_opus_48kbps_target_vbr' for r in records),
               'retained_publisher_written_editions': sum(r['written']['status'] == 'retained_publisher_written_edition' for r in records),
               'pending_written_editions': sum(r['written']['status'] != 'retained_publisher_written_edition' for r in records),
               'retained_audio_bytes': sum(r['audio']['bytes'] for r in records),
               'source_original_bytes_verified': sum(r['audio'].get('source_original', r['audio'])['bytes'] for r in records),
               'retained_audio_seconds': sum(r['audio']['decoded_duration_seconds'] for r in records),
               'publisher_written_words': sum(r['written']['words'] for r in records),
               'message_bodies_read_by_ai': sum(r['written']['manual_read_by_ai'] for r in records),
               'automatically_extracted_unread_bodies': sum(not r['written']['manual_read_by_ai'] and r['written']['status'] == 'retained_publisher_written_edition' for r in records),
               'failed_candidates': sum(f['status'] == 'failed_not_counted' for f in failures),
               'resource_deferred_candidates': sum(f['status'] == 'deferred_resource_budget' for f in failures),
               'historical_failed_or_deferred_attempts': historical_failure_events,
               'resolved_historical_failed_or_deferred_attempts': resolved_failure_events,
               'candidate_frame': len(records)+len(failures), 'youtube_media_downloads': 0,
               'youtube_caption_downloads': 0, 'new_asr_editions': 0,
               'added_to_frozen_493_source_analysis': 0}
    module = {'schema_version': 1, 'study': 'first-party-publisher-media', 'generated_at': now(),
              'summary': summary, 'records': records, 'failures': failures, 'pending_queue': pending_queue, 'source_runs': editions,
              'limits': ['These are publisher-linked audio and independent written editions, not YouTube downloads.',
                         'Some different publisher pages reuse embedded YouTube IDs; co-occurrence is not content equivalence.',
                         'Opus files are verified lossy derivatives; only the first three original MP3s are retained.',
                         'Automatically selected message blocks have not been semantically read or aligned to audio.',
                         'These acquisitions are not incorporated in the frozen 493-source analytical frame.']}
    output.mkdir(parents=True); write(output/'publisher-media.json', module)
    write(output/'output-manifest.json', {'schema_version': 1,
          'public_allowlist': [binding(output/'publisher-media.json')]})
    print(json.dumps(summary))
    return module


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--selection', type=Path)
    mode.add_argument('--combine', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(1, 2), default=1)
    parser.add_argument('--retain-opus', action='store_true')
    parser.add_argument('--output-budget-mib', type=int, default=600)
    parser.add_argument('--minimum-free-gib', type=float, choices=(1.5, 2.0), default=2.0)
    args = parser.parse_args()
    if args.combine: combine_runs(args.combine, args.output)
    else: run(args.selection, args.output, args.workers, args.retain_opus,
              args.output_budget_mib*1024**2, args.minimum_free_gib)
