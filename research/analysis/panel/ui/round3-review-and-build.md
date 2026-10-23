# Round 3: implemented neural/caption analysis and visual review

Reviewed changed artifact: round2 pipeline data, including newly retrieved watch metadata, executed all-MiniLM-L6-v2 embeddings, and a separate English caption pilot. This is an actual changed implementation, not a third report on the original UI.

## Implemented after round2 review
- Added learned-title centroid cosine alongside lexical cosine, preserving method-specific values and model-eligible n for each pair.
- Added per-account nearest learned embeddings and caption topic rates; caption source layer remains separate from title proportions.
- Added global/per-account caption acquisition counts, included-document table, caption type/language/word-count/selection metadata, and derived-data downloads.
- Caption denominator corrected from an initial UI draft: per1,000 alphabetic words per video, then equal-video average. It is not a pooled word-count statistic.
- Added selected-accountCSV export using existing formula-safe CSV machinery, retaining all15 audit fields.
- Added report and bundled-analysis download entry points at the top of the route and in Methods.
- Explicit English-likely title eligibility and sample thresholds now accompany comparative wording.

## Actual visual artifact review
UIworker viewed generated duration.png and title-topics.png. Duration mean/median/IQR legend and minute axis were readable; topic heatmap had fixed0–1 legend and visible denominator n. Two defects sent to pipeline: Japanese label rendered as missing-glyph boxes, and hard-truncated account labels could lose discriminating suffixes. Pipeline owns corrective rendering.

## Executed verification
- `node --check dist/app.js` passed.
- Actual-data renderer harness passed all4views,25rowpagination,page2range,exactdatebinding,missingcoverage, noNaN/noobject-string rendering.
- Selected-account CSV generated in harness with duration,date,eligibility,source/provenance fields; rowcount exceeded10 as expected.

## Pending final gate
All9figurefiles and underlying CSVs were verified on the final round3 data. All four renderer views, pagination, exact-date binding, missing coverage and selected-account CSV checks passed. Final duration PNG uses readable account handles/current names; final within/between caption PNG now includes the observed negative cosine minimum (−0.03235) instead of clipping it. Monthly indexed counts CSV also exists and is linked. Root browser review, report/ZIP generation, push and publication remain separately owned gates. No mobile/screen-reader test by UIworker. External academic peer review not claimed.
