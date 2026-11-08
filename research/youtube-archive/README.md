# YouTube collection repair

This extension repairs the historical channel/video inventory and provides an audio-first, resumable collection workflow. Open the [collection dashboard](https://occult-kranti.github.io/channels-ET/dist/youtube-archive/). Existing analyses and their frozen source editions remain available in [Channel Lab](https://occult-kranti.github.io/channels-ET/dist/channel-lab/) and [Transcript Knowledge](https://occult-kranti.github.io/channels-ET/dist/transcript-knowledge/).

The active collection policy has **no item-count cap**. Only positively Bashar-associated material has a **300-second duration floor**, including reposts. Other included mediums have no minimum duration. Unknown duration is unresolved metadata, not a short-video exclusion. Jamie Butler and the screened comedy/unrelated subscriptions remain excluded. Discovery preserves these routes and decisions instead of silently deleting them.

## What is counted

| Record | Meaning | Does not establish |
|---|---|---|
| Literal channel route | A handle, legacy path or UC account URL found in a source | A distinct platform account or medium |
| Historical uploader binding | An inspected historical watch response binds the upload to a UC ID | Current ownership, current availability or a full account census |
| Publisher-linked video ID | An explicit YouTube URL in a first-party page or sitemap | The uploader, audio retention or a completed YouTube crawl |
| Enumerated tab | An attempted public videos, Shorts or streams listing with terminal-state evidence | Private/deleted videos or all historical uploads |
| Verified audio | A real retained file with media validation and hashes | A transcript or completed analysis |
| Caption, ASR, analyzed text | Separately tracked text stages | Interchangeable editions or measured recognition accuracy |

The current gateway diagnostic received **CONNECT 403 before reaching YouTube**, while ordinary GitHub requests succeeded. It is a shared transport failure, not evidence that every indexed video is unavailable. The collection ledger preserves zero media/caption requests for jobs held by that gate. Current yt-dlp JavaScript support, client settings or token plugins cannot repair a failed CONNECT tunnel. The implementation and [source review](TOOL-RESEARCH.md) distinguish these supported fixes from the observed failure stage.

## Organization

- `inventory.py` reconciles historical routes, watch metadata and subsequent discovery editions, retaining evidence strength and exclusions.
- `publisher_discovery.py` fetches declared first-party pages and sitemaps, follows allowed links and preserves pending work and response hashes. It does not request YouTube endpoints or use relay services.
- `collector.py` handles the portable audio-first collection queue and its real execution ledger. See [collection instructions](COLLECTION.md) for current commands, runtime pins and state transitions.
- `reconcile.py` freshly verifies previously retained selected publisher media and text without assigning them to YouTube editions.
- `build_public.py` copies explicit producer allowlists into `dist/youtube-archive/`; `verify_release.py` checks the exact artifact set, hashes, module bindings and publication boundary.
- `browser_check.mjs` checks actual loaded dashboard modules, filters, exports and layouts. Offline synthetic tests are not collection observations.

Full media, exact transcripts, response bodies, worker databases and private receipts remain under the private managed workspace. GitHub contains organized code, public metadata, manifests, source notes and derived research. The managed workspace is not a permanent ChatGPT-account backup; no Google Drive upload is asserted. Future redistribution of full source files requires an appropriate basis rather than an automatic public Git add.

## Retained corpus reconciliation

The canonical frame contains **493 selected source texts / 1,411,446 words**. This run rehashes their text artifacts and **341 linked media paths / 10,715,508,036 bytes**. The bytes include selected publisher video/audio editions and are not a total archive size. Distinct resolved paths, encoded-media families, publication rows, Ra audio segments and canonical text units are different units. Per-context counts explicitly mean selected units with verified media. The older Ra segment and publisher-publication ledgers remain separately source-bound.

No new topic-model fit is inferred from metadata-only discovery. A newly retained source must pass media/text validation, provenance and eligibility before a new analysis edition can be built. The prior corpus and its models are preserved.

## Reproduce the selected-artifact check

```bash
python3 research/youtube-archive/reconcile.py \
  --frame /workspace/channels-et-private/channel-lab-2026-11/frame-02/frame.json \
  --output /workspace/channels-et-private/youtube-archive-2026-11/reconciliation-NEW \
  --receipt /workspace/channels-et-private/youtube-archive-2026-11/reconciliation-NEW-receipt.json
```

Use a fresh output directory. The loader verifies raw artifact and normalized text hashes; the reconciliation additionally checks source/edition IDs, body hashes, words and context IDs against the public registry. Each retained selected media path is rehashed. Public outputs omit source bodies and private file paths. The [independent AI review](REVIEW.md) records accepted checks and outstanding collection limits; it is not human peer review.
