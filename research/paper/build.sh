#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
export TEXINPUTS="$(pwd)/vendor/AuthorKit27:${TEXINPUTS:-}"
export BSTINPUTS="$(pwd)/vendor/AuthorKit27:${BSTINPUTS:-}"
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass1.log
bibtex build/main > build/bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass2.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass3.log
cp build/main.pdf ../../dist/analysis/channeling-atlas-paper.pdf
printf '%s\n' 'Built dist/analysis/channeling-atlas-paper.pdf'
