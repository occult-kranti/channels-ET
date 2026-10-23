# Review of executed Round 2

Date: 23 October 2026. Frozen input: `research/analysis/rounds/round2/data.json`. Input hash and the hashes of the inspected implementation files are in `round2-executed-input-snapshot.json`. The earlier `round2-review.md` reviewed the baseline while Round 2 was being prepared; it is not a review of the executed Round 2 model output. This document supplies that review.

## What is now supported

The frozen build reports 925 unique videos, 227 account groups, 758 known durations and 364 exact dates. It resolves publishers for 787 videos and leaves 138 unassigned. Its language policy is explicit: deterministic langdetect, an English-likely threshold and at least four alphabetic title words. This addresses the baseline's mixed-language qualification while retaining the heuristic's uncertainty.

A pinned `sentence-transformers/all-MiniLM-L6-v2` artifact is actually used through ONNX inference, with a 384-dimensional output, recorded model revision and file hashes. These are genuine neural embeddings, distinct from the TF-IDF baseline. MiniLM is an established compact baseline, not a claim to have run or beaten contemporary Qwen or Jina models.

The implementation uses attention-masked mean pooling, vector normalization and non-overlapping 240-token caption chunks. It averages chunks into each video, then gives videos equal weight in publisher centroids. This avoids treating many chunks from a long recording as independent publisher observations. The final partial chunk has the same chunk weight as a full chunk; that is a declared modeling choice, not a token-weighted whole-document mean.

Thirty English-caption documents cover 17 publishers. Thirteen publishers have at least two captions and enter the caption similarity matrix; four have one caption and remain useful for descriptive coverage only. Thirty-four transcripts are available overall, including material outside this English pilot. All these denominators should remain separate. Pilot document lengths range from 87 to 8,588 alphabetic words; two short clips should not be described as a comprehensive sample of a channel's teaching.

## Independent calculation from the frozen matrices

I recomputed the full-caption versus trimmed-caption comparison from the exported matrices, not from a claimed result flag. The implementation removes approximately the first and last 10% of whitespace-delimited words before re-embedding.

| Measure | Round 2 result |
|---|---:|
| Eligible publisher groups | 13 |
| Unique off-diagonal pairs | 78 |
| Spearman rank correlation, full versus trimmed | 0.9695 |
| Median absolute cosine change | 0.0221 |
| Maximum absolute cosine change | 0.0990 |
| Publishers whose closest neighbor changes | 4 of 13 |

The changed nearest neighbors occur for Athina Król, Daniel Scranton, Wendy Kennedy and Pamela Aaralyn. The row-level evidence is in `round2-caption-sensitivity-check.json`.

**Admissible interpretation:** the broad pair ordering is stable under this one boundary-trimming perturbation, while some individual nearest-neighbor labels are unstable. It is not a test of accuracy, source identity or generalization to other uploads. Trimming can remove substantive material as well as introductions and advertising, so it cannot isolate the cause of a change.

## Round 3 corrections and bounded hypotheses

1. **Matched title/caption comparison.** Comparing the full title sample with only two recent caption documents changes both text class and video sample. Any claim that titles differ from spoken content must use titles for exactly the same caption video IDs or prominently retain that sampling confound. This is the strongest next test for H5.
2. **Show the stability result with both scales.** If reporting the high rank correlation, also show the four changed nearest neighbors. An aggregate can be stable while a named pair recommendation changes. Do not select the more flattering statistic alone.
3. **Separate keyword rates from topics learned by the model.** The caption indicators are regex occurrences per 1,000 alphabetic words, averaged equally over videos. They are neither time spent on a topic nor independently validated semantic categories. The short 87-word caption can have a large rate from a few matches; display its denominator.
4. **Metadata wording.** The top-level `textMethod` in the Round 2 JSON still describes only keyword indicators and TF-IDF. Update it to mention the separate executed neural title/caption pilot. The source's generated/manual caption flag says how captions were supplied; it does not establish speaker identity, original spoken language, transcription accuracy or the absence of dubbing.
5. **Add explicit figure captions for neural/caption results.** The frozen Round 2 `figures` list still has only the four baseline figure definitions. New figures should specify model/revision, 30 documents versus 13 matrix-eligible groups, equal-video aggregation, masking, uncorrected automatic captions and the lack of speaker diarization. Neither 0.8 cosine nor a matching dictionary word establishes agreement on a claim.
6. **Context controls remain unresolved.** No matched non-channeling genre control, blinded human coding or recording-level duplicate audit is present. Therefore 'shared language in this pilot' is supportable; 'unusually convergent independent communications' is not. The 2026 direct studies use a different elicitation design and their numeric scores are not a reference threshold for this corpus.

## Code observations that passed this bounded review

Title and transcript text remain separate. Full transcript text is not copied into the public output by the inspected semantic module. The code exports derived vectors, IDs and hashes. No eligible masked neural title had fewer than two remaining alphabetic words in the frozen set, so the potential empty-string embedding problem was not observed. Pair tables retain their own nA/nB denominators. Scientific claims should use these measured limitations rather than speculative extra fixes.

This is model-agent code/interpretation review and a direct recomputation of one sensitivity diagnostic. It is not human peer review, a full independent encoder reimplementation, visual screenshot QA, or a replication of an external paper.
