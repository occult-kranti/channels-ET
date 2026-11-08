# Independent review of the knowledge-bank extension

This review uses an independent AI-agent role. It is not human annotation,
external peer review, transcription ground truth or authentication of the
claimed speakers. It reviews source bindings, interpretations, numerical
reproducibility and the limits of the executed experiments separately.

## Retrieval query freeze

Before inspecting the proposed knowledge cards or any retrieval rankings, the
reviewer read four complete publisher-written source editions, totaling **5,244
words**, from four different medium contexts. Four information needs and their
known supporting sources were then frozen. Eight exact evidence spans bind
normalized-body offsets, source/body hashes, word counts and span hashes. One
information need explicitly requires preserving negative qualifications.

The private query file is `review/retrieval-queries-01.json`, SHA-256
`84634a835af5e0e074caa258c0e98bb0426691dc4dee37c5c70549692f9b4263`.
Its frame is the fixed **25-edition / 47,280-word** knowledge corpus, SHA-256
`95131882eaed23b9429d3beb6cdffcda3fa62b32569d36412cd013c206008aae`.
Query text and relevance targets were not supplied to the card-authoring role
before its freeze. No retrieval rankings were inspected before query freezing.

These are source-informed, prospectively fixed retrieval checks. The reviewer
knew the inspected source answers, so the labels are neither source-blind nor
human ground truth. Unlisted sources remain **unjudged**, not automatically
irrelevant. Success at retrieving known support does not establish answer
correctness, completeness, agreement between sources or external validity.
The fixed queries must not be used to tune representations or retrieval rules.

## Knowledge-card and question-bank review

The final candidate passed after five targeted corrections. The reviewer read
all 25 card paraphrases and all 11 comparison assessments, checked all **43
evidence spans**, and matched all 15 ASR-based supports to their complete printed
segment texts and declared time bounds. This does not verify acoustic alignment.
The five documentary questions were independently matched against the retained
original publisher PDF; their responses match the corresponding source-text
spans. Public questions remain labeled paraphrases of the printed questions.

The independent reading covers **10,083 unique body words across 15 sources**,
including four complete bodies and bounded passages from the others. This is a
different reading frame from the card author's declared coverage. It is not a
claim to have read every body in the 25-source corpus or listened to the audio.

Review required these corrections:

1. Bind the Lyssa card's skills recommendation to the actual skills paragraph.
2. Preserve the Universe/Creator as the referent of distrust in the Glasson
   Mother Mary passage, rather than treating it as every kind of interpersonal
   distrust.
3. Preserve the Contact recording's “this year” claim alongside uncertainty
   about the later public stage.
4. Preserve the Pamela interview's specific election expectations alongside its
   changing-timeline qualifications; a generic summary would hide testable content.
5. Extend one Pamela support to its complete ASR turn instead of ending at a
   mid-word character boundary. The builder now rejects partial-turn supports.

All 11 relations are defensible at their declared scope. The Mother Mary pair
describes potential practical tension only if one text is extended to a case it
does not assess. It is not a direct contradiction under shared conditions. The
zero explicit-contradiction count is appropriate; disagreement must not be
manufactured to fill a chart. Optional spiritual intermediaries and voluntary
practices likewise do not contradict claims rejecting compulsory intermediaries
or universal formulas.

The public SQLite database passed integrity, foreign-key, row-equality and
actual full-text-search checks. It contains 25 sources, 13 questions, 25 cards,
11 comparisons, 100 graph nodes and 135 edges. Its rows match the public JSON;
source-body/evidence tables and private paths are absent. Those full bodies,
evidence slices and literal documentary turns remain in a separate private
database. The independent receipt is `review/knowledge-independent.json`.

Accepted knowledge JSON SHA-256:
`9ef331231f1efdb52d482a00324999f5f1f3cfe5d7c66527e6e79a04dd5ef6b2`.
Accepted public database SHA-256:
`3a84753b36bf0cd7df5b39a842e6a52a9dbd2249e3e98effd4acd582afe3287c`.

## Speech-model acquisition and first pilot

The reviewer independently rehashed all six pinned Parakeet model/configuration
files: **2,509,473,204 bytes**, from official revision
`541d1f99c6b0c3cd0b11a95167540bb8edefd82b`. Configuration Git-object hashes and
primary model LFS SHA-256 match the downloaded bytes. All 16 prepared 30-second
PCM windows were rehashed and checked for nonoverlap, giving 480 seconds of
unique selected audio. Temporary model storage is not a permanent archive.

The first successful actual Parakeet pilot independently passed code, request,
model, PCM and output bindings. It recognized 78 words from one 30-second window,
exhausted all 375 encoder frames without an explicit token cap, and took 7.00
seconds of inference and 20.71 seconds including process startup. The observed
worker peak was approximately 2.81 GiB. These are measured execution results,
not transcription-accuracy or state-of-the-art ranking claims. The earlier
dependency failure was retained separately and produced no admitted transcript.

