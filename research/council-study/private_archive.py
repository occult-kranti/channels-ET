#!/usr/bin/env python3
"""Build a private Council text bundle and links to existing retained recordings."""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(ref):
    path = Path(ref['path'])
    raw = path.read_bytes()
    if len(raw) != ref['bytes'] or sha(raw) != ref['sha256']:
        raise ValueError('Source artifact has changed')
    return path, raw


def build(manifests, output):
    output = output.resolve()
    private = Path('/workspace/channels-et-private')
    if not output.is_relative_to(private) or output.exists():
        raise ValueError('Choose a fresh private output directory')
    rows, bindings, seen = [], [], set()
    for path in manifests:
        raw = path.read_bytes()
        data = json.loads(raw)
        bindings.append({'file': path.name, 'bytes': len(raw), 'sha256': sha(raw)})
        for d in data.get('documents', data.get('records', [])):
            sid = d['source_id']
            if sid in seen:
                raise ValueError('Duplicate source ID in archive')
            seen.add(sid)
            ref = d.get('plain_text_artifact', d['text_artifact'])
            path, body = checked(ref)
            text = json.loads(body)['text'] if path.suffix == '.json' else body.decode('utf-8')
            if len(text.split()) != d['words']:
                raise ValueError('Text word count differs from source manifest')
            url = d['canonical_url']
            if urlsplit(url).scheme not in ('https', 'http'):
                raise ValueError('Unexpected source URL scheme')
            audio_path = None
            audio = d.get('audio_artifact')
            if audio:
                audio_path, _ = checked(audio)
            rows.append({'source_id': sid, 'title': d['title'], 'source_url': url,
                'medium': d.get('medium_name', 'Unresolved'),
                'claimed_name': d.get('council_label', d.get('council_label_exact', 'Unresolved')),
                'scope': d.get('attribution_scope', d.get('text_scope', 'See source manifest')),
                'words': d['words'], 'text_sha256': sha(text.encode()),
                'text_file': 'texts/' + sha(sid.encode())[:24] + '.txt',
                'audio_path': str(audio_path) if audio_path else None,
                'audio_sha256': audio['sha256'] if audio else None,
                '_text': text})
    output.mkdir(parents=True, mode=0o700)
    portable = [{k: v for k, v in r.items() if k not in ('_text', 'audio_path')} for r in rows]
    manifest = {'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'text_records': len(rows), 'audio_records': sum(bool(r['audio_path']) for r in rows),
        'words': sum(r['words'] for r in rows), 'input_bindings': bindings, 'records': portable,
        'scope': 'Private source-edition archive; no recordings duplicated. Recognition, speaker identity and council identity remain unverified.'}
    bundle = output / 'council-texts.zip'
    with zipfile.ZipFile(bundle, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
        z.writestr('README.txt', 'Private Council study text editions.\nSee manifest.json for source attribution, hashes and scope.\nAudio is retained separately in the managed workspace.\nASR is unverified; a discussed council is not necessarily the attributed speaker.\n')
        for r in rows:
            z.writestr(r['text_file'], r['_text'])
    with zipfile.ZipFile(bundle) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP integrity failure')
        for r in rows:
            if sha(z.read(r['text_file'])) != r['text_sha256']:
                raise ValueError('ZIP text hash mismatch')
    manifest['bundle'] = {'file': bundle.name, 'bytes': bundle.stat().st_size, 'sha256': sha(bundle.read_bytes())}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    cells = []
    for r in rows:
        audio = ('<a href="' + html.escape(quote(os.path.relpath(r['audio_path'], output), safe='/'), quote=True)
                 + '">Open retained Opus audio</a>') if r['audio_path'] else 'Written source; no audio in this archive'
        cells.append('<tr><th scope="row">' + html.escape(r['title']) + '<small>' + html.escape(r['medium'])
                     + '</small></th><td>' + html.escape(r['claimed_name']) + '</td><td>' + f"{r['words']:,}"
                     + '</td><td>' + audio + '</td><td><a href="' + html.escape(r['source_url'], quote=True) + '">Publisher</a></td></tr>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private Council archive</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;background:#f6f3e9;color:#193e34}small{display:block;font-weight:normal}.scroll{overflow:auto}table{border-collapse:collapse;min-width:700px}th,td{padding:1rem;text-align:left;border-bottom:1px solid #bcc8be}a{color:#075c86}</style><h1>Private Council study archive</h1><p>' + str(len(rows)) + ' text editions · ' + str(manifest['audio_records']) + ' referenced recordings</p><p><a href="council-texts.zip">Download all text editions and source metadata</a> · <a href="manifest.json">Archive manifest</a></p><p>Recordings remain in their original archive folders. Audio links work inside this managed workspace; they are not public streams or permanent ChatGPT storage. Opus files are full-duration lossy derivatives with edition-specific encoding settings. Automatic text and speaker identities remain unverified.</p><div class="scroll"><table><thead><tr><th>Publication</th><th>Attributed name</th><th>Words</th><th>Audio</th><th>Source</th></tr></thead><tbody>' + ''.join(cells) + '</tbody></table></div></html>'
    (output / 'index.html').write_text(page)
    print(json.dumps({k: manifest[k] for k in ('text_records', 'audio_records', 'words', 'bundle')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.manifest, args.output)
