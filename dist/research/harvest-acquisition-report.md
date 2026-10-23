# Indexed-source acquisition handoff

Generated 2026-10-23T22:54:40.493793+00:00 from the separate ledgers below. This collection supplement
continues in `occult-kranti/channels-ET`; the Bashar checkout remains preserved at
`151efb25824dd54768edef7b71ca2a22f1c6d1ac`.

**Live dashboard:** https://occult-kranti.github.io/channels-ET/
→ Acquisition. The official [Pages workflow](../../.github/workflows/pages.yml)
publishes reviewed static artifacts. It performs no remote media collection.

## Actual collection state

| Unit | Observed count/state | Authoritative record |
|---|---:|---|
| Unique indexed YouTube IDs | 942 | [Inventory](inventory/summary.json) |
| Literal channel routes / explicit playlists | 362 / 169 | [Routes](inventory/channel-routes.json), [playlists](inventory/playlists.jsonl) |
| Keyword discovery queries | 597 | [Query provenance](inventory/queries.jsonl) |
| Prepared typed jobs | 3,357 | [Worker summary](summary.json), [SQLite](state.sqlite) |
| YouTube worker attempts | 0 | [Attempt ledger](attempts.json) |
| Saved YouTube videos / caption artifacts | 0 / 0 | [Artifact ledger](artifacts.json) |
| Independent publisher audio | 19 / 19 selected episodes | [Publisher ledger](publisher_sources/publisher-summary.json) |
| Completed publisher-audio bytes | 1,664,529,703 | Actual locally hashed bytes |
| Completed publisher-audio duration | 22.225 hours | Actual `ffprobe` duration |
| Current-response editions with RSS metadata warnings | 4 | Strict attempts plus source-specific review amendments |
| Full decoded-audio ASR passes | 19 | [ASR summary](asr/summary.json) |
| Audio processed by those passes | 22.225 hours | Source-hashed local audio |
| ASR segments / whitespace-delimited words | 20,938 / 222,699 | Actual saved machine outputs; unverified recognition |
| Publisher / ASR dispatcher state | `completed` / `completed` | Ledgers are independently timestamped |

Publisher sources not yet completed in this snapshot: 0.
ASR rejected receipts: 0. Source inventory, typed
jobs, files, audio hours, platform captions and ASR passes are distinct units.
The inventory is a purposive union, not a census or completed channel crawl.

The single fresh ordinary YouTube watch probe failed with a **proxy CONNECT 403
before TLS**. It is a global access preflight, not 942
failed video attempts. Desired network policy was already unrestricted; root
observed enforced revision 5 while other actors observed unknown enforcement.
Retained diagnostics supplied no explanatory records. This is an unresolved
access condition, not proof of an extractor defect. See the dated
[probe](access/preflight-2026-10-23-revision5.json) and
[toolchain receipt](access/toolchain.json). Do not repeat requests absent a
meaningful access change or diagnosis; obtain one fresh ordinary successful
probe before a bounded worker batch.

## Methodology and implemented tools

The inventory preserves original Bashar index links, the Atlas source layers,
literal channel routes, playlist IDs and keyword queries with source hashes,
JSON pointers and typed relationship edges. Stable upload IDs deduplicate jobs;
shared titles or names do not merge practitioners, publishers or original
sessions. The 925-upload frozen scientific
sample remains distinct from this 942-ID collection frame.

We read official yt-dlp, EJS, youtube-transcript-api, FFmpeg, GitHub storage/Pages
and relevant downloader implementation guidance. The
[source register](tool-research/PRIMARY-SOURCES.md) records URLs, immutable Git
commits, hashes and reading depth; [recommendations](tool-research/RECOMMENDATIONS.md)
explain the tool choices. This is source-backed engineering work, not a successful
YouTube client trial. Browser extensions or alternative clients were not used
to route around the explicit proxy denial.

The implemented worker uses `yt-dlp==2026.10.21`, matching
`yt-dlp-ejs==0.8.0`, Node 24 explicitly selected as its JS runtime, and FFmpeg.
It has SQLite atomic claims, finite leases and heartbeats, bounded parallelism,
retry/backoff, an access-denial circuit breaker, separate manual/automatic
caption tracks, listing cursors and explicit playlist expansion. Byte hashes,
`ffprobe`, unavailable-fragment failure and changed-file quarantine guard actual
media certification. The current tests are offline adversarial fixtures; they
do not establish live extractor compatibility or complete platform coverage.

