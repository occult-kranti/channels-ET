# Channel Lab: common-frame text analysis

This release analyzes **493 canonical text publications, containing 1,411,446
whitespace-delimited words**, from the retained English-source collection. The
strongest practical result is sensitivity to which part of a document is read:
the publisher-context macro-average top-five neighbor Jaccard is **0.05066**
between the complete MiniLM representation and a centered, bounded text window.
The document-average value is **0.10705**. Similarity results therefore need the
exact edition, text extent and source context beside them.

These are descriptive measurements of retained texts. They do not authenticate
claimed speakers, establish agreement between answers, estimate population
prevalence, or evaluate the truth of channeling claims. The existing studies are
preserved; this is an additive common-frame analysis.

## Frozen frame and units

The source registry admits only bodies that pass their original artifact hash,
selection rule, normalization and word-count checks. The final frame is
`frame-02/frame.json`, SHA-256
`0d69378f9e9a2280e7ed05981b647fbfe280016380b3072b2b3a320961ae2c8c`.
The companion public registry is independently hash-bound by `analysis.json`.
Unicode NFKC normalization and outer whitespace removal define each selected
body; declared source-specific transformations remain in its provenance.

There are **26 publisher/channel contexts** and **14 creator-attribution context
IDs**. These are different grouping variables, and neither is a census of unique
human mediums. Official Bashar material and Bashar guest appearances remain
separate contexts. Thirteen guest publishers do not become thirteen independent
mediums. The Ra context is a session collection; an interview host does not
identify every utterance's speaker. Claimed entities are source attributions.

The source owner reconciled 572 edition rows using known publication URLs,
recording families and exact normalized body matches. Alternate editions and
merge decisions remain visible. This does not detect every repost, paraphrase,
shared teaching or underlying dependence. The canonical choice prefers explicitly
paired OmNa publisher writing over its uncertain ASR edition. New recognition
outputs remain separate alternatives pending the paired sensitivity analysis.

Coverage is very unequal: Tracy contributes 203 publications and Ra 106,
together 309/493. Eleven publishing contexts contain one publication. Dates are
unknown for 110 documents and stay null. Observed retained publications are not
verified total YouTube uploads. Missing historical caption bodies, undiscovered
uploads, ineligible languages and unavailable sources are outside this fit.

Frame 02 corrected 67 missing official-Bashar audio metadata joins. Before cache
reuse, the ordered source IDs, body hashes, row indices, words, selected editions
and mask phrases were checked against frame 01. No selected text changed.

## Lexical representation and identity control

All primary lexical and neural inputs use a position-preserving exact-phrase
mask assembled from the source registry's creator, publisher and claimed-label
phrases. Matched characters become spaces, preserving private character
locators. Whole-phrase boundaries prevent partial-name replacements. This is a
bounded control: unlisted names, aliases, introductions, spelling and style
remain. For example, the fitted factor labels still expose bare `bashar` and
the promotional phrase `new book`; these are retained as observable confounds.

The lexical tokenizer extracts Unicode letter/apostrophe tokens, case-folds
them and normalizes curly apostrophes. Standalone numbers are not lexical terms;
the neural encoder still receives the masked source text, including numbers.
The shared TF-IDF vocabulary contains 24,000 unigrams/bigrams, with minimum
document frequency two, sublinear term frequency, smoothed IDF and document L2
normalization. The English stop list retains `no`, `not`, `nor` and `never`.

Document keywords are the largest weights in this shared fit. Publisher-context
contrast terms subtract the equally weighted mean of the other context means
from the selected context's mean L2-normalized TF-IDF vector. They are
compositional lexical contrasts, not word prevalence or significance tests.
An unmasked lexical fit supplies a separate identity-mask sensitivity.

Zero-feature inputs are explicitly unavailable. They cannot acquire artificial
self-similarity, zero-valued similarity or fabricated neighbors. All 493 actual
primary rows are available, but the missing-representation contract is tested.

## Full-input neural representation and runtime

The unchanged `sentence-transformers/all-MiniLM-L6-v2` baseline is pinned to
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; the model manifest and
encoder code hashes are in the analysis. This is a reproducible small baseline,
not a newly trained model or a claim of state-of-the-art performance.

