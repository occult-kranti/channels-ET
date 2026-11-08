# Transcript knowledge extension

This is an exploratory, source-bound extension of the released Channel Lab. It
uses its frozen 493 canonical text editions, 1,411,446 words and 26 publisher
contexts. It is not a complete YouTube collection or a test of the physical
identity of attributed speakers. Earlier corpora, annotations, model fits and
speech editions remain separately versioned.

## Questions and implementation

1. Which retained sources contain printed question/response turns, uncertain
   question candidates, or written messages without an observed question?
2. Can a reader retrieve the exact source and qualifications behind a bounded
   answer card, and distinguish it from an automatically generated reading aid?
3. How do private full-evidence retrieval methods rank a small, independently
   selected set of known supporting sources?
4. Which visible connections reflect publication, attribution, evidence support,
   lexical mixture or computed similarity, and how do filters change the view?

The extraction owner will inspect a varied pilot before processing the complete
frame. Source profiles process every selected body but do not imply that a human
or an AI reviewer closely read every passage. Private extractive digests retain
exact source locations. Public automatic outlines remain distinct from curated
paraphrases. Question punctuation alone cannot establish an interview turn, an
answer boundary or an attributed speaker.

The four bank types are `observed_question_answer`,
`unverified_question_candidate`, `generated_reading_prompt` and
`curated_comparison`. Printed roles remain publisher attributions, not verified
audio identities. A candidate's following text is context, not an established
answer. New recognitions cannot inherit old evidence locations automatically.

The curation owner selects varied sources and windows before new retrieval
rankings, adds bounded readings in previously unread publisher contexts, and
reuses prior cards only through exact selected-edition joins. Every source note
states the actual reading coverage. Reviewer inspection and model annotation
are not human annotation or external expert endorsement.

## Retrieval and graph contracts

The private SQLite database contains canonical bodies, bounded passages and
evidence spans. Its CLI supports lexical search, exact evidence lookup and typed
graph paths. The public database and static search contain released metadata,
automatic outlines and bounded annotations only. These are different search
collections; public search is not advertised as full-transcript search.

The numerical diagnostic compares SQLite FTS5 BM25 passage search collapsed to
sources, the existing full-source TF-IDF representation, the existing MiniLM
representation, and fixed top-50 reciprocal-rank fusion with k=60. All use the
same 493 eligible sources; lexical no-match cases remain explicit. Query
embeddings may be computed; the corpus is not refitted. The independent reviewer
freezes 12 source-informed information needs and four ambiguity/verification
controls before seeing new rankings. Known-support ranks and Hit@k are
diagnostics with partial judgments, not general relevance or answer accuracy.
Controls must not receive invented source support.

Graph nodes distinguish publisher context, creator context, document, printed
claimed label, lexical factor and curated question/card. Typed edges state their
construction and evidence. Shared labels and similar language do not establish
the same being, agreement, causal influence or contradiction. Thousands of
unreviewed question candidates will not be drawn as thousands of interpreted
claims. Their omitted/lazy-layer counts remain visible.

## Reproduction and release

Use pinned, license-inspected open-source components where they improve a
specific part of the workflow. The literature register distinguishes inspected
papers, repository code, proposed methods and methods actually implemented.
Using a typed graph does not constitute a reproduction of GraphRAG, LightRAG or
HippoRAG. No new neural training or stronger recognition-accuracy claim is made.

Processing is deterministic and bounded by recorded inputs, settings and stable
IDs. Heavy intermediates use RAM storage; accepted databases and compact
receipts are retained privately. The 2 GiB free-disk floor remains in force.
Full source text, raw media, model weights and private exact passages do not
enter GitHub Pages. The release uses explicit allowlists and SHA-256 bindings.

Three actual milestones are recorded: pilot/source-contract review;
executed extraction/retrieval/curation review; corrected integrated release and
live browser verification. Meaningful tests cover boundaries, missing evidence,
source/edition joins, candidate versus answer semantics, search filters and
graph edge provenance. The final report separates executed results, unresolved
limits and future experiments. No gate is passed merely because code exists.
