#!/usr/bin/env python3
"""Verify public publisher-media metadata, not inaccessible private audio bytes.

The producer and private independent review validate raw media. This stdlib-only
CI check recomputes public accounting and provenance-stage constraints.
"""
import argparse
import json
import math
from pathlib import Path
import re

HEX = re.compile(r'^[0-9a-f]{64}$')
VIDEO = re.compile(r'^[A-Za-z0-9_-]{11}$')


def require(condition, message):
    if not condition: raise ValueError(message)


def near(a, b):
    return isinstance(a, (int, float)) and math.isfinite(a) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-7)


def audio_fields(a):
    require(a['status'] == 'full_audio_decode_verified', 'Audio was not admitted after full decode')
    require(a['ffprobe_exit'] == a['ffmpeg_exit'] == a['ffmpeg_error_bytes'] == 0,
            'Audio validation status is not clean')
    require(isinstance(a['bytes'], int) and a['bytes'] > 0, 'Invalid retained audio byte count')
    require(HEX.fullmatch(a['sha256']) is not None, 'Invalid audio SHA-256')
    require(HEX.fullmatch(a['decoded_pcm_sha256']) is not None, 'Invalid PCM SHA-256')
    require(isinstance(a['decoded_pcm_samples'], int) and a['decoded_pcm_samples'] > 0, 'Invalid decoded samples')
    require(a['decoded_pcm_format'] == 's16le_mono_16000Hz', 'Unexpected decode format')
    require(near(a['decoded_duration_seconds'], a['decoded_pcm_samples']/16000), 'Decoded duration/sample mismatch')
    require(near(a['container_duration_seconds'], a['container_duration_seconds'])
            and abs(a['container_duration_seconds']-a['decoded_duration_seconds']) <= 1,
            'Container/decoded duration mismatch')


