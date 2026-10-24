#!/usr/bin/env python3
"""Package a deterministic standalone Overleaf compilation bundle; no raw text."""
import hashlib
import json
from pathlib import Path
import zipfile

PAPER = Path(__file__).resolve().parents[1]
names = ['main.tex', 'body.tex', 'appendices.tex', 'references.bib', 'aaai2027.sty',
         'aaai2027.bst', 'README.md', 'protocol.json', 'input-manifest.json']
files = [PAPER / name for name in names] + sorted(p for p in (PAPER / 'generated').rglob('*') if p.is_file())
files += [PAPER / 'build.sh'] + sorted((PAPER / 'scripts').glob('*.py'))
target = PAPER / 'channels-et-transcript-source.zip'
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        info = zipfile.ZipInfo(str(path.relative_to(PAPER)), date_time=(2026, 10, 24, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, path.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt = {'status': 'living_research_draft', 'pdf_sha256': sha(PAPER / 'channels-et-transcript-paper.pdf'),
           'source_zip_sha256': sha(target), 'source_members': len(files),
           'raw_speech_or_full_third_party_text_included': False,
           'style': 'Unmodified official AAAI2027 preprint; venue compliance is not certified.'}
(PAPER / 'artifact-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
