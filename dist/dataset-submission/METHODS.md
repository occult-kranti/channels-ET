# Reconciled corpus analysis

This module describes the finite retained corpus. It does not estimate how much channeling content exists on YouTube, test extraterrestrial claims, or establish agreement between speakers. The private source frame determines every selected text and its provenance; the public exports contain source identifiers, derived measures, compact tables and figures.

## Units and input contract

The analysis reads `frame.json` with the verified `research/channel-lab/sources.py::load_frame` loader. A row is one selected text edition for an admitted publication/source unit. Publisher contexts, creator contexts, YouTube accounts, videos, recordings, editions and attributed entities remain separate. Two new OmNa editions share publication URLs with older editions and differ only in whitespace; the corpus engineer preserves both editions and selects the prior text. No naive concatenation of prior and new corpus counts is performed here.

The loader checks artifact bytes, SHA256, Unicode NFKC plus outer-whitespace normalization, word counts and row order before modeling. Word totals use whitespace splitting. NLP tokens use Unicode alphabetic words, allow internal apostrophes, normalize curly apostrophes and casefold. These are distinct measures. All source data remain private.

## Reproduction

Use the existing analysis virtual environment, Python3.12, with bounded CPU threads. The pinned dependencies and exact executable code hashes are in `public/results.json`. The output includes a private numerical witness and public source profiles.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  ANALYSIS_PYTHON \
  research/dataset-submission/analysis/run_analysis.py \
  --frame PRIVATE_DATASET/frame.json \
  --private PRIVATE_DATASET/analysis \
  --public research/dataset-submission/analysis/public \
  --model PINNED_MODEL_DIRECTORY

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  ANALYSIS_PYTHON \
  research/dataset-submission/analysis/verify_analysis.py \
  --frame PRIVATE_DATASET/frame.json \
  --private PRIVATE_DATASET/analysis \
  --public research/dataset-submission/analysis/public
