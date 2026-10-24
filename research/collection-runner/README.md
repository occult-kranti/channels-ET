# Isolated long-form collection runner

Current execution is **blocked**. The actual policy inventory produced 2,408 planned jobs: 942 metadata jobs, 733 caption jobs and 733 video jobs. Neither `run-one` nor the two-worker bounded controller claimed a job or started a downloader under the retained access denial. No new YouTube media, captions or metadata were collected by this runner.

The default cap is **100 unique Bashar-associated YouTube IDs**, across every uploader and format. A video's captions, audio and video share one source-ID slot. The 19 previously retained podcast recordings are separate materials and do **not** consume this default YouTube cap. An optional, explicitly selected conservative scenario limits new Bashar IDs to 81. The other practitioners have no source-count cap; all operations remain subject to the shared storage budget and the explicit bounded run size.

## Offline use

From the repository root, these commands initialize a new private ledger from the source-pinned policy and retain the current denial without making network requests:

```sh
python3 research/collection-runner/runner.py init \
  --blocked-probe research/youtube-access/brave/watch-receipt.json \
  --runtime-receipt research/access-repair/diagnostics/runtime-revision6.json
python3 research/collection-runner/runner.py plan
python3 research/collection-runner/runner.py dry-run \
  --runtime-receipt research/access-repair/diagnostics/runtime-revision6.json
python3 -m unittest discover -s research/collection-runner -p 'test_guards.py' -v
```

`plan-summary.json`, `plan.jsonl`, `dry-run.json`, `blocked-run-one.json` and `blocked-bounded-run.json` record the actual offline preparation and refusal. The synthetic adversarial tests exercise queue transactions and transport mocks; their fixture access rows are not evidence of real platform access. `verification.json` records the executed test results and source hashes.

## Eligibility and identity checks

Inherited selection is a plan, not permission to download. Every asset requires fresh, source-file-hash-bound platform metadata with an exact canonical video ID and duration of at least 300 seconds. Positive Shorts URLs, extractor `media_type=short`, `is_short=true`, historical Shorts evidence or fresh `#shorts` title markers remain held. Ongoing live durations, unresolved duration conflicts and ambiguous Bashar context are metadata-only.

The installed, pinned `yt-dlp==2026.10.21` emits `media_type` rather than an `is_short=false` field for ordinary YouTube videos. Its `YoutubeIE` source classifies `short` from `microformat.isShortsEligible`, `livestream` from `isLiveContent`, and otherwise `video`. The runner uses that extractor classification with a canonical HTTPS watch identity and explicit positive-Shorts vetoes. Completed recorded streams need a completed live status. Missing format evidence requires a source-hashed review; the runner does not pretend that a missing boolean is verified. This is an extractor-based format check, not a human audit. The local source inspection and option-parser checks are retained in `toolchain-inspection.json`.

Fresh title, uploader, channel, description, tags and other explicit metadata are checked again for `Bashar` or `Darryl Anka`, together with inherited provenance. A newly identified Bashar item consumes a global slot before an asset claim. A positive Bashar match cannot be reviewed into the uncapped group. These are conservative association rules, not verified speaker or entity attribution; mere mentions can also consume a slot. Reviews must bind the exact current metadata hash. Changing metadata invalidates prior conflict and format resolutions. Metadata objects must match their hashed JSON files.

SQLite `BEGIN IMMEDIATE` makes admission, unique-ID cap slots, leases and per-job byte reservations atomic across processes. Slots remain consumed after failed attempts, which is stricter than counting successful downloads alone. This prevents repeated failures, aliases or formats from opening extra slots. Expired leases retain their reservations and block that source until an operator checks its process and quarantine; they never requeue automatically. The private raw directory binds to one cap database. Never delete or replace that database to reset the cap; moving it requires migration of its existing slots and state. This is an operational guard for cooperative processes, not protection against someone editing the database or source code.

## Access gate and future bounded execution

The private ledger is `/workspace/channels-et-raw/collection-runner/state.sqlite`; raw metadata, signed URLs, logs and outputs stay outside Git. The shared budget root is `/workspace/channels-et-raw`, including already retained audio and all other files. The runner uses the same `.collection-worker.lock` as the earlier collector, a 20 GiB aggregate budget and a 6 GiB free-space reserve. Per-job reservations are 4 MiB metadata, 8 MiB captions, 128 MiB audio and 512 MiB video. It checks running and completed output sizes, shared physical bytes, free space and final artifact reservations. The subprocess monitor can stop a write after its polling interval; it is not an operating-system disk quota. Oversized or failed outputs stay quarantined and are never admitted as verified artifacts.

