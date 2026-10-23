#!/usr/bin/env python3
"""Freeze a distinct rounds 10–12 candidate without weights or raw media."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKIP = {'rounds', '__pycache__', 'build', 'cache', 'checkpoints'}
SKIP_SUFFIXES = {'.aux', '.log', '.blg', '.out', '.pyc', '.gguf', '.safetensors', '.bin'}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('round', type=int, choices=(10, 11, 12))
    p.add_argument('--description', required=True)
    args = p.parse_args()
    dest = HERE/'rounds'/f'round{args.round}'
    dest.mkdir(parents=True, exist_ok=True)
    target = dest/'candidate.zip'
    if target.exists():
        p.error('Round already frozen; do not replace earlier evidence')
    rows = []
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for base in (HERE, ROOT/'dist/research'):
            if not base.exists():
                continue
            for path in sorted(base.rglob('*')):
                if not path.is_file() or any(x in SKIP for x in path.relative_to(base).parts):
                    continue
                if path.suffix in SKIP_SUFFIXES:
                    continue
                blob = path.read_bytes()
                name = str(path.relative_to(ROOT))
                z.writestr(name, blob)
                rows.append({'path': name, 'bytes': len(blob), 'sha256': sha(blob)})
    manifest = {'round': args.round, 'description': args.description,
                'frozenAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'reviewType': 'AI-agent technical review; not human peer review',
                'archiveSha256': sha(target.read_bytes()), 'files': rows}
    (dest/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'round': args.round, 'files': len(rows),
                      'archiveSha256': manifest['archiveSha256']}))
