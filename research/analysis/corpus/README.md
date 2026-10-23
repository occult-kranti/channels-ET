# Acquisition evidence release — 2026-10-23

Collection is complete. Interpretation, dashboard checks and publication are separate review steps.

- Watch metadata: 925 unique IDs attempted; 878 successful metadata records; 877 positive durations; one zero-duration item; 47 unavailable records. The final record data are maintained once, at `../inputs/fresh_metadata.json`; this folder does not duplicate the full snapshot.
- Caption pilot: 36 selected records, 34 caption downloads, 30 English/en-US documents eligible for the balanced analysis. One extra Scranton document is reserved for a separate concordance/window sensitivity case. Two Japanese and one Czech caption document remain outside the monolingual comparison.
- Full caption text, caption segments, original web-message text, media and credentials are absent from this release. The manifests preserve source URLs, caption-language and ASR flags, access failures, artifact hashes and derived numeric results.

The user authorized research, analysis, code maintenance and repository publication. This authorization does not convert third-party captions into public-domain material or authorize redistribution of their full text. Raw captions remain outside the Git checkout and are used only for local analysis. A current public watch-page response is evidence about available metadata, not a guarantee of playback access or of rights to the audiovisual work.

No purchases, subscriptions, logins, paywall access, proxies, access-control bypasses or private communications were used. A members-only caption attempt and a disabled-caption attempt remain failures. Metadata errors were not retried. The capture protocol would stop on HTTP 403/429; no such block occurred.

`acquire_youtube.py` is the portable maintenance CLI. Caption mode requires `acquisition-requirements.txt` and an external raw directory outside Git. Metadata mode uses only Python's standard library. `capture_metadata_2026-10-23.py` preserves the exact historical batch code; it includes the original workspace input paths and is a provenance snapshot, not the recommended portable command. `collection_methods.md` explains scope, denominators and exclusions. `release_manifest.json` supplies byte hashes and the canonical records hash for comparison to the shared input snapshot.

Reacquisition may change titles, availability, counts and hashes. Keep new dated snapshots and retain the failure ledger. Do not turn available-duration means into whole-channel averages or indexed-date counts into posting rates.

The Scranton concordance and window tables are numeric, single-video diagnostics. The caption boundary was matched to an author-published closing, not verified by listening to audio. They show why whole-upload caption analysis needs a content-window sensitivity check; they do not validate every caption or isolate a claimed entity's voice.
