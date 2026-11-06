#!/usr/bin/env python3
"""Transcribe local, ffprobe-validated recordings; never download media."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_atomic(path, text):
    temporary = path.with_name(path.name + '.tmp')
    try:
        temporary.write_text(text, encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_media(path, expected_hash=None):
    info = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
         '-of', 'json', str(path)], text=True, stderr=subprocess.PIPE, timeout=60))
    if not any(s.get('codec_type') == 'audio' for s in info.get('streams', [])):
        raise ValueError('No audio stream')
    duration = float(info['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid duration')
    media_hash = digest(path)
    if expected_hash and expected_hash != media_hash:
        raise ValueError('Media hash mismatch')
    return duration, media_hash


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path, help='JSON list of source records')
    p.add_argument('--output', required=True, type=Path, help='New private output directory outside Git')
    p.add_argument('--model', default='tiny', help='Whisper model name or local model path')
    p.add_argument('--device', default='cpu')
    p.add_argument('--compute-type', default='int8')
    p.add_argument('--language', default=None)
    args = p.parse_args(argv)
    records = json.loads(args.input.read_text(encoding='utf-8'))
    if not isinstance(records, list):
        raise ValueError('Input must be a JSON list')
    # Discover the checkout containing this script, independent of the caller's cwd.
    script_dir = Path(__file__).resolve().parent
    root = Path(subprocess.check_output(
        ['git', '-C', str(script_dir), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
    out = args.output.resolve()
    if out == root or root in out.parents:
        raise ValueError('Output must be outside the Git checkout')
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / 'transcription-manifest.json'
    if manifest.exists():
        raise ValueError('Output manifest already exists; choose a new output directory')
    results, seen, model = [], set(), None
    for row in records:
        record = {'status': 'failed', 'transcript_source': 'faster-whisper ASR'}
        try:
            if not isinstance(row, dict):
                raise ValueError('Record must be a JSON object')
            vid = row.get('video_id', '')
            record.update(video_id=vid, channel=row.get('channel', ''), title=row.get('title', ''))
            if not isinstance(vid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                raise ValueError('Invalid video ID')
            if vid in seen:
                raise ValueError('Duplicate video ID')
            seen.add(vid)
            if not row.get('channel') or not row.get('media_path'):
                raise ValueError('channel and media_path are required')
            record['source_url'] = 'https://www.youtube.com/watch?v=' + vid
            source = Path(row['media_path'])
            if not source.is_absolute():
                source = args.input.resolve().parent / source
            source = source.resolve()
            target = out / (vid + '.txt')
            segments_target = out / (vid + '.segments.json')
            if target.exists() or segments_target.exists():
                raise ValueError('Output for this video already exists')
            duration, media_hash = validate_media(source, row.get('sha256'))
            if model is None:
                from faster_whisper import WhisperModel
                model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
            segments, meta = model.transcribe(str(source), beam_size=5, language=args.language, vad_filter=True)
            lines, timings = [], []
            for segment in segments:  # faster-whisper defers inference until iteration
                text = segment.text.strip()
                if text:
                    lines.append(text)
                    timings.append({'start': segment.start, 'end': segment.end, 'text': text})
            if not lines:
                raise ValueError('No speech segments')
            if digest(source) != media_hash:
                raise ValueError('Media changed during transcription')
            write_atomic(target, '\n'.join(lines) + '\n')
            write_atomic(segments_target, json.dumps(timings, ensure_ascii=False, indent=2) + '\n')
            record.update(status='ok', transcript_path=str(target), transcript_sha256=digest(target),
                          media_sha256=media_hash, duration_seconds=duration, language=meta.language,
                          language_probability=meta.language_probability, model=args.model,
                          device=args.device, compute_type=args.compute_type,
                          asr_version=importlib.metadata.version('faster-whisper'))
        except Exception as exc:
            record['error'] = str(exc)[:500]
        results.append(record)
        write_atomic(manifest, json.dumps(results, ensure_ascii=False, indent=2) + '\n')
        print(f"{record.get('video_id', '<invalid>')}: {record['status']}", flush=True)
    if not records:
        write_atomic(manifest, '[]\n')
    print('Completed:', sum(r['status'] == 'ok' for r in results), '/', len(results))
    return int(any(r['status'] != 'ok' for r in results))


if __name__ == '__main__':
    sys.exit(main())
