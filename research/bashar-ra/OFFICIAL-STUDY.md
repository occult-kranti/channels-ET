# Publisher-selected Bashar speech: separate follow-on study

This study extends the corrected Run04 baseline with publicly available official
Bashar Communications clips. It does **not** convert clips into complete historical
sessions or replace the 106 Ra-session / 19 mixed-context-recording baseline.
Official attribution identifies the publisher context, not every voice or the
claimed identity of a communicator.

## Source frame and admission

The frozen player census contains 87 publications meeting the discovery-time
duration criterion. Final execution requires an explicit transcript or exclusion
disposition for every exact publication ID. Measured audio duration can reveal a
boundary exclusion even when a rounded player duration met the discovery criterion.
An unavailable or excluded source remains in the denominator; `phase=pilot` must
not be presented as final frame coverage.

The initial 15-publication pilot consists of 14 available platform-generated
caption tracks and one locally recognized public Q&A excerpt, totaling 12,589
whitespace words. That snapshot is preserved separately from the final batch.
It is not a random sample of all Bashar recordings. The final acquisition and
transcription manifests, not this initial pilot, determine final eligibility.

Each admitted normalized document is bound to original evidence by SHA-256 and
byte count. Platform WebVTT is independently parsed and compared cue by cue for
text, timing and order. The original player identity, automatic-caption language
label, acquisition receipt and duration must agree. A downloaded caption track
does not establish that every audible word is present or correct.

Local ASR is checked against the original completed processing receipt, unchanged
segment stream and media hashes. An edition-qualified normalized source ID maps
explicitly to the original publication ID in executed receipts; original receipts
are never rewritten to match a later database identifier. The pinned producer's
read-only completion verifier checks retained artifacts and accepts only its
strictly declared, newly removed PCM derivative. It cannot excuse a missing
original recording or another missing output.

Container presentation duration and decoded sample duration are separate fields.
Although the pinned producer permits a difference up to the greater of two seconds
or two percent, this study additionally requires a difference of at most two seconds.
Local ASR timestamps refer to decoded PCM samples, without a claim of validated
source-player alignment.

This check caught an incomplete edition of publication 204089777: a 5.994667-second
packet gap corresponded to an acquisition-time HTTP503 under the downloader's
default fragment-skipping behavior. The old media hash is explicitly rejected;
its raw files/receipts remain preserved, and only a separately acquired strict
replacement can be admitted. Packet-duration agreement alone does not establish
complete retrieval, and the producer's two-percent tolerance must not excuse known
missing media. The final acquisition audit and corrected source manifest remain
part of the evidence chain.

Both explicitly translated recordings are labeled multilingual regardless of a
decoder's dominant-language estimate. They are excluded from this English lexical
study, with their acquisition/transcription status preserved. English model
selection and platform language labels are not human verification of all speech.

## Publications, editions and model units

One text edition is selected per publication. Where a platform caption and local
ASR edition coexist, the declared preference is the platform track; this is a
consistent selection policy, not an accuracy ranking. Alternate editions remain
documented and privately retained. A held alternate edition does not count its
otherwise admitted publication as wholly unavailable.

Verified identical encoded-media hashes are grouped into one model unit, with a
deterministic representative. Every publication remains in the source table and
private question database, including its model-unit mapping. Counts therefore
distinguish the original frame, admitted publications, held publications, alternate
editions, model units and exact-media aliases. A media family with conflicting
genre labels requires review. Title similarity and five-token overlap alone never
remove an observation or establish a shared historical session.

Publisher-title/description classifications distinguish ordinary public excerpts,
translated material, greetings, event promotions and product introductions or
explanations. These classifications are metadata screening, not verified discourse
annotation. Promotional and greeting material appears in separate comparison
strata and does not train the official-excerpt-only topic model. Historical
session/product families remain unresolved where the evidence does not establish
them. Grouping identical bytes cannot solve re-encoding or excerpt overlap.

## Comparison and sensitivity analyses

The corrected baseline analysis and code are pinned by hash. The engine reproduces
the baseline TF-IDF matrix and normalized NMF shares before projecting any new
clip. Baseline vocabulary/IDF and NMF components remain fitted exclusively to the
125 original primary documents. Official clips are projections into that fixed
space; their component shares are not probabilities or validated equivalent topics.
Refit and projection warnings are retained.
If a projected document/window has no retained vocabulary features, its zero-norm
row is explicitly flagged and excluded from pair summaries and nearest-source
retrieval. A library's zero cosine convention is not evidence of dissimilarity.

A separate model explores the official excerpt units using the baseline's
unigram/bigram TF-IDF, NMF candidate counts and seed diagnostics. Four components
are displayed for readability. Greetings and promotional/product material are
excluded from these topic fits. The same caveats about structured initialization,
convergence, dependence and unvalidated cluster labels apply as in METHODS.md.

The frozen MiniLM model uses the corrected whole-token source mask from Run04,
preserving negative and future contractions. Every available input wordpiece is
processed through nonoverlapping 240-token chunks. Baseline vectors are reused
from exact-input, hash-bound caches; a matrix check permits only small float32
cache-precision differences. No weights are retrained or rewritten.

