# Canonical source frame

The analytic unit is one selected English text edition for one reconciled publication/body family. It is not one YouTube upload, an independent historical channeling session, a verified medium utterance, or one newly downloaded recording.

`sources.py` reuses the accepted loaders for the joint292, completed publisher228, knowledge25, legacy primary17 and Crimson10 frames. It checks original text artifacts and the retained accepted receipt chains. No network collection, model inference, transcription or source speaker verification occurs here. All 572 candidate rows reconcile to 493 selected units and 1,411,446 whitespace words. The earlier cohorts and all their source artifacts remain unchanged.

## Private loader

```python
docs = sources.load_frame('/private/frame-01/frame.json')
for doc in docs:
    record, text = doc['record'], doc['text']
```

The loader returns a list in frozen `row_index` order. Each selected artifact's byte hash and byte count are checked before applying its declared reading transform; its normalized body hash and word count are checked afterward. Bodies use Unicode NFKC plus outer-whitespace removal. Selected legacy HTML-caption readers additionally remove markup and decode entities exactly as their accepted loaders do. All offsets are Python Unicode character positions in this normalized body, end-exclusive. Audio timestamps cannot be inferred from text position.

`frame.json` contains private paths and must never enter public Git or the dashboard. The frame stores references, not duplicate corpus text. `registry.json` is its public metadata projection. `output-manifest.json` allowlists only `registry.json`; its hash binds that release.

## Publication and edition identity

Each `source_id` is `doc-` followed by 20 hexadecimal characters of the canonical publication identity hash. It remains stable if another verified edition of that publication is selected. `selected_edition_id` and `legacy_source_ids` provide explicit joins to earlier source receipts, cards, and recognition runs. `publication_id`, `recording_family_id`, `audio_sha256`, `media_sha256`, and `body_sha256` represent different units.

Union rules are exact normalized body hash, exact encoded media hash, exact individual publication URL, or collection-scoped declared publication/family ID. Container URLs are never individual-document keys: guest podcast episodes use their explicit enclosure identity rather than their common RSS feed, and Magenta PDFs use individual download URLs rather than the shared articles index. Conservative URL normalization lowercases the host, normalizes hexadecimal escapes, strips fragments/trailing slashes, and preserves query strings and path case. No similar-title matching or unsupported cross-platform equivalence is used.

Publication/family IDs are scoped to their channel context to avoid collisions such as two different publishers using item `1`. Exact-body reprints can still join across contexts, but every original context is retained in `original_contexts` and flagged by `cross_context_alias`. This observed frame has zero cross-context exact alias groups. The selected context is deterministic and does not authenticate the author or claimed speaker.

`alternate_editions` binds every distinct accepted edition to the canonical source. Reused same-artifact rows appear once in this ledger. `merge_links` records the exact join rule and value. `upstream_dispositions` preserves upstream exclusions/duplicate decisions rather than silently admitting pending or superseded records. These records are metadata, not independent observations.

The canonical selection favors the previously inspected body-only written editions, then linked publisher captions, then accepted baseline ASR. This resolves one Daniel RSS/body overlap and pairs five OmNa written messages with their corresponding audio ASRs. Ten Crimson source-bound video ASRs remain the accepted primary selection; their publisher PDF references were not substituted. New Parakeet recognition editions belong in the separate paired sensitivity/batch ledger and do not silently replace these selected bodies or old evidence spans.

## Context, dates and states

`channel_id` identifies a publishing/collection context, while `creator_id` identifies the named creator context and `publisher_id` identifies the actual publishing organization/show. Official Bashar is separate from 13 guest podcast contexts. The Pamela Aaralyn guest interview uses its Inspire Nation publishing context and remains distinct from Pamela Rose Kribbe's written sources. Mixed interviews do not acquire identified speaker turns from these labels.

The 14 distinct `creator_id` values are attribution-context categories, not 14 authenticated people. Official Darryl Anka and mixed-speaker Darryl guest contexts deliberately have separate IDs; the Ra session context and Akanksshaa host context also name collective or mixed material. Any macro-average over this field must be labeled **creator-context**, not a person census or a medium-population estimate.

`claimed_label` is the selected edition's printed attribution; `claimed_labels` retains compatible metadata labels from joined editions. These are source claims, not independently authenticated identities. `mask_phrases` provides known contextual names for a disclosed, incomplete name-masking sensitivity. It is not an exhaustive entity recognizer.

`publication_date` is normalized source metadata, nullable; `publication_date_raw` preserves the source value. Publication dates are not necessarily original speech dates. An upstream known Unix-epoch placeholder stays excluded from chronology. `duration_seconds` remains null without a positively joined recording; words are not used to invent duration.

`media_sha256` is the retained encoded file hash. `media_hash_kind` distinguishes encoded audio from encoded video. Crimson hashes identify video files and therefore have `audio_sha256: null`; their `recording_id` starts `media-sha256:`. Other joined encoded audio uses `audio-sha256:`. These are not decoded PCM hashes. A retained-file state does not validate transcript accuracy or audio/text alignment. Ra's independently retained linked archival segments remain in the upstream archive ledger; this text frame does not invent session-level alignment or sum absent joins.

Every selected text has English eligibility inherited from its accepted cohort and records the available language basis. This is neither new human language detection nor recognition validation. Text scope preserves extracts, written responses, full ASR and mixed material rather than labeling everything complete historical sessions.

## Public coverage and validation

There are 26 modeled publisher contexts, 12 screened YouTube account references, and 17 historical caption-metadata references. The latter two kinds are separate coverage rows, never extra analytic observations. The 17 historical rows retain earlier indexed-upload and caption-count denominators; their original private caption bodies are unavailable here and excluded from this new fit. Linked publisher texts are not counted as YouTube downloads. Lifetime uploaded totals remain `null`.

Per-context `canonical_text_units`, `selected_words` and `retained_recording_units_joined` have distinct units. `analyzed_text_units` is initially null for eligible primary contexts because actual completion must come from the analysis artifact, not a source-loader claim. Metadata-only contexts have zero new modeled units. Join dashboard outputs by canonical source IDs or exact declared publication/media aliases, never by fuzzy display names.

`verify_registry(root)` is a standard-library-only CI gate for count integrity, row ordering, duplicate bodies, channel membership, selected-edition joins, hash types and private-path/body leakage. It validates public metadata consistency; only `load_frame` can validate retained private body bindings. The source tests exercise ID collisions, exact body joins, source/edition distinction, tamper detection and publication URL preservation.

The accepted private release is `frame-02`. Its predecessor remains intact. Independent review identified that 67 official Bashar rows exposed retained audio through the direct `audio_artifact` field rather than the first loader's narrow evidence-role selector. The correction adds those exact upstream joins, reaching 82 official text/media joins. Every ordered `(source_id, row_index, body_sha256, words, selected_edition_id)` tuple is unchanged; `metadata-correction.json` records both frame hashes. This is a metadata correction, not another corpus fit or more downloaded audio.

`source_coverage.py` adds the separate allowlisted `collection-coverage.json`, bound to the registry and existing public collection/acquisition ledger hashes. It distinguishes Ra's 2,620 linked audio segments from 106 selected session texts, 86 retained official Bashar publication records/84 media families from 82 canonical modeled texts, and 204 retained Tracy publications from 203 exact families. Five OmNa audios accompany eight written canonical messages. These denominators must never be added as unique observations or used as lifetime upload completion percentages. Its standard-library `verify(root)` gate checks the explicit registry join and units; absent archive-wide totals are unknown, not zero.
