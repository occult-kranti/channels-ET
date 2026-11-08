# Bashar / Ra storage and execution plan

This records a capacity audit and a narrowly approved cache cleanup for the new corpus; it is not a claim that the Ra recordings have been downloaded. Existing sources, transcripts, model weights, receipts and the preceding Crimson Circle archive remain preserved.

## Observed capacity

At the audit on 7 November 2026, the filesystem reported **6,838,636,544 free bytes**. The preceding acquisition workflow's 6 GiB free-space guard leaves **396,185,600 bytes** for new files. That guard has not been changed.

The cloud CPU quota is four cores (`cpu.max = 400000 100000`), memory is limited to 32 GiB, and no NVIDIA or DRI devices are exposed. The existing CPU ASR and analysis environments and cached models should be reused. Any additional checkpoint requires a separately bounded acquisition; the later multilingual extension is recorded below.

`du` reports visible allocated blocks, including files potentially supplied by an overlay lower layer. Those values are not a promise of reclaimable writable space. A before/after filesystem measurement is required for any approved cleanup.

## Reconstructible or disposable candidates

| Candidate | Logical bytes | Why it can be considered | Required preservation |
|---|---:|---|---|
| Three expanded GitHub Pages `artifact.tar` copies | 670,525,440 | Each file was SHA-256 matched to the sole `artifact.tar` member of its retained original `github-pages.zip` | Keep each original ZIP and surrounding CI receipts; preserve the reconstruction ledger |
| pip HTTP package cache | 259,249,753 | Re-downloadable installer responses; no installed packages or model files are in this candidate directory | Keep installed environments and all model caches |
| npm `_cacache` | 250,287,850 | Re-downloadable package cache; distinct from installed `node_modules` and `_npx` environments | Keep installed dependencies and project files |
| Current ET static deployment staging | 75,381,770 | Clean commit `117312a2675e8af2edbe24ad9b4842253377ec33`; all 414 staged assets match the deployment manifest and can be rebuilt | Keep Git history, external verification logs and a copy of the deployment manifest |
| **Total potential logical bytes** | **1,255,444,813** | Original pre-cleanup candidate inventory | Only the separately recorded subset below was removed |

The three TAR paths are under the existing `setup-validation` trees for chart relationships, date wayfinding and the eschatology atlas. Their compressed originals retain the exact same bytes; removing only expanded copies would not erase the original CI artifact. The archive paths, member names and hashes are recorded privately in `capacity/duplicate-pages-tars.json`.

The candidates were checked against every original source path and acquisition-proof path in the preceding 151-artifact archive plan. None is a dependency of that archive. Its hardlink relationships and all 338 archived files remain untouched.

The 8.48 GB visible `/workspace/.cache` directory is primarily model weights and installed environments, not disposable package downloads. It is excluded from cleanup. Browser caches, historical screenshots, source documents, raw recordings, failed ASR evidence and other projects are also outside the approved candidate list.

## Completed bounded cleanup

After reviewing the audit, the coordinator authorized exactly the two installer-cache content directories and the three expanded TAR files. Each TAR was rehashed against the preserved original ZIP member immediately before removal. All cache files were regular files with one filesystem link; their identities, sizes and hashes were recorded before removal. The cache root directories remain. Original ZIPs and their surrounding receipts were rechecked after cleanup.

The cleanup removed **1,180,063,043 logical bytes** across 994 files, plus empty cache subdirectories. Observed filesystem free space changed from **6,834,135,040 to 8,021,471,232 bytes** (**+1,187,336,192 bytes**). The filesystem delta can include concurrent writes and directory allocation, so it is reported separately from removed file bytes. No release staging, model files, installed environments or source artifacts were removed.

`capacity/cleanup-receipt.json` preserves the exact removed paths, before/after measurements, each retained ZIP hash, the recovered TAR-member hashes and reconstruction commands. Restoration of an expanded TAR is `python3 -m zipfile -e <retained-original.zip> <original-pages-directory>`, followed by the recorded SHA-256 comparison. The deleted pip/npm content is repopulated only if future normal package installation needs it; current installed packages remain intact.

