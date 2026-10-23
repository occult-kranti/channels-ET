#!/usr/bin/env python3
"""Package a standalone LaTeX manuscript without raw captions/model weights."""
import hashlib,json,pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
archive=root/'channeling-atlas-expansion-source.zip'
paths=[root/'main.tex',root/'body.tex',root/'appendices.tex',root/'references.bib',root/'input-manifest.json',root/'README.md']+sorted((root/'generated').rglob('*'))
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(paths):
        if p.is_file():
            info=zipfile.ZipInfo(str(p.relative_to(root)),date_time=(2026,10,23,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes())
manifest={'pdf_sha256':hashlib.sha256((root/'channeling-atlas-expansion-paper.pdf').read_bytes()).hexdigest(),'source_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'packaged_files':sum(p.is_file() for p in paths),'compile':'PDFLaTeX -> BibTeX -> PDFLaTeX twice','limitations':['Working draft; not submitted or accepted.','No human construct validation or raw-caption re-inference is claimed.','Source package compiles the paper; full data recomputation uses repository expansion scripts.']}
(root/'artifact-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
