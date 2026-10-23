# Continuation acquisition, rounds 10–12

All files here belong to `/workspace/channels-ET`. The previous
`/workspace/bashar-index` research release is unchanged.

## Actual access and corpus state

The new environment's desired HTTP policy is unrestricted; its observed policy
state is unknown. A justified new ordinary public YouTube watch preflight at
21:09:59 UTC on 23 October 2026 still failed with a **proxy CONNECT 403**. A separate
primary-author transcript request to L/L Research session 1 at 21:10:28 UTC returned
**HTTP 403**, whose origin/intermediary source was not established. These are two
different access observations, not proof that either source is deleted. Do not tell
the user to enable the setting again merely because a desired setting has not
established actual access. No additional client or mirror was tried to evade them.

There are **zero newly retrieved captions, transcript bodies or audiovisual files**.
The 590 keyword queries, 157 inherited channel routes and 215 caption candidates
remain unexecuted. `acquisition-status.json` exposes all 106 candidate identities'
requested versus attempted fields. The general watch preflight is not counted as
106 candidate-specific attempts. The primary-author failure is separate from
YouTube availability. These records are dated receipts, not continuous monitoring.

`corpus-index.sqlite` is a metadata-only index: 925 inherited uploads, 106 inherited
candidate records, 140 explicit candidate-to-account attribution edges, two current
failed operations and **zero transcript artifacts**. The 140 edges are neither 140
unique channels nor the separate 157-route crawl plan. Titles, source URLs, publisher
metadata and context labels remain separate from actual speaker, which is unknown.
No raw speech text was reconstructed from frozen vectors or digest paraphrases.

The external `/workspace/channeling-atlas-private` folder was inspected for retained
corpus files; it contains only literature README/license files. No original raw
caption corpus was found there. No credentials or secret files were inspected.

## Implemented collection routes

`channel_pipeline.py` uses installed yt-dlp 2026.10.21 and
youtube-transcript-api 1.2.4. Installing these clients, implementing routes and
passing mocked controls do not constitute successful live collection.

Channel mode stores a durable state per inherited channel job. Default batches
request up to 100 returned entries and persist the next 1-based playlist position;
resuming continues from that position instead of silently crawling the same prefix.
`--batch-entries 0` requests the remaining returned public listing without a local
entry cap. The source can change between batches, so positional resumption is not a
fixed population sample. Returned upload IDs are preserved with route/person edges
in JSONL; cross-route duplicates remain discoverable. Completion means reaching the
end of the returned public listing, not proof of every upload, private/deleted item,
original session or practitioner's complete output. A block stops the affected
run rather than rotating clients or exit identities.

Caption mode accepts discovered-video JSONL or a plan, deduplicates upload IDs,
lists offered original tracks and by default attempts all of them. Language and
ASR/manual flags, segment count, source URL and artifact hash are retained. Each raw
document goes to `/workspace/channels-et-raw/captions`, outside Git. Partial track
successes and a later failure remain distinguishable; `all_offered_tracks_retrieved`
is false when the cap/failure prevents completion. Tracks are not silently translated.

The inherited `research/expansion/acquisition/collect.py` remains the 590-query
keyword-search route; it supports explicit job/person filters, round-robin batches,
and append-only resumption of unattempted jobs. Ordinary watch metadata refresh is
a separate mode. Flat listing fields are not promoted to complete watch metadata,
and publisher/entity context does not establish an actual speaker.

Network modes in the new pipeline require `--access-receipt` pointing to a successful
matching-video ordinary public-watch probe from the preceding 24 hours. Current
blocked receipts are rejected before another client is started. After a meaningful
access change, run a new dated standard-library preflight using the inherited CLI,
then use its actual successful receipt. Do not fabricate or edit a receipt to pass
the gate. No cookies, account login, paywalls, CAPTCHA solving, proxy rotation or
TLS verification bypass is implemented.

## Commands after actual access is established

