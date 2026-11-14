# Acquisition-2026-11 handoff

## Current branch and release state

Active integration branch: `research/acquisition-2026-11-expanded`, created from current `main` at `bf6a40f01fd693da00ecce6a6752273985df95a3`. The older task worktree and October baseline are historical evidence, not a reason to overwrite the newer Living research dashboard on `main`.

Round 14 is complete across acquisition/provenance, rights/ethics, ASR methods, analysis methods and dashboard/release. Its findings drove the corrected candidate, quarantine, statistical, account-reconciliation, documentation and CI work in this folder. Round 15 must certify a fresh corrected snapshot before a pull request is treated as reviewed. Preview is not publication; merge to `main` and Pages deployment require separate explicit review/confirmation.

## Actual terminal accounting

| State | Count | Meaning |
|---|---:|---|
| Observed videos | 2,840 | Observed public inventory, not a full-channel census |
| Observed accounts | 302 | Named account references; 99 currently have zero observed videos |
| Default selected | 733 | October baseline; exactly 100 Bashar-associated across all accounts |
| Actual audio | 35 | 1,321,921,399 bytes and 73,899.368 seconds |
| Completed English ASR | 34 | 146,605 words, 13,169 segments, 19.472 hours |
| Analyzed | 34 | Hash-bound documents in the public analysis registry |
| Under-300 exclusions | 7 | Measured durations below 300 seconds; admitted bytes zero, quarantined bytes retained separately |
| Language exclusions | 1 | Pavlina Klemm German audio; unsupported by tiny.en |
| Route-limit holds | 1 | `8WHAw-wIuQg`; no media, ASR or analysis attempted |
| Pending outside the 43 candidates | 2,797 | Neither failed nor completed; no progress inferred |

Candidate/reference selection labels agree for all 43 IDs, including the duplicate `ctgvKZcIWIg`. The acquisition ledger contains all 43 terminal records, including the explicit route-limit hold.

## Analysis and review results

- 572 literal question units and 781 question sentences.
- 69 fresh AI-agent verdicts: 7 confirm, 49 reclassify, 13 boundary_error. These are not human annotations; `humanValidated=false` everywhere.
- 473 token-keyed families: 17 cross-video, three same-video-only recurrence, 20 repeated anywhere and 63 family-less stopword-only rows.
- NMF stability 0.7438; all base/stability runs converged before 1,200 iterations.
- Maximum KMeans silhouette 0.0070. Each ARI mean uses nine non-base comparisons and excludes the trivial ARI=1 self-comparison.
- Document cosine mean/max 0.0495/0.1285. Maximum proper-name share 0.62%.
- Answer orientation: 358 descriptive/explanatory, 129 `unclassified_default`, 61 conditional/hedged, 12 process/practice, six timing-specific and six not captured.
- 119/119 analysis checks and 46/46 audio checks pass. The verifier recomputes every Q&A unit and all headline corpus/sensitivity statistics from the private segment index.
- `verification-reuse.json` adds 73/73 current consistency checks with `fullHashRerun=false`: earlier full audio hashes still match acquisition/ledger receipts and current ffprobe durations. It is not presented as a new full hash run.
- Nine legacy language-metadata records were backfilled from existing hash-bound ASR text without retranscription. The German partial is now an exact copy of the current final segment stream with a separate repair-script hash; future quarantine code preserves the current run’s partial. Legacy receipts are renamed and hash-bound separately.

Do not turn lexical recurrence into semantic equivalence, repost evidence, entity agreement or truth. Uploader, practitioner, claimed entity, original session and speaker remain separate units.

## Reproduction contract

Private locations are supplied through `CHANNELS_ET_RAW_ROOT`, `CHANNELS_ET_MODEL_CACHE` and `CHANNELS_ET_AUDIT_ROOT`. Do not commit their absolute values.

