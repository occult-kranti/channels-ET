# Independent harvest and release review

This review concerns the new acquisition/deployment supplement. The reviewed paper, models and historical releases stay frozen. Tests using local fixtures do not count as empirical source collection.

## Completion claims

- A channel is an explicitly dated route/listing scope. Record videos, Shorts and stream tabs or the extractor's equivalent nested containers separately. A returned playlist container is not a video or a reason to declare an empty channel complete.
- Record public-listing exhaustion, locally capped/partial enumeration, extractor failure and unavailable/ignored slots separately. Exhausting a returned public list cannot establish access to private, deleted, age-restricted, paid or otherwise unavailable uploads.
- Deduplicate video IDs across routes without discarding route/practitioner attribution. Upload identity, source session, publisher, practitioner and inferred speaker remain different fields.
- A zero-exit downloader is insufficient for success. Every completed artifact must exist, be nonempty, have a supported type, match the requested upload and be hashed from its final local bytes. A failed merge or missing fragment cannot certify complete media.
- Captions, audio-only files and audiovisual files have separate requested and observed types. Audio-only fallback cannot fulfill an audiovisual download claim. ASR/manual track labels are not accuracy validation.
- Resumption revalidates retained artifacts, including existence and hash, instead of trusting only an archive ID or prior success row. Preserve previous failures and partial results. Terminal denials and potentially retryable failures have distinct states.

## Parallel execution and resource bounds

- SQLite claims use a transaction and one lease per work item. Expired leases may be reclaimed, but cannot let an older process finalize a new owner's job. Each final update binds the current lease owner/token.
- Global reserved bytes, actual raw-tree usage and free-space reserve are reconciled transactionally. Unknown remote size is not zero. Merging can temporarily need both component files and the final file.
- Watch quotas while processes run and recheck after fast process exit. Include partial files, temporary fragments, subtitle/metadata sidecars and failed downloads in actual usage. Stop subprocess descendants when stopping a job.
- Downloader fragment concurrency and job concurrency are separate; document their combined resource envelope. A shared yt-dlp archive locks appends but each process retains a separate in-memory set, so the work queue must independently prevent duplicate same-ID jobs.
- Whole-state JSON writes and log appends must not race; an authoritative transactional database or single writer must preserve every attempt and output relation.

## Release acceptance

- Raw media, captions, logs containing signed URLs and credentials remain outside Git. Public records expose bounded diagnostics, source URLs, types and hashes rather than temporary authorization URLs or environment secrets.
- Release summaries reconcile requested, attempted, success, partial, quota-stopped, blocked, unavailable, failed and pending work. No failure is silently promoted to ignored success.
- A download manifest is an inventory, not evidence that every listed item was downloaded. Release totals must reconcile to actual verified artifact rows.
- Git push and GitHub Pages deployment have separate commit/run/URL receipts. A workflow file, queued Action or successful push alone does not certify a deployed site; bind the successful deployment to the intended commit and inspect the served artifact if access is available.

These are acceptance criteria before inspection of the new worker. Findings and executed checks will be recorded against actual source hashes.
