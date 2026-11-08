#!/usr/bin/env bash
set -euo pipefail
paper_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$paper_dir/../../.." && pwd)
report_dir="$repo_root/dist/bashar-ra/report"
cd "$paper_dir"
mkdir -p "$report_dir/figures" .build
pandoc paper.md --standalone --citeproc --from=markdown --to=latex --lua-filter=vector-figures.lua --include-in-header=header.tex --resource-path=. --output=paper.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build paper.tex > .build/pdflatex-pass1.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build paper.tex > .build/pdflatex-pass2.log
cp .build/paper.pdf "$report_dir/paper.pdf"
cp paper.md paper.tex references.bib snapshot.json README.md build.sh vector-figures.lua header.tex refresh_snapshot.py refresh_official_supplement.py "$report_dir/"
cp figures/*.png figures/*.pdf "$report_dir/figures/"
python3 - "$report_dir" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); files=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.name!='build-manifest.json':
        files.append({'file':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'build-manifest.json').write_text(json.dumps({'schema_version':1,'kind':'public-living-research-paper','files':files},indent=2)+'\n')
PY
printf 'Built %s\n' "$report_dir/paper.pdf"
