# Source-bound audio measurements and local transcription

`audio.py` processes explicitly supplied local files. It does not download media,
models or captions, and it does not upload to Drive. YouTube downloads,
independently published creator videos and publisher RSS audio remain separate
providers: `youtube`, `publisher_video` and `publisher_rss`. Reprocessing a retained
recording does not create a new source or establish a matching YouTube edition.

## Input and execution

The private input is an object with `schema_version: 1`, a stable `batch_id`, and
`records`. Each record has `provider`, `source_id`, `medium_id`, `channel_id`,
`kind` (`video` or `audio`), absolute `local_path`, `sha256`, integer `bytes`, and
`verification_receipt: {path, sha256}`. The proof must contain exactly one matching
entry in `verified_artifacts`, binding those file/identity fields with
`status: "verified"`. The normal YouTube adapter is `export_verified.py`, which
reads the preserved collection ledger rather than treating an arbitrary URL as
downloaded media. When the proof declares provider, medium, channel or language
metadata, the manifest cannot contradict or erase it. The proof is rehashed
again after processing before any completed result is admitted.

YouTube records also require the exact `video_id`, `source_id: "youtube:ID"`,
`duration_seconds >= 300`, `duration_scope: "source_video"`, `is_short: false`, and
`metadata_refreshed_at_acquisition: true`. Their proof retains the exact metadata
hash, source video ID and measured duration. Every selected video, including an
independently published creator video, must contain both video and audio and be
at least five minutes long. The source is rehashed, reprobed and checked again
after processing. These checks concern bytes and declared acquisition identity;
they do not authenticate a voice or substantiate an attributed claim.

Use a private output directory outside project Git checkouts:

```sh
# Full first-audio-stream measurements only; no inference or model loading.
python3 research/batch-media/audio.py \
  --input /private/verified-media.json --output /private/audio-study

# Explicit local English inference using the existing cached model.
/workspace/channels-et-asr-venv/bin/python research/batch-media/audio.py \
  --input /private/verified-media.json --output /private/audio-study-asr \
  --transcribe --language en --model /workspace/channels-et-asr-cache/tiny-en
```

The model argument must be an existing local CTranslate2 Whisper directory;
model names, URLs and implicit downloads are rejected. Required model files are
hashed. Tokenizer special IDs distinguish English-only and multilingual
checkpoints, then the loaded model's actual language capability is checked.
`source_language` may be an explicit code or `unknown`. A known non-English
source is rejected by the English-only model. Unknown language with explicit
English selection is visibly an unverified assumption, not language detection.
Invalid or conflicting language metadata must be resolved before English-only
transcription; it cannot silently become an ordinary unknown-language assumption.
An existing compatible multilingual model can use `--language auto`; this is
rejected for English-only checkpoints. Multilingual inference is supported by
the contract but was not run in this iteration.

CPU settings are int8, two threads, one model worker, beam 5, temperature zero
and local VAD with a 500 ms minimum silence setting. Package versions, the VAD
asset hash, all model file hashes, source proof hash and executed script hash
enter the reproducibility binding. Only one worker may own an output directory;
the batch runs source records sequentially. The actual ten-source creator pilot
uses at most two such processes in separate directories, two CPU threads each,
with immutable per-source input manifests. Its private scheduler additionally
reserves remaining original-video bytes and unfinished PCM output space before
starting another source, retaining the 6 GiB free-space reserve. This aggregate
coordination is a caller responsibility; launching arbitrary independent CLI
processes does not inherit that scheduler's two-process limit. Network counts in an audio receipt
describe this local component, not the separately recorded upstream acquisition.

## Measurements and files

FFmpeg decodes the complete first audio stream to a 16 kHz mono signed 16-bit PCM
WAV. Its allowed input protocols are local file/pipe only. The original recording
is retained. Container duration and decoded duration must agree within the
declared two-second-or-two-percent tolerance; this operational tolerance is not
proof of complete original-event coverage. Inputs are bounded to 24 hours and
the input manifest to 2,000 records / 4 MiB. Before decoding, free disk must cover
the duration-derived WAV estimate plus a 6 GiB reserve. This is not a filesystem
quota or protection from unrelated processes writing concurrently.

`audio-metrics.json` reports:

- sample count, decoded duration, RMS and sample peak relative to digital full
  scale, dBFS, and DC offset;
- samples with absolute normalized amplitude at least 0.999, a clipping-risk
  indicator rather than proof of analog clipping;
- non-overlapping 20 ms windows whose RMS is at most −40 dBFS, sample-weighted
  quiet duration/fraction, longest contiguous quiet interval and quiet runs of
  at least half a second. The final partial window has its actual sample weight.

Exact digital zero has `null` dBFS, meaning negative infinity; it is not an
unknown measurement. Downmixing, resampling and compression affect the numbers.
Quiet-window time is not speaking time, and VAD duration is a separate model
output. No emotion, intention, truth, speaker identity or extraterrestrial
origin is inferred from acoustics.

