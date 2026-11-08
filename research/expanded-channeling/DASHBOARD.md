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

The final UI run binds joint analysis `final-02`, message pilot `final-02`, final typed graph statistics and an as-of publisher-audio snapshot of 30 retained publications (304,758,859 bytes; 50,147.959625 decoded seconds; two completed local ASRs). The broader acquisition remains running; these counts are not a claim of completion. All counts are read from JSON rather than fixed in the interface.

Graph edges use opaque `#607966` on `#fffef9`, a measured 4.70:1 contrast, with solid/dashed distinction. Measured text pairs are 5.60:1 for muted body text, 7.30:1 for forest text, 8.11:1 for white button text and 6.07:1 for focus rings on the paper surface. Figures offer explicit full-size SVG links and numeric table alternatives where available.

The reproducible commands are:

```sh
python3 -m http.server 8057 --bind 127.0.0.1
BASE=http://127.0.0.1:8057 node research/expanded-channeling/dashboard_check.mjs
BASE=http://127.0.0.1:8057 node research/subscription-screening/dashboard_check.mjs
```

Each harness binds source hashes before and after, uses actual release data, exercises filters, complete exports, focus, empty results and controlled missing-data recovery, and records screenshots and errors privately. Deliberately invalid response injections are isolated failure tests; they never become released research. Browser checks are Chromium checks, not screen-reader, cross-browser or WCAG certification. 200% CSS zoom is checked as a reflow approximation; no claim of native browser zoom equivalence is made.