From `/workspace/channels-ET`, with `ACCESS_RECEIPT` set to the successful dated
receipt path (not a token):

```sh
/workspace/channels-et-analysis-venv/bin/python research/continuation/acquisition/channel_pipeline.py channels --access-receipt "$ACCESS_RECEIPT" --max-jobs 3 --batch-entries 100
/workspace/channels-et-analysis-venv/bin/python research/continuation/acquisition/channel_pipeline.py channels --access-receipt "$ACCESS_RECEIPT" --max-jobs 157 --batch-entries 0
/workspace/channels-et-analysis-venv/bin/python research/continuation/acquisition/channel_pipeline.py captions --access-receipt "$ACCESS_RECEIPT" --input research/continuation/acquisition/runs/discovered-videos.jsonl --max-jobs 100 --max-tracks 0
```

The first small batch is for inspecting actual results/errors. Review before
increasing scope. Failed/blocked state is retained rather than silently retried;
start a new dated run directory after diagnosis to reattempt an affected route.
The previous successful acquisition runtime does not certify future source rights.

## Download planning and storage controls

Media mode defaults to a **no-network resource dry run**. The executed dry run used
three inherited upload records, estimating 51.2 MB total from duration ×160 kbit/s
×1.25 overhead. These are planning estimates, not measured download sizes. Files
with unknown duration/size are ineligible in this planning route.

```sh
/workspace/channels-et-analysis-venv/bin/python research/continuation/acquisition/channel_pipeline.py media --input research/continuation/acquisition/media-candidates.json --output research/continuation/acquisition/dry-run
```

Only explicit `--execute` and a successful access receipt start media retrieval.
The initial quota is 2 GiB across the external raw directory, with 4 GiB free disk
reserved and a 128 MiB per-file cap. The command prefers bounded audio suitable for
later speech analysis, with an explicit low-resolution fallback; it does not claim
all videos were downloaded. yt-dlp's size limit is combined with a live file/disk
monitor and 4 MiB/s rate limit. The monitor checks twice per second, so small buffered
overshoot remains possible; it does not promise byte-perfect quotas. Downloads stop
on quota, free-space, time or platform-denial failures. Partial files are retained
externally with their stop state, not certified as complete artifacts. Completed
files receive streaming SHA-256 hashes. Raw media and logs remain outside Git.
Actual per-file size, total raw-directory bytes and remaining free space are checked
again after the process exits, including a downloader that finishes before the
first polling check. A zero exit code that exceeds limits is recorded as
`quota_stopped`, with observed local-file hashes retained and no successful media
artifact claim. Only nonempty files with recognized audio/video extensions can
enter the successful artifact list. Quotas also bound caption writes; all-track
selection does not override external storage limits.

## Validation and remaining work

`verify_pipeline.py` currently passes eleven no-network control tests: access gate,
resumable offsets, stop-on-block, raw-directory separation, unknown-size/quota
planning, metadata-only/full-list command construction, metadata corpus integrity
and error redaction. Adversarial regressions additionally check unavailable
playlist slots and fast completed downloads that exceed the actual file cap.
An ID-only input row is normalized to `video_id` before caption/media routes use it.
Mock responses and synthetic IDs are removed with their
temporary directories; they are not empirical research records. These tests do not
establish extraction accuracy, live client compatibility, media rights or speaker
identity. An independent workstream should review the changed implementation before
the next release.
`verify_adapter_provenance.py` separately verifies the downloadable model adapter's
archive/member hashes, declared base license/revision and 48 training-row source
hash/pointer bindings. Its 218 passing local checks concern provenance, not model
quality, training-data truth or source-recording redistribution rights.

Actual collection remains unresolved despite unrestricted desired access. Useful
next work is access diagnosis through the supported environment route, then fresh
source probes, channel/search pilots, offered captions and source-aware annotation.
Human or audio validation and any cross-practitioner answer-agreement inference
remain separate from prepared collection software.
