# Bashar-related recordings and the Ra published sessions

This is an exploratory comparison of retained documents, not a test of the
claimed identity or origin of the communicators. “Bashar” and “Ra” are source
context labels. They do not identify the speaker of every utterance, independent
creators, empirical events, or two randomized populations.

## Frozen source frame

The primary comparison contains the **106 numbered Ra sessions** in the
Lawofone.info **Lightly Edited** edition and **19 retained Bashar-related
publisher recordings** with local machine ASR. The latter comprise interviews,
one promotional interview and skeptical commentary; they are not an authenticated
complete archive of channelled Bashar sessions. The source's printed Ra roles
and questions are documentary attribution, not voice/identity verification.

Five complete official Bashar written pages form a separate reference stratum.
Thirty-five downloaded official handout PDFs have partial text/OCR coverage and
are explicitly excluded from the complete-text fits. Their images, diagrams and
relationships cannot be reconstructed from a title or corrupted OCR. Source
collection manifests and dashboard acquisition status remain separate from this
analysis: a retained transcript does not establish surviving audio or video.
New media acquired after the frozen input manifests are not silently added to
these models.

The Ra source explains that editing and original books can reconstruct gaps in
the surviving audio. Thus `coverage_status=full` means the complete selected
published text, not a complete original tape. Dates, edition identifiers,
unresolved original-session identity, source format and attribution limits stay
attached to each record. Historical Ra sessions and contemporary publisher
recordings have inseparable period, genre, editing, speech-production and
recognition differences.

## Reproduction and validation

Run `analyze.py` with repeated `--manifest` arguments and a new private `--output`
directory. The source collectors write a common versioned manifest. Records bind
normalized text and original evidence by absolute private path, byte length and
SHA-256. Normalized text has a source ID and ordered role-labeled turns where
available; it must equal the newline-joined turn texts. Raw text never enters
Git or the public dashboard.

The adapter checks every evidence file, refuses known synthetic inputs during
ordinary execution, validates Ra extraction receipts against original pages and
normalized text, and validates Bashar ASR against completed original receipts,
original audio hashes and unchanged segment text/order/times. Counts are checked
against the upstream receipts. Failed, partial and non-English records are
explicit exclusions. Missing or changed evidence in a purported completed record
stops execution. These checks establish byte/provenance consistency, not human
recognition accuracy.

When a manifest declares `expected_source_ids`, its unique valid ID set must match
the record set. An unavailable expected source therefore requires an explicit
status row; it cannot disappear from a declared complete inventory. The canonical
Ra session set was independently checked as 1 through 106.

Exact repeated source records and exact text aliases are counted once. Conflicting
editions of one session require a separate analysis rather than adding another
observation. Exact media families do not identify re-encoded or excerpted sessions.
Five-token shingle overlap screens near-duplicate candidates without automatically
removing them or declaring syndication. Shared stock phrases, advertisements or
doctrine can also cause overlap.

Only source-level complete session/recording documents enter the primary topic
and cluster models. Turns, question records and embedding chunks are never treated
as independent session observations. Written references are projected into the
primary fitted vocabulary in a separate output; they do not train the primary
model. All original publisher material and ASR remain preserved.

## Lexical measures and controls

The common tokenizer applies Unicode NFKC, changes curly apostrophes to straight
apostrophes, lowercases and matches ASCII letter words with internal apostrophes.
Whitespace counts and these analysis-token counts have separate names. The
English-only analysis does not silently generalize its tokenizer or stoplist to
other languages.

The ten declared word-form groups cover ontology, agency/free will, ethics/polarity,
fear, practices, time/probability, contact, healing/body, knowing/uncertainty and
relationships. Counts are exact forms per 1,000 analysis tokens. Equal-document
means and pooled-token rates expose length weighting. Negated, quoted, hypothetical,
ambiguous and editorial occurrences still count. A polarity word can describe a
magnetic effect rather than an ethical position, and a fear-related word can occur
in a tarot-image question rather than a recommended practice. The independent
reading layer records these actual counterexamples and does not treat the
dictionary as validated annotation.

TF-IDF uses unigrams/bigrams, sublinear TF, smoothed IDF, L2 row normalization,
`min_df=2` for at least five documents (otherwise 1), `max_df=1.0`, and at most
12,000 features. English stop words retain `no`, `not`, `nor`, and `never` at the
stoplist step; feature selection can still affect rare terms, and a cosine score
does not model entailment or contradiction.

The engine fits explicitly different variants:

- Raw vocabulary after the common tokenizer and stoplist.
- A fixed spoken-filler list removed.
- Fixed names and source markers removed in addition to fillers.
- A centered, contiguous 1,500-token window before filler/name removal; shorter
  documents are excluded only from this sensitivity.
- Ra printed responses only, with Bashar mixed-speaker ASR unchanged. This is an
  asymmetric editorial-structure sensitivity, not a comparison of matched voices.
