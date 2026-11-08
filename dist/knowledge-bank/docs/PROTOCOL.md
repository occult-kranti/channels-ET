# Knowledge bank and speech-recognition comparison

Exploratory protocol, 8 November 2026. This additive study preserves every earlier
transcript edition, numerical fit and paper. Its research object is published
discourse and its representation in a knowledge system, not the authentication
of claimed beings or forecasts. This protocol develops during the study and is
not a preregistration.

## Questions and finite frames

1. Can a stronger contemporary open speech-recognition model run within this
   CPU cloud, and how do its resource use and output differ from a controlled
   small-model rerun on identical audio windows?
2. How do lexical and neural representations change neighboring documents,
   source/label groupings and the apparent similarity of answers?
3. Which source-linked answers share a proposition, remain compatible, differ
   in focus, create conditional tension, or explicitly contradict one another
   under the same referent, conditions and time?
4. Does a small, source-bound card index improve access to known supporting
   sources, and what coverage or qualifiers does that consolidation lose?

The fixed knowledge frame is the earlier 20-message written pilot plus five
Council text editions. Exact normalized bodies and declared publication families
are checked before fitting: **25 retained editions, 47,280 whitespace words, six
medium contexts, zero identified aliases**. Unresolved common origins remain
unresolved. The separate completed 228-unit publisher fit is not added to this
denominator. Its existing results remain a reference study.

The speech pilot uses independently selected retained recordings and deterministic
nonoverlapping excerpts. A proposed maximum of sixteen 30-second windows spans
Council, Ra, Bashar, OmNa and Multidimensional Soul contexts, subject to successful
source/receipt joins and a first-window feasibility test. The executed benchmark
must report the actual admitted windows, not this proposed maximum. Excerpt
transcripts do not count as complete new recording transcripts or replace prior
full-length editions.

## Speech-model admission

Use a pinned primary model release and inspected model card; published benchmark
claims do not establish local accuracy or universal state of the art. Preserve
model-file hashes, runtime versions, request parameters, audio/PCM lineage,
window offsets, completed inference status, timestamps and resource measurements.
Compare identical PCM with a controlled cached Whisper baseline. A difference
between recognizers is not a word-error rate against ground truth. Known
publisher captions are not silently treated as verbatim, aligned reference text.

The environment has four CPU cores, a 32 GiB memory limit and no detected GPU.
Persistent disk is nearly full. New model weights, caches and temporary PCM use
RAM-backed storage; those weights are ephemeral and must be reconstructed from
their pinned source after environment loss. Initial admission allows at most two
one-thread inference workers, with model/process memory within an 18 GiB budget.
The first 30-second window is timed before admitting the parallel batch. Revisit
the configuration if it takes more than 180 seconds or exceeds the memory budget.
Keep the existing 2 GiB persistent-disk floor and all earlier media/models intact.

## Measurement and interpretation

The common 25-edition analysis compares TF-IDF and the existing pinned MiniLM
encoder, with exact-name masking, length/pooling sensitivities, neighbor overlap,
source-confounding diagnostics and explicitly labeled projection alignment.
Two-dimensional proximity is a projection, not a probability or belief space.
Term overlays derived from TF-IDF must not be labeled neural word embeddings.
Dependent source pairs are descriptive measurements; they are not independent
trials, entity-origin probabilities or a basis for unplanned significance tests.

Question records distinguish analyst-created questions from paraphrases of
genuine printed questions. Unknown audio speakers stay unknown. Every curated
card retains its source edition, exact support locations, time and condition
qualifiers, annotation provenance and uncertainty. Similarity scores retrieve
candidates; they do not decide agreement or contradiction. A zero observed
contradiction count is a valid outcome of bounded reading, not universal harmony.

The independent reviewer freezes four source-informed retrieval queries and
known supporting-source labels before inspecting cards or rankings. These are
AI-authored, purposive queries with incomplete relevance judgments; they are
not human ground truth or a blind generalization test. No settings are tuned
against their rankings. Card indexing excludes question strings and evaluation
labels. Source text, card answers and their fixed hybrid are compared using
declared source-level ranks, known-support hit rates and reciprocal ranks.
Unjudged sources are not called irrelevant. Index size, source coverage,
document length, curation and source multiplicity remain explicit confounds.

## Google paper and consolidation boundary

The literature role identified *Language Models Need Sleep*, arXiv:2606.03979,
through Google's October 2026 research blog and inspected the primary paper.
Its parameter expansion, learned memory experts, imitation objectives and
synthetic replay are distinct from our retrieval system. The present source-card
experiment is an engineering analogy about offline consolidation and retrieval;
it does not reproduce that training algorithm, modify language-model weights,
or establish a shared biological mechanism. Literature-specific claims and
limitations belong in the versioned source register.

Cross-field connections are recorded as hypotheses or design analogies with a
proposed test and disconfirmation condition. Neither a graph edge nor repeated
language upgrades an analogy into empirical evidence.

## Review and release

Five AI roles cover speech engineering, literature, computational methods,
source/question annotation and critical interface design. A separate independent
auditor checks frozen queries, decisive source readings and executed benchmarks;
the root agent integrates the work. These are AI roles, not human expert peer
reviewers. Record objections, corrections, actual executed checks and remaining
limits in a panel ledger. Repeat affected checks after meaningful changes.

Public Git/Pages contain code, sanitized question/card metadata, paraphrases,
derived data, plots, documentation and a queryable sanitized database. Full
audio/text, evidence spans, model weights and path-bearing receipts remain
private. The new dashboard is additive. Publish only actual accepted artifacts
with exact source/output hashes, clearly separated from proposed experiments.

## Recorded design amendments

After the first executed retrieval result, an independent reviewer derived a
structural defect in full-list reciprocal-rank fusion without viewing rankings:
with 25 raw sources, 14 card-covered sources and constant 60, even the worst
double-listed source scores above the best raw-only source. The initial run is
preserved. Full-list fusion remains a diagnosed coverage-biased control. A single
fixed repair fuses only the top five candidates from each list and then appends
the untouched raw-source tail. This is a **post-hoc design repair**, not a
prospectively held-out improvement test; queries, cards and representation
settings remain unchanged. Both policies are reported, including failures.

The first admitted Parakeet feasibility window consumed all 375 encoder frames:
30 seconds of audio took 7.00 seconds of inference and 20.71 seconds including
setup. After independent review, the finite extension admits the four complete
Council recordings (178.99 minutes) for new parallel recognition editions. It
uses nonoverlapping 30-second chunks, retaining the final partial chunk and
checking complete decoded sample coverage. The original full-recording S16 PCM
hashes are checked before conversion to floating-point model input. Chunk
boundaries and context length still differ from the older recognition pipeline.
The controlled sixteen-window comparison and this full-recording extension are
separate denominators. Actual completion is determined only by retained receipts.

The primary 25-edition model and every existing card remain bound to their old
source hashes. New full-recognition editions support a separate paired
sensitivity analysis and an affected-card audit; they do not automatically
replace evidence, move annotation offsets, or establish improved word accuracy.
