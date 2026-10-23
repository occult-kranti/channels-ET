# Local speech recognition for original publisher audio

This stage transcribes actual publisher-RSS audio saved under
`/workspace/channels-et-raw/publisher-audio/`. It does not retrieve YouTube media.
The source ID, stable enclosure URL, audio path and SHA-256 must match a completed
record in `../publisher_sources/publisher-summary.json` before decoding starts.

The CPU baseline is faster-whisper 1.2.1 / CTranslate2 4.8.3 using the MIT-licensed
`Systran/faster-whisper-tiny.en` conversion, pinned by immutable Hub revision and
official Git/LFS checksums. This is a fast English ASR baseline, not a SOTA claim.
The model cache stays outside Git at `/workspace/channels-et-asr-cache/tiny-en`.

```sh
python3 -m venv /workspace/channels-et-asr-venv
/workspace/channels-et-asr-venv/bin/python -m pip install -r research/harvest/asr/environment-freeze.txt
/workspace/channels-et-asr-venv/bin/python -m pip check
/workspace/channels-et-asr-venv/bin/python research/harvest/asr/download_model.py
```

Run `transcribe.py --help` for a single completed source, or use `run_queue.py`
to process completed publisher audio with two independent workers/two CPU threads
each. Keep raw speech and transcript text outside the repository. The cloud image
supplies FFmpeg/ffprobe; the downloader verifies each source file before ASR.

Output includes segment JSONL, plain text, SRT and a source-bound receipt. A per-
output process lock prevents duplicate writers. Existing results are reusable only
when their recorded source, settings and actual output bytes validate; interrupted
or stale receipts are retained. The source archive records the exact script used
by the first completed runs before later concurrency hardening. No transcript text
is copied into the public summary or GitHub Pages downloads.

```sh
/workspace/channels-et-asr-venv/bin/python research/harvest/asr/build_summary.py
```

`summary.json` rechecks actual local audio/transcript hashes and exports counts and
metadata only. Clipped diagnostics are separate from full decoded-audio passes.
Decoder exhaustion with VAD does not establish that every spoken word was captured.
Names, words, punctuation, speakers and timestamps remain unverified; no diarization
or human accuracy annotation was performed. Frame quantization can place a segment
slightly beyond the measured duration; the executed validation allows two seconds
and retains the actual timestamps rather than silently correcting them.

The first two attempts failed before transcription because newer PyAV 19 removed
an argument used by faster-whisper 1.2.1. Pinning PyAV 16.1.0 restored actual decoding;
both successful full-file runs and this failed setup are recorded. See
`setup-events.json`, per-source receipts and the independent artifact audit.
