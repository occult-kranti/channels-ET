# Source-bound transcript analysis

This executed analysis uses **20 complete publisher-audio ASR documents** and a
**separate 16-document publisher-text comparison**. The audio set contains 19
Bashar-related interviews/promotional/commentary recordings and one Athina Król
creator-RSS episode attributed to Ashtar. There are 14 audio publishers, not 14
verified mediums. The publisher-text comparison contains 15 Daniel Scranton RSS
items and one Paul Selig publisher transcript. Paul is a spiritual-Guides
comparison source, not a verified biological-ET source.

The outputs support source exploration and measurement criticism. No YouTube
video was newly downloaded; no speaker diarization, human transcription accuracy,
claim truth, ET identity or civilization origin is established.

## Actual data and units

| Unit | Audio ASR | Publisher text |
| --- | ---: | ---: |
| Independently retained documents | 20 | 16 |
| Receipt-reported words | 226,093 | 13,575 |
| Common analysis tokens | 226,138 | 13,556 |
| Decoded audio seconds | 81,691.621533 | Not applicable |
| Retained audio bytes | 1,691,458,021 | Not applicable |

Receipt counts keep their original definitions: the ASR collector used whitespace
words; the publisher extractor used its original regex-word count. The common
analysis tokenizer applies Unicode NFKC normalization, converts curly apostrophes,
lowercases, and matches ASCII alphabetic words with an optional internal
apostrophe. Its rate denominator includes one-letter words. These token counts
are not silently substituted for the acquisition receipts.

All transcript and segment files are checked against their exact receipt hashes
and byte counts. ASR records join the original publisher audio by source ID and
audio hash. Publisher text files join the inspected primary-source metadata.
`sources.json` gives stable `sourceId` joins and the short `A01…A20` / `T01…T16`
figure labels. Source contexts are metadata labels, not an attribution of every
word to the guest or claimed entity. Ads, hosts and guests remain unsegmented.

There are also 457 non-overlapping segment-group chunks of approximately 500
common tokens, and 200 normalized audio-time bins. Chunks expose only source
pointers, times and counts. They are **not** NMF/cluster observations or
independent statistical samples. Models are fitted to the 20 audio documents or
the separate 16 publisher texts.

## Models and calculations actually run

The executable [protocol](protocol.json) records choices and limitations. The
installed analysis environment uses sklearn 1.8.0, NumPy 2.3.5, SciPy 1.17.0 and
Matplotlib 3.10.8. All calculations use CPU; this layer runs no neural inference,
training, source collection or external requests.

TF-IDF uses unigrams/bigrams, sublinear term frequency, smoothed inverse document
frequency, L2 row normalization, `min_df=2`, `max_df=0.95` and at most 3,000
features. The English stoplist retains negation at the stoplist step, with a
declared additional spoken-filler list. Audio and publisher-text vocabularies and
IDF are fitted independently. A separately labeled cross-modality comparison
projects publisher text into the **audio-fitted** vocabulary and SVD; it does not
pool topic or cluster fits. Author, genre, date, length and modality confound that
projection.

NMF displays three components, a choice recorded before execution for readable
exploration. Candidates K=2–6 and seeds 11, 23, 47, 71 and 97 remain available.
Topic-term rows are matched using the Hungarian assignment of cosine similarities;
seed stability is a diagnostic rather than semantic validity. Document weights
are nonnegative row shares that sum to one. Component concentration and effective
source counts expose components dominated by a single recording.

KMeans uses the same document TF-IDF, 30 starts per seed and candidates K=2–6.
The displayed candidate maximizes the seed-11 cosine silhouette; all scores and
adjusted-Rand seed checks remain public. Two-component TruncatedSVD is a view of
these vectors, not a validated semantic map. Component signs are arbitrary.

Theme dictionaries overlap and count explicit word-pattern occurrences per 1,000
common tokens. Source-context overlays show equal-document means. Pooled-token
rates remain available as a length-weighting sensitivity. The patterns align
with provisional reading-code names, but do not use qualitative labels as gold
standard. Dictionary hits are not validated semantic annotations.

Claimed-civilization/star-system patterns are separate from entity names such as
Bashar and Ashtar. No rule maps Bashar automatically to Essassani. Orion or Sirius
can be astronomical or fictional mentions; strict ASR matching can miss names.
The co-mention graph counts each document once per pair, separately by modality.
It represents neither social relations nor relations among physical civilizations.

The document graph is the undirected union of each source's two nearest TF-IDF
neighbors with cosine at least 0.20. The complete cosine matrices and threshold
counts at 0.15–0.75 are retained. Circular graph positions are schematic. Publisher
topic edges are equal-document averages, and publisher accounts are not mediums.

## Results that constrain interpretation

