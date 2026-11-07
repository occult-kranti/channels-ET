# Receipt-bound analysis of the acquired recording batch

`analyze.py` reads completed **machine ASR** records from explicitly supplied
`audio-run.json` files. It performs no acquisition, inference, upload or speaker
assignment. Raw text and analysis outputs must stay in a private directory
outside Git. The separately retained publisher PDFs are useful references but
are not added as independent recordings or interchangeable ASR versions.

## Inputs and provenance

```sh
/workspace/channels-et-analysis-venv/bin/python research/batch-media/analyze.py \
  --run /private/pilot/audio-run.json \
  --run /private/second-recording/audio-run.json \
  --output /private/new-analysis
```

Repeat `--run` for each known completed batch manifest. The command does not
recursively sweep unrelated directories or assume every running output is done.
A new empty output directory is required; existing evidence is never overwritten.
A failed or metrics-only record is explicitly excluded rather than counted as a
transcript. Integrity failure in a purported completed record stops the analysis.

The adapter verifies the run-listed receipt hash, processing-binding hash,
original acquisition-proof hash, exact source/provider identity, original media
bytes, and every artifact listed by the completed receipt. A single recognized
`segments.json` must have the same source ID, exact joined text, segment count,
whitespace-word count and bounded ordered timestamps as the receipt. A retained
`audio-metrics.json` must match its receipt summary. These are provenance and
consistency checks, not a fresh independent listening test or an authentication
of a claimed entity. Synthetic fixtures are rejected by normal CLI execution;
unit tests expose their own explicitly synthetic in-process mode. A positive
fixture marker anywhere in the retained run, receipt, source or acquisition
proof remains synthetic even if a later source wrapper omits that marker.

Duplicate source IDs with identical media/transcript hashes are counted once.
Conflicting versions under one source ID require explicit resolution. Different
source IDs with byte-identical original media are aliases and also count once.
Different encodings or excerpts can still duplicate a performance; their
original-session identity remains unresolved. Exact transcript-text hashes from
different media are flagged, not automatically merged into one performance.
This separate content hash excludes the source ID and other JSON wrapper fields.

The upstream audio script hash and model-file digest remain attached to each
record. The first creator-video pilot used the earlier exact audio script before
a subsequent input-language/provenance guard correction. Its original receipt
is preserved; later source-bound validation does not retroactively change which
code performed that inference. Different processing signatures are not hidden.
Reported timestamp-repair policy, anomaly and repair counts, maximum adjustment,
text-change flag and terminal-alignment warning are retained per recording in
private and public summaries. Absent fields remain “not reported,” not zero
anomalies. A clipped terminal timestamp does not validate its recognized words.
Reported ASR-execution and repair/helper code hashes must match both the processing
binding and retained verified artifacts, and remain in the public quality block.
The explicit repaired-machine transcript label is admitted only with its known
bound clipping policy and retained execution/repair/helper code evidence. Its
full qualification remains attached; publisher-reference text is not admitted.

## Descriptive quantities

The main table reports original/decoded duration, ASR whitespace words, Unicode
regex-token count, declared and model-reported language, audio measurements and
source hashes. These word definitions have different denominators. The regex
matches letter sequences with internal apostrophes; it is not a linguistically
validated segmentation method for every script.

Ten exploratory English word-form dictionaries cover freedom, enlightenment,
energy, fear, choice, consciousness, relationships, body, religion and metaphysics.
Their complete exact forms are exported in `analysis.json`. Counts use
case-folded tokens and are normalized per 1,000 regex tokens. They include
negated, quoted, hypothetical and rhetorical uses. For example, the word “love”
does not prove that the passage is about an interpersonal relationship. The
codebook was chosen for exploratory inspection of the present collection, not
preregistered or externally validated topic measurement.

Known non-English, conflicting/invalid declared-language records, or ASR that
does not report English are excluded from the English dictionary and lexical
fits, while their source metadata remain in the recording inventory. A model
estimate or an explicit English assumption on missing source metadata stays
labelled; it is not human language validation. English stop words and token rules
must not silently stand in for multilingual analysis.

Every segment containing a question mark produces a private **punctuation
question candidate** with its time range and following segment as context. The
following segment is never automatically called an answer. Rhetorical questions,
audience dialogue and ASR punctuation errors remain unclassified; speaker and
human adjudication fields remain unknown/false. These outputs are not a verified
Q&A database.

## Lexical comparisons and sensitivity

With at least two English-eligible documents, the program fits word-unigram and
bigram TF-IDF with English stop words, sublinear term frequency, L2 normalization,
`min_df=1` and at most 10,000 features. All selected documents receive terms and
a complete cosine matrix. It separately fits a fixed proper-name-masked version,
removing exact forms of Adamus, Shaumbra, Geoffrey, Hoppe, Linda, Saint, Germain,
Crimson and Circle, preserving all other text characters. ASR spelling variants
are not silently corrected. This is a
sensitivity check, not a control for genre, shared publisher, recurring audience,
recording order or other confounders. Floating-point overshoot is clipped to the
mathematical [0,1] interval of these nonnegative normalized vectors.

