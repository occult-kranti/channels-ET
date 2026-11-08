#!/usr/bin/env python3
"""Check the public Bashar/Ra release without accessing private source archives."""
import argparse
import hashlib
import json
from pathlib import Path

from publish import safe_public


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(site):
    root = site / 'dist/bashar-ra'
    data = json.loads((root / 'data.json').read_text())
    collection = json.loads((root / 'collection.json').read_text())
    reading = json.loads((root / 'reading.json').read_text())
    for obj in (data, collection, reading):
        safe_public(obj)
    assert data['schema_version'] == 1 and not data['synthetic_fixture_run']
    docs = data['documents']
    assert len({r['source_id'] for r in docs}) == len(docs) == data['counts']['admitted_documents']
    assert data['counts']['primary_session_documents'] == 125
    assert sum(d['source_kind'] == 'authored_reference' for d in docs) == 5
    assert data['counts']['corpora']['ra']['primary_session_documents'] == 106
    assert data['counts']['corpora']['bashar']['primary_session_documents'] == 19
    ids = data['semantic']['source_ids']
    matrix = data['semantic']['cosine_matrix']
    assert len(ids) == len(set(ids)) == 125 and len(matrix) == 125
    assert all(len(row) == 125 for row in matrix)
    assert all(abs(matrix[i][i] - 1) < 1e-5 for i in range(125))
    figure_count = 0
    for item in data['figures']:
        assert Path(item['file']).name == item['file']
        path = root / 'figures' / item['file']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['file']
        figure_count += 1
    for label, stats in collection['corpora'].items():
        assert 0 <= stats['unique_audio_sources'] <= stats['retained_audio_files']
        assert stats['retained_audio_files'] == stats['original_audio_retained'] + stats['compact_audio_retained']
        assert stats['unique_transcribed_sources'] <= stats['transcript_editions']
        assert stats['media_bytes'] >= 0 and stats['video_downloaded'] == 0
    for item in collection.get('figures', []):
        assert Path(item['file']).name == item['file']
        path = root / 'collection-figures' / item['file']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
        figure_count += 1
    ra = collection['corpora']['ra']
    assert ra['inventory_audio_total'] == 2620 and ra['transcript_editions'] == 106
    assert ra['unique_audio_sources'] <= ra['inventory_audio_total']
    if ra['download_status'] == 'completed':
        assert ra['unique_audio_sources'] == ra['compact_audio_retained'] == 2620
        assert ra['retained_audio_files'] == 2621 and ra['original_audio_retained'] == 1
    bashar = collection['corpora']['bashar']
    assert bashar['duration_eligible_profile_ids'] == 87 and bashar['official_profile_ids'] == 307
    pointer = collection.get('supplementary_studies', {}).get('official_speech')
    if pointer:
        assert pointer == 'official-speech.json'
        supplemental = json.loads((root / pointer).read_text())
        assert supplemental['schema_version'] == 1 and not supplemental.get('synthetic_fixture_run')
        assert sha(root / pointer) == collection['supplementary_sha256']
        safe_public(supplemental)
        for item in supplemental.get('figures', []):
            assert Path(item['file']).name == item['file']
            path = root / 'official-figures' / item['file']
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
            figure_count += 1
    for path in root.rglob('*'):
        if path.is_file():
            assert path.suffix.lower() not in {'.mp3', '.mp4', '.opus', '.wav', '.sqlite', '.jsonl', '.vtt', '.srt'}, path
    pdf = root / 'report/paper.pdf'
    if pdf.exists():
        body = pdf.read_bytes()
        assert body.startswith(b'%PDF-') and b'%%EOF' in body[-1024:]
        snapshot = json.loads((root / 'report/snapshot.json').read_text())
        safe_public(snapshot)
        assert snapshot['analysis_sha256'] == sha(root / 'data.json')
        assert snapshot['public_reading_sha256'] == sha(root / 'reading.json')
        assert not any(word in snapshot['status'].lower() for word in ('awaiting', 'pending'))
        package = json.loads((root / 'report/build-manifest.json').read_text())
        for artifact in package['files']:
            relative = Path(artifact['file'])
            assert not relative.is_absolute() and '..' not in relative.parts
            path = root / 'report' / relative
            assert path.stat().st_size == artifact['bytes'] and sha(path) == artifact['sha256'], relative
    return {'status': 'passed', 'primary_documents': 125, 'reference_documents': 5,
        'figures_verified': figure_count, 'analysis_sha256': sha(root / 'data.json'),
        'collection_sha256': sha(root / 'collection.json'), 'supplement_present': bool(pointer),
        'scope': 'Public artifact integrity and accounting; independent source/analysis reviews are separate.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.site), indent=2))
