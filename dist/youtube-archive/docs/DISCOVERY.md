# First-party discovery and publisher audio leads

The discovery lane reads public creator/publisher pages, archives, sitemaps and linked feed routes through ordinary HTTPS. It never requests a YouTube player, media URL or proxy site. The result is an inventory of **observed links**, with evidence for each link. A linked video ID is not a verified upload, an available video, an uploader association, a saved recording or an analyzed transcript.

The public artifact is `publisher-discovery.json`, delivered as the `discovery` module. The acquisition pipeline and publisher-media retention module have separate receipts and denominators.

The final edition attempted **1,239 distinct publisher/URL pairs**, retrieved **1,215 documents**, and observed **1,890 distinct YouTube IDs in their markup/sitemaps**. It exhausted the declared URL queue with zero pending entries. Of these IDs, **743** were absent from the two specified historical ledgers, expanding their combined observed-ID union from 2,055 to **2,798**. The collector downloaded no YouTube media.

| Publisher context | Retrieved / attempted pages | Linked video IDs | Absent from the two prior ledgers |
| --- | ---: | ---: | ---: |
| Magenta Pixie | 25 / 25 | 1,114 | 0 |
| Elan Interactions | 5 / 5 | 5 | 3 |
| Daniel Scranton | 148 / 148 | 116 | 90 |
| Natalie Glasson / OmNa | 434 / 434 | 222 | 221 |
| Channeling Erik publisher site | 139 / 151 | 87 | 87 |
| Laarkmaa | 14 / 14 | 18 | 17 |
| Lyssa Royal Holt | 9 / 9 | 17 | 14 |
| Kristin Davies Medium | 6 / 6 | 0 | 0 |
| Bashar Communications | 2 / 2 | 0 | 0 |
| Tracy Kumbera | 51 / 51 | 7 | 7 |
| Athina Król | 2 / 2 | 0 | 0 |
| Paul Selig | 13 / 25 | 2 | 2 |
| Kryon / Lee Carroll | 16 / 16 | 1 | 1 |
| Arkayla | 3 / 3 | 3 | 3 |
| Sam the Illusionist | 7 / 7 | 0 | 0 |
| Crimson Circle | 341 / 341 | 298 | 298 |

These are publisher associations, not verified uploader inventories. A zero means no video ID was found within this source scope; it does not mean the channel has no videos. Page counts include robots documents and sitemaps. Paul Selig's nine additional YouTube HTTP redirect observations are preserved separately from this HTML/sitemap table and can be reconciled by the archive inventory owner.

## Prospective source scopes

The initial configuration binds the previous ET/tradition registers, subscription-screening references, the retained Bashar-index source pin and the earlier Magenta archive index. Sixteen publisher contexts were selected: Magenta Pixie, Elan Interactions, Daniel Scranton, OmNa, Channeling Erik, Laarkmaa, Lyssa Royal Holt, Kristin Davies, Bashar Communications, Tracy Kumbera, Athina Król, Paul Selig, Kryon/Lee Carroll, Arkayla, Sam the Illusionist and Crimson Circle.

The configuration records exact seed URLs, allowed publisher hosts, path patterns and maximum link depths. These are finite research scopes, not claims to cover every page a publisher has ever published. The earlier Magenta inventory comprises 23 archive pages and 1,114 linked IDs. Its main archive page, 22 numbered pages, robots document and sitemap remain distinct page types in the fresh crawl.

The collector first records each publisher's robots policy. It follows eligible same-publisher links, including announced sitemaps, while keeping visited and queued URL sets. It recognizes explicit watch, short-link, embed, Shorts and live URLs, including YouTube-nocookie embeds and JSON-escaped URLs. Playlist placeholders and malformed IDs are rejected. Non-Bashar videos have no minimum duration; unknown duration does not exclude an ID from discovery. Bashar's 300-second acquisition requirement belongs to the later eligibility stage, not metadata removal.

Every retrieved response has its source URL, final URL, UTC retrieval time, HTTP status, byte count and SHA-256. Raw pages stay private. Failed requests, disallowed or out-of-scope references, invalid XML and pending URLs remain visible. A page marked terminal means only that the parser found no eligible continuation under the declared rules. It does not establish the end of a YouTube uploads playlist or an entire website.

## Requests, resource bounds and repaired editions

Two workers perform bounded document requests. The collector checks every redirect against declared publisher hosts before sending another request. The six-megabyte response limit is enforced inside each response read. Wall-time and aggregate-source-byte thresholds are **soft stops checked between batches**, so an in-flight batch can finish beyond a threshold. Source HTML is held in RAM; public metadata and compressed evidence archives are handled separately.

The initial 48-page pilot produced 236 linked video IDs and was retained. The first 600-page edition retrieved 589 documents. Seven failures arose from a local Unicode URL-encoding defect on Daniel Scranton paths containing the infinity character. The repaired edition percent-encodes the request path/query without double-encoding existing escapes, reuses verified successful responses, and retries failed receipts explicitly. It retrieved 597 of those 600 documents. Previous failed receipts and executed-code snapshots are preserved.

An extended run reused that cache and attempted the remaining declared queues, stopping at its source-byte guard with 79 URLs pending. A further cached continuation increased the RAM source budget to finish that finite scope where possible. Each run records its executed code, cache-parent hash and actual request results; the final continuation also records explicit execution limits. Purely cached batches incur no network-pacing delay and do not create new retrieval timestamps. An unsuccessful request is never treated as a successful cache entry.