Review requested atomic worker-receipt writes to prevent a supervisor from
reading a partial JSON file; this was implemented before inference. Hard
deadlines and separate startup/inference timings are explicit. Resource samples
are periodic observations; file cache is not treated as nonreclaimable process
memory. Concurrent cloud workloads limit interpretation of wall-clock timings.
Private receipts are `review/asr-model-pcm-independent.json` and
`review/asr-feasibility-independent.json`.

The completed paired benchmark also passed independent artifact joins and
numerical recounts for **16 windows / 480 seconds**, with two actual CPU workers
for each recognizer. All 32 output/request/PCM bindings match. Parakeet's raw
generation-duration arrays independently sum to its recorded encoder advances,
and every admitted window exhausts its valid encoder frames. This establishes
model execution and input traversal, not correct recognition of every word.

The Parakeet stage took **62.40 seconds** including process startup, with **54.11
seconds** of overlapping worker inference; the controlled tiny.en stage took
**12.48 seconds**, with **9.95 seconds** of inference overlap. Parakeet produced
913 whitespace-delimited words and tiny.en 1,015. Independently recomputed median
symmetric word-edit disagreement is **0.07065**; it is not WER. Two windows differ
in literal negation counts. Neither the word totals nor these differences tell
which recognizer is more accurate without a reference or listening audit.

Review exposed six tiny.en segment-end estimates beyond their 30-second input
windows, by at most one second. These raw estimates remain unchanged and are now
visible as diagnostics. They do not imply speech outside the actual input.
Parakeet exposes window boundaries only, so this is not a comparison of timestamp
accuracy. Both model checkpoints now have public artifact hashes. The reported
627,057,286 floating state elements include normalization buffers and are labeled
accordingly, rather than presented as an exact learned-parameter count. Literal
calendar-word counts, including ambiguous “may,” are not detected dates.

The final benchmark projection SHA-256 is
`11a4242e924fa2509bfc11ef49337defab8d431ac885265913c77d31c48da5f7`.
Private checks are `review/asr-parallel-independent.json` and
`review/asr-public-final-independent.json`, followed by
`review/asr-public04-independent.json`. The final metadata additionally records
a post-hoc repetition diagnostic, independently recounted on all 32 outputs.
One tiny.en Ra window consists of 112 identical normalized tokens; none of the
Parakeet windows meets the disclosed run-length threshold of ten. All windows
remain in the reported denominator. This is a reason to inspect the recording,
not an acoustically verified hallucination or proof that the alternative is
accurate.

## Full-recording recognition extension

The separate full-recording extension passed independent completion review:
**four recordings, 359 contiguous windows, 171,833,236 input samples and
10,739.57725 seconds** of audio. Every stored float32 input was inverted exactly
to int16, and both chunk and whole-recording hashes match the original canonical
16 kHz mono S16 inputs. Every final partial window is included. All source audio,
original receipt, request, executed code, output and assembled text bindings were
checked, including all 359 raw encoder-duration sums.

The new edition contains **26,319 words**, compared with 25,964 in the previous
four machine-text editions. Two chunks produced empty recognized text; they
remain in the coverage denominator without an inferred explanation. The stage
took **1,273.79 seconds** with **1,252.74 seconds** of overlapping worker
inference. Actual model parameter enumeration reports **627,008,134 learned
elements**, distinct from the earlier state-tensor count. Shared cloud work,
recognition architecture, precision, segmentation and decoder context prevent
causal speedup or accuracy claims.

Full input coverage is not complete linguistic accuracy. Independent 30-second
windows can split speech and lose context; fixed window boundaries are not
verified word timestamps or speaker turns. The old source editions and their
annotation locators remain unchanged. The accepted metadata-only public
projection SHA-256 is
`fdfdd4d7fdeec4c7d2675061095d457b390e86a80343633e1ab9e0fcba71a7b9`.
Private proofs are `review/asr-full-completion-independent.json` and
`review/asr-full-public-independent.json`.

The paired downstream sensitivity calculation also passed. An independent
scalar dynamic-programming implementation reproduced the four full token-edit
distances: **104, 145, 108 and 1,602**. A separate log-TF/IDF reconstruction from
the source texts reproduced the baseline and counterfactual lexical matrices.
Arithmetic on the executed neural-vector witnesses reproduced both semantic
matrices and paired cosines; this did not repeat model inference. All 100
neighbor lists and the reported means, maxima and overlap calculations match.
The final unordered-recording plot uses unconnected score markers and was
visually inspected.

The average paired old/new cosine is **0.96159** for TF-IDF and **0.98804** for
MiniLM. Across the 25 logical source IDs, mean old/new top-five-neighbor Jaccard
is **0.96000** and **0.89333**, respectively. These are sensitivity measures;
similar vectors can still hide a consequential wording change. The hypothetical
four-row replacement contains 47,635 words, while the released primary fit
retains its 47,280 words. **Nine existing cards are flagged for re-reading and
none is rewritten or silently rebound to new evidence.**

