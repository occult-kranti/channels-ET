# Official Brave diagnostic, 24 October 2026

The requested official Brave test ran through the **same inherited proxy**, with TLS certificate verification enabled. Brave successfully rendered the live Pages acquisition dashboard after the configured public proxy CA was added to its dedicated private profile. The single subsequent YouTube navigation failed.

At `2026-10-24T00:32:17.511Z`, one ordinary navigation targeted `https://www.youtube.com/watch?v=fZmY4xS_qXE`. Brave reported `net::ERR_TUNNEL_CONNECTION_FAILED`. Its network log recorded exactly one target-bound `CONNECT www.youtube.com:443` and **HTTP/1.1 403 Forbidden**, `server: envoy`. No origin page response, video, audio or caption was obtained. The 403's underlying reason remains unknown: the response alone does not distinguish a policy refusal from an internal proxy fault. This test does not establish that YouTube itself denied access.

## Verified runtime and trust

- Official upstream release: [brave/brave-browser v1.98.60](https://github.com/brave/brave-browser/releases/tag/v1.98.60), published 21 October 2026 according to the parent-verified GitHub release metadata.
- Official Linux amd64 DEB: 153,190,012 bytes; SHA-256 `812a001d7631b5ab49e55dec6148a0bc2d459e9fc03106c286295ee03fd062fc`, matching the upstream asset digest supplied by the parent release check.
- Actual executable version: `Brave Browser 156.1.98.60 unknown`. DevTools reports Chromium `156.0.8078.48`, revision `52db4b25c0aa3038e9a1c6021428b136cc3cb5f`. This was the actual official Brave executable in headless mode, not a spoofed user agent.
- The package was extracted to `/workspace/channels-et-brave-runtime`, without a system install or package scripts. `ldd` reported no missing dynamic libraries.
- The fresh private profile first reproduced `ERR_CERT_AUTHORITY_INVALID` on the allowed HTTPS control. The exact Chromium engine's official schema/protobuf was checked before provisioning the **existing configured public CA** into its per-profile `ServerCertificate` store. The store has one trusted row and passes integrity checks; system trust and the old Chromium profile were not changed.
- Brave's own Certificate Manager then listed the CA under Trusted Certificates. The live Pages control returned HTTP 200, TLS 1.3, issuer `openai.com`, with `ignoreHTTPSErrors: false`, and rendered the actual acquisition dashboard.
- The inherited proxy environment, CA verification and routing were preserved. No proxy website, VPN, alternate external egress, SPKI exception, TLS-ignore flag, extension or replacement client chain was used.

The runtime, private profile, rollback certificate DB and full NetLog stay **outside Git**. The full NetLog can contain browser metadata and must not be published. `summarize-netlog.cjs` exports only the exact target authority, same-source-ID tunnel events, HTTP status and server header. No full page body or browser cache is published. As with the existing cloud Chromium harness, this container launch uses `--no-sandbox`; TLS verification remains enabled.

## Reusable source and receipts

`prepare-runtime.py` downloads only the official pinned asset, verifies its size/checksum before extraction, and records actual version/dependency checks. `profile_ca.py` aborts on unexpected engine/build/schema/CA fingerprint or additional certificate rows. `probe.cjs` uses the private profile, instruments page requests and failures, and requires the successful allowed control before watch mode. A private exclusive marker prevents a second watch navigation. Do not delete that guard or rerun the source request without a new authorized scope or meaningful access change.

The sequence already executed was:

```bash
python research/youtube-access/brave/prepare-runtime.py
node research/youtube-access/brave/probe.cjs initialize
node research/youtube-access/brave/probe.cjs control
# Initial control failed on certificate trust, as retained in baseline-control-receipt.json.
python research/youtube-access/brave/profile_ca.py
node research/youtube-access/brave/probe.cjs control
# The allowed control passed before the one source navigation below.
node research/youtube-access/brave/probe.cjs watch
```

The offline `node research/youtube-access/brave/summarize-netlog.cjs` command can re-extract safe evidence without another network request. `python research/youtube-access/brave/profile_ca.py --check` checks the closed profile's CA store without changing it. `watch` exits normally when diagnostic recording completes; that exit status is not a claim of source access. The watch receipt explicitly records `navigation_failed`.

Receipts distinguish package verification, the initial trust failure, repaired allowed-control success, and the unsuccessful source navigation. Runtime-policy observation was revision 6, configured unrestricted, actor observation unknown; it does not establish destination reachability. The deployed dashboard, historical source cohorts, manuscripts and model results were not changed by this diagnostic.
