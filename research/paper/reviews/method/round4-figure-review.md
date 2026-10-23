# Round 4 — executed figure and formula review

Reviewed the actual four PNG figure exports and `generated/formulas.tex`, not proposed visuals. The source hashes and findings are preserved in `round4-figure-review.json`. The full manuscript PDF was not yet available at this point, so this is a component review only.

The matched title/caption scatter clips negative x values at zero. This is a blocking figure accuracy issue. The duration legend overlaps the long Divine Insights IQR and the 0.969 sensitivity annotation crosses the lower axis; both need layout repair. Some generated prose needs spaces between numbers and words. The pipeline has received these concrete changes.

The coverage figure now makes an important distinction: 25 video IDs have both eligible title and caption, but three singleton groups do not enter the centroid comparison. That comparison uses 22 contributing videos from 11 publishers and 55 dependent pairs. The broader matched keyword-presence analysis uses all 25 videos. Manuscript text must preserve these denominators.

Independent LOPO computation from the frozen published pair matrices agrees: eleven leave-one-publisher-out comparisons each contain ten publishers and 45 pairs; the correlation ranges from -0.0433465 to 0.3786561 around the full-sample 0.205628. This is descriptive influence, not an inferential interval.

The generated pooling equations agree with the executed definition. Average-tie ranks, empty/zero-vector treatment, masking and the short terminal chunk's equal weight still need textual specification in the manuscript. Next gate: inspect the actual manuscript PDF and repaired figure exports before closing the first manuscript round.
