# YouTube archive collection

This collector separates channel discovery, item eligibility, verified local
media, offered captions, queued speech recognition and completed analysis. It
does not treat an indexed URL, a successful extractor exit or a download-archive
entry as a downloaded recording.

## Actual access test, 8 November 2026

The ordinary configured route to a historically bound Daniel Scranton watch
page returned an Envoy **HTTP CONNECT 403**, curl exit 56, origin HTTP status 0
and no YouTube response body. The same configured route reached GitHub with
HTTP 200. The cloud configuration reported network mode `unrestricted` and
state `unknown`; that setting did not establish working YouTube access.

The exact private evidence is retained under
`/workspace/channels-et-private/youtube-archive-2026-11/route-01/`.
The watch receipt SHA-256 is
`3edbd4e5a0c8bc99ac139c210b643d41a6d9ba2faba61d8ca17856db4a74007f`.
An independent reviewer checked the saved header and receipt hashes. This is a
failure before reaching YouTube, not evidence of a YouTube bot challenge,
deleted video or unavailable caption. Collection was therefore held globally:
**zero new tab, video-metadata, media or caption extraction operations**.

The current published `collector-status.json` binds the exact inventory used
and records this hold. Existing publisher recordings and earlier caption
cohorts are reconciled separately; none are relabeled as new YouTube downloads.
The locally generated one-second test audio is only a software fixture.

The final initialized edition contains **2,812 distinct observed IDs across
297 account references**. Of these, 2,159 indexed eligible/duration-probe IDs
are held by the shared route gate, 22 retain historical Bashar-duration holds,
and 631 await relevance review. These are queue states, not a complete channel
upload census. Its private resumable store is
`/workspace/channels-et-private/youtube-archive-2026-11/collector-03`;
the bound inventory SHA-256 is
`0411954faeccfb5637a1ef01a154c638cff0927b8baafbffe5cbd5ef8d2bcfff`.

## Supported runtime and investigated fixes

An isolated environment at `/workspace/channels-et-youtube-venv` contains
`yt-dlp[default]==2026.10.26` and `yt-dlp-ejs==0.8.0`, with Node 24.19.0 and
FFmpeg/ffprobe 7.1.5. The older analysis environment remains unchanged.
Installation and an offline `YoutubeDL` initialization were recorded under
`/workspace/channels-et-private/youtube-archive-2026-11/runtime-01/`.
Node is explicitly enabled through `js_runtimes={'node': {}}`; no remote code
components are fetched during collection.

Sources inspected:

