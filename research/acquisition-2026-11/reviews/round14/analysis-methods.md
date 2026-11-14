# Round 14 — Analysis methods review

Snapshot: `research/acquisition-2026-11/reviews/round14/snapshot.json`, canonical payload SHA-256 `677b2b7a9b831c0d03eaa21362d2db15ca0f144dbb3adf5dc33d20b5eed4d136`. AI technical review only; not human annotation or human peer review.

## Verdict

Conditional PASS, with the proper-name maximum corrected before citation. The reviewer independently reproduced document, segment, word, Q&A, family, NMF, KMeans, network and review-hash results from the private segment index.

## Findings and required follow-up

- **H1 — wrong sensitivity maximum:** synthesis reported 0.42%; the recomputed maximum was 0.62% for `-8k6d9StYig`. Correct the narrative and bind extrema in verification.
- **M1 — ARI self-comparison:** `seedStabilityARIvsBase` included the trivial ARI=1 base-versus-base comparison. Use only the other nine seeds and recompute all values.
- **M2 — zero-pattern orientation default:** unmatched answers were labeled descriptive. Emit `unclassified_default`, disclose its count, and update the protocol.
- **M3 — verification depth/staging:** consistency checks could not detect a wrong statistic, and the packaged manifest lagged current analysis. Recompute headline metrics in verification and restage.
- **L1 — protocol scope:** replace the 13-pilot/~12-document language with 34 included documents and 43 terminal candidates.
- **L2 — convergence wording:** report actual convergence state unconditionally rather than saying nonconvergence “would” matter.
- **L3 — stopword asymmetry:** `what` and `who` were not treated like other WH-stopwords, producing a large generic family. Apply WH-stopwords uniformly and document it.
- **L4 — answer-cap semantics:** clarify that `complete_line_cap` means the extraction window filled, not that the answer ended.
- **L5 — truncated risk plot:** use all families, including singletons, rather than the top-50 display subset.
- **L6 — singleton registry:** expose `recurrence_scope` in `common-questions.csv` to distinguish cross-video, same-video-only and singleton rows.

## Evidence boundary

No semantic-equivalence, repost-finding, truth, or entity-reality claim was accepted. The large generic token family demonstrated why token recurrence is not substantive agreement.
