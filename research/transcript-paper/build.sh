#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
paper_python="${CHANNELS_ET_ANALYSIS_PYTHON:-/workspace/channels-et-analysis-venv/bin/python}"
export SOURCE_DATE_EPOCH=1792800000
export FORCE_SOURCE_DATE=1
export TEXMFHOME=/workspace/channels-et-tex/texmf
export TEXMFVAR=/workspace/channels-et-tex/var
export TEXMFCONFIG=/workspace/channels-et-tex/config
export MPLCONFIGDIR=/tmp/channels-et-transcript-paper-mpl
export XDG_CACHE_HOME=/tmp/channels-et-transcript-paper-cache
"$paper_python" scripts/generate.py
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass1.log
bibtex build/main > build/bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass2.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass3.log
cp build/main.pdf channels-et-transcript-paper.pdf
"$paper_python" scripts/package.py
