# Transcript knowledge: design and evidence contract

Design Partner's create, accessibility and verification workflow guides this additive static workbench. Existing Channel Lab pages remain unchanged. The dominant job is exploration: find a question or concept, distinguish the kind of record, inspect its source edition, then follow explicitly typed connections.

## Information architecture

The question bank is the entry point. Its searchable results and selected-record reading pane share one visible filter state. Source and context digests provide coverage and lexical outlines, with substantive reviewed summaries identified separately. The connection explorer offers typed relations, context filters and bounded hop paths, alongside a complete filtered edge table and export. Methods and downloads explain source boundaries, measured retrieval diagnostics and public versus private search.

Deep links address records, source editions and publishing contexts. Browser navigation preserves the chosen view and explicit filters. Mobile layouts expose all four navigation choices and stack the reading pane in document order; wide analytical tables and diagrams scroll locally.

## Evidence distinctions

- `observed_question_answer`: a locator for a printed documentary question/answer unit. A public cue label is not automatically the original question wording.
- `unverified_question_candidate`: an automatic punctuation/question cue in a written source, caption or machine transcript, with question/answer roles unverified. The actual source origin is shown separately.
- `generated_reading_prompt`: a generated research prompt, not something asserted to have been asked in the recording.
- `curated_comparison`: a source-bound analyst comparison with explicit inspected support and limitations.

Missing answer paraphrases remain missing. Automated lexical profiles are distinct from close-read summaries. Publisher contexts, creator contexts, claimed labels and fitted lexical factors retain separate identities. Graph paths state each relation and do not convert co-occurrence or similarity into agreement or authenticated identity.

## Artifact and search contract

The root-owned manifest binds `profiles`, `bank`, `curated`, `graph`, `retrieval` and `database`; `literature` is optional. Profiles contain source and publishing metadata, avoiding a duplicate registry download. The light bank index supports global filtering and search; full per-source record metadata and evidence locators load lazily from hash-bound shards. The public SQLite artifact is a download, not an excuse to publish private transcript bodies.

The pinned local MiniSearch bundle provides browser search over public cue labels, prompts, annotations and source metadata only. It does not search private full transcript bodies or reproduce SQLite BM25 scores. OR matching is explicit, negation and apostrophes are preserved, and fuzzy/prefix matching is off by default. Any prefix option is labeled. Ranking affects retrieval order, not answer credibility.

## Verification plan

Use actual accepted producer files. Check search and filter denominators, type/status distinctions, shard identity and hash validation, source/context/record deep links, unknown and no-answer states, graph relation/hop filtering, exports, native-dialog focus and responsive reflow at 320/390/1440 pixels. Separately label simulated transport or integrity faults. Inspect actual screenshots and retain proofs in RAM until the root approves a compact durable receipt.

No completed reading, measurement or deployment is claimed until its actual artifact or test exists.

## Implemented release and review

The accepted release provides 493 automatic source profiles, 9,424 extracted/prompt entries and 26 distinct curated questions backed by 27 qualified answer cards. The browser catalog therefore has 9,450 items. Curated questions appear first and have a direct preset; automatic cues and generated prompts remain available. The 26 publishing-context pages separate automatic outlines from bounded reading notes. Source pages link back to Channel Lab for numerical topics, speech editions and comparison views.

A multi-source comparison matches a source filter only when at least one of its linked sources satisfies all selected source conditions. The complete comparison then retains its other sources, visibly marking those outside the active source filters. JSON exports include those per-source match flags; CSV exports distinguish all linked IDs from matching IDs. A selected reading that falls outside a changed filter stays open with an adjacent notice instead of silently appearing to belong to the new result set.

The graph contains 622 typed nodes and 3,664 declared edges. Its default omits the 256 derived semantic-neighbor edges; users can enable them explicitly. Exact printed-label filters group observed strings, not authenticated beings or identities. NMF factor edges remain clearly identified computed relations. One- and two-hop navigation preserves original edge directions in the path list. Combined diagrams cap drawing at 180 nodes and 700 edges, while the filtered table and JSON/CSV retain the complete eligible graph. All 9,424 extraction/prompt entries remain outside the compact interpreted graph and are available through the bank, shards and SQLite.

Retrieval tables show known-support source ranks, including the diagnostic q06 result of 1 / 6 / 284 / 5 for BM25 / TF-IDF / MiniLM / fusion. Controls are unscored. Information-need categories and publishing/source-context IDs have separate labels. Opening a graph answer card preserves its conditions, time scope and qualifying note; support edges resolve exact edition and span hashes.

## Executed browser verification

On 2026-11-08, `browser_check.mjs` passed 28 integrated check groups against all seven actual modules. It covered the 9,450-item search catalog, all four record types, missing printed-question wording, generated-only sources, multi-source filter transitions, source/context routes for all 493/26 entities, hash-bound lazy shards, provenance dialogs, JSON/CSV downloads, typed graph paths and label filters, complete-versus-drawn graph counts, empty relations, retrieval ranks and controls, unknown IDs, and 320/390/1440-pixel layouts. No browser runtime errors or page-level horizontal overflow occurred. Three separate intercepted scenarios confirmed visible failure for a shard HTTP error, same-size shard hash corruption and a required-module HTTP error; they supplied no replacement observations.

The measured local initial load was 683 ms and the “fear” query returned 159 public-index records in 59 ms. These are single local observations with the retained data, not representative network or device performance claims. Source shards remained unloaded until a record needed them. The test bound app SHA-256 `5df2f04623af3d31deb6841c9307120ee08da91339dbfe2882abfc194436aedf` and pre-document-refresh manifest `87192ba7b9c296c470aeb70f201f7876eb456997c3b1637b364bfc0855334ef6`.

An independent reviewer additionally passed five actual browser scenarios for retained out-of-filter readings, multi-source exports, the q06/category labels, exact-label graph membership and responsive graph containment. The implementation reviewer visually inspected desktop bank, source details, curated reading, typed paths, combined graph and retrieval tables, plus mobile bank and reading views. The large combined graph is intentionally a bounded overview; focused paths and the edge table carry the inspectable detail. The browser suite is reproducible locally; deployment verification is separate from this local acceptance.

The final visual correction replaces a misleading aggregate “Unknown” condition field on curated records with “See each qualified answer below”; the actual per-answer conditions and time qualifications remain visible. The complete 28-group suite and three fault scenarios passed again against the final application bytes.
