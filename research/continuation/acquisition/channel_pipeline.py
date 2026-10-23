#!/usr/bin/env python3
"""Resumable metadata/caption collection and quota-controlled media preparation.

The current continuation has no successful public YouTube preflight. Network modes
require a separately successful preflight receipt; they never bypass a denial.
Raw captions/media stay outside Git. Public ledgers contain metadata and hashes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_RAW = pathlib.Path('/workspace/channels-et-raw')
DEFAULT_PLAN = ROOT / 'research/expansion/acquisition/collection-plan.json'


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(blob): return hashlib.sha256(blob).hexdigest()
def file_sha(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): hasher.update(chunk)
    return hasher.hexdigest()
def load(path): return json.loads(path.read_text())
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def inside_git(path):
    resolved = path.resolve()
    for parent in (resolved, *resolved.parents):
        meta = parent / '.git'
        if meta.is_dir() and (meta / 'HEAD').is_file(): return True
        if meta.is_file() and meta.read_text().strip().startswith('gitdir:'): return True
    return False


def raw_directory(path):
    if inside_git(path): raise ValueError('Raw captions/media must remain outside real Git checkouts')
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def sanitized(error):
    text = re.sub(r'(?i)(https?://)[^/@\s]+:[^/@\s]+@', r'\1[redacted]@', str(error))
    text = re.sub(r'(https?://[^?\s]+)\?[^\s]+', r'\1?[query-redacted]', text)
    return re.sub(r'(?i)(authorization|cookie|token|key|password)(\s*[:=]\s*)[^\s,;]+', r'\1\2[redacted]', text)[-1200:]


def blocked(error):
    return bool(re.search(r'403|429|forbidden|requestblocked|ipblocked|too many requests|captcha|sign in to confirm|bot challenge', str(error), re.I))


def require_access(receipt):
    if receipt is None: raise ValueError('Network modes require --access-receipt from a successful current ordinary public preflight')
    data = load(receipt)
    rows = data.get('records', [])
    if data.get('blocked') or not rows or not all(r.get('status') == 'success' for r in rows):
        raise ValueError('The supplied access receipt did not establish successful public access; do not substitute a client to evade the recorded denial')
    for row in rows:
        if row.get('operation') != 'watch_metadata_preflight' or not row.get('matching_video_id') or row.get('http_status') != 200:
            raise ValueError('Receipt must bind a successful matching-video ordinary public-watch preflight')
        retrieved = dt.datetime.fromisoformat(row['retrieved_at'])
        age = (dt.datetime.now(dt.timezone.utc) - retrieved).total_seconds()
        if age < -300 or age > 24 * 3600:
            raise ValueError('Access receipt must be current within24hours; a new preflight is required after diagnosis/state change')


def packages():
    return {name: importlib.metadata.version(name) for name in ('yt-dlp', 'youtube-transcript-api')}


def append(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f: f.write(json.dumps(record, ensure_ascii=False) + '\n')


def state(path):
    return load(path) if path.exists() else {'schema_version': 1, 'channels': {}, 'captions': {}, 'media': {}}


def channel_command(url, start, size):
    cmd = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-cache-dir', '--skip-download', '--flat-playlist',
           '--dump-single-json', '--retries', '0', '--extractor-retries', '0', '--socket-timeout', '25',
           '--playlist-start', str(start), '--no-warnings']
    if size: cmd += ['--playlist-end', str(start + size - 1)]
    return cmd + [url]


def enumerate_channels(args):
    require_access(args.access_receipt)
    plan = load(args.plan)
    path = args.output / 'state.json'
    current = state(path)
    jobs = [j for j in plan['accounts'] if not args.person_id or set(j.get('person_ids', [])) & set(args.person_id)]
    count = 0
    for job in jobs:
        old = current['channels'].get(job['id'], {})
        if old.get('complete_listing') or old.get('status') == 'blocked': continue
        if count >= args.max_jobs: break
        start = old.get('next_start', 1)
        record = {'job_id': job['id'], 'source_url': job['url'], 'person_ids_inherited': job.get('person_ids', []),
                  'started_at': now(), 'playlist_start': start, 'entry_cap': args.batch_entries,
                  'software': packages()['yt-dlp'], 'actual_speaker_status': 'unknown_not_audio_verified'}
        try:
            p = subprocess.run(channel_command(job['url'], start, args.batch_entries), capture_output=True, text=True, timeout=args.timeout)
            if p.returncode:
                raise RuntimeError(sanitized(p.stderr))
            data = json.loads(p.stdout)
            rows = []
            returned_slots = data.get('entries', [])
            if not isinstance(returned_slots, list): raise ValueError('Expected a list of returned playlist slots')
            entries = [e for e in returned_slots if isinstance(e, dict)]
            for e in entries:
                vid = e.get('id')
                if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid or ''): continue
                rows.append({'video_id': vid, 'title': e.get('title'), 'duration_seconds': e.get('duration'),
                             'source_url': 'https://www.youtube.com/watch?v=' + vid,
                             'publisher_platform_id': e.get('channel_id'), 'publisher_name': e.get('channel') or e.get('uploader'),
                             'publisher_route': job['url'], 'person_ids_inherited': job.get('person_ids', []),
                             'actual_speaker_status': 'unknown_not_audio_verified', 'retrieved_at': now(),
                             'access_depth': 'flat_playlist_metadata_not_complete_watch_or_speech_review'})
            for row in rows: append(args.output / 'discovered-videos.jsonl', row)
            consumed_slots = len(returned_slots)
            complete = args.batch_entries == 0 or consumed_slots < args.batch_entries
            record.update(status='success', listed_entries=consumed_slots, usable_video_entries=len(rows),
                          unusable_returned_slots=consumed_slots - len(rows),
                          response_sha256=sha(p.stdout.encode()), complete_listing=complete,
                          completeness_scope='end_of_returned_public_listing_only; not_private_deleted_or_all_platform_uploads',
                          next_start=start + consumed_slots, rows=rows)
        except Exception as error:
            record.update(status='blocked' if blocked(error) else 'failed', error_type=type(error).__name__, error=sanitized(error),
                          complete_listing=False, next_start=start)
        record['finished_at'] = now()
        current['channels'][job['id']] = {k: v for k, v in record.items() if k != 'rows'}
        append(args.output / 'channel-attempts.jsonl', record)
        save(path, current)
        count += 1
        if record['status'] == 'blocked': break
        time.sleep(args.delay)
    return summarize(args.output, current)


def video_inputs(args):
    if args.input is None:
        raise ValueError('--input must name discovered-videos.jsonl or a caption/video plan')
    if args.input.suffix == '.jsonl': rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    else:
        data = load(args.input)
        rows = data.get('captions', data.get('records', [])) if isinstance(data, dict) else data
    unique = {}
    for row in rows:
        vid = row.get('video_id', row.get('id'))
        if re.fullmatch(r'[A-Za-z0-9_-]{11}', vid or ''): unique.setdefault(vid, {**row, 'video_id': vid})
    return list(unique.values())


def collect_captions(args):
    require_access(args.access_receipt)
    from requests import Session
    from youtube_transcript_api import YouTubeTranscriptApi
    class LimitedSession(Session):
        def request(self, *a, **kw):
            kw.setdefault('timeout', 25); self.cookies.clear()
            return super().request(*a, **kw)
    api = YouTubeTranscriptApi(http_client=LimitedSession())
    raw = raw_directory(args.raw_dir / 'captions')
    path = args.output / 'state.json'; current = state(path)
    for row in [r for r in video_inputs(args) if r['video_id'] not in current['captions']][:args.max_jobs]:
        vid = row['video_id']; record = {'video_id': vid, 'started_at': now(), 'source_url': 'https://www.youtube.com/watch?v=' + vid,
                                      'person_ids_inherited': row.get('person_ids', row.get('person_ids_inherited', [])),
                                      'title': row.get('title'), 'actual_speaker_status': 'unknown_not_audio_verified', 'tracks': []}
        try:
            tracks = list(api.list(vid))
            selected = tracks if args.max_tracks == 0 else tracks[:args.max_tracks]
            record['offered_tracks'] = len(tracks)
            record['selected_track_cap'] = args.max_tracks
            for track in selected:
                quota = int(args.quota_gib * 1024 ** 3)
                reserve = int(args.reserve_gib * 1024 ** 3)
                if tree_bytes(args.raw_dir) >= quota or shutil.disk_usage(raw).free < reserve:
                    raise RuntimeError('Local raw storage quota/free-space reserve reached before caption fetch')
                result = track.fetch()
                document = {'video_id': vid, 'source_url': record['source_url'], 'title': record['title'],
                            'language_code': result.language_code, 'is_generated': result.is_generated,
                            'segments': result.to_raw_data(), 'actual_speaker_status': 'unknown_not_audio_verified'}
                blob = json.dumps(document, ensure_ascii=False, indent=2).encode()
                if tree_bytes(args.raw_dir) + len(blob) > quota or shutil.disk_usage(raw).free - len(blob) < reserve:
                    raise RuntimeError('Local raw storage quota/free-space reserve would be exceeded by caption artifact')
                language_filename = re.sub(r'[^A-Za-z0-9_-]', '_', result.language_code)
                raw_file = raw / (vid + '-' + language_filename + '-' + sha(blob)[:12] + '.json')
                raw_file.write_bytes(blob)
                record['tracks'].append({'language_code': result.language_code, 'is_generated': result.is_generated,
                                         'segment_count': len(document['segments']), 'source_sha256': sha(blob),
                                         'raw_local_path': str(raw_file), 'status': 'success'})
            record['status'] = 'success' if record['tracks'] else 'unavailable'
            record['all_offered_tracks_retrieved'] = len(record['tracks']) == len(tracks) and bool(tracks)
        except Exception as error:
            status = 'quota_stopped' if 'Local raw storage quota' in str(error) else ('blocked' if blocked(error) else 'failed')
            record.update(status=status, error_type=type(error).__name__, error=sanitized(error),
                          all_offered_tracks_retrieved=False)
        record['finished_at'] = now(); current['captions'][vid] = record
        append(args.output / 'caption-attempts.jsonl', record); save(path, current)
        if record['status'] in ('blocked', 'quota_stopped'): break
        time.sleep(args.delay)
    return summarize(args.output, current)


def tree_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()) if root.exists() else 0


def media_plan(rows, raw, quota_bytes, reserve_bytes, per_file_bytes):
    raw = raw_directory(raw)
    used = tree_bytes(raw); free = shutil.disk_usage(raw).free
    decisions = []
    allocated = 0
    for row in rows:
        duration = row.get('duration_seconds', row.get('durationSeconds'))
        # Planning estimate only, not a remote byte measurement or guaranteed size.
        estimate = int(duration * 160000 / 8 * 1.25) if not isinstance(duration, bool) and isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0 else None
        allowed = estimate is not None and estimate <= per_file_bytes and used + allocated + estimate <= quota_bytes and free - allocated - estimate >= reserve_bytes
        decisions.append({'video_id': row['video_id'], 'source_url': 'https://www.youtube.com/watch?v=' + row['video_id'],
                          'estimated_bytes': estimate, 'estimate_basis': 'duration * 160kbit/s * 1.25 overhead; not observed size',
                          'eligible': allowed, 'reason': 'within_planning_limits' if allowed else 'unknown_size_or_quota_or_reserve_or_per_file_cap',
                          'actual_speaker_status': 'unknown_not_audio_verified'})
        if allowed: allocated += estimate
    return {'created_at': now(), 'dry_run': True, 'quota_bytes': quota_bytes, 'reserve_free_bytes': reserve_bytes,
            'per_file_cap_bytes': per_file_bytes, 'current_raw_bytes': used, 'filesystem_free_bytes': free,
            'estimated_eligible_bytes': allocated, 'records': decisions}


def download_command(row, media, per_file_bytes):
    return [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-cache-dir', '--no-playlist', '--no-progress',
            '--retries', '0', '--fragment-retries', '0', '--extractor-retries', '0', '--socket-timeout', '25',
            '--limit-rate', '4M',
            '--format', 'bestaudio[abr<=160]/bestaudio/best[height<=360]', '--max-filesize', str(per_file_bytes),
            '--output', str(media / (row['video_id'] + '.%(ext)s')), row['source_url']]


def media(args):
    raw = raw_directory(args.raw_dir)
    rows = video_inputs(args)[:args.max_jobs]
    plan = media_plan(rows, raw, int(args.quota_gib * 1024 ** 3), int(args.reserve_gib * 1024 ** 3), args.max_file_mib * 1024 ** 2)
    save(args.output / 'media-plan.json', plan)
    if not args.execute: return plan
    require_access(args.access_receipt)
    path = args.output / 'state.json'; current = state(path)
    media_path = raw_directory(raw / 'media')
    for row in plan['records']:
        if not row['eligible'] or row['video_id'] in current['media']: continue
        log_path = raw / ('download-' + row['video_id'] + '.log')
        record = {'video_id': row['video_id'], 'started_at': now(), 'source_url': row['source_url'],
                  'actual_speaker_status': 'unknown_not_audio_verified', 'quota_enforced': True}
        started = time.monotonic(); interrupted = None
        with log_path.open('wb') as log:
            process = subprocess.Popen(download_command(row, media_path, plan['per_file_cap_bytes']), stdout=log, stderr=log)
            while process.poll() is None:
                if tree_bytes(raw) > plan['quota_bytes'] or shutil.disk_usage(raw).free < plan['reserve_free_bytes']:
                    interrupted = 'disk_quota_or_free_reserve'; process.terminate(); break
                if any(p.stat().st_size > plan['per_file_cap_bytes'] for p in media_path.glob(row['video_id'] + '.*') if p.is_file()):
                    interrupted = 'per_file_size_limit'; process.terminate(); break
                if time.monotonic() - started > args.timeout:
                    interrupted = 'time_budget'; process.terminate(); break
                time.sleep(0.5)
            try: code = process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); code = process.wait()
        message = sanitized(log_path.read_text(errors='replace'))
        observed_files = [p for p in media_path.glob(row['video_id'] + '.*') if p.is_file()]
        actual_raw_bytes = tree_bytes(raw)
        actual_free_bytes = shutil.disk_usage(raw).free
        max_actual_file_bytes = max((p.stat().st_size for p in observed_files), default=0)
        if interrupted is None and (actual_raw_bytes > plan['quota_bytes'] or actual_free_bytes < plan['reserve_free_bytes'] or max_actual_file_bytes > plan['per_file_cap_bytes']):
            interrupted = 'post_exit_disk_or_file_limit'
        record.update(status='quota_stopped' if interrupted else ('success' if code == 0 else ('blocked' if blocked(message) else 'failed')),
                      reason=interrupted, exit_code=code, finished_at=now(), error=message if code else None)
        record['post_exit_validation'] = {'raw_directory_bytes': actual_raw_bytes, 'filesystem_free_bytes': actual_free_bytes,
                                          'largest_matching_file_bytes': max_actual_file_bytes,
                                          'within_storage_limits': actual_raw_bytes <= plan['quota_bytes'] and actual_free_bytes >= plan['reserve_free_bytes'] and max_actual_file_bytes <= plan['per_file_cap_bytes']}
        record['observed_local_files'] = [{'filename': p.name, 'bytes': p.stat().st_size, 'sha256': file_sha(p)} for p in observed_files]
        if record['status'] == 'success':
            media_extensions = {'.mp4', '.webm', '.m4a', '.mp3', '.opus', '.ogg', '.wav', '.aac', '.flac', '.mkv', '.mov'}
            files = [p for p in observed_files if p.suffix.lower() in media_extensions and p.stat().st_size > 0]
            record['artifacts'] = [{'filename': p.name, 'bytes': p.stat().st_size, 'sha256': file_sha(p)} for p in files]
            if not files: record['status'] = 'failed_no_media_artifact'
        current['media'][row['video_id']] = record
        append(args.output / 'media-attempts.jsonl', record); save(path, current)
        if record['status'] in ('blocked', 'quota_stopped'): break
        time.sleep(args.delay)
    return summarize(args.output, current)


def summarize(output, current):
    result = {'checked_at': now(), 'software': packages(), 'channels_attempted': len(current['channels']),
              'channels_success': sum(r['status'] == 'success' for r in current['channels'].values()),
              'channel_listings_complete': sum(r.get('complete_listing', False) for r in current['channels'].values()),
              'caption_videos_attempted': len(current['captions']),
              'caption_tracks_retrieved': sum(len(r.get('tracks', [])) for r in current['captions'].values()),
              'media_videos_attempted': len(current['media']),
              'media_videos_success': sum(r['status'] == 'success' for r in current['media'].values()),
              'has_failed_or_blocked_history': any(r['status'] not in ('success',) for group in current.values() if isinstance(group, dict) for r in group.values() if isinstance(r, dict) and 'status' in r),
              'speaker_validation': 'none; publisher and claimed entity do not identify actual speaker'}
    save(output / 'pipeline-summary.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('channels', 'captions', 'media'))
    p.add_argument('--plan', type=pathlib.Path, default=DEFAULT_PLAN)
    p.add_argument('--output', type=pathlib.Path, default=HERE / 'runs')
    p.add_argument('--raw-dir', type=pathlib.Path, default=DEFAULT_RAW)
    p.add_argument('--input', type=pathlib.Path)
    p.add_argument('--access-receipt', type=pathlib.Path)
    p.add_argument('--max-jobs', type=int, default=3)
    p.add_argument('--batch-entries', type=int, default=100, help='per-channel entries;0 requests remaining full listing')
    p.add_argument('--max-tracks', type=int, default=0, help='offered caption tracks per video;0 selects all')
    p.add_argument('--person-id', action='append', default=[])
    p.add_argument('--delay', type=float, default=1)
    p.add_argument('--timeout', type=int, default=180)
    p.add_argument('--quota-gib', type=float, default=2)
    p.add_argument('--reserve-gib', type=float, default=4)
    p.add_argument('--max-file-mib', type=int, default=128)
    p.add_argument('--execute', action='store_true', help='media default is a no-network dry run')
    args = p.parse_args()
    if args.max_jobs < 1 or args.batch_entries < 0 or args.max_tracks < 0 or args.delay < 0 or args.timeout < 1:
        p.error('limits must be nonnegative and job/time limits positive')
    if not math.isfinite(args.quota_gib) or not math.isfinite(args.reserve_gib) or args.quota_gib <= 0 or args.reserve_gib < 0 or args.max_file_mib <= 0:
        p.error('disk quota/per-file cap must be positive; free reserve nonnegative')
    try:
        result = {'channels': enumerate_channels, 'captions': collect_captions, 'media': media}[args.mode](args)
        print(json.dumps(result, ensure_ascii=False))
        return 2 if result.get('has_failed_or_blocked_history') else 0
    except Exception as error:
        print(json.dumps({'status': 'not_executed', 'error_type': type(error).__name__, 'error': sanitized(error)}))
        return 2


if __name__ == '__main__': sys.exit(main())
