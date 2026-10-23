# Model panel — round 12 disconfirmation and closure

Reviewed round-11 archive SHA-256:
`dbfdc2e6c655c13124830e3db1a741fba7cf2270ecf140809e2f9e7be6a1410f`.
Role: AI model implementation/research reviewer. No human ground-truth or
original-speech validation is claimed.

## Actual prompt-order test

The same 12 digest excerpts, base Qwen2.5 model, greedy 96-token budget, CPU
threads and original conditional/evidence instructions were reused. Only the
theme-option order was reversed. Nine reversed records parsed; eight source
items had valid parses in both conditions. Six of those eight theme labels
changed. The reversed labels were seven `personal_practice` and two
`contact_forecast`; none chose the reversed first option, `unclear`.

This **disconfirms simple first-option copying**, while showing substantial
local prompt sensitivity. It does not validate either set of labels. Both parse
denominators, missing cases and raw outputs are retained. One initial attempt
was stopped before completion after identifying a null-value aggregate bug;
the corrected attempt is the completed experiment. The partial log and correction
are disclosed in `round12-run-events.json`.

## Separate codebook sensitivity

The inherited conditional regex matched `dependency`/`dependence` forms even
when they did not express a logical condition. A separately named, post-hoc
narrower pattern changes 60 indicators to 58 among 949 answer gists, with two
source-linked changed records. Original labels and sample selection are
unchanged. The narrower rule remains unvalidated; other false matches and
missed conditions are possible. This is not a repaired human reference.

## Actual current-family annotation

Official Qwen3.5-0.8B then processed the same 12 excerpts with the **original**
label schema/order and 96-token cap. It used its own tokenizer/chat template,
Transformers 5.20.2, thinking disabled, float32 and two CPU threads. The
image-text architecture received text only. No adapter or Qwen3.5 fine-tuning
was used. Operational differences are preserved in its protocol.

- All 12 outputs parsed as the required JSON schema.
- Ten evidence strings were exact answer-gist substrings. Five of those were
  longer than eight words, leaving five combined exact-and-short spans.
  Two strings were nonexact. Overlength exact strings are length failures,
  not invented evidence.
- All 12 conditional labels were yes. Its 6/12 dictionary concordance therefore
  **equals the always-yes baseline**, with no evidence of discrimination under
  that indicator. The original baseline's 5/9 likewise equals its always-yes
  baseline. Neither statistic is human annotation accuracy.
- Theme labels were 11 `personal_practice` and one `contact_forecast`.
- Mean generation time was 6.901981 seconds per excerpt, no output hit the
  96-token cap, and peak process RSS was 5,612,900 KiB.

The newer model meets the format/literal-span criteria more often in this small
same-item comparison, but that does not establish source truth, semantic label
accuracy or a general model ranking. Different architectures, tokenizers and
required runtimes prevent isolating parameter scale as the cause. No images,
video, audio, GPU comparison or newer-model training was performed. Neural
experiments stopped after this bounded run.

## Reproduction and closure evidence

`annotation-comparison.json` separates exact spans, length limits and their
intersection for all three conditions. `round12-verification.json` passes 129
source-only checks, including identical source IDs/text, original output hashes,
prompt-only order changes, source pins, the released adapter and current-model
receipts. It does not replay neural inference.

The released adapter ZIP still has SHA-256
`19bd5b720446af07603390e276baebfb0010fb4df7971199262cae64fd7adb0c`.
The offline benchmark verifier now passes 282 checks, including equality of the
released matrix and recorded training receipt. It explicitly skips tokenization;
historical executed tokenization evidence remains separately preserved. The
round-11 diagnostic audit passes 102 checks. All primary 50 predictions/metrics
and the original 12 annotations retain their bytes.

README spacing and exact CPU/modern environment instructions were rewritten.
`setup_model_envs.sh` was exercised against the prepared environments: both
`pip check` runs and modern-library isolation assertions pass. This is a
repeatability check, not a fresh-machine claim. Weight caches remain outside
Git. Runtime logs and manifest hashes are retained, including failed/interrupted
attempts. No further neural experiments or data mutations are pending.
