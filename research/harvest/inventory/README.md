# Source-pinned harvest inventory

This offline inventory combines the original Bashar Index root page/data package with the standalone Atlas's 925-upload snapshot, discovery index and 157-route collection plan. It does not crawl YouTube or claim any video is available or downloaded. The original Bashar checkout is read only.

`source-manifest.json` pins both repository commits and the exact SHA-256/bytes of 154 copied public metadata files. `sourcepins/` makes the build standalone: rebuilding never needs the old repository or network. Initial source capture used `capture_sources.py`; rerun it only to deliberately create a new source snapshot, not as part of ordinary reproduction.

Run from the channels-ET root with standard-library Python:

```sh
python research/harvest/inventory/build_inventory.py
python research/harvest/inventory/verify_inventory.py
```

The verifier independently extracts raw video links, checks the 925-source inclusion, all relationship endpoints, preferred duration values, database integrity and storage arithmetic, then reproduces every output in a fresh directory. `build_inventory.py --output /absolute/directory` supports isolated use. No package install, credentials, network calls or model inference is needed.

## Files and units

| File | Unit / key |
|---|---|
| `videos.jsonl` | One syntactically valid YouTube upload ID, `video_id`; `source_kind=youtube_video`, `source_id=youtube:<id>` |
| `channel-routes.json` | `{schema_version:1,records:[...]}`; one literal normalized route, `route_id` and URL |
| `edges.jsonl` | Typed, source-pinned practitioner/account/route/video relations; relation meanings preserved |
| `publisher-accounts.json` | Original 256 analysis account groups, not unique practitioners or verified platform channels |
| `practitioner-candidates.json` | Original 106 discovery practitioner/lineage/partial-name records, not verified speaker labels |
| `practitioner-profiles.json` | Original 26 earlier Atlas profiles; their explicit video/account links retain this separate namespace |
| `queries.jsonl` | Distinct explicit YouTube search queries, separate from channel jobs |
| `playlists.jsonl` | Distinct YouTube playlist IDs, separate from channels and videos |
| `podcast-sources.jsonl` | All 48 original podcast rows, distribution links and explicit same-row YouTube associations |
| `rejected-video-mentions.jsonl` | Non-video templates/incomplete query mentions that failed eleven-character ID validation |
| `inventory.sqlite` | Indexed source/video/route/edge/query/playlist/podcast/profile tables plus full `record_json` |
| `summary.json`, `schema.json` | Counts, duration/storage scenarios and machine-readable contracts |

The inventory contains 942 unique video IDs: the complete 925-upload snapshot plus seventeen additional IDs. The original Bashar root index/data has 119 linked IDs, of which 104 overlap the 925 snapshot and fifteen are original-root additions. Two further additions come from other retained Atlas source links. The 684 original catalogue sessions are not 684 downloadable YouTube uploads.

There are 362 literal channel routes, including every route in the historical 157-route plan. They may contain multiple documented or unresolved URLs for the same platform channel. Normalization removes transport/query differences, trailing slashes and channel listing suffixes only. It never joins similar names or guesses numeric/handle identity. Explicit inherited alias links remain edges rather than silently collapsing routes. URLs inside search-query prose and incomplete navigation templates are excluded from channel jobs.

`known_video_count` is derived only from explicit route/video edges. A discovery association can be weaker than a metadata uploader mapping; its relation type remains visible in `edges.jsonl`. No display-name join is used. 898 videos have an explicit route association and 44 do not. Publisher labels, account groups, practitioner candidates, attributed entities and actual speakers remain separate. Historical metadata failure/success is preserved as history and never substituted for current availability.

## Durations, capacity and scheduling

881 videos have positive recorded durations, totaling 1,807,579 seconds (502.105 hours); 61 have no duration. The primary rule prefers the retained analysis duration, then an explicit podcast duration, then another positive recorded duration. Ten video IDs have differing positive recorded durations; all alternatives and source pointers remain in `duration_conflict_values` and `metadata_observations`. Word counts are never converted into inferred durations.

The known-duration payload alone is about 13.47/26.94/40.40 GiB at assumed audio rates of 64/128/192 kbps, or 107.74/315.64/736.50 GiB at assumed combined audiovisual rates of 512/1500/3500 kbps. These are scenario calculations, not observed encodings or a guaranteed bound. They omit missing-duration uploads, new channel discoveries, overhead and redundant representations. Ideal transfer times assume a sustained 50 Mbps and omit every operational delay.

After a successful access preflight, enumerate all inherited routes/playlists, refresh per-ID metadata and unavailable/private/deleted outcomes, save offered captions, then download media in resumable byte-quota batches with a shared video-ID archive. Begin with one media worker and two metadata/caption workers; keep a 15% disk reserve. Reconcile actual bytes and free space before each batch. A full-channel job has unknown total duration/count until its listing is obtained, and a returned public listing cannot establish access to private/deleted material.

The inventory's statuses are always `indexed_not_checked`, `availability=not_checked` and `enumeration_status=not_enumerated`. Its attempted/saved/failed/queued/bytes counters are zero by scope. Read the acquisition worker's run ledger for actual outcomes; never relabel an inventory row as downloaded or failed merely because it exists here.

## Independent primary podcast sources

The 48 podcast rows include 22 Apple links, nine Spotify links and 21 explicit YouTube links. Those counts overlap. A same-row YouTube link is an inherited episode association, not verified equality of edits, titles or recording identity. Apple and Spotify URLs are distribution references; this inventory does not infer a primary publisher, RSS feed or media enclosure from their titles. Every source has a separate `source_kind`/`source_id` namespace. Independently inspected publisher RSS/GUID/enclosure records belong to the separate source-research/acquisition ledger and must retain their own evidence. Unmatched episodes stay unmatched; no title-similarity merge is permitted.
