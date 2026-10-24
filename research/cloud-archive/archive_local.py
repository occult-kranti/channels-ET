#!/usr/bin/env python3
"""Materialize a verified private local snapshot; never contact Drive or YouTube."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import stat
import sys
import uuid

REPO = Path(__file__).resolve().parents[2]
RAW_ROOT = Path('/workspace/channels-et-raw')
PLAN_PATH = REPO / 'research/storage-drive/archive-plan.json'
GUARD_PATH = REPO / 'research/storage-drive/archive.py'
GUARD_SHA256 = '24b71670627a5fc64ac2bcb19d4173f9475fe4c5b357f360a9cfc3c8053694c0'
BUDGET = 20 * 1024 ** 3
RESERVE = 6 * 1024 ** 3


def load_guard():
    if hashlib.sha256(GUARD_PATH.read_bytes()).hexdigest() != GUARD_SHA256:
        raise RuntimeError('Reviewed source-guard dependency changed; stop for review')
    # run_path reads the frozen code; no source or bytecode file is modified.
    return runpy.run_path(str(GUARD_PATH), run_name='cloud_archive_source_guard')


G = load_guard()
ArchiveError = G['ArchiveError']
hash_source = G['hash_source']
regular_source = G['regular_source']
safe_relative = G['safe_relative']
OwnedJsonOutput = G['OwnedJsonOutput']


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect_files(plan_path=PLAN_PATH, raw_root=RAW_ROOT, expected_plan_sha256=None):
    """Bind all 99 source files and 101 existing metadata files to the frozen plan."""
    plan_path, raw_root = Path(plan_path), Path(raw_root)
    if expected_plan_sha256 and sha(plan_path) != expected_plan_sha256:
        raise ArchiveError('Frozen source plan hash changed')
    plan = read_json(plan_path)
    if Path(plan['raw_root']) != raw_root:
        raise ArchiveError('Plan raw root differs from the selected local raw root')
    archive_name = safe_relative(plan['archive_name'])
    if '/' in archive_name:
        raise ArchiveError('Source archive name must be one directory')
    staging = raw_root / 'drive-staging' / archive_name
    ledger = {}
    sums = regular_source(staging / 'manifests/SHA256SUMS', raw_root)
    for line in sums.read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
        if not match:
            raise ArchiveError('Malformed staged SHA256SUMS entry')
        relative = safe_relative(match[2])
        if relative in ledger:
            raise ArchiveError('Duplicate staged checksum path')
        ledger[relative] = match[1]
    files, paths = [], set()
    for row in plan['files']:
        relative = safe_relative(row['relative_path'])
        if relative in paths or relative != G['artifact_path'](row):
            raise ArchiveError('Source destination collision or identity mismatch')
        paths.add(relative)
        source = regular_source(row['local_path'], raw_root)
        if source.stat().st_size != row['bytes'] or ledger.get(relative) != row['sha256']:
            raise ArchiveError('Source size or staged source SHA differs from frozen plan')
        files.append({'source_path': str(source), 'relative_path': relative, 'bytes': row['bytes'],
                      'sha256': row['sha256'], 'md5': row['md5'], 'kind': row['kind'],
                      'origin': 'source_artifact', 'source_id': row['source_id'],
                      'provider': row['provider'], 'practitioner': row['practitioner'],
                      'uploader': row['uploader']})
        sidecar_relative = relative + '.provenance.json'
        sidecar_path = regular_source(staging / sidecar_relative, raw_root)
        expected = {k: v for k, v in row.items() if k != 'local_path'}
        expected['schema_version'] = 1
        if read_json(sidecar_path) != expected:
            raise ArchiveError('Staged sidecar differs from frozen source provenance')
        actual = hash_source(sidecar_path, raw_root)
        if ledger.get(sidecar_relative) != actual['sha256']:
            raise ArchiveError('Staged provenance checksum differs')
        files.append({'source_path': str(sidecar_path), 'relative_path': sidecar_relative,
                      **actual, 'kind': 'provenance-sidecar', 'origin': 'archive_metadata',
                      'source_id': row['source_id']})
        paths.add(sidecar_relative)
    manifest_path = regular_source(staging / 'manifests/archive-manifest.json', raw_root)
    manifest = read_json(manifest_path)
    expected_files = [{k: v for k, v in r.items() if k != 'local_path'} for r in plan['files']]
    expected_aliases = [{k: v for k, v in r.items() if k != 'local_path'}
                        for r in plan.get('byte_identical_aliases', [])]
    if (manifest.get('files') != expected_files or manifest.get('byte_identical_aliases') != expected_aliases or
            manifest.get('plan_sha256') != G['digest_json'](plan) or manifest.get('archive_name') != archive_name or
            manifest.get('source_artifact_count') != plan['source_artifact_count']):
        raise ArchiveError('Staged manifest differs from frozen plan')
    for relative in ['manifests/archive-manifest.json', 'manifests/SHA256SUMS']:
        source = regular_source(staging / relative, raw_root)
        actual = hash_source(source, raw_root)
        if relative.endswith('.json') and ledger.get(relative) != actual['sha256']:
            raise ArchiveError('Staged manifest checksum differs')
        files.append({'source_path': str(source), 'relative_path': relative,
                      **actual, 'kind': 'archive-manifest', 'origin': 'archive_metadata'})
        paths.add(relative)
    if set(ledger) != paths - {'manifests/SHA256SUMS'}:
        raise ArchiveError('Staged checksum set differs from exact planned artifact set')
    if len(paths) != len(files) or sum(r['bytes'] for r in files if r['origin'] == 'source_artifact') != plan['canonical_bytes']:
        raise ArchiveError('Archive count or byte total is inconsistent')
    return plan, files


def check_directory(path, create=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ArchiveError('Local archive path must be absolute without traversal')
    for parent in [*reversed(path.parents), path]:
        try:
            info = parent.lstat()
        except FileNotFoundError:
            if not create:
                continue
            parent.mkdir(mode=0o700)
            info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ArchiveError('Local archive directory contains a symlink or non-directory')
    return path


def rename_no_replace(source, destination):
    """Linux atomic publication which fails when any destination already exists."""
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, 'renameat2', None)
    if function is None:
        raise ArchiveError('Atomic no-replace rename unavailable; no fallback overwrite allowed')
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise ArchiveError('Archive destination already exists; no overwrite')
        raise OSError(error, os.strerror(error))


@contextlib.contextmanager
def worker_lock(raw_root):
    path = check_directory(raw_root) / '.collection-worker.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ArchiveError('Shared worker lock is not a regular file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ArchiveError('Another collection worker owns the shared lock; no copy started') from exc
        yield
    finally:
        os.close(fd)


def used_raw_bytes(raw_root):
    total = 0
    for folder, directories, files in os.walk(raw_root, followlinks=False):
        directories[:] = [name for name in directories if not (Path(folder) / name).is_symlink()]
        for name in files:
            info = (Path(folder) / name).lstat()
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def copy_verified(row, raw_root, partial_root):
    source = regular_source(row['source_path'], raw_root)
    relative = safe_relative(row['relative_path'])
    target = partial_root / relative
    check_directory(target.parent, create=True)
    if target.exists() or target.is_symlink():
        raise ArchiveError('Local target already exists; no overwrite')
    temporary = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.partial')
    source_fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArchiveError('Copy source is not a regular file')
        target_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                            getattr(os, 'O_NOFOLLOW', 0), 0o600)
        sha256, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
        with os.fdopen(target_fd, 'wb') as destination, os.fdopen(source_fd, 'rb', closefd=False) as incoming:
            while block := incoming.read(4 * 1024 * 1024):
                destination.write(block)
                size += len(block)
                sha256.update(block)
                md5.update(block)
            destination.flush()
            os.fsync(destination.fileno())
        after = os.fstat(source_fd)
        actual = {'bytes': size, 'sha256': sha256.hexdigest(), 'md5': md5.hexdigest()}
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or
                any(actual[key] != row[key] for key in actual)):
            raise ArchiveError('Source changed or differs from planned bytes; partial retained')
        if hash_source(temporary, partial_root) != actual:
            raise ArchiveError('Independent copied-file checksum failed; partial retained')
        copied = temporary.stat()
        if copied.st_nlink != 1 or (copied.st_dev, copied.st_ino) == (before.st_dev, before.st_ino):
            raise ArchiveError('Copy is not an independent single-link file')
        rename_no_replace(temporary, target)
        return {k: v for k, v in row.items() if k != 'source_path'} | {'status': 'independent_copy_hash_verified'}
    finally:
        os.close(source_fd)


def verify_snapshot(root, files):
    root = check_directory(root)
    expected = {r['relative_path']: r for r in files}
    found = set()
    for folder, directories, names in os.walk(root, followlinks=False):
        for directory in directories:
            if (Path(folder) / directory).is_symlink():
                raise ArchiveError('Archive contains a symlink directory')
        for name in names:
            path = Path(folder) / name
            relative = path.relative_to(root).as_posix()
            row = expected.get(relative)
            if row is None:
                raise ArchiveError('Unexpected archive file or incomplete partial')
            actual = hash_source(path, root)
            if any(actual[k] != row[k] for k in actual) or path.stat().st_nlink != 1:
                raise ArchiveError('Archive file hash, size or independent-link verification failed')
            found.add(relative)
    if found != set(expected):
        raise ArchiveError('Archive is missing planned files')
    return {'verified_at': now(), 'files': len(found), 'bytes': sum(r['bytes'] for r in files),
            'sha256_and_md5_verified': True, 'exact_file_set_verified': True,
            'all_files_regular_single_link': True}


def create_archive(files, plan, output_dir, raw_root=RAW_ROOT, name=None, budget=BUDGET, reserve=RESERVE):
    raw_root, output_dir = Path(raw_root), Path(output_dir)
    name = name or f'cloud-local-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}-{uuid.uuid4().hex[:10]}'
    if safe_relative(name) != name or '/' in name or name.startswith('.'):
        raise ArchiveError('Archive name must be one safe visible directory')
    base = raw_root / 'cloud-archive'
    final, partial = base / name, base / ('.' + name + '.partial')
    receipt_path, state_path = output_dir / 'archive-receipt.json', output_dir / 'archive-state.json'
    # Reserve both outputs before creating an archive or taking any write action in raw storage.
    # The reviewed writer rejects existing output files and symlink parents.
    source_paths = [raw_root]
    with OwnedJsonOutput(receipt_path, 'plan', source_paths=source_paths) as receipt_output:
        with OwnedJsonOutput(state_path, 'plan', source_paths=source_paths) as state_output:
            receipt = {'schema_version': 1, 'started_at': now(), 'status': 'preflight',
                       'storage_kind': 'managed_chatgpt_cloud_local', 'archive_name': name,
                       'archive_path': str(final), 'partial_path': str(partial),
                       'source_archive_plan_name': plan['archive_name'], 'source_plan_sha256': G['digest_json'](plan),
                       'planned_files': len(files), 'planned_bytes': sum(r['bytes'] for r in files),
                       'copied_files': 0, 'copied_bytes': 0, 'published': False, 'records': [],
                       'raw_budget_bytes': budget, 'free_space_reserve_bytes': reserve,
                       'network_requests': 0, 'actual_drive_uploads': 0,
                       'source_files_opened_for_write': 0, 'independent_copy_not_symlink_or_hardlink': True}
            receipt_output.update(receipt)
            state_output.update({'schema_version': 1, 'status': 'preflight', 'actual_local_archive_completed': False,
                                 'actual_drive_uploaded_files': 0})
            try:
                with worker_lock(raw_root):
                    check_directory(base)
                    if final.exists() or final.is_symlink() or partial.exists() or partial.is_symlink():
                        raise ArchiveError('Archive or partial root already exists; no overwrite or resume')
                    used, free = used_raw_bytes(raw_root), shutil.disk_usage(raw_root).free
                    receipt['raw_bytes_before'] = used
                    receipt['disk_free_bytes_before'] = free
                    incoming = receipt['planned_bytes']
                    if used + incoming > budget or free < incoming + reserve:
                        raise ArchiveError('Shared raw-byte budget or free-space reserve prevents archive copy')
                    check_directory(base, create=True)
                    partial.mkdir(mode=0o700)
                    receipt['status'] = 'copying'
                    receipt_output.update(receipt)
                    for row in files:
                        record = copy_verified(row, raw_root, partial)
                        receipt['records'].append(record)
                        receipt['copied_files'] += 1
                        receipt['copied_bytes'] += row['bytes']
                        receipt_output.update(receipt)
                    receipt['verification'] = verify_snapshot(partial, files)
                    rename_no_replace(partial, final)
                    receipt['published'] = True
                    # Verify the published path too; no completion claim on publication alone.
                    receipt['verification'] = verify_snapshot(final, files)
                    receipt['raw_bytes_after'] = used_raw_bytes(raw_root)
                    receipt['disk_free_bytes_after'] = shutil.disk_usage(raw_root).free
                    receipt['status'] = 'completed'
            except (ArchiveError, OSError, ValueError) as exc:
                receipt['status'] = 'failed_partial_retained'
                receipt['error'] = str(exc) if isinstance(exc, ArchiveError) else type(exc).__name__
                raise
            finally:
                receipt['finished_at'] = now()
                receipt_output.update(receipt)
                complete = receipt['status'] == 'completed'
                state = {'schema_version': 1, 'checked_at': now(), 'status': receipt['status'],
                         'storage_kind': 'managed_chatgpt_cloud_local',
                         'user_authorized_fallback': True, 'user_reported_drive_connected': True,
                         'drive_connection_available_in_environment': False,
                         'actual_local_archive_created': final.is_dir() or partial.is_dir(),
                         'actual_local_archive_completed': complete,
                         'actual_local_archive_path': str(final if receipt['published'] else partial),
                         'actual_local_files': receipt['copied_files'], 'actual_local_bytes': receipt['copied_bytes'],
                         'hash_verified': complete, 'planned_files': len(files),
                         'planned_bytes': receipt['planned_bytes'], 'source_artifacts': sum(r['origin']=='source_artifact' for r in files),
                         'metadata_artifacts': sum(r['origin']=='archive_metadata' for r in files),
                         'actual_drive_folder_count': 0, 'actual_drive_uploaded_files': 0,
                         'actual_drive_upload_attempts': 0, 'quota_verified': False,
                         'user_reported_drive_quota_tb': 5, 'effective_drive_acl_verified': False,
                         'environment_retention_guaranteed': False,
                         'retention': 'Local managed environment storage; availability after environment deletion or expiry is not guaranteed.',
                         'git_media_files': 0, 'chat_attachment_created': False, 'network_requests': 0,
                         'receipt_path': str(receipt_path.relative_to(REPO) if receipt_path.is_relative_to(REPO) else receipt_path),
                         'source_plan_path': 'research/storage-drive/archive-plan.json',
                         'source_guard_sha256': GUARD_SHA256,
                         'limits': ['Local archive completion is not a Drive upload, Git media copy or downloadable chat attachment.',
                                    'Source manifest archive_name preserves the original plan identity; this local wrapper has its own dated name.',
                                    'Default local filesystem privacy is not an external storage durability or Drive ACL guarantee.',
                                    'No YouTube video or caption artifact was acquired by this storage operation.']}
                state_output.update(state)
            return receipt, state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='Actually copy and verify all source-plan artifacts locally')
    build.add_argument('--output-dir', type=Path, required=True, help='New metadata receipt directory outside the raw root')
    verify = commands.add_parser('verify', help='Rehash the exact materialized local archive')
    verify.add_argument('receipt', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'build':
            proof = read_json(REPO / 'research/storage-drive/verification.json')
            plan, files = collect_files(expected_plan_sha256=proof['source_pins']['archive-plan.json'])
            receipt, state = create_archive(files, plan, args.output_dir)
            print(json.dumps({k:v for k,v in state.items() if k != 'limits'}, indent=2))
        else:
            receipt = read_json(args.receipt)
            if not receipt.get('published') or receipt['status'] != 'completed':
                raise ArchiveError('Receipt does not identify a completed published archive')
            files = receipt['records']
            path = Path(receipt['archive_path'])
            if path.parent != RAW_ROOT / 'cloud-archive':
                raise ArchiveError('Receipt archive path is outside the dedicated archive root')
            print(json.dumps(verify_snapshot(path, files), indent=2))
        return 0
    except (ArchiveError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'status':'stopped','reason':str(exc) if isinstance(exc,(ArchiveError,RuntimeError)) else type(exc).__name__,
                          'network_requests':0,'sources_deleted_or_overwritten':False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
