# Source-bound profiles and typed question evidence

The extractor processes every selected body in the frozen 493-source Channel Lab frame. Its output is an automatic source profile and a typed question-evidence bank, not 493 close readings or a claim to understand every recording. Full source bodies, exact questions, responses and surrounding text remain private. Public artifacts contain source metadata, generated navigation labels, lexical outlines and exact locator metadata; the separately curated cards provide reviewed paraphrases.

## Counting and source identity

One canonical source is one previously selected publication/body unit, not necessarily a video or a historically independent channeling session. Official excerpts, mixed interviews, publisher messages and edited Ra sessions retain their different origins. Source profiles preserve the selected edition, normalized body hash, original source URL, publishing context, creator-context and source-attributed labels. Creator-context labels do not identify authenticated speakers or establish that every utterance is addressed to a claimed entity.

The original source loader verifies each retained artifact and its normalized body hash. All character spans use Python Unicode positions in that selected NFKC-normalized body, with an exclusive end. Every private support stores its exact slice and SHA-256. Record IDs hash the policy version, record type, canonical source/edition/body, exact span boundaries and any generated prompt wording. A different edition, boundary or policy cannot silently inherit an old record identity.

## Four record types

| Type | Admission and answer policy |
|---|---|
| `observed_question_answer` | A Ra publisher-printed `questioner` turn followed by one or more `response` turns with the same printed question ID, before another questioner or uncertain boundary. This observes editorial layout, not supernatural identity, factual truth or answer adequacy. |
| `unverified_question_candidate` | A punctuation-delimited question cue in other sources, or a printed prompt lacking a positively paired response. It can be quoted, rhetorical, promotional, erroneous or part of mixed speech. The following context is explicitly not an identified answer. |
| `generated_reading_prompt` | One transparent template-based reading task per source, informed by its frozen lexical profile. It is not observed source speech, has no question span and has no identified answer. |
| `curated_comparison` | Reserved for the separately reviewed curation layer. The extractor creates no automatic semantic comparisons or contradiction labels. |

Ra prompt/response boundaries are rebuilt directly from the retained printed turns. Refusals, uncertainties, corrections and multi-paragraph responses remain intact. Missing-question editorial placeholders are flagged with `question_text_available: false`; their lost wording is never reconstructed. Responses without a preceding printed questioner turn remain outside the paired-Q&A bank, while the full source remains available through source retrieval.

For other texts, a candidate extends from a prior `.`, `!` or `?` boundary to the next question mark, preserving arbitrary line wraps. One-word cues such as “Why?” are retained; punctuation with no lexical token is recorded as skipped. This broad rule does not establish complete grammatical questions or distinct speakers. Long cues, quotation characters and commercial vocabulary are only surface flags. Up to 600 following characters are retained privately as inspection context; the cutoff can end mid-thought and is never an answer boundary. Unknown machine speakers remain unknown.

Lyssa's five previously reviewed documentary questions are a special external-edition case: their printed wording is in a separate question/answer artifact, while the canonical selected body contains responses only. The curator preserves that external artifact binding rather than inventing canonical question offsets. This extractor only pairs documentary questions actually present in its selected body.

## Automatic profiles and navigational extracts

Profiles reuse the completed primary analysis's exact TF-IDF terms and normalized NMF factor weights. No vocabulary, topic model, encoder or model weights are fitted here. Their template states processed word count, source format, ranked lexical cues and extracted record counts. It does not turn keyword frequencies into teachings, beliefs or predictions. Factor weights are not topic probabilities.

Each private profile also carries a navigational extractive digest of at most 180 words. The deterministic selector chooses up to three passages, one from each positional third, rewarding the source's frozen unigram TF-IDF weights and penalizing overlap with previously selected passages. Punctuation/paragraph units longer than 60 whitespace words are split into explicitly flagged word windows. The operational `complete_sentence_or_paragraph` flag only distinguishes unsplit delimiter units from these artificial windows; it does not validate grammar, coreference or semantic completeness.

Every digest passage retains exact offsets and neighboring up-to-200-character context locators, plus `omitted_context` and `standalone_faithfulness_validated: false`. An exact extract can still mislead if its antecedent, condition, quotation frame or qualification lies elsewhere. The digest is a navigation aid, not a validated standalone summary. The private source database supports inspection of the full body.

