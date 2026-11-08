# Publisher audio collection and transcription

This collection uses explicit downloadable media from publishers whose ordinary
HTTPS delivery endpoints work in the environment. It does not turn publisher
RSS entries into verified YouTube uploads. The current finite frame contains
204 Tracy Kumbera RSS entries, 20 entries in the current Multidimensional Soul
RSS feed window, and five directly inspected OmNa message/audio pairs. These
229 publications are not a census of historical sessions or channel uploads.

There is no minimum duration for these sources. The 299-second Tracy publication
previously excluded by the old rule is included. Bashar alone retains the
300-second minimum in its separate collection. There is no per-medium count
cap; finite discovery frames, accessible sources and measured storage determine
what can be admitted.

The selected audio frame completed on 2026-11-08: all 229 publications,
1,571,640,963 retained Opus bytes and 258,545.2438125 decoded seconds (71.82
hours). Their admitted original encodings total 5,418,526,850 verified bytes
before temporary-original cleanup. These are publication-level totals, not an
accounting of every network retry or interrupted transfer. There are 228 exact
original-byte families: two differently titled Tracy publications contain the
same encoded recording. All 71 exact publisher-caption links are reconciled.
Transcription is a separate ongoing stage. Failed recognition editions and
separately reviewed alternate editions have distinct provenance and statuses.

## Stored representations and identities

Each successful source is downloaded completely, hashed and decoded. A complete
48 kb/s CBR Opus derivative preserves the first audio stream's channel count.
The original and derivative are independently decoded to 16 kHz mono samples;
sample counts, durations and decoder completion are recorded. The permitted
duration difference is 100 ms. Original encoded bytes and SHA-256 are retained
in provenance, but the newly staged original is deleted only after the compact
copy and its receipts validate. The retained recording is therefore a **lossy
derivative**, not the original MP3 encoding.

Original-byte hashes define exact encoded-media families. They do not establish
independent historical sessions. A publisher account can contain interviews,
introductions, advertisements and several speakers; account context is not an
utterance-level medium or channellee annotation.

Raw media, full transcripts, publisher pages and detailed receipts remain in
the private workspace. Public JSON contains titles, source links, hashes,
durations, byte counts and processing status. GitHub Pages serves those
metadata and analyses, rather than the complete media archive. Workspace
retention is not a guarantee of permanent ChatGPT account storage.

## Executed phases

`acquire_publisher_audio.py` is the immutable v2 collector. Its SHA-256 is
`2663bef91d36ecb2ce1b9e7ba13edcb958716c6faa000ec90f77450d98a59165`.
It admitted 30 recordings before a deliberate transition to parallel RAM
staging. `transition_publisher_phase.py` stopped the identified collector,
checked its lock and surviving processes, revalidated completed receipts and
inventoried all physical files. One interrupted source's original and partial
Opus were preserved outside the admitted counts. Its original source identity
may subsequently be acquired successfully in v3; that does not make the old
partial an additional admitted source.

`acquire_publisher_audio_v3.py` reuses those 30 receipts without changing them.
It holds the original phase's lock and a separate current-phase lock, freezes
the source frame and both executed code versions, and runs at most two download
and conversion workers. A shared budget reserves predicted compact bytes
before admission; observed byte counts can never exceed that reservation or
the overall cap silently. A single coordinator writes the manifest. If one
worker fails, no new work is scheduled; the other already admitted worker can
finish and its result is recorded.

The v3 resource plan is an explicit change from v2 disk staging:

| Resource | v3 bound |
| --- | ---: |
| Disk free floor | 2 GiB |
| Disk operational reserve | 128 MiB |
| Retained Opus budget, including reused v2 sources | 1.62 GB |
| New original per worker, in `/dev/shm` | 160 MB |
| Compact output per worker, on disk | 26 MB |
| New PCM per ASR worker, in `/dev/shm` | 120 MB |
| RAM staging envelope | 600 MB |
| Additional cgroup headroom at admission | 512 MiB |

Two compact streams plus the 32 MiB provenance allowance fit within the new
disk reserve. Two originals and two maximum PCM files occupy at most 560 MB
of the RAM staging envelope. Both tmpfs availability and actual cgroup memory
headroom are checked; the tmpfs mount's nominal capacity alone is insufficient.
Existing recordings, models and archives are never deleted to make room.

Every phase has its own immutable executed-code copies and resource-plan
receipts. Later source or parameter changes need an explicit successor phase.
The older `research/batch-media/audio.py` remains byte-identical to its accepted
SHA-256 `7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64`.

## Text processing

The RSS frame contains 71 exact publisher-caption links, joined by publication
ID, GUID and enclosure URL. They first occur at frame position 59, so the first
30 audio sources legitimately have zero such links. An exact link avoids a
redundant ASR pass; it does not establish caption accuracy or audio alignment.

`audio_derivative_v2.py` validates the acquisition receipt and full derivative
before decoding. Its counted WAV writer enforces a 120 MB cap, requires natural
decoder EOF, and requires the complete PCM hash and sample count to match the
acquisition proof. It uses the existing local English-only Whisper tiny
CTranslate2 checkpoint, CPU int8, two CPU threads per worker, beam size five,
temperature zero and the frozen core's VAD configuration. No model download,
weight training, speaker diarization or human accuracy review is implied.

The collector's written OmNa message links are not treated as exact speech
transcripts. Those audio sources are also transcribed. Their text versus ASR
differences may include introductions, spoken additions, transcription error or
publisher editing; they are not automatically doctrinal differences.