With inference requested, `segments.json` contains the plain recognized `text`
and timestamped `segments`; `transcript.txt` includes readable time ranges and
`transcript.srt` uses SRT timing. ASR log probabilities and no-speech probabilities
are uncalibrated model outputs. Empty recognized speech has an explicit status.
Presenter, host and audience turns may mix; no diarization or per-turn claimed
entity attribution is performed. Every transcript remains machine-generated and
unverified until the promised independent listening/annotation work occurs.

## Resume, storage and privacy

Completed results are reused only when source, proof, model, parameters, tool
versions and script hashes match, and every retained artifact still rehashes to
its receipt. Changed output bytes are an error, not permission to overwrite.
An interrupted directory without a complete receipt remains unadmitted; inspect
it and use a new output directory. The tool does not resume midway through a
decoder or an ASR segment stream.

Timestamp guards reject nonfinite, negative, reversed, unordered or materially
out-of-duration segment times. A failure records the exact numeric values and
segment index privately, without changing the model output. The optional
`--retain-asr-diagnostics` switch additionally journals raw segments before the
guard and exhausts the inference generator after a timestamp failure. Its
request-bound diagnostic completion record remains explicitly unadmitted; it
does not count as a completed transcript. These private diagnostics can support
a separately documented and tested recovery without repeating model inference.
They are excluded from the finalized artifact handoff until such a recovery is
independently accepted.

`repair_terminal_end` is an explicit postprocessing helper, never an automatic
inference fallback. It permits only the last segment to overrun the recording,
with its start inside the final 30 seconds and its end at most 30 seconds beyond
the decoded duration (one Whisper analysis window). Every earlier endpoint must
be inside the actual recording and the final result must remain ordered. The
helper clips that final end to the measured EOF, retaining its original start
and end, the exact adjustment and an unverified terminal-text/alignment flag.
Words and segment order are unchanged. This repairs a display interval; it does
not show that the terminal words were spoken or improve recognition accuracy.

The actual sixth publisher recording produced one final endpoint at 7010.01 s
for a decoded recording lasting 7002.6453125 s. Its 886-segment diagnostic stream
was retained, and only that endpoint was clipped by 7.3646875 s. The separate
private repair receipt binds original inference and repair code hashes, model
and source checks, raw diagnostic/request hashes, and a fresh original-to-PCM
decode comparison. No third model inference was used. The first two failed
attempts remain distinct from the admitted repaired result. This observed case
was an EOF overrun, not the separately considered VAD-boundary hypothesis.

`audio-run.json` lists individual outcomes and receipt paths. The finalized
`final-artifacts.json` has the storage adapter's `{schema_version, batch_id,
artifacts}` shape, with exact per-file hashes, sizes and verification-receipt
bindings. It contains original media, decoded audio, metrics, request metadata
and available transcript formats. An empty or failed batch creates no fictitious
video, transcript or uploaded file. The raw sources, paths and full transcript
texts stay private; only reviewed numerical/source summaries belong in public
Git or Pages.

## Verification scope

`python3 -m unittest discover -s research/batch-media -p test_audio.py -v` runs
35 local tests using explicitly synthetic waveforms, an encoded synthetic
five-minute video, temporary proof files and no network calls. They check known
RMS/quiet fractions, partial windows, polarity, empty/zero signals, actual local
resampling, source/receipt identity, malformed HTML as media, language guards,
timecodes, disk reservations, completed-result reuse, tamper rejection and
interrupted-output behavior. Those fixtures do not count as source acquisition,
speech accuracy or a YouTube/Drive access test. Actual creator-video processing
has separate private runtime receipts.

The first full creator-video pass used an exact retained `audio.py` snapshot
before the additional proof-language/context guard was added. Its receipt binds
that executed version. The later guard passed 31 local tests, revalidated the
same actual input and rehashed all seven completed artifacts. The model, decoder
and measurement formulas were unchanged, so that first inference was not run
again merely to obtain a new script hash. Subsequent sources use the frozen
guarded version. This distinction is retained in the private post-inference
verification receipt rather than retroactively attributing earlier execution to
later code.

The additional exact timestamp diagnostics passed two further synthetic tests,
including exhaustion of a mocked failing segment stream without issuing a
completed receipt. No inference parameters or timestamp acceptance thresholds
changed in that diagnostic-only revision. Failed attempts and successful
previous-version receipts are retained separately rather than overwritten.
Two additional recovery tests check exact terminal clipping, unchanged text and
order, and rejection of earlier overruns, regression, nonfinite or broad timing
changes. The actual repair finalizer also independently checks all corrected
endpoints against the exact decoded duration. Its retained helper snapshot
predates an extra generic guard for earlier overruns under one second; that
edge case did not occur in this recording and the finalizer already rejected it.
