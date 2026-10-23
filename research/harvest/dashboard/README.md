# Acquisition and downloads view

The primary research navigation includes `#harvest`. The component is
`harvest.js`; the retained dashboard builder copies it to `dist/research/` and
includes the exported harvest data in the dashboard snapshot. All asset and
download links remain relative to support `/channels-ET/dist/research/` on Pages.

The view keeps these source units separate:

- Offline inventory: unique valid video IDs, literal account routes, explicit
  many-to-many route/video edges, recorded durations and hypothetical storage.
  Indexed does not mean checked, queued, enumerated or downloaded.
- YouTube worker: authoritative job, attempt and artifact exports. A general
  root probe is one request, not one attempt for every indexed source. Channel
  and playlist listing routes stay separate. Worker attempts count leased
  operations, each of which can issue zero or several HTTP requests. Listing
  exhaustion concerns the returned public listing only. Only boolean true or
  integer 1 completion flags enter saved-file totals; retained incomplete and
  invalidated rows stay visible in the artifact ledger.
- Original publisher audio: independently saved RSS enclosures, verified local
  bytes and hashes. These are not automatically equivalent to indexed YouTube
  editions. Audio-only saving does not fulfill a video-download claim.
- ASR: source-hashed automatic transcription receipts, full-audio versus clip
  scope, model/runtime information and local output hashes. ASR output is not
  human-reviewed speech, speaker attribution or factual validation.

The Pages view reads exported state; it does not launch downloads. Reloading
checks the latest published snapshot and retains its actual export dates.
The interactive job data is a compact projection of status, target and selected
title fields. Complete input/provenance and lease details stay in the separately
downloadable full job manifest with its own byte hash.
Public downloads use an explicit metadata allowlist. Raw audio/video, subtitle
text, full ASR text, temporary URLs and base-model weights are not copied by this
view's builder. Existing paper and model-result files retain their source bytes.

Run from the repository root:

```sh
python3 research/continuation/dashboard/build_dashboard.py
REQUIRE_ASR=1 node research/harvest/dashboard/check_browser.cjs
```

The browser check expects a prefix-mounted local server at
`http://127.0.0.1:8014/channels-ET/dist/research/`; `DASHBOARD_URL` can override
that address. It checks source totals, operation-state reconciliation, actual
download hashes, filtered exports, keyboard controls, narrow layout and 200%
CSS zoom. Synthetic UI-state checks are explicitly recorded as fixtures and
never count as source acquisition.
