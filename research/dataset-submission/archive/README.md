# Private research archive

**10 November update:** the user has authorized public storage in the existing
`channels-ET` repository. Public research and the retained-object index are
published through Git. Complete source publication is tracked by source-specific
redistribution terms and verified transfer receipts. Release-asset uploads
currently return HTTP 401, including a tiny synthetic test file. The private-only
uploader below preserves its earlier guard and is not silently repurposed to
publish raw sources. No new repository is required.

The original 8 November archive design used **private full archive + public research**. Raw recordings, complete transcript editions and source snapshots belong in the private `occult-kranti/channels-et-dataset` repository. The public research dashboard receives only a status summary and approved derived data. Private storage does not establish permission to redistribute third-party recordings publicly.

## Storage contract

`archive.py inventory` reads the retained project roots and records each regular file's relative path, size, SHA-256, mode and modification time. Identical bytes are stored once as content-addressed objects; every logical path remains in the manifest. Path counts therefore do **not** equal recording, video, transcript or analytical-document counts. Symlinks are documented without following them. Selected-frame media/text provenance is independently joined by the dataset engineer; the raw-root archive also retains older alternate encodings, source HTML, extraction outputs and diagnostic research artifacts.

Credentials and key files, installed dependencies, model/runtime caches, lock files and Python bytecode are excluded explicitly. The inventory also checks recognizable private keys, GitHub token formats and selected currently configured secret values. This is a guard against known patterns, not a claim of perfect secret detection. Files held by that check are named in the private exclusion ledger without revealing their content. New files under the active `dataset-submission-2026-11` run are excluded from the initial snapshot and require a final frozen supplement. Source files are never deleted.

`archive.py plan` binds the exact inventory bytes and assigns every unique content object to one independent `.tar.zst` shard. The default payload budget is 1 GiB. Each shard contains only opaque `objects/<sha256>` members and can be decompressed independently. The private inventory restores the original aliases. Packaging rehashes every input and rejects changed files. Local verification decompresses every shard and hashes every contained object.

GitHub documents a maximum of **1,000 assets per release** and requires **each file to be under 2 GiB**; it states no total release-size or release-bandwidth limit. See [About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases). These limits do not guarantee that a particular account, integration or network route permits an upload. The archiver checks the destination repository's `private` flag before each transfer and refuses a public destination.

`archive.py upload` never clobbers an existing asset. It checks the GitHub asset state, length and digest where supplied, then performs an authenticated download of the **entire remote asset** and calculates SHA-256 while streaming. Only equal remote bytes receive a verification receipt. HTTP success or matching file sizes alone do not count as verification. Repeating a transfer resumes by verifying an existing same-name asset; conflicting bytes fail closed.

## Run

Python 3.10+, `zstd` and authenticated GitHub CLI are required. Keep credentials in the environment's authorization mechanism, never in commands, manifests or the repository.

```bash
python3 research/dataset-submission/archive/archive.py inventory --output /private/run/inventory-01
python3 research/dataset-submission/archive/archive.py plan \
  --inventory /private/run/inventory-01/inventory.json --output /private/run/plan.json
python3 research/dataset-submission/archive/archive.py build \
  --inventory /private/run/inventory-01/inventory.json --plan /private/run/plan.json \
  --number 1 --output /dev/shm/private-archive/shard-001.tar.zst
python3 research/dataset-submission/archive/archive.py upload \
  --repo occult-kranti/channels-et-dataset --tag retained-corpus-2026-11-08 \
  --asset /dev/shm/private-archive/shard-001.tar.zst \
  --receipt /private/run/remote-shard-001.json
python3 -m unittest discover -s research/dataset-submission/archive -p 'test_*.py' -v
```

Create the private release before uploading. Upload the inventory, its binding, the plan, archive code and later final-study supplement as well as the shards. Retain the local and remote verification receipts. A source/edition manifest without every declared object's verified shard is an incomplete transfer.

This cloud run has limited disk headroom. Stage one shard at a time on RAM-backed storage, retain at least 1.5 GiB free on the staging filesystem, and delete only newly generated staging files after a durable remote verification receipt exists. Never delete retained original media to make room. A stopped upload remains incomplete and can be resumed using the same frozen inventory and plan.

Use `transfer.py --inventory ... --plan ... --stage ... --receipts ... --repo ... --tag ...` for that sequential workflow. It obtains an exclusive local transfer lock and preserves verified receipts outside RAM staging. The retained snapshot uses `--prefix shard`; use `--prefix supplement` and a separate receipt directory for the final-study supplement, avoiding asset-name collisions within a release. `freeze_package.py` first copies and verifies the dataset engineer's receipt-bound final package; these immutable copies can be inventoried alongside the final analysis witnesses. The final committed public code needs its own Git snapshot binding.

`freeze_analysis.py --private <analysis-witness-directory> --public <analysis-public-directory> --output <fresh-staging-directory>` reproduces the analysis input snapshot from its exact producer receipt. RAM staging is temporary. If it is lost, reconstruct the frozen package and analysis directories at the roots recorded by the supplement inventory; every source byte must still match that inventory before a shard can be rebuilt. A failed hash is a changed snapshot, not permission to silently update the old manifest. Preserve original dataset/analysis files and immutable manifests on the workspace until remote storage is verified.

## Restore and audit

Download the private inventory, plan and all required shards using an authenticated account. Check each downloaded shard against its remote receipt before decoding. A tar shard's member names are object hashes, not original filenames. `restore.py` performs safe object extraction, validates every byte and restores aliases into a fresh destination. It does not follow or recreate symlinks. Budget for all restored logical bytes unless choosing hardlinks. Do not extract an unvalidated tar with general-purpose path-trusting code.

```bash
python3 research/dataset-submission/archive/restore.py \
  --inventory inventory.json --plan plan-01.json --shard-dir downloaded-assets \
  --receipts local-shard-receipts --output restored-corpus --hardlinks
```

For the final-study supplement, use its inventory/plan/receipt set and `--prefix supplement`. Restored content is read-only; original modes and modification times remain in the inventory. Hardlinked aliases share an inode, so copy a restored file before editing it.

The public `archive.json` is a status receipt, not proof that every possible online video has been acquired. The acquisition inventory, selected analytical corpus, retained source-file archive and GitHub transfer have separate denominators. Source-level acquisition failures and uncollected media remain visible in the research dataset even when all retained files are successfully archived.
