#!/usr/bin/env python3
"""Freeze and load a source-bound, deduplicated knowledge-bank edition frame."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_artifact(ref):
    path = Path(ref['path'])
    raw = path.read_bytes()
    if digest(raw) != ref['sha256'] or ('bytes' in ref and len(raw) != ref['bytes']):
        raise ValueError('Source artifact changed: ' + str(path))
    return path, raw


def body_from_artifact(ref):
    path, raw = read_artifact(ref)
    text = json.loads(raw)['text'] if path.suffix == '.json' else raw.decode('utf-8')
    return unicodedata.normalize('NFKC', text).strip()


def load_frame(path):
    frame = json.loads(Path(path).read_text())
    docs = []
    for r in frame['records']:
        text = body_from_artifact(r['text_artifact'])
        if digest(text.encode()) != r['body_sha256'] or len(text.split()) != r['words']:
            raise ValueError('Frozen normalized body changed: ' + r['source_id'])
        docs.append({'record': r, 'text': text})
    if len(docs) != frame['coverage']['documents']:
        raise ValueError('Frame count differs')
    return docs, frame


def build(pilot, councils, output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(Path('/workspace/channels-et-private')):
        raise ValueError('Use a fresh private output file')
    selected, excluded, inputs, hashes, families, ids = [], [], [], {}, {}, set()
    for path, kind in [(pilot, 'written_pilot')] + [(p, 'council_follow_on') for p in councils]:
        raw = path.read_bytes(); data = json.loads(raw)
        inputs.append({'path': str(path), 'sha256': digest(raw), 'bytes': len(raw), 'prior_frame': kind})
        for old in data.get('documents', data.get('records', [])):
            sid = old['source_id']
            if sid in ids:
                raise ValueError('Repeated source ID requires explicit disposition')
            ids.add(sid)
            ref = dict(old['text_artifact'])
            text = body_from_artifact(ref)
            expected = old.get('words')
            if expected is not None and len(text.split()) != expected:
                raise ValueError('Declared source word count differs: ' + sid)
            hashed = digest(text.encode())
            family = old.get('publication_family_id') or old.get('publication_id')
            if hashed in hashes or (family and family in families):
                excluded.append({'source_id': sid, 'reason': 'exact_normalized_body_or_declared_publication_family',
                    'selected_source_id': hashes.get(hashed, families.get(family)), 'body_sha256': hashed})
                continue
            hashes[hashed] = sid
            if family: families[family] = sid
            medium = old.get('medium_name') or old.get('medium')
            label = old.get('label') or old.get('council_label') or old.get('council_label_exact')
            if not medium or not label: raise ValueError('Missing source-local attribution')
            comparison = old.get('comparison_label')
            if not comparison:
                comparison = 'arcturian' if sid == 'galactic-daniel-20190327' else re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
            broad = comparison in {'arcturian', 'pleiadian', 'andromedan', 'sassani'}
            is_asr = Path(ref['path']).suffix == '.json'
            r = {'source_id': sid, 'title': old['title'],
                'source_url': old.get('source_url') or old.get('canonical_url'),
                'medium_id': 'medium-' + re.sub(r'[^a-z0-9]+', '-', medium.lower()).strip('-'),
                'medium': medium, 'source_medium_id': old.get('medium_id'),
                'claimed_label': label, 'comparison_label': comparison,
                'comparison_level': 'broad_civilization_label_not_same_speaker' if broad else 'printed_named_label_not_authenticated_identity',
                'document_kind': 'machine_transcript' if is_asr else 'publisher_written_message',
                'prior_frame': kind, 'published_at': old.get('published_at') or old.get('publisher_date'),
                'publication_family_id': family, 'words': len(text.split()),
                'text_artifact': ref, 'body_sha256': hashed,
                'body_normalization': 'Unicode NFKC then strip outer whitespace; Python character offsets, end-exclusive',
                'attribution_scope': old.get('attribution_scope') or old.get('source_local_attribution') or old.get('text_scope'),
                'text_scope': old.get('body_boundary') or old.get('text_scope') or old.get('boundary') or old.get('body_boundary'),
                'speaker_role': 'unknown' if is_asr else old.get('speaker_role', 'publisher_attributed_written_message'),
                'speaker_identity_verified': False, 'audio_alignment_verified': False}
            if old.get('qa_artifact'): r['qa_artifact'] = old['qa_artifact']
            selected.append(r)
    selected.sort(key=lambda r: r['source_id'])
    frame = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Additive fixed-edition knowledge frame: earlier20 written-message pilot plus5 Council text editions; source assertions, not verified entities or new independent observations.',
        'coverage': {'documents': len(selected), 'words': sum(r['words'] for r in selected),
            'mediums': len({r['medium_id'] for r in selected}), 'excluded_aliases': len(excluded)},
        'inputs': inputs, 'records': selected, 'excluded_aliases': excluded,
        'script_sha256': digest(Path(__file__).read_bytes())}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frame, indent=2, ensure_ascii=False) + '\n')
    load_frame(output)
    print(json.dumps({'coverage': frame['coverage'], 'sha256': digest(output.read_bytes())}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot-provenance', type=Path, required=True)
    p.add_argument('--council-manifest', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); build(a.pilot_provenance, a.council_manifest, a.output)
