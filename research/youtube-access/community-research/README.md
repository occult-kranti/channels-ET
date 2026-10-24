# Community guidance and independent Brave review

Reviewed on **24 October 2026**. The supported Brave test ran, but YouTube access remains unresolved: its private NetLog records one `CONNECT www.youtube.com:443`, followed by `HTTP/1.1 403 Forbidden` and `server: envoy`. There was no origin page response, video, audio or caption acquisition. The response does not identify whether the underlying cause is a destination policy, proxy fault or another platform condition.

The independent local review passed **49/49 checks**. It reconciled all thirteen held Brave source/receipt files, the actual private package checksum, configured CA database, single-navigation guard, recorded control and target-bound NetLog events. It made no new YouTube requests, browser runs or media downloads. See [the machine-readable review](independent-brave-review.json) and [its retained code](review_sources.py).

## What was actually researched

Ten ordinary documentation/community request operations used the inherited proxy and certificate verification, with concurrency at most three. Seven succeeded. One GitHub search returned a validation error requiring `is:issue`; the one corrected query succeeded, and both receipts remain. The single Reddit request returned HTTP403 and a network-security block page. The single identifiable Simon Willison Substack feed request failed at proxy CONNECT403. Neither supplied a usable community article or solution, and neither was retried. This is a bounded source sample, not an exhaustive Reddit/Substack search.

Full responses remain private under `/workspace/channels-et-private/community-research/`. [The source register](source-register.json) contains ten curated evidence entries with URLs, dates, exact response hashes, short verified excerpts, reading depth and relevance. The GitHub issue bodies came from one search response; comments and linked fixes were not fetched.

| Source actually read | What it establishes for this case |
| --- | --- |
| [Official yt-dlp README](https://github.com/yt-dlp/yt-dlp#dependencies), dependencies | EJS and a supported JavaScript runtime provide full YouTube extractor support; ffmpeg/ffprobe handle media. These prerequisites are already installed. They do not establish a rejected network tunnel. |
| [Official yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ), Cloudflare-related HTTP403 section | Its explanation is scoped to that class of site error. It does not identify our pre-origin Envoy403. Its cookie/challenge/IP recipes were not used. |
| [Official Brave connection-security guidance](https://support.brave.com/hc/en-us/articles/360018185871-How-do-I-check-if-a-site-s-connection-is-secure) | Certificate trust is a distinct browser connection concern. The article's actual returned title was checked; a guessed URL slug was not treated as its title. |
| [Official Chromium error definitions](https://github.com/chromium/chromium/blob/main/net/base/net_error_list.h), `TUNNEL_CONNECTION_FAILED` | Defines the observed error as a failure to establish a tunnel through a proxy. It does not diagnose why the proxy returned403. The current-branch snapshot is not the installed engine revision. |
| [RFC9110 §9.3.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6) | “Any response other than a successful response indicates that the tunnel has not yet been formed.” |
| [Public yt-dlp issue8276](https://github.com/yt-dlp/yt-dlp/issues/8276), created4 October2023 | A reporter describes a Twitter proxy444 while other destinations work. It illustrates destination-specific observations, not a verified repair for this environment. |
| [Public yt-dlp issue11185](https://github.com/yt-dlp/yt-dlp/issues/11185), created7 October2024 | Its log combines a proxy503 during release-info retrieval with later successful YouTube format enumeration. These are different hosts/stages; its client-format observations do not repair our failed tunnel. |

Closed GitHub issues are not counted as verified fixes. A third returned report mixed Twitter/YouTube context and lacked a useful complete diagnostic, so it was excluded from repair evidence. Reddit and Substack acquisition failures are recorded as unavailable sources, not community consensus or negative search findings.

## Concrete tool decisions

The actual browser was the official [Brave v1.98.60 release](https://github.com/brave/brave-browser/releases/tag/v1.98.60), published `2026-10-21T09:09:05Z`. A fresh official release API response independently confirms the retained amd64 package's **153,190,012 bytes** and SHA256 `812a001d7631b5ab49e55dec6148a0bc2d459e9fc03106c286295ee03fd062fc`. DevTools recorded Chromium `156.0.8078.48`, revision `52db4b25c0aa3038e9a1c6021428b136cc3cb5f`.

The configured managed CA repaired Brave's allowed Pages HTTPS control with TLS verification enabled. Its isolated profile, package, raw NetLog and browser storage remain private. [The pinned launch code](../brave/probe.cjs), [allowlisted offline NetLog extractor](../brave/summarize-netlog.cjs) and [held source manifest](../brave/source-manifest.json) identify the exact implementation. `verification.json` means the diagnostic was checked; the watch receipt explicitly records `navigation_failed`.

Retain the existing official yt-dlp/EJS/Node/ffmpeg stack for a future successful-access pilot. Another downloader, browser switch, Shields change or extension is not supported as a repair for this observed failure stage. No extension, cookie export, challenge handling, alternate egress, mirror, remote acquisition runner or TLS-ignore configuration was installed or executed.

The next useful network action depends on a concrete supported platform/proxy repair. Supply the dated target authority, Envoy403 observation and private NetLog hash through the supported environment-diagnosis process; the present evidence does not reveal an internal cause or a working agent-side repair. After a meaningful repair, make one ordinary verified-TLS watch probe through the inherited proxy. If it succeeds, perform one bounded metadata/caption pilot before resuming the collection queue. The existing thousands of indexed jobs and a requested thousand-video target remain planned work; this diagnostic acquired **zero** YouTube videos.

The earlier paper, model experiments, nineteen-source cohort and separately dated primary-publisher supplement remain unchanged.
