# Continuation diagnostics

This new layer preserves the historical expansion analyses. It calculates three exploratory diagnostics from the retained 925-upload metadata, 30 English-caption vectors and 949 AI-digest Q&A candidates. A fourth question audits the executed local model experiments and their separate post-hoc controls. No new transcript or encoder inference is implied by the first three calculations.

Run from this repository root:

```sh
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/audit_benchmark.py
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/audit_model_diagnostics.py
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/audit_prompt_sensitivity.py
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/analyze.py
MPLCONFIGDIR=/tmp/channels-et-matplotlib XDG_CACHE_HOME=/tmp/channels-et-cache /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/figures.py
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/verify.py
OPENBLAS_NUM_THREADS=2 /workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/reproduce.py
```

The standalone analysis environment uses `research/analysis/requirements.txt` (recorded installed versions are in `environment-freeze.txt`); outputs record exact NumPy, SciPy and scikit-learn versions. Scripts locate this repository relative to their own file. These commands read saved model outputs and never start model inference. `analyze.py --output /absolute/path` supports independent numerical reproduction. `reproduce.py` compares all thirteen generated numerical JSON/CSV files byte for byte in a fresh temporary directory and verifies that the generic reproduction receipt binds to the current canonical results and outputs.

## Question and answer lexical resemblance

The question and answer-gist representations use separate word unigram/bigram TF–IDF vocabularies, English stop words and sublinear term frequency. There are 441,797 unordered distinct-upload candidate pairs across 949 candidates from 67 uploads. Scores within the same upload are excluded. Upload-pair means provide one alternative weighting; they do not create independent subjects.

Of 127 question neighbors at cosine ≥.40, the mean answer-gist cosine is .1709. Restricting to 57 neighbors crossing conservative quarantine groups gives .0440. This is a selected-pool contrast: quarantine itself uses question resemblance, so the two pools differ in prompt similarity as well as source association. It does not isolate a source-reuse effect. The count-matched random reference intentionally samples ordinary distinct-upload pairs; it does not match prompt resemblance, publisher, language or length and is not a calibrated statistical null.

All these source questions and answers are inherited AI-generated paraphrases/gists from one practitioner context. Answer lexical resemblance does not measure proposition agreement, factual truth, human judgment or an attributed entity's speech.

## Lexical connectivity and source quarantine

The threshold graph has one vertex per question candidate and edges only between different uploads. Thresholds .40–.90 are exploratory operational choices. The .40 graph links 178 candidates, with a largest connected component of fifteen; all 771 isolated candidates remain counted. Graph components are lexical neighborhoods, not validated topics or original-session families.

A strict two-link source-family sensitivity requires at least two cross-upload question pairs above .70, .80 or .90. Separately, the model worker specified a stronger benchmark guard: link uploads if any exactly normalized question repeats, any question pair has cosine ≥.80, or at least three question pairs have cosine ≥.40. The independently reconstructed benchmark partition has 55 groups across 67 uploads: 47 singleton groups, five groups of two uploads, two groups of three and one of four.

`generated/source-family-map.json` exports the conservative partition for source-aware model splitting. It is a quarantine policy. The analysis does not assert that linked uploads are copies of the same performance. Unknown recording-family relations and pretrained-model contamination remain possible.

## Matched representation and length diagnostics

The same 25 uploads from fourteen publishers have both retained title and caption vectors, producing 300 dependent unordered pairs (eleven within-publisher and 289 between-publisher). Absolute log duration ratio, mean log duration in minutes and absolute log caption word-count ratio are observed nuisance variables.

Raw title–caption pair Spearman correlation is .2486. After projecting their ranks separately on an intercept and ranked nuisance variables, the correlation of residual ranks is .1294. Omitting each publisher gives partial correlations from −.0256 to .2068; this deterministic influence range is not a confidence interval. A separate projection of cosine scores reports within-minus-between residual differences. Neither procedure establishes causal mediation, speaker identity or independent performances.

## Actual model experiment boundary

The verifier checks the available benchmark split without importing its producer. The first split has 48 training examples from 47 quarantine groups, and eight held-out questions from eight disjoint groups. Candidate IDs, upload IDs and conservative source groups are disjoint. The inspected retrieval implementation fits and searches only training examples. The completed pilot supplies fifty predictions: five arms with eight held-out questions and two deliberately unsupported control prompts each. A separate independent audit checks all predictions, replays train-only retrieval, verifies token-F1/citation-label scores and their aggregates, binds training examples to their split, and verifies saved adapter artifact hashes.

Model reconstruction targets are AI digest gists. Token overlap and citation-label membership are narrow diagnostics, not factual correctness or source entailment. The tiny selected test set cannot establish a reliable ranking. One actual CPU LoRA epoch completed 48 microsteps and twelve optimizer steps, adapting 270,336 parameters in 65.04 seconds. No GPU comparison was executed. A later Qwen3.5-0.8B probe tests schema/span compliance on twelve fixed digest excerpts; it does not repeat the held-out reconstruction benchmark or establish contemporary-model performance on the underlying videos.

The first five arm means for token F1 are .034993 (lexical extractive), .060212 (base closed), .010638 (base train-only RAG), .145307 (LoRA closed) and .012240 (LoRA train-only RAG). The RAG evidence excludes held-out source groups and target answers, so this is sparse-source transfer, not an ordinary answer-present RAG comparison. Low overlap does not establish RAG inferiority.

