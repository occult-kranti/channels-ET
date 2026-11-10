# Hashtag discovery and audio collection plan

This plan is published on 10 November 2026. It does **not** execute a new crawl,
download, transcription or model run. The restored checkout was synchronized
with the previously published `91b2f70` commit before editing. Historical source
receipts are preserved; this update does not revalidate all original media in the
restored workspace.

## Published baseline and current status

| Item | Status |
| --- | --- |
| Existing dataset, plots, dashboard and paper | Published; 683 selected documents, 694 editions and 1,599,556 selected words across 26 publisher contexts |
| Existing YouTube reference inventory | 2,812 observed video IDs and 297 account references; lifetime upload totals unknown |
| Expanded query design | Prepared: eight families with 62 example search strings |
| Fresh hashtag searches and all-tab enumeration | Planned; not executed by this update |
| New audio downloads, transcripts and analysis | Zero in this documentation/publication phase |
| Raw-source remote upload | Not verified in the published archive receipt; separate from pushing research code and metadata |

The machine-readable [collection-plan.json](collection-plan.json) supplies the
dashboard view. Its example terms are leads, not claims that a channel, medium or
nonhuman speaker has been verified. The [published links catalogue](../../DEPLOYED-LINKS.md)
provides the dashboards, papers and downloadable research artifacts.

## Discovery and relevance

Start with `#channeling`, `#channelling`, `#mediumship`, `#mediums`, untagged spelling
variants and phrases such as “trance medium.” Add documented combinations with
claimed ET civilizations, councils, angels, named communications and religious
figures. Native-script variants broaden discovery without assuming every term is
an exact translation or every religious practice is channeling.

Preserve each literal query, language, source family, timestamp, result page and
limitation in a versioned execution ledger. Use known account identities where
already established; keep new aliases unresolved until supported. Distinguish
human medium, publisher, uploader, reposter and claimed speaker. Screen art-material
uses of “medium,” comedy, unrelated channels and metaphorical “channeling” using
actual evidence. Preserve the existing explicit screening exclusions. Mixed-content
accounts require video-level decisions.

Council of Contact and Council of Contract remain separate search terms. Name or
spelling similarity is not identity evidence. Hashtag/search coverage is a declared
discovery frame, never a complete census of all channeling content on YouTube.

## Channel enumeration and collection

For each admitted account, enumerate **Videos, Shorts and Streams** with supported
continuation handling. Union by video ID, preserve per-tab provenance and record
failed or interrupted pages. Unavailable items and unknown durations remain visible.
Completing an extractor run does not prove that all public, unlisted or historical
uploads have been observed.

The policy has **no item-count cap**. Only Bashar-associated material retains the
**300-second minimum**, including reposts. Other included mediums have no duration
floor. Unknown Bashar durations stay pending until metadata resolves them.

Refresh current yt-dlp/EJS guidance, supported JavaScript runtimes, relevant GitHub
issues and Stack Overflow answers. Compare YouTube.js, NewPipeExtractor, pytubefix
and youtube-transcript-api only against concrete supported use cases. Record what
was inspected and tested. Updating an extractor does not repair a pre-origin
transport denial; distinguish that failure from origin authentication, rate limits,
missing captions or extractor defects. Do not substitute relays or blocked-endpoint
evasion. Existing diagnostic receipts are historical until a fresh test is run.

Validate **one full-duration audio-first pilot** before increasing concurrency.
Use stable-ID folders, an atomic job ledger, resumable downloads, bounded workers,
disk reservations, rate-aware retries and SHA-256/decoding/duration checks. A global
access hold is not thousands of individually failed downloads. Keep access-held,
capacity-held and retryable work in the queue.

## Text, analysis and publication

Preserve manually authored captions, automatic captions, publisher-written text,
translations and local ASR as different editions. Reuse a pinned local speech model
after checking model integrity, language support and available resources. Record
the model revision, software, settings, language, timestamps, source audio hashes
and segmentation coverage. Machine confidence is not measured word accuracy.

Admit validated bodies to a new frozen analysis frame before refitting TF-IDF,
topics, clusters, networks or question-bank candidates. Preserve earlier editions
and avoid counting repeated publications as independent observations. Inspect
length, transcript-origin and publisher-context sensitivity. Candidate questions
and nearby text are not automatically validated question–answer pairs.

Publish measured progress using separate units: **discovered video IDs, enumerated
IDs, verified audio sources, sources with text, analyzed body units, attempted
failures and queued/held jobs**. Unknown lifetime totals stay null. Exports and
dashboard values must derive from the same records. Source redistribution terms
remain distinct from the user's authorization to store material publicly; actual
remote file verification is required before reporting an upload.

## Planned storage layout

```text
manifests/queries.jsonl
metadata/channels.jsonl
metadata/videos.jsonl
state/collection.sqlite
audio/<channel_id>/<video_id>/
text/<channel_id>/<video_id>/<edition_id>/
analysis/<frame_version>/
public/
```

This is the target organization, not a claim that those new folders already contain
downloads. Existing executable collection and analysis code remains available in
the [YouTube archive workflow](../youtube-archive/README.md) and
[dataset methods](README.md).
