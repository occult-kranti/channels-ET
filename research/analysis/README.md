# Reproducible channel analysis

This is a convenience sample of indexed upload IDs, not a census of YouTube, channelers or complete accounts. Video uploader, reported human channeler, entity label and original session are different units.

## Inputs and outputs

- `inputs/claude_videos.json`, `claude_accounts.json`, `claude_audit.json`: normalized, row-provenanced records from the supplied ZIP. Missing IDs are excluded from the video union.
- `inputs/fresh_metadata.json`: frozen public watch-page acquisition records. Current uploader, title, duration and UTC date supersede inherited values; differences are retained in output observations.
- `inputs/language_cache.json`: deterministic title-language decisions, with method/probability. Short-title detection remains uncertain.
- `inputs/model_manifest.json`: Apache-2.0 MiniLM model revision and artifact hashes; weights are not stored in Git.
- `inputs/derived_text_features.json`: numeric, source-linked model outputs and caption keyword features; no full caption text. Fingerprint prevents silently reusing vectors after title or channel changes.
- `rounds/`: frozen first-pass and revised data, hashes and round2 metadata input. Reviews are maintained by the main project panel.
- `../../dist/analysis/`: interactive snapshot, CSV tables, numeric embedding archives and SVG/PNG figures. The report is maintained separately.

## Rebuild from committed evidence, without network or raw captions

Install `requirements.txt` into a virtual environment, then run from the Channeling Atlas project root:

```sh
python research/analysis/build_analysis.py
```

The default rebuild recalculates video statistics, TF-IDF and figures from frozen input, and validates/reuses the numeric neural derivatives. It does not retrieve new videos or claim to regenerate speech from embeddings. Changes to titles or channel associations invalidate the fingerprint and require explicit recomputation.

## Recompute learned features with authorized local caption text

```sh
python research/analysis/download_model.py --output /absolute/path/to/model
python research/analysis/build_analysis.py --recompute-text --model-dir /absolute/path/to/model --corpus-file /absolute/path/to/corpus.json --metadata-file research/analysis/inputs/fresh_metadata.json
```

The corpus schema is `records[]` with video_id, transcript_status, language_code, is_generated, text, sha256 (caption-artifact hash), url and selection. Text is only read locally. The output contains a separate actual text SHA and source-artifact SHA, derived topics and numeric vectors. Do not commit raw transcripts unless you have redistribution rights.

`CHANNELING_ANALYSIS_VENDOR` may point to an optional existing dependency directory; it is not required in a standard virtual environment. Model retrieval verifies every hash and executes no remote model code.

## Definitions

- Durations: mean, median and linear 25th/75th percentiles of known eligible durations, with measured/indexed denominator. Unknown durations remain null, never zero. A duration can be readable even when a video is members-only or unplayable.
- Dates: UTC day from current publication timestamp; inherited exact day if no current timestamp exists. Relative labels stay text. A one-day inherited/current difference can be timezone conversion. Monthly counts describe indexed records, not total channel upload rates.
- Titles: current watch title supersedes supplied or translated title; variants remain. English-likely gate is langdetect1.0.9 seed42, probability≥0.80, at least four alphabetic words. Detected English is not manual language verification.
- Lexical similarity: English name-and-genre-masked word unigram/bigram TF-IDF; min_df2, max_df0.9, sublinear_tf; equal-video centroid; at least five usable titles. This is a sparse lexical vector method.
- Semantic similarity: sentence-transformers/all-MiniLM-L6-v2, pinned revision, 384 dimensions, ONNX CPU. This is an established English baseline, not a claim of state-of-the-art performance for channeling text. Titles use at most254 wordpieces plus special tokens.
- Captions: separate purposive English pilot; one additional Scranton concordance sample is excluded from the balanced analysis. Automatic captions are not corrected, translated or speaker-diarized. A retrieved caption does not establish that a performance is channeling or that an entity exists.
- Long text: non-overlapping240-wordpiece chunks plus CLS/SEP. Attention-mask mean pooling and L2 normalization per chunk; equal chunk mean→video normalization→equal video mean→channel normalization. The short final chunk has equal weight, an explicit limitation. No silent truncation to the first passage of a recording.
- Caption keywords: occurrences per1,000 word tokens matching `[A-Za-z]+(?:'[A-Za-z]+)?`; contractions count as one word. Compute per video, then average equally by publisher. Categories overlap and remain unvalidated descriptive indicators.
- Sensitivity: raw versus masked titles; excluding all repeated masked-title strings;50 fixed-seed balanced five-title samples; removing the first and last floor(10% of the token count) whitespace-separated tokens after masking. Pairwise scores share documents and are dependent. No inferential p-values or causal effects are reported.
- Matched comparison: title and caption model comparisons use exactly the same eligible video IDs. Longer captions have more opportunities for keyword matches, so title/caption presence bars are not topic-intensity estimates.

The review-led-game-design skill contributed traceable evidence→decision→implementation→verification and purposive-sample cautions. Gameplay, currency and progression instructions were inapplicable. Data Analytics build-dashboard/visualize-data contributed units, denominators, null handling, correct chart families and figure review. The existing Sites layout was preserved.

## Continuation handoff

See the project [README roadmap](../../README.md#roadmap-next-research-phase) and [branch register](../maintenance/branch-register.json). Preserve the frozen rounds and run rebuilds in a disposable worktree before replacing a public release. Changing inputs requires reviewing the neural-feature fingerprint and the paper snapshot pin.
