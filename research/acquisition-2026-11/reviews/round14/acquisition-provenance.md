# Round 14 — Acquisition and provenance review

Snapshot: `research/acquisition-2026-11/reviews/round14/snapshot.json`, canonical payload SHA-256 `677b2b7a9b831c0d03eaa21362d2db15ca0f144dbb3adf5dc33d20b5eed4d136`. AI technical review only; not human peer review.

## Verdict

Conditional PASS. No blocker or high-severity defect within the frozen snapshot. The candidate partition, 35 audio files, 2,840 records/302 accounts, 733 selected IDs and exactly 100 Bashar-selected records reconciled. `uploaded_total` remained null and no full-channel census was claimed.

## Findings and required follow-up

- **M1 — selection join:** `ctgvKZcIWIg` was `candidate_unreviewed` in `all-candidates.json` but `selected_default` in `video-reference.csv`. Normalize the candidate and supplemental records, and add a candidate/reference selection-agreement check.
- **L1 — mixed candidate schema:** the original 13 records lacked `selection` and `rightsStatus`. Normalize all 43 records to one key set.
- **L2 — implicit hold:** the route-limit hold was absent from the acquisition ledger. Add an explicit terminal `held_route_limit_over_150_minutes` record.
- **L3 — quarantine bytes:** `mediaBytes: 0` could be misread as absence of retained quarantine audio. Add admitted-byte, quarantined-byte and quarantined-hash fields.
- **L4 — snapshot scope:** the 23-file snapshot did not bind the raw tree; later corrections require a new snapshot rather than reuse of this receipt.
- **L5 — browser instrumentation:** linked JSON/CSV registries need fetch checks in addition to screenshots. The staged verifier supplies them; retain that evidence.
- **L6 — summary semantics:** `completedRecords` includes the language-excluded audio and could be added naively to the language count. Add `completedAudioRecords` and an explicit meaning field.

## Post-snapshot quarantine follow-up

The regenerated German receipt was independently rechecked: all four quarantined files match the new hashes, including the partial segment JSONL; settings and code hashes are bound and the code snapshot verifies. A stale nested receipt remained and was to be renamed as unverified legacy evidence.
