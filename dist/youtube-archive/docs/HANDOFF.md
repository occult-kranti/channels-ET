# Collection handoff · 8 November 2026

Continue in `occult-kranti/channels-ET`. The new operational page is
[`dist/youtube-archive/`](https://occult-kranti.github.io/channels-ET/dist/youtube-archive/).
Its release manifest binds each producer edition; the old analyses retain their
own source frames and manifests.

## Accepted index and collection state

The repaired inventory contains **2,812 observed video IDs and 297 reconciled
account references**, including unresolved identities and excluded accounts.
The preceding retained frame had 2,060 IDs. The difference is 743 new HTML/sitemap
IDs plus nine IDs observed in first-party HTTP redirect locations; those
redirects were not followed to YouTube. All 28 screenshot subscriptions remain
represented, with 12 included and 16 excluded. There are 878 historical
watch-page uploader bindings and 30 historical caption-analysis references.

Sixteen declared publisher contexts produced 1,239 attempted page requests,
1,215 retained documents and 1,890 distinct HTML/sitemap-linked YouTube IDs.
The declared pending queue is empty, while **24 failed or held requests remain
explicit**. This is neither a complete-site claim nor completed YouTube
pagination. Source paths, depth rules, host boundaries and each failure are
listed in [DISCOVERY.md](DISCOVERY.md).

The ordinary YouTube probe remains **CONNECT 403 before origin**, independently
checked against retained headers and two successful GitHub controls. The final
YouTube collector has **zero new tab, metadata, media and caption operations**;
held jobs are not failed origin requests or deleted/private videos. Portable
runner tests include real yt-dlp processing against local HTTP fixtures, which
is separately labeled and does not prove YouTube extraction works here.

The queue preserves the no-count-cap policy, Bashar-only 300-second minimum,
unknown-duration probes and user exclusions. Item relevance and actual uploader
identity remain separate from duration screening. See [COLLECTION.md](COLLECTION.md)
for the supported runtime, commands, atomic jobs, strict decode validation,
caption selection, shared-error circuit breakers and resumption states.

## Private retention and reproducibility

The private task root is `/workspace/channels-et-private/youtube-archive-2026-11/`.

| Location | Purpose |
|---|---|
| `accepted/inventory`, `accepted/collection-final`, `accepted/discovery` | Frozen public producer editions and exact copies |
| `accepted/publisher-text` | 149 recovered publisher-written editions, their private bodies and locators |
| `accepted/literature` | Current yt-dlp / GitHub / Stack Overflow source review |
| `reconciliation-02` | Fresh verification of 493 selected text artifacts and 341 old selected media paths |
| `collector-03` | Resumable YouTube SQLite queue with no invented acquisition attempts |
| `publisher-media-*` | Immutable actual publisher-audio runs, original/derivative checks and request receipts |
| `publisher-discovery-final.tar.gz` | Verified compressed source-page archive |
| `discovery-receipts` | Smaller candidate/configuration/run receipts and restoration path notes |

The compressed crawl preserves **1,215 source pages** and 1,220 verified members:
634,500,021 uncompressed bytes in 198,942,326 compressed bytes. Its SHA-256 is
`fffc32c3b9a522d0e8d924f8b8fd6d2282ffa74269a36edf83314da9c9f42052`.
`archive_discovery.py` verifies every source binding, then decompresses and
rehashes every stored member before accepting the archive. RAM working editions
are not treated as durable external backups.

The completed finite publisher frame contains **192 audio files / 44.55 hours / 942,245,703 bytes**, with zero current pending jobs and all 32 earlier resource holds resolved. The associated written-text union contains **192 editions / 189,717 words**; exact page joins do not imply word alignment.

The first three new publisher recordings retain original MP3s. Later runs retain
full-duration lossy 48 kbps Opus derivatives, with original and derivative hashes,
strict full-decode receipts and source-page bindings. Only newly staged originals
are removed after verified derivatives exist; older source artifacts remain
untouched. Resource-limited jobs remain explicit. A fresh continuation may use
the separately documented 1.5 GiB reserve after measured capacity review; older
runs keep their recorded 2 GiB profile. The actual final run summaries govern
completed and deferred counts, rather than candidate counts.

The 149-message recovery supplement contains **150,251 words**, six complete AI
readings and 143 automatic extractions. It preserves all 91 earlier recovered
body hashes and separates 17 publisher notices/marketing endings. Three inspected
footers named an entity different from the message's closing; these footers are
not entity-identity evidence. This is publisher text, not ASR or an aligned
transcript. Join it to audio only by exact record ID, page URL and page SHA.

GitHub/Pages contains source code, metadata, manifests and bounded research
annotations. Full audio, source HTML and written bodies remain private. There
is no asserted Google Drive upload or permanent ChatGPT-account backup.

## Analysis and verification boundaries

The old 493-source / 1,411,446-word analytical frame is unchanged. Newly collected
publisher files are not silently added to that fit, question bank or graph.
Future analysis must admit and deduplicate a new source edition explicitly;
matching page titles, embedded video IDs or claimed entities are insufficient.

Run the metadata release gate with:

```sh
python3 research/youtube-archive/verify_release.py --site /workspace/channels-ET
python3 -m unittest discover -s research/youtube-archive -p 'test_*.py'
python3 research/youtube-archive/publisher_discovery_tests.py
```

The release gate checks exact allowlists, hashes, source/collector edition joins,
ID inclusion and uploader-only asset credit. Source-page/body/audio reconstruction
and independent browser checks have separate private receipts. [REVIEW.md](REVIEW.md)
states actual executed checks and remaining limits. AI-agent review is not human
peer review. `research/batch-media/audio.py` remains unchanged.
