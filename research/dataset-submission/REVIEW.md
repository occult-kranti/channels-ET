# Independent review of the dataset submission package

This is an AI-agent evidence review, not human peer review, annotation validation,
ethics approval, or an ICWSM acceptance decision. Review scope follows the actual
inputs and artifacts available on 8 November 2026. Work in progress is not counted
as an executed review round. The user authorized a private full archive and public
research; that authorization does not establish third-party redistribution rights.

**Decision: share the public working research release with the stated caveats.**
The reviewed corpus, numerical results, paper and local dashboard pass the checks
below. The full private archive has **not** been uploaded, and the package is
**not** ready for conference submission. These are distinct unfinished outcomes.

## Milestone record

| Milestone | Status | Executed evidence and current decision |
| --- | --- | --- |
| 1. Scope, permissions, venue and data units | passed | Current requirements and finite working-release scope verified: **15 January 2027 AoE**, explicit units and public/private boundary. DOI, human authorship, checklist sign-off and asset-specific rights remain submission requirements. |
| 2. Source frame, deduplication, coverage and archive | passed locally; remote archive blocked | Verified 683 selected documents / 1,599,556 words, all 694 edition bodies, joins, JSONL and SQLite. Rehashed 533 joined media files / 11,657,753,739 bytes. Retained-root inventory accounting, one base shard and the corpus/analysis supplement passed independent checks. Remaining base shards and remote transfer are unfinished. |
| 3. Analysis, paper claims and limitations | passed within exploratory scope | Independent lexical refit and result checks passed. Refined numerical witnesses, repaired plots and final ten-page working paper were checked. Length and factor-stability limitations remain explicit; human semantic/ASR validity is unmeasured. |
| 4. Public dashboard, artifacts and readiness | passed locally | Representative independent browser, export, modal-focus and failure-state checks passed. All 75 public artifact hashes and scoped structured-export privacy checks passed. Live deployment verification remains integration's separate check. |

## Executed source check

The independent checker reads actual source files and applies the declared body
transform: Unicode NFKC and outer whitespace stripping, with the recorded JSON
and HTML cleanup where applicable. It verifies file/body hashes and recomputes
word counts. It does not call the producer's loader. The candidate pool comprises
685 selected-old-plus-new bodies; this is not the edition-lineage denominator.

| Quantity | Independently verified result |
| --- | ---: |
| Prior selected documents | 493 |
| Prior selected words | 1,411,446 |
| New publisher-written editions | 192 |
| New written-edition words | 189,717 |
| Duplicate publication pairs across those cohorts | 2 |
| Selected documents after preserving old editions | 683 |
| Selected words after the same rule | 1,599,556 |

The duplicate pairs are the OmNa publications “Celestial Andromedan Innovations”
and “As You Focus So You Become.” Exact normalized-body hashes differ because
internal whitespace is preserved. A second comparison that collapses whitespace
identifies the two matching pairs; no additional pair appears in that check.
Neither this check nor page co-occurrence establishes audio/text alignment or
equivalence with a linked YouTube recording.

Private reproducibility receipts are retained under
`dataset-submission-2026-11/review/`: `check_sources.py` and
`source-check.json`. The old-frame SHA-256 is
`0d69378f9e9a2280e7ed05981b647fbfe280016380b3072b2b3a320961ae2c8c`.

The frozen enlarged frame SHA-256 is
`3eb35b14a9067e9e162862ed030c15d5b7646a38b3060ac85686f4604eb2c9c4`.
`check_frame.py` and `frame-check.json` independently verify its 26 publisher
contexts, 14 creator contexts, 300 missing publication dates, one selected edition
per source, all selected-body hashes, and the linked media bytes. The new audio
subset is 192 files / 942,245,703 bytes / 160,392.925125 decoded seconds: three
original MP3 files and 189 lossy Opus derivatives. These are publisher audio,
not direct YouTube downloads.

The later `edition-body-check.json` also checks each of the 694 retained edition
bodies against its underlying artifact, declared transform and public lineage
row. There are 11 alternatives, 691 distinct exact body hashes and 1,616,070 words
across all editions. Those edition words are nonindependent and must not replace
the selected-corpus denominator.

## Executed analysis review

The reviewer independently rebuilt full-text and centered-300-word TF–IDF from
the checked source bodies, including the declared tokenizer, stop words and exact
identity-phrase masks. No producer analysis helper was imported. Vocabulary and
IDF agreed on 24,000 features; the largest cosine-matrix discrepancy was
8.44 × 10⁻¹⁵ (floating-point rounding).

The checker also reproduced all 676 publisher-context similarity cells and pair
counts, 888 mutual-five-neighbor edges, 9,024 punctuation question cues, selected
NMF mixture/seed-alignment calculations, and the illustrative eight-cluster
silhouette (0.253764). The cue count is not a validated question/answer bank.
The checker did not independently refit the neural encoder or every NMF/KMeans
model; it checked retained numerical witnesses for the stated model aggregates.

Restricting the input to a centered 300-word span gives mean top-five-neighbor
Jaccard 0.137349 across sources and 0.062477 when equally averaging publisher
contexts. Pairwise rank correlation is 0.536109. This substantial representation
sensitivity is a substantive limitation, not a minor implementation detail. It
precludes treating the displayed cluster membership as a stable doctrine or
claimed-entity taxonomy. Alphabetic tokenization and conversational register can
also influence terms such as `d`, `yeah` and `kind`.

