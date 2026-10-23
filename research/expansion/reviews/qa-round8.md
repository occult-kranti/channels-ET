# Extraction panel — round 8 challenge and revision

Reviewed artifact: round-7 candidate database and summary, including the
corrected 27 known publisher IDs plus seven unresolved name groups. This round
adds source-linked interpretation rather than relabeling inherited digests as
new transcripts. Role: AI extraction reviewer, not human peer review.

## Findings and changes

1. **Low lexical answer cosine cannot be called disagreement.** A contact
   preparation question receives passion/formula and personal-vibration advice
   in two gists, but their answer cosine is approximately 0.056. A life-purpose
   pair similarly uses compatible language at cosine 0.346. Added 12
   source-bound, model-assisted paired readings with explicit undetermined
   agreement classifications. These are examples, not validation scores.
2. **A precise relative prediction cannot be placed on a timeline without its
   recording date.** One pair says approximately two years versus a broad
   2025–2033 window with a later bound. The annotations retain unresolved
   recording dates and do not call the pair a chronological contradiction.
3. **Repeated question sequences may mark reused source sessions.** The
   executed sensitivity keeps all 949 normalized question-and-answer pairs,
   but only 936 normalized questions. Removing 15 identical-question matches
   leaves 112 of the 127 retrieval pairs. Eleven upload pairs have multiple
   similar-question matches. These are shared-source leads, not identified
   original sessions or independent observations.
4. **New model readings need fresh artifact bindings.** Each side of every
   paired reading now carries the candidate ID, source URL, path, hash and
   JSON pointer. Added a separate `model_pair_reading` SQLite table. The
   original candidate count and no-speaker/no-timestamp schema remain.
5. **Caption-window infrastructure must not imply real caption execution.**
   README identifies v1 SQLite as digest-specific. The separate future
   caption-window CLI has only synthetic fixture validation, no real-corpus
   precision/recall or recovered speech turns.

## Acceptance evidence

`qa/verification.json`: 4,128 checks passed, including all 949 source
hash/pointer/string bindings, SQLite integrity and foreign keys, all source-bound
paired annotations, and caption-window synthetic tests. Reproduction uses a
fresh external output directory and compares eight generated artifacts byte for
byte; see `qa/reproduction.json`. No caption text, human labels or new
cross-practitioner findings were added.

The paired subset is purposive: first 12 distinct left-question strings in
descending question-cosine order, tied by candidate IDs. It cannot estimate
annotation accuracy, population agreement, or contradiction prevalence.
