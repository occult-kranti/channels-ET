#!/usr/bin/env bash
set -euo pipefail
cd /workspace/channels-ET

python3 -m venv /workspace/channels-et-analysis-venv
/workspace/channels-et-analysis-venv/bin/python -m pip install --no-cache-dir -r research/continuation/analysis/environment-freeze.txt
/workspace/channels-et-analysis-venv/bin/python -m pip check

python3 -m venv /workspace/channels-et-harvest-venv
/workspace/channels-et-harvest-venv/bin/python -m pip install --no-cache-dir -r research/harvest/environment-freeze.txt
/workspace/channels-et-harvest-venv/bin/python -m pip check

python3 -m venv /workspace/channels-et-asr-venv
/workspace/channels-et-asr-venv/bin/python -m pip install --no-cache-dir -r research/harvest/asr/environment-freeze.txt
/workspace/channels-et-asr-venv/bin/python -m pip check

for research_tool in node ffmpeg ffprobe pdflatex bibtex pdftotext pdfinfo pdffonts pdftoppm; do
  command -v "$research_tool" >/dev/null
done
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) process.exit(1)'
if [ ! -f /workspace/channels-et-tex/texmf/tex/latex/newtx/newtxtext.sty ]; then
  /workspace/channels-et-analysis-venv/bin/python research/continuation/paper/scripts/setup_tex.py
fi

# Model download and live collection are explicit commands, not setup side effects.
/workspace/channels-et-harvest-venv/bin/python -c 'from importlib.metadata import version; assert version("yt-dlp") == "2026.10.21"; assert version("yt-dlp-ejs") == "0.8.0"'
/workspace/channels-et-asr-venv/bin/python -c 'from importlib.metadata import version; assert version("av") == "16.1.0"; import faster_whisper'

# Isolated schema/control validation for the current long-form collection layer.
python3 -m venv /workspace/channels-et-collection-venv
/workspace/channels-et-collection-venv/bin/python -m pip install --no-cache-dir -r research/youtube-access/environment-freeze.txt
/workspace/channels-et-collection-venv/bin/python -m pip check
