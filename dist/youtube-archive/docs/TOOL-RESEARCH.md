# YouTube archive tools: current guidance and applicable fixes

Reviewed **8 November 2026** using ordinary HTTP requests to official project
documentation, pinned source code, GitHub issue APIs, Google documentation and
the Stack Exchange API. This research lane made **no YouTube media requests**,
installed no downloader plugin, exported no cookies and used no relay websites.
Exact source URLs, dates, access depth and response hashes are in
[source-ledger.json](source-ledger.json). Raw research responses remain private.

The useful approach is a resumable **index first, audio second** pipeline. An
extractor update, working JavaScript runtime or PO-token provider can address a
specific extractor/origin failure. None demonstrates a repair for a failed
network tunnel before YouTube is reached.

## Current versions and prerequisites

The official latest stable release returned by GitHub was **2026.10.26**,
published `2026-10-26T22:25:26Z`. Its pinned `pyproject.toml` requires **Python
3.11 or newer** and **`yt-dlp-ejs==0.8.0`**. The separately inspected current
master commit is `412e7f0a4b0588fe884a02b344ac66a06538475b`; current-branch code
must not be described as identical to the installed release without checking.

The current [EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) requires:

- **Deno ≥2.3.0**, enabled by default, or **Node ≥22.0.0**, explicitly enabled
  with `--js-runtimes node` or a path-qualified equivalent.
- The compatible EJS scripts as well as the runtime. For Python installations,
  `yt-dlp[default]` supplies the companion dependency; pin the complete
  environment for a reproducible run. Updating only the downloader while leaving
  incompatible EJS behind can leave the runtime apparently installed but unused.
- `ffmpeg` and `ffprobe` for extraction, container fixes and artifact validation.

