# Channel and recording laboratory: execution protocol

This is an additive exploratory release. It preserves the earlier Bashar–Ra,
publisher-audio, Council and knowledge-bank editions. The intended product is a
static, inspectable dashboard with channel/context pages, individual document or
recording pages, selected-source comparisons and review diagnostics. It is not a
YouTube census or an authentication test for attributed entities.

## Units and source frame

The source owner reconciles the currently retained accepted corpora before any
new model is fit. A publication, an underlying recording, a text edition, a human
medium, a publishing account and a claimed speaker are different objects. Exact
body hashes, known audio families and canonical publication URLs support bounded
deduplication; they do not establish independence of ideas or unknown origins.
Alternate editions remain traceable. Missing historical caption bodies are
metadata-only records and cannot enter a new text fit.

The final source manifest, rather than a planning estimate, defines the sample.
Every admitted text must pass its original artifact hash and have a reproducible
normalization/selection rule. Public data contain source metadata, numerical
features and bounded interpretations; full bodies and local file paths remain
private. Channel upload totals stay null when no complete census is verified.

## Batch recognition extension

The pre-execution rule selects all five retained OmNa audio publications, plus
the shortest retained, eligible recording without an accepted full Parakeet
upgrade from each of the official Bashar, Tracy Kumbera, Multidimensional Soul
and Athina contexts. The selected frame is capped at nine recordings and four
audio hours. Bashar retains an actual decoded 300-second minimum. Other contexts
have no duration minimum. Selection is not tuned using later recognition outputs.

The selected source hashes and actual durations are frozen before inference.
The existing four Council upgrades are reused as prior editions, not rerun or
counted as new recordings. New recognition does not silently replace evidence
in the canonical analysis or existing answer cards.

The pinned Parakeet model runs on two one-thread CPU workers, with a bounded
queue, immutable outputs, complete sample-window coverage, model/input/output
hashes and an explicit resume policy. The producer records completed, failed,
held and cached outcomes separately. A resumed successful item must be verified
before it is skipped. Resource guards enforce a 2 GiB free-disk floor. Temporary
PCM, models and numerical witnesses use RAM-backed storage; no prior source,
model, failed attempt or accepted analysis is deleted to make room.

Runtime, actual worker overlap, input coverage and machine-output disagreement
are operational measurements. They do not demonstrate word accuracy, verified
speaker identity or a causal speedup from parallelism. Independent short windows
can lose context. A comparison with older ASR editions changes the recognition
pipeline, not solely the learned weights.

## Computational analysis

Fit a common lexical representation over the frozen body frame; use pinned
pretrained embeddings with full-input coverage and explicit pooling. Document
length, origin, dates and missingness are analysis variables. Per-document key
terms, topic mixtures and source-position profiles support navigation. A text
position is not an audio timestamp unless exact source-time boundaries support
the correspondence.

Cross-source views expose actual pair counts and the source/creator composition
behind each group mean. Document pairs share observations, so pair counts are
not independent sample sizes. Source balancing is a descriptive sensitivity,
not a correction for an inaccessible or purposive sampling frame. Seed,
length, name-mask, origin, cluster and network-threshold checks are selected to
address these concrete failure modes. Two-dimensional geometry is displayed
with distortion/variance qualifications and never substituted for the original
similarity metric. Clusters and lexical cues are not verified doctrines,
emotion labels, causal mechanisms or tests of common entity identity.

## Bounded source readings and critical review

The reading agent records the passages actually inspected, their edition hashes,
locations and source qualifications. Reused annotations retain their original
evidence; new paraphrases distinguish observation, interpretation and hypothesis.
Similarity may propose a comparison but cannot assign agreement or contradiction.

The critical reviewer challenges source selection, duplicate/edition handling,
speaker attribution, imbalance, measurement validity, projection and threshold
choices, incomplete annotation, external validity and novelty. Three milestones
are planned: protocol/design critique; executed-output/source audit; correction
and release verification. The panel log records actual exchanges and outcomes.
These AI roles do not constitute human peer review, conference acceptance,
human transcription validation or institutional ethics approval.

## Publication and verification

Publish only explicit reviewed output allowlists with byte/hash bindings. Check
source/model joins and numerical accounting, inspect real plots, exercise actual
desktop/mobile and deep-link flows, and test empty/error/failure states. Stage the
complete existing static site without rebuilding unavailable historical inputs.
Commit and deploy through the existing Pages action, then verify the live commit,
download bytes and rendered controls. Report executed results and unresolved
limits separately; a proposed analysis or a queued job is not completion.
