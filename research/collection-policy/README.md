# Long-form collection policy: metadata selection, not acquisition

**HOLD — metadata only.** This folder applies the newest collection constraints to the portable inherited index. It makes no network requests, downloads no videos, and does not change historical study results or harvest queues. Selecting an ID does not establish current availability, a verified speaker, a successful download, or permission to skip the acquisition runner's access and validation checks.

The default is **733 YouTube IDs: 100 Bashar-associated uploads across every evidenced account and route combined, plus all 633 eligible other uploads**. The user's 100 limit applies to videos. The 19 previously retained independent publisher RSS recordings are a separate source type and do not consume the default YouTube limit. An optional conservative all-material scenario reserves those 19 and selects **714 new YouTube IDs: 81 Bashar and 633 others**. A video's captions and extracted audio belong to its same unique upload ID; they do not create additional video slots. Other practitioners have no count cap.

## What the inherited index actually contains

| Available metadata stratum | Indexed unique upload IDs | Eligible on inherited metadata | Under 300 seconds | Duration unknown | Duration conflicting |
| --- | ---: | ---: | ---: | ---: | ---: |
| Explicit Bashar association | 173 | 115 | 22 | 26 | 10 |
| Ambiguous Bashar-context links | 15 | 0 | 0 | 15 | 0 |
| Other, without Bashar labels in available metadata | 754 | 633 | 101 | 20 | 0 |
| All indexed uploads | **942** | **748** | **123** | **61** | **10** |

The requested roughly 1,000 is a target, not a reported acquisition count. Of 748 eligible metadata records, the default selects 733 and holds 15 eligible Bashar IDs at the global cap. The conservative alternative holds 34 eligible Bashar IDs. Unknown or conflicting durations remain held, including conflicts where every alternative exceeds five minutes. Eligibility requires a finite positive duration of **at least 300 seconds**, inclusive; invalid numerical values and booleans fail closed.

One indexed ID, `eKRwhz2gAzw`, has an inherited `/shorts/` URL. It lasts 155 seconds and is already among the 123 under-minimum exclusions. The Shorts evidence is an overlapping flag, not an additional disjoint exclusion. The original URL occurs at `/discovery/records/451/aliases/0` and `/discovery/records/451/provenance/0/url` in the pinned `channels-ET:dist/data.json`. No record is asserted to have a live verified platform format. The builder also recognizes explicit inherited short-format flags tied to literal video IDs and conservatively holds explicit title markers such as `#shorts`; it never labels all short-duration videos as platform Shorts.

## Bashar accounts, reposts and the denominator

There are **68 Bashar-relevant literal routes** in this local evidence: 62 have an indexed association to an explicitly Bashar-linked upload; six additional Bashar-branded routes have zero indexed IDs. Zero indexed IDs does not mean an empty live channel. All 362 literal routes and 169 indexed playlists remain available for future discovery. The data also identify 52 inherited analytical publisher groups associated with Bashar uploads; these groups are not verified unique platform accounts or unique practitioners.

The 173 explicit Bashar upload IDs include 162 associated with at least one route and 11 with no route or publisher group. Their route associations total 247 edges: 70 IDs have multiple route associations, yielding 85 edges beyond the 162 unique routed IDs. **Do not sum per-route counts as unique uploads.** Alias components use only explicit inherited alias edges and do not establish current platform identities.

Every evidenced interview or repost account is included when its specific indexed video has explicit Bashar evidence. A mixed interview account's other videos are not classified as Bashar merely because one upload is Bashar-linked. New upload IDs may repeat older recordings. Upload-ID deduplication is exact; original-session deduplication and the original recording dates are unresolved. Historical upload-publication observations are retained separately, with their source semantics; no title date or upload date is silently treated as the original session date.

**The full lifetime count across all Bashar accounts is unknown.** Live channel enumeration is blocked in the parent acquisition environment and is not attempted here. No count in this folder estimates private, deleted, unlisted, future, omitted, or not-yet-discovered repost uploads. The 173 explicit IDs and 15 additional ambiguous contextual IDs describe this inherited evidence only. Metadata discovery can expand the index without a practitioner count cap; downloading Bashar materials must still enforce the global video cap.

## Methodology and limitations

