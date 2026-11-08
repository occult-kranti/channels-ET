# Transcript knowledge: evidence retrieval and typed connections

This extension makes the retained collection navigable without treating every
question mark as a verified question/answer exchange or every similarity as
agreement. It reuses Channel Lab's **493 canonical editions, 1,411,446 words,
26 publishing contexts and 14 creator-attribution contexts**. These are not a
YouTube census, a count of independently authenticated mediums, or a fully
close-read corpus. The canonical source frame and earlier model fits are unchanged.

In the executed twelve-question diagnostic, passage BM25 retrieved every known
support source within the first three results. Fixed fusion improved the average
reciprocal rank but moved one known support from BM25 rank one to fusion rank
five. Whole-document neural similarity was particularly weak for that question.
The results support keeping lexical evidence search and exact source inspection;
they do not establish uniform neural or hybrid superiority.

## Separate evidence layers

The extraction module processes every selected body and supplies 493 automated
profiles and **9,424** typed records: **2,523** publisher-formatted Ra question/
response pairs, **6,408** unverified question candidates, and **493** generated
reading prompts. Printed roles are documentary attributions. Candidate adjacent
text is context rather than an established answer; generated prompts were not
spoken by the source. Their extraction policy, failures and exact locators are
owned by the extraction module.

Four of the printed Ra records contain editorial missing-question placeholders,
so their original question text is unavailable. Another 107 response turns lack
a matching present questioner turn and are left unpaired; many are opening
statements, so they are not all lost questions. Forty-one sources have only the
generated reading prompt and no observed/candidate question record. Their full
bodies still enter private passage search. These distinctions prevent the bank
total from being advertised as 9,424 verified audience questions with answers.

Curated questions and qualified answer cards form a separate, bounded reading
layer. Their source hashes and spans are verified again during database
ingestion. An unchanged source ID is insufficient: the selected body, artifact
and span hashes must also match. A support cannot silently transfer to a new
recognition edition. Reused cards preserve their original attribution and
review limits. Processing every body does not imply reading every passage or
listening to every recording.

## Private and public SQLite databases

The private database stores the exact normalized source bodies, extraction
question/answer/context text and exact checked evidence. It additionally divides
each body into nonoverlapping passages of at most **500 whitespace words**,
including the partial tail. Character ranges, word ranges and span hashes bind
each passage. These are source-text positions, not audio timestamps.

The public database contains source metadata, automatic lexical outlines,
extraction statuses and locators, curated question/card paraphrases and exact
provenance keys. Original source bodies and extraction question/answer/context
text are null; there are no public passage rows. Metadata fields are explicitly
allowlisted. Public full-text search contains exactly:

1. A source's title, approved automated outline, leading lexical terms and fixed
   topic labels.
2. Qualified curated card text: paraphrase, conditions, time scope and caveat.
3. Curated question wording, as a separately typed item.

Generated prompts and unverified candidate wording do not enter an answer-card
index. Original source text does not hide in the FTS auxiliary tables. The
stdlib release verifier reconstructs every approved public search item and
compares the complete multiset with the actual FTS content. Database integrity,
foreign keys, raw-text nulls, source counts and edition joins are checked too.

Both databases preserve the same source, record, question, card and evidence
keys. Exact evidence lookup in the public database returns a locator; the
private database returns the verified slice and checks its hash. A private
database is an evidence archive, not a claim that source text is factually true.

The CLI quotes tokens into a bounded FTS OR expression and uses bound SQL
parameters. Source/channel/creator/origin/date filters limit eligible sources.
Dates use ISO `YYYY-MM-DD`; unknown dates are excluded when a date bound is
specified. Invalid limits and dates fail explicitly. Filtering does not rebuild
the index or alter the original relevance statistics.

## Public browser search is a different system

The website searches released metadata and annotations. Its pinned MiniSearch
implementation uses BM25+ with its own token/field-length conventions. The
private numerical diagnostic below uses SQLite FTS5 passage BM25. They search
different collections and use different scorers. Their score magnitudes and
rankings must not be conflated. No browser interface is advertised as searching
private full transcripts it does not contain.

## Typed graph and provenance paths

