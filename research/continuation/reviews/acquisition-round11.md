# Acquisition panel round 11 — inspected candidate and corrections

Frozen round-10 archive:
`5681c632f4b4f0fd857711d0d7ee2c6483bd39963cd2ff48c564d7710e7f2008`.
Exact inspected source/PDF/adapter metadata hashes are recorded in
`acquisition-round11-receipt.json`. This is model-agent technical review, not human
peer review or audiovisual validation. The reviewer owns the collector; independent
methods-role findings supplied the two adversarial corrections below. Paper,
dashboard and model release metadata were inspected across workstream boundaries.

## Collection claims and access

The 14-page candidate's collection section and dashboard distinguish installed
clients, queued operations and actual returned material. The observed operations
remain one YouTube watch preflight with proxy CONNECT 403 and one independent
primary-author transcript request with HTTP 403 of undetermined origin/intermediary.
The 106 candidate queues have zero candidate-specific search, channel or caption
attempts. General access denials are not replicated into 106 source-level failures.
Desired unrestricted policy is distinct from the unknown observed policy state and
actual responses. No new network request was made during this review.

Raw storage remains outside Git; source captions, audiovisual files, signed URL
queries, credentials and base-model weights are not introduced into the research
package. The actual corpus index contains 925 inherited metadata rows and zero
transcript artifacts. Speaker attribution remains unknown rather than inferred from
a publisher, name, claimed entity or generated answer.

## Collector findings, decisions and verification

| Finding | Correction | Acceptance evidence |
|---|---|---|
| A returned playlist batch containing an unavailable `None` slot consumed a position, but filtering it before counting could falsely signal completion and repeat a position | Count raw returned slots separately from usable video records; preserve unusable-slot count; advance by consumed positions | Adversarial batch `[video, None, video]` at cap 3 remains incomplete and resumes at position 4 |
| A fast downloader could exit successfully before a polling quota check observed an oversized file | Post-exit validation checks actual file bytes, total raw bytes and free reserve; excess becomes `quota_stopped`, with local hashes retained and no successful artifact | Finished-zero fixture writing cap+1 byte is rejected; successful-media count remains zero |
| Completion could be read as platform-wide exhaustiveness | Retain explicit end-of-returned-public-listing scope; document dynamic positional pagination and unavailable/private/deleted material | No complete-channel, original-session or all-video acquisition claim appears |

All ten collector tests pass without network requests. The two new regression
fixtures are control tests and were removed with their temporary directories.
Existing 2 GiB raw quota, 4 GiB free reserve, 128 MiB file cap, rate/time limits,
caption-write quota and successful-preflight gate remain active. Planning estimates
are not downloaded byte measurements. Polling may permit small transient overshoot;
post-validation prevents certification of an oversized completed artifact.

## Adapter release provenance and licensing metadata

The inspected pilot ZIP matched its packaging receipt and all five member hashes.
Its base identifier and exact revision matched `adapter_config.json`; bundled
Apache-2.0 license bytes matched the verified base-model manifest. The README
correctly describes a 48-example, one-epoch adapter trained on inherited digest
paraphrases, excludes raw speech/base weights, and withholds expert-model claims.

One release-provenance correction was requested from the model owner: bind the
standalone adapter package to source Q&A hash, split/protocol hashes, training row
IDs and digest source hash/pointers. The bundled hyperparameter/loss receipt alone
did not provide those bindings. A metadata-only training-source manifest and a
notice distinguishing base/adapter licensing from inherited digest-data provenance
are appropriate; no retraining or quality conclusion follows from this finding.
Round 12 must verify the actual revised package and its hashes.

## Disposition

Collector defects found in this loop are corrected and locally verified. Adapter
provenance correction is outstanding at this receipt. Live YouTube and primary-source
collection remain unresolved access branches; software controls and model downloads
do not constitute new channel transcripts. The previous Bashar repository remains
unchanged.
