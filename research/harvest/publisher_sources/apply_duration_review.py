#!/usr/bin/env python3
"""Apply the specifically approved Align #561 current-response amendment.

No network request and no changed tolerance. The original strict attempt remains
in the append-only journal; a new, explicitly reviewed outcome binds the bytes.
"""
import datetime
import fcntl
import hashlib
import json
import pathlib
import subprocess

H = pathlib.Path(__file__).resolve().parent
RAW = pathlib.Path('/workspace/channels-et-raw/publisher-audio')
IDENT = 'rss-988576741-1ecc5cb023cf'
EXPECTED_SHA = '2faf0b5e0de8be739cbdf0e83bc5a04f26aa10e85d6853cb1568c3068fc75d3a'
EXPECTED_BYTES = 81631438
EXPECTED_SECONDS = 5099.179878


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def main():
    with (RAW.parent / '.collection-worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        decision_path = H / 'duration-review-amendment.json'
        decision = json.loads(decision_path.read_text())
        summary_path = H / 'publisher-summary.json'
        summary = json.loads(summary_path.read_text())
        assert summary['terminal'] is True and not summary['in_flight'], 'Wait for download run to terminate'
        assert summary['planned_jobs'] == 19 and decision['source_id'] == IDENT
        current = next(r for r in summary['records'] if r['source_id'] == IDENT)
        if decision['status'] == 'applied':
            assert current['status'] == 'completed' and sha(pathlib.Path(current['raw_local_path'])) == EXPECTED_SHA
            print(json.dumps({'status': 'already_applied', 'source_id': IDENT}))
            return
        assert decision['status'] == 'approved_pending_exclusive_promotion'
        assert current['status'] == 'validation_mismatch' and current['error'] == 'rss_duration_outside_tolerance'
        assert current['http_status'] == 200 and current['resumed_from_bytes'] == 0
        assert current['rss_enclosure_length_bytes'] == 0 and current['rss_duration_seconds'] == 4999
        assert current['response_declared_remaining_bytes'] == EXPECTED_BYTES == current['bytes']
        assert current['sha256'] == EXPECTED_SHA == decision['expected_sha256']
        path = pathlib.Path(current['raw_local_path'])
        assert path.parent.resolve() == RAW.resolve() and path.suffix == '.mp3' and not path.exists()
        partial = path.with_suffix(path.suffix + '.part')
        assert not partial.is_symlink() and partial.is_file() and partial.stat().st_size == EXPECTED_BYTES
        assert sha(partial) == EXPECTED_SHA
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size,format_name:stream=codec_type,codec_name,sample_rate,channels', '-of', 'json', str(partial)], text=True))
        duration = float(probe['format']['duration'])
        assert abs(duration - EXPECTED_SECONDS) < 1e-6 and any(s.get('codec_type') == 'audio' for s in probe['streams'])
        original_summary_sha = sha(summary_path)
        strict_record_sha = hashlib.sha256(json.dumps(current, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        amended = {**current, 'status': 'completed', 'validation_outcome': 'saved_complete_publisher_response_with_duration_warning',
                   'strict_validation_status': 'validation_mismatch', 'strict_validation_error': current['error'],
                   'error': None, 'rss_duration_within_tolerance': False, 'rss_duration_seconds': 4999,
                   'duration_seconds': duration, 'duration_delta_from_rss_seconds': duration - 4999,
                   'content_or_youtube_edition_equivalence_verified': False,
                   'warning': 'Complete current publisher HTTP response; RSS duration differs by100.179878seconds. Ads/edition changes are possible untested explanations. Not proof of original recording or video equivalence.',
                   'review_amendment': {'path': 'research/harvest/publisher_sources/duration-review-amendment.json',
                                        'applied_at': timestamp, 'review_roles': decision['review_roles'], 'human_review': False,
                                        'original_strict_record_sha256': strict_record_sha,
                                        'original_summary_sha256': original_summary_sha, 'additional_network_requests': 0,
                                        'amendment_script_sha256': sha(pathlib.Path(__file__).resolve())},
                   'ffprobe_revalidated_at_amendment': probe, 'finished_at': timestamp}
        partial.replace(path)
        partial.with_suffix(partial.suffix + '.meta.json').unlink(missing_ok=True)
        summary['records'] = [amended if r['source_id'] == IDENT else r for r in summary['records']]
        completed = [r for r in summary['records'] if r['status'] == 'completed']
        summary.update(updated_at=timestamp, completed_audio_files=len(completed),
                       completed_audio_bytes=sum(r['bytes'] for r in completed),
                       completed_audio_seconds=sum(r['duration_seconds'] for r in completed),
                       duration_warning_audio_files=sum(r.get('validation_outcome') == amended['validation_outcome'] for r in completed),
                       run_status='completed' if len(completed) == summary['planned_jobs'] else 'completed_with_failures')
        with (H / 'publisher-attempts.jsonl').open('a') as f:
            f.write(json.dumps(amended) + '\n')
        save(summary_path, summary)
        decision.update(status='applied', applied_at=timestamp, original_strict_record_sha256=strict_record_sha,
                        final_audio_sha256=EXPECTED_SHA, final_audio_bytes=EXPECTED_BYTES,
                        final_audio_duration_seconds=duration, updated_summary_sha256=sha(summary_path))
        save(decision_path, decision)
        print(json.dumps({'status': 'applied', 'source_id': IDENT, 'raw_local_path': str(path),
                          'sha256': EXPECTED_SHA, 'bytes': EXPECTED_BYTES, 'duration_seconds': duration,
                          'validation_outcome': amended['validation_outcome']}, indent=2))


if __name__ == '__main__':
    main()
