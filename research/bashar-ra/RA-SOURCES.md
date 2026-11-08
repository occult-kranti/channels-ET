# Ra source frame, editions, and acquisition

This collection studies the published **Ra / Law of One** material attributed to
the L/L Research sessions of 1981–1984. The attribution is the publisher's claim;
the corpus does not independently establish an extraterrestrial speaker or the
truth of the material. Collection and verification are different measurements.

**Completed on 7 November 2026:** all 106 selected published transcripts and all
**2,620 linked recording segments** are retained privately. The canonical audio
archive contains **115.08963 hours** of full-length, lossy 48 kbps CBR Opus copies
occupying **2,518,498,970 bytes**. The collector verified **6,620,288,811 bytes**
of source MP3s before conversion; the pre-existing original pilot is preserved.
No videos were downloaded. Historical recording gaps remain as described below.

## Source authority and finite frame

The [L/L Research site](https://www.llresearch.org/) is the originating publisher.
In this execution, ordinary HTTPS requests reached the origin but received HTTP
403 responses, including an origin `error code: 1010` page. This was recorded as
an origin denial, separately from any YouTube CONNECT failure. No alternate
egress, disabled TLS, account, checkout, or access bypass was used.

[lawofone.info](https://www.lawofone.info/) is maintained by Tobey Wheelock. Its
homepage explicitly states that it republishes the copyrighted material **with
permission from L/L Research**. Its [session index](https://www.lawofone.info/sessions.php)
defines 106 numbered sessions, and its [versions page](https://www.lawofone.info/versions.php)
describes the separate textual editions. These pages, the original-audio offer,
and the robots file were retained privately as evidence. Publisher permission to
republish is not treated as a general license for this repository to redistribute
the complete books or recordings. This repository publishes code and derived
analysis; the full text and media remain in private workspace storage.

## Textual edition

The analysis uses **one Lightly Edited page per canonical session**. It does not
combine editions as independent observations. The original volumes I–IV omitted
personal material; Book V restored much of it. The source's Relistened, Lightly
Edited, original-book, and 2018 *Ra Contact* editions are related editorial
products, not interchangeable verbatim transcripts. In the selected edition,
questions receive light editing and some missing audio is supplied from earlier
published text. See the source's version history for the detailed rules.

All 106 pages were retained and normalized. The frozen extraction contains
**5,153 printed turns and 278,601 whitespace-delimited words**. It preserves
session identity, printed question identifiers, publisher roles (`Questioner`,
`Ra`), bracketed notices, and response-only numbered contexts. A paragraph is a
turn within a session, not a separate session or independent recording.
Navigation, optional footnote-marker asterisks, and page furniture are excluded.
Footnote commentary is not incorporated into the speaking-turn corpus.

“Full” text coverage means the complete selected **published page**, not a
complete historical recording or an unedited conversation. Known examples:

- Session 1's printed notice explains that part of its tape was reused.
- Eighteen retained turns consist only of bracketed material. Four printed prompt
  slots are placeholders, including 1.6, 1.7, 1.8, and 69.1.
- Session 103 has a response under 103.3 without a separately printed prompt.
- The original extraction's `audio_gap_notices` field uses a narrow pattern and
  is not an exhaustive missing-audio detector. `[Inaudible]` and “not on tape”
  can appear outside that field. The retained text remains the reference.

Independent DOM parsing reproduced the 106-session, turn, and word counts and
verified 536 artifact hashes. This is an extraction/provenance check, not a
manual accuracy review of all words or a comparison of every transcript with
its audio.

## Published original-recording segments

The source's [audio page](https://www.lawofone.info/audio.php) explicitly offers
original recordings through normal session players, free official downloads,
and an official YouTube project described as work in progress. The normal
player pages `/s/N?au=1` expose finite MP3 links. All 106 player pages were
retained, yielding **2,620 unique published original-recording segments**.

The robots file disallows audio/query crawling for indexing. The operation here
is the user's requested private retrieval of the recordings explicitly offered
by the publisher, not search indexing or a public media mirror. No forbidden
authentication, origin denial, cart workflow, or network route was bypassed.

The official [Bring4th audio collection](https://store.bring4th.org/collections/ra-session-audio)
describes digitized cassette recordings. Its product notes warn that sessions
1–17 are faint and recording quality improves from session 18 onward. The store
also offers free digital products through a cart, but checkout was not attempted.
Store full-session files and player segments may be different editions of the
recordings; they are not silently counted as duplicates or substitutes.
Jim McCarty's later audiobook and synthetic speech readings are separate media
types and are excluded from this original-recording frame.

All 2,620 linked audio IDs have printed transcript context. Ten printed IDs have
no audio link in the frozen player pages: **1.11, 1.12, 1.13, 11.1, 51.0, 52.0,
88.1, 98.1, 98.2, and 99.1**. This is link coverage, not a proof that no other
recording exists. A complete download of this frame would mean all **published
segments**, not full continuous master tapes or complete surviving history.

The initial pilot was the actual `1-0.mp3`: **17,824,705 bytes**, approximately
**1,114.044 seconds**, and MP3 at about **128 kbps**, verified with `ffprobe`.
The pilot receipt binds its URL, source-page hash, headers, bytes, file hash, and
container inspection. No transcript was manufactured from this pilot, and
container verification does not establish voice identity or intelligibility.

At the initial frozen HEAD pass, all 2,620 URLs were checked without audio bodies:
2,619 returned valid audio headers totaling **6,607,616,289 bytes** and one
(`83-3.mp3`) returned HTTP 503. An isolated follow-up is recorded separately.
The byte budget must use a final successful per-URL inventory before bulk
retrieval. The separately authorized isolated retry succeeded, producing a final
source total of **6,620,288,811 bytes** across all 2,620 segments. Both the initial
503 and the successful follow-up remain in the evidence. A HEAD inventory is
availability/size evidence, not downloaded media.

The selected full-corpus retention format is **full-length Ogg Opus, 48 kbps
constant bitrate**, to fit the private workspace while keeping all published
segments. These are lossy derivatives, not retained original MP3 files. Each
source MP3 is first downloaded and verified against the exact headers, hashed,
container-checked, and fully decoded to a null sink. The entire first audio
stream is encoded with its original channel count; there is no trimming or
silence removal. The output is independently decoded, and its duration must
match the input within **50 milliseconds**, an explicit codec-padding tolerance.
Only after the retained copy and its receipt pass does the collector delete
that newly downloaded temporary MP3. The pre-existing pilot original stays.

The actual local pilot produced a 6,770,304-byte stereo Opus file from the
17,824,705-byte stereo original, with decoded duration differing by approximately
one microsecond. This verifies that one file's encoding path works; it is not a
perceptual assessment or proof that every source has the same compression ratio.
The finite batch enforces a **3 GiB free-space floor, 256 MiB shared scratch
budget, and 4 GiB retained-copy ceiling**. Two workers each use one encoder CPU
thread and a bounded share of scratch. Source hashes and sizes remain distinct
from retained-copy hashes and sizes. The final audio manifest, not this pilot or
the HEAD inventory, determines how many recordings were actually retained.

The completed archive passed all container, channel-count, byte, hash, and
decoded-duration checks. It preserves 2,618 stereo segments and two mono
segments; the maximum observed input/output decoded-duration difference was
**20 microseconds**. A separate finalizer rehashed every retained copy and
original-source receipt. An independent agent then checked all source IDs,
HEAD/source-page/proof/cleanup bindings, 106 ordered playlists, and bounded
retained-file hashes and probes. The canonical archive has 2,620 unique original
byte hashes and 2,620 unique retained-file hashes. The original MP3 pilot and
separate local Opus validation pilot are auxiliary artifacts of the same source,
not additional corpus observations.

The first finite pass admitted 2,590 recordings and recorded 30 isolated HTTP
503 failures with no source body bytes. One explicitly approved retry recovered
all 30, reusing every successful copy. Thus the batch made **2,649 media GET
attempts** (2,619 successful source GETs plus 30 failures) and reused the earlier
pilot GET, for **2,650 media GET attempts including that pilot**. The separate
frozen HEAD audit made 2,621 attempts. These counts exclude discovery HTML and
transcript requests. All failure evidence remains available; there are no
unretrieved links or unadmitted staging files in the completed audio archive.

## Reproducible artifacts and commands

The private root for this run is
`/workspace/channels-et-private/bashar-ra-2026-11/ra/`. It is temporary execution
storage, not a promise of persistent ChatGPT file storage or a Google Drive
upload. Retention elsewhere requires a separate authorized export.

Important artifacts:

| Artifact | Purpose |
|---|---|
| `discovery/` | Permission, edition, canonical frame, audio offer, robots, and origin-response evidence |
| `complete-transcript-manifest.json` | Frozen 106-session analysis manifest |
| `transcripts/` and `session13-retry/` | Source HTML, normalized text, extraction and retrieval receipts |
| `executed-source/acquire_ra-transcripts.py` | Exact earlier extractor version bound by the text receipts |
| `audio-pages/` | Retained normal player pages |
| `audio-inventory-complete.json` | Frozen 106-page / 2,620-link audio frame |
| `audio-coverage.json` | Printed-ID/link coverage and source limitations |
| `audio-head-audit/` | Individual HEAD receipts, initial complete pass, and separately recorded follow-up |
| `audio-head-retry-83-3/` | Isolated successful retry and merged complete size inventory |
| `audio-pilot/` | Actual pilot MP3 and its receipt |
| `compact-local-pilot/` | Actual local encoding test and decoded-duration comparison |
| `audio-compact/` | Full-length lossy Opus copies, source and retained-file proofs, attempt manifests, and ordered M3U playlists when retrieved |

The successful final pass produced `audio-compact/audio-manifest-complete.json`, the
canonical archive index and points to each `session-complete.m3u`. Earlier
per-attempt manifests and playlists remain as evidence and may omit segments
that were temporarily unavailable. Successful copies are reused during the
single inspected retry; failure receipts and HTTP-attempt counts remain visible.

Canonical complete audio-manifest SHA-256:
`05bafffc5c4526f50df50656082fb6ec3666f48c05f3b462972d5b893b43d202`.
The executed compact collector is retained as
`executed-source/acquire_ra-compact.py` with SHA-256
`04af8937f282fbe417dd4065a2f8e5294a6f5c13db9fb81873666664d98786a4`.
Execution used FFmpeg/ffprobe 7.1.5; exact versions, arguments, storage limits,
and the separate explicit-retry launch are retained in the execution receipts.

Frozen transcript-manifest SHA-256:
`1f303635eaee27db96a25bd227a779940a14e7c60f80ac95bcb0cb35482d417d`.
Frozen complete audio-frame SHA-256:
`c954a492fd07c8e4b90e046677431d71e6991755d7799fe87479e11e992c3590`.
These files are immutable. Later downloader development does not rewrite earlier
receipts to pretend they used the newer code. The public collector now includes
an audio-inventory mode implementing the same player-link discovery, with
stronger failure gates than the preserved exploratory script.

Example commands from the repository root, after retaining the source evidence:

```bash
python research/bashar-ra/acquire_ra.py --mode transcripts \
  --output /private/ra/transcripts --discovery /private/ra/discovery \
  --sessions 1-106 --workers 2

python research/bashar-ra/acquire_ra.py --mode audio-inventory \
  --output /private/ra/player-inventory --discovery /private/ra/discovery \
  --sessions 1-106 --workers 2

python research/bashar-ra/head_ra_audio.py \
  --frame /private/ra/audio-inventory-complete.json \
  --output /private/ra/new-head-audit

# Preserve any failed HEAD attempt and its separately authorized follow-up.
# The following is this run's inspected complete-frame transfer/storage budget.
python research/bashar-ra/acquire_ra.py --mode compact-audio \
  --audio-frame /private/ra/audio-inventory-complete.json \
  --sizes /private/ra/audio-head-retry-83-3/head-inventory-complete.json \
  --output /private/ra/audio-compact --max-bytes 6620288811 \
  --reserve-bytes 3221225472 --scratch-bytes 268435456 \
  --max-retained-bytes 4294967296 --workers 2 \
  --reuse-pilot /private/ra/audio-pilot/receipt.json

python -m unittest discover -s research/bashar-ra -p test_acquire_ra.py -v
```

Inventory and transcript runs use fresh outputs to retain earlier attempts.
When an isolated temporary source error is resolved, the completed manifest is
assembled from successful source-bound records; the original failed manifest
remains. There are no blind retry loops. The media downloader supports explicit
`--retry-transient` only for HTTP 500/502/503/504, preserves attempt histories,
and can reuse a verified pilot with `--reuse-pilot /private/ra/audio-pilot/receipt.json`.
Source-wide authentication, policy, rate, or transport failures stop future
requests and persist a halt record. Partial bytes remain unadmitted pending
inspection. No source error is relabeled as successful retrieval.

Audio admission checks frozen source-page identity, exact HEAD coverage, length,
MIME, ETag when supplied, an explicit total byte cap, SHA-256, and an MP3 audio-only
container. The original-retention mode requires at least 1 GiB free reserve;
the executed compact mode uses the 3 GiB floor and 256 MiB scratch budget above.
Two workers share a paced
start gate. Per-session ordered playlists reference retained segment files;
there is no second concatenated media copy or persistent decoded PCM. The tests
exercise synthetic success, tampering, wrong edition/identity, truncation,
nonmedia payloads, byte/reserve rejection, policy halt, transport halt, and
immutable explicit-retry records. Actual-source validation separately reparsed
all 106 saved player pages against the 2,620-link frame. Compact-mode tests also
cover duration/channel mismatch, output-size overrun, retained-budget rejection,
unchanged pilot retention, cleanup ordering, exact transfer budget, verified
resume, and explicit temporary-error retries. All **39 collector tests** passed;
the HEAD successor has a separate nine-test suite. `head_ra_audio.py` is a portable
successor to the privately retained executed HEAD script; it does not rewrite
the historical evidence to claim that the successor was used for the initial run.
