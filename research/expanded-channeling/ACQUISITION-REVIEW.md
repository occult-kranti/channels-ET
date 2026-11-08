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

## Snapshot-following ASR queue

The critic inspected the queue that follows advancing acquisition snapshots
and found two concrete problems before launch: recovery was outside the ASR
lock, and an invalid existing receipt or stale failure manifest could cause
repeated attempts. Both were corrected. Six queue tests passed independently,
including rejection of those repeat-loop cases and termination after a final
validated snapshot. Recovery now runs while holding the ASR lock; inference
then acquires its own lock. The queue uses one recognition worker while
collection is active and two after the frame completes.

Only the reviewed, source-bound terminal-display policy may recover
automatically. Other diagnostics, resource failures and invalid admitted
receipts halt, preserving attempts. Each repair remains a separately marked
normalization edition; automatic handling does not validate its terminal
speech. The queue was accepted for execution at SHA-256
`632dfa8f699fb9acf499ed0c6df86037fcb11b0fa06c2208ff88ad7101af9746`.
This code review is not a claim that its future workload has completed.

## Source-specific recognition hold and queue successor

One later Akanksshaa recording produced an exhausted but degenerate raw
recognition stream: 2,244 segments, 92 distinct text strings and 2,152 repeated
`Satya.` strings. Sixteen segment ends exceeded decoded duration by more than
one second; 17 exceeded strict EOF. The critic independently counted these
values and inspected the bound request/diagnostic. This is outside the
terminal-only display repair. Its text remains unadmitted and its audio and
failed artifacts remain retained.

A separate v3 queue permits only this reviewed source/model edition to be
held while other recordings continue. It verifies the exact source/audio,
request, exhausted raw diagnostic, model and original execution-code hashes.
A changed audio or model cannot silently inherit the hold. Eight successor
tests passed independently, including altered hold bindings, fail-stop
behavior and explicit incomplete-recognition final status. The actual ledger
passed validation and no admitted receipt existed for the held source.

The reviewed queue SHA-256 is
`a9b5513f575bc61ef6c2006eec9f02c88abd711bdb3ddbe0fc85b9ad39344876`;
the source-specific hold ledger SHA-256 is
`d22d547c4af5a2169ebcb3280d9158660d0c68c9e66e04db0cef44466113e265`.
The queue was accepted for continuation with the hold visible. Finishing
its remaining selected frame cannot be described as finishing all recognition.

The metadata projector was subsequently reviewed with four passing tests for
held versus pending sources, empty recognition, tampered proof and a valid
alternate edition preserving failure history. An actual frozen projection
reconciled its retained-audio, completed-text, caption-linked, held and pending
counts. The held source retained its audio and no successful transcript word
count; public output contained neither private paths nor the repeated raw
diagnostic text. Projector SHA-256:
`b134b7ee9f6442bb8a5080114414102ae3ec1b7453bf97d2fde809ccf9c08749`.
Later progress publications must still freeze and identify their own inputs.

## One-source alternate-recognition experiment

A separate one-attempt successor was reviewed for the held source, using the
already cached multilingual tiny checkpoint at revision
`d90ca5fe260221311c53c58e660288d3deb8d356`, explicit English metadata, and
`condition_on_previous_text=false`. It is a distinct model/settings edition,
not an edit of the frozen English-only inference or its failed output.

The critic found and required corrections to repeated decoder proof checks,
normalization/repair metadata checks, and request/snapshot/failed-history
bindings. After correction, eight test methods passed independently,
including eight altered-and-rehashed metadata cases, a real synthetic-audio
decode with mocked recognition, rejection of multiple timestamp failures,
and a permanent one-attempt reservation. Actual source/hold/model bindings,
the complete collection frame and current resource gate were checked before
accepting the one-CPU trial at code SHA-256
`1db7a61b40155b4df06d020889d8e6004982d51c85bfbdc2671f7e8e87501b1d`.
This entry records permission to execute the reviewed experiment, not a
successful or accurate transcript. Its actual terminal result requires a
separate bound review before analysis admission. A reduction in repeated
output alone cannot establish recognition accuracy.

The one actual trial subsequently completed and received that separate
review. Its terminal manifest SHA-256 is
`84462f3d7d06b15478c537591fa2515b50ddfc596a494914ccc7752a8d2278dd`,
and receipt SHA-256 is
`af59ef43ae1ef89f3b7811cb5b0b2773880d77881f5001b66932cb660ae5cedf`.
The critic verified all 474 raw/normalized segments, 5,846 words, unadjusted
timestamps within the 2,687.8955-second source, complete inference-stream
exhaustion, source/model/settings/code/PCM/history bindings and cleanup of
only the newly created retry PCM. The maximum identical segment count is
two. The distinct alternate edition is accepted for descriptive analysis;
the original failed edition and its hold history remain retained. No audio
was listened to in this review, and no word-accuracy improvement is established.