Centered 400-analysis-token controls are reported separately. Lexical windows use
the baseline tokenizer/stoplist and frozen baseline IDF. Neural windows retain a
contiguous source span, including its interior punctuation, numbers and case;
Unicode NFKC and curly-to-straight apostrophe normalization are explicit. Shorter
documents are excluded only from this sensitivity. These controls reduce selected
length differences but do not match speakers, dates, genre, editorial selection,
recognition settings or source families. The original pilot's joined-token neural
window experiment is superseded by this source-span implementation.

The ten original word-form dictionaries retain fixed membership. Rates are
reported separately by stratum, with equal-model-unit means and pooled-token
denominators. Paired document cosines share observations and are not independent
samples. No p-values, causal effects, agreement probabilities or verified
communicator-origin probabilities are estimated.

## Recognition, questions and edition disagreement

The retained mixed-context ASR used `Systran/faster-whisper-tiny.en` with beam size
one. New English excerpt ASR uses the locally bound tiny English model with beam
size five; the two translated recordings use a separately bound multilingual model.
The platform's automatic-caption model/settings are unknown. Encoder choices,
VAD, music, gaps, speaker mixtures and publisher editing confound the comparison.
Model/language settings remain attached to documents where known.

Cue interval coverage measures the union of retained timestamp intervals divided
by media duration. It is not speech recall, transcript accuracy or proof that a
gap contains silence. Question marks produce unverified candidates; adjacent text
is context, never an automatically identified answer. The private SQLite database
preserves publication-level source/turn records and candidate status.

For the two separately requested caption/local-ASR edition pairs, token edit
distance uses the baseline NFKC/lowercase ASCII word tokenizer, with punctuation
removed and no stopword removal. The distance and both transcript lengths are
reported, along with distance divided by caption-token count. Both inputs are
machine-generated: this is **edition disagreement**, not recognition accuracy or
word error rate against verified ground truth. The pair-selection rule and
transcript hashes remain documented by collection.

## Release and current status

`official-speech.json` and its allowlisted PNG/SVG/PDF figures contain derived
metadata and results. Full source text, audio, model files, original receipts,
private QA JSON and `official-questions.sqlite` stay outside Git and public pages.
The final artifact manifest binds every output. Source-reading coverage is stated
separately; computational processing does not imply that a person or model has
closely read every excerpt.

The final reviewed frame has 87 publication dispositions: 84 English transcript
publications (69,166 words), two mixed-language recordings excluded from English
fits, and one measured 299.648-second recording excluded by the five-minute rule.
All 86 qualifying preferred transcripts across languages contain 70,159 words.
Two exact encoded-media aliases reduce the 84 English publications to 82 model
units (67,536 words): 75 excerpts, four promotional/product clips and three
greetings. The 75 excerpt units contain 62,590 words. There are 14 platform-caption
and 70 local-ASR English publication editions, or 14 and 68 after exact-media
grouping. Historical full-session identity remains unresolved.

The final follow-on output is bound to public JSON SHA-256
`68e4c40a34fa0bd7efcea13a32ea501b0f7bfd55643935f01e2d8a7a68907b01`.
Its 207 model units include the unchanged 125-unit baseline and the 82 additional
units. Full neural processing covers 690,771 content wordpieces in 2,982 chunks,
with zero truncation. The 206 eligible centered windows cover 97,914 wordpieces
in 476 chunks. One short promotional source is excluded only from the window
sensitivity. Independent review checked all 16 output artifacts, exact matrix and
source identities, topic shares, pair summaries, nearest-source ranks and every
input's tokenizer coverage; 24 admission/measurement tests pass.

Mean full-text lexical cosine is 0.15084 for excerpt/context pairs and 0.05309
for excerpt/Ra pairs; centered-window values are 0.05207 and 0.02200. Corresponding
neural values are 0.61474/0.44775 and 0.33771/0.27908. These different scales are
not probabilities, and the changes show substantial dependence on input length
and pooling. Source preparation and genre remain confounded.

The official-excerpt-only partition is weak: selected k=3 has seed-11 silhouette
0.01156 and mean seed adjusted Rand 0.06647. The four displayed NMF components
have matched seed cosine 0.88178. Their term sets concern parallel realities and
contact; negative/positive beliefs and fear; higher/physical mind and
visualization; and physical/spirit experience. These are exploratory word sets,
not validated doctrinal categories. Publication-level question-mark extraction
finds 479 unverified candidates (454 after exact-media grouping), with no
identified answers. Machine-edition disagreement is 6/869 and 4/606 normalized
caption tokens in the two selected pairs, with no ground-truth accuracy claim.

A positive per-media packet/log audit is required by the final analysis gate.
The first candidate frame failed when a retained HTTP 503 log and a 5.994667-second
packet gap exposed a skipped fragment in publication 204089777. Its old encoding
and transcript remain preserved and unadmitted. Strict reacquisition produced a
new complete media/transcript edition before the final fit. The authoritative
source manifest hash is
`633a9254fd493e566ebb553cd4c3a893e432f59b63ea6bbca364421526ab621c`;
the independent final media audit is
`b5aeca2c0e59b67001760482f7e5fcf4190c9834d7ddc075121b0c5145e56c3d`.
The gate rehashes media, acquisition receipts, retained logs and compressed raw
packet evidence, then recomputes packet order, internal gaps and initial/terminal
boundaries with a maximum 50-millisecond tolerance. Passing this check establishes
no detected acquisition gap within that contract; it does not establish complete
historical sessions or transcript accuracy. The earlier 15-source results remain
explicitly labeled pilots.
