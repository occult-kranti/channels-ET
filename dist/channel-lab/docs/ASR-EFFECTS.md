# Paired recognition impact in fixed representations

This extension asks how replacing nine retained recording transcripts changes lexical and embedding similarities and nearest-neighbor displays. It is a paired **representation sensitivity**, not a speech-recognition accuracy benchmark. The primary 493-source frame remains unchanged.

The nine recordings were selected by the speech-to-text batch before these comparisons: all five retained OmNa recordings, plus the shortest eligible official Bashar, Tracy Kumbera, Multidimensional Soul and Athina recordings under the existing batch limit. This purposive set is not representative of the complete channels. The selection is not changed after viewing similarity results.

Two comparisons have different targets:

1. **Same retained audio:** compare each old ASR with its new Parakeet edition. Both source chains bind the exact encoded audio hash. Model, windowing and decoding settings differ, so the comparison does not isolate architecture causally.
2. **Selected canonical text:** compare the selected primary edition with the new ASR. Four primary editions are the old ASRs. Five OmNa primary editions are publisher-written messages, so those comparisons combine recognition and editorial/text-origin differences.

The old counterpart is accepted only if its exact artifact hash joins the canonical alternate-edition ledger and its normalized body reproduces the ledger's body hash. The new edition must have complete contiguous sample coverage, exhaustion flags, the same recording identity and its independently validated artifact hash. Full sample coverage is not word accuracy or successful recovery of every spoken word.

## Fixed-space calculation

The primary model supplies the frozen vocabulary, IDF, canonical sparse TF-IDF matrix, full-body MiniLM vectors, global source-name mask and exact encoder/pooling implementation. No topic model, vocabulary, IDF or model weight is refitted. The global name mask is reused exactly. New texts receive the same Unicode normalization and text transformations before encoding.

Four old ASR neural vectors are reused because they are the canonical bodies. The five other old ASRs must be encoded because only their written counterparts entered the primary model. Consequently the extension encodes 14 small texts—nine new recognitions and five old ASRs—and never reruns the 493-source embedding pass. The reconstructed lexical transform is checked numerically against the four canonical old ASR vectors.

For each pair, report lexical and neural cosine for both targets above. Surface counts compare whitespace words, lexical tokens, negation cues and number cues. Negation cues are `no`, `not`, `never`, `nor`, `cannot` and lexical tokens ending in `n't`; number cues are digit sequences and a declared finite dictionary of number/ordinal words. Rates use lexical-token denominators. These counters do not resolve sentence meaning, measure factual correctness or determine whether a qualifier survived.

The neighborhood experiment replaces all nine canonical vectors simultaneously, retaining the other 484 source vectors and a common candidate universe. Each source excludes itself. Ties break by stable source ID after descending cosine. Report the old/new top-five neighbors for the nine changed sources, their mean Jaccard, the all-source mean, the unchanged-source mean, and the count of unchanged sources whose neighbor sets changed. The latter exposes propagation through the candidate set; the all-source mean alone can hide effects by averaging over 484 unchanged representations.

Zero lexical/embedding representations remain unavailable, not zero similarity. Before/after neighbor comparisons use the same intersection of available source IDs. Undefined rates and empty neighbor comparisons remain null. The descriptive rows are dependent; no p-values or population accuracy estimates are produced.

## Artifacts and checks

`asr_effects.py` consumes the final frame, primary analysis, RAM model witnesses and completed full-batch ASR manifest. It emits the sanitized `asr-effects.json`, a three-panel SVG, and an explicit public allowlist. Full transcript bodies never enter these artifacts. Private RAM witnesses retain the replacement vectors, original ASR vectors, index mapping, all-source neighbor indices and exact artifact bindings for independent numerical reconstruction.

`verify_asr_effects.py` provides a standard-library public consistency/privacy gate. `test_asr_effects.py` exercises fixed vocabulary, origin distinction, unchanged-source neighbor effects, deterministic ties, zero representations, duplicate replacement rejection and accepted-body hash validation. Public checks do not substitute for independent private-source/numeric witness inspection.

Similarity is not correctness or agreement between answers. The older knowledge cards, evidence spans and interpretations stay bound to their original editions. Adoption of a new transcript requires a new source-bound reading; no automatic card or locator transfer occurs.

## Executed release

Run01 completed against frame02 and the completed nine-recording batch. Its public `asr-effects.json` SHA-256 is `f24e59afa4d71cad30432c990e484a0d51cd8c7c4703899462daf3bab272a0b5`. Four old primary vectors were reused; 14 small texts produced 112 encoder chunks in 6.86 seconds on one CPU thread. This is measured invocation time, not a matched speedup or accuracy benchmark. The portable baseline witness only changes the feature-name array from object to Unicode dtype; every numerical array remains exactly equal to the original witness.

| Observed descriptive result | TF-IDF | MiniLM |
|---|---:|---:|
| Same-audio old/new ASR cosine range, nine pairs | 0.930–0.993 | 0.964–0.990 |
| Mean top-five Jaccard for the nine replaced sources | 0.661 | 0.578 |
| Mean top-five Jaccard across all 493 sources | 0.992 | 0.985 |
| Otherwise unchanged sources with a changed neighbor set | 2 of 484 | 11 of 484 |

The large all-source averages dilute changes among the nine replaced representations. High whole-document cosine can coexist with changed retrieval neighbors. Five written-primary OmNa comparisons additionally reflect text-origin differences and must not be presented as recognition-only changes.

Same-audio ASR word counts changed from 15,215 to 15,300. Across the nine pairs, surface counters changed by one net negation cue, seven number-word cues, and minus five digit-number cues. These are formatting-sensitive aggregate differences, not verified meaning changes or corrected errors. Exact per-source before/after counts and neighbor lists are in the public artifact; source texts and the 217,640-byte numeric witness remain private.
