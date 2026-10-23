# Round 5: independent methods and rendered-PDF review

**Verdict: pass for the reviewed methods, corrected figures, and derived numerical results. No new blocking methods finding. A final round-6 freeze review remains required.**

The actual 12-page frozen PDF is `research/paper/rounds/round5/main.pdf`, SHA-256 `b009dbb772b562494d27251239334c42a70934424ac74bc2c5230f06f7bc2be0`. Its body SHA-256 is `ba9a08bab6c8a2864ebc920180a566468b43ef8f3308a7142b8e1fcd5999e387`; generated results SHA-256 is `45175aa2e4422828b70ca68fe878ca275217887f9fb925ff8ab7c5a576ff8604`. Rendered pages 4–9 were visually inspected, covering methods, all four figures, tables, results and the core limitations. Other pages were not claimed as visually reviewed by this panel.

## Closed findings from round 4

| Finding | Round-5 closure evidence |
|---|---|
| P4-F1, clipped negative scatter values | Figure 3A now extends below zero and visibly includes the negative title-cosine observations. |
| P4-F2, overlapping duration legend | Figure 2 legend occupies open space clear of every interval. |
| P4-F3, sensitivity annotation crossing axis | Figure 4 has four separated rows and labels above the lower-axis region. |
| P4-F4, concatenated labels | Publisher/pair labels and generated prose use ordinary spaces. |
| P4-M1, mask construct | Abstract, methods, table and discussion consistently describe a name-and-genre mask; the paper states that names and generic terms were not separately ablated. |
| P4-M2, trimming token definition | Methods explicitly use whitespace-separated tokens after masking, floor 10% at each end, and distinguish keyword-rate tokenization. |
| P4-M3, duration source wording | Abstract and results identify combined fresh and inherited usable coverage, including four inherited durations. |
| P4-M4, matched caption | The matched figure accurately describes both scatter and omission panels, effective samples and dependence. |

## Independent arithmetic

`verify_round5_independent.py` reconstructs account centroids from saved 384-dimensional video vectors, computes unordered pair cosines, applies custom average-tie ranks to the exported six-decimal scores, and derives nearest neighbors without importing pipeline functions. It also verifies vector norms, video/group membership, CSV pair alignment, chunk lengths, and terminal-chunk weights. **231 checks pass.**

| Quantity | Independently reproduced value |
|---|---:|
| Full caption documents | 30 |
| Documents contributing to the account matrix | 26 |
| Account groups / unordered pairs | 13 / 78 |
| Equal-chunk vs token-weighted rank correlation | 0.984395351483959 |
| Mean absolute cosine change | 0.01416575641025641 |
| Maximum absolute cosine change | 0.063327 |
| Changed nearest-neighbor assignments | 2 of 13 |
| Chunk count / content WordPieces | 320 / 73,170 |
| Saved equal-chunk float32 replay vs published vectors | Exact match, maximum coordinate delta 0 |

The two changes are Daniel Scranton: Blossom Goodchild to RIZ & Lady O; and Pamela Aaralyn: Elsa Farrus to Lorie Ladd. Both reproduce from independently reconstructed centroids.

The source-level pooling formula matches the implementation: each unit chunk vector is weighted by its content WordPiece count, excluding special tokens, then the document vector is normalized; account centroids still weight videos equally. The equal baseline and weighted variants share all 30 documents and the same qualifying 13 groups. The manuscript properly distinguishes the full-pilot token totals from the 26 documents used in the pair comparison.

This review verifies downstream derivatives rather than rerunning raw-caption neural inference. The stored float32 baseline is identical to the published archive. The more precise maximum pre-serialization delta of 7.409544477976482e-9 is the pipeline's replay receipt, not a number independently reconstructed from raw text by this reviewer. The manuscript's stated bound of 7.5e-9 is consistent with that receipt. Raw captions remain excluded from distribution, and the reproduction document accurately explains the resulting limitation.

## Adversarial interpretation checks

The new comparison changes pooling weights, not document selection, tokenization, model, or speaker composition. The draft does not treat a high global rho as validated thematic similarity, and it preserves local neighbor changes. It does not attribute the masking difference to names alone. The matched title/caption comparison remains 22 contributing videos and 55 dependent pairs; the larger 25-video eligibility pool is separately identified. Omission ranges are descriptive influence, not uncertainty intervals. Automatic tracks and platform-labeled manual tracks are correctly distinguished from human verification.

No new confirmatory inference, human validation, population coverage, or source-authenticity claim was introduced. Final review must remain tied to the actual round-6 artifact and should ensure that the final disclosure accurately records completion of all three manuscript rounds.