## Acquisition budget decision

Before parallel Ra audio transfers, obtain a finite manifest of official recording URLs, representation/edition, expected size and actual response metadata. A single canonical session may have several tape sides, remasters or transcript editions; these are not independent sessions. A HEAD length is a planning estimate until the downloaded bytes and decoded container validate.

The approved cleanup is complete. Its observed 8,021,471,232 free bytes leaves **1,579,020,288 bytes** above the unchanged 6 GiB floor, before subsequent task writes. The source inventory must determine the full compressed-audio requirement; one advertised file size must not be extrapolated into a claim that the whole corpus fits. Bind the new-task budget to current free space and known pending source bytes, while reserving room for metadata, plots and release validation. No transfer should rely on a stale free-space measurement.

Retain compressed publisher originals and official full transcripts. Reuse already verified Bashar recordings/transcripts. Avoid generating whole-corpus PCM or duplicate full-media ZIPs merely to analyze text. Any bounded audio-validation sample should declare its temporary decoded-byte requirement separately. An independently configured new-task reserve, if needed, must be documented and must not silently modify the preceding workflow's guards or receipts.

Private audit: `/workspace/channels-et-private/bashar-ra-2026-11/capacity/capacity-audit.json`. The coordinator authorized the recorded cleanup and owns the final transfer budget; the source acquisition agent owns the measured official audio inventory. The release-staging candidate remains preserved.

## Complete published-audio header pass

The frozen player-page inventory contains **2,620 distinct MP3 segment URLs across 106 canonical session pages**. Every retained player page was rehashed before the independent header audit. Ordinary HTTPS HEAD requests used two workers, a global maximum of five starts per second, no redirects, no response-body reads and no automatic retries. All 2,620 URLs were attempted once.

The pass returned **2,619 HTTP 200 `audio/mpeg` responses**, advertising **6,607,616,289 compressed bytes**. The remaining segment, session 83 question 3, returned an isolated HTTP 503. Its failed evidence is preserved; the pass does not establish a finite observed total for all originals until that missing length is resolved. Header bytes are planned source sizes, not downloaded media or verified playback.

At the terminal capacity check, the filesystem had **7,764,779,008 free bytes**. A proposed new-task reserve of 1 GiB plus 256 MiB of output scratch would leave **6,422,601,728 bytes**, already **185,014,561 bytes below** the known original-audio total, before the missing segment and further Bashar acquisitions. Reusing the existing verified pilot by hardlink can avoid 17,824,705 duplicate bytes. The coordinator must settle storage representation and budget before starting a complete original-audio batch; no further files have been deleted and the preceding 6 GiB guards remain intact.

The frozen header manifest SHA-256 is `ce41a92ce780e6573eace833fd8c4d60330edf37f0a46b63b89d5f5285ab71fe`. Any later isolated retry or completed inventory must retain this initial evidence and have a distinct receipt. If space requires a compact audio derivative, it must be labeled separately from the original publisher bytes and retain the original-source hashes, conversion settings and exact coverage. No conversion had been performed at that initial decision stage; the completed result is recorded below.

The coordinator authorized one isolated retry of session 83 question 3. It returned HTTP 200 `audio/mpeg` with **12,672,522 bytes**, completing the observed compressed-original total at **6,620,288,811 bytes**. The successful merged header manifest has SHA-256 `be9551eab18e126bdf322c25b2b7a01ef221bbfafe8f18cbce95b72fc1cb6627` and binds both the unchanged initial pass and the separate retry receipt. There were 2,621 header attempts, including the preserved isolated 503; no media bodies were read by this audit.

## Explicit new-collection representation and reserve

To preserve previous archives and leave capacity for additional Bashar material, the coordinator selected **full-length 48 kbit/s constant-bitrate Opus derivatives** for new Ra audio retention. These are lossy conversions, not the original publisher MP3 bytes. Each original must be retrieved to bounded staging, hashed and validated; removal of that temporary original is permitted only after its complete derivative has passed duration/container checks and a receipt binds both source and output. The already retained original pilot remains preserved. No temporal clipping, whole-corpus PCM or duplicate source archive is required.