1. `transcribe_youtube.py`: resumable pinned tiny.en ASR. Reuse requires valid audio, pinned settings, allowlisted code edition and all output hashes inside the per-video lock. Summary updates are locked and atomic; nonterminal results cannot downgrade terminal records, and terminal-to-terminal changes need explicit confirmation.
2. `analysis/build.py`: gates on all 43 candidates reaching completed, excluded or held states, then writes a new candidate-bound gate only after all outputs succeed.
3. `analysis/make_review.py`: binds the 69 verdicts to current question hashes and metadata. `analysis/apply_review.py` adds reviewed classes without exposing answer bodies.
4. `analysis/verify.py`: validates raw artifacts and independently recomputes extraction, statistics and synthesis bindings. A nonzero failure count blocks packaging.
5. `verify_audio.py`: validates all 35 audio files and the seven under-300 plus one language exclusions. `reuse_verified_audio.py` provides the faster current-consistency path when explicitly allowed with `CHANNELS_ET_REVERIFY_AUDIO=0`; it requires the earlier full receipt and never claims a new full hash.
6. `build_reference.py`: joins actual audio/ASR/analysis states and computes account-membership reconciliation. It never runs when private inputs are absent in CI.
7. `materialize_public_artifacts.py`: builds a missing public SQLite from public CSV/JSON and renders missing PNGs from SVG. It does not need private media or transcript bodies.
8. `package_acquisition.py`: requires the exact candidate hash and passing analysis receipt, strips workstation paths, and writes the public workbench manifest.

`stage_site.py` runs raw verification only when the authorized roots are mounted. Otherwise it validates the committed passing receipts and materializes/packages only public derivatives; it never resets actual states to pending.

## Review history

### Historical 13-source pilot

`reviews/pilot-13-baseline/` preserves the 95-check pilot receipt and explicitly marks it as not certifying the expanded corpus.

### Round 14

`reviews/round14/` contains five AI reviews and the frozen snapshot. Main corrections:

- candidate schema/selection/hold/quarantine-byte normalization;
- four-file German quarantine with settings/code binding and legacy receipt separation;
- portable private roots, sanitized public summaries and path-redacted code-edition snapshots;
- corrected 0.62% name-share maximum, non-self ARI, `unclassified_default`, WH-stopword symmetry, full risk totals and independent numerical recomputation;
- unattributed/multi-account presentation reconciliation;
- portable package root, required static assets, candidate-hash gates and expanded media/path checks;
- actual desktop/mobile navigation and dashboard baseline-versus-supplement wording.

Round-14 receipts must not certify the changed artifacts.

### Round 15

The round-15 snapshot includes the transcriber, code-edition snapshots, model manifest, corrected analysis/protocol/review artifacts, account reconciliation, release scripts, staged verification and browser interaction evidence. The snapshot digest recipe is canonical compact JSON with `snapshotSha256` omitted. Five expert perspectives must review that snapshot and any final fixes must be rechecked.

## Publication and storage boundaries

- Raw audio/video, full third-party transcripts, private segment/QA indexes, credentials and model weights remain outside public Git/Pages.
- Public artifacts contain code, metadata, aggregates, SVG/PNG figures, SQLite registries rebuilt from public rows, bounded excerpts and hashes only.
- Converter-assisted acquisition may be subject to YouTube/provider terms. Technical feasibility does not establish download or redistribution permission.
- Source-specific rights review is still required for raw redistribution. Kryon or Ashtar terms may allow particular releases only when followed exactly; no blanket license is inferred.
- The separate first-party LoRA adapter is trained on AI-generated paraphrases and redistributed under its own documented terms; no third-party base-model weights are included.
- The reported approximately 5 TB Drive allowance remains unverified. Folder creation is not a media upload.
- No diarization, speaker verification, human WER, human annotation or human peer review is claimed.
- Observed inventory is not a full-channel census; `uploaded_total` remains null. No completed 1,000-video crawl is claimed.
- Preview is not publication. No merge or deployment is implied by pushing this branch.

## Final release sequence

1. Complete round 15 and resolve all blocker/high findings.
2. Run analysis 119/119, audio 46/46, static dashboard checks, staged HTTP verification and desktop/mobile interaction checks on the final bytes.
3. Push all source/public artifacts to `research/acquisition-2026-11-expanded`; let CI materialize and verify public SQLite/PNG outputs. The GitHub token lacks workflow-file scope, so the existing checked-in-static workflow and its 10-minute budget remain unchanged; no scope bypass is attempted. The source-only fallback and 33-artifact package are verified locally for that path.
4. Save a website preview version and inspect it. Preview is not publication.
5. Create a draft pull request to current `main`, including the snapshot, checks, known limitations and account-reconciliation table.
6. Only after separate user/maintainer review consider merge, Pages deployment, compact Drive/provenance uploads and any source-specific raw release.
