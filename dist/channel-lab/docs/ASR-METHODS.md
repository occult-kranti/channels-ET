# Bounded speech-recognition batch and immutable transcript editions

This extension reuses the previously downloaded official NVIDIA Parakeet
TDT 0.6B v3 checkpoint, revision
`541d1f99c6b0c3cd0b11a95167540bb8edefd82b`. It makes no new audio or model
downloads and does not modify pretrained weights. Source recordings and earlier
transcripts remain unchanged. See the prior [ASR methods](../knowledge-bank/asr_METHODS.md)
and [RAM dependency lock](../knowledge-bank/asr_requirements_ram.lock) for model
selection, attribution, weight checksums and the actual installed runtime.

## Frozen selection and source admission

The frame was selected before recognition: all five retained OmNa recordings,
plus the shortest eligible retained recording not already fully upgraded by
Parakeet in each of four contexts: Tracy Kumbera, Multidimensional Soul, official
Bashar and Athina Król. Duration, then stable publication/source ID, determines
ties. Bashar requires at least 300 seconds; the other contexts have no minimum.
The four completed Council upgrades are reused as prior editions and are not
recognized again. Athina would be omitted if it pushed the batch above four hours.

All nine fit: **7,956.60625 seconds (132.61 minutes), 269 windows**. The selected
Tracy item is 299.530875 seconds and remains eligible. The official Bashar item is
300.6933125 seconds after exact canonical decoding and passes its threshold.
This operational sample is purposive. It cannot estimate whole-channel accuracy,
typical channel topics or civilization differences.

The frozen frame has SHA-256
`2316c1d6c13c411b05f99b748e915efa3143595862bc9c36dc72e4ac1d1f4a43`.
An independent AI reviewer reconstructed the selection from source manifests,
rehashed all 67,714,206 source-audio bytes and the nine old text artifacts, and
checked exclusion of the four prior upgraded recordings. Seven publisher
recordings reproduce their accepted complete 16 kHz mono S16 PCM hashes and
sample counts; the same seven hashes/counts also match their old ASR decoder
receipts. This does not control architecture, decoding settings or window context.
Official Bashar and Athina were newly canonical-decoded from their
unchanged audio; an exact prior S16 hash match is not asserted for those two.
The entire admission decode streams to a hash without saving a full PCM file.

## Queue, model and resource bounds

The runner accepts a source frame and is not hardcoded to four recordings. Its
prospective guard allows up to 64 recordings and four hours per frame. This
release uses the nine-source selection above. Two persistent model processes
each use one CPU thread, CPU float32 and local-only model loading. One bounded
queue distributes independent windows dynamically to available workers, avoiding
static assignment of long recordings to a single worker. At most four queued
S16 windows are prefetched; each has at most 480,000 samples (30 seconds).
The producer holds one additional window, and each worker holds its current
window. FFmpeg decoding uses one thread and natural EOF validation.

Each worker converts S16 to float32 using `int16 /32768`. Every output binds the
source-audio hash, S16 and float32 window hashes, sample bounds, model revision,
worker code and protocol fingerprint. Raw generated token IDs and frame-duration
advances are retained. The full valid encoder-frame range must be traversed.
No explicit token limit is supplied. Transformers reported its model-agnostic
default `max_length` during the pilot; this is not unbounded generation. Admitted
outputs must still pass the recorded encoder-exhaustion checks.

Hard limits include 180 seconds per in-flight recognition window, 240 seconds for
model setup, one hour for the worker stage, 18 GiB conservative ASR memory,
10 MB new durable private outputs and a 2 GiB filesystem free-space floor.
Memory accounting sums all old/new ASR RAM-file bytes plus resident memory of the
two workers, supervisor and owned decoder. This conservatively double-counts some
mapped model pages. The controller terminates only processes it created. Decoder
stdout is streamed with a 60-second no-output deadline; intentional queue
backpressure resets that idle deadline. Error logs are capped at 64 KiB.

## Resume and artifact integrity

An edition ID hashes the exact source audio, canonical decoded PCM, model revision,
settings and worker code. Completed editions are admitted only after rechecking
all chunk bytes, model/protocol identity, nonempty raw generation evidence,
contiguous coverage, the last partial tail, exact normalized turn metadata and
the assembled text. A filename alone never establishes completion.

Partial chunk outputs are atomic RAM-backed checkpoints. A resumed run decodes
the same source again and compares each cached window to its exact S16 bytes
before skipping inference. Partial caches survive a process interruption while
this environment remains running; RAM is not durable account storage.
Completed text, timecoded JSON, raw chunk evidence and compact receipts are copied
to a fresh private staging directory. Only a finished edition is atomically
renamed into its final location. A failed staging directory is preserved, and a
later attempt can assemble a new staging directory without overwriting it.

The worker-stage inference receipt is immutable and is separate from later copy
or finalization status. A later disk-copy failure therefore cannot invalidate the
receipt bound into an earlier completed edition. A completed-edition resume check
rehashes and validates outputs and launches no model workers.

## Actual pilot and overlap with the full batch

