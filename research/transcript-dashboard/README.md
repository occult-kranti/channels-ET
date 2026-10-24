# Transcript study explorer — 23 October 2026, New York

The standalone explorer is built into `dist/transcripts/`, with a generated link from the existing research navigation. It is a new study surface; previous dashboard source folders, the earlier scientific data and manuscript remain byte-preserved. Root's entry page and Pages deployment are managed separately.

The interface provides five views:

- Study overview: source contexts, analytical token counts and equal-document topic shares.
- Lexical maps: thresholded document networks, separate-fit cluster projections, an explicitly ASR-reference authored overlay, aligned topic/keyword heatmaps, filtered TF-IDF ranks, strict dictionary co-mentions and audio-time profiles.
- Readings & Q&A: sampled-word coverage, six source-bound interpretive comparisons, provisional AI syntheses and 37 typed/paraphrased candidates. Interview, fragmentary, rhetorical/self-question, reported and analyst-constructed authored prompts remain distinct.
- Contexts & storage: inherited YouTube routes/publishers/practitioner/entity/civilization associations with explicit assigned/unassigned coverage; separate assigned partitions of 99 actual source artifacts; the actual 200-file managed local archive, distinguished from Drive and durable chat storage.
- Sources & methods: the new 22-page paper, portable source ZIP, exact numerical results, metadata database, all nine figure families and source-bound downloads.

Twenty ASR documents (19 Bashar-context publications and one Ashtar-attributed creator episode) and 16 authored comparisons use separate TF-IDF/topic/clustering fits. Topic IDs are not comparable across fits. Analytical regex tokens, whitespace words and historical acquisition receipt counts have separate labels. Quantitative complete-text processing is distinct from AI reading of sampled windows: 11,992/226,093 unique ASR whitespace words and 6,319/13,656 authored words. Packet words include overlapping windows.

An edge is lexical association, not agreement, a social relation or physical-origin evidence. Source claims, inherited labels and strict text-dictionary matches are separate layers. All speaker/edition verification remains false; source-context and storage metadata do not identify voices. No full raw transcript or recording is published.

## Rebuild and verify

From `/workspace/channels-ET`:

```bash
python research/transcript-dashboard/build.py
python research/transcript-dashboard/verify.py
TRANSCRIPT_URL=http://127.0.0.1:8016/channels-ET/dist/transcripts/ \
TRANSCRIPT_OUTPUT=/workspace/channels-ET/dist/transcripts \
node research/transcript-dashboard/check-browser.cjs
```

`inputs.json` is an explicit SHA-256 allowlist of final owner exports. The builder never crawls, trains, transcribes, authenticates storage, or globs private source directories. Candidate builds require `--candidate --output /tmp/channels-et-transcript-preview/channels-ET/dist/transcripts`; they cannot target public `dist`. Final builds copy metadata and derived artifacts only, and regenerate the navigation link from the protected baseline commit. Source and UI review receipts are kept research-only to avoid a circular dependency on the data/PDF hashes they certify.

The existing static stack was retained with native HTML/SVG and no new frontend dependency. The shared Data runtime reference remains unavailable through the skill reader and no installed runtime/preparer was found; this app does not claim that runtime contract. The Data/dashboard and Design Partner workflows informed provenance, composition, filtering and rendered checks.

## Executed acceptance evidence

`source-verification.json` records **589 passed checks**: exact inputs/output bytes, 20/16 source IDs and hashes, within-fit matrices/topic shares, recomputed term/rate values, 105 support windows and 37 typed Q&A joins, six interpretive support sets, every attribution-coverage frame, canonical/local storage accounting and prior held source/manuscript freezes.

`browser-verification.json` records **265 passed checks**, including all **70** served downloads matching current retained source bytes and displayed hashes. Tests cover actual filtered JSON downloads; threshold/neighbor-rule provenance; independent authored models; reference-square keyboard inspection; native dialog Escape; empty mean values; question-kind/family filters; separate storage scopes; 390- and 320-pixel page reflow; and 720 CSS-pixel desktop reflow. Five final screenshots were captured and four were visually inspected. Independent technical reviewers separately exercised broader desktop/mobile/keyboard/zoom-equivalent flows and are binding their final receipts after this hold.

These are loopback functional checks with external browser requests blocked, not source-collection operations or a screen-reader/WCAG certification. Narrow-screen projection points can overlap; enlarged hit areas, zoom, source tables and exact pair exports provide alternatives. Root performs the actual Pages deployment and live verification.

Final transcript paper: SHA-256 `57102be0b866a80f7b49b9de89e6d0823d962fe8cd3f71fb229ede8d68bb700f`; source ZIP `604ab5db35595e2cd5cb5cdc8540671ac1e702b0333e7fb79c2cb354648b3bd2`. The earlier 16-page paper is unchanged.
