# Qualitative synthesis — expanded non-Bashar self-run ASR corpus (acquisition-2026-11)

## Evidence boundary

All statements below describe **self-run baseline ASR** of public YouTube audio:
provider label `self_run_faster_whisper_tiny.en`, sourceType
`public_youtube_audio_self_run_ASR`. Audio was acquired through the ordinary
public y2mate.gs paste-link interface and transcribed locally with the pinned
Systran/faster-whisper-tiny.en model (CPU int8, beam size 1, VAD,
`condition_on_previous_text=false`, contiguous 300-second decode windows covering
100% of each file). Converter-assisted acquisition may be subject to YouTube and
provider terms; public availability and technical feasibility do not establish
permission to download or redistribute. These transcripts are **not rendered subtitles** and are not original caption tracks. This layer is independent of the provider-rendered
subtitle workstream in `research/expansion-2026/non-bashar-analysis`.

There is no diarization, no speaker verification, no human WER measurement, and
**humanValidated=false** throughout. Uploader, practitioner, and claimed entity
remain distinct metadata roles. Claimed-entity names are **publisher metadata**
labels only; nothing here establishes a physical origin, entity reality, speaker
identity, answer truth, or agreement between sources. Raw recordings and full
transcript bodies remain in private research storage pending source-specific
redistribution review. Public outputs contain metadata, aggregates, hashes, and
bounded review excerpts only.

## Candidate accounting and artifact validation

The terminal partition is **34 analyzed + 8 excluded + 1 route-limit hold = 43
candidates**. Thus **8 of 43** candidates are excluded and **1 route-limit hold**
remains outside the analyzed denominator; no pending candidate is counted as
analyzed.

- The 34 included English documents contain **13,169 ASR segments, 146,605
  whitespace words, and 19.472 hours of audio**. Every included record is bound
  across the audio file, acquisition receipt, ASR receipt, acquisition ledger,
  ASR summary, and output hashes. Decode windows cover the full decoded audio;
  included ASR text coverage is at least 0.75 of ffprobe duration.
- **Seven under-300 exclusions:** `DfBrQbKIWHg`, `GV8PXtHeBk8`,
  `Rus5nLjg8ZE`, `6eZDJwSzj3Y`, `VvOZKNFKbmo`, `-HH8KFobnHk`, and
  `hSlyR0POnFw`. Their measured durations are below the 300-second policy
  minimum. Their audio is quarantined and they have no completed ASR or analysis
  state.
- **One unsupported-language exclusion:** Pavlina Klemm (`-KVKPRLFte4`). The
  audio is German; forced English-only ASR produced degenerate text. The receipt
  is `excluded_language_mismatch` (detected `de`, expected `en`). All four ASR
  outputs, including the partial segment file, are quarantined and hash-bound,
  and the regenerated receipt binds the pinned settings and a source-snapshot-
  verified code edition. The partial is an exact copy of the current final
  segment stream, with `partialProvenance` and a separate repair-script hash;
  no retranscription is claimed for that repair. Future quarantine code preserves
  and hashes the partial produced during the same run. The older nested receipt
  is retained only as an explicitly unverified legacy record.
- **One route-limit hold:** `8WHAw-wIuQg`, an eight-hour Kryon compilation, is
  `held_route_limit_over_150_minutes`. No audio, completed ASR, or analysis is
  claimed for it.
- **Edition difference, not a language exclusion:** Aurora Ray (`-8k6d9StYig`)
  has an Arabic provider-rendered subtitle edition but coherent English audio
  and English self-run ASR. The editions are not treated as equivalent.
- **Non-fatal coverage notes:** `-leIq8XP15k` and `widNthTctcU` have ASR text
  coverage of approximately 0.924, consistent with a speech-free or music tail
  under VAD. `-o4q27DpxaA` and `6GsKmBdXOtI` have final segments extending only
  marginally beyond nominal ffprobe duration. Christine Day retains an elevated
  repetition flag at normal speech rate; this may reflect mantra-like delivery,
  ASR looping, or both.

