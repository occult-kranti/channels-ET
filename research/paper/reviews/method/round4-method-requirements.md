# Manuscript round 4 — methods design review

Reviewer: `/root/method_panel`. This begins a new manuscript phase after publication of the dashboard/report/GitHub deliverables. It is not a relabeling of the three prior analysis rounds. Input data SHA256: `f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc`.

The dataset, source-level equations, features and figures are available; the manuscript protocol/main text was not yet present at the initial design inspection. The next review must read the actual draft and rendered figures rather than treating these recommendations as evidence that a manuscript exists.

## Recommended paper argument

The defensible contribution is a reproducible measurement audit of a small, purposively assembled YouTube discourse corpus. Titles, captions, publishers, claimed speakers and original sessions are distinct units. The paper can show how comparison results change when the observable and preprocessing change. It cannot estimate the world population of ET-channeling mediums, establish speaker authenticity, determine agreement of substantive claims from cosine alone, or validate extraordinary origins.

A suitable working framing is **“Titles, Captions, and Measurement Sensitivity in a YouTube Channeling Corpus.”** Treat “ET channeling” as the content's attributed genre and self-description, not an established extraterrestrial communication category. Avoid a novelty claim such as “first” unless a separate systematic review supports it. Describe the manuscript as an exploratory research draft prepared in an ICWSM-style format; do not imply submission, acceptance or peer review.

The main results should answer three bounded questions:

1. **RQ1 — coverage and format:** What metadata and text are available in this merged index, and how heterogeneous are sampled upload lengths? Duration is a description of upload packaging and sample composition, not measured thematic depth, popularity or quality.
2. **RQ2 — text-layer comparison:** For the same eligible video IDs and publisher groups, how closely do title-based and caption-based similarity rankings correspond? The matched set removes video-selection mismatch but does not equalize text length, editorial function, transcription quality or content granularity.
3. **RQ3 — sensitivity:** How stable are comparisons to identity masking, repeated-title exclusion, balanced five-title sampling, removal of outer caption text and leaving one publisher out? Each control tests one specified perturbation; none is a universal validity certificate.

Keep theory-driven hypotheses separate from post hoc interpretations. This corpus and its analysis were assembled before the manuscript RQs; call the study retrospective and exploratory. No preregistration, held-out confirmatory test or blinded human coding occurred.

## Required unit and selection accounting

The methods section needs one compact selection table or flow figure with these frozen totals, deriving them from data at build time:

- Source union: 482 earlier indexed YouTube IDs plus 457 valid IDs from 466 supplied rows, with 14 overlapping IDs, yields 925 unique IDs. Nine supplied unlinked leads are outside the ID-based union.
- Publisher mappings: 256 account-route groups are retained; 180 have indexed videos, 178 have at least one known duration. Unresolved aliases can split one actual account. Thus neither 256 nor 180 is a human-medium count.
- Duration/date coverage: 881 videos have lengths (877 fresh, four inherited); 880 have exact days (878 fresh plus inherited exact dates). Dates mean UTC publication days, not recording dates.
- Title eligibility: 742 English-likely title records; 706 both eligible and attributable are embedded. The title-language gate is seeded langdetect, probability at least 0.80 and at least four alphabetic words. Short-text probabilities are not calibrated correctness probabilities. English display text may be a platform translation.
- Caption retrieval: 36 attempted, 34 retrieved; exclude three non-English and one additional concordance document from the main pilot, leaving 30 documents across 17 publisher groups. Thirteen groups have at least two captions and enter the primary caption-centroid matrix.
- Matched comparison: 25 shared title/caption video IDs; 11 groups meet the two-document threshold on both sides, yielding 55 unordered account pairs. Explain that total matched documents can include singleton groups not admitted to the account-comparison matrix.

Document source precedence and conflicts: current watch-page title/uploader/duration/UTC date supersede inherited assertions; raw variants remain. A missing field is null, not zero. Exact video-ID deduplication does not resolve original-session reuploads. Supply the ascertainment/search protocol, date and failure log in the supplement. The supplied draft and the earlier index are not independent probability samples.

## Measurement equations

Use notation consistent across text, tables and captions. Let $a$ index a publishing account route, $i$ a unique uploaded video, $q$ a dictionary category and $j$ a caption chunk.

**Durations.** For the $n_a^D$ sampled videos with usable duration $d_i$ in seconds,

$$\bar d_a = \frac{1}{60n_a^D}\sum_{i\in I_a^D}d_i.$$

Report mean minutes, median, linear-interpolated 25th/75th percentiles and the measured/indexed count. The IQR is not a confidence interval. The caption should say “sampled uploads”; avoid “average channel video” without that qualifier.

**Keyword presence in titles.** Let $k_{iq}$ be the number of regex matches in document $i$. For $n_a^T$ eligible titles,

$$p_{aq}^{T}=\frac{1}{n_a^T}\sum_{i\in I_a^T}\mathbf{1}[k_{iq}>0].$$

Categories overlap. These are predefined lexical indicators, not a fitted topic model, latent topics, manually validated themes, time spent on a topic or agreement of claims. The codebook must be linked and its exact patterns versioned.

**Caption keyword rates.** With $w_i$ word tokens matched by `[A-Za-z]+(?:'[A-Za-z]+)?`,

$$r_{iq}=1000\,k_{iq}/w_i,\qquad \bar r_{aq}=\frac{1}{n_a^C}\sum_{i\in I_a^C}r_{iq}.$$

