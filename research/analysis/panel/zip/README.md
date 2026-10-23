# ZIP audit and source reconciliation

This folder records the independent review of the supplied Claude draft and its integration into the channel-analysis dashboard. It includes metadata and numerical audit evidence only; no caption bodies or full transcript text are included.

- `audit.md` and `audit.json`: initial archive inventory, eligibility rules, limitations and corrections.
- `raw-metadata/`: exact copies of the two supplied metadata CSVs used by the independent checks, retaining their original file hashes.
- `source_manifest.json`: member paths, byte lengths and SHA-256 hashes for the supplied archive; it authenticates bytes, not factual claims.
- `check_round1_integration.py`: reconstructs the initial union, duration eligibility, account bindings and averages directly from the raw CSVs.
- `check_source_precedence.py`: verifies a frozen round against that round's metadata snapshot, without importing producer code. Run `python check_source_precedence.py round3`.
- `round2_metadata_spotchecks.json`: eight purposeful source-to-source cases, plus available comparisons at the time of the check.
- `round2_source_precedence.json`: checks the pinned round 2 data and acquisition hashes.
- `skills-fragment.json`: application of the investigative-evidence and temporal-evidence methods.

A separate worker reconstructed these comparisons, but the YouTube acquisitions were shared with the corpus worker. This is fresh-context review, not independent second-source corroboration. Source-supplied, current metadata, derived values and unresolved observations remain distinct.
