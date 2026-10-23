# First-build independent review

Reviewer: `/root/method_panel`. Input: `dist/analysis/data.json`, version `round1`, SHA256 `12519511fc622c87e0049d5737ad2016cf1f17d78956cb4f4cb8aa3c8522762a`.

Executed the independent verifier frozen before reading producer code. All 2,211 checks passed: unique IDs, publisher reference resolution, positive durations, exact-date format, means, medians, linear quartiles, eligible title counts and duration coverage recomputed from 925 video rows across 189 account-route groups. Separately recomputed all 1,701 channel×topic counts and shares (3,402 checks), all passed. The 19×19 lexical cosine matrix is symmetric, has unit diagonal, valid range and 171 unique pair records.

These tests validate arithmetic against the assembled data, not external truth or representativeness. Raw ZIP baseline has 450 duration strings; assembled model retains 449 eligible durations. Source/identity discrepancy audit is assigned independently to `/root/zip_audit`.

## Required repairs for next build

1. **Publication-date display binding:** the per-channel contributing-record table reads `publishedAt` / `publishedDate`, while analysis schema uses `date`. Valid dates therefore appear unresolved in the UI. Correct to source schema and show `dateSource`.
2. **Evidence-layer display:** the same table defaults to generic supplied/indexed metadata and omits actual `durationSource`, `dateSource` and `titleSource`. Surface these fields or a concise per-field provenance detail.
3. **Language denominator:** the first model mixes all title languages under an English dictionary. Implement the already planned language eligibility rule consistently in topic shares, lexical vectors and English MiniLM; retain excluded title counts and uncertain language status.
4. **Model execution distinction:** this first build has TF–IDF only, accurately labeled. Learned embeddings and transcript comparisons must remain absent until actual outputs and model/run provenance exist.
5. **Figure inspection:** static SVG captions are broadly accurate about sampled counts, quartiles and lexical similarity. Export PNGs for visual review and state source snapshot/cutoff plus download location for underlying tables. Do not mark visual review complete from code inspection.

## Accepted narrow results

Duration summaries and title-keyword indicators are reproducibly computed for the current assembled sample. No evidence yet supports whole-channel means, channel posting rates, transcript-level topic proportions or ontological claims. The first repair set follows observed defects; the next round should add language/fresh-metadata/model evidence, then be reviewed on its actual outputs.