The ONNX CPU session uses one intra-operation and one inter-operation thread.
Every source is tokenized without truncation, then partitioned into contiguous,
nonoverlapping chunks of at most 240 content wordpieces. Each chunk receives
CLS/SEP. Attention-mask mean pooling, including those special tokens, is L2
normalized. The primary document vector is the normalized mean of chunk vectors
weighted by their content-wordpiece counts. Equal-chunk pooling is a separate
control. Jobs are sorted by content length, with original ordinal tie-breaking,
and padded in batches of eight. Padding is masked.

The executed full pass covered **1,733,285 content wordpieces in 7,463 chunks**
across all 493 bodies, taking **463.90 seconds** in this environment. Bounded
masked and unmasked passes covered 178,445 and 178,790 wordpieces, respectively;
each used 986 chunks and took about 46 seconds. The later numerical/plot stage
reused these exact caches and took 47.90 seconds. These are observed runtimes,
not causal speedup estimates or semantic-accuracy benchmarks. A small batch
profile selected eight; a separate mixed-length padding check matched the
reference chunk encoder exactly.

Caches bind the ordered source IDs and body hashes, model, chunking, pooling,
batching and code. Reuse checks shapes, hashes, finiteness and vector norms.
The current invocation records reuse separately from original inference time.
Every chunk vector and its owner/start/length remain in a private RAM witness.
The independent reviewer reconstructed all pooled vectors without rerunning
neural inference; the maximum difference was 5.55e-17.

## Topics and source-text progression

Eight-factor nonnegative matrix factorization is fit to the shared TF-IDF matrix
with genuine random starts at seeds 11, 23 and 47 and at most 500 iterations.
Eight is a declared exploratory resolution, not an inferred number of doctrines.
The primary seed is 11; labels show leading lexical terms rather than invented
interpretive categories.

NMF has a scale ambiguity: multiplying one factor and dividing its corresponding
document weights preserves the reconstruction. Before comparing mixtures, each
topic-term row is normalized to unit L2 and its document-weight column is scaled
by the original norm. This preserves W×H. Row-normalized document weights and
topic progression use this fixed factor scale. Hungarian matching aligns seeds
by term-vector cosine; dominant-topic adjusted Rand index and mixture changes
then refer to the aligned, scaled factors.

Every body is split into nonoverlapping windows of at most 500 whitespace words,
including the last partial window. The frozen vocabulary and primary NMF
transform produce **3,076** progression rows. Private locators bind exact body
hashes, character spans, span hashes and word ranges. Public rows expose word
ranges and normalized source position. These are **text positions, not audio
timestamps, speaker turns or demonstrated changes in a claimed entity**.

The three fits converged without iteration-limit warnings. Relative to seed 11,
seed 23's mean matched factor cosine is 0.95484 and seed 47's is 0.89788;
dominant-topic ARIs are 0.92358 and 0.86507. However, **one seed-47 factor has
matched cosine only 0.28782**. The average must not be read as every topic being
stable. Reconstruction and numerical stability do not validate the topic labels.

## Comparisons, networks and sensitivity

Pair similarities use the original feature spaces. Cosines are rounded to
Float32 before rankings and summaries, so the lazy binary exports reproduce
tie behavior exactly. Equal scores break ties by canonical source ID. Binary
NaN means an unavailable representation; scalar JSON uses null where needed.

Within-context means use unordered pairs without self-pairs; cross-context
means use all available cross pairs. Each matrix publishes its pair counts.
The following are distinct descriptive summaries:

| Similarity | Equal publisher-context pairs | Equal creator-context pairs | All cross-publisher document pairs |
| --- | ---: | ---: | ---: |
| Lexical | 0.15571 | 0.08652 | 0.06349 |
| Neural | 0.66190 | 0.55573 | 0.52800 |

There are 325 publisher-context pairs, 91 creator-context pairs and 91,278
cross-publisher document pairs. Pairs share observations and are dependent.
These are not independent sample sizes; no pairwise p-values or population
confidence intervals are manufactured from them.

