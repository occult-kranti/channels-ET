# Round 3 — final independent methods review

**Verdict: pass for publication as a bounded exploratory index and analysis, with the limitations below retained.** Reviewer: `/root/method_panel`; this is model-agent review, not human academic peer review.

Final data SHA256: `8615040031871018dd25607f659d2294a3624a41074f11ab0bbcfad31f520920`. Report SHA256: `c439ef2b91b9b45523b960a41d4888f9424783bdbc87814e58d1c0fd437a770f`. The report includes the same data hash and the corrected focal Ryok/The Galactic Guide account.

## Executed final checks

| Check family | Checks | Outcome |
|---|---:|---|
| Duration, dates, denominators, identity references | 4,068 | Pass |
| Actual 384D vectors, eligibility, equal-video centroids and cosine matrices | 785 | Pass |
| Raw caption artifact hashes, normalized text hashes, token counts and topic rates | 630 | Pass |
| Sensitivity metrics, matched samples and within/between pair values | 43 | Pass |
| Report data hash and focal account selection | 2 | Pass |

The assembled sample contains 925 unique video IDs and 256 account-route groups; 180 groups have indexed videos and 178 have at least one duration. Available durations total 881 (877 freshly retrieved, four inherited). The exact-date count is 880. These are index units, not a count of human mediums or a channel census.

The title model embeds 706 attributable eligible titles; 23 groups meet the five-title comparison threshold. Thirty English caption documents enter the pilot, from 34 available out of 36 attempted. Three non-English documents and one extra concordance document are excluded from the main pilot. Thirteen groups meet its two-caption threshold. The 384-dimensional learned vectors are actual executed MiniLM outputs, not TF–IDF renamed as semantic embeddings.

## Independently confirmed comparisons

- Raw versus identity-masked neural title pair rankings: 253 shared pairs, Spearman 0.625801. This demonstrates sensitivity to identity terms within the chosen method; it is not a copying or shared-origin test.
- Removing repeated masked-title strings: 253 pairs, Spearman 0.992388. This narrow duplicate-string control leaves most pair ordering intact; it does not eliminate all reuploads or common-source dependence.
- Full versus outer-10%-trimmed captions: 78 pairs, Spearman 0.969499. Four of 13 nearest-neighbor labels change. Broad rank stability therefore does not imply every neighbor relationship is stable.
- Matched titles versus captions: exactly 25 shared video IDs, 11 qualifying account centroids and 55 account pairs; Spearman 0.205628. The weak correspondence is a selected-pilot text-layer result. It does not establish that either representation measures semantic agreement accurately.
- Caption document comparisons: 13 same-publisher pairs and 422 different-publisher pairs reproduce from the saved vectors. Pairs share documents and must not be treated as independent observations for significance testing.

## Figure and repair review

Inspected PNG renderings of the four initial figures and all five added figures. The Japanese account label now uses its known handle instead of missing glyph boxes; shortened names show ellipses and full identities remain in exported data. New caption charts show small sample sizes, units and model-specific cosine scales. The within/between chart includes negative values rather than clipping the axis at zero. Captions identify the convenience sample, multi-label keyword overlap, uncorrected ASR, dependent pairs, equal-video weighting and the mathematical coupling in the duration-format scatter.

The first-build UI publication-date binding and provenance omissions were repaired by the interface agent. The second-build hash ambiguity is resolved: `captionArtifactSha256` matches the raw caption JSON, while `textSha256` matches the exact analysis text. The denominator now explicitly preserves contractions with `[A-Za-z]+(?:'[A-Za-z]+)?`; independent per-1,000-token rates reproduce. The report's original focal-route selection omission was corrected.

## Limits retained

No human/audio transcript-accuracy audit, speaker diarization, blinded topic-code validation, random sampling or population inference was performed. English-likely title language describes the available text and can include platform translations. Automatic captions mix hosts, questions, promotion and attributed channeling voices. Equal chunk weighting gives a short terminal chunk the same weight as a full chunk. Source truth and model validity are not established by arithmetic consistency. Metadata availability does not guarantee playback availability. None of these computations authenticate extraterrestrial sources, healing, predictions, agreement of substantive claims or causal influence.

The three rounds are anchored to distinct input snapshots and observed repairs. No further dashboard-analysis work is required by this reviewer before the coordinator's publication checks. Any additional manuscript rounds are a separate subsequent phase.
