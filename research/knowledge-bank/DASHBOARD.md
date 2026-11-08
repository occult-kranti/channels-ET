# Knowledge-bank interface

The additive static page lives at `dist/knowledge-bank/`. It keeps the existing Atlas pages and data editions intact. The interface uses local HTML, CSS, JavaScript and release files without a framework, CDN, remote model endpoint or runtime API key. Serve the directory over a local HTTP server for offline use; browser security generally blocks JSON fetches from `file://`.

## Reading flow

1. Establish the study frame and separate modeled text, annotated questions and comparisons.
2. Find a question by topic, provenance, medium context, assessment or free text. Read qualified paraphrases next to their source context.
3. Open an answer, comparison or publisher inspector to inspect source hashes and supporting character/turn locators.
4. Trace the typed provenance graph. Its columns denote record types; their distance is a layout choice. Dashed analogy edges are distinct from source attribution and comparison edges. Hover or keyboard focus highlights connected records.
5. Compare lexical and semantic maps, nearest neighbors, cluster seed sensitivity, source/label confounds, lexical term weights and all 300 pair records.
6. Inspect ASR feasibility and paired-window measurements separately from full recordings, then inspect the consolidation/retrieval diagnostic, hypotheses, source reading coverage and research literature.
7. Export the question bank, graph edges, neighbors and pairs as CSV, or download the manifest-bound JSON, SQLite, methodology and standalone figures.

The map overlay uses separate fitted coordinates and an explicitly disclosed orthogonal Procrustes display orientation. Circles denote lexical positions, open squares denote aligned semantic positions. Connecting lines are display displacements, not belief changes. The term heatmap is source-group mean TF-IDF, not a word-embedding plot. A distinct contextual-token section plots 24 selected term centroids and their sampled source contexts in a single shared PCA transform, with source counts, original-space cosine neighbors and visible normalization/selection limits. The sentence-trained token states are an exploratory representation, not validated word senses. NMF factors expose relative source loadings without presenting them as belief probabilities. The constructed negation example is visibly synthetic and excluded from all source counts.

## Release contract

`manifest.json` schema version 1 binds named modules by local file, byte count and SHA-256. Required modules are `analysis` and `knowledge`. Optional modules include `literature`, `experiments`, `retrieval`, `asr`, `full_asr`, `asr_sensitivity` and `contextual_terms`. The integrator owns this manifest and its artifact allowlist. Source model figures use basenames within their original JSON; the site serves them beneath `figures/` without modifying those source hashes.

The loader rejects unsafe file paths, mismatched byte counts or available WebCrypto SHA-256 mismatches, unsupported manifests, missing required arrays and top-level synthetic fixture releases. WebCrypto is available on localhost and HTTPS. Required failures remove observation counts and offer Retry. Optional failures leave the supported analysis usable while reporting unavailable results as unknown, not zero. Publisher URLs accept only HTTP/HTTPS; dynamic text is escaped; CSV cells are quoted and formula-leading content is escaped.

Public answer cards contain labeled paraphrases and hashes/locators. Raw source transcripts, audio, local model paths, private database content and authentication material are never part of the public module contract. The public SQLite database is a sanitized export of the source/question/card graph, not the private raw evidence archive.

## Accessibility and responsive behavior

The interface follows the applied Design Partner implementation, accessibility and verification workflow: native labeled inputs, semantic tables, visible keyboard focus, a skip link, keyboard-operable SVG source records, a native modal dialog with restored external focus, reduced-motion handling and forced-colors styles. Color is accompanied by text, shape, table rows or line style. The map and table containers scroll locally when their scientific content requires width; the body does not scroll horizontally at 320 px. The secondary navigation scrolls horizontally on small screens and highlights the active section.

The interface uses the existing warm neutral/forest Atlas palette and stable, alphabetically assigned medium colors shared with the research plots. Mobile answer cards become a single column. Source hashes wrap; unavailable/empty/error states remain readable. Font sizes, wrapping and 200 percent zoom are exercised in the actual browser.

## Verification

Run `node research/knowledge-bank/browser_check.mjs --url http://127.0.0.1:8765/dist/knowledge-bank/ --out /dev/shm/channels-et-knowledge-2026-11/browser` after serving the repository. The script uses the environment's installed Playwright and Chromium. Its optional `--release-map` accepts a private file map only for pre-integration review of already existing real artifacts; it does not synthesize observations. Final deployment validation should omit this option.

The script writes a JSON receipt and bounded JPEG screenshots into the requested directory. Keep temporary browser output in RAM; retain only a small reviewed proof subset privately. Tests verify counts and exports against the loaded release itself, rather than hard-coding future result totals. New optional module schemas should receive direct field/denominator checks when integrated. Visual inspection remains necessary for diagrams, labels and scientific interpretation even when all DOM checks pass.
