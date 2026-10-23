# Round 1 methods and literature panel

Status: source review and prospective recommendations, 23 October 2026. These are recommendations to the analysis implementation, not claims that these tests have already run. This is a panel of model agents; it is not human academic peer review or participation by historical scientists.

## What the literature supports

The closest studies are Wahbeh and Glick's 2026 prospective ET-attributed interview analyses (L01/L02). Their author institution reports three channelers, 28 topical areas, transformer embeddings and reflexive thematic analysis. Their two papers share a research program and are not independent replications. The public publisher text returned 403; this workstream read the author institution abstracts, not the complete methods. Their numbers therefore belong only to that study. The 2023 exploratory channeling study (L03) reported virtually no cross-channeler correspondence on its question set despite some shared qualitative themes. The literature gives a reason to measure and inspect overlap, not a predetermined result.

Modern embedding papers (L05/L07/L08/L09/L14/L16) provide useful candidates and benchmarking discipline. They do not establish that a particular model is best for ET-channeling titles or transcripts. The first working analysis should retain a transparent lexical baseline. A neural comparison is an addition only when actual model inference succeeds and model/version/inputs are saved. TF-IDF and SVD are vectors but must not be labeled transformer embeddings.

L10/L11/L12/L15 support a mixed workflow: numeric diagnostics, traceable documents, informative labels and direct review. Model-agent agreement is not a replacement for a blinded human annotation study. L13 motivates a stability check when only a few documents represent a channel.

## Units and provenance contract

1. The primary unit for duration and publication counts is a unique video ID. The publisher account is separate from the named channeler/medium or attributed entity. Multiple uploads of one session remain separate platform records but are linked as possible content duplicates when evidence supports it.
2. Duration is seconds from the source's runtime field or visible timestamp. The final caption timestamp is not total duration. Trailers, shorts, clips, interviews, complete sessions and compilation videos should be flagged where known. Unknown duration stays missing, never zero.
3. Titles, descriptions, transcripts and researcher-written notes are different text classes. Do not mix them into a single semantic corpus without explicit labels and a sensitivity result. Search snippets are not transcripts. Keep original title separate from a display label such as 'YouTube video'.
4. Every result has a source, retrieval date, evidence-access level and acquisition path. Metadata inherited from Claude remains inherited until rechecked. Include the original CSV/JSON row and normalized ID.
5. Frequency is the number of observed dated uploads in this collected sample. Without channel-census coverage or a declared fixed crawl window it is not a posting rate, activity prevalence, channel growth measure or event frequency.

## Minimum channel table

Account label and route; unique indexed videos; exact-date known count; duration-known count; duration coverage percentage; sample mean minutes; median minutes; 25th and 75th percentiles where meaningful; shortest/longest observed duration; observed runtime hours; earliest/latest exact publication dates; valid title-document count; transcript-document count; text languages; top title keywords; sample/coverage note.

For n=1 a mean can be displayed but it is just one observed video's length. For n=0 show unavailable. Do not add confidence intervals implying a random sample. A convenience sample can have a mathematically computed bootstrap interval that still says nothing about unseen uploads.

## Defensible first figures

- Coverage chart: duration-known versus unknown videos by account, with exact counts. Caption says the denominator is indexed unique uploads, not the account's complete upload history.
- Mean/median duration comparison: horizontal dot or dumbbell chart for accounts with at least three observed durations, accompanied by n and coverage. Include a view of individual durations or an interquartile range so long sessions do not hide a clip-heavy distribution.
- Observed uploads by month: stack or small multiples by account for exact dates only; a missing-date bucket remains visible. Zero means no observed record in the corpus for that month, not known inactivity.
- Title topic/keyword shares: normalized per account with n titles; label dictionary rules or c-TF-IDF terms explicitly. Names removed for the primary subject comparison and retained in a sensitivity view. Keywords can overlap; percentages need not sum to 100 if multi-label.
- Similarity heatmap: compute in the full vector space and show eligible accounts only. Caption gives representation, aggregation, n, name filtering and language policy. Diagonal 1.0 is identity, not a finding. Do not interpret colors as probabilities or evidence for entities.
- Per-channel drilldown: observed duration distribution, monthly sample counts, top terms and source-linked videos. Sparse accounts should get a useful coverage notice rather than a fabricated plot.

A 2D projection is optional navigation. Its geometry cannot justify cluster claims; preserve explained variance for PCA/SVD or stochastic parameters for UMAP. Distances in the plot are not the same as full-space cosine scores.

## Round 2 should follow observed defects

Freeze these initial hypotheses now, before results are selected:

H1: Apparent channel differences in mean duration may reflect clip/session format mix. Test: recompute summaries stratified by known format or show distribution and label unknown formats. Without format evidence, keep this as a plausible explanation, not a result.

H2: High cross-channel similarity may be driven by repeated names, entity labels, publisher boilerplate or reuploaded content. Test: compare raw and name-stripped titles, remove exact normalized-title duplicates, and identify top pairs whose rank changes most.

H3: A few prolific indexed accounts may dominate global topic frequencies. Test: compare upload-weighted totals to equal-account averages. Both are corpus summaries; neither estimates prevalence in all ET channeling.

H4: Similarity for accounts with few documents is unstable. Test: leave one document out for eligible accounts or repeatedly equal-subsample; report rank/score variation. Do not imply generalization beyond this corpus.

H5: Title vocabulary differs from spoken themes. Test only where source-matched transcripts are actually available. With no usable transcripts, leave unresolved and label all topic results 'titles'.

Do not silently reclassify a failed test as support. Freeze the next-round contract after the first round review chooses the actual unresolved defect.

## Captions checklist

Each figure needs an analytical question, measured quantity, sample size and eligibility rule, source/cutoff, missingness treatment, transformation, and one-sentence limit. Separate observations from interpretations. Use units on axes. A chart of topic percentages needs its denominator. A similarity chart needs its model. A monthly frequency chart needs date coverage. All figures should have downloadable underlying tables.

## Custom skill review

| Skill read | Applicability | Contribution or reason not applied |
|---|---|---|
| paired-physics-research | General workflow transfer only | Freeze acceptance tests before production; choose each later round from actual review; preserve accepted, failed and unresolved findings. No physical derivation, continuum or scale-matching claims are appropriate here. |
| historical-physics-panel | Applied to panel framing and source discipline | Independent model agents are research lenses, not historical people or human peer reviewers. Read its lenses-and-evidence reference. Require actual reading depth and alternative explanations. |
| newton-analysis-synthesis | General critique transfer only | Distinguish observable text similarity from an unidentifiable hidden cause; use negative controls and alternate representations. Its physics/theorem/historical-source domain is not used. |
| tesla-mechanism-resonance | Not applicable as a physical method | Text resemblance is not resonance, energy transfer, phase coupling or a demonstrated communication mechanism. Retain only general whole-pipeline checks. |

## Reproducibility and permissions

Store code, normalized metadata, model configuration, hashes, computed tables, brief source-linked excerpts and analysis notes. Open-source software licenses do not grant rights to redistributed transcripts. Record transcript provenance and permission/status separately; maintain acquisition scripts and text hashes when full text cannot be included. Do not circumvent unavailable captions, sign-in restrictions or other access barriers. A GitHub push and a website deployment are separately verified actions.
