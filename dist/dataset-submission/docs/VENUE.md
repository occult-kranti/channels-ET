# ICWSM dataset-track target — verified 8 November 2026

The current official target is **ICWSM 2027, Datasets track, 15 January 2027 at 23:59 AoE** (16 January at 11:59 UTC). The requested “Jan 17” date is not supported by the inspected official call. This is a working research package; it has not been submitted and is not yet submission-ready.

Primary guidance: <https://www.icwsm.org/2027/submit/>. Retrieved 2026-11-08, HTTP 200, SHA-256 `b19d00c07a9fcfeca5e3eb9d900e7c168ef9677134678a7400777249ce02d29e`.

## Requirements and decisions

| Requirement | Verified guidance | Package decision / remaining work |
|---|---|---|
| Deadline | Dataset submissions only in January; 15 January 2027, 23:59 AoE | Calendar target corrected; no submission made |
| Length | 2–10 pages, excluding paper checklist | Target ≤10 pages including references; keep substantive material within the limit |
| Format | AAAI two-column, US Letter, English, high-resolution PDF | Unmodified official `aaai2027` style, working-preprint mode |
| Review | Single-blind; no revise-and-resubmit option | Human authorship TBD; anonymization is not required for this track |
| Dataset | Link to actual dataset, content/structure, data quality and collection, applications, FAIR documentation | Public metadata/derived dataset and private source archive are explicitly distinct |
| Persistent identifier | DOI indexing the dataset required | **TBD**; a GitHub URL or SHA is not a DOI |
| Checklist | All questions unaltered; first section after references, before appendices; missing checklist causes desk rejection | Official 35-question transcription retained; evidence-backed draft answers need human review |
| Generative AI | Disclose content creation in Acknowledgements; no AI author | Draft discloses ChatGPT/Codex roles and model-agent reviews |
| Ethics/assets | Explain risks, licenses, consent, PII, reproducibility in checklist; adhere to AAAI conduct | Do not invent IRB approval, consent or media license; release basis remains asset-specific |
| Scope | Socially relevant web/social-media contribution; algorithm-only work is outside scope | Study measurement and preservation of public spiritual-media discourse; no supernatural verification claim |

The official dataset section includes a copied sentence saying “Accepted demo papers…”; the same page’s publication section explicitly includes accepted dataset papers. This apparent editorial typo is recorded rather than silently used as contrary policy. The current call links a 2026 Overleaf display template but the **AAAI 2027 author kit**. We use the current 2027 kit. The linked ICWSM checklist PDF has a 2025 title and older overview text; its unchanged questions remain the ones linked by the current call. Recheck these artifacts before actual submission.

## Exact inspected policy passages

- Dataset deadline: “15th January 2027 AoE.” General deadline rule: “All deadlines are 23:59 AoE (Anywhere on Earth).”
- “2-10 pages (excluding paper checklist).”
- “Dataset submissions require a DOI (Digital Object Identifier) that indexes the dataset.”
- “Documentation following FAIR principles (Findable, Accessible, Interoperable, Reusable).”
- “The completed checklist must be unaltered (i.e., no questions removed).”
- “Any use of generative AI tools must be disclosed in the Acknowledgements section.”

## Access and publication boundary

The inspected call requires an actual dataset link and DOI; it does not state that every collected audio/video must be republished. The contributed dataset therefore needs a precise public scope and reproducible uses. Private raw media may support authorized recomputation, but it must not be advertised as an openly accessible full-text/audio dataset. A DOI deposit, asset-rights review and adequate reviewer access remain unresolved. FAIR accessibility can describe authentication conditions; it does not erase copyright, privacy or platform obligations.

## Writing precedents inspected

- **YouNiverse (ICWSM 2021)**: collection/preprocessing pipeline, dataset schema, channel-sampling audit, descriptive figures and limitations. Distinguishes metadata releases from omitted comment text. Its popularity-based sampling correction cannot be imported without a comparable sampling frame.
- **Global YouTube Trending Dataset (ICWSM 2026)**: publisher metadata verified via Crossref; author manuscript inspected for collection intervals, schema/composite keys, expected-versus-observed snapshots, ethics, FAIR and limitations. A fixed snapshot schedule supplies its denominator; our first-party seed crawl does not supply total channel uploads.
- **MetaHarm (ICWSM 2025)**: publisher-supplied abstract and public Zenodo record inspected, not full paper in this run. Separates domain-expert, model and crowdworker annotation; useful precedent for keeping annotation origins distinct. Do not transfer its harm labels to this corpus.
- **Hijab-comment dataset (ICWSM 2025)**: publisher-supplied Crossref abstract inspected only; a religious-discourse precedent, not validation of the present annotations.

Publication venue and metadata verification do not imply independent reproduction of any cited paper. New publisher PDF attempts returned HTML bot-check pages; they are recorded as failed full-text access, not read PDFs. The retained YouNiverse PDF and an openly available author manuscript provided the actual layout/method inspection.

See `sources.json`, `requirements.json`, and the manuscript’s `related-work.bib`. Source response bytes and exact inspection notes are retained in the private research ledger; the public ledger stores URLs, hashes and access depth.
