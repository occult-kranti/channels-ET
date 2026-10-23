# Methods panel — expansion round 1

Role: AI methods/literature reviewer. Baseline: GitHub main 1d6eb36; existing 925-upload / 30-English-caption release. This is technical review, not human peer review.

| Finding | Evidence | Impact | Decision / acceptance check |
|---|---|---|---|
| Identity audit must precede expanded human/entity counts | README N1; uploader/practitioner/entity/session differ | False counts and wrongly attributed answers | Stable separate IDs, unresolved aliases, no human count from account rows |
| Flat playlist metadata is incomplete | Official yt-dlp README, --flat-playlist / approximate_date | Unknown or approximate dates could become spurious exact history | Metadata layer fields retain status/source; no fabricated dates |
| Current source access may differ from frozen derivatives | Handoff excludes raw captions and model weights | Cannot build transcript Q&A from vectors | Every Q&A row states source layer; no transcript claim from digest or metadata |
| Q&A extraction needs ambiguity fields | ASR punctuation loss; naturalistic host/response mixture | Rhetorical/host question mislabeled as audience/ET answer | Candidate-only labels, time spans, cue, speaker unknown, review state, source hash |
| Topical overlap is not answer agreement | Prior JSE2023/direct-study register and methods synthesis | Unsupported substantive conclusions | Neighbor scores called lexical/semantic resemblance; relation coding unresolved until validated |
| Keyword methods need precise names | README inspections: BERTopic and KeyBERT have distinct mechanisms | Method inflation and irreproducibility | Query keywords, regex counts, TF-IDF, NMF and embedding keyword methods distinguished |
| Panel cannot certify human construct validity | Existing paper TBD declarations | False reliability and novelty claims | AI review label preserved; human validation remains pending |
| Acquisition failures must halt affected route | Transcript API documents RequestBlocked/IpBlocked | Tool may encourage proxy evasion | Stop/log block; no residential proxies, cookie import or access bypass |
| Scholar retrieval blocked in this instance | retrieval-receipt.json, OJS/ACL 403 tunnel | No fresh fulltext reading | Carry forward source depths; cite inspected historical register without new-access claim |

Accepted implementation priorities: exact query ledger; roster identity table; provenance-separated Q&A SQLite schema; caption versus digest availability tables; account-balanced keyword/distribution plots; metadata-only search crawl with failure logs; explicit executed/optional method register. Recheck changed artifacts in round 2, then apply corrections before round 3.

Source artifacts: expansion/literature/METHODS.md, scholarly-register.json, software-register.json, retrieval-receipt.json, package-versions.json. Retrieval inspected ten README/license files. Five scholarly/API destinations failed; none were worked around.

Implementation alignment correction: the query protocol now names the actual three exact-name templates plus inherited entity-label pairing. The 590 planned queries do not include channeled/channelling/medium spelling-family expansion; that remains proposed sensitivity work.
