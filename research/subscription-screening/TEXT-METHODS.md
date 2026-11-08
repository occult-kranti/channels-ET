# Separate publisher-text study

This study uses newly acquired publisher-hosted text from Tracy Kumbera and
Magenta Pixie. It is separate from the frozen Bashar–Ra baseline and the official
Bashar excerpt study. It does not infer transcript coverage for the other screened
accounts or promote historical title summaries into newly read source text.

The acquisition frame contains 91 files: 71 SRT caption publications, 15 English
publisher-labeled transcript PDFs, one Portuguese transcript PDF, three other
reference/incantation PDFs, and one third-party republished reference. All remain
in the source inspector. The English transcript frame contains 86 publications;
one pair of identical raw SRT files is represented once in the model, producing
85 model units (70 caption files and 15 transcript PDFs). The duplicate file does
not establish duplicate audio or an independent historical performance. Unknown
recording/session families remain unresolved.

## Admission and source preservation

`analyze_texts.py` requires the expected publication count and verifies the entire
manifest against the original acquisition frame. Source and normalized artifacts,
receipts, extraction files and supporting evidence are SHA-256 and byte checked.
Every nonempty SRT block must parse with ordered, bounded times. PDF text must
reconstruct the declared number of pages from the retained form-feed extraction
and match the retained `pdfinfo` page count. Reconstructed turns and joined text
must equal the normalized document, including exact source word/turn counts.
Malformed or partial source frames fail admission rather than silently fitting a
successful subset. Fixture evidence cannot become observations.

Original bytes and normalized cue/page text stay private and unchanged. For
analysis, SRT markup is removed and HTML entities decoded. PDF extraction covers
text only: it does not interpret diagrams, typography, layout or image-only text.
Caption generation is unverified except one Magenta PDF explicitly declaring
YouTube automated-caption origin. Publisher-hosted captions are not assumed human
or machine on the basis of their hosting service. None is audio-aligned or
speaker-diarized. Language reflects the recorded publisher/bounded title-page
basis, not a full-document language audit.

Publisher, medium and claimed-entity metadata remain separate. A project-level
claim about the Nine does not identify every speaker or passage, and empty entity
labels are not filled using titles. Unknown/epoch-like dates remain missing for
chronological inference.

## Models and comparisons

The helper implementation is pinned to the corrected Bashar–Ra Run04 code hash,
but these models are fitted anew only on this study's eligible text units. No old
Bashar/Ra vectors, topics or labels are pooled into the new fit.

Lexical preprocessing uses NFKC normalization and lowercase ASCII word forms with
an optional internal apostrophe. TF–IDF uses unigrams/bigrams, sublinear term
frequency, smoothed IDF, L2 normalization, minimum document frequency two and at
most 12,000 features. English stopwords are removed while preserving `no`, `not`,
`nor` and `never`. Raw-token, conversational-filler and publisher-name-masked
variants are compared. The publisher-name mask contains only Tracy, Kumbera,
Magenta and Pixie. Generic entity-name words such as “Nine” and “consciousness”
remain content. Removing digits means expressions such as 3D/5D can share a `d`
token; this lexical fit cannot distinguish their numbered concepts. Neural
inputs preserve digits, but no separate numbered-concept validity test is claimed. Whole-word semantic masking preserves negative/future
contractions.

A centered 600-analysis-token source span is projected into the full-fit TF–IDF
vocabulary/IDF. Its corresponding neural input preserves the contiguous span's
punctuation, numbers and case after declared Unicode/apostrophe normalization.
Short sources would be excluded only from that sensitivity. This reduces one
length difference; it does not match preparation methods, dates, genre, editorial
selection or speakers.

NMF explores 2–8 components with three seeds; four components are displayed for
readability, not selected as an optimum. Component top words, source shares,
concentration, convergence and seed matching are retained. A further eight trials
fit 80% source-unit subsets without replacement in the fixed full-corpus
vocabulary/IDF and match components with a Hungarian assignment. This is a
conditional perturbation diagnostic, not an independent-session sample, confidence
interval or statistical reliability coefficient. K-means selects the maximum
seed-11 cosine silhouette across candidate counts, without publisher labels as an
oracle. Seed adjusted-Rand values, sizes and singleton counts expose instability.
The network is the undirected union of three nearest lexical neighbors above a
0.15 cosine threshold, with threshold sensitivity. It is a vocabulary network,
not evidence of contact, influence or common identity.

The same ten word-form dictionaries used in the baseline are retained explicitly.
Equal-unit and pooled-token rates have different denominators; both are shown.
Polysemy, quotations, recognition errors and negation prevent interpreting these
rates as validated beliefs. The longest English transcript PDF is retained in the
full frame, then removed in a declared leave-one-document-out sensitivity that
refits TF–IDF and recomputes keyword rates. Its share of publisher transcript words
is stated so length dominance remains visible.

Optional frozen MiniLM inference uses the already verified local ONNX model,
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Every content wordpiece is
processed in nonoverlapping 240-token chunks, using the pinned token and
content-token-weighted document pooling contract. Exact input/model/code hashes
bind caches. Coverage is reported for every full text and every 600-token span.
No model training, fine-tuning or weight editing occurs. Neural and lexical
cosines have different scales and are not agreement probabilities.

## Interpretation and outputs

Source differences are inseparable from caption/PDF format, generation/editing,
publication period and editorial selection in this frame. Units may share
historical sessions. Pairwise cosine values share source observations; they are
not independent samples. No causal inference, significance tests, source-claim
verification or authenticated entity classification is reported.

The private SQLite database contains all publication cues/pages and unverified
question-mark candidates. It identifies no substantive questions, speakers or
answers automatically. Component-selected reading leads identify exact source
hashes and complete cue/page windows; their selection scores are aids to reading,
not proof of representativeness or semantic correctness. Manual/source-reading
coverage is reported separately by its owner.

Public outputs are `source-topics.json` and allowlisted PNG/SVG/PDF figures. Full
text, receipts, raw files, private reading windows and SQLite stay outside Git.
The output manifest hashes each artifact. Final measured diagnostics and results
are documented in `TEXT-RESULTS.md` after the actual run and independent review.
