# Related-work synthesis and writing implications

The paper's strongest position is a measurement and provenance study of a small public-video index. Existing research already supplies channeling content studies, ethnographic accounts, channel embeddings, and topic-validation methods. The contribution lies in showing what changes when the document layer and attribution unit change, using a frozen, traceable corpus. The four ready-to-integrate paragraphs are in `round5-paragraph-proposals.tex`.

## Three designs that should remain separate

Elicited-answer studies compare participants under prompts; naturalistic public uploads mix prompts, speakers and publishing decisions; AI-mediated archival querying introduces generated answer text. These designs have different observational units. The two 2026 prospective articles share a research program, while the separate JSE2026 study processes two collections through a common AI system. Neither a larger corpus nor a higher cosine score bridges these differences. The manuscript should discuss design relevance rather than stage a numerical contest among published scores.

The 2020 qualitative study and the 2023 correspondence study illustrate why themes and agreement differ. A shared category can coexist with incompatible or nonmatching answers. Human topical coding, textual resemblance, agreement with a proposition and evidence about an attributed source are separate constructs. Our nine overlapping keyword indicators should keep their concrete operational name throughout captions and results.

## Closest platform work and the remaining gap

Tube2Vec is the closest representation precedent and should receive more space than the more distant conspiracy-pathway comparator. Its MiniLM title/description account averages make clear that average channel vectors are an established tool. It also evaluates representations against human tasks. Our much smaller selection, title-only metadata branch, caption branch and perturbation suite address a different question: whether seemingly comparable account rankings survive changes in what text is measured. Reddit-sharing and recommendation vectors remain unexecuted candidates; the released repository was inspected, not run.

YouNiverse is useful for the ordering of the data section: acquisition, eligibility, distributions, coverage and only then substantive examples. Its thresholded sampling and weights are specific to its collection; our source union cannot inherit them. Ota et al. is explicitly an ICWSM Poster Paper, and its commenter transitions are proxies rather than observed viewing paths. Starbird et al. combines shared-text detection with manual source tracing; similarity alone does not supply direction or identify an original author. These comparisons strengthen our uploader/session distinction without transferring political labels.

## Small-community research contributes context, not a sample-size exemption

Claisse and Durrant make positionality, purposive recruitment, participant feedback and the first author's community relationship visible. Their methods section and participant table support a contextual interpretation of twelve interviews. The illustrations explain experiences and study practice rather than claiming quantitative inference. Our manuscript cannot borrow that qualitative grounding just because its pilot is similarly small: it has no participant interviews or human interpretive study. The anthropological abstracts offer a limited reminder that practices and audience interactions matter; access limits are recorded and no full ethnographic reading is claimed.

Chen et al. separates narratives, visuals and comments into explicit questions, codebooks and validation stages. That structure is useful for connecting each figure to an analytical question. Its high agreement statistics belong to its human-checked coding and do not transfer to our keyword families. Our paper should show fewer plots with explicit denominators rather than copying its much broader multimodal design.

## Validation is the next substantive step

Chang, Doogan and Buntine, Hoyle et al., and Li et al. address different ways that coherent or fluent model outputs can fail to support useful human interpretation. Their combined implication is a concrete future study: select contrasting examples, blind coders to model rankings, retain prompt and speaker context, and distinguish thematic overlap from agreement and formulaic reuse. No current model-agent panel substitutes for this step.

Schroeder and Wood-Doughty's reliability framework concerns repeated fitted topic models. Our perturbation correlations should not inherit its measurement-theory labels. Bloem et al. concerns word embeddings learned from small collections; its relevance to pretrained sentence centroids is an analogy about stability, not direct validation. MTEB and MMTEB justify testing task-appropriate alternatives, but not choosing a current best model by leaderboard alone.

## Executed, inspected and proposed

Executed in the analysis: transparent regular expressions, TF-IDF and a pinned all-MiniLM-L6-v2 ONNX encoder with stated pooling, plus descriptive perturbations. Inspected as research/software comparators: Tube2Vec, topic-evaluation papers, the 2026 domain supplement, and the Phase1 software register. Proposed only: alternative encoders, BERTopic or other fitted topic models, LLM topic judges, human construct validation, original-session grouping and speaker segmentation. This distinction should remain visible in the paper and dashboard.

This was a targeted primary-source search, not a systematic review or an exhaustive current-model ranking. Citation completeness is judged by relevance and verified support, not by the number of entries.
