# Expanded living manuscript

This is a new exploratory manuscript for the expansion phase, separate from the historical six-round paper. The public-video baseline remains 925 uploads. No new YouTube content was retrieved during the blocked initial preflight. The Q&A database contains AI-digest paraphrase candidates in one practitioner context, not a cross-medium transcript corpus.

Build from the repository root with:

```sh
bash channeling-atlas/research/expansion/paper/build.sh
```

The build reads the current expansion analysis, Q&A and acquisition summaries, regenerates values/tables, copies the six reviewed analysis figures, compiles the paper with PDFLaTeX and BibTeX, and packages the source. Required standard TeX packages are geometry, fontenc, inputenc, lmodern, graphicx, booktabs, longtable, array, amsmath, amssymb, natbib, url, hyperref, caption and enumitem. Python generation uses the standard library.

The build fixes PDF date metadata with `SOURCE_DATE_EPOCH=1792713600` and `FORCE_SOURCE_DATE=1`, the documented evidence date at UTC midnight, and fixes ZIP entry metadata. That timestamp is a reproducible build setting, not an observed collection time. Binary repeatability is checked on the same machine/path; clean-package verification additionally compares extracted page text.

`channeling-atlas-expansion-source.zip` is a standalone manuscript compilation package: extract it, select PDFLaTeX, and run PDFLaTeX, BibTeX on `main`, then PDFLaTeX twice. Generated tables and figure PDFs are included. It compiles the frozen manuscript; it does not execute collection or inference. The repository scripts and cited raw-input pointers support broader reconstruction.

`input-manifest.json` hashes the exact evidence summaries used; `artifact-manifest.json` identifies the resulting PDF and ZIP. `verification.json` records actual build, clean-package compilation and render checks. Historical review receipts do not certify this changed artifact. The new rounds are recorded in the expansion review directory.

Human authorship, affiliations, construct validation, institutional determination, rights review and final submission decisions remain pending. This is not a submitted or accepted paper, and model-agent reviews are not independent human peer review.
