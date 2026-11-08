# Dataset and measurement card

**Purpose.** Study source attribution, discourse similarity, scoped answer
comparisons, recognition sensitivity and knowledge-system maintenance. This is
an exploratory convenience sample, not a census, a representative religious
survey or an assessment of paranormal truth.

**Observation units.** Keep publication, original recording, retained audio
derivative, decoded waveform, recognition edition, text edition, sampled
context, claim card and comparison distinct. A question may be analyst-created
or a paraphrase of a printed question; neither category identifies an unknown
audio speaker. Reused sources and synthetic controls are explicitly labeled.

**Composition.** The fixed text frame has 25 distinct normalized bodies and
47,280 whitespace words, six medium contexts, 17 exact printed labels and 13
comparison labels. Broad civilization labels do not assert the same speaker.
Twenty earlier written messages and five Council editions are reused. Four of
those Council editions are machine transcripts; the remaining Council source
is a written Arcturian comparison control. Date, source, genre, author and
recognition method are confounded. English-only selection excludes other
languages and traditions without implying absence.

**Question/reading sampling.** Curated cards were developed from visible source
answers. Actual reading spans cover 14 sources and 15,795 unique body words;
only ten complete written bodies were read for this annotation layer. Five
documentary-question fields add 65 words. Four independent audit queries were
frozen before their author inspected cards or rankings. They are source-informed
AI questions with known-support labels and incomplete relevance judgments, not
human gold labels or an independent population test. The card author did not
see those queries before freezing the cards.

**Acquisition and access.** This study reuses previously retained publicly
available publisher sources. No new YouTube recording is counted. Thirty-second
Bashar test excerpts are internal windows of an eligible recording; the existing
five-minute minimum for collecting Bashar publications is unchanged. Other
recordings retain their no-minimum collection policy. The speech model was
retrieved from its official NVIDIA release at a pinned revision; model-card
benchmark claims remain external claims with different datasets.

**Transformations.** Source normalization, exact-name masking, tokenization,
TF-IDF, complete neural chunk coverage, pooling and projections are recorded in
machine-readable outputs. Contextual token states use a bounded term/occurrence
selection and source balancing. Source chunks, card answers, qualified cards
and fusion policies are separate indexes. The top-five fusion repair followed
the first results and is explicitly post-hoc. Original results are retained.

**Recognition.** The excerpt comparison reuses identical PCM for both systems,
with pinned settings and measured worker overlap. There is no independently
word-aligned reference. The full Council extension first verifies the older
canonical S16 waveform, then converts to floating-point input and processes
nonoverlapping 30-second chunks including each tail. This differs from older
whole-recording/VAD context handling. Boundary effects, word accuracy, speaker
identity and exact audio alignment remain unmeasured. New transcripts are
additional editions, not automatically preferred ground truth.

**Quality controls.** Exact source and model hashes, duplicate/family checks,
chunk/sample coverage, transcript-output status, source/character/turn locators,
database joins, raw timing overruns and model repetition flags are inspectable.
Independent AI reviewers corrected five substantive or locator issues in the
card layer and derived the naive-fusion coverage bias. These checks do not
replace listening, human annotation, external validation or outcome assessment.

**Dependencies and uncertainty.** Documents by one medium and derived editions
of one recording are not independent observations. Pair scores are dependent.
Small, unequal source strata, repeated vocabulary, formatting, date and text
length can drive clusters. A high cosine can accompany a negation; a similar
word can have different senses; a graph edge can represent only attribution.
Projection explained variance and neighborhood distortion are exposed.

**Release and use.** Public artifacts contain metadata, derived measurements,
bounded paraphrases, typed links, plots and a sanitized SQLite question bank.
Full publisher texts, audio, recognized transcripts, exact evidence slices,
model weights and path-bearing receipts remain private. Public availability
does not grant blanket redistribution rights, and named sources are not
anonymized. Use the public site for exploration and source navigation; do not
use it as a verified prediction service or automatic truth/credibility classifier.

**Maintenance.** Preserve immutable source editions. A changed body hash
invalidates automatic reuse of its annotation offsets and triggers an affected
card review. Keep original and corrected annotations with their reasons and
review status. Regenerate downstream artifacts from the selected edition and
rerun affected checks. Temporary cloud memory is not an archival retention plan.