The new compact collection has an explicit **4 GiB maximum retained-output budget**, a **3 GiB free-space floor**, and **256 MiB operational reserve**. Its source-transfer ceiling is the exact 6,620,288,811-byte frozen header inventory; source changes must stop rather than silently enlarge it. These are parameters for this separate acquisition path. Existing 6 GiB guard defaults remain unchanged. Source/derivative retention counts, lossiness, format, hashes and failed or incomplete transfers must remain separately visible in the dashboard and receipts.

The portable [`head_ra_audio.py`](head_ra_audio.py) successor can reproduce a new complete header pass using absolute `--frame` and fresh private `--output` paths. Its nine offline tests exercise source identity, body-free header handling, denial/transport pause and size/type validation. It is a later reusable implementation, not the executed source of the earlier frozen private audit.

## Bounded multilingual ASR extension

The separately approved frozen MiniLM baseline acquisition retained **90,872,263 bytes** across four model/tokenizer/configuration files, pinned to `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. These are retained artifact bytes from its file-hash manifest, not a newly inferred network-traffic total. The general-purpose encoder is reused without training or weight modification.

Two official items are explicitly described as Japanese translations. The coordinator approved a separate multilingual Whisper tiny checkpoint acquisition capped at 100,000,000 bytes, preserving the existing English-only model. `Systran/faster-whisper-tiny` revision `d90ca5fe260221311c53c58e660288d3deb8d356` required **78,208,361 transferred bytes**, including retained upstream metadata and README. Every selected file matched its pinned upstream Git-blob or LFS hash; the download used ordinary HTTPS with no automatic retries or framework downloads.

An offline-only local CTranslate2 CPU/int8 load confirmed the multilingual contract, including the Japanese language token. This was a capability check, not an accuracy evaluation, training run or weight modification. The private model cache contains acquisition, file-hash and load-validation receipts. Japanese or bilingual transcripts remain distinct from the frozen English comparison and must not be silently admitted as English text.

## Bashar publisher encodings and temporary PCM

The separate Bashar collection selects the lowest available original-language publisher audio encoding for each eligible public player, while preserving the previously acquired higher-quality pilot. The frozen selection contains 74 lower and 13 higher publisher tracks. A retained lower-track sample has 302.442667 seconds and 4,805,475 bytes, approximately 128 kbit/s AAC. These are publisher encodings, not new lossy conversions made by this project. The sample-based 630,055,383-byte estimate and 833,182,320-byte source-cap total are planning quantities; final actual retained and excluded-file totals must come from acquisition receipts.

The new acquisition and ASR queues explicitly use **3 GiB plus 256 MiB** of free-space reserve. The existing six-GiB collector and ASR defaults remain unchanged. A new ASR request can select `--min-free-bytes` and `--discard-decoded-audio`; both choices are bound in its execution receipt. The latter removes only that fresh request's `audio-16khz-mono.wav` after successful source, acquisition-proof, model and output verification. Its original size/hash, source derivation and `retained: false` disposition remain in the receipt. Failed work retains its temporary derivative for inspection; all original publisher media, previous WAVs and prior receipts remain preserved. Absent new PCM is excluded from retained-file exports and cannot make an absent original or transcript pass verification.

## Completed collection and integrity review

The canonical Ra archive now retains all **2,620 published recording segments** as **2,518,498,970 bytes** of full-length lossy Opus, with **106 ordered session playlists**. The verified original MP3 sources total **6,620,288,811 bytes**; their temporary copies were removed only under the recorded conversion contract. The existing **17,824,705-byte original pilot** remains. A separate **6,770,304-byte local Opus validation pilot** is an auxiliary copy of the same source, outside the canonical corpus. These three representations are not three independent recordings.

The canonical archive contains **414,322.667872 decoded seconds (115.08963 hours)**. The maximum source/retained decoded-duration difference is **20 microseconds**. Thirty first-pass HTTP 503 failures were preserved and recovered in one separately approved retry pass; no source is missing from the frozen frame. There were 2,649 batch media GET attempts, including 30 failed attempts and excluding the reused pilot's earlier GET. The canonical manifest SHA-256 is `05bafffc5c4526f50df50656082fb6ec3666f48c05f3b462972d5b893b43d202`.

The source owner rehashed every retained file and original-source proof before canonicalization. Independent review checked all source IDs, HEAD lengths, source-page/proof/cleanup bindings, playlist order and attempt counts, then rehashed and probed bounded media samples. This establishes acquisition and encoding coverage of the published frame, not a complete historical tape archive, a transcript-to-tape alignment, or listening validation.

The corrected Bashar frame retains **86 qualifying current publisher audio files**, **84 distinct encoded-media hashes**, and **576,358,404 bytes**. One 299.648-second boundary file (5,196,831 bytes) remains retained but excluded. A second 4,549,330-byte encoding remains as superseded evidence after a missing fragment was discovered; its strict replacement is counted among the 86 current sources. The two unadmitted encodings total **9,746,161 bytes** and are not extra current publications. All 87 candidate publication dispositions are preserved. Preferred text contains **70,159 words across 86 editions**, with two alternative machine editions kept separately.

The missing-fragment case exposed a downloader default that could skip an unavailable fragment. Future acquisition now refuses missing fragments. The corrected sources passed an all-source packet/log audit, including initial and terminal boundaries; independent review recomputed **1,602,732 packet rows** across the 86 distinct retained encodings, including the held editions. The reviewed corpus and final audit are bound by hashes in the source manifests and private review receipts. No prior source media, failed edition, or historical proof was deleted.

## Separate screened-publisher RSS phase: finite planning envelope

This is a new-phase recommendation, not a change to the running or historical Ra/Bashar guards. Its frozen RSS inventory contains 224 entries; 223 advertise at least 300 seconds. Those 223 advertise **5,369,281,393 source bytes** and **254,552 seconds**. The largest and longest advertised item is **148,127,913 bytes / 3,703 seconds**, implying **118,496,000 bytes** for 16 kHz mono s16 PCM. These are publisher declarations pending response-header and actual-media confirmation. The 48 kbit/s payload estimate is 1,527,312,000 bytes, or 1,573,131,360 bytes with a 3% container allowance.

At 2026-11-07 02:44 UTC, measured free space was **4,298,670,080 bytes**. A separate 2 GiB floor plus 448 MiB operational reserve and a 1.65 GB retained-audio ceiling requires 4,267,245,696 bytes, leaving only 31,424,384 bytes beyond the complete reservation. A **1.62 GB ceiling** leaves 61,424,384 bytes and is the more conservative recommendation while release/build work continues. Recheck free space immediately before execution; unrelated writes can reduce either margin.

For two ASR workers, this recommendation assumes ASR reads explicitly verified retained Opus derivatives, so only one original remains staged. The bounded working set is one original capped at 160,000,000 bytes, two PCM files capped at 120,000,000 bytes each, one compact output capped at 26,000,000 bytes, and 32 MiB for new provenance/text/figures: **459,554,432 bytes**, within the 448 MiB reserve by 10,207,616 bytes. If both publisher originals must remain until their ASR jobs finish, this working-set calculation does not apply. A derivative-specific provenance contract must preserve the original/output relationship and identify lossy ASR input truthfully.

Two ASR workers with two CPU threads each plus one transient encoder thread can briefly oversubscribe the four-core quota; throughput improvement must be measured. No additional model download is included. Hold any source whose actual size/duration exceeds the finite bounds, stop new scheduling on a resource/integrity failure, and preserve failure staging for review. Additional first-half publisher inventories require a separate budget; do not silently append them to this frame. The private `capacity/screened-rss-resource-plan.json` retains the exact inputs, arithmetic and planning status. The coordinator owns the final new-phase decision.