The compact graph distinguishes publisher context, creator-attribution context,
source, fixed lexical factor, exact observed claimed label, curated question and
qualified answer card. Publisher and creator contexts remain separate, including
guest appearances. An observed label records the literal source attribution;
matching labels do not authenticate a common entity.

Edges state their origin and units. Publication and attribution edges are
metadata. Factor edges carry the previously fitted, scale-canonicalized NMF
contribution. Semantic-neighbor edges reuse Channel Lab's original-space mutual
three-neighbor cosine graph and are explicitly derived. Card-to-source support
edges carry checked evidence IDs, while card-to-question edges indicate the
qualified source reading addresses that question. No source-to-question `asks`
edge is created for analyst prompts. Source → card → question navigation avoids
inventing an observed speech event.

All 9,424 extraction records remain accessible through the database and source
shards. They are deliberately omitted from the compact interpreted graph, with
counts by omitted type published. A UI may display an explicitly marked record
layer for a selected source; that does not promote a candidate into an answer.

Graph queries return actual one- or two-hop paths, with directed-edge traversal
reported as forward or reverse. Derived similarity edges are marked undirected
and excluded by default. Source/context/origin/date/relation filters are
applied before traversal. A bounded path count exposes truncation. Shared-label
or shared-factor paths are navigation links, not agreement, contradiction,
causality or evidence for supernatural identities. A JSON locator map resolves
support IDs without requiring a browser SQLite runtime. GraphML exports carry
the same node IDs, directed provenance edges, derived-edge flags and weights.

## Frozen retrieval diagnostic

An independent agent selected **12 source-supported information needs and four
ambiguity/evidence-sufficiency controls** before any new rankings. The frozen
query SHA-256 is
`27f6917ea6c2a52569b7ec8ec4b6d9ba06be583342822ecfa24de63ea70d4da8`.
The supported questions span twelve sources and ten publisher/source families.
Each positive source mapping has an exact selected-body span hash. Query wording
and mappings were withheld from extraction and curation authors while their
policies were fixed. Nevertheless, the questions were informed by reading source
answers: they are not blind human labels or a prospective relevance benchmark.

Four conditions use the same 493 eligible source editions:

- **Passage BM25:** SQLite FTS5 over original 500-word passages, collapsed to the
  maximum match score per source. Equal scores break ties by canonical source ID.
- **Frozen TF-IDF:** the existing masked, whole-document 24,000-feature model.
  Query terms are transformed using its unchanged vocabulary and IDF.
- **Frozen MiniLM:** the existing complete-document pooled vectors from the
  pinned `all-MiniLM-L6-v2` model. Only the sixteen question vectors are new.
- **Fixed fusion:** the top 50 sources from each preceding condition contribute
  `1/(60 + rank)`. Sources outside their candidate union follow the unchanged
  MiniLM order. No card presence, graph degree or annotation count is a bonus.

The candidate cutoff, constant, tie policy and fallback were fixed before
rankings. There is no parameter search, new corpus embedding fit or trained
model split. Lexical zero-match sources do not receive fabricated positive
matches. Query-vector inputs use the same exact-phrase mask as the frozen vector
models. SQLite BM25 uses the original passage text, so masking and text extent
differ between arms. Maximum passage pooling gives long documents more chances
to match; each citation exposes its source passage count. These are concrete
confounds rather than controlled model-only comparisons.

The frozen execution produced these descriptive results:

| Condition | Mean reciprocal rank | Hit@1 | Hit@3 | Hit@5 | Source-family macro reciprocal rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| Passage BM25 | 0.91667 | 10/12 | 12/12 | 12/12 | 0.92500 |
| Frozen full TF-IDF | 0.67083 | 6/12 | 10/12 | 10/12 | 0.65500 |
| Frozen full MiniLM | 0.81974 | 9/12 | 11/12 | 11/12 | 0.80869 |
| Fixed top-50 fusion | 0.93333 | 11/12 | 11/12 | 12/12 | 0.92000 |

