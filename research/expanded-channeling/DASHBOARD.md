# Expanded channeling dashboard

The static surface at `dist/channeling-network/` separates people, publishing accounts, claimed-name records, comparison groups, sources and text-model contexts. It extends the existing Atlas rather than replacing the Bashar–Ra and subscription-audit studies.

## Product and evidence contract

The primary task is to follow a claimed relationship back to its source, then determine whether comparable text has actually been retained. Shared names are research labels. The graph never claims shared entity identity; its two-column position has no statistical interpretation. The shared-label matrix distinguishes direct channeling attributions from directory, category, contact, repost and other links. Human-medium counts use an explicit role allowlist; hosts and contactees are not silently included.

The UI consumes two source registers, the frozen joint analysis, a separate new-message pilot, and publisher-audio acquisition receipts. It preserves unknown upload totals and separates publication counts from deduplicated model units. It does not assign biography-level claimed labels to every passage or treat captions as verified speakers. Source inspection exposes access depth and dates. Full raw source texts and media remain outside the public dashboard.

The six views are:

1. **Explore identities:** search medium/name/tradition, filter identity type and declared tradition, inspect attribution, paginate and export all matching records.
2. **Relationship map:** select a declared comparison neighborhood; inspect human and claimed-name nodes using pointer or keyboard. Solid lines indicate direct channeling attributions; dashed lines indicate other research relationships. Narrow screens have a local horizontal scroll region and a table alternative.
3. **Shared-label matrix:** compare named figures/specific collectives separately from broad civilizations/traditions; show direct and all-linked medium counts.
4. **Text analysis:** source-context cosine matrix with pair counts and length-controlled scores, topic factors, cluster composition, exported figures and a reviewed false Q/A match. A separate pilot section compares source-attributed written messages; its questions are analyst-composed.
5. **Collection coverage:** account audit, text-model denominators and a separately timestamped publisher-audio receipt snapshot with source/publisher filters and CSV export.
6. **Methods and sources:** declared interpretations, access-depth source filter, unresolved leads, data downloads and local-serving instructions.

`dist/subscription-audit/` also adds a publisher-text study and a distinct publisher-linked YouTube discovery explorer. Newly crawled publisher links never overwrite the historical video-ID inventory or become a channel upload census. Current duration eligibility follows Bashar ≥300 seconds; other sources have no minimum. The prior five-minute field remains visible in historical metadata and exports.

## Design implementation

Design Partner's create, interaction, accessibility and verification guidance was applied. The surface uses the established Atlas forest/cream palette, editorial headings, stable table scanning lanes, visible evidence and restrained functional color. No CDN, animation library, external font or analytics dependency is required.

Native labels, buttons, selects, source links and dialogs provide the interaction primitives. Dialogs contain focus, close with Escape, and restore focus. Every graph node has a keyboard inspector. Empty filters, missing sources, loading failures and retry recovery have explicit states. The release rejects synthetic-flagged inputs and conflicting identity fields. Color is redundant with text, node placement and line style. Reduced motion and forced-color styles are present.

Download the site folder and serve it over local HTTP for offline use. `file://` fetch restrictions differ by browser. Publisher/source links need internet connectivity. The workspace archive must not be described as permanent ChatGPT account storage.

## Executed review and verification

The panel is five AI research roles, not external human review. Product work received source/evidence objections from the critic and a separate traditions/source-interpretation review.

Round-one actual-data browser verification:

- New dashboard: 154 assertions, 12 screenshots and 12 CSV exports passed in Chromium at 320, 390 and 1440 CSS pixels, with no console/runtime errors. Receipt: private `browser-network-round1b/receipt.json`.
- Subscription audit, including publisher texts: 946 assertions, 12 screenshots and nine CSV exports passed at the same widths, with no console/runtime errors. Receipt: private `browser-subscription-round1b/receipt.json`.

Visual review then caught default SVG path fill and unreadably scaled mobile graph labels. The correction sets path fill to none, retains full graph label size inside a local scroll region, increases node size and makes the table alternative prominent. Critic corrections also distinguish direct attribution from directory roles, change topic document counts to argmax-factor wording, show reviewed retrieval status, and reject conflicting identity merges.

