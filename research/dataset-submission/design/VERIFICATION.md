# Dataset dashboard verification

The additive dataset workbench passed **29 browser test groups** in Chromium through Playwright against actual producer modules and the public release manifest:

`71fa8b4868887e6e94882290d97f869a22dee41d38f12d10430b0abc4ec23868`

`browser-receipt.json` preserves the time, exact manifest hash, UI asset hashes, test groups and named screenshots. `browser-check.mjs` is the reproducible harness. A later release may change documentation or archive status; these assertions describe the identified release and UI assets, not future bytes.

## Executed coverage

- All six top-level views at 320, 390 and 1,440 CSS pixels, without whole-document horizontal overflow. Dense tables retain local scrolling.
- All six views at 200% CSS zoom and with reduced motion enabled.
- Publication and context counts bound to the actual dataset; direct YouTube downloads remain 0, and unobserved upload totals remain Unknown.
- Context name filtering, no-result/reset states and filtered CSV export; the selected export contained exactly one matching context.
- Ra profile navigation, 106 selected publication records, full filtered metadata export and 40-record pagination. Its upstream 2,620 audio segments remain distinct from whole-session text units and selected media joins.
- Publication/context source dialogs, Tab containment, Escape, close-button operation and focus restoration; browser Back/Forward navigation; unknown-context recovery; escaped search input.
- Comparison matrix switching from the largest ten to all 26 publisher contexts, with numeric values and source-count labels.
- All six bundled research figure images loaded. SVG full-size views and downloadable figure assets are available through registered release paths.
- Actual public metadata ZIP, paper PDF and Overleaf source ZIP downloaded and verified against their manifest byte lengths and SHA-256 values. The paper view renders the official 15 January 2027 AoE deadline, 8 body/reference pages and 10 total pages with the checklist.
- Required dataset hash, byte-length, HTTP, descriptor-absence and unsafe-path faults withhold the release. Hash and HTTP faults for each optional analysis/archive/venue module preserve independently verified data and show the failure. A hash-valid analysis with a mismatched source-frame hash is withheld.
- No uncaught page JavaScript errors during nominal tasks.

## Visual inspection and repairs

Desktop and mobile overview screenshots were inspected, together with the matrix, research figures and the mobile Ra upstream-collection panel. Repairs found during executed tests included a query serializer dropping the meaningful matrix selection `all`, desktop grid minima overflowing under 200% CSS zoom, dialog metadata needing a keyboard-scrollable region, and legacy venue paths masking the correct bundled paper paths. The final run passed after these fixes.

The forest/cream Atlas identity, accessible text labels, local table scrolling and source-specific units are preserved. The data page distinguishes prepared private storage from verified remote retention; a pending destination is not presented as a successful backup. Figures expose full-size SVG and PDF downloads so dense scientific labels are not limited to the on-page preview.

## Limits of this verification

This was a Chromium/Playwright run, plus visual screenshot inspection. It is not a screen-reader test, a cross-browser certification, a full WCAG conformance audit, or a native browser zoom test; the zoom check used CSS zoom explicitly. No offline service-worker installation is claimed. Scientific validity, acquisition completeness and private-upload receipts are separately assessed by the dataset, analysis and archive pipelines.