The displayed audio K=2 solution is **19 sources versus one Ashtar-attributed
recording** (cosine silhouette 0.238345; seed ARI 1). This is a stable singleton
partition in this convenience sample. It does not validate medium or ET classes.
Higher-K audio silhouettes are about 0.056–0.089 and their labels are less stable.
The separately fitted publisher-text solution selects K=6 and contains two
singleton clusters. It cannot identify populations of independent channelers.

The three displayed audio components have top labels `reality / physical / idea`,
`workers / jumps / sole`, and `bashar / channeling / information`. These labels
must be read against source context. The reading workstream found the second
component's terms in the Athina episode's discussion of lightworkers, claimed
vibrational changes and a possible ASR substitution of “sole” for “soul”. That
interpretation is provisional and has not been checked against audio. It is a
counterexample to treating topic-token labels as an ontological classification.

The four most similar audio pairs share their publisher: Align, ACID FOR SQUARES,
Danica Patrick, and Healing + Human Potential, with cosines about 0.568, 0.536,
0.520 and 0.514. Publisher format, recurrent hosts and repeated subject matter
are plausible contributors, not identified causal explanations. Original-session
dependence remains unresolved.

Proper-name exclusion preserves 95% of audio nearest neighbors; the commercial
vocabulary control preserves 90%. Restricting to the central 80% of audio time
preserves 80%, with pair-rank correlation about 0.945. This time window does not
establish that ads or hosts were removed. Leave-one-publisher-out NMF matching,
using the original fixed vocabulary/IDF, ranges from about 0.677 to 0.993.
The publisher-text commercial-vocabulary control has no effect on cosine ranks
in this fit. That null result does not establish that promotional sections were
successfully removed: only the explicitly listed vocabulary was excluded.

Negation is an explicit measurement limitation. All audio documents contain
`no`, `not` and `never`; therefore `max_df=0.95` removes those unigrams despite
their retention in the stoplist. `nor` occurs in one document and fails `min_df`.
Ninety-two negation-containing bigrams survive. A fixed **synthetic** control,
“Following excitement is safe” versus “Following excitement is not safe”, yields
cosine 1.0 in the audio fit. This is a constructed failure demonstration, not a
corpus accuracy rate. Lexical cosine cannot be treated as agreement or entailment.

The strict audio civilization dictionary finds Pleiadian/Pleiades in five sources
and Orion in five, co-occurring in two. The publisher-text dictionary finds
Arcturian/Arcturus in six sources even though only three posts carry that primary
source-attributed label. Mentions can concern other groups, comparison or
promotions. Those counts cannot be interpreted as speakers or source origins.

A **post-hoc** spelling sensitivity preserves the original strict counts. Four
audio sources contain four literal `esasani`/`sasani` candidates where the strict
Essassani/Sassani family had zero matches. The Ashtar episode contains 14
`ashta`/`ashtalt`/`ashtara`/`ashtah` candidates in addition to three strict Ashtar
matches. These strings are unvalidated candidates, not accepted aliases or
corrected transcript counts. No audio-name validation has been performed.

## Figures and exports

Nine inspected figure families each have vector PDF, SVG and PNG versions:
source coverage; audio cosine heatmap; source/modality projection overlay; audio
NMF topic shares; context/theme-rate overlay; document lexical network;
modality-separated civilization co-mentions; model diagnostics; and normalized
audio-time theme profiles. Captions are in `captions.json`. PDFs embed TrueType
fonts and have no Type 3 fonts. The source overlay uses callouts to avoid crowded
labels without moving the actual points.

`analysis.json` contains source rows, separate TF-IDF fits, topic/cluster outputs,
lexical rates, graph edges, sensitivities and figure bindings. Its fixed top-40
display vocabulary has exact per-document weights, permitting filtered means
within that vocabulary without refitting or pretending all 3,000 terms are shown.
CSV tables expose source rows, pair similarities, topic shares, keyword rates,
model candidates and leave-publisher-out diagnostics.

Full transcripts, segment bodies, publisher text and fitted sparse feature data
stay outside Git. The retained numeric feature cache is under
`/workspace/channels-et-raw/transcript-analysis/`. Public files contain no source
body quotations; the sentence-pair controls above are synthetic author-written
examples.

## Reproduction and review

From the repository root:

```sh
/workspace/channels-et-analysis-venv/bin/python research/transcript-analysis/build.py
/workspace/channels-et-analysis-venv/bin/python research/transcript-analysis/verify.py
```

The build requires the exact locally retained private source files and pinned
environment; public metadata alone cannot recreate absent copyrighted speech.
It never downloads data. `verification.json` records eight executed source,
calculation, graph, time/chunk and font checks. The independent review under
`research/transcript-review/` additionally reconstructs decisive calculations from
the actual raw inputs without importing this builder. AI-agent review is not
human peer review or human annotation validation.