Round-two corrections and the final frozen core were verified in actual Chromium. The final new-dashboard run passed 199 assertions with 15 screenshots and 15 CSV exports; the subscription audit passed 967 assertions with 12 screenshots and 12 CSV exports. Both reported zero runtime/console errors and unchanged input hashes. Final frozen-input receipts are private `browser-network-frozen30/receipt.json` and `browser-subscription-frozen30/receipt.json`. Both complete harnesses were rerun after the data-only refresh and public graph input rebinding; 199 and 967 assertions passed again with no runtime errors and unchanged artifact hashes. Earlier final receipts remain preserved as prior snapshots. The five AI panel roles also included an independent traditions/source review that passed nine targeted UI checks.

The core-publication UI run binds joint analysis `final-02`, message pilot `final-02`, final typed graph statistics and an as-of publisher-audio snapshot of 30 retained publications (304,758,859 bytes; 50,147.959625 decoded seconds; two completed local ASRs). The broader acquisition remains running; these counts are not a claim of completion. All counts are read from JSON rather than fixed in the interface.

Graph edges use opaque `#607966` on `#fffef9`, a measured 4.70:1 contrast, with solid/dashed distinction. Measured text pairs are 5.60:1 for muted body text, 7.30:1 for forest text, 8.11:1 for white button text and 6.07:1 for focus rings on the paper surface. Figures offer explicit full-size SVG links and numeric table alternatives where available.

The reproducible commands are:

```sh
python3 -m http.server 8057 --bind 127.0.0.1
BASE=http://127.0.0.1:8057 node research/expanded-channeling/dashboard_check.mjs
BASE=http://127.0.0.1:8057 node research/subscription-screening/dashboard_check.mjs
```

Each harness binds source hashes before and after, uses actual release data, exercises filters, complete exports, focus, empty results and controlled missing-data recovery, and records screenshots and errors privately. Deliberately invalid response injections are isolated failure tests; they never become released research. Browser checks are Chromium checks, not screen-reader, cross-browser or WCAG certification. 200% CSS zoom is checked as a reflow approximation; no claim of native browser zoom equivalence is made.

## Collected-audio and embedding supplements

The subsequent optional modules are implemented in `dist/channeling-network/studies.js`. The inline `optional-studies` JSON configuration enables a study only after its accepted local artifacts are copied. An empty configuration makes no collected-study, semantic-study or report requests. A declared study that fails to load has an explicit unavailable state while the accepted core remains usable. PDF, Markdown and portable LaTeX/Overleaf ZIP links are shown only after their declared local files respond successfully.

The collected-audio section binds `three-context-final-02`: 75 retained audio publications at that analysis cutoff, 27 selected/model transcript editions, and 67,424 words. The selected texts comprise ten new local ASR editions and 17 exact prior-model caption editions. These are displayed separately by publisher context, with no claim that reused captions are new independent observations. The analysis cutoff remains distinct from the separately dated collection-progress snapshot.

Its source explorer supports search, context/origin/previous-overlap filters, sorting, pagination, a keyboard-accessible provenance inspector and complete metadata exports. Whole-text and centered 300-token cosine matrices retain their actual source orders and eligible sets. Users can export all distinct source pairs, inspect keyword dictionaries/rates and topic factors, and review written-versus-recognized edition overlap without mistaking it for recognition accuracy. Utterance speakers and claimed identities remain unassigned.

The semantic supplement binds `semantic-pilot/final-01` and is described as a separately computed analysis using a pretrained embedding model. It preserves the 20-message pilot denominator, 24,436 full-text wordpieces, 113 full-text chunks and zero reported truncated wordpieces. Tables separate whole-text, 300-token and equal-chunk means. Two named-label pairs remain distinct from ten broad-civilization-label pairs. Six source-linked readings preserve their material differences, optionality and counterpoints; embedding scores are not presented as agreement, equivalence or shared identity.

Final supplementary verification:

- `studies_check.mjs`: **1,242 assertions**, nine screenshots and six CSV exports passed at 320, 390 and 1440 CSS pixels, with zero runtime/console errors and unchanged source hashes. This checks all 351 unordered full-matrix pair exports at each width, actual publisher counts, previous-caption reuse, semantic denominators and all six reading counterpoints, source focus/filters, figures, report links and isolated configuration/error states. Receipt: private `browser-additional-final/receipt.json`.
- Existing dashboard regression: **208 assertions**, 15 screenshots and 15 CSV exports passed with both supplements enabled. Receipt: private `browser-network-supplementary-final/receipt.json`.
- Screenshots were visually inspected for mobile collection coverage, the source inspector and desktop semantic comparison. Study-generated dates now display readable UTC minutes; exact timestamps remain in the source JSON.

```sh
BASE=http://127.0.0.1:8057 node research/expanded-channeling/studies_check.mjs
```

The companion paper links are labeled as the core-studies paper; the new modules do not imply that a frozen paper already contains later analyses.

## Matrix rendering at collection scale

Collected-text matrices with more than 40 eligible sources now render independently selectable row and column blocks of at most 20 × 20 cells. The selected positions and actual eligible-source denominator are explicit. Source buttons and column numbers retain the full-study order, including non-contiguous membership in the 300-token subset. Switching whole/window views resets block positions. Native selectors preserve keyboard focus after an update; source inspectors keep their original identities. Small matrices, including the released 27-source study, retain the previous complete view.

The CSV still exports every distinct source pair and preserves missing-window cells as missing. A map replaces repeated linear window-ID searches in the export path. The public JSON retains both complete matrices; the bounded view does not alter research values.

Focused verification passed **130 checks** with zero runtime errors at 320 and 1440 CSS pixels. It checked every actual 27-source matrix value and full export, then isolated in-memory fixtures of 40, 41, 81 and 229 sources. Tests exercised the threshold, independent blocks, partial final blocks, keyboard focus, source inspection, whole/window membership, explicit subset counts and reflow. Each 229-source export retained all **26,106** unordered pairs, including correct missing-window values. Two screenshots and four CSV receipts were saved privately; fixture files are explicitly marked as synthetic stress evidence and never enter released research data. Public artifact hashes remained unchanged during the test.

Receipt: private `browser-matrix-scale-round1/receipt.json`. The 229-source block render took approximately 10–12 ms in the tested Chromium context; this is an informational inner-HTML timing, not an end-to-end performance guarantee.

```sh
BASE=http://127.0.0.1:8057 node research/expanded-channeling/matrix_scale_check.mjs
```

## Frozen 229-record acquisition receipt

Both dashboards now display the same dated acquisition receipt: 229 retained publisher recordings, 31 completed local ASR editions, 71 publisher-caption-linked recordings, one recognition hold and 126 pending local ASRs. This complete finite audio frame does not establish a complete YouTube inventory or a complete transcript corpus. Twelve accepted ASR editions have timestamp-display repairs; these remain separate from held recognition output and do not establish text accuracy. Five written-message links overlap other states rather than adding five recordings.

The network coverage view provides a native text-state filter, per-publisher held/pending counts, the actual held-source diagnostic, and complete CSV fields for transcript status, active recognition holds, failed editions and normalization status. State selection uses typed receipt fields: a title containing “Held Trauma” is not classified as a recognition hold. The subscription audit adds a compact audio receipt section, including OmNa outside the original screenshot account frame, with the source-linked held record and a link to the full inventory. Failed receipt loading leaves an explicit unavailable state while channel screening remains usable. Existing frozen study denominators are unchanged.

Focused actual-data Chromium verification passed **787 assertions**, saved 12 screenshots and three complete 229-record CSV exports, and reported zero runtime errors at 320, 390 and 1440 CSS pixels. Every exported record's processing state, active-hold flag and failed-edition count matched the source JSON. Checks also covered every publisher's distribution, filter focus, the typed title-word counterexample, clearing, mobile reflow and an isolated missing-receipt response. Source/UI hashes remained unchanged during verification. Mobile overview and held-diagnostic screenshots and the desktop audit summary were visually inspected. Receipt: private `browser-acquisition-229/receipt.json`.

```sh
BASE=http://127.0.0.1:8765 node research/expanded-channeling/acquisition_ui_check.mjs
```

### Final acquisition wording

Removed the per-record “In previous frozen fits: no” line from the audio inventory: newly retained recordings and previously modeled caption text are distinct, so that terse label could imply reused captions had never been analyzed. The collected-text study continues to expose exact caption overlap. This changes wording only, not frozen source data or fitted results.