```

`--model` is optional, but omitting it intentionally omits the neural comparator. It never silently substitutes a remote service. The model cache contains a pinned `sentence-transformers/all-MiniLM-L6-v2` ONNX model at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; hashes are validated before inference. No model training, fine-tuning, distillation or weight modification is claimed. This is an auditable CPU baseline, not a claim of current state-of-the-art quality.

## Measures and exploratory analyses

1. **Corpus profile.** Selected-document counts, whitespace words, text origin, length, metadata date coverage and publisher concentration. Unknown uploaded totals remain null. Publisher dates do not establish the date of a recorded utterance. Channels with fewer than five selected documents receive descriptive profiles; there is no within-channel cluster analysis for such contexts.
2. **TF-IDF.** Full selected text, unigrams+bigrams, sublinear term frequency, smoothed inverse document frequency, minimum document frequency2, maximum24000features, L2 normalization. The scikit-learn English stop list is used with negations `no/not/nor/never` retained. The exact list is exported. A declared identity-phrase registry is masked with length-preserving spaces before tokenization; it is incomplete and does not anonymize sources. A top-term score is a document's normalized TF-IDF weight; a context score averages its source weights. A contrast score subtracts the equal-context mean of other contexts. These are not phrase counts or significance measures.
3. **Topics.** Eight exploratory nonnegative matrix factorization components, random initialization with seeds11/23/47, maximum2000iterations, tolerance1e-4. Components are L2 normalized and their source weights reciprocally rescaled to preserve reconstruction. Source mixtures normalize those weights to sum1. Each context mixture averages source mixtures. Top-term labels are automatic descriptors, not validated semantic themes. The alternative seed components are matched with maximum-cosine bipartite assignment; matched cosines, dominant-topic ARI and mixture differences are exported.
4. **Context imbalance.** Select up to10sources per context by ascending SHA256(sourceID), giving a documented deterministic balanced-fit subset. Refit NMF on that subset in the full fixed vocabulary, then transform every source. The second IDF model also uses the fixed vocabulary but estimates document frequencies on the same subset before transforming all sources. The resulting differences are sensitivity diagnostics, not a correction proving representativeness.
5. **Clustering.** TF-IDF to50D truncated SVD, then row L2 normalization and KMeans with10initializations. Main k=8 and seed11 are illustrative fixed choices; k4/6/8/10 crossed with seeds11/23/47 are reported without selecting the largest score as a validated optimum. Cosine silhouette, seed ARI and ARI against publisher, creator and origin labels are descriptive. Topics and clusters are different constructions.
6. **Networks and context comparison.** An undirected source edge exists only when both sources are in each other's top5cosine neighbors, ties by sourceID. There is no minimum-cosine threshold. All pairs are scored in the original TF-IDF space. Mean context matrices use every cross-context source pair; diagonal cells use unordered distinct within-context pairs. Singleton diagonals are null. Pair counts are denominators, not independent sample sizes. Two-dimensional SVD coordinates are lossy display coordinates; original-space cosine remains authoritative.
7. **Length and neural comparison.** Extract a centered span of at most300alphabetic words from each unmasked body, then apply the identical phrase registry. Compare full and bounded lexical neighborhoods on an identical source universe. MiniLM sees those same bounded text spans, with complete240wordpiece chunks, no wordpiece truncation, attention-mask mean including CLS/SEP, normalized chunk vectors, and content-wordpiece-weighted normalized document means. The lexical-versus-neural comparison uses bounded lexical vectors, avoiding a hidden full-text/window mismatch. Top5set Jaccard is reported with source-macro and context-macro averages; pairwise Spearman is descriptive because pairs overlap.
8. **Context and origin confounds.** For each source, its top5same-group fraction minus `(groupSize−1)/(N−1)` is averaged within groups and then across groups. This availability-adjusted enrichment does not separate confounded publisher identity, writing style, transcription process or subject matter. It does not imply a mechanism.
9. **Question cues.** A punctuation rule extracts candidate spans ending in `?` and the following1000characters, with sourceID/bodySHA/character offsets in the private witness. Those are not verified questions, answer turns, common answers or contradictions. Public output contains counts only. Existing separately curated question-bank records keep their own validation and denominator; this module does not relabel them.

## Interpretation and next experiments

The exploratory hypotheses are that source-length controls change nearest neighbors; publisher/context imbalance changes topic factors; and text origin partly tracks lexical neighborhoods. The observed diagnostics can motivate these hypotheses but are not independent confirmatory tests. A defensible next study needs stratified human annotations, duplicated-question judgments, explicit answer spans, provenance-aware held-out creator/recording splits, ASR validation against manually transcribed audio, and a preregistered estimand. A natural next retrieval evaluation would compare lexical, MiniLM and stronger multilingual baselines against blinded, source-balanced relevance judgments. Another would fit origin-matched models once multiple contexts have comparable written and spoken editions.

The alphabetic tokenizer can fragment alphanumeric labels (for example, `3D` produces `d`). T01 contains `d` and conversational contractions; T07 contains `yeah` and `kind`. These factors may capture formatting or register, rather than substantive themes. An alphanumeric-token sensitivity and annotated term audit remain proposed work.

These outputs describe reported discourse. They do not establish claimed identity, civilization, truth, therapeutic efficacy, agreement or contradiction. Closely matching text may reflect reposts, templates or source reuse. High-cosine pairs are review candidates, not automatic deduplication decisions. The corpus is finite and convenience-sampled; dates, speakers, language labels and ASR are not independently revalidated by this analysis.

## Primary method references

- Salton, G., and Buckley, C.1988. Term-weighting approaches in automatic text retrieval. *Information Processing & Management*24(5):513–523. https://doi.org/10.1016/0306-4573(88)90021-0
- Lee, D.D., and Seung, H.S.1999. Learning the parts of objects by non-negative matrix factorization. *Nature*401:788–791. https://doi.org/10.1038/44565
- Rousseeuw, P.J.1987. Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*20:53–65. https://doi.org/10.1016/0377-0427(87)90125-7
- Hubert, L., and Arabie, P.1985. Comparing partitions. *Journal of Classification*2:193–218. https://doi.org/10.1007/BF01908075
- Reimers, N., and Gurevych, I.2019. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *EMNLP-IJCNLP*. https://aclanthology.org/D19-1410/
- Wang, W., et al.2020. MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers. *NeurIPS*. https://arxiv.org/abs/2002.10957

The actual pinned all-MiniLM sentence encoder is a released model, not identical to every architecture or evaluation in those method papers. No related-work citation is a validation result for this corpus.

## Public release allowlist

Only `public/analysis.json`, `public/results.json`, `public/verification.json`, `public/tables/*.csv`, and `public/figures/*.{pdf,svg,png}` are public analytical artifacts. Private source bodies, punctuation-cue spans, model cache, local paths and numerical archives remain in the private dataset archive. The dashboard/paper release process binds its own manifest to these files. Public metadata may still identify publishers and source URLs; this is not an anonymized dataset.