- Bracketed spans removed. This can remove editorial insertions and stage directions
  as well as missing-audio notices; it is not a guarantee of “pure speech.”
- Promotional and skeptical-commentary formats excluded using source metadata.

Joint vocabulary/IDF reflects unequal corpus size. These controls expose selected
dependencies but cannot resolve the differences between an edited historical
session archive and a current publisher sample.

## Topics, clusters and networks

NMF candidates span `k=2..8`, bounded by document/feature dimensions, and seeds
11, 23 and 47. NNDSVDar initialization, 800 maximum iterations and tolerance
`1e-4` are recorded. Hungarian matching of component term vectors measures seed
sensitivity. Reconstruction error, convergence warnings, iterations and component
concentration/effective document count accompany every candidate. Four components
are displayed where available as a declared readability choice; this is not an
optimal or validated topic count. Component weights are normalized decomposition
shares, not topic probabilities or reliability coefficients.

NNDSVDar supplies nearly identical structured starting points across these seeds.
Very high seed agreement under this initialization is a narrow numerical check,
not a broad perturbation or sampling-stability experiment. The actual six-component
candidate reached the 800-iteration limit in all three seeds; that diagnostic is
retained rather than described as a converged optimum.

KMeans uses the same name/source-marker-filtered TF-IDF, ten initializations,
500 maximum iterations and the same candidate counts/seeds. The displayed solution
maximizes seed-11 cosine silhouette; all candidate scores, seed adjusted-Rand
comparisons and singleton counts remain available. Source labels are not used
to fit or select clusters. A stable source-aligned partition can still be an
editing, host, format or vocabulary effect.

Two-dimensional TruncatedSVD is a display of lexical vectors, not a map of
spiritual dimensions. The document graph is the undirected union of each source's
three nearest neighbors at cosine at least 0.15, with threshold counts from
0.10 to 0.50. Circular graph positions are schematic. Edges connect documents;
they do not connect verified beings, societies or physical civilizations.

The source-reading literature notes explain why representative passages are
needed alongside top words, why seed stability is not semantic validity, and why
source-format data statements matter. The project does not claim to have replicated
those papers or obtained human peer review.

## Frozen neural embedding sensitivity

The optional neural layer uses the pinned Apache-2.0
`sentence-transformers/all-MiniLM-L6-v2` revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Four local model/tokenizer/configuration
files are checked against retained exact hashes. This is an established English
baseline, not a claim of state-of-the-art channeling-domain accuracy. No weights
are trained or rewritten. ONNX execution uses two intra-operation CPU threads,
one inter-operation thread and batches of sixteen.

The tokenizer has truncation disabled. Every content wordpiece is processed in
nonoverlapping chunks of at most 240 content tokens, with CLS/SEP and attention-mask
mean pooling. Chunk vectors are L2-normalized. Document vectors use the number of
content wordpieces as weights, followed by L2 normalization. An equal-chunk mean
is calculated from the same inference as a weighting sensitivity. Per-document
chunk counts, processed tokens and zero truncated tokens are reported; a first-512-
token shortcut is not used. Complete model/input/encoder bindings and vector hashes
govern cache reuse; corrupt or incomplete caches are refused.

Cached vectors use float32. Tiny differences from initial in-memory pooling can
occur through storage precision; this is not a new model or repeated training.

Fixed names/source markers are masked as complete apostrophe-aware lexical tokens,
preserving straight and curly contractions such as `don't`, `don’t`, `we'll` and
`we’ll`. Not all genre or identity cues are removed. Pooling
loses ordering between chunks and can obscure disagreement. Cosine from this
model and cosine from TF-IDF have different interpretations and are not interchangeable
scales. They are not probabilities of equivalent beliefs, verified entities or
true predictions.

## Documentary exchanges and question leads

Printed Ra questioner turns are paired with the following same-question-ID printed
response turns. The result is a **documentary prompt/response exchange**, not an
automatically validated substantive question. Acknowledgments and requests to
continue remain labeled prompts. Opening responses without a present questioner,
orphan responses such as 103.3, and bracket-only lost/inaudible questions remain
explicit counts. The full published text is never rewritten to invent a question.

Bashar ASR turns containing `?` produce unverified punctuation candidates. The
following turn is stored only as context; it is not automatically an answer or
attributed to Bashar. The private SQLite database separates documents, turns,
publisher prompt/response pairs and ASR candidates.

Neural prompt retrieval requires a present question text, `?`, and at least eight
analysis tokens in either corpus. Bracket-only placeholders are excluded. All
eligible Ra prompts and their documentary responses, and all eligible Bashar ASR
candidates, receive complete chunk coverage. The nearest cross-corpus prompts are
reading leads with IDs and scores; they are not validated question equivalences or
evidence of matched answers. Ra paired prompt/response similarity is summarized
per session alongside one cyclic shift of response assignments within that session.
That comparison is descriptive, not a null-distribution test or independent sample.

