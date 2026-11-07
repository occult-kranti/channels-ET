#!/usr/bin/env python3
"""Explicit batch archives with hash-bound, file-level Google Drive resume.

No OAuth discovery, credentials, sharing, deletion, sync, or automatic cleanup.
The caller verifies media/ASR provenance; this module verifies retained bytes.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import html
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import uuid
from urllib.parse import quote, urlsplit

SPEC = importlib.util.spec_from_file_location('batch_archive_guards', Path(__file__).resolve().parents[1] / 'storage-drive/archive.py')
guards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guards)
LOCAL_SPEC = importlib.util.spec_from_file_location('batch_local_copy_guards', Path(__file__).resolve().parents[1] / 'cloud-archive/archive_local.py')
local_guards = importlib.util.module_from_spec(LOCAL_SPEC)
LOCAL_SPEC.loader.exec_module(local_guards)
ArchiveError = guards.ArchiveError
RAW_ROOT = guards.RAW_ROOT
PRIVATE_ROOT = Path('/workspace/channels-et-private')
KINDS = {'video', 'audio', 'caption', 'transcript', 'analysis', 'source-metadata', 'reference_document', 'reference_text'}
PROVIDERS = {'youtube', 'publisher_rss', 'publisher_video', 'publisher_reference', 'derived_analysis'}
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024 * 1024
MAX_FILES = 10000
HASH = re.compile(r'[a-f0-9]{64}')
FOLDER_ID = re.compile(r'[A-Za-z0-9_-]{3,256}')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path, roots=None):
    path = Path(path)
    if roots is not None:
        root = next((r for r in roots if guards.within(path, r)), None)
        if root is None:
            raise ArchiveError('Verification receipt is outside approved private roots')
        guards.regular_source(path, root)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ArchiveError('JSON input exceeds 8 MiB')
    value = json.loads(path.read_bytes())
    # Reject nonfinite caller values rather than serializing nonstandard JSON.
    json.dumps(value, allow_nan=False)
    return value


def integer(value, positive=False):
    return isinstance(value, int) and not isinstance(value, bool) and value >= (1 if positive else 0)


def source_root_for(path):
    path = Path(path)
    root = next((r for r in [RAW_ROOT, PRIVATE_ROOT] if guards.within(path, r)), None)
    if root is None:
        raise ArchiveError('Source is outside approved raw/private storage roots')
    return root


def storage_used_bytes():
    """Both approved trees, logical regular-file bytes, unique physical inodes."""
    total, seen = 0, set()
    for root in [RAW_ROOT, PRIVATE_ROOT]:
        local_guards.check_directory(root)
        for folder_path, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories if not (Path(folder_path) / name).is_symlink()]
            for name in files:
                info = (Path(folder_path) / name).lstat()
                identity = (info.st_dev, info.st_ino)
                if stat.S_ISREG(info.st_mode) and identity not in seen:
                    seen.add(identity)
                    total += info.st_size
    return total


def receipt_snapshot(path, include_bytes=False):
    """Read/hash one bounded nonsymlink receipt snapshot, never credentials."""
    path = Path(path)
    guards.inspect_output_ancestors(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_JSON_BYTES:
            raise ArchiveError('Receipt must be one bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_JSON_BYTES + 1)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size) or len(data) != before.st_size:
            raise ArchiveError('Receipt changed while reading')
        value = json.loads(data)
        json.dumps(value, allow_nan=False)
        result = (value, hashlib.sha256(data).hexdigest())
        return (*result, data) if include_bytes else result
    finally:
        os.close(fd)


def verify_artifact(item):
    if not isinstance(item, dict) or item.get('provider') not in PROVIDERS or item.get('kind') not in KINDS:
        raise ArchiveError('Unsupported artifact provider or kind')
    for key in ['medium_id', 'channel_id', 'source_id']:
        guards.safe_component(item.get(key))
    if not integer(item.get('bytes')) or not isinstance(item.get('sha256'), str) or not HASH.fullmatch(item['sha256']):
        raise ArchiveError('Artifact requires exact bytes and SHA-256')
    source_root = source_root_for(item['local_path'])
    initial = Path(item['local_path']).stat(follow_symlinks=False)
    actual = guards.hash_source(item['local_path'], source_root)
    final = Path(item['local_path']).stat(follow_symlinks=False)
    source_state = {'device': initial.st_dev, 'inode': initial.st_ino, 'mtime_ns': initial.st_mtime_ns, 'bytes': initial.st_size}
    if source_state != {'device': final.st_dev, 'inode': final.st_ino, 'mtime_ns': final.st_mtime_ns, 'bytes': final.st_size}:
        raise ArchiveError('Source identity changed during verification')
    guards.check_expected(item, actual)
    proof = item.get('verification_receipt')
    if not isinstance(proof, dict) or set(proof) != {'path', 'sha256'} or not HASH.fullmatch(str(proof.get('sha256', ''))):
        raise ArchiveError('Artifact requires a hash-bound verification receipt')
    proof_path = Path(proof['path'])
    proof_root = next((r for r in [RAW_ROOT, PRIVATE_ROOT] if guards.within(proof_path, r)), None)
    if proof_root is None:
        raise ArchiveError('Verification receipt is outside approved private roots')
    before = guards.hash_source(proof_path, proof_root)
    if before['sha256'] != proof['sha256']:
        raise ArchiveError('Verification receipt hash mismatch')
    value = load_json(proof_path, [proof_root])
    entries = value.get('verified_artifacts') if isinstance(value, dict) else None
    expected = {k: item[k] for k in ['local_path', 'sha256', 'bytes', 'source_id', 'kind']}
    matching = [r for r in entries or [] if isinstance(r, dict) and all(r.get(k) == v for k, v in expected.items())]
    if len(matching) != 1 or matching[0].get('status') != 'verified':
        raise ArchiveError('Verification receipt must uniquely bind a verified artifact')
    bound = matching[0]
    for key in ['provider', 'medium_id', 'channel_id']:
        if key in bound and bound[key] != item[key]:
            raise ArchiveError('Artifact identity conflicts with its verification receipt')
    if guards.hash_source(proof_path, proof_root) != before:
        raise ArchiveError('Verification receipt changed while being inspected')
    if item['provider'] == 'youtube':
        if not re.fullmatch(r'youtube:[A-Za-z0-9_-]{11}', item['source_id']):
            raise ArchiveError('YouTube source ID must identify one video')
        duration = item.get('duration_seconds')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 300:
            raise ArchiveError('YouTube source duration must be at least 300 seconds')
        if item.get('duration_scope') != 'source_video' or item.get('is_short') is not False or item.get('metadata_refreshed_at_acquisition') is not True:
            raise ArchiveError('YouTube source metadata and non-Shorts verification are required')
        # Selection/identity eligibility is a collector responsibility; this is
        # not an independent recrawl or a claim about the speaker's identity.
    row = {k: item[k] for k in ['local_path', 'provider', 'medium_id', 'channel_id', 'source_id', 'kind']}
    row.update(actual, source_root=str(source_root), source_state=source_state, verification_receipt=dict(proof))
    # Preserve attribution qualifications from the hash-bound proof, not from
    # arbitrary caller overrides. A context label is not a verified speaker.
    provenance_keys = ['title', 'channel', 'published_date', 'source_url', 'context_associations',
                       'medium_assignment_basis', 'actual_speaker_status', 'attribution_status',
                       'claimed_entity_label', 'youtube_edition_identity', 'acquisition_validated_at',
                       'acquisition_proof_basis', 'source_classification_at_acquisition', 'original_status',
                       'validation', 'model', 'model_id', 'model_revision', 'human_reviewed',
                       'transcript_accuracy_verified', 'source_audio_sha256', 'source_video_sha256',
                       'license', 'license_summary', 'rights_basis', 'scope', 'limitations',
                       'parent_source_ids', 'input_source_ids', 'input_receipts', 'derivation',
                       'analysis_method', 'methods', 'reading_coverage', 'source_verification']
    row['bound_provenance'] = {k: bound[k] for k in provenance_keys if k in bound}
    row['attribution_scope'] = ('Receipt-bound publisher/context labels; not independent speaker or claimed-entity verification.'
                                if all(k in bound for k in ['provider', 'medium_id', 'channel_id']) else
                                'Caller-supplied organization labels; identity is not established by the byte-verification receipt.')
    for key in ['duration_seconds', 'duration_scope', 'is_short', 'metadata_refreshed_at_acquisition']:
        if key in item:
            row[key] = item[key]
    basename = Path(item['local_path']).name
    guards.safe_relative(basename)
    row['relative_path'] = '/'.join([guards.safe_component(row[k]) for k in ['provider', 'medium_id', 'channel_id', 'source_id']] + [row['kind'], basename])
    guards.safe_relative(row['relative_path'])
    return row


def build_plan(manifest, archive_name=None):
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ArchiveError('Unsupported batch manifest')
    batch_id = manifest.get('batch_id')
    if not isinstance(batch_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', batch_id):
        raise ArchiveError('A bounded batch ID is required')
    artifacts = manifest.get('artifacts')
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_FILES:
        raise ArchiveError('An explicit nonempty batch of at most 10000 artifacts is required')
    rows = [verify_artifact(item) for item in artifacts]
    if len({r['relative_path'] for r in rows}) != len(rows):
        raise ArchiveError('Duplicate archive destinations')
    archive_name = archive_name or f'channels-ET-{batch_id}-{uuid.uuid4().hex[:10]}'
    if '/' in guards.safe_relative(archive_name):
        raise ArchiveError('Archive name must be one safe directory')
    return {'schema_version': 1, 'kind': 'explicit-batch-archive-plan', 'batch_id': batch_id,
            'archive_name': archive_name, 'raw_root': str(RAW_ROOT), 'private_root': str(PRIVATE_ROOT), 'files': rows,
            'file_count': len(rows), 'source_bytes': sum(r['bytes'] for r in rows),
            'scope': 'Explicit retained artifacts only. Byte integrity and supplied verification receipts are checked; media decoding, ASR accuracy, speaker identity and selection completeness are not independently established here.'}


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get('kind') != 'explicit-batch-archive-plan' or plan.get('raw_root') != str(RAW_ROOT) or plan.get('private_root') != str(PRIVATE_ROOT):
        raise ArchiveError('Unsupported or incorrectly rooted batch plan')
    rebuilt = build_plan({'schema_version': plan.get('schema_version'), 'batch_id': plan.get('batch_id'), 'artifacts': plan.get('files')}, plan.get('archive_name'))
    if rebuilt != plan:
        raise ArchiveError('Plan contents or source integrity changed')
    return True


def archive_index(plan):
    """A local-only index computed from the plan, with no receipt/hash cycle."""
    labels = {'youtube': 'YouTube', 'publisher_video': 'Publisher video · not YouTube',
              'publisher_rss': 'Publisher audio / RSS', 'publisher_reference': 'Publisher reference',
              'derived_analysis': 'Derived corpus analysis'}
    kinds = {'video': 'Video', 'audio': 'Audio', 'transcript': 'Machine transcript · unreviewed',
             'caption': 'Caption', 'reference_document': 'Publisher reference PDF',
             'reference_text': 'Extracted publisher text', 'analysis': 'Analysis', 'source-metadata': 'Metadata'}
    groups = {}
    for row in plan['files']:
        groups.setdefault(row['source_id'], []).append(row)
    cards = []
    for source_id, rows in groups.items():
        title = next((r['bound_provenance'].get('title') for r in rows if r['bound_provenance'].get('title')), source_id)
        title = html.escape(str(title)[:280])
        origins = ' · '.join(sorted({labels[r['provider']] for r in rows}))
        trs = []
        for row in rows:
            url = quote(row['relative_path'], safe='/')
            proof = 'manifests/verification/' + row['verification_receipt']['sha256'] + '.json'
            filename = html.escape(Path(row['local_path']).name)
            trs.append(f'<tr><th scope="row">{html.escape(kinds[row["kind"]])}</th><td><a href="{url}">{filename}</a></td>'
                       f'<td>{row["bytes"]:,}</td><td><a href="{proof}">Verification record</a><br><code>{row["sha256"][:16]}…</code></td></tr>')
        source_link = ''
        candidate = next((r['bound_provenance'].get('source_url') for r in rows if r['bound_provenance'].get('source_url')), None)
        if isinstance(candidate, str):
            parsed = urlsplit(candidate)
            if parsed.scheme in {'https', 'http'} and parsed.netloc and not parsed.username and not parsed.password:
                source_link = f'<p><a href="{html.escape(candidate, quote=True)}" target="_blank" rel="noopener noreferrer">Open original source online</a></p>'
        cards.append(f'<section><h2>{title}</h2><p class="source">{html.escape(source_id)}<br>{html.escape(origins)}</p>{source_link}'
                     '<div class="scroll"><table><thead><tr><th>Type</th><th>Open local file</th><th>Bytes</th><th>Provenance</th></tr></thead>'
                     '<tbody>' + ''.join(trs) + '</tbody></table></div></section>')
    counts = {k: sum(r['kind'] == k for r in plan['files']) for k in KINDS}
    summary = f'{counts["video"]} videos · {counts["reference_document"]} reference documents · {counts["transcript"]} transcript files · {len(plan["files"])} source artifacts'
    text = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' \
        '<title>Channels ET · Private media archive</title><style>' \
        ':root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#090c10;color:#e6edf5;font:16px/1.55 system-ui,sans-serif}' \
        'main{max-width:1180px;margin:auto;padding:clamp(18px,4vw,48px)}h1{font-size:clamp(28px,5vw,46px);line-height:1.15}h2{font-size:22px}' \
        'a{color:#83e8d1;text-underline-offset:3px}a:focus-visible{outline:3px solid #ffd58b;outline-offset:4px}' \
        '.eyebrow{letter-spacing:.15em;color:#83e8d1;font-size:13px}.note,section{border:1px solid #354052;background:#111720;border-radius:14px;padding:22px;margin:22px 0}' \
        '.source{color:#aebbd0;overflow-wrap:anywhere}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;min-width:640px}' \
        'th,td{text-align:left;padding:13px 12px;border-bottom:1px solid #303b4c;vertical-align:top}th{font-weight:600}code{color:#b7c4d7;font-size:12px}' \
        '</style></head><body><main><p class="eyebrow">CHANNELS ET / PRIVATE LOCAL ARCHIVE</p><h1>Recordings, transcripts &amp; source evidence</h1>' \
        f'<p>{html.escape(summary)}</p><p class="source">Batch: {html.escape(plan["batch_id"])} · {plan["source_bytes"]:,} logical source bytes</p>' \
        '<aside class="note"><strong>Open this index from the complete archive folder.</strong> Links below point to local files; a text-only bundle will not contain every media target. ' \
        'There are no automatic external requests or embedded players. Source links open online only when clicked.<br><br>' \
        'This archive is managed-cloud filesystem storage, not guaranteed permanent ChatGPT-account storage or Drive. Explicit hardlink mode may share original media inodes; ' \
        'later in-place source edits affect those paths too. The external transfer receipt states the actual storage mode. ' \
        'Machine transcripts and derived readings remain unreviewed; publisher labels do not establish speaker or claimed-entity identity.</aside>' \
        '<p><a href="manifests/archive-manifest.json">Complete source manifest</a> · <a href="manifests/SHA256SUMS">SHA-256 checksums</a></p>' \
        ''.join(cards) + '</main></body></html>\n'
    return text.encode()


def metadata_payloads(plan):
    """Calculate exact metadata bytes before disk mutations or budget checks."""
    output = []
    projections = []
    proofs = {}
    total = 0
    def add(relative, payload):
        nonlocal total
        total += len(payload)
        if total > MAX_METADATA_BYTES:
            raise ArchiveError('Batch archival metadata exceeds 64 MiB; split the explicit batch')
        output.append({'relative_path': relative, 'payload': payload, 'bytes': len(payload),
                       'sha256': hashlib.sha256(payload).hexdigest(), 'md5': hashlib.md5(payload, usedforsecurity=False).hexdigest()})
    for row in plan['files']:
        projected = {k: v for k, v in row.items() if k not in {'local_path', 'source_root', 'verification_receipt'}}
        projected['verification_receipt_sha256'] = row['verification_receipt']['sha256']
        projected['verification_receipt_archive_path'] = 'manifests/verification/' + row['verification_receipt']['sha256'] + '.json'
        projections.append(projected)
        # Disjoint namespace prevents a source named x.provenance.json from
        # colliding with generated provenance for another source named x.
        relative = 'manifests/provenance/' + row['relative_path'] + '.json'
        add(relative, (json.dumps(projected, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        reference = row['verification_receipt']
        if reference['sha256'] not in proofs:
            _, digest, original = receipt_snapshot(reference['path'], include_bytes=True)
            if digest != reference['sha256']:
                raise ArchiveError('Verification receipt changed before archival staging')
            proofs[digest] = original
    for digest, original in proofs.items():
        add('manifests/verification/' + digest + '.json', original)
    add('index.html', archive_index(plan))
    public_manifest = {'schema_version': 1, 'batch_id': plan['batch_id'], 'plan_sha256': guards.digest_json(plan), 'files': projections,
                       'scope': 'Private archive provenance; supplied verification receipts are hash-bound, not a claim of human-reviewed transcripts.'}
    add('manifests/archive-manifest.json', (json.dumps(public_manifest, sort_keys=True, indent=2) + '\n').encode())
    checksums = ''.join(f"{r['sha256']}  {r['relative_path']}\n" for r in [*plan['files'], *output])
    add('manifests/SHA256SUMS', checksums.encode())
    return output


def stage_metadata(plan, stage_root, *, budget=None, reserve=0):
    # Reuse exclusive/no-follow staging, but never import the old implicit
    # ninety-nine-object cohort or its historical selected-ID policy.
    stage = guards.stage_destination({'archive_name': plan['archive_name'], 'files': plan['files']}, Path(stage_root))
    guards.inspect_output_ancestors(stage / 'placeholder')
    payloads = metadata_payloads(plan)
    missing = 0
    for row in payloads:
        p = stage / row['relative_path']
        if p.exists() or p.is_symlink():
            actual = guards.hash_source(p, stage)
            if actual != {k: row[k] for k in ['bytes', 'sha256', 'md5']}:
                raise ArchiveError('Existing staged metadata differs from the bound plan')
        else:
            missing += row['bytes']
    if budget is not None and (storage_used_bytes() + missing > budget or shutil.disk_usage(RAW_ROOT).free < missing + reserve):
        raise ArchiveError('Storage budget or free-space reserve prevents metadata staging')
    stage.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = []
    for row in payloads:
        p = guards.safe_stage_write(stage, row['relative_path'], row['payload'])
        actual = guards.hash_source(p, stage)
        if actual != {k: row[k] for k in ['bytes', 'sha256', 'md5']}:
            raise ArchiveError('Staged metadata bytes differ from the plan')
        output.append({'local_path': str(p), 'relative_path': row['relative_path'], **actual})
    return stage, output


def scoped_runner(runner, folder_id):
    if not isinstance(folder_id, str) or not FOLDER_ID.fullmatch(folder_id):
        raise ArchiveError('Missing or invalid Drive folder ID')
    def run(args):
        return runner([f'--drive-root-folder-id={folder_id}' if arg.startswith('--drive-root-folder-id=') else arg for arg in args])
    return run


@contextlib.contextmanager
def remote_lock(remote, lock_root):
    # Serializes local processes, not other machines or Drive editors.
    if not re.fullmatch(r'[A-Za-z0-9_-]+', remote):
        raise ArchiveError('Select a literal existing remote name')
    lock_root = Path(lock_root)
    guards.inspect_output_ancestors(lock_root / 'placeholder')
    lock_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = lock_root / ('drive-' + hashlib.sha256(remote.encode()).hexdigest() + '.lock')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ArchiveError('Unsafe local lock file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ArchiveError('Another local upload owns this remote lock') from exc
        yield
    finally:
        os.close(fd)


def folder(listing, name):
    matches = [r for r in listing if r.get('Name') == name]
    if len(matches) > 1:
        raise ArchiveError('Ambiguous duplicate Drive folder names')
    if not matches:
        return None
    row = matches[0]
    if row.get('IsDir') is not True or not FOLDER_ID.fullmatch(str(row.get('ID', ''))):
        raise ArchiveError('Drive parent is not an identifiable folder')
    return row['ID']


def upload(plan, remote, receipt_path, stage_root, *, resume_from=None,
           private_root_confirmed=False, runner=guards.run_rclone, lock_root=None):
    if not private_root_confirmed:
        raise ArchiveError('Bind the intended authorized account and private My Drive root first')
    validate_plan(plan)
    source_paths = [r['local_path'] for r in plan['files']]
    source_paths += [r['verification_receipt']['path'] for r in plan['files']]
    guards.output_path(receipt_path, 'receipt', stage_root=stage_root, source_paths=source_paths)
    guards.stage_destination({'archive_name': plan['archive_name'], 'files': [{'local_path': p} for p in source_paths]}, Path(stage_root))
    prior = None
    prior_sha = None
    if resume_from is not None:
        prior_path = Path(resume_from)
        # A resume is a new, exclusively created receipt; never mutate history.
        if prior_path.is_symlink() or not prior_path.is_file() or prior_path.stat().st_nlink != 1:
            raise ArchiveError('Resume receipt must be one regular nonsymlink file')
        guards.inspect_output_ancestors(prior_path)
        prior, prior_sha = receipt_snapshot(prior_path)
        if (prior.get('kind') != 'batch-drive-transfer' or prior.get('schema_version') != 1 or
            prior.get('plan_sha256') != guards.digest_json(plan) or prior.get('remote') != remote or
            prior.get('archive_name') != plan['archive_name'] or not FOLDER_ID.fullmatch(str(prior.get('root_folder_id', '')))):
            raise ArchiveError('Resume receipt does not bind this plan, remote and created folder ID')
        if guards.overlap(Path(receipt_path), prior_path) or guards.overlap(Path(stage_root), prior_path):
            raise ArchiveError('Resume history overlaps a new output')
    receipt = {'schema_version': 1, 'kind': 'batch-drive-transfer', 'started_at': now(),
               'plan_sha256': guards.digest_json(plan), 'remote': remote, 'archive_name': plan['archive_name'],
               'root_folder_id': prior['root_folder_id'] if prior else None, 'prior_receipt_sha256': prior_sha,
               'status': 'preflight', 'records': [], 'directory_ids': {}, 'remote_mutation_attempts': 0,
               'uploaded_files': 0, 'verified_existing_files': 0, 'verified_bytes': 0,
               'unverified_remote_state_possible': bool(prior and prior.get('unverified_remote_state_possible')),
               'prior_unverified_remote_state_possible': bool(prior and prior.get('unverified_remote_state_possible')),
               'effective_acl_verified': False,
               'resume_scope': 'File-level verification/reuse; no cross-process byte-range resume, remote deletion or mismatch overwrite. Local lock does not exclude other Drive clients.'}
    lock_root = lock_root or RAW_ROOT / 'drive-receipts/.locks'
    with remote_lock(remote, lock_root), guards.OwnedJsonOutput(receipt_path, 'receipt', stage_root=stage_root, source_paths=source_paths) as out:
        out.update(receipt)
        try:
            status = guards.remote_status(remote, runner)
            free = status['quota'].get('free')
            if not integer(free):
                raise ArchiveError('Authenticated free quota must be a finite nonnegative integer')
            receipt['quota_at_start'] = status['quota']
            stage, metadata = stage_metadata(plan, stage_root)
            all_files = [*plan['files'], *metadata]
            listing = guards.remote_listing(remote + ':', runner)
            found = folder(listing, plan['archive_name'])
            if prior:
                if found != prior['root_folder_id']:
                    raise ArchiveError('Resume archive root ID/name changed or is missing')
            elif found:
                raise ArchiveError('Archive root already exists; use its matching receipt to resume')

            def mutate(args):
                receipt['remote_mutation_attempts'] += 1
                receipt['unverified_remote_state_possible'] = True
                out.update(receipt)
                result = runner(args)
                if result.returncode:
                    raise ArchiveError(f'Drive mutation failed (exit {result.returncode}); remote state requires inspection')

            if not prior:
                if free < sum(r['bytes'] for r in all_files):
                    raise ArchiveError('Authenticated free quota is insufficient for this complete batch')
                mutate(['mkdir', remote + ':' + plan['archive_name'], *guards.DRIVE_FLAGS])
                found = folder(guards.remote_listing(remote + ':', runner), plan['archive_name'])
                if not found:
                    raise ArchiveError('Created archive folder ID could not be verified')
                receipt['root_folder_id'] = found
                receipt['unverified_remote_state_possible'] = False
                out.update(receipt)

            def parent_id(relative, create):
                current = receipt['root_folder_id']
                segments = relative.split('/')[:-1]
                traversed = []
                for name in segments:
                    traversed.append(name)
                    prefix = '/'.join(traversed)
                    bound = scoped_runner(runner, current)
                    found_id = folder(guards.remote_listing(remote + ':', bound), name)
                    previous = (prior or {}).get('directory_ids', {}).get(prefix)
                    if previous is not None and found_id != previous:
                        raise ArchiveError('Previously bound parent folder ID changed or disappeared')
                    if found_id is None:
                        if not create:
                            return None
                        args = ['mkdir', remote + ':' + name, *guards.DRIVE_FLAGS]
                        args = [f'--drive-root-folder-id={current}' if a.startswith('--drive-root-folder-id=') else a for a in args]
                        mutate(args)
                        found_id = folder(guards.remote_listing(remote + ':', bound), name)
                        if found_id is None:
                            raise ArchiveError('Created parent folder ID could not be verified')
                        receipt['unverified_remote_state_possible'] = receipt['prior_unverified_remote_state_possible']
                    recorded = receipt['directory_ids'].get(prefix)
                    if recorded is not None and recorded != found_id:
                        raise ArchiveError('Parent folder changed during this run')
                    receipt['directory_ids'][prefix] = found_id
                    current = found_id
                return current

            # Determine remaining bytes from current remote hashes, not prior
            # counters. No nested directories are created during this preflight.
            needed = 0
            for row in all_files:
                pid = parent_id(row['relative_path'], False)
                exists = pid is not None and guards.remote_file(remote + ':/' + Path(row['relative_path']).name, row, scoped_runner(runner, pid))
                if not exists:
                    needed += row['bytes']
            if free < needed:
                raise ArchiveError('Authenticated free quota is insufficient for missing batch files')
            receipt['remaining_bytes_at_preflight'] = needed
            receipt['status'] = 'running'
            out.update(receipt)
            for row in all_files:
                pid = parent_id(row['relative_path'], True)
                bound = scoped_runner(runner, pid)
                record = {k: row[k] for k in ['relative_path', 'sha256', 'md5', 'bytes']}
                record['status'] = 'checking_remote'
                receipt['records'].append(record)
                out.update(receipt)

                def counted(args):
                    if args and args[0] == 'copyto':
                        receipt['remote_mutation_attempts'] += 1
                        receipt['unverified_remote_state_possible'] = True
                        record['status'] = 'copy_attempt_remote_state_unknown'
                        out.update(receipt)
                    return bound(args)

                source_root = stage if row in metadata else source_root_for(row['local_path'])
                outcome = guards.transfer_one(row, source_root, remote + ':/' + Path(row['relative_path']).name, counted)
                record['status'] = outcome
                receipt['uploaded_files' if outcome.startswith('uploaded') else 'verified_existing_files'] += 1
                receipt['verified_bytes'] += row['bytes']
                receipt['unverified_remote_state_possible'] = receipt['prior_unverified_remote_state_possible']
                out.update(receipt)
            receipt['status'] = 'completed'
            receipt['unverified_remote_state_possible'] = False
        except Exception as exc:
            receipt['status'] = 'failed_no_rollback'
            receipt['error'] = str(exc) if isinstance(exc, ArchiveError) else type(exc).__name__
            raise
        finally:
            receipt['finished_at'] = now()
            out.update(receipt)
    return receipt


def local_hardlink(row, archive_root):
    """Link one explicit source atomically; never allocate a copy as fallback."""
    source = guards.regular_source(row['source_path'], source_root_for(row['source_path']))
    target = archive_root / guards.safe_relative(row['relative_path'])
    local_guards.check_directory(target.parent, create=True)
    before = source.stat(follow_symlinks=False)
    if before.st_dev != archive_root.stat().st_dev:
        raise ArchiveError('Hardlink mode requires the same filesystem; no copy fallback')
    expected = {k: row[k] for k in ['bytes', 'sha256', 'md5']}
    if guards.hash_source(source, source_root_for(source)) != expected:
        raise ArchiveError('Source changed before hardlink creation')
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError as exc:
        raise ArchiveError('Hardlink destination already exists; no overwrite') from exc
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            raise ArchiveError('Hardlink mode requires the same filesystem; no copy fallback') from exc
        raise
    after = source.stat(follow_symlinks=False)
    linked = target.stat(follow_symlinks=False)
    if (not stat.S_ISREG(linked.st_mode) or linked.st_nlink < 2 or
        (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) !=
        (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size) or
        (linked.st_dev, linked.st_ino) != (before.st_dev, before.st_ino) or
        guards.hash_source(target, archive_root) != expected):
        raise ArchiveError('Source or linked bytes changed during hardlink creation; retained for inspection')
    return {k: v for k, v in row.items() if k != 'source_path'} | {
        'status': 'shared_inode_hash_verified', 'source_identity': [before.st_dev, before.st_ino],
        'shared_copy_semantics': 'Same file contents as the source; later in-place source edits also change this archive path.'}


def verify_local_tree(root, rows):
    """Verify the exact file set and each declared copy/link relationship."""
    local_guards.check_directory(root)
    expected = {r['relative_path']: r for r in rows}
    found = set()
    for directory, directories, names in os.walk(root, followlinks=False):
        for name in directories:
            local_guards.check_directory(Path(directory) / name)
        for name in names:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            row = expected.get(relative)
            if row is None:
                raise ArchiveError('Unexpected archive file or incomplete partial')
            actual = guards.hash_source(path, root)
            if actual != {k: row[k] for k in ['bytes', 'sha256', 'md5']}:
                raise ArchiveError('Archived bytes changed')
            source = Path(row['source_path']).stat(follow_symlinks=False)
            target = path.stat(follow_symlinks=False)
            same = (source.st_dev, source.st_ino) == (target.st_dev, target.st_ino)
            if row['storage_mode'] == 'hardlink':
                if not same or target.st_nlink < 2:
                    raise ArchiveError('Declared shared-inode relationship changed')
            elif same or target.st_nlink != 1:
                raise ArchiveError('Declared independent copy relationship changed')
            found.add(relative)
    if found != set(expected):
        raise ArchiveError('Archive is missing planned files')
    return {'files': len(found), 'logical_bytes': sum(r['bytes'] for r in rows), 'exact_file_set_verified': True}


def local_archive(plan, receipt_path, *, resume_from=None, budget=20 * 1024 ** 3,
                  reserve=6 * 1024 ** 3, archive_root=None, mode='copy'):
    """Organize a verified batch in private managed-cloud storage.

    Copy is the default; explicit hardlink mode shares source-file inodes.
    Completed files can be reused after an interrupted run. Unverified temporary
    files are preserved and stop automatic resume; no cleanup/delete is implied.
    """
    validate_plan(plan)
    if mode not in {'copy', 'hardlink'}:
        raise ArchiveError('Local archive mode must be copy or explicit hardlink')
    if not integer(budget, True) or not integer(reserve):
        raise ArchiveError('Archive budget and reserve must be nonnegative integer bytes')
    archive_parent = Path(archive_root) if archive_root is not None else RAW_ROOT / 'batch-archives'
    if archive_parent == RAW_ROOT or not guards.within(archive_parent, RAW_ROOT):
        raise ArchiveError('Local archive root must be inside the approved raw tree')
    final_root = archive_parent / plan['archive_name']
    partial_root = archive_parent / (plan['archive_name'] + '.partial')
    stage_root = RAW_ROOT / 'drive-staging'
    protected = [r['local_path'] for r in plan['files']] + [r['verification_receipt']['path'] for r in plan['files']]
    if any(guards.overlap(root, Path(source)) for root in [final_root, partial_root] for source in protected):
        raise ArchiveError('Archive destination overlaps a source or verification receipt')
    guards.output_path(receipt_path, 'receipt', stage_root=stage_root,
                       source_paths=[*protected, str(final_root), str(partial_root)])
    guards.stage_destination({'archive_name': plan['archive_name'], 'files': [{'local_path': p} for p in protected]}, stage_root)
    local_guards.check_directory(archive_parent)
    prior = None
    prior_sha = None
    if resume_from is not None:
        prior, prior_sha = receipt_snapshot(resume_from)
        if (prior.get('kind') != 'batch-local-archive' or prior.get('schema_version') != 1 or
            prior.get('plan_sha256') != guards.digest_json(plan) or prior.get('archive_name') != plan['archive_name'] or
            prior.get('mode', 'copy') != mode or
            prior.get('final_root') != str(final_root) or prior.get('partial_root') != str(partial_root) or
            not isinstance(prior.get('root_identity'), list) or len(prior['root_identity']) != 2):
            raise ArchiveError('Local resume receipt does not bind this plan and archive identity')
        if any(guards.overlap(Path(resume_from), p) for p in [Path(receipt_path), stage_root, final_root, partial_root]):
            raise ArchiveError('Resume receipt overlaps new outputs')
    receipt = {'schema_version': 1, 'kind': 'batch-local-archive', 'started_at': now(),
               'batch_id': plan['batch_id'], 'archive_name': plan['archive_name'], 'plan_sha256': guards.digest_json(plan),
               'prior_receipt_sha256': prior_sha, 'final_root': str(final_root), 'partial_root': str(partial_root),
               'root_identity': prior['root_identity'] if prior else None, 'status': 'preflight',
               'copied_files': 0, 'linked_files': 0, 'reused_files': 0, 'verified_bytes': 0, 'records': [],
               'mode': mode, 'new_unique_file_bytes': 0,
               'source_artifact_count': len(plan['files']), 'network_requests': 0,
               'storage_kind': 'managed_cloud_local_filesystem', 'drive_uploaded_files': 0,
               'retention_guaranteed': False, 'independent_copies': mode == 'copy',
               'shared_inode_semantics': ('Source artifacts share their original filesystem inode; later in-place edits change both paths. Metadata is independently copied. This is organized access, not an independent media backup.' if mode == 'hardlink' else None),
               'scope': 'Private workspace archive, not permanent ChatGPT-account storage or Drive. File-level resume only; partial/unexpected files are preserved and require inspection. No deletion or overwrite.'}
    try:
        with remote_lock('local-archive', PRIVATE_ROOT / 'batch-media-locks'), local_guards.worker_lock(RAW_ROOT), guards.OwnedJsonOutput(receipt_path, 'receipt', stage_root=stage_root, source_paths=protected) as out:
            out.update(receipt)
            try:
                free = shutil.disk_usage(RAW_ROOT).free
                if free < reserve:
                    raise ArchiveError('Free-space reserve prevents archive staging')
                stage, metadata = stage_metadata(plan, stage_root, budget=budget, reserve=reserve)
                all_files = [*plan['files'], *metadata]
                rows = [{'source_path': r['local_path'], 'storage_mode': ('hardlink' if mode == 'hardlink' and r in plan['files'] else 'copy'),
                         **{k: r[k] for k in ['relative_path', 'bytes', 'sha256', 'md5']}} for r in all_files]
                receipt['planned_files'] = len(rows)
                receipt['planned_bytes'] = sum(r['bytes'] for r in rows)
                receipt['raw_budget_bytes'] = budget
                receipt['free_space_reserve_bytes'] = reserve
                local_guards.check_directory(archive_parent, create=True)
                active = partial_root
                if prior:
                    candidates = [p for p in [partial_root, final_root] if p.exists() or p.is_symlink()]
                    if len(candidates) != 1:
                        raise ArchiveError('Resume needs exactly one bound partial or completed archive')
                    active = candidates[0]
                    local_guards.check_directory(active)
                    info = active.stat()
                    if [info.st_dev, info.st_ino] != prior['root_identity']:
                        raise ArchiveError('Local archive directory identity changed')
                else:
                    if partial_root.exists() or partial_root.is_symlink() or final_root.exists() or final_root.is_symlink():
                        raise ArchiveError('Archive destination already exists; use its bound receipt to resume')
                    partial_root.mkdir(mode=0o700)
                    info = partial_root.stat()
                    receipt['root_identity'] = [info.st_dev, info.st_ino]
                    out.update(receipt)
                if stat.S_IMODE(active.stat().st_mode) & 0o077:
                    raise ArchiveError('Archive directory permissions are no longer owner-only')
                def assert_identity(path):
                    local_guards.check_directory(path)
                    info = path.stat()
                    if [info.st_dev, info.st_ino] != receipt['root_identity']:
                        raise ArchiveError('Local archive directory identity changed during the run')
                expected = {r['relative_path']: r for r in rows}
                found = set()
                for directory, directories, names in os.walk(active, followlinks=False):
                    for name in directories:
                        local_guards.check_directory(Path(directory) / name)
                    for name in names:
                        path = Path(directory) / name
                        relative = path.relative_to(active).as_posix()
                        if relative not in expected:
                            raise ArchiveError('Unexpected or unfinished file retained in archive; inspect before resume')
                        found.add(relative)
                needed = 0
                for row in rows:
                    if row['relative_path'] not in found:
                        if row['storage_mode'] == 'copy':
                            needed += row['bytes']
                        continue
                    path = active / row['relative_path']
                    actual = guards.hash_source(path, active)
                    source_info = Path(row['source_path']).stat()
                    info = path.stat()
                    same = (info.st_dev, info.st_ino) == (source_info.st_dev, source_info.st_ino)
                    relationship_bad = (not same or info.st_nlink < 2) if row['storage_mode'] == 'hardlink' else (same or info.st_nlink != 1)
                    if actual != {k: row[k] for k in ['bytes', 'sha256', 'md5']} or relationship_bad:
                        raise ArchiveError('Existing archive object differs or its copy/link relationship changed')
                if active == final_root and len(found) != len(rows):
                    raise ArchiveError('Completed archive is missing files; do not modify its published snapshot')
                used = storage_used_bytes()
                free = shutil.disk_usage(RAW_ROOT).free
                if used + needed > budget or free < needed + reserve:
                    raise ArchiveError('Raw-byte budget or free-space reserve prevents archive copy')
                receipt.update(status='running', raw_used_at_start=used, remaining_copy_bytes=needed)
                out.update(receipt)
                for row in rows:
                    assert_identity(active)
                    if row['relative_path'] in found:
                        record = {k: v for k, v in row.items() if k != 'source_path'} | {'status': 'existing_' + row['storage_mode'] + '_hash_verified'}
                        receipt['reused_files'] += 1
                    else:
                        # Recheck resource bounds before every independent copy.
                        new_bytes = row['bytes'] if row['storage_mode'] == 'copy' else 0
                        if storage_used_bytes() + new_bytes > budget or shutil.disk_usage(RAW_ROOT).free < new_bytes + reserve:
                            raise ArchiveError('Resource budget changed before the next archive copy')
                        if row['storage_mode'] == 'hardlink':
                            record = local_hardlink(row, active)
                            receipt['linked_files'] += 1
                        else:
                            record = local_guards.copy_verified(row, source_root_for(row['source_path']), active)
                            receipt['copied_files'] += 1
                            receipt['new_unique_file_bytes'] += row['bytes']
                    receipt['records'].append(record)
                    receipt['verified_bytes'] += row['bytes']
                    out.update(receipt)
                assert_identity(active)
                verify_local_tree(active, rows)
                if active == partial_root:
                    local_guards.rename_no_replace(partial_root, final_root)
                assert_identity(final_root)
                verify_local_tree(final_root, rows)
                receipt.update(status='completed', actual_root=str(final_root), exact_file_set_verified=True)
            except Exception as exc:
                receipt['status'] = 'failed_no_rollback'
                receipt['error'] = str(exc) if isinstance(exc, (ArchiveError, local_guards.ArchiveError)) else type(exc).__name__
                raise
            finally:
                receipt['finished_at'] = now()
                out.update(receipt)
    except local_guards.ArchiveError as exc:
        raise ArchiveError(str(exc)) from exc
    return receipt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    pp = sub.add_parser('plan')
    pp.add_argument('manifest', type=Path)
    pp.add_argument('--output', required=True, type=Path)
    vp = sub.add_parser('verify-plan')
    vp.add_argument('plan', type=Path)
    sp = sub.add_parser('status')
    sp.add_argument('--remote', required=True)
    up = sub.add_parser('upload')
    up.add_argument('plan', type=Path)
    up.add_argument('--remote', required=True)
    up.add_argument('--receipt', required=True, type=Path)
    up.add_argument('--stage-root', type=Path, default=RAW_ROOT / 'drive-staging')
    up.add_argument('--resume-from', type=Path)
    up.add_argument('--private-mydrive-root-confirmed', action='store_true')
    lp = sub.add_parser('local-archive', help='Verified private cloud archive: independent copy default, explicit shared-inode hardlink option; no networking')
    lp.add_argument('plan', type=Path)
    lp.add_argument('--receipt', required=True, type=Path)
    lp.add_argument('--resume-from', type=Path)
    lp.add_argument('--archive-root', type=Path, default=RAW_ROOT / 'batch-archives')
    lp.add_argument('--mode', choices=['copy', 'hardlink'], default='copy', help='Hardlink explicitly shares source inodes; no cross-device copy fallback')
    args = p.parse_args(argv)
    try:
        if args.command == 'plan':
            guards.output_path(args.output, 'plan')
            value = build_plan(load_json(args.manifest))
            guards.write_new_json(args.output, value)
            result = {k: v for k, v in value.items() if k != 'files'}
        elif args.command == 'verify-plan':
            value = load_json(args.plan)
            validate_plan(value)
            result = {'status': 'verified_local_bytes_and_receipts', 'files': len(value['files']), 'drive_requests': 0}
        elif args.command == 'status':
            result = guards.remote_status(args.remote)
        elif args.command == 'local-archive':
            value = local_archive(load_json(args.plan), args.receipt, resume_from=args.resume_from, archive_root=args.archive_root, mode=args.mode)
            result = {k: v for k, v in value.items() if k != 'records'}
        else:
            value = upload(load_json(args.plan), args.remote, args.receipt, args.stage_root,
                           resume_from=args.resume_from, private_root_confirmed=args.private_mydrive_root_confirmed)
            result = {k: v for k, v in value.items() if k not in {'records', 'directory_ids'}}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ArchiveError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'stopped', 'reason': str(exc) if isinstance(exc, ArchiveError) else type(exc).__name__, 'actual_upload_success_not_implied': True}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
