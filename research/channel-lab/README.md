# Channel and recording laboratory

[Open the laboratory](https://occult-kranti.github.io/channels-ET/dist/channel-lab/)

The laboratory adds source-level and publisher-context exploration to the
existing Channeling Atlas studies. It reconciles **493 canonical documents and
1,411,446 whitespace words** from 572 accepted source rows and 502 distinct
text artifacts. The frame has 26 modeled publisher contexts. Its 14 named
creator-context IDs are not a count of distinct people: official and guest
Bashar contexts differ, Ra is a session context, and guest identities in mixed
interviews remain unresolved.

The 55 coverage rows keep modeled publisher contexts, 12 screened account
references and 17 historical caption-study references distinct. They are not 55
independent mediums. Historical caption bodies that cannot be reverified are
excluded from the new fit. Earlier research editions and manuscripts remain
unchanged.

## Explore the actual source frame

- **Evidence inventory:** filter/search the registry, distinguish canonical text
  counts from saved publisher media and unknown YouTube upload totals.
- **Publisher-context pages:** inspect text origins, publication-date coverage,
  topic profiles, contrast terms and the constituent source records.
- **Document/recording pages:** inspect one source's provenance, alternate
  editions, keywords, model topic weights, text-position progression and
  original-space neighbors. Written sources remain labeled as written sources.
- **Cross-source comparisons:** select contexts or individual sources, compare
  lexical and neural similarities, inspect the source composition behind group
  means, and vary network edge rules. A shared name or high similarity does not
  authenticate a shared entity or a matching answer.
- **Speech batch:** inspect a separately selected nine-recording recognition
  extension, sample coverage, actual audio-window measurements and edition
  comparisons. New recognitions never silently overwrite the canonical frame.
- **Source readings:** inspect twelve purposively selected comparison cases;
  their bounded reading coverage is explicitly separate from computational
  coverage of the 493-document frame.

The interface is static and runs its filters, views and matrix inspection in the
browser. It requires no remote inference service. Raw audio/video, full
transcripts, exact annotation spans and model files remain in the private managed
workspace, not the public Pages deployment or permanent ChatGPT account storage.

## Analysis and review

The common fit compares masked TF-IDF and pinned MiniLM representations, fixed
eight-factor NMF, source-level topic progression, and a separate eight-cluster
partition. The experiment examines lexical/neural neighbor differences,
bounded-window sensitivity, incomplete name masking, alternate chunk pooling,
topic/cluster seed stability, format composition, and publisher/creator-context
balancing. These choices address specific source and measurement risks; they do
not establish population prevalence, word accuracy, causal effects or a true
number of doctrines.

Source-text positions use normalized body character/word locations, not invented
video timestamps. Actual ASR windows use sample boundaries; they are not aligned
word timestamps. Publisher transcript pages are not an independent listening
reference for a particular recording edition.

The independent AI reviewer challenges source joins, duplicate families,
annotation scope, factor scaling, sampling imbalance, output accounting and
rendered interpretations. Review decisions and residual limits are recorded in
[REVIEW.md](REVIEW.md) and [PANEL.md](PANEL.md). This process does not constitute
human peer review, institutional review or conference acceptance.

## Reproducible components

- [Protocol](PROTOCOL.md) and [source schema](SOURCE-SCHEMA.md)
- `sources.py`: immutable source reconciliation and verified text loader
- `analyze_encoder.py` and `analyze_corpus.py`: bounded CPU representations,
  lexical/topic models and numerical witnesses
- `asr_batch_prepare.py`, `asr_batch.py`, `asr_batch_worker.py` and
  `asr_batch_project.py`: frozen selection, bounded streaming queue, immutable
  recognition editions and verified resume
- `asr_effects.py`: separate counterfactual edition comparison using the frozen
  baseline vocabulary and representation contracts
- `build_readings.py`: source-bound qualitative cases with checked private spans
- `build_public.py`: explicit reviewed allowlists and public hash manifest
- `verify_release.py`: static-set, source, numerical and cross-module release
  checks; no private source bodies are needed for the public checks

Examples from the repository root:

```bash
python3 research/channel-lab/verify_release.py --site .
python3 research/channel-lab/asr_batch.py --help
python3 research/channel-lab/analyze_corpus.py --help
```

Full computational reproduction additionally requires the hash-bound retained
private sources and pinned model, as documented by the producing scripts and
their receipts. Public figures and metadata alone do not reconstruct missing
copyrighted source bodies. The downloadable release manifest identifies exact
public artifacts; no task is declared executed merely because code exists.

## Release completion

The accepted common fit processed **493 retained documents / 1,411,446 words**
across 26 publisher contexts. Independent lexical/numerical checks covered the
representations, neighbor controls, group matrices, factor scaling and
projections; a separate check reproduced all 14 network settings and the
four-source Mary/Magdalene contrast. These are retained-source results, not a
complete census of channel uploads.

Three findings matter when interpreting the plots:

- Publisher-macro top-five neighbor overlap is **0.3202** for lexical versus
  neural representations and **0.0507** for full versus centered, at-most-300-token
  neural text. Representation and selected content substantially change which
  sources look closest; these scores do not measure accuracy.
- Four preselected Mary/Magdalene messages have higher **average** within-creator
  similarity than same-label cross-creator similarity in all four representations,
  with individual-pair exceptions. This small descriptive comparison supports a
  source-style alternative, not authenticated entities or universal agreement.
- Conversation, identity and promotion terms remain visible in topic factors.
  One factor's seed comparison falls to **0.2878**, despite a much higher mean.
  Eight model factors are not eight established doctrines or civilizations.

The speech extension completed **nine new recognition editions, 132.61 minutes,
269 windows and 15,300 words** from retained audio, with **no new downloads**.
Independent checks verified the waveform/output joins and complete sample
coverage. Two CPU workers had 891.88 seconds of observed overlap during a
899.39-second stage; no matched serial speedup or word-error-rate claim follows.
Four empty windows are retained, and the original canonical texts stay unchanged.

A separately audited [edition sensitivity comparison](../../dist/channel-lab/asr-effects.json)
replaces only the nine selected representations: mean top-five neighbor overlap
for those sources is **0.6614 lexical / 0.5780 neural**. Whole-frame averages are
much higher because 484 representations remain unchanged. Five replacements
also change publisher-written text to ASR, so this is not an isolated test of
recognition quality. The contextual-word overlay separately explores 24 terms
and 921 sampled occurrences; its token states are not validated word senses.

The twelve source-read cases cover **10,006 unique words in 22 canonical sources**
across nine contexts, plus explicitly separate alternative-edition readings.
They establish no explicit contradiction within this purposeful set; they do
not establish agreement across the corpus. [Readings](READINGS.md) and the
[actual review log](PANEL.md) document the evidence boundaries, numerical caveats
and hash-bound acceptance. Public modules are
[analysis](../../dist/channel-lab/analysis.json),
[speech](../../dist/channel-lab/batch-asr.json) and
[readings](../../dist/channel-lab/readings.json). Final publication and browser
receipts remain separate from these completed analysis checks.
