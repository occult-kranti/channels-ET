# Source-bound knowledge-bank supplement

This additive AI-assisted technical report preserves earlier project papers. It is not peer reviewed or submitted. Authorship/maintainer and human validation: TBD.

`report.pdf` is the reading copy, `report.md` is the readable source, and `main.tex` plus `figures/` is the self-contained typesetting source. `source.zip` contains those sources, README and input bindings, but no raw corpus, audio, full transcripts, model weights or private paths. `manifest.json` binds accepted inputs and generated artifacts.

## Rebuild

```sh
python research/knowledge-bank/report/build.py \
  --analysis ACCEPTED_ANALYSIS_JSON \
  --knowledge ACCEPTED_KNOWLEDGE_JSON \
  --retrieval ACCEPTED_RETRIEVAL_JSON \
  --asr ACCEPTED_PAIRED_ASR_JSON \
  --literature research/knowledge-bank/literature-register.json
```

Optional completed full-audio inputs must be supplied together: `--asr-full COMPLETED_MANIFEST_JSON --sensitivity ACCEPTED_SENSITIVITY_JSON`. The sensitivity binding must match the full manifest. Optional `--asr-full-public ACCEPTED_PUBLIC_FULL_ASR_JSON` adds runtime metrics only after verifying its binding to that same private manifest. Optional `--contextual-terms ACCEPTED_CONTEXTUAL_JSON` adds the separately scoped target-token exploration and its verified figure. Main analysis, retrieval and paired-ASR hashes are pinned to reviewed releases; changing those requires review and a deliberate pin update. Two abstract-level primary references are retained in `additional-references.json`, supplementing the original 14-record literature register.

Requirements: Python 3.10+, Pandoc, pdfLaTeX with standard LaTeX packages. Numerical models are not rerun by this report builder. It reads and verifies existing outputs. Temporary compilation goes to `/dev/shm`; durable report artifacts are capped at 5 MB. From an extracted source ZIP, run `pdflatex -interaction=nonstopmode -halt-on-error main.tex` twice. The PDF build is not claimed byte-reproducible because TeX timestamps/metadata can vary; figure and input numerical hashes remain explicit.

## Reading boundaries

Twenty-five source editions are modeled, fourteen are closely read, and four queries are a diagnostic. Naive RRF is a diagnosed coverage-bias condition; the top-five repair is post-hoc. ASR disagreement is not WER or accuracy. Source-card consolidation is external indexing, not Google's parameter-training Sleep algorithm. Full text and speech evidence remain in the private evidence archive.
