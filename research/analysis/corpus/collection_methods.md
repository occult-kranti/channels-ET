# YouTube acquisition methods and frozen coverage

On 2026-10-23, we attempted public watch-page metadata for all 925 unique valid video IDs in the union of the existing atlas (482) and Claude's supplied draft (457), with 14 IDs shared. We used ordinary unauthenticated requests, five workers, no media downloads, no cookies, no credentials, no proxies and no retries. The batch would stop on HTTP 403/429. It completed without that stop condition.

We recovered metadata for 878 videos and positive durations for 877. One recovered item has zero duration and is excluded from duration means. The 47 remaining videos exposed no matching videoDetails through this route: 10 LOGIN_REQUIRED and 37 ERROR responses. Failures were retained, not interpreted as deleted content. Publisher IDs, current titles, channel routes, durations and exact reported timestamps were extracted from public watch metadata. Each success includes a retrieval time and SHA-256 of the fetched HTML. The hash records observed byte identity; the full HTML is not redistributed. Metadata availability does not establish that a video can be played.

Duration summaries describe averages of the indexed videos with available durations. This is not full channel enumeration, random sampling, total audience size or an estimate of posting rate. Upload timestamps do not date the original source session, particularly for reposts.

A separate purposeful caption pilot selected the first two valid video IDs in each supplied status-ok channel's recent-video order, plus the requested Bashar and Athina accounts, excluding explicit donation/register/all-day-event titles. One channel (Aluna Ash) had only one supplied entry. One additional Scranton video was collected for author-web/caption concordance and excluded from balanced comparisons. The 36 selected records yielded 34 caption documents: 32 automatic and 2 manual. Track languages were 29 en, 2 en-US, 2 ja and 1 cs. Excluding the extra Scranton record leaves 30 English/en-US pilot documents. Availability failures were a disabled caption track and a members-only video; neither was circumvented.

The caption package was youtube-transcript-api 1.2.4. Three initial language-preference failures were repaired by selecting actually offered en-US/Czech tracks; the initial failure and correction remain logged. No automatic translation was requested. Captions were not audio-verified, human-corrected or speaker-segmented. Full text remains only in external scratch storage. Public artifacts contain source URLs, language/ASR labels, content hashes and derived features, without full captions.

The 75 structured Bashar digests already in the pinned repository are researcher summaries, not original transcripts, and are excluded from the direct caption corpus. Topic percentages and word counts inherited from those digests are not validated by this collection.

## Maintenance

`acquire_youtube.py` provides a portable metadata/caption acquisition CLI. Install the pinned `acquisition-requirements.txt` for caption mode; metadata mode uses Python's standard library. Give caption mode an external raw directory outside Git. Reacquisition can legitimately change titles, availability and hashes. Preserve a new dated snapshot rather than overwriting this frozen one.

Frozen metadata SHA-256: `845262d5e255a253fccec86c75f1d980d454791616dcb5cccf63dc80441cc380`.

The original batch capture script is `capture_metadata_2026-10-23.py`; its hash is recorded in `metadata_summary.json`. The portable maintenance CLI uses the same metadata fields and availability contracts, with resumable logging.
