# Expansion panel — acquisition round 1

Reviewer: model-agent acquisition perspective, not human peer review. Baseline:
GitHub main `1d6eb36`, frozen analysis SHA-256
`f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc`.

1. **Access blocker.** The current watch probe (`acquisition/preflight-initial.json`)
   failed with `Tunnel connection failed: 403 Forbidden`. No new YouTube metadata,
   search result or caption was acquired. Required action: supported runtime domain
   access, then one renewed probe after the state changes. Client substitution is
   not an access workaround. Acceptance: successful ordinary request plus preserved
   timestamp/status/hash; otherwise keep analyses explicitly historical.
2. **Frame ambiguity.** The 106 discovery people include partial names, lineages,
   historical and non-ET context. Decision implemented: `identity-map.json` retains
   explicit inherited edges and unresolved identities. Acceptance: no counts of
   unique humans/official ET channels derived from route or candidate counts.
3. **Search recall.** Prior discovery was heterogeneous. Decision implemented:
   590 auditable exact-name/entity query jobs and all 157 account-route jobs.
   These remain planned. Acceptance: actual collection reports attempted operations,
   duplicates, retrieved IDs and failures, not just a query-plan length.
4. **Caption selection.** The old 36-record pilot was purposeful and yielded 30
   balanced English documents. Decision implemented: retain that provenance and
   queue broader per-publisher candidates (215 total); do not claim random sampling
   or language/format matching. Acceptance: characterize achieved strata after
   retrieval and retain the historical/follow-up selection distinction.
5. **Reproducibility and rights.** Decision implemented: pinned third-party tools,
   explicit caps, no retries on blocks, external versioned raw-caption storage,
   preservation of all earlier runs and text hashes. Acceptance: safety checks,
   dependency check, failure-state visibility and no full captions in public exports.

Artifact for the next loop: executable `acquisition/collect.py`, generated frame/
query plan/identity map, pinned software, preflight receipt, and the revised research
output built from available evidence. Round 2 must inspect that changed output and
resolve any claim of newly acquired data or validated speech/Q&A unsupported here.
