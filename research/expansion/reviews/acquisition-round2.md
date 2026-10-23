# Expansion panel — acquisition round 2

Artifact reviewed: round-1 `collect.py`, generated 590-query/157-route frame and
the revised acquisition README. Reviewer: acquisition model-agent, with coordinator
method findings; this is not human validation. Previous releases remain intact.

## Findings and implemented corrections

1. **Template mismatch (accepted).** The companion methods document implied
   spelling/medium variants absent from the plan. The methods owner aligned the
   executed plan to three actual templates plus differing entity labels. Additional
   variants remain proposed recall sensitivity; the 590-query plan is unchanged.
2. **Repeated prefix (accepted).** Small repeated runs could select only the same
   early candidates. Added repeatable `--person-id`/`--job-id`, round-robin ordering
   by inherited practitioner ID, and explicit `--resume` that preserves previous
   records while skipping attempted jobs. Failed jobs require a new dated targeted
   run after diagnosis; resumption does not silently retry them.
3. **Discovery versus observation (accepted).** Flat playlist metadata is partial.
   Added `metadata --input` for separate public-watch refresh of deduplicated
   discovered video IDs; source-input provenance and response hashes remain attached.
4. **Automation status (accepted).** Collector previously always returned shell
   success even on blocked operations. It now returns status 2 for a current batch
   with failed, blocked or unavailable operations, while preserving the ledger.
5. **Safety/recovery evidence (accepted).** Added `verify_safety.py`: six real local
   control tests verify stop-on-block, nonzero status, resume record preservation,
   identity filtering, overwrite protection, raw-caption Git exclusion, nested
   discovery-ID deduplication and round-robin ordering. All six passed; fixture
   provider responses are explicitly non-empirical, and no network requests occurred.

Current access remains the recorded blocked preflight, not a new observation of
platform availability. No unsupported access retry was made. Next round must check
the integrated dashboard/paper's collection counts and planned/executed wording,
plus any further acquisition evidence that becomes available after a state change.