The primary control indicator detects the literal `INSUFFICIENT_EVIDENCE` marker, not every refusal. Base controls output `Insufficient evidence.` and therefore score zero despite refusing. The model figure pairs lexical reconstruction with strict-marker counts and the separately labeled broader phrase diagnostic. One LoRA closed response invents an exact studio temperature (23°C), while another says the unpublished hash is unavailable; neither outcome is inferred merely from token overlap. No longer-generation-budget experiment was executed.

## Artifacts and verification

`results.json` provides source hashes, measured summaries, graph rows, matched pair rows and the three independent audits of executed model outputs. `generated/` contains complete question-neighbor and upload-pair aggregates, conservative source maps, CSVs, independent verification and reproduction receipts. Six inspected figure families are exported as PDF/SVG/PNG with exact units and captions in `generated/figure-captions.json`: question/answer alignment, lexical graph stability, caption duration controls, source leakage guard, model reconstruction/controls and common question-cosine support. Their legends sit outside the plotted data.

`audit_benchmark.py` checks actual model predictions independently from their producer. The independent core verifier reconstructs decisive lexical pairs, component counts, source partitions, vector joins, nuisance conditioning and available split partitions. It does not import the analysis or benchmark producer. These checks verify calculations and source binding, not source-digest accuracy, human annotation, transcript quality or physical claims.


## Round 11 corrections

The protocol amendment records a prompt-similarity support diagnostic before its calculation. The .40–<.50, .50–<.60 and .60–<.70 bins contain both quarantine strata; together they retain 93 neighbor pairs (36 within, 57 cross), while 34 higher-similarity within-group pairs lack cross-stratum support. The identical pooled-bin weights are .580645, .279570 and .139785. Standardized answer-cosine means are .297186 within versus .044210 cross, a positive .252977 contrast. Unsupported means remain null. The directional contrast is not disconfirmed by this coarse check, but remaining topic, length and within-bin similarity selection prevents a causal source-reuse or agreement interpretation. Original .170854 all-neighbor and .044017 cross-quarantine means remain preserved.

`audit_model_diagnostics.py` independently checks post-hoc refusal phrases, citation-stripped token overlap, four answer-present training-source controls, and a twelve-text local-label probe. Broader phrase counts differ from strict marker compliance: base closed has two recognizable phrase refusals despite zero underscore markers. The four positive outputs cite no required source label, even when two reproduce the supplied answer gist exactly; these controls expose training-source targets deliberately and are not held-out performance. The twelve-text probe has nine parsed outputs, all selecting the same theme, and zero source-exact answer spans. Its five-of-nine dictionary conditional concordance is not accuracy.

The model generation budget was not rerun. Five LoRA-closed and one LoRA-RAG held-out outputs hit the 40-token cap; this is censoring bookkeeping, not an executed longer-budget sensitivity. Removing citation labels changes only the lexical-extractive mean appreciably (.034993 to .035715); original raw scores remain intact.

For cache-independent reproduction, `audit_benchmark.py` verifies the released adapter ZIP and each member hash, then matches the adapter weight bytes to the original executed training receipt. The ZIP's README/config normalization is recorded by its own manifest. The audit was executed with every external model-cache read rejected, and passed using the portable package. Numerical verification does not require importing Torch, loading base weights or rerunning the model.

## Round 12 prompt and contemporary-family probes

`audit_prompt_sensitivity.py` independently replays source-only scoring for three executed annotation conditions and binds the saved prompts, predictions and comparison tables to their hashes. Reversing the theme options changes six labels among eight jointly parsed texts; each ordering parses nine of twelve outputs. The reversed probe selects its first option zero times out of nine, so a simple first-option-copy account does not explain these outputs. This small prompt-order check does not validate themes or establish general position effects.

The Qwen3.5-0.8B text-only probe uses the same twelve items, original schema and theme order, and nominal 96-token limit. All twelve outputs parse; ten contain a literal answer-gist substring, six satisfy the eight-word limit, and five satisfy both. Five literal spans exceed eight words and two are not literal substrings. All twelve conditional labels are yes, giving six-of-twelve dictionary concordance, exactly the always-yes baseline. The original Qwen2.5 probe's five-of-nine concordance also equals its always-yes baseline. Parse and evidence-format compliance are distinct from semantic accuracy. Model architecture, tokenizer/template and Transformers version differ, and the same token cap does not imply the same word budget; this is not a model-quality ranking. No images, audio or videos were inputs to either probe.

A separate post-hoc regex sensitivity replaces `depend\w*` with `depends?|depending`, changing the conditional indicator from 60 to 58 of 949 answer gists. The two removed matches are dependence/dependency wording. Original labels and the twelve-item selection remain preserved. Neither lexicon is human validated. The protocol, executed output hashes, independent audit and final review distinguish these performed checks from the unexecuted longer-budget benchmark or new transcript acquisition.

After the manuscript is built, `/workspace/channels-et-analysis-venv/bin/python research/continuation/analysis/verify_final_sources.py` checks its current input-manifest bindings, the six exact copied figure PDFs, all model-audit inputs and the current numerical reproduction receipt. It writes `generated/final-source-consistency.json`; the round-12 review records the exact reviewed manuscript hash and the pages inspected visually.
