# Supported collection tools and storage — checked 23 October 2026

The current YouTube failure is a **proxy CONNECT 403 before origin TLS**, recorded by the coordinator in `research/harvest/access/preflight-2026-10-23-revision5.json`. Changing extractors, JavaScript engines or user agents cannot repair that transport denial. This guide describes supported setup and a future healthy-access workflow; it does not claim a successful YouTube download.

Official documentation and selected implementation passages were actually retrieved through the inherited proxy with TLS verification enabled. The source register gives exact hashes, Git commits and reading depth. The installed analysis environment reports yt-dlp **2026.10.21**, youtube-transcript-api **1.2.4**, Node **24.19.0** and FFmpeg **7.1.5**; `yt-dlp-ejs` was absent when checked. No package installation or YouTube request was performed for this documentation audit.

## Setup that matters after permitted access works

Current full YouTube support needs **yt-dlp-ejs plus a supported JavaScript runtime**. Official EJS documentation requires Deno >=2.3 or Node >=22; Deno is recommended and the only default-enabled runtime. Existing Node 24 can be selected explicitly with `--js-runtimes node`. EJS must match the chosen yt-dlp version: the inspected 2026.10.21 PyPI default extra pins **yt-dlp-ejs==0.8.0**. Runtime requirements differ from the higher requirements for building EJS from source.

For a separate, pinned collection environment, the supported installation form is:

```sh
python -m pip install 'yt-dlp[default]==2026.10.21'
```

Install through the configured package/proxy/CA path; preserve inherited TLS trust. Freeze package versions and hashes after a successful pilot. The project recommends nightly builds for ordinary users because websites change quickly; a research run should pin its tested release. A later official release/nightly can be a bounded diagnosis of an origin extraction regression, never a response to this proxy denial. FFmpeg/ffprobe must be actual executables, not the unrelated Python package named `ffmpeg`.

With the compatible EJS package installed, `--remote-components` is unnecessary. Keep remote components disabled for a frozen run rather than fetching unrecorded scripts. Do not substitute mirrors, proxy rotation, cookie extraction, browser-authentication workarounds or GitHub Actions for a denied local destination.

## Keep listing, captions and audio success separate

1. Enumerate metadata first. `--flat-playlist` avoids full per-item extraction but can omit metadata; a returned listing is not a complete worldwide channel history. Preserve unavailable slots and raw cursor positions. Reconcile stable IDs independently of titles, relative ages or playlist order. Scheduled/live, private/deleted and inaccessible entries need explicit states.
2. Inventory `subtitles` and `automatic_captions` from the permitted metadata response before selecting tracks. Record language, manual/automatic origin, translation status, advertised format, selection reason and failure per track. A platform's manual flag is not an accuracy audit.
3. Fetch manual and automatic tracks **separately**, with separate filenames/directories and ledgers. Pinned `YoutubeDL.process_subtitles` gives manual subtitles precedence when both types share a language; `--write-subs --write-auto-subs` in one call does not preserve both versions. One requested format per language is not every offered format.
4. Use `--skip-download` for caption-only work, `--sub-format 'vtt/best'`, and an explicit language selection such as `--sub-langs 'en.*,-live_chat'`. Selecting `all` can include many automatic translations and live-chat data; do not silently call those independent original-language transcripts. An English pilot is not multilingual coverage.
5. Retain full raw info JSON only locally where appropriate: it can include transient delivery URLs. Public records should carry stable source URLs, hashes, provenance and selected metadata, not expiring signed CDN query values.

Caption commands are illustrative and **not executed against YouTube**:

```sh
yt-dlp --ignore-config --no-remote-components --js-runtimes node \
  --skip-download --write-subs --no-write-auto-subs \
  --sub-langs 'en.*,-live_chat' --sub-format 'vtt/best' \
  -P /workspace/channels-et-raw/captions/manual \
  -o '%(id)s.%(ext)s' 'PERMITTED_PUBLIC_SOURCE_URL'

yt-dlp --ignore-config --no-remote-components --js-runtimes node \
  --skip-download --no-write-subs --write-auto-subs \
  --sub-langs 'en.*,-live_chat' --sub-format 'vtt/best' \
  -P /workspace/channels-et-raw/captions/automatic \
  -o '%(id)s.%(ext)s' 'PERMITTED_PUBLIC_SOURCE_URL'
```

## Resume, archive and completeness

`--continue` and `.part` files are defaults. Preserve stable ID-based paths. `--force-overwrites` includes `--no-continue`, so it defeats this resume strategy. The download archive tracks successful video/media downloads; metadata/caption-only scans need their own success ledger. In the inspected code, simulated/skip-download operations write archive entries only when forced. Do not use `--force-write-archive` to make a metadata scan look like acquired media, or share that scan's archive with media acquisition.

