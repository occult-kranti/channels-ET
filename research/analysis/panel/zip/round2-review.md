# Round 2: source reconciliation review

## Work completed

- Independently reconstructed the round 1 numerical inclusion, binding, mean, median and missingness checks from raw supplied CSVs. All eight checks passed.
- Compared eight purposeful known-duration cases from eight accounts with current watch-page metadata acquired by the corpus worker. All eight account IDs matched; six durations matched exactly and two differed by one second.
- The acquisition is shared with the corpus worker. This is fresh-context review, not independent second-source corroboration.

## Corrections carried into the next build

| Video ID | Required treatment |
|---|---|
| MDdyY1WYmHY | Fresh watch metadata verifies 3,206 seconds (53:26); override inherited exclusion using new provenance. YouTube date is 2026-09-25, while notes refer to a 2026-09-30 podcast release. Preserve both date roles. |
| 7wrxKKVLcBA | Supplied English title differs from current German title; preserve both and identify which text feeds NLP. |
| g88RqksSChM | Supplied English title differs from current Spanish title; preserve both. |
| t_OYRnFXEHQ; xxbzklPyRtg | Supplied English titles differ from current Portuguese titles; preserve both. |

## Interpretable results and boundaries

Source metadata supports available-case duration comparisons; it does not support channel-wide means from a capped recent-upload sample. Duration differences of one second have no practical effect on rounded minute-scale comparisons, but raw values should remain available. Metadata conflicts can reflect title localization or revision and must not be framed as deception.

English keyword indicators cannot assign zero-topic absence to non-English titles. Language-separated or multilingual analysis is required before interpreting cross-channel semantic differences. A duplicate promotional title in Daniel Scranton and Pamela Aaralyn samples is a dependency, not evidence of shared independently channeled content.

## Evidence

- `round1_integration_checks.json` / `check_round1_integration.py`
- `round2_metadata_spotchecks.json` / `verify_fresh_metadata.py`
- `skills-fragment.json`

## Remaining review

Confirm these source corrections in the next built data; inspect final account mapping and captions after the fresh metadata batch. The semantic-topic conclusions require separate transcript coverage and stability checks.

## Frozen round 2 build review

Reviewed `research/analysis/rounds/round2/data.json`, SHA-256 `f5b96cd04d9fb9ccf5db34e0fc0b056f0dc3d7a53579b86361f90d9861dc5024`. Independently checked 340 fresh durations, 341 fresh publication dates, 341 fresh titles and their account bindings, plus 418 remaining inherited durations. Every field matched the source record identified by its retained HTML hash; inherited values remained explicitly unverified. No blocking data errors found.

Four account display names should replace generic “Related account” labels with the acquired publisher: The Galactic Guide, David Lotherington, Running With Spirit - Jake, and The Moore Show. Numeric account identity and video membership are correct. Exactly one Ishuwa account exists in this frozen snapshot and its matching SVG.

The four localized title cases retain prior English variants and are excluded from English title indicators. Athina’s duration now uses fresh metadata. Seven one-day inherited/fresh date differences may result from UTC normalization; they should not be presented as substantive contradictions without further evidence.

Reproducible checks: `check_round2_integration.py` and `round2_integration_checks.json`.
