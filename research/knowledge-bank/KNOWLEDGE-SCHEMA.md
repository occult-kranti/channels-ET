# Knowledge-bank data interface, version 1

`knowledge.json` is the sanitized public payload; `questions.sqlite` is its
queryable companion. Full source text, documentary wording and supporting slices
stay in the private evidence database. The larger numerical study is separate.

- `coverage`: source-frame, source-reading, question, card and comparison counts.
- `sources[]`: `source_id`, title, source_url, medium_id, medium, claimed_label,
  comparison_label, comparison_level, document_kind, prior_frame, published_at,
  words, text_artifact_sha256, body_sha256, attribution_scope, speaker_role,
  identity/alignment status. No local paths.
- `questions[]`: `question_id`, `question_type` (`analyst_constructed` or
  `documentary_printed_paraphrase`), `question`, `topic_id`, `selection_basis`,
  `informed_by_answer_reading`, optional documentary-source/artifact/turn binding.
  Public documentary questions are labeled paraphrases of printed questions.
- `cards[]`: `card_id`, `question_id`, `source_id`, `paraphrase`, `claim_type`,
  `conditions`, `time_scope`, `qualifying_note`, `supports[]`, `annotation`.
- `supports[]`: `source_id`, `body_sha256`, `text_artifact_sha256`,
  `start_character`, `end_character` (NFKC stripped body; end exclusive),
  `span_sha256`, `words`, optional turn_ids/start_seconds/end_seconds.
  Text slices are private; ASR speaker roles and timing accuracy stay unverified.
- `comparisons[]`: `comparison_id`, `question_id`, `left_card_id`, `right_card_id`,
  `relation`, `reason`, `matching_context`, `qualification`, source label scope.
  Relation vocabulary: `shared_proposition`, `compatible`, `different_focus`,
  `conditional_tension`, `explicit_contradiction`, `unresolved`. A zero count is
  valid. These are bounded AI readings, not labels predicted from cosine scores.
- `topics[]`: stable topic_id, title and scope.
- `graph`: typed nodes and edges for source/medium/printed-label/question/card/
  comparison provenance. An attribution edge is not physical entity evidence.
- `reading_coverage[]`: actual unique inspected spans/words per source;
  source bodies modeled is separate from bodies or passages read.
- `limitations[]`, `input_bindings[]`, `annotation_provenance`.

Queries and cards are developed with source answers visible. Any retrieval
comparison using them is a source-retrieval diagnostic, not held-out accuracy.
No similarity threshold turns linguistic overlap into agreement or contradiction.
Contradiction requires the same proposition, referent, conditions and time, with
incompatible assertions. Differences in emphasis or optional practices are not
contradictions. Shared named labels do not authenticate a common speaker.

The frozen private source frame is `knowledge/frame-01.json`. Its loader is
`knowledge_sources.load_frame(path)`, returning `(docs, frame)`, where each item
has `record` metadata and the checked normalized `text` used for character spans.
The metadata includes private `text_artifact` references. Consumers must sanitize
them before publication. Reuse of a text edition is not a new observation.