Occasionally Whisper's final displayed end extends beyond the decoded audio.
`recover_asr_terminal.py` admits only an exhausted diagnostic with a single
eligible final-segment end overrun, both terminal endpoints within the frozen
30-second policy. It changes the final display end only, preserves all
recognized words and earlier timings, and binds the original failed request,
model, executed inference code and raw diagnostic. Such editions have
`normalization_status: terminal_end_display_repair_text_unchanged`. This is not
an accuracy or alignment repair; the terminal words remain unverified. Other
timestamp anomalies halt for review.

`continue_publisher_asr.py` supervises successive immutable acquisition
snapshots. It uses one ASR worker while acquisition is active and up to two
after the audio frame completes. Only the reviewed terminal display repair is
automatic. Lock contention waits; existing-receipt validation failures, stale
failure manifests, unrecognized diagnostics and resource failures stop the
queue instead of looping or silently admitting a partial output.

The first source-bound continuation was `continue_publisher_asr_v3.py`. One
tiny.en attempt for the Maureen St. Germain interview produced 2,244 segments,
including 2,152 identical recognized strings; 16 segment ends exceeded the
decoded duration plus the validator's one-second tolerance. That edition is
held and excluded from text analysis. The recording itself remains verified
and retained. This observation does not establish what the original audio
actually says; the recording has not been manually listened to for this audit.
An untimed export would not resolve the recognition-quality problem.

The v3 queue accepts only a reviewed hold ledger bound to that exact source,
audio receipt, model, failed request, exhausted diagnostic and executed code.
It preserves the failed artifacts, processes the other sources, and reports
`selected_frame_complete_with_recognition_holds` if held editions remain.
A different source edition or model does not inherit the hold automatically.
Public projection separates pending transcription, an admitted text, empty
recognition and a held failed edition; failed recognition is not failed audio
acquisition. A separately accepted alternate text can resolve a source's active
hold while retaining the earlier failed-edition history.

The Maureen interview's separate, reviewed alternate uses the existing cached
multilingual tiny checkpoint, English requested explicitly and
`condition_on_previous_text=False`. It produced 5,846 words in 474 segments
with unadjusted in-range timestamps. Its maximum exact repeated segment count
was two. This comparison is a diagnostic of recognized output; it does not
establish which model is more accurate. The first failed edition remains in
the hold history. See [FALLBACK-ASR.md](FALLBACK-ASR.md).

A second tiny.en attempt, the Sanjanaa Deodhar interview, produced 645 segments
with 18 ends beyond decoded duration plus one second. Its maximum repeated
string count was 44, so it is classified as multiple segments outside the audio,
not predominant repeated output. Its complete diagnostic is preserved without
transcript admission. Its separately reviewed multilingual tiny trial produced
8,078 words in 568 segments without timestamp normalization. The last endpoint
is 0.082 seconds beyond strict EOF, inside the frozen validator's one-second
tolerance; it is not a claim of exact audio alignment. The maximum identical
recognized string count was six. Both original failed PCM files remain
preserved. See
[FALLBACK-ASR-SECOND-SOURCE.md](FALLBACK-ASR-SECOND-SOURCE.md).

The v4 continuation adds a narrowly defined automatic quarantine policy for
future exhausted recognitions with multiple segment ends beyond audio EOF.
Every hold reruns source, model, executed-code, raw diagnostic and complete PCM
proof validation. Other integrity, resource or infrastructure failures still
halt. Initial reviewed rows remain byte-equivalent in successor ledgers; later
automatic rows identify their policy hash and explicitly state that they were
not individually reviewed or listened to. Failed recognized text is never used
as a transcript. Initial failed PCM files are preserved. Only newly generated
failed tmpfs PCM can be removed after full verification and a bound cleanup
receipt, retaining its request, diagnostic and regenerable Opus source.

## Reproducible commands

Supply private absolute paths for all raw inputs and outputs. Do not overwrite
an existing phase with a changed code version. The normal v3 invocation is:

```sh
python3 research/subscription-screening/acquire_publisher_audio_v3.py \
  --previous PRIVATE/publisher-audio-v2/transition-inherited-manifest.json \
  --transition PRIVATE/publisher-audio-v2/transition-to-v3.json \
  --output PRIVATE/publisher-audio-v3 \
  --ram /dev/shm/channels-et-publisher-audio-v3 \
  --captions PRIVATE/second14-texts/manifest.json --workers 2
```

Run the queue in the existing ASR environment:

```sh
python research/subscription-screening/continue_publisher_asr_v4.py \
  --acquisition PRIVATE/publisher-audio-v3/manifest.json \
  --output PRIVATE/publisher-asr-v2 \
  --pcm-root /dev/shm/channels-et-publisher-asr-v2 \
  --holds PRIVATE/publisher-asr-v2/recognition-holds-v2.json
```

`project_publisher_audio.py` makes a metadata-only public snapshot while saving
the exact input bytes privately by hash. Running processes and static published
snapshots have separate statuses. A dashboard snapshot is not evidence that all
later queue items have finished. New text analyses use a separately bound
completed snapshot and never silently change earlier fitted denominators.

Validation includes real synthetic-media conversion and decoding, short-source
inclusion, streaming byte caps, full PCM hash/sample checks, shared concurrent
admission, artifact and metadata tampering, partial preservation, lock exclusion,
empty recognition, bounded terminal normalization and fail-stop queue behavior.
Independent AI review also repeated full decodes of actual acquisition pilots.
Those checks assess pipeline integrity; they do not authenticate channeling
claims or establish transcription accuracy.
