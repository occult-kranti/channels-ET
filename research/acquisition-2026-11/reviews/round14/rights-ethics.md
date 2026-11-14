# Round 14 — Rights, ethics and release-boundary review

Snapshot: `research/acquisition-2026-11/reviews/round14/snapshot.json`, canonical payload SHA-256 `677b2b7a9b831c0d03eaa21362d2db15ca0f144dbb3adf5dc33d20b5eed4d136`. AI technical review only; not legal advice or human peer review.

## Verdict

Conditional PASS for the acquisition package: no media, full transcripts, credentials or model weights were found; public Q&A is hash-only and review excerpts are bounded. Rights, Drive quota, source-role and code-edition wording was honest.

## Findings and required follow-up

- **M1 — post-snapshot drift:** the code-edition manifest changed after capture and the public copy lagged. Repackage, reverify and create a new snapshot.
- **M2 — workstation paths:** new Git-bound receipts/scripts contained absolute paths; broader legacy Pages artifacts also expose historical workspace paths. Parameterize private roots, sanitize public summaries, scan the release, and keep any legacy remediation separate and explicit.
- **M3 — boundary checks:** widen path-prefix and media-suffix checks, enforce review-note length limits, and extend transcript-leak probes to public SQLite and generated HTML.
- **L1 — fragile redaction:** use a hard failure for path-shaped strings instead of relying only on a narrow denylist.
- **L2 — platform terms:** state that converter-assisted acquisition may be subject to YouTube/provider terms and that public availability does not establish download or redistribution permission.
- **L3 — legacy license wording:** where Bashar material is discussed, distinguish absence of full transcripts from the presence of bounded attributed quotations.
- **L4 — unused editions:** mark code editions with no produced receipts as provenance-only; do not imply they generated current artifacts.

## Scope note

The reviewer did not accept source hashes as redistribution rights, speaker identity, original-session identity, ET origin, or truth. Those boundaries remain unchanged in the corrected release.
