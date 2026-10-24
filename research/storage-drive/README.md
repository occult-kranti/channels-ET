# Private Google Drive archive workflow

The archive is **prepared locally, not uploaded**. The user selected “Connect Google Drive in Apps,” but this environment still exposes no Drive tool, configured rclone remote or authorized Drive identity. That selection is not an OAuth completion receipt. No new Drive folder exists, no Drive file has been uploaded, and the reported 5 TB allowance has not been checked against an account. See [storage-state.json](storage-state.json) for the dated evidence and [verification.json](verification.json) for executed checks.

The current offline plan covers 99 existing private cloud artifacts: 20 original publisher audio responses, 60 ASR output files for those 20 recordings, and 19 primary publication/text/feed files. These are **not YouTube downloads**. The frozen 19-recording Bashar cohort and separate Athina recording retain their different provenance. Primary texts include authored RSS material and a publisher-issued spiritual Guides transcript; they are not validated biological ET testimony. No speaker or ASR accuracy is implied by archiving.

Full audio, transcripts and publications remain under `/workspace/channels-et-raw`, outside Git and Pages. Repository files contain code, hashes, acquisition metadata and plans only. User-reported available capacity does not imply permission to publish copyrighted material.

## Organization and integrity

Each new archive uses one dated, unique directory in the explicitly selected user's **My Drive root**:

```text
channels-ET-private-YYYY-MM-DD-UNIQUE/
  provider/practitioner/uploader/upload-ID/
    audio/recording.mp3
    video/video.webm
    transcript/transcript.txt
    transcript/transcript.srt
    transcript/segments.jsonl
    primary-text/document.txt
    source-document/document.pdf
    source-metadata/feed.rss
    <each file>.provenance.json
  manifests/archive-manifest.json
  manifests/SHA256SUMS
```

Paths use readable identity labels plus identity digests. Publisher, practitioner, uploader and upload ID are separate fields. The manifest preserves original labels and source receipts. Byte-identical files can have one canonical object plus aliases; SHA-256 over actual source bytes establishes that alias. Similar titles, reposts, original sessions, publisher editions and YouTube editions are never merged by inference. The current plan has zero byte-identical aliases.

Every canonical object gets an adjacent provenance sidecar. The archive manifest records each file's source SHA-256, MD5, size, source identity and acquisition provenance; `SHA256SUMS` also covers the sidecars and manifest. SHA-256 tracks source bytes. Drive's returned MD5 **and** exact size check transfer integrity; MD5 is not treated as proof of authenticity or origin. Missing remote hashes stop verification rather than falling back to size alone. Files are uploaded without conversion to Google Docs.

The uploader forces My Drive root, clears Shared Drive and service-account overrides, skips shortcuts, clears shared-with-me/trash filters, and never issues sharing or permission changes. A fresh My Drive folder uses the account's default permissions. **Effective ACLs and organizational account defaults are not independently audited by this rclone version.** The operator must bind the correct authorized user account and inspect its actual permissions before treating privacy as verified. The account-selector flag below records that operational check; it is not a request for fresh user authorization already given in this task. If a Drive plugin becomes available, prefer its adequate account/folder/upload/permission capabilities.

## Commands

Run from the repository root; Python needs no third-party package:

```bash
python research/storage-drive/archive.py plan --output /workspace/channels-et-archive-plans/plan-UNIQUE.json
python research/storage-drive/archive.py verify-plan /workspace/channels-et-archive-plans/plan-UNIQUE.json
python -m unittest discover -s research/storage-drive -p 'test_*.py' -v
```

`plan` is an offline dry run: it reads acquisition receipts and rehashes actual local files. It sends no network request and creates no remote object. Replace `UNIQUE` with a new output name: **existing output files are never overwritten**, including the checked-in [archive-plan.json](archive-plan.json), which is one previously executed plan. A new invocation also chooses a fresh dated archive name. Local sidecars were staged outside Git for review, without copying media.

**Only after an existing user-authorized direct Drive remote is available**, select its exact existing name. Replace `EXISTING_AUTHORIZED_REMOTE` below; it is a placeholder, not a remote configured by this work:

```bash
rclone listremotes --long
python research/storage-drive/archive.py status --remote EXISTING_AUTHORIZED_REMOTE
python research/storage-drive/archive.py upload /workspace/channels-et-archive-plans/plan-UNIQUE.json \
  --remote EXISTING_AUTHORIZED_REMOTE \
  --private-mydrive-root-confirmed \
  --receipt /workspace/channels-et-raw/drive-receipts/UNIQUE/receipt.json
```

The code never starts OAuth, reads credential files, uses ambient Google credentials, creates an alias, or assumes the Apps choice connected an account. `status` first requires the selected existing remote to have type `drive`; aliases and connection strings are rejected. `about --json` then measures actual quota. Upload stops if the account's free bytes are unknown or insufficient. The workflow does not require the allowance to equal 5 TB when a smaller authenticated capacity is sufficient.