The frozen two-window pilot recognized the first 60 seconds of the first selected
OmNa recording. It completed in **13.43513 seconds**, with one window per worker,
46 and 48 whitespace words, and **6.802 seconds of observed inference overlap**.
The independent reviewer reproduced the whole first recording's S16 hash and both
window S16/float32 hashes, checked the six pinned model files and frozen code, and
confirmed 375/375 encoder frames for each output. This checks provenance and
execution; it does not verify the words against a human reference.

The full batch reuses those two exact verified outputs and schedules 267 remaining
windows. The 60-second pilot is part of the full 7,956.60625-second coverage, not
additional unique audio. Model loading, warm processing, cache hits and actual
process overlap are observed execution properties. No matched serial experiment
supports a causal speedup claim. Shared cloud analysis activity also affects wall
times. Final completed counts, resource measurements and no-inference resume
results are provided in the admitted `batch-asr.json` module.

The batch completed **all nine recordings and 269 windows**, producing **15,300
whitespace words**, compared with 15,215 in their old ASR counterparts. The main
worker stage recognized 267 new windows and reused the two pilot outputs. It took
**899.387 seconds (14.99 minutes)**, with **891.876 seconds of measured inference
overlap**. The dynamic queue assigned 134 and 133 new windows to the workers.
Their model loads took 3.527 and 3.447 seconds; median new-window real-time factor
was 0.22457. Conservative ASR memory peaked at 10,105,880,070 bytes (9.41 GiB).
These measurements describe this shared cloud execution, not a matched speedup
experiment. The sampled pilot and main stage are separate timing scopes.

The actual completed-edition resume revalidated all nine editions in **0.25673
seconds from process start through exit**, including source/output checks. It
launched zero model workers and performed zero new recognition. Completed receipt
hashes were unchanged. Four empty windows, two each in Bashar and Athina, remain
in the coverage denominator. No window met the ten-identical-token-run screen.
The shortest actual final tail was 0.6933125 seconds; it traversed all nine valid
encoder frames and was retained with empty text. No listening-based judgment of
empty-text causes or word correctness is implied.

An independent AI reviewer decoded all nine complete sources again after the
timed stage, checking all **127,305,700 S16 samples**, every S16/float32 chunk
hash, every displayed RMS/peak/word timeline value, raw generation durations,
encoder exhaustion, exact text assembly and canonical-registry joins. The 267 new
timing records and two original pilot-output hashes reconciled. The accepted
metadata-only module has SHA-256
`3d5e8c11e8cc4be3f5d7598788dc85611b8830d39ae8187be25d2ffb2c087ac8`.
This independently verifies computation and provenance, not word accuracy.

## Interpretation and visualization limits

Text is assembled in sample order with whitespace joining, without editorial
correction, overlap deduplication or speaker inference. Fixed-window boundaries
can split words or sentences and lose preceding context. Complete sample
coverage and encoder exhaustion do not establish complete linguistic recovery.
All speaker roles remain unknown, and no independent human word reference supports
WER or accuracy claims. Higher capacity, fluency or disagreement with the old
model does not prove improvement. The pretrained model supports 25 European
languages; this is not global language coverage or verified multilingual accuracy.

Per-window RMS dBFS, normalized peak amplitude and recognized whitespace-word
counts are exposed for source-linked timelines. These refer to actual sample
windows. They are not emotion measures, identified voices or word alignments.
An RMS-zero window has a null dBFS value with an explicit zero flag. Empty text
and runs of ten identical normalized word tokens are exploratory review leads;
they do not automatically establish silence, recognition failure or hallucination.
No windows are dropped from the full-coverage denominator by these screens.

The public module joins each edition to the canonical registry using publication
IDs or explicit legacy aliases, then checks the exact recording hash identity.
The registry's selected edition can be a publisher-written text rather than an
old ASR, particularly for OmNa. Registry text, old ASR and new ASR retain separate
identities and hashes; annotation offsets cannot be transferred silently.

## Reproduction and meaningful checks

`asr_batch_prepare.py` freezes and checks a source frame. `asr_batch.py` runs a
bounded queue using `asr_batch_worker.py`; `--max-new-chunks 2` creates the actual
sampled pilot. A fresh run ID against the unchanged frame/protocol resumes cached
chunks or verified completed editions. Each actual run uses frozen code copies.
`asr_batch_project.py` accepts the completed private manifest, no-inference resume
receipt and canonical registry, then emits only sanitized metadata through an
explicit `output-manifest.json` allowlist. Full source text stays private.
`asr_batch_resume.py` measures the no-inference verification from subprocess start
through exit, including the source and output checks that precede the controller's
worker-stage timer. Its separate receipt prevents reporting an almost-empty
worker stage as the entire validation time.

Six focused tests cover empty/malformed duration evidence, changed model/worker/
protocol/PCM cache metadata, a one-sample final tail and whole-decode hash mismatch,
interrupted finalization followed by successful resume, altered normalized turn
metadata, and termination of only the explicitly owned process. Independent AI
review supplements these tests with real source/model/output hashes and timings.
Neither constitutes human transcription verification.
