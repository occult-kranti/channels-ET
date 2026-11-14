# Round 14 — Dashboard and release review

Snapshot: `research/acquisition-2026-11/reviews/round14/snapshot.json`, canonical payload SHA-256 `677b2b7a9b831c0d03eaa21362d2db15ca0f144dbb3adf5dc33d20b5eed4d136`. AI release review only; no merge or publication approval.

## Verdict

Staged preview PASS; PR FAIL pending CI portability and timeout fixes. All 505 staged files verified, acquisition numbers reconciled, and desktop/mobile browser checks were clean. No deployment was performed.

## Findings and required follow-up

- **B1 — nonportable package root:** `package_acquisition.py` used a workstation-absolute repository path. Derive the root from `__file__` so Pages CI can run the package step.
- **H1 — Pages timeout:** the full build could exceed the 10-minute job timeout. Use a 45-minute budget for the legacy full-build workflow and retain the newer main branch’s checked-in-static path with an appropriate budget.
- **M1 — required assets:** add the stylesheet, ECharts bundle and three local fonts to required-file and HTTP-route checks.
- **L1 — snapshot recipe:** document canonical compact JSON with `snapshotSha256` omitted.
- **L2 — packaging gate:** bind `candidateIdsSha256` before packaging as well as during final site verification.
- **L3 — interaction evidence:** record view navigation, inspector, theme and release-collapse checks, not only page loads.
- **L4 — mobile CSS:** retain a specific compact-screen acquisition link and avoid future cascade regressions.
- **L5 — path scrub:** scan CSV and non-`/mnt` workstation prefixes at package time.
- **L6 — dirty scope:** disclose that static-input dirtiness covers `index.html`, `.nojekyll` and `dist`; review snapshots bind research/scripts separately.

## Release boundary

The reviewer verified October baseline versus November actual separation, 35 audio/34 analyzed/43 terminal candidates, public artifact hashes, and the raw-workspace-unavailable fallback. Live Pages verification and merge remained out of scope.
