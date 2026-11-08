# Independent collection review

This is an independent AI-agent audit of the new YouTube archive lane. It is not
an assertion that every channel or video has been collected. Historical study
corpora, acquisition receipts and older policies remain unchanged.

## Current contract

The current `research/subscription-screening/collection-policy.json` already
implements the latest user instructions and supersedes the historical global
five-minute rule and 100-Bashar limit. The new lane also adopts audio-first
acquisition. The new queue has no source-count cap. Only positively
Bashar-associated uploads require at least 300 seconds; other relevant channelers
have no minimum duration, including short uploads. Jamie Butler is excluded.
Unknown or conflicting Bashar durations stay in the inventory and require
fresh metadata or actual media-duration measurement before final admission. A mixed
interview account is not wholly Bashar because one upload mentions Bashar.
Resource-bounded invocations and storage limits must not be disguised as a
permanent source cap or a completed whole-channel download.

## Admission and completeness tests

- Resolve account handles/routes to canonical channel IDs when supported by
  actual evidence. Publisher contexts, literal URLs, aliases and distinct mediums
  are different units. Record resolution method and observation time; unresolved
  routes cannot silently become distinct authenticated accounts.
- Define each enumerated tab or collection: videos, Shorts, streams and uploads
  playlists overlap. Retain per-tab IDs and pagination/continuation disposition.
  Deduplicate upload IDs globally and expose cross-tab/account associations.
  A declared platform count, an extracted first page, a search result set or a
  recent RSS feed is not a full upload inventory.
- Claim completion only for the defined accessible tab/playlist scope at a dated
  observation with terminal pagination evidence and no failed continuation.
  Private, deleted, unlisted, region-limited and future uploads remain outside
  any unsupported lifetime-total claim. Duplicate uploads of one recording remain
  separate platform IDs unless content/session equivalence is evidenced.
- Count independently: observed upload IDs; duration/policy-eligible IDs;
  attempted and successfully retained video; retained audio; transcripts by
  source and edition; analyzed source units. Publisher RSS audio and Ra archive
  segments are not YouTube downloads. A newer transcript edition does not add a
  newly downloaded recording or a newly discovered upload.
- Network receipts must distinguish proxy CONNECT rejection, origin HTTP status,
  extractor failure, unavailable media, metadata success and completed asset
  validation. A gateway rejection is not evidence of YouTube bot detection.
  Alternative tools are applicable only if their actual request path and needed
  capabilities work; replacing a browser or adding a token does not establish
  that an inaccessible origin became reachable. No gateway-bypass relay is used.
- Audio-first success requires retained nonempty bytes, canonical video/source
  joins, container/audio-stream inspection and plausible duration. A zero exit
  code, filename, metadata JSON, thumbnail, HTML response or partial file alone
  is insufficient. Caption success requires parsed textual cues and source
  identity; absence of captions is distinct from a failed caption request.
- Resume must preserve completed artifact hashes, failed attempts and partial
  state; it must not confuse a queued item with a retained file. Atomic writes,
  bounded workers, free-space checks and per-source logs make interrupted runs
  inspectable. Sensitive signed URLs, cookies and credentials remain private.

## Executed review

The fresh ordinary-route probe at 19:53:07 UTC on 8 November 2026 failed with
curl exit 56 and proxy CONNECT HTTP 403. The retained header identifies Envoy;
the YouTube origin HTTP status is zero, no origin TLS was established and zero
response-body bytes were downloaded. Independent checks reconciled the saved
header/receipt hashes, exact command and zero-retry setting. Two GitHub controls
succeeded with CONNECT 200 and origin HTTP 200 and matched their retained body
hashes. The official latest yt-dlp release response reports 2026.10.26.

The extractor, media and caption stages were held before execution; their new
YouTube acquisition counts are zero. No redundant network request was made by
the independent reviewer. This establishes a destination-specific transport
failure in the observed configuration, not YouTube-origin bot detection, a
missing video or a proof that an extractor update repairs connectivity.

The corrected baseline inventory (`86b1078a…b3a98ab`) passed an independent
reconstruction of 13,902 source references, all 878 historical watch-page
identity/uploader joins and 30 historical caption-analysis references. Its 289
reconciled account references contain 2,060 observed unique video IDs. These are
not 289 authenticated mediums or complete accounts. All 173 previously explicit
Bashar-associated IDs retain the 300-second rule. The baseline contains 1,974
IDs passing duration/exclusion screening, 15 requiring a Bashar duration probe,
22 below that threshold and 49 unassigned to an account. Zero durations are
missing measurements, not proof of a zero-length upload. Passing duration and
explicit-exclusion checks does not establish channeling relevance. Candidate
accounts keep a separate review requirement for newly enumerated uploads.
The inventory has no measured platform upload totals and no completed tabs.
Final discovery integration will be checked as a separate edition.

The independent publisher-page discovery pilot passed checks of all 48 retained
page hashes, exact linked-video evidence and allowed first-party URLs. It observed
236 distinct YouTube IDs and 522 pending page requests. Nine literal account-link
observations represent eight case-normalized routes because two Elan handle links
differ only by letter case. These are page associations, not uploader verification.
The longer resource-bounded discovery edition remains under review; exhausting a
declared page queue cannot establish complete publisher-site or YouTube coverage.

