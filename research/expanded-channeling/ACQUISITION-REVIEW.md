# Publisher acquisition and ASR review — 8 November 2026

This is the independent AI critic's execution review, separate from the
[accepted core research review](PANEL-REVIEW.md). Counts below identify the
observed checkpoints; the acquisition dashboard uses its own dated,
hash-bound snapshot. These reviews do not validate the sources' claims or
speech-recognition accuracy.

## Collector v2

The critic inspected the sequential collector, required repeated identity,
sample-count and source-lineage validation, an exclusive execution lock and
immutable code bindings. Eight tests passed independently. Two additional
real-FFmpeg adverse cases verified that compact-output and decoded-duration
caps fail closed and preserve partial attempts.

The first actual publisher pilot was independently rehashed and decoded:
685.139625 seconds, 4,164,092 retained Opus bytes, and provenance for
8,382,001 original bytes. The retained PCM hash/sample count reproduced
exactly; channels matched and only the newly staged original was removed.
The removed original was not independently decoded again. Collector v2
SHA-256 is `2663bef91d36ecb2ce1b9e7ba13edcb958716c6faa000ec90f77450d98a59165`.

## Explicit transition to parallel RAM staging

The source frame remains 229 explicit publisher enclosures: 224 RSS items
and five OmNa page-linked recordings. This is not a YouTube upload census.
Only Bashar has the 300-second minimum; the non-Bashar frame includes its
299-second item.

Collector v3 uses two bounded acquisition workers. Each original is capped
at 160 MB and staged in a separate RAM directory; each compact stream is
capped at 26 MB. Two 120 MB ASR PCM files may also use RAM. The declared RAM
envelope is 600 MB, with an additional 512 MiB cgroup headroom check for
models/workers. The persistent-disk floor stays at 2 GiB. The new phase
explicitly budgets 128 MiB disk reserve for two compact streams, provenance
and remaining margin, and retains the 1.62 GB admitted-audio cap. This is a
new resource contract, not an unnoticed change to the old collector.

The critic inspected shared admission accounting, process locks, immutable
frame/plan bindings and cgroup checks. Four tests passed independently,
including concurrent budget admission, excess actual size rejection,
exclusive locking and two simultaneous real FFmpeg conversions. The
transition then stopped v2 and inventoried its actual files. The critic
rehashed **246 files / 328,537,279 bytes**, verified 30 completed receipts,
and confirmed one interrupted unadmitted group remained preserved:
19,532,602 original bytes and 3,670,016 partial Opus bytes, plus provenance.
Those extra files are outside admitted-recording counts. The augmented
manifest is in the original phase directory, so the original v2 lock is
held during v3 and concurrent resumption cannot occur.

An actual v3 pilot added one Tracy recording: 7,418,654 retained bytes and
1,220.7251875 decoded seconds. Independent full decoding reproduced its PCM
hash and sample count; resource-plan, frame, original-receipt and cleanup
bindings passed. Two-worker collection may continue within those bounds.
No review promises that every frame item succeeds. V3 SHA-256 is
`2caf08d4025d37ba98700b84c3cc757cdf8f4abbff63754a8f9aa31044d0b5ed`.

## Local ASR and explicit timestamp recovery

The separate ASR successor imports the unchanged accepted legacy helpers.
It checks complete decoded PCM hashes/sample counts, caps each WAV at
120 MB, binds the model and executed validator, validates normalized source
IDs/counts/timestamps, distinguishes empty recognition, and stops new
scheduling after an observed worker failure. Six tests passed independently;
their mocked recognition checks are not inference or accuracy evidence.

The actual first inference produced **852 words / 71 segments** from the
685.139625-second pilot. The critic verified output hashes, identities,
counts, timing, unknown speaker roles, acquisition PCM agreement and cleanup
of only the new temporary PCM. Inference was not independently repeated,
and the critic did not listen to the audio. Successor SHA-256 is
`70754e0aeef744f3bd04cb14013e7e4bb67ef778bb4b8b515945d0a816147c99`.

The Quan Yin recording then correctly halted when the final recognized
segment ended beyond the audio. A separately executed recovery applies the
frozen helper's strict terminal policy: only the final segment can overrun,
its start and end must be within one 30-second window of EOF, all earlier
times and every recognized word stay unchanged, and the diagnostic stream
must have been exhausted. Three recovery tests passed independently.

The actual recovery retains **1,437 words / 83 segments** and changes only
the last displayed end from 920.26 to 912.799625 seconds, a 7.460375-second
adjustment. The critic compared every raw and normalized segment, verified
original inference/recovery/request/diagnostic hashes and checked PCM
cleanup after the new receipt passed. No inference was repeated, no text
was corrected, and terminal alignment remains unverified. The recovered
edition must remain labeled `terminal_end_display_repair_text_unchanged`.
Recovery SHA-256 is
`713960d1dec269fadac0ec8fbb411de371ae1150a3a466b927cf2dd6146f96ea`.

## Current decision

Bounded collection and ASR may continue on verified inputs under these
contracts. Public releases must use frozen snapshots, distinguish retained
sources from original/derived files and transcript editions, retain
unadmitted attempts outside success counts, and show running/failed/complete
states as observed. Full media and transcripts remain private; code,
metadata, aggregates and bounded reading paraphrases may be published.