Conditional/modal, temporal, negation, numeric, commercial and refusal patterns are surface counts. Homonyms and rhetorical uses remain unresolved. Counts do not identify prediction dates, logical scope, speaker intentions, factual correctness or sentiment. Full-body machine processing does not count as manual reading or listening; both human-read and audio-listened flags are false in this automatic layer.

## Pilot correction before the full batch

Pilot01 used six actual sources: 29,775 words and 147 records, including 28 Ra printed pairs. Independent review checked all 300 support spans and examined a Ra refusal, a singular/plural correction, a quoted written question and ambiguous interview material. A separate Crimson pilot exposed a concrete line-wrap defect: `what were your human expectations\nof enlightenment?` had been truncated to `of enlightenment?` by a newline-delimited candidate rule.

Policy v2 removes newline as a question boundary, preserves one-word cues, discloses fragment/multiple-utterance possibilities and fixed context truncation, and adds neighboring digest context/faithfulness markers. Corrected pilot02 used seven actual sources: 42,267 words, 326 records and 659 support spans. Independent checks rebuilt all 28 Ra pairs and verified that the two cited wrapped Crimson prompts now survive intact while remaining unverified, unanswered candidates.

Completed resume originally checked only public artifact hashes. The corrected version additionally binds the private manifest and rechecks the private question-bank and profile hashes. Both producer and independent reviewer copied the actual corrected pilot, changed the private bank, and observed the exact `Completed private bank changed` rejection. Originals remain untouched. The corrected unmodified pilot returned a verified complete cache hit without processing or inference.

## Files and local use

`profiles.json` contains all public source profiles. `bank-index.json` contains source/type counts, source-shard hashes and a light global record index for complete browser search/filtering. `records/<source_id>.json` shares the source edition/body binding once and contains full public record metadata and locators. Exact source wording is excluded from all three.

Private `question-bank.jsonl` contains raw question, response and inspection-context fields with exact support slices. Private `profiles-private.json` contains the navigational extracts. Per-source caches support deterministic continuation. The database/retrieval lane imports these records into private SQLite/FTS and exports a sanitized public database; generated reading prompts must never be indexed as if they were observed answers.

`output-manifest.json` explicitly allowlists every public artifact and binds a separate private manifest. `verify_extraction.py` checks public type/source/edition/count joins, shard hashes, generated/candidate answer prohibitions and raw-text/private-path leakage. The private loader and independent audit check actual source slices. No new media downloads, ASR, human transcript validation or automatic card transfer occurs in this extraction.

## Executed full frame

The accepted v2 policy processed all **493 sources / 1,411,446 words**, producing **9,424 typed records**: 2,523 publisher-labeled Ra pairs, 6,408 unverified question candidates and 493 generated reading tasks. The automatic extractor produced no curated comparisons; that is a separate reviewed layer. Forty-one sources have neither documentary pairs nor unverified candidates and remain visible with their profile and generated reading task.

Four documentary pairs have editorial placeholders instead of recoverable question wording. An additional 107 printed response turns have no present matching questioner turn—often opening statements, not necessarily missing questions—and are not fabricated into pairs. Two punctuation-only candidates were skipped with explicit dispositions. Fifteen printed responses match the limited refusal/uncertainty surface pattern; this count is not a substantive refusal classifier.

The navigational digests contain 1,479 exact passages totaling 39,579 words. Of these, 133 are explicitly flagged fixed-word windows from long units. These are machine-selected excerpts, not a manual-reading denominator. The same full batch returned a verified complete resume hit with zero processing/inference; a separate private-bank corruption test was rejected. Twelve focused tests pass, including wrapped and quoted cues, refusals, same-ID pairing, source-bound digest windows, source/edition ID stability, public privacy and private resume tampering.

Public artifact bindings:

- `profiles.json`: `a63f3eb8963dcd13b520816c9582b6106e563b57fe0d7725f61a144c1bdc082b`
- `bank-index.json`: `b56a65397aaf4a47f72b708048e787bdf1aeb752a47ee4b9504dfbf3e47c3a72`

Together those initial files are 6.27 MB; the 493 separately loaded record shards total 11.24 MB. The private raw question bank is 29.97 MB and the private profiles/digests are 4.30 MB. Public and private byte counts describe different artifacts and must not be added as additional source observations.
