# Round 15 review and correction log

Five AI-agent perspectives reviewed the initial 51-file snapshot (`3114aa23b2a6a5245c47035a52a50eaff41c4755315b633062ce4c045395ee60`). This was not human peer review. The original snapshot was not accepted for PR certification because packaging provenance and ASR partial reproducibility needed correction.

## Findings and dispositions

- **ASR (initial FAIL):** the partial was deleted before quarantine hashing. The code now preserves the current run’s partial. The German partial is an exact copy of the current final segment stream (`2083709c2aa68892e2d0cbd963bc7441578432f3736c33fda1597d1b20618b3a`) with a separate repair-script receipt; no retranscription is claimed. Legacy receipts are renamed and hash-bound separately. Nine legacy language-metadata records were backfilled from existing hash-bound transcripts without retranscription.
- **Acquisition:** candidate schemas, explicit hold and byte semantics were verified. `supplemental-candidates.json` and the model manifest are bound in the replacement snapshot. Language-excluded admitted bytes and quarantined ASR-output bytes are explicit.
- **Analysis:** all round-14 numerical findings remained fixed. The final verifier independently recomputes Q&A, TF-IDF, NMF, KMeans, network and sensitivity results, plus the new language and `producedCurrentArtifacts` checks: **121/121 passed**.
- **Rights:** private roots remain environment-based; code-edition snapshots record path-redaction transformations. Platform-terms and first-party LoRA notes are present. `producedCurrentArtifacts` distinguishes receipt-producing editions from provenance-only editions.
- **Release:** source-only fallback materializes SQLite and six PNGs, including a `--force` fresh-build mode. Twenty-four compressed chunk records (47 payloads) also reassemble and hash-verify CSV/JSON/SQLite/PNG exactly, avoiding whole-file API truncation. The canonical public package has **34 artifacts**, and staged HTTP verification passes **507 files**. The current main dashboard and its other validators are preserved; no workflow file is changed because the token lacks that scope.
- **Browser evidence:** metadata-only HARs (`desktop.har`, `mobile.har`) record 33 successful responses per viewport. Measured initial page loads are 3,912,374 bytes, and all measured page responses total 11,066,118 bytes. These are real captured metrics, not cache-dependent resource timing estimates.
- **Provenance:** the canonical public manifest is identical across app, integration, final public and staged trees (`3cd87df86025717b0be12f85d0e002f89a138ff7dce3ef713382ae5bb16544f8`). The replacement snapshot must be captured after the final corrective branch head is known, from one canonical integration tree.

## Final verification state

- Analysis: **121/121**
- Earlier full audio verification: **46/46**
- Current consistency verification: **73/73**, `fullHashRerun=false`
- Package: **34 artifacts**
- Staged site: **507 files**, acquisition routes and registries passed
- Browser: desktop and mobile interactions, downloads, zero console errors, zero failed requests, zero HTTP errors, no page-level horizontal overflow

A focused five-perspective re-review is required on the replacement snapshot before a draft PR is treated as reviewed. Preview is not publication; no merge or deployment is implied.