A separately labelled **synthetic method diagnostic**, outside the source corpus,
compares “aliens exist” and “aliens do not exist.” This preprocessing can yield
cosine one for those opposite statements. Similarity therefore cannot be read as
agreement, truth, a psychological trait, evidence of ET origin or a forecasting
probability.

At least four distinct English document vectors and sufficient vocabulary are
required for exploratory NMF. Its component count is bounded by
`min(3, documents−1, features−1)`, initialization is NNDSVDa, random seed 42 and
maximum iterations 1,000. Component terms, document weights, reconstruction error
and convergence warnings are retained. There is no search for a favorable topic
count, no significance claim, and no assertion that components are validated
belief categories. Repeated identical text does not manufacture four topics.

The first working batch is one creator's selected course recordings. Multiple
recordings, question candidates or word pairs are not multiple independent
mediums. No empirical p-values, confidence intervals, human ASR-accuracy score
or cross-medium validation is supplied.

## Outputs and bounds

- `analysis.json`: source-linked numerical summaries, full dictionaries,
  comparisons, methodological controls and limitations; no transcript bodies.
- `recordings.csv`, `keyword-counts.csv`, and available similarity matrices:
  machine-readable derived tables. Text that could start a spreadsheet formula
  is escaped; source JSON retains the original descriptive value.
- `question-candidates-private.json`: excerpts and following context; private.
- `provenance-private.json`: private input locations and hashes; private.
- PNG/SVG figures: recording duration/text volume, dictionary rates, and available
  raw/masked cosine matrices. For more than 40 recordings, figures are skipped
  with an explicit reason while full tables remain available.
- `output-manifest.json`: output file sizes/hashes and the analysis code hash.

An optional explicit `--public-output /absolute/new/public-directory` writes a
separate allowlisted aggregate JSON, selected figures and release manifest for
review. Projection must exactly match the retained private JSON; the JSON and
every copied figure must match its private output-manifest hash and size, and
copied figure bytes are rechecked. It never copies question excerpts, transcript bodies, private input
locations or source-context free text. Source-page metadata, numerical tables,
short TF-IDF/NMF terms and provenance hashes are retained. Synthetic analyses
cannot be projected as actual study results. This prepares static files only;
it does not push, upload or deploy them. All original private outputs remain.

Inputs are bounded to 2,000 records, 20 million cumulative admitted text
characters, 4 MiB run manifests, 2 MiB processing receipts, 4 MiB acquisition
proofs and 64 MiB segment documents. The program fails explicitly at a bound
rather than silently truncating. These operational bounds do not establish
population coverage.

## Verification and actual execution

The 36 local tests use synthetic, explicitly labelled receipt/media fixtures.
They cover changed media, transcripts, proofs and processing bindings; source
identity; exact-file aliases; language exclusions; single-document abstention;
keyword denominators; questions without invented answers; negation failure;
distinct versus repeated document fits; symlink handling; CSV formula escaping;
and preservation of incomplete-record status. They do not validate source truth
or recognition accuracy.

A separate actual one-recording pilot analyzed the newly downloaded 2012
“Call to Freedom” video: 7,619.456 decoded seconds, 14,183 ASR whitespace words,
and 183 punctuation-question candidates. It correctly produced no pairwise or
NMF fit. Its private output is an engineering/measurement diagnostic, not a
completed ten-recording study. The final batch results are generated only from
its eventual complete input receipts and retain their own timestamps and hashes.

The subsequent complete run admitted all ten publisher-video recordings dated
2012-10-06 through 2013-08-03, from one creator/course context. It retained
71,704.2773 decoded seconds, 18,760 ASR segments, 133,080 whitespace words and
1,540 unverified punctuation-question candidates; no verified Q&A pairs were
created. There were no exact-file aliases, conflicting versions or identical
transcript-text hashes in this batch. Source 06 retains an explicit 7.3647-second
terminal endpoint correction with unchanged recognized text and an unverified
terminal-alignment warning.

Across the 45 dependent recording pairs, raw TF-IDF cosine averaged 0.2606
(range 0.2208–0.2996). The fixed-name mask averaged 0.2594, with a maximum absolute
pair change of 0.00237. The narrow mask therefore has little numerical effect in
this particular fit; it does not remove shared creator, course, audience or ASR
confounding. The three-component NMF fits converged, but the leading component
contains conversational forms such as “going,” “just” and “really.” These are
exploratory lexical components rather than validated substantive topic labels.

The complete dictionary counted 766 energy-group forms, 716 body-group forms and
646 freedom-group forms among 133,050 regex tokens (5.757, 5.381 and 4.855 per
1,000 tokens respectively). Those are dictionary mentions, including possible
negation and ASR errors, not the percentage of a recording devoted to a topic.
The reviewed public projection and three figure pairs are in
[`public/quantitative/`](public/quantitative/); full candidate excerpts remain
private. No comparison across independently sampled mediums or evidence about
ET origin follows from these results.
