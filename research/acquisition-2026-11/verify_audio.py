#!/usr/bin/env python3
"""Verify all acquired public YouTube audio files and write a coverage receipt."""
import concurrent.futures
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "youtube-audio"
PUBLIC = Path(__file__).resolve().parents[0]
REPO = PUBLIC.parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_directory(directory, inherited_map):
    results = []
    def result(name, ok, detail=''):
        results.append({'check': name, 'ok': bool(ok), 'detail': detail})
    receipt_path = directory / 'acquisition.json'
    audio = directory / 'audio.mp3'
    if not receipt_path.exists():
        result(f'receipt exists:{directory.name}', False, 'missing acquisition.json')
        return results, None
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('status') == 'excluded_under_300':
        result(f'valid under-300 exclusion:{directory.name}',
               receipt.get('durationSeconds', 300) < 300, str(receipt.get('durationSeconds')))
        return results, None
    if receipt.get('status') == 'excluded_language_mismatch':
        quarantine = directory / 'quarantine'
        result(f'valid language quarantine:{directory.name}',
               quarantine.is_dir() and (quarantine / 'asr-transcript.txt').exists(),
               'quarantine/')
    if receipt.get('status') != 'completed':
        result(f'failed record not counted as media:{directory.name}', receipt.get('status') == 'failed', '')
        return results, None
    if not audio.exists():
        result(f'completed media exists:{directory.name}', False, 'audio.mp3 missing')
        return results, None
    data = audio.read_bytes()
    actual_hash = sha256(audio)
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,sample_rate,channels', '-of', 'json', str(audio)
    ], text=True))
    duration = float(probe['format']['duration'])
    expected = inherited_map.get(directory.name)
    valid = actual_hash == receipt.get('sha256') and len(data) == receipt.get('bytes') and duration > 0
    if expected:
        valid = valid and abs(duration - expected) <= max(5, expected * 0.02)
    result(f'valid audio and hash:{directory.name}', valid,
           f'bytes={len(data)} duration={duration:.3f} expected={expected}')
    record = {'videoId': directory.name, 'bytes': len(data), 'sha256': actual_hash,
              'durationSeconds': duration, 'probe': probe}
    return results, record


def main():
    checks = []
    def check(name, ok, detail=''):
        checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
        print(('PASS' if ok else 'FAIL'), name, '-', detail)
    records = []
    inherited = json.loads((REPO / 'research/expansion-2026/youtube-transcripts/retry-videos.json').read_text())
    inherited_map = {r['video_id']: r.get('duration_seconds') for r in inherited}
    directories = [p for p in sorted(ROOT.iterdir()) if p.is_dir()] if ROOT.exists() else []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        outcomes = list(executor.map(lambda d: validate_directory(d, inherited_map), directories))
    for directory_checks, record in outcomes:
        checks.extend(directory_checks)
        for row in directory_checks:
            print(('PASS' if row['ok'] else 'FAIL'), row['check'], '-', row['detail'])
        if record:
            records.append(record)
    ledger = PUBLIC / 'acquisition-ledger.json'
    check('acquisition ledger exists', ledger.exists(), 'acquisition-ledger.json')
    if ledger.exists():
        rows = json.loads(ledger.read_text())['records']
        completed = [r for r in rows if r.get('status') == 'completed']
        excluded_language = [r for r in rows if r.get('status') == 'excluded_language_mismatch']
        check('completed plus excluded-language media equals validated audio',
              len(completed) + len(excluded_language) == len(records),
              f'completed={len(completed)} excludedLanguage={len(excluded_language)} media={len(records)}')
        excluded_under_300 = [r for r in rows if r.get('status') == 'excluded_under_300']
        check('under-300 exclusions are explicit and not counted as completed',
              len(excluded_under_300) == 7 and all(r.get('durationSeconds', 300) < 300 for r in excluded_under_300),
              f'excluded={len(excluded_under_300)}')
        excluded_language = [r for r in rows if r.get('status') == 'excluded_language_mismatch']
        check('one German/unsupported-language quarantine is explicit',
              len(excluded_language) == 1 and excluded_language[0]['videoId'] == '-KVKPRLFte4',
              f'excluded={len(excluded_language)}')
    report = {'schemaVersion': 1, 'nChecks': len(checks),
              'nPassed': sum(c['ok'] for c in checks), 'nFailed': sum(not c['ok'] for c in checks),
              'checks': checks, 'validatedMedia': records,
              'totals': {'files': len(records), 'bytes': sum(r['bytes'] for r in records),
                         'durationSeconds': sum(r['durationSeconds'] for r in records)}}
    (PUBLIC / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"{report['nPassed']}/{report['nChecks']} checks passed")
    return 1 if report['nFailed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
