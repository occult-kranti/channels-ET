# Round 2 — actual-output independent review

Reviewer: `/root/method_panel`. Frozen second-build input SHA256 `f5b96cd04d9fb9ccf5db34e0fc0b056f0dc3d7a53579b86361f90d9861dc5024`, from `research/analysis/rounds/round2/data.json` / then-current `dist/analysis/data.json`.

## Executed verification

The same independent aggregate verifier passes 3,168 checks against 925 unique video IDs, 227 account routes, 758 duration observations and 364 exact-date observations. It recomputes means, medians, quartiles, denominators and reference integrity from individual rows.

A second independent verifier reads actual NPZ vector files, not producer functions. All 762 checks pass: 682 title vectors, 30 caption vectors and 30 trimmed-caption vectors are finite, unit-normalized and 384 dimensional; video IDs resolve; eligible title constraints hold; channel centroids reconstruct from equal-video means; all exported cosine matrices reproduce by dot product, are symmetric with unit diagonals and valid ranges. The title matrix covers 24 groups with minimum five titles; caption matrices cover 13 groups with minimum two included documents. This verifies vector aggregation, not the substantive accuracy of a neural model.

Independently read the source caption JSONs and reproduced all 270 topic-hit counts. The reported text hash matches the source JSON file bytes, not the analysis-text string. Word-count denominator requires a more exact tokenizer definition before final independent rate verification; apparent differences from a simple alphabetic-token regex are consistent with contraction handling, not an established numerical defect.

## Actual visual inspection

Opened all four second-build PNGs: duration, coverage, title-topic heatmap and lexical-similarity heatmap. Labels, units and colorbars are generally legible. Duration means/medians/IQRs clearly distinguish a few long-form publisher samples from many shorter samples. That graph must not be interpreted as whole-channel ranking. Heatmap diagonal and pale low off-diagonal lexical similarities are consistent with numerical outputs.

Observed defect: the Japanese publisher name renders as missing-glyph boxes in duration and coverage plots. Use the known ASCII account handle as an explicit fallback, or provide a suitable font. Some long labels are truncated without an ellipsis; retain the full mapping in the downloadable table and show ellipsis or a stable short label.

## Required final-round repairs / explanations

1. Repair missing Japanese glyphs and make shortened labels explicit.
2. Rename `textSha256` to `sourceFileSha256`; add `normalizedTextSha256` if reproducibility of exact model inputs is claimed.
3. Specify the exact word-token regex (including contraction treatment) and verify per-1,000-word rates against it.
4. Explain 807 eligible English-likely titles versus 682 embedded titles (attribution/cleaning eligibility) and 34 retrieved caption documents versus 30 included English pilot documents. Identify every exclusion reason rather than only displaying totals.
5. The requested final hypothesis analysis must use executed sensitivity comparisons. Trimming first/last text portions tests sensitivity to those portions; it does not isolate advertisements, hosts or introductions without diarization.
6. Keep title vectors, full-caption vectors and trimmed-caption vectors distinctly labeled. Their cosine scales are model/text-length dependent; larger caption cosine than title cosine does not establish greater agreement.
7. Display the small caption denominators at each channel and in any similarity plot. Two purposively selected videos per channel cannot support population-level thematic distinctions or causal lineage claims.

## Interpretation bounds retained

Many supplied titles are English renderings of channels whose current localized watch titles differ. The English-likely rule describes available title text, not the original language of speech. Automatic captions may contain hosts, questions, advertisements and the attributed voice; no speaker-level statement can be inferred without separation. Source-family dependence and reuploads remain unresolved at recording level even after exact video-ID deduplication.

The first-build date/evidence display defects were sent to the UI worker; it reports repaired schema bindings and tests. Final release should verify repaired UI against the final dataset. Round 3 should respond to this actual-output review and preserve this snapshot rather than silently replacing its provenance.
