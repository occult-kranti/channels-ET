#!/usr/bin/env python3
"""Recheck retained source artifacts without equating publisher and YouTube editions."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''): h.update(chunk)
    return h.hexdigest()


def binding(path):
    return {'file': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def build(frame_path, output, receipt):
    if output.exists(): raise ValueError('Use a fresh output directory')
    frame_path = frame_path.resolve()
    spec = importlib.util.spec_from_file_location('archive_sources', ROOT / 'research/channel-lab/sources.py')
    sources = importlib.util.module_from_spec(spec); spec.loader.exec_module(sources)
    # The established loader checks artifact hashes, text transformations and body hashes.
    docs = sources.load_frame(frame_path)
    frame = json.loads(frame_path.read_text())
    registry_path = ROOT / 'dist/channel-lab/registry.json'
    registry = json.loads(registry_path.read_text())
    if {d['record']['source_id'] for d in docs} != {d['source_id'] for d in registry['documents']}:
        raise ValueError('Private frame and public registry differ')
    registry_by_id = {d['source_id']: d for d in registry['documents']}
    for doc in docs:
        record = doc['record']; public = registry_by_id[record['source_id']]
        for field in ('selected_edition_id', 'body_sha256', 'words', 'channel_id'):
            if record[field] != public[field]: raise ValueError('Canonical registry field differs: ' + field)
    coverage_path = ROOT / 'dist/channel-lab/collection-coverage.json'
    coverage = json.loads(coverage_path.read_text())
    if coverage['registry_sha256'] != digest(registry_path): raise ValueError('Registry changed')
    upstream = {r['channel_id']: r for r in coverage['channels']}
    contexts = {}; media_cache = {}; text_paths = {}; private_checks = []
    for doc in docs:
        r = doc['record']; cid = r['channel_id']
        context = contexts.setdefault(cid, {'channel_id': cid, 'display_name': r['channel_name'],
            'selected_text_units': 0, 'selected_words': 0, 'selected_units_with_verified_media': 0,
            'upstream_collection_counts': upstream.get(cid, {}).get('upstream_collection_counts'),
            'upstream_scope': upstream.get(cid, {}).get('scope'),
            'source_binding': upstream.get(cid, {}).get('source_binding')})
        context['selected_text_units'] += 1; context['selected_words'] += r['words']
        text_path = Path(r['text_artifact']['path']); text_paths[str(text_path.resolve())] = text_path.stat().st_size
        ref = r.get('media_artifact')
        if not ref: continue
        path = Path(ref['path']); key = str(path.resolve())
        if key not in media_cache:
            if not path.is_file(): raise ValueError('Missing retained media: ' + str(path))
            actual = digest(path)
            if actual != ref['sha256'] or ('bytes' in ref and path.stat().st_size != ref['bytes']):
                raise ValueError('Retained media bytes changed: ' + str(path))
            media_cache[key] = {'sha256': actual, 'bytes': path.stat().st_size}
            private_checks.append({'path': str(path), **media_cache[key]})
        elif media_cache[key]['sha256'] != ref['sha256']: raise ValueError('Conflicting media reference')
        context['selected_units_with_verified_media'] += 1
    output.mkdir(parents=True)
    result = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Fresh byte verification of the frozen canonical source frame; upstream segment/publication ledgers remain separately scoped historical receipts.',
        'youtube': {'verified_audio_files': 0, 'verified_video_files': 0, 'verified_transcript_files': 0,
            'note': 'No exact YouTube-edition media/text admitted by this reconciliation. Publisher editions and historical caption analyses cannot be joined by title or medium alone.'},
        'canonical_frame': {'documents': len(docs), 'words': sum(r['record']['words'] for r in docs),
            'selected_text_artifacts_verified': len(docs), 'media_files_hash_verified': len(media_cache),
            'frame_sha256': digest(frame_path), 'registry_sha256': digest(registry_path)},
        'publisher_contexts': list(contexts.values()),
        'storage': {'destinations': [
            {'id': 'managed-workspace', 'label': 'Private managed workspace', 'status': 'retained_files_verified',
             'scope': 'Exact selected source artifacts rehashed. This is not permanent ChatGPT account storage or an external backup.'},
            {'id': 'github', 'label': 'GitHub / Pages', 'status': 'metadata_and_code_only',
             'scope': 'Public code, metadata, manifests, derived research and bounded annotations; full audio/video/transcripts remain private.'},
            {'id': 'drive', 'label': 'Google Drive', 'status': 'no_verified_upload',
             'scope': 'No callable authenticated Drive connection or upload receipt in this run.'}],
            'selected_media_bytes': sum(v['bytes'] for v in media_cache.values()),
            'selected_text_bytes': sum(text_paths.values()), 'free_disk_bytes': shutil.disk_usage(ROOT).free,
            'disk_floor_bytes': 2 * 1024**3,
            'count_basis': 'Distinct resolved paths in the selected canonical frame only; not total archive storage and not deduplicated by encoded content.'},
        'input_bindings': [binding(registry_path), binding(coverage_path), binding(ROOT / 'research/harvest/artifacts.json')],
        'limitations': ['Publisher context is not a verified YouTube uploader identity.',
            'Ra segment counts, publication rows, unique encoded families and canonical text units have different denominators; do not add them.',
            'All existing canonical texts were previously analyzed; this run checks retention and does not rerun topic models.',
            'Media rehashing confirms retained bytes, not speech-recognition accuracy or equivalent YouTube editions.',
            'Earlier 30 YouTube-caption analyses lack verified retained original bodies in this canonical frame.']}
    target = output / 'reconciliation.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (output / 'output-manifest.json').write_text(json.dumps({'public_allowlist': [
        {'file': target.name, 'bytes': target.stat().st_size, 'sha256': digest(target)}]}, indent=2) + '\n')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'generated_at': result['generated_at'], 'frame': str(frame_path),
        'frame_sha256': result['canonical_frame']['frame_sha256'], 'media_checks': private_checks,
        'output_sha256': digest(target)}, indent=2) + '\n')
    print(json.dumps({'documents': len(docs), 'media_files_rehashed': len(media_cache),
        'media_bytes': result['storage']['selected_media_bytes'], 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args(); build(args.frame, args.output, args.receipt)
