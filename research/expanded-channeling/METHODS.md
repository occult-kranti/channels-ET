# Expanded channeling comparison methods

This is an exploratory source study. It does not authenticate claimed beings or estimate the probability that a message has an extraterrestrial origin. The five AI panel roles provide source research, methods, implementation and independent criticism; they are not human expert endorsement.

## Three distinct evidence layers

1. **Claim register:** source-specific medium → named entity, collective, civilization affiliation, contact report or publisher category. A repeated label is not shared speaker identity. Joint practices, known training lineages and reposters must remain visible. Category associations and contact-only records do not count as demonstrated direct channeling.
2. **Observed text:** exact retained publisher texts or machine transcripts. Unknown speakers remain unknown. A project biography cannot label every utterance in a mixed interview. New source-specific attributed messages form a separate follow-on cohort.
3. **Interpretation:** bounded source-linked reading and exploratory lexical retrieval. Similar words do not establish equivalent answers, agreement, shared origin or causal influence.

## Joint accepted-text snapshot

`analyze.py` creates a new fit while retaining all prior studies unchanged. It pins the accepted baseline Run04, official Bashar final01 and Tracy/Magenta Run01 JSON hashes, their input manifest hashes, and the accepted helper code. It rechecks each admitted normalized-text artifact's hash, bytes, identity and word count. Prior full acquisition/ASR/media validations are reused, not claimed to have been rerun. The executed analysis source is copied privately; execution fails if source code changes during the run.

| Observed context | Model units | Whitespace words |
| --- | ---: | ---: |
| Ra Lightly Edited sessions | 106 | 278,601 |
| Bashar-related interviews/commentary | 19 | 222,699 |
| Official Bashar excerpts | 75 | 62,590 |
| Official promotion/product | 4 | 2,895 |
| Official greetings | 3 | 2,051 |
| Tracy publisher captions | 70 | 144,568 |
| Magenta transcript PDFs | 15 | 60,706 |
| Total | **292** | **774,110** |

These are neither 292 independently sampled recordings nor 292 verified channeling sessions. Accepted exact-media/text aliases remain collapsed. Broader excerpt/repost/session identity is unresolved. Excluded reference texts and non-English editions remain reported; researched mediums without admitted text are missing data, not zero similarity. Unknown total-upload counts remain null.

The current acquisition policy has **no minimum duration for non-Bashar sources** and a **300-second minimum for Bashar**. Historical frozen studies retain their former sampling restrictions and do not become newly complete inventories.

## Vocabulary, topics and clusters

Common NFKC tokenization preserves apostrophes and negation. Masking removes complete source-name tokens (including Ra, Bashar, Darryl/Anka, Carla/Rueckert, Don/Elkins, Jim/McCarty, Tracy/Kumbera and Magenta/Pixie) and a declared filler list. It never removes `don` from `don't` or `ll` from `we'll`. TF-IDF uses uni/bigrams, sublinear term frequency, smoothed IDF, L2 normalization, min_df2, max12,000features and the helper's English stop list retaining no/not/nor/never.

Mean pairwise cosine is shown by source context. Diagonal means exclude self-pairs and count each unordered pair once; cross-context means enumerate every cross pair. Centered **600-token spans**, selected before masking, use the fixed whole-text vocabulary/IDF. Shorter texts are explicitly excluded rather than padded. A genre restriction excludes official promotions/greetings and baseline promotional/skeptical formats. Removing the single longest document refits vocabulary/IDF separately. These controls address some length/format effects, not all sampling confounds.

NMF and KMeans explore k2–8 with seeds11,23,47. Four NMF components are displayed for readability, not because four was established as optimal. Top terms are labels, normalized weights are factors rather than probabilities, and all candidate convergence/seed diagnostics are retained. KMeans displays the maximum seed11 cosine silhouette; SVD is only a two-dimensional projection. Source-context adjusted Rand agreement is descriptive confounding evidence, not validation. No inferential p-values or multiple-testing novelty claims are made. Previous neural studies are not concatenated because their source masking differs; this run adds no neural inference or fine-tuned weights.

## Private Q/A database and public retrieval audit

