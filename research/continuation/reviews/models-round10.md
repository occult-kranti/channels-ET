# Model panel — continuation round 10

Role: AI local-model implementation reviewer. Scope: the new `channels-ET`
repository; the original Bashar repository is untouched.

The environment exposes four CPU-quota cores and no CUDA device. The selected
baseline is official Apache-2.0 Qwen2.5-0.5B-Instruct at pinned revision
`7ae557604adf67be50417f59c2c2f167def9a775`. The baseline is intentionally small
enough for an actual bounded CPU LoRA run. It is not described as current state
of the art. Official Qwen3 and Qwen3.5 model metadata are recorded separately.

Implemented before prediction: conservative source-family quarantine,
48-example training selection, eight heldout questions from separate proxy
groups, two unsupported controls, train-only TF-IDF retrieval, four generation
arms and an extractive lexical baseline. The 55 proxy groups across 67 upload
IDs are not verified original sessions. `split.json` preserves all selected
candidate IDs, upload IDs, group IDs and exact source hash.

`protocol.json` fixes this exploratory pilot before model predictions. Targets
are existing model-generated digest paraphrases, not human-reviewed answers or
verified extraterrestrial claims. Token F1 is reconstruction overlap. Citing a
supplied source label tests syntactic membership, not whether a generated claim
is entailed by the excerpt. No heldout answer is placed in the RAG index.

Setup used a separate CPU model virtual environment. Torch, Transformers,
PEFT, Accelerate and numerical versions are recorded in `hardware.json`.
Official files are downloaded from pinned revisions; safetensors use the
official Hub LFS SHA-256 and smaller files use their Git blob hashes. TLS and
artifact verification remain enabled. The first premature local tokenizer load
failed while artifacts were still incomplete; it produced no predictions or
training. Its observed error and correction are recorded in `setup-events.json`;
the initial full log was replaced by the subsequent run log. Loading is retried only after
the complete verified model manifest is written.

Execution status must be read from `run-status.json`, `training-receipt.json`
and `benchmark-results.json`; installed packages or downloaded weights alone
do not count as completed inference or training. The newer-family Qwen3.5 smoke
test uses a separate modern Transformers environment, with the baseline
environment's CPU Torch shared read-only through explicit package links; old Transformers/PEFT are not exposed. A modelcard/API response does not
establish local runtime capability or domain quality.