Question `q06`, about the scope of a Council identity label, is an informative
exception: the inspected source ranks **1** with passage BM25, **6** with full
TF-IDF, **284** with full MiniLM and **5** with fusion. This was retained without
tuning queries, the source frame or fusion parameters. The family-macro score
slightly favors BM25 over fusion despite fusion's higher question-average score.
One known positive source per supported question makes Hit@k and known-support
recall identical here; it does not mean every relevant source was judged.

Known-support reciprocal rank, Hit@1/3/5/10 and known-support recall are computed
only for the twelve supported questions. Other retrieved sources are unjudged,
not negatives. Publisher/source-family summaries expose grouped dependence;
they do not create a trained holdout or independent sample. The four controls
retain their returned candidates but have null correctness metrics. Retrieval
alone cannot establish personal forecasts, identities or requested proof; no
calibrated abstention threshold is invented.

Each result cites the exact selected source. Where lexical search finds a
passage, its top BM25 locator is shown, explicitly labeled as an unjudged passage
rather than established answer evidence. Otherwise the whole-source locator is
used. A correct source hit therefore does not establish that the returned
passage adequately answers the question. Known support locators are separate
from retrieved candidate locators.

Typed graph navigation accompanies source inspection. It does not enter these
four ranking conditions. This implementation does not claim to reproduce or
benchmark GraphRAG, LightRAG, HippoRAG or model-weight consolidation.

## Verification and reproduction

Eight focused tests cover source/span mismatch rejection, complete passage
boundaries, public/private text separation, literal FTS token handling,
context-filtered typed graph paths, bounded fusion plus raw fallback,
partially judged metrics, and rejection of private metadata. A real seven-source
pilot ingested 326 records and 659 checked evidence spans with 88 private
passages before the full build.

The public verifier requires only Python's standard library. It checks the
public database hash/integrity/foreign keys, exact FTS composition, source and
extraction denominators, graph/evidence/GraphML joins, original selected-edition
bindings, per-query metric arithmetic, family summaries and plot hashes.
Independent full-evidence auditing separately checks source spans, private FTS,
query transformation and numerical witnesses. These agent checks are not human
transcription validation or external peer review.

The executed databases contain 493 sources/profiles, 9,424 extraction records,
26 curated questions, 27 cards and **19,417** deduplicated evidence locators.
There are **3,076** private passages and **547** approved public search items.
The compact graph has **622 nodes and 3,664 edges**, including 256 separately
marked semantic-neighbor edges; all 9,424 extraction records are explicitly
outside that interpreted layer. The 35 MB public SQLite file carries no original
body text; the approximately 91 MB private file retains the evidence.

Independent numerical review rebuilt all 3,076 passage slices and a fresh FTS5
index, manually reconstructed log-TF/frozen-IDF query features, checked saved
query/document cosine arithmetic, and reproduced all **64** complete rankings,
fusion candidates, fallback tails and summaries with maximum score difference
zero. This arithmetic check reused recorded neural states rather than rerunning
the model. The source-reading and graph/path audits remain separate. The actual
retrieval figure was inspected for labels, rank scales and clipping.

The separate graph audit rebuilt all node/edge memberships and GraphML
directions, reopened 26 card-bearing source bodies, rehashed all 34 card support
spans, and compared 1,083 CLI paths across 24 filter/traversal cases. Five invalid
requests were rejected. One optional printed-question number is omitted from a
graph locator projection; the full documentary binding remains in curated JSON,
while all required source/body/span fields agree.

Independent database review reconstructed all 547 approved public FTS items,
checked the complete public/private table projection and all 493 private body
hashes, and exercised seven combined filter memberships and fourteen searches.
It also verified all sixteen query inputs, their 378 content wordpieces, cache
hashes, saved vectors and the model manifest. The original document embeddings
were reused, not counted as new inference.

Build and search entry points are in `retrieve_graph.py`; the literal data
contract is [RETRIEVAL-SCHEMA.md](RETRIEVAL-SCHEMA.md). Use a new output directory
for each edition. `build` consumes the verified frame, old analysis, final
profiles, private record JSONL and curated output. `evaluate` additionally
requires the pinned model, unchanged portable vector witness and frozen query
file. It saves all 64 full rankings and query-vector witnesses privately.

