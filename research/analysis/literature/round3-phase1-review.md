# Phase 1 final literature and methods review — executed Round 3

Reviewed 23 October 2026. This review concerns the actual final dashboard data, analysis implementation, report prose and figure definitions. It does not begin the separate manuscript phase. File hashes are in `round3-input-snapshot.json`; independently reconstructed numerical checks are in `round3-independent-check.json`.

## Decision

The report supports a descriptive, source-linked account and upload index with a bounded English caption pilot. It does not support a worldwide count of active human mediums, a population estimate, a validated ontology of subjects, or conclusions about the existence or origin of the claimed communicating entities. No substantive methods or literature blocker remains for publishing Phase 1 with its existing limitations.

## What was actually checked

- Read the final `data.json`, `build_report.py`, executed `semantic_analysis.py`, all nine figure definitions/captions, and the separate Scranton concordance/window artifacts.
- Reconstructed all four sensitivity diagnostics from the exported matrices, rather than accepting the reported summaries. Differences from exported pair summaries were below 1e-6 and arose from rounding.
- Independently reconstructed matched title and caption account centroids from public NPZ numeric vectors using the same video IDs; confirmed 25 matched videos, 11 account groups with at least two matched videos, and 55 off-diagonal account pairs. This reruns aggregation, not embedding inference.
- Inspected the actual PNG renders for caption similarity, matched title/caption indicators, within/between caption similarity, and duration-format comparison. Axes, legends and visible values were consistent with the data. This review is not a comprehensive browser/accessibility audit; that is a separate panel responsibility.
- Checked literature/source-access claims against the 16-paper bibliography and inspected supplement records. No raw captions or third-party full texts were copied into the public literature folder.

## Numerical findings and admissible interpretation

| Check | Independently confirmed result | Interpretation that the evidence supports |
|---|---:|---|
| Raw versus identity-masked title similarity | 253 account pairs; Spearman 0.625801 | Identity words materially change this model's ordering in this corpus. Masking is a sensitivity choice, not a validated removal of all identity signals. |
| All versus repeated-title-excluded comparison | 253 pairs; Spearman 0.992388 | Removing ten repeated masked-title documents changes little in this particular account-pair ordering. It does not eliminate reposts, shared audio, or near duplicates. |
| Full versus outer-10%-trimmed captions | 78 pairs; Spearman 0.969499 | Broad pair ordering is similar under this one perturbation. Four of 13 accounts change nearest neighbor, so local pair choices remain sensitive. |
| Same-video title versus caption centroids | 25 videos; 11 eligible accounts; 55 pairs; Spearman 0.205628 | Title and caption representations give substantially different account-pair rankings in this selected pilot under this model. This is not a universal predictive-accuracy estimate. |
| Within versus between caption vectors | 13 within pairs, median 0.661225; 422 between pairs, median 0.430898 | These observed distributions differ. Pairs reuse documents and are dependent; the box plot supports no independent-sample significance test or population claim. |
| Keyword indicator match prevalence | Same 25 videos; captions match more often for all nine dictionaries | Title-only matching misses vocabulary occurring in captions. Captions provide far more matching opportunities; presence is not emphasis, semantic agreement, or validated subject labeling. |

The fresh metadata layer covers 925 unique indexed videos, 881 durations and 880 exact dates. The analysis groups them into 256 observed/inherited account records, not 256 independently verified people. There are 30 English caption-pilot documents across 17 account groups; 13 groups meet the two-caption threshold for the full caption heatmap. Caption collection, language filtering and account attribution are separate selection steps and must not be conflated with complete coverage.

## Report and figure corrections from this review

1. **Applied and rechecked:** the matched title/caption caption now describes vocabulary presence rather than inferred subjects; its longer-text opportunity caveat is explicit.
2. **Applied and rechecked:** the report's introduction describes upload-length differences, gives observed account means and says no formal format annotation was performed. A duration threshold is an operational proxy, not a classified genre.
3. **Applied and rechecked:** mean/median discussion was narrowed to the influence of longer uploads when the mean is higher. Negative mean-minus-median values are visible in the duration-format plot.
4. **Applied and rechecked:** `meta.textMethod` now lists the executed pinned MiniLM model as well as dictionary indicators and TF-IDF.
5. **Applied and rechecked:** the Scranton discussion explicitly distinguishes its Unicode-token concordance from the main alphabetic-word rate calculation. Its 564/583 (96.7%) and 564/1326 (42.5%) ordered token ratios match the saved supplementary artifact. The separate 606/662-word closing-window split uses another denominator and remains a single illustrative case, without audio verification.
6. **Applied and rechecked:** the account-centroid explanation now correctly states that the hierarchy prevents longer recordings from contributing more chunks directly to an account representation. An account's own mean still reflects which videos were selected.

There is an unused `figure('semantic-similarity')` call in the report generator that renders no output because no figure with that ID exists. It is not a missing numerical analysis: MiniLM title results and diagnostics are exported. Remove the unused call during later cleanup or intentionally add the corresponding plot; the current report should continue to describe nine rendered figures.

## Literature interpretation and implementation boundaries

The executed model is the compact English `all-MiniLM-L6-v2` baseline, with a pinned revision and exported numeric features. The implementation uses attention-masked mean pooling, normalized 240-token chunk vectors, an equal chunk mean for each caption document, then equal-video account centroids. The short final chunk gets the same weight as a full chunk. This is a disclosed modeling choice, not a demonstrated optimal aggregation. Titles and uncorrected automatic captions are different text layers. No diarization or audio verification separates hosts, audience questions, promotion and reported channeling voices.

BERTopic, Qwen3 embeddings, Jina embeddings and multilingual benchmarks are reviewed research candidates. They were not executed in this project, and the report correctly avoids calling MiniLM the current state of the art. The bibliography separates method description, model availability, and actual project execution. The four historical-physics skills contribute workflow, source discipline and inverse-inference critique only; no physical mechanism is inferred from text similarity.

The two 2026 Wahbeh–Glick papers are described as related outputs from the same research program, not independent replications. The inspected public supplement (Figshare 31100860 v1) provides an interview instrument, selected code and summary outputs, but not the participant answer inputs or a complete implementation of the reported residualized within-channeler analysis. Its global concatenation/encoding code also warrants a possible truncation caution; unavailable inputs prevent quantifying it. The project does not claim to reproduce those studies. The 2023 structured-question study used a different design and sample, so its lower cross-channeler correspondence should not be pooled as a directly commensurate effect. Textual resemblance cannot establish an external communicating source.

## Limits and next hypotheses

The usable output is an exploratory map, with source provenance and uncertainty visible. Future manuscript work should test identity masking, duplicate audio, genre/host segments, model sensitivity and language coverage under declared sampling rules. The visible low-similarity row for one account in the caption heatmap is a diagnostic prompt to inspect sampled material and transcription, not evidence that the person or claimed entity is uniquely different. More model comparisons alone cannot resolve collection bias or a lack of validated subject labels.

No new inferential significance test, causal claim, semantic topic validation or global active-medium estimate is endorsed by this review. The manuscript and three further review rounds remain a separate, subsequent phase.
