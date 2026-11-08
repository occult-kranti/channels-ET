# Knowledge-bank representation and comparison methods

This additive study compares retained text editions and the consequences of
representing them in different ways. It does not authenticate a claimed speaker,
train a language model, or replace the accepted earlier fits. Source reading and
the question/card database are separate layers: a high cosine is never converted
into an agreement or contradiction label.

## Fixed source frame

The frozen frame combines the earlier 20 publisher-written messages with the five
Council-study editions, after checking normalized body hashes and any declared
publication families. There are **25 distinct editions, 47,280 whitespace words,
six canonical medium contexts, 13 comparison labels and 17 exact printed labels**.
No exact body or declared publication-family alias was excluded. All text was
already retained; these are not 25 new acquisitions or independent observations
beyond the older studies. The separate 228-unit publisher fit is not merged into
this experiment.

The exact frame is SHA-256
`95131882eaed23b9429d3beb6cdffcda3fa62b32569d36412cd013c206008aae`.
`knowledge_sources.py` checks each artifact's byte count and SHA-256, applies
Unicode NFKC and strips outer whitespace, then rechecks the frozen body hash and
word count. Character locators in the card bank refer to this normalized body.
Daniel Scranton's two inherited IDs map to the same named author; Pamela Aaralyn
and Pamela Rose Kribbe remain different people. Source metadata, not lexical
similarity, supplies these explicit identity mappings.

Four machine transcripts retain unknown utterance roles and unmeasured recognition
accuracy. The long Pamela Aaralyn interview includes Council discussion, future-human
questions, host speech and promotions. The Daniel Council text is an Arcturian
message discussing a proposed Galactic Council, not a Galactic Council speech.
The remaining publisher messages are separate editorial editions. None is a
verified audio reference for computing word error rate.

## Representations and controls

The main transformation masks complete medium-name and printed-label phrases,
longest first, with whitespace/hyphen matching. It does not remove every token
such as *contact*, *council* or *light*. Apostrophes and negation remain intact.
Unlisted aliases, shortened names and inflections remain: the term overlay visibly
retains some identity-related vocabulary. This is an exact-phrase control, not
proof that all source-label leakage has been removed.

The lexical model uses Unicode letter/apostrophe tokens, unigrams/bigrams,
sublinear term frequency, smoothed inverse document frequency and L2 document
normalization. `min_df=1`, `max_features=12000`; the English stop list retains
`no`, `not`, `nor` and `never`. It fits a new vocabulary/IDF on the 25 masked texts.
The unmasked sensitivity model fits separately on the same complete bodies.
Standalone numerals are not lexical features under this tokenizer, whereas the
neural tokenizer can retain them. Dates, quantities and time-qualified claims
therefore require their source passages; neither representation's cosine is a
test of agreement about a predicted date or numerical assertion.

