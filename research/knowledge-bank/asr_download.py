#!/usr/bin/env python3
"""Download a pinned, allowlisted speech-model snapshot into temporary RAM storage."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

FILES = ('config.json', 'generation_config.json', 'model.safetensors',
         'processor_config.json', 'tokenizer.json', 'tokenizer_config.json')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def download(repo, revision, output, receipt, byte_cap=3_000_000_000):
    output = output.resolve()
    if not output.is_relative_to(Path('/dev/shm')) or output.exists():
        raise ValueError('Model output must be a fresh directory under /dev/shm')
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('A complete immutable Hub commit is required')
    if len(repo.split('/')) != 2 or any(x in repo for x in ('..', '?', '#', '%')):
        raise ValueError('Unexpected model repository')
    url = f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true'
    with urlopen(Request(url, headers={'User-Agent': 'ChannelsET-ASR-Research/1.0'}), timeout=40) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('Metadata exceeds admission cap')
    metadata = json.loads(raw)
    if metadata['sha'] != revision:
        raise ValueError('Resolved revision differs from requested commit')
    sources = {row['rfilename']: row for row in metadata['siblings']}
    chosen = [sources[name] for name in FILES]
    total = sum(row['size'] for row in chosen)
    if total > byte_cap or shutil.disk_usage('/dev/shm').free < total + 2 * 1024**3:
        raise ValueError('Model bytes exceed temporary-storage budget')
    if shutil.disk_usage('/workspace').free < 2 * 1024**3:
        raise ValueError('Durable disk floor is not available')
    output.mkdir(parents=True)
    result = {'status': 'downloading', 'repo': repo, 'revision': revision,
              'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'storage': 'Temporary RAM-backed model files; not permanent account storage',
              'output_path': str(output), 'metadata_url': url,
              'metadata_sha256': hashlib.sha256(raw).hexdigest(),
              'selected_bytes': total, 'byte_cap': byte_cap,
              'script_sha256': sha(Path(__file__)), 'files': []}
    dump(receipt, result)
    dump(receipt.with_name('model-source-metadata.json'), metadata)
    try:
        for row in chosen:
            name, size = row['rfilename'], row['size']
            canonical = f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
            temporary = output / (name + '.part')
            h, count = hashlib.sha256(), 0
            with urlopen(Request(canonical, headers={'User-Agent': 'ChannelsET-ASR-Research/1.0'}), timeout=90) as response, temporary.open('xb') as target:
                status = response.status
                if status != 200:
                    raise ValueError('Expected complete HTTP response for model file')
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    count += len(block)
                    if count > size:
                        raise ValueError('Downloaded model file exceeds pinned size')
                    target.write(block)
                    h.update(block)
                target.flush()
                os.fsync(target.fileno())
            digest = h.hexdigest()
            if count != size or (row.get('lfs', {}).get('sha256') and row['lfs']['sha256'] != digest):
                raise ValueError('Model size or primary LFS SHA-256 mismatch')
            # Non-LFS config files have an exact Git object identity in the pinned API.
            if not row.get('lfs'):
                git_hash = hashlib.sha1(f'blob {count}\0'.encode() + temporary.read_bytes()).hexdigest()
                if git_hash != row['blobId']:
                    raise ValueError('Configuration Git object hash mismatch')
            target = output / name
            temporary.rename(target)
            result['files'].append({'file': name, 'bytes': count, 'sha256': digest,
                                    'canonical_url': canonical, 'http_status': status,
                                    'primary_lfs_sha256': row.get('lfs', {}).get('sha256'),
                                    'primary_git_blob': row['blobId']})
            dump(receipt, result)
            print(name, count, flush=True)
        result['status'] = 'downloaded_and_hash_verified'
    except Exception as exc:
        result['status'] = 'failed'
        result['failure_type'] = type(exc).__name__
        # Do not record redirected signed URLs or HTTP exception bodies.
        dump(receipt, result)
        raise
    result['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    dump(receipt, result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--receipt', required=True, type=Path)
    a = p.parse_args()
    download(a.repo, a.revision, a.output, a.receipt)
