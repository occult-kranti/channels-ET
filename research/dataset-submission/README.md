# Channeling discourse dataset and ICWSM working paper

This release organizes the retained corpus into a versioned dataset, a source-bound
analysis and a browsable research dashboard. It preserves earlier study snapshots.
The dataset records published channeling discourse; it does not verify claimed
nonhuman sources or represent a complete census of YouTube.

**[Dashboard](https://occult-kranti.github.io/channels-ET/dist/dataset-submission/)**
· [Paper PDF](https://occult-kranti.github.io/channels-ET/dist/dataset-submission/paper/paper.pdf)
· [Overleaf source](https://occult-kranti.github.io/channels-ET/dist/dataset-submission/paper/overleaf-source.zip)
· [Metadata ZIP](https://occult-kranti.github.io/channels-ET/dist/dataset-submission/channeling-discourse-metadata-2026-11-08.zip)
· [Dataset methods](dataset/README.md) · [Datasheet](dataset/DATASHEET.md)
· [Analysis methods](analysis/README.md) · [Venue requirements](venue/VENUE.md)
· [Paper source and build](paper/README.md) · [Independent AI review](REVIEW.md)
· [Executed work plan](PLAN.md)

## What is in this edition

| Unit | Count | Meaning |
| --- | ---: | --- |
| Selected publication/text units | 683 | One selected text edition per admitted publication component |
| Retained text editions | 694 | Selected bodies plus 11 alternative editions; not 694 independent observations |
| Selected words | 1,599,556 | Whitespace-delimited words after the specified normalization |
| Publisher contexts | 26 | Includes guest and mixed-speaker contexts, not 26 complete YouTube channels |
| Creator/context identifiers | 14 | Source-attributed contexts, not verified speaker identities |
| Encoded media files joined to selected texts | 533 | Physically retained files; excludes unjoined Ra segment counts |
| Bytes in those joined media files | 11,657,753,739 | Independently rehashed, distinct from full-archive storage size |
| Observed YouTube video IDs | 2,812 | Discovered references, not downloaded videos or a complete channel census |
| YouTube account references | 297 | Includes unresolved route aliases and candidate accounts |
| Direct YouTube downloads | 0 | Current reconciled ledger; independent publisher recordings remain separate |
| Lifetime uploaded totals | Unknown | No successful complete YouTube tab enumeration |

The 192 recently retained OmNa audio files accompany 192 publisher-written
editions. Two articles duplicate previously selected publications after whitespace
normalization. The new frame adds 190 publication units, preserves both alternative
editions and joins their audio as same-page evidence. This association is not
word alignment or proof of equivalence to a linked YouTube recording.

All 694 full edition bodies are organized in private JSONL and SQLite, including
the 683 selected bodies. The public metadata release contains identifiers, source
links, origin labels, hashes, edition relationships, typed media/account references
and derived research outputs. It excludes complete third-party bodies and media.

## Per-context coverage

The dashboard includes every selected publisher context, individual publication
profiles and the full YouTube reference table. Download `channels.csv` for the
selected-frame table and use the source inventory for upstream collection units.
For example, Ra has 106 selected session texts and 2,620 retained audio segments;
official Bashar has 86 retained publications / 84 encoded families but 82 selected
English analytical texts. Segment, family, publication and selected-text counts
cannot be added or used interchangeably. Candidate uploader associations are not
treated as verified channel ownership.


| Publisher context | Analyzed texts | Selected words | Joined encoded media | Separate upstream coverage |
| --- | ---: | ---: | ---: | --- |
| Spirit Channel with Athina Król | 1 | 3,394 | 1 | — |
| Bashar Communications official Vimeo | 82 | 67,536 | 82 | 86 audio publications / 84 encoded families |
| Crimson Circle — Freedom Series | 10 | 133,080 | 10 | — |
| Daniel Scranton publisher texts | 22 | 14,710 | 0 | — |
| ACID FOR SQUARES — guest context | 2 | 33,178 | 2 | — |
| Align Podcast — guest context | 2 | 24,763 | 2 | — |
| Danica Patrick Pretty Intense Podcast — guest context | 2 | 24,220 | 2 | — |
| Gaia Consciousness — guest context | 1 | 5,181 | 1 | — |
| Gateways to Awakening with Yasmeen Turayhi — guest context | 1 | 10,903 | 1 | — |
| Healing + Human Potential — guest context | 2 | 23,320 | 2 | — |
| Impossible Dreams — guest context | 1 | 10,718 | 1 | — |
| Inspire Nation Show with Michael Sandler — guest context | 1 | 16,931 | 1 | — |
| Just Tap In with Emilio Ortiz — guest context | 1 | 13,147 | 1 | — |
| Mayim Bialik's Breakdown — guest context | 2 | 18,050 | 2 | — |
| Next Level Soul Podcast with Alex Ferrari — guest context | 1 | 14,326 | 1 | — |
| Oh No, Ross and Carrie — guest context | 1 | 19,916 | 1 | — |
| SoulTalk with Kute Blackson — guest context | 1 | 11,177 | 1 | — |
| Virtual Campfire hosted by Krystal Kelley — guest context | 2 | 13,800 | 2 | — |
| Lyssa Royal Holt publisher texts | 1 | 2,671 | 0 | — |
| Magenta Pixie publisher PDFs | 15 | 60,706 | 0 | — |
| Multidimensional Soul publisher interviews | 20 | 122,532 | 20 | — |
| Natalie Glasson / OmNa | 198 | 195,037 | 197 | — |
| Pamela Rose Kribbe publisher texts | 4 | 7,324 | 0 | — |
| Paul Selig publisher transcript | 1 | 2,569 | 0 | — |
| Ra Lightly Edited sessions | 106 | 278,601 | 0 | 2,620 audio segments |
| Tracy Kumbera publisher episodes | 203 | 471,766 | 203 | — |

Every row has an unknown lifetime YouTube upload total and zero newly downloaded
YouTube videos. Joined media are retained independently published files; a zero
join is not a claim that the broader archive has no audio for that context.

## Analysis and findings

The new fit covers all 683 selected publications: TF-IDF, eight-factor NMF,
cluster diagnostics across several cluster counts/seeds, a mutual-neighbor graph,
per-context profiles, topic mixtures and a pinned local MiniLM comparator. Numeric
tables and vector figures accompany the dashboard. Question punctuation creates
9,024 candidate cues; these are not validated question–answer pairs.

The two largest contexts supply 58.7% of documents. Eleven contexts have only one
document and 18 have fewer than five, so small profiles remain descriptive. A
length sensitivity is substantial: full-text versus centered 300-word neighbor
Jaccard averages about 0.137 across documents and 0.063 after context-macro averaging.
Text length, origin and publisher context materially affect similarity. Topics,
clusters and shared claimed names do not establish doctrinal agreement or shared
entity identity. There is no human word-error-rate evaluation or validated ground
truth for the automatic question candidates.

## Private archive and public release

The user has superseded the separate-repository plan: all work now uses the existing
`occult-kranti/channels-ET` repository, with an [organized dataset index](../../dataset/README.md).
Code, metadata, analysis, figures and paper are public. The user has now authorized public source storage. Source-specific redistribution
terms and supported release uploads are being checked; the dashboard reports
actual transfer status, never a presumed backup. The archive tool uses content
hashes, bounded staging, resumable release assets and restoration checks. Original
source files remain retained locally. Dependencies, credentials and model caches
are excluded from archival payloads.

No Google Drive transfer or permanent ChatGPT-account storage is claimed. The
managed execution workspace is the local research location. Existing sources
remain available there while remote archival access is being established.

## Collection status and continuation

The collection rule has no item-count cap. Bashar-associated items retain a
300-second minimum, including reposts; other included mediums have no duration
floor. The [YouTube collector](../youtube-archive/README.md) implements tab
enumeration, resumable jobs, caption provenance, media decoding/hashes and bounded
workers. Its fresh 8 November 2026 22:53 UTC probe failed at HTTPS CONNECT with
HTTP 403 before an origin response. That transport failure prevents a truthful
claim that every indexed YouTube video has been downloaded.

The independently reachable publisher collection is separate. Its latest complete
audio cohort is 192 recordings / 44.55 decoded hours. Publisher-written messages
are labeled as written editions, never silently recast as ASR. Further explicit
publisher audio links remain [unchecked leads](../youtube-archive/NEXT-SOURCES.md).
They are not added to this frozen dataset without acquisition and verification.

## Paper status

The inspected official ICWSM 2027 call gives **15 January 2027 at 23:59 AoE** for
dataset papers. It requires 2–10 pages excluding the mandatory checklist, the
AAAI template, an actual dataset DOI and documentation of content, structure,
collection, quality and applications. Dataset review is single blind. The working
paper and portable LaTeX source describe the actual released metadata dataset
and the separately restricted source archive.

This is a working draft, not a submitted or accepted paper. Final human author
details, DOI deposition and responsible institutional/ethical determinations
remain explicit readiness items. AI assistance is disclosed and is not human
peer review. The [venue ledger](venue/VENUE.md) records the primary source and
inspected comparison papers.

## Reproduce and validate

Dataset and numerical reproduction commands are in their module READMEs. The
private frame hashes bind the analysis; public validation requires no raw source
bodies or model downloads:

```bash
python3 research/dataset-submission/verify_release.py --site .
python3 -m unittest discover -s research/dataset-submission/dataset -p 'test_*.py'
```

`build_public.py` combines explicit producer allowlists, validates hashes and
rejects private JSON paths or unlisted artifacts. `manifest.json` binds every
published download and dashboard module. The browser verifies module bytes and
reports unavailable optional modules separately from core-data failure. Pages CI
validates this new release alongside every retained study before deployment.

The public metadata can be inspected without access to the private texts. Exact
text-model reproduction additionally requires the retained source editions or
lawful re-acquisition of equivalent content; changing online sources may prevent
byte-identical rehydration. Public aggregate results are not a substitute for the
private input corpus.

## Public publication continuation · 10 November

The user authorized public storage in the existing repository. The organized
`dataset/` entry point, public metadata ZIP, complete paper, analysis outputs and
all retained-object bookkeeping are published through Git and Pages. Source
redistribution terms are recorded in [PUBLIC-SOURCE-RIGHTS.md](PUBLIC-SOURCE-RIGHTS.md).
No blanket license for the complete original archive was established. Separate
Release-asset upload tests returned HTTP 401; no raw-source remote transfer is
claimed. The 8 November paper and dataset retain their explicit frozen scope.
