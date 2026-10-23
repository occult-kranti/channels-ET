# Round 3: final provenance and attribution review

**Result: passed.** No blocking source-precedence or account-binding errors were found in the frozen phase 1 build.

Reviewed data SHA-256: `f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc`.

Reviewed metadata-input SHA-256: `223f4212cd027ae5d190c2ec164a1b1b5b00312117070af3ffcfd36ff1c32ad0`.

## Checks completed

The independent audit matched 877 fresh duration values, 878 fresh UTC publication dates, 878 fresh titles and 878 current account bindings to their retained watch-page metadata and HTML source hashes. Four remaining duration values match the supplied CSV and remain explicitly marked unverified. All account aliases resolve to a single group. No observed publication date is in the future relative to the declared check date. The four language-localization cases preserve earlier titles and remain outside the English title model. Athina's 53:26 duration is now supported by current metadata.

The generic “Related account” names identified in round 2 are corrected wherever a fresh publisher is available. Brad Johnson's interview video `KtvDmi4JWyc` now belongs to uploader Multidimensional Soul; the interview publisher is not merged with Brad's account. The export preserves inherited `publisher` separately from current `observedPublisher`.

## Reconciliation with the supplied ZIP

Current metadata succeeded for 453 of the 457 linked ZIP videos. Among 446 comparable durations, 229 match exactly, 216 differ by one second, and one differs by two seconds. Ninety-two titles differ or are localized; these differences do not themselves establish source error or deception. Exactly one supplied numeric account ID differs from the current uploader: the Brad Johnson interview above.

The complete acquisition input contains 925 attempted videos: 878 successful metadata retrievals and 47 failures. A failure is not evidence that a video, channel or medium is absent.

## Scope of approval

This approves the checked metadata transformations and attribution rules. It does not establish channel-wide means, population activity prevalence, the accuracy of every caption, or the claimed ontological source of channeling. Another worker performed the source acquisition, and this reviewer reconstructed the checks from those records; the review is independent in context, not a second independent source.

## Reproduction

Run `python research/analysis/panel/zip/check_source_precedence.py round3` from any directory. Frozen source inputs are read from `research/analysis/rounds/round3/`. No caption bodies or full transcript text are included in this audit folder. Numerical figure/statistics review and interface review are recorded by the other panel workers.

A final prose-only caption correction changed the prior data hash `8615040031871018dd25607f659d2294a3624a41074f11ab0bbcfad31f520920` to the reviewed hash above. The source-precedence audit was rerun successfully on the final bytes. The input hash and all checked counts remain unchanged.