The neural baseline is the already cached
`sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, with every model file checked against its
pinned manifest. It is a lightweight reproducible baseline, **not a claim of
current embedding SOTA**. The ONNX session uses one intra-operation and one
inter-operation thread. No weights are updated.

All input content wordpieces are encoded in nonoverlapping chunks of at most 240,
with CLS/SEP added explicitly. Token vectors are averaged over the attention mask,
including those special tokens; each chunk vector is L2 normalized. Document
vectors are content-wordpiece-weighted means of chunk vectors, then L2 normalized.
An equal-chunk mean is retained as a pooling sensitivity. There is no truncation,
disk embedding cache or silently omitted tail. Arrays remain in process memory;
compact public results and private provenance are saved separately.

Centered spans contain exactly 300 Unicode analysis tokens before phrase masking.
All 25 editions qualify. These spans use the whole-text lexical vocabulary and IDF;
the neural model uses its unchanged tokenizer and weights. Centered passages are
not random samples: differences confound length with the local content selected.
The unmasked neural run measures complete-phrase masking sensitivity on unchanged
full bodies.

## Similarities, neighbors and source confounding

All **300 distinct unordered pairs** remain available. Pair strata distinguish
same medium versus different medium and same comparison label versus other label.
The 13 cross-medium shared-label pairs include broad civilization comparisons as
well as named-personality comparisons; their source-specific labels and comparison
levels remain inspectable. Neither broad labels nor identical names authenticate
the same speaker or independent origin.

Nearest neighbors exclude the source itself and use descending full-space cosine,
breaking exact ties by source ID. The top-five set overlap is Jaccard similarity.
The executed results are:

| Diagnostic | Observed value | Interpretation limit |
| --- | ---: | --- |
| Lexical versus neural pair-rank Spearman | 0.54160 | Correlation of 300 dependent representation scores, not answer accuracy |
| Mean lexical versus neural top-five Jaccard | 0.34048 | Retrieval neighborhoods differ materially between representations |
| Mean neural whole-text versus centered-span Jaccard | 0.55048 | Selected passage and length affect neighbors |
| Mean lexical whole-text versus centered-span Jaccard | 0.40302 | Same sensitivity, with fixed full-fit vocabulary/IDF |
| Mean masked versus unmasked neural Jaccard | 0.89714 | Listed phrase masking changes some neighbors; residual aliases remain |
| Mean masked versus unmasked lexical Jaccard | 0.92381 | Same source-name control in the lexical representation |
| Maximum weighted versus equal-chunk pair change | 0.09348 | Pooling can alter a cosine even with complete chunk coverage |

Same-medium/different-label pairs have mean neural cosine **0.60864** (53 pairs),
versus **0.52137** for cross-medium/shared-comparison-label pairs (13 pairs).
That is a descriptive source/style pattern in this chosen frame, not a test of
entity identity, doctrinal agreement or a causal medium effect. The 222 other
cross-medium pairs average 0.54481; the 12 same-medium/shared-label pairs average
0.64274. Pair dependence and unequal source contexts prohibit treating these as
300 independent measurements. No p-values or population confidence intervals are
reported.

Three NMF factors and three KMeans clusters are fixed exploratory display choices,
not optimized doctrine counts. KMeans uses `n_init=10` and seeds 11, 23 and 47.
Cosine silhouettes and adjusted Rand indices against medium, text origin and
comparison label expose confounding and seed sensitivity. Lexical silhouettes
are only **0.03559–0.03679**. Neural silhouettes are **0.14480–0.18679**, with
between-seed adjusted Rand agreement **0.42292–0.95330**. These results do not
support stable, validated entity or doctrine classes.

## Maps and lexical overlays

The lexical map uses two uncentered TruncatedSVD components; the neural map uses
two centered PCA components. Each displayed coordinate set is centered and scaled
to RMS radius one. Orthogonal Procrustes rotates or reflects the neural display
toward the lexical display. It changes orientation only: it does not align latent
meanings or make the two spaces interchangeable.

The two-component variance shares are **6.30% lexical** and **26.52% neural**.
Neighborhood trustworthiness at five neighbors is **0.80094** and **0.84518**,
respectively. The alignment RMS residual is 0.90658. Maps are therefore explicitly
lossy; the full-space matrices support retrieval. Number labels use deterministic
offsets without moving any source coordinate. The portable figure includes its
25-edition source key, variance and trustworthiness diagnostics.

The source/term overlay uses mean L2-normalized TF-IDF weights per medium, giving
each document in that medium equal weight. Displayed terms are the union of the
six highest mean-weight features per medium, capped at 30 in a declared order.
This is a lexical feature-vector overlay, not newly trained neural word embeddings
or a validated test of unique vocabulary. Unequal medium sample sizes, interview
framing and surviving name variants remain visible.

Five figure families are exported as SVG, PNG and PDF: source maps, lexical/neural
pair scatter, neighbor stability, source/term heatmap and source/label contrasts.
The visual refinement adds a portable key and explanatory prose without changing
any document, vector score, coordinate, cluster or numerical result.

## Negation stress case and answer comparisons

Five explicitly constructed statements form a separate synthetic control. They
are not corpus documents, source evidence or an accuracy benchmark. The direct
negation pair “Contact will happen this year” / “Contact will not happen this year”
has neural cosine **0.82995**; the approximate paraphrase scores **0.54204**, and
the condition-changing version scores **0.78684**. This single illustrative case
shows why high cosine cannot itself establish common answers or contradictions.

The question/card bank instead requires bounded source reading, exact supporting
spans and explicit relation labels. A contradiction needs the same proposition,
referent, conditions and time with incompatible assertions. Different emphasis,
private versus physical contact, or a conditional forecast is not automatically a
contradiction. Analyst questions, paraphrased printed questions and unknown ASR
speakers remain distinct. See [the database schema](KNOWLEDGE-SCHEMA.md).

## Consolidation and connections to other fields

The separately executed root retrieval experiment compares raw source chunks,
answer cards, qualified cards and a fixed hybrid. Its independently authored
queries were frozen before card/ranking inspection, but were informed by source
reading. Known-support retrieval is a diagnostic, not blind human accuracy;
unjudged retrieved sources are not automatically irrelevant. Curated card coverage,
chunk multiplicity, source length and paraphrase vocabulary confound comparisons.
Question text and answer-key IDs must not be embedded into the answer cards.

The Google paper is a source for a **comparison of ideas**, not a claim that this
index implements its parameter-training procedure. The literature register
distinguishes actual weight updates, memory consolidation and synthetic-dream
training from the source-bound card/index experiment implemented here.

Useful cross-field connections are methodological rather than evidence of a
physical channeling mechanism:

- **Measurement error:** stronger ASR is a new measurement edition. Recognition
  changes should be traced into names, negation, conditions, retrieval and topic
  stability while holding audio input fixed; inter-model disagreement is not WER.
- **Information retrieval:** source-family grouping and query freezing reduce
  leakage. Ranking agreement measures representation stability, not truth.
- **Oral history and discourse analysis:** attribution, editorial boundaries,
  introductions, interviewer questions and speaker uncertainty change what a
  passage can support.
- **Lossy compression and memory consolidation:** a shorter card can preserve a
  proposition while losing its conditions, date or minority view. Those fields
  remain source-bound and must be audited separately from retrieval scores.
- **Scientific provenance:** a graph edge can mean “supports this paraphrase,”
  “discusses this label,” or “resembles this topic.” Typed edges prevent these
  relations from becoming unsupported identity or causal claims.

## Reproduction and release checks

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/channels-et-analysis-venv/bin/python \
  research/knowledge-bank/analyze.py \
  --frame /workspace/channels-et-private/knowledge-bank-2026-11/knowledge/frame-01.json \
  --model /workspace/channels-et-private/bashar-ra-2026-11/model-cache/minilm-1110a243 \
  --output /workspace/channels-et-private/knowledge-bank-2026-11/analysis/FRESH-RUN

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/channels-et-analysis-venv/bin/python \
  research/knowledge-bank/analyze_refine.py \
  --parent /workspace/channels-et-private/knowledge-bank-2026-11/analysis/FRESH-RUN \
  --output /workspace/channels-et-private/knowledge-bank-2026-11/analysis/FRESH-RELEASE

/workspace/channels-et-analysis-venv/bin/python -m unittest discover \
  -s research/knowledge-bank -p test_analysis.py
python3 research/knowledge-bank/verify_analysis.py --public-dir /path/to/analysis-and-figures
```