The resume path was exercised after the expanded acquisition: all 34 completed
ASR results and the language exclusion were reused only after their audio,
settings, output hashes, and code-edition allowances validated. Two stale summary
entries were refreshed from the actual on-disk receipts without re-transcribing
the audio. Summary updates are serialized and atomic, and a skipped or failed
result cannot downgrade an existing terminal record.

### ASR code-edition provenance

Six historical code hashes occur among included receipts. Twenty-two included
documents use editions with exact surviving source snapshots; twelve use legacy
receipt hashes whose source snapshots are unavailable. `asr-code-editions.json`
records this distinction. Legacy reuse means **artifact reuse after hash and
settings validation**, not source-code equivalence. Every public source-registry
code hash is joined back to its receipt and the edition manifest. Public
archival snapshots are path-redacted where necessary; `snapshotSha256` binds the
public file while the original receipt code hash is retained separately and the
transformation is disclosed. `producedCurrentArtifacts` distinguishes editions
that generated current receipts from provenance-only editions.

Nine legacy completed receipts originally lacked language metadata. Those fields
were backfilled from the existing hash-bound ASR text without retranscription,
using the same script-aware heuristic and a separately recorded backfill-script
hash. This is not human language validation. Every included receipt now has
`detectedLanguage=en`, `languageReviewRequired=false`, a word-rate and a Boolean
verification flag; the analysis independently re-detects language from transcript
text as before.

## Corpus diagnostics

### TF-IDF and NMF

TF-IDF uses unigram and bigram Unicode features after stopword and proper-name
masking. Practitioner and claimed-entity brand tokens—including Kryon, Ryokah,
Yahyel, Bashar, Galactic, and Federation—are excluded from the TF-IDF/NMF input;
the verifier rejects their reappearance in NMF top terms. Proper names account
for at most 0.62% of tokens in any one document. Nineteen English-oriented
commercial-regex hits occur across seven documents; these are review flags, not
validated advertisements or a cross-language detector.

The six NMF components are largely document- or format-specific:

1. self/body/energy and consciousness vocabulary;
2. “dear ones,” shift, and year-oriented phrasing;
3. Earth/human civilization, DNA, and similarity vocabulary;
4. ocean/waves, toxicity/purge, card, and volunteer vocabulary;
5. supercomputer/simulation, higher-self, lessons, and code vocabulary;
6. showing/book/snake/judgment, livestream, and Akashic-record vocabulary.

NMF mean best-match seed-stability cosine is **0.7438** across ten random-init
runs. The base run and all ten stability runs converged before the
1,200-iteration cap. Iteration counts and convergence are exported and
independently recomputed. This remains a descriptive diagnostic, not evidence of
robust semantic categories. Topic × claimed-entity overlays compare
publisher-attached labels only.

### KMeans and document network

KMeans diagnostics for k=2..8 have maximum mean silhouette **0.0070**. Seed ARI
uses nine comparisons against the base seed for each k; the trivial base-versus-
itself ARI=1 is excluded. ARI still varies widely. There is no defensible
cluster claim from these 34 documents.

The document network has mean pairwise TF-IDF cosine **0.0495** and maximum
**0.1285**. The strongest edges connect related Kryon or Ryokah recordings and
repeated practitioners across publishers. A cross-publisher edge involving the
multi-practitioner event is not independent evidence of an entity-level effect.
Below-threshold strongest-neighbor edges are visualization aids; all-zero nodes
remain isolated and no zero-weight pseudo-edge is admitted.

Question density and temporal placement remain format properties. Interview,
panel, livestream, relay, and solo-monologue sources produce different numbers
of literal question units; these differences must not be reified as properties
of a claimed civilization or personality.

## Literal Q&A layer

The corpus yields **572 literal question units and 781 question sentences**.
Automatic discourse labels are 290 direct-interview candidates, 275 unclear
contexts, six rhetorical candidates, and one secondary report. These automatic
labels are deliberately provisional.

- **Question families:** other_theme 524, predictions 18, reality_agency 11,
  healing 9, ascension 6, contact_timing 2, and dna_origins 2.
- **Answer-window states:** 430 complete line-cap, 133 interrupted by the next
  question, three end-of-transcript boundary-unknown, two no-answer-window, and
  four no-answer-at-end. `complete_line_cap` means the four-segment extraction
  window filled; it does not establish that the speaker finished the answer.
