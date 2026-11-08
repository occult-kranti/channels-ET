# Source-grounded transcript search: literature and tool choices

This extension uses a small retrieval and evidence layer over the **493 retained
canonical sources**. It does not need a new model, a hosted graph database or a
large graph-RAG framework to make questions, source summaries and connections
inspectable. The actual new third-party component is **MiniSearch 7.2.0**, an
MIT-licensed browser search library. Its pinned bundle, license and provenance
are [vendored with the page](../../dist/transcript-knowledge/vendor/minisearch.provenance.json).

The [source ledger](source-ledger.json) records eleven selected papers, standards
and software references, exact retrieved-byte hashes, access depth, repository
commits and implementation status. Primary pages and code were retrieved on
8 November 2026. Raw research copies remain private; this directory contains
citations, implementation decisions and reproducible tests. This is a focused
review, not an exhaustive ranking of current RAG systems.

## What was learned from the primary sources

| Source | Inspected mechanism and useful idea | Boundary for this implementation |
| --- | --- | --- |
| [GraphRAG, Edge et al.](https://arxiv.org/html/2404.16130v2), v2, 19 February 2025 | LLM entity/relation extraction, hierarchical graph communities, community summaries and query-time map/reduce. Methods and evaluation limits were read, along with current code. | The paper's global-sensemaking evaluation used two roughly million-token corpora. A provenance diagram is not a GraphRAG reproduction. Microsoft's pinned README now says the project is in maintenance mode and warns about indexing cost. |
| [LightRAG, Guo et al.](https://arxiv.org/html/2410.05779v3), v3, 28 April 2025 | Separate detailed entity retrieval from broader relationship/theme retrieval; retain source chunks and support incremental updates. | Its paper and current code still use LLM extraction, keyword generation and answer generation. The paper's 125 generated questions per dataset and GPT-4o-mini answer judging do not measure our transcript fidelity. No conference venue was verified in the inspected pages. |
| [HippoRAG 2, Gutiérrez et al.](https://proceedings.mlr.press/v267/gutierrez25a.html), ICML 2025 | The peer-reviewed paper adds passage nodes to an entity graph, filters retrieved triples and runs Personalized PageRank. Keeping passages addresses the loss of context in entity-only representations. | Its experiments use Llama-3.3-70B-Instruct and NV-Embed-v2. We adopt the context-preservation principle, not its OpenIE, graph-walk algorithm or reported benchmark gains. |
| [RAPTOR, Sarthi et al.](https://arxiv.org/html/2401.18059v1), 31 January 2024 | Recursively cluster, summarize and re-embed passages; retrieve across abstraction levels. Methods, summary-error appendix and tree-builder code were inspected. | A source digest is not a recursive summary tree. Appendix E's six problematic summaries among 150 sampled nodes across 40 stories are that study's observation, not our expected error rate. OpenReview access was blocked, so its venue record was not reverified in this pass. |
| [BM25S, Lù](https://arxiv.org/abs/2407.03618), technical report, 4 July 2024 | Sparse precomputed lexical scoring; the inspected code explicitly distinguishes several BM25 variants. | Its speedups concern its benchmark settings. BM25S is a reference here, not an installed dependency or measured local speedup. |
| [Reciprocal Rank Fusion, Cormack, Clarke and Büttcher](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf), SIGIR 2009 | Combine rank positions rather than incomparable raw scores. The complete two-page paper was read; its constant 60 was fixed after a pilot. | Fusion needs an explicit candidate and missing-coverage policy. It cannot establish relevance, truth, independent corroboration or agreement. |
| [Extractive is not Faithful, Zhang, Wan and Bansal](https://aclanthology.org/2023.acl-long.120/), ACL 2023 | The official abstract distinguishes incorrect/incomplete coreference, incorrect/incomplete discourse and misleading omissions in extracted summaries. | Abstract and bibliography were inspected, not the complete experiment or code. Copying source sentences alone does not make a digest faithful. Its reported error rate is not transferred here. |

The paper editions and current software snapshots are separate artifacts. The
MIT licenses were read for GraphRAG, LightRAG, HippoRAG, RAPTOR, BM25S and
MiniSearch. Only MiniSearch code is redistributed by this addition. No claim of
running the other frameworks follows from citing or inspecting them.

## Small implementation that fits this corpus

**Keep two search scopes explicit.** The private analysis can search retained
transcript passages using [SQLite FTS5](https://www.sqlite.org/fts5.html#the_bm25_function).
The public static page searches only bounded question paraphrases, answer
summaries, topic terms and documentary metadata supplied in its public projection.
It does not ship or search the private full transcripts. Search results should
say which fields matched and link to the source record and original publisher.

**Use summaries to navigate, then return to evidence.** A source-local digest can
show its edition, text origin, selected themes, extract/paraphrase type and
supporting spans. Keep questions separate from their proposed answers; preserve
refusals and corrected premises. Retain surrounding context for ambiguous
pronouns, qualifications, dates, negation and attribution. An automatically
selected excerpt is a navigational excerpt until a source-reading audit supports
a stronger interpretation. A channel summary must state how many sources and
which text origins it represents.

**Use typed, bounded graph paths.** Suitable relations include a source containing
a passage, a printed question being followed by a response, an evidence span
supporting a paraphrase, and a source mentioning an attributed label. Similarity
edges are separately typed candidates for inspection. A graph path cannot turn
“mentions Mary” into an authenticated identity or turn two related topics into
the same answer. Printed labels stay associated with their medium and edition;
explicit comparison groups are navigation categories. One or two documented
hops are more interpretable here than an untested graph diffusion score.

**Reuse vectors at their actual granularity.** The existing MiniLM document
vectors are useful for related-source navigation. They are not passage vectors
and cannot locate a particular answer inside a long recording. Arbitrary new
semantic queries also require a compatible query encoder; a static keyword
search box does not provide this merely because saved vectors exist. Any future
passage-embedding or query-encoding arm needs its own input, pooling, runtime and
evaluation record.

## The prior fusion failure remains a regression case

The earlier [independent retrieval review](../knowledge-bank/INDEPENDENT-REVIEW.md)
proved a structural problem with unrestricted fusion: with 25 raw-source
candidates, 14 card-covered sources and RRF constant 60, even the lowest covered
source could receive `1/85 + 1/74`, exceeding the highest uncovered source's
`1/61`. Card availability then determined ranking regardless of query evidence.
The later top-five repair was explicitly post-hoc; it must not be presented as
an untouched successful experiment.

For a new hybrid experiment, freeze candidate cutoffs and aggregation before
viewing rankings. Collapse repeated passage hits to sources under a declared
rule, cap repeated-source exposure, retain a raw-source fallback and report
coverage by answer type. Compare lexical-only retrieval with graph expansion
under the same result and evidence budget. Keep generated navigation prompts and
known-support answer keys out of the source-derived answer index. Source-informed
audit queries measure known-support retrieval, not blind human answer accuracy;
unjudged sources are not automatically irrelevant.

## Actual browser library and reproducible checks

The local `vendor/minisearch.js` is the **unchanged UMD bundle from npm 7.2.0**,
86,348 bytes, SHA-256
`03c27931eb603af1d3358579e9885eafdb6a2f5fa9929557b3e77d7e99d06d03`.
The package tarball passed its registry SHA-512 integrity and SHA-1 checks. Its
`package.json` matches the inspected repository snapshot
`3d239d1c3ae7aef1bf5d8945dd7b5f0709f646f5`. The MIT notice and source map accompany
the bundle. It creates the browser global `MiniSearch` and needs no external
script or inference service at runtime.

Recommended options preserve apostrophes, numerals and negation; matching is
explicit OR, with fuzzy and prefix expansion off by default. Optional prefix
matching is a labeled interface choice. Use a stable `id`, index only approved
public fields and render returned strings as text rather than HTML.

```javascript
const index = new MiniSearch({
  idField: 'id',
  fields: ['question', 'summary', 'metadata'],
  storeFields: ['id', 'question', 'summary', 'metadata'],
  tokenize: value => String(value).normalize('NFKC')
    .match(/[\p{L}\p{M}\p{N}]+(?:['’][\p{L}\p{M}\p{N}]+)*/gu) || [],
  processTerm: term => term.toLowerCase(),
  searchOptions: { combineWith: 'OR', prefix: false, fuzzy: false }
});
```

Sixteen synthetic API checks cover the browser global, negation preservation,
Unicode letters/combining marks/apostrophes, numerals, OR matching, optional prefix behavior, default
no-fuzzy behavior, empty/unmatched queries, duplicate IDs and serialization.
They are integration checks, not a corpus retrieval-quality benchmark:

```bash
node research/transcript-knowledge/test-minisearch.cjs
```

MiniSearch's inspected scorer is **BM25+**, with defaults `k=1.2`, `b=0.7` and
`delta=0.5`; its per-field length counts unique tokens. SQLite FTS5 uses a distinct
BM25 convention with `k1=1.2`, `b=0.75`, ordinary token-count lengths and negative
scores so lower values rank first. Their corpora, tokenization and scoring differ.
Browser scores must not be compared numerically with private retrieval scores or
presented as the evaluated private retrieval arm.

## Provenance standards and remaining experiments

[W3C PROV-O](https://www.w3.org/TR/2013/REC-prov-o-20130430/) distinguishes evidence
entities, transformation activities and responsible agents. Its derivation
relations describe production history, not truth. The
[Web Annotation Data Model](https://www.w3.org/TR/2017/REC-annotation-model-20170223/#text-position-selector)
defines start-inclusive, end-exclusive text positions over normalized Unicode
code points and warns that changing text invalidates offsets. Bind each local
span to its canonical source ID, edition, body hash and normalization rule.
Python character offsets must not be applied as JavaScript UTF-16 indices without
conversion. Public positions/hashes avoid copying entire restricted source text
into an annotation. These are conceptual mappings; no RDF or JSON-LD conformance
claim is made without validation.

The implementation's execution records separately report its source-informed
retrieval diagnostic and typed graph checks; literature citations are not evidence
that those checks passed. Further experiments should remain bounded:
qualification retention after digest updates, question-boundary precision on
manually inspected documentary versus ASR cases, missing-card regression controls,
and graph expansion versus lexical-only retrieval at an equal source budget.
Each needs exact denominators and an explicit unresolved category. Recursive
generated summaries, graph-based relevance diffusion, local generative QA and
model training remain separate proposed work unless the execution ledger records
that they actually ran.