Independent publisher RSS episodes were followed from the original index's
22 Apple-linked podcast rows using catalog-to-feed bridges, episode GUIDs,
titles and dates. Nineteen original-publisher episodes were selected; an
explicit third-party redistribution and paid-TV entry were excluded, and one
older episode was absent from the current limited feed. These are independently
published audio editions, not downloaded YouTube videos. Interviews, a promotional
podcast edition and skeptical commentary retain
their source-format labels. Guest, host, advertisements and claimed-entity turns
have not been diarized or verified. [The frozen plan](publisher_sources/expanded-plan.json)
contains exact inclusion rules and source cautions.

Publisher download concurrency is two with HTTPS verification, shared quota
locking and validator-bound partial-file resume. A complete HTTP response can
disagree with the RSS size or duration. Such bytes first fail strict validation;
specific independently reviewed amendments may retain the captured current
publisher edition with its exact warning. Strict original events and hashes
remain available. Advertising or edition changes are hypotheses, not established
explanations. Expiring delivery URL credentials are redacted; stable original
RSS enclosure URLs remain the reproducible locators.

Local ASR uses `faster-whisper==1.2.1`, CTranslate2 CPU int8, PyAV 16.1.0 and
the hash-pinned MIT `Systran/faster-whisper-tiny.en` conversion. Two processes
with two CPU threads each decode English with beam size 1 and VAD. Existing
outputs are reused only after source, settings, executed code and file hashes
validate. The [ASR README](asr/README.md) and [queue protocol](asr/QUEUE.md)
retain the PyAV setup failure and the source-promotion recovery correction.
No GPU, human accuracy score, SOTA performance or verified speaker count is
claimed. Decoder exhaustion does not prove recognition of every spoken word.

## Storage and reproduction

Raw audio: `/workspace/channels-et-raw/publisher-audio/`.
Full ASR text, segments and SRT: `/workspace/channels-et-raw/transcripts/`.
These cloud-local files and model weights are outside Git and Pages. A fresh
Git clone supplies code and metadata, not private audio or transcript bodies;
cloud-filesystem persistence depends on retaining the environment snapshot.

The shared raw quota is 20 GiB with a 6 GiB filesystem reserve and 256 MiB
per publisher file. Main and publisher collectors hold the same process lock;
ASR has its own queue/output locks. Partial and quarantined bytes consume space.
Known indexed duration is 502.105 hours with
61 unknown lengths. Even an assumed combined
512 kbit/s video payload needs about 107.74 GiB for known durations alone, beyond
this machine's disk. Full channel expansion has no known storage upper bound.
Large-scale full-video retention therefore needs additional provisioned storage
and healthy source access; GitHub Pages publishes compact research artifacts.

From the repository root:

```sh
# Recreate/check the pinned local environments, without collection or inference:
bash research/harvest/setup_environment.sh

# After genuinely successful supported public YouTube access, follow this gate:
cat research/harvest/README.md

# Independent publisher edition collection and verified local ASR:
/workspace/channels-et-harvest-venv/bin/python research/harvest/publisher_sources/download.py --plan research/harvest/publisher_sources/expanded-plan.json
/workspace/channels-et-asr-venv/bin/python research/harvest/asr/download_model.py
/workspace/channels-et-asr-venv/bin/python research/harvest/asr/run_queue.py --watch-seconds 1200

# Refresh metadata/UI after writers finish; no collection/inference:
/workspace/channels-et-harvest-venv/bin/python research/harvest/harvest.py export
/workspace/channels-et-asr-venv/bin/python research/harvest/asr/build_summary.py
python3 research/continuation/dashboard/build_dashboard.py
python3 research/harvest/build_handoff.py
```

Reacquisition and ASR commands can perform network/compute work and update their
ledgers. Completed reuse requires matching original files; metadata alone cannot
reconstruct missing raw speech. Setup was tested on this instance; fresh-task
restoration is not independently established. Local models from the earlier
study remain separate from this new ASR stage.

## Review, deployment and next analysis

The six role-agents performed acquisition, provenance/literature, inventory,
ASR/data, dashboard and independent skeptical review; these are AI-agent technical
reviews, not human peer review. Exact assertions and findings are under
[audits](audits/), [reviews](reviews/) and [dashboard checks](dashboard/).
The [deployment receipts](../deployment/) distinguish local project-prefix tests,
successful Actions and live HTTPS hash verification. The final source release
manifest binds the current metadata and assets; historical receipts certify their
own immutable snapshots only.

The manuscript, Q&A database, figures and Qwen/RAG/LoRA experiments remain at
their earlier reviewed evidence state. Next steps are human-checked ASR samples,
speaker/advertisement segmentation, original-session and edition resolution,
literal question-answer extraction with timestamps, and new preregistered
comparisons before adding this speech to paper or training results. No topical
or answer-agreement inference is manufactured from download counts.
