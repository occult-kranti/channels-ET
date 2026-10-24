#!/usr/bin/env python3
"""Compile the actual source ZIP and render the exact candidate, offline."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((PAPER / 'input-manifest.json').read_text())
for row in manifest['files']:
    path = ROOT / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
work = Path(tempfile.mkdtemp(prefix='transcript-paper-clean-', dir='/workspace'))
with zipfile.ZipFile(PAPER / 'channels-et-transcript-source.zip') as archive:
    for member in archive.namelist():
        assert not member.startswith('/') and '..' not in Path(member).parts
    archive.extractall(work)
environment = dict(os.environ, TEXMFHOME='/workspace/channels-et-tex/texmf',
                   TEXMFVAR='/workspace/channels-et-tex/var', TEXMFCONFIG='/workspace/channels-et-tex/config',
                   SOURCE_DATE_EPOCH='1792800000', FORCE_SOURCE_DATE='1')
commands = [['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'], ['bibtex', 'main'],
            ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
            ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex']]
for i, command in enumerate(commands):
    result = subprocess.run(command, cwd=work, env=environment, text=True, capture_output=True)
    (work / f'compile-{i}.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
pdf = PAPER / 'channels-et-transcript-paper.pdf'
text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'])
clean_text = subprocess.check_output(['pdftotext', '-layout', str(work / 'main.pdf'), '-'])
assert text == clean_text, 'Standalone source package changes extracted page text'
log = (PAPER / 'build/pass3.log').read_text()
assert not re.search(r'Overfull|undefined', log, re.I), 'Layout or citation warning requires correction'
fonts = subprocess.check_output(['pdffonts', str(pdf)], text=True)
assert 'Type 3' not in fonts
assert all(row.split()[-5] == 'yes' for row in fonts.splitlines()[2:])
info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
pages = int(re.search(r'^Pages:\s+(\d+)', info, re.M).group(1))
render = work / 'render'
render.mkdir()
subprocess.run(['pdftoppm', '-png', '-scale-to', '1400', str(pdf), str(render / 'page')], check=True, capture_output=True)
assert len(list(render.glob('page-*.png'))) == pages
report = {'status': 'PASS', 'pdf_sha256': sha(pdf), 'source_zip_sha256': sha(PAPER / 'channels-et-transcript-source.zip'),
          'pages': pages, 'input_hashes_verified': len(manifest['files']),
          'clean_source_compilation': {'directory': str(work), 'commands': commands, 'all_exit_zero': True,
                                       'extracted_page_text_identical': True},
          'latex': {'overfull_boxes': 0, 'undefined_citations_or_references': 0},
          'fonts': {'all_embedded': True, 'no_type3': True, 'report': fonts},
          'render': {'directory': str(render), 'pages_rendered': pages,
                     'visual_inspection': 'Pending exact-candidate page inspection; rendering is not inspection.'},
          'scope': 'Local artifact verification, not human review or venue-compliance certification.'}
(PAPER / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
