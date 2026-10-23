# Extraction panel — new round 1

Role: AI extraction/database reviewer. This is not human peer review.
Baseline: committed `data/digests/`, frozen Atlas data and latest handoff at
GitHub main `1d6eb36`. Raw caption text is absent from available workspace
shared/scratch/library-files locations; acquisition subsequently reported
blocked new caption access. No transcript content is inferred from frozen
numeric embeddings.

| Finding | Evidence | Decision and implementation | Acceptance |
|---|---|---|---|
| No prior separate queryable Q&A store | 949 `qa_topics` entries in committed source digests | Build provenance-linked SQLite, JSON and CSV, source hash/pointer, keyword codebook | 949 exact source strings and hash pointers checked |
| 75 digests does not mean 75 Q&A documents | Eight digests have no candidate pairs | Report 75 source digests, 67 with pairs | Source-total reconciliation |
| Context is one practitioner, with mixed formats | All 949 pairs inherit Darryl Anka/Bashar; 353 pairs are in 20 interview videos | Keep practitioner, entity context and publisher separate; never infer turn speaker or cross-medium agreement | Zero speaker assertions/timestamps; cross-practitioner comparison false |
| Missing publisher IDs were accidentally collapsed in the first implementation | 105 rows have null publisher ID but seven distinct inherited names | Separate 27 known ID groups and seven unresolved name groups; unknown same-publisher is null | Publisher totals and null handling verified |
| Repetition may be a shared session | Multiple near/exact questions occur across the same uploads | 127 retrieval pairs, exact-wording sensitivity, duplicate-source flags; session independence unknown | Every pair retains no-agreement/no-independence qualifications |
| Question themes can differ from answer mechanisms | 20 model close-read source pairs; contact question can receive formula advice | Separate overlapping question and answer keyword fields; qualitative notes in `close-reading.json` | Twenty candidate IDs resolve, source depth disclosed |
| Future transcript extraction needs timestamps and a release boundary | Existing digests have no segment times | Add external-only raw caption-window CLI with hash/feature manifest | Synthetic boundary and Git-output rejection tests only |

Implementation output: `research/expansion/qa/`. Source text was reused only
from already released derivative digests; no raw transcript or full video was
added. The source of each paraphrase remains explicit. Candidate counts describe
the earlier digest generator's selections, not all questions in a recording.

Initial executed validation: 4,090 checks passed, covering all 949 source
hash/pointer/string joins, source identity, 106 identity coverage rows, SQLite
integrity/foreign keys and pair qualifications. See `qa/verification.json` for
the current artifact hash. Later reviews must bind the changed files, not reuse
this receipt as proof of a new revision.
