# Reconciled YouTube account and observed-video inventory

This inventory reconciles the retained channel research and screenshot screening into an explicit account scope. It does **not** claim a complete channel crawl, current YouTube availability, new downloads, or transcripts that are not retained. The independent collector and first-party publisher discovery have their own receipts and scope.

The policy has no video-count cap. Non-Bashar material has no duration minimum; Bashar material, including reposts on mixed accounts, requires 300 seconds. Unknown or conflicting Bashar duration remains a probe task. Jamie Butler is excluded by the user's preference; the research identifies a medium/channeler and does not call her a comedian.

## Inputs and identities

`inventory.py` binds every input by SHA-256/bytes and binds observations to JSON pointers or JSONL/CSV row locators. It reads the earlier 362-route / 942-video harvest, 925 historical watch-metadata records, atlas account groups, 28 screenshot-screened routes, focused YouTube research, expanded ET and traditions registers, Council sources, the Magenta publisher archive, and optional fresh first-party publisher discovery. The five explicit Council watch URLs beyond the older harvest/Magenta union are retained as source mentions, not invented uploader assignments.

Account identity uses literal routes and exact platform IDs. Handles are case normalized, but accents are preserved. `/user/name`, `/c/name`, bare custom routes, handles, and UC IDs remain separate unless the **same historical successful watch response** binds a route to one UC ID. If a route has conflicting UC associations, it is not merged. Same names, a shared medium, repeated claimed entities, old atlas alias groups, and multiple links on a publisher page do not establish equivalent accounts. These weaker references remain visible. Two entries may therefore still represent one unresolved real account; the count is a conservative resolved-reference count, not a census of distinct people.

Historical watch observations from October 23, 2026 bind 878 known videos to their observed uploader. They do not establish current account access, ownership authentication, or lifetime upload totals. All `videos`, `shorts`, and `streams` tabs begin `not_enumerated` with no terminal-pagination claim. The collector records its independent attempted scope.

Publisher contexts are distinct from accounts. Medium and claimed-label metadata describe a source attribution context, not authenticated identities, every upload, or each utterance. An account hosting a guest does not become the guest's own channel. Publisher-embedded videos can be associated with a retained publisher-linked collection route; fresh discovery additionally requires the video and account link to occur on the same first-party page. Neither co-occurrence nor `publisher_embed` sets `verified_uploader_account_id`. A page can link to guests or unrelated accounts, so newly linked routes stay candidates unless previously admitted. Malformed account paths carrying unescaped tracking parameters are retained as rejected route mentions, not silently repaired.

## Public contract

`inventory.json` contains `accounts`, `videos`, `account_video_links`, `identity_links`, `publisher_contexts`, `unresolved_references`, `inputs`, `coverage`, and `policy`.

- Accounts expose a stable key, actual UC ID when known, literal handles/URLs, screening status, source-attributed contexts, duration policy, unknown lifetime total, tab status and explicit observed-ID counts.
- Videos expose global unique IDs, source URLs, historical titles/durations/access observations, known uploader when exactly bound, weaker associated-account IDs, and duration-policy decisions.
- Typed account/video edges distinguish `historical_watch_uploader`, `inherited_route_association`, `screening_route_association`, `research_route_association`, and `publisher_embed`.
- Decisions are `eligible`, `excluded_duration`, `duration_probe_required`, `excluded_account`, or `unassigned_review`. Eligibility is a duration/scope condition, **not** proof of channeling content or a completed download. Mixed-account short non-Bashar videos stay eligible. A shared Essassani label does not make an Elan video Bashar.
- `observed_associated_video_ids` overlaps across account rows. It must never be summed as a platform-wide unique-video count. `historically_verified_uploader_video_ids` uses the stronger historical watch edge.
- Historical caption analyses retain artifact references only; their original corpus is absent here. The CSV's UTF-8 BOM is handled explicitly. This inventory's zero new media/text counts are operation-specific, not claims that separate publisher-audio collections are empty.

Each account's inclusion is `included_screened`, `included_research`, `candidate_unreviewed`, or `excluded`. The broad inherited candidate frame is visible for enumeration/review; it does not claim that every candidate channel or upload is relevant. Explicit screenshot exclusions take precedence. No generic account-level failure is inferred from one network gateway failure.

## Run and verify

```sh
python research/youtube-archive/inventory.py \
  --output /dev/shm/youtube-archive-2026-11/inventory-NN \
  --discovery /path/to/publisher-discovery.json
python research/youtube-archive/verify_inventory.py /dev/shm/youtube-archive-2026-11/inventory-NN
python -m unittest discover -s research/youtube-archive -p test_inventory.py -v
```

The producer refuses to overwrite an edition and emits an exact public allowlist. Inputs and source references remain historical when no new body was fetched. Tests cover literal/case/accent identities, conflicting UC bindings, weak aliases, duplicate IDs, publisher embeds, Jamie's exclusion, mixed-account and unknown-duration policies, and the distinction between a shared civilization and Bashar-specific material.

## Frozen final edition

`inventory-03-final` contains 2,812 distinct observed video IDs and 297 reconciled account references, including all 28 screenshot routes (12 included and 16 excluded). It combines the 2,060-ID retained baseline with 743 new HTML/sitemap references and nine additional first-party HTTP Location references. The latter are explicitly separate from HTML evidence and never establish a YouTube response or uploader. The discovery input has SHA-256 `98d4d339098b9da4248506ca867d60553752f34cd914e7fe1afd5c0009672966`; inventory SHA-256 is `0411954faeccfb5637a1ef01a154c638cff0927b8baafbffe5cbd5ef8d2bcfff`.

Independent reconstruction checked all 16,085 source references, 878 historical watch uploader joins, 30 historical caption-reference joins, all duration/exclusion decisions and all 237 fresh same-page publisher/account/video associations. This verifies the declared inventory joins, not the identity or relevance of every speaker, current YouTube access, or a complete channel census. The final publisher crawl exhausted its declared finite queue with 1,239 attempted pages, 1,215 retrieved and 24 failed/held; that is not a whole-site or YouTube-tab completeness claim.
