# One experimental alternate recognition edition

`retry_publisher_asr.py` implements one source-specific trial after the current
publisher audio frame completes. It is separate from the frozen English-only
ASR pipeline and does not replace or edit the original failed edition.

The target is the Multidimensional Soul publication “How Akashic Records HELP
YOU Make the HIGHEST and BEST Choices | Maureen St. Germain,” source ID
`publisher-rss:akanksshaa:rss:f35e0cfac4d68e2c`. Its original tiny.en diagnostic
contains 2,244 segments, 92 unique text strings and 2,152 exact repetitions of
“Satya.” Sixteen segment ends exceed the frozen validator's audio-duration-plus-
one-second bound. The source audio remains retained and verified. No human
listening established whether the audio contains a repeated phrase, so the
diagnostic is a recognition-quality hold, not proof that every repetition was
invented by the model.

The trial uses the existing cached `Systran/faster-whisper-tiny` multilingual
checkpoint at revision `d90ca5fe260221311c53c58e660288d3deb8d356`, with its pinned
file hashes. It requests English from the publisher's metadata, disables
`condition_on_previous_text`, and keeps beam size five, temperature zero, VAD
with a 500 ms minimum silence, CPU int8 and one worker. The default CPU thread
count is one. It downloads no model and changes no weights. Changing both the
checkpoint and conditioning means the result cannot isolate either change's
causal effect.

The script requires a completed collection manifest, exact held source/audio/
request/model bindings, adequate disk, tmpfs and cgroup headroom, and fresh
private output and PCM directories. An exclusive reservation in the original
failed-source directory prevents another invocation from silently running a
second trial in a different output directory. All original failed artifacts
remain intact. Only a newly created retry PCM is removed after a completed
alternate receipt validates.

Full audio is decoded through the already tested 120 MB PCM writer. The sample
count and PCM hash must reproduce the acquisition proof. The complete inference
stream is saved privately. Limits of 10,000 segments, 20 MiB of raw diagnostic
JSON and 1,800 seconds are checked at segment yields; reaching a limit produces
an unadmitted partial, not a complete transcript. These cooperative checks do
not claim to interrupt a model call that never yields.

Admission requires valid source, model, decoder, language, timing and artifact
bindings. The existing single-final-end display policy may bound one eligible
terminal overrun; other timing failures are held. Recognition with at least
100 identical segments covering half the nonempty segments, or a consecutive
identical run of 100 segments, remains held for audio review even if timestamps
pass. This conservative corpus-quality rule does not assert that repetition
cannot be present in real speech. No words are deleted to make an output pass.

A structurally admissible result receives the distinct edition suffix
`:asr:tiny-multilingual-no-conditioning-retry1`. Its normalized text retains
unknown speaker roles, `no_answer_identified: true` and
`speaker_identity_verified: false`. Its receipt explicitly records the new
model, inference settings, executed code and raw diagnostic. It does not claim
the frozen English-only script produced this alternate edition.

The canonical private output directory is `publisher-asr-fallback-v1`.
Its `manifest.json` has one of these states:

| State | Records | Interpretation |
| --- | ---: | --- |
| File absent | — | Trial has not produced an execution artifact; do not assume success. |
| `single_experimental_retry_running` | 0 | Trial is in progress. |
| `single_experimental_retry_completed_pending_review` | 1 | Structural checks passed; independent review is still required. |
| `experimental_retry_unadmitted` | 0 | Exhausted inference failed admission. |
| `single_experimental_retry_failed` | 0 | Execution failed; diagnostic artifacts remain. |

Publication and refresh automation must also require an independent review
receipt binding the exact terminal manifest SHA and, when present, the exact
alternate receipt SHA. The immutable trial manifest is not rewritten merely to
change its review status. The original English-only hold remains historical
evidence even when an independently reviewed alternate edition is selected.
Lower repetition counts or valid timestamps are not a measured word accuracy
improvement, and this trial performs no word error rate comparison.

The agreed `independent-review.json` contract uses `schema_version: 1`,
`status: accepted_for_analysis` or `accepted_unadmitted_hold`, the exact
`manifest_sha256`, `receipt_sha256` (or null when no receipt exists),
`publication_id`, and a plain-language `decision`. The refresh process must
check those bindings before using the alternate or treating the trial as a
reviewed terminal hold.

```sh
python research/subscription-screening/retry_publisher_asr.py \
  --acquisition PRIVATE/publisher-audio-v3/manifest.json \
  --holds PRIVATE/publisher-asr-v2/recognition-holds-v1.json \
  --output PRIVATE/publisher-asr-fallback-v1 \
  --pcm-root /dev/shm/channels-et-publisher-fallback-v1 \
  --cpu-threads 1
```

Run only after the collection-complete/resource gate and independent code
review. The tests exercise real synthetic media decoding with mocked
recognition; they verify pipeline behavior and do not constitute a successful
actual retry or an accuracy evaluation.

## Observed single trial

The authorized trial completed on 8 November 2026 after all 229 source audio
items in the acquisition frame completed. One CPU thread processed the full
2,687.8955-second source. It produced 5,846 words in 474 segments, with no
timestamp repair and no endpoint beyond the decoded audio duration. The largest
exact-text repetition count was two segments (0.42% of segments), compared with
2,152 segments (95.90%) in the original failed edition. This comparison describes
recognition output; the different checkpoint and conditioning remain confounded,
and no listening or word accuracy evaluation was performed.

Independent review accepted the alternate for analysis as a distinct recognition
edition, checking source, model, settings, code, exhausted raw stream, full PCM,
normalization, original failed history and cleanup bindings. The original failed
edition and its hold remain unchanged. Only the new retry PCM was removed after
its completed receipt validated. The exact private artifact bindings are:

| Artifact | SHA-256 |
| --- | --- |
| Terminal manifest | `84462f3d7d06b15478c537591fa2515b50ddfc596a494914ccc7752a8d2278dd` |
| Alternate receipt | `af59ef43ae1ef89f3b7811cb5b0b2773880d77881f5001b66932cb660ae5cedf` |
| Independent review | `0aa762737d9483a5b51e46e32d4b98b58207a5a232b784ee3e86b638cab909fa` |
| Executed retry script | `1db7a61b40155b4df06d020889d8e6004982d51c85bfbdc2671f7e8e87501b1d` |

All eight test methods passed independent review before this execution, including
rehashed adversarial metadata mutations. Tests and structural review establish
the edition's recorded lineage and admission rules, not recognition accuracy.
