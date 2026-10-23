# Living research paper: continuation rounds 10–12

This is the current manuscript in `occult-kranti/channels-ET`. Historical paper releases remain separately preserved. The official AAAI 2027 preprint style is unchanged; the document is a living exploratory draft, not a submitted or accepted paper or a certification of ICWSM compliance.

From this repository root:

```sh
bash research/continuation/paper/build.sh
```

The builder regenerates values from current source artifacts, copies reviewed analytical plots, compiles with PDFLaTeX/BibTeX, and creates `channels-et-paper.pdf` and `channels-et-source.zip`. `input-manifest.json` identifies the current evidence files; `artifact-manifest.json` identifies the PDF and ZIP. Evidence-date metadata and ZIP entries are fixed for repeatable same-environment builds. That metadata date is not a collection timestamp.

Use the standalone `/workspace/channels-et-analysis-venv`, prepared with this repository's `research/analysis/requirements.txt`; no original Bashar checkout is required. Set `CHANNELS_ET_ANALYSIS_PYTHON` to another explicitly prepared interpreter when using a different workspace layout. The figure generator uses the pinned scientific dependencies; the manuscript result generator otherwise uses Python's standard library.

Standard TeX packages and the `newtx` font dependencies are required. If the local font tree is absent, `scripts/setup_tex.py` downloads four CTAN packages, verifies the retained SHA-256 pins, and creates a local `/workspace/channels-et-tex` tree. It never edits global TeX configuration or substitutes the official style. Download/source information is in `tex-dependencies.json`. An archive checksum change requires diagnosis, not updating a pin simply to make installation pass.

The standalone source ZIP compiles the frozen manuscript with PDFLaTeX, BibTeX on `main`, and two further PDFLaTeX passes. A standard Overleaf environment supplies the TeX packages. The ZIP includes the official style and bibliography style at its root plus all generated tables and figure PDFs. It does not execute collection, model training or inference, and does not include raw captions or model weights.

Current local-model results appear only when an executed benchmark receipt exists. Package installation, a running process or a training plan is not a result. Q&A candidates remain derivative digests in one practitioner context; model outputs are research outputs, not verified physical claims. Human authorship, construct validation, institutional determination, rights review and concrete submission decisions remain TBD.