The nine focused tests check negation-preserving phrase masking, numbered labels,
span selection, stable nearest neighbors, pair categories, projection normalization,
complete unequal-chunk pooling, invalid inputs and model tampering. The stdlib
verifier independently recounts public units, pairs, matrices, nearest neighbors,
Jaccards, coverage, cluster joins and all 15 figure hashes. Structural checks do
not replace independent source reading or numerical refitting.

The numerical parent analysis is SHA-256
`b14021aa3a84b6a0769f09dbd2774a094c94532a932cb200ceaaadf6c740dcc5`.
The refined release, including figure-label spacing cleanup, is SHA-256
`e1407aa84f8eb33375f15647a5635daae0e75b55c365e7771e3ab0b728e818df`.
The invariant source/numerical projection is SHA-256
`9c42d6484029f2f65f8c24d64c454a74865fbc7df52e0351dfe5debcdbaae822`.
Original outputs and executed code remain privately retained; public Git/Pages
receive code, metadata, bounded paraphrases and derived plots, not full source text.

An independent methods implementation also reconstructed the separate retrieval
experiment's 25 source bodies, 276 raw chunks, 25 cards and four frozen queries.
It used manual logarithmic TF and smoothed IDF from term counts, fresh inference
through the shared pinned MiniLM encoder, and independently implemented source
aggregation, ranking, RRF, metrics and 199 source-label shuffles. All 32 original
rankings matched, with maximum score error `2.220446049250313e-16` for each
representation. The private review is `review/retrieval-methods-independent.json`.
After an unrelated review overwrote its original receipt filename, this summary
was reconstructed from the retained successful execution log and hash-pinned
inputs; it does not claim byte identity with the lost receipt. A separately named
run-02 review checks unchanged original numerical rows and the explicitly
post-hoc top-five RRF arm.