Private evidence: `check_analysis.py`, `analysis-check.json`, and
`numerical-array-bindings-pre-refinement.json`. The initial reviewed analysis
SHA-256 is `978abeaf67cb0b4213a99ee5ae5d244bcbb9a78358aed0283983b5aceb19cd09`.
The final refined analysis is
`083ae06c83eeec0974eb0280eb25d6949fccb25ccfdd8d08c44f27494aa7b308`.
`analysis-refinement-check.json` confirms that only the seed-47 component and
weight arrays changed; the other 27 arrays remain byte-identical. Seed 47
converged at 1,126 iterations. Its mean matched-component cosine is 0.794588,
but two matches are only 0.187529 and 0.343372. The paper states this heterogeneous
stability explicitly.

## Findings sent to artifact owners

| Finding | Owner | Status |
| --- | --- | --- |
| Sensitivity table expanded 683 source rows per diagnostic and omitted the actual `analysis` label | Dashboard | Fixed; compact named table independently tested |
| Loader checked an absent `dataset_sha256` field rather than matching actual analysis/dataset frame hashes | Dashboard | Fixed; hash-valid wrong-frame injection withheld |
| Corpus figure legend overlapped the largest bars; origin boxplot labels overlapped | Analysis | Fixed; revised plot visually checked |
| Sensitivity figure's long axis label reached the image boundary | Analysis | Fixed; wrapped label visually checked |
| Generic context-balancing prose obscured the difference between balanced IDF and subset-fitted NMF | Manuscript | Fixed; separate fits and 107-source subset described |
| Compute checklist referred broadly to resources not yet specified beyond runtime/RSS/packages | Manuscript | Fixed; CPU/quota/no-GPU witness and cached/original inference timings documented |
| Release verifier used obsolete archive fields and allowed absent analysis-frame binding | Integration | Corrected to actual contracts; integration tests reported by owner |
| Corpus/analysis archive supplement excludes final venue/review/probe/release receipts | Archive | Separate closing-provenance supplement remains necessary; no complete-backup claim |

Final PDF SHA-256:
`2f17888a5679891e49da4b90dd6fa8776337db67939c790d10f699e1a99753a4`.
It has ten US Letter pages: eight body/reference pages followed by two checklist
pages. All 35 official-linked question wordings were checked; final text and
rendered pages 1, 5 and 9 were inspected. Numerical claims match the reviewed
results and the placeholder paragraph is gone. Clean compilation from the ZIP
was tested by the producer, not repeated by this review lane. Private receipt:
`paper-check.json`.

## Venue check and release constraints

The current primary source is <https://www.icwsm.org/2027/submit/>; retained HTML
SHA-256 is `b19d00c07a9fcfeca5e3eb9d900e7c168ef9677134678a7400777249ce02d29e`.
The dataset track requires 2–10 pages excluding the paper checklist, AAAI
two-column US Letter formatting, single-blind review, a DOI indexing the actual
dataset, dataset links and documentation of content, structure, collection,
quality, potential applications and FAIR principles. The checklist must be
unaltered and appear immediately after references, before appendices. AI use
requires disclosure; AI cannot be an author. Only the checklist and its
supplemental discussion are explicitly excluded from the page limit in the
current call.

No sentence in the inspected dataset section requires every raw audio file to be
public. A public metadata release must nevertheless be a real, clearly bounded
dataset with usable access, rather than a private archive described as open.
Private backup is not DOI deposition or evidence of raw-content redistribution
permission. Final claims about licensing, ethical review and human validation
must follow their actual status.

## Archive and public-interface checks

The retained-root inventory contains 39,327 logical paths, 36,413 unique content
objects and 17,806,101,487 unique bytes, with 21 planned base shards. Independent
accounting found no unlisted regular files after explicit exclusions and matched
all 1,416 declared text/media/source closure paths to inventory hashes and sizes.
Logical bytes include duplicate copies and are not unique-media storage. This
accounting did not rehash every archived object; selected media were independently
rehashed separately.

The review independently checked compressed-file hashes and decompressed object
hashes for the 751,649,698-byte base pilot and 54,548,852-byte corpus/analysis
supplement. Only one of 21 base shards has been built and checked locally; the
supplement contains 52 objects. The active study was excluded from the base
inventory, so final venue/review/probe/release receipts need a closing-provenance
supplement. **Zero remote assets are verified.** Repository access remains
unavailable; local artifacts are not called uploaded.

Independent browser checks covered all six desktop views, a mobile overview,
the compact sensitivity table, publisher modal/focus behavior, a filtered export,
and two injected failures. Corrupt required data fails closed. An analysis with
a recomputed valid payload hash but the wrong input-frame hash is withheld.
Targeted checks verified that Ra's 106 selected sessions and 2,620 upstream audio
segments remain distinct, zero remote upload totals are visible, and the actual
paper PDF opens. The dashboard owner's broader 29-group suite also passed the
final UI; it is a producer check, not additional independent review tests.

Private receipts: `archive-inventory-check.json`, `local-shard-check.json`,
`ui-check.json`, `ui-coverage-check.json`, and `public-release-check.json`.
The 75-file public check binds manifest
`71fa8b4868887e6e94882290d97f869a22dee41d38f12d10430b0abc4ec23868`.
It covers all artifact hashes and private-path checks on structured exports and
structured ZIP members. No raw media, private databases or numerical witness
archives appear in the public artifact list. This review's final documentation
update requires integration to rebuild the manifest before publication; frozen
corpus and numerical bindings remain unchanged.

## Remaining work and limits

- YouTube lifetime upload totals remain unknown; direct media retrieval is
  blocked before origin. Observed IDs are not acquired recordings.
- Complete private backup requires repository access, remaining base shards,
  final provenance closure and verified remote bytes.
- DOI deposition, human authorship, asset-specific rights decisions and
  responsible institutional determination remain unfinished submission items.
- Human transcription/annotation quality, topic validity and external
  generalization remain unmeasured.
- Integration owns live deployment checks after the final manifest rebuild;
  this review records local artifacts rather than an unobserved deployment.
