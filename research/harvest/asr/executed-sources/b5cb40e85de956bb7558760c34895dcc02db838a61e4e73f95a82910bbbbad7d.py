#!/usr/bin/env python3
"""Transcribe an actual local publisher audio file; keep all raw speech outside Git."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
RAW = Path('/workspace/channels-et-raw')
MODEL = Path('/workspace/channels-et-asr-cache/tiny-en')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def stamp(seconds):
    milliseconds = round(seconds * 1000)
    return f'{milliseconds // 3600000:02d}:{milliseconds // 60000 % 60:02d}:{milliseconds // 1000 % 60:02d},{milliseconds % 1000:03d}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--cpu-threads', type=int, default=2)
    parser.add_argument('--max-seconds', type=float, help='Explicit diagnostic clip, not a full transcription')
    args = parser.parse_args()
    if not 1 <= args.cpu_threads <= 4 or args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        raise ValueError('CPU threads must be 1..4 and an explicit clip must have positive length')
    if args.audio.is_symlink():
        raise ValueError('Input file must not be a symlink')
    audio = args.audio.resolve()
    if not audio.is_relative_to(RAW) or audio.is_symlink() or not audio.is_file():
        raise ValueError('Input must be an actual file in the external raw-media directory')
    audio_hash = digest(audio)
    if audio_hash != args.source_sha256:
        raise ValueError('Audio bytes do not match the saved acquisition receipt')
    publisher_receipts = HERE.parent / 'publisher_sources/publisher-summary.json'
    publisher = json.loads(publisher_receipts.read_text())
    matches = [r for r in publisher['records'] if r.get('status') == 'completed'
               and r.get('source_id') == args.source_id and r.get('enclosure_url') == args.source_url
               and r.get('sha256') == audio_hash and Path(r['raw_local_path']).resolve() == audio]
    if len(matches) != 1:
        raise ValueError('Source ID/URL/path/hash must resolve to one actual completed publisher acquisition')
    model_manifest = json.loads((HERE / 'model-manifest.json').read_text())
    for item in model_manifest['files']:
        if digest(MODEL / item['path']) != item['sha256']:
            raise ValueError('Model cache differs from its verified manifest')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(audio)], text=True))
    duration = float(probe['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Audio duration must be finite and positive')
    if not any(x['codec_type'] == 'audio' for x in probe['streams']):
        raise ValueError('Input has no detected audio stream')
    suffix = '-clip' + str(args.max_seconds) if args.max_seconds else ''
    output = RAW / 'transcripts' / (audio_hash[:20] + suffix)
    if RAW.resolve() != RAW or not output.resolve().is_relative_to(RAW):
        raise ValueError('Raw/output directories must remain outside Git at the fixed external path')
    output.mkdir(parents=True, exist_ok=True)
    for filename in ('receipt.json', 'segments.partial.jsonl', 'segments.jsonl', 'transcript.txt', 'transcript.srt'):
        if (output / filename).is_symlink():
            raise ValueError('Output must not be a symlink: ' + filename)
    receipt_path = output / 'receipt.json'
    options = {'language': 'en', 'beam_size': 1, 'vad_filter': True, 'condition_on_previous_text': False}
    if args.max_seconds:
        options['clip_timestamps'] = [0, args.max_seconds]
    versions = {p: importlib.metadata.version(p) for p in ['faster-whisper', 'ctranslate2', 'av']}
    signature_data = {'sourceId': args.source_id, 'sourceUrl': args.source_url, 'audioSha256': audio_hash,
                      'modelManifestSha256': digest(HERE / 'model-manifest.json'), 'versions': versions,
                      'cpuThreads': args.cpu_threads, 'decoding': options, 'scriptSha256': digest(Path(__file__))}
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    if receipt_path.exists():
        prior = json.loads(receipt_path.read_text())
        files = prior.get('outputs', [])
        if (prior.get('status') == 'completed' and prior.get('executionSignature') == signature
                and {r['name'] for r in files} == {'segments.jsonl', 'transcript.txt', 'transcript.srt'}
                and all((output / r['name']).is_file() and (output / r['name']).stat().st_size == r['bytes']
                        and digest(output / r['name']) == r['sha256'] for r in files)):
            (HERE / (audio_hash[:20] + suffix + '-receipt.json')).write_text(json.dumps({**prior, 'transcriptDirectory': str(output)}, indent=2) + '\n')
            print(json.dumps({'state': 'existing_verified_result', 'receipt': str(receipt_path)}))
            return
        receipt_path.rename(output / ('stale-receipt-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json'))
    if shutil.disk_usage(RAW).free < 6 * 1024**3:
        raise ValueError('ASR free-space reserve is below six GiB')
    from faster_whisper import WhisperModel
    import ctranslate2
    began = time.monotonic()
    model = WhisperModel(str(MODEL), device='cpu', compute_type='int8', cpu_threads=args.cpu_threads,
                         num_workers=1, local_files_only=True)
    segments, info = model.transcribe(str(audio), **options)
    rows = []
    partial = output / 'segments.partial.jsonl'
    if partial.exists():
        partial.rename(output / ('interrupted-segments-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.jsonl'))
    with partial.open('w') as stream:
        for segment in segments:
            row = {'id': segment.id, 'start': segment.start, 'end': segment.end,
                   'text': segment.text.strip(), 'avg_logprob': segment.avg_logprob,
                   'no_speech_prob': segment.no_speech_prob}
            if rows and row['start'] < rows[-1]['start']:
                raise ValueError('Segment times are not monotonic')
            if not (0 <= row['start'] <= row['end'] <= duration + 2):
                raise ValueError('Segment lies outside its actual media duration')
            rows.append(row)
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
    if not rows:
        raise RuntimeError('No ASR segments produced; this is not a completed speech transcript')
    partial.replace(output / 'segments.jsonl')
    (output / 'transcript.txt').write_text('\n'.join(row['text'] for row in rows) + '\n')
    (output / 'transcript.srt').write_text('\n\n'.join(f"{i}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text']}" for i, r in enumerate(rows, 1)) + '\n')
    files = [{'name': name, 'bytes': (output / name).stat().st_size, 'sha256': digest(output / name)}
             for name in ('segments.jsonl', 'transcript.txt', 'transcript.srt')]
    elapsed = time.monotonic() - began
    receipt = {'status': 'completed', 'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'sourceId': args.source_id, 'sourceUrl': args.source_url, 'sourceKind': 'publisher_original_audio',
               'sourceAudioPath': str(audio), 'sourceAudioSha256': audio_hash, 'sourceAudioDurationSeconds': duration,
               'publisherAcquisitionRecord': {'sourceId': matches[0]['source_id'], 'audioSha256': matches[0]['sha256'],
                                              'enclosureUrl': matches[0]['enclosure_url']},
               'transcribedScope': 'explicit_clip' if args.max_seconds else 'full_decoded_audio',
               'clipSeconds': args.max_seconds, 'lastSegmentEndSeconds': rows[-1]['end'] if rows else None,
               'segments': len(rows), 'words': len(' '.join(r['text'] for r in rows).split()),
               'modelId': model_manifest['modelId'], 'modelRevision': model_manifest['revision'],
               'device': 'cpu', 'computeType': 'int8', 'cpuThreads': args.cpu_threads,
               'versions': versions, 'executionSignature': signature, 'executionProtocol': signature_data,
               'cudaDevices': ctranslate2.get_cuda_device_count(), 'secondsElapsed': elapsed,
               'realTimeFactor': elapsed / min(duration, args.max_seconds or duration),
               'decoding': options, 'reportedLanguage': info.language, 'outputs': files,
               'decoderDurationSeconds': info.duration, 'durationAfterVadSeconds': info.duration_after_vad,
               'humanReviewed': False, 'speakerDiarizationPerformed': False, 'youtubeVideoEditionVerified': False,
               'limitations': ['Automatic English-only transcription; names, claims, punctuation and timestamps are unverified.',
                               'Full decoded audio is not proof that speech recognition captured every spoken word.',
                               'Primary audio publication and any indexed YouTube upload are distinct editions unless verified.',
                               'Raw audio and transcript text remain private cloud files, not part of the public Git/Pages release.']}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    # Public bookkeeping contains hashes/counts only, never source transcript text.
    public = {**receipt, 'transcriptDirectory': str(output)}
    (HERE / (audio_hash[:20] + suffix + '-receipt.json')).write_text(json.dumps(public, indent=2) + '\n')
    print(json.dumps({'status': 'completed', 'segments': len(rows), 'words': receipt['words'],
                      'secondsElapsed': elapsed, 'realTimeFactor': receipt['realTimeFactor'], 'receipt': str(receipt_path)}))


if __name__ == '__main__':
    main()
