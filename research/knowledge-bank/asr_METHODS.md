# Stronger speech recognition: feasibility, comparison and full-input editions

This study tests a modern open speech model in the current CPU-only cloud and
measures how its text differs from the existing small-model approach. Model
capacity, lexical agreement and fluent output do not establish transcription
accuracy. No independently word-aligned human reference was supplied for these
recordings, so the reported edit statistic is **model disagreement, not WER**.

## Model selection and actual runtime

We inspected the complete primary model cards for OpenAI Whisper large-v3-turbo,
its faster-whisper conversion, Distil-Whisper large-v3.5 and its official CT2
conversion, and NVIDIA Parakeet TDT0.6b-v3. These offer different language,
architecture, speed and accuracy tradeoffs. Distil-v3.5's own table reports lower
short-form error and faster inference than turbo, but higher long-form error;
neither that table nor model popularity establishes a universal best model for
channeling recordings.

The executed upgrade is [NVIDIA Parakeet TDT0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3/blob/541d1f99c6b0c3cd0b11a95167540bb8edefd82b/README.md),
immutable Hub revision `541d1f99c6b0c3cd0b11a95167540bb8edefd82b`. Its card gives an
original release date of 14 August 2025, supports 25 European languages, and
reports 6.34% mean WER on its listed English benchmark. That is a publisher
benchmark claim, not this study's result or a current universal leaderboard rank.
The supported language inventory is not global language coverage; this pilot does
not establish multilingual accuracy for every channel or religious tradition.
The inspected repository revision was updated in August 2026; a newer card date
does not prove newly trained weights. The model's CC BY 4.0 attribution is retained.

Six pinned files totaling **2,509,473,204 bytes** were actually downloaded into
temporary RAM-backed storage. The main safetensors file is 2,508,311,120 bytes,
SHA-256 `3a2026366188c8c68598edbbff92f8d11590a08e0ae2e6775544e7b07d6a5e11`.
The downloader checks exact primary LFS SHA-256 for the weights and Git blob
identity for configuration files. No remote model code is executed. HF metadata's
627,057,286 floating state elements include normalization buffers; this is not an
exact learned-parameter count. The full worker records the latter separately.
This run uses the published pretrained weights; it does not retrain or edit them.

The environment has a four-core CPU quota, 32 GiB cgroup memory limit and no CUDA
GPU. The existing modern environment supplies PyTorch 2.6.0+cpu and
Transformers 5.20.2. The first load attempt stopped before inference because
librosa was missing. A separately recorded, fresh attempt succeeded after 27
audio-feature dependency wheels were installed into a RAM-only target. Existing
virtual environments were unchanged. [The wheel lock](asr_requirements_ram.lock)
pins the actual Python 3.12/Linux x86_64 wheels, including librosa 0.11.0 and
NumPy 2.3.5. Runtime-generated caches and model files remain temporary; this is not
permanent ChatGPT-account storage. Package and model download receipts are private.

## Frozen paired-window experiment

The frame contains eight retained recordings across six source contexts: the four
Council recordings, the lexicographically first qualifying retained Ra segment,
official Bashar publication, OmNa recording and Multidimensional Soul recording
within specified pinned manifests. Eligibility for the latter selection concerns
enough audio for two windows; it is not a new channel-wide duration restriction.
The Bashar publication retains the existing 300-second minimum. The frame is
purposive and does not sample entire channels or all languages.

Two nonoverlapping 30-second windows per recording are centered at 25% and 75% of
its declared decoded duration, rounded down to whole-second starts. Selection was
frozen before new recognition. Every window has 480,000 mono 16 kHz float32 samples
and a checked SHA-256. Both models receive **exactly the same PCM bytes**. The
eight minutes of unique audio produce 32 model-window inferences; the separate
single-window feasibility attempt is not added to that denominator.

Parakeet runs FP32 with its normal greedy TDT generation, one CPU thread per
process and no explicit maximum-token truncation. Each admitted output must
exhaust the valid encoder frames; raw token IDs and per-step frame advances are
retained privately. The comparison uses the cached tiny.en checkpoint with
faster-whisper 1.2.1/CT2 4.8.3, CPU int8, beam 5, English, temperature 0, no VAD and
no previous-text conditioning. This is a **controlled tiny.en rerun**, not a
comparison against differently windowed historical full-recording output. The
two engines also differ in language handling, precision and decoding algorithm.

Both completed stages use two one-thread processes. Parakeet's observed inference
interval overlap is 54.11 seconds; tiny's is 9.95 seconds. Stage wall times are 62.40
and 12.48 seconds respectively, including worker validation/loading/inference.
Median per-window real-time factors are 0.2285 and 0.0416. Shared cloud activity
continues during these measurements, so they do not establish isolated hardware
performance or a causal parallel speedup. No matched serial benchmark was run.
Peak per-process RSS is cumulative; it is not per-window incremental allocation.

The producer reports 913 Parakeet whitespace words and 1,015 tiny words. NFKC
normalization, case-folding, apostrophe preservation and Unicode word tokenization
precede Levenshtein distance. Dividing by the larger token count yields a symmetric
disagreement score: median 0.07065, mean 0.14962 across 16 pairs. Distinct-token Jaccard
has median 0.88348; it ignores word order, frequency, negation scope and proposition
meaning. Two windows have different literal negation-cue counts; zero differ in
digit-bearing-token count. Month/day word cues include ambiguous forms such as
*may* and are not identified dates.