The actual first-party audio pilot and two-file follow-up passed independent
page/hash/href, encoded-file, container and full PCM-decode checks. The pilot
retained one original MP3 (7,227,747 bytes; 596.1143125 decoded seconds) and a
673-word separately published written message. The reviewer read all 673 words
and independently reconstructed the selected message, closing and attribution
blocks. The follow-up retained two original MP3s (20,435,530 bytes;
1,662.1191875 decoded seconds) and 2,128 publisher-written words. The latter
check independently reconstructed text boundaries and redecoded both files; it
was not a second complete semantic reading. All three have zero YouTube
acquisitions, zero new ASR editions and no audio–writing or YouTube-equivalence
claim. Subsequent template-selected publisher bodies must be labelled as
unread when they have not been inspected. An Opus derivative must not be labelled
an unchanged original file.

The retained-corpus reconciliation (`bd6807e5…e5d780`) also passed independent
source/count checks: 493 selected text artifacts were rehashed (32,796,736 bytes),
all 341 distinct media paths were checked for existence/size and joined to the
root's fresh complete-media rehash receipt (10,715,508,036 bytes). Three small
media files were redundantly rehashed by this reviewer (5,634,634 bytes); the
reviewer did not repeat the entire media rehash. All 26 publisher-context counts
and selected edition/body/channel fields matched. Context-level media counts
are linked selected units, while the global storage denominator is distinct
resolved paths. Separate Ra segment and official Bashar publication/family
ledgers retain their original units and historical verification scopes.

Portable collector review found and corrected decoded-versus-container Bashar
duration, nonfatal decoder errors/process cleanup and boolean fresh durations.
The inspected collector revision (`22d2020d…f4b40ddb`) passed four tests executed by
this reviewer: the three requested regressions and the real yt-dlp
processor/downloader with an audio file and caption served over loopback HTTP.
The latter is a local integration check, not a successful YouTube request.
A later review found that the official Bashar legacy account URL was omitted
by the fallback route validator, although the pinned yt-dlp extractor accepts it.
The corrected final collector (`e5e19f8a…3ea0f46e`) supports strictly validated
legacy routes; its added actual Bashar/invalid-route regression was independently
executed and passed. The owner reports 17 focused offline tests on that revision.
The actual collector has
remained held before extraction, so the defects did not admit a bad download.
Its private store keeps per-tab receipts, immutable acquisition attempts, exact
uploader-based asset credit, verified-file resume and an ASR queue distinct from
completed recognition. Extractor-generator exhaustion is labelled narrowly and
does not assert independently observed final platform continuation.

The account provenance UI used incorrect identity-link field names and omitted
historical handle-to-channel-ID evidence from its inspector. The corrected
actual preview passed an independent six-check browser review: complete identity
link sets, unassigned global IDs, shared-gateway versus publisher distinctions,
workspace-retention limits, 320-pixel containment and no runtime errors. This
preview used the initial inventory edition; the final integrated browser gate
must bind the final producer data separately.

The 189-source OmNa audio candidate frame passed independent exact page-byte,
anchor-label, HTTPS/S3 URL, uniqueness and old-archive/three-pilot exclusions.
Forty candidates have available template-selected written blocks, all unread;
149 initially have text extraction explicitly pending. Candidate preflight alone
establishes offered links, not completed downloads, speaker identity,
audio–text equivalence or verified English speech. An embedded YouTube ID
reused on several publisher pages cannot identify their recording editions.

The immutable 40-file batch (`e79e0749…ae6ced4`) subsequently passed independent
checks of every retained Opus file: encoded hash/bytes, stream/codec inspection
and full 16-kHz mono PCM decode hash/sample count. Exact publisher page bytes,
audio hrefs and written/attribution blocks also matched for all 40 records.
These files total 170,798,373 retained bytes and 29,022.0759375 decoded seconds;
the separate publisher writing totals 36,665 words. The reviewer did not listen
to these recordings or semantically read these 40 messages. Original MP3s were
fully decoded by the executed producer and removed only after derivative
validation; their hashes/decode results remain receipts. Because those originals
are no longer retained, this independent pass verifies the Opus files and their
receipt joins, not a fresh rehash of the discarded originals. Lossy conversion changes the
waveform and would need a controlled comparison before acoustic-quality claims.
No ASR accuracy,
YouTube-equivalent download or new frozen-corpus analysis is inferred.

The final declared publisher crawl (`589096f9…871fe25`) passed an independent
reconstruction of every retained page: 1,239 page receipts, 1,215 retrieved
pages, 626,826,314 saved bytes, 1,890 distinct HTML/sitemap-linked YouTube IDs
and 22 literal account-link associations (21 after handle-case normalization).
All source hashes, exact ID sets and observation/evidence joins matched. The
queue has zero pending declared requests, but 24 failed or externally redirected
requests and the explicit host/path/depth restrictions remain. This is completion
of the declared queue, not all pages on these sites or any YouTube account.
Nine additional YouTube IDs occur in first-party HTTP Location headers. Those
redirect targets were not followed; they have receipt locators rather than an
invented target-page HTML hash or uploader identity.

