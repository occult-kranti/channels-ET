# Expansion panel — acquisition round 3 / formal round 9

Reviewed round-8 archive SHA-256:
`03654cafae00e7fc15bdd1f30b60cfcc75fb1047b774036d931eb2bb79e64bc3`.
This is an AI-agent technical review. The reviewer owns the collector and therefore
does not claim independent authorship review of that code; the paper/dashboard and
Q&A importer were inspected across workstream boundaries. Exact source hashes are
in `acquisition-round3-receipt.json`.

## Integrated evidence check

The current 24-page paper's acquisition methods and dashboard collection panel
correctly distinguish prepared plans, installed clients and successful empirical
operations. The sole recorded live preflight used standard-library `urllib` and
returned a proxy tunnel HTTP 403. Neither yt-dlp nor youtube-transcript-api performed
a successful live collection in this extension. The 590 queries, 157 channel-route
crawls and 215 caption candidates remain planned; the 925-upload baseline remains
historical. The public summary now records live-client counts explicitly. A dated
block receipt is not a live network-health check. No new network attempt occurred
during this review, and collection remains blocked pending supported runtime access.

## Corrected collector issues

1. The raw-directory guard previously treated the sandbox's reserved empty
   `/workspace/.git` as a real checkout and rejected the intended external raw
   directory. It now recognizes HEAD-bearing Git metadata and linked-worktree
   `gitdir:` files, while ignoring empty reserved directories. Tests cover both
   accepted external storage and rejected real checkouts.
2. Historical caption `person` slugs are not stable candidate IDs. The regenerated
   plan preserves them as `inherited_person_key`, sets unvalidated `person_id` to
   null, and links `person_ids` only through inherited explicit video-URL edges.
   No name-based human merge or verified speaker attribution was added.

All six collector safety tests were rerun and passed without network requests.
The separately authored methods harness independently passed 38 mocked control
checks against the final collector. Mocked successful provider responses are not
acquired research records. The acquisition summary's source hashes reconcile.

## Independent Q&A importer review and correction

The reviewer identified incomplete full-document timing validation, an answer
window whose final segment could exceed the documented 120-second cap, missing
language/ASR/attribution provenance, and a later overlapping-segment end-boundary
error. Findings were sent to the Q&A owner; that owner implemented corrections.
The corrected importer validates IDs, finite nonnegative ordered timestamps and
durations, language/ASR and label types; excludes whole segments crossing the cap;
retains question end and the maximum selected answer-segment end; and emits explicit
unverified caption-window evidence with source URL basis and unknown attribution.
Raw input and raw windows are rejected inside actual Git checkouts. Public manifests
contain hashes/times/indicators, not source text.

An independent local synthetic overlap regression confirmed question end 1s and
answer end 52s for selected segments ending at 52s and 4s. This tests a boundary
control, not caption extraction accuracy. No real caption-window import occurred;
the 949 digest-derived candidates retain their original evidence classification.

## Remaining limits and disposition

No collector/interface blocker remains in the inspected implementation. Live
collection is **still externally blocked**; no multi-medium transcript comparison,
audio accuracy audit, validated answer-agreement classifier or human annotation was
completed. Those limitations remain visible in the paper and dashboard. The review
passes implementation/provenance controls only and does not certify unavailable
empirical collection, source rights, human peer review or extraterrestrial claims.
