#!/usr/bin/env python3
"""Verify the static knowledge release without private transcript access."""
import argparse
from collections import Counter
import hashlib
import json
import sqlite3
from pathlib import Path

from build_public import REQUIRED, inspect_public_json, inspect_public_sqlite, safe_path


def require(condition, message):
    if not condition: raise ValueError(message)


def checked(root, ref):
    path = safe_path(root, ref['file'])
    raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
            'Artifact bytes/hash differ: ' + ref['file'])
    if path.suffix == '.json': inspect_public_json(raw)
    if path.suffix in {'.sqlite', '.sqlite3', '.db'}: inspect_public_sqlite(path)
    return raw


def publication_checks(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    require(manifest['schema_version'] == 1 and REQUIRED <= manifest['modules'].keys(),
            'Completed publication modules missing')
    refs = manifest['artifacts']
    require(len({r['file'] for r in refs}) == len(refs), 'Duplicate public artifact identity')
    indexed = {r['file']: r for r in refs}
    for ref in refs: checked(root, ref)
    require({'index.html', 'app.js', 'styles.css', 'vendor/minisearch.js'} <= indexed.keys(),
            'UI or pinned search library omitted from publication hashes')
    modules = {}
    for key, ref in manifest['modules'].items():
        require(ref['file'] in indexed, 'Module omitted from artifact inventory')
        require(all(ref[k] == indexed[ref['file']][k] for k in ('bytes', 'sha256')),
                'Module/artifact binding differs')
        modules[key] = json.loads(checked(root, ref))
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    expected = indexed.keys() | {'manifest.json'}
    require(actual == expected, 'Published set differs; unexpected=' + str(sorted(actual - expected)) +
            ', missing=' + str(sorted(expected - actual)))
    return manifest, modules


def source_checks(profiles, registry, registry_sha256):
    docs = {r['source_id']: r for r in registry['documents']}
    rows = profiles['profiles']
    require(len(rows) == len(docs) and {r['source_id'] for r in rows} == docs.keys(),
            'Automatic profile source universe differs')
    require(profiles['bindings']['registry_sha256'] == registry_sha256,
            'Profile registry binding differs')
    for row in rows:
        original = docs[row['source_id']]
        for field in ('selected_edition_id', 'body_sha256', 'words', 'channel_id', 'creator_id', 'title'):
            require(row[field] == original[field], 'Canonical profile field differs: ' + field)
        require(row['summary_kind'] == 'automatic_source_profile', 'Automatic outline mislabeled as close reading')
        require(row['coverage']['human_read'] is False and row['coverage']['audio_listened'] is False,
                'Unsupported human reading/audio claim')
        require(row['coverage']['processed_words'] == row['coverage']['total_words'] == original['words'],
                'Automatic profile body coverage differs')
    return {'source_profiles': len(rows), 'words': sum(r['words'] for r in rows),
            'publisher_contexts': len({r['channel_id'] for r in rows})}


def cross_bindings(root, manifest, modules, registry):
    refs = manifest['modules']; profiles = modules['profiles']; curated = modules['curated']
    frame_hash = profiles['bindings']['frame_sha256']
    require(curated['bindings']['frame']['sha256'] == frame_hash, 'Curated frame differs from profiles')
    for name in ('database', 'graph'):
        bindings = modules[name]['bindings']
        for key in ('profiles', 'curated'):
            require(bindings[key]['sha256'] == refs[key]['sha256'], 'Downstream annotation binding differs: ' + name + '/' + key)
    for name in ('database', 'graph', 'retrieval'):
        binding = modules[name]['bindings']
        require(binding['frame']['sha256'] == frame_hash and
                binding['registry']['sha256'] == profiles['bindings']['registry_sha256'] and
                binding['analysis']['sha256'] == profiles['bindings']['analysis_sha256'],
                'Downstream canonical input binding differs: ' + name)
    docs = {r['source_id']: r for r in registry['documents']}
    for row in curated['source_bindings']:
        original = docs[row['source_id']]
        require(row['selected_edition_id'] == original['selected_edition_id'] and
                row['body_sha256'] == original['body_sha256'] and
                row['text_artifact_sha256'] == original['text_artifact']['sha256'],
                'Curated evidence edition differs from the canonical source')
    path = safe_path(root, modules['database']['public_database']['file'])
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        rows = db.execute('SELECT source_id,selected_edition_id,body_sha256,words FROM sources').fetchall()
        expected = {(r['source_id'], r['selected_edition_id'], r['body_sha256'], r['words']) for r in docs.values()}
        require(set(rows) == expected and len(rows) == len(expected), 'Database source editions differ from published profiles')
        records = {r[0] for r in db.execute('SELECT record_id FROM records')}
        require(records == {r['record_id'] for r in modules['bank']['records']}, 'Database/bank record sets differ')
        require({r[0] for r in db.execute('SELECT card_id FROM cards')} == {r['card_id'] for r in curated['cards']},
                'Database/curated card sets differ')
    return {'canonical_sources': len(docs), 'database_record_ids': len(records),
            'curated_source_bindings': len(curated['source_bindings']), 'frame_sha256': frame_hash}


def verify(site):
    root = Path(site).resolve() / 'dist/transcript-knowledge'
    manifest, modules = publication_checks(root)
    registry_path = Path(site).resolve() / 'dist/channel-lab/registry.json'
    raw = registry_path.read_bytes(); registry = json.loads(raw)
    checks = {'canonical_profiles': source_checks(modules['profiles'], registry, hashlib.sha256(raw).hexdigest())}
    from verify_extraction import verify as verify_extraction
    from verify_curated import verify as verify_curated
    from verify_retrieval import verify as verify_retrieval
    checks['extraction'] = verify_extraction(root)
    checks['curated'] = verify_curated(root)
    checks['retrieval_graph_database'] = verify_retrieval(root)
    checks['cross_bindings'] = cross_bindings(root, manifest, modules, registry)
    return {'status': 'passed', 'artifacts': len(manifest['artifacts']),
            'modules': list(modules), 'checks': checks,
            'manifest_sha256': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest(),
            'scope': 'Public byte integrity, exact publication set, canonical joins and module invariants. Private source reading and model arithmetic have separate audit receipts.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().site)))
