#!/usr/bin/env python3
"""Plan private research archives offline; upload only to an explicit Drive remote.

Uses only Python's standard library and an already configured rclone executable.
Never configures OAuth, reads credential files, shares, syncs, deletes or moves.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import uuid

SCHEMA = 1
REPO = Path(__file__).resolve().parents[2]
RAW_ROOT = Path('/workspace/channels-et-raw')
KINDS = {'audio', 'video', 'transcript', 'primary-text', 'source-document', 'source-metadata'}
DRIVE_FLAGS = ['--drive-root-folder-id=root', '--drive-team-drive=',
               '--drive-service-account-file=', '--drive-service-account-credentials=',
               '--drive-import-formats=', '--drive-allow-import-name-change=false',
               '--drive-shared-with-me=false', '--drive-trashed-only=false',
               '--drive-skip-shortcuts', '--drive-auth-owner-only',
               '--retries=1', '--low-level-retries=1', '--contimeout=20s', '--timeout=5m']


class ArchiveError(Exception):
    pass


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def absolute_local_path(path):
    path = Path(path)
    if '..' in path.parts:
        raise ArchiveError('Output path traversal rejected')
    return path if path.is_absolute() else Path.cwd() / path


def within(path, root):
    return path == root or root in path.parents


def overlap(a, b):
    return within(a, b) or within(b, a)


def inspect_output_ancestors(path):
    for parent in [*reversed(path.parent.parents), path.parent]:
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ArchiveError('Output parent must be a real directory, never a symlink or file')


def output_path(path, purpose, stage_root=None, source_paths=()):
    """Validate without writing; use before any remote preflight or staging."""
    path = absolute_local_path(path)
    inspect_output_ancestors(path)
    try:
        path.lstat()  # Also rejects a dangling symlink, directory or hardlink.
    except FileNotFoundError:
        pass
    else:
        raise ArchiveError('Output already exists; no file, symlink or directory will be overwritten')
    if within(path, RAW_ROOT):
        receipt_root = RAW_ROOT / 'drive-receipts'
        if purpose != 'receipt' or path == receipt_root or not within(path, receipt_root):
            raise ArchiveError('Output is inside the source raw tree; receipts require dedicated drive-receipts storage')
    if stage_root is not None and overlap(path, absolute_local_path(stage_root)):
        raise ArchiveError('Receipt output must not overlap staging')
    if any(overlap(path, absolute_local_path(source)) for source in source_paths):
        raise ArchiveError('Output must not overlap a source artifact')
    return path


class OwnedJsonOutput:
    """Exclusive creation, then atomic updates to this instance's own inode only.

    The parent directory is opened component by component with O_NOFOLLOW.
    Updates never follow an output symlink or modify a pre-existing caller file.
    """
    def __init__(self, path, purpose, stage_root=None, source_paths=()):
        self.path = output_path(path, purpose, stage_root, source_paths)
        self.parent_fd = None
        self.identity = None
        self.parent_identity = None
        self.name = self.path.name
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_NOFOLLOW', 0)
        current = os.open('/', flags)
        try:
            for component in self.path.parent.parts[1:]:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
                following = os.open(component, flags, dir_fd=current)
                os.close(current)
                current = following
            self.parent_fd = current
            current = None
            info = os.fstat(self.parent_fd)
            self.parent_identity = (info.st_dev, info.st_ino)
            try:
                fd = os.open(self.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             getattr(os, 'O_NOFOLLOW', 0), 0o600, dir_fd=self.parent_fd)
            except FileExistsError as exc:
                raise ArchiveError('Output appeared during preflight; refusing to overwrite it') from exc
            try:
                info = os.fstat(fd)
                self.identity = (info.st_dev, info.st_ino)
            finally:
                os.close(fd)
        except Exception:
            if self.parent_fd is not None:
                os.close(self.parent_fd)
                self.parent_fd = None
            raise
        finally:
            if current is not None:
                os.close(current)

    def check_owned(self):
        inspect_output_ancestors(self.path)
        parent = self.path.parent.stat(follow_symlinks=False)
        if (parent.st_dev, parent.st_ino) != self.parent_identity:
            raise ArchiveError('Owned output parent changed; stopping without replacement')
        try:
            info = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ArchiveError('Owned output disappeared; refusing to recreate another file') from exc
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                (info.st_dev, info.st_ino) != self.identity):
            raise ArchiveError('Owned output was replaced, symlinked or hardlinked; no overwrite')

    def update(self, value):
        self.check_owned()
        data = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
        temporary = '.drive-archive-output-' + uuid.uuid4().hex + '.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, 'O_NOFOLLOW', 0), 0o600, dir_fd=self.parent_fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            self.check_owned()
            os.replace(temporary, self.name, src_dir_fd=self.parent_fd, dst_dir_fd=self.parent_fd)
            info = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
            self.identity = (info.st_dev, info.st_ino)
            os.fsync(self.parent_fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.parent_fd)
            except FileNotFoundError:
                pass

    def close(self):
        if self.parent_fd is not None:
            os.close(self.parent_fd)
            self.parent_fd = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def write_new_json(path, value, purpose='plan'):
    with OwnedJsonOutput(path, purpose) as output:
        output.update(value)


def safe_component(value):
    """Readable identity plus digest; distinct labels cannot silently collide."""
    if not isinstance(value, str) or not value.strip():
        raise ArchiveError('Empty path identity')
    if '/' in value or '\\' in value or '..' in value or any(ord(c) < 32 for c in value):
        raise ArchiveError('Unsafe path identity')
    clean = re.sub('[^a-z0-9_-]+', '-', value.lower()).strip('-_')[:55] or 'label'
    return clean + '-' + hashlib.sha256(value.encode()).hexdigest()[:10]


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ArchiveError('Unsafe relative archive path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in {'.', '..', ''} for x in value.split('/')):
        raise ArchiveError('Archive path traversal rejected')
    if any(ord(c) < 32 for c in value):
        raise ArchiveError('Control character in archive path')
    return p.as_posix()


def regular_source(path, root):
    """Reject traversal, final or intermediate symlinks, and special files."""
    path, root = Path(path), Path(root)
    if not path.is_absolute() or '..' in path.parts or not root.is_absolute():
        raise ArchiveError('Source must be an absolute path without traversal')
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ArchiveError('Source is outside the approved raw root') from exc
    for part in [root, *reversed(root.parents), *list(path.parents)[:len(path.parents)-len(root.parents)], path]:
        if part.is_symlink():
            raise ArchiveError('Symlink source or directory rejected')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ArchiveError('Source is not a regular file')
    return path


def hash_source(path, root):
    path = regular_source(path, root)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArchiveError('Nonregular open source rejected')
        sha = hashlib.sha256()
        md5 = hashlib.md5(usedforsecurity=False)
        size = 0
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            while data := stream.read(4 * 1024 * 1024):
                size += len(data)
                sha.update(data)
                md5.update(data)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or size != before.st_size:
            raise ArchiveError('Source changed during hashing')
        return {'bytes': size, 'sha256': sha.hexdigest(), 'md5': md5.hexdigest()}
    finally:
        os.close(fd)


def check_expected(row, actual):
    if not re.fullmatch('[a-f0-9]{64}', row.get('sha256', '')):
        raise ArchiveError('A full expected source SHA-256 is required')
    if actual['sha256'] != row['sha256'] or actual['bytes'] != row.get('bytes'):
        raise ArchiveError('Source size or SHA-256 differs from acquisition receipt')


def source_row(path, sha256, size, provider, practitioner, uploader, source_id, kind, provenance):
    return dict(local_path=str(path), sha256=sha256, bytes=size, provider=provider,
                practitioner=practitioner, uploader=uploader, source_id=source_id,
                kind=kind, provenance=provenance)


def artifact_path(r):
    if r.get('kind') not in KINDS:
        raise ArchiveError('Unknown artifact kind')
    if r['provider'] == 'youtube':
        if r.get('selection_eligible') is not True or r.get('is_short') is not False:
            raise ArchiveError('YouTube material needs explicit eligibility and non-Shorts verification')
        duration = r.get('duration_seconds')
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or duration < 300:
            raise ArchiveError('YouTube duration must be measured and at least 300 seconds')
        policy = r.get('selection_policy_receipt')
        if not isinstance(policy, dict) or set(policy) != {'path', 'sha256'}:
            raise ArchiveError('YouTube material needs a pinned selection policy receipt')
        rel = safe_relative(policy['path'])
        p = regular_source(REPO / rel, REPO)
        if p != REPO / 'research/collection-policy/selected-default.jsonl':
            raise ArchiveError('Only the default selected-ID policy receipt is supported')
        if hashlib.sha256(p.read_bytes()).hexdigest() != policy['sha256']:
            raise ArchiveError('YouTube policy receipt changed')
        records = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        matching = [row for row in records if row.get('source_id') == r['source_id']]
        if len(matching) != 1 or matching[0].get('selected_default') is not True:
            raise ArchiveError('YouTube artifact is not selected in the pinned default policy')
        if r.get('metadata_refreshed_at_acquisition') is not True:
            raise ArchiveError('YouTube metadata must be refreshed at acquisition, beyond inherited eligibility')
    identity = [safe_component(r[k]) for k in ('provider', 'practitioner', 'uploader', 'source_id')]
    filename = Path(r['local_path']).name
    if filename in {'', '.', '..'} or '/' in filename or '\\' in filename or any(ord(c) < 32 for c in filename):
        raise ArchiveError('Unsafe source basename')
    return safe_relative('/'.join(identity + [r['kind'], filename]))


def collect_existing(repo=REPO):
    """Adapt receipt-bound 19-episode cohort, separate Athina cohort, primary texts."""
    rows, identities = [], {}
    for filename, practitioner in [
        ('research/harvest/publisher_sources/publisher-summary.json', 'Darryl Anka'),
        ('research/access-repair/athina/publisher_sources/publisher-summary.json', 'Athina Król')]:
        summary = load_json(repo / filename)
        for r in summary['records']:
            if r.get('status') != 'completed':
                continue
            identity = dict(provider='publisher-rss', practitioner=practitioner,
                            uploader=r['publisher_name'], source_id=r['source_id'])
            identities[r['source_id']] = identity
            provenance = {'receipt': filename, 'source_kind': r['source_kind'],
                          'title': r['episode_title'], 'source_url': r['enclosure_url'],
                          'duration_seconds': r['duration_seconds'],
                          'youtube_edition_equivalence_verified': False,
                          'source_format': r.get('source_format', 'unverified'),
                          'speaker_identity_verified': False,
                          'redistribution_license': 'not_established'}
            rows.append(source_row(r['raw_local_path'], r['sha256'], r['bytes'],
                                   **identity, kind='audio', provenance=provenance))
    asr_records = load_json(repo / 'research/harvest/asr/summary.json')['records']
    asr_records.append(load_json(repo / 'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json'))
    for r in asr_records:
        if r.get('status') != 'completed':
            continue
        for output in r['outputs']:
            if Path(output['name']).name != output['name']:
                raise ArchiveError('ASR output name traversal')
            rows.append(source_row(Path(r['transcriptDirectory']) / output['name'],
                                   output['sha256'], output['bytes'], **identities[r['sourceId']],
                                   kind='transcript', provenance={
                                       'source_audio_sha256': r['sourceAudioSha256'],
                                       'asr_model': r['modelId'], 'asr_revision': r['modelRevision'],
                                       'scope': r['transcribedScope'], 'human_reviewed': False,
                                       'speaker_diarization_performed': False,
                                       'transcript_accuracy_verified': False}))
    filename = 'research/access-repair/primary-sources/expanded-metadata.json'
    expanded = load_json(repo / filename)
    for key, item, practitioner, uploader, kind in [
        ('response', expanded['paul'], 'Paul Selig', 'Paul Selig', 'source-document'),
        ('pdfinfo', expanded['paul'], 'Paul Selig', 'Paul Selig', 'source-metadata'),
        ('text', expanded['paul'], 'Paul Selig', 'Paul Selig', 'primary-text'),
        ('response', expanded['athina'], 'Athina Król', 'Spirit Channel with Athina Król', 'source-metadata')]:
        f = item[key]
        rows.append(source_row(f['raw_local_path'], f['sha256'], f['bytes'], 'publisher-web',
                               practitioner, uploader, item['source_id'], kind,
                               {'receipt': filename, 'source_url': item['requested_url'],
                                'scope': item.get('scope'), 'redistribution_license': 'not_established'}))
    for item in expanded['daniel']['items']:
        f = item['text']
        rows.append(source_row(f['raw_local_path'], f['sha256'], f['bytes'], 'publisher-rss',
                               'Daniel Scranton', 'Daniel Scranton', f"daniel-item-{item['item_index']:02d}",
                               'primary-text', {'receipt': filename, 'source_url': item['url'],
                                                'title': item['title'], 'scope': item['content_scope'],
                                                'redistribution_license': 'not_established'}))
    return rows


def build_plan(rows, raw_root=RAW_ROOT, archive_name=None):
    archive_name = archive_name or f'channels-ET-private-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}-{uuid.uuid4().hex[:10]}'
    if safe_relative(archive_name) != archive_name or '/' in archive_name:
        raise ArchiveError('Archive name must be one safe directory')
    files, aliases, seen_hashes, seen_paths = [], [], {}, set()
    for r in rows:
        rel = artifact_path(r)
        if rel in seen_paths:
            raise ArchiveError('Duplicate destination path; resolve acquisition identity explicitly')
        seen_paths.add(rel)
        actual = hash_source(r['local_path'], raw_root)
        check_expected(r, actual)
        row = {**r, **actual, 'relative_path': rel}
        if actual['sha256'] in seen_hashes:
            aliases.append({**row, 'canonical_relative_path': seen_hashes[actual['sha256']]})
        else:
            seen_hashes[actual['sha256']] = rel
            files.append(row)
    return {'schema_version': SCHEMA, 'planned_at': utc_now(), 'mode': 'offline_plan',
            'archive_name': archive_name, 'raw_root': str(raw_root),
            'user_reported_quota_tb': 5, 'quota_verified': False,
            'drive_folder_created': False, 'uploaded_files': 0,
            'privacy': 'planned My Drive root folder; no folder or permissions yet exist',
            'source_artifact_count': len(rows), 'canonical_file_count': len(files),
            'byte_identical_alias_count': len(aliases),
            'canonical_bytes': sum(r['bytes'] for r in files),
            'kinds': dict(collections.Counter(r['kind'] for r in files)),
            'files': files, 'byte_identical_aliases': aliases,
            'limits': ['Publisher and YouTube editions are not merged by titles or sessions.',
                       'Automatic transcripts retain unvalidated speaker and recognition status.',
                       'This plan has not checked a Drive account, quota, ACL or upload.']}


def validate_plan(plan):
    if plan.get('schema_version') != SCHEMA:
        raise ArchiveError('Unsupported plan schema')
    if Path(plan['raw_root']) != RAW_ROOT:
        raise ArchiveError('Plan raw root differs from the configured private raw root')
    if '/' in safe_relative(plan['archive_name']):
        raise ArchiveError('Unsafe archive name')
    seen = set()
    canonical = {}
    for r in plan['files']:
        rel = safe_relative(r['relative_path'])
        if rel != artifact_path(r):
            raise ArchiveError('Destination path differs from source identities')
        if rel in seen:
            raise ArchiveError('Destination collision in plan')
        seen.add(rel)
        actual = hash_source(r['local_path'], plan['raw_root'])
        check_expected(r, actual)
        if actual['md5'] != r['md5']:
            raise ArchiveError('Local MD5 changed')
        if r['sha256'] in canonical:
            raise ArchiveError('Canonical plan contains duplicate source bytes')
        canonical[r['sha256']] = r
    if plan.get('canonical_bytes') != sum(r['bytes'] for r in plan['files']):
        raise ArchiveError('Plan byte total is inconsistent')
    aliases = plan.get('byte_identical_aliases', [])
    for alias in aliases:
        rel = safe_relative(alias['relative_path'])
        if rel != artifact_path(alias):
            raise ArchiveError('Alias path differs from source identities')
        if rel in seen:
            raise ArchiveError('Alias destination collision')
        seen.add(rel)
        source = canonical.get(alias['sha256'])
        if not source or source['relative_path'] != alias['canonical_relative_path'] or source['bytes'] != alias['bytes']:
            raise ArchiveError('Invalid byte-identical alias')
        actual = hash_source(alias['local_path'], plan['raw_root'])
        check_expected(alias, actual)
    if (plan.get('canonical_file_count') != len(plan['files']) or
        plan.get('byte_identical_alias_count') != len(aliases) or
        plan.get('source_artifact_count') != len(plan['files']) + len(aliases) or
        plan.get('kinds') != dict(collections.Counter(r['kind'] for r in plan['files']))):
        raise ArchiveError('Plan artifact counts are inconsistent')
    return True


def safe_stage_write(stage, relative, data):
    target = stage / safe_relative(relative)
    for parent in [*reversed(target.parent.parents), target.parent]:
        if parent.is_symlink():
            raise ArchiveError('Staging symlink rejected before write')
        parent.mkdir(exist_ok=True)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError:
        regular_source(target, stage)
        if target.read_bytes() != data:
            raise ArchiveError('Existing staged metadata differs; choose a new staging directory')
    else:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
    return target


def stage_destination(plan, stage_root):
    stage_root = absolute_local_path(stage_root)
    if within(stage_root, RAW_ROOT) and not within(stage_root, RAW_ROOT / 'drive-staging'):
        raise ArchiveError('Staging inside the raw tree requires dedicated drive-staging storage')
    if overlap(stage_root, RAW_ROOT / 'drive-receipts'):
        raise ArchiveError('Staging must not overlap the dedicated receipt directory')
    source_paths = [Path(r['local_path']) for r in plan['files'] + plan.get('byte_identical_aliases', [])]
    if any(overlap(stage_root, source) for source in source_paths):
        raise ArchiveError('Staging must not overlap source artifacts')
    stage = stage_root / plan['archive_name']
    inspect_output_ancestors(stage)
    try:
        info = stage.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ArchiveError('Staging must be a real directory, never a symlink or file')
    return stage


def stage_manifests(plan, stage_root):
    """Only metadata is staged; full source bytes stay under the raw root."""
    validate_plan(plan)
    stage = stage_destination(plan, stage_root)
    if not stage.is_absolute() or '..' in stage.parts:
        raise ArchiveError('Staging directory must be an absolute path without traversal')
    # Validate before mkdir/write, including a symlink in a not-yet-existing subtree.
    for parent in [*reversed(stage.parents), stage]:
        if parent.is_symlink():
            raise ArchiveError('Staging symlink rejected')
        parent.mkdir(exist_ok=True)
    uploads = []
    for r in plan['files']:
        rel = r['relative_path'] + '.provenance.json'
        sidecar = {k: v for k, v in r.items() if k != 'local_path'}
        sidecar['schema_version'] = SCHEMA
        target = safe_stage_write(stage, rel, (json.dumps(sidecar, indent=2, ensure_ascii=False) + '\n').encode())
        uploads.append({'local_path': str(target), 'relative_path': rel, **hash_source(target, stage)})
    manifest = {'schema_version': SCHEMA, 'archive_name': plan['archive_name'],
                'plan_sha256': digest_json(plan), 'source_artifact_count': plan['source_artifact_count'],
                'files': [{k: v for k, v in r.items() if k != 'local_path'} for r in plan['files']],
                'byte_identical_aliases': [{k: v for k, v in a.items() if k != 'local_path'}
                                          for a in plan['byte_identical_aliases']],
                'checksum_note': 'Local SHA-256 records source provenance; remote MD5 plus size verifies transfer.'}
    for name, value in [('manifests/archive-manifest.json', manifest)]:
        p = safe_stage_write(stage, name, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())
        uploads.append({'local_path': str(p), 'relative_path': name, **hash_source(p, stage)})
    checksum_path = safe_stage_write(stage, 'manifests/SHA256SUMS',
                                    ''.join(f"{r['sha256']}  {r['relative_path']}\n" for r in plan['files'] + uploads).encode())
    uploads.append({'local_path': str(checksum_path), 'relative_path': 'manifests/SHA256SUMS',
                    **hash_source(checksum_path, stage)})
    return stage, uploads


def run_rclone(args):
    # Inherit proxy and CA environment. Never print credentials or raw error text.
    return subprocess.run(['rclone', *args], capture_output=True, text=True, check=False, timeout=360)


def existing_drive_remote(remote, runner=run_rclone):
    if not isinstance(remote, str) or not re.fullmatch('[A-Za-z0-9_-]+', remote):
        raise ArchiveError('Select a literal existing remote name without a colon or path')
    result = runner(['listremotes', '--long'])
    if result.returncode:
        raise ArchiveError(f'rclone remote enumeration failed (exit {result.returncode})')
    remotes = {}
    for line in result.stdout.splitlines():
        match = re.fullmatch(r'([^\s:]+):\s+(\S+)\s*', line)
        if match:
            remotes[match[1]] = match[2]
    if remote not in remotes:
        raise ArchiveError('No explicitly selected authorized remote exists; nothing was uploaded')
    if remotes[remote] != 'drive':
        raise ArchiveError('Selected remote must be a direct Google Drive remote, not an alias')
    return remote + ':'


def remote_status(remote, runner=run_rclone):
    root = existing_drive_remote(remote, runner)
    result = runner(['about', root, '--json', *DRIVE_FLAGS])
    if result.returncode:
        raise ArchiveError(f'Authenticated Drive quota check failed (exit {result.returncode}); no upload')
    quota = json.loads(result.stdout)
    return {'checked_at': utc_now(), 'remote': remote, 'authenticated_quota_read': True,
            'user_reported_quota_tb': 5, 'quota': quota,
            'reported_5tb_verified': isinstance(quota.get('total'), int) and quota['total'] >= 5_000_000_000_000,
            'drive_folder_created': False, 'uploaded_files': 0}


def remote_listing(path, runner=run_rclone, missing_ok=False):
    result = runner(['lsjson', path, '--hash', '--hash-type=MD5', '--no-modtime', '--no-mimetype', *DRIVE_FLAGS])
    # rclone's defined exit 3 is directory-not-found, never an auth/network fallback.
    if missing_ok and result.returncode == 3:
        return None
    if result.returncode:
        raise ArchiveError(f'Drive listing failed (exit {result.returncode}); stopping without retries')
    rows = json.loads(result.stdout)
    if not isinstance(rows, list):
        raise ArchiveError('Unexpected Drive directory listing schema')
    names = collections.Counter(r['Name'] for r in rows)
    if any(count > 1 for count in names.values()):
        raise ArchiveError('Duplicate Drive names detected; no automatic deduplication or overwrite')
    return rows


def remote_file(path, expected, runner=run_rclone):
    parent, name = path.rsplit('/', 1)
    listing = remote_listing(parent, runner, missing_ok=True)
    if listing is None:
        return False
    matches = [r for r in listing if r['Name'] == name]
    if not matches:
        return False
    row = matches[0]
    if row.get('IsDir') or row.get('Size') != expected['bytes'] or row.get('Hashes', {}).get('MD5', '').lower() != expected['md5']:
        raise ArchiveError('Drive destination exists with different or unavailable size/MD5; no overwrite')
    return True


def transfer_one(row, source_root, destination, runner=run_rclone):
    before = hash_source(row['local_path'], source_root)
    check_expected(row, before)
    if before['md5'] != row['md5']:
        raise ArchiveError('Source MD5 changed before transfer')
    if remote_file(destination, row, runner):
        return 'verified_existing'
    result = runner(['copyto', row['local_path'], destination, '--immutable', '--checksum',
                     '--no-update-modtime', '--transfers=1', '--checkers=1', *DRIVE_FLAGS])
    if result.returncode:
        raise ArchiveError(f'Drive copy failed (exit {result.returncode}); partial remote artifact may remain')
    if hash_source(row['local_path'], source_root) != before:
        raise ArchiveError('Source changed during transfer; remote result requires inspection')
    if not remote_file(destination, row, runner):
        raise ArchiveError('Post-copy Drive artifact is missing')
    return 'uploaded_size_md5_verified'


def upload(plan, remote, stage_root, private_root_confirmed=False, runner=run_rclone, receipt_path=None):
    if not private_root_confirmed:
        raise ArchiveError('Explicit confirmation of the selected user account/My Drive archive destination is required')
    validate_plan(plan)
    if receipt_path is None:
        raise ArchiveError('A new dedicated receipt output is required before any Drive request')
    stage_destination(plan, stage_root)
    sources = [r['local_path'] for r in plan['files'] + plan.get('byte_identical_aliases', [])]
    receipt_path = output_path(receipt_path, 'receipt', stage_root=stage_root, source_paths=sources)
    receipt = {'schema_version': SCHEMA, 'started_at': utc_now(), 'plan_sha256': digest_json(plan),
               'remote': remote, 'archive_name': plan['archive_name'], 'quota_at_start': None,
               'folder_creation_attempted': False, 'drive_folder_created': False,
               'uploaded_files': 0, 'verified_existing_files': 0, 'attempted_files': 0,
               'unverified_remote_state_possible': False,
               'privacy': 'New My Drive root folder; sharing never requested. Effective ACL not independently audited.',
               'effective_acl_verified': False, 'records': [], 'status': 'preflight'}
    with OwnedJsonOutput(receipt_path, 'receipt', stage_root=stage_root, source_paths=sources) as output:
        output.update(receipt)
        try:
            status = remote_status(remote, runner)
            receipt['quota_at_start'] = status['quota']
            stage, sidecars = stage_manifests(plan, stage_root)
            total = plan['canonical_bytes'] + sum(r['bytes'] for r in sidecars)
            if not isinstance(status['quota'].get('free'), int) or status['quota']['free'] < total:
                raise ArchiveError('Authenticated free quota is unknown or insufficient; no folder created')
            root = remote + ':'
            listing = remote_listing(root, runner)
            if any(r['Name'] == plan['archive_name'] for r in listing):
                raise ArchiveError('Archive root already exists; choose a new offline plan, never merge or overwrite')
            receipt['status'] = 'running'
            receipt['folder_creation_attempted'] = True
            receipt['unverified_remote_state_possible'] = True
            output.update(receipt)
            result = runner(['mkdir', root + plan['archive_name'], *DRIVE_FLAGS])
            if result.returncode:
                raise ArchiveError(f'Archive mkdir failed (exit {result.returncode}); inspect remote before retry')
            receipt['drive_folder_created'] = True
            receipt['unverified_remote_state_possible'] = False
            output.update(receipt)
            # Sequential transfers limit Drive requests; source acquisition can run independently.
            for row in [*plan['files'], *sidecars]:
                destination = root + plan['archive_name'] + '/' + safe_relative(row['relative_path'])
                source_root = stage if row in sidecars else Path(plan['raw_root'])
                receipt['attempted_files'] += 1
                receipt['unverified_remote_state_possible'] = True
                record = {'relative_path': row['relative_path'], 'bytes': row['bytes'],
                          'sha256': row['sha256'], 'md5': row['md5'], 'status': 'attempt_started_remote_state_unknown'}
                receipt['records'].append(record)
                output.update(receipt)
                outcome = transfer_one(row, source_root, destination, runner)
                key = 'uploaded_files' if outcome.startswith('uploaded') else 'verified_existing_files'
                receipt[key] += 1
                record['status'] = outcome
                receipt['unverified_remote_state_possible'] = False
                output.update(receipt)
            receipt['status'] = 'completed'
        except (ArchiveError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            receipt['status'] = 'failed_no_rollback'
            receipt['error'] = str(exc) if isinstance(exc, ArchiveError) else type(exc).__name__
            raise
        finally:
            receipt['finished_at'] = utc_now()
            output.update(receipt)
    return receipt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    planp = sub.add_parser('plan', help='Offline plan from current private source files; no network')
    planp.add_argument('--output', type=Path, required=True)
    planp.add_argument('--additional-artifacts', type=Path)
    planp.add_argument('--archive-name')
    verifyp = sub.add_parser('verify-plan', help='Rehash all sources offline')
    verifyp.add_argument('plan', type=Path)
    statusp = sub.add_parser('status', help='Read quota using an explicit already authorized remote')
    statusp.add_argument('--remote', required=True)
    upp = sub.add_parser('upload', help='Create one new My Drive archive; no overwrite/delete/share')
    upp.add_argument('plan', type=Path)
    upp.add_argument('--remote', required=True)
    upp.add_argument('--stage-root', type=Path, default=RAW_ROOT / 'drive-staging')
    upp.add_argument('--receipt', type=Path, required=True)
    upp.add_argument('--private-mydrive-root-confirmed', action='store_true')
    args = p.parse_args(argv)
    try:
        if args.command == 'plan':
            output_path(args.output, 'plan')
            rows = collect_existing()
            if args.additional_artifacts:
                rows.extend(load_json(args.additional_artifacts)['artifacts'])
            plan = build_plan(rows, archive_name=args.archive_name)
            write_new_json(args.output, plan)
            print(json.dumps({k: v for k, v in plan.items() if k not in {'files', 'byte_identical_aliases'}}, indent=2))
        elif args.command == 'verify-plan':
            plan = load_json(args.plan)
            validate_plan(plan)
            print(json.dumps({'status': 'all_local_sources_rehashed', 'files': len(plan['files']), 'network_requests': 0}))
        elif args.command == 'status':
            print(json.dumps(remote_status(args.remote), indent=2))
        else:
            result = upload(load_json(args.plan), args.remote, args.stage_root,
                            args.private_mydrive_root_confirmed, receipt_path=args.receipt)
            print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))
        return 0
    except (ArchiveError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'stopped', 'reason': str(exc) if isinstance(exc, ArchiveError) else type(exc).__name__,
                          'no_automatic_retry': True}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
