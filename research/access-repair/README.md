# Connection repair and independent primary publications

This work follows the 23 October acquisition release at `ad6b96e`. It does not
replace the frozen nineteen-podcast ledger or certify new YouTube downloads.

## What the new connection tests establish

The managed environment changed from runtime revision 5 to revision 6. A fresh
ordinary watch-page request at **2026-10-23 23:59:23 UTC**, using the inherited
proxy and normal certificate verification, still failed with
`Tunnel connection failed: 403 Forbidden`. This is before a YouTube TLS session
or page response. The current runtime reports unrestricted desired policy with
unknown enforcement; the startup policy also says unrestricted. These facts do
not establish that this destination is reachable.

A separate, single CONNECT-response diagnostic at **2026-10-24 00:00:43 UTC**
identified the responding server as **Envoy**, status **403**, a sixteen-byte
plain-text error body and no explanatory error/request-ID headers. No origin
TLS or media request was made by that diagnostic. Retained platform diagnostics
contained zero records. The evidence does not identify the underlying policy,
authentication or platform-protection cause.

See [the ordinary request](diagnostics/revision6-watch-probe.json),
[proxy response](diagnostics/revision6-proxy-response.json) and
[current runtime observation](diagnostics/runtime-revision6.json). These are two
proxy connection attempts for diagnosis, **zero video jobs**. The 3,357 queued
YouTube operations remain unattempted. Upgrading yt-dlp or importing a browser
certificate cannot cause a rejected CONNECT tunnel to become established.

## Safe reproduction and next network step

Offline evidence inspection makes no network request:

```sh
python3 research/access-repair/diagnose_connection.py
```

The probe command requires a current snapshot from
`cloud_environment.environment_status`, a concrete reason and a new dated
`diagnostics/*watch-probe.json` output. It refuses another ordinary request when
that same runtime revision already has a recorded proxy denial. Keep TLS
verification and the inherited proxy configuration enabled.

```sh
# Only after a meaningful supported configuration/platform access repair:
python3 research/access-repair/diagnose_connection.py --probe \
  --runtime-snapshot CURRENT_RUNTIME_JSON --reason 'EXACT_APPLIED_CHANGE' \
  --output research/access-repair/diagnostics/NEW_REVISION-watch-probe.json
```

A network/platform administrator needs to diagnose why the managed HTTP proxy
rejects `CONNECT www.youtube.com:443`, despite the desired unrestricted policy.
The two dated receipts above are a minimal reproducible support record. There
is no available tool here to restart or repair the proxy or obtain its internal
logs. Changing a configuration draft alone does not apply a runtime repair.
Once an ordinary watch request genuinely succeeds, use a bounded metadata pilot
before the existing resumable collection queue.

The applicable managed-environment
[runtime skill](skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md)
requires preserving inherited proxy settings and configured CA trust. Its
[networking reference](skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/references/networking.md)
states: “An explicit destination-policy denial requires the supported
configuration workflow; do not bypass the proxy to reach a blocked destination.”
No destination-policy cause is inferred solely from the opaque 403; no alternate
egress, mirrors, proxy rotation, remote Actions acquisition or TLS bypass is used.

## Browser repair and original sources

The [browser repair](browser/) reproduced Chromium's certificate error, then
imported only the configured public environment CA into an isolated, version-
guarded Chromium 154 profile. The live Pages dashboard and original publisher
RSS returned HTTP 200 over verified TLS 1.3. The Certificate Manager listed the
configured CA as trusted. An unrelated self-signed certificate was still rejected
in a separate loopback-only test context. Actual browser profiles, trust databases
and caches remain outside Git. This repairs browser trust for allowed sites; it
does not establish that the rejected YouTube tunnel is repaired.

The [primary-source work](primary-sources/) follows explicit source links already
in the Atlas to independently published original author text, a creator podcast
page/feed and an official transcript page/PDF. These are distinct publications;
their acquisition is not a YouTube download or proof of edition equivalence.
Full bodies/text stay private under
`/workspace/channels-et-raw/primary-publications/`; public metadata retains exact
source pointers, URLs, hashes, dates and extraction scope. Spiritual-guide
material remains a comparison source rather than a verified biological-ET claim.

## Material acquired during this follow-up

| Independent original source | Actual retained material | Scope |
|---|---|---|
| Daniel Scranton RSS | 15 authored items; 10,998 rendered-text words | Includes embedded promotions/footers; source-claimed entities, not verified audiovisual speech |
| Paul Selig publisher-linked PDF | Four pages; 2,577 extracted words | Spiritual Guides comparison; page/PDF scope is not established as an entire recorded session |
| Athina Król creator RSS episode | One audio file; 26,928,318 bytes; 1,682.991020 seconds | Exact creator episode URL/GUID/date bridge; no YouTube-edition equivalence |
| Athina audio ASR | One full decoded-audio pass; 259 segments; 3,394 machine-recognized words | Unverified English recognition; speakers and claimed-entity turns unsegmented |

[Athina's isolated acquisition/ASR cohort](athina/README.md) is separate from
the frozen nineteen Bashar-related recordings. Together they contain twenty
primary publisher audio files and twenty full-audio ASR passes; the manuscript
and prior statistical/model results are unchanged. Primary author-text word
counts are not added to ASR speech counts. Earlier discovery metadata
(`audio_acquired: false`) describes its pre-download stage, not this later ledger.

Only code and provenance metadata enter Git/Pages. Full recordings, primary
publisher PDFs/text and ASR bodies stay under `/workspace/channels-et-raw/`.
The remaining YouTube blocker requires a supported proxy/platform repair; no
new browser can establish a tunnel that the proxy itself rejects.
