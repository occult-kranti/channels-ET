# Bounded completion refresh

`refresh_pipeline.py` watches this **existing 229-publication publisher frame** once. It does not fetch new media, start recognition, or run a recurring job. It waits for the reviewed standard ASR queue and the two explicitly requested fallback decisions. It refreshes source-context descriptive analyses only; it generates no doctrinal, speaker-identity, or agreement claims.

The 292-unit joint study, 20-message written pilot, semantic pilot, and 21-page companion paper retain their pinned inputs. The 21-page core paper excludes the later collected-audio and semantic studies. The earlier 27-text collected-audio snapshot remains documented in the release handoff; each future fit is a separate version and does not silently change those results. Linked captions can already belong to older studies; exact audio/text aliases are not independent observations.

## Before launch

Review and commit the watcher, tests, UI and currently verified assets. Check out `main` at that reviewed commit; the live remote `main` must match. The entire worktree and index must be clean. The current queue must have resumed successfully after any diagnostic requiring review. **Do not launch against a halted queue.**

The reviewed v4 policy binds an initial two-source hold ledger and the exact queue code. Later exhausted timestamp failures can be quarantined only by that pinned policy: every added hold must preserve its source/model/diagnostic proofs, declare automatic policy application, and remain unadmitted. It must not be described as an individually reviewed or human-reviewed source. Changed policy/frame, unknown status, global errors or additional fallback attempts require a reviewed successor; do not remove guards to force completion.

Each of the two independent fallback verdicts must be `accepted_for_analysis` or `accepted_unadmitted_hold` and bind its exact terminal manifest and receipt. The authorized publications are `@akanksshaa:rss:f35e0cfac4d68e2c` and `@akanksshaa:rss:b9fd4b8c29ce9611`, with separate `publisher-asr-fallback-v1` and `publisher-asr-fallback-v2` outputs. No undeclared retries are admitted. A pending verdict waits within the declared deadline and can never publish. `halted_*` queue statuses stop immediately. The actual declared source sets must partition into accepted recognition, exact publisher captions and reviewed holds; completion counts alone are insufficient.

## Commands

Read-only status (no transcript bodies or credentials):

```bash
git status --short
git rev-parse HEAD
git branch --show-current
python - <<'PY'
import json
from pathlib import Path
base=Path('/workspace/channels-et-private/subscription-screening-2026-11')
for name in ('publisher-audio-v3/manifest.json','publisher-asr-v2/queue-status.json','publisher-asr-fallback-v1/manifest.json','publisher-asr-fallback-v1/independent-review.json','publisher-asr-fallback-v2/manifest.json','publisher-asr-fallback-v2/independent-review.json'):
    p=base/name
    if not p.exists():
        print(name, 'not present')
        continue
    value=json.loads(p.read_bytes())
    print(name, {k:value[k] for k in ('status','completed_count','frame_count','source_count','asr_candidate_count','recognition_hold_count') if k in value})
PY
```

Run the guard suite:

```bash
python -m unittest discover -s research/expanded-channeling -p test_refresh_pipeline.py
/workspace/channels-et-analysis-venv/bin/python -m unittest discover -s research/expanded-channeling -p test_collected_audio.py
```

Replace `FULL_REVIEWED_COMMIT_SHA` with the exact reviewed 40-character commit. Choose a fresh private output directory for each attempt. This example performs a private dry run; it never writes public files, the Git index or a commit:

```bash
/workspace/channels-et-analysis-venv/bin/python research/expanded-channeling/refresh_pipeline.py \
  --expected-head FULL_REVIEWED_COMMIT_SHA \
  --output /workspace/channels-et-private/expanded-channeling-2026-11/completion/dry-run-01 \
  --dry-run --once
```

`--once` exits safely when work/review is pending. Omit it to check every 30 seconds, for at most 48 hours by default (`--max-wait-hours`, maximum 168). For the approved single live watch, omit `--dry-run`, use another fresh output path, and redirect stdout/stderr to a **private** log. `--no-push` creates only the verified local commit; it never pushes. A completed dry run cannot be implicitly resumed into publication: use a new fresh run with the same verified HEAD.

## What is guarded

- Exact source frame, source records, selected snapshot lineage, ASR artifact hashes, bound review decisions, duplicate IDs and the publication partition.
- A narrow repeated-segment degeneration check. This is not recognition-accuracy validation.
- No symlinks or parent traversal; frozen source inputs stay outside Git. Temporary fit/site copies use mode-0700 RAM directories only with sufficient finite cgroup headroom. Otherwise the stricter disk budget must pass.
- At least 2 GiB plus 128 MiB free disk, with additional measured copy budgets. Raw fit artifacts are capped at 128 MiB. Executed code, source provenance, frozen input bindings, SQLite, output manifests, original figure edition and approved public bytes are retained durably under the private output before publication. RAM paths are not archival storage.
- Eleven literal metadata/figure destinations only: three identical acquisition metadata copies, the subscription audit JSON, the collected-audio JSON, and its six figures. No recordings, full transcripts, private paths, credentials, model weights or source SQLite enter Git. The reviewed prior public structure is a closed field contract; novel output fields require review. Three explicit v4 failed-edition fields (`review_status`, `quarantine_policy_sha256`, `human_reviewed`) are a reviewed extension; no inferred human review is allowed.
- Existing source-topic/video-index references are retained. All Pages, screening, joint, pilot, registry, collected, semantic and paper verifiers run on the privately staged release.
- Exact clean HEAD before and after staging, unchanged target bytes, no foreign working/index changes, exact staged and committed blob hashes, expected parent, and live remote HEAD. A race stops without `reset`, `clean`, force push, or overwriting another person's changes. Publication uses a literal approved GitHub URL and an explicit commit SHA. GitHub Pages CI verifies the pushed assets again.

There is no filesystem-wide lock against unrelated tools. The watcher takes its own exclusive lock and checks for concurrent Git/worktree changes; if another tool edits during publication, it stops for review and may leave only its explicitly enumerated local changes or a local unpushed commit. Do not blindly rerun against a dirty tree. Inspect the private approved-publication manifest and Git diff first.

After successful publication or a `--no-push` commit, it creates a fresh **private** archive navigator and text ZIP from the same frozen acquisition/merged-recognition inputs. A navigator failure is reported separately and does not conceal a successful Git commit/push. Audio remains referenced in place. The private output `completion.json` states commit/push and archive outcomes; `input-bindings.json`, `recognition-diagnostic.json`, and `approved-publication.json` retain the audit trail. Log errors are safe status codes, never raw subprocess errors containing URLs or secrets.

## Stop and resume

A halted queue or unexpected state ends with `stopped_requires_review`; nothing is published. Diagnose the original private queue logs with the media reviewer. Preserve failed recognition editions and do not add them to accepted manifests. A v4 source-specific timestamp hold needs exact evidence and validation under the independently reviewed policy. Other failure classes or additional alternate-recognition attempts need a separate reviewed decision and explicit contract update. The initial two hold rows cannot be changed or removed; their accepted alternate editions change current transcript availability while retaining failed-edition history.

Once the queue and contract are reviewed, commit any necessary code change and use the new exact clean HEAD and a fresh output directory. A changed remote branch, edited worktree, expired deadline or insufficient disk/memory is not permission to override the guard. The existing snapshot remains usable while the new run waits or stops.