## Separate contextual-token exploration

`contextual_terms.py` adds the literal token-vector view without changing the
document fit or relabeling the lexical heatmap. From the same fixed TF-IDF matrix,
it selects the 24 highest mean-weight unigrams with document frequency at least
three, excluding every component token of listed medium and printed-label names.
Ties use alphabetical order. Negation remains eligible; `not` and `no` were
selected. The eligible pool contains 806 terms.

An exact-name mask replaces matching characters with spaces of the same length,
preserving original normalized source coordinates. At each source/term pair,
occurrences at the floor first-third and ceiling second-third ordinal indices are
selected, or the sole occurrence if only one exists. This samples 711 occurrences
from 2,290 available occurrences across 409 source/term pairs. Each input contains
the target's wordpieces, up to 24 preceding and 24 following wordpieces, and the
model's special tokens. Mean pooling uses only the final-layer hidden states of
target subwords, excluding special and neighboring tokens. Occurrence vectors are
normalized, averaged equally within source and normalized again; source vectors
are averaged equally within term and normalized. Longer sources therefore do not
receive a weight proportional to all their occurrences. Exact source body hashes,
original character spans, token ranges, input-token hashes and sampling counts
remain in the private locator manifest.

A single PCA is fitted to the 24 term centroids and transforms all 409 source
means. Both layers use the same centering and RMS-radius scaling; these coordinates
are not aligned to the earlier document projections. The first two components
explain **23.16%** of centroid variance, with trustworthiness at five neighbors
**0.8646**. The portable figure overlays source means for the first four
rule-selected terms (`not`, `time`, `energy`, `feel`), while the dashboard can
select any of the 24. KMeans with fixed three clusters and seeds 11, 23 and 47
has cosine silhouettes **0.1402–0.1517** and between-seed adjusted Rand indices
**0.5524–0.7693**. These are unstable exploratory categories, not validated senses,
doctrines or civilizations.

The normalized term mean is a directional prototype. Renormalization precedes
PCA, so its plotted position need not equal the arithmetic center of the plotted
source points; the shared transform does not remove that distinction.

The largest term-pair cosine is `energy`/`energies` (**0.8674**), followed by
`simply`/`just` (**0.7785**) and `not`/`no` (**0.7452**). Morphology and common
linguistic usage therefore provide immediate competing explanations for the
nearest-term structure; these pairs do not establish shared channeled teachings.

The encoder was trained for sentence embeddings. Extracting contextual token
states from it is an exploratory use, not a claim of validated word-sense quality
or a newly trained word model. Spelling, grammar, local context and source style
remain encoded. Two deterministic samples cannot exhaust a term's senses, and
source coverage differs by term. Equal source weights do not balance mediums.
Neither token cosine nor a plotted cluster establishes answer agreement or
contradiction. Source-reading cards remain the separate evidence layer.

Four tests cover character-preserving masking, two-occurrence sampling, subword
target offsets and clipped boundary windows. The public verifier checks all
source joins, selected-term document frequencies, occurrence counts, normalized
coordinates, matrices, cluster silhouettes and three figure hashes. Private vector
witnesses retain all 711 occurrence, 409 source and 24 term vectors for independent
arithmetic review; every executed vector is finite and unit-normalized. This
review is distinguished from independent neural re-encoding.
The independent review reconstructed manual log-TF/IDF selection, all 711 exact
source/token locators and ordinal choices, source/term pooling, the shared PCA
and cosine matrix. It also confirmed the final figure-only edition preserves
all numerical fields. Its receipt is `review/contextual-independent.json`.

The final contextual-token JSON is SHA-256
`5d3d509f6a50927019eedf936170a7df8bfe5bc5dff5874b015d211581c6327e`.
Its figure-only refinement changes label offsets, preserving the source/numerical
projection SHA-256
`b67ca2b827bf155a00cc50f77e2be02ff632d3911eac902c35545fa7a5f2e80a`.
`verify_contextual_terms.py --public-dir <directory>` checks a directory containing
this JSON, the accepted `analysis.json` and the three figure files. Run inputs and
the first numerical edition remain retained privately.

## Paired full-recording ASR sensitivity

