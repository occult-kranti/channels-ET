# Local model and retrieval experiments

These are small CPU feasibility and source-reconstruction experiments. References
are existing **AI-generated Darryl Anka/Bashar-context digest paraphrases**, not
human ground truth, actual speech turns or verified facts. Model weights stay
outside Git.

## Executed experiments

The pinned Apache-2.0 baseline is Qwen2.5-0.5B-Instruct revision
`7ae557604adf67be50417f59c2c2f167def9a775`. Five arms answer the same eight
heldout questions and two unsupported controls: lexical retrieval, base model,
base model with RAG, LoRA model, and LoRA model with RAG.

The CPU adapter trained 270,336 of 494,303,104 parameters on 48 digest pairs for
one epoch: 48 microsteps, 12 optimizer steps, rank 4, alpha 8, q/v projection
targets, sequence cap 192, gradient accumulation 4 and learning rate 0.0002.
Training took 65.04 seconds with two Torch threads. No GPU was exposed; no GPU
timing or training comparison was invented.

`split.json` preserves every selected source ID. Conservative question/repost
rules group 67 uploads into 55 proxy source families. Training spans 47 families;
the eight heldout questions come from eight different families. These are not
verified original sessions and cannot eliminate unknown reuse or pretraining
overlap. RAG fits its index on the 48 training examples only, taking at most two
excerpts above query cosine 0.10. Heldout answer gists are never supplied as
evidence. Five heldout questions have some evidence; three have none.

The references measure lexical reconstruction. Higher LoRA closed-book overlap
does not establish reliability: that adapter invented an unsupported studio
temperature of 23°C on a control. The strict `INSUFFICIENT_EVIDENCE` marker misses
ordinary `Insufficient evidence.` wording, so a separate post-hoc phrase diagnostic
is retained. Four answer-present training-source citation controls also omit the
requested source label. These controls are not heldout tests. Citation membership
is not entailment.

Latency includes retrieval when used, tokenization and generation, excluding
initial loading and index fitting. It is not a hardware ranking. The instruction
asks for under 40 words; the actual hard cap is 40 tokens. No training answers or
inference prompts were truncated. Five LoRA-closed and one LoRA-RAG outputs hit
the generation cap. A longer-budget generation experiment was not run.

## Actual content annotation and disconfirmation

The baseline classified 12 fixed excerpts from 12 proxy source families using
the documented theme/conditional schema and a 96-token cap. Nine records parsed,
three failed, all nine primary labels were `contact_forecast`, and no parsed
evidence span matched its answer gist exactly. Conditional/regex concordance was
5/9, equal to an always-yes baseline.

Changing only the theme-option order changed 6 of 8 labels with valid paired
parses. The reversed run produced seven `personal_practice` and two
`contact_forecast` labels; none chose the reversed first option, `unclear`.
This disconfirms simple first-option copying while demonstrating local prompt
sensitivity. Parse failures and raw outputs remain visible. A separate post-hoc
regex sensitivity excludes `dependency`/`dependence` forms: 60 conditional
indicators become 58 among 949 rows. Neither rule is human-validated.

Official Qwen3.5-0.8B revision `2fc06364715b967f1860aea9cf38778875588b17`
actually ran on CPU using Transformers 5.20.2 and its own chat template with
thinking disabled. A provenance JSON smoke test generated 23 tokens in 3.881313
seconds. That easy probe explicitly supplies its target facts.

The newer model then processed the **same 12 excerpts, original schema/order and
96-token cap**: 12 records parsed, 10 spans were exact answer substrings, and five
of those exceeded eight words, leaving 5/12 combined exact-and-short spans.
There were two nonexact spans. All 12 conditional labels were yes, so its 6/12
dictionary concordance also equals an always-yes baseline. Theme labels were
11 `personal_practice` and one `contact_forecast`. This is source/format
compliance on a tiny purposive sample, not human accuracy, truth or a general
model ranking. Different architectures, tokenizers and required runtimes prevent
isolating parameter scale as a cause. No images, video, speech, GPU or Qwen3.5
fine-tuning were tested.

## Rebuild the software environments

The tested platform is Linux x86-64 with Python 3.12. From this repository root:

```sh
bash research/continuation/models/setup_model_envs.sh
```

The script contains the complete reproducible commands. It creates
`/workspace/channels-et-model-venv`, installs `torch==2.6.0+cpu` from the official
`https://download.pytorch.org/whl/cpu` index, installs the exact baseline freeze
and runs `pip check`. It creates `/workspace/channels-et-modern-venv`, links only
Torch and small dependencies read-only from the baseline environment, installs
the modern freeze, then checks that old Transformers/PEFT are not exposed.
Both environments pass their package checks. The modern environment depends on
retaining the baseline environment at that path.

The exact baseline creation/install commands are:

```sh
python3 -m venv /workspace/channels-et-model-venv
/workspace/channels-et-model-venv/bin/python -m pip install --no-cache-dir \
  --index-url https://download.pytorch.org/whl/cpu 'torch==2.6.0+cpu'
/workspace/channels-et-model-venv/bin/python -m pip install --no-cache-dir \
  -r research/continuation/models/cpu-environment-freeze.txt
/workspace/channels-et-model-venv/bin/python -m pip check
```

The helper's Python block provides the exact modern-environment symlink
procedure; it shares Torch, torchgen, functorch, sympy, mpmath, networkx, jinja2
and markupsafe plus their distribution metadata, not the old model libraries.
It then installs `modern-environment-freeze.txt`. Baseline core versions are
Torch 2.6.0+cpu, Transformers 4.51.3, PEFT 0.15.2 and Accelerate 1.6.0; modern
Transformers is 5.20.2. TLS and artifact verification remain enabled.

## Download pinned weights and rerun inference/training

Use a disposable copy before rerunning: these commands overwrite run outputs.
They do not run during the ordinary source-only site build.

```sh
/workspace/channels-et-model-venv/bin/python research/continuation/models/download_model.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/run_benchmark.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/package_adapter.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/verify_benchmark.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/run_content_labels.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/run_round11_diagnostics.py
/workspace/channels-et-model-venv/bin/python research/continuation/models/run_round12_order_probe.py
```

Download and run the newer model separately:

```sh
/workspace/channels-et-modern-venv/bin/python research/continuation/models/download_model.py \
  --model Qwen/Qwen3.5-0.8B \
  --revision 2fc06364715b967f1860aea9cf38778875588b17 \
  --cache /workspace/channels-et-model-cache/qwen3.5-0.8b \
  --manifest qwen35-manifest.json
/workspace/channels-et-modern-venv/bin/python research/continuation/models/smoke_current_family.py
/workspace/channels-et-modern-venv/bin/python research/continuation/models/run_qwen35_content_labels.py
python3 research/continuation/models/build_annotation_comparison.py
```

The two required weight sets occupy about 2.74 GB before virtual environments.
The downloader checks safetensors against official Hub LFS SHA-256 values and
smaller files against official Git blob hashes. Caches remain under
`/workspace/channels-et-model-cache`; only manifests enter Git. The initial
premature tokenizer attempt and corrected, interrupted option-probe attempt are
disclosed in setup/run-event records; neither is promoted as a completed experiment.

## Verify released artifacts without model weights

```sh
python3 research/continuation/models/verify_benchmark.py --offline
python3 research/continuation/models/verify_round11.py
python3 research/continuation/models/build_annotation_comparison.py
python3 research/continuation/models/verify_round12.py
```

These commands recompute saved metric/source bookkeeping and verify the adapter
ZIP and source pins. The offline verifier explicitly skips tokenizer recomputation
and identifies the retained length audit. None replays neural inference.
Current-cache tokenization checks and historical receipts remain separate.

The public `qwen-digest-lora-pilot.zip` contains the actual approximately 1 MB
adapter, config, Apache notice, training receipt and all 48 source hash/pointer
entries, with QA/split/protocol hashes. Full base weights and raw captions are
absent. The NOTICE distinguishes the Apache base/adapter distribution from the
inherited MIT digest dataset; original recording rights remain separate.

All generated labels and references remain model outputs. They do not validate
source speakers, extraterrestrial identities, mechanisms, medical claims or
original speech. Raw outputs, parse failures, source spans and limitations are
inspectable in the adjacent JSON artifacts.
