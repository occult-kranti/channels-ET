# First-batch channeling source selection — 7 November 2026

This is an **offline, source-bound acquisition proposal**, not a receipt for downloaded videos. The user requests a first batch of ten recordings per medium, then broader collection. `selection.py` reads the dated existing metadata and the November 6 discovery additions. It does not call YouTube, create Drive files, allocate Bashar slots, or modify the existing collection ledger.

The current frame contains **106 inherited practitioner/context records** and **11 newer discovery leads**. Three leads explicitly cross-reference existing records. Two paired practices are represented as joint contexts: Calenara (Caroline and Leo) and Laarkmaa (Pia Orleane and Cullen Baird Smith). The result is **112 study contexts**: 104 person candidates, three joint contexts, three historical-author archives, one institutional lineage, and one publishing outlet. These are not 112 verified individual mediums. The GFL Station outlet does not receive a person quota. Current identity, ownership, speaker roles and original-session identity remain unverified until source-specific review.

The historical analysis contains **256 publishing-account groups**, including records without measured videos. They are not 256 human mediums or a complete list of current channels. The source selection still contains 942 indexed unique upload IDs, with 733 default-selected long-form candidates under its earlier policy. All numerical inputs and source hashes are listed in `plan/proposed-batch.json`.

## Proposed first wave

The proposal has **264 unique upload IDs**: ten explicitly Bashar-associated and 254 other-labelled IDs. These contribute **274 context–video associations**, because an upload can be associated with more than one study context. It is downloaded at most once by upload ID. Twelve contexts have ten known eligible candidates, 67 have a partial candidate quota and 33 have no selected candidate; the last group includes the outlet. A short quota means discovery or metadata work remains, not that a live channel has few videos or is inactive.

| Study context | Known eligible candidates | Proposed first batch | Preferred inherited route |
|---|---:|---:|---|
| Athina Król | 10 | 10 | https://www.youtube.com/@athinakrol |
| Blossom Goodchild | 28 | 10 | https://www.youtube.com/channel/UCtYNUevWytubYiElIY44pbg |
| Calenara — Caroline and Leo | 51 | 10 | https://www.youtube.com/@calenara |
| Daniel Scranton | 33 | 10 | https://www.youtube.com/@danielscranton |
| Darryl Anka | 99 | 10 | https://www.youtube.com/@basharchanneledbydarrylanka |
| Laarkmaa — Pia Orleane and Cullen Baird Smith | 10 | 10 | https://www.youtube.com/user/laarkmaa |
| Lyssa Royal Holt | 18 | 10 | https://www.youtube.com/channel/UCeuLbnOjJBUfqqm2KEqkpLA |
| Pamela Aaralyn | 22 | 10 | https://www.youtube.com/@pamelaaaralyn |
| Shaun Swanson | 26 | 10 | https://www.youtube.com/@shaunswanson |
| Tyler Ellison | 11 | 10 | https://www.youtube.com/channel/UCLw58p9pkhoNAXd9PpjMxdg |
| Wendy Kennedy | 13 | 10 | https://www.youtube.com/@hgrfrequencies |
| Wieteke Koolhof | 14 | 10 | https://www.youtube.com/@design4awareness |

The remaining contexts and their shortfalls are all present in `plan/context-quotas.csv`. New video leads `FX3_Jp__y7M` and `VTqOxKh7VCA` have no qualifying inherited duration/format in this selection and remain `discovery_only`. They cannot become media jobs based on a website link alone.

## Selection and attribution rules

1. Only source rows already marked selected and eligible by the existing long-form policy, with a finite duration of at least 300 seconds, no explicit Shorts evidence, no hold reason, and a matching YouTube ID enter the candidate pool. Every item still needs fresh platform metadata. A five-minute video is eligible; an unknown duration is not.
2. A direct inherited practitioner-to-video link or an explicitly linked publisher classified `official` or `channeler` supplies a candidate association. A mixed interview outlet, reupload account or unknown account does **not** assign all its videos to every associated guest. Direct source-specific interview/reupload links remain candidates with their provenance.
3. Rank candidates deterministically by evidence tier (both direct link and eligible publisher association, direct link alone, then eligible publisher association alone), inherited publication date descending within the tier, then video ID. This is a convenience sampling rule, not random sampling or proof of the latest upload.
4. Joint appearances remain joint context records. Authors, guests, hosts, publishers, ASR speakers and claimed entities are separate fields/concepts. A named entity in metadata is an attributed claim, not an authenticated nonhuman speaker. ASR alone does not resolve these roles.
5. Deduplicate by exact upload ID globally. Reuploads of an original performance remain unresolved until actual audio/video fingerprints and content review are possible. Upload dates are not original performance dates.
6. The first wave proposes ten Bashar-associated IDs; the existing reconciled SQLite ledger still owns the **global 100-ID Bashar cap across all accounts and formats**. Do not reset or replace it to obtain new capacity. Other contexts have no lifetime count cap, but this pilot selects at most ten each.

## Outputs and commands

```sh
python3 research/batch-media/selection.py --output /private/batch-plan
python3 -m unittest discover -s research/batch-media -p test_selection.py -v
```

`proposed-batch.json` contains a globally deduplicated `records` list accepted by the existing metadata-only discovery importer, all context quotas, retained candidate lists and source hashes. Import does not grant media admission. `summary.json` and `context-quotas.csv` are compact planning views. The ten offline tests exercise duration/format boundaries, identity mismatches, mixed-publisher exclusion, direct links, global deduplication, joint contexts, separate outlets, deterministic bounded selection and the held source snapshot. They are not evidence of successful network acquisition.

## Inspected live-source status

The requested Pages root and JavaScript, research entry, and GitHub main README were actually fetched through the inherited proxy on November 6–7. They revealed that the original local checkout was stale: the live/main continuation was `314f5622245a792e31648e45039da304fadb4243`. Root updated the checkout before this planner was built. The planner inputs were fetched from that immutable commit and matched the updated local files. The current live research-update view combines session records, the 256 historical account groups, 11 discovery leads and the one new publisher-podcast ASR receipt. It does not show successful YouTube downloads. The November 6 README reports one private Drive-retained podcast transcript, which is a separate acquisition from YouTube; current Drive access still needs actual runtime verification.

Raw live retrieval copies and receipts remain outside Git at `/workspace/channels-et-private/batch-2026-11/inventory/`. No YouTube requests were made by this inventory workstream. Access and storage diagnostics are owned by the acquisition coordinator, not inferred from this plan.
