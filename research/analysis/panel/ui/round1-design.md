# Round 1: analysis surface decision record

Baseline: Channeling Atlas at source commit 851ab6d2c0ea8de749cd163389f71035180c6bdc, inspected as static source. No browser inspection performed by UI worker. Existing data index is not a census of channels or uploads.

## Product invariants
- Preserve the ivory/moss editorial identity, all existing routes and source attribution.
- New primary task: compare observed video samples between publishing accounts and understand data coverage before interpretation.
- Distinguish a publisher account from a human medium, and title/summary metadata from transcript content.
- Keep sample sizes, missingness and captions next to each figure.

## Accepted round-1 architecture
1. One Analysis route, with three views: channel table, selected-channel inspection, corpus comparisons/method.
2. Start with coverage statement and the exact observed sample counts, not a ranking of entities or people.
3. Searchable/sortable account table lists video n, duration n/coverage, arithmetic mean, median, IQR and exact-date n. Missing values remain em dashes with clear missing-data labels, never zero.
4. Account selection reveals duration distribution, observed dated uploads, title-topic frequencies and nearest accounts with the method named. Full data and figures downloadable.
5. Comparative figures show titles/summary corpus as separate layers. Genuine learned embeddings only appear if the pipeline actually executed them; lexical vectors explicitly named TF–IDF.
6. Plot captions state unit, denominator, observation window, exclusions and scope; associated data tables remain available for charts.
7. Loading, failed-fetch, empty-filter, too-few-observations states designed explicitly. Native controls and visible focus preserved. Narrow layouts stack controls and locally scroll wide tables.

## Rejected / deferred
- No galaxy illustration, 3D network or popularity score: these obscure sampling and publication relationships.
- No channel-wide average or upload-frequency census claim from selected videos.
- No transcript topic analysis label for metadata or researcher-written summaries.
- No identity or causal inference from vocabulary proximity.

## Skill applicability
| Skill | Application | Status / limitation |
| --- | --- | --- |
| impeccable | New surface within existing world; dense Compare/Read layout; bounded QA | SKILL.md read. Launcher absent, as are referenced playbook/craft files in installed package; fallback source inspection used. |
| panel-led-product-redesign | Three rounds require reviewed changed artifacts; findings/decision/acceptance ledger | Active; round 1 design now, implementation pending opened checkout. |
| design-partner | Native control semantics, chart data alternatives, stable comparison lanes, responsive layout | SKILL.md plus foundations, modes, accessibility, verification read. |

## Acceptance checks
- New route opens from main nav and direct hash.
- Each channel with known lengths shows mean/median and duration numerator/denominator.
- Unknown-length channels remain in table and can be filtered.
- Every displayed graph has a caption identifying sample coverage and text layer.
- Switching a channel changes all per-channel metrics/plots coherently.
- Filters have empty and reset states; link targets and downloads resolve.
- Browser task through root verifies selection, table sorting/filtering and chart/data alternatives; static syntax check passes.
