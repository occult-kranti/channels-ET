#!/usr/bin/env python3
"""Export a small private text bundle; never package source media into public Git."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile


def export(manifests, output, qa=None):
    repo = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(repo):
        raise ValueError('Full source text must remain outside the public repository')
    if output.exists():
        raise ValueError('Use a fresh output path; earlier bundles remain unchanged')
    candidate = output.with_suffix('.partial.zip')
    rows, excluded, seen, bindings = [], [], {}, []
    with zipfile.ZipFile(candidate, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for manifest in manifests:
            bindings.append({'file': manifest.name, 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()})
            for r in json.loads(manifest.read_text())['records']:
                if not r.get('text_artifact') or r.get('collection_status') not in {'retrieved', 'completed'}:
                    excluded.append({'source_id': r['source_id'], 'status': r.get('collection_status'), 'reason': r.get('hold_reason', r.get('eligibility_status'))})
                    continue
                artifact = r['text_artifact']
                path = Path(artifact['path'])
                raw = path.read_bytes()
                if len(raw) != artifact['bytes'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
                    raise ValueError('Source text binding changed')
                key = (r['source_id'], r['edition_id'])
                if key in seen:
                    if seen[key] != artifact['sha256']:
                        raise ValueError('Conflicting text editions')
                    continue
                seen[key] = artifact['sha256']
                data = json.loads(raw)
                text = data['text']
                stem = hashlib.sha256(('|'.join(key)).encode()).hexdigest()[:18]
                member = f"{r['corpus']}/{stem}.txt"
                archive.writestr(member, text.encode('utf-8'))
                archive.writestr(f"normalized/{r['corpus']}/{stem}.json", raw)
                rows.append({'file': member, 'source_id': r['source_id'], 'recording_id': r.get('recording_id', r['session_id']),
                    'edition_id': r['edition_id'], 'title': r['title'], 'source_url': r['source_url'],
                    'source_kind': r['source_kind'], 'source_format': r.get('source_format', ''),
                    'language': r.get('language', ''), 'coverage_status': r.get('coverage_status', ''),
                    'whitespace_words': len(text.split()), 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'normalized_json_sha256': artifact['sha256']})
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: "'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value
            for k, value in row.items()} for row in rows)
        archive.writestr('text-index.csv', stream.getvalue())
        archive.writestr('manifest.json', json.dumps({'source_manifests': bindings, 'records': rows, 'excluded': excluded}, indent=2, ensure_ascii=False))
        if qa:
            archive.write(qa, 'baseline-qa.sqlite')
        archive.writestr('README.txt', 'PRIVATE SOURCE-TEXT BUNDLE\n\nText, normalized turns/segments and a source/edition index. Media are stored separately, not duplicated here. Public excerpts remain partial original sessions; ASR/captions and OCR are not human-verified. Different editions and duplicate uploads are not independent recordings. The baseline QA database, when included, covers only its frozen study, not every later text. Source copyrights remain with their holders; this private bundle is not a public redistribution or training license.\n')
    with zipfile.ZipFile(candidate) as archive:
        if archive.testzip() is not None:
            raise ValueError('Export CRC check failed')
    candidate.rename(output)
    result = {'file': str(output), 'text_records': len(rows), 'whitespace_words': sum(r['whitespace_words'] for r in rows),
        'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'crc_check': 'passed'}
    output.with_suffix('.receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--qa', type=Path)
    a = p.parse_args()
    export(a.manifest, a.output, a.qa)
