# Round 14 — ASR methods review

Snapshot: `research/acquisition-2026-11/reviews/round14/snapshot.json`, canonical payload SHA-256 `677b2b7a9b831c0d03eaa21362d2db15ca0f144dbb3adf5dc33d20b5eed4d136`. AI technical review only; no retranscription and no human WER.

## Verdict

Conditional PASS; no blocker or high-severity finding. Independent checks confirmed pinned settings, full 300-second-window coverage, 105 output hashes, 35 audio hashes, terminal-state protections, six historical code hashes, German quarantine, Aurora edition mismatch handling, and `humanValidated=false`.

## Findings and required follow-up

- **M1 — snapshot scope:** include the transcriber, all code-edition snapshots and `research/harvest/asr/model-manifest.json` in the next review snapshot.
- **M2 — quarantine chain:** the legacy German receipt lacked settings/code hashes and did not bind the partial segment JSONL. Regenerate it with the pinned code, bind all four files, and require settings/code validation on exclusion reuse.
- **M3 — language trigger:** non-English detection required degenerate statistics before quarantine. Quarantine on detected German/Arabic regardless of degeneracy; retain the provider-edition exception for coherent English audio such as Aurora.
- **L4 — terminal transitions:** block or explicitly confirm exclusion-to-completed and other terminal-to-terminal transitions.
- **L5 — reuse race:** perform reuse validation inside the per-video lock.
- **L6 — output binding:** assert exactly three completed output keys in the verifier instead of allowing an empty map to no-op.
- **L7 — snapshot recipe:** document canonical JSON minus `snapshotSha256` as the digest recipe.
- **L8 — tail coverage:** segment-end coverage cannot detect VAD-misclassified trailing speech; retain the documented limitation.
- **L9 — staging drift:** always restage before publication claims.

## Residual limitation

Four legacy code editions have no surviving source snapshot. Their 12 records rely on artifact-level verification only. The current atomic edition initially produced no records; the subsequent German quarantine regeneration supplies an actual current-edition exclusion receipt.
