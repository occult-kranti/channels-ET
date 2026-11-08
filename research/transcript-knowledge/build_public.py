#!/usr/bin/env python3
"""Copy reviewed transcript-knowledge producer allowlists into the static site."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3

MODULES = {'profiles.json': 'profiles', 'bank-index.json': 'bank',
           'curated.json': 'curated', 'graph.json': 'graph',
           'retrieval.json': 'retrieval', 'database.json': 'database',
           'literature.json': 'literature'}
REQUIRED = {'profiles', 'bank', 'curated', 'graph', 'retrieval', 'database'}
FORBIDDEN = {'full_text', 'transcript_text', 'source_body', 'private_evidence_text',
             'private_path', 'raw_question', 'raw_answer', 'question_text',
             'answer_text', 'evidence_text', 'exact_text', 'raw_context'}
PRIVATE_SUFFIXES = {'.mp4', '.mkv', '.webm', '.mp3', '.wav', '.flac', '.opus',
                    '.m4a', '.ogg', '.safetensors', '.pt', '.pth', '.gguf', '.npz', '.pkl'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid publication path')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Unsafe publication path')
    target = (Path(root) / path).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError('Publication path escapes its directory')
    return target


def inspect_public_json(raw):
    if any(s in raw for s in (b'/workspace/', b'/dev/shm/', b'channels-et-private')):
        raise ValueError('Private path in public JSON')
    value = json.loads(raw)
    def visit(node):
        if isinstance(node, dict):
            if FORBIDDEN.intersection(node):
                raise ValueError('Raw evidence field in public JSON')
            for x in node.values(): visit(x)
        elif isinstance(node, list):
            for x in node: visit(x)
        elif isinstance(node, float) and not math.isfinite(node):
            raise ValueError('Non-finite public JSON number')
    visit(value)
    return value


def inspect_public_sqlite(path):
    path = Path(path)
    if path.name != 'database-public.sqlite':
        raise ValueError('Only the declared public SQLite database may be published')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as con:
        if con.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise ValueError('Public SQLite database is corrupt')
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        allowed = {'meta', 'sources', 'profiles', 'records', 'questions', 'cards', 'evidence',
                   'record_evidence', 'card_evidence', 'passages', 'public_search',
                   'graph_nodes', 'graph_edges', 'public_search_data', 'public_search_idx',
                   'public_search_content', 'public_search_docsize', 'public_search_config'}
        if any(t not in allowed and not t.startswith('sqlite_') for t in tables):
            raise ValueError('Unexpected or private table in public SQLite')
        if not {'sources', 'records', 'evidence', 'public_search'} <= tables:
            raise ValueError('Public SQLite schema is incomplete')
        for table, columns in {'sources': ['body'],
                'records': ['question_text', 'answer_text', 'context_text'],
                'evidence': ['text']}.items():
            existing = {r[1] for r in con.execute('PRAGMA table_info("' + table + '")')}
            for column in columns:
                if column in existing and con.execute('SELECT 1 FROM "' + table + '" WHERE "' + column + '" IS NOT NULL LIMIT 1').fetchone():
                    raise ValueError('Raw evidence in public SQLite: ' + table + '.' + column)
        if 'passages' in tables and con.execute('SELECT 1 FROM passages LIMIT 1').fetchone():
            raise ValueError('Private passage rows in public SQLite')
        for table in tables & allowed:
            columns = {r[1] for r in con.execute('PRAGMA table_info("' + table + '")')}
            for column in columns:
                if column.endswith('_json'):
                    for (value,) in con.execute('SELECT "' + column + '" FROM "' + table + '" WHERE "' + column + '" IS NOT NULL'):
                        inspect_public_json(value.encode())
    return {'status': 'passed_public_database_boundary', 'tables': len(tables)}


def publish(args):
    root = args.site.resolve() / 'dist/transcript-knowledge'
    root.mkdir(parents=True, exist_ok=True)
    entries = {}; modules = {}; receipts = []

    def record(path, name, expected=None, copy=False):
        if path.suffix in PRIVATE_SUFFIXES:
            raise ValueError('Private media/model/intermediate in public allowlist')
        raw = path.read_bytes()
        if expected and (len(raw) != expected['bytes'] or digest(raw) != expected['sha256']):
            raise ValueError('Producer byte/hash mismatch: ' + name)
        if path.suffix == '.json': inspect_public_json(raw)
        if path.suffix in {'.sqlite', '.sqlite3', '.db'}: inspect_public_sqlite(path)
        ref = {'file': name, 'bytes': len(raw), 'sha256': digest(raw)}
        if name in entries:
            if entries[name] != ref: raise ValueError('Conflicting public artifact: ' + name)
            return ref
        target = safe_path(root, name)
        if copy:
            extra = max(0, len(raw) - (target.stat().st_size if target.exists() else 0))
            if shutil.disk_usage(root).free - extra < args.disk_floor_bytes:
                raise ValueError('Publication would cross the free-disk floor')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if target.read_bytes() != raw: raise ValueError('Published bytes changed')
        entries[name] = ref
        receipts.append({'input_path': str(path.resolve()), **ref})
        if name in MODULES:
            key = MODULES[name]
            modules[key] = {**ref, 'required': key in {'profiles', 'bank'}}
        return ref

    for folder in args.producer:
        descriptor = json.loads((folder / 'output-manifest.json').read_text())
        allowlist = descriptor['public_allowlist']
        if not allowlist or len({x['file'] for x in allowlist}) != len(allowlist):
            raise ValueError('Empty or duplicate producer allowlist')
        for ref in allowlist:
            record(safe_path(folder, ref['file']), ref['file'], ref, copy=True)
    if not args.preview and not REQUIRED <= modules.keys():
        raise ValueError('Completed release modules are missing: ' + str(sorted(REQUIRED - modules.keys())))
    source = Path(__file__).resolve().parent
    for path in sorted(source.glob('*.md')):
        record(path, 'docs/' + path.name, copy=True)
    for name in ('index.html', 'app.js', 'styles.css'):
        record(root / name, name)
    for path in sorted((root / 'vendor').rglob('*')) if (root / 'vendor').exists() else []:
        if path.is_file(): record(path, str(path.relative_to(root)))
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual - (entries.keys() | {'manifest.json'}):
        raise ValueError('Unlisted stale artifacts: ' + str(sorted(actual - entries.keys() - {'manifest.json'})))
    manifest = {'schema_version': 1,
                'title': 'Transcript Knowledge · Channeling Atlas',
                'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'scope': 'Frozen retained-source profiles, typed question candidates, bounded curated answers and source-linked graph. Public search excludes private full transcripts.',
                'modules': modules, 'artifacts': list(entries.values()),
                'builder_sha256': digest(Path(__file__).read_bytes())}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    (root / 'manifest.json').write_bytes(raw)
    if args.receipt:
        if not args.receipt.resolve().is_relative_to(Path('/workspace/channels-et-private')):
            raise ValueError('Copy receipt must remain private')
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps({'manifest_sha256': digest(raw),
            'generated_at': manifest['generated_at'], 'copies': receipts}, indent=2) + '\n')
    print(json.dumps({'modules': list(modules), 'artifacts': len(entries), 'manifest_sha256': digest(raw)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--producer', type=Path, action='append', default=[])
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--disk-floor-bytes', type=int, default=2 * 1024**3)
    publish(parser.parse_args())
