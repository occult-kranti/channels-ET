# Other publisher audio leads

Saved-page triage on 8 November 2026 found additional explicit audio links outside the OmNa collection. This is a future source queue. No audio endpoint was requested, no new audio was saved, and the frozen YouTube discovery and OmNa acquisition frames remain unchanged.

All 781 previously retrieved non-OmNa pages were rehashed against the crawl manifest. A local parser inspected explicit HTTP(S) anchors ending in common audio extensions; selected examples were read in context. This does not establish current file availability, full website coverage, recording duration, or audio/video equivalence.

| Publisher | Saved pages checked | Pages with explicit audio anchors | Distinct offered audio URLs | Those pages with any YouTube ID | Scope and next check |
| --- | ---: | ---: | ---: | ---: | --- |
| Crimson Circle | 341 | 128 | 284 | 21 | Includes channeling, welcome, Q&A and music supplements. Separate these before a recording pilot. |
| Kryon | 16 | 1 | 4 | 0 | Four narrated *Parables of Kryon* downloads; these are book readings with music and explanations. |
| Laarkmaa | 14 | 2 | 12 | 1 | Eleven archived interview links and one approximately ten-minute gathering sample. |
| Channeling Erik | 139 | 2 | 2 | 2 | Older externally hosted radio/interview files; content and availability remain unchecked. |
| Elan Interactions | 5 | 0 | 0 | 0 | Saved home page sends free-session access to YouTube; no direct audio anchor established in this scope. |

A YouTube ID appearing on the same page is an observed association only. It does not show that an MP3 is the audio of that video. URL counts are not recording counts or downloads. The complete source-bound ledger also records the ten other inspected publishers with no matching audio anchors in their saved pages.

## Concrete separately scoped pilots

- **Crimson Circle:** [Farewell to Shiva](https://www.crimsoncircle.com/library/clarity-series/farewell-to-shiva), dated 3 September 2005, explicitly offers [channel audio](https://cdn.crimsoncircle.com/library/7/74/188/audio/ch050903.mp3), separate welcome and Q&A files, a written summary and transcript controls. This saved page contains no observed YouTube ID. Its publisher identifies the speaker as Tobias; that is source attribution, not independently verified identity. This is the strongest direct channeling-audio lead in the inspected examples.
- **Kryon:** [Parables of Kryon](https://www.menus.kryon.com/parables-of-kryon) explicitly offers four MP3s beginning with [Parables-01.mp3](https://www.kryon.com/Audio/Parables-01.mp3). The page describes a 1996 production of 19 parables read by team members, children, actors and voice artists, with music and Lee Carroll explanations. Keep this book-narration genre separate from channeling sessions.
- **Laarkmaa:** [Audio from the Laarkmaa Heart Gathering](https://www.laarkmaa.com/post/2015/06/14/audio-from-the-laarkmaa-heart-gathering) offers an approximately ten-minute sample about ascension and karma. It is a sample, not the complete gathering. The linked audio uses HTTP; retain that literal evidence and test its current transport separately.

The saved [Kryon free-audio page](https://menus.kryon.com/freeaudio) also links **22 annual archive indexes**, covering 2002–2005 together and each year 2006–2026. Their `www.kryon.com` host was outside the earlier `menus.kryon.com` crawl scope. They are explicit first-party page leads, not confirmed audio files; none was fetched in this triage.

For Elan, the saved home page's “access all the Elan sessions, for free” anchor targets `https://youtube.com/@elaninteractions`. The saved robots file explicitly disallows `/audio-downloads.html` and several archive paths. Those pages were not fetched. This does not establish that no other publicly offered audio exists.

Some modern Crimson pages offer primary MP4 downloads and an MP3 music supplement. The inspected *ALT Brain, Neurodivergence, and Mastery* page is one such case: its MP3 is labelled “Merabh Music,” so it must not substitute for the full channeling. Paul Selig's saved WPR article contains an MP3 literal in embedded markup, but no matching explicit audio anchor; it is excluded from the offered-anchor totals.

## Audit bindings

The private portable ledger `non-omna-triage-02/triage.json` binds each offered URL to its exact saved source-page hash, archive member and same-page observed YouTube IDs. Its SHA-256 is `12c2986acce049e1676419227484f368fd7b6180f134e9ed2edcb40807b7d74b`. The prior triage edition preserves the executed local parser. Both editions record zero network requests and zero media downloads.

Source pages remain in the verified compressed archive `publisher-discovery-final.tar.gz`, SHA-256 `fffc32c3b9a522d0e8d924f8b8fd6d2282ffa74269a36edf83314da9c9f42052`, under `crawl/pages/`. The `discovery-receipts/persistence-manifest.json` maps original RAM paths to archive members and verifies the compact copied configs, run manifests, candidate frames and executed scripts. Any future acquisition needs its own source selection, validated pilot, resource budget and retention receipt.
