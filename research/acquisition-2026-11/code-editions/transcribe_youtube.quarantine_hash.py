#!/usr/bin/env python3
"""Transcribe acquired public YouTube audio with pinned faster-whisper tiny.en.

Adapted from the publisher-cohort ASR pipeline: CPU int8, beam_size=1, VAD,
condition_on_previous_text=False, contiguous 300 s chunks covering 100% of each
file. No diarization, speaker verification, human WER, or edition-equivalence
claims. Provider-rendered subtitles are preserved as separate source artifacts.
"""
import datetime
import fcntl
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('${CHANNELS_ET_RAW_ROOT}/youtube-audio')
MODEL_CACHE = Path('${CHANNELS_ET_MODEL_CACHE}/tiny-en')
MANIFEST = Path('${CHANNELS_ET_REPO_ROOT}/research/harvest/asr/model-manifest.json')
CHUNK_SECONDS = 300
SETTINGS = {
    'language': 'en', 'beam_size': 1, 'vad_filter': True,
    'condition_on_previous_text': False, 'device': 'cpu', 'compute_type': 'int8',
    'modelId': 'Systran/faster-whisper-tiny.en',
    'revision': json.loads(MANIFEST.read_text())['revision'],
    'chunkSeconds': CHUNK_SECONDS,
    'chunkingNote': 'Every sample is decoded once to 16 kHz mono and transcribed in contiguous 300 s windows; timestamps are offset-stitched. Window-boundary words can be split; this is a recorded limitation.',
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def settings_hash():
    return hashlib.sha256(json.dumps(SETTINGS, sort_keys=True).encode()).hexdigest()


def code_hash():
    return sha256(Path(__file__).resolve())


def ffprobe(path):
    return json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
        text=True, timeout=300))


def srt_stamp(seconds):
    ms = round(seconds * 1000)
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def verify_model():
    for item in json.loads(MANIFEST.read_text())['files']:
        path = MODEL_CACHE / item['path']
        if not path.exists() or sha256(path) != item['sha256']:
            raise RuntimeError(f"model cache verification failed: {item['path']}")


ARABIC_RE = __import__('re').compile(r'[\u0621-\u063A\u0641-\u064A\u0671-\u06D3]')
GERMAN_MARKERS = set('der die das und ist nicht ich sie mit den von zu auf ein eine auch für an werden dem wie wir sind es war hat bei im des zum oder aus als haben dass sich so nur noch über kann aber wenn nach um am vor einer einem einen wurden'.split())
ENGLISH_MARKERS = set('the and is of to in that it for on with as are was at be this have from or one had by but not what all were they we when your can said there use an each which she do how their if will up other about out many then them these so some'.split())


