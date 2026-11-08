# Channel and recording laboratory: interface contract

The new static workbench is additive. The existing Atlas, acquisition audits and knowledge-bank pages stay intact. Design Partner's create, accessibility and verification workflow guides implementation; actual reviewed data and a skeptical interpretation pass determine acceptance.

## User flow

Evidence inventory → collection-context detail → individual recording or text edition → selected-source comparison → measurement and source inspector.

The landing page is a coverage table, not a wall of interchangeable cards. Context detail combines the retained source list, dated coverage, fitted topic profile, key terms and bounded readings. Individual source pages expose the chosen edition, publication/publisher context, media and text provenance, topic progression, quality flags and inspectable original-space neighbors. Text position is not presented as audio time without an explicit time binding.

`?channel=ID` and `?recording=SOURCE_ID` are stable deep links. `?view=compare`, `?view=batch` and `?view=methods` address workbench views. Browser history and a visible route hierarchy preserve navigation. Large source tables paginate; matrices and source-detail files load only when needed.

## Measurement boundaries

- Known enumerated YouTube metadata, retained publisher media, canonical text units and alternate recognition editions have separate counts. Unknown uploaded totals remain null and visibly unknown.
- A collection context is distinct from a publisher, named medium, recording and attributed entity. No join is inferred from a similar display name.
- Channel profiles describe the selected retained documents. They do not estimate the complete channel's topic prevalence.
- Topic weights are relative model loadings; cosine is a representation-dependent similarity; none establishes agreement, contradiction or a shared identity.
- Graph controls alter display thresholds and neighbors within the selected sources, using a fixed fitted matrix. They do not refit the corpus or validate clusters. Drawing caps and complete exports retain their exact denominators.
- Readings remain labeled paraphrases with conditions, counter-readings, edition hashes and inspection coverage. Historical-card links do not silently transfer annotations to newer ASR wording.
- Batch status distinguishes planned, attempted, completed, failed, held and verified reused work. Full input coverage is separate from verified transcription accuracy.

## Artifact contract

The root-owned schema-1 manifest binds `registry` and `analysis` as required final modules, with optional-loader support for `coverage`, `batch_asr`, `readings` and `asr_effects`. Every descriptor supplies a local filename, byte count and SHA-256. The final release validator requires accepted completed producer outputs. Analytical JSON points to two lazy Float32 little-endian full-space cosine matrices and optional per-source detail JSON, with their own hashes and sizes. No original transcript body, raw audio or private path is published.

The `coverage` module separates archive-wide units from recordings positively joined to the text frame. In particular, Ra's retained archival segments cannot be read as zero merely because session text rows have no direct media join. Official publication audio records, encoded-media families and canonical texts likewise have separate denominators.

Missing representations stay unavailable. Float32 NaN rows are excluded from pair means, neighbors and graph nodes; no artificial zero similarity or origin coordinate replaces them. Topic-available document counts are shown alongside the full context denominator. Model-agent reading coverage is separate from corpus processing and never implies audio listening or human validation.

The optional ASR sensitivity panel distinguishes exact same-audio recognition editions from comparisons against selected written sources. It presents the nine-source counterfactual without replacing the primary corpus, inheriting old evidence locators or ranking model accuracy. Sample-window word counts and measured amplitude are separate from selected-text topic positions.

The interface uses semantic tables and native controls, a native modal inspector, keyboard-operable diagrams, visible focus, non-color status labels, reduced-motion support and local overflow containers. It keeps the Atlas warm neutral/forest identity while adding a desktop sidebar and compact mobile navigation. No remote inference, CDN library or API key is required at runtime.

## Verification milestones

1. Challenge identity joins, evidence denominators, sample/format imbalance and diagram semantics before implementation.
2. Inspect actual producer artifacts and numerical results; exercise source-specific pages, comparisons, filters, lazy loading, exports and failure states using the actual release.
3. Correct independent-review findings, test desktop/mobile deep links and deployed controls, and retain bounded screenshots and hash-bound browser receipts privately.

No placeholder observations are admitted for browser acceptance. Until reviewed source files arrive, the application displays loading, unavailable or error states rather than invented counts or graphs.

## Design review corrections

The independent pre-integration review found three schema/display mismatches. Topic progression now gives each bar its actual `start_fraction`–`end_fraction` width, including short final units, and exposes the underlying word ranges. Object-valued ASR quality flags are rendered explicitly, including zero counts and empty windows. Hypothesis diagnostics preserve singular limitation fields and numeric zero results, with measured diagnostics separated from confirmed hypotheses.

The implementation also guards asynchronous route changes, repeated matrix selections and simultaneous pair requests. CSV exports preserve active source filters or graph settings and neutralize spreadsheet formula prefixes. Empty comparison selections remain empty; arbitrary source IDs never select substitute evidence. Required module failures stop the release view, while optional module failures remain visibly unknown.

`browser_check.mjs` exercises actual source artifacts, both 320/390-pixel mobile and 1440-pixel desktop layouts, lazy loading, source filters and exports, provenance dialogs, text-position widths, original-space neighbor order, graph thresholds, pair inspection, archive coverage units and all registry route constructors. Proof files and compressed screenshots are retained outside the public repository. Final pass counts and release hashes are recorded only after execution.

## Executed browser acceptance

The integrated six-module release passed **29 core check groups** on 8 November 2026, with no intercepted data requests in the core pass and no browser runtime errors. A separate three-case transport simulation confirmed that a failed required analysis stops the release, a missing optional batch remains unknown, and a changed matrix byte is rejected by its SHA-256 binding. No replacement measurements were generated.

Checks covered all 493 source and 55 context view constructors, actual source-profile fractions, recognition-window counts and object-valued flags, source-filter and graph CSV exports, exact original-space neighbor ordering, contextual-term selection, source-pair controls, explicit empty selections, and the distinct Ra/Bashar archive units. The dense graph test admitted all 121,278 pairs among 493 available sources while drawing the declared strongest 1,500; the complete selected edge list remained available for export. The optional nine-edition ASR sensitivity rendered same-audio and written-origin comparisons separately.

All core page types remained within the viewport at 320 and 390 pixels; data tables and wide plots use local scroll regions. The final visual pass inspected desktop inventory, source topic progression, network, contextual-token overlay, ASR ledger and window profile, the explicitly labeled H4/H5 results, and mobile navigation. Mobile navigation exposes all four workbench views without requiring horizontal discovery. Twelve compressed screenshots and the hash-bound local proof occupy approximately 1.14 MB in private review storage.

The local integrated proof binds manifest `09e63578425ee50a5c38e2141cd94e303c111f13dc453d27d850656ecc2ef963` and application `f3cab4d62f0c976b889de41557d5577bc286c6e701eed36b78e9b30f2362b8d3`. That manifest precedes this final documentation refresh; producer modules and UI bytes remain unchanged. Deployed verification is a separate release step rather than an inferred consequence of local checks.
