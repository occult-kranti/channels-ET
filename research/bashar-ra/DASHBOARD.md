# Bashar–Ra comparison dashboard

The standalone static page is at `dist/bashar-ra/`. Its six views cover source and acquisition coverage, keyword and topic models, lexical and semantic networks, question structure and source-linked reading, source metadata, and methods. Existing Atlas pages are preserved.

## Public inputs and boundaries

The page loads `data.json` (required, schema version 1), `collection.json` (optional collection status), and `reading.json` (optional source-linked paraphrases) from the same directory. Figures are served from `figures/`. Every asset URL is relative to the page, so the app works at the GitHub project path as well as on a local HTTP server. There are no external JavaScript, font, or chart dependencies.

The analysis release must provide actual admitted sources and aggregate measurements. The browser rejects a release marked `synthetic_fixture_run: true`, duplicate source IDs, unknown corpus labels, and unsupported schema versions. Missing collection measurements display as unreported; an available transcript never implies that its original audio or video was downloaded.

Collection status distinguishes `unique_audio_sources`, `retained_audio_files`, `original_audio_retained`, and `compact_audio_retained`, and can report `retained_audio_encoding`, `inventory_original_bytes` and `audio_hours`. `unique_transcribed_sources` differs from `transcript_editions`. Published original-inventory bytes are explicitly different from admitted compressed-audio bytes; PCM working files, model caches and total workspace usage are not implied. A separate note reports preserved but unadmitted audio. `collection_resolution_status` and `qualifying_audio_status` distinguish resolving a candidate from admitting it. Audio segments and compact derivatives are not presented as independent sessions. The baseline text analysis remains frozen while collection coverage changes.

Optional receipt-derived acquisition plots are declared by `collection.figures` and served from `collection-figures/`. The study report is linked at `report/paper.pdf`, with Markdown, LaTeX and bibliography companions. No report length is hard-coded.

The public inputs contain metadata, hashes, aggregate measurements and paraphrases. They must not contain raw transcript or question/answer text, machine-specific private paths, signed media URLs, credentials, or model-cache locations. The integrator reviews these inputs before publication. The page does not fetch the private archive.

The primary comparison separates publisher-edited Ra sessions from Bashar-related interview, promotional and commentary ASR. Authored Bashar references remain an independent source stratum: they appear in the inventory and bounded reading, but do not silently enter primary keyword bars or fitted primary-source networks. Partial reference extracts are reported through exclusions and collection coverage. Search covers source metadata, not full transcript text.

## Interactions and interpretation

- Topic terms are exploratory factors. Candidate errors, seed stability and convergence diagnostics are displayed, without claiming a validated optimal topic count.
- The network uses actual fitted pairwise cosine matrices. Corpus filters and thresholds change the display without refitting. At most 650 strongest qualifying edges are drawn; CSV exports every qualifying edge. Node position groups corpus labels for navigation and encodes no semantic distance.
- The retained static network figure uses its declared three-nearest-neighbor rule. Its sensitivity results are identified separately from the interactive all-pairs threshold view.
- Source selection works through the graph, a native select control, or source tables. Source dialogs expose provenance, dates at their recorded precision, edition, text kind, hashes and any supplied media status.
- Cluster diagnostics show selection, first-seed silhouette, cross-seed adjusted Rand, singleton counts and cluster sizes. None is a test of the truth or origin of the records' claims.
- Publisher-labelled Ra prompt/response pairs and Bashar ASR punctuation candidates retain separate definitions. Semantic retrieval links are unvalidated reading leads. Public qualitative comparisons are source-linked paraphrases, with counterpoints and evidence limits.
- Follow-up contextual reviews show both broad overlaps and retrieval failures, with exact inspected coverage. Newly retained official-excerpt readings are marked as outside the primary fitted set unless their actual source IDs occur in that fit. The page does not turn a selected review into a population-wide precision estimate.
- Filtered source CSV exports all matching rows, not only the current page. CSV cells escape quotes and protect spreadsheet formula prefixes. The source inspector permits only public HTTP(S) links without embedded credentials.

## Official-speech follow-on

When `collection.supplementary_studies.official_speech` points to the exact local filename `official-speech.json`, the Topics view exposes a separate study switch. The supplement must have schema version 1, unique source IDs and explicit strata; synthetic-flagged data are rejected. Where WebCrypto is available, the browser hashes the fetched baseline bytes and requires the supplement's baseline SHA to match. An invalid or unavailable supplement does not replace the baseline analysis.

The follow-on has its own expected, admitted and held publication counts, phase, source strata, keyword rates, official-only topic/cluster diagnostics, duplicate/family review, and question-candidate counts. It compares complete text and 400-token lexical/neural projections through an accessible source selector. A nearest neighbor remains a reading lead; absent short-window results are shown as unavailable, not zero. One chosen transcript edition represents each official publication in its fits.

Official source records have independent search, stratum filters, pagination and provenance dialogs. Search and projection controls update only their local sections to preserve the surrounding plots and scroll position. The four optional figure families live in `official-figures/`. The baseline network and source explorer continue to use their original admitted sets.

## Local use and verification

Serve the repository with an HTTP server; browser `file:` fetch restrictions may prevent direct double-click use:

```sh
python3 -m http.server 8055 --bind 127.0.0.1 --directory .
```

Then open `http://127.0.0.1:8055/dist/bashar-ra/`. Once the approved data and figures have been copied, run from the repository root:

```sh
node research/bashar-ra/dashboard_check.mjs
```

The harness accepts `BASE`, `PLAYWRIGHT_PKG`, `PLAYWRIGHT_EXECUTABLE_PATH`, and `BASHAR_RA_BROWSER_OUTPUT` environment overrides. It uses actual release data for navigation, filter, graph, source-dialog, CSV, figure-loading and layout checks at 320, 390 and 1440 CSS pixels. When the supplement is declared, it also checks its denominators, study switch, source filters/dialogs/pagination, all four representation selectors and its actual figures. Separate request interception checks unavailable data, retry, and rejection of a synthetic flag; those test responses are never written to the public page. Report artifacts are checked over HTTP. Source/report hashes before and after establish that verification does not mutate release inputs.

The UI provides semantic headings and labels, focus indicators, a skip link that preserves the active view, a native dialog with explicit Tab/Shift-Tab cycling and Escape handling, source-selection alternatives to graph nodes, labelled scrollable tables, reduced-motion support, and shape/text distinctions alongside corpus color. Automated browser checks do not establish screen-reader compatibility or scientific validity. A separate body-text enlargement check is not a claim of complete browser-zoom or WCAG conformance.

Verification status and artifact hashes belong to the private browser receipt and the integrated release handoff. Do not describe an unexecuted harness or an outdated receipt as a completed release check.

## Implementation ownership

This dashboard owns `dist/bashar-ra/index.html`, `styles.css`, and `app.js`; the browser harness and this document support the same page. Acquisition and analysis workstreams own scientific inputs and figures. Root integration owns Atlas navigation, release input sanitization, publication and deployment.