Upload validates local output and staging paths before any rclone request. A required receipt is exclusively created as a new file; it cannot replace a source, an unrelated file, a symlink, a hardlink or a directory, and no parent may be a symlink. Receipts inside the raw tree are limited to `drive-receipts/`; staging inside the raw tree is limited to `drive-staging/`. Receipts, staging and source paths cannot overlap. Plan outputs are prohibited throughout the raw tree. Receipt updates use atomic replacement bound to the exclusively created file's recorded identity; if another actor replaces, symlinks or hardlinks it, updates stop without modifying that replacement. A failed authentication preflight can leave the newly created local receipt with zero remote write attempts.

Upload rehashes sources, refuses a pre-existing archive root, and uses `copyto --immutable --checksum`. Every individual destination is checked before copying and again afterward using a directory listing that rejects duplicate Drive names. Identical bytes can be verified and reused within that run; different or unavailable hashes stop the run. Transfers are sequential to bound request pressure; collection workers can remain independently parallel. No `sync`, delete, move, public link, sharing or automatic retry is used. Installed rclone flags were checked locally against version 1.60.1-DEV.

**There is no resume command.** A failure retains the local sources and any partial remote archive. Receipts distinguish attempted writes, confirmed folder creation, verified files and uncertain remote state after a timeout/failure. Inspect that receipt and the remote before another upload. A new plan/archive can duplicate already uploaded bytes; automatic merging, dedupe and cleanup are intentionally absent. A crash can leave a partial remote object; the uploader never claims zero remote bytes merely because verification failed.

Current official rclone documentation also says that Drive's shared default OAuth client is being retired during 2026. An authorized remote needs a working client configuration maintained through the supported account setup. This workflow neither provisions a client nor reads its credentials.

## Future YouTube material

The current plan contains zero YouTube artifacts. The collector, not the archive tool, must obtain content through working authorized access and refresh actual duration/platform format first. The repository's default selection receipt caps Bashar at 100 YouTube IDs across uploaders and does not count the separate publisher-audio cohort against those slots. Reposts remain distinct upload IDs; original-session equality is unresolved. The archive does not expand that cap or select replacement IDs.

Pass `--additional-artifacts manifest.json` to `plan`. Each artifact must already exist below the private raw root and provide:

```json
{
  "artifacts": [{
    "local_path": "/workspace/channels-et-raw/youtube/VIDEO_ID/video.webm",
    "sha256": "FULL_LOWERCASE_SOURCE_SHA256",
    "bytes": 12345,
    "provider": "youtube",
    "practitioner": "Explicit practitioner label",
    "uploader": "Explicit uploader account label",
    "source_id": "youtube:VIDEO_ID",
    "kind": "video",
    "provenance": {"source_url": "https://www.youtube.com/watch?v=VIDEO_ID", "metadata_receipt": "collector receipt"},
    "selection_eligible": true,
    "is_short": false,
    "duration_seconds": 600,
    "metadata_refreshed_at_acquisition": true,
    "selection_policy_receipt": {
      "path": "research/collection-policy/selected-default.jsonl",
      "sha256": "FULL_SHA256_OF_THE_ACTUAL_SELECTION_FILE"
    }
  }]
}
```

Allowed kinds include `video`, `audio`, `transcript`, `primary-text`, `source-document`, `source-metadata`. The importer verifies source bytes, the pinned default selection file and selected source ID. Unknown/nonfinite/under-300-second durations, Shorts, missing policy receipts, or metadata not refreshed at acquisition are rejected. A caller's refreshed-format assertion still depends on the collector's receipt; storage is not a second video inspection. Original labels, uncertain speakers and publication/session distinctions belong in provenance.

## Verification and sources

Offline tests cover traversal, source boundaries, final/intermediate symlinks, immutable staging, source changes, exact-byte dedup, destination collisions, pinned selection/duration/Shorts gates, missing/non-Drive remotes, quota failure, remote duplicate names, MD5/size failures, immutable copies, post-copy verification, and uncertain write receipts. Output regressions reproduce and prevent receipt-equals-source destruction, unrelated-file overwrite, symlink/hardlink output attacks, raw/staging overlap and changed owned-output identities. Rclone interactions in these tests are mocks, not real Drive uploads. Independent agents reviewed source/path, remote collision, privacy, failure-receipt and local-output behavior; these were agent reviews, not a human security audit.

Official source URLs, retrieval timestamps and SHA-256 values are in [official-docs-sources.json](official-docs-sources.json): [Drive backend](https://rclone.org/drive/), [copyto](https://rclone.org/commands/rclone_copyto/), [lsjson](https://rclone.org/commands/rclone_lsjson/), and [about](https://rclone.org/commands/rclone_about/). They were fetched over the inherited environment proxy with TLS verification. Current web documentation can describe newer rclone features; this implementation separately checked the installed CLI flags and does not use unverified newer metadata-permission APIs.
