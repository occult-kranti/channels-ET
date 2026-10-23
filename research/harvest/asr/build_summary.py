#!/usr/bin/env python3
"""Export verified ASR bookkeeping only; raw text stays in private cloud files."""
import datetime
import hashlib
import json
import math
import tempfile
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RAW = Path('/workspace/channels-et-raw')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def main():
    records = []
    rejected = []
    publishers = json.loads((HERE.parent / 'publisher_sources/publisher-summary.json').read_text())['records']
    for path in sorted(HERE.glob('*-receipt.json')):
        if not re.fullmatch(r'[a-f0-9]{20}(?:-clip[0-9.]+)?-receipt.json', path.name):
            continue
        try:
            row = json.loads(path.read_text())
            folder = Path(row['transcriptDirectory']).resolve()
            reason = None
            audio = Path(row['sourceAudioPath']).resolve()
            if not folder.is_relative_to(RAW.resolve()) or not audio.is_relative_to(RAW.resolve()) or row['status'] != 'completed':
                reason = 'Invalid external output or receipt state'
            elif not any(r.get('status') == 'completed' and r.get('source_id') == row['sourceId']
                         and r.get('enclosure_url') == row['sourceUrl'] and r.get('sha256') == row['sourceAudioSha256']
                         and Path(r.get('raw_local_path', '/missing')).resolve() == audio
                         for r in publishers):
                reason = 'No matching completed primary-publisher acquisition record'
            elif not Path(row['sourceAudioPath']).is_file() or sha(Path(row['sourceAudioPath'])) != row['sourceAudioSha256']:
                reason = 'Original local audio absent or changed'
            elif len(row.get('outputs', [])) != 3 or {f['name'] for f in row.get('outputs', [])} != {'segments.jsonl', 'transcript.txt', 'transcript.srt'}:
                reason = 'Exact three-file transcript output set is missing'
            elif not all((folder / f['name']).resolve().is_relative_to(RAW.resolve()) and (folder / f['name']).is_file() and (folder / f['name']).stat().st_size == f['bytes']
                         and sha(folder / f['name']) == f['sha256'] for f in row['outputs']):
                reason = 'Transcript artifact absent or changed'
            elif row['transcribedScope'] not in {'full_decoded_audio', 'explicit_clip'}:
                reason = 'Unknown transcription scope'
            elif not math.isfinite(row['sourceAudioDurationSeconds']) or row['sourceAudioDurationSeconds'] <= 0:
                reason = 'Invalid source duration'
            elif any(type(row[key]) is not int or row[key] < 0 for key in ('segments', 'words')):
                reason = 'Invalid segment or word counts'
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            reason = f'Unreadable or malformed receipt/artifact: {type(exc).__name__}'
        if reason:
            rejected.append({'receipt': path.name, 'reason': reason})
        else:
            records.append(row)
    full = [r for r in records if r['transcribedScope'] == 'full_decoded_audio']
    result = {'schemaVersion': 1, 'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'sourceKind': 'publisher_original_audio_asr', 'completedFullTranscripts': len(full),
              'diagnosticClips': len(records) - len(full),
              'totalAudioDurationSeconds': sum(r['sourceAudioDurationSeconds'] for r in full),
              'totalSegments': sum(r['segments'] for r in full), 'totalWords': sum(r['words'] for r in full),
              'totalTranscriptBytes': sum(f['bytes'] for r in full for f in r['outputs']),
              'records': records, 'rejectedReceipts': rejected, 'humanReviewed': False,
              'rawTranscriptTextPublished': False, 'youtubeVideoEditionVerified': False,
              'scope': 'Actual source-hashed primary-audio ASR files. Automatic recognition is unverified; counts do not establish speech accuracy, speakers, or YouTube-video coverage.'}
    with tempfile.NamedTemporaryFile(mode='w', dir=HERE, prefix='summary-', suffix='.tmp', delete=False) as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
        temporary = Path(stream.name)
    temporary.replace(HERE / 'summary.json')
    print(json.dumps({k: result[k] for k in ['completedFullTranscripts', 'diagnosticClips', 'totalAudioDurationSeconds', 'totalWords']}))


if __name__ == '__main__':
    main()
