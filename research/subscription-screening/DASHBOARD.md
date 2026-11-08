# Subscription screening dashboard

`dist/subscription-audit/` is a standalone static companion to the existing research dashboard and Bashar–Ra study. It publishes researched account metadata and coverage, without publishing the submitted screenshots or raw source transcripts.

## Data contract

The page loads same-directory `data.json`, schema version 1, with `generated_at`, `scope`, and a `channels` array. Each account has a unique normalized `id`, display `name`/`handle`, `status` (`include`, `exclude`, or `uncertain`), `status_reason`, `research_category`, `channel_url`, optional canonical `youtube_channel_id`, and evidence objects containing `label`, `url`, and `note`.

`status_reason: "user_requested"`, `user_requested_exclusion: true`, or the normalizer's `user_excluded: true` overrides other classification and displays an exclusion. Jamie Butler's exclusion must remain in the normalized data as the user's decision; a researched category cannot override it.

The `counts` object supports numbers, nulls, or `{value, basis, url, checked_at}` objects for:

- `public_uploads_observed`
- `eligible_5min_observed`
- `audio_sources_retained`
- `video_sources_retained`
- `transcribed_sources`
- `analyzed_sources`
- `historical_caption_analyses`
- `historical_title_analyses`

`observed_uploads_are_total` is false unless explicitly true in the source data. `inventory_checked_at` records the actual observation. The current fields are displayed as **Indexed video IDs**, with an explicit **Total uploads: unknown** cue. They come from inherited historical handle routes, not a fresh uploader-identity verification or channel census. `inventory_basis` supplies the counting basis when the historical count is a plain number rather than an object.

Historical caption records and their current retention status can be supplied as `historical_caption_records` and `historical_caption_retention_status` at the account level or under `counts`. Historical caption/title analyses are displayed separately from current pipeline counts. A prior analysis does not establish that its full text is retained now.

Unknown current counts and retention remain unknown, and export as blank cells. Zero is displayed only when the normalized data explicitly report zero after reconciliation. Audio, video, transcribed and analyzed counts are separate stages; the UI never infers one from another.

## Behavior and verification

The page provides search, screening-decision and researched-category filters, an unreconciled-coverage filter, pagination, source-linked account inspectors, and a CSV export of all filtered records rather than only the visible page. Table scrolling is local, and dialogs have native Escape handling, explicit Tab/Shift-Tab cycling and focus restoration. Decisions use text and shape as well as color.

The separate per-video section reads `videos[]` records with `video_id`, `channel_id` or `channel_ids`, title, URL, duration, recorded eligibility and collection status. Its search, account-route/duration/status filters and pagination are independent of account screening filters. Current audio/video/transcript/analysis stages remain unknown unless supplied explicitly; historical caption-analysis notes use exact video-ID matches against historical caption records. Its CSV exports every filtered inventory row. Account inspectors can navigate to the corresponding video view with keyboard focus preserved. Publisher/RSS records are not silently merged into this YouTube inventory.

It reuses `../bashar-ra/styles.css`, adds its own small stylesheet, and has no external JavaScript/font dependency. All local asset paths work under the GitHub project base path. Source links allow only HTTP(S) URLs without embedded credentials. CSV cells protect spreadsheet formula prefixes; a literal video ID beginning with `-` receives the same spreadsheet protection and is verified against its original ID after removing that protective marker.

After root integration supplies the actual normalized data, serve the repository over local HTTP and run:

```sh
node research/subscription-screening/dashboard_check.mjs
```

The harness uses the real release at 320, 390 and 1440 CSS pixels. It checks source identities, Jamie Butler's authoritative exclusion, all decision/category/coverage filters, unknown-versus-zero CSV preservation, pagination, dialogs, empty states and failure recovery. Isolated HTTP/synthetic-flag tests use request interception and do not create public fixtures. It records screenshots, download hashes and before/after source hashes privately. UI checks do not validate the research classifications or establish complete account inventories; those require their cited evidence and receipt reconciliation.

Root integration owns normalized data, inventory reconciliation, publication and navigation from the existing dashboard. Research agents own account classifications and evidence. This page and its browser harness own presentation and interaction behavior.
