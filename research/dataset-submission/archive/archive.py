#!/usr/bin/env python3
"""Content-addressed private research archives and verified GitHub Release transfer.

No source file is removed. Model/runtime caches and credentials are excluded.
Remote operations require a private destination repository on every invocation.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOTS = {
    'channels-et-private': Path('/workspace/channels-et-private'),
    'channels-et-raw': Path('/workspace/channels-et-raw'),
    'channeling-atlas-private': Path('/workspace/channeling-atlas-private'),
}
EXCLUDE_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'model-cache',
                'batch-media-locks', 'dataset-submission-2026-11'}
EXCLUDE_NAMES = {'.env', '.netrc', '.npmrc', '.pypirc', 'rclone.conf', 'credentials.json',
                 'credentials', 'id_rsa', 'id_ed25519', 'id_ecdsa', 'cookies.txt'}
PATTERNS = (
    re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
)
HEX = re.compile(r'^[0-9a-f]{64}$')
PRIVATE_FLOOR = 1536 * 1024**2
SHARD_LIMIT = 1024**3


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def dump(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def read(path): return json.loads(Path(path).read_text())
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''): h.update(block)
    return h.hexdigest()
def binding(path):
    path = Path(path); return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Command failed: ' + command[0] + ': ' + result.stderr[-1500:])
    return result.stdout


def allowed_relative(name):
    path = Path(name)
    if path.is_absolute() or not name or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe relative archive name')
    return path


def sensitive(raw, secret_values):
    if any(value in raw for value in secret_values): return True
    # Prefix checks avoid three expensive regex scans across large binary media.
    if b'PRIVATE KEY-----' in raw and PATTERNS[0].search(raw): return True
    if any(prefix in raw for prefix in (b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_')) and PATTERNS[1].search(raw): return True
    return b'github_pat_' in raw and PATTERNS[2].search(raw) is not None


def hash_source(path, secret_values=()):
    before = path.stat(); h = hashlib.sha256(); carry = b''; secret_hit = False
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(block)
            window = carry + block
            secret_hit = secret_hit or sensitive(window, secret_values)
            carry = window[-max(512, max((len(x) for x in secret_values), default=0)):]
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed during inventory: ' + str(path))
    return {'bytes': after.st_size, 'sha256': h.hexdigest(), 'mode': after.st_mode & 0o777,
            'mtime_ns': after.st_mtime_ns, 'device': after.st_dev, 'inode': after.st_ino}, secret_hit


def inventory(output, roots=None):
    roots = roots or ROOTS
    output = Path(output)
    if output.exists(): raise ValueError('Use a fresh immutable inventory edition')
    values = [os.environ[k].encode() for k in ('GH_TOKEN', 'GITHUB_TOKEN', 'OPENAI_API_KEY',
        'HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'SUPABASE_SERVICE_ROLE_KEY')
        if len(os.environ.get(k, '')) >= 16]
    files = []; exclusions = []; symlinks = []; cache = {}; objects = {}
    for label, root in roots.items():
        root = Path(root)
        if not root.exists():
            exclusions.append({'root': label, 'relative_path': '.', 'reason': 'root_absent'}); continue
        for current, directories, names in os.walk(root, followlinks=False):
            current = Path(current)
            for name in list(directories):
                path = current / name; rel = str(path.relative_to(root))
                if name in EXCLUDE_DIRS:
                    directories.remove(name); exclusions.append({'root': label, 'relative_path': rel,
                        'reason': 'active_new_study_or_model_runtime_cache'}); continue
                if path.is_symlink():
                    directories.remove(name); symlinks.append({'root': label, 'relative_path': rel,
                        'target': os.readlink(path), 'kind': 'directory_symlink_not_followed'})
            for name in sorted(names):
                path = current / name; rel = str(path.relative_to(root))
                if name in EXCLUDE_NAMES or name.endswith(('.pyc', '.pyo', '.lock')):
                    exclusions.append({'root': label, 'relative_path': rel, 'reason': 'credential_runtime_or_lock_file'}); continue
                if path.is_symlink():
                    symlinks.append({'root': label, 'relative_path': rel, 'target': os.readlink(path),
                                     'kind': 'file_symlink_not_followed'}); continue
                if not path.is_file():
                    exclusions.append({'root': label, 'relative_path': rel, 'reason': 'not_regular_file'}); continue
                st = path.stat(); key = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
                if key not in cache: cache[key] = hash_source(path, values)
                meta, secret_hit = cache[key]
                if secret_hit:
                    exclusions.append({'root': label, 'relative_path': rel, 'reason': 'credential_pattern_or_active_secret_detected'}); continue
                row = {'root': label, 'relative_path': rel, **meta,
                    'artifact_scope': 'retained_project_file; acquisition_or_analysis_status_not_inferred_from_extension'}
                files.append(row)
                objects.setdefault(meta['sha256'], {'sha256': meta['sha256'], 'bytes': meta['bytes'],
                    'source_root': label, 'source_relative_path': rel, 'aliases': 0})['aliases'] += 1
    files.sort(key=lambda r: (r['root'], r['relative_path']))
    data = {'schema_version': 1, 'created_at': now(), 'scope': 'Retained pre-submission project source, media, text, provenance and research outputs; active new-study outputs are a later supplement.',
        'roots': {k: str(v) for k, v in roots.items()}, 'files': files,
        'objects': sorted(objects.values(), key=lambda r: r['sha256']),
        'symlinks': symlinks, 'exclusions': exclusions,
        'counts': {'logical_regular_file_paths': len(files), 'unique_content_objects': len(objects),
            'logical_bytes': sum(r['bytes'] for r in files), 'unique_content_bytes': sum(r['bytes'] for r in objects.values()),
            'symlinks_recorded': len(symlinks), 'explicit_exclusions': len(exclusions),
            'credential_bearing_files_excluded': sum(r['reason'] == 'credential_pattern_or_active_secret_detected' for r in exclusions)},
        'limits': ['Private archive only. No rights to publicly redistribute raw files are inferred.',
            'Logical path counts include aliases and partial/diagnostic artifacts; they are not media or analytical source counts.',
            'Model/runtime caches and live dataset-submission outputs are excluded explicitly; final study outputs require a separate bound supplement.',
            'File and directory symlinks are recorded but not followed or recreated automatically.'],
        'producer_sha256': sha(__file__)}
    output.mkdir(parents=True); dump(output / 'inventory.json', data)
    dump(output / 'inventory-binding.json', binding(output / 'inventory.json'))
    print(json.dumps(data['counts']), flush=True)
    return data


def plan(inventory_path, output, payload_limit=SHARD_LIMIT):
    if Path(output).exists(): raise ValueError('Use a fresh immutable plan edition')
    if not 1024 <= payload_limit < 2 * 1024**3 - 16 * 1024**2:
        raise ValueError('Shard payload must leave tar/compression headroom below GitHub 2GiB limit')
    inv = read(inventory_path); shards = []; group = []; size = 0
    # Largest first; each object appears exactly once. All paths are recovered via inventory aliases.
    for item in sorted(inv['objects'], key=lambda r: (-r['bytes'], r['sha256'])):
        if item['bytes'] > payload_limit: raise ValueError('An object exceeds the selected shard payload limit')
        cost = item['bytes'] + 1024
        if group and size + cost > payload_limit:
            shards.append({'number': len(shards)+1, 'payload_bytes': size, 'objects': group}); group = []; size = 0
        group.append(item['sha256']); size += cost
    if group: shards.append({'number': len(shards)+1, 'payload_bytes': size, 'objects': group})
    value = {'schema_version': 1, 'inventory_binding': binding(inventory_path),
        'payload_limit_bytes': payload_limit, 'compression': 'zstd level3 singlethread',
        'shards': shards, 'counts': {'shards': len(shards), 'objects': sum(len(s['objects']) for s in shards),
            'unique_source_bytes': inv['counts']['unique_content_bytes']},
        'github_asset_limit_bytes_exclusive': 2 * 1024**3, 'github_max_assets_per_release': 1000,
        'publication': 'private_release_only'}
    if len(shards) + 8 > 1000: raise ValueError('Too many release assets')
    dump(output, value); return value


class CheckedReader:
    def __init__(self, path, expected):
        self.path = path; self.stream = path.open('rb'); self.expected = expected
        self.h = hashlib.sha256(); self.n = 0; self.before = path.stat()
    def read(self, size):
        data = self.stream.read(size); self.h.update(data); self.n += len(data); return data
    def close(self):
        self.stream.close(); after = self.path.stat()
        if self.n != self.expected['bytes'] or self.h.hexdigest() != self.expected['sha256']:
            raise ValueError('Source object differs from frozen inventory')
        if (self.before.st_size, self.before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Source object changed while archived')


def check_shard(path, expected):
    seen = {}; errors = tempfile.TemporaryFile()
    process = subprocess.Popen(['zstd', '--decompress', '--stdout', '--quiet', str(path)], stdout=subprocess.PIPE, stderr=errors)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for member in archive:
                if not member.isfile() or not member.name.startswith('objects/'):
                    raise ValueError('Unexpected archive member type/name')
                key = member.name.removeprefix('objects/')
                if not HEX.fullmatch(key) or key in seen or key not in expected:
                    raise ValueError('Unexpected or duplicate archive object')
                stream = archive.extractfile(member); h = hashlib.sha256(); size = 0
                for block in iter(lambda: stream.read(4 * 1024**2), b''): h.update(block); size += len(block)
                if key != h.hexdigest() or size != expected[key]: raise ValueError('Archived object bytes changed')
                seen[key] = size
        # Drain the decoder so a long zero-filled tar trailer cannot fill its pipe.
        for block in iter(lambda: process.stdout.read(65536), b''):
            if block.strip(b'\0'): raise ValueError('Nonzero trailing archive data')
        if process.wait() != 0: raise ValueError('Zstd validation failed')
    finally:
        if process.poll() is None: process.kill(); process.wait()
        process.stdout.close()
        errors.close()
    if seen != expected: raise ValueError('Shard lacks declared objects')
    return {'objects_verified': len(seen), 'source_bytes_verified': sum(seen.values()), **binding(path)}


def build_shard(inventory_path, plan_path, number, output, floor=PRIVATE_FLOOR):
    inv = read(inventory_path); schedule = read(plan_path)
    if schedule['inventory_binding'] != binding(inventory_path): raise ValueError('Plan binds a different inventory')
    items = {r['sha256']: r for r in inv['objects']}; chosen = schedule['shards'][number-1]
    if chosen['number'] != number: raise ValueError('Invalid shard index')
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.with_suffix(output.suffix+'.partial').exists(): raise ValueError('Fresh shard path required')
    if shutil.disk_usage(output.parent).free - chosen['payload_bytes'] < floor:
        raise ValueError('Insufficient staging capacity above reserve')
    partial = output.with_suffix(output.suffix+'.partial'); errpath = output.with_suffix(output.suffix+'.zstd.log')
    with partial.open('xb') as sink, errpath.open('wb') as errors:
        process = subprocess.Popen(['zstd', '-T1', '-3', '--quiet', '--stdout'], stdin=subprocess.PIPE, stdout=sink, stderr=errors)
        try:
            with tarfile.open(fileobj=process.stdin, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
                for key in chosen['objects']:
                    item = items[key]; source = Path(inv['roots'][item['source_root']]) / allowed_relative(item['source_relative_path'])
                    reader = CheckedReader(source, item)
                    try:
                        info = tarfile.TarInfo('objects/'+key); info.size = item['bytes']; info.mode = 0o444
                        info.uid = info.gid = info.mtime = 0; archive.addfile(info, reader)
                    finally: reader.close()
            process.stdin.close()
            if process.wait() != 0: raise ValueError('Zstd compression failed')
        finally:
            if process.poll() is None: process.kill(); process.wait()
            if process.stdin and not process.stdin.closed:
                try: process.stdin.close()
                except BrokenPipeError: pass
    if partial.stat().st_size >= 2 * 1024**3: raise ValueError('GitHub release asset size exceeded')
    partial.rename(output)
    receipt = check_shard(output, {key: items[key]['bytes'] for key in chosen['objects']})
    receipt.update(shard_number=number, inventory_binding=binding(inventory_path), plan_binding=binding(plan_path),
        created_at=now(), producer_sha256=sha(__file__), zstd_version=run(['zstd', '--version']).strip(),
        source_files_removed=False)
    dump(output.with_suffix(output.suffix+'.receipt.json'), receipt)
    return receipt


def repository(repo):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo): raise ValueError('Invalid GitHub repository')
    data = json.loads(run(['gh', 'api', 'repos/'+repo]))
    if data.get('private') is not True: raise ValueError('Raw archive destination is not private')
    return {'full_name': data['full_name'], 'private': True, 'default_branch': data['default_branch']}


def release_info(repo, tag):
    return json.loads(run(['gh', 'api', 'repos/'+repo+'/releases/tags/'+tag]))


def verify_remote(repo, tag, local_ref):
    repository(repo); release = release_info(repo, tag)
    assets = [r for r in release['assets'] if r['name'] == local_ref['file']]
    if len(assets) != 1: raise ValueError('Expected one exact remote asset')
    asset = assets[0]
    if asset['state'] != 'uploaded' or asset['size'] != local_ref['bytes']:
        raise ValueError('Remote asset size/state differs')
    digest = asset.get('digest')
    if digest is not None and digest != 'sha256:'+local_ref['sha256']:
        raise ValueError('GitHub asset digest differs')
    errors = tempfile.TemporaryFile()
    process = subprocess.Popen(['gh', 'release', 'download', tag, '--repo', repo,
        '--pattern', local_ref['file'], '--output', '-'], stdout=subprocess.PIPE, stderr=errors)
    h = hashlib.sha256(); count = 0
    try:
        for block in iter(lambda: process.stdout.read(4 * 1024**2), b''): h.update(block); count += len(block)
        if process.wait() != 0: raise ValueError('Authenticated remote asset download failed')
    finally:
        if process.poll() is None: process.kill(); process.wait()
        process.stdout.close()
        errors.close()
    if count != local_ref['bytes'] or h.hexdigest() != local_ref['sha256']:
        raise ValueError('Remote bytes differ from local archive')
    return {'repository': repo, 'repository_private': True, 'release_tag': tag, 'release_id': release['id'],
        'release_url': release['html_url'], 'asset_id': asset['id'], 'asset_name': asset['name'],
        'asset_api_digest': digest, 'downloaded_bytes': count, 'downloaded_sha256': h.hexdigest(),
        'verified_at': now(), 'verification': 'full_authenticated_remote_download_and_sha256'}


def upload(repo, tag, path, receipt):
    repository(repo); path = Path(path); local_ref = binding(path)
    if local_ref['bytes'] >= 2 * 1024**3: raise ValueError('Asset exceeds GitHub release limit')
    release = release_info(repo, tag)
    existing = [a for a in release['assets'] if a['name'] == path.name]
    if not existing: run(['gh', 'release', 'upload', tag, str(path), '--repo', repo])
    result = verify_remote(repo, tag, local_ref); result['local_asset'] = local_ref
    dump(receipt, result); return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inventory'); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('plan'); p.add_argument('--inventory', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--payload-limit', type=int, default=SHARD_LIMIT)
    p = sub.add_parser('build'); p.add_argument('--inventory', type=Path, required=True); p.add_argument('--plan', type=Path, required=True); p.add_argument('--number', type=int, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--reserve', type=int, default=PRIVATE_FLOOR)
    p = sub.add_parser('upload'); p.add_argument('--repo', required=True); p.add_argument('--tag', required=True); p.add_argument('--asset', type=Path, required=True); p.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inventory': inventory(args.output)
    elif args.command == 'plan': print(json.dumps(plan(args.inventory, args.output, args.payload_limit)['counts']))
    elif args.command == 'build': print(json.dumps(build_shard(args.inventory, args.plan, args.number, args.output, args.reserve)))
    elif args.command == 'upload': print(json.dumps(upload(args.repo, args.tag, args.asset, args.receipt)))


if __name__ == '__main__': main()