The private SQLite database keeps full source text fragments, source IDs, exact printed Ra pairs, unknown-speaker candidates, unknown answers (`NULL`) and retrieval records. It contains **2,523 Ra documentary pairs**, including four missing-question placeholders. A printed response is documentary pairing, not voice verification. Non-Ra punctuation is segmented within existing cue/page boundaries; thus its count differs from earlier cue-based studies. It does not add speaker diarization or infer an answer from adjacent text.

The first exploratory retrieval inspection exposed false high scores from generic fragments and rare-word deletion. The corrected version requires6–80masked tokens and at least4distinct non-stop content unigrams; it uses a common question-only TF-IDF with min_df1 and exact-text-deduplicated vocabulary fitting. A review lead needs cosine≥0.35, a top-versus-runner-up margin≥0.03, and≥3shared content unigrams. Lower/higher threshold counts are published. Thresholds were adapted after inspection and have no measured precision or external validation.

In the completed corrected snapshot there are2,629unverified punctuation candidates;411are eligible queries and1,949Ra questions are eligible targets.410queries abstain;1candidate reaches the heuristic threshold. Bounded reading rejects that candidate: a fragment about whether today's era differs from a thousand years earlier is matched to Ra16.14 asking the name of an ancient visitor. Both use time-span wording but ask different questions. **No accepted same-question pair or non-Ra identified answer results from this retrieval pass.** The public `qa-review.json` binds the inspected query/target text hashes and contains short paraphrases only. Historical accepted thematic reading remains available on the Bashar/Ra reading page under its own source scope.

Private example:

```sh
python research/expanded-channeling/query_qa.py --database /workspace/channels-et-private/expanded-channeling-2026-11/analysis/run-04/qa-private.sqlite --query 'free will' --limit 10
```

