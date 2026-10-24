# Verified Chromium proxy-CA trust repair

On 2026-10-24, the installed Chromium 154.0.8037.57 rejected live GitHub Pages with `ERR_CERT_AUTHORITY_INVALID`. Importing the **configured public environment proxy CA** into a dedicated browser profile repaired HTTPS trust. The browser subsequently loaded the published acquisition dashboard and an independent publisher RSS feed with HTTP 200, TLS 1.3, and certificate verification enabled. An unrelated self-signed certificate was still rejected.

This repairs the browser's certificate trust. It does **not** repair YouTube's separate proxy `CONNECT 403` denial before origin TLS. These scripts made zero YouTube requests. See the parent access-repair report for the fresh revision-6 destination probe.

## Scope and evidence

- Private profile: `/workspace/channels-et-browser-profile`, outside the repository. Its trust database, rollback copy, cache, local fixture key/certificate, cookies and storage must remain private and out of Git. No remote page bodies were saved to this research folder.
- Trusted CA: the existing `NODE_EXTRA_CA_CERTS` file `/usr/local/share/ca-certificates/environment-proxy-ca.crt`, SHA-256 `c71b4d1e9d7775c538c688ab10cea9ce417d7312e89838f9d15ff73256cd7fc3`. No private CA key is used.
- Mechanism: Chromium's built-in per-profile `ServerCertificate` database, schema version 1. The headless native import button requires an unavailable OS file dialog. `profile_ca.py` therefore provisions the same trusted-CA record while the browser is closed, guarded by the exact browser version, schema, CA fingerprint and empty-or-identical contents. Chromium's own Certificate Manager then confirms the entry under **Installed by you / Trusted Certificates**.
- Existing system trust, legacy NSS stores, HOME and the inherited proxy environment are unchanged. No extension, replacement browser, TLS-ignore flag or SPKI exception was installed.
- `baseline-receipt.json` records the initial certificate rejection. `verification-receipt.json` records the successful browser controls and negative certificate control. `trust-store-receipt.json` records repeatable, read-back verification of the sole CA row and database integrity.

The live controls use the inherited proxy with `ignoreHTTPSErrors: false`. The optional local negative control uses a **separate** context with the same CA profile, an explicit `127.0.0.1` proxy bypass, and a request guard blocking every other host. It never navigates externally. Playwright otherwise forces loopback through the proxy; the first local attempt was therefore inconclusive (`ERR_TUNNEL_CONNECTION_FAILED`). After the authorized local-only correction, the unrelated certificate produced `ERR_CERT_AUTHORITY_INVALID` and zero HTTP requests reached the fixture.

The existing cloud Chromium launch needs `--no-sandbox`; this is separate from TLS verification. This profile is intended for trusted research controls in the managed container. The repair establishes neither a hardened browser sandbox nor access to denied destinations.

## Reproduce on this pinned environment

Existing dependencies are `/usr/bin/chromium`, Python 3, OpenSSL and the preinstalled Playwright package at `/opt/codex/cua_node/lib/node_modules/playwright`. No package installation was needed.

From `/workspace/channels-ET`:

```bash
node research/access-repair/browser/initialize-profile.cjs
python research/access-repair/browser/profile_ca.py
python research/access-repair/browser/profile_ca.py --check
node research/access-repair/browser/verify-browser.cjs verify
```

Close this dedicated browser before the CA helper runs. Repeating the import is an idempotent readback when the pinned certificate is already present. Unexpected versions, schema, fingerprints or additional certificate rows abort rather than overwrite them. A new browser version or rotated CA needs source/schema and public-certificate review first. The original empty DB is retained privately as `Default/ServerCertificate.before-configured-ca`; rollback must also occur with the browser closed.

`baseline` mode is an initial diagnostic for an unconfigured profile; it expects a certificate error. Do not use it as a readiness test after the CA is installed. `verify --local-control-only` retries only the local negative control using an already saved positive live-control receipt, preserving the earlier live check time.

These commands configure this browser profile and validate current-instance behavior. They do not modify cloud network policy or publish an environment snapshot. Reusing the profile in future browser automation requires `launchPersistentContext` with this exact profile, the inherited proxy, and certificate verification enabled.

## Official schema references

The implementation is pinned to Chromium's exact installed source tag, rather than assuming an NSS database is the active profile store:

- [Server certificate database implementation](https://chromium.googlesource.com/chromium/src/+/154.0.8037.57/components/server_certificate_database/server_certificate_database.cc)
- [Trust metadata protobuf](https://chromium.googlesource.com/chromium/src/+/154.0.8037.57/components/server_certificate_database/server_certificate_database.proto)
- [Certificate Manager navigation](https://chromium.googlesource.com/chromium/src/+/154.0.8037.57/chrome/browser/resources/certificate_manager/navigation.ts)

The stored protobuf bytes `0a020803` encode outer `trust` field 1, inner `trust_type` field 1, enum `TRUSTED = 3`, with no extra constraints. The browser-created `meta` table is preserved. This narrow offline provisioning technique is version-specific; it is not a general-purpose certificate-store editor.

The receipts' `youtubeRequests: 0` describes explicit YouTube navigation or
collection operations requested by this control script. It is not an instrumented
count of every possible page subresource request. Live checks target only the
Pages site and the publisher RSS feed; no YouTube access test is inferred.