def detect_language(text):
    arabic = len(ARABIC_RE.findall(text))
    latin = len(__import__('re').findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', text))
    if arabic >= 40 and arabic > 2 * max(1, latin):
        return 'ar'
    tokens = __import__('re').findall(r'[a-zA-ZäöüÄÖÜß]+', text.lower())
    if not tokens:
        return 'unknown'
    de = sum(token in GERMAN_MARKERS for token in tokens) / len(tokens)
    en = sum(token in ENGLISH_MARKERS for token in tokens) / len(tokens)
    if de > en and de > 0.08:
        return 'de'
    if en > 0.08:
        return 'en'
    return 'unknown'


def quarantine_language(directory, detected):
    quarantine = directory / 'quarantine'
    quarantine.mkdir(exist_ok=True)
    for name in ('asr-transcript.txt', 'asr-segments.jsonl', 'asr-transcript.srt', 'asr-receipt.json'):
        source = directory / name
        if source.exists():
            source.replace(quarantine / name)
    acquisition = json.loads((directory / 'acquisition.json').read_text())
    audio = directory / 'audio.mp3'
    receipt = {
        'videoId': directory.name,
        'status': 'excluded_language_mismatch',
        'detectedLanguage': detected,
        'expectedLanguage': 'en',
        'modelLanguage': 'en',
        'languageVerified': False,
        'exclusionReason': 'Non-English source must not be decoded through the English-only tiny.en model; provider text is retained separately for language-aware review.',
        'audioSha256': sha256(audio),
        'bytes': audio.stat().st_size,
        'durationSeconds': float(ffprobe(audio)['format']['duration']),
        'outputSha256': {name: sha256(quarantine / name) for name in
                         ('asr-transcript.txt', 'asr-segments.jsonl', 'asr-transcript.srt')},
        'settingsSha256': settings_hash(),
        'codeSha256': code_hash(),
        'quarantinedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'humanValidated': False,
    }
    (directory / 'asr-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(f'{directory.name} quarantined non-English ASR: {detected}', flush=True)
    return receipt


def transcribe_one(directory):
    acquisition_path = directory / 'acquisition.json'
    if not acquisition_path.exists():
        return {'videoId': directory.name, 'status': 'skipped', 'reason': 'no acquisition receipt'}
    acquisition = json.loads(acquisition_path.read_text())
    if acquisition.get('status') != 'completed':
        return {'videoId': directory.name, 'status': 'skipped',
                'reason': f"acquisition status {acquisition.get('status')}"}
    audio = directory / 'audio.mp3'
    if not audio.exists() or audio.is_symlink():
        return {'videoId': directory.name, 'status': 'failed', 'error': 'audio missing or symlink'}
    audio_hash = sha256(audio)
    if audio_hash != acquisition.get('sha256'):
        return {'videoId': directory.name, 'status': 'failed', 'error': 'audio hash changed since acquisition'}
    provider_path = ROOT.parent / 'youtube-transcripts' / directory.name / 'transcript.json'
    provider_text = ''
    if provider_path.exists():
        provider = json.loads(provider_path.read_text())
        provider_text = '\n'.join(row.get('text', '') for row in provider.get('records', []))
    detected = detect_language(provider_text) if provider_text else 'unknown'
    out_receipt = directory / 'asr-receipt.json'
    if out_receipt.exists():
        verify_model()
        old = json.loads(out_receipt.read_text())
        if old.get('status') == 'completed' and old.get('audioSha256') == audio_hash \
                and old.get('settingsSha256') == settings_hash() and old.get('codeSha256') == code_hash():
            ok = all((directory / name).exists() and sha256(directory / name) == h
                     for name, h in old.get('outputSha256', {}).items())
            if ok:
                print(f'{directory.name} reuse validated ASR result', flush=True)
                return old
    lock = (directory / '.asr.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return {'videoId': directory.name, 'status': 'skipped', 'reason': 'output lock held'}
    try:
        verify_model()
        probe = ffprobe(audio)
        duration = float(probe['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            raise RuntimeError('invalid duration')
        if not any(s['codec_type'] == 'audio' for s in probe['streams']):
            raise RuntimeError('no audio stream')
        from faster_whisper import WhisperModel
        import faster_whisper
        import av
        import ctranslate2
        model = WhisperModel(str(MODEL_CACHE), device='cpu', compute_type='int8',
                             cpu_threads=1, num_workers=1)
        from faster_whisper.audio import decode_audio
        started = time.time()
        waveform = decode_audio(str(audio), sampling_rate=16000)
        sr = 16000
        total_samples = waveform.shape[0]
        segments, seg_id, chunk_index = [], 0, 0
        partial_path = directory / 'asr-segments.partial.jsonl'
        with partial_path.open('w') as partial:
            for start_sample in range(0, total_samples, CHUNK_SECONDS * sr):
                chunk = waveform[start_sample:start_sample + CHUNK_SECONDS * sr]
                offset = start_sample / sr
                iterator, _info = model.transcribe(
                    chunk, language='en', beam_size=1, vad_filter=True,
                    condition_on_previous_text=False)
                for seg in iterator:
                    record = {'id': seg_id, 'start': round(seg.start + offset, 3),
                              'end': round(seg.end + offset, 3), 'text': seg.text,
                              'chunk': chunk_index}
                    seg_id += 1
                    segments.append(record)
                    partial.write(json.dumps(record) + '\n')
                    partial.flush()
                chunk_index += 1
        del waveform
        with (directory / 'asr-segments.jsonl').open('w') as handle:
            for record in segments:
                handle.write(json.dumps(record) + '\n')
        text = ''.join(s['text'] for s in segments).strip() + '\n'
        (directory / 'asr-transcript.txt').write_text(text)
        with (directory / 'asr-transcript.srt').open('w') as handle:
            for index, segment in enumerate(segments, 1):
                handle.write(f"{index}\n{srt_stamp(segment['start'])} --> {srt_stamp(segment['end'])}\n"
                             f"{segment['text'].strip()}\n\n")
        partial_path.unlink(missing_ok=True)
        elapsed = time.time() - started
        overlap_count = sum(1 for left, right in zip(segments, segments[1:])
                            if right['start'] < left['end'])
        words = text.lower().split()
        trigrams = [' '.join(words[index:index + 3]) for index in range(max(0, len(words) - 2))]
        repeated_trigram_share = (max(__import__('collections').Counter(trigrams).values()) / max(1, len(trigrams)))
        words_per_minute = len(words) / (duration / 60 if duration else 1)
        audio_detected = detect_language(text)
        if detected in ('de', 'ar') and (words_per_minute < 50 or repeated_trigram_share >= 0.15):
            return quarantine_language(directory, detected)
        receipt = {
            'videoId': directory.name,
            'sourceUrl': acquisition['sourceUrl'],
            'title': acquisition.get('title'),
            'publisher': acquisition.get('publisher'),
            'practitionerContext': acquisition.get('practitionerContext'),
            'claimedGroup': acquisition.get('claimedGroup'),
            'status': 'completed',
            'sourceType': 'public_youtube_audio_self_run_ASR',
            'audioSha256': audio_hash,
            'audioEdition': 'y2mate_mp3_transcode',
            'detectedLanguage': audio_detected,
            'providerDetectedLanguage': detected,
            'providerEditionMismatch': detected != audio_detected and detected != 'unknown',
            'languageVerified': audio_detected == 'en' and words_per_minute >= 50 and repeated_trigram_share < 0.15,
            'languageReviewRequired': audio_detected == 'unknown',
            'wordRateWpm': round(words_per_minute, 2),
            'repeatedTrigramShare': round(repeated_trigram_share, 4),
            'boundaryOverlapCount': overlap_count,
            'audioBytes': audio.stat().st_size,
            'ffprobeDurationSeconds': duration,
            'audioStreams': [s['codec_name'] for s in probe['streams'] if s['codec_type'] == 'audio'],
            'segmentCount': len(segments),
            'wordCount': len(text.split()),
            'lastSegmentEnd': segments[-1]['end'] if segments else 0.0,
            'fullLength': abs(total_samples / sr - duration) <= 1.0,
            'chunksProcessed': chunk_index,
            'decodedDurationSeconds': round(total_samples / sr, 3),
            'settings': SETTINGS,
            'settingsSha256': settings_hash(),
            'codeSha256': code_hash(),
            'codePath': str(Path(__file__).resolve()),
            'modelCacheVerification': str(MODEL_CACHE / 'cache-verification.json'),
            'versions': {'faster_whisper': faster_whisper.__version__,
                         'ctranslate2': ctranslate2.__version__, 'av': av.__version__},
            'elapsedSeconds': round(elapsed, 1),
            'realtimeFactor': round(duration / elapsed, 2) if elapsed else None,
            'outputSha256': {name: sha256(directory / name) for name in
                             ('asr-transcript.txt', 'asr-segments.jsonl', 'asr-transcript.srt')},
            'completedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'humanValidated': False,
            'claims': 'No diarization, no human WER, no speaker identity, no YouTube-edition equivalence. tiny.en int8 CPU baseline ASR only.',
        }
        out_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(f"{directory.name} ASR words={receipt['wordCount']} segments={len(segments)} "
              f"duration={duration:.0f}s elapsed={elapsed:.0f}s", flush=True)
        return receipt
    except Exception as exc:  # noqa: BLE001
        receipt = {'videoId': directory.name, 'status': 'failed',
                   'error': f'{type(exc).__name__}: {exc}', 'audioSha256': audio_hash,
                   'settingsSha256': settings_hash(), 'codeSha256': code_hash(),
                   'failedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        out_receipt.write_text(json.dumps(receipt, indent=1) + '\n')
        print(f'{directory.name} ASR failed: {exc}', flush=True)
        return receipt
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def main():
    video_id = sys.argv[1] if len(sys.argv) > 1 else None
    directories = [ROOT / video_id] if video_id else [p for p in sorted(ROOT.iterdir()) if p.is_dir()]
    new_results = [transcribe_one(p) for p in directories]
    out = Path('${CHANNELS_ET_REPO_ROOT}/research/acquisition-2026-11/asr-summary.json')
    prior = json.loads(out.read_text()) if out.exists() else {'records': []}
    records = {r['videoId']: r for r in prior.get('records', [])}
    for result in new_results:
        records[result['videoId']] = result
    ordered = [records[key] for key in sorted(records)]
    completed = [r for r in ordered if r.get('status') == 'completed']
    summary = {
        'counts': {status: sum(r.get('status') == status for r in ordered)
                   for status in {r.get('status') for r in ordered}},
        'totals': {
            'audioHours': round(sum(r.get('ffprobeDurationSeconds', 0) for r in completed) / 3600, 3),
            'words': sum(r.get('wordCount', 0) for r in completed),
            'segments': sum(r.get('segmentCount', 0) for r in completed),
        },
        'records': ordered,
    }
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print('counts:', summary['counts'], 'totals:', summary['totals'])


if __name__ == '__main__':
    main()