```sh
python research/transcript-knowledge/retrieve_graph.py search \
  --database /workspace/channels-et-private/transcript-knowledge-2026-11/accepted/database-01/database-private.sqlite \
  --scope private --query "optional assistance"
python research/transcript-knowledge/retrieve_graph.py evidence \
  --database /workspace/channels-et-private/transcript-knowledge-2026-11/accepted/database-01/database-private.sqlite \
  --evidence-id EXACT_EVIDENCE_ID
python research/transcript-knowledge/retrieve_graph.py paths \
  --graph GRAPH_JSON --start source:CANONICAL_SOURCE_ID --hops 2
python research/transcript-knowledge/verify_retrieval.py --public-dir RELEASE_DIR
```

Public outputs use an explicit file/bytes/SHA-256 allowlist. Full bodies, private
question/answer text, embeddings and model weights are excluded from Pages.
Durable private retention is distinct from public publication and ephemeral RAM
workspaces. New speech editions cannot replace selected source evidence without
their own verified admission and reannotation process.

The authoritative durable database is
`/workspace/channels-et-private/transcript-knowledge-2026-11/accepted/database-01/database-private.sqlite`.
Its accepted retention manifest also covers extraction and retrieval artifacts.
The original numerical witnesses remain in Channel Lab's
`release/essential-numerical-witnesses.tar.xz`. The exact Unicode-feature witness
bound by this retrieval release is retained separately at
`/workspace/channels-et-private/transcript-knowledge-2026-11/retrieval-graph-01/baseline-witness`.
Its core, lexical matrix and conversion receipt total 13.17 MB; their hashes
match the diagnostic. An additional methods receipt preserves frozen query and
producer-code bindings; identical database/cache copies were hash-verified and
hardlinked to the accepted files, preserving both paths without duplicate
storage.

## Arbitrary local semantic queries

`query_semantic.py` is a separate, additive CLI for new queries. It does not
change the executed sixteen-query diagnostic. It offers `tfidf`, `minilm` and
`rrf`, plus passage `bm25`, using the same frozen database, vocabulary, vectors,
mask and model. A required accepted retrieval contract checks the exact database,
analysis and numerical-witness hashes. Only a new query vector is encoded.

Channel, creator, origin and date filters define the eligible source universe
before each method is ranked or fused. The global index statistics remain fixed.
Returned candidates include source URLs, body hashes, exact locator references,
per-arm scores, component match counts and the fusion/tail distinction. Missing
lexical matches have null component scores, rather than invented scores. Score
units differ across methods and must not be compared as probabilities.

Empty filtered universes and zero lexical matches receive explicit states.
This CLI never generates answers and is not browser semantic search. Three
additional tests cover stable ties/filter-before-ranking, invalid/empty inputs,
and a real-SQL empty universe with operator-like filter text and no model load.
Six actual runs exercised all-source fusion (493 eligible), filtered fusion
(eight eligible), one-context neural search (one eligible), an empty future-date
filter, a zero-vocabulary match, and literal operator-like query text. The
database hash remained unchanged. These are functionality checks, not added
relevance labels or a retuned benchmark.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /workspace/channels-et-analysis-venv/bin/python research/transcript-knowledge/query_semantic.py \
  --database /workspace/channels-et-private/transcript-knowledge-2026-11/accepted/database-01/database-private.sqlite \
  --analysis dist/channel-lab/analysis.json \
  --witness /workspace/channels-et-private/transcript-knowledge-2026-11/retrieval-graph-01/baseline-witness \
  --contract /workspace/channels-et-private/transcript-knowledge-2026-11/accepted/retrieval-01/retrieval.json \
  --model /workspace/channels-et-private/bashar-ra-2026-11/model-cache/minilm-1110a243 \
  --method rrf --query "Mary Magdalene light" --channel natalie-glasson-omna --limit 5
```

Omit `--channel` for the whole source universe. `--creator`, `--origin`,
`--after YYYY-MM-DD` and `--before YYYY-MM-DD` are optional; unknown dates do not
satisfy bounded date filters. TF-IDF alone does not need `--model`. These commands
need the private retained artifacts and the analysis environment; publication of
metadata on Pages does not expose the private evidence archive.
