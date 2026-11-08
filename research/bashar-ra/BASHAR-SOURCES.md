# Bashar source acquisition and coverage

This collection separates recorded speech, written teaching references, session
handouts, and discovery metadata. It does not establish the truth of attributed
claims, an extraterrestrial identity, or complete coverage of Bashar's work.
Raw audio, transcripts, HTML, PDFs, player configurations and signed media URLs
remain in private cloud workspace storage, outside Git and Pages. This workspace
is not a verified persistent Google Drive upload or a user-managed ChatGPT drive.

## Retained material revalidated

The prior collection contains **19 publisher recordings**, **22.2246 hours**,
**1,664,529,703 original-audio bytes**, and **222,699 machine-recognized words** in
20,938 segments. Each original audio file, acquisition receipt, ASR receipt,
execution signature and all 57 ASR output files were checked again. Source and
receipt identities, decoded duration, transcript/segment consistency and timestamps
also passed. No audio was redownloaded and no inference was repeated for these 19.

They comprise 17 interviews, one publisher promotional interview and one skeptical
commentary. They are **Bashar-context recordings, not 19 verified direct channeling
sessions**. Hosts, guests, advertisements and quoted speech are not diarized.
Uploader/publisher labels do not authenticate a voice. No matching YouTube edition
has been established. The publication-unit identifier is the RSS source ID;
historical channeling-session identity remains unresolved. Exact media hashes
identify duplicate editions but do not prove that distinct files contain distinct
sessions. Four earlier acquisition warnings about RSS-declared duration or size
remain preserved.

The earlier 16 publisher-text documents concern Daniel Scranton or Paul Selig,
not Bashar, and are excluded. Titles and AI digests are never admitted as speech
transcripts.

Private manifest: `bashar/corpus/manifest.json` under the study's external private
root. Its frozen execution source is `bashar/inventory-executed-source.py`; the
execution binding records hashes. Current source code may have additional checks
and acquisition functions; it is not retroactively described as the executed code.

## Official written references

Five visible teaching-page bodies were retained from the publisher:

