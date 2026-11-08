#!/usr/bin/env python3
"""Build a private, local archive navigator without copying media or source text."""
import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote


def build(root, manifests, ra_audio=None):
    root = root.resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError('Private index must be outside the public repository')
    rows, seen, bindings = [], set(), []
    for manifest in manifests:
        bindings.append({'manifest': str(manifest), 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()})
        for r in json.loads(manifest.read_text())['records']:
            if r['source_id'] in seen:
                raise ValueError('Duplicate source record; select explicit editions')
            seen.add(r['source_id'])
            text = Path(r['text_artifact']['path']) if r.get('text_artifact') else None
            if text and (not text.is_file() or text.stat().st_size != r['text_artifact']['bytes']):
                raise ValueError('Retained text missing/changed')
            audios = [e for e in r.get('evidence', []) if e.get('role') in ('source_audio', 'audio') and Path(e['path']).suffix.lower() != '.wav']
            if not audios and r.get('audio_artifact'):
                audios = [r['audio_artifact']]
            if not audios and r.get('retained_unadmitted_artifact'):
                audios = [r['retained_unadmitted_artifact']]
            for audio in audios:
                if not Path(audio['path']).is_file() or Path(audio['path']).stat().st_size != audio['bytes']:
                    raise ValueError('Retained source audio missing/changed')
            rows.append({'source_id': r['source_id'], 'title': r['title'], 'corpus': r['corpus'],
                'source_kind': r['source_kind'], 'source_format': r.get('source_format', ''),
                'source_url': r['source_url'], 'text_path': str(text) if text else '',
                'audio_path': audios[0]['path'] if audios else '',
                'duration_seconds': r.get('audio_duration_seconds', ''),
                'word_count': r.get('whitespace_words', r.get('asr_words', ''))})
    if ra_audio:
        bindings.append({'manifest': str(ra_audio), 'sha256': hashlib.sha256(ra_audio.read_bytes()).hexdigest()})
        data = json.loads(ra_audio.read_text())
        for r in data['records']:
            p = Path(r['retained']['path'])
            if not p.is_file() or p.stat().st_size != r['retained']['bytes']:
                raise ValueError('Retained compact file missing/changed')
            rows.append({'source_id': r['source_id'], 'title': f"Ra recording segment {r['question_id']}",
                'corpus': 'ra', 'source_kind': 'compact_audio', 'source_format': '48 kbps CBR Opus (lossy)',
                'source_url': r['url'], 'text_path': '', 'audio_path': str(p),
                'duration_seconds': r['retained']['decoded_duration_seconds'], 'word_count': ''})
    def link(path, title):
        if not path:
            return '—'
        rel = quote(os.path.relpath(path, root), safe='/')
        return '<a href="' + rel + '">' + html.escape(title) + '</a>'
    groups = []
    for corpus in ('ra', 'bashar'):
        body = []
        for r in rows:
            if r['corpus'] != corpus:
                continue
            body.append('<tr><th>' + html.escape(r['title']) + '</th><td>' + html.escape(r['source_format'] or r['source_kind']) + '</td><td>' + link(r['text_path'], 'Text / turns JSON') + '</td><td>' + link(r['audio_path'], 'Play / save audio') + '</td><td><a href="' + html.escape(r['source_url'], quote=True) + '">Publisher</a></td></tr>')
        groups.append('<details open><summary>' + corpus.capitalize() + ' · ' + str(len(body)) + ' indexed records</summary><div class="scroll"><table><thead><tr><th>Source</th><th>Kind</th><th>Text</th><th>Audio</th><th>Origin</th></tr></thead><tbody>' + ''.join(body) + '</tbody></table></div></details>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private Bashar–Ra archive</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;background:#faf8ef;color:#163e37}a{color:#075f9b}h1{font-size:2rem}summary{font-size:1.3rem;cursor:pointer;padding:1rem 0}table{border-collapse:collapse;width:100%}td,th{padding:.65rem;text-align:left;border-bottom:1px solid #ccd5ce}th{max-width:32rem}.scroll{overflow:auto}input{padding:.7rem;font:inherit;max-width:90%;width:30rem}</style><h1>Private Bashar–Ra archive</h1><p>Local navigator for retained files. This folder is managed workspace storage, not a permanent ChatGPT account archive. Download or copy files elsewhere for long-term preservation. Media and full text are not on the public dashboard.</p><p>Ra Opus files are full-length lossy conversions of published original-recording segments. The original pilot MP3 remains preserved. Ordered M3U playlists are in each session folder. A published transcript does not establish a surviving recording; Bashar excerpts are distinct from complete sessions, interviews and written references.</p><p><a href="archive-index.csv">Download file index CSV</a> · <a href="archive-index-manifest.json">Index provenance</a></p><label>Filter records <input type="search" id="filter" placeholder="Session, topic in title, source kind…"></label>''' + ''.join(groups) + '''<script>document.querySelector('#filter').addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))})</script></html>'''
    (root / 'index.html').write_text(page)
    with (root / 'archive-index.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (root / 'archive-index-manifest.json').write_text(json.dumps({'schema_version': 1,
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'records': len(rows),
        'manifest_bindings': bindings, 'scope': 'Private navigator; records can include multiple editions and audio segments, not unique sessions.'}, indent=2) + '\n')
    (root / 'START-HERE.md').write_text('''# Bashar and Ra private study archive

Open [the searchable local navigator](index.html), or [the file index CSV](archive-index.csv).

- `ra/transcripts/`: 106 published Lightly Edited sessions, source HTML, normalized text and turns.
- `ra/audio-compact/`: full-length 48 kbps CBR Opus segments, per-session playlists, source/output hashes and acquisition receipts. Completeness follows its current audio manifest.
- `ra/audio-pilot/`: preserved original MP3 pilot.
- `bashar/corpus/`: normalized copies and proofs for 19 retained interview/commentary transcripts. Original media is reused in its existing archive, linked by the navigator.
- `bashar/official-excerpt-corpus/`: first official excerpt's local ASR; subsequent batch manifests identify additional retained audio and transcripts.
- `bashar/official-platform-captions/`: separately retained publisher-hosted automatic captions.
- `bashar/official-pages/` and `bashar/official-handouts/`: written references, PDF originals, extraction/OCR and coverage receipts.
- `analysis/run-04/`: corrected frozen baseline analysis, figures, private Q&A SQLite and source provenance. Earlier runs are preserved as superseded; the official-speech follow-on is separate.
- `reading/`: source-linked interpretation and exact sampled-reading coverage.
- `capacity/`: acquisition and methodological reviews, resource decisions and cache-cleanup proofs.

These are managed cloud workspace files. No Google Drive transfer or permanent ChatGPT-account storage is implied. Raw copyrighted material remains private; public release contains aggregates, metadata and bounded paraphrases. ASR and source claims are unverified. No old source archives were removed.
''')
    print(json.dumps({'private_index_records': len(rows), 'output': str(root / 'index.html')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--manifest', type=Path, action='append', required=True)
    p.add_argument('--ra-audio', type=Path)
    a = p.parse_args()
    build(a.root, a.manifest, a.ra_audio)