## Outputs, uncertainty and release

`analysis.json` contains metadata, counts, dictionaries, matrices, diagnostics and
source IDs without full source text. PNG, SVG and PDF figures carry captions and
hashes. `provenance-private.json`, `qa-private.json`, the SQLite database, source
text and model/cache files remain private. The output manifest binds every artifact.
The public dashboard must whitelist metadata/results and never copy the private
QA or provenance files wholesale.

No p-values, independent creator-population estimates, empirical ET-origin
probabilities, clinical/physical mechanisms or causal effects are estimated.
Counts describe what was retained and admitted. Audio survival, acquisition
coverage, textual completeness, recognition accuracy, source attribution and
physical truth are separate questions. Every manuscript conclusion must remain
within these observable boundaries.

## Observed frozen run

The final run admitted 130 documents: 125 primary session/recording units and five
written references. Thirty-five partial handouts were excluded; zero exact text
aliases were found. The primary corpus contains 501,300 whitespace words
(278,601 Ra and 222,699 Bashar-related); its tokenizer produces 505,748 analysis
tokens. The separate written references add 1,646 whitespace words.

| Lexical variant | Bashar-related within | Ra within | Across contexts |
| --- | ---: | ---: | ---: |
| Fixed names/source markers removed | 0.3508 | 0.1460 | 0.0929 |
| Centered 1,500-token windows | 0.1620 | 0.1070 | 0.0558 |
| Ra responses only, Bashar ASR unchanged | 0.3605 | 0.1385 | 0.0798 |
| Promotional interview and commentary excluded | 0.3628 | 0.1440 | 0.0924 |

These are descriptive mean pairwise TF-IDF cosines, not agreement probabilities.
Full primary comparisons contain 171 Bashar-related within-context pairs, 5,565
Ra within-context pairs and 2,014 across-context pairs. Those overlapping pairs
are not independent observations. The matched-length variant omits four short
Ra sessions; the format exclusion retains 17 Bashar-related interviews and all
106 Ra sessions. The large length-sensitivity change limits any interpretation of
the initial within-context contrast.

The selected KMeans `k=2` solution has cosine silhouette 0.0929 and partitions the
two source contexts. This low-separation, source-aligned result cannot distinguish
doctrinal differences from transcript editing, genre, recording period, publisher,
speaker structure or ASR. Four displayed NMF components emphasize density and
entities; contemporary reality/passion vocabulary and spoken forms; catalyst and
archetypical mind vocabulary; and pyramid/chamber terminology. These are top-word
descriptions of decompositions, not independently validated concepts.

The corrected frozen MiniLM layer processed every one of 610,730 content wordpieces in
2,611 primary-document chunks. Its weighted-versus-equal-chunk cosine comparison
has mean absolute change 0.0118 and pair-rank Spearman correlation 0.9959. High
rank agreement only addresses this pooling choice. A separate question layer
processes 2,311 eligible printed Ra prompts and their documentary responses,
along with 775 eligible Bashar ASR punctuation candidates; no content is truncated.

The private question database preserves 2,523 printed prompt/response exchanges,
including four missing-question placeholders, and 1,303 ASR punctuation candidates.
There are 107 printed response turns without a present questioner turn and 18
bracket-only turns. Across 106 Ra sessions, the mean of session-mean prompt/response
cosines is 0.3350 versus 0.2068 for one within-session cyclic shift; all session
differences are positive. This is a descriptive documentary-linkage diagnostic,
not a significance test or authentication of the answers. The cross-corpus nearest
prompt results are explicitly unvalidated reading leads.

No pairs passed the declared five-token overlap screening thresholds among 7,750
primary document pairs. That absence does not exclude re-encoded, paraphrased,
excerpted or otherwise latent duplicates. Thirty automated tests and an
independent model-agent review checked the implemented invariants; this is not
human peer review or an empirical transcription-accuracy study.

### Corrected semantic transformation

An independent follow-up review found that the initial word-boundary name mask
matched `don` inside `don't` and `ll` inside `we'll`. Complete chunk processing had
correctly covered that already-altered input, so coverage checks alone did not
catch the transformation defect. The corrected mask operates on whole tokens,
with explicit tests for straight, curly and multiple-apostrophe contractions.

Run04 supersedes the semantic matrices, coverage, retrieval scores and figures
from Run01–Run03. Changed inputs were recomputed using the same frozen model;
unaffected exact-input cache records were reused. Raw source text, lexical
analyses, NMF/clustering, dictionaries and documentary QA eligibility are unchanged.
The correction changes some document cosines by as much as 0.0693, so the old
semantic values must not be relabeled as current. The top four retrieval identities
remain the same; the former sixth lead becomes fifth, changing the top-five set.
Source-reading audits retain their original run bindings and separately record
the corrected-run comparison and newly admitted fifth lead.
