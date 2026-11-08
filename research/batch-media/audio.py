#!/usr/bin/env python3
"""Private, source-bound local audio measurements and optional offline ASR.

This program never downloads media or models and never uploads files. A receipt
verifies bytes and processing, not transcript accuracy or a speaker's identity.
"""
from __future__ import annotations

import argparse
from array import array
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import wave

SCHEMA = 1
SAMPLE_RATE = 16000
WINDOW_SAMPLES = 320  # 20 ms at the declared analysis sample rate.
SILENCE_DBFS = -40.0
NEAR_FULL_SCALE = 0.999
MAX_DURATION = 86400
FREE_RESERVE = 6 * 1024**3
HASH = re.compile(r'^[0-9a-f]{64}$')
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:_.-]{0,159}$')
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
DEFAULT_MODEL = Path('/workspace/channels-et-asr-cache/tiny-en')
MODEL_FILES = ('config.json', 'model.bin', 'tokenizer.json')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def encoded(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def object_hash(obj):
    return hashlib.sha256(encoded(obj).encode()).hexdigest()


def private_path(value, *, exists=False):
    """Reject symlink routes and every containing Git checkout, not only cwd."""
    if not isinstance(value, (str, Path)) or not str(value) or '\x00' in str(value):
        raise ValueError('A nonempty local path is required')
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError('Private paths must be absolute')
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed in private paths')
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Private source/output paths must not traverse symlinks')
        marker = parent / '.git'
        # This managed image has an empty /workspace/.git placeholder which Git
        # itself does not recognize as a repository. A real/unreadable marker is
        # still rejected, including linked-worktree files and unborn checkouts.
        if marker.exists() and not (marker.is_dir() and not any(marker.iterdir())):
            raise ValueError('Raw audio and transcripts must remain outside Git checkouts')
    if exists and not path.is_file():
        raise ValueError('Expected private regular file is missing')
    return path


def positive_number(value, label, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be a finite positive number')
    if maximum is not None and value > maximum:
        raise ValueError(label + ' exceeds the declared bound')
    return value


def atomic_json(path, obj):
    temporary = path.with_name(path.name + '.partial')
    with temporary.open('x', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(obj, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def text_file(path, text):
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        stream.write(text)


def artifact(path, source_id, kind, **extra):
    return {'local_path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'status': 'verified', 'source_id': source_id, 'kind': kind, **extra}


def probe_media(path):
    command = ['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
               '-show_entries', 'format=duration,format_name:stream=index,codec_type,codec_name,sample_rate,channels,width,height',
               '-of', 'json', str(path)]
    try:
        result = subprocess.run(command, capture_output=True, check=True, text=True, timeout=60)
        info = json.loads(result.stdout)
        duration = positive_number(float(info['format']['duration']), 'Decoded-container duration', MAX_DURATION)
    except (subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('ffprobe did not validate a finite local media duration') from exc
    streams = info.get('streams')
    if not isinstance(streams, list) or not any(s.get('codec_type') == 'audio' for s in streams):
        raise ValueError('The source has no audio stream')
    return {'duration_seconds': duration, 'format_name': info['format'].get('format_name'), 'streams': streams}


def validate_record(raw):
    if not isinstance(raw, dict):
        raise ValueError('Each source must be a JSON object')
    for key in ('source_id', 'medium_id', 'channel_id'):
        if not isinstance(raw.get(key), str) or not IDENTIFIER.fullmatch(raw[key]):
            raise ValueError(key + ' must be a bounded stable identifier; use an explicit unknown context when unresolved')
    if raw.get('provider') not in ('youtube', 'publisher_rss', 'publisher_video', 'publisher_audio') or raw.get('kind') not in ('video', 'audio'):
        raise ValueError('A supported explicit provider and media kind are required')
    if not isinstance(raw.get('sha256'), str) or not HASH.fullmatch(raw['sha256']):
        raise ValueError('A source SHA-256 is required')
    size = raw.get('bytes')
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ValueError('Source bytes must be a positive integer')
    path = private_path(raw.get('local_path'), exists=True)
    if path.stat().st_size != size or sha256(path) != raw['sha256']:
        raise ValueError('Source bytes or hash differ from the selected artifact')
    proof = raw.get('verification_receipt')
    if not isinstance(proof, dict) or not HASH.fullmatch(str(proof.get('sha256', ''))):
        raise ValueError('A hash-bound media verification receipt is required')
    proof_path = private_path(proof.get('path'), exists=True)
    if proof_path.stat().st_size > 8 * 1024**2 or sha256(proof_path) != proof['sha256']:
        raise ValueError('Verification receipt is oversized or its hash differs')
    report = json.loads(proof_path.read_text(encoding='utf-8'))
    if not isinstance(report, dict) or not isinstance(report.get('verified_artifacts'), list):
        raise ValueError('Verification receipt must contain a finalized artifact list')
    matching = [item for item in report.get('verified_artifacts', []) if isinstance(item, dict)
                and all(item.get(k) == raw[k] for k in ('local_path', 'sha256', 'bytes', 'source_id', 'kind'))
                and item.get('status') == 'verified']
    if len(matching) != 1:
        raise ValueError('Verification receipt must bind exactly one matching finalized media artifact')
    for key in ('provider', 'medium_id', 'channel_id', 'source_language', 'source_language_status',
                'is_short', 'duration_scope', 'metadata_refreshed_at_acquisition'):
        declared = matching[0].get(key)
        if declared is not None and raw.get(key) != declared:
            raise ValueError('Manifest contradicts or omits proof-bound ' + key)
    media = probe_media(path)
    if raw['kind'] == 'video' and not any(s.get('codec_type') == 'video' for s in media['streams']):
        raise ValueError('A video artifact must have both video and audio streams')
    if raw['kind'] == 'video' and media['duration_seconds'] < 300:
        raise ValueError('Selected videos must be at least five minutes long')
    if raw['provider'] == 'publisher_video' and raw['kind'] != 'video':
        raise ValueError('Publisher-video inputs must be actual audio-and-video files')
    if raw['provider'] == 'publisher_video':
        duration = positive_number(raw.get('duration_seconds'), 'Publisher source duration', MAX_DURATION)
        if duration < 300 or abs(duration - media['duration_seconds']) > max(2, duration * .02):
            raise ValueError('Publisher video and declared source durations do not match')
    if raw['provider'] == 'publisher_audio':
        # An original audio-only track from a public publisher player is neither
        # an RSS enclosure nor an acquired video. Keep its identity explicit.
        if raw['kind'] != 'audio' or matching[0].get('provider') != 'publisher_audio':
            raise ValueError('Publisher-audio source requires an explicit proof-bound audio provider')
        if any(stream.get('codec_type') == 'video' for stream in media['streams']):
            raise ValueError('Publisher-audio input must be an actual audio-only track without video streams')
        duration = positive_number(raw.get('duration_seconds'), 'Publisher audio source duration', MAX_DURATION)
        validation = matching[0].get('validation', {})
        bound_duration = positive_number(validation.get('ffprobe_duration_seconds'), 'Publisher audio receipt duration', MAX_DURATION)
        if (validation.get('source_id') != raw['source_id']
                or not HASH.fullmatch(str(validation.get('acquisition_receipt_sha256', '')))):
            raise ValueError('Publisher-audio receipt must bind the original acquisition and exact source ID')
        acquisition_binding = report.get('acquisition_receipt', {})
        if (not isinstance(acquisition_binding, dict)
                or acquisition_binding.get('sha256') != validation['acquisition_receipt_sha256']):
            raise ValueError('Publisher-audio acquisition receipt binding is missing or contradictory')
        acquisition_path = private_path(acquisition_binding.get('path'), exists=True)
        if acquisition_path.stat().st_size > 8 * 1024**2 or sha256(acquisition_path) != acquisition_binding['sha256']:
            raise ValueError('Publisher-audio acquisition receipt bytes differ')
        acquisition = json.loads(acquisition_path.read_text(encoding='utf-8'))
        original = acquisition.get('audio', {})
        if (acquisition.get('status') != 'completed' or acquisition.get('source_id') != raw['source_id']
                or original.get('path') != raw['local_path'] or original.get('sha256') != raw['sha256']
                or original.get('bytes') != raw['bytes']):
            raise ValueError('Publisher-audio acquisition receipt does not bind this completed original audio')
        acquired_duration = positive_number(acquisition.get('duration_seconds'), 'Acquired publisher audio duration', MAX_DURATION)
        if (min(duration, media['duration_seconds'], bound_duration) < 300
                or abs(duration - media['duration_seconds']) > max(2, duration * .02)
                or abs(bound_duration - media['duration_seconds']) > .1
                or acquired_duration < 300 or abs(acquired_duration - media['duration_seconds']) > .1):
            raise ValueError('Publisher audio is short or its source/receipt/media durations differ')
    if raw['provider'] == 'youtube':
        vid = raw.get('video_id')
        if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid) or raw['source_id'] != 'youtube:' + vid:
            raise ValueError('YouTube source identity must match its exact video ID')
        if raw.get('is_short') is not False or raw.get('metadata_refreshed_at_acquisition') is not True or raw.get('duration_scope') != 'source_video':
            raise ValueError('YouTube artifacts require explicit acquisition-time long-form metadata')
        duration = positive_number(raw.get('duration_seconds'), 'YouTube source duration', MAX_DURATION)
        validation = matching[0].get('validation', {})
        bound_duration = positive_number(validation.get('ffprobe_duration_seconds'), 'Receipt media duration', MAX_DURATION)
        if (duration < 300 or media['duration_seconds'] < 300 or bound_duration < 300
                or validation.get('source_video_id') != vid
                or not HASH.fullmatch(str(validation.get('metadata_sha256', '')))):
            raise ValueError('YouTube source requires a bound fresh-metadata/ID/duration validation')
        if abs(media['duration_seconds'] - duration) > max(2, duration * .02) or abs(media['duration_seconds'] - bound_duration) > .1:
            raise ValueError('YouTube media and declared source durations do not match')
    return dict(raw), media


def decode_audio(source, target, duration, *, reserve_bytes=FREE_RESERVE):
    """Decode the full first audio stream locally; never follow network protocols."""
    estimate = math.ceil(duration * SAMPLE_RATE * 2 * 1.03) + 1024**2
    if shutil.disk_usage(target.parent).free < estimate + reserve_bytes:
        raise ValueError('Insufficient disk for decoded audio plus the free-space reserve')
    partial = target.with_name(target.stem + '.partial.wav')
    command = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
               '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:a:0', '-vn',
               '-ac', '1', '-ar', str(SAMPLE_RATE), '-c:a', 'pcm_s16le', '-f', 'wav', str(partial)]
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=min(1200, max(120, duration * .5)))
    except subprocess.SubprocessError as exc:
        raise ValueError('Full local audio decoding failed; any partial output was not admitted') from exc
    if partial.stat().st_size > estimate:
        raise ValueError('Decoded audio exceeds its reserved duration-derived size')
    with wave.open(str(partial), 'rb') as audio:
        if audio.getframerate() != SAMPLE_RATE or audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError('Decoded analysis audio does not have the required PCM format')
        decoded_duration = audio.getnframes() / SAMPLE_RATE
    if decoded_duration <= 0 or abs(decoded_duration - duration) > max(2, duration * .02):
        raise ValueError('Decoded audio duration differs materially from container duration')
    if target.exists():
        raise ValueError('Refusing to overwrite previously decoded audio')
    os.replace(partial, target)
    os.chmod(target, 0o600)
    return decoded_duration


def audio_metrics(path):
    """Measure decoded PCM, including sample-weighted, non-overlapping quiet windows."""
    total = 0
    square_sum = 0
    signed_sum = 0
    peak = 0
    near_full = 0
    quiet_samples = 0
    quiet_windows = 0
    windows = 0
    quiet_start = None
    longest_quiet = 0
    qualifying_quiet_runs = 0
    threshold_squared = (32768 * 10**(SILENCE_DBFS / 20))**2
    with wave.open(str(path), 'rb') as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError('Metrics require 16 kHz mono signed 16-bit PCM WAV')
        while True:
            block = audio.readframes(WINDOW_SAMPLES)
            if not block:
                break
            values = array('h', block)
            if sys.byteorder != 'little':
                values.byteswap()
            n = len(values)
            power = sum(v * v for v in values)
            square_sum += power
            signed_sum += sum(values)
            peak = max(peak, max(abs(v) for v in values))
            near_full += sum(abs(v) / 32768 >= NEAR_FULL_SCALE for v in values)
            quiet = power / n <= threshold_squared
            if quiet:
                quiet_samples += n
                quiet_windows += 1
                if quiet_start is None:
                    quiet_start = total
            elif quiet_start is not None:
                length = total - quiet_start
                longest_quiet = max(longest_quiet, length)
                qualifying_quiet_runs += length >= SAMPLE_RATE / 2
                quiet_start = None
            total += n
            windows += 1
    if not total:
        raise ValueError('Decoded audio contains no samples')
    if quiet_start is not None:
        length = total - quiet_start
        longest_quiet = max(longest_quiet, length)
        qualifying_quiet_runs += length >= SAMPLE_RATE / 2
    rms = math.sqrt(square_sum / total) / 32768
    peak_fraction = peak / 32768
    return {'schema_version': SCHEMA, 'scope': 'First audio stream after mono downmix and resampling; full decoded recording',
            'sample_rate_hz': SAMPLE_RATE, 'channels': 1, 'sample_format': 'signed 16-bit little-endian PCM',
            'sample_count': total, 'decoded_duration_seconds': total / SAMPLE_RATE,
            'rms_fraction_full_scale': rms, 'rms_dbfs': 20 * math.log10(rms) if rms else None,
            'sample_peak_fraction_full_scale': peak_fraction,
            'sample_peak_dbfs': 20 * math.log10(peak_fraction) if peak_fraction else None,
            'dc_offset_fraction_full_scale': signed_sum / total / 32768,
            'near_full_scale_threshold_fraction': NEAR_FULL_SCALE,
            'near_full_scale_samples': near_full, 'near_full_scale_sample_fraction': near_full / total,
            'quiet_window_milliseconds': 20, 'quiet_threshold_dbfs': SILENCE_DBFS,
            'quiet_windows': quiet_windows, 'total_windows': windows,
            'quiet_samples': quiet_samples, 'quiet_duration_seconds': quiet_samples / SAMPLE_RATE,
            'quiet_sample_fraction': quiet_samples / total,
            'longest_contiguous_quiet_seconds': longest_quiet / SAMPLE_RATE,
            'quiet_runs_at_least_half_second': qualifying_quiet_runs,
            'definitions': {'dbfs': '20 log10(normalized amplitude); null means negative infinity for exact digital zero.',
                'quiet': 'Non-overlapping 20 ms windows with RMS <= -40 dBFS; the final partial window is weighted by its actual samples.',
                'near_full_scale': 'Absolute decoded sample amplitude >= .999 of 32768; a clipping-risk indicator, not proof of analog clipping.',
                'runs': 'Consecutive quiet windows; no phonetic, musical or speech classification is inferred.'},
            'limitations': ['Downmixing, resampling and encoding affect these measurements.',
                'Quiet-window duration is not speaking time. ASR VAD duration is a separate model output.',
                'These statistics do not measure emotion, truth, identity, spiritual state or physical extraterrestrial origin.']}


def local_model_binding(path):
    path = private_path(path)
    if not path.is_dir():
        raise ValueError('Supply an existing local model directory; model downloads are disabled')
    files = []
    vocabularies = [name for name in ('vocabulary.txt', 'vocabulary.json') if (path / name).is_file()]
    if not vocabularies:
        raise ValueError('The local CTranslate2 vocabulary file is missing')
    for name in (*MODEL_FILES, *vocabularies):
        file = private_path(path / name, exists=True)
        files.append({'path': name, 'bytes': file.stat().st_size, 'sha256': sha256(file)})
    config = json.loads((path / 'config.json').read_text())
    tokenizer = json.loads((path / 'tokenizer.json').read_text())
    vocabulary = dict(tokenizer.get('model', {}).get('vocab', {}))
    for token in tokenizer.get('added_tokens', []):
        if token.get('content') in ('<|endoftext|>', '<|startoftranscript|>'):
            name, token_id = token['content'], token.get('id')
            if name in vocabulary and vocabulary[name] != token_id:
                raise ValueError('Tokenizer has conflicting language-contract token IDs')
            vocabulary[name] = token_id
    special = (vocabulary.get('<|endoftext|>'), vocabulary.get('<|startoftranscript|>'))
    if special == (50256, 50257):
        language_mode = 'english-only'
    elif special == (50257, 50258):
        language_mode = 'multilingual'
    else:
        raise ValueError('Local checkpoint has an unrecognized Whisper language/tokenizer contract')
    return {'path': str(path), 'files': files, 'files_sha256': object_hash(files),
            'model_name': 'local CTranslate2 Whisper checkpoint', 'config_model_type': config.get('model_type'),
            'language_mode': language_mode,
            'language_mode_basis': 'Whisper end-of-text/start-of-transcript token IDs; cross-checked against loaded CTranslate2 model'}


def language_plan(record, model, requested):
    source = record.get('source_language') or 'unknown'
    if not isinstance(source, str) or not re.fullmatch(r'unknown|[a-z]{2,3}(?:-[A-Za-z0-9]+)*', source):
        raise ValueError('source_language must be unknown or a declared language code')
    if not isinstance(requested, str) or not re.fullmatch(r'auto|[a-z]{2,3}', requested):
        raise ValueError('Requested ASR language must be auto or a language code')
    source_base = source.split('-')[0]
    language_status = record.get('source_language_status', 'declared' if source != 'unknown' else 'missing')
    if language_status not in ('declared', 'missing', 'invalid', 'conflicting'):
        raise ValueError('Unrecognized source language metadata status')
    if model['language_mode'] == 'english-only' and language_status in ('invalid', 'conflicting'):
        raise ValueError('Resolve invalid/conflicting language metadata before English-only transcription')
    if model['language_mode'] == 'english-only' and (requested != 'en' or source_base not in ('en', 'unknown')):
        raise ValueError('English-only ASR cannot process a known non-English source or autodetect language')
    if source_base != 'unknown' and requested not in ('auto', source_base):
        raise ValueError('Requested ASR language conflicts with the declared source language')
    return {'source_language': source, 'requested_language': requested,
            'source_language_status': language_status,
            'effective_language_argument': None if requested == 'auto' else requested,
            'assumption': ('Source language is unknown; explicit requested language is an unverified assumption.'
                           if source == 'unknown' and requested != 'auto' else None),
            'automatic_language_detection': requested == 'auto',
            'language_mode': model['language_mode'],
            'scope': 'Metadata or model language estimates are not a human audit of every spoken segment.'}


def versions(transcribe):
    out = {'python': sys.version.split()[0]}
    for tool in ('ffmpeg', 'ffprobe'):
        out[tool] = subprocess.check_output([tool, '-version'], text=True, timeout=15).splitlines()[0]
    if transcribe:
        for package in ('faster-whisper', 'ctranslate2', 'av', 'onnxruntime', 'numpy'):
            out[package] = importlib.metadata.version(package)
        spec = importlib.util.find_spec('faster_whisper')
        assets = Path(spec.origin).parent / 'assets'
        out['vad_assets'] = [{'path': p.name, 'sha256': sha256(p)} for p in sorted(assets.glob('*.onnx'))]
        if not out['vad_assets']:
            raise ValueError('Installed local VAD model asset is unavailable')
    return out


def timestamp(seconds, *, srt=False):
    if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Invalid segment time')
    value = round(seconds * 1000)
    hours, value = divmod(value, 3600000)
    minutes, value = divmod(value, 60000)
    seconds, milliseconds = divmod(value, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02}{"," if srt else "."}{milliseconds:03}'


class TimestampValidationError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__('ASR timestamp validation failed: ' + encoded(diagnostic))


def normalize_segments(segments, duration, progress=None):
    rows = []
    previous_start = 0
    for index, segment in enumerate(segments):
        start, end = float(segment.start), float(segment.end)
        if not all(math.isfinite(v) for v in (start, end)) or start < 0 or end < start or start < previous_start or end > duration + 1:
            # repr preserves the exact offending numeric values, including NaN,
            # without emitting non-standard JSON or silently changing timings.
            raise TimestampValidationError({'segment_index': index, 'start_repr': repr(start),
                'end_repr': repr(end), 'previous_start_repr': repr(previous_start),
                'decoded_duration_repr': repr(duration),
                'reason': ('nonfinite' if not all(math.isfinite(v) for v in (start, end)) else
                    'negative_start' if start < 0 else 'end_before_start' if end < start else
                    'start_regression' if start < previous_start else 'beyond_duration')})
        previous_start = start
        text = segment.text.strip()
        if text:
            rows.append({'start_seconds': start, 'end_seconds': end, 'text': text,
                         'avg_logprob': getattr(segment, 'avg_logprob', None),
                         'no_speech_probability': getattr(segment, 'no_speech_prob', None)})
            if progress is not None and len(rows) % 100 == 0:
                progress(len(rows), end)
    return rows


def repair_terminal_end(raw_segments, duration, *, max_overrun_seconds=30.0):
    """Explicit diagnostic recovery; never called automatically by inference.

    Only the final segment may end beyond EOF, with both endpoints within one
    30-second Whisper window of EOF. Preserve text/order and every earlier time.
    This bounds a display interval; it cannot validate the terminal spoken words.
    """
    positive_number(duration, 'Decoded duration', MAX_DURATION)
    positive_number(max_overrun_seconds, 'Terminal recovery bound', 30)
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ValueError('Terminal recovery requires the entire nonempty diagnostic stream')
    candidates = []
    for index, row in enumerate(raw_segments):
        if row.get('segment_index') != index or not isinstance(row.get('text'), str):
            raise ValueError('Diagnostic segment indices/text are invalid')
        candidates.append(SimpleNamespace(start=float(row['start_repr']), end=float(row['end_repr']),
            text=row['text'], avg_logprob=(None if row.get('avg_logprob_repr') in (None, 'None') else float(row['avg_logprob_repr'])),
            no_speech_prob=(None if row.get('no_speech_prob_repr') in (None, 'None') else float(row['no_speech_prob_repr']))))
    normalize_segments(candidates[:-1], duration)
    if any(segment.end > duration for segment in candidates[:-1]):
        raise ValueError('Terminal recovery cannot also admit an earlier end beyond decoded duration')
    last = candidates[-1]
    if (not all(math.isfinite(v) for v in (last.start, last.end))
            or not max(0, duration - 30) <= last.start < duration
            or not duration < last.end <= duration + max_overrun_seconds):
        raise ValueError('Only a bounded final-segment end overrun is eligible for explicit recovery')
    original_end = last.end
    last.end = duration
    repaired = normalize_segments(candidates, duration)
    if not repaired or not last.text.strip():
        raise ValueError('Terminal recovery requires a nonempty final segment')
    repaired[-1].update(original_start_seconds=last.start, original_end_seconds=original_end,
                        timestamp_repair='terminal_end_clipped_to_decoded_duration')
    quality = {'timestamp_policy': 'terminal_end_clipped_to_decoded_duration',
        'timestamp_anomaly_count': 1, 'timestamp_repaired_segment_count': 1,
        'timestamp_maximum_adjustment_seconds': original_end - duration,
        'text_changed_by_repair': False, 'terminal_text_alignment_unverified': True,
        'timestamp_repair': {'raw_segment_index': len(candidates) - 1,
            'original_start_seconds': last.start, 'original_end_seconds': original_end,
            'corrected_end_seconds': duration, 'max_allowed_overrun_seconds': max_overrun_seconds,
            'earlier_timestamps_unchanged': True, 'segment_order_unchanged': True,
            'policy_scope': 'Display interval restricted to existing audio; terminal recognition/alignment remains unverified.'}}
    return repaired, quality


def run_asr(audio, model, duration, languages, diagnostics=None):
    from faster_whisper import WhisperModel
    engine = WhisperModel(str(model), device='cpu', compute_type='int8', cpu_threads=2,
                          num_workers=1, local_files_only=True)
    if bool(engine.model.is_multilingual) != (languages['language_mode'] == 'multilingual'):
        raise ValueError('Loaded model language capability differs from its bound tokenizer')
    print(json.dumps({'stage': 'asr_started', 'decoded_seconds': duration, 'requested_language': languages['requested_language']}), flush=True)
    stream, info = engine.transcribe(str(audio), language=languages['effective_language_argument'], beam_size=5, vad_filter=True,
                                    vad_parameters={'min_silence_duration_ms': 500}, temperature=0)
    report = {'language_requested': languages['requested_language'], 'language_reported': info.language,
                  'language_plan': languages,
                  'reported_language_probability': info.language_probability,
                  'decoder_duration_seconds': info.duration,
                  'duration_after_vad_seconds': info.duration_after_vad,
                  'scope': 'Full decoded audio submitted; VAD and recognition may omit speech.',
                  'human_reviewed': False, 'speaker_diarization_performed': False,
                  'named_entities_verified': False, 'model_probabilities_calibrated': False}
    def progress(count, end):
        print(json.dumps({'stage': 'asr_progress', 'segments': count, 'last_segment_end_seconds': end}), flush=True)
    if diagnostics is None:
        return normalize_segments(stream, duration, progress=progress), report
    # Optional private diagnostic capture exhausts the actual generator even
    # after a timestamp guard failure. It is never an admitted transcript; a
    # later repair needs its own explicit method and validation receipt.
    count = 0
    journal = diagnostics / 'asr-raw-segments.jsonl'
    with journal.open('x', encoding='utf-8') as target:
        os.chmod(journal, 0o600)
        def captured():
            nonlocal count
            for segment in stream:
                target.write(encoded({'segment_index': count, 'start_repr': repr(float(segment.start)),
                    'end_repr': repr(float(segment.end)), 'text': segment.text,
                    'avg_logprob_repr': repr(getattr(segment, 'avg_logprob', None)),
                    'no_speech_prob_repr': repr(getattr(segment, 'no_speech_prob', None))}) + '\n')
                target.flush()
                count += 1
                yield segment
        candidate = captured()
        error = None
        try:
            rows = normalize_segments(candidate, duration, progress=progress)
        except TimestampValidationError as exc:
            error = exc
            for _ in candidate:
                pass
        target.flush()
        os.fsync(target.fileno())
    atomic_json(diagnostics / 'asr-diagnostic-completion.json', {
        'schema_version': SCHEMA, 'status': 'diagnostic_only_not_admitted',
        'inference_stream_exhausted': True, 'raw_segment_count': count,
        'raw_segments': {'path': str(journal), 'sha256': sha256(journal), 'bytes': journal.stat().st_size},
        'request_sha256': sha256(diagnostics / 'request.json'), 'asr': report,
        'first_timestamp_failure': error.diagnostic if error is not None else None})
    if error is not None:
        raise error
    return rows, report


def verify_completed(receipt_path, binding):
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('binding_sha256') != object_hash(binding) or receipt.get('binding') != binding:
        raise ValueError('Existing result is bound to different source/model/settings/code')
    if receipt.get('status') not in ('completed', 'completed_metrics_only', 'completed_no_recognized_speech'):
        raise ValueError('Existing result is not complete')
    items = receipt.get('verified_artifacts')
    if not isinstance(items, list) or len(items) < 3:
        raise ValueError('Existing result has no complete artifact list')
    for item in items:
        retained = item.get('retained', True)
        if not isinstance(retained, bool):
            raise ValueError('Artifact retention state must be explicit boolean')
        path = private_path(item.get('local_path'), exists=retained)
        source_path = binding['source']['local_path']
        if str(path) != source_path and not path.is_relative_to(receipt_path.parent):
            raise ValueError('Existing result refers outside its source/output scope')
        if not retained:
            if (binding.get('storage', {}).get('retain_decoded_audio') is not False
                    or path != receipt_path.parent / 'audio-16khz-mono.wav'
                    or str(path) == source_path or item.get('kind') != 'audio'
                    or item.get('disposition') != 'new_derivative_removed_after_verification'
                    or not HASH.fullmatch(str(item.get('sha256', '')))
                    or isinstance(item.get('bytes'), bool) or not isinstance(item.get('bytes'), int)
                    or item['bytes'] <= 0 or path.exists()):
                raise ValueError('Only the explicitly discarded new decoded derivative may be absent')
            continue
        if path.stat().st_size != item.get('bytes') or sha256(path) != item.get('sha256'):
            raise ValueError('Existing completed artifact was changed; refusing silent replacement')
    return receipt


def process_record(raw, output, *, transcribe=False, model_path=DEFAULT_MODEL, language='en', retain_asr_diagnostics=False,
                   min_free_bytes=FREE_RESERVE, retain_decoded_audio=True):
    if isinstance(min_free_bytes, bool) or not isinstance(min_free_bytes, int) or min_free_bytes < 0:
        raise ValueError('Minimum free bytes must be a nonnegative integer')
    if not isinstance(retain_decoded_audio, bool):
        raise ValueError('Decoded-audio retention must be boolean')
    record, media = validate_record(raw)
    source = Path(record['local_path'])
    runtime = versions(transcribe)
    model = local_model_binding(model_path) if transcribe else None
    languages = language_plan(record, model, language) if transcribe else None
    binding = {'schema_version': SCHEMA, 'source': record,
               'media_probe': media, 'script_sha256': sha256(Path(__file__)), 'versions': runtime,
               'analysis': {'sample_rate_hz': SAMPLE_RATE, 'window_samples': WINDOW_SAMPLES,
                            'quiet_threshold_dbfs': SILENCE_DBFS, 'near_full_scale_fraction': NEAR_FULL_SCALE},
               'storage': {'min_free_bytes': min_free_bytes, 'retain_decoded_audio': retain_decoded_audio},
               'asr': {'requested': transcribe, 'model': model, 'device': 'cpu', 'compute_type': 'int8',
                       'cpu_threads': 2, 'num_workers': 1, 'language_plan': languages, 'beam_size': 5,
                       'temperature': 0, 'vad_filter': True, 'min_silence_duration_ms': 500,
                       'retain_asr_diagnostics': retain_asr_diagnostics}}
    signature = object_hash(binding)
    folder = output / 'sources' / object_hash(record['source_id'])[:16] / signature[:20]
    private_path(folder)
    receipt_path = folder / 'receipt.json'
    if receipt_path.exists():
        receipt = verify_completed(receipt_path, binding)
        return receipt_path, receipt, True
    if folder.exists() and any(folder.iterdir()):
        raise ValueError('Incomplete prior attempt retained; inspect it and choose a new output directory')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(folder, 0o700)
    started = time.perf_counter()
    request_path = folder / 'request.json'
    atomic_json(request_path, {'binding_sha256': signature, 'binding': binding, 'started_at': now()})
    decoded = folder / 'audio-16khz-mono.wav'
    duration = decode_audio(source, decoded, media['duration_seconds'], reserve_bytes=min_free_bytes)
    metrics = audio_metrics(decoded)
    print(json.dumps({'stage': 'audio_metrics_completed', 'source_id': record['source_id'], 'decoded_seconds': duration}), flush=True)
    metrics_path = folder / 'audio-metrics.json'
    atomic_json(metrics_path, metrics)
    inherited_validation = {'ffprobe_duration_seconds': media['duration_seconds']}
    if record['provider'] == 'youtube':
        proof = json.loads(Path(record['verification_receipt']['path']).read_text())
        inherited_validation = next(x['validation'] for x in proof['verified_artifacts']
                                    if x.get('local_path') == record['local_path'] and x.get('sha256') == record['sha256'])
    outputs = [artifact(source, record['source_id'], record['kind'], validation=inherited_validation),
               artifact(decoded, record['source_id'], 'audio'), artifact(metrics_path, record['source_id'], 'analysis'),
               artifact(request_path, record['source_id'], 'source-metadata')]
    asr = None
    status = 'completed_metrics_only'
    if transcribe:
        try:
            segments, asr = run_asr(decoded, model_path, duration, languages,
                                    diagnostics=folder if retain_asr_diagnostics else None)
        except TimestampValidationError as exc:
            atomic_json(folder / 'asr-timestamp-failure.json', {
                'schema_version': SCHEMA, 'status': 'failed_not_admitted',
                'binding_sha256': signature, 'source_id': record['source_id'],
                'timestamp_failure': exc.diagnostic})
            raise
        text = '\n'.join(row['text'] for row in segments)
        segment_json = folder / 'segments.json'
        atomic_json(segment_json, {'schema_version': SCHEMA, 'source_id': record['source_id'],
                                  'transcript_source': 'machine ASR; unverified', 'text': text, 'segments': segments})
        transcript = folder / 'transcript.txt'
        text_file(transcript, ''.join(f"[{timestamp(row['start_seconds'])} --> {timestamp(row['end_seconds'])}] {row['text']}\n" for row in segments))
        subtitles = folder / 'transcript.srt'
        text_file(subtitles, '\n'.join(f"{i}\n{timestamp(row['start_seconds'], srt=True)} --> {timestamp(row['end_seconds'], srt=True)}\n{row['text']}\n" for i, row in enumerate(segments, 1)))
        outputs.extend(artifact(p, record['source_id'], 'transcript') for p in (segment_json, transcript, subtitles))
        asr.update(segments=len(segments), whitespace_word_count=len(text.split()),
                   last_segment_end_seconds=segments[-1]['end_seconds'] if segments else None)
        status = 'completed' if segments else 'completed_no_recognized_speech'
    private_path(source, exists=True)
    if source.stat().st_size != record['bytes'] or sha256(source) != record['sha256']:
        raise ValueError('Source changed during audio processing; outputs are not admitted')
    final_proof = private_path(record['verification_receipt']['path'], exists=True)
    if sha256(final_proof) != record['verification_receipt']['sha256']:
        raise ValueError('Source verification proof changed during processing; outputs are not admitted')
    if record['provider'] == 'publisher_audio':
        # The upstream acquisition receipt is a separately retained file: bind
        # its unchanged bytes again, not only the outer proof that names it.
        validate_record(record)
    if model is not None and local_model_binding(model_path) != model:
        raise ValueError('Model files changed during inference; outputs are not admitted')
    if not retain_decoded_audio:
        # Only a derivative created in this fresh request folder can be removed.
        # Verify all newly finalized outputs first; originals/prior WAVs stay put.
        for item in outputs:
            path = private_path(item['local_path'], exists=True)
            if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
                raise ValueError('Output changed before derivative-retention decision')
        decoded_item = next(item for item in outputs if item['local_path'] == str(decoded))
        decoded_item.update(retained=False, disposition='new_derivative_removed_after_verification',
                            derived_from_sha256=record['sha256'], removed_at=now())
        decoded.unlink()
    receipt = {'schema_version': SCHEMA, 'kind': 'source-bound-audio-analysis', 'status': status,
               'completed_at': now(), 'binding_sha256': signature, 'binding': binding,
               'source_id': record['source_id'], 'provider': record['provider'],
               'new_source_downloads': 0, 'network_requests': 0, 'model_downloads': 0,
               'network_count_scope': 'This local audio-processing component only; upstream acquisition has separate receipts.',
               'decoded_duration_seconds': duration, 'audio_metrics': metrics, 'asr': asr,
               'elapsed_seconds': time.perf_counter() - started, 'verified_artifacts': outputs,
               'verification_scope': 'Source/output bytes, media streams and executed processing; not speech accuracy or source truth.',
               'limitations': ['ASR text is not a human-verified transcript or a speaker/claimed-entity attribution.',
                   'Host, presenter and audience speech may mix; no diarization assigns individual or entity turns.',
                   'Only the first audio stream is processed; original video/audio is retained separately.',
                   'Language selection and any unknown-language assumption are explicit; recognition accuracy is unvalidated.',
                   'Completed-result resume rehashes every artifact; partial ASR/decoder state is not resumed.',
                   'Publisher RSS recordings do not establish matching YouTube video-edition identity.']}
    atomic_json(receipt_path, receipt)
    return receipt_path, receipt, False


def final_artifacts(record, receipt_path, receipt):
    common = {k: record[k] for k in ('provider', 'medium_id', 'channel_id', 'source_id')}
    if record['provider'] == 'youtube':
        common.update({k: record[k] for k in ('video_id', 'duration_seconds', 'is_short', 'metadata_refreshed_at_acquisition', 'duration_scope')})
    return [{**item, **common, 'verification_receipt': {'path': str(receipt_path), 'sha256': sha256(receipt_path)}}
            for item in receipt['verified_artifacts'] if item.get('retained', True)]


def run_batch(input_path, output, *, transcribe=False, model_path=DEFAULT_MODEL, language='en', retain_asr_diagnostics=False,
              min_free_bytes=FREE_RESERVE, retain_decoded_audio=True):
    input_path = private_path(input_path, exists=True)
    if input_path.stat().st_size > 4 * 1024**2:
        raise ValueError('Input manifest exceeds 4 MiB')
    data = json.loads(input_path.read_text())
    if (not isinstance(data, dict) or data.get('schema_version') != SCHEMA
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', str(data.get('batch_id', '')))
            or not isinstance(data.get('records'), list) or len(data['records']) > 2000):
        raise ValueError('Expected schema_version 1, a bounded batch_id and records list (maximum 2,000)')
    output = private_path(output)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    results, finalized, seen = [], [], set()
    with (output / '.audio-worker.lock').open('a') as lock:
        os.chmod(output / '.audio-worker.lock', 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another audio worker owns this output directory') from exc
        for record in data['records']:
            source_id = record.get('source_id') if isinstance(record, dict) else None
            result = {'source_id': source_id, 'status': 'failed'}
            try:
                if source_id in seen:
                    raise ValueError('Duplicate source ID in one batch')
                seen.add(source_id)
                receipt_path, receipt, reused = process_record(record, output, transcribe=transcribe,
                    model_path=model_path, language=language, retain_asr_diagnostics=retain_asr_diagnostics,
                    min_free_bytes=min_free_bytes, retain_decoded_audio=retain_decoded_audio)
                result.update(status=receipt['status'], reused=reused, receipt_path=str(receipt_path),
                              receipt_sha256=sha256(receipt_path), provider=record['provider'])
                finalized.extend(final_artifacts(record, receipt_path, receipt))
            except Exception as exc:
                result.update(error_type=type(exc).__name__, error=str(exc)[:300] if isinstance(exc, ValueError) else 'Local processing failed; no outputs from this source were admitted')
            results.append(result)
            atomic_json(output / 'audio-run.json', {'schema_version': SCHEMA, 'batch_id': data['batch_id'],
                        'input_sha256': sha256(input_path), 'updated_at': now(), 'records': results,
                        'network_requests': 0, 'new_source_downloads': 0})
            print(f"{source_id or '<invalid>'}: {result['status']}", flush=True)
        storage = {'schema_version': SCHEMA, 'batch_id': data['batch_id'], 'artifacts': finalized,
                   'scope': 'Private verified file handoff; no Drive upload has been attempted by the audio tool.'}
        atomic_json(output / 'final-artifacts.json', storage)
    return {'records': results, 'artifacts': len(finalized), 'failed': sum(row['status'] == 'failed' for row in results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Private source manifest; exact schema in AUDIO.md')
    parser.add_argument('--output', type=Path, required=True, help='Private output directory outside every Git checkout')
    parser.add_argument('--transcribe', action='store_true', help='Run the existing local English ASR model; no download')
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL, help='Existing local CTranslate2 model directory only')
    parser.add_argument('--language', default='en', help='Explicit language code, or auto with a verified multilingual model')
    parser.add_argument('--retain-asr-diagnostics', action='store_true', help='Retain private raw segments and exhaust inference after a timestamp failure; never admit failed output')
    parser.add_argument('--min-free-bytes', type=int, default=FREE_RESERVE, help='Minimum free disk reserve, bound in each new request; default six GiB')
    parser.add_argument('--discard-decoded-audio', action='store_true', help='Remove only the new temporary PCM derivative after verified output; original media retained')
    args = parser.parse_args(argv)
    try:
        result = run_batch(args.input, args.output, transcribe=args.transcribe, model_path=args.model,
                           language=args.language, retain_asr_diagnostics=args.retain_asr_diagnostics,
                           min_free_bytes=args.min_free_bytes, retain_decoded_audio=not args.discard_decoded_audio)
    except (ValueError, OSError) as exc:
        print(f'Audio run stopped: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({'source_records': len(result['records']), 'finalized_artifacts': result['artifacts'], 'failed': result['failed']}))
    return int(result['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
