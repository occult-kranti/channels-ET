# Expansion analytics panel — round 1

Reviewed baseline: `dist/analysis/data.json`, SHA-256 `f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc`, README handoff at GitHub `1d6eb36`.

The old release provides 925 convenience-sample upload records, 30 selected English caption derivatives and a 706-title embedding archive. Raw caption text is unavailable in this checkout. New analysis can quantify selection, missingness, publisher concentration, title keyword/duration associations and matched derivative sensitivity; it cannot establish answer agreement or medium-level differences.

Accepted implementation: preserve the baseline and add a separate protocol/results layer; retain exact upload/account denominators; compute matched title/caption cosine pairs on identical IDs; use a publisher-label permutation only as a descriptive negative control, with dependent pair scores never treated as independent experimental observations. Plot duration distributions and count coverage, make missingness visible, and retain all chart-ready rows.

Rejected: population confidence intervals over convenience-sample videos; entity-label causal comparisons without identity and speaker validation; treating repeated titles as proven reposts; naming keyword detections validated topics.

Acceptance: executable analysis plus source hashes, finite JSON values, CSV figures inputs, publication-ready figure exports and numeric reconciliation tests. Later rounds must review changed outputs, not reissue this opinion.
