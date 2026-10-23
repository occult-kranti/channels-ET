#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Freeze PDF date metadata to the documented evidence date, not wall-clock build time.
export SOURCE_DATE_EPOCH=1792713600
export FORCE_SOURCE_DATE=1
python3 scripts/generate_paper.py
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass1.log
bibtex build/main > build/bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass2.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass3.log
cp build/main.pdf channeling-atlas-expansion-paper.pdf
python3 scripts/package_paper.py
