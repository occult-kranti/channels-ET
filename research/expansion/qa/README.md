# Candidate question and answer database

This release contains **949 inherited AI-digest question/answer-gist pairs from
67 of 75 Bashar Index digests**. All pairs share an inherited Darryl Anka
practitioner context and Bashar entity context. The contexts do not identify who
spoke each answer. Interview speech, claimed channeling, clips and mixed formats
are retained separately. There are **27 resolved publisher-group IDs**, plus
**7 unresolved publisher-name groups** containing 105 pairs. A publisher is a
distribution route, not a different medium.

All 106 inherited practitioner/lineage candidate records are retained in
`practitioner-coverage.json` and SQLite. One has digest-derived Q&A; 105 have
no usable Q&A text in this release. Their entity and account edges are inherited
source leads rather than revalidated identities. Zero missing-text rows were
filled with invented answers. Cross-practitioner answer comparison is unavailable.

## Rebuild and verify

From the GitHub repository root, using the analysis environment:

```sh
python channeling-atlas/research/expansion/qa/build_qa.py
python channeling-atlas/research/expansion/qa/verify_qa.py
```

The builder reads `data/digests/*.json`, the frozen Atlas data, and the current
acquisition practitioner frame. It does not collect videos or alter the old
analysis. `qa-candidates.sqlite`, JSON and CSV are alternative access formats
for the same derived candidate rows. `source-manifest.json` preserves the file
hash, JSON pointer, watch URL, digest-generation date and original digest-source
URL. The upstream source field frequently points to youtubetotranscript.com;
this release **reuses the committed digest**, and does not claim a new fetch
through that service. No raw captions are published.

The SQLite schema is **v1, specific to digest paraphrases**. Its constraints
require unknown speaker/timestamp fields and no human-reviewed flags. Verified
transcript turns need a separately versioned schema migration; they must not be
silently inserted into this table or relabeled as existing evidence. The future
caption-window CLI writes a separate candidate artifact and does not update the
digest database.

```sql
SELECT name, qa_candidate_count, qa_availability
FROM practitioner_coverage ORDER BY qa_candidate_count DESC, name;

SELECT q.id, q.question, q.answer_gist, s.source_url, q.source_pointer
FROM qa_candidates q JOIN sources s USING(video_id)
WHERE q.id = 'qa-0htF1V0v6ec-007';
```

`verify_qa.py` checks all 949 source hashes/pointers, exact source strings,
video identity, attribution gaps, database integrity, foreign keys and every
similar-question pair's release qualification. Its caption-window tests use
synthetic fixtures and cannot establish empirical caption extraction accuracy.

## Keyword and similarity methods

`codebook.json` contains complete case-insensitive regular expressions for eight
overlapping subject categories. Each expression is applied separately to the
question and answer gist. The question and answer counts have denominator 949
digest pairs. They are not full-transcript topic rates, shares of speaking time,
or validated measures of what an entity believes. The qualitative subset
demonstrates why question themes and answer mechanisms need separate fields.

Question retrieval uses English-stop-word-filtered, sublinear word unigram and
bigram TF-IDF vectors with L2 normalization. All pairs from different uploads
with cosine at least 0.40 are retained: **127 candidate pairs**. An independent
answer-gist TF-IDF vector space supplies an answer lexical cosine, which is
explicitly **not an answer-agreement score**. All pairs remain within one
practitioner context. Different uploads can reuse the same original session.

There are 936 distinct normalized question strings and 11 repeated-question
groups. An exact normalized question-and-answer-gist deduplication retains all
949 rows; different paraphrases can survive this check. `summary.json` reports
the pair sensitivity excluding repeated question wording and flags upload pairs
with multiple similar questions as possible shared-source candidates. Neither
operation resolves original-session identity.

Keyword extraction ranks the 100 largest sums of normalized TF-IDF question
features and includes document frequencies. Answer modality indicators match
possibility, conditions, probability language, absolutes and sentence-initial
imperatives. Overlapping marker counts are lexical diagnostics, not calibrated
epistemic confidence or a measure of deception.

Retrieval volume depends on its threshold: the retained candidate-pair counts
are 127, 73, 47, 34, 24 and 18 at cosine thresholds 0.40, 0.50, 0.60, 0.70,
0.80 and 0.90. These are exploratory retrieval sensitivities, not equivalence
accuracy estimates. At 0.40 there are 71 distinct upload pairs; the three
largest upload-pair groups supply 30 of 127 matches (23.6%). Concentration can
reflect shared topics or reused sources; neither interpretation is established.
`summary.json` deliberately previews only 100 of the 127 question-pair records;
its `questionPairsPreview` field discloses truncation. `question-pairs.json`
contains all 127. The CSV uses literal `false` for boolean negatives and empty
cells for unknown values; unknown timestamps are not zero.

`close-reading.json` records 20 AI-assisted readings of actual digest pairs,
selected as the first pair from evenly spaced filename-sorted nonempty digests.
The notes identify advice, cosmology, nested attribution, precise forecasts,
health claims and question/answer theme mismatches. They are model annotations,
not human labels, independent source validation or an audio comprehension audit.

`pair-close-reading.json` adds 12 exploratory paired readings. Selection takes
the first 12 distinct left-question strings from descending cosine order with
candidate-ID tie breaks. Source hashes and pointers bind each side. These are
purposive high-similarity examples, not a representative validation sample.
All classifications retain undetermined answer agreement. For example, similar
preparation advice can have low lexical overlap; different relative/absolute
contact windows cannot establish temporal drift without reliable recording dates.

## Future caption windows

`ingest_captions.py` accepts an authorized local document with
`video_id` and `segments[]` containing `text`, `start` and `duration`.
Question-mark-bearing segments are followed by at most 12 segments or 120
seconds from the question start, stopping at the next question mark. A whole
segment whose end crosses the cap is excluded rather than truncating text
without alignment. IDs and all segment times/durations are validated, including
nonfinite, negative and out-of-order values. This is an **experimental
punctuation-window heuristic**, without diarization, robust ASR punctuation,
speaker turns or answer-boundary validation.

```sh
python channeling-atlas/research/expansion/qa/ingest_captions.py \
  /workspace/channeling-raw/authorized-caption.json \
  /workspace/channeling-raw/fresh-question-windows.json \
  /workspace/channeling-raw/fresh-window-manifest.json
```

Choose fresh output paths. Raw windows are rejected inside a Git checkout.
The manifest contains timestamps, hashes, language/ASR status, supplied
unverified practitioner/entity/publisher labels and derived keyword categories,
but no question or answer text. Missing language, ASR and attribution remain
unknown. A canonical URL derived from video ID is marked as not fetched.
The script was tested with synthetic fixtures;
**no real caption-window run is claimed**. Before an empirical run, establish
the input's access/release basis and manually or human-review a stratified
subset, including false positives, missed questions and non-answer segments.
