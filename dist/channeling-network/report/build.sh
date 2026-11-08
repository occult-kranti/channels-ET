#!/usr/bin/env bash
# Portable local build: run inside a checkout or the downloaded report directory.
set -euo pipefail
paper_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$paper_dir"
for dependency in pandoc pdflatex python3; do
  command -v "$dependency" >/dev/null || { printf 'Missing build dependency: %s\n' "$dependency" >&2; exit 1; }
done
mkdir -p .build
pandoc paper.md --standalone --citeproc --from=markdown --to=latex --lua-filter=vector-figures.lua --include-in-header=header.tex --resource-path=. --output=paper.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build paper.tex > .build/pdflatex-pass1.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build paper.tex > .build/pdflatex-pass2.log
cp .build/paper.pdf paper.pdf
python3 - <<'PY'
import hashlib,json,pathlib,subprocess
root=pathlib.Path('.');files=[]
for p in sorted(root.rglob('*')):
    if not p.is_file() or '.build' in p.parts or '__pycache__' in p.parts or p.name=='build-manifest.json':continue
    files.append({'file':p.as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'schema_version':1,'kind':'expanded-channeling-companion-paper','inputs':'snapshot.json; frozen public model outputs and source graph','tools':{'pandoc':subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0],'pdflatex':subprocess.check_output(['pdflatex','--version'],text=True).splitlines()[0]},'human_authorship':'TBD','human_peer_review':False,'media_progress_counts_included':False,'files':files}
(root/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
printf 'Built %s\n' "$paper_dir/paper.pdf"
