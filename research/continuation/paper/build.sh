#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
paper_python="${CHANNELS_ET_ANALYSIS_PYTHON:-/workspace/channels-et-analysis-venv/bin/python}"
if [ ! -x "$paper_python" ]; then
  echo 'Prepare /workspace/channels-et-analysis-venv with research/analysis/requirements.txt before building the research paper.' >&2
  exit 1
fi
export SOURCE_DATE_EPOCH=1792713600
export FORCE_SOURCE_DATE=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/workspace/channels-et-tex/matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/workspace/channels-et-tex/cache}"
if [ ! -f /workspace/channels-et-tex/texmf/tex/latex/newtx/newtxtext.sty ]; then
  "$paper_python" scripts/setup_tex.py
fi
export TEXMFHOME=/workspace/channels-et-tex/texmf
export TEXMFVAR=/workspace/channels-et-tex/var
export TEXMFCONFIG=/workspace/channels-et-tex/config
export TEXINPUTS="$(pwd)/vendor//:${TEXINPUTS:-}"
export BSTINPUTS="$(pwd)/vendor//:${BSTINPUTS:-}"
"$paper_python" scripts/evidence_flow.py
"$paper_python" scripts/generate.py
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass1.log
bibtex build/main > build/bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass2.log
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass3.log
cp build/main.pdf channels-et-paper.pdf
"$paper_python" scripts/package.py
