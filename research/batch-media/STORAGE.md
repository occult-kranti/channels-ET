# Verified batch storage

The current destination is **private managed-cloud filesystem storage**, as the
user requested on 7 November 2026. It is not permanent ChatGPT-account storage,
a chat attachment or Google Drive. Environment expiry/deletion can remove it.
Full recordings, transcripts and verification receipts stay outside public Git
and Pages. A downloadable artifact must be deliberately packaged and linked.

The earlier README's 6 November claim that a publisher transcript was retained
in Drive cannot be confirmed from `research/new-round/publisher-asr-receipt.json`:
that receipt has audio/transcript hashes but no Drive transfer identity or
verification. It may describe another environment; this is not evidence that
the reported transfer never happened. In this environment the 6–7 November
inspection found no callable Drive tool, no configured rclone remote and no
configured outbound identity. An ambient Google credential variable was not
read or repurposed. Actual new Drive upload attempts remain zero.

## Input and provenance

`storage.py` imports the existing source/output guards from
`research/storage-drive/archive.py` and the reviewed independent-copy helpers
from `research/cloud-archive/archive_local.py`. It does not silently add the old
99-artifact collection or alter its historical selected-ID receipt.

An explicit input manifest has this structure:

```json
{
  "schema_version": 1,
  "batch_id": "publisher-pilot-2026-11-07",
  "artifacts": [{
    "provider": "publisher_video",
    "medium_id": "publisher-attributed-medium",
    "channel_id": "publisher-channel",
    "source_id": "publisher:source-id",
    "kind": "video",
    "local_path": "/workspace/channels-et-private/EXISTING-VIDEO.mp4",
    "sha256": "ACTUAL_64_CHARACTER_LOWERCASE_SHA256",
    "bytes": 12345,
    "verification_receipt": {
      "path": "/workspace/channels-et-private/EXISTING-PROOF.json",
      "sha256": "ACTUAL_PROOF_SHA256"
    }
  }]
}
```

The paths and hashes above are placeholders, not acquired files. Sources must
be regular files below `/workspace/channels-et-raw` or
`/workspace/channels-et-private`; symlink escapes are rejected. Providers are
`youtube`, `publisher_rss`, `publisher_video`, `publisher_reference` and
`derived_analysis`. Kinds are `video`, `audio`, `caption`, `transcript`,
`analysis`, `source-metadata`, `reference_document` and `reference_text`.
`reference_document` denotes the original reference PDF; `reference_text`
denotes its extracted text. A multi-document analysis/reading report can use
`provider: "derived_analysis"`, `kind: "analysis"` and a corpus source ID such
as `corpus:crimson-circle:freedom-series:first10:2026-11-07`. Its hash-bound proof
preserves parent source IDs, input receipts, methods, limitations and reading
coverage. Such artifacts are analytical derivatives, not additional videos,
mediums, speech transcripts or independently verified scientific findings.

Each proof must contain `verified_artifacts`, with exactly one matching entry
for the artifact's `local_path`, `sha256`, `bytes`, `source_id` and `kind`, plus
`status: "verified"`. Failed media validation cannot become a verified archive
entry merely by changing its filename. The uploader rehashes actual bytes and
the proof; it does not independently redo codec, ASR or speaker validation.
The producer must supply sanitized, explicit verification receipts rather than
credentials, cookies, request headers or authentication-bearing URLs.

If provider/medium/channel identity is present in the proof, conflicting input
identity is rejected. Attribution fields—including joint context associations,
the medium assignment basis, unknown-speaker status, source URL and acquisition
scope—are projected from the **hash-bound proof**, not arbitrary caller
overrides. Missing identity proof remains explicitly caller-supplied
organization labels. A publisher/context/claimed entity is not independently
verified as the actual speaker or a nonhuman source.

YouTube artifacts additionally require `source_id: "youtube:VIDEO_ID"`, a
finite `duration_seconds >= 300`, `duration_scope: "source_video"`,
`is_short: false` and `metadata_refreshed_at_acquisition: true`. Duration for a
caption or derived transcript means its parent video. The collector remains
responsible for the selected-ID ledger, per-medium pilot and global Bashar cap.
Independent publisher video, audio and PDF never count as YouTube downloads.

## Local archive commands

Run from the repository root. Every output path must be new.

```bash
python3 research/batch-media/storage.py plan /PRIVATE/verified-artifacts.json \
  --output /PRIVATE/archive-plan.json
python3 research/batch-media/storage.py verify-plan /PRIVATE/archive-plan.json
python3 research/batch-media/storage.py local-archive /PRIVATE/archive-plan.json \
  --archive-root /workspace/channels-et-raw/batch-2026-11/cloud-archive \
  --receipt /PRIVATE/local-archive-receipt.json
```

The directory structure is:

```text
channels-ET-BATCH-UNIQUE/
  index.html
  provider/medium/channel/source-ID/kind/original-filename
  manifests/provenance/provider/medium/channel/source-ID/kind/filename.json
  manifests/verification/ORIGINAL-PROOF-SHA256.json
  manifests/archive-manifest.json
  manifests/SHA256SUMS
```

Readable identity components include digests to avoid slug collisions. Original
verification receipts are copied byte-for-byte into the private archive;
sidecars point to them by their original SHA-256. Provenance occupies a separate
namespace so a source called `x.provenance.json` cannot collide with a generated
sidecar. `SHA256SUMS` covers all planned objects except itself; the external
transfer receipt also hashes the checksum file. From the archive root,
`sha256sum --check manifests/SHA256SUMS` rechecks archived bytes without access
to the original source directory.