Accepted sensitivity JSON SHA-256:
`02aacfb8ceef15df14226c16df587799f1a1e5e0dcb55c53e858b46905db113a`.
The independent receipt is `review/asr-sensitivity-independent.json`.

## Retrieval-design criticism

Before inspecting any retrieval rankings, the reviewer identified a structural
problem in full-list reciprocal-rank fusion with missing card coverage. With
25 raw-source candidates, 14 card-covered candidates and RRF constant 60, even
the worst-ranked covered source receives at least `1/85 + 1/74`, which exceeds
the best possible score `1/61` for an uncovered source. Thus every card-covered
source outranks every uncovered source regardless of query evidence.

The root run had already completed when this criticism arrived. The initial
result must therefore remain an explicitly diagnosed naive-fusion control. A
fixed top-five candidate fusion plus raw-source fallback is a **post-hoc design
repair**, not a prospectively untouched test. The original rankings, frozen
queries and source cards must remain preserved, and the comparison must not be
presented as evidence that hybrid retrieval or Google sleep training generally
fails.

The repaired run passed independent rank-policy, metric and public-projection
checks. All 32 original model/condition/query rows, including their numeric
scores, are unchanged. All answer and qualifier strings are identical between
the two card releases; only evidence-boundary metadata changed. The eight added
top-five fusion rows were independently reconstructed, all 40 known-support
rank/Hit/MRR calculations checked, and all ten summary and seeded-shuffle
calculations recomputed. Public outputs contain support locators and hashes but
no private evidence passages or filesystem paths.

The fourth query's known source has no card. Raw-source ranks are 3 for TF-IDF
and 4 for MiniLM; naive fusion lowers them to 15 and 16 by its coverage bias.
The post-hoc repair moves them to 5 and 7, respectively. The repair therefore
does not uniformly outperform raw retrieval. Card conditions cover three of the
four declared supports, which must remain visible alongside retrieval scores.
The fixed query set is too small and purposive to establish general rankings
between representations, consolidation policies or retrieval systems.

The repaired result SHA-256 is
`0df6a4967ed08fd10aed7a11a9d43c3373c53660a352b66eaaa3121e15a946a4`.
The private arithmetic/policy receipt is
`review/retrieval-run02-independent.json`. This check is separate from the
methods reviewer's independent initial TF-IDF/MiniLM representation refit.

## Independent rendered review

A separate browser pass inspected the actual release artifacts through an
explicit local preview mapping. It checked the conditional-tension comparison,
representation overlay, missing-card retrieval query, speech-model scope and
320-pixel layout. The numerical and interpretive qualifications are visible
beside the affected results; missing full-recording modules are unknown rather
than zero. This pre-integration pass does not establish deployed availability.

Two interaction/display defects were corrected and rechecked: changing the
selected point did not immediately update its displayed title, and a shared CSS
stroke rule made unselected semantic squares white-on-white. All 25 semantic
squares now have visible group-colored outlines, selection updates immediately,
and the aligned display retains all 25 source IDs in each representation.
The connections are expressly labeled display displacement, not changing belief
or a common latent dimension. Eight focused independent browser checks passed;
the scoped receipt is `review/browser-independent.json`.

## Contextual-token experiment

The separate token-state exploration passed source admission and arithmetic
review on its actual stored outputs: **24 terms, 409 source/term pairs, 711
sampled occurrences from 2,290 available occurrences**, all from the same fixed
25-source frame. Every original and masked character span, token offset,
ordinal sample choice and model-input token-ID hash was independently checked.
The largest input contains 51 wordpieces including its two special tokens.
Document-frequency counts reconcile exactly with the observed source/term pairs.

The reviewer independently reconstructed the log-TF/IDF term-selection rule,
checked all 384-dimensional sample/source/term vectors for finite unit norms,
and recalculated both mean-pooling stages, the complete term cosine matrix and
the shared PCA coordinates. The first two components explain **23.16%** of the
variance; trustworthiness at five neighbors is **0.86458**. These checks use the
actual saved representation witnesses; they do not repeat neural inference or
validate a word-sense model. The label-cleanup release changes figures and
revision metadata only, and its refined plot was visually inspected.

Sentence-trained MiniLM token states retain lexical identity, model priors and
local context. Nearby terms or source-context points do not establish shared
answers or entities. The term vector is renormalized after averaging sources,
so its displayed location need not be the arithmetic center of the projected
source points. Only two predetermined occurrences per source/term are sampled.
The accepted public SHA-256 is
`5d3d509f6a50927019eedf936170a7df8bfe5bc5dff5874b015d211581c6327e`;
the private receipt is `review/contextual-independent.json`.
