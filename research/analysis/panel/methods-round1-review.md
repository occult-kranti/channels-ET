# Round 1 — independent methods review

Reviewer: `/root/method_panel`, an actual model agent, not external academic peer review. Reviewed original ZIP CSV/README and the existing discovery schema. No site files changed. Date: 2026-10-23. Round 1 is a design review against observed inputs; rounds 2 and 3 must inspect executed outputs and drive repairs.

## Observed input constraints

The ZIP README explicitly labels its contents draft and independently unverified. The video CSV has 466 rows, 457 distinct nonblank video IDs (plus 9 rows without IDs), 450 nonblank length fields, 3 nonblank exact dates and 453 relative-date strings. Fourteen channel handles have exactly 30 rows and another has 28; this is a capped convenience sample, not a census. The ZIP's `ok` status denotes its producer's claimed inspection and cannot be promoted to current independent verification. The original site contains 873 linked records with per-record provenance; account routes are not necessarily deduplicated human identities.

There are no repeated nonblank video IDs within the ZIP video CSV. The 9 blank-ID rows are unresolved records, not one duplicated video; they must not be merged together. `round1-duplicate-evidence.json` records this correction. Joining on title or person name alone is inadmissible. A video's true publisher is one account even when multiple guests/speakers are attributed; any cross-source publisher conflicts must not be counted twice as two channels' uploads.

## Finite analysis contract

| Observable | Unit / denominator | Valid conclusion | Required limitations |
|---|---|---|---|
| Average duration | Seconds over unique video IDs with parseable positive lengths, grouped by supported publishing account | Mean of sampled uploads with recorded lengths | Show `n measured / n indexed`; missing is null, never zero; not a whole-channel average |
| Duration distribution | Median, Q1–Q3, min/max of the same sample | Describes skew and short/long-form mix | Show points or distribution and small n; do not call videos ≤60 s YouTube Shorts unless source type confirms it |
| Length sensitivity | Per-channel values restricted to a consistent content type where supplied | Tests whether interview/session/clip mixtures change rankings | Editorial content labels may be uncertain; keep all-uploads default clearly labeled |
| Indexed activity | Count of distinct indexed IDs per exact month, plus relative-date bins separately | Describes captured records | Not posting rate, growth, complete chronology or absence of activity |
| Approximate recency | Source-reported labels such as “1 month ago,” as of observed date | Coarse sample recency only | Do not manufacture exact upload dates; boundaries are uncertain |
| Topic prevalence | Unique videos with dictionary hit / eligible unique-title videos per account | Presence of topic words in titles | Multi-label totals may exceed 100%; titles do not establish spoken content |
| Lexical similarity | Cosine of TF–IDF account vectors, equal-video aggregation after preprocessing | Similar vocabulary in observed text | Not semantic agreement, influence, shared source, authenticity or coordinated behavior |
| Semantic similarity | Cosine of named sentence-embedding model applied to eligible texts, with fixed version and aggregation | Model-specific semantic proximity of sampled texts | State model/language/truncation; threshold not calibrated probability; no arbitrary “high similarity” claim |
| Transcript comparison | Matched source-linked transcript documents in their own stratum | Describes those actual transcripts only | ASR/manual status, language, segment selection and completeness visible; no titles silently substituted |
| Corpus coverage | Counts by source, account, language, text type, length/date availability | Defines analysis support | Imported claims and independently inspected data shown separately |

All channel accounts must appear in the searchable table, with unavailable values explicit. Means should require at least one observation but be labeled `single observed video` at n=1; cross-channel comparison plots should visibly state minimum support and excluded account count. Avoid ranking tiny and large samples as equally reliable. No inferential population confidence intervals: bootstrap intervals would only reflect the convenience sample conditional on its selection and may be misleading.

## Identity and dependence controls

1. Deduplicate exact YouTube IDs before statistics. Keep all original assertions; use the strongest supported publisher binding without overwriting conflicts.
2. Keep `publisher_account`, `speaker_person`, `claimed_entity`, `content_format` and `source_family` separate. A Bashar distributor is an account, not another medium.
3. Exact repeated videos and reuploads are correlated. Report exact-ID deduplication; where text hashes match, run a duplicate-text sensitivity pass. Similar titles alone do not prove reupload identity.
4. A channel identity merge needs supplied official links or exact stable IDs, not embedding resemblance. Preserve unresolved handle/channel-ID equivalences separately.
5. Identical metadata imported from the same repo or notes is one source family. Multiple agents reading it add no evidence independence.
6. Date conflicts and duration conflicts require conflict fields; do not average discrepant metadata without review.

