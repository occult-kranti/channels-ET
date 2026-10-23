# Round 1 build and root review

Actual first build: 925 unique video IDs, 189 account groups, 449 eligible duration records across 16 groups, 58 exact dates inherited from source metadata. Native browser opened #/analysis and verified the table, channel detail, selected-account duration histogram, monthly count empty state, keyword frequencies and nearest title vocabularies. This was a baseline before fresh metadata and transcript results.

Accepted corrections for Round 2:
- Paginate 189 table rows; explicit no-indexed-video empty state.
- Retain inherited duration status beside sample denominators.
- Integrate acquired metadata to resolve publisher IDs, dates and measured lengths.
- Do not convert relative ages or podcast dates to upload dates.
- Exclude multilingual title confusion from English model comparisons; preserve supplied and observed title variants.
- Mask identity terms in both similarity and keyword sensitivity analyses.
- Add actual model-backed title/transcript comparisons separately; do not call TF-IDF neural embeddings.
- Export PNG as well as SVG for independent visual review.

Not yet complete at this checkpoint: neural inference, complete metadata refresh, transcript analysis, final captions, report, publication. No population or extraterrestrial-origin inference is supported.
