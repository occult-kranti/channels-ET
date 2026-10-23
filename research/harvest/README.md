# Resumable indexed-source harvest

This is a prepared public-source collection queue, not evidence that every indexed
video or channel has been downloaded. The current ordinary YouTube watch probe
failed before TLS with `Tunnel connection failed: 403 Forbidden`, despite the
runtime reporting unrestricted, enforced network revision 5. The worker reads
that receipt and exits before claiming any job. It makes no alternate-egress,
cookie, CAPTCHA or access-control workaround attempts.

The imported inventory contains **942 distinct upload IDs**, **362 literal channel
routes** and **169 explicit playlists**. Three independent initial jobs per upload
(metadata, offered captions, video) plus the two enumeration units produce
**3,357 queued jobs**. Multiple routes can refer to the same platform channel;
neither route count nor publisher labels establish distinct speakers. Enumeration
deduplicates discovered videos by their actual upload IDs. Source references and
typed candidate/entity/publisher edges remain in the separate inventory files.

The independently fetched original-publisher podcast audio and its ASR outputs
have their own provenance and ledgers under `publisher_sources/` and `asr/`.
They are not YouTube downloads or verified equivalent editions. Main-worker
artifact counts exclude them; `raw_bytes` measures the entire shared raw tree,
including those branches and retained partial/quarantined files, at export time.

## Offline initialization and verification

Run from `/workspace/channels-ET`. Initialization is idempotent and preserves
attempts, discovered videos, source edges and completed state.

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/channels-et-harvest-venv/bin/python research/harvest/harvest.py init \
  --videos research/harvest/inventory/videos.jsonl \
  --channels research/harvest/inventory/channel-routes.json \
  --playlists research/harvest/inventory/playlists.jsonl
PYTHONDONTWRITEBYTECODE=1 /workspace/channels-et-harvest-venv/bin/python research/harvest/verify_harvest.py
PYTHONDONTWRITEBYTECODE=1 /workspace/channels-et-harvest-venv/bin/python research/harvest/audits/verify_worker_independent.py
```

These tests use temporary synthetic fixtures and make no network requests. Their
receipts bind the exact worker source hash; they validate controls, not real video
availability, caption accuracy or extraction quality.

## Gated execution and resume

The following command currently exits 2 with a blocked access gate and zero worker
attempts. Reading this existing receipt does not retry the denied request.

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/channels-et-harvest-venv/bin/python research/harvest/harvest.py run \
  --access-receipt research/harvest/access/preflight-2026-10-23-revision5.json \
  --workers 4 --max-jobs 12
```

After a meaningful access-state change, obtain a fresh ordinary successful watch
probe through the supported network route. A successful probe must be less than
24 hours old, and newer than any worker-observed access denial. Begin with a
bounded batch; only then raise `--max-jobs`. Repeating `run` resumes due queued,
retryable, partial and disk-wait work without recreating successful jobs. Each
operation has at most three worker attempts by default; transient retries receive
bounded exponential delay. Source/proxy denials stop submission and cancel active
work. Rate limits reduce concurrency. The default round-robin kinds are
`metadata,captions,video,channel,playlist,audio`.

Enumeration uses returned-slot cursors, including unavailable slots, and expands
videos, Shorts, streams and nested public playlist containers returned by the
extractor. Root routes are preserved as provided; they are not narrowed to a
`/videos` tab. The batch default is 100 returned slots. A bounded inline container
without a resumable route prevents a complete-tree claim. Completion means only
the end of the returned public listing and expanded containers; it excludes
private/deleted/omitted material and does not establish original-session coverage.

## Storage and artifact checks

All raw data stays outside Git under `/workspace/channels-et-raw`. The default
budget is 20 GiB for the whole shared tree with at least 6 GiB filesystem free.
Per-job caps are 256 MiB video, 128 MiB audio fallback, 64 MiB caption data, 16 MiB
listing and 4 MiB metadata. The initial video preference is a combined stream at
360p, with 480p as the alternative. An actual size/format limit can create a
separate audio fallback job; audio never counts as video. There is no promise
that a finite disk budget can retain every indexed full video.

SQLite claims and leases prevent duplicate concurrent same-ID jobs. Each running
job reserves its own remaining bytes; another job's temporary overrun cannot
erase that reservation. Main and publisher workers use the same exclusive
`.collection-worker.lock`, with parallel threads inside the owning process.
Planning, frequent monitoring, termination and post-exit validation bound storage
use; polling cannot guarantee zero transient overshoot. Partial files remain local
and consume quota. When the budget fills, export status and manage storage before
resuming; the worker does not silently delete research data.

Actual media requires a nonempty file, SHA-256 and successful `ffprobe`. Video
requires real audio and a non-attached video stream: embedded album art is not a
video. A material duration mismatch fails certification. Missing fragments abort
the download. `--ignore-errors` is not used, and exit zero alone is insufficient.
An unbound or hash-invalid completed-looking media file is quarantined with its
old/new hashes and source URL before download; it cannot be re-certified because
the client skips an existing filename. Quarantine bytes remain in the budget.
Ordinary `.part` resumption is separate. Hash-verified reused local media and
caption tracks are explicitly identified as reuse, not fresh body downloads.

Captions retain manual and automatically generated tracks separately, including
the same language. The worker does not request translations. Coverage is the
current offered descriptor slots saved or hash-verified locally, not verification
of transcript words, claimed entity or actual speaker. Failed partial caption
collections can resume. `--refresh-captions` explicitly re-fetches bodies.

## Environment and public exports

The dedicated environment uses the matched `yt-dlp==2026.10.21` /
`yt-dlp-ejs==0.8.0` pair and `youtube-transcript-api==1.2.4`. Node 24 is explicitly
enabled with `--js-runtimes node`; `ffmpeg` and `ffprobe` are installed. These
extractor prerequisites do not repair the current proxy tunnel denial.

The complete Python environment, including transitive dependencies and pip, is
pinned in [environment-freeze.txt](environment-freeze.txt). From the repository
root, reproduce it with:

```sh
python3 -m venv /workspace/channels-et-harvest-venv
/workspace/channels-et-harvest-venv/bin/python -m pip install --no-cache-dir -r research/harvest/environment-freeze.txt
/workspace/channels-et-harvest-venv/bin/python -m pip check
```

Node and FFmpeg are system prerequisites outside the Python freeze. The current
environment passes `pip check` and an offline installed-pin dry run; the receipt
[environment-verification.json](environment-verification.json) records that
scope. This does not claim a fresh installation was performed. Before release,
stop metadata writers and checkpoint `state.sqlite` with
`PRAGMA wal_checkpoint(TRUNCATE)`; its transient `-wal` and `-shm` files are ignored.

`state.sqlite` is authoritative. `summary.json`, `jobs.json`, `attempts.json` and
`artifacts.json` are atomic public metadata exports; raw media, captions, signed
format URLs and process logs stay local. Export rechecks file existence/size and
changed timestamps; permitted execution additionally hashes every certified
artifact before resume. A missing or changed artifact is reopened for work.
Leases have a heartbeat and check process start identity before recovery. Export
timestamps and raw-tree bytes are snapshots, not a global cross-file transaction.
See [schema.json](schema.json) for units and status meanings.
