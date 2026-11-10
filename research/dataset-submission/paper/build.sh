#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
export TEXINPUTS="$(pwd)/vendor:${TEXINPUTS:-}"
export BSTINPUTS="$(pwd)/vendor:${BSTINPUTS:-}"
# Optional existing cloud font tree; a standard complete TeX installation needs none.
if [ -z "${TEXMFHOME:-}" ] && [ -d /workspace/channels-et-tex/texmf ]; then
  export TEXMFHOME=/workspace/channels-et-tex/texmf
  export TEXMFVAR=/workspace/channels-et-tex/var
  export TEXMFCONFIG=/workspace/channels-et-tex/config
fi
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex > build/pass1.log
bibtex build/paper > build/bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex > build/pass2.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex > build/pass3.log
cp build/paper.pdf paper.pdf
python package.py
