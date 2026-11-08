#!/usr/bin/env python3
"""Produce sanitized batch status and actual audio-window amplitude timelines."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import unicodedata

from asr_batch_prepare import artifact, read_bound


def loaded(ref):
    return json.loads(read_bound(ref).read_text())


def repetition(text):
    tokens = re.findall(r"\b\w+(?:['’]\w+)*\b", unicodedata.normalize('NFKC', text).casefold())
    longest = current = 0; previous = None
    for token in tokens:
        current = current+1 if token == previous else 1
        longest = max(current, longest); previous = token
    return longest


def project(manifest_path, resume_path, resume_invocation_path, registry_path, output_dir):
    if output_dir.exists():
        raise ValueError('Public editions are immutable; use a fresh output directory')
    manifest = json.loads(manifest_path.read_text())
    if manifest['status'] != 'completed_full_batch':
        raise ValueError('Only a completed full batch can be published')
    frame = loaded(manifest['frame']); stage = loaded(manifest['stage_receipt'])
    registry = json.loads(registry_path.read_text())
    resume = json.loads(resume_path.read_text())
    invocation = json.loads(resume_invocation_path.read_text())
    if (invocation['status'] != 'verified_no_inference_resume'
            or invocation['resume_inference_receipt']['sha256'] != digest_path(resume_path)
            or invocation['full_manifest']['sha256'] != digest_path(manifest_path)
            or invocation['new_inference_chunks'] != 0):
        raise ValueError('Whole-resume timing witness does not bind this completed batch')
    if (stage['status'] != 'completed' or resume['status'] != 'completed'
            or resume['submitted_chunks'] or resume['completed_new_chunks'] or resume['workers']
            or resume['verified_complete_cache_hits'] != len(frame['sources'])
            or resume['frame']['sha256'] != manifest['frame']['sha256']
            or resume['worker_sha256'] != stage['worker_sha256']
            or len(stage['workers']) != 2
            or len({x['state']['learned_parameter_elements'] for x in stage['workers']}) != 1):
        raise ValueError('Completed run and verified no-inference resume receipt required')
    receipts = {r['edition_id']: r for r in [loaded(x) for x in manifest['editions']]}
    if len(receipts) != len(manifest['sources']):
        raise ValueError('Edition cardinality mismatch')
    records = []; all_chunks = []; attempted = set()
    main_pids = {x['pid'] for x in stage['workers']}
    for source in manifest['sources']:
        matches = [x for x in registry['documents'] if x.get('publication_id') == source['publication_id']
                   or source['publication_id'] in x.get('legacy_source_ids', [])]
        if len(matches) != 1 or matches[0]['recording_id'] != source['recording_id']:
            raise ValueError('Registry publication/audio identity does not resolve uniquely')
        canonical = matches[0]
        receipt = receipts[source['edition_id']]; normalized = loaded(receipt['text_artifact'])
        chunks = [loaded(x) for x in receipt['chunks']]
        timeline = []; cursor = 0; flagged = 0
        for chunk in chunks:
            if (chunk['start_sample'] != cursor or chunk['source_audio_sha256'] != source['audio_artifact']['sha256']
                    or not chunk['encoder_exhausted'] or chunk['edition_id'] != source['edition_id']):
                raise ValueError('Chunk/source/coverage mismatch')
            cursor = chunk['end_sample']; repeat = repetition(chunk['text']); flagged += repeat >= 10
            timeline.append({'id': chunk['job_id'], 'start_seconds': chunk['start_sample']/16000,
                             'end_seconds': chunk['end_sample']/16000, 'samples': chunk['end_sample']-chunk['start_sample'],
                             'words': chunk['words'], 'rms_dbfs': chunk['rms_dbfs'], 'rms_zero': chunk['rms_zero'],
                             'peak_amplitude': chunk['peak_amplitude'], 'inference_seconds': chunk['inference_seconds'],
                             'empty_text': not chunk['text'].strip(), 'longest_identical_token_run': repeat})
            if chunk['worker_pid'] in main_pids:
                attempted.add(source['recording_id'])
            all_chunks.append(chunk)
        if cursor != source['canonical_s16_pcm']['sample_count'] or len(chunks) != source['planned_chunks']:
            raise ValueError('Full input coverage mismatch')
        old = source.get('old_text_artifact'); old_words = None
        if old:
            raw = read_bound(old).read_text()
            try:
                old_words = len(json.loads(raw)['text'].split())
            except (json.JSONDecodeError, TypeError, KeyError):
                old_words = len(raw.split())
        records.append({k: source[k] for k in ('source_id', 'publication_id', 'recording_id', 'edition_id',
                                               'medium', 'title', 'source_url', 'model_revision')})
        records[-1].update(status='completed', coverage_scope='full',
                           registry_source_id=canonical['source_id'],
                           registry_selected_edition_id=canonical['selected_edition_id'],
                           registry_selected_body_sha256=canonical['body_sha256'],
                           audio_sha256=source['audio_artifact']['sha256'],
                           canonical_s16_pcm_sha256=source['canonical_s16_pcm']['sha256'],
                           input_samples=cursor, covered_samples=cursor,
                           input_audio_seconds=cursor/16000, covered_audio_seconds=cursor/16000,
                           planned_chunks=source['planned_chunks'], completed_chunks=len(chunks), failed_chunks=0,
                           words=normalized['words'], old_words=old_words,
                           empty_text_chunks=sum(x['empty_text'] for x in timeline),
                           quality_flags={'repetition_windows': flagged,
                                          'screen_rule': 'Longest consecutive identical normalized token run >=10; post hoc screening, no exclusions or listening-based truth.'},
                           source_language_evidence=source['source_language_evidence'],
                           accuracy_verified=False, speaker_role='unknown',
                           old_transcript_sha256=old['sha256'] if old else None,
                           new_transcript_sha256=receipt['text_artifact']['sha256'],
                           edition_receipt_sha256=next(x['sha256'] for x in manifest['editions'] if loaded(x)['edition_id'] == source['edition_id']),
                           timeline=timeline)
    current = [x for x in all_chunks if x['worker_pid'] in main_pids]
    intervals = [[(x['wall_start_unix'], x['wall_end_unix']) for x in current if x['worker_pid'] == pid]
                 for pid in sorted(main_pids)]
    overlap = sum(max(0, min(a[1], b[1])-max(a[0], b[0])) for a in intervals[0] for b in intervals[1]) if len(intervals) == 2 else 0
    if len(current) != stage['completed_new_chunks'] or len(all_chunks) != frame['planned_chunks']:
        raise ValueError('Timing/cache chunk denominators differ')
    data = {'schema_version': 1, 'status': 'completed_full_batch',
            'summary': {'planned_recordings': len(records), 'attempted_recordings': len(attempted),
                        'completed_recordings': len(records), 'failed_recordings': 0, 'held_recordings': 0,
                        'planned_chunks': frame['planned_chunks'], 'completed_chunks': len(all_chunks),
                        'newly_recognized_full_run_chunks': len(current), 'cache_reused_chunks': stage['cached_chunks'],
                        'verified_complete_cache_hits': resume['verified_complete_cache_hits'],
                        'input_audio_seconds': frame['input_audio_seconds'],
                        'covered_audio_seconds': sum(r['covered_audio_seconds'] for r in records),
                        'words': sum(r['words'] for r in records), 'new_audio_downloads': 0,
                        'reused_prior_editions': manifest['reused_prior_editions']},
            'model': {'id': manifest['model_id'], 'revision': manifest['model_revision'],
                      'learned_parameter_elements': stage['workers'][0]['state']['learned_parameter_elements'],
                      'storage': 'Previously downloaded pinned model reused from temporary RAM; no new weight download or training.',
                      'supported_languages_scope': 'Published model supports 25 European languages; this sample does not establish multilingual accuracy.'},
            'settings': manifest['settings'], 'records': records,
            'performance': {'worker_count': len(stage['workers']), 'cpu_threads_per_worker': 1,
                            'stage_wall_seconds': stage['stage_wall_seconds'], 'actual_inference_overlap_seconds': overlap,
                            'summed_inference_seconds': sum(x['inference_seconds'] for x in current),
                            'median_new_chunk_real_time_factor': statistics.median(x['real_time_factor'] for x in current),
                            'model_load_seconds': [x['state']['model_load_seconds'] for x in stage['workers']],
                            'chunks_per_worker': [sum(x['worker_pid'] == pid for x in current) for pid in sorted(main_pids)],
                            'max_conservative_asr_memory_bytes': max(x['conservative_asr_bytes'] for x in stage['resource_samples']),
                            'resume_check_wall_seconds': invocation['whole_process_wall_seconds'],
                            'resume_timing_scope': invocation['scope'],
                            'scope': 'Shared cloud workload; measured worker stage includes loading/hash validation and queue processing. Selection admission, durable finalization and metadata projection are outside this timing. Cached pilot windows are excluded from current-stage timing. No matched serial speedup or accuracy comparison.'},
            'timeline_scope': 'Actual fixed audio-sample windows. RMS dBFS and peak are amplitude measurements, not emotion, speaker identity, transcript accuracy or word alignment.',
            'limitations': ['Purposive selection: all retained OmNa plus shortest eligible source in four other contexts; not representative channel or civilization estimates.',
                            'Library generation defaults still apply. No explicit token cap was supplied; outputs are admitted only after actual valid encoder-frame exhaustion, not an assumption of unbounded generation.',
                            'Full sample coverage and encoder exhaustion do not establish every spoken word was recovered accurately.',
                            'Independent nonoverlapping windows lose cross-boundary context; final tails included, speaker roles unknown.',
                            'Machine text and repetition/empty-text flags have not been verified by listening or human reference.',
                            'Prior transcripts and four completed Council upgrades remain preserved; these are new editions of retained audio, not new media downloads.',
                            'Partial chunk caches and model weights are temporary RAM; verified completed transcript editions are private workspace files. Environment deletion can remove them.'],
            'provenance': {'private_manifest_sha256': digest_path(manifest_path),
                           'registry_sha256': digest_path(registry_path),
                           'frame_sha256': manifest['frame']['sha256'], 'stage_receipt_sha256': manifest['stage_receipt']['sha256'],
                           'resume_receipt_sha256': digest_path(resume_path), 'producer_sha256': digest_path(Path(__file__))}}
    data['provenance']['resume_invocation_sha256'] = digest_path(resume_invocation_path)
    raw = (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode()
    if b'/workspace/' in raw or b'/dev/shm/' in raw or len(raw) > 1_000_000:
        raise ValueError('Public output includes private paths or exceeds metadata budget')
    output_dir.mkdir(parents=True)
    target = output_dir/'batch-asr.json'; target.write_bytes(raw)
    manifest_out = {'status': 'completed', 'public_allowlist': [{'file': target.name, 'bytes': len(raw),
                                                            'sha256': hashlib.sha256(raw).hexdigest()}]}
    (output_dir/'output-manifest.json').write_text(json.dumps(manifest_out, indent=2)+'\n')
    print(json.dumps(data['summary']))


def digest_path(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--resume-receipt', type=Path, required=True)
    parser.add_argument('--resume-invocation', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    project(args.manifest, args.resume_receipt, args.resume_invocation, args.registry, args.output_dir)
