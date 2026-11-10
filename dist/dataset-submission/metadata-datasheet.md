# Dataset card: source-bound channeling discourse archive

## Purpose and scope

This release supports reproducible analysis of publisher-attributed channeling discourse, collection availability, transcript provenance, and differences across sources and textual renditions. It does not test whether a claimed nonhuman speaker exists, independently identify speakers, or establish the truth of spiritual/paranormal propositions. The empirical corpus is a finite convenience sample, not a census of channeling communities, religions, languages, or YouTube uploads.

## Composition and units

The selected corpus contains 683 publication/body components and 1,599,556 whitespace-delimited words. Each component has one selected edition. The complete accepted lineage contains 694 retained textual editions: 683 selected and 11 alternatives. The 694 editions contain 691 strict normalized body hashes; repeated textual editions are not independent observations. The 26 publisher contexts map to 14 source-attributed creator contexts, including mixed-speaker guest interviews. These context counts do not measure diarized speakers.

Separately, the discovery inventory contains 2,812 observed YouTube IDs and 297 account references. A reference may be a literal unresolved route, an observed handle or an historically verified uploader; those states remain explicit. All account lifetime-upload totals remain unknown. The selected corpus joins 533 physically retained encoded media files. Those files are not all archived media: Ra's 2,620 linked audio segments, preserved original encodings, auxiliary validation files, and excluded/nonselected source files belong to separate source and archive ledgers.

There are 192 newly retained OmNa publisher audio files: three original MP3 files and 189 verified lossy Opus derivatives. The new written bodies comprise 189,717 words before cross-release reconciliation. Two of those articles already existed in the old 493-unit selected frame with whitespace-equivalent written text, yielding 190 additional selected publication units. Their new audio is linked to the preserved selected units without asserting timing alignment or equivalence to linked YouTube videos.

## Text provenance and dates

| Origin as recorded | Selected units |
| --- | ---: |
| `publisher_written` | 226 |
| `local_asr` | 221 |
| `publisher_transcript` | 106 |
| `linked_publisher_caption` | 70 |
| `retained_local_asr` | 19 |
| `publisher_labeled_transcript_pdf` | 15 |
| `platform_auto_caption` | 14 |
| `machine_asr` | 12 |

These are source-preserved labels, not a uniform transcription pipeline. Origin-sensitive analyses should disclose any grouping and test sensitivity to ASR versus publisher-written text. Human word-error-rate validation is unavailable. Written messages and edited transcripts may differ materially from speech. Linked captions may have source errors. Thirty historical YouTube caption-analysis references lack verified original bodies in the current accepted frame; they remain metadata references and are excluded from selected-body analysis.

Accepted publication dates exist for 383 units, spanning 1981-01-15 to 2026-11-08. Three hundred units lack accepted dates. Date formats and timezone information differ by source. Do not treat missing dates as retrieval time, and do not infer a causal longitudinal trend from these convenience samples.

## Collection and preparation

Source URLs, hashes, extraction transformations, word counts, current media encodings, and source-specific collection provenance remain bound to records. Text normalization is Unicode NFKC plus removal of outer whitespace only. No internal whitespace, case or wording changes enter the strict body hash. Source pages and original private text artifacts are preserved. Some publisher notices and marketing/navigation material were separated during body extraction; the original notices and per-page locators remain in the source archives.

Prior accepted components are preserved. For the new OmNa cross-release duplicates, individual article URL equality and exact whitespace-folded body equality are both required. Semantic similarity, overlapping titles, shared claimed entities, and repeated terminology are not sufficient for identity merging. All alternative bodies remain retained. The selected frame is SHA-256-bound and its input bindings are recorded.

The present YouTube route was denied before reaching the origin. Zero successful YouTube media downloads are attributed to this inventory. Public publisher sources supported the retained audio and textual material. Publisher media must not be relabeled as successful YouTube downloads. The collection workflow retains unresolved references and failed attempts rather than silently shrinking the denominator.

## Sensitive content and interpretation

Spiritual or religious expression may be sensitive and may include personal testimony or health-related claims. Topic membership is a statistical annotation, not a diagnosis, belief label for a person, or identity determination. Guest interviews and questions may contain speech by people other than the source-attributed medium. The release must avoid extracting personal profiles, inferred protected attributes, or authoritative health predictions from this corpus. Relevant source removals or correction requests should be evaluated at source and edition level with a tombstone and versioned count update.

## Intended and unsupported uses

Intended uses include reproducible descriptive text analysis, provenance research, source-availability audits, edition comparison, question/answer retrieval research with checked quotations, and evaluation of how transcription origin or publisher imbalance changes findings. Suitable baselines include TF–IDF, origin-stratified topic comparisons, publisher-controlled retrieval, and annotation reliability studies.

Unsupported claims include population prevalence, verified cross-medium entity identity, evidence that channeling is paranormal, causal influence inferred from lexical similarity, transcript accuracy without a reference set, and a lifetime-completion percentage without a complete uploader enumeration. Raw text is not a factual reference for medical, financial, or geopolitical recommendations.

## Distribution and rights

Public distribution contains metadata, provenance hashes, edition lineage, source links, aggregate/derived annotations, code and documentation. Full media, captions and text remain in the private research archive until a source-specific redistribution basis is documented. A source being publicly accessible, archived successfully or linked from YouTube does not establish a redistribution license. The public metadata's license and code license must be declared separately from third-party source rights. There is currently no blanket license grant for the underlying media/text corpus.

Private artifacts include normalized selected JSONL, complete edition JSONL, a searchable SQLite database, file/hash closures, source pages and acquisition receipts. Archive status must be reported from actually verified remote upload receipts; a local path is not permanent ChatGPT storage.

## Maintenance and reproducibility

Versions bind source snapshots, selected frame hash, code and parameters, release manifest, analysis outputs, and archive verification. Counts should be regenerated from the same frame, with an explicit migration note if selected editions or admission rules change. The public build must not require downloading source content. Source acquisition and ASR are separate opt-in execution steps, preserving source policy, operational resource limits and failure states. Corrections should update provenance and edition selection without silently overwriting historical editions.

The source-bound loader verifies every selected artifact, strict normalized hash, word count and row order. Release tests check one selected edition per source, exact public/private metadata joins, SQLite body integrity, null-versus-zero counting, inventory foreign keys, and absence of private paths/full bodies in public exports. Independent review separately rehashed all 533 selected linked media files and all selected/full-edition bodies. These checks establish artifact integrity and counting consistency, not scientific validity or transcript accuracy.