`index.html` is a local, searchable-by-browser index of recordings, reference
documents, transcript files, analyses and their verification receipts. It
escapes source labels, links every retained source artifact and makes no
automatic external request or media playback. Original-source links are
explicit online navigation. The index is computed from the frozen plan and is
itself hashed; it does not depend on the later transfer receipt or public status
document, avoiding a circular hash dependency. A small text-only ZIP will not
contain every large media link target.

The default `--mode copy` makes independent copies, never source hardlinks/symlinks. It
checks source bytes during copying, independently rehashes the copied bytes,
requires single-link regular destinations, verifies the exact final file set,
and publishes with Linux atomic no-replace rename. The archive root's device
and inode are checked during copying and after publication. Newly created
archive directories and copied files are owner-only. Existing source bytes are not
modified or deleted.

Before metadata staging and before each media copy, the implementation checks
an aggregate **20 GiB budget** across both approved source trees, counting
regular-file logical bytes once per physical inode, and an actual filesystem
free-space reserve of **6 GiB**. These are operational bounds, not a guarantee
against unrelated processes filling the disk. The shared collector lock and
an archive-process lock reduce local races. Metadata is computed before it is
written and capped at 64 MiB per explicit batch. JSON inputs/receipts are
bounded to 8 MiB; at most 10,000 explicitly supplied artifacts enter a plan.

### Explicit space-saving hardlinks

The user authorized an organized shared-inode archive to avoid duplicating the
ten-video publisher batch on the same limited cloud disk. Add `--mode hardlink`
to `local-archive` only for this explicitly chosen behavior. Each source artifact
is linked atomically on the same filesystem, its size/SHA-256/MD5 and inode
relationship are verified, and generated provenance/manifests are independently
copied. An existing destination or cross-device error stops the operation; no
automatic copy fallback, overwrite, deletion or source chmod occurs.

This is **not an independent media backup or immutable snapshot**: a later
in-place edit to a source changes its linked archive path too. Source identity,
modification time and hashes are bound in the plan and checked again on resume.
The archive root remains owner-only; linked source file permissions are
preserved, not relabelled as newly created mode-0600 files. A receipt separates
`linked_files`, `copied_files`, `reused_files`, logical verified bytes and newly
allocated unique **file-content** bytes. The latter excludes small filesystem
metadata overhead, which is also constrained by actual free-space checks.
Budget counting includes shared inodes once across both approved trees.

Resume must retain the same `--mode hardlink` option. Switching a bound archive
between copy and hardlink modes is rejected. The preceding independent
200-file local archive is unchanged; its earlier copy semantics remain valid.

## Local file-level resume

An interrupted operation retains its first receipt and partial directory. A
resume creates a new receipt linked to the first receipt hash, plan hash and
actual archive directory identity:

```bash
python3 research/batch-media/storage.py local-archive /PRIVATE/archive-plan.json \
  --archive-root /workspace/channels-et-raw/batch-2026-11/cloud-archive \
  --resume-from /PRIVATE/local-archive-receipt.json \
  --receipt /PRIVATE/local-archive-resume-receipt.json
```

Resume rehashes existing objects and copies only missing complete-file
destinations. A completed archive is reverified and left unchanged. Different
bytes, replaced directories, source changes, undeclared hardlinks, symlinks, unexpected
files or unfinished temporary files stop automatic resume and remain for
inspection. It does not delete a partial file, repair a published snapshot or
claim byte-range resume inside an interrupted media file.

## Optional future Drive transfer

Drive is deferred while no callable authorized connection is available. The
user has already authorized upload; a missing authenticated account is the
dependency. Never put credentials in chat. Once an explicitly configured,
direct rclone Drive remote for the intended user exists:

```bash
python3 research/batch-media/storage.py status --remote AUTHORIZED_REMOTE_NAME
python3 research/batch-media/storage.py upload /PRIVATE/archive-plan.json \
  --remote AUTHORIZED_REMOTE_NAME --private-mydrive-root-confirmed \
  --receipt /PRIVATE/drive-receipt.json
```

The account/root flag records operational account selection, not a new request
for previously granted upload authorization. Quota is read from the selected
account. The code creates a fresh My Drive root folder, binds its returned
folder ID, and resolves each nested parent by ID with duplicate-name checks.
Transfers use immutable `copyto`; original conversion/sharing/deletion/sync
remain disabled. Remote MD5 **and exact size**, not MD5 alone, must match local
source bytes. Missing hashes or ambiguous destinations fail explicitly.

Add `--resume-from /PRIVATE/drive-receipt.json` and use a new `--receipt` path to
resume a previously bound folder. The saved plan, remote and actual folder ID
must agree. Every existing file is re-inspected rather than trusting old
completion counters. Missing/replaced bound parents fail before replacement.
An uncertain write remains uncertain until the remote objects are checked;
different partial bytes are not overwritten. A failure before the created root
ID was captured requires inspection and cannot be safely inferred. This is
file-level resume, not a promise of resumable upload sessions across process
restarts. Local locks do not exclude other machines or Drive editors. Effective
organizational ACLs are not independently audited by this rclone version.

## Verification scope

Run `python3 -m unittest discover -s research/batch-media -p 'test_storage.py' -v`.
The suite exercises actual temporary-file copies and hardlinks, byte/proof mutations, explicit
private-root handling, receipt-qualified attribution, staged-budget rejection,
root replacement, complete and interrupted-file workflows, mode-bound resume,
shared-content tampering, cross-device refusal without fallback, and local locks.
Drive behavior uses an in-memory command mock for identity binding, nested
duplicates, missing hashes, quota failures, uncertain writes and resume. These
mock tests are not live Drive verification. Actual pilot archive receipts must
be reported separately from tests and from the still-empty YouTube collection.
