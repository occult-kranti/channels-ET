#!/usr/bin/env python3
"""Artificial mutations of a public metadata fixture; no collection occurs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from verify_publisher_media import verify


def run(module):
    raw = Path(module).read_bytes(); original = json.loads(raw)
    valid = verify(module)
    derivative = next(i for i, r in enumerate(original['records'])
                      if r['audio']['retention'] == 'verified_lossy_opus_48kbps_target_vbr')
    pending = next(i for i, r in enumerate(original['records'])
                   if r['written']['status'] == 'not_retained_template_pending')
    mutations = [
        ('wrong_audio_count', lambda d: d['summary'].__setitem__('retained_publisher_audio_files', len(d['records'])+1)),
        ('wrong_audio_bytes', lambda d: d['summary'].__setitem__('retained_audio_bytes', d['summary']['retained_audio_bytes']+1)),
        ('invented_youtube_download', lambda d: d['summary'].__setitem__('youtube_media_downloads', 1)),
        ('invented_asr_edition', lambda d: d['summary'].__setitem__('new_asr_editions', 1)),
        ('duplicate_record_id', lambda d: d['records'][1].__setitem__('record_id', d['records'][0]['record_id'])),
        ('duration_sample_mismatch', lambda d: d['records'][0]['audio'].__setitem__('decoded_duration_seconds', 1)),
        ('invented_pending_body_words', lambda d: d['records'][pending]['written'].__setitem__('words', 1)),
        ('unclean_decode_status', lambda d: d['records'][0]['audio'].__setitem__('ffmpeg_exit', 1)),
        ('false_original_retention', lambda d: d['records'][derivative]['audio'].__setitem__('source_original_retained', True)),
        ('missing_source_run_success', lambda d: d['source_runs'][0]['successful_record_ids'].pop()),
        ('resolved_id_left_pending', lambda d: d['pending_queue'].append({'record_id': d['records'][0]['record_id']})),
        ('wrong_resolved_hold_count', lambda d: d['summary'].__setitem__('resolved_historical_failed_or_deferred_attempts', 0)),
    ]
    rejected = []
    with tempfile.TemporaryDirectory(prefix='publisher-public-mutations-', dir='/dev/shm') as directory:
        path = Path(directory)/'publisher-media.json'
        for name, mutate in mutations:
            data = copy.deepcopy(original); mutate(data)
            path.write_text(json.dumps(data))
            try: verify(path)
            except ValueError as error: rejected.append({'case': name, 'rejection': str(error)})
            else: raise AssertionError('Invalid fixture admitted: '+name)
    return {'status': 'passed_valid_control_and_12_public_metadata_mutations',
            'module_sha256': hashlib.sha256(raw).hexdigest(), 'valid_control': valid,
            'rejected_mutations': rejected,
            'scope': 'Artificial metadata changes only; no source data or audio modified.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', type=Path)
    print(json.dumps(run(parser.parse_args().module), indent=2))
