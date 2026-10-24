# Source-linked transcript reading and Q&A candidates

This layer adds **executed AI-assisted close reading** to the full-corpus lexical
analysis. It contains 36 source records, 105 inspected windows, ten overlapping
qualitative codes and 37 paraphrase-based reading aids. It is separate from the
historical 949-candidate digest database. No human annotation, speaker
diarization, YouTube video acquisition or new external model inference occurred.

The available audio is 19 Bashar-related publisher recordings and one
Ashtar-attributed Athina Król creator episode. Those are not 20 independent
mediums or balanced ET populations. The text comparison contains 15 Daniel
Scranton RSS items and one Paul Selig spiritual-Guides publisher transcript.
Publisher labels describe attribution; they do not verify an extraterrestrial
speaker, civilization or biological origin.

## What was actually read

| Source stratum | Reading scope | Unique words inspected / available |
| --- | --- | ---: |
| Twenty audio-ASR documents | Beginning, middle and ending windows, one question-enriched window per recording, additional targeted contexts; the complete single Ashtar ASR was also read | **11,992 / 226,093 (5.304%)** |
| Fifteen Daniel RSS items | First 250 whitespace-delimited words of each retained item | **3,750 / 11,087 (33.823%)** |
| Paul publisher PDF extraction | Complete retained four-page text extraction, including marked sound losses | **2,569 / 2,569 (100%)** |
| All authored text | The two text scopes above, kept separate from speech | **6,319 / 13,656 (46.273%)** |

ASR coverage spans **1,112 of 21,197 segments** and 4,787.85 seconds of retained
ASR intervals within 81,691.621533 seconds of source audio. This is coverage of
recognized text and its timestamp intervals, not a measurement of recognition
accuracy or a verified fraction of every spoken word. Segment boundaries can
extend beyond the requested window targets. Ads, silence and other editorial
content remain part of the original recordings.

There are 96 initial windows: 30-second targets at beginning/middle/end and one
60-second question-enriched target for each ASR document, 15 opening text
prefixes, and Paul's full extraction. Nine adaptive windows are explicit:
three contexts prompted by NMF terms, the full rare Ashtar comparison plus a
bounded purpose-guidance locator, and four post-hoc spelling contexts requested
after exact lexical zeros were observed. The additional Ashtar reading is
deliberate oversampling of the only non-Bashar audio comparison, not balanced
sampling. All 105 final windows were inspected semantically by the agent.

The reading packet has **19,603 word tokens including overlapping windows**.
Use the deduplicated counts above for coverage. Both numerators and denominators
use Python `str.split()` whitespace tokens. Some inherited publisher metadata
uses a regex tokenizer instead: for example, Paul's inherited count is 2,577,
whereas the retained text has 2,569 whitespace tokens. These definitions are
preserved rather than silently mixed.

Question enrichment uses punctuation/question markers and selected thematic
words. The resulting sample is purposeful. Document code counts are descriptions
of inspected windows, **not estimates of full-corpus theme prevalence**.

## Qualitative codes and actual counterexamples

The codebook covers contact/disclosure; beliefs and agency; fear and self-worth;
practice/alignment; consciousness/ontology; claimed being identity;
validation/criticism; bodily or health claims; collective ethics; and publisher
promotion. Codes overlap. There are 142 source-document/code assignments,
supported by exact window IDs. These are provisional AI interpretations, not
human gold labels or an independent test of the unsupervised topics.

Six inspectable findings in `interpretive-findings.json` illustrate why lexical
results need context:

- A skeptical podcast repeats belief/reality vocabulary while criticizing the
  guidance. Similarity therefore cannot establish agreement.
- Retail, health-service, software and podcast advertisements occur inside the
  retained bodies, including the middle of an apparent answer. Their words can
  drive document topics without describing an alleged entity's teaching.
- Some agency passages expressly qualify what changes are possible, and a
  forecast passage declines to restate an earlier transmission. A shared theme
  does not erase these qualifications.
- In the single Ashtar comparison, an NMF term about workers refers to
  lightworkers, jumps describes claimed vibrational/timeline changes, and sole
  may reflect recognition of soul. A source-specific component can combine
  meaningful vocabulary with transcription noise.
- Contact-readiness passages concern different subjects: individual preparation,
  humanity as a whole, or an already receptive audience. They cannot be treated
  as an agreement or contradiction test without validating the question context.
