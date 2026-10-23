# Evaluation design: lookup, RAG and adaptation

This is a source-grounded engineering experiment. A statement can be faithful to a retrieved channeling source while remaining an unverified claim about the world. Questions and prompts should ask what an identified source says; they must not treat attributed cosmology or health assertions as externally established gold facts.

## Distinguish the executed arms

1. Lexical/dense retrieval only: rank source records and return IDs; report Recall@k/MRR against the declared source target. These scores establish known-record retrieval, not semantic answer correctness.
2. Extractive nearest-neighbor lookup: return an existing source answer field with its source ID. Call it lookup; it is not a generative language-model result.
3. Base generator, closed book: unchanged model, no source context. Record the fixed prompt and generated tokens.
4. Base generator plus retrieved context: same base checkpoint and decoding, fixed retrieval/model-token budget; this is the RAG arm when generation actually occurs.
5. LoRA-adapted generator, closed book: base weights frozen; actual low-rank matrices trained. Record adapter rank, alpha, dropout, target modules, trainable/total counts, optimizer, epochs/steps, tokens, checkpoint selection, seed, hardware and elapsed time.
6. LoRA plus retrieval is a separate arm if run. Do not merge its result into either RAG-only or fine-tuning-only.

An unrun arm remains proposed or blocked. A tiny CPU checkpoint can demonstrate execution but is not a test of all contemporary LLMs or production usefulness. Use the same underlying base checkpoint, question set, prompts and decoding where comparisons require them. If model families differ, call that comparison confounded and present it separately. Pin model revisions, tokenizers, package versions, licenses and actual downloaded checksums; preserve normal TLS/checksum verification.

## Two different tasks

**Source lookup/grounded answering:** the test question is held out from training, but source evidence may remain in the retrieval index by design. This is an open-book task. Explicitly state whether the index contains the exact question, a near duplicate, only the answer gist or an independent caption passage. If the exact question is indexed, report that easy lookup condition and a question-field-masked/paraphrased sensitivity; do not claim general semantic understanding.

**Generalization to new sources/practitioners:** remove the test recording and known original-session family from all adaptation data and decide prospectively which independent supporting sources may remain indexed. A source-free question may be unanswerable from that index; abstention can be the correct behavior. This task needs more than one actual practitioner corpus to evaluate cross-practitioner transfer. A roster with empty text fields does not supply test cases.

## Leakage and split controls

- Freeze train/development/test membership before tuning. Use development data for checkpoint/threshold/prompt selection; do not select the winning prompt on test overlap scores.
- Group by upload ID and, where established, original-session/repost family. Keep exact and normalized Q&A duplicates together; inspect near-duplicate sequences. An upload-ID split alone cannot establish recording independence.
- Distinguish publisher holdout from practitioner holdout. They test different units. Keep single-practitioner results visibly restricted.
- Audit source hashes, IDs, normalized duplicate questions/answers, and relevant spans across partitions. Record unresolved candidate families rather than asserting a leakage-free corpus.
- Generated paraphrases derived from test answers are not independent held-out human queries. If used, label the generating model, source dependence and task as a synthetic stress test.
- If source text may have appeared in base-model pretraining, say the pretraining-contamination status is unknown. The current experiment cannot prove novel knowledge acquisition.

## Measurements and interpretation

Report retrieval hit/MRR denominators, output count/failure/abstention counts, wall time and resource use. Answer token-F1, ROUGE or embedding resemblance to an inherited digest gist are automatic reference-overlap proxies. They are not calibrated factual correctness, a human agreement statistic, source attribution accuracy or the truth of an attributed claim. Keep lexical overlap with the provided context separate from correctness against a reference answer. A generated answer can copy a passage yet answer the wrong question.

Source citations should resolve to actual retrieved IDs and text windows; the presence of a syntactically valid citation alone is not semantic support. Track unsupported additions and explicit uncertainty with a written codebook, using model annotation only under a model-output label. Independent human relevance/faithfulness/answer-relation labels remain TBD. ARES-style calibrated intervals require corresponding human data and assumptions; do not manufacture them from agent agreement.

Useful negative controls: shuffled irrelevant context, retrieval context without the exact question field, known-unanswerable query, contradictory-source pair, source labels permuted, and evidence placed early/middle/late within the same token budget. Label synthetic controls as tests, not natural corpus findings. Run equal-source and duplicate-family sensitivities when data allow. Dependent question pairs and samples sharing an account are not independent participants.

A failed model load, exhausted memory, unstable training or no held-out gain belongs in the result ledger. Compare actual outputs, not only training loss or successful installation. A trained adapter that does not beat the base or lookup baseline is a useful negative result. Never turn a successful smoke test into an accuracy claim.