The machine-readable final artifact supplies the authoritative counts, per-publisher rows, remaining failures and any pending URLs. A queue can be exhausted while failed requests and excluded link classes remain. That distinction is retained in both the result and dashboard.

The final 24 failed/held document requests comprise 21 redirects outside declared publisher hosts, two HTTP 503 responses and one HTTP 410 response. The redirects include nine YouTube destinations, nine references to the same FeedBurner feed, and three Apple Podcasts destinations; none was requested by this collector. Its 238,006 out-of-scope link occurrences are counted across parsed pages, can repeat URLs, and are not a count of missing videos or unique unvisited pages. The final saved response bodies total 626,826,314 bytes in RAM.

## What account and video links establish

Account-link observations preserve the literal route and source page. A handle, legacy `/user/` route and `UC…` channel ID are not automatically merged. Handle case variants are reported separately from a case-folded route count; this is still not a count of authenticated accounts.

An official publisher page can contain guest, promotional or comment links. Accordingly, an account linked somewhere in its markup is an **unreviewed association**, not a declaration that the account belongs to that publisher or is a relevant channeling medium. Malformed account routes containing tracking parameters in the path are rejected rather than silently repaired into a claimed account. Video links have the same source-context limitation.

Some publisher URLs redirect to YouTube or an external feed service. The HTTP Location is retained as a redirect observation, and the collector stops before requesting the external destination. Such evidence is different from a retrieved HTML page and must retain that distinction if imported into a wider inventory.

## The explicit historical comparison

The discovery projection compares IDs against two named, hash-bound ledgers:

- The existing aggregate inventory: 942 distinct IDs.
- The earlier Magenta archive: 1,114 distinct IDs.
- Their overlap: one ID; their union: **2,055**.

“Not in the two declared prior ledgers” means set difference against that exact union. It does not mean that no other historical file ever mentioned an ID. The archive inventory owner has a separately reconciled 2,060-ID baseline with five additional references, so its final union and increment must be calculated independently. The public output includes each controlling file hash and the arithmetic, preventing these similar but different denominators from being conflated.

The projection verifies every retained page hash and every observation-to-receipt join. It retains per-page eligible-link counts publicly, while the full URL lists remain in the private manifest. All observed ID counts remain separate from YouTube upload totals, which are unknown.

## Real publisher audio without a false YouTube-download claim

The crawler also records pages where a YouTube reference co-occurs with explicit audio or transcript links. Co-occurrence alone is only a lead. It does not prove that an MP3, written message and YouTube video contain the same words, timing or waveform.

Three OmNa pages were inspected directly. Each offers a specific Download Audio MP3 link alongside a written message and YouTube reference:

- “Is Archangel Michael Shattering Your Boundaries?” — `xsgGSzfdLaY`.
- “What Are You Giving to the Earth?” — `wnVpxf4SClg`.
- “Is Disconnection Stealing Your Joy?” — `1O3BcL4F6xc`.

The inspected template separates main message block `a959f86`, closing block `8d74e16` and attribution block `0143f75`. The additional two messages were read completely in this lane; their respective main/closing word counts were 1,154/9 and 960/8 under the stated visible-text join. These readings do not validate spiritual, energetic or health assertions. The media owner separately validates the first pilot's original audio and full decoded coverage before scaling.

The first stricter automatic candidate frame required this text template and admitted 40 additional pages. A subsequent **audio-first** frame separated explicit audio eligibility from text extraction: 189 distinct MP3 candidates, of which 40 had the checked text template and 149 had text pending. These are candidate counts from their frozen input edition, not retained-download counts. The collector performed no media request.

Audio eligibility requires one explicit MP3 anchor labeled as an audio download on a retained publisher message page, the inspected OmNa S3 host, one co-located YouTube reference, and exact source-byte bindings. Shop, cart and product routes are not substitutes for a message. Exact old audio URL matches, the three pilot audio URLs and duplicate audio URLs are excluded. No title-only deduplication or YouTube-ID equivalence is inferred. An earlier candidate edition used pilot ID exclusions; an independent audit confirmed that its accepted 189-URL set did not overlap the three exact pilot URLs. The newer producer uses the exact pilot audio URLs explicitly.

A different text template does not block otherwise valid audio acquisition. Such candidates carry empty text block selectors and `publisher_text_pending_template_review`; the media worker may retain verified audio while text remains pending. Automatically checked pages are never labeled as manually read. Original audio verification, complete decoding, compressed derivatives, storage guards and later transcription belong to the separate media pipeline.

## Code and verification

`publisher_discovery.py` supports fresh collection, hash-verified cache reuse and offline replay. `publisher_discovery_project.py` produces compact public metadata and the exact historical set difference. `publisher_media_candidates.py` preserves the original strict text-template frame; `publisher_audio_candidates.py` implements independent audio/text admission. None of those lead producers downloads media.

`publisher_discovery_tests.py` checks all supported URL forms, deceptive hosts, non-HTTP URLs, playlist placeholders, malformed account routes, scoped link depth, separate audio leads and rejection of an outbound YouTube redirect before a second request. Private audits separately reparse saved pages and check source and candidate joins. Passing those checks establishes reproducibility and provenance within the tested scope, not video availability, speaker identity, transcript accuracy or the truth of a channeling claim.

Raw HTML and source manifests can be archived losslessly, then extracted back into RAM for replay. Their byte hashes, rather than filenames or a successful HTTP status alone, control admission. The root release preserves the compressed evidence archive and publishes only the allowlisted metadata.
