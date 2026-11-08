#!/usr/bin/env python3
"""Create a private, portable export of four verified completed ASR editions.

Only transcript bytes and small provenance metadata are included. This builder
uses the standard library, makes no network requests and never loads media or
model weights. Existing output directories are never overwritten.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bound(ref):
    raw = Path(ref['path']).read_bytes()
    if len(raw) != ref['bytes'] or sha(raw) != ref['sha256']:
        raise ValueError('An input artifact differs from its full-manifest binding')
    return raw


def portable_binding(ref):
    return {'bytes': ref['bytes'], 'sha256': ref['sha256']}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def path_strings(value, location='$'):
    """Find absolute values and known environment paths without modifying text."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(path_strings(child, location + '.' + str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(path_strings(child, location + '[' + str(index) + ']'))
    elif isinstance(value, str):
        if value.startswith('/') or re.search(r'(?:/workspace/|/dev/shm/|/tmp/|/home/|[A-Za-z]:\\)', value):
            found.append(location)
    return found


def build(manifest_path, model_receipt_path, output_dir):
    if output_dir.exists():
        raise ValueError('Choose a fresh output directory; previous archives are immutable')
    manifest_raw = manifest_path.read_bytes()
    full = json.loads(manifest_raw)
    if full['status'] != 'completed_full_chunked_asr' or len(full['documents']) != 4:
        raise ValueError('Expected the completed four-recording ASR edition')
    model_raw = model_receipt_path.read_bytes()
    model = json.loads(model_raw)
    if (model['status'] != 'downloaded_and_hash_verified'
            or model['repo'] != full['model_id'] or model['revision'] != full['model_revision']):
        raise ValueError('Model download receipt does not match the completed run')
    stage = json.loads(read_bound(full['stage_receipt']))
    if stage['status'] != 'completed':
        raise ValueError('Inference stage is incomplete')

    members = {}
    expected_copies = {}
    documents = []
    ids = set()
    embedded_paths = []
    for index, doc in enumerate(full['documents'], 1):
        if doc['source_id'] in ids:
            raise ValueError('Duplicate source edition')
        ids.add(doc['source_id'])
        json_raw = read_bound(doc['text_artifact'])
        text_raw = read_bound(doc['plain_text_artifact'])
        parsed = json.loads(json_raw)
        receipt = json.loads(read_bound(doc['asr_receipt']))
        old = json.loads(read_bound(doc['old_text_artifact']))
        old_receipt = json.loads(read_bound(doc['old_asr_receipt']))
        if (parsed['source_id'] != doc['source_id']
                or parsed['counterpart_source_id'] != doc['counterpart_source_id']
                or parsed['words'] != len(parsed['text'].split())
                or parsed['words'] != doc['words']
                or text_raw.decode('utf-8') != parsed['text'] + '\n'):
            raise ValueError('Source identity or exact transcript assembly mismatch')
        coverage = doc['coverage']
        if (receipt['coverage'] != coverage or coverage['input_samples'] != coverage['covered_samples']
                or not all(coverage[k] for k in ('contiguous', 'starts_at_zero', 'ends_at_sample_count', 'all_encoder_exhausted'))):
            raise ValueError('Full sample coverage is not established')
        canonical = doc['canonical_s16_pcm']
        if (canonical['sha256'] != old_receipt['decoder']['raw_pcm_sha256']
                or canonical['sample_count'] != old_receipt['decoder']['sample_count']):
            raise ValueError('Canonical old/new audio binding differs')
        cursor = 0
        for turn in parsed['turns']:
            if (turn['start_sample'] != cursor or turn['end_sample'] <= cursor
                    or turn['start'] != cursor / 16000
                    or turn['end'] != turn['end_sample'] / 16000
                    or turn['speaker_role'] != 'unknown'):
                raise ValueError('Timecoded JSON has invalid sample boundaries or speaker roles')
            cursor = turn['end_sample']
        if cursor != coverage['covered_samples'] or len(parsed['turns']) != coverage['chunk_count']:
            raise ValueError('Timecoded JSON does not cover the bound full input')
        slug = re.sub(r'[^a-z0-9]+', '-', doc['medium'].casefold()).strip('-')
        folder = f"transcripts/{index:02d}-{slug}-{sha(doc['source_id'].encode())[:10]}"
        refs = {}
        for key, raw, suffix in [('timecoded_json', json_raw, 'json'), ('plain_text', text_raw, 'txt')]:
            member = folder + '/transcript.' + suffix
            if member in members:
                raise ValueError('Duplicate archive member')
            members[member] = raw
            expected_copies[member] = {'bytes': len(raw), 'sha256': sha(raw)}
            refs[key] = {'member': member, **expected_copies[member]}
        locations = path_strings(parsed)
        if locations:
            embedded_paths.append({'member': refs['timecoded_json']['member'], 'json_locations': locations})
        documents.append({
            **{k: doc[k] for k in ('source_id', 'counterpart_source_id', 'publication_id', 'title',
                                   'source_url', 'medium', 'claimed_label', 'attribution_scope')},
            **refs, 'new_words': doc['words'], 'old_words': len(old['text'].split()),
            'source_audio': portable_binding(doc['audio_artifact']),
            'old_text_artifact': portable_binding(doc['old_text_artifact']),
            'old_asr_receipt': portable_binding(doc['old_asr_receipt']),
            'new_asr_receipt': portable_binding(doc['asr_receipt']),
            'canonical_s16_pcm': canonical, 'model_f32_pcm': doc['decoded_pcm'],
            'coverage': coverage, 'speaker_role': 'unknown', 'accuracy_verified': False,
            'empty_text_windows': sum(not turn['text'].strip() for turn in parsed['turns']),
        })

    portable = {
        'schema_version': 1, 'status': 'verified_private_transcript_export',
        'scope': 'Four completed new ASR editions; source media and model weights are not included.',
        'source_run_created_at': full['created_at'],
        'summary': {'recordings': len(documents), 'words': sum(d['new_words'] for d in documents),
                    'chunks': sum(d['coverage']['chunk_count'] for d in documents),
                    'covered_audio_seconds': full['covered_audio_seconds'],
                    'covered_samples': sum(d['coverage']['covered_samples'] for d in documents),
                    'new_audio_downloads': 0, 'original_transcript_bytes_preserved': True},
        'model': {'id': model['repo'], 'revision': model['revision'],
                  'model_card': f"https://huggingface.co/{model['repo']}/blob/{model['revision']}/README.md",
                  'license_attribution': 'NVIDIA Parakeet TDT 0.6B v3; model card specifies CC BY 4.0.',
                  'runtime': 'PyTorch/Transformers, CPU float32, two one-thread workers',
                  'weights_modified_or_trained': False,
                  'files': [{k: item[k] for k in ('file', 'bytes', 'sha256', 'canonical_url')}
                            for item in model['files']]},
        'documents': documents,
        'path_scan': {'method': 'Recursive JSON string scan: absolute values, common environment roots and Windows drive paths.',
                      'copied_json_path_findings': embedded_paths,
                      'original_bytes_unchanged_even_when_paths_detected': True},
        'provenance': {'private_full_manifest': {'bytes': len(manifest_raw), 'sha256': sha(manifest_raw)},
                       'model_download_receipt': {'bytes': len(model_raw), 'sha256': sha(model_raw)},
                       'input_frame': portable_binding(full['input_frame']),
                       'stage_receipt': portable_binding(full['stage_receipt']),
                       'finalizer_sha256': full['finalizer_sha256'],
                       'executed_worker_sha256': stage['worker_sha256'],
                       'executed_orchestrator_sha256': stage['orchestrator_sha256'],
                       'archive_builder_sha256': sha(Path(__file__).read_bytes())},
    }
    if path_strings(portable):
        raise ValueError('Portable metadata unexpectedly contains absolute paths')
    members['manifest.json'] = json_bytes(portable)
    disclosure = (f'{len(embedded_paths)} copied JSON files contain path-like strings; see manifest.json path_scan. '
                  'Those original bytes are preserved unchanged.' if embedded_paths else
                  'The automated path scan found no absolute or known environment paths in the copied JSON. '
                  'All eight transcript files preserve their original bytes.')
    readme = f"""# Private Council transcript export

Four completed new NVIDIA Parakeet TDT 0.6B v3 transcript editions, with original
plain text and timecoded JSON. The portable manifest links each edition to its
publisher URL, medium label, preserved old counterpart hashes, canonical audio
hashes and pinned model revision. No media, model binaries or old text editions
are duplicated in this export. Source rights and publisher attribution remain
unchanged; this is a private research export.

Coverage: {portable['summary']['covered_samples']:,} samples,
{full['covered_audio_seconds']:.5f} seconds, {portable['summary']['chunks']} windows,
and {portable['summary']['words']:,} machine-generated whitespace words. These are
four reused recordings, not four newly downloaded recordings.

## Reading the files

Each transcript.json contains the complete assembled text and a `turns` array.
These entries are fixed, nonoverlapping audio windows of at most 30 seconds,
including the final partial window. Start/end values are seconds from the start
of the recording; start_sample/end_sample refer to mono 16 kHz PCM. The windows
are not word alignments or verified speaker turns. All speaker roles are unknown.
Use manifest.json to map each folder to the source title and public publisher URL.

## Limits

Recognition used independent windows, so boundaries can split words or sentences
and lose conversational context. Complete sample coverage and encoder exhaustion
do not verify every word. No human reference supports a WER/accuracy claim.
Two Pamela windows have empty text and remain included; silence or recognition
failure has not been independently established by listening. Text was assembled
in order without editorial correction, overlap deduplication or speaker inference.
Publisher labels for claimed entities do not verify who speaks or the claims.
The earlier four editions and primary 25-document analysis remain unchanged;
old annotation offsets must not be transferred silently to these new editions.

## Integrity and portability

{disclosure}
The newly generated manifest contains no absolute filesystem paths. Its archive
member paths are relative. Every copied file is verified against the completed
full-run manifest before writing, then re-read from the ZIP and SHA-256 checked.
The original path-bearing run receipts are represented by hashes, not copied.
Model/source hashes bind provenance; the referenced artifacts are not all inside
this small export. SHA-256 checks establish byte integrity, not factual accuracy.
ZIP member timestamps are fixed for reproducible packaging; they are not recording
or publication dates. Rebuilding requires the source manifest and bound files.
"""
    members['README.md'] = readme.encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    archive_raw = buffer.getvalue()
    if len(archive_raw) > 2_000_000:
        raise ValueError('Private transcript archive exceeds the two-megabyte admission budget')
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(members):
            raise ValueError('Archive integrity or member set failed')
        for name, expected in members.items():
            actual = archive.read(name)
            if actual != expected:
                raise ValueError('ZIP member does not preserve its admitted bytes')
        for name, expected in expected_copies.items():
            raw = archive.read(name)
            if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
                raise ValueError('Copied transcript failed post-packaging hash verification')
    parent = output_dir.parent
    existing = parent
    while not existing.exists():
        existing = existing.parent
    if shutil.disk_usage(existing).free - len(archive_raw) - 32_768 < 2 * 1024**3:
        raise ValueError('Archive would cross the two-GiB disk floor')
    receipt = {
        'status': 'verified', 'archive': 'council-parakeet-transcripts.zip',
        'bytes': len(archive_raw), 'sha256': sha(archive_raw), 'members': len(members),
        'copied_transcript_files': len(expected_copies), 'recordings': len(documents),
        'original_bytes_preserved': True, 'copied_artifact_hashes_verified_against_full_manifest': True,
        'every_zip_member_reopened_and_verified': True, 'network_requests': 0,
        'audio_or_model_binaries_included': False, 'portable_metadata_absolute_paths': 0,
        'copied_json_files_with_path_findings': len(embedded_paths),
        'full_manifest_sha256': sha(manifest_raw), 'portable_manifest_sha256': sha(members['manifest.json']),
        'builder_sha256': sha(Path(__file__).read_bytes()), 'transcript_members': expected_copies,
    }
    output_dir.mkdir(parents=True)
    archive_path = output_dir / receipt['archive']
    archive_path.write_bytes(archive_raw)
    if sha(archive_path.read_bytes()) != receipt['sha256']:
        raise ValueError('Written archive differs from its verified bytes')
    (output_dir / 'verification.json').write_bytes(json_bytes(receipt))
    print(json.dumps({k: receipt[k] for k in ('status', 'archive', 'bytes', 'sha256', 'members', 'copied_transcript_files',
                                           'recordings', 'copied_json_files_with_path_findings')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--model-receipt', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    build(args.manifest, args.model_receipt, args.output_dir)