## Second failed edition and bounded automatic quarantine

A second Akanksshaa interview produced 645 raw segments, 542 distinct strings,
and 18 segment ends more than one second beyond its 3,419.298-second source.
This was not the first source's predominant repeated-word degeneration, and
multiple invalid segment ends remained outside the terminal-only repair.
The original attempt and both initial failed PCM files were preserved.

The separately reviewed v4 policy may quarantine later exhausted attempts
with the same bounded multiple-EOF failure class while other sources
continue. It replays exact source, model, request, raw stream, first timestamp
failure, execution code and full PCM proofs. Global integrity, resource or
infrastructure failures still stop. Added holds declare automatic application
of the reviewed policy, not individual source-content or human review. No
held transcript enters the analysis. Only new temporary PCM can be removed
after verified regeneration provenance and a durable cleanup receipt; both
initial failed PCM files remain protected.

The critic required two corrections: preserving the frozen validator's
integer representation for a first-row failure, and binding every dynamic
ledger to the unchanged initial rows so a new hold cannot evade its automatic
markers. Fourteen queue tests and six projector tests passed independently.
Both actual initial failures were replayed through the final read-only
validator, including their retained PCM payloads. The accepted policy is
`c14acb79dbfdef7ecd47d56a20b53f2f944ad1fec8e7b981f398dc8620aec09f`;
the initial two-source ledger is
`79c3bbac5f9c2a3b6c674961e9b103f8001cbb0f0a757c79d291ec242a70a1c0`.
The projector with explicit failed-edition provenance is
`0dc48ecfbf27b41abaae944bd8bd41c89f08c944cb6e120550bbfc475ded75ab`.
This accepts the policy and actual initial inputs, not any future source's
recognition quality or a claim that processing has finished.

## Second one-source alternate-recognition experiment

A separately reserved trial changed only the permitted source ID and hold
reason in the reviewed first alternate implementation. Nine test methods
passed independently, including the exact two-line code difference and the
inherited adversarial binding cases. The new code is
`4b15573d8a52a62fedbe9344a9184d6f88ff1beb096b90061fb52588b7679c88`.
It uses the same pinned multilingual tiny checkpoint and no-conditioning
settings, one CPU thread, and a distinct output directory. Neither initial
failed edition was replaced.

The single actual trial produced **8,078 words / 568 segments**. The critic
verified the exact terminal manifest
`bfcb8a88e6bdc8cb4c8ef4234bb52681d3aeefe46fa1fda44760dc209c8f33e4`
and receipt
`fd45bf9962d63db4babc357c8c5205019f08c506e52ab3a2e42c04f84212a62f`,
all raw-to-normalized text/timing/role records, exhausted stream, model,
source, code, PCM proof, failed-history bindings and new-PCM cleanup.
Timestamps are unadjusted. One final endpoint is 0.082 seconds beyond strict
EOF, within the unchanged frozen one-second validator tolerance; none exceeds
that tolerance. The maximum identical segment count is six. This distinct
edition is accepted for descriptive analysis. No listening or word-accuracy
comparison was performed; fewer repeated strings do not establish accuracy.

## Current decision

The declared publisher collection frame is now complete. The critic checked
the final manifest at SHA-256
`82c007e60fdddd3c970bd4831beb632dca8a3fe183bbca01a715de6d409de694`:
229 publications comprise 204 Tracy, 20 Multidimensional Soul and five OmNa
records, retaining 1,571,640,963 bytes and 258,545.2438125 decoded seconds.
There are 228 distinct original-byte families, including one two-record
duplicate family. All 229 retained audio hashes and receipts, 458 decoder-log
proofs, frame and resource bindings were rechecked. All 224 RSS GUID/enclosure
joins and 71 caption URL/GUID/enclosure joins independently matched the saved,
hash-bound primary feeds. Three retained files were freshly decoded and their
PCM hashes and sample counts matched; this included the 299.53-second Tracy
record admitted under the non-Bashar zero-minimum policy. No collection source
error is recorded. The interrupted v2 attempt remains outside admitted counts.

This completes the specified publisher frame, not all YouTube uploads or all
historical recordings. ASR may continue on verified inputs under these
contracts. Public releases must use frozen snapshots, distinguish retained
sources from original/derived files and transcript editions, retain
unadmitted attempts outside success counts, and show running/failed/complete
states as observed. Full media and transcripts remain private; code,
metadata, aggregates and bounded reading paraphrases may be published.