`asr_sensitivity.py` separately compares the four retained Council recordings'
older Whisper editions against completed Parakeet TDT v3 editions. This is a
recognition-pipeline comparison: the older VAD/context handling and the new
independent, nonoverlapping windows of at most 30 seconds differ along with the
model. All four retained Opus hashes and canonical 16 kHz mono signed-16-bit PCM
hashes/sample counts match the original decoder receipts. New model inputs are
the same canonical samples converted to float32 by division by 32768. The
analysis admits only the completed four-recording manifest and checks every
prepared/raw/normalized chunk join, including final partial tails. Complete
sample coverage does not establish complete or accurate linguistic recognition.

The new run covers **171,833,236 samples**, **359 windows** and
**10,739.57725 seconds** (178.99 minutes). Old recognized words total **25,964**;
new recognized words total **26,319**. The primary 25-edition, 47,280-word analysis
remains unchanged. A counterfactual index replacing only the four ASR rows would
contain **47,635** words. It is a sensitivity calculation, not an adopted new
corpus edition. The lexical vocabulary, IDF and exact-name mask are frozen from
the accepted baseline; new words transform into that existing feature space.
MiniLM uses exactly the accepted pinned model and full-chunk pooling contract.

| Recording | Old / new words | Normalized token disagreement | Paired TF-IDF | Paired MiniLM |
| --- | ---: | ---: | ---: | ---: |
| Tracy: Timeline of Contact & Disclosure | 2,932 / 2,939 | 3.54% | 0.9678 | 0.9867 |
| Tracy: First Contact Is Here | 3,440 / 3,449 | 4.19% | 0.9660 | 0.9863 |
| Tracy: September Energy Update | 2,661 / 2,666 | 4.04% | 0.9652 | 0.9877 |
| Pamela Aaralyn: mixed interview | 16,931 / 17,265 | 9.25% | 0.9474 | 0.9915 |

Token disagreement is exact unit-cost Levenshtein distance after Unicode
normalization/case folding and word tokenization retaining numbers and
apostrophes, divided by the longer token sequence. Both sides are machine
outputs; this is neither word error rate against a human reference nor measured
recognition accuracy. The mixed interview's 9.25% token disagreement alongside
0.9915 neural cosine demonstrates that a high document cosine can conceal
substantial wording changes. This does not identify which wording is correct.

Mean paired cosines are **0.9616** for TF-IDF and **0.9880** for MiniLM. Across all
25 query sources, old/new top-five neighbor-set Jaccard averages are **0.9600**
and **0.8933**, respectively. Unchanged sources can acquire different neighbors
when four candidate vectors change; all 21-by-21 unchanged-source similarities
remain fixed. These descriptive changes are not significant probabilities or an
accuracy improvement. Existing source annotations remain bound to their original
hashes and locators. **Nine cards** touch the four older ASR editions and are
flagged for independent rereading before any transfer; **zero cards** are
automatically rewritten.

Eleven targeted tests cover exact token-edit arithmetic against independent
dynamic programming, retained negation/numbers, complete partial tails, missing
samples, gaps, duplicate recordings, different canonical PCM, changed raw-window
inputs, artifact tampering, incomplete manifests and empty recognition. The
public verifier checks source/card joins, count and matrix arithmetic, unchanged
source pairs, all neighbor rankings, summary values and three figure hashes.
Old and counterfactual pooled vectors are retained in a private RAM witness for
independent arithmetic review; this is distinguished from a second neural
re-encoding.
The independent reviewer reconstructed the frozen lexical fit and both neural
matrices from the saved vector witness, checked 100 neighbor lists and all nine
card flags, and independently computed all four exact token-edit distances with
a separately compiled scalar dynamic-programming implementation. Distances
were 104, 145, 108 and 1,602 tokens in the table's source order. Its receipt is
`review/asr-sensitivity-independent.json`.

The completed full-ASR manifest SHA-256 is
`3991b8649962b5223993479cd6e70dc9c09b81983d61bb21f770ca4b21429e68`.
The separate sensitivity JSON SHA-256 is
`02aacfb8ceef15df14226c16df587799f1a1e5e0dcb55c53e858b46905db113a`.
`verify_asr_sensitivity.py --public-dir <directory>` expects the sensitivity
JSON, unchanged `analysis.json`, unchanged `knowledge.json` and its three figure
files. New source text and audio stay private; public output contains derived
measurements and provenance hashes.
