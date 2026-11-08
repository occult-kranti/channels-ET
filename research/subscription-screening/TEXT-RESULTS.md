# Publisher-text results · separate supplementary study

The newly acquired text supports exploratory comparison of two publisher
contexts. It does not establish text coverage for all screened accounts, the
truth of source claims, or the identity of any claimed communicator.

The source manifest is SHA-256
`e9f48461d7ebe063251d563918bbd3fa405cf885b150afc50f981dcd95305b0b`.
Run01 public derived data is
`6dceb3c3a48c16d69dc0e373e88aa4501563ea75a9f5dd64fd2a3176f446d145`;
executed code is
`d87cce63b42192509c60b602e95c80c8fda232f19068baf1e7cdda54d4c8c030`.

| Source stratum | Publication records | Model units | Words in model units |
|---|---:|---:|---:|
| Tracy publisher-hosted captions | 71 | 70 | 144,568 |
| Magenta English transcript PDFs | 15 | 15 | 60,706 |
| Portuguese transcript PDF | 1 | Excluded from English fit | — |
| Other reference/incantation/republication PDFs | 4 | Excluded from transcript fit | — |

All 91 publications remain visible and contain 217,191 whitespace words. The
primary 86-publication frame contains 207,710 words, reduced to 205,274 words
across 85 model units after grouping one exact raw-caption duplicate. Identical
caption bytes establish text duplication only; their two episode titles and
publication records remain preserved. This is not proof of duplicate audio.

## Comparisons and denominator sensitivity

| Pair group | Full name-masked TF–IDF | Centered 600-token spans | Longest PDF omitted, refitted TF–IDF |
|---|---:|---:|---:|
| Within Magenta PDFs | 0.19474 | 0.07780 | 0.20166 |
| Between publisher contexts | 0.07737 | 0.03467 | 0.07572 |
| Within Tracy captions | 0.12270 | 0.05586 | 0.12470 |

Values are mean cosine similarities over dependent text pairs. The full and
window comparisons contain 105 PDF/PDF, 1,050 cross-context and 2,415
caption/caption pairs; these pair counts are not independent sample sizes.
Removing the longest PDF changes the first two counts to 91 and 980. Source
format, generation/editing, dates and editorial selection remain confounded.
Raw-token and filler-filtered fits have similar descriptive ordering. Removing
publisher names alone changes the full cross-context mean only from 0.07719 to
0.07737; that does not eliminate the other confounds.

The 85-page automated-caption-origin PDF contains 23,969 words, 39.48% of the
English Magenta transcript words. Its influence differs by denominator. For
example, the Magenta ontology dictionary's pooled rate changes from 5.955 to
8.553 occurrences per 1,000 analysis tokens when that PDF is omitted, whereas its
equal-document mean changes from 7.502 to 7.898. The ethics/polarity pooled rate
changes from 7.731 to 11.159; the equal-document mean changes from 8.689 to 9.134.
These are word-form counts, including possible polysemy, quotations, negation
and recognition errors, not validated doctrinal prevalence.

## Components, clusters and network

Four displayed NMF word sets emphasize:

- Soul, ego, identity and mind.
- Service/self, planetary, starseeds, polarity and template vocabulary.
- Dragons, goddesses, love, power and Magdalene vocabulary.
- Solar, light codes, sun, comet, Atlas and ascension vocabulary.

These labels summarize top words as reading leads. They are not authenticated
entity assignments or independently validated topics. The ASCII lexical tokenizer
removes digits, so a frequent `d` token can conflate expressions such as 3D/5D;
this fit cannot establish differences between numbered dimensional concepts.
The neural inputs preserve those numbers, but no specific dimensional-concept
agreement test was conducted.

The selected k-means k=2 partition reproduces the 15-PDF/70-caption division
exactly. Its silhouette is 0.06292; adjusted Rand agreement across the three
seeds is 1.0. Stable recovery of a confounded publisher/format division is not
independent evidence of distinct belief systems. The four-component NMF seed
matching is nearly one under its structured initialization. Eight source-subset
perturbations have mean matched cosine 0.95598, ranging from 0.92203 to 0.97274;
these are conditional diagnostics with fixed vocabulary/IDF, not confidence
intervals or statistical reliability coefficients. All candidate NMF fits
converged before the declared 800-iteration limit.

The default three-nearest-neighbor vocabulary graph has 167 undirected edges,
including one cross-context edge. The threshold sensitivity is included in the
data. Edge presence cannot establish influence, contact, shared authorship or
common communicator identity.

## Frozen neural sensitivity and questions

Complete MiniLM processing covers all 85 model units: 251,478 content wordpieces
in 1,088 chunks, with zero truncation. The 85 centered 600-token spans contain
63,033 wordpieces in 321 chunks. Full text cross-context mean cosine is 0.56340;
the centered-span value is 0.42234. Within-PDF and within-caption values are
0.63820/0.66602 for full text and 0.45136/0.52187 for centered spans. Neural and
TF–IDF scales are different and are not agreement probabilities. Long-document
pooling and source preparation materially affect the comparison.

The private database contains 91 publications and 15,888 cue/page records, with
687 records containing question marks. These are unverified punctuation
candidates in mixed or unknown speaker text, including rhetorical questions and
cue fragments. It identifies zero verified semantic questions and zero answers.
Sixteen component-selected complete cue/page contexts were emitted as bounded
reading leads. Separate source-reading attestations determine which contexts
were actually read; full-text computational processing is not a claim of full
manual close reading.

## Verification and delivery

Thirteen admission/measurement regression tests pass. Source hashes, receipts,
raw-to-normalized reconstruction and every publication's declared disposition
were checked before fitting. The independent output audit accepted this data hash after rehashing all 19
outputs, recomputing 24,906 pair values, checking every topic/reading locator and
SQLite count, and independently retokenizing every full text and window. Its
private receipt is `capacity/final-screened-text-study-independent.json`. The keyword and SVD-map figures were visually
inspected for readable marks, labels and legends. Public files are the derived
JSON and five figure families in PNG/SVG/PDF; full text, raw sources, private
reading windows, model files and SQLite remain outside Git. See
[TEXT-METHODS.md](TEXT-METHODS.md) for the complete measurement contract.
