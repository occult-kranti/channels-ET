# Paper round 8: challenge, correction and rendered verification

This is the second new expansion loop, following the frozen round-7 implementation. Review roles are model agents, not human peer reviewers.

## Artifact reviewed

Initial expansion PDF: SHA-256 `12bbbd2a4bc71a611e790170676db2fa53deb0f202ce9251234bddf388e4fc7c`, 21 pages. Root, methods and quantitative roles inspected source/text and figure output. Paper role rendered all initial pages and observed the full-commit line overflow. The quantitative role observed a negative-control legend/line collision in the actual plot and corrected its source.

## Applied changes

- Replaced implied execution of collector packages with the actual status: dependencies installed/import-tested, watch preflight performed by `urllib`, no successful new collection.
- Aligned query descriptions with the 590 planned templates; spelling variants are future sensitivity, not executed searches.
- Specified question/answer separate TF-IDF fits, word unigram/bigram features, English stopwords, sublinear TF, smooth IDF, L2 normalization, and distinct-upload question cosine cutoff 0.40.
- Removed misleading prospective/preregistered language and clarified schema/prior-summary inspection before new calculations.
- Removed unexecuted caption-selection resampling language; only deterministic quantiles and actual publisher-label controls are described.
- Added 11 within-publisher/289 between-publisher matched pairs, 11 eligible plus 3 singleton publishers, equal-account and leave-one-publisher-out values, and representation-specific cross-layer difference.
- Kept six paired medians at zero and society as the actual sign reversal; no claim of seven reversals.
- Used generated Q&A coverage: 67 Q&A-bearing of 75 source digests, 949 candidates, 27 resolved publisher IDs, 105 unresolved-ID candidates in seven inherited-name groups; all one practitioner context.
- Added an unexecuted future-analysis matrix with evidence, unit, comparison/falsifier, confounds and plot design, plus complete 20-case and 12-pair model-reading ledgers.
- Replaced unbreakable full hashes in prose with short commits plus full manifest identities, shortened a table header, and corrected long-table widths.
- Re-copied the corrected negative-control plot with a nonoverlapping legend.

## Verification

Corrected manuscript: 24 pages, PDF SHA-256 `b8df4a2ba9f4b9a09fda4ebe0959e9731fa84f769e3023f08910a4548b6cb12d`. Source ZIP SHA-256 `a6db21a9a5f693ab87f645fc477c1d0b0ace8ad2ae87b4f6a57fbd3168dd77b7`.

All four compilation steps returned zero. Final LaTeX pass has zero overfull boxes and no undefined citations/references. All 24 pages were rendered; the contact sheet and full-size pages 13/22 were inspected for plot legends and table boundaries. A clean extraction of the source ZIP compiled with PDFLaTeX/BibTeX and produced identical extracted page text. Exact commands and paths are in `paper/verification.json`.

No raw-caption re-inference, new platform retrieval, audiovisual close reading, human annotation, human peer review or submission is claimed. New evidence availability remains a material external limitation.

Status: round-8 paper implementation and bounded checks complete; ready for round-8 freeze and final round-9 review.
