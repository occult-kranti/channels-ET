# Knowledge bank and speech-recognition laboratory

[Dashboard](https://occult-kranti.github.io/channels-ET/dist/knowledge-bank/) ·
[Technical report](report/report.pdf) · [Portable LaTeX source](report/source.zip)

This additive research layer compares representations, consolidates bounded
source readings into a question bank, and measures a stronger speech pipeline.
Earlier corpus editions and papers remain unchanged. Sources describe claimed
channeling; the study does not authenticate entities, speakers or predictions.

| Layer | Actual frame | What it supports |
| --- | --- | --- |
| Fixed text comparison | 25 editions, 47,280 words, six medium contexts, 300 document pairs | TF-IDF/MiniLM comparisons, neighbor changes, source/format confounding and exploratory topics |
| Curated knowledge bank | 13 questions, 25 cards, 11 comparisons; 100 graph nodes and 135 edges | Source-linked propositions, qualifications and scoped answer comparisons |
| Reading coverage | 15,795 body words across 14 sources, plus 65 printed-question words | Bounded AI reading; ten complete written bodies and selected windows from four ASRs |
| Retrieval audit | Four independently frozen, source-informed queries; 276 raw chunks versus 25 cards from 14 sources | Known-support ranking and coverage diagnostics, not general relevance accuracy |
| Contextual token states | 24 terms, 409 source-term pairs, 711 sampled occurrences from 2,290 available | Shared-projection source overlays; not a validated word-sense or entity ontology |
| Controlled speech comparison | 16 paired 30-second windows, eight recordings, six contexts, eight minutes of unique audio | Paired output disagreement, resource use and actual concurrency |
| Full-recording extension | Four existing Council recordings, 178.99 minutes, 359 nonoverlapping chunks | New recognition editions and a separate paired sensitivity; original evidence stays fixed |

**Full-recording extension completed:** 26,319 recognized words in 21.23 minutes
on two CPU workers. All 171,833,236 decoded samples were covered; two windows
produced no text and remain recorded. Independent checks verified original audio
bindings, complete sample coverage and output assembly. This establishes coverage,
not transcription accuracy. The separate sensitivity flags nine existing cards
for rereading before transfer; no original card or source edition was replaced.

The main 25-edition frame reuses the 20 written-message pilot and five Council
texts. It does not add the separate 228-unit publisher study to its denominator.
The speech benchmark overlaps the full-recording extension: their durations and
outputs must not be summed as independent recordings. No new channel audio or
YouTube upload census was collected for this study.

## Findings and implemented checks

Lexical and neural neighbors differ substantially (mean top-five Jaccard about
0.340). Exact-name masking, centered windows, pooling choices, source/label
strata and seeded clusters remain inspectable. The clusters have weak separation
and unstable assignments. A clearly separated synthetic negation control shows
that high cosine similarity cannot establish agreement.

The question bank distinguishes eight analyst questions from five paraphrases
of genuine printed questions. Its 11 source-read comparisons include one shared
proposition, four compatible pairs, three differences in focus, one conditional
tension and two unresolved comparisons. Zero strict scoped contradictions were
admitted; this does not imply universal agreement. Unknown audio speakers remain
unknown, and every card retains original source hashes and evidence locations.

The card-only index lacks one of the four known supporting sources. An
independent reviewer also derived a structural flaw in naive full-list rank
fusion: with 25 raw sources and 14 card-covered sources, every double-listed
source scores above every raw-only source regardless of query meaning. The
original result is retained. A fixed top-five candidate repair is labeled
post-hoc and does not establish a general improvement. Raw-source MiniLM remains
stronger than its card-only and repaired-fusion counterparts on these four
purposive queries. Raw evidence must remain available alongside curated cards.

NVIDIA Parakeet TDT 0.6B v3 was actually downloaded, hash-verified and run on CPU.
The pinned six-file model is 2,509,473,204 bytes. The paired benchmark completed
in 62.40 seconds including setup, versus 12.48 seconds for cached tiny.en; both
used two one-thread workers. Median symmetric word-edit disagreement is 0.07065,
not word error rate. One tiny output has an extreme 112-token identical run;
all outputs remain retained and the repetition flag is post-hoc quality triage.
No audio-listening reference or measured accuracy improvement is claimed.

## Google's Sleep paper and the implemented analogue

The matching paper is [*Language Models Need Sleep*](https://arxiv.org/html/2606.03979v2),
discussed in [Google's October 2026 blog](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/).
Its memory experts, parameter expansion, distillation/imitation and synthetic
replay update neural weights. This project implements an external,
source-bound consolidation and retrieval experiment. It does **not** reproduce
that training algorithm or update language-model weights. The literature review
also distinguishes Sleep-time Compute, Nested Learning, GraphRAG and HippoRAG.

## Documents, data and reusable workflows

- [Protocol and recorded amendments](PROTOCOL.md), [methods](METHODS.md),
  [data card](DATASET-CARD.md), [annotation codebook](CODEBOOK.md)
- [Literature](LITERATURE.md), [panel decisions](PANEL.md),
  [independent review](INDEPENDENT-REVIEW.md), [interface review](REVIEW.md)
- [Question database](../../dist/knowledge-bank/questions.sqlite),
  [reading document](../../dist/knowledge-bank/question-bank.md),
  [offline query tool](question_query.py)
- [Project skills](skills/): versioned source-card consolidation, scoped answer
  comparison and speech-edition evidence workflows. These are repository skills,
  not a claim that a new global plugin was installed.

Example offline query from the repository root:

```bash
python3 research/knowledge-bank/question_query.py \
  --database dist/knowledge-bank/questions.sqlite --query contact
python3 research/knowledge-bank/question_query.py \
  --database dist/knowledge-bank/questions.sqlite --relation conditional_tension
python3 research/knowledge-bank/verify_release.py --site .
```

`build_public.py` copies explicit reviewed output allowlists into the static page
and binds each module/download by SHA-256. Numerical and reading inputs remain
versioned; new editions never silently replace their parents. Full evidence,
transcripts and exact annotation spans remain under the private
`knowledge-bank-2026-11/` archive. Model weights, runtime dependency target and
temporary PCM live in RAM-backed storage and are ephemeral; pinned download and
wheel hashes support reconstruction. This is not permanent ChatGPT account
storage. Existing audio, models and the hash-pinned legacy collector are intact.

The maintained experiment ledger distinguishes executed, partial and proposed
work. In particular, human transcription accuracy, annotation reliability,
representative query evaluation, graph-retrieval gains and physical mechanisms
remain unmeasured. Five AI panel roles plus an independent audit supported this
release; they are not human expert peer review.