- Practical guidance has different structures: a general action/belief formula,
  a three-stage purpose account and other spiritual identity/practice framings.
  They are comparison leads, not evidence of independent civilizations agreeing.

No audio verification was performed for these interpretations. Full ASR text,
sampled passages and publisher text stay private.

## What the 37 Q&A records mean

| Kind | Records |
| --- | ---: |
| Explicit interview-prompt candidates | 14 |
| Fragmentary interview-prompt candidate | 1 |
| Rhetorical coaching prompts | 2 |
| Recalled autobiographical self-questions | 2 |
| Secondary reported question with skeptical commentary | 1 |
| Rhetorical guidance question in the full Ashtar comparison | 1 |
| Analyst-constructed comparison prompts for authored text | 16 |
| **Total reading-aid records** | **37** |

Every public question and answer is an **AI paraphrase**. The 16 authored
comparison prompts are constructed reading questions, not literal questions that
someone asked a medium. Audio candidates also include self-questions, coaching
and secondary reporting. They must not be counted as 21 validated interview
exchanges or 37 literal entity answers.

Each record joins a source ID, full-text hash, window hash and exact supporting
segment IDs/times or character offsets. The support is a **shared evidence
window**; the question and answer turns are not independently bounded or
diarized. Partial replies, fragments and advertisement interruptions are labeled.
Speaker attribution remains unknown and human validation remains TBD.

Ten `promptFamily` groups help browse broadly related questions. Membership is
an AI analytic grouping. It does not demonstrate semantic question equivalence,
answer entailment, agreement, copying or a common physical source.

The SQLite file contains only source metadata, window locators, code definitions,
code links, paraphrases and methods. It contains no raw transcript/window body.

## Post-hoc entity-spelling sensitivity

`posthoc-entity-spelling-review.json` retains strict and candidate-token results
separately. The canonical audio tokens `essassani` and `sassani` have zero exact
matches, while candidate spellings `esasani` and `sasani` occur four times across
four documents. Their inspected contexts discuss a claimed species,
civilization, people or world; one is skeptical secondary reporting.

The canonical `ashtar` appears three times in one document. Four additional
candidate spellings contribute 14 occurrences, all in that same creator
recording. More spellings do not create more independent sources. These are
plausible recognition/spelling candidates, **not audio-verified aliases**. They
are not merged into the predeclared strict lexical counts. Exact-token zeros
therefore remain exact-token zeros rather than absence claims about content.

## Files and reproduction

| File | Purpose |
| --- | --- |
| `documents.json`, `source-manifest.json` | 36-source metadata and receipt/private-file hashes |
| `reading-windows.json` | 105 text-free locators and deduplicated coverage |
| `reading-attestation.json` | Exact inspected source/window hashes and frozen manual-annotation hash |
| `annotations-manual.json` | AI-authored source-specific paraphrases and code assignments |
| `codebook.json`, `qualitative-codes.json` / `.csv` | Definitions and supported provisional coding |
| `qa-candidates.json` / `.csv` / `.sqlite` | 37 typed, paraphrase-only reading aids |
| `prompt-family-comparisons.json` | Ten coarse analytic comparison families |
| `interpretive-findings.json` | Six source-linked counterexamples/comparison leads |
| `posthoc-entity-spelling-review.json` | Exact-token sensitivity and inspected context pointers |
| `summary.json`, `verification.json` | Counts, caveats and executed integrity checks |

From the repository root, with the retained private source files present:

```sh
python3 research/transcript-reading/prepare_reading.py
python3 research/transcript-reading/build_reading.py
python3 research/transcript-reading/build_interpretations.py
python3 research/transcript-reading/verify_reading.py
```

The preparation step verifies all 60 ASR outputs and 16 publisher-text files
before constructing the private packet. The build reuses the frozen AI-authored
annotations. It rejects any source, packet, inspected-window or annotation hash
that differs from the explicit reading attestation; new text requires actual
reinspection and a new documented attestation. A hash-bound attestation records
the agent's reading claim, not independently observable cognition or human
validation. Rebuilding does not perform fresh semantic reading or model inference.

No collection, external network operation, audio/video download, neural inference
or old-database edit is performed by these commands. Verification is scoped to
source integrity, exact locators, coverage arithmetic, artifact joins and release
boundaries. Semantic paraphrase accuracy and speaker/question equivalence remain
human-review tasks.
