#!/usr/bin/env python3
"""Publish only explicit, hash-verified collection metadata allowlists."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil

MODULES = {'inventory.json': 'inventory', 'collector-status.json': 'collection',
           'reconciliation.json': 'reconciliation', 'literature.json': 'literature',
           'publisher-discovery.json': 'discovery', 'publisher-media.json': 'publisher_media',
           'publisher-text-recovery.json': 'publisher_text'}
REQUIRED = {'inventory', 'collection', 'reconciliation', 'discovery'}
SUFFIXES = {'.json', '.csv', '.tsv', '.md', '.html', '.css', '.js'}
FORBIDDEN = {'full_text', 'transcript_text', 'source_body', 'private_path', 'raw_question',
             'raw_answer', 'evidence_text', 'exact_text', 'cookies', 'authorization', 'access_token'}


def sha(raw): return hashlib.sha256(raw).hexdigest()


def safe(root, name):
    if not isinstance(name, str) or not name or ':' in name or '\\' in name:
        raise ValueError('Invalid publication name')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe publication path')
    target = (Path(root) / path).resolve()
    if not target.is_relative_to(Path(root).resolve()): raise ValueError('Publication path escapes root')
    return target


def inspect(raw):
    if any(s in raw for s in (b'/workspace/', b'/dev/shm/', b'channels-et-private')):
        raise ValueError('Private path in public JSON')
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate public JSON key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique_object)
    def walk(v):
        if isinstance(v, dict):
            if FORBIDDEN & set(v): raise ValueError('Private content or credential field in public JSON')
            for key in v: walk(key)
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
        elif isinstance(v, str) and any(marker in v for marker in ('/workspace/', '/dev/shm/', 'channels-et-private')):
            raise ValueError('Private path in decoded public JSON')
        elif isinstance(v, float) and not math.isfinite(v): raise ValueError('Nonfinite public number')
    walk(value); return value


def verify(site):
    root = Path(site) / 'dist/youtube-archive'
    manifest = inspect((root / 'manifest.json').read_bytes())
    refs = manifest['artifacts']; names = [r['file'] for r in refs]
    if len(names) != len(set(names)): raise ValueError('Duplicate publication name')
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual != set(names) | {'manifest.json'}: raise ValueError('Unlisted or missing public artifacts')
    by_name = {}
    for ref in refs:
        path = safe(root, ref['file'])
        if path.suffix not in SUFFIXES: raise ValueError('Nonmetadata artifact')
        raw = path.read_bytes()
        if len(raw) != ref['bytes'] or sha(raw) != ref['sha256']: raise ValueError('Public artifact hash mismatch')
        if path.suffix == '.json': inspect(raw)
        by_name[ref['file']] = ref
    if not REQUIRED <= set(manifest['modules']): raise ValueError('Missing release module')
    for key, ref in manifest['modules'].items():
        if key != MODULES.get(ref['file']): raise ValueError('Invalid module mapping')
        if {k: ref[k] for k in ('file', 'bytes', 'sha256')} != by_name.get(ref['file']):
            raise ValueError('Module and artifact differ')
    r = inspect((root / 'reconciliation.json').read_bytes())
    if sum(c['selected_text_units'] for c in r['publisher_contexts']) != r['canonical_frame']['documents']:
        raise ValueError('Reconciliation denominator differs')
    if sum(c['selected_words'] for c in r['publisher_contexts']) != r['canonical_frame']['words']:
        raise ValueError('Reconciliation word denominator differs')
    return {'status': 'passed_metadata_release_checks', 'artifacts': len(refs), 'modules': sorted(manifest['modules'])}


def build(site, producers, receipt, disk_floor_bytes=2 * 1024**3):
    if disk_floor_bytes < 1024**3: raise ValueError('Publication reserve must be at least 1 GiB')
    if receipt and receipt.resolve().is_relative_to(site.resolve()):
        raise ValueError('Private copy receipt must remain outside the public repository/site')
    root = site / 'dist/youtube-archive'; root.mkdir(parents=True, exist_ok=True)
    refs = {}; modules = {}; copies = []
    def include(path, name, expected=None, copy=False):
        if path.suffix not in SUFFIXES: raise ValueError('Nonmetadata artifact')
        raw = path.read_bytes(); ref = {'file': name, 'bytes': len(raw), 'sha256': sha(raw)}
        if expected and ref != {k: expected[k] for k in ('file', 'bytes', 'sha256')}:
            raise ValueError('Producer hash or size differs')
        if path.suffix == '.json': inspect(raw)
        if name in refs and refs[name] != ref: raise ValueError('Conflicting producer output')
        target = safe(root, name)
        if copy:
            extra = max(0, len(raw) - (target.stat().st_size if target.exists() else 0))
            if shutil.disk_usage(root).free - extra < disk_floor_bytes: raise ValueError('Disk reserve reached')
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        refs[name] = ref; copies.append({'source_path': str(path.resolve()), **ref})
        if name in MODULES: modules[MODULES[name]] = {**ref, 'required': MODULES[name] in REQUIRED}
    for folder in producers:
        listing = json.loads((folder / 'output-manifest.json').read_text())['public_allowlist']
        if not listing or len({r['file'] for r in listing}) != len(listing): raise ValueError('Invalid producer allowlist')
        for ref in listing: include(safe(folder, ref['file']), ref['file'], ref, True)
    for path in sorted(Path(__file__).parent.glob('*.md')): include(path, 'docs/' + path.name, copy=True)
    for name in ('index.html', 'app.js', 'styles.css'): include(root / name, name)
    manifest = {'schema_version': 1, 'title': 'YouTube archive · Channeling Atlas',
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Source-bound discovery, account identity, enumeration and verified retention. Unknown channel totals remain unknown.',
        'modules': modules, 'artifacts': list(refs.values()), 'builder_sha256': sha(Path(__file__).read_bytes())}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    (root / 'manifest.json').write_bytes(raw)
    result = verify(site)
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({'manifest_sha256': sha(raw), 'copies': copies, 'verification': result,
            'minimum_free_disk_bytes': disk_floor_bytes, 'free_disk_bytes': shutil.disk_usage(root).free}, indent=2) + '\n')
    print(json.dumps({**result, 'manifest_sha256': sha(raw)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--site', type=Path, required=True)
    p.add_argument('--producer', type=Path, action='append', default=[]); p.add_argument('--receipt', type=Path)
    p.add_argument('--disk-floor-bytes', type=int, default=2 * 1024**3)
    a = p.parse_args(); build(a.site, a.producer, a.receipt, a.disk_floor_bytes)