def verify(root):
    path = Path(root)
    if path.is_dir():
        path = path/'publisher-media.json' if (path/'publisher-media.json').exists() else path/'dist/youtube-archive/publisher-media.json'
    data = json.loads(path.read_bytes()); records = data['records']; summary = data['summary']
    ids = [r['record_id'] for r in records]
    require(len(ids) == len(set(ids)), 'Duplicate successful record ID')
    require(len({r['audio']['url'] for r in records}) == len(records), 'Duplicate successful source audio URL')
    successes = set(ids)
    for r in records:
        require(HEX.fullmatch(r['page_sha256']) is not None, 'Invalid page SHA-256')
        require(r['association']['youtube_content_equivalence_verified'] is False,
                'Unsupported YouTube-equivalence assertion')
        require(r['association']['audio_written_word_alignment_verified'] is False,
                'Unsupported audio/text alignment assertion')
        require(all(VIDEO.fullmatch(i) for i in r['linked_youtube_ids']), 'Malformed linked YouTube ID')
        a = r['audio']; audio_fields(a)
        if a['retention'] == 'verified_lossy_opus_48kbps_target_vbr':
            require(a['codec'] == 'opus', 'Derivative codec mismatch')
            audio_fields(a['source_original'])
            require(a['source_original_retained'] is False
                    and a['source_original_deleted_after_verified_output'] is True,
                    'Derivative/original retention mismatch')
            require(abs(a['decoded_duration_seconds']-a['source_original']['decoded_duration_seconds']) <= .1,
                    'Derivative/source duration mismatch')
        else:
            require(a['retention'] == 'original_publisher_bytes' and a['codec'] == 'mp3',
                    'Unexpected original retention representation')
        w = r['written']
        require(w['asr_generated'] is False and w['word_aligned_to_audio'] is False,
                'Publisher-written text mislabeled as recognition/alignment')
        require(w['human_validated'] is False, 'Unsupported human validation assertion')
        require(isinstance(w['manual_read_by_ai'], bool), 'Invalid reading scope')
        if w['status'] == 'retained_publisher_written_edition':
            require(w['origin'] == 'publisher_written' and w['public_stage_name'] == 'written_message',
                    'Written edition origin/stage mismatch')
            require(isinstance(w['words'], int) and w['words'] > 0 and w['bytes'] > 0
                    and HEX.fullmatch(w['sha256']) is not None, 'Invalid retained written-edition binding')
        else:
            require(w['status'] == 'not_retained_template_pending' and w['words'] == w['bytes'] == 0
                    and w['sha256'] is None and w['manual_read_by_ai'] is False
                    and w['public_stage_name'] == 'written_message_pending',
                    'Pending written edition has invented retained content')
    successful_attempts = []; history = []; candidate_ids = set()
    run_ids = [run['run_id'] for run in data['source_runs']]
    require(len(run_ids) == len(set(run_ids)), 'Duplicate source run')
    for run in data['source_runs']:
        require(HEX.fullmatch(run['manifest_sha256']) is not None, 'Invalid source manifest binding')
        rs = run['successful_record_ids']; fs = run['failed_or_deferred_attempts']
        require(len(rs) == len(set(rs)), 'Duplicate success in source run')
        require(run['candidate_attempts'] == len(rs)+len(fs), 'Source-run attempt denominator differs')
        require(not set(rs) & {f['record_id'] for f in fs}, 'Source-run item is both successful and failed')
        require(all(f['status'] in {'failed_not_counted', 'deferred_resource_budget'} for f in fs),
                'Unknown source-run failure state')
        successful_attempts.extend(rs); history.extend(fs)
        candidate_ids.update(rs); candidate_ids.update(f['record_id'] for f in fs)
    require(set(successful_attempts) == successes and len(successful_attempts) == len(successes),
            'Successful records do not join source runs exactly once')
    unresolved = {f['record_id']: f for f in history if f['record_id'] not in successes}
    require(data['failures'] == list(unresolved.values()), 'Current failures differ from unresolved historical outcomes')
    pending_ids = [q['record_id'] for q in data['pending_queue']]
    require(len(pending_ids) == len(set(pending_ids)) and set(pending_ids) == set(unresolved),
            'Current pending queue differs from unresolved candidates')
    expected = {
        'retained_publisher_audio_files': len(records),
        'unique_retained_audio_sha256': len({r['audio']['sha256'] for r in records}),
        'unique_source_original_sha256': len({r['audio'].get('source_original', r['audio'])['sha256'] for r in records}),
        'retained_original_mp3_files': sum(r['audio']['retention'] == 'original_publisher_bytes' for r in records),
        'retained_opus_derivative_files': sum(r['audio']['retention'] == 'verified_lossy_opus_48kbps_target_vbr' for r in records),
        'retained_publisher_written_editions': sum(r['written']['status'] == 'retained_publisher_written_edition' for r in records),
        'pending_written_editions': sum(r['written']['status'] == 'not_retained_template_pending' for r in records),
        'retained_audio_bytes': sum(r['audio']['bytes'] for r in records),
        'source_original_bytes_verified': sum(r['audio'].get('source_original', r['audio'])['bytes'] for r in records),
        'retained_audio_seconds': sum(r['audio']['decoded_duration_seconds'] for r in records),
        'publisher_written_words': sum(r['written']['words'] for r in records),
        'message_bodies_read_by_ai': sum(r['written']['manual_read_by_ai'] for r in records),
        'automatically_extracted_unread_bodies': sum(not r['written']['manual_read_by_ai'] and r['written']['status'] == 'retained_publisher_written_edition' for r in records),
        'failed_candidates': sum(f['status'] == 'failed_not_counted' for f in unresolved.values()),
        'resource_deferred_candidates': sum(f['status'] == 'deferred_resource_budget' for f in unresolved.values()),
        'historical_failed_or_deferred_attempts': len(history),
        'resolved_historical_failed_or_deferred_attempts': sum(f['record_id'] in successes for f in history),
        'candidate_frame': len(candidate_ids),
        'youtube_media_downloads': 0, 'youtube_caption_downloads': 0,
        'new_asr_editions': 0, 'added_to_frozen_493_source_analysis': 0,
    }
    for key, value in expected.items():
        require(near(summary.get(key), value), 'Aggregate counter differs: '+key)
    return {'status': 'passed_public_publisher_media_metadata', 'records': len(records),
            'historical_holds_resolved': expected['resolved_historical_failed_or_deferred_attempts'],
            'currently_unresolved': len(unresolved), 'retained_audio_bytes': expected['retained_audio_bytes'],
            'scope': 'Public metadata arithmetic/provenance-stage audit; no private media bytes or acoustic accuracy checked here.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    print(json.dumps(verify(parser.parse_args().root)))
