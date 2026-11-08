# Retrieval, database and graph interface — version 1

The producer is `retrieve_graph.py`. Its source universe is the unchanged,
hash-verified 493-document Channel Lab frame. No source bodies are public.

## Files and module keys

- `database-public.sqlite`: safe metadata, extraction statuses/locators, curated
  questions/cards and public annotation full-text search.
- `database-private.sqlite`: the same relational keys plus exact selected bodies,
  500-word passage FTS5 and private question/answer/evidence text. Never publish.
- `database.json`: `{schema_version,status,bindings,coverage,tables,search_scope,
  public_database,limitations}`; `public_database` is a file/bytes/SHA-256 reference.
- `graph.json`: `{schema_version,status,bindings,coverage,node_types,
  relation_types,nodes,edges,limitations}`.
- `retrieval.json`: `{schema_version,status,bindings,settings,coverage,queries,
  summaries,controls,limitations}`. Each query has its frozen ID/text/type/family,
  known support IDs, exact support locators and four `conditions`. Each condition
  reports `top_results` (at most ten), known-support ranks and metrics. Full rank
  lists and query vectors are private numerical witnesses.

The parent release manifest will expose these as `database`, `graph` and
`retrieval` modules. Source profiles, record shards and curated readings are
upstream modules with their own hashes.

## Database tables

`meta(key,value_json)`; `sources(source_id,title,source_url,channel_id,creator_id,
publication_date,text_origin,body_sha256,selected_edition_id,words,metadata_json,
body)`; `profiles(source_id,profile_json)`; `records(record_id,type,source_id,
question_origin,answer_status,speaker_status,question_text,answer_text,
context_text,metadata_json)`; `questions(question_id,question_type,question,
metadata_json)`; `cards(card_id,question_id,source_id,paraphrase,conditions,
time_scope,qualifying_note,metadata_json)`; `evidence(evidence_id,source_id,
body_sha256,start_character,end_character,span_sha256,words,role,text,
metadata_json)`; `record_evidence(record_id,evidence_id)`;
`card_evidence(card_id,evidence_id)`; `passages(passage_id,source_id,
start_character,end_character,word_start,word_end,span_sha256,text)`.

Public `body`, record question/answer/context text, evidence text and passage text
are absent or null; the public database contains no passage rows. Curated
question and card paraphrases remain public. Full original metadata paths and
private artifact references are not copied into public JSON columns.

`public_search` is FTS5 over approved public source title, lexical outline,
curated question and qualified answer-card text, with typed `item_id`,
`item_type`, `source_id` and `text` fields. `passage_search` exists only privately.
Source/channel/creator/date/origin filters operate on source IDs with bound
parameters. Free text is safely tokenized and quoted as an OR expression; SQL or
FTS operators supplied in user text do not execute as operators.

## Typed graph

Nodes: `{id,type,label,source_id?,channel_id?,creator_id?,record_id?,topic_id?,
source_ids?,status?,publication_date?,text_origin?}`. Types are
`publisher_context`, `creator_context`, `source`, `lexical_factor`,
`observed_claimed_label`, `question`, `answer_card`.

Stable IDs: `source:<canonicalID>`, `channel:<channelID>`, `creator:<creatorID>`,
`topic:T01`, `label:<SHA16 of exact label>`, `question:<questionID>`,
`card:<cardID>`. An exact label node records printed attribution, not an
authenticated entity shared by its sources.

Edges: `{id,source,target,relation,origin,evidence_ids:[],weight?}`. Relations:
`published_by`, `attributed_context`, `observed_label`, `factor_weight`,
`asks`, `responds_to`, `supported_by`, `derived_semantic_neighbor`.
`factor_weight` is the existing normalized NMF contribution; a semantic-neighbor
weight is original-space cosine. Other edges are unweighted. Relation definitions
and epistemic limits are supplied in `relation_types`.

The compact primary graph includes all selected sources and curated questions/
cards. It does not turn extracted question candidates into verified claims.
`coverage.eligible_record_types` and `coverage.omitted_record_counts` expose the
selection. The UI may add explicitly typed record nodes from a selected source's
public shard; that layer remains an extraction display, not new interpretation.

Graph search returns actual typed one- or two-hop paths and their exact evidence
anchors. Semantic-neighbor edges are excluded by default. Filtering changes the
displayed graph, not source attribution or a model fit. A shared label or factor
path is not agreement, contradiction, causality or proof of common identity.

## Frozen retrieval comparison

Before new rankings, an independent agent freezes twelve supported queries and
four ambiguity/unsupported-verification controls with exact source-span hashes.
No parameters are selected from these results. It is a source-informed,
partially judged diagnostic, not held-out human accuracy or a trained split.
Source-family labels expose grouped summaries and shared-evidence dependence.

Fixed conditions: private passage BM25 collapsed by maximum score per source;
existing whole-document masked TF-IDF; existing whole-document masked MiniLM;
top-50 reciprocal rank fusion of those three, constant 60, followed by the
unchanged MiniLM order for sources outside the candidate union. All methods have
the same 493 eligible source editions; lexical zero-match sources are not
represented as successful matches. Passage multiplicity and unmasked-BM25 versus
masked-vector input are explicit confounds. Only query vectors are newly encoded.

Known-support Hit@1/3/5/10 and reciprocal rank use inspected positive mappings.
Unjudged sources are not negatives. Control queries show returned candidates,
not calibrated correctness, exhaustive absence or automatic answerability.
Graph traversal accompanies results as provenance; no graph-expansion retrieval
condition or GraphRAG performance is claimed without an executed comparison.
