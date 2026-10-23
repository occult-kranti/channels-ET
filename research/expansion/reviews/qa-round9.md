# Extraction panel — final round 9 corrections

Reviewed round-8 archive SHA-256:
`03654cafae00e7fc15bdd1f30b60cfcc75fb1047b774036d931eb2bb79e64bc3`.
Role: AI extraction/database reviewer. No independent human labels or audiovisual
validation were added.

| Review finding | Implemented correction | Observed result |
|---|---|---|
| CSV serialization confused false values with missing values | Serialize booleans as literal JSON `false`; unknown values remain empty | All 949 CSV records preserve false speaker/human flags and empty timestamp/entity-speaker fields |
| Empty-string formula guard accidentally emitted an apostrophe for null | Guard formula-prefix check with a nonempty string condition | Unknown fields remain empty, formula escaping preserved |
| Retrieval threshold 0.40 was arbitrary and no threshold sensitivity was visible | Recount retained candidates at 0.40–0.90 | Counts 127,73,47,34,24,18; corresponding distinct upload-pair counts71,34,19,11,11,9 |
| Many matches may concentrate in reused uploads | Add upload-pair concentration diagnostic | 71 distinct upload pairs; top three supply30/127=23.6%; original sessions unresolved |
| Summary silently previewed100 of127 pairs | Add `questionPairsPreview` shown/total/truncated/fullArtifact metadata | 100 shown,127 total, full export remains `question-pairs.json` |
| TF-IDF reproducibility relied on implicit defaults | Record complete tokenization/IDF/normalization parameters | Word uni/bigrams, English stop words, smooth IDF, sublinear TF, L2, min_df1/max_df1.0, default two-character word tokenization |
| Future caption-window input validation was incomplete | Validate11-character ID, every finite nonnegative start/duration, order and ASR flag | Malformed synthetic inputs rejected; whole segments crossing120s end cap excluded; overlapping segment ends use their maximum and question-end boundaries are retained |
| Future manifest omitted important provenance | Preserve language, ASR status, source URL basis, unverified inherited labels and explicit candidate type | Missing values remain unknown; no speaker, human review or fetched-URL assertion added |

`qa/verification.json` records **4,156 passing checks**, including all949 source
hash/pointer/string bindings, CSV semantics, threshold/concentration counts,
SQLite integrity and foreign keys,20 digest close readings and12 paired
annotations. Caption import tests are synthetic fixtures only. No empirical
caption-window precision or recall is claimed.

`qa/reproduction.json` records byte-identical regeneration of eight outputs in
a fresh temporary directory. Current summary SHA-256:
`7cc9705a73bed33523397b0e4812bb47974dfc21a8a48c83d294c53948a46128`.
The 949 candidate pairs,67 Q&A-containing digests, one-practitioner scope,
27 resolved publisher IDs plus seven unresolved name groups, and all106
candidate identity coverage records remain unchanged.