## Topic and embedding gates

Use a transparent keyword baseline before a complex model. Publish the topic dictionary and overlap rules. Exclude source descriptions, analyst notes and identity labels from the actual title corpus; they would create analysis-generated topical similarity. Preserve multilingual texts and either analyze languages separately or name a multilingual model. Language detection on short titles is uncertain.

If sentence embeddings cannot actually execute, ship the executed TF–IDF and optionally SVD vectors with their accurate names, plus a reproducible optional embedding script and a documented missing-model/network status. Never label TF–IDF/SVD vectors as pretrained sentence embeddings. Do not present a proposed model or repository as an executed analysis.

For centroid similarities, use equal document weighting per account, normalize explicitly, exclude empty vectors and publish n. Present a table/heatmap for a declared sufficiently supported subset, not a dense hairball of 157 account routes. Two-dimensional projections are illustrative; axes generally have no substantive topic meaning and distance distortions must be stated. Prefer the original pairwise heatmap and top representative terms over an unsupported semantic map.

For topic models, inspect representative documents and topic stability under preprocessing and duplicate removal. A generated topic label is an analyst interpretation. Rare names often dominate sparse titles; compute a name/entity-term-masked sensitivity pass alongside the unmasked baseline. Do not silently remove the very content the user requested: display both and explain the change.

## Hypotheses with discriminators

H1: Account duration differences are mainly format-mix differences. Compare median/mean and proportion ≤60 s / 1–10 min / >10 min, plus source-labeled content types. Falsifier: large differences persist within adequately supported comparable formats. Current samples cannot establish population differences.

H2: Similarity is driven by shared entity names, generic promotional language and repost duplication. Compare base vectors against entity/name masking and exact-text deduplication. A substantial drop supports sensitivity to vocabulary, not a causal copying claim. Persistence only supports robustness to these specific controls.

H3: Frequently indexed entities reflect collection strategy and channel selection. Compare title-topic counts with per-account normalized prevalence and coverage. A dominant entity in pooled counts that weakens under equal-account weighting supports sampling influence.

H4: Title topic distribution differs from transcript topic distribution. Test only on paired title/transcript videos with actual text. If too few pairs, report untested; do not substitute cross-channel title comparisons.

H5: Apparent frequent posting reflects a recent-30 sample and different recency windows. Inspect observed date coverage and sample cap. Without complete dated upload windows, keep this untested as a true posting-rate hypothesis.

## Figure contract and caption templates

Every plotted figure must state the unit, source layer, denominator, exclusions, cutoff and interpretation limit. Use an accessible accompanying data table and downloadable underlying CSV. Legends must distinguish missing from zero.

- Duration: “Mean and median length of [n] unique sampled uploads with recorded duration across [k] accounts, as supplied/verified on [date]. Bars show minutes; labels show measured/indexed count. This capped discovery sample is not a complete channel catalog.”
- Activity: “Counts of indexed videos with exact publication dates by month. [n]/[N] videos have eligible dates; relative dates are shown separately. These counts measure coverage, not upload frequency.”
- Topic chart: “Share of sampled titles matching each transparent keyword category. Denominator: unique eligible titles per account; videos can match multiple categories. Matches describe title vocabulary, not a transcript or verified message.”
- Similarity: “Cosine similarity between [model/method] account centroids from [text layer], with ≥[n] texts per account. Values describe this sample and preprocessing; they are not probabilities or evidence of common origin.”
- Coverage: “Available fields in the merged index, split by supplied metadata and independently retrieved observations. Missing records were excluded from dependent calculations.”
- Transcript pilot: “Analysis of [n] acquired transcript documents ([language], [full/partial/ASR/source]) from [k] accounts. These are the accessible subset; no inference to other accounts is made.”

## Round 2 acceptance criteria

Executed outputs must reconcile to unique video IDs; CSV means/medians must independently recompute; source attribution conflicts must be visible or excluded from channel totals; only measured fields used; captions must match actual filtering; vector method/version and parameters must be exported. Round 2 critic then selects concrete repairs and at least one hypothesis sensitivity test. Round 3 must review repaired outputs, rerun invariants and record unresolved gaps, rather than relabeling parallel work as three rounds.
