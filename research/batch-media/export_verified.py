#!/usr/bin/env python3
"""Export source-bound, actually verified local YouTube media; no network or ledger writes."""
import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ID = re.compile(r'[A-Za-z0-9_-]{11}')
HASH = re.compile(r'[a-f0-9]{64}')
COMPONENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,159}')
MAX_JSON = 8 * 1024**2


class ExportError(ValueError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def safe_path(value, *, root=None, file=False):
    path = Path(value).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ExportError('path_symlink_or_traversal')
    if root is not None and not path.is_relative_to(Path(root).absolute()):
        raise ExportError('path_outside_required_root')
    if file and not path.is_file():
        raise ExportError('source_file_missing')
    return path


def inside_git(path):
    # Managed /workspace can contain an empty .git placeholder, which is not a
    # repository. Match real checkouts and worktree gitdir markers only.
    for parent in [Path(path), *Path(path).parents]:
        marker = parent / '.git'
        if marker.is_dir() and (marker / 'HEAD').is_file(): return True
        if marker.is_file() and marker.stat().st_size < 4096 and marker.read_text().startswith('gitdir:'): return True
    return False


def read_json(path):
    path = safe_path(path, file=True)
    if path.stat().st_size > MAX_JSON:
        raise ExportError('json_size_limit')
    data = path.read_bytes()
    value = json.loads(data)
    canonical_json(value)
    return value, hashlib.sha256(data).hexdigest()


def finite_duration(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 300


def declared_language(metadata):
    """Preserve only a bounded explicit source declaration, never subtitle labels."""
    declared = metadata.get('language')
    pattern = r'[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})*'
    if isinstance(declared, str) and len(declared) <= 35 and re.fullmatch(pattern, declared):
        return {'source_language': declared, 'source_language_status': 'declared',
                'source_language_basis': 'captured_metadata.language_not_human_reviewed'}
    status = 'missing' if declared in (None, '') else 'invalid'
    if isinstance(declared, list) and len(declared) <= 20:
        candidates = sorted({v for v in declared if isinstance(v, str) and len(v) <= 35 and re.fullmatch(pattern, v)})
        if len(candidates) > 1: status = 'conflicting'
    return {'source_language': 'unknown', 'source_language_status': status,
            'source_language_basis': 'no_single_valid_captured_metadata.language_declaration;_subtitles_not_used'}


def probe_media(path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                 'format=duration:stream=codec_type,height', '-of', 'json', str(path)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60, check=True)
        if len(result.stdout) > MAX_JSON:
            raise ExportError('ffprobe_output_limit')
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        raise ExportError('ffprobe_failed') from None


def selected_records(path):
    document, digest = read_json(path)
    rows = document.get('records') if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ExportError('selection_records_required')
    records = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ExportError('selection_row_object_required')
        vid = row.get('video_id', row.get('id'))
        if not isinstance(vid, str) or not ID.fullmatch(vid) or row.get('source_id') != 'youtube:' + vid:
            raise ExportError('selection_identity_mismatch')
        contexts = row.get('context_associations')
        if not isinstance(contexts, list) or not contexts:
            raise ExportError('selection_context_associations_required')
        for context in contexts:
            if not isinstance(context, dict) or not COMPONENT.fullmatch(str(context.get('context_id', ''))) or not isinstance(context.get('name'), str) or not context['name'].strip():
                raise ExportError('selection_context_invalid')
        if vid in records:
            raise ExportError('selection_duplicate_video_id')
        records[vid] = {**row, 'video_id': vid}
    batch_id = document.get('batch_id') or 'youtube-batch-' + digest[:16]
    if not isinstance(batch_id, str) or not COMPONENT.fullmatch(batch_id):
        raise ExportError('batch_id_invalid')
    return records, digest, batch_id


def validate_row(artifact, item, job, candidate, raw, bashar_slots):
    vid = candidate['video_id']; source_id = 'youtube:' + vid
    if artifact['source_id'] != source_id or artifact['kind'] != 'video' or artifact['status'] != 'verified_quarantine':
        raise ExportError('artifact_ledger_identity_or_status')
    if not item or item['video_id'] != vid or not item['selected'] or not job or job['status'] != 'verified_quarantine' or job['attempts'] < 1:
        raise ExportError('source_admission_or_completed_job_missing')
    relative = Path(artifact['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] != 'quarantine':
        raise ExportError('artifact_relative_path_invalid')
    path = safe_path(raw / relative, root=raw / 'quarantine', file=True)
    if type(artifact['bytes']) is not int or artifact['bytes'] <= 0 or not HASH.fullmatch(str(artifact['sha256'])):
        raise ExportError('artifact_size_or_digest_invalid')
    initial_stat = path.stat()
    if initial_stat.st_size != artifact['bytes'] or sha(path) != artifact['sha256']:
        raise ExportError('artifact_bytes_mismatch')
    validation = json.loads(artifact['validation_json']); canonical_json(validation)
    if not isinstance(validation, dict) or validation.get('source_video_id') != vid or not HASH.fullmatch(str(validation.get('metadata_sha256', ''))) or not finite_duration(validation.get('ffprobe_duration_seconds')):
        raise ExportError('captured_validation_invalid')
    metadata_path = safe_path(path.parent / (vid + '.info.json'), root=raw / 'quarantine', file=True)
    metadata, metadata_hash = read_json(metadata_path)
    if metadata_hash != validation['metadata_sha256'] or not isinstance(metadata, dict) or metadata.get('id') != vid:
        raise ExportError('captured_metadata_hash_or_identity_mismatch')
    try:
        url = urlsplit(metadata.get('webpage_url', ''))
        canonical = url.scheme == 'https' and url.hostname in {'www.youtube.com', 'youtube.com'} and url.port in (None, 443) and not url.username and not url.password and url.path == '/watch' and parse_qs(url.query).get('v') == [vid]
    except ValueError:
        canonical = False
    if not canonical or not finite_duration(metadata.get('duration')):
        raise ExportError('captured_metadata_watch_or_duration_invalid')
    positive_short = metadata.get('is_short') is True or metadata.get('media_type') == 'short' or any('/shorts/' in str(metadata.get(k, '')) for k in ('webpage_url', 'original_url')) or re.search(r'(?i)#shorts?\b', str(metadata.get('title', '')))
    normal_format = metadata.get('is_short') is False or metadata.get('media_type') == 'video' or metadata.get('media_type') == 'livestream' and metadata.get('live_status') in ('was_live', 'not_live')
    if positive_short or not normal_format or metadata.get('is_live') is True or metadata.get('live_status') in ('is_live', 'post_live'):
        raise ExportError('non_shorts_completed_format_unproven')
    channel_id = metadata.get('channel_id')
    if not isinstance(channel_id, str) or not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', channel_id):
        raise ExportError('canonical_channel_id_missing')
    # New acquisition proof is immutable in the artifact row. Legacy rows may
    # use their exact matching metadata/current-item snapshot, with no NOW TTL.
    captured_at = validation.get('validated_at')
    if validation.get('metadata_refreshed_at_acquisition') is True:
        admission = validation.get('admission_metadata')
        if not isinstance(admission, dict) or not HASH.fullmatch(str(admission.get('metadata_sha256', ''))) or type(admission.get('metadata_verified_at')) not in (int, float) or not math.isfinite(admission['metadata_verified_at']):
            raise ExportError('acquisition_input_metadata_proof_missing')
        try:
            acquired = dt.datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
            started = dt.datetime.fromisoformat(validation['acquisition_started_at'].replace('Z', '+00:00'))
            if acquired.tzinfo is None or started.tzinfo is None or admission['metadata_verified_at'] <= 0 or acquired < started or not 0 <= started.timestamp() - admission['metadata_verified_at'] <= 300:
                raise ValueError()
        except (AttributeError, TypeError, ValueError, KeyError):
            raise ExportError('acquisition_time_proof_invalid') from None
        classification = validation.get('source_classification_at_acquisition')
        if validation.get('non_shorts_verified_at_acquisition') is not True:
            raise ExportError('captured_non_shorts_admission_missing')
        proof_basis = 'artifact_captured_admission_and_validation'
    else:
        try:
            matching = item['metadata_sha256'] == metadata_hash and canonical_json(json.loads(item['metadata_json'])) == canonical_json(metadata)
        except (TypeError, json.JSONDecodeError):
            matching = False
        verified_at = item['metadata_verified_at']
        if not matching or type(verified_at) not in (int, float) or not math.isfinite(verified_at) or verified_at <= 0 or not item['format_verified']:
            raise ExportError('legacy_acquisition_snapshot_unresolved')
        captured_at = dt.datetime.fromtimestamp(verified_at, dt.timezone.utc).isoformat()
        classification = item['classification']; proof_basis = 'legacy_exact_matching_ledger_metadata_snapshot'
    if classification not in ('bashar', 'other_not_bashar_labeled'):
        raise ExportError('captured_source_classification_unresolved')
    explicit_bashar = re.search(r'\bbashar\b|\bdarryl\s+anka\b', canonical_json({k: metadata.get(k) for k in ('title', 'uploader', 'channel', 'description', 'tags', 'creator', 'artists')}), re.I)
    if (classification == 'bashar' or explicit_bashar) and source_id not in bashar_slots:
        raise ExportError('bashar_cap_slot_missing')
    if classification == 'bashar' and len(bashar_slots) > 100:
        raise ExportError('global_bashar_cap_accounting_invalid')
    if explicit_bashar and classification != 'bashar':
        raise ExportError('captured_bashar_classification_conflict')
    probe = probe_media(path)
    try:
        duration = float(probe['format']['duration'])
    except (KeyError, TypeError, ValueError):
        raise ExportError('actual_duration_invalid') from None
    streams = probe.get('streams', [])
    if not finite_duration(duration) or not any(s.get('codec_type') == 'video' for s in streams) or not any(s.get('codec_type') == 'audio' for s in streams):
        raise ExportError('actual_media_stream_or_duration_invalid')
    if not all(math.isclose(duration, expected, rel_tol=.02, abs_tol=5) for expected in (metadata['duration'], validation['ffprobe_duration_seconds'])):
        raise ExportError('actual_duration_mismatch')
    if 'video_height_limit' in validation:
        limit = validation['video_height_limit']; heights = [s.get('height') for s in streams if s.get('codec_type') == 'video']
        if type(limit) is not int or not 0 < limit <= 720 or not heights or any(type(h) is not int or not 0 < h <= limit for h in heights):
            raise ExportError('actual_height_mismatch')
    safe_path(path, root=raw / 'quarantine', file=True)
    safe_path(metadata_path, root=raw / 'quarantine', file=True)
    final_stat = path.stat()
    if (initial_stat.st_dev, initial_stat.st_ino, initial_stat.st_size, initial_stat.st_mtime_ns) != (final_stat.st_dev, final_stat.st_ino, final_stat.st_size, final_stat.st_mtime_ns) or sha(path) != artifact['sha256'] or sha(metadata_path) != metadata_hash:
        raise ExportError('media_or_metadata_changed_during_verification')
    contexts = candidate['context_associations']; primary = min(c['context_id'] for c in contexts)
    row = {'local_path': str(path), 'sha256': artifact['sha256'], 'bytes': artifact['bytes'], 'provider': 'youtube',
           'source_id': source_id, 'video_id': vid, 'kind': 'video', 'medium_id': primary, 'channel_id': channel_id,
           'channel': metadata.get('channel') or metadata.get('uploader'), 'title': metadata.get('title'),
           'context_associations': contexts, 'medium_assignment_basis': 'lexicographically_first_inherited_context_not_verified_speaker',
           'actual_speaker_status': 'unknown_not_audio_verified', 'source_url': 'https://www.youtube.com/watch?v=' + vid,
           'duration_seconds': duration, 'duration_scope': 'source_video', 'is_short': False,
           **declared_language(metadata),
           'metadata_refreshed_at_acquisition': True, 'acquisition_validated_at': captured_at,
           'acquisition_proof_basis': proof_basis, 'source_classification_at_acquisition': classification}
    safe_validation = {k: validation[k] for k in ('source_video_id', 'metadata_sha256', 'ffprobe_duration_seconds', 'tls_verification',
                       'proxy', 'quarantine_only', 'validated_at', 'metadata_refreshed_at_acquisition', 'admission_metadata',
                       'acquisition_started_at', 'source_classification_at_acquisition', 'non_shorts_verified_at_acquisition',
                       'video_height_limit', 'measured_video_heights') if k in validation}
    proof = {**row, 'status': 'verified', 'original_status': artifact['status'], 'validation': safe_validation,
             'metadata_receipt': {'path': str(metadata_path), 'sha256': metadata_hash},
             'actual_ffprobe_duration_seconds': duration,
             'ledger_artifact_row_sha256': hashlib.sha256(canonical_json(dict(artifact)).encode()).hexdigest()}
    return row, proof


def export_verified(database, selection, raw, output):
    raw = safe_path(raw)
    if not raw.is_dir(): raise ExportError('existing_raw_directory_required')
    database = safe_path(database, root=raw, file=True)
    selected, selection_hash, batch_id = selected_records(selection)
    output = safe_path(output)
    if output.exists() or inside_git(output) or output.is_relative_to(raw):
        raise ExportError('new_private_output_outside_git_and_raw_required')
    records, proofs, exclusions, row_digests = [], [], [], []
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row; connection.execute('PRAGMA query_only=ON'); connection.execute('BEGIN')
        slots = {r[0] for r in connection.execute('SELECT source_id FROM bashar_slots')}
        for vid, candidate in selected.items():
            source = 'youtube:' + vid
            item = connection.execute('SELECT * FROM items WHERE source_id=?', (source,)).fetchone()
            job = connection.execute("SELECT * FROM jobs WHERE source_id=? AND kind='video'", (source,)).fetchone()
            artifacts = connection.execute("SELECT * FROM artifacts WHERE source_id=? AND kind='video' AND status='verified_quarantine' ORDER BY rowid DESC", (source,)).fetchall()
            reasons = []
            for artifact in artifacts:
                try:
                    row, proof = validate_row(artifact, item, job, candidate, raw, slots)
                    records.append(row); proofs.append(proof)
                    row_digests.append(proof['ledger_artifact_row_sha256']); break
                except (ExportError, OSError, ValueError, TypeError, KeyError) as error:
                    # Only our fixed reason identifiers enter the report; never raw
                    # decoder stderr, exception paths, metadata or signed URLs.
                    reasons.append(str(error) if isinstance(error, ExportError) else 'artifact_inspection_failed')
            else:
                exclusions.append({'source_id': source, 'video_id': vid, 'reasons': sorted(set(reasons)) or ['no_verified_video_artifact_in_ledger']})
    if sha(selection) != selection_hash: raise ExportError('selection_changed_during_export')
    output.parent.mkdir(parents=True, exist_ok=True); safe_path(output.parent)
    output.mkdir(exist_ok=False)
    receipt = {'schema_version': 1, 'kind': 'verified_local_youtube_media_export', 'verified_at': now(), 'batch_id': batch_id,
               'ledger_path': str(database), 'selection_sha256': selection_hash, 'source_row_digests': row_digests,
               'verified_artifacts': proofs, 'excluded': exclusions, 'selected_source_count': len(selected),
               'verified_video_count': len(records), 'network_requests': 0, 'ledger_mutated': False,
               'scope': 'Rehashed retained video bytes, captured source metadata and measured streams; not a new download, speaker verification or caption/ASR accuracy assessment.',
               'exporter_sha256': sha(Path(__file__))}
    receipt_path = output / 'verification-receipt.json'
    with receipt_path.open('x') as stream: stream.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    reference = {'path': str(receipt_path), 'sha256': sha(receipt_path)}
    for row in records: row['verification_receipt'] = reference
    manifest = {'schema_version': 1, 'batch_id': batch_id, 'records': records, 'selection_sha256': selection_hash,
                'verification_receipt': reference, 'selected_source_count': len(selected), 'excluded_source_count': len(exclusions)}
    manifest_path = output / 'verified-media.json'
    with manifest_path.open('x') as stream: stream.write(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return {'manifest': str(manifest_path), 'verification_receipt': reference, 'selected': len(selected), 'verified': len(records), 'excluded': len(exclusions)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New private output directory outside Git and raw input tree')
    args = parser.parse_args(argv)
    print(json.dumps(export_verified(args.database, args.selection, args.raw, args.output), indent=2))


if __name__ == '__main__': main()
