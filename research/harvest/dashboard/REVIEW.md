# Acquisition-view implementation and review

This supplement adds an acquisition view while preserving the research paper,
scientific result files and model experiment outputs. Review and browser roles
are AI agents, not human usability participants or source annotators.

The interface separates offline URL inventory, worker queues and operation
leases, one dated root watch-page probe, complete YouTube artifacts, independently
retrieved publisher audio, and unvalidated automatic transcripts. Literal channel
routes and playlist references remain separate. Per-route video associations are
many-to-many source edges and cannot be summed as unique upload totals.

The first actual two-audio/two-ASR snapshot passed 179 browser, source and
download-binding checks at the Pages prefix, with four additional fixture-only
UI-state checks. Its receipt is retained separately as
`initial-two-source-verification.json`. The later sanitized 19-audio/11-ASR
preview rendered the 3,357-job queue, skeptical commentary and RSS warnings
without runtime errors or 390px overflow. These snapshots do not certify later
source files or a later Pages deployment.

Independent source/UI review found and repaired supported resume-path issues:

- Only `complete=true` or integer `1` artifact rows enter saved totals.
  Incomplete and invalidated rows remain visible with their completion state.
- Caption language uses `language_code`; track origin preserves boolean or
  integer `true/1` and `false/0`, keeping unknown distinct from manual.
- Operation attempts count worker leases, each of which can issue zero or
  several HTTP requests. They are not all-video HTTP request counters.
- Publisher warnings remain visible even when reviewed current-response audio
  is counted as saved. Skeptical commentary and promotional interviews retain
  their catalog roles and are not promoted into a channeler's attributed speech.
- Full provenance stays in byte-bound downloadable manifests; the interactive
  job payload is a compact projection, reducing unnecessary initial transfer.

Source-only Chromium fixture checks verified completion flags, retained invalid
rows and integer caption flags. Fixtures do not count as acquisition or ASR.

Direct live Chromium access through the inherited proxy encountered an NSS
certificate-authority failure. TLS verification was kept enabled. Browser
interaction checks therefore use the exact `/channels-ET/` prefix locally;
separate verified live HTTPS/hash checks bind the deployed files. No proxy or
certificate-validation bypass was introduced.

Final acceptance: `browser-verification.json` records 187 passing checks,
9 separate fixture-only checks, zero errors and 42 source-bound downloads.
The accepted snapshot contains terminal 19/19 publisher audio and ASR ledgers,
final shared raw-tree usage and the final generated acquisition report.
