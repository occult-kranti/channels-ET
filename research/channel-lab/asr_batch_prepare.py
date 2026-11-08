#!/usr/bin/env python3
"""Freeze a duration-ordered, bounded full-recording ASR frame without new media."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

PRIVATE = Path('/workspace/channels-et-private')
REPO = Path('/workspace/channels-ET')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def artifact(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def canonical_command(path):
    return ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1', '-i', str(path),
            '-map', '0:a:0', '-vn', '-sn', '-dn', '-ac', '1', '-ar', '16000',
            '-c:a', 'pcm_s16le', '-threads', '1', '-f', 's16le', 'pipe:1']


def read_bound(ref):
    path = Path(ref['path'])
    if path.stat().st_size != ref['bytes'] or digest(path) != ref['sha256']:
        raise ValueError('Bound artifact changed: ' + path.name)
    return path


def fingerprint_decode(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, 'pcm')
    selector.register(process.stderr, selectors.EVENT_READ, 'error')
    h = hashlib.sha256(); count = 0; stderr = bytearray(); began = time.monotonic()
    try:
        while selector.get_map():
            if time.monotonic() - began > 120:
                raise TimeoutError('Canonical admission decode exceeded 120 seconds')
            for key, _ in selector.select(timeout=0.2):
                raw = os.read(key.fd, 1024 * 1024)
                if not raw:
                    selector.unregister(key.fileobj)
                elif key.data == 'pcm':
                    h.update(raw); count += len(raw)
                else:
                    stderr.extend(raw)
                    if len(stderr) > 65536:
                        raise ValueError('Decoder error log exceeded admission cap')
        code = process.wait(timeout=5)
        return h.hexdigest(), count, bytes(stderr), code
    finally:
        selector.close()
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)
        process.stdout.close(); process.stderr.close()


def select():
    bindings = []
    def load(path):
        bindings.append(artifact(path))
        return json.loads(Path(path).read_text())
    prior_path = PRIVATE/'knowledge-bank-2026-11/asr/full-council-01/manifest.json'
    prior = load(prior_path)
    completed = {x['audio_artifact']['sha256'] for x in prior['documents']}
    pubs = load(PRIVATE/'subscription-screening-2026-11/publisher-audio-v3/manifest.json')
    old = load(PRIVATE/'expanded-channeling-2026-11/completion/coordinated-council-01/inputs/merged-asr.json')
    old_by_publication = {x['publication_id']: x for x in old['records'] if x['status'] == 'completed'}
    records = []
    selections = []
    for context, medium, take_all in [('tr-medium-natalie-glasson', 'Natalie Glasson / OmNa', True),
                                    ('tracy_kumbera_publisher', 'Tracy Kumbera', False),
                                    ('akanksshaa_publisher', 'Multidimensional Soul', False)]:
        candidates = sorted([x for x in pubs['records'] if x['status'] == 'completed'
                             and x['source'].get('medium_context_id') == context
                             and x['audio']['sha256'] not in completed],
                            key=lambda x: (x['decoded_16k_mono']['duration_seconds'], x['publication_id']))
        chosen = candidates if take_all else candidates[:1]
        selections.append({'context': context, 'eligible_count': len(candidates), 'selected': len(chosen),
                           'rule': 'all retained' if take_all else 'shortest decoded duration; publication ID breaks ties'})
        for x in chosen:
            old_row = old_by_publication.get(x['publication_id'])
            old_text = old_row.get('transcript') if old_row else None
            if not old_text and old_row:
                for key in ('text_artifact', 'transcript_artifact'):
                    if key in old_row:
                        old_text = old_row[key]
                if not old_text:
                    old_text = old_row.get('outputs', {}).get('normalized')
            records.append({'source_id': x['source_id'], 'publication_id': x['publication_id'],
                            'medium': medium, 'title': x['source']['title'], 'source_url': x['source']['source_url'],
                            'source_language_evidence': x['source'].get('language_basis', 'Publisher context; not manually listened'),
                            'audio_artifact': {k: x['audio'][k] for k in ('path', 'bytes', 'sha256')},
                            'prior_canonical_s16': x['decoded_16k_mono'],
                            'old_asr_record': old_row, 'old_text_artifact': old_text,
                            'selection_duration_seconds': x['decoded_16k_mono']['duration_seconds']})
    official = load(PRIVATE/'bashar-ra-2026-11/bashar/official-vimeo-corpus-reviewed/manifest.json')
    candidates = sorted([x for x in official['records'] if x.get('integrity_status') == 'passed'
                         and x.get('eligibility_status') == 'qualifying_actual_duration'
                         and x.get('audio_duration_seconds', 0) >= 300
                         and x['audio_artifact']['sha256'] not in completed],
                        key=lambda x: (x['audio_duration_seconds'], x['source_id']))
    x = candidates[0]
    selections.append({'context': 'official_bashar', 'eligible_count': len(candidates), 'selected': 1,
                       'rule': 'shortest verified duration >=300 seconds; source ID breaks ties'})
    records.append({'source_id': x['recording_id'], 'publication_id': x['session_id'],
                    'old_counterpart_source_id': x['source_id'], 'medium': 'Darryl Anka / official Bashar',
                    'title': x['title'], 'source_url': x['source_url'],
                    'source_language_evidence': x['language_basis'],
                    'audio_artifact': {k: x['audio_artifact'][k] for k in ('path', 'bytes', 'sha256')},
                    'prior_canonical_s16': None, 'old_text_artifact': x['text_artifact'],
                    'selection_duration_seconds': x['audio_duration_seconds']})
    athina_path = REPO/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json'
    x = load(athina_path)
    athina = {'source_id': x['sourceId'], 'publication_id': x['sourceId'], 'medium': 'Athina Król',
              'title': 'Meet Your Guides: Ashtar', 'source_url': x['sourceUrl'],
              'source_language_evidence': 'Prior automatic English ASR; not human language verification',
              'audio_artifact': artifact(x['sourceAudioPath']), 'prior_canonical_s16': None,
              'old_asr_receipt': artifact(athina_path),
              'old_text_artifact': {'path': str(Path(x['transcriptDirectory'])/'transcript.txt'),
                                    **{k: next(o for o in x['outputs'] if o['name'] == 'transcript.txt')[k]
                                       for k in ('bytes', 'sha256')}},
              'selection_duration_seconds': x['decoderDurationSeconds']}
    if athina['audio_artifact']['sha256'] != x['sourceAudioSha256']:
        raise ValueError('Athina source differs from accepted old receipt')
    include_athina = sum(x['selection_duration_seconds'] for x in records) + athina['selection_duration_seconds'] <= 14400
    if include_athina:
        records.append(athina)
    selections.append({'context': 'athina', 'eligible_count': 1, 'selected': int(include_athina),
                       'rule': 'single retained accepted source, only if total remains <=4 hours'})
    if len(records) > 9 or len({x['audio_artifact']['sha256'] for x in records}) != len(records):
        raise ValueError('Selection exceeds bounds or duplicates exact audio')
    for row in records:
        row['recording_id'] = 'audio-sha256:' + row['audio_artifact']['sha256']
    return records, selections, bindings, artifact(prior_path)


def prepare(output):
    if output.exists():
        raise ValueError('Frozen frames cannot be overwritten')
    records, selection, bindings, prior = select()
    for row in records:
        path = read_bound(row['audio_artifact'])
        if row.get('old_text_artifact'):
            read_bound(row['old_text_artifact'])
        command = canonical_command(path)
        # The admission pass streams to a hash; no full PCM file is retained.
        pcm_sha, count, stderr, code = fingerprint_decode(command)
        if code or count % 2 or not count:
            raise ValueError('Canonical source decoding failed')
        samples = count // 2
        previous = row.pop('prior_canonical_s16')
        if previous and (samples != previous['sample_count'] or pcm_sha != previous['raw_pcm_sha256']):
            raise ValueError('Canonical PCM differs from accepted acquisition')
        row['canonical_s16_pcm'] = {'sha256': pcm_sha, 'sample_count': samples,
                                   'duration_seconds': samples/16000, 'sample_rate': 16000,
                                   'channels': 1, 'format': 's16le',
                                   'matches_prior_canonical_receipt': bool(previous)}
        row['decode'] = {'command': command, 'returncode': code, 'stderr_bytes': len(stderr),
                         'stderr_sha256': hashlib.sha256(stderr).hexdigest(), 'natural_eof': True}
        row['planned_chunks'] = (samples + 479999)//480000
        # Keep a binding to the old record, without embedding an entire old worker request.
        old = row.pop('old_asr_record', None)
        if old:
            row['old_counterpart_source_id'] = old['source_id']
            row['old_asr_record_sha256'] = hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()
    total = sum(x['canonical_s16_pcm']['duration_seconds'] for x in records)
    if total > 14400:
        raise ValueError('Measured source duration exceeds four-hour admission')
    frame = {'schema_version': 1, 'status': 'frozen_full_recording_frame',
             'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'producer_sha256': digest(__file__),
             'selection': selection, 'sources': records, 'source_bindings': bindings,
             'reused_prior_editions_manifest': prior, 'reused_prior_editions': 4,
             'recordings': len(records), 'input_audio_seconds': total,
             'planned_chunks': sum(x['planned_chunks'] for x in records),
             'scope': 'Nine predeclared retained recordings, complete sample coverage planned; no new media downloads or quality-based selection.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frame, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k: frame[k] for k in ('status', 'recordings', 'input_audio_seconds', 'planned_chunks')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    prepare(parser.parse_args().output)