The bounded control takes a centered span of **up to 300 lexical tokens**;
shorter bodies remain intact. Both sides of every neighbor comparison use the
same available-source universe. Thus a missing candidate does not become a
representation effect. Windowing changes both content and length, so it cannot
isolate a causal length effect.

| Top-five neighbor-set comparison | Document mean Jaccard | Publisher-context macro Jaccard |
| --- | ---: | ---: |
| Full lexical versus full neural | 0.23822 | 0.32019 |
| Full versus bounded lexical | 0.12941 | 0.07770 |
| Full versus bounded neural | 0.10705 | **0.05066** |
| Masked versus unmasked lexical | 0.89588 | 0.94230 |
| Masked versus unmasked bounded neural | 0.92980 | 0.96136 |
| Wordpiece-weighted versus equal-chunk neural | 0.83939 | 0.89618 |

All six actual comparisons have 493 eligible sources. The low bounded-window
stability is a substantive limitation of neighborhood interpretation. High
stability under an incomplete exact-name mask does not show identity or style
leakage has been removed. Representation agreement is not answer agreement.

Same-context neighbor fractions are compared with the availability baseline
(context size−1)/(N−1), then macro-averaged across contexts. Creator-context and
text-origin summaries expose alternative confounds. K-means at eight clusters,
seeds 11/23/47 and ten initializations supplies exploratory silhouette and
source/creator/origin ARIs; no cluster is treated as a verified civilization.

Networks report mutual nearest-neighbor k=3/5/10 and cosine thresholds
0.30/0.50/0.70/0.85, with edge, component, isolation and largest-component counts.
The interactive view derives the selected graph from frozen original-space
matrices. Display filtering does not refit the model. A drawing cap limits
rendered edges while retaining a complete selected-edge export. Lexical cosine
at least 0.95 flags possible duplicate review; it causes no automatic merge.

## Shared-label case contrast

Four Mary/Magdalene publications, selected before these new rankings, compare
two same-printed-label cross-creator pairs with two different-label within-creator
pairs. The difference between their **mean** within-creator and cross-creator
cosines is +0.06214 (full lexical), +0.03265 (full neural), +0.03768 (bounded
lexical) and +0.02588 (bounded neural). This is a small, purposive source-style
contrast, not evidence for or against the identity of a claimed being.

The ordering is not universal at the individual-pair level: Natalie's full
neural within-creator pair is 0.46261, below both same-label cross-creator pairs
(0.51282 and 0.56194). The averages cannot erase that variation. Source style,
topic, text extent and edition remain confounded. The separate source-reading
module inspects claim scope and conditions; cosine never assigns contradiction.

## Lexical and contextual-token overlays

The lexical heatmap selects 24 non-name unigrams by equal-publisher-context mean
TF-IDF, requiring document frequency at least three and presence in at least
two contexts. Components of the declared name phrases are excluded. Cells are
mean L2-normalized document TF-IDF weights, not topic prevalence or word vectors.

A separate target-token experiment uses those same 24 terms. For each term and
publisher context, at most two documents are selected by a deterministic hash
of term and canonical source ID. One middle ordinal occurrence per document
is examined in a window extending up to 24 wordpieces on each side. Only the
target's hidden subwords are mean-pooled; neighboring tokens and special tokens
are excluded from that mean. Normalized occurrence vectors are averaged within
publisher context and normalized, then equally averaged across contexts and
normalized for each term prototype.

The executed sample contains **921 document-term pairs** from 7,270 eligible
pairs and **587 publisher-context/term means**. The maximum model input is 53
wordpieces including special tokens. Private evidence retains exact original
and masked spans, token indices, target bounds and input hashes. Public data
contain terms, source IDs, counts, coordinates and term cosines, without quotes.

One PCA fitted to the 24 term prototypes transforms every context mean into the
same display space. The first two components explain 22.77% of variance and
trustworthiness at five neighbors is 0.83438. A normalized prototype need not
sit at the arithmetic mean of its displayed context points. These sentence-
trained hidden states are exploratory; they are not validated word senses or a
learned civilization ontology. Spelling, grammar and publisher style can dominate
proximity. The bounded sample does not represent every occurrence of a term.

