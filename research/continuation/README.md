# Living ET-channel study

This is the current cross-channel research home. `occult-kranti/bashar-index` is
preserved as a separate project. The current work adds to the existing Atlas and
keeps earlier papers, datasets and model-agent reviews accessible.

Start with the [working paper](paper/channels-et-paper.pdf),
[Overleaf source ZIP](paper/channels-et-source.zip),
[dashboard](../../dist/research/index.html), [source register](literature/source-register.json)
and [continuation protocol](PROTOCOL.md). Upload the source ZIP as an Overleaf
project with `main.tex` as the main document. No hosted Overleaf project was created.

## Rebuild from the retained evidence

From the repository root, install the pinned analytical dependencies in an external
virtual environment. This does not require model weights or credentials.

```sh
python3 -m venv /workspace/channels-et-analysis-venv
/workspace/channels-et-analysis-venv/bin/python -m pip install -r research/continuation/analysis/environment-freeze.txt
/workspace/channels-et-analysis-venv/bin/python -m pip check
/workspace/channels-et-analysis-venv/bin/python research/continuation/build.py
```

PDFLaTeX, BibTeX, standard TeX packages, `pdftotext`, `pdfinfo` and `pdffonts` are
installed in this cloud image. The paper builder downloads checksum-pinned CTAN
font dependencies only when their external local tree is missing. Once installed,
the retained-source rebuild needs no network. `--skip-expansion` reuses historical
expansion outputs; `--skip-paper` keeps existing PDFs and does not validate a fresh
paper compilation. The builder audits saved neural outputs and the released
adapter; it explicitly skips exact tokenizer reconstruction and never runs live
collection, training or generation. Those replay instructions are in
[models/README.md](models/README.md).

Serve the repository root with `python3 -m http.server 8000 --bind 127.0.0.1`.
The root routes to `dist/research/`; legacy Atlas hash routes remain available.
The static dashboard requires no application server, database service or model
process. Browser checks in `dashboard/` use Chromium and Playwright available in
this cloud image. Publication to a hosted service remains separate.

## Evidence and compute boundaries

- Inherited source: 925 upload records; 30 English-caption vectors without their
  raw caption text; 949 AI-digest Q&A candidates from one practitioner context.
  These are not verified speaker turns or a multi-medium answer corpus.
- Actual pilot: CPU Qwen2.5-0.5B base generation, training-only RAG, a 48-example
  LoRA run and five-arm evaluation on eight source-quarantined questions plus
  two unsupported controls. A separate twelve-excerpt labeling probe retains
  malformed output and invalid evidence spans. These experiments do not validate
  a scientific claim or establish a reliable model ranking.
- Current-family feasibility: Qwen3.5-0.8B actually loaded and generated provenance
  JSON on CPU in a separate modern runtime. It also processed the same twelve
  annotation excerpts: twelve outputs parsed and five exact short evidence spans
  passed, compared with nine parsed/zero valid spans for the older baseline.
  Its all-yes conditional labels only match the always-yes dictionary baseline.
  Neither test establishes human accuracy, state-of-the-art performance or image/video capability.
  The machine has a four-CPU quota, 32 GiB memory and no detected CUDA GPU.
- Live acquisition: executable resumable search/channel/caption/media collectors,
  quota controls and an indexed queue are provided. Ordinary YouTube and author
  transcript requests returned HTTP 403. No successful new raw transcript or video
  downloads are claimed; complete-channel coverage is unestablished.

## Organization

| Location | Contents |
|---|---|
| `research/expansion/` | Migrated historical rounds 7–9, keyword extraction, Q&A database and prior paper |
| `acquisition/` | Public-channel crawler, access receipts, corpus SQLite and quota tests |
| `analysis/` | Exploratory source-aware calculations, six scientific figure families and independent numerical audits |
| `literature/` | Newly checked papers, full-text access depth, official venue guidance and independent reviews |
| `models/` | Executed predictions, grouped split, training receipt, pilot adapter ZIP and reproducible scripts |
| `paper/` | Living LaTeX source, generated tables/plots, PDF and standalone Overleaf ZIP |
| `dashboard/` | Interface source and actual browser receipts |
| `rounds/`, `reviews/` | Frozen candidates and three further AI-agent technical-review cycles |

Model weights, training intermediates and raw media stay outside Git. The small
pilot adapter ZIP carries its base revision, license, training source hashes and
limitations. Human labels, multi-practitioner transcript comparisons, semantic
claim agreement, broader model evaluation and manuscript submission decisions
remain explicit TBDs in the paper and handoff.