This is source-linked metadata classification and deterministic sampling. It is not transcript comprehension or an assessment of any extraordinary claim. Classification uses exact entity labels, practitioner records actually named Darryl Anka, keyword extraction from titles and publisher/practitioner observations (`Bashar` or `Darryl Anka`), and explicit Bashar-branded route associations. Each positive decision retains its field, matched value and source pointers. Broad practitioner notes or a contextual link from the Bashar index do not verify the actual speaker. Fifteen otherwise empty contextual video links remain ambiguous and held.

Duration observations and conflicting alternatives remain inspectable. Source snapshot hashes are checked before rebuilding. Historical publication dates marked `fresh_watch_metadata_UTC` are distinguished from inherited dates with unverified semantics. Actual speaker identity remains `unknown_not_audio_verified` for every record; host, guest, advertising, entity-attributed turns and compilations have not been manually segmented by this layer.

Eligible Bashar records are ordered using deterministic round-robin selection among inherited publisher groups, falling back to inherited route-alias components and then unresolved upload IDs. IDs within groups and group keys are sorted. The first 100 form the default Bashar sample and the first 81 form the conservative alternative. This balances the available metadata groups without claiming random or representative sampling, verified uploaders, or independent original recordings. All 633 eligible other records are selected in both scenarios. Every selected item still requires fresh metadata, access clearance, and runner verification before acquisition.

`retained-bashar-reservation.json` preserves the 19 previously retained RSS source IDs, recorded media hashes/bytes/durations, linked YouTube URLs and validation warnings from a pinned acquisition receipt. Their YouTube edition equivalence is unverified. Even warning-bearing retained files consume budget in the optional conservative scenario; their inclusion does not claim clean content validation. Raw media are not copied into this folder.

## Files and runner contract

| File | Purpose |
| --- | --- |
| `policy.json` | Version 2 cap semantics, five-minute threshold and HOLD state |
| `selection.jsonl`, `selection.csv` | All 942 decisions, classification evidence, durations, route/account IDs, reasons and sample ranks |
| `selected-default.jsonl` | 733 metadata-selected IDs: 100 Bashar plus 633 others |
| `selected-conservative-all-materials.jsonl` | Optional 714-ID alternative: 81 Bashar plus 633 others |
| `route-inventory.json`, `.csv` | All 362 literal routes, local known counts and overlap flags |
| `bashar-routes.json`, `.csv` | The 68 relevant literal routes, including zero-indexed discovery candidates |
| `bashar-publishers.json`, `.csv` | The 52 inherited analytical publisher groups and their local Bashar counts |
| `summary.json` | Machine-readable counts, cap accounting and unknown lifetime denominators |
| `retained-bashar-reservation.json` | Sanitized source-pinned record of 19 retained independent RSS materials |
| `input-manifest.json` | Hashes and byte counts for input inventories, policy, reservation and immutable source snapshots |
| `schema.json` | JSON Schema for each selection row |
| `verification.json` | Test receipt and hashes of code, policy and exports |

The stable acquisition key is `source_id = youtube:<video_id>`. Both `selected_default` and `selected_conservative_all_materials` are explicit booleans. `default_decision` and `conservative_decision` distinguish selection from cap holds; `hold_or_exclusion_reasons` preserves eligibility gates. `duration_state`, `duration_values_seconds`, `shorts_evidence`, `classification_evidence`, `source_refs`, `channel_route_ids` and `publisher_account_ids` must remain available to the runner. Account IDs are inherited analytical groups, not canonical platform channel IDs. `metadata_refresh_required` is always true; `acquisition_status` is always `not_downloaded_by_this_layer`. A consumer must verify hashes and fresh runtime metadata rather than trust a boolean as download authorization.

## Reproduce and verify

From the repository root:

```sh
python research/collection-policy/build_policy.py
python research/collection-policy/verify_policy.py
```

The builder uses Python's standard library only. Verification additionally requires `jsonschema` (tested with 4.26.0). It checks all 942 schema records and source joins, input hashes, disjoint duration accounting, the exact five-minute boundary, non-finite/bool rejection, explicit Shorts evidence without duration inference, ambiguous and mixed-account classification, global cap invariants, uncapped other records, route overlap, separate publication/session dates, order-independent sampling, and a byte-identical rebuild in a temporary directory inside this folder. Verification performs zero network requests and zero downloads. It writes `verification.json`; its own hash is deliberately excluded from its receipt to avoid a hash cycle.