The final public discovery (`98d4d339…672966`), inventory (`0411954f…2bcfff`) and
collector (`ecbe76a6…89ea3e0`) have exact checked joins. The final inventory has
297 account references and 2,812 unique IDs, adding 752 to its 2,060-ID baseline.
All 16,085 source references resolved, all 878 historical watch identity/uploader
joins and 30 caption-reference joins matched, and all 237 fresh publisher
account/video associations had shared first-party page evidence. The final
policy counts are 2,144 passing duration/exclusion checks, 15 requiring a Bashar
duration probe, 22 below its threshold and 631 unassigned. The separate discovery
comparison uses only two older ledgers: 2,055 baseline IDs plus 743 new
HTML/sitemap IDs gives 2,798; that intentionally narrower calculation does not
include the five other inventory references or nine HTTP redirects.

The earlier held collector edition is preserved. The final collector's exact
inventory/runtime bindings and every account/video membership
matched. Its private SQLite database independently confirmed zero attempts,
artifacts and ASR jobs; public logical request counts and retained bytes are
also zero. The shared CONNECT denial therefore remains a global hold, not
2,812 individually failed YouTube downloads. Candidate relevance review,
historical duration holds and the shared transport hold remain separate states.

Supplementary written recovery (`1f26be98…27e1cdab`) subsequently recovered all
149 selected publisher messages: 150,251 words, with six full AI-agent readings
reported by the owner and 143 automatic extractions. This reviewer independently
reconstructed all 149 exact bodies and page/wrapper/author/character locators;
the initially recovered 91 bodies are unchanged. Seventeen exact publisher
notice/marketing blocks are retained separately in private artifacts. The
reviewer read the final 190 characters and complete notices for all 17 relevant
messages. Three marketing footers name a different claimed entity from the
message ending, reinforcing why footer text cannot identify a speaker. None of
the closing self-attributions were removed. These are publisher-written editions,
not speech recognition or proof of audio equivalence. Their recovery is separately
counted even if an associated audio request is held or fails.

The remaining audio batches are complete and reconciled. The first run retained
117 of its 149 candidates and preserved 32 pre-request storage holds. A fresh
continuation used the explicitly authorized 1.5-GiB resource reserve, with its
measured free space, staging reservation, finite selection and capacity arithmetic
recorded separately; the earlier 2-GiB policy and receipts were not rewritten.
All 32 remaining candidates succeeded. No pre-existing accepted source data was
removed. The independent reviewer rehashed all 149 retained Opus files
(743,784,053 bytes), checked every page/link/download/original-decode and
supplementary-text join, and fully redecoded a prespecified shortest, longest
and sorted-middle sample. The three sample PCM hashes/counts matched. For the
remaining 146 files, strict decode completion is supported by the executed
producer receipts joined to independently rehashed encoded bytes; this was not a
second independent full decode of those 146 files.

The final aggregate (`7bac4155…4a99670b`) passed independent reconciliation of
all five immutable acquisition runs: **192 retained audio files**, comprising
three original MP3s and 189 lossy Opus derivatives, **942,245,703 retained bytes**
and **160,392.925125 decoded seconds** (about 44.55 hours). All 32 historical
storage holds are retained as history and resolved; the current finite candidate
queue has zero unresolved jobs. Failed/deferred attempts are not double-counted
as new candidates. The 43 acquisition-stage written editions and 149 separate
supplementary recoveries have disjoint IDs and exact source-page joins: **192
publisher-written editions, 189,717 words**. Those are not newly generated ASR
transcripts. New YouTube media/caption downloads, ASR editions and admissions to
the frozen 493-source analytical corpus remain zero.

The actual seven-module local integration passed eight independent browser
checks without mocked data or route interception: exact account identity evidence,
unassigned IDs, YouTube-versus-publisher separation, workspace retention limits,
the combined writing totals and their 43/149 split, 320-pixel containment and
absence of runtime errors. The reviewer visually inspected the desktop storage
view. The design owner's broader browser gate separately covers the final UI
revision and fault handling; this is not a live deployment verification.

A separate future-source triage has 302 distinct audio anchors on 133 retained
non-OmNa pages: Crimson Circle 284, Laarkmaa 12, Kryon 4 and Channeling Erik 2.
This reviewer checked all metadata/source/count joins and actual anchor markup
on one saved page for each publisher, without rerunning the whole 781-page scan
or requesting those endpoints. Genre, availability, duration and recording
identity remain unverified. These unrequested leads are outside the completed
finite OmNa frame and prevent an assertion that all publisher audio has been
collected. No complete YouTube channel acquisition is claimed.

**Publication assessment:** no unresolved material error in the accepted
collection, provenance, file-retention, written-recovery or integration evidence.
This is an AI-agent reproducibility review, not human validation, external peer
review, content authentication or a guarantee of storage permanence. Subsequent
media/model/collection changes require their own receipts and scope checks.
