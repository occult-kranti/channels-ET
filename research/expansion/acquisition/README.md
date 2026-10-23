# Public YouTube collection: expansion protocol

This directory implements the next acquisition phase without modifying the frozen
925-upload release. The current `preflight-initial.json` records **one blocked
watch-page probe and zero successful operations**. It is not a search-result,
caption or new-video dataset. Collection cannot proceed until ordinary public
YouTube access is available through the environment's supported network route.

## Frame, identity and planned operations

`collection-plan.json` and `identity-map.json` were generated from the retained
`dist/data.json` discovery layer and `dist/analysis/data.json` snapshot. They retain
106 practitioner/lineage/partial-name candidates, 157 indexed account routes and
925 unique historical upload IDs. These are different units. The candidates
include historical and non-ET context, unconfirmed identities and repost publishers;
they are not a census of humans, currently active mediums or verified ET channels.
No new identity or official-account check has been completed.
`identity-publisher-links.json` links 83 of the 106 candidates to retained
analysis publisher groups by exact normalized URL/explicit alias only. The other
23 have no retained exact route match. This is a reproducible inherited-attribution
join, not independent identity confirmation; one candidate can have several routes
and one route can retain several candidate attributions.

Each inherited candidate receives the exact-name templates `"name" channeling`,
`"name" questions answers`, and `"name" interview`, plus `"name" "entity"` for
each distinct inherited entity label. The resulting **590 queries are planned**,
not executed observations. All 157 account routes are queued separately. Accounts
without a named practitioner remain unresolved. Exact existing source-record edges
support the identity export; similar names do not justify merged people/accounts.

The 215 caption candidates consist of the historical 36-record purposeful pilot
followed by the lexicographically first nonpilot upload ID from each inherited
publisher that has one. The second stage broadens account coverage but is still a
convenience sample. Ordering by ID is reproducible and is not random sampling.
Language, recording format and access must be measured after acquisition and must
not be silently inferred from an English title. No multilingual or speaker
attribution validity is claimed by this selection rule.
Historical caption `person` slugs are retained as `inherited_person_key`, not
misrepresented as stable candidate IDs. Stable candidate links use only an existing
explicit video-URL edge; `person_id` remains null without a unique validated mapping.
`person_ids` preserves any inherited explicit candidate edges without promoting
them to verified speaker identities.

## Software and execution

The isolated Python environment uses **yt-dlp 2026.10.21** for public search/channel
metadata and **youtube-transcript-api 1.2.4** for offered caption tracks. They are
open-source third-party clients; they are not a guarantee of platform access,
complete search recall or caption quality. Requirements are pinned here separately
from the original analysis dependencies. `pip check` passed after installation.

From the Channeling Atlas directory:

```sh
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py plan
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py preflight --output /absolute/new/preflight.json
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py search --max-jobs 3 --per-job 8 --output /absolute/new/search-pilot.json
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py channels --max-jobs 3 --per-job 12 --output /absolute/new/channel-pilot.json
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py captions --max-jobs 6 --raw-dir /workspace/channeling-raw --output /absolute/new/caption-pilot.json
/workspace/bashar-index-venv/bin/python research/expansion/acquisition/collect.py metadata --input /absolute/new/search-pilot.json --max-jobs 8 --output /absolute/new/watch-refresh.json
```

Use a new output path for each independent run; the CLI refuses to overwrite earlier
results. `--resume` explicitly appends not-yet-attempted jobs to the same operation
ledger and preserves earlier records/run history. Previously failed or blocked jobs
are not silently retried; use an explicit `--job-id` and a new dated ledger only
after diagnosing or changing the prerequisite. `--person-id` and `--job-id` are
repeatable filters. Within a selected batch, jobs run round-robin across inherited
practitioner IDs, reducing repeated-query concentration in the first small batch;
this is not random sampling or balance across validated human identities.
Do not run acquisition until the public watch preflight succeeds. Review each pilot
before increasing the explicit caps. A larger follow-up should record its own caps,
selection and coverage. No fixed cap makes the search exhaustive. Results can rank,
disappear or differ across time/location/client. Count attempted operations and
unique retrieved IDs separately, retaining duplicate query hits and failures.
Flat search/channel fields remain a discovery layer; the separate metadata mode
accepts discovery manifests, deduplicates their upload IDs, and refreshes ordinary
watch metadata. It retains unavailable records without inventing durations or dates.
The CLI exits nonzero when the current batch has a failed/blocked/unavailable
operation. Successful no-new-job resumption is not new empirical validation.

The one live preflight was Python standard-library `urllib`, not a yt-dlp or
youtube-transcript-api acquisition run. Both clients are installed and their
collector routes are implemented; neither has successfully collected new data here.
The clients run without credentials/cookies or local user configuration. yt-dlp
uses flat playlists, disabled retries and skip-download; this pipeline does not
download audiovisual files. The inherited TLS trust and platform proxy remain
enabled. HTTP 403/429, bot challenges and access-denial responses stop the current
run. Do not retry unchanged blocked requests, rotate proxies, solve CAPTCHAs, import
browser cookies, or switch clients to evade an access restriction.

For the current environment the required ordinary destinations are `youtube.com`,
`www.youtube.com`, `youtu.be`, and, if the client requests its public API route,
`youtubei.googleapis.com`. Declaring those destinations in a draft does not change
the live policy. Recheck after the supported settings update. Video media CDN
access is unnecessary for this metadata/caption pipeline. A browser caption export
can be imported later with its provenance and rights basis; none was supplied or
used in this run. Paid, private, members-only or deleted content remains unavailable.

Raw captions are written only outside all Git checkouts, with source IDs, segment
times, original language, ASR status and SHA-256. Existing different text versions
receive hash-suffixed filenames. Public manifests contain derived counts and hashes,
not full captions. Do not treat a matching title or caption track as verified speech
accuracy. Transcription accuracy, speaker roles and question/answer boundaries need
separate inspection and validation. Caption retrieval does not establish original
session identity, a medium's identity, extraterrestrial origin or answer truth.

## Current executed versus pending state

Executed: frame generation; dependency installation; dependency consistency check;
one ordinary public watch preflight; local collector safety verification.

Pending: runtime destination access; live keyword/channel pilot; additional caption
retrieval; identity confirmation; original/repost audit; audio/manual transcript
validation; review before expansion. A failed request is missing evidence, not a
zero-video channel or a negative finding about the subject.
