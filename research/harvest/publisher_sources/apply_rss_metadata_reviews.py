#!/usr/bin/env python3
"""Apply three specific independently reviewed current-response amendments.

No new network request, changed tolerance, guessed edition join or generic
acceptance rule. Original strict failure events stay in the acquisition journal.
"""
import datetime
import fcntl
import hashlib
import json
import pathlib
import subprocess

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
RAW = pathlib.Path('/workspace/channels-et-raw/publisher-audio')
CASES = {
    'rss-1546456269-353036e21117': (59230133, 'f3b7cc1ba691e1ee5532847daadfe038825c37712e23a57d2d2ea606473ca897', 3696.979438),
    'rss-1546456269-b82d79f0d2c0': (40274039, 'b8de61ae962b10ac1e904ba3ec8c1262a01361de3a28c1ef21828c42e528fb5f', 2511.9085),
    'rss-425328515-addbc47ecbd7': (106006995, 'f0a4b75d81fc2cead2a9d90e0c81167b57dbca0f6a3e6cd465051f1accc5b2bd', 6595.291378),
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


with (RAW.parent / '.collection-worker.lock').open('a+') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    summary_path = H / 'publisher-summary.json'
    summary = json.loads(summary_path.read_text())
    assert summary['terminal'] is True and not summary['in_flight'] and summary['planned_jobs'] == 19
    audit_path = H.parent / 'audits/rss-metadata-disagreement-review.json'
    assert audit_path.is_file(), 'Independent specific-source review must exist'
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    previous_summary_sha = sha(summary_path)
    applied = []
    amended_records = {}
    for ident, (expected_bytes, expected_sha, expected_seconds) in CASES.items():
        record = next(row for row in summary['records'] if row['source_id'] == ident)
        if record.get('validation_outcome') == 'saved_complete_publisher_response_with_rss_metadata_warning':
            assert record['status'] == 'completed' and sha(pathlib.Path(record['raw_local_path'])) == expected_sha
            continue
        assert record['status'] == 'validation_mismatch' and record['error'] == 'rss_enclosure_size_differs_from_actual'
        assert record['http_status'] == 200 and record['resumed_from_bytes'] == 0
        assert record['bytes'] == record['response_declared_remaining_bytes'] == expected_bytes
        assert record['sha256'] == expected_sha and record['rss_enclosure_length_bytes'] > 0
        final = pathlib.Path(record['raw_local_path'])
        assert final.parent.resolve() == RAW.resolve() and not final.is_symlink()
        partial = final.with_suffix(final.suffix + '.part')
        current = partial if partial.exists() else final
        assert current.is_file() and not current.is_symlink() and current.stat().st_size == expected_bytes
        assert sha(current) == expected_sha
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size,format_name:stream=codec_type,codec_name,sample_rate,channels', '-of', 'json', str(current)], text=True))
        duration = float(probe['format']['duration'])
        assert abs(duration - expected_seconds) < 1e-6 and any(s.get('codec_type') == 'audio' for s in probe['streams'])
        strict_sha = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        amendment_name = ident + '-metadata-amendment.json'
        amendment_path = 'research/harvest/publisher_sources/' + amendment_name
        amended = {**record, 'status': 'completed', 'error': None,
                   'validation_outcome': 'saved_complete_publisher_response_with_rss_metadata_warning',
                   'strict_validation_status': 'validation_mismatch', 'strict_validation_error': record['error'],
                   'rss_size_matches_actual': False,
                   'rss_size_delta_bytes': expected_bytes - record['rss_enclosure_length_bytes'],
                   'duration_seconds': duration, 'duration_delta_from_rss_seconds': duration - record['rss_duration_seconds'],
                   'content_or_youtube_edition_equivalence_verified': False,
                   'warning': 'Complete current publisher HTTP response; RSS byte size and possibly duration differ. Source-specific reviewed acceptance, not original/video-edition equivalence or a relaxed integrity threshold.',
                   'review_amendment': {'path': amendment_path, 'applied_at': timestamp,
                                        'review_roles': ['Independent manuscript/source reviewer', 'Coordinator'], 'human_review': False,
                                        'original_strict_record_sha256': strict_sha, 'original_summary_sha256': previous_summary_sha,
                                        'independent_audit_path': str(audit_path.relative_to(R)), 'independent_audit_sha256': sha(audit_path),
                                        'additional_network_requests': 0, 'amendment_script_sha256': sha(pathlib.Path(__file__).resolve())},
                   'ffprobe_revalidated_at_amendment': probe, 'finished_at': timestamp}
        if ident == 'rss-425328515-addbc47ecbd7':
            assert amended['source_format'] == 'skeptical_commentary'
        if current == partial:
            assert not final.exists()
            partial.replace(final)
            partial.with_suffix(partial.suffix + '.meta.json').unlink(missing_ok=True)
        amended_records[ident] = amended
        decision = {'source_id': ident, 'status': 'applied', 'reviewed_at': timestamp,
                    'decision': amended['validation_outcome'], 'review_roles': amended['review_amendment']['review_roles'],
                    'human_review': False, 'independent_audit_path': str(audit_path.relative_to(R)),
                    'independent_audit_sha256': sha(audit_path), 'original_strict_record_sha256': strict_sha,
                    'final_audio_sha256': expected_sha, 'final_audio_bytes': expected_bytes,
                    'rss_enclosure_length_bytes': record['rss_enclosure_length_bytes'],
                    'rss_size_delta_bytes': amended['rss_size_delta_bytes'], 'final_audio_duration_seconds': duration,
                    'rss_duration_seconds': record['rss_duration_seconds'], 'duration_delta_seconds': amended['duration_delta_from_rss_seconds'],
                    'youtube_edition_equivalence_verified': False, 'strict_attempt_preserved': True, 'additional_network_requests': 0}
        save(H / amendment_name, decision)
        applied.append(decision)
    index = json.loads((R / 'research/deep/repo_raw/data/podcasts.json').read_text())
    summary['records'] = [amended_records.get(row['source_id'], row) for row in summary['records']]
    for row in summary['records']:
        if 'source_format' not in row:
            pointer = int(row['original_index_edge']['source_pointer'].strip('/'))
            assert index[pointer]['type'] == 'interview'
            row['source_format'] = 'interview'
            row['source_format_basis'] = 'Inherited original-index type; actual audio speaker turns remain unverified.'
    completed = [r for r in summary['records'] if r['status'] == 'completed']
    summary.update(updated_at=timestamp, completed_audio_files=len(completed),
                   completed_audio_bytes=sum(r['bytes'] for r in completed), completed_audio_seconds=sum(r['duration_seconds'] for r in completed),
                   warning_audio_files=sum(bool(r.get('validation_outcome')) for r in completed),
                   run_status='completed' if len(completed) == summary['planned_jobs'] else 'completed_with_failures')
    with (H / 'publisher-attempts.jsonl').open('a') as journal:
        for record in amended_records.values():
            journal.write(json.dumps(record) + '\n')
    save(summary_path, summary)
    print(json.dumps({'applied': applied, 'completed_audio_files': len(completed), 'planned_jobs': summary['planned_jobs']}, indent=2))