- [Official yt-dlp release 2026.10.26](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.26), obtained through the official latest-release API.
- [yt-dlp README](https://github.com/yt-dlp/yt-dlp#readme), including supported JavaScript runtimes, EJS dependencies and the documented recommendation to reproduce extractor site-change bugs with a current release/nightly.
- The README's pointers to [EJS setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS) and [PO-token guidance](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) identify origin/client issues to investigate only after the route reaches YouTube. Those pointers are not evidence that a token or browser change fixes this CONNECT denial.

Updating an extractor and configuring its JavaScript runtime are supported
client-side preparations. They do not repair a gateway rejection before the
origin request. The collector uses ordinary configured networking: it does not
implement relay sites, alternate proxy routes, credential extraction or access
control bypasses. A fresh ordinary probe is appropriate after the environment
route is repaired; repeatedly launching the same blocked video request is not.

## Scope and admission

- There is no item-count or publication-date cap.
- Bashar items, including positively attributed reposts, require at least
  300 seconds of **decoded audio**. Other sources have no duration minimum;
  their relevant Shorts are eligible. Unknown duration remains pending.
- Fresh titles containing the explicit name Bashar or explicit attribution
  through/by Darryl Anka conservatively raise that item's floor to 300 seconds.
  This cue is not a verified speaker-identification result.
- Jamie Butler remains excluded as requested. No mixed publisher account is
  assumed to contain only one medium or one type of content.
- Inventory duration/exclusion eligibility does not prove content relevance.
  Existing indexed eligible IDs may queue, subject to fresh uploader and
  duration checks. Newly enumerated uploads from unreviewed candidate accounts
  remain pending relevance review. Nonexcluded candidate accounts can still
  be inventoried without declaring every upload a channeling video.
- Current live, upcoming and unfinalized post-live streams are deferred.
  Completed streams use the same item checks as other videos.

The input is `inventory.json`, with `accounts`, `videos` and account/video
associations. Exact channel IDs are preserved separately from handles and weak
historical associations. A fresh tab response must supply a stable `UC…` ID;
it cannot silently replace an earlier resolution. Fresh video metadata must
identify that exact video's uploader within the accepted account set. Public
per-account retained counts require this verified owner, not merely a weak
historical association.

## Enumeration and resumption

The collector consumes the `videos`, `shorts` and `streams` tab generators
without `playlist_end`, item-range or date filters, persisting every valid
video ID as it arrives. IDs are deduplicated across tabs and accounts while
association provenance remains intact. Invalid slots, interrupted generators
and exceptions are recorded as partial or failed states.

Inventory-listed legacy account routes with one name segment are supported,
including `/BasharChanneledbyDarrylAnka`. Watch, playlist, search, other reserved
platform endpoints and arbitrary nested paths are rejected as account routes.
The literal route remains an observation until the extractor supplies a stable
channel ID; its inclusion does not by itself prove account ownership.

`extractor_completed_accessible_tab` means the generator ended without a
declared cap or exception. It does **not** independently establish that the
platform returned its final continuation or expose private/deleted uploads.
Consequently `uploaded_total` stays null. Raw entries, runtime, exact options,
error disposition and counts are retained privately for each tab attempt.

SQLite maintains claimed jobs, attempts, editions, membership, files and the
ASR queue. A process lock prevents two collector processes using one archive.
Completed artifacts are rehashed before reuse; changed files require review.
Failed attempts retain their own partial edition, and new attempts do not
overwrite it. Resumption is at the verified-job level; cross-edition partial
byte transfer is not claimed. A new input edition should use a fresh archive
root so its status binds precisely to that immutable inventory.

## Download, caption and storage checks

After metadata admission, the requested format is `bestaudio/best`. An
audio-only original is preferred; a combined fallback is honestly counted as
a retained video. Each completed file receives a SHA-256, ffprobe inspection
and strict full decoding of its first audio stream to hashed 16 kHz mono
signed-16-bit PCM. `-xerror -err_detect explode`, a nonblocking decode deadline,
zero decoder-error output, positive sample count and duration reconciliation
are required. Decoder processes are closed and reaped on failures. The
Bashar floor applies to the resulting sample-derived duration.

Manual captions are preferred over automatic captions. Within each class,
the declared original language is preferred, then English, then another
offered language. Tracks with `tlang` translation requests and live chat are
excluded from the actual extractor input, not merely from display metadata.
Accepted JSON3 or VTT becomes an exact raw caption artifact and normalized
JSON/text files. Caption timing, translation quality, diarization and factual
claims are not independently validated. Missing or failed captions put
verified audio in the ASR queue; **queued is not transcribed or analyzed**.

One fully verified audio artifact plus its caption/ASR disposition establishes
the acquisition pilot. A captionless recording can therefore unlock bounded
parallel acquisition without falsely claiming a transcript. The default is
two media workers, with an allowed range of one to four. Enumeration precedes
the media queue and is currently sequential. A shared CONNECT denial, origin
rate limit or bot challenge stops the run. Three distinct consecutive jobs
with the same generic extraction/network or origin/media-403 class also hold
the run for inspection; this circuit breaker does not diagnose its cause.
Per-item private/removed/restricted states remain distinct.

Reservations and progress checks preserve a 2 GiB free-disk floor plus an
8 MiB guard. A resource stop leaves incomplete jobs and existing files intact.
No finite cloud disk can promise retention of all future channel uploads;
collection resumes when authorized storage capacity is available.

Raw media, captions, logs and transcripts stay outside Git checkouts. This
managed workspace is not a promise of permanent ChatGPT account storage or a
Google Drive upload. The public export contains only metadata, hashes,
counts, exact owner associations and state labels. No private filesystem
paths, signed media URLs or source transcript bodies are exported.

## Commands

```bash
python3 -m venv /workspace/channels-et-youtube-venv
/workspace/channels-et-youtube-venv/bin/python -m pip install --no-cache-dir -r research/youtube-archive/requirements.txt

# Use a fresh private root for the accepted inventory edition.
/workspace/channels-et-youtube-venv/bin/python research/youtube-archive/collector.py --root /workspace/channels-et-private/youtube-archive-next init --accounts /path/to/inventory.json

# Run this ordinary probe after a route change; retain the printed receipt path.
/workspace/channels-et-youtube-venv/bin/python research/youtube-archive/collector.py --root /workspace/channels-et-private/youtube-archive-next probe --url 'https://www.youtube.com/watch?v=W9-Y8E-eTFg'
/workspace/channels-et-youtube-venv/bin/python research/youtube-archive/collector.py --root /workspace/channels-et-private/youtube-archive-next run --gate-receipt /path/to/receipt.json --workers 2
/workspace/channels-et-youtube-venv/bin/python research/youtube-archive/collector.py --root /workspace/channels-et-private/youtube-archive-next export --output /path/to/new-public-status-edition

/workspace/channels-et-youtube-venv/bin/python -m unittest discover -s research/youtube-archive -p test_collector.py -v
```

A passed transport receipt expires after one hour and never implies media
success. A failed receipt keeps the global hold without making fresh
per-video requests. `--no-enumeration` resumes the existing indexed queue;
it does not make any account's upload inventory complete.

The focused tests cover global gating, exact-owner credit, per-item duration,
decoded-duration boundaries, boolean duration rejection, caption track
pruning, reservations, incomplete pagination, cross-tab identity conflicts,
unsafe path IDs, repeated-error holds, strict decoder failure/cleanup, a real
one-second local decode and captionless pilot/ASR behavior. A loopback HTTP
integration fixture also exercises the actual installed yt-dlp downloader,
subtitle selection and processing through verified audio and caption text;
only its metadata extractor is replaced. Concurrent reservation tests enforce
the shared disk floor. All 17 focused tests pass in the pinned runtime, including
legacy account URL construction and rejection of non-account paths. Live YouTube tab,
media and caption success remain unverified in this environment until the
ordinary route reaches the origin and a real acquisition passes these checks.
