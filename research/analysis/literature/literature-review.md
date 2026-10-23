# Primary literature and open-source methods

Checked 2026-10-23. This targeted review contains 16 academic sources and 6 implementation repositories. It does not claim exhaustive literature coverage or a current universal best model. Reading depth and access limits are explicit.

## L01 — Semantic Structure and Correspondence in Prospective Trance-Channeled Communications Attributed to Extraterrestrial Intelligences

Helané Wahbeh; Beth Glick (2026-04-12). [domain empirical paper](https://doi.org/10.1080/02604027.2026.2656120).

**Read:** Author institution abstract; selected publisher methods accessible in search index; public Figshare v1 code/results/protocol inspected; live publisher full text returned 403. Three experienced channelers answered standardized interviews across 28 topical areas. The authors report transformer-embedding correspondence of 0.65–0.79 across channelers for the same purported ETI and 0.75–0.88 within channeler across ETIs after residualization.

**Use here:** Close comparator for structured same-question corpus design. Use matched questions and separate within-person from between-person comparisons.

**Limit:** Three-person sample, not the YouTube population. Similarity does not establish truth or an ET source. Supplement lacks participant answer inputs and the supplied code export lacks explicit global-text chunking and within-channeler residualization; full results were not replicated.

[Inspected supplement](https://doi.org/10.6084/m9.figshare.31100860.v1). See the supplement manifest and round reviews for precise access and replication limits.

## L02 — Qualitative Structure and Meaning in Prospective Trance-Channeled Communications Attributed to Extraterrestrial Intelligences

Helané Wahbeh; Beth Glick (2026-04-15). [domain empirical paper](https://doi.org/10.1080/02604027.2026.2656119).

**Read:** Author institution abstract; publisher full text returned 403. The authors analyze prospectively collected interviews with reflexive thematic analysis, reporting recurring narrative frames and conceptual metaphors. They explicitly avoid ontological conclusions.

**Use here:** Pair quantitative similarities with close reading, contextual notes, contrasting examples and stated alternative interpretations.

**Limit:** Shares authors and the prospective research program with L01; do not count it as an independent replication. This review does not verify an unobserved entity or communication mechanism.

## L03 — Channelers’ Answers to Questions from Scientists: An Exploratory Study

Helané Wahbeh; Paolo Speirn; Luciano Pederzoli; Patrizio Tressoldi (2023-10-19). [domain empirical paper](https://journalofscientificexploration.org/index.php/jse/article/view/2907).

**Read:** Publisher abstract and metadata. Fifteen channelers answered ten scientific questions in channeled and non-channeled states. Three judges found low within-person cross-state correspondence and virtually no correspondence across channelers, while qualitative themes overlapped for some questions.

**Use here:** Retain disconfirming findings and distinguish thematic overlap from response agreement. Compare equivalent question types and answer lengths.

**Limit:** Different participants, prompts and measures from L01; the results cannot be pooled directly or treated as a clean contradiction.

## L04 — A qualitative exploratory analysis of channeled content

J. Anastasia; H. Wahbeh; A. Delorme; J. Okonsky (2020). [domain empirical paper](https://doi.org/10.1016/j.explore.2020.02.008).

**Read:** Author institution abstract and citation. Thirteen adult trance channels answered a research-oriented prompt; analysis identified seven themes across scientific-methodology, channeling-process and open-ended-information categories.

**Use here:** Demonstrates a small-corpus thematic analysis with an explicit eliciting question. Preserve prompt context when interpreting frequencies.

**Limit:** Prompt-driven and not an ET-channel census. The author institution page lists August 1; journal issue is July–August, so only year is normalized.

## L05 — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks

Nils Reimers; Iryna Gurevych (2019-11). [established method](https://aclanthology.org/D19-1410/).

**Read:** Publisher abstract and metadata. Introduces sentence encoders whose representations can be compared with cosine similarity, avoiding joint inference for every sentence pair.

**Use here:** Use a frozen documented encoder on matched text units; preserve model identifier, revision, language, truncation and normalization settings.

**Limit:** Cosine similarity depends on model and corpus. It does not measure factual correctness or independent origins. This paper does not validate every later Sentence Transformers model.

## L06 — BERTopic: Neural topic modeling with a class-based TF-IDF procedure

Maarten Grootendorst (2022-03-11). [method preprint and software](https://arxiv.org/abs/2203.05794v1).

**Read:** arXiv abstract and repository README sections. Combines document embeddings, clustering and class-based TF-IDF topic representations.

**Use here:** Candidate for sufficiently rich transcript chunks; show representative source passages, outliers and robustness across parameters.

**Limit:** Clustering sparse titles can produce unstable or entity-name-driven topics. BERTopic has not been executed merely because it is cited.

## L07 — MMTEB: Massive Multilingual Text Embedding Benchmark

Kenneth Enevoldsen et al. (2025-11-13). [benchmark paper](https://arxiv.org/abs/2502.13595v4).

**Read:** arXiv abstract, version history and ICLR acceptance metadata. Extends embedding evaluation across hundreds of tasks and languages, including long-document and instruction-related tasks.

**Use here:** Choose candidate encoders by the task and languages actually present; reserve an in-domain evaluation set.

**Limit:** Reported rankings belong to the paper’s evaluation snapshot and do not establish the best model for this domain or today.

## L08 — Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models

Yanzhao Zhang et al. (2025-06-11). [contemporary candidate preprint](https://arxiv.org/abs/2506.05176v3).

**Read:** arXiv abstract, version history and official repository usage. Offers 0.6B, 4B and 8B embedding/reranking models and reports strong multilingual benchmark results.

**Use here:** Candidate for a future multilingual comparison against a small baseline, with identical documents and local validation.

**Limit:** No Qwen inference or benchmark was run by this literature workstream. Its state-of-the-art claim is historical and benchmark-specific.

## L09 — jina-embeddings-v5-text: Task-Targeted Embedding Distillation

Mohammad Kalim Akram et al. (2026-04-28). [contemporary candidate preprint](https://arxiv.org/abs/2602.15547v2).

**Read:** arXiv abstract and version history. Presents compact task-targeted models and reports competitive same-size performance, multilingual support and long-context inputs.

**Use here:** Current alternative worth testing for clustering versus retrieval tasks after checking the selected model card and license.

**Limit:** Abstract review only; no weights downloaded or scores reproduced. A 32k-token capacity does not eliminate length and genre confounding.

## L10 — Large Language Models Struggle to Describe the Haystack without Human Help: A Social Science-Inspired Evaluation of Topic Models

Zongxia Li et al. (2025-07). [method evaluation paper](https://aclanthology.org/2025.acl-long.375/).

**Read:** Publisher abstract and metadata. A user study on two datasets finds readable LLM topic labels can be too generic for domain-specific exploration; human supervision improves usefulness at an effort cost.

**Use here:** Require specific labels, traceable examples, counterexamples and review of whether a label teaches anything about the corpus.

**Limit:** This supports human validation, not a universal ranking of topic methods. A model-agent panel is not equivalent to the study’s human participants.

## L11 — LLM Reading Tea Leaves: Automatically Evaluating Topic Models with Large Language Models

Xiaohao Yang; He Zhao; Dinh Phung; Wray Buntine; Lan Du (2025). [method evaluation paper](https://aclanthology.org/2025.tacl-1.17/).

**Read:** Publisher abstract and metadata. Proposes WALM, a joint evaluation of document and topic semantic quality, and reports agreement with human judgments in its experiments.

**Use here:** Optional complementary diagnostic beside traceable lexical baselines and manual review; record judge/model identity.

**Limit:** An LLM judge can share biases with a generator; it must not replace direct source inspection or be labeled independent human review.

## L12 — Text as Data: The Promise and Pitfalls of Automatic Content Analysis Methods for Political Texts

Justin Grimmer; Brandon M. Stewart (2013). [established methodological review](https://web.stanford.edu/~jgrimmer/tad2.pdf).

**Read:** Author-hosted paper abstract and introduction. Argues that automatic content analysis requires problem-specific validation and close reading.

**Use here:** Treat units, sample construction and validity checks as part of the analysis; keep model outputs distinguishable from substantive claims.

**Limit:** Political-text examples transfer as methodology, not as findings about channeling. Only the introduction was read in detail.

## L13 — Evaluating the Consistency of Word Embeddings from Small Data

Jelke Bloem; Antske Fokkens; Aurélie Herbelot (2019-09). [small-domain empirical methods paper](https://aclanthology.org/R19-1016/).

**Read:** Publisher abstract and metadata. Studies embeddings from small philosophical corpora and shows consistency depends on data, model and term frequency.

**Use here:** Use split-sample and leave-one-document-out stability checks; flag low-sample channels instead of overinterpreting their nearest neighbors.

**Limit:** The original method concerns word embeddings, so applying its stability principle to sentence-level channel centroids is our adaptation.

## L14 — On the Robustness of Multilingual Text Embedding Rankings Across Learning Tasks, Languages, and Benchmark Datasets

Ana Gjorgjevikj; Barbara Koroušić Seljak; Tome Eftimov (2026-05-29). [contemporary benchmark-analysis preprint](https://arxiv.org/abs/2605.31142v1).

**Read:** arXiv abstract and metadata. Studies how multilingual model rankings change with dataset composition and aggregation choices.

**Use here:** Report sensitivity to language mix and channel weighting rather than advertising one universal best embedding model.

**Limit:** Preprint and abstract-level review; not independently replicated here.

## L15 — Reading Tea Leaves: How Humans Interpret Topic Models

Jonathan Chang; Sean Gerrish; Chong Wang; Jordan L. Boyd-Graber; David M. Blei (2009). [established topic-evaluation paper](https://papers.nips.cc/paper_files/paper/2009/hash/f92586a25bb3145facd64ab20fd554ff-Abstract.html).

**Read:** Publisher abstract. Shows held-out likelihood and human semantic interpretability can diverge.

**Use here:** Add topic/document intrusion-style review and check examples, not only numeric model scores.

**Limit:** Human review tasks are recommendations; this agent panel does not constitute a blinded human study.

## L16 — MTEB: Massive Text Embedding Benchmark

Niklas Muennighoff; Nouamane Tazi; Loïc Magne; Nils Reimers (2023). [benchmark paper](https://aclanthology.org/2023.eacl-main.148/).

**Read:** Publisher search-index abstract; arXiv abstract. Benchmarks embeddings over diverse tasks and finds no universal best method in its tested set.

**Use here:** Use retrieval, clustering and semantic-similarity evaluations aligned with intended use.

**Limit:** Older benchmark snapshot; not a current leaderboard claim.

## Open-source repositories

- [Sentence Transformers](https://github.com/huggingface/sentence-transformers): Dense sentence/document embeddings; documented MiniLM example emits 384-dimensional vectors. Read: README embedding usage. Status: Reviewed, not run by literature agent. See repository and selected model license; not audited here.
- [BERTopic](https://github.com/MaartenGr/BERTopic): Topic clustering with embeddings and c-TF-IDF; supports dynamic and class-based variants. Read: README overview and license marker. Status: Reviewed candidate. MIT.
- [MTEB](https://github.com/embeddings-benchmark/mteb): Task-specific embedding evaluation; not a substitute for channeling-domain labels. Read: README installation and example usage. Status: Reviewed evaluation tool. Apache-2.0.
- [Qwen3-Embedding](https://github.com/QwenLM/Qwen3-Embedding): Documented Sentence Transformers inference for Qwen3-Embedding-0.6B; model-specific query prompts. Read: Official README inference section. Status: Reviewed candidate. Models Apache-2.0 per paper; verify chosen artifact.
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api): Fetch available captions and retain language/generated/manual flags. Availability and blocks vary. Read: README fetch/list/manual/generated sections. Status: Feasibility to be established by corpus workstream. MIT for code; not a transcript-content license.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): Metadata-only extraction supports numeric duration seconds and upload date; no video download required for this analysis. Read: README --skip-download and duration fields. Status: Feasibility to be established by corpus workstream. Check repository license and bundled dependencies; source access does not grant video-content rights.