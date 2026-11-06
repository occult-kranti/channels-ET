# Latest-video study

This work-in-progress adds a reproducible selection, transcription and topic-comparison layer to the existing YouTube collection runner. It does not modify earlier studies. The selection unit is the **first eligible recorded upload in each supplied newest-first channel listing**, not necessarily that channel's latest channeling session. Shorts, recordings under five minutes and unresolved formats are excluded. A playlist snapshot can be stale or incomplete; document when and how it was obtained, and treat all results as a sample. Host accounts, clips and reuploads are not automatically distinct practitioners.

## Install and access

Use Python 3, `ffmpeg`/`ffprobe`, `yt-dlp`, `faster-whisper`, `scikit-learn`, `numpy` and optionally `matplotlib`. The existing acquisition runner's [README](../collection-runner/README.md) defines its verified-TLS access gate, source-hashed review, the global 100-unique-ID Bashar cap, disk budget and quarantine. **Do not reset the ledger or circumvent a denied access gate.** Its original private storage may have been removed by workspace maintenance; do not create a fresh ledger without recovering or reconciling the old accounting first.

The [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#readme) describes playlist ordering and metadata; the [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper#usage) describes CPU int8 transcription and model downloads. Model names download weights from a model host when not cached; a verified local model directory can be supplied instead. Use only material you have access and rights to process, and do not publish raw media or full transcripts without permission.

## Workflow

1. With access genuinely restored, obtain timestamped, newest-first channel listings with sufficient metadata using the approved access-gated collection workflow. Keep raw listings privately. Flat listings may omit `media_type` or duration; entries with missing format/duration are deliberately held, not guessed.
2. Run `python research/latest-video-study/select.py /private/channel1.json /private/channel2.json --output /private/selection.json`. The selection contains valid candidate IDs under `records` and a separate `excluded` list. It records selection time, not the time the original listings were captured. Retain listing retrieval timestamps separately.
3. Import candidates with `python research/collection-runner/runner.py import-discovery --input /private/selection.json`. This queues **metadata only**. Follow the runner README to obtain fresh metadata, conduct source-bound admission/review, respect the Bashar cap and execute a bounded video job. A successful `ffprobe` and matching source ID are required before treating output as media. Stop on a rate limit, site denial or validation failure.
4. Prepare a private JSON list with `video_id`, `channel`, `title`, `media_path`, and optionally `sha256` matching verified, locally retained video. Run:

   ```sh
   python research/latest-video-study/transcribe.py --input /private/verified-media.json --output /private/transcripts --model tiny
   python research/latest-video-study/analysis.py /private/transcripts/transcription-manifest.json --output /private/derived
   ```

   The first command validates each audio stream and records media and transcript hashes, duration, language and ASR configuration. Failures appear in the manifest. The analysis outputs TF-IDF terms, a lexical cosine matrix and a heatmap when plotting dependencies exist. With at least four documents it also fits exploratory NMF; the terms and clusters are hypotheses, not validated topics or evidence of ET identity.

5. Manually inspect a sample against audio, distinguish captions from ASR, disclose errors, language, host/guest mixing and excluded channels, and avoid attributing every word to a claimed entity. Keep raw files private. Publish only aggregate, source-linked results reviewed for third-party rights.

## Current execution

On 6 November 2026 metadata access was observed, but an actual YouTube media attempt returned an invalid response. A later automatic-caption request was rate-limited (HTTP 429). No fresh YouTube video or new audio transcription was successfully obtained in this pass. No new cross-channel findings are claimed. The one prior caption test is not a latest-video comparison.
