# The Bashar Index — data package

Generated 2026-09-11. Companion to the published website "The Bashar Index".

- digests/*.json — 75 structured digests of public YouTube recordings (summary, paraphrased Q&A, 20-topic mix, key terms, ≤30-word quotes, dates, tools, entities). AI-generated from auto-transcripts; not transcripts.
- videos.json / recordings.csv — the same 75 recordings with metadata, content type, year reliability, archetype cluster and map coordinates.
- analysis.json / topic_share.csv / key_terms.csv — topic shares (weighted/unweighted), archetype clusters, vocabulary, entities, tools, dates/predictions, question themes, tag co-occurrence, method notes.
- topics.py — the scikit-learn pipeline that produced analysis.json.
- catalog_sessions.json / session_catalog.csv — 684 catalogued sessions and events, 1984–2027, with sources.
- podcasts.json — 48 podcast/interview appearances; skeptical_coverage.md — critical coverage.
- diagrams.json + diagrams_svg/*.svg — 56 diagram records (concept, structure notes, sources, confidence) and the original SVG redrawings (styled via CSS classes; see the site for the theme).
- glossary.json (104 terms), timeline.json (68 events), teachings.md (source-cited reference), anka_works.json, events_upcoming.json, official_channels.md, divine_light_vibes_channel.json.

Bashar® material is © Darryl Anka / Bashar Communications, Inc. This package is an independent research aid and contains no recordings, transcripts or handout artwork.
