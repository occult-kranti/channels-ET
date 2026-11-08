#!/usr/bin/env python3
"""Preserve the exact private crawl edition in a verified compressed archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def stream_hash(stream):
    h = hashlib.sha256(); size = 0
    for block in iter(lambda: stream.read(4 * 1024**2), b''):
        h.update(block); size += len(block)
    return h.hexdigest(), size


def archive(source, config, target):
    if target.exists() or target.with_suffix(target.suffix + '.partial').exists():
        raise ValueError('Use a fresh archive edition')
    private = json.loads((source / 'discovery-private.json').read_text())
    expected = {}
    for row in private['page_receipts']:
        if row['status'] == 'retrieved':
            name = row['artifact_file']
            if Path(name).is_absolute() or '..' in Path(name).parts: raise ValueError('Unsafe source path')
            expected['crawl/' + name] = (row['sha256'], row['bytes'])
    with config.open('rb') as stream: config_hash, config_size = stream_hash(stream)
    if config_hash != private['config_binding']['sha256'] or config_size != private['config_binding']['bytes']:
        raise ValueError('Config differs from crawl binding')
    expected['config/' + config.name] = (config_hash, config_size)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.partial')
    with tarfile.open(partial, 'w:gz', compresslevel=6) as out:
        for path in sorted(source.rglob('*')):
            if not path.is_file(): continue
            if path.is_symlink(): raise ValueError('Symlinks are not retained as source artifacts')
            if shutil.disk_usage(target.parent).free < 2 * 1024**3 + 32 * 1024**2:
                raise ValueError('Private archive would approach the free-disk floor')
            name = 'crawl/' + str(path.relative_to(source))
            with path.open('rb') as stream: actual = stream_hash(stream)
            if name in expected and expected[name] != actual: raise ValueError('Source page differs from receipt')
            expected[name] = actual; out.add(path, arcname=name, recursive=False)
        out.add(config, arcname='config/' + config.name, recursive=False)
    checked = {}
    with tarfile.open(partial, 'r:gz') as inp:
        for member in inp:
            if not member.isfile() or member.name in checked or member.name not in expected:
                raise ValueError('Unexpected compressed member')
            with inp.extractfile(member) as stream: checked[member.name] = stream_hash(stream)
            if checked[member.name] != expected[member.name]: raise ValueError('Compressed member changed')
    if checked != expected: raise ValueError('Compressed archive lacks declared source artifacts')
    partial.rename(target)
    with target.open('rb') as stream: final_hash, final_bytes = stream_hash(stream)
    receipt = {'status': 'verified_compressed_private_crawl', 'source_directory': str(source),
        'archive_path': str(target), 'sha256': final_hash, 'compressed_bytes': final_bytes,
        'uncompressed_bytes': sum(n for _, n in expected.values()), 'verified_members': len(checked),
        'verified_source_pages': len({r['artifact_file'] for r in private['page_receipts'] if r['status'] == 'retrieved'}),
        'discovery_counts': private['counts'],
        'scope': 'Exact private source bytes survive compression; no source deletion or permanent external backup is asserted.'}
    target.with_suffix(target.suffix + '.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path); p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(); archive(a.source, a.config, a.output)
