# Baseline review conducted while Round 2 was being prepared

Reviewed the executed round-1 output and implementation on 23 October 2026. This is a baseline review, not a review of executed Round 2 outputs; see round2-executed-review.md for that later review. Exact input hashes and coverage are in `round2-input-snapshot.json`. This review inspects code, figure definitions/captions and computed tables; it does not claim a visual screenshot review or independent rerun of transformer inference.

## First-build results actually inspected

The frozen output contains 925 unique video IDs, 189 account groups, 449 known durations, 58 exact dates and 902 title-eligible records; 260 video IDs have no resolved publisher group. Only eligible subsets enter the cosine comparison. The first build states that no transcript analysis has yet run.

The mean/median figure correctly uses IQR whiskers rather than confidence intervals, shows measured/indexed counts, sets a five-duration minimum and describes convenience sampling. The 20-account coverage figure is explicitly not a popularity ranking. The title heatmap describes overlapping English keyword matches, not inferred transcript themes. These scope boundaries should survive later UI and report edits.

A visible example of why the distribution matters is the RIZ & Lady O sample: 30 measured videos have a mean around 20.61 minutes but a median around 5.97 minutes. This supports reporting both statistics; the data do not establish the cause of that gap without format labels. SOLi School similarly has a sample mean around 17.81 and median around 5.09 minutes. These examples are first-build observations and should be refreshed from the final output before publication.

## Corrections or qualifications requested

1. **Language comparability.** `clean()` strips non-ASCII characters and uses English stopwords. Pavlina Klemm's sample contains English, Czech and German titles while entering the same lexical cosine matrix. Add a clear language-comparability limitation or an explicitly auditable English subset. ASCII dominance is not an English-language classifier. A mixed-language low similarity does not establish thematic difference. Preserve multilingual records in the directory even when excluding them from a particular text model.
2. **Eligibility denominators.** The title dictionary denominator is `titleEligible`; the cosine denominator additionally requires at least two cleaned words. These are distinct counts. Display the similarity-specific n in pair tables and captions, not a broader titleCount substituted for it.
3. **Topic label precision.** Current plots are keyword indicators. Keep that label even after adding neural similarities; a transformer distance does not turn the dictionary into a validated topic model. Some matches are polysemous or part of names. I tested raw versus the current clean function and found no changed indicator counts in this first build (`round2-keyword-sensitivity.json`). One eligible title includes 'Federation of Light', illustrating a possible name/energy match; I found no evidence here that it materially dominates the plot. My earlier warning was a proposed check, not an observed large bias.
4. **Document length in neural models.** When transcript vectors are added, record tokenization, chunk size/overlap, padding mask, pooling and normalization. Average chunks to videos before averaging videos to publishers if the intended unit gives each video equal weight. Do not let a long recording become dozens of independent publisher observations.
5. **Frequency.** Only 58 first-build exact dates are present. A graph must show dated-versus-undated coverage and observed sample counts. Do not infer inactivity, regular cadence or change in topic popularity from unobserved months.
6. **Inference bounds.** Retain labels for official practitioners, repost accounts and interview publishers. Similarity at publisher level can reflect packaging or repeated material. It neither counts independent channelers nor tests whether an entity is real. Correlation between similarity matrices does not validate the origin or truth of the content.

These are interpretation/measurement corrections. None requires replacing the existing transparent baseline or adding unvalidated complex models.

## Direct 2026 study supplement now inspected

The public Figshare record [10.6084/m9.figshare.31100860.v1](https://doi.org/10.6084/m9.figshare.31100860.v1) was retrieved through its public API. All four downloaded files match the repository's supplied MD5 values. License: CC BY 4.0. The metadata is preserved in `figshare-31100860-metadata.json` and files in `figshare-31100860/`.

The files contain interview questions, an analysis-code export, a workbook of across-channeler results and a small CSV of within-channeler summaries. They do not contain the participant answer documents required by the code. The code names MiniLM, MPNet and QA-MPNet, computes cosine scores and directly encodes concatenated global text. It has no explicit long-document chunking, package/model revision pins or within-channeler residualization implementation in the supplied export. Consequently this package allows method inspection but does not, by itself, reproduce all reported results. The live publisher page remained blocked; selected methods were accessible in the search index. Those observations should replace the earlier abstract-only reading description, without claiming full-study replication.

The absence of explicit chunking raises a truncation risk for long inputs; without source answer documents this review cannot measure how much text was truncated. The lesson for our dashboard is to make the actual chunking and coverage inspectable, rather than merely copying a published workflow.

## Suggested next bounded test

Review the first transcript/model build against the length and equal-video-weight rules above. Then compare nearest publisher pairs with (a) title lexical vectors, (b) title neural vectors and (c) transcript neural vectors only where paired documents exist. Keep this a pilot if coverage is small. Publish disagreements as evidence about method sensitivity, not as errors to hide.
