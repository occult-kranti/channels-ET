# Council study interface

The additive static page lives at `dist/council-study/`, linked from the existing relationship dashboard. It preserves the earlier studies and uses the Atlas typography, colors and native controls. No backend service or external font/CDN is required for the page itself.

## User flow

1. Read the bounded source-name findings, including the unresolved exact “Council of Contract” search and the independently supported “Council of Contact” records.
2. Select a medium or exact printed name in the attribution map, or use the equivalent search/filter table. A graph node groups an identical printed name; it does not authenticate an entity identity.
3. Inspect a source edition, its actual source URL, text scope, attribution basis, word count and hash. Explicit `primary_source_id` / receipt bindings can link a publisher record to a distinct ASR edition; the primary register retains its own access state, artifact hash scope and source qualifications.
4. Compare whole-text and centered-300-token cosine matrices, pair types, name-mask sensitivity, topic factors and literal keyword rates. Complete CSVs contain every eligible row/pair, including rows outside the current table page or matrix block.
5. Compare qualitative dimensions across retained source texts. The matrix exposes analyst paraphrases and exact turn/time/hash locators. Questions are explicitly analyst-constructed; source recommendations and timing claims are not endorsed advice or verified forecasts. Supplemental Galactic-source cards preserve complete-written-text versus selected-ASR-span coverage and show each observation together with its qualification and source hashes.
6. Inspect new versus reused audio receipts separately from the written-text study. Total YouTube upload counts remain unknown where the source frame does not establish them.
7. Read earlier-corpus phrase matches in bounded context cards, with separate context hashes, coverage and unknown speaker roles. These are not extra texts in the council-study denominator.
8. Follow the research-source register, methods and downloadable JSON.

## States and boundaries

- The analysis is required. A failed or synthetic-flagged analysis shows a recoverable error, with no example observations or replacement counts.
- Registers and audio receipts fail independently. Missing acquisition data are unknown rather than zero; the text-study denominator stays available.
- Only declared local data resources are fetched. External source links accept ordinary HTTP(S) URLs, and source values are escaped before insertion.
- Search and exact source filters are shareable in the URL. A stale filter outside the current snapshot remains visibly selected and returns an empty result; it is not silently replaced by an all-source selection.
- Tables and the attribution diagram scroll locally on narrow screens. Large matrices use selectable 20×20 blocks above 40 texts, retaining global source IDs and complete CSV export.
- Native dialogs keep underlying page controls inert and restore their source trigger when closed; browser chrome remains keyboard-reachable. Controls have persistent labels and visible focus; mobile form text is at least 16px. Matrix cells include numbers, and source states include words/shapes as well as color.
- CSV values beginning with spreadsheet formula characters are escaped. Full transcripts, private audio paths and model files are not part of this view.

## Verification status

Design Partner’s create/interaction workflow and accessibility reference informed the implementation. No prior `.design/*-report.md` was found for this surface.

The actual released five-text study passed `dashboard_check.mjs` on 2026-11-08 at 16:47 UTC: 907 assertions, 15 screenshots and 15 CSV downloads at 320px, 390px and 1440px. There were no runtime/console errors or document-wide horizontal overflow. The checked data contained five text editions / 26,451 words, three medium contexts, four retained recordings, and four ASR editions. Figures, exact numeric matrices, metadata exports, all keyword rates, bounded reading paraphrases/qualifications, source hashes and explicit publisher-to-ASR joins were checked against the loaded files. Complete input hashes were unchanged across the run.

The check covered keyboard map activation, modal opening/Escape/focus restoration, filters and honest empty results, all four qualitative comparison dimensions, required-data failure/retry, rejection of synthetic-flagged analysis, unavailable optional acquisition, CSV formula escaping, and 200% CSS zoom reflow. Native Chromium Tab can reach browser chrome (`document.hasFocus() === false`); it did not focus an underlying page control. A first draft assertion incorrectly treated browser chrome as a dialog escape and was corrected before the passing run. The page code needed no focus-trap change.

An independent review passed 76 assertions at 320px and 1440px with zero runtime errors and unchanged input hashes. It checked Airacle qualifications, the explicit Pamela ASR-to-primary source link, the exact-name filter and every whole-text matrix cell. Desktop/mobile overview, attribution map, qualitative table, mixed-interview reading notes, research figures and source dialogs were visually inspected.

The accepted analysis SHA-256 is `cab65cbfc9d4bd5913353cefbbf3e9ad7e3422d4ddf7361968b1b49d100b9908`; tested application SHA-256 is `a9b31f7d06a41ff26537ec9d2c1133c46b9712118f9722d19c94dae0360ae9c7`. Detailed receipts and screenshots remain in the private audit workspace (`browser-final-02/receipt.json` and `review/ui-independent.json`). The shipped page contains public metadata and bounded paraphrases, not private audio/transcript bodies.

The five-text release does not exercise the code path for matrices above 40 texts. No screen-reader, cross-browser, native-browser-zoom or full WCAG certification is claimed. Exploratory clusters exactly match medium contexts in this frame; the adjacent interface note explicitly identifies source/style/format confounding.
