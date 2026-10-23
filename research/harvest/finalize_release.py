#!/usr/bin/env python3
"""Bind a terminal acquisition supplement to exact public/source bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXCLUDED = {
    'research/harvest/FINAL-RELEASE.json',
    'research/harvest/reviews/final-release-review.json',
}


def read(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    publisher = read('research/harvest/publisher_sources/publisher-summary.json')
    asr = read('research/harvest/asr/summary.json')
    queue = read('research/harvest/asr/queue-state.json')
    worker = read('research/harvest/summary.json')
    inventory = read('research/harvest/inventory/summary.json')
    assert publisher['terminal'] and not publisher['in_flight'], 'Publisher run is still active'
    assert publisher['completed_audio_files'] == publisher['planned_jobs'] == len(publisher['records'])
    assert all(r['status'] == 'completed' for r in publisher['records'])
    assert queue['status'] == 'completed' and not queue['in_flight'], 'ASR queue is not terminal/completed'
    assert queue['verified_completed_total'] == asr['completedFullTranscripts'] == publisher['planned_jobs']
    assert not asr['rejectedReceipts'] and asr['diagnosticClips'] == 0
    assert worker['attempts_total'] == 0 and not any(worker['artifacts_by_type'].values())
    assert worker['access_gate']['status'] == 'blocked'
    counts = inventory['counts']
    expected = counts['unique_video_ids'] * 3 + counts['channel_routes'] + counts['playlists']
    assert sum(sum(v.values()) for v in worker['counts_by_kind'].values()) == expected
    pub = {r['source_id']: r for r in publisher['records']}
    assert len({r['sourceId'] for r in asr['records']}) == len(pub)
    for record in asr['records']:
        source = pub[record['sourceId']]
        assert record['sourceAudioSha256'] == source['sha256'] and record['sourceUrl'] == source['enclosure_url']
    copies = {
        'harvest-summary.json': 'research/harvest/summary.json',
        'harvest-publisher-audio.json': 'research/harvest/publisher_sources/publisher-summary.json',
        'harvest-asr-summary.json': 'research/harvest/asr/summary.json',
        'harvest-inventory-summary.json': 'research/harvest/inventory/summary.json',
        'harvest.js': 'research/harvest/dashboard/harvest.js',
    }
    for target, source in copies.items():
        assert (ROOT / 'dist/research' / target).read_bytes() == (ROOT / source).read_bytes(), target

    paths = ['README.md', '.gitignore', 'research/continuation/HANDOFF.md',
             'research/continuation/dashboard', 'research/harvest',
             'scripts/pages', '.github/workflows/pages.yml', 'dist/research']
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', *paths], cwd=ROOT)
    files = []
    for relative in sorted(set(raw.decode().split('\0')) - {''} - EXCLUDED):
        path = ROOT / relative
        if not path.is_file():
            continue
        assert not path.is_symlink(), f'Unexpected symlink: {relative}'
        assert path.suffix.lower() not in {'.mp3', '.mp4', '.webm', '.wav', '.srt', '.vtt'}, relative
        assert path.stat().st_size < 50 * 1024 * 1024, relative
        files.append({'path': relative, 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {
        'schemaVersion': 1, 'frozenAt': datetime.now(timezone.utc).isoformat(),
        'status': 'source_and_static_release_prepared',
        'checkoutParentCommitAtFreeze': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'binding': 'Per-file hashes bind current source and artifacts; later Action/live receipts identify deployed commit.',
        'liveUrl': 'https://occult-kranti.github.io/channels-ET/',
        'youtubeIds': counts['unique_video_ids'], 'channelRoutes': counts['channel_routes'],
        'playlists': counts['playlists'], 'preparedJobs': expected,
        'youtubeWorkerAttempts': worker['attempts_total'], 'youtubeVideoDownloads': 0,
        'publisherAudioFiles': publisher['completed_audio_files'],
        'publisherAudioBytes': publisher['completed_audio_bytes'],
        'publisherAudioSeconds': publisher['completed_audio_seconds'],
        'fullDecodedAudioAsrPasses': asr['completedFullTranscripts'],
        'asrSegments': asr['totalSegments'], 'asrWords': asr['totalWords'],
        'humanTranscriptAccuracyValidated': False, 'youtubeEditionEquivalenceVerified': False,
        'rawAudioAndTranscriptTextInPublicRelease': False,
        'excludedToAvoidCircularBinding': sorted(EXCLUDED),
        'deploymentReceipts': 'research/deployment/; these are recorded after deployment and outside this file list',
        'files': files, 'fileCount': len(files), 'totalBytes': sum(f['bytes'] for f in files),
    }
    (HERE / 'FINAL-RELEASE.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'preparedJobs', 'publisherAudioFiles', 'fullDecodedAudioAsrPasses', 'fileCount', 'totalBytes')}))


if __name__ == '__main__':
    main()
