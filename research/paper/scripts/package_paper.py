#!/usr/bin/env python3
"""Export the reviewed manuscript and a self-contained Overleaf import package."""
from pathlib import Path
import hashlib, json, shutil, zipfile

ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / 'research/paper'
PUBLIC = ROOT / 'dist/analysis'
EXPORT = PUBLIC / 'paper'
EXPORT.mkdir(parents=True, exist_ok=True)
sha = lambda b: hashlib.sha256(b).hexdigest()

# Derived public results only; no caption text, model weights, or build environment.
for p in sorted((PAPER / 'generated').glob('*')):
    if p.is_file() and p.suffix in {'.json', '.csv', '.npz', '.md'}:
        shutil.copy2(p, EXPORT / p.name)
for p in sorted((PAPER / 'generated/figures').glob('*.png')):
    shutil.copy2(p, EXPORT / p.name)
shutil.copy2(PAPER / 'literature/source-register.csv', EXPORT / 'bibliography.csv')
shutil.copy2(PAPER / 'literature/annotated-bibliography.md', EXPORT / 'annotated-bibliography.md')
shutil.copy2(PAPER / 'build/main.pdf', PUBLIC / 'channeling-atlas-paper.pdf')

files = {}
for name in ['main.tex', 'body.tex', 'references.bib']:
    files[name] = (PAPER / name).read_bytes()
for name in ['aaai2027.sty', 'aaai2027.bst']:
    files[name] = (PAPER / 'vendor/AuthorKit27' / name).read_bytes()
for p in sorted((PAPER / 'generated').glob('*.tex')):
    files[str(p.relative_to(PAPER))] = p.read_bytes()
for p in sorted((PAPER / 'generated/figures').glob('*.pdf')):
    files[str(p.relative_to(PAPER))] = p.read_bytes()
for name in ['reviews/design/icwsm-checklist-working.tex', 'vendor/source-license-manifest.json']:
    files[name] = (PAPER / name).read_bytes()
files['README.md'] = b'''# Channeling Atlas working manuscript\n\nImport this ZIP into Overleaf, choose PDFLaTeX and main.tex, then compile.\nThe unchanged official AAAI 2027 style is at the ZIP root. The source uses\nits supported preprint option. This is a working research draft, not a\nsubmitted, accepted, or venue-compliance-certified paper.\n\nHuman authorship, institutional ethics determination, construct validation,\nand all official checklist answers remain TBD. The model-agent reviews\nare not independent human peer review.\n\nTables and figures are frozen outputs from the linked research repository:\nhttps://github.com/occult-kranti/channels-ET/tree/main/research/paper\nThe package compiles the paper; it does not run collection or inference.\nRaw captions and model weights are not included. The manuscript describes\nwhat can be reproduced from the public derived data and what needs source text.\n\nFor local compilation, install PDFLaTeX/BibTeX and the dependencies listed\nin the repository README. Run pdflatex main, bibtex main, then pdflatex main\ntwice. Preserve prior releases and rerun the documented analysis pipeline\nbefore editing numerical claims.\n'''
manifest = {'evidenceSnapshot': '2026-10-23', 'scope': 'Manuscript compilation source, generated tables and figures, official template files.', 'files': {k: sha(v) for k, v in sorted(files.items())}}
files['package-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
zip_path = PUBLIC / 'channeling-atlas-overleaf.zip'
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for name, contents in sorted(files.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, contents)
release = {'pdfSha256': sha((PUBLIC / 'channeling-atlas-paper.pdf').read_bytes()), 'overleafSha256': sha(zip_path.read_bytes()), 'overleafFiles': len(files), 'analysisDataSha256': sha((PUBLIC / 'data.json').read_bytes()), 'generatedResultsSha256': sha((PAPER / 'generated/paper-results.json').read_bytes())}
(EXPORT / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
print(json.dumps(release))
