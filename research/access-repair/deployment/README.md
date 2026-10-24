# Supplement deployment checks

The dated access-repair supplement adds public receipts to the existing static Pages release. `scripts/pages/verify_site.py` retains the original dashboard/download and 19-episode bookkeeping checks. When the supplement exists, it also fetches every published `access-repair-*` artifact and verifies its byte hash, dashboard source binding, primary-source metadata totals and separate Athina audio/ASR joins.

The retained browser evidence is limited to allowed Pages/RSS HTTPS controls and an unrelated local certificate rejection. The dated YouTube probe still records a proxy CONNECT 403 before origin TLS. Deployment verification inspects these receipts without repeating their source requests. Reported publisher-text word counts and ASR counts are metadata checks; raw audio and text stay outside Git/Pages. Paul Selig's publisher transcript remains a spiritual-mediumship comparison source.

The original publisher-audio and ASR summary hashes are checked against the earlier frozen live receipt at `research/deployment/final-live-verification.json`. The supplement's source ID must be separate from that original cohort. New local and hosted deployment receipts are saved in this directory, preserving the earlier deployment receipts.