## Reproduction and release

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/channels-et-analysis-venv/bin/python research/expanded-channeling/analyze.py --output /workspace/channels-et-private/expanded-channeling-2026-11/analysis/NEW-RUN
/workspace/channels-et-analysis-venv/bin/python -m unittest discover -s research/expanded-channeling -p 'test_analyze.py'
python research/expanded-channeling/verify_outputs.py --public-dir /path/to/public-or-private-allowlisted-output
```

Output paths must be outside Git and fresh. Incomplete development runs01–03 are retained; only a complete independently accepted run is publishable. The public allowlist contains `analysis.json` and5figure families in SVG/PNG/PDF. Private provenance, full Q/A and raw texts never enter that allowlist. New publisher-message analyses and the typed claim graph receive their own source bindings and denominators.

## New attributed-message pilot

`analyze_pilot.py` separately fits **20 new publisher message bodies, 20,829 words, four mediums and 11 comparison labels**. It binds three new source manifests, full original artifacts and exact extracted body hashes. Page navigation, comments and promotions are excluded by declared source boundaries. Duplicate exact body hashes are rejected until they receive a separate alias disposition. This is a purposive feasibility sample, not a complete archive or new random sample.

The four source contexts are Natalie Glasson, Pamela Kribbe, Daniel Scranton and Lyssa Royal. The Lyssa source is a published 1993 dialogue excerpt: its five explicit `Question:` paragraphs remain in a separate private Q/A artifact; the **2,671-word printed-layout response derivative** enters the pilot. The full 2,742-word dialogue remains preserved. This does not authenticate a voice or make the whole dialogue a single speaker's utterance.

The pilot uses a public complete source-name mask, uni/bigram TF-IDF with min_df1, and fixed-IDF centered **300-token** sensitivity. Twenty exact text hashes are distinct. Three NMF/KMeans components are an exploratory display, with source-medium ARI and seed diagnostics; no optimal count or validation is asserted. Same-label pairs remain distinguished by comparison level: **Pleiadian and Arcturian are broad civilization labels**, while the Marian comparisons share written names. Different councils and named speakers are not merged.

The frame has seven cross-medium Pleiadian document pairs, three Arcturian pairs, one Mother Mary pair and one Mary Magdalene pair. Their equal-pair mean full-text cosine is **0.0364**, versus **0.0659** among 49 different-label pairs within the same medium. The centered-span means are 0.0183 and 0.0315. These selected, dependent pairs suggest that publisher/medium vocabulary deserves attention; they cannot establish a general style effect or a civilization's coherent doctrine. Per-label values and all pair source IDs are supplied so the broad and named comparisons can be separated.

A methods agent read nine complete bounded source bodies: **11,274 model words**, plus the 71 excluded Lyssa question words. Four explicit comparison notes preserve shared themes, different recommendations and counterexamples. The Mother Mary comparison distinguishes trust/abundance language from boundaries and inner-child care. The Magdalene comparison distinguishes grace/initiation language from embodied passion and shadow integration. Pleiadian messages differ between free choice, daily recentering and a financial/community model; Arcturian messages differ between a purported history of practices and a present-focused attention exercise. These are source interpretations, not factual endorsement or matched audience questions. Source hashes and the exact public reading note are frozen beside the executed pilot.

## Claim graph and missingness

`claim_graph.py` validates every relation's person, label and supporting-source references. It merges shared register IDs only when immutable identity fields agree, preserving all source/account metadata. Direct-channeling counts exclude mere civilization affiliations, publisher categories, contact-only reports, series-medium listings and reposted attributions. Pia Orleane and Cullen Baird Smith remain two people but one declared collaboration practice; no practice is claimed to have an independently established origin.

An explicit comparison-label crosswalk joins the **new pilot's text availability** to broader register groups without merging source-specific entity IDs. Unsupported groups display `insufficient_cross_medium_attributed_text`; no missing text becomes a zero cosine. Registry record counts are not counts of all channelers on YouTube. Broad labels, named labels and related-name/aspect comparisons retain separate types.

## Executed review corrections

The independent critic recomputed all 98 whole/window group cells and pair counts in the joint study, all 411 eligible Q/A retrieval scores and selection decisions, and the final annotation/source bindings. NMF/KMeans were not independently rerun. A postrun binding edition records the already-applied Q/A review without changing scores or annotation content. A subsequent **visual-only edition** moves the similarity colorbar outside the matrix after direct image inspection exposed an overlap; numerical results remain identical. The joint public artifact is `analysis/final-02`, with the earlier editions retained. New pilot numerical/source verification is separately documented in the panel review.

The source panel's second review identified a residual council-title signature in the pilot's partial token mask. `pilot_sensitivity.py` therefore creates a separate posthoc variant removing the complete Pleiadian High Council of Seven/7 and Arcturian Council title phrases before the existing token mask. It refits vocabulary/IDF on the same 20 messages and preserves the original topic model. Same-label cross-medium mean cosine changes from 0.03636 to 0.03648; different-label within-medium mean changes from 0.06588 to 0.06538. The largest individual pair change is 0.03483. The public final pilot is `pilot/final-02`; both masking variants, phrase counts and exact patterns remain inspectable. The modest aggregate change does not remove other source-style confounds.

## Continuing collection snapshots

`analyze_collected_audio.py` can analyze later completed publisher recordings without mutating either frozen study. It copies exact acquisition and ASR manifest bytes into a new private run before selecting records. Every selected source binds retained full-duration derivative bytes, an immutable collection receipt, and a normalized caption/ASR artifact. A source entering the live collection after that copy is deferred to the next explicit snapshot. Full audio being decoded is not equivalent to all speech being recognized: VAD and ASR errors remain visible.

Where an exact GUID/enclosure caption link exists, one publisher-caption edition is preferred; otherwise the latest completed local ASR edition is selected. This is an operational edition rule, not an accuracy ranking. Alternative editions are retained as dispositions; exact original-media families and exact text hashes are collapsed. Reused Tracy captions are labelled as previously collected text, not new ASR. An OmNa written message and an audio transcript are related editions, not independent channelers. All machine-text speaker roles remain unknown, including introductions and interview guests.

This separate snapshot reports audio retained, text available, local ASR, reused captions, words and duration by publisher context, with unknown YouTube upload totals remaining null. Lexical fits require two eligible texts; NMF/KMeans display at most three exploratory components only with at least five eligible texts. A fixed lexical keyword dictionary reports word-form counts, not validated beliefs or answer accuracy. Private SQLite retains exact source text and unknown-speaker segments; public artifacts contain metadata, aggregates, top terms and three distribution figures. Any later successful downloads or recognitions require a fresh output directory and new source-bound denominator.

For a new recording with a same-page written message, the collection study additionally reports token-sequence overlap between editions, with their separate word counts and hashes. It uses ordered token matching (`SequenceMatcher`, automatic popular-token suppression disabled). This is **not word error rate**: introductions, endings, editorial shortening, paraphrase and recognition errors are not disentangled, and the written message has not been established as a verbatim audio reference.
