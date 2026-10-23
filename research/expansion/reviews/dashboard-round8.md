# Dashboard round 8 — implemented corrections

Reviewer: AI design/implementation role. This is browser and source verification, not participant usability research or independent human peer review.

Reviewed the changed round-7 explorer and implemented a second revision. Baseline source evidence remains the frozen 925-upload snapshot; the new Q&A and acquisition layers retain separate source classifications.

| Finding | Evidence and impact | Decision / implemented correction | Acceptance check |
|---|---|---|---|
| New paper entry linked the historical PDF | Initial explorer header pointed to rounds 1–6 artifact | Current PDF/source links point to expansion paper artifacts; earlier paper remains explicitly labeled in Methods | Build copies current PDF/ZIP into expansion; local request checks |
| Planned queries had no visible practitioner coverage | 590 query rows could obscure absence of text for most of 106 candidates | Added independently searchable inherited identity/Q&A roster; zero means absent release text, not never answered questions | Bashar filter resolves roster to Darryl context; candidate status/source leads visible |
| Q&A publisher grouping could be mistaken for multiple practitioners | QA worker corrected null-ID aggregation | 27 resolved account IDs, 7 unresolved name groups and 105 candidates explicitly separated; one practitioner remains | Browser count/disclosure check |
| Pair preview lacked immediate source/independence detail | Lexical neighbors are correlated derived summaries | Added source recording links, source candidate IDs, original-session independence unknown, answer agreement unassessed and separate answer-gist cosine | Open pair detail in rendered browser |
| Preview scope was not explicit | Ten rows shown from 127 qualifying candidate pairs | Label ten highest-scoring preview and link complete 127-row JSON; offer 12-pair model-only close-reading record | Browser disclosure and JSON download checks |
| Methods claimed language/format strata already used | Independent methods reviewer compared collector to UI prose | State actual historical-pilot + one nonpilot upload per publisher deterministic rule; future strata labeled proposed; exact TF-IDF settings/cutoff documented | Code review of collection policy and methods copy |
| Access status could go stale on future builds | Root source review found hard-coded preflight-only description | Build now reads dated acquisition-summary.json; text reports observed successes/blocks/date and distinguishes snapshot from live status | Current snapshot shows zero successes/one block; future positive branch cannot silently say zero |
| Missing duration definition could drift | Overview used non-null filter while caption said positive | Filter positive seconds, preserving missing values | Current measured duration count remains 881 |
| Spreadsheet cells can interpret public strings as formulas | Export contains untrusted publisher/title/paraphrase strings | Neutralize formula-leading string cells while retaining exact source JSON | Source inspection; filtered CSV browser download scope checks |
| Narrow nav could hide the selected tab | Five views exceed narrow width | Horizontal navigation scrolls selected view into sight; repeated heading compacts on secondary routes | 390px route checks and screenshot inspection |

`dashboard/round8-browser.json` records the executed rendered checks, screenshot paths, and zero page errors. Desktop 1440px and mobile 390px widths were exercised across all five views; account, query and Q&A filters, filtered CSVs, meaningful empty states, pair details and keyboard focus were checked. No claim of a complete accessibility audit is made.

The shared Data runtime/prebuilt contract remains unavailable: provider read of `skill://Plugin_fc9843a6fb34819195d6c7802398a8a7/shared/data-app.md` failed, and filesystem discovery found neither `data-app.md` nor `prepare-data-app.mjs`. The explorer extends the existing buildless HTML/CSS/JavaScript stack. No Sites publishing tool is callable in this environment; deployment is not verified.
