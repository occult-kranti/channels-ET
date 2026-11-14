# Acquisition and ASR workstream — November 2026

This workstream records actual public YouTube audio acquisition and self-run ASR separately from the October metadata-only baseline. It does not claim a completed 1,000-video crawl or a full-channel census.

## Verified state

- **2,840 observed videos / 302 accounts**; `uploaded_total` is null. The baseline default selection remains 733, including exactly 100 Bashar-associated records across all accounts combined.
- **35 real audio files**, 1,321,921,399 bytes and 73,899.368 seconds.
- **43 terminal candidates = 34 analyzed + 8 excluded + 1 route-limit hold.** Seven exclusions are under 300 seconds, one is German audio unsupported by the English-only model, and the eight-hour Kryon compilation remains held above the public converter’s 150-minute route limit.
- **34 completed English ASR documents**, 146,605 words, 13,169 segments and 19.472 hours.
- **572 literal question units / 781 question sentences**, with 69 fresh AI-agent verdicts (7 confirm, 49 reclassify, 13 boundary errors). `humanValidated=false` throughout.
- **119/119 analysis checks and 46/46 audio checks pass.** Verification independently recomputes Q&A extraction, TF-IDF, NMF, nine-non-self-ARI KMeans, document similarity and sensitivity values.
- NMF stability is 0.7438 with all runs converged; maximum KMeans silhouette is 0.0070, so no cluster structure is claimed. The registry has 473 families: 17 cross-video, three same-video-only recurrence and 63 family-less stopword-only rows.

## Public versus private artifacts

Public code, metadata, CSV/JSON registries, SVG figures, bounded review notes and hashes are reviewable in this folder. Raw recordings, full third-party transcript bodies, private segment indexes, credentials and model weights remain outside public Git/Pages. Source hashes identify bytes only; they do not establish redistribution rights, speaker identity, original-session identity, ET origin or truth.

Converter-assisted acquisition may be subject to YouTube/provider terms. Public availability and technical feasibility do not establish download or redistribution permission.

Private locations are supplied with environment variables rather than committed absolute paths:

- `CHANNELS_ET_RAW_ROOT`: authorized raw research root containing `youtube-audio/` and `analysis-2026-11/`.
- `CHANNELS_ET_MODEL_CACHE`: authorized cache containing `tiny-en/`.
- `CHANNELS_ET_AUDIT_ROOT`: observed account/video JSONL inventory used by `build_reference.py`.

## Reproduce in the authorized workspace

```sh
python3 research/acquisition-2026-11/transcribe_youtube.py
python3 research/acquisition-2026-11/analysis/build.py
python3 research/acquisition-2026-11/analysis/make_review.py
python3 research/acquisition-2026-11/analysis/apply_review.py
python3 research/acquisition-2026-11/analysis/verify.py
python3 research/acquisition-2026-11/verify_audio.py
python3 research/acquisition-2026-11/build_reference.py
python3 research/acquisition-2026-11/materialize_public_artifacts.py
python3 research/acquisition-2026-11/package_acquisition.py
```

The transcriber is resumable. Existing results are reused only after audio, settings, allowlisted code-edition and output hashes validate. Summary updates are atomic and cannot downgrade terminal records. Four quarantined German ASR artifacts are hash-bound, including the partial segment JSONL.

`materialize_public_artifacts.py` rebuilds the public SQLite database from the committed CSV/JSON registries when it is absent and renders missing PNGs from the committed SVG figures. This supports a source-only GitHub branch without corrupting binary artifacts in transit.

## Account reconciliation

The workbench has 302 named account rows plus one unattributed presentation row. Named rows contain 2,286 account-video memberships; 631 videos have no account association. Seventy-six multi-account videos create 77 extra memberships. Reconcile as **2,286 + 631 − 77 = 2,840 unique videos**. Audio, ASR and analysis counts require the same deduplication.

See [HANDOFF.md](HANDOFF.md) for review history, release sequence and remaining boundaries, and [qualitative-synthesis.md](analysis/qualitative-synthesis.md) for analysis findings and limitations.
