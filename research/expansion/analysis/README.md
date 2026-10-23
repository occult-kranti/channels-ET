# Expansion diagnostics

This layer adds exploratory calculations to the preserved 23 October 2026 evidence snapshot. It does not rerun video collection, recover raw captions, train a model or certify reported entities. `protocol.json` was written after schema inspection and review of previously published summaries, before these new calculations; it is not a preregistration.

From the repository root:

```sh
OPENBLAS_NUM_THREADS=2 /workspace/bashar-index-venv/bin/python channeling-atlas/research/expansion/analysis/analyze.py
MPLCONFIGDIR=/workspace/setup-validation/matplotlib XDG_CACHE_HOME=/workspace/setup-validation/cache /workspace/bashar-index-venv/bin/python channeling-atlas/research/expansion/analysis/figures.py
/workspace/bashar-index-venv/bin/python channeling-atlas/research/expansion/analysis/verify.py
/workspace/bashar-index-venv/bin/python channeling-atlas/research/expansion/analysis/verify_qa_crosslayer.py
/workspace/bashar-index-venv/bin/python channeling-atlas/research/expansion/analysis/verify_final_consistency.py
```

The Python dependencies are the original pinned analysis requirements. The scripts resolve their own project root. `analyze.py --output /absolute/directory` supports an isolated numerical reproduction; figure and verification scripts use the canonical local output. Input hashes are checked against the reviewed snapshot so a new collection cannot silently inherit old findings.

## Measurements and limitations

- Coverage uses one 925-upload denominator. The 30 English-caption documents are a selected analytical subset, not a caption-availability estimate. Positive duration means `durationSeconds > 0`; exact-date eligibility and heuristic English-title eligibility remain separate.
- Concentration uses 886 attributed uploads and 180 publishing-account groups with uploads. The 39 unresolved associations and 76 empty account routes do not enter Gini, HHI or cumulative account shares. Accounts are neither unique practitioners nor claimed entities.
- Caption selection compares empirical duration medians and IQRs for 30 pilot uploads, 430 other uploads in pilot publishing accounts and 851 other indexed uploads. The comparator sets overlap. These are sample descriptions, with no random-sampling or causal interpretation.
- Keyword extraction uses the nine frozen transparent regular expressions, one indicator per eligible title, among 702 English-likely titles with positive measured duration. Categories overlap. Five duration bands are length bins, not manual format labels. Within-account long/short contrasts require at least three eligible titles on each side of 30 minutes; their median and IQR describe heterogeneity, not confidence intervals.
- Duplicate-title families use explicit NFKD accent removal, casefold and word-token normalization; a variant additionally removes the frozen name-and-genre mask words. This normalization differs from the original embedding pipeline's key and is reported separately. Same title text does not identify a repeated original session.
- Frozen MiniLM title and caption vectors overlap on 25 uploads from 14 publishers. Eleven publishers have at least two matched uploads; three singletons contribute to between-publisher comparisons only. All pair scores share uploads and are dependent. The pooled mean within-minus-between cosine is complemented by an account-balanced contrast and a leave-one-publisher-out influence range. Account balancing first averages cross-pair scores for each other account, then averages other accounts equally, and finally averages eligible focal accounts equally.
- A fixed-seed 2,000-draw publisher-label shuffle preserves group sizes on the fixed vectors. It is a descriptive negative control with hypothetical label exchangeability, not a population p-value, semantic-validity test, or independent-pair experiment. Observed reference percentile `1.0` means all recorded shuffled statistics were lower; it is not proof of significance or answer agreement.
- Cross-layer cosine separations are representation-specific. Their difference is a descriptive sensitivity on the same IDs, not a calibrated semantic effect. Masked title separation is larger here, but neither layer identifies who spoke or whether two answers agree.

## Executed results

The caption-pilot median is 8.61 minutes, compared with 19.37 minutes among other indexed uploads and 12.04 minutes among other uploads in the pilot accounts. This contradicts the exploratory prediction of a longer pilot. Top-ten accounts contribute 38.04% of attributed uploads, below the exploratory 50% threshold; top twenty contribute 66.93%. Gini is 0.6713 and the HHI-equivalent count is 40.30 equally represented accounts.

Matched caption within-minus-between mean cosine is 0.1541; the masked title counterpart is 0.2291. Account-balanced values are 0.1533 and 0.2286. Deterministic publisher omissions leave caption differences from 0.1214 to 0.1793; these endpoints are not confidence bounds. Only two of nine pooled keyword contrast directions match the corresponding within-account median directions. Most within-account medians are zero; this cautions against attributing pooled length associations to content format.

`generated/verification.json` records the independent source/count/numerical reconciliation. It does not import the producer or validate the substantive topic constructs. The six figures have inspected PNGs plus PDF/SVG exports and caption manifests. Exact chart inputs and a paired-vector table are retained as CSV/JSON. The Q&A database is a separate workstream; these diagnostics make no cross-practitioner answer-agreement claim.

The later cross-workstream audit checks all released Q&A digest pointers, recalculates question TF–IDF pairs without importing that producer, verifies retrieval thresholds and upload-pair denominators, and preserves CSV false/null distinctions. The final consistency audit requires a built expansion paper; it compares every recorded manuscript input and copied figure hash, then checks the rendered sensitivity table and key denominator/uncertainty statements. These checks do not establish the accuracy of the original digests or human question equivalence.

To regenerate only a corrected figure, use `figures.py --only negative-control` (or another figure ID). This retains the complete caption manifest without rewriting unrelated figure exports.
