# Dashboard round 9 — final verification

Reviewer: AI implementation/browser role. The root rebuilt the complete frozen data/dashboard pipeline before this pass. No public data or application files changed during verification. This is not human usability testing or a full accessibility audit.

The final browser run passed **57 checks with zero page errors**. It exercised all five views at desktop 1440px and narrow 390px widths, filtered account/query/Q&A scopes, empty states, filtered CSV downloads with explicit false flags, the six-row retrieval-cutoff sensitivity table, source-pair disclosures, keyboard form submission, keyboard disclosure activation, and page reflow under 200% CSS zoom. CSS zoom is the executed reflow check, not a claim that browser UI zoom was automated. Five public PDF/ZIP/SQLite/JSON artifact routes returned successful responses.

Final corrections after round 8 exposed all 127 candidate pairs through the full JSON download while marking the ten displayed and 100-row compact preview, and added the six retrieval-cutoff comparisons and upload-pair concentration context. The public database, summary, PDF and ZIP were compared byte for byte with their reviewed sources.

The PDF is the final 25-page working manuscript. Its text and page rendering are reviewed by the paper workstream; this pass verifies its public route and bytes.

## Bound artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `paper.pdf` | 459228 | `9eb942301eab65212b1c1f0aaae9c938e7f86b01d6e7ca7c9e6e90e7a8bd64e1` |
| `source.zip` | 118072 | `c0bf5184a71029fe7f1fbe38d5ca259d4a789866a69622b300665e3d6a5fa4d4` |
| `qa-candidates.sqlite` | 925696 | `5c8e8eb8dc0d1a67461719ebfc5d35b18f03a30eed77a9acbe7a06101fa8321c` |
| `qa-summary.json` | 245639 | `7cc9705a73bed33523397b0e4812bb47974dfc21a8a48c83d294c53948a46128` |
| `qa-question-pairs.json` | 86407 | `17629517ea6d187d92aab30079be8d5b61f2fc581e54012410e5bf10a544a476` |
| `app.js` | 34927 | `18737c6377638d09ded0f1aca0cd17d910063a4759337c3b24cd1990cba77238` |
| `styles.css` | 9307 | `ee3cde4b2c135ec84791a5525a26f63cc9871571c18b044beb2a266f813d49d1` |
| `index.html` | 2072 | `745eb05cd91bf2fe198cafd9f0e1f355cc5a1ec34c0e5f6fe24b80eb5fcc97a6` |
| `diagnostics.json` | 297579 | `1a288dea2475eedc4b1acb2a5cf0a01196c2af1c5b15a41443e3b6a9a2eb2545` |
| `acquisition-status.json` | 2071 | `07e87b9ee175c1ed1cf9946303671923fa5153fe0a196bd920bdfdbfe0243c75` |

The full machine-readable result is `dashboard/round9-browser.json`; current screenshots are `dashboard/round9-overview.png`, `dashboard/round9-questions-mobile.png` and `dashboard/round9-questions-mobile-viewport.png`.

Material limits remain: no newly successful YouTube retrieval, no multi-practitioner transcript Q&A corpus, no verified speaker segmentation, no human construct/audio validation, unavailable shared Data runtime, and no callable Sites publishing capability. The historical buildless application remains available and links to this extension.