Contractions are one token. Compute rates per video before equal-video averaging; pooling all words across the account would produce a different, length-weighted estimand. A long caption has more opportunities for at least one keyword than a short title, so matched presence differences do not imply hidden semantic themes.

**Learned embeddings.** Name the exact MiniLM repository, revision, ONNX artifact hashes, software versions, tokenizer, maximum title input (254 wordpieces plus special tokens), and identity-mask list. The model is an executed baseline, not a demonstrated state-of-the-art encoder for this domain. Distinguish it from the sparse TF–IDF baseline.

For a caption chunk, attention-mask mean pooling gives $u_{ij}$ and $z_{ij}=u_{ij}/\|u_{ij}\|_2$. For $K_i$ non-overlapping chunks of up to 240 wordpieces,

$$v_i=\operatorname{norm}\left(\frac{1}{K_i}\sum_{j=1}^{K_i}z_{ij}\right),\qquad
c_a=\operatorname{norm}\left(\frac{1}{n_a}\sum_{i\in I_a}v_i\right),\qquad
s_{ab}=c_a^\top c_b,$$

where $\operatorname{norm}(x)=x/\|x\|_2$. Define treatment of empty/zero vectors and special tokens explicitly. The final shorter chunk receives equal weight, a model choice that can influence output. For titles, the single title vector enters the same equal-video publisher aggregation. Retain source-level versus masked model-text hashes separately if exact input reconstruction is claimed.

**Ranking and perturbations.** Spearman correlation is the Pearson correlation of average-tie ranks across the same set of unordered publisher pairs. Those pairs share publishers/documents; no independent-pair p-value or population confidence interval is justified here. Report pair count and comparison domains for every correlation. Cosine magnitudes across TF–IDF and MiniLM are not on interchangeable semantic scales.

For leave-one-publisher-out (LOPO), remove a publisher and all its incident pairs from both matched matrices, then recompute the same rank statistic on the remaining common pairs. With 11 qualifying groups, each leave-out comparison has 10 groups and 45 pairs. The resulting range measures leverage within this fixed sample, not a bootstrap confidence interval, out-of-sample validation or a population uncertainty interval.

## Validity model and competing explanations

Observed text similarity can vary with at least six components: the sampled discourse content; publisher selection/editing and branding; host/question/promotion material; language/translation and ASR; the text-layer length and granularity; and representation/preprocessing/aggregation. These components cannot be uniquely identified from the available vectors.

| Apparent finding | Ordinary alternative | Discriminating evidence still needed |
|---|---|---|
| Two publishers have similar caption centroids | Shared genre vocabulary, host language or repetitive promotion | Speaker/segment annotations and matched prompts, plus close reading |
| One publisher has a distinct centroid | Different language, format, sample dates or ASR quality | Matched-format/language set and transcript accuracy audit |
| Titles and captions rank pairs differently | Editorial compression and word-count opportunity differences | Matched content units and human similarity judgments |
| Same-publisher document pairs exceed other pairs | Stable format/voice, topic selection or recording reuse | More independent sessions, recording-level deduplication and account-level validation |
| A sensitivity correlation is high | Aggregate ranks stable while nearest neighbors change | Both global rank and local-neighbor diagnostics |
| Duration relates to long-video share | Both summaries are calculated from the same durations | Independent content-format labels; no causal conclusion from this plot |

Do not turn exploratory clusters into entity taxonomy or a map of source civilizations. Identity and similarity are separate assertions; an embedding cannot resolve account ownership or speaker identity.

## Results and figure requirements

The main text can prioritize coverage, one duration panel, matched title/caption comparison and a sensitivity table/LOPO plot. Place dense account heatmaps and the dependent within/between boxplot in the supplement if space is limited. Do not fill the paper with every dashboard graphic.

Each main figure requires: a precise question; unit and denominator; minimum inclusion threshold; accessible labels; source date; explanation of any color scale; and a caption that states what cannot be inferred. A plot's caption must describe the actual rendered metric, not an intended future analysis. Show negative cosine values if present. Keep full numeric backing tables and figure-generation scripts.

Report the already checked values narrowly: 55 matched account pairs, rank correlation approximately 0.206; identity-masking correlation approximately 0.626; repeated-title exclusion approximately 0.992; outer-text trimming approximately 0.969, with four of thirteen nearest neighbors changing. Derive all values from the frozen feature file rather than manual transcribing. New LOPO statistics must be executed and independently reviewed before entering the manuscript.

## Ethical and reproducibility statements

Use only public or otherwise authorized data; this study does not require contacting practitioners, accessing private groups or purchasing sessions. Public religious/spiritual discourse should not be recast as psychiatric diagnosis. State that the analysis examines public representations and attributed claims. Avoid ranking individuals by credibility, mental health or purported supernatural authenticity.

Raw third-party captions and model weights are not redistributed. Metadata, source locators, hashes, numeric features, code and permitted figures are released. Explain that full neural recomputation requires separately acquiring authorized caption text and the pinned model; offline rebuilding from saved features is not a fresh model run. Describe the six model-agent roles accurately; this review is not external peer review or human annotation. Do not claim an IRB exemption, consent determination or legal dataset license that was not actually obtained.

## Round 4 acceptance gate and next rounds

Round 4 is complete only after an actual manuscript build is read against these requirements and the executed paper figures, including the new LOPO diagnostic. Record input and PDF hashes and concrete defects. Round 5 then addresses those objections and performs an adversarial interpretation/source audit. Round 6 checks the repaired manuscript, formulas, captions, references and artifact links. Do not pre-complete rounds 5 or 6, or count searches/build retries as research rounds.