## Figures, publication and validation

Document maps use independently fitted lexical TruncatedSVD and neural PCA,
centered and scaled to unit RMS display radius. Their axes are not aligned
latent dimensions. The two-dimensional lexical view explains only **4.10%**
of variance, with trustworthiness@5 0.79156; the neural view explains **19.09%**,
with trustworthiness@5 0.76180. Compare sources in the full matrices, not by
visual map distance. Static colors distinguish broad source groups imperfectly;
the interactive inspector and filters resolve individual identities.

Five plot families are exported as PNG, SVG and PDF: source coverage, factor
mixtures, document maps, neighbor sensitivity, and the two distinct term views.
Each actual PNG was inspected for labels, scales and clipping. Public output is
an explicit 7,580,383-byte allowlist: analysis JSON, two Float32 matrices, 493
document-detail files and 15 figure files. It contains no full source bodies,
private filesystem paths or hidden-state vectors. The accepted analysis SHA-256
is `59f08dddc1b72bc3ed9b70c41f515a91a5e6bdb3ad427a9a0048deb62390635a`.

The stdlib release gate checks source order and registry hash, all document and
word counts, exact detail/artifact hashes, 486,098 binary matrix cells, symmetry,
availability, topic mixture sums, progression coverage, group means/pair counts,
neighbors, graph accounting and figure hashes. Six focused tests cover zero
features, shared comparison universes, offset-preserving masking, NMF scale
ambiguity, deterministic ties/singletons and unavailable graph nodes. A seventh
test verifies portable witness conversion preserves the original bytes and
numerical values, loads without pickle, and refuses to overwrite an edition.

Independent arithmetic review refit lexical counts and manually recomputed
log-TF/IDF/L2, checked 5,916 ranking rows, 2,704 group cells, all three NMF
factorizations/alignment/mixtures and both document projections. Maximum observed
difference was 2.84e-14. Neural arithmetic was verified from the executed chunk
witness rather than by a second inference run. Independent contextual review
also rebuilt all 24 term selections, 921 occurrence/window bindings, 587 context
means, term prototypes, cosines and shared projection arithmetic; 208 distinct
sources contribute to that bounded sample. Graph and qualitative-case audits
have separate receipts recorded by the release integrator. These are AI-agent
reviews, not human peer review.

Private RAM witnesses retain vectors, sparse matrices, factors, locators and
execution receipts while the environment exists. A portable witness edition
changes only the feature-name array from object dtype to Unicode, allowing
`numpy.load(..., allow_pickle=False)`; every array value is unchanged, both
versions are retained, and a receipt binds their hashes. The public artifacts
are the durable release; ephemeral RAM is not promised as permanent storage.

## Reproduction

From the repository, with the verified private source frame and pinned model
available:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /workspace/channels-et-analysis-venv/bin/python research/channel-lab/analyze_corpus.py \
  --frame /workspace/channels-et-private/channel-lab-2026-11/frame-02/frame.json \
  --model /workspace/channels-et-private/bashar-ra-2026-11/model-cache/minilm-1110a243 \
  --output /dev/shm/channel-lab-2026-11/analysis/new-immutable-run
```

Use a new output directory. The numerical cache is reusable only after its exact
input/code/model contract passes. The producer's generic legacy encoder import
can interact with other research modules' names; run its targeted tests in an
isolated process for this frozen release. The lightweight public verifier does
not import NumPy, scikit-learn or the encoder:

```sh
python research/channel-lab/verify_analysis.py --public-dir PATH_TO_PUBLIC_RELEASE
```

For a subsequent run, `analyze_witness.py --trusted-source PRIVATE_WITNESS
--destination NEW_PRIVATE_WITNESS --analysis-sha256 ANALYSIS_HASH` creates the
portable witness without changing the producer or its scientific output. It
accepts only trusted local producer files because the original feature-name
array requires pickle-aware loading; downstream readers use the portable
edition with `allow_pickle=False`.

Public verification cannot re-encode texts it does not distribute. Independent
fit reproduction requires access to the privately retained source artifacts.
No model weights were edited, no recognition accuracy ground truth was created,
and no browser filter constitutes a new experiment.