`-N/--concurrent-fragments` controls DASH/HLS fragments **within one download**, not the number of videos or channel workers. Start with one fragment stream and two bounded audio jobs. Concurrency multiplies requests, throughput and temporary disk use; it does not solve access controls. Use finite retries, timeouts, per-request/subtitle sleeps and a circuit breaker. After a 429 or bot challenge, preserve the failure and stop/back off rather than escalating concurrency.

For research audio, use `--abort-on-unavailable-fragments`: the default can skip unavailable fragments, which is unsuitable for a claim of complete source speech. Avoid `--ignore-errors`; its help explicitly says postprocessing failures can still be considered success. A zero subprocess exit alone is not an audio success criterion.

An access-approved media job can combine ID-based output, an audio format, `--download-archive`, `--continue --part`, a rate limit, `-N 1`, finite retries and `--max-filesize`. Preserve partials on interruption. Promote a final artifact only after observed size, byte hash and ffprobe validation, with supplied expected size/duration checked where available. Do not assign a new corpus row just because a process started.

## Resource planning and hard bounds

Use `bytes ≈ seconds × bits_per_second / 8` for planning only. One hour at 160 kbit/s is about **72 MB**; at 64 kbit/s, **28.8 MB**. Mono 16 kHz signed 16-bit PCM is **115.2 MB/hour**, excluding headers. Compressed originals, decoded temporary audio, model caches, partials and outputs occupy separate space. Measure actual files and filesystem free space; do not infer the final file size from a duration or bitrate field.

`--max-filesize` is not a whole-workspace quota. In the inspected HTTP downloader its known-size check depends on `Content-Length`; fragmented streams, conversion, logs and unknown sizes require external monitoring and final validation. Keep the coordinator's raw-tree **20 GiB** budget, **6 GiB** free reserve and **256 MiB/file** cap; acquire the shared `/workspace/channels-et-raw/.collection-worker.lock` before any writer process. Publisher collection uses two threads inside that exclusive lock. YouTube writers must use the same lock; multiple independent processes must not each assume the full budget is available.

Actual independent publisher-podcast files are handled by `research/harvest/publisher_sources/`, outside the denied YouTube route. Their raw audio stays in `/workspace/channels-et-raw/publisher-audio/`; public summaries distinguish exact original-index edges from unresolved edition equivalence. A publisher RSS feed is a separate source, not evidence that a YouTube URL was downloaded. Public availability does not grant an open redistribution license.

## Failure diagnosis

| Observation | Supported interpretation/action |
|---|---|
| Proxy CONNECT 403 before TLS | Origin connection was not established. Retain request/time/policy observation and stop that destination; use supported environment diagnosis. JS/EJS changes do not address it. |
| HTTP 403 after a connection | An HTTP response was received; distinguish origin/CDN/reverse-proxy evidence using the actual response/redirect context. The number alone does not identify the cause. |
| No supported JS runtime / signature or challenge-solving warning | If ordinary access is healthy, check the matched EJS package, explicit runtime selection and official release diagnostics. This is an extraction-layer issue, distinct from transport denial. |
| Sign-in/bot challenge, CAPTCHA, 429 | Retain an access-restriction/rate state and stop/back off. This guide does not adopt FAQ cookie/IP-changing recipes. |
| No offered subtitles or unavailable track | Record caption absence/unavailability for that source; do not treat it as an empty spoken answer or a global connectivity failure. |
| Exit zero but missing/oversize/truncated/invalid audio | Failed artifact validation; preserve diagnostics/partial state and do not count completed material. |

## GitHub is the source and results repository

Keep code, lockfiles, manifests, source edges, compact derived tables, scientific figures and the working paper in Git. Keep raw audio/video, full third-party transcript bodies, model weights and caches outside it. Public dashboards should use bounded derivatives and manifests; they should not silently rehost acquired media.

The current official GitHub pages report:

- Regular Git warns for files >50 MiB and rejects files >100 MiB; browser uploads are limited to 25 MiB. Separate repository guidance recommends generated files in object storage. Its 10 GB on-disk recommendation is not permission to fill a code repository with media; the large-file guide gives more conservative ideal/strongly recommended sizes.
- LFS stores pointer files in Git and actual objects separately. Per-file limits are 2 GB on Free/Pro, 4 GB on Team and 5 GB on Enterprise Cloud. The checked billing article gives Free/Pro 10 GiB storage and 10 GiB bandwidth, with budget-dependent blocking or billing. Every changed binary version consumes storage. **Git LFS cannot be used with GitHub Pages.**
- The releases-specific article gives up to 1,000 assets per release and **each under 2 GiB**, with no stated total release/bandwidth limit. The generic large-file page also mentions plan-dependent limits; use the stricter 2 GiB bound if using releases. Releases are not an automatic rights basis for distributing third-party recordings.
- GitHub Pages limits a published site to **1 GB**, with a **100 GB/month soft bandwidth limit** and a ten-minute deployment timeout. The ten-builds/hour soft limit does not apply to custom Actions publishing workflows. Prefer compact results pages, not a media archive.

These are documentation observations, not confirmation of this account's paid plan, storage allowance, redistribution rights or current usage.
