# Living research manuscript

This is an exploratory working draft, not a submitted or accepted paper. Human authorship, institutional ethics determination, human annotation, and venue-specific checklist approval remain TBD. The data and prose distinguish public publishing accounts, practitioners, uploads, original sessions, attributed entities, titles, and captions.

The first three analysis rounds were completed and published before manuscript work began. Manuscript rounds 4–6 preserve their exact draft inputs and review records under `rounds/` and `reviews/`. Read `protocol.json` for the current completion state.

## Build and update

Use a disposable worktree or copy. From the Channeling Atlas project root (the root of the `channels-ET` GitHub repository), install the analysis Python dependencies and run:

```sh
python research/paper/scripts/analyze_paper.py
python research/paper/scripts/generate_results.py
bash research/paper/build.sh
python research/paper/scripts/package_paper.py
python research/analysis/build_report.py
```

The paper build uses PDFLaTeX, BibTeX, the unchanged official AAAI 2027 style in supported `preprint` mode, and standard packages including newtx, TeX Gyre, mweights, kastrup, natbib, caption, graphicx, amsmath and booktabs. See `reviews/design/tex-dependency-receipt.json` for exact local dependency sources and hashes. The current environment's extra TeX font tree is outside the repository; a normal TeX installation must provide the listed packages. No modified or substitute venue style is used.

`generated/` contains numerical macros, tables, figures, CSVs and a machine-readable results file. `body.tex` contains the narrative. Changing the data requires regenerating outputs, reviewing every associated prose claim, rerendering the PDF, and creating a new snapshot. Preserve earlier releases. The analysis snapshot is frozen separately from manuscript improvements.

The publication copy is `dist/analysis/channeling-atlas-paper.pdf`. The Overleaf import ZIP contains `main.tex`, `body.tex`, `references.bib`, generated LaTeX/PDF assets and the required style files at the ZIP root. Select PDFLaTeX and compile `main.tex`. This package compiles the reviewed manuscript; it does not run data collection or inference.

## Literature and source access

The bibliography includes peer-reviewed journal and conference papers, with repository and archival sources recorded separately where relevant. `literature/` documents search terms, reading depth and source limitations. A publisher abstract, an author manuscript, a supplement, and a full publisher article are different access levels. A cited study's reported results are not treated as independently reproduced findings.

The ICWSM 2027 guidance checked for the 23 October 2026 release calls for an initial full paper of at most 11 pages including references, with a separate mandatory checklist and optional appendices outside that limit. This working draft uses that venue as a writing and format reference. The official checklist is provided for future human completion; TBD entries are not compliant final answers. The paper has not been submitted, anonymized for a concrete review process, or certified as venue-compliant.

## Data release boundary

The public package contains public metadata, source links, derived numerical features, code, figures and review records. It excludes raw captions, retrieved author-message text and model weights. Frozen-feature reproduction and full recomputation from speech are different capabilities: the latter needs authorized local source text and the pinned model. An available video URL does not guarantee that identical captions can later be reacquired.

The supplementary analyses are descriptive. Pair scores share videos/accounts; leave-one-account-out ranges are influence diagnostics, not confidence intervals. No result determines a communication's origin, truth, a person's clinical state, or the number of active mediums worldwide.

## Completed release checks

`reviews/coordinator-completion.json` binds all six final model-agent receipts to the delivered PDF. `reviews/overleaf-build-check.json` records clean-package compilation. `reviews/implementation/round6-offline-reproduction.json` records byte-identical regeneration of 23 scientific outputs. The official template ZIP is an ignored download cache; the required style files and its source URL/hash are preserved.

## Handoff and future rounds

The project [README](../../README.md#handoff-resume-here) contains the branch workflow, release hashes, prioritized roadmap and acceptance criteria. Begin future reviews in new round directories. `scripts/close_reviews.py` is specifically bound to historical rounds 4–6 and must not be used to certify a later draft. Build and packaging commands overwrite the public PDF/ZIP, so reproduce in isolation before promoting reviewed outputs. Human validation and submission tasks remain TBD.