All 16 outputs remain in the results. A **post hoc** quality screen identifies one
Ra window with 112 identical normalized tiny tokens in succession (run ratio 1.0).
Its Parakeet output is substantially shorter and different. This is a text-quality
audit lead, not proof of a hallucination, correct alternative wording, or absence
of legitimate repetition in the audio. Six tiny windows have unadjusted segment
end estimates beyond 30 seconds, with a maximum overrun of 1 second. Those estimates
do not establish speech beyond the available input. Parakeet is represented by
the fixed window boundaries; timestamp accuracy is not compared.

## Separate full-recording extension

The finite extension covers the same four retained Council audio files, totaling
171,833,236 decoded samples / 10,739.57725 seconds. Preparation reproduces each old
ASR's exact FFmpeg S16 mono 16 kHz command and verifies its complete raw-PCM SHA-256
and sample count. The new model input is explicitly `int16 /32768` converted to
float32. This holds the canonical decoded waveform constant when later comparing
old and new full text; the separate paired-window experiment above used direct
float32 decoding for both of its models.

The full waveform is partitioned into 359 independent, nonoverlapping chunks of
at most 30 seconds. Every final partial tail is included. Output assembly is ordered
verbatim concatenation, without overlap deduplication, punctuation stitching or
speaker inference. Chunk boundaries can split words and sentences and lose prior
context. Complete sample coverage and encoder exhaustion do not imply complete or
accurate linguistic recovery, and this is not unbroken long-context decoding.

The controller freezes its executed code, pins every request and uses two warm
one-thread workers. Hard limits include 180 seconds per inference window, 240 seconds
for setup, 1,800 seconds for the full worker stage, 18 GiB conservative ASR memory
accounting and 5 MB additional durable full-run artifacts. The conservative memory
quantity adds ASR temporary-file bytes to worker RSS, double counting some mapped
model pages. Cgroup anonymous/shmem/file-cache counters are recorded separately;
reclaimable file cache is not described as model heap usage.

Only a final `completed_full_chunked_asr` manifest admits the four new editions.
It binds all 359 chunk outputs, exact contiguous sample ranges, full F32 hash,
canonical old S16 hash, old/new text hashes, worker receipts and unknown speaker
roles. The old four transcripts and primary 25-text knowledge-bank fit remain
unchanged. A separate sensitivity analysis may transform the new editions with
the frozen old vocabulary, IDF and embedding model; old annotation locators must
not be silently attached to changed new text.

The completed extension produced **26,319 whitespace words**, compared with
25,964 in the four preserved old editions. The three Tracy recordings contain
3,449, 2,666 and 2,939 new words; the Pamela recording contains 17,265. Two Pamela
windows have empty text and remain in the complete coverage denominator. Empty
text does not establish silence or a recognition failure without listening review.
The workers completed all 359 windows in **1,273.79 seconds (21.23 minutes)**,
including validation, loading and inference. Their measured inference intervals
overlapped for 1,252.74 seconds. Median chunk real-time factor was 0.23444, and
maximum conservative ASR memory was 10,022,882,150 bytes (9.33 GiB). Model loading
took 3.94 and 3.87 seconds. Download, PCM preparation and final projection are
outside this worker-stage timing. Both workers recorded **627,008,134 learned
parameter elements**. These shared-cloud measurements do not establish isolated
hardware performance or speedup against a matched serial run.

An independent AI reviewer rehashed every chunk, inverted all float32 samples
back to int16 and reproduced the original complete S16 hashes. It also checked
the full source/request/output joins, all raw encoder-duration sums, contiguous
sample coverage, exact concatenated text and observed worker overlap. This is a
provenance and computation audit, not human verification of transcription accuracy.
The complete private manifest has SHA-256
`3991b8649962b5223993479cd6e70dc9c09b81983d61bb21f770ca4b21429e68`;
the metadata-only public projection has SHA-256
`fdfdd4d7fdeec4c7d2675061095d457b390e86a80343633e1ab9e0fcba71a7b9`.

## Reproduction and checks

`asr_download.py` downloads a pinned model into a fresh RAM directory.
`asr_prepare.py` freezes the paired-window frame; `asr_orchestrate.py` and
`asr_worker.py` execute bounded workers. `asr_summarize.py` produces public
`asr-benchmark.json`. `asr_full.py` prepares/runs/finalizes the separate full-input
edition with `asr_full_worker.py`; `asr_full_project.py` produces metadata-only
`asr-full.json` after completion. Private controllers retain their exact executed
source copies, even if later public code adds reporting or validation changes.

The cloud-specific runner constants name the existing interpreters and private
artifact roots. Other environments must recreate the recorded package versions
and adjust those explicit paths before running. Do not rerun full collection or
overwrite prior editions merely to regenerate a public projection. Source media,
full machine texts, model binaries and private path-bearing receipts stay outside
public Git and Pages.

Eight focused tests in `asr_tests.py` exercise negation-preserving normalization,
word-order/set distinctions, empty/symmetric distances, repetition diagnostics,
same-size artifact tampering, storage admission, required model/clip guards and
termination of only the controller's own worker at a hard stage deadline. Actual
input/output/source/memory/timing checks are recorded separately by independent
AI reviewers; tests do not establish word accuracy or constitute human review.

Primary contextual sources include the [Parakeet technical report](https://arxiv.org/abs/2509.14128),
[Fast Conformer](https://arxiv.org/abs/2305.05084),
[Token-and-Duration Transduction](https://arxiv.org/abs/2304.06795), and
[Distil-Whisper](https://arxiv.org/abs/2311.00430). Their links are supplied by the
inspected model cards; unless separately recorded by the literature panel, this
ASR lane claims full model-card inspection rather than full-paper review. The
Parakeet report's abstract and bibliographic page were additionally inspected:
its title covers both Canary and Parakeet. The abstract's 1.7-million-hour training
and 10×-faster claims concern Canary and are not transferred to the Parakeet run.