| Official page | Extracted words | Scope |
|---|---:|---|
| [A Message from Bashar](https://www.bashar.org/message) | 858 | Written teaching |
| [Basic Principles](https://www.bashar.org/principles) | 300 | Written teaching |
| [Follow Your Excitement Formula](https://www.bashar.org/formula) | 234 | Written teaching |
| [Seven Sequential Steps](https://www.bashar.org/sevensteps) | 143 | Written teaching |
| [Five Laws of Creation](https://www.bashar.org/fivelaws) | 111 | Written teaching |

The 1,646 words are the exact visible main bodies, with scripts and navigation
excluded by explicit heading/footer boundaries. Full HTML and HTTP receipts are
retained. Publication dates are unknown; a footer copyright year is not used as a
publication date. These texts are authored references, not authenticated verbatim
transcriptions of particular recordings.

All **35 explicitly linked PDFs** on the official
[handouts page](https://www.bashar.org/handouts) were downloaded: **34,630,206 bytes**,
**59 pages**, and **5,126 extracted words**. Downloaded bytes match the saved HEAD
size plan; PDF headers and page counts validate. Forty-seven pages required
English Tesseract OCR after sparse native extraction. OCR runs used 160-DPI page
renders, English `--psm 3`, and one thread; temporary renders were removed after
extraction. All original PDFs and extraction receipts remain private.

The handout text coverage is explicitly **partial**: text extraction omits
relationships encoded in diagrams and OCR has not been exhaustively corrected.
These are session handouts, not complete session transcripts. A Formula page and
Formula handout overlap; the 40 reference files are not 40 independent doctrines,
sessions or creators. Claims about synchronicity, manifestation, health or physics
are attributed publisher statements, not established findings.

Private manifests: `bashar/official-pages/manifest.json` and
`bashar/official-handouts/manifest.json`. Both bind the frozen
`official-reference-executed-source.py` with SHA-256
`47245e89eb1ea001ea2540cce7cd56fec7d50afe84b6aee4d0da00fafe602cf6`.

## Official public video route and bounded audio pilot

The [official Bashar website](https://www.bashar.org/) links the
[Bashar Communications Vimeo profile](https://vimeo.com/basharcommunications).
Its finite public listing yielded **307 unique video IDs**. This is one publisher
profile, not a count of all Bashar uploads across YouTube or all platforms.

The first yt-dlp profile request failed certificate verification with its bundled
CA store. The supported `--compat-options no-certifi` setting uses this environment's
system CA while keeping TLS verification enabled. That retry succeeded. The proxy
was retained, and no cookies, account credentials, alternate proxy or disabled TLS
were used. A public Vimeo web-page extractor subsequently requested login; the
public oEmbed API explicitly linked a separate embeddable player, which provided
public audio metadata without authentication. These outcomes are retained
separately rather than reporting a successful login or paid-session download.

The first audio pilot is
[The Mind Body Meditation: Bashar discusses Time Travel with Alan Steinfeld](https://vimeo.com/392834325).
The original publisher explicitly calls this a clip from a longer session. Its
public audio-only track is **422.336 seconds**, **13,467,324 bytes**, SHA-256
`a5e9eb83c5a0fbadbd4f69e0b03f332654881387e3aff3de93d02d6938e9eed7`.
The player exposes no captions. Public profile membership, oEmbed identity,
player identity, original audio format and actual duration agree. The collector
used one fragment worker, a 100 MiB pilot cap, no retries, and a 6 GiB free-space
reserve. The complete public excerpt was retained; the complete advertised paid
session was not obtained. Attribution to Bashar/Alan Steinfeld comes from the
publisher, and is not independent voice authentication.

The full available excerpt was submitted to the existing local Whisper tiny.en
CPU model: **870 words in 50 timestamped segments**. English was an explicit
unverified assumption, not detected spoken-language evidence. VAD retained 341.344
seconds and the last recognized segment ends at 376.38 seconds; these values do
not establish that all audible speech was transcribed. Unknown speaker roles are
preserved. The acquisition, model, executed core, parameters, segments and outputs
are hash-bound. An independent provider-guard review led to stronger admission
checks; the actual source passed a separate post-execution validation, while the
original inference receipt and executed code were left unchanged.

Private acquisition receipt: `bashar/vimeo-pilot-392834325/receipt.json`.
The executed pilot source is frozen separately; subsequent code changes do not
rewrite that receipt. See the study's acquisition inventory for the finite
profile's final language-label, availability and caption counts. The duration
census retrieved all 307 oEmbed records: **87 are at least five minutes**, totaling
**34,727 seconds (9.6464 hours)**; 220 shorter items are excluded. Most eligible
entries are publisher-selected highlights or previews. Metadata-only records do
not count as downloaded audio or transcripts. At the pilot's measured bitrate,
87 originals would require about 1.107 GB; this is a planning estimate, not a
downloaded-byte total or guaranteed size.

The [Bashar TV introduction](https://tv.bashar.org/pages/introduction) presents
12 curated sessions in four paid bundles. Catalog descriptions and checkout links
are discovery evidence only. No paywall or account-only recording was accessed.

The completed public-player metadata census exposes audio-only formats for all
87 eligible publications. Publisher title/description screening separates their
formats; these labels are not an independent verification of a performance:

| Publication format | Count |
|---|---:|
| Session highlights or excerpts | 77 |
| Explicitly translated session excerpt | 1 |
| Initial time-travel Q&A excerpt | 1 |
| New Year greetings, completeness unresolved | 3 |
| Event promotions | 2 |
| Product introductions | 2 |
| Product explainer attributed to Kirby Seid | 1 |

Fourteen player configurations provide `en-x-autogen` caption tracks. Although
yt-dlp places these under `subtitles`, their language label explicitly marks
automatic captions; they are not human-authored reference transcripts. All 14
direct VTT files were retained: **116,465 bytes**, **1,499 cues**, **11,719 words**.
Their original model and accuracy are unknown. Parsing retains cue order/times,
removes caption markup and decodes HTML entities without editing speech or
inferring speaker roles. Together with the initial local-ASR pilot, the fixed
15-publication speech snapshot contains 12,589 words; it remains separate from
the earlier 19 mixed-context recordings and from the later complete frame run.

The original-language low-track sample, Vimeo 714615663, validates as 302.442667
seconds and 4,805,475 bytes, with an approximately 128 kbps AAC container. Choosing
the lowest available original-language publisher encoding for each publication,
while retaining the existing high-quality pilot, yields 74 low and 13 high tracks.
The revised sample-based size estimate is 630,055,383 bytes; conservative source
caps sum to 833,182,320 bytes. These are planning values, not actual acquisition
totals. Two media workers acquire the explicit finite frame with zero retries,
inherited proxy, verified TLS and a 3 GiB + 256 MiB free-space floor.

The corrected audio collection retains **86 qualifying public publications**,
totaling **576,358,404 bytes**, including the two previously verified pilots.
There are 84 selected source acquisitions beyond those pilots. Two pairs of uploads have identical encoded audio
bytes: 204086275/204072408 and 204086006/204073990. Thus these 86 publications
represent **84 distinct encoded-media hashes**; broader historical-session overlap
is still unresolved. Publication copies remain in storage, while analysis can
collapse these proven duplicate families.

One additional original file remains retained but excluded: Vimeo 329903959 is
advertised as 300 seconds but measures **299.648 seconds**, below the strict
five-minute rule. Its 5,196,831 bytes remain in a separate unadmitted-artifact
receipt. It was not padded, redownloaded or silently counted as qualifying.
The frame therefore has 87 resolved publication dispositions, with 86 qualifying
publications and one boundary exclusion.

A downstream duration audit also caught an incomplete first encoding of Vimeo
204089777. Its downloader recorded HTTP 503 and skipped a six-second HLS fragment
under yt-dlp's default behavior. Container duration alone concealed the gap: the
container spanned 310.954667 seconds, while only 304.96 seconds decoded. A separate
strict reacquisition used `skip_unavailable_fragments=False`; its decoded duration
is 310.9546875 seconds, and a new ASR edition replaces the incomplete one. The
4,549,330-byte partial source, its ASR and all prior frozen manifests remain
preserved and explicitly superseded. No tolerance was loosened to admit them.

The final whole-frame audit rehashes media and checks retained transport logs,
all packet intervals, initial timestamps and terminal/container boundaries, with
a 50 ms codec tolerance. It binds compressed raw packet evidence and immutable
code snapshots. All 86 selected editions pass; the old incomplete encoding fails
and the short recording remains excluded. Physical original-audio storage is
**586,104,565 bytes across 88 encodings**: 86 selected files and two unadmitted
files totaling 9,746,161 bytes. These operational checks do not establish complete
historical-session coverage or transcription accuracy.

One local ASR worker uses two CPU threads, reuses the 14 available platform-caption
editions and the earlier local pilot, and records every remaining success, failure
or hold separately from audio acquisition. Two explicitly Japanese-translated
publications require a pinned multilingual model; they do not enter English-only
inference or the English comparison merely because their descriptions are English.
Multilingual auto-detection does not guarantee complete code-switch transcription.
Only newly generated PCM derivatives may be removed after source, model and output
verification; their hashes, sizes and `retained: false` dispositions remain in
receipts. Original media and previous WAVs/receipts are preserved.

The final preferred speech collection contains **86 publications and 70,159
whitespace-delimited words**: 14 platform automatic-caption editions and 72 local
ASR editions. Eighty-four publications have English-model/platform-language labels;
two explicitly translated publications use the pinned multilingual tiny model and
remain outside English lexical fits. Whitespace counts across these language
groups are not a language-neutral measure. Two additional local ASR editions of
captioned recordings support the paired sensitivity comparison.

All 86 selected publications also have full-stream recording-quality measurements.
Twelve caption-only sources required metrics-only processing, with no new ASR.
Their summed decoded duration is 34,429.482375 seconds; every selected container/
decode discrepancy is at most 0.042688 seconds. The public
`audio-quality-summary.json` reports RMS, peaks and quiet-window measurements;
quiet windows are not a measure of speaking time or evidence about an entity.

Two deterministic captioned-publication selections also receive a local ASR
edition after the main queue: lowest numeric Vimeo ID and the upper-median
duration item, with numeric ID as tie-break. Comparing these two machine editions
measures transcript disagreement, not recognition accuracy against ground truth.

## Reproduction and boundaries

`acquire_bashar.py inventory --output /absolute/private/fresh-directory` verifies
and normalizes the retained publisher cohort. `handouts --plan … --output …`
requires the exact saved, linked PDF frame, known size bounds and a fresh private
output. `vimeo-pilot --info … --profile … --oembed … --output …` accepts the reviewed
single public player edition and audio-only format; use the environment's existing
yt-dlp virtual environment. It is deliberately not an unrestricted bulk downloader.

`test_acquire_bashar.py` checks source/receipt mismatches, changed hashes,
fixture contamination, digest misclassification, incomplete ASR scope, timestamp
and count consistency, symlink routing, altered PDF frames, bounded main-text
extraction, and Vimeo publisher/player/audio-only/five-minute boundaries.
Synthetic fixtures test the verifier and never count as acquired data.

`run_vimeo_asr.py` and `normalize_vimeo.py` are portable successors with explicit
CLI paths; run either with `--help`. The queue accepts a fresh output directory and
an optional prior finalized run for verified source-byte-matched reuse. The
normalizer separately emits acquisition dispositions, one preferred transcript
edition per publication, and the paired alternative editions. Reused platform
captions and the initial pilot preserve their original source and edition IDs.
New local transcript edition IDs map explicitly to unchanged receipt recording
IDs through `asr_receipt_source_id` and `recording_id`.
Both successors require an exact-edition media-integrity audit; they reject the
superseded encoding even if an older acquisition receipt called it completed.
Use `--acquisition-dir` for a corrected queue input and `--media-manifest` for the
normalizer's corrected acquisition projection. `audit_vimeo_media.py` can reuse
hash-verified raw packet evidence without repeating media requests.

Authoritative private final inputs are under `official-vimeo-corpus-reviewed/`:
`manifest.json` (SHA-256 `633a9254fd493e566ebb553cd4c3a893e432f59b63ea6bbca364421526ab621c`),
`acquisition-manifest.json`, `audio-dispositions-manifest.json` and
`paired-editions-manifest.json`. The final integrity audit is
`vimeo-completeness-audit-final/manifest.json`, SHA-256
`b5aeca2c0e59b67001760482f7e5fcf4190c9834d7ddc075121b0c5145e56c3d`.
Earlier `official-vimeo-corpus/` and intermediate corrected manifests are retained
for lineage; they are not the selected final corpus.

The actual initial frame ran the preserved source
`vimeo-frame-executed-source.py`, SHA-256
`0efa34a192eff3d8ca9b98791375b174edb33219fdc2042c8e92c0df3b36b1e0`.
Its ASR queue snapshot is `vimeo-asr-queue-executed.py`, SHA-256
`99f9a5abe50e1ba465aa9bf5097d652b2a15821a79fc893c29f04b64a7262485`.
The reviewed audio core is bound at SHA-256
`7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64`.
The public successors have additional argument/reuse/preflight checks and are
not described as having executed this initial batch. Each actual receipt retains
its own exact execution binding.

YouTube's ordinary cloud connection still fails at the CONNECT proxy before
origin TLS. This is distinct from Vimeo's supported CA-store issue. No new bulk
YouTube attempts or alternate proxy routes were used. The user explicitly lifted
the earlier Bashar count cap for this study; clips below five minutes and Shorts
remain excluded. Available-source, rights and actual disk bounds still apply.
Vimeo preview eligibility does not make an excerpt a
full session, and only explicit finite source frames justify completeness claims.

The publisher retains copyright. Its site advertises personal-use access and
limited fair-use terms, and its robots metadata distinguishes search/reference
use from AI training. Public access does not grant unrestricted republication or
model-training rights. The current work retains source copies for private research
and releases code, provenance summaries and aggregate analysis, not the full
copyrighted collection. Exhaustive historical coverage, independent speaker
verification, transcription accuracy, missing paid sessions and unseen uploader
reposts remain unresolved.
