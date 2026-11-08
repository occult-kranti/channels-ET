#!/usr/bin/env python3
"""Verify the exact static publication set and cross-module release bindings."""
import argparse
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

from build_public import safe_path, inspect_public_json
from sources import verify_registry
from source_coverage import verify as verify_coverage
from verify_analysis import verify as verify_analysis
from verify_asr_effects import verify as verify_effects


def require(value, message):
    if not value: raise ValueError(message)


def checked(root, ref):
    path = safe_path(root, ref['file'])
    require(path.is_file(), 'Missing artifact: ' + ref['file'])
    raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
            'Artifact bytes/hash differ: ' + ref['file'])
    if path.suffix == '.json': inspect_public_json(raw)
    return raw


def publication_checks(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    required = {'registry', 'coverage', 'analysis', 'batch_asr', 'readings', 'asr_effects'}
    require(required <= manifest['modules'].keys(), 'Completed release modules missing')
    artifacts = manifest['artifacts']
    require(len({x['file'] for x in artifacts}) == len(artifacts), 'Duplicate public artifact identity')
    indexed = {x['file']: x for x in artifacts}
    for ref in artifacts: checked(root, ref)
    modules = {}
    for key, ref in manifest['modules'].items():
        require(ref['file'] in indexed, 'Module omitted from download manifest')
        require(all(ref[k] == indexed[ref['file']][k] for k in ('bytes', 'sha256')), 'Module/download binding differs')
        modules[key] = json.loads(checked(root, ref))
    ui = {'index.html', 'app.js', 'styles.css'}
    for name in ui: require((root / name).is_file(), 'Missing UI asset: ' + name)
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    expected = set(indexed) | ui | {'manifest.json'}
    require(actual == expected,
            'Published file set differs; unexpected=' + str(sorted(actual - expected)) +
            ', missing=' + str(sorted(expected - actual)))
    return manifest, modules


def batch_checks(batch, registry):
    require(batch['status'] == 'completed_full_batch', 'Speech batch is incomplete')
    rows = batch['records']; summary = batch['summary']; settings = batch['settings']
    docs = {r['source_id']: r for r in registry['documents']}
    require(len({r['registry_source_id'] for r in rows}) == len(rows), 'Repeated batch source')
    for name in ('planned_recordings', 'attempted_recordings', 'completed_recordings', 'verified_complete_cache_hits'):
        require(summary[name] == len(rows), 'Batch recording count differs: ' + name)
    require(summary['failed_recordings'] == summary['held_recordings'] == summary['new_audio_downloads'] == 0,
            'Batch failure/download scope changed')
    sample_rate = settings['sample_rate']
    for row in rows:
        doc = docs[row['registry_source_id']]
        require(row['registry_selected_edition_id'] == doc['selected_edition_id'] and
                row['registry_selected_body_sha256'] == doc['body_sha256'], 'Batch selected source edition differs')
        require(row['audio_sha256'] == doc['audio_sha256'] and
                row['recording_id'] == 'audio-sha256:' + row['audio_sha256'], 'Batch recording identity differs')
        require(row['model_revision'] == batch['model']['revision'], 'Speech model revision differs')
        require(row['status'] == 'completed' and row['coverage_scope'] == 'full' and
                row['accuracy_verified'] is False and row['speaker_role'] == 'unknown', 'Unsupported batch completion/accuracy status')
        timeline = row['timeline']
        require(len(timeline) == row['planned_chunks'] == row['completed_chunks'] and row['failed_chunks'] == 0,
                'Speech window count differs')
        require(len({t['id'] for t in timeline}) == len(timeline), 'Repeated speech window')
        samples = 0
        for index, window in enumerate(timeline):
            require(window['start_seconds'] == samples / sample_rate, 'Speech windows contain a gap or overlap')
            require(0 < window['samples'] <= settings['window_samples'], 'Invalid speech window size')
            require(index == len(timeline) - 1 or window['samples'] == settings['window_samples'], 'Interior speech window shortened')
            samples += window['samples']
            require(window['end_seconds'] == samples / sample_rate, 'Speech window endpoint differs')
            require(window['empty_text'] == (window['words'] == 0) and window['words'] >= 0, 'Empty-window word count differs')
            require(0 <= window['peak_amplitude'] <= 1 and window['inference_seconds'] >= 0, 'Invalid amplitude/inference value')
            require(window['rms_zero'] == (window['rms_dbfs'] is None), 'Zero amplitude status differs')
        require(samples == row['input_samples'] == row['covered_samples'], 'Speech sample coverage is incomplete')
        require(samples / sample_rate == row['input_audio_seconds'] == row['covered_audio_seconds'], 'Speech duration differs')
        require(sum(t['words'] for t in timeline) == row['words'] and
                sum(t['empty_text'] for t in timeline) == row['empty_text_chunks'], 'Speech words/empty windows differ')
        require(sum(t['longest_identical_token_run'] >= 10 for t in timeline) == row['quality_flags']['repetition_windows'],
                'Repetition screen count differs')
    for field in ('planned_chunks', 'completed_chunks', 'words', 'input_audio_seconds', 'covered_audio_seconds'):
        require(math.isclose(sum(r[field] for r in rows), summary[field], abs_tol=1e-9), 'Speech aggregate differs: ' + field)
    perf = batch['performance']
    require(summary['newly_recognized_full_run_chunks'] + summary['cache_reused_chunks'] == summary['completed_chunks'],
            'Cached/new speech counts differ')
    require(sum(perf['chunks_per_worker']) == summary['newly_recognized_full_run_chunks'] and
            len(perf['chunks_per_worker']) == perf['worker_count'] == settings['workers'], 'Worker allocation differs')
    require(0 < perf['actual_inference_overlap_seconds'] <= perf['stage_wall_seconds'] and
            perf['resume_check_wall_seconds'] > 0, 'Invalid overlap/resume measurement')
    return {'recordings': len(rows), 'windows': summary['completed_chunks'], 'audio_seconds': summary['covered_audio_seconds'],
            'words': summary['words'], 'accuracy_verified': False}


def cross_bindings(manifest, modules):
    refs = manifest['modules']; registry = modules['registry']; analysis = modules['analysis']
    batch = modules['batch_asr']; effects = modules['asr_effects']
    frame_hash = refs['registry']['source_frame']['sha256']; registry_hash = refs['registry']['sha256']
    for value in (analysis['bindings'], effects['bindings']):
        require(value['frame_sha256'] == frame_hash and value['registry_sha256'] == registry_hash,
                'Cross-module canonical frame/registry binding differs')
    require(batch['provenance']['registry_sha256'] == registry_hash, 'Batch uses a different registry')
    require(effects['bindings']['analysis_sha256'] == refs['analysis']['sha256'] and
            effects['bindings']['asr_manifest_sha256'] == batch['provenance']['private_manifest_sha256'],
            'ASR sensitivity baseline/batch binding differs')
    for field in ('model_manifest_sha256', 'encoder_script_sha256'):
        require(effects['bindings'][field] == analysis['bindings'][field], 'Frozen encoder binding differs')
    docs = {r['source_id']: r for r in registry['documents']}
    batch_by_id = {r['registry_source_id']: r for r in batch['records']}
    editions = {(r['source_id'], r['edition_id']): r for r in registry['alternate_editions']}
    require({r['source_id'] for r in effects['pairs']} == batch_by_id.keys(), 'ASR sensitivity source set differs')
    for row in effects['pairs']:
        doc = docs[row['source_id']]; spoken = batch_by_id[row['source_id']]
        require(row['selected_edition_id'] == doc['selected_edition_id'] and
                row['selected_body_sha256'] == doc['body_sha256'], 'Sensitivity selected edition differs')
        require(row['audio_sha256'] == spoken['audio_sha256'] and row['recording_id'] == spoken['recording_id'],
                'Sensitivity recording binding differs')
        require(row['new_asr_edition_id'] == spoken['edition_id'] and
                row['new_asr_artifact_sha256'] == spoken['new_transcript_sha256'] and
                row['old_asr_artifact_sha256'] == spoken['old_transcript_sha256'], 'Sensitivity transcript artifact differs')
        old = editions[(row['source_id'], row['old_asr_edition_id'])]
        require(old['body_sha256'] == row['old_asr_body_sha256'] and
                old['text_artifact_sha256'] == row['old_asr_artifact_sha256'], 'Sensitivity old edition differs')
        require(row['same_audio_cue_change']['before']['whitespace_words'] == spoken['old_words'] and
                row['same_audio_cue_change']['after']['whitespace_words'] == spoken['words'], 'Sensitivity speech words differ')
    return {'canonical_sources': len(docs), 'paired_editions': len(effects['pairs']), 'frame_sha256': frame_hash}


def readings_checks(readings, registry, frame_binding):
    require(readings['input_bindings']['frame'] == frame_binding, 'Readings use a different canonical frame')
    sources = {r['source_id']: r for r in registry['documents']}
    coverage = readings['coverage']; bound = readings['source_bindings']
    require(coverage['frame_source_units'] == len(sources) and
            coverage['frame_words'] == sum(r['words'] for r in sources.values()), 'Reading-frame denominator differs')
    require(len({r['source_id'] for r in bound}) == len(bound) == coverage['primary_sources_read'], 'Reading source count differs')
    require(sum(r['unique_words_inspected'] for r in bound) == coverage['primary_unique_words_read'], 'Reading-word coverage differs')
    require(sum(r['complete_body_inspected'] for r in bound) == coverage['primary_complete_bodies_read'], 'Whole-body reading count differs')
    for row in bound:
        original = sources[row['source_id']]
        require(row['body_sha256'] == original['body_sha256'] and
                row['text_artifact_sha256'] == original['text_artifact']['sha256'] and
                row['selected_edition_id'] == original['selected_edition_id'], 'Source reading changed its evidence edition')
        require(0 < row['unique_words_inspected'] <= original['words'], 'Invalid bounded reading extent')
        require(row['human_validated'] is False and row['audio_listened'] is False, 'Unsupported listening/human validation claim')
    cases = readings['cases']
    require(len({r['case_id'] for r in cases}) == len(cases) == coverage['case_count'], 'Case identity/count differs')
    require(dict(Counter(r['relation'] for r in cases)) == coverage['relation_counts'], 'Case relation summary differs')
    for case in cases:
        require(case['question_kind'] == 'analyst_comparison', 'Analyst comparison mislabeled as documentary question')
        require(case['conditions'] and case['counter_reading'] and case['limitations'], 'Unqualified source comparison')
        require(set(case['source_ids']) <= sources.keys(), 'Case references an unknown canonical source')
        for evidence in case['evidence']:
            original = sources[evidence['source_id']]
            require(evidence['edition_join'] == 'same_edition' and
                    evidence['edition_text_sha256'] == original['body_sha256'] == evidence['selected_body_sha256'],
                    'Primary case evidence was silently transferred across editions')
            location = evidence['locator']
            require(0 <= location['start_character'] < location['end_character'] and location['words'] > 0,
                    'Invalid reading evidence location')
    modeled = {r['channel_id'] for r in registry['channels'] if r['type'] == 'modeled_publisher_context'}
    require({r['channel_id'] for r in readings['channel_notes']} == modeled, 'Reading notes omit or invent a modeled context')
    require(coverage['human_validated'] is False and coverage['audio_listened_seconds'] == 0, 'Unsupported reading validation status')
    return {'cases': len(cases), 'source_units_read': len(bound), 'unique_body_words_read': coverage['primary_unique_words_read'],
            'whole_bodies_read': coverage['primary_complete_bodies_read'], 'human_validated': False}


def verify(site):
    root = Path(site).resolve() / 'dist/channel-lab'
    manifest, modules = publication_checks(root)
    require('coverage' in modules, 'Collection totals must remain separate from modeled source counts')
    checks = {'registry': verify_registry(root), 'coverage': verify_coverage(root)}
    checks['readings'] = readings_checks(modules['readings'], modules['registry'], manifest['modules']['registry']['source_frame'])
    checks['analysis'] = verify_analysis(root)
    checks['batch_asr'] = batch_checks(modules['batch_asr'], modules['registry'])
    checks['asr_effects'] = verify_effects(root)
    checks['cross_bindings'] = cross_bindings(manifest, modules)
    return {'status': 'passed', 'modules': list(modules), 'artifacts': len(manifest['artifacts']),
            'module_checks': checks,
            'manifest_sha256': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest(),
            'scope': 'Exact static file set, artifact integrity and public-boundary checks; full source and model checks have separate receipts.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().site)))
