# Independent methods panel — continuation round 11

Reviewed candidate 10 archive `5681c632f4b4f0fd857711d0d7ee2c6483bd39963cd2ff48c564d7710e7f2008`, including the actual 14-page paper PDF `0ad9ae29da658a55c14acdbdced2abbdfda96b985a519745912f08230f1ec081`. Paper text/source/citations, fresh scholarly registers, model code and saved outputs, actual adapter weights, and collector code were inspected. This is model-agent technical review, not human peer review, source-audio observation or a new inference run.

The paper's core distinctions are sound: train-only retrieval may not contain the held-out answer; eight held-out questions do not rank model families; strict underscore-marker emission is narrower than plain-language refusal; citation-label membership does not establish entailment; source-family proxies do not establish original-session independence; and pretraining contamination is unknown. All new research claims stay within one practitioner's AI-digest paraphrases.

| Finding | Consequence | Correction and current verification |
|---|---|---|
| M11-01: pagination used a filtered entry count | Unavailable slots could shift resume and falsely mark a listing complete | Acquisition owner preserves raw slots. Independent `[valid, None, valid]` fixture at cap 3 remains incomplete and resumes at slot 4. Passed. |
| M11-02: quota checks ran only while process was alive | A fast zero-exit process could leave an oversize file counted as success | Post-exit file/total/reserve validation added. Independent already-completed oversize fixture becomes `quota_stopped`, with no successful artifact. Passed. Polling cannot promise zero transient overshoot. |
| M11-03: same/cross quarantine groups are question-selected | The .171 all-neighbor versus .044 cross-group comparison cannot identify a source-reuse mechanism | Owner added a shared-question-support standardization. Independent verification finds 93 shared-support pairs in three bins, 34 excluded, standardized means .297186 within and .044210 cross. This is a new pool; high-similarity bins have no cross-group support. Coarse bins retain confounds. Revised paper must preserve those distinctions. |
| M11-04: response budgets differ | Lexical full-gist copying and 40-token generation have unequal opportunities for overlap | Requested adjacent table/prose disclosure and no algorithm-ranking interpretation. Recheck revised candidate. |

Independent executed verification:

- **381 model checks:** all 50 saved outputs, eight-question/two-control arm denominators, token F1 recomputation, strict markers, citation membership, retrieval IDs restricted to training, split disjointness, independently reconstructed source-proxy components, training receipt and finite/nonzero saved LoRA B matrices. No model inference repeated.
- **420 alignment checks:** explicit count/smooth-IDF/sublinear-TF/L2 representations and direct sparse dots, with no producer/vectorizer import; every retained neighbor score and new shared-support bin/weight/mean recomputed.
- **8 adversarial collector checks:** cursor/completeness, post-exit oversize validation, stale/blocked/wrong preflight refusal, current fixture field acceptance and sanitized error strings. Zero external requests; mock results are not research data.

The inspected 20+12 model interpretations from the earlier phase remain derivative-text interpretations, not human judgments. Fresh peer-reviewed precedents support branch separation and held-out evaluation, but their human reliability or calibrated RAG intervals do not transfer. The actual official style now matches the fresh source-pinned kit; historical style files remain preserved.

Two functional bugs were corrected during this review; the new analytic control has been independently checked. Final closure waits for the revised paper/dashboard and root's next frozen candidate. The detailed file hashes and finding states are in `literature/methods-round11.json`. Access failures, incomplete source evidence, human validation, source rights and submission decisions remain explicit limitations rather than technical-test successes.