Network execution requires the explicit inherited HTTPS proxy, verified TLS, and a runner-created successful watch probe from the exact current configuration within 300 seconds. The runtime input must be a dated, current `cloud_environment.environment_status` observation with matching configured/observed revision and typed network mode/state. A browser installation/package receipt is rejected. Fingerprints bind the revision, network mode/state, proxy and CA configuration; observation timestamps and JSON formatting do not create a new configuration, and policy lists use sorted unique values. The complete runtime-file SHA is retained separately for provenance. Explicitly labeled synthetic runtime fixtures cannot authorize a real probe or collection. The initial package-receipt binding was corrected without erasing its blocked record; see `runtime-binding-migration.json` and the retained legacy dry run.

External success JSON cannot unlock the gate: imported receipts can only record a denial. Redirects may not leave the canonical HTTPS YouTube watch endpoint or requested ID. The saved watch response must contain a parsed player response with the requested ID and `playabilityStatus.status=OK`. Proxy/CA/runtime fingerprints are hashes; credentials are never printed or saved in public exports. The strict redirect rule follows the reviewed access-diagnostic approach in `research/access-repair/diagnose_connection.py`, with additional same-ID and player checks.

A denied configuration cannot be repeatedly probed. After an actual supported configuration change, an operator may request one new ordinary probe. An expired **successful** probe can be explicitly renewed on an otherwise healthy configuration. Each collection claim rechecks the live gate atomically. Any bounded acquisition or validation failure pauses that configuration globally, preventing a queue of fresh attempts after a broad failure. There are no automatic downloader retries or alternate egress routes.

Only after access has actually been restored can the following commands perform work:

```sh
python3 research/collection-runner/runner.py probe --video-id fZmY4xS_qXE \
  --runtime-receipt PATH_TO_NEW_CURRENT_RUNTIME_RECEIPT
python3 research/collection-runner/runner.py run-bounded --workers 2 --max-jobs 6 \
  --runtime-receipt PATH_TO_NEW_CURRENT_RUNTIME_RECEIPT
```

These commands were not used to collect material in the current blocked environment. The controller schedules metadata then caption/video assets per source, with at most two workers and an explicit upper bound on job invocations. It stops when the gate expires or a global failure occurs; it does not automatically renew the probe. Asset acquisition uses `--load-info-json` from the exact fresh metadata whose identity was checked before cap reservation, avoiding a silent second extraction that changes identity. Metadata also expires after 300 seconds. An explicit `refresh-metadata --source-id youtube:ID --reason REASON` queues one refresh and retains an event record of the previous attempt. Large healthy runs may therefore need bounded batches and explicit successful-probe renewal.

The existing pinned harvest virtualenv is reused read-only; no package or old ledger was changed. The downloader uses explicit proxy settings, system CA verification (`--compat-options no-certifi`), ignored user configuration and zero extractor/fragment/general retries. Metadata output IDs must match. Captions require WebVTT timestamped cues; video/audio requires a matching stream and `ffprobe` duration at least 300 seconds matching the source metadata. These checks do not establish transcript accuracy or speaker identity. Every accepted output remains `verified_quarantine`, not a public or uploaded artifact.

## Enumeration and storage handoff

This runner has not crawled every channel, playlist or search. Separately obtained enumeration artifacts can enter through a real offline adapter:

```sh
python3 research/collection-runner/runner.py import-discovery --input CACHED_ENUMERATION_JSON_OR_JSONL
```

The adapter accepts a flat JSONL stream or JSON `records`, `videos` or `entries` list, validates each 11-character YouTube ID, pins its target URL to `https://www.youtube.com/watch?v=ID`, deduplicates it globally and creates **only a metadata job**. Claimed URLs and inherited duration/identity fields do not grant asset admission. After fresh metadata, a source-hashed `review` can explicitly admit a resolved item. Positive Shorts or Bashar evidence cannot be overridden. New discovery must enter this policy path; do not call the old worker's automatic enqueue/download flow. Pagination or source polling is a separate, access-gated metadata operation, and no enumeration completeness is claimed here.

The old harvest ledger and original 19-source study remain untouched. There are currently no collected YouTube files to hand to Drive. `archive-additional-artifacts.json` is an honest empty handoff; an actual future archive needs validated retained bytes, explicit practitioner/uploader labels and the matching selected-policy receipt. The runner performs no cloud upload or deletion.
