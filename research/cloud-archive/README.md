# Verified local cloud archive

The user authorized the managed cloud environment as the fallback when Drive storage is unavailable. The current environment still exposes no callable Google Drive tool, authorized outbound Drive identity or configured rclone remote, despite the user's report that Drive was connected in Apps. No credentials were read and no new login was started. This operation copies files **locally**; it sends no Drive, YouTube or other network request.

See [archive-state.json](archive-state.json) for the actual completion state and [archive-receipt.json](archive-receipt.json) for the exact file list, hashes, byte totals, budget checks and destination. A completed snapshot contains **200 files / 1,703,879,268 bytes**: 99 source artifacts and 101 provenance sidecars/manifests. The source artifacts comprise 20 publisher audio responses, 60 ASR outputs and 19 primary publication/text/feed files. **No YouTube download is included.** Measured duration and contextual publisher/practitioner/entity distributions are maintained separately in `research/storage-distributions/`.

The local destination is one new dated directory below:

```text
/workspace/channels-et-raw/cloud-archive/cloud-local-YYYY-MM-DD-UNIQUE/
  provider/practitioner/uploader/upload-ID/kind/file
  provider/practitioner/uploader/upload-ID/kind/file.provenance.json
  manifests/archive-manifest.json
  manifests/SHA256SUMS
```

Provider, practitioner, publisher/uploader and upload ID remain distinct identities. Existing source hashes and provenance are preserved; no title/session-based edition merging is introduced. The copied source manifest retains the original storage plan's archive name. The local wrapper's separate dated name and original plan identity are bound in the new receipt. Spiritual/claimed-entity source labels do not establish actual speakers or nonhuman origin. ASR accuracy and speaker attribution remain unvalidated.

Each destination is an independently copied regular file with one filesystem link, rather than a source symlink, hardlink or shared mutable path. Source bytes are read without write access. New archive directories have owner-only permissions and copied files use mode 0600. The copier verifies streamed source bytes against the frozen SHA-256/MD5/size receipt, independently rehashes the copied file, verifies the entire exact 200-file set before publication, then verifies it again at its published path. `SHA256SUMS` binds 199 objects; the checksum-list file itself is additionally hashed by the local receipt.

The exclusive `.partial` root and each file are published with Linux `renameat2(RENAME_NOREPLACE)`, which fails if a destination exists. There is no overwrite, merge, automatic resume or cleanup operation. A failed or interrupted copy leaves a clearly named partial directory and its receipt for inspection. It never deletes the original sources. This workflow holds the collector's shared `.collection-worker.lock`, enforces the existing 20 GiB total raw-storage budget, and preserves 6 GiB free space before copying.

The archive is outside Git and Pages. Repository files contain only code, tests and metadata receipts. A filesystem path in the receipt is **not a browser download link or a chat attachment**. Local availability can survive an environment restart, but this work establishes no guaranteed retention after environment expiry/deletion and no durable external backup. The reported 5 TB Drive allowance and Drive privacy/ACLs remain unchecked. Actual Drive folders and uploads remain zero.

To recheck the completed archive, without networking:

```bash
python research/cloud-archive/archive_local.py verify research/cloud-archive/archive-receipt.json
python -m unittest discover -s research/cloud-archive -p 'test_*.py' -v
```

The actual archive was created with `build --output-dir research/cloud-archive`. Do not rerun it into the same receipt directory: output files are exclusively created and existing receipts are rejected. A deliberate new snapshot needs a fresh metadata output directory, enough budget and a new archive root; it will duplicate bytes. Source validation and output ownership use the frozen, SHA-pinned `research/storage-drive/archive.py` helpers read-only. The Drive workflow's code and receipts were not changed by this fallback.

Offline tests cover actual independent copy semantics, source changes, hash failure, malformed provenance/manifest binding, duplicate or racing destinations, exact file-set verification, source/output symlinks and hardlinks, traversal, budget/free-space guards, and shared-lock exclusion. Tests use small temporary files and do not contact any remote service.
