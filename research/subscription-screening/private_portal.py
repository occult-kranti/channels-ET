#!/usr/bin/env python3
"""Generate a private media/text navigator without copying source recordings."""
import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote
import zipfile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def build(root, acquisition, asr, text_bundle=False, bashar_archive=None):
    repo = Path(__file__).resolve().parents[2]
    root = root.resolve()
    if root.is_relative_to(repo):
        raise ValueError('Private media navigator cannot be generated inside public Git')
    root.mkdir(parents=True, exist_ok=True)
    bashar_archive = bashar_archive or Path('/workspace/channels-et-private/bashar-ra-2026-11/index.html')
    raw = acquisition.read_bytes(); audio = json.loads(raw)
    speech_raw = asr.read_bytes(); speech = json.loads(speech_raw)
    completed = {r['publication_id']: r for r in speech.get('records', []) if r.get('status') == 'completed'}
    texts = root / 'caption-texts'; texts.mkdir(exist_ok=True)
    rows, bindings = [], [{'kind': 'acquisition', 'sha256': digest(raw)}, {'kind': 'asr', 'sha256': digest(speech_raw)}]
    def verify(artifact):
        p = Path(artifact['path'])
        if not p.is_file() or p.stat().st_size != artifact['bytes']:
            raise ValueError('Retained artifact is missing or has changed size')
        return p
    for r in audio['records']:
        if r.get('status') != 'completed': continue
        source = r['source']; media = verify(r['audio']); a = completed.get(r['publication_id'])
        transcript, transcript_kind = '', 'Pending or held; consult the ASR queue'
        if a:
            artifact = a['outputs']['text']; p = verify(artifact)
            if digest(p.read_bytes()) != artifact['sha256']: raise ValueError('ASR text hash changed')
            transcript = str(p); transcript_kind = 'Local ASR · speakers and accuracy unverified'
            if a.get('normalization_status'): transcript_kind += ' · ' + a['normalization_status']
        captions = (r.get('caption_link') or {}).get('records', [])
        if captions:
            artifact = captions[0]['text_artifact']; p = verify(artifact); body = p.read_bytes()
            if digest(body) != artifact['sha256']: raise ValueError('Caption text hash changed')
            value = json.loads(body); destination = texts / (artifact['sha256'][:24] + '.txt')
            destination.write_text(value['text'], encoding='utf-8')
            transcript = str(destination); transcript_kind = 'Publisher-hosted caption text · exact episode link, alignment unverified'
        rows.append({'publication_id': r['publication_id'], 'publisher': source['publisher'], 'title': source['title'],
            'source_url': source['source_url'], 'audio_path': str(media), 'audio_sha256': r['audio']['sha256'],
            'audio_bytes': r['audio']['bytes'], 'decoded_seconds': r['decoded_16k_mono']['duration_seconds'],
            'text_path': transcript, 'text_kind': transcript_kind})
    if len({r['publication_id'] for r in rows}) != len(rows): raise ValueError('Duplicate publication in portal')
    def local_link(path, label):
        if not path: return 'Pending / held'
        href = quote(os.path.relpath(path, root), safe='/')
        return '<a href="' + html.escape(href, quote=True) + '">' + html.escape(label) + '</a>'
    table = []
    for r in rows:
        search = html.escape(' '.join([r['publisher'], r['title'], r['publication_id']]).casefold(), quote=True)
        table.append('<tr data-search="' + search + '"><th scope="row">' + html.escape(r['title']) + '<small>' + html.escape(r['publisher']) + '</small></th><td>' + f"{r['decoded_seconds']/60:.1f} min · {r['audio_bytes']/1e6:.1f} MB" + '</td><td>' + local_link(r['audio_path'], 'Play / save Opus') + '</td><td>' + local_link(r['text_path'], 'Open text') + '<small>' + html.escape(r['text_kind']) + '</small></td><td><a href="' + html.escape(r['source_url'], quote=True) + '">Publisher</a></td></tr>')
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    title = 'Private publisher audio archive'
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + title + '</title><style>body{font:16px/1.5 system-ui;background:#f7f5ec;color:#183c32;max-width:1200px;margin:2rem auto;padding:0 1rem}a{color:#075e94}h1{font-size:2.2rem}small{display:block;font-size:.85rem;font-weight:normal}input{padding:.7rem;font:inherit;width:min(95%,38rem)}.scroll{overflow:auto}table{border-collapse:collapse;min-width:700px;width:100%}td,th{border-bottom:1px solid #bfcac0;text-align:left;padding:.8rem;vertical-align:top}th{width:35%}.note{border-left:4px solid #a15a30;padding:1rem;background:#fff}</style><h1>' + title + '</h1><p>' + f"{len(rows)} retained publisher audio sources · {sum(r['decoded_seconds'] for r in rows)/3600:.2f} decoded hours · {sum(bool(r['text_path']) for r in rows)} linked text files" + '</p><p class="note">Private managed-workspace files. These full-length 48 kbps Opus recordings are lossy derivatives; original encodings were verified before conversion. Text recognition and speaker identity are unverified. This is not permanent ChatGPT account storage or a YouTube upload census.</p><p>' + local_link(bashar_archive, 'Open Bashar–Ra archive') + ' · <a href="archive-index.csv">Download this file index</a></p><p>Snapshot: ' + now + '</p><label>Find a publisher, title or ID<br><input id="search" type="search" placeholder="Tracy, Multidimensional Soul, OmNa…"></label><div class="scroll"><table><thead><tr><th>Publication</th><th>Duration / size</th><th>Audio</th><th>Text</th><th>Source</th></tr></thead><tbody>' + ''.join(table) + '</tbody></table></div><script>document.querySelector("#search").addEventListener("input",e=>{const q=e.target.value.toLocaleLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.dataset.search.includes(q))})</script></html>'
    (root / 'index.html').write_text(page)
    def csv_safe(value):
        return "'" + value if isinstance(value, str) and value[:1] in ('=', '+', '-', '@') else value
    with (root / 'archive-index.csv').open('w', newline='') as f:
        fields = ['publication_id', 'publisher', 'title', 'source_url', 'audio_path', 'audio_sha256', 'audio_bytes', 'decoded_seconds', 'text_path', 'text_kind']
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        writer.writerows({k: csv_safe(v) for k, v in r.items()} for r in rows)
    manifest = {'generated_at': now, 'records': len(rows), 'text_links': sum(bool(r['text_path']) for r in rows), 'source_bindings': bindings,
        'scope': 'Private navigator; existing recordings are referenced, not duplicated. Snapshot counts do not imply final pipeline completion.'}
    if text_bundle:
        bundle = root / 'publisher-texts-snapshot.zip'
        items = []
        with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for r in rows:
                if not r['text_path']: continue
                body = Path(r['text_path']).read_bytes()
                name = 'texts/' + digest(r['publication_id'].encode())[:24] + '.txt'
                z.writestr(name, body)
                items.append({'publication_id': r['publication_id'], 'publisher': r['publisher'],
                    'title': r['title'], 'source_url': r['source_url'], 'text_kind': r['text_kind'],
                    'file': name, 'bytes': len(body), 'sha256': digest(body)})
            z.writestr('manifest.json', json.dumps({'snapshot': manifest, 'items': items}, indent=2, ensure_ascii=False) + '\n')
            z.writestr('README.txt', 'Private text snapshot; no recordings are duplicated in this ZIP.\nPublisher captions and local ASR are distinguished in manifest.json.\nRecognition accuracy, speaker identity and audio-text alignment remain unverified.\nThis snapshot does not claim every recording has text.\n')
        with zipfile.ZipFile(bundle) as z:
            if z.testzip() is not None: raise ValueError('Text bundle integrity failure')
            for item in items:
                if digest(z.read(item['file'])) != item['sha256']: raise ValueError('Text bundle hash mismatch')
        manifest['text_bundle'] = {'file': bundle.name, 'records': len(items), 'bytes': bundle.stat().st_size, 'sha256': digest(bundle.read_bytes())}
        page = page.replace('<a href="archive-index.csv">Download this file index</a>', '<a href="archive-index.csv">Download this file index</a> · <a href="publisher-texts-snapshot.zip">Download this text snapshot ZIP</a>')
        (root / 'index.html').write_text(page)
    (root / 'index-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path); p.add_argument('--acquisition', required=True, type=Path); p.add_argument('--asr', required=True, type=Path)
    p.add_argument('--text-bundle', action='store_true', help='Also create a private portable text-only ZIP')
    p.add_argument('--bashar-archive', type=Path, help='Optional existing private Bashar–Ra navigator path')
    a = p.parse_args(); build(a.root, a.acquisition, a.asr, a.text_bundle, a.bashar_archive)
