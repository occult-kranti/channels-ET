# Paper round 11: implemented challenge and artifact review

This loop reviews the frozen round-10 14-page continuation manuscript and produces a changed, executed-results candidate in `channels-ET`. Historical papers and the original Bashar repository are unchanged by this workstream. The reviewers are model agents, not human peer reviewers.

## Material corrections

- Made the selected-pool confound explicit: source-proxy groups are constructed from question similarity, so the 127-neighbor versus 57-cross-group answer-cosine contrast cannot identify source reuse. Added the executed 93-pair, three-bin common-support comparison; 34 unsupported high-similarity within-group pairs remain excluded rather than imputed.
- Retained sparse-source RAG as a transfer stress test: its 48-item retrieval store deliberately lacks held-out source answers. Low reference overlap is not a ranking of conventional answer-present RAG quality.
- Documented the precise seed-42 first-candidate split: 48 examples from 47 training groups; eight first-by-ID questions from eight held-out groups. This is not a representative difficulty or topic benchmark.
- Exposed the extractive full-gist versus 40-new-token generator budget difference, five adapted closed-book and one adapted retrieval cap hits, and zero prompt truncations. Cap observations are not an executed budget-sensitivity experiment.
- Preserved original strict-marker metrics and added the separately disclosed post-hoc refusal-phrase diagnostic. The phrase rule was chosen after inspecting responses and is not human semantic-refusal accuracy.
- Added four exact training-source, answer-present positive controls separately from held-out tests. Two outputs reach supplied-gist token F1=1, but zero emit a valid evidence label. Label syntax still does not establish entailment or external truth.
- Added the actual twelve-excerpt content-label task: nine parseable outputs, three failures, all nine parseable conditional labels yes and primary labels contact/forecast, five-of-nine dictionary concordance, and zero-of-nine valid short exact spans. These are failure-prone method comparisons, not annotation accuracy or corpus prevalence.
- Added the successful pinned Qwen3.5-0.8B CPU text-only compatibility probe. The prompt supplies the requested provenance values; 23 generated tokens under a 32-token cap reproduce that JSON schema. This is not independent provenance classification, multimodal/video analysis, matched model comparison or state-of-the-art validation.
- Added a generated evidence-transformation diagram and integrated all six current continuation figures with precise captions. Kept fresh official AAAI 2027 style bytes unchanged and separated human/venue decisions as TBD.

## Artifact and checks

Candidate: **16 pages**, `research/continuation/paper/channels-et-paper.pdf`.

PDF SHA-256: `9b5d59e51430ae2429f36b5c3c3e293a2f655f814eb58403485e993203029b88`.

Standalone source ZIP SHA-256: `7795f5a1cfacb05aa831dcaf4b6dcf43858bde6927a3a5c3ecd745fc793a6165`.

The clean package extracted and compiled with PDFLaTeX/BibTeX, all four commands exited zero, and extracted page text exactly matches the delivered PDF. All fonts are embedded and no Type 3 fonts occur. Final pass has zero overfull boxes and no undefined references/citations. All sixteen pages were rendered and inspected in a contact sheet; full-size pages 1, 7, 8 and 10 were inspected for narrative, common-support values/legend, model tables/control labels and nuisance plots. No clipping or overlapping content was observed. All 22 input-manifest hashes match current evidence files.

Exact commands, font report and render paths are retained in `paper/verification.json`. This is bounded local artifact verification, not human peer review or submission approval.

Status: round-11 manuscript implementation and checks complete; ready for round-11 freeze and formal final round 12.
