# Round 4: frozen PDF methods and figure review

Reviewed `research/paper/rounds/round4/main.pdf`, SHA-256 `a395941231d063d3faab18f0ea90766438ed9c1135a612102b92f1edb6ee9bc1` (10 pages). The actual rendered pages 3–8 were inspected. Manuscript source and a text page map were also read; this is not a claim that all ten pages received visual inspection.

**Round 4 review is complete. The draft requires the following corrections in round 5 before final release.** No new analyses were added during this PDF review.

| Finding | Actual PDF evidence | Required correction |
|---|---|---|
| P4-F1 — blocking figure accuracy | Page 7, Figure 3A begins its title-cosine x-axis at zero, clipping negative observations present in the underlying CSV. | Include the negative data range; preserve all 55 observations. |
| P4-F2 — figure layout | Page 6, Figure 2 legend overlaps the Divine Insights interval row. | Move legend clear of all data. |
| P4-F3 — figure layout | Page 8, Figure 4A annotation 0.969 crosses the lower axis. | Place annotations with clearance from axis and labels. |
| P4-F4 — figure typography | Some labels concatenate counts and words, including publisher/pair counts. | Restore ordinary spacing in generated labels and prose. |
| P4-M1 — construct interpretation | The PDF attributes the masking result to identity vocabulary, while the actual mask also removes genre and packaging terms such as channel, transmission, message, official, galactic and council. | Consistently call this the predefined name-and-genre mask and say that names and generic terms were not separately ablated. |
| P4-M2 — measurement reproducibility | Methods refer to trimming words without distinguishing the whitespace split used for trimming from the regex tokens used for keyword rates. | Specify trimming whitespace-separated tokens after masking, with floor 10% removed at each end. |
| P4-M3 — coverage wording | Page 5 says the refresh supplies measured duration for 95.2%, although the denominator includes four inherited durations. | Say usable duration coverage, comprising 877 fresh and four inherited observations. |

The actual Figure 3 caption and full-width layout resolve P4-M4: both scatter and LOPO panels are now described, with the denominator and dependent-pair limitation. The earlier source receipt remains a historical record of the initial draft.

Equations (1) and (2) render clearly and agree with the implemented per-video rates, equal-chunk pooling and equal-video account means. Coverage distinguishes 25 eligible matched videos from the 22 that contribute to 11 account centroids. The larger caption matrix uses 26 contributing videos in 13 groups, while the full pilot contains 30 videos across 17 groups. Figure 1 is readable at full width. The LOPO plot exposes the negative lower bound and labels its influence range descriptively, consistent with the independent calculation recorded in `round4-lopo-independent.json`.

The draft appropriately identifies the work as retrospective and exploratory; it does not invent human validation, a population sampling frame, causal identification, ontological verification, peer review, or submission. No additional numerical discrepancy was identified in the reviewed PDF content. Closing the listed items against a newly built round-5 PDF, and then independently reviewing a round-6 final freeze, remain necessary.
