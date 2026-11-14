#!/usr/bin/env python3
"""Resumable public YouTube audio acquisition through the ordinary y2mate.gs UI.

No cookies, CAPTCHA solving, private/paid access, proxy rotation, or credential
sharing. A record completes only when a nonzero MP3 is downloaded and ffprobe
validates its duration. Source/publication rights are tracked separately.
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(os.environ['CHANNELS_ET_RAW_ROOT']) / 'youtube-audio'
PUBLIC = Path(__file__).resolve().parents[0]
SOURCE_CANDIDATES = PUBLIC.parents[1] / 'research/expansion-2026/youtube-transcripts/retry-videos.json'


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def candidates(path):
    if not path.exists():
        return []
    return {row['video_id']: row for row in json.loads(path.read_text())}


def load_rows(args):
    if args.video_id:
        if args.video_id not in candidates(args.candidates):
            raise ValueError(f'{args.video_id} is absent from the candidate list')
        return [candidates(args.candidates)[args.video_id]]
    rows = [r for r in candidates(args.candidates).values()
            if r.get('selection') != 'held_route_limit_over_150_minutes']
    if args.only_completed:
        ledger_path = PUBLIC / 'acquisition-ledger.json'
        done = set()
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text())
            done = {r.get('video_id', r.get('videoId')) for r in ledger['records']
                    if r.get('status') in ('completed', 'excluded_under_300', 'excluded_language_mismatch')}
        rows = [r for r in rows if r['video_id'] not in done]
    return rows[:args.max_items]


class Under300Error(ValueError):
    def __init__(self, duration):
        super().__init__(f'duration below 300 seconds: {duration}')
        self.duration = duration


def validate_audio(path, inherited):
    if not path.exists() or path.stat().st_size < 10000:
        raise ValueError('zero or truncated audio file')
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,sample_rate,channels', '-of', 'json', str(path)
    ], text=True))
    duration = float(probe['format']['duration'])
    if duration < 300:
        raise Under300Error(duration)
    if inherited and abs(duration - inherited) > max(5, inherited * 0.02):
        raise ValueError(f'duration mismatch: {duration} vs inherited {inherited}')
    return duration, probe


def quarantine_under_300(directory, duration):
    quarantine = directory / 'quarantine'
    quarantine.mkdir(exist_ok=True)
    for name in ('audio.mp3.part', 'audio.mp3'):
        source = directory / name
        if source.exists():
            source.replace(quarantine / name)
    quarantined_audio = quarantine / 'audio.mp3'
    receipt = {
        'videoId': directory.name, 'status': 'excluded_under_300',
        'durationSeconds': duration, 'mediaBytes': 0, 'admittedMediaBytes': 0,
        'quarantinedBytes': quarantined_audio.stat().st_size if quarantined_audio.exists() else 0,
        'quarantinedAudioSha256': sha256(quarantined_audio) if quarantined_audio.exists() else None,
        'mediaBytesMeaning': 'admitted_media_bytes_excluding_quarantine',
        'exclusionReason': 'Measured duration is below the 300-second policy minimum.',
        'quarantinedAt': utcnow(), 'humanValidated': False,
    }
    (directory / 'acquisition.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    ledger_path = PUBLIC / 'acquisition-ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'schemaVersion': 1, 'records': []}
    ledger['records'] = [r for r in ledger['records'] if r['video_id'] != directory.name]
    ledger['records'].append(receipt)
    ledger['updatedAt'] = utcnow()
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    print(f'{directory.name} excluded under 300s: {duration}', flush=True)
    return receipt


def fetch_one(browser, video):
    vid = video['video_id']
    target = ROOT / vid
    target.mkdir(parents=True, exist_ok=True)
    audio = target / 'audio.mp3'
    if audio.exists():
        duration, probe = validate_audio(audio, video.get('duration_seconds'))
        return {'status': 'completed', 'video_id': vid, 'resumed': True,
                'bytes': audio.stat().st_size, 'sha256': sha256(audio),
                'duration_seconds': duration, 'ffprobe': probe,
                'suggestedFilename': 'audio.mp3', 'completedAt': utcnow()}
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
    started = utcnow()
    try:
        page.goto('https://y2mate.gs/', wait_until='domcontentloaded', timeout=60000)
        page.locator('#link').fill(video['source_url'])
        page.get_by_role('button', name='Convert', exact=False).first.click()
        page.get_by_text('completed', exact=False).wait_for(timeout=180000)
        with page.expect_download(timeout=30000) as download_info:
            page.get_by_role('button', name='Download', exact=False).first.click()
        download = download_info.value
        partial = target / 'audio.mp3.part'
        download.save_as(str(partial))
        duration, probe = validate_audio(partial, video.get('duration_seconds'))
        partial.replace(audio)
        return {'status': 'completed', 'video_id': vid, 'resumed': False,
                'bytes': audio.stat().st_size, 'sha256': sha256(audio),
                'duration_seconds': duration, 'ffprobe': probe,
                'suggestedFilename': download.suggested_filename,
                'startedAt': started, 'completedAt': utcnow()}
    except Exception as exc:
        if isinstance(exc, Under300Error):
            return quarantine_under_300(target, exc.duration)
        return {'status': 'failed', 'video_id': vid,
                'error': f'{type(exc).__name__}: {exc}'[:1000],
                'startedAt': started, 'completedAt': utcnow()}
    finally:
        page.close()


def write_receipt(video, result):
    target = ROOT / result['video_id']
    target.mkdir(parents=True, exist_ok=True)
    receipt = dict(result)
    receipt.update({
        'sourceUrl': video['source_url'], 'title': video.get('title'),
        'publisher': video.get('publisher'), 'practitionerContext': video.get('practitioner'),
        'claimedGroup': video.get('entity'), 'route': 'y2mate.gs ordinary public paste-link interface',
        'sourceType': 'public_youtube_audio', 'humanValidated': False,
        'rightsReview': 'redistribution_requires_source_specific_review; public Git/Pages is not implied',
    })
    (target / 'acquisition.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video-id')
    parser.add_argument('--candidates', type=Path, default=SOURCE_CANDIDATES)
    parser.add_argument('--only-completed', action='store_true')
    parser.add_argument('--max-items', type=int, default=1)
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    if args.workers != 1:
        raise ValueError('This pilot is intentionally bounded to one conversion at a time')
    ledger_path = PUBLIC / 'acquisition-ledger.json'
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        for directory in sorted(ROOT.iterdir()) if ROOT.exists() else []:
            for receipt_path in (directory / 'acquisition.json', directory / 'asr-receipt.json'):
                if not receipt_path.exists():
                    continue
                receipt = json.loads(receipt_path.read_text())
                if receipt.get('status') not in ('excluded_under_300', 'excluded_language_mismatch'):
                    continue
                ledger['records'] = [r for r in ledger['records']
                                     if r.get('video_id', r.get('videoId')) != receipt['videoId']]
                ledger['records'].append(receipt)
        ledger['updatedAt'] = utcnow()
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    rows = load_rows(args)
    for directory in sorted(ROOT.iterdir()) if ROOT.exists() else []:
        if directory.is_dir() and (directory / 'audio.mp3').exists():
            try:
                validate_audio(directory / 'audio.mp3', None)
            except Under300Error as exc:
                quarantine_under_300(directory, exc.duration)
    if not rows:
        print('No pending candidates')
        ledger_path = PUBLIC / 'acquisition-ledger.json'
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'schemaVersion': 1, 'records': []}
        completed = [r for r in ledger['records']
                     if r.get('status') in ('completed', 'excluded_language_mismatch')]
        summary = {
            'updatedAt': utcnow(),
            'completedRecords': len(completed),
            'completedAudioRecords': len(completed),
            'completedRecordsMeaning': 'audio files completed, including any separately labeled language-excluded audio',
            'failedRecords': sum(r.get('status') == 'failed' for r in ledger['records']),
            'excludedUnder300': sum(r.get('status') == 'excluded_under_300' for r in ledger['records']),
            'excludedLanguageMismatch': sum(r.get('status') == 'excluded_language_mismatch' for r in ledger['records']),
            'mediaBytes': sum(r.get('bytes', 0) for r in completed),
            'durationSeconds': sum(r.get('duration_seconds', r.get('durationSeconds', 0)) for r in completed),
            'route': 'y2mate.gs automated public web-UI conversion',
            'rightsReview': 'Raw audio is private research storage. No public redistribution license is inferred.',
        }
        (PUBLIC / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('SUMMARY', summary, flush=True)
        return
    PUBLIC.mkdir(parents=True, exist_ok=True)
    ledger_path = PUBLIC / 'acquisition-ledger.json'
    prior = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'schemaVersion': 1, 'records': []}
    ledger = prior
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        for video in rows:
            print('FETCH', video['video_id'], video.get('title'), flush=True)
            result = fetch_one(browser, video)
            result['route'] = 'y2mate.gs'
            result['retrievedAt'] = utcnow()
            receipt = write_receipt(video, result)
            ledger['records'] = [r for r in ledger['records'] if r['video_id'] != video['video_id']]
            ledger['records'].append(receipt)
            ledger['updatedAt'] = utcnow()
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
            print('RESULT', result['status'], result.get('bytes', 0), result.get('duration_seconds'), result.get('error', ''), flush=True)
        browser.close()
    completed = [r for r in ledger['records']
                 if r.get('status') in ('completed', 'excluded_language_mismatch')]
    summary = {
        'updatedAt': utcnow(),
        'completedRecords': len(completed),
            'completedAudioRecords': len(completed),
            'completedRecordsMeaning': 'audio files completed, including any separately labeled language-excluded audio',
        'failedRecords': sum(r.get('status') == 'failed' for r in ledger['records']),
        'excludedUnder300': sum(r.get('status') == 'excluded_under_300' for r in ledger['records']),
        'excludedLanguageMismatch': sum(r.get('status') == 'excluded_language_mismatch' for r in ledger['records']),
        'mediaBytes': sum(r.get('bytes', 0) for r in completed),
        'durationSeconds': sum(r.get('duration_seconds', 0) for r in completed),
        'route': 'y2mate.gs automated public web-UI conversion',
        'rightsReview': 'Raw audio is private research storage. No public redistribution license is inferred.',
    }
    (PUBLIC / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SUMMARY', summary, flush=True)


if __name__ == '__main__':
    main()
