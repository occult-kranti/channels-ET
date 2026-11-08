# One alternate edition for the second held source

`retry_publisher_asr_v2.py` is a separate successor for
`publisher-rss:akanksshaa:rss:b9fd4b8c29ce9611`, the Multidimensional Soul
publication headed “2026–27 ARCHANGELS ALERT” with Sanjanaa. Its original
English-only inference exhausted the full source into 645 segments. Nineteen
segment ends exceed strict audio EOF, and 18 exceed the frozen validator's
one-second tolerance. The largest identical-text count is 44 segments across
542 distinct strings. The original edition remains unadmitted under
`multiple_segments_outside_audio`; its recognition text and failed PCM remain
preserved. These diagnostics do not establish the accuracy of the recognized
words or the presence or absence of repeated speech in the audio.

The new script differs from the first reviewed fallback implementation in
exactly two lines: its fixed source ID and permitted hold reason. The source,
model, decoder, output and failed-history validation; one-attempt reservation;
resource guards; repetition policy; and single-terminal-end normalization
policy are unchanged. It uses the same pinned multilingual tiny checkpoint and
disables conditioning on previous text. Inference requests one CPU thread.

The successor code SHA-256 is
`4b15573d8a52a62fedbe9344a9184d6f88ff1beb096b90061fb52588b7679c88`.
Nine test methods passed independent review: all eight predecessor contract
tests, including adversarial rehashed-metadata cases, plus an exact two-line
diff and immutable-predecessor-hash check. Independent source, hold, model and
resource review preceded execution. The first fallback's code and result are
unchanged.

Canonical private output is `publisher-asr-fallback-v2`, with newly created PCM
under `/dev/shm/channels-et-publisher-fallback-v2`. The trial uses the same
terminal manifest and separate `independent-review.json` contract documented
in [FALLBACK-ASR.md](FALLBACK-ASR.md). The first trial's acceptance cannot admit
this source's result: its exact terminal manifest and receipt require their
own review. Only newly created trial PCM may be removed after successful
receipt verification; neither original failed PCM may be deleted.

```sh
python research/subscription-screening/retry_publisher_asr_v2.py \
  --acquisition PRIVATE/publisher-audio-v3/manifest.json \
  --holds PRIVATE/publisher-asr-v2/recognition-holds-v2.json \
  --output PRIVATE/publisher-asr-fallback-v2 \
  --pcm-root /dev/shm/channels-et-publisher-fallback-v2 \
  --cpu-threads 1
```

This is one bounded experimental recognition edition, not a model weight
update, measured accuracy gain or manual assessment of the audio. Changing
both the checkpoint and conditioning prevents attributing differences to
either change alone.

## Observed trial

The single trial completed on 8 November 2026 with 8,078 words in 568
segments, using unadjusted timestamps. The final segment ends at 3,419.38
seconds, 0.082 seconds beyond the decoded 3,419.298-second duration. This
falls within the unchanged frozen validator's one-second tolerance; no
endpoint exceeded that tolerance and no timestamps were clipped. The largest
exact-text repetition count was six segments (1.06%). No listening or word
accuracy evaluation was performed.

Both original failed PCM artifacts remain present. Only the newly created
retry PCM was removed after the alternate receipt passed verification.

| Artifact | SHA-256 |
| --- | --- |
| Terminal manifest | `bfcb8a88e6bdc8cb4c8ef4234bb52681d3aeefe46fa1fda44760dc209c8f33e4` |
| Alternate receipt | `fd45bf9962d63db4babc357c8c5205019f08c506e52ab3a2e42c04f84212a62f` |
| Independent review | `4e0b18d6c38bd6a180ee6fd8be19fb43ce80a5fdaaf802cbd4c40b11ce65fb4e` |

Independent review accepted this exact alternate for descriptive analysis,
checking all 568 raw/normalized segments, source/model/code/PCM lineage,
original failed-artifact preservation and new PCM cleanup. The review records
the terminal 0.082-second tolerance case explicitly. Acceptance does not
establish recognition accuracy or exact acoustic alignment.