Node 24.19.0 was already exercised in the preceding static-site work and meets
the documented Node minimum. The collector must record the actual downloader,
EJS and ffmpeg versions it invokes; a different shell's PATH is not sufficient.
Do not copy the lower runtime minima from the historical
[#14404 announcement](https://github.com/yt-dlp/yt-dlp/issues/14404): the current
guide has superseded them. Bun support is now deprecated in that guide, and
PhantomJS is not the current YouTube challenge solution.

## What a complete channel index can mean

| Entry point | Useful scope | Important limit |
| --- | --- | --- |
| Channel root, such as `https://www.youtube.com/@HANDLE` | Current yt-dlp combines available videos, Shorts and streams tabs. | It can return nested playlists. The inspected code has a members-only-tab TODO; this is not every upload ever associated with an account. |
| `/videos` | The channel's ordinary video tab. | Does not substitute for Shorts or streams. An absent tab can produce an expected error. |
| `/shorts` | Short-form tab, retained for non-Bashar accounts. | Flat entries can lack reliable duration/date fields. |
| `/streams` | Scheduled, active and archived stream entries exposed by the tab. | Scheduled or ongoing entries are not finished audio files; retain their status and revisit later. |
| Uploads playlist | An additional inventory/reconciliation route. | Availability and authentication still apply. It is not evidence that private/deleted historical items can be recovered. |
| Official publisher's embedded YouTube links | Independent discovery of candidate IDs. | Such IDs are publisher-discovered references, not a completed YouTube channel enumeration. |

Prefer stable `channel_id` and `video_id` identifiers. Keep each video's channel,
tab and playlist memberships as separate observations, then deduplicate downloads
globally by extractor and video ID. A reupload under a different ID is a different
upload even when its audio later proves identical. Cross-tab overlap must not
inflate the unique-upload count.

`--flat-playlist` avoids full per-video extraction, but the README explicitly says
some metadata may be missing. `--lazy-playlist` changes iteration and disables
`n_entries`; neither flag proves pagination reached the end. Current channel code
follows continuation-only intermediate responses, including the case discussed
in [#12933](https://github.com/yt-dlp/yt-dlp/issues/12933). That issue's suggested
one-line patch was questioned by a project member because it could accidentally
include recommendations. Use a current supported extractor, not an old forum
patch or a custom loop that stops at the first empty-looking page.

Record the page/tab request, start/end times, exit status, entry count, unique ID
count, malformed/unavailable placeholders and terminal/completeness status.
Preserve partial results after interruption, but label them partial. A first page,
an advertised `playlist_count`, a feed, a search result or an empty blocked
response cannot establish an account-wide total. A defensible status is
**“completed traversal of the accessible view at this time”**, with historical
private/deleted totals still unknown.

The extractor can reload some playlists to show unavailable items. This preserves
evidence that an item is unavailable; it does not grant access to its media.
Treat private, deleted, members-only, age-restricted, region-restricted,
scheduled and active-live states distinctly when the source actually identifies
them. An opaque failure remains unresolved, rather than becoming “deleted.”

The official Data API is another supported indexing interface **when an API
project/key and destination access are available**. Google's channel resource
exposes `contentDetails.relatedPlaylists.uploads`; `playlistItems.list` accepts
at most 50 items per page and supplies `nextPageToken`. Its documented request
cost is one quota unit. This is an alternative documented service interface,
not an implemented or verified-access workaround in this research lane.

## Discovery is not a download archive

`--download-archive` is a skip ledger whose entries identify extractor/video IDs.
It does not prove that a file still exists, has an audio stream or has been
transcribed. Keep it separate from the discovery inventory and our verified
artifact/analysis ledger.

Two particularly important current semantics:

- `--force-write-archive` can write entries even under simulation. Never combine
  it with discovery and then count those entries as saved media.
- `--ignore-errors` can consider a download successful even if postprocessing
  fails. Normal continuation (`--no-abort-on-error`) plus explicit artifact
  verification is more suitable for trustworthy completion counts.

The inspected code uses a locked append when recording an archive ID. That lock
does not reserve a video before concurrent workers download it. Use a unique
`(extractor, video_id)` job key and an atomic job claim, with distinct states for
discovered, metadata-resolved, queued, downloading, media-verified,
transcript-available, analyzed and failed/deferred. Reconcile the archive against
verified files on resume. Keep a source ID/date/format/hash record rather than
adding research annotations inside yt-dlp's archive text file.

`--break-on-existing` is inappropriate for a first exhaustive inventory or an
archive with gaps: finding one previously saved item can stop traversal before
older unsaved items are reached. It is only an incremental optimization under
an explicit ordering and completeness assumption.

## Audio-first collection and controlled parallelism

Save the best available audio-only stream first, preserving a suitable native
codec/container. MP3 is not necessary for analysis, and a `.webm` file can contain
audio only. Use ffmpeg to create temporary PCM input for ASR rather than storing
large WAV copies by default. A fallback that downloads a combined video/audio
format must be separately declared because it changes transfer and storage cost.

For Bashar, resolve duration and require **at least 300 seconds**; unknown
duration is pending metadata, not permission to pass the filter. Other channelers
have **no minimum duration**. There is no overall Bashar count cap in the latest
user instruction. Keep ended broadcasts separate from scheduled/active streams
so an unbounded live capture does not silently enter a finite archive job.

These are command sketches for the collector after ordinary access succeeds,
not evidence that these commands downloaded anything in this research review:

```bash
# A bounded process writes a private temporary result, then validates its
# exit status and JSON before admitting it as an enumeration receipt.
yt-dlp --ignore-config --flat-playlist --dump-single-json --skip-download \
  'https://www.youtube.com/@HANDLE/videos'

# Audio-only pilot; paths and runtime are supplied by the actual environment.
yt-dlp --ignore-config --js-runtimes node --no-abort-on-error \
  --retries 3 --fragment-retries 3 --extractor-retries 3 -t sleep \
  --download-archive '/PRIVATE/archive.txt' \
  --write-info-json -f bestaudio -x --audio-format best \
  -o '/PRIVATE/media/%(channel_id)s/%(id)s/%(id)s.%(ext)s' \
  'https://www.youtube.com/watch?v=VIDEO_ID'
```

The actual runner should keep logs and info JSON private, since format URLs and
session-dependent metadata are not suitable public dashboard content. Validate
the produced file with ffprobe, check a nonempty audio stream and duration, hash
the bytes and then admit it as media-verified. ASR and analysis have separate
completion receipts.

Start with one successful pilot, then a small bounded worker queue and a shared
host-level rate budget. `-N` controls fragments within one video; it is not a
channel-worker limit. Current official guidance recommends delays for YouTube
request-rate failures, and `-t sleep` is a provided preset. A 429/temporary
origin failure needs backoff and a checkpoint, not more workers. Stop repeated
attempts when a shared transport failure affects every job. Preserve HTTP
`Retry-After` when supplied and avoid treating quoted guest/account request rates
as a guaranteed throughput allowance.

## Match the remedy to the failure layer

| Observed layer | Supported next action | What this does not fix |
| --- | --- | --- |
| Proxy `CONNECT` fails before origin TLS | Retain the destination, timestamp and sanitized error; diagnose the configured environment/network service. | EJS, cookies, client selection, PO tokens and browser extensions cannot establish that rejected tunnel. |
| Certificate trust failure | Verify the configured CA chain while retaining TLS verification. | Disabling verification does not diagnose a tunnel or player error. |
| Incomplete channel/playlist extraction | Check a current supported release, explicit tab, continuation behavior and logged interruptions. | A successful first page does not justify a complete count. |
| JavaScript challenge/runtime error | Verify the current release, compatible EJS, supported runtime and explicit Node configuration. | This is downstream of network access. |
| Origin authentication or private-content requirement | Use an authorized session only for content the account can access; keep credentials private. | Cookies do not grant access to somebody else's private media. Current extractor documentation says YouTube OAuth login no longer works with yt-dlp. |
| Missing client formats, SABR or PO-token warning | Inspect the actual verbose extractor warning and current client/PO-token guidance. | Forcing `all` clients or including `missing_pot` formats is not a verified repair. A missing format differs from a blocked transport. |
| Origin rate limiting | Bounded retries, documented sleep options, lower concurrency and resumable jobs. | Additional parallelism does not create a larger legitimate request budget. |
| Media/postprocessing failure | Check selected format, available bytes, ffmpeg output and ffprobe results. | A filename extension or process exit alone is not verified audio. |

The [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) distinguishes
GVS media requests, Innertube player requests and subtitle requests. Tokens have
client and content/session bindings, and the guide says manual reuse is no longer
recommended because many tokens are video-specific. It recommends supported
provider plugins for the `mweb`/GVS case when needed. The inspected
[BgUtils provider README](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)
itself says a token does not guarantee resolving 403 or bot checks. Its script
mode also warns about concurrency/cache limitations. This is a documented
origin-stage option to evaluate only for an observed applicable failure; no
provider was installed or represented as a fix here.

The collector's fresh **8 November 2026, 19:53 UTC** ordinary-route receipt
recorded `CONNECT` HTTP **403**, curl exit **56**, origin HTTP **0** and **zero
downloaded bytes** for a YouTube watch request. The same configured route reached
the GitHub API and README with tunnel and origin HTTP **200**. An independent
saved-receipt/header/body audit passed at 19:54 UTC; its SHA-256 is
`903f128fac7c9081cf35e840eed326cc5a25782c9dc1d58c52587b629f4546cd`.
This locates the observed failure before TLS to YouTube; it does not establish
the gateway's underlying policy or fault, nor a YouTube-origin bot rejection.
The collector held extraction after this preflight, recording **zero new
YouTube metadata extractions, media downloads or captions**. This literature
lane inspected those saved receipts without repeating the network request.

The earlier **24 October Brave diagnostic** observed the same failure layer.
The new receipt, rather than that historical browser result, supports the
current status. The preflight recorded yt-dlp 2026.10.21 and Node 24.19.0;
preparation of an isolated 2026.10.26 runtime is separate from a successful
YouTube request. No proxy sites, alternate egress or browser-security bypass
is proposed.

## What the Stack Overflow answers add—and where they are dated

The API returned six answer bodies selected for inspection. Votes and accepted
status are recorded in the ledger; they are not proof of a current repair.

| Answer inspected | Useful point | Local decision |
| --- | --- | --- |
| [59976565, 29 January 2020](https://stackoverflow.com/a/59976565) | Describes `youtube ID` archive lines and extracting IDs from a channel. | Do **not** prefill the download archive from discovered IDs: that would deliberately mark unsaved items as already downloaded. Use a separate inventory. |
| [58500968, 22 October 2019](https://stackoverflow.com/a/58500968) | Separates metadata/subtitle retrieval from media downloads. | Its old youtube-dl options, including annotations, are not a current command recipe. Check current yt-dlp names and keep caption success separate. |
| [78340276, 17 April 2024](https://stackoverflow.com/a/78340276) | Illustrates filtering before an item enters the archive. | Its `height>=?720` intentionally allows unknown values. Do not copy that unknown-value behavior into the strict Bashar duration rule. |
| [78858352, 11 August 2024](https://stackoverflow.com/a/78858352) | Suggests keeping comments beside archive entries. | Keep research state in structured sidecar metadata instead; do not rely on informal comments as a downloader API. |
| [77419511, 3 November 2023](https://stackoverflow.com/a/77419511) | Explains that selecting an extension is different from extracting audio with ffmpeg. | Preserve native audio when suitable and verify it; do not rename a video/audio container to `.mp3` as conversion. |
| [79362811, 16 January 2025](https://stackoverflow.com/a/79362811) | Uses flat JSON listing for later sorting. | Useful separation of enumeration and selection, but optional view counts and the dated sort URL are not completeness guarantees. |

The recent “bot” question returned by the API had no answer in the inspected
answer response. That is an access-limited research observation, not evidence
that no solution exists. The review did not scrape Reddit, Substack or external
proxy sites. The concrete supported improvements are current pinned
dependencies, correct pagination/accounting, audio-first verification, atomic
jobs and rate-aware resumption; their actual success must be measured by the
collector's receipts.