- **Answer orientation:** 358 descriptive/explanatory, 129 unclassified_default,
  61 conditional/hedged, 12 process/practice-oriented, six timing-specific, and
  six not captured. The 129 unclassified windows (22.5% of all units) match none
  of the orientation patterns and are not positive descriptive evidence.
  Orientation describes captured text shape only.
- **Publisher concentration:** Kryon Lee Carroll contributes 104 units, The
  Galactic Guide 89, The Importance of your last lifetime 82, Heart Coherence
  Collaborative 52, Daniel Scranton 40, Barbara Marciniak 36, The Stargate
  Experience 32, and The Heyoka 32. Counts therefore reflect publisher and
  format coverage, not balanced sampling across claimed sources.

### Fresh expanded AI review

A new stratified sample of **69 units** was reviewed by three analysis agents;
this is `ai_agent_review`, not human annotation. Every verdict is bound to the
current question SHA-256 and source metadata. Verdicts are **7 confirm, 49
reclassify, and 13 boundary_error** (18.8% boundary errors). Reviewed classes are
34 rhetorical, 19 direct-interview, eight unclear, seven secondary-report, and
one self-report.

The expanded Kryon material changes the qualitative picture: many apparently
direct questions are speaker-posed hypotheticals, audience polls, agreement tags,
or immediately self-answered rhetorical pivots in solo monologue. Phrases such
as “you might say” and “dear one” are not sufficient evidence of a second
speaker. Conversely, some unclear Ryokah units contain recoverable two-party
audience Q&A and were promoted only where a responsive exchange is visible.
Quoted audience questions, anecdotal dialogue, and practitioner-relayed speech
remain secondary reports. Boundary errors include headless clauses, multiple
questions split across units, a following question placed in the answer slot,
and non-responsive turn alignment. No speaker diarization was added to resolve
these cases retrospectively.

### Common-question recurrence

There are **473 token-keyed families**. **17 recur across videos**, three repeat
only within a single video, and 20 repeat anywhere. Sixty-three stopword-only
units remain family-less and cannot form a spurious empty-key common question.
Interrogative stopwords are applied uniformly, preventing a one-token “what” or
“who” family.

Cross-video recurrence is dominated by generic forms: comprehension checks
(“do you understand?”), rhetorical feeling prompts, “does this make sense?”,
“what else?”, possibility wording, and the repeated outro “Why not join us?”
The latter appears in four Kryon-associated videos and is a publication/outro
pattern, not a substantive common research question. Token-key recurrence is not
semantic equivalence, independent recurrence, or evidence of reposting by
itself. `repostRisk` is a review flag, not a repost finding. The CSV adds an
explicit `recurrence_scope` column for cross-video, same-video-only, and
singleton rows; the risk figure includes all 473 families, including singletons.

## Independent numerical verification

Beyond receipt and hash validation, the verifier recomputes every Q&A unit and
its answer/orientation/family fields from the private segment index, plus TF-IDF
top terms, NMF iterations and stability, KMeans silhouettes and non-self ARIs,
network mean/max cosine, and all proper-name/commercial sensitivity values.
Synthesis extrema and headline diagnostics are bound to those recomputed values.
This does not make the categories substantive truths; it prevents stale or
internally inconsistent numerical artifacts from passing merely because their
hashes agree.

## Limitations for every downstream use

This is a modest, English-only, tiny-model ASR corpus with unmeasured transcript
accuracy. Window boundaries can split words; long ASR segments and sentence
splitting can split questions or misalign answers. There is no diarization or
speaker verification and **humanValidated=false**. AI review is not human
annotation; no human peer review occurred. All NMF runs converged before their
cap, and KMeans still provides no defensible cluster basis. Legacy ASR code
snapshots are incomplete and explicitly labeled. Observed acquisition candidates
are not a full-channel census, and the eight-hour route hold is not a download
failure count. Literal `?` extraction misses questions without question marks
and inherits ASR errors verbatim. Question types, token families, answer windows,
and orientation categories do not measure truth, originality, speaker identity,
or agreement between claimed entities.
