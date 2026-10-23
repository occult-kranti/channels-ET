#!/usr/bin/env python3
"""Preserve an immutable expansion candidate and exact content manifest."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ATLAS = HERE.parents[1]
EXCLUDED_PARTS = {'rounds', '__pycache__', '.cache', 'screenshots'}
EXCLUDED_SUFFIXES = {'.aux', '.bbl', '.blg', '.log', '.out', '.pyc', '.toc'}


def selected_files():
    for base in (HERE, ATLAS/'dist/expansion'):
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            relative = path.relative_to(base)
            if not path.is_file() or any(p in EXCLUDED_PARTS for p in relative.parts):
                continue
            if path.suffix in EXCLUDED_SUFFIXES:
                continue
            yield path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('round', type=int, choices=(7, 8, 9))
    parser.add_argument('--description', required=True)
    args = parser.parse_args()
    dest = HERE/'rounds'/f'round{args.round}'
    dest.mkdir(parents=True, exist_ok=True)
    if (dest/'candidate.zip').exists():
        parser.error('Round already frozen; preserve the earlier candidate')
    rows = []
    with zipfile.ZipFile(dest/'candidate.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in selected_files():
            data = path.read_bytes()
            relative = str(path.relative_to(ATLAS))
            archive.writestr(relative, data)
            rows.append({'path': relative, 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest()})
    manifest = {'round': args.round, 'description': args.description,
                'frozenAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'panelType': 'AI-agent technical review, not human peer review',
                'baselineDataSha256': hashlib.sha256((ATLAS/'dist/analysis/data.json').read_bytes()).hexdigest(),
                'archiveSha256': hashlib.sha256((dest/'candidate.zip').read_bytes()).hexdigest(),
                'files': rows}
    (dest/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'round': args.round, 'files': len(rows),
                      'archiveSha256': manifest['archiveSha256']}))
