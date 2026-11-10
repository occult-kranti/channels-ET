# Dataset workbench design

The additive static workbench lives at `dist/dataset-submission/`. It preserves the existing collection ledger and Channel Lab. Design Partner's create, accessibility and verification workflow informed the implementation; the Atlas forest-green, cream and serif identity remains consistent with those workspaces.

## Primary tasks and views

1. **Overview:** identify the exact selected corpus, editions, word count, collection state and release status.
2. **Publisher contexts:** filter source groupings, compare coverage, open a source-specific page and export the exact filtered rows.
3. **Publication explorer:** filter selected metadata by text origin and context; inspect provenance and export every matching row across pagination.
4. **Compare and analyze:** inspect learned topic terms, the document projection, context similarity values, sensitivity results and research figures.
5. **Paper and methods:** open the actual PDF and LaTeX release artifacts, verify the official deadline and track open submission requirements.
6. **Data and archive:** distinguish public metadata from private source files, inspect module hashes and download release artifacts.

The dominant interaction is comparison. Aligned table columns carry counts, while publishers and publications have stable deep links. Text origin and missing totals remain visible. A native source-record dialog supports keyboard interaction and restores focus on close. Filters use explicit apply/reset controls; CSV exports use the complete filtered set, not just the current page. CSV cells neutralize spreadsheet formula prefixes.

## Information contract

`manifest.json` follows the collection ledger module contract: `modules[name] = {file, bytes, sha256, required}`. `dataset` is mandatory even if its descriptor omits `required`. Analysis, venue and archive modules can fail independently. Every JSON module is byte-length and SHA-256 verified before rendering. Unsafe relative paths are rejected. Optional module faults remain visible; required failures withhold the dataset and present a reload action. HTTP or HTTPS external source URLs are allowed; arbitrary schemes are rejected.

The dataset module is the canonical source for selected publication metadata. UI adapters bind its exact fields rather than infer a complete channel count. `selected_unique_encoded_media` and `unique_encoded_media_joined` retain their encoded-file units. They are not a count of unique sessions, publication units or YouTube videos. Unknown channel lifetime totals are rendered **Unknown**, never as zero or as a completion percentage. The UI does not add legacy corpus units and new publisher editions.

The analysis module must match the dataset’s `frame_sha256` when it supplies that frame binding. The loader also checks an optional `dataset_sha256` against the dataset module’s release hash. A hash-valid analysis from a different frame is withheld; input bindings remain inspectable. Figures and downloadable artifacts are offered only when included in the release manifest. Full source bodies, private paths, raw media and claims of public full-transcript access are excluded from this dashboard's exports.

## Responsive and accessibility decisions

The desktop sidebar becomes a six-link grid on narrow screens. Dense scientific tables keep local horizontal scrolling with a focusable, named region. The document itself must not scroll horizontally at 320 CSS px. Forms use persistent visible labels and 16 px inputs, important controls are at least 44 px tall, and indicators retain text alongside color. Skip navigation, semantic heading hierarchy, native links and buttons, `aria-current`, a live status region and visible focus support keyboard navigation. No external font, animation framework or chart dependency is required. Reduced motion and forced colors have explicit CSS accommodations.

All plots carry captions and numerical data or source metadata. The projection is diagnostic; it does not turn proximity into a claim of agreement or authenticated identity. Matrix values are readable without color. Small contexts and source-origin confounding are visible in their analysis metadata.

## Reproducible verification

Run the repository HTTP server, build the public manifest, then:

```sh
DATASET_BASE_URL=http://127.0.0.1:8765/dist/dataset-submission/ \
DATASET_TEST_OUTPUT=/dev/shm/dataset-dashboard-browser \
node research/dataset-submission/design/browser-check.mjs
```

The script reads actual producer modules, checks all six views at 320 / 390 / 1,440 pixels, exports filtered records, exercises pagination, provenance-dialog keyboard behavior, history, empty/reset states, invalid contexts, escaped input, 200% CSS zoom, reduced motion and required/optional module corruption. It saves screenshots and a receipt outside the public source bundle. A browser accessibility tree or keyboard check is not claimed as a screen-reader test.
