# Compact publisher-audio / local-ASR contract

This is a proposed new execution contract, not evidence of acquired media. The
accepted Bashar core at `research/batch-media/audio.py` remains unchanged. New
screened RSS processing uses the separately versioned `audio_derivative_v2.py`.

`source_id` is a safe processing identifier, for example
`publisher-rss:tracykumbera:993981f9f0ef856e`. `publication_id` preserves the exact
feed identity, for example `@tracykumbera:rss:993981f9f0ef856e`; neither is a claim
of a unique original session. Exact original-byte SHA-256 defines a separate
`exact_media_family_id`. Publisher captions, generated ASR, and any superseded or
failed attempts keep independent identities and provenance.

All records sent to the new local audio processor use:

```json
{
  "provider": "publisher_audio",
  "source_origin": "publisher_rss",
  "input_representation": "full_duration_lossy_opus_derivative",
  "kind": "audio",
  "source_id": "publisher-rss:tracykumbera:993981f9f0ef856e",
  "publication_id": "@tracykumbera:rss:993981f9f0ef856e",
  "medium_id": "tracy_kumbera",
  "channel_id": "tracy_kumbera_podcast",
  "source_language": "en",
  "source_language_status": "publisher_feed_declares_en_not_detection",
  "local_path": "/private/retained.opus",
  "sha256": "ACTUAL_RETAINED_FILE_SHA256",
  "bytes": 123456,
  "duration_seconds": 300.0065,
  "decoded_16k_mono_sample_count": 4800000,
  "decoded_16k_mono_duration_seconds": 300.0,
  "verification_receipt": {"path": "/private/asr-source-proof.json", "sha256": "ACTUAL_PROOF_SHA256"}
}
```

The example numbers and placeholders above are synthetic. Actual execution must
read and hash real files; a syntactically valid digest is insufficient.

The immutable original-source receipt has `status: "original_source_verified"`,
`source_id`, `publication_id`, `source_origin: "publisher_rss"`, the exact
`enclosure_url`, `final_url`, recorded delivery redirects/headers, and:

- `original: {sha256, bytes, probe, channels}`;
- `decoded_16k_mono: {sample_count, duration_seconds, raw_pcm_sha256}`;
- original publisher feed and inventory artifact bindings;
- retrieval and measurement code/version hashes.

The completed acquisition receipt has `status: "completed"`, the same source
identity/origin/representation, `duration_seconds` from the retained Opus
container, `audio: {path, sha256, bytes, probe}`,
`decoded_16k_mono: {sample_count, duration_seconds, raw_pcm_sha256}`, and `lineage`:

```json
{
  "original_source_receipt": {"path": "/private/original-source.json", "sha256": "ACTUAL_RECEIPT_SHA256", "bytes": 1234},
  "original_enclosure_url": "https://publisher.example/explicit.mp3",
  "original_sha256": "ACTUAL_ORIGINAL_BYTES_SHA256",
  "original_bytes": 1000000,
  "original_channels": 2,
  "retained_channels": 2,
  "original_decoded_16k_mono": {"sample_count": 4800000, "duration_seconds": 300.0},
  "retained_decoded_16k_mono": {"sample_count": 4800000, "duration_seconds": 300.0},
  "max_duration_difference_seconds": 0.1,
  "conversion": {
    "mode": "full_first_audio_stream",
    "codec": "libopus",
    "target_bitrate_bps": 48000,
    "vbr": false,
    "channels_preserved": true,
    "trimmed": false,
    "silence_removed": false,
    "code_sha256": "ACTUAL_COLLECTOR_SHA256",
    "ffmpeg_version": "ACTUAL_VERSION"
  }
}
```

The outer ASR proof contains a hash-bound `acquisition_receipt` and exactly one
`verified_artifacts` item binding the retained Opus, provider, source origin,
input representation, context, language, and both decoded-16k fields. Its
`validation` contains `source_id`, `ffprobe_duration_seconds`, and
`acquisition_receipt_sha256`. The core must rehash the acquisition and original
source receipts and verify all repeated fields, channel counts, and complete
decoded-duration/sample-count relationships. A separate cleanup receipt records
deletion of only the new temporary original after admission of the compact copy.
It must never claim that the original MP3 remains stored after deletion.

The proposed capped PCM path decodes the full retained Opus to raw 16 kHz mono
signed-16-bit samples through a pipe. A counted writer creates the WAV, checking
the explicit cap before every write. It requires natural decoder EOF and a zero
exit code; a cap-triggered stop always fails and preserves the partial file.
Full measured sample count must agree with the proof within 100 ms. The default
legacy decode behavior and old receipts remain unchanged.

An exact publisher-caption→GUID→enclosure link suppresses redundant fresh ASR
for that publication. It does not establish caption accuracy, completeness, or
speaker alignment. Caption duplicates are not automatically audio duplicates.
Only actual original-byte hashes can establish an exact media family.
