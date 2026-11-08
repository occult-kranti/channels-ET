# Literature review: sleep, memory and source-grounded comparison

This review supports the 8 November 2026 knowledge-bank extension. It is a bounded
primary-source review, not a systematic survey or a claim to have identified the
best model on every current benchmark. The [source register](literature-register.json)
separates publication dates, exact versions, retrieved artifacts, sections
actually inspected and proposed local applications. Full source pages and
extracted paper text remain private. No benchmark score below is a result from
the Channeling Atlas.

## The Google paper identified

The user's description strongly matches **Ali Behrouz, Farnoosh Hashemi, Adel
Javanmard and Vahab Mirrokni, “Language Models Need Sleep: Learning to Self-Modify
and Consolidate Memories,” arXiv:2606.03979v2**. The arXiv record dates v1 to
2 June 2026 and v2 to 10 July 2026; it notes an earlier OpenReview version from
September 2025. The matching Google Research blog, **“The sleep framework: A new
way for LLMs to retain knowledge in continual learning,”** is dated **27 October
2026**. The primary blog names abstraction/distillation, consolidation and
cross-domain expert mixing, matching all three parts of the user's description.

- [Pinned paper v2](https://arxiv.org/html/2606.03979v2)
- [Google Research explanation](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/)

The inspected paper's main prose, appendices and selected experimental tables
support the following technical account:

| Stage | What the authors actually implement | What a source-bank implementation can borrow |
| --- | --- | --- |
| Wake | Process incoming information in faster-updating memory components | Preserve incoming source editions and acquisition/recognition provenance |
| Consolidate | Add or activate low-rank experts in slower memory blocks; preserve older parameters | Produce versioned, evidence-linked cards while retaining original text and dissenting claims |
| Knowledge seeding | Combine on-policy generalized knowledge distillation with RL-based imitation; train expanded weights | Audit paraphrase fidelity, qualifiers and retrieval usefulness; this is an analogy, not distillation of weights |
| Prune | Reset higher-frequency experts after transfer | Invalidate stale indexes and rebuild from immutable evidence; do not delete source evidence or minority claims |
| Dream | Randomly activate additional MoE experts, generate synthetic training samples, select them using gradient-based scores, train/evaluate adaptations | Propose explicitly hypothetical cross-field questions, then demand source checks or a new experiment before admitting findings |

The paper is **not** a recipe that makes a frozen chat model learn simply by
writing notes. It modifies model memory architecture and numerical weights.
Section 3.3 specifies compute–consolidate–update ordering, frozen old parameters,
student/teacher distributions and imitation rewards; Section 3.4 uses synthetic
generation, gradient-based selection, LoRA updates and downstream evaluation.
Appendix B describes 3B/8B backbones and additional memory modules, with separate
smaller-model experiments. Merely placing summaries in SQLite or a vector index
does not execute those methods.

The Google blog and pinned paper do not link a specific executable author model
or code release. A bounded exact-title GitHub search returned a different-title
“Do Language Models Need Sleep?” project and a third-party LangChain
“sleep-replication”; neither was established as this Google paper's official
implementation. This is an access/release finding within the inspected sources,
not proof that no implementation exists anywhere.

### Results that need their experimental context

- The headline **10-million-token** result is on **BABILong** with task-specific
  fine-tuning of the small models. Appendix B.2 explicitly reports substantial
  drops for the small models, including Hope, without fine-tuning. It is not a
  demonstrated general-purpose 10-million-token capacity for our corpus.
- The **80% ARC** figure is the fraction of tested generated dreams yielding a
  correct answer under a filtered protocol with **11 training and eight held-out
  tasks**, and five test-time dreams per unseen task. It is not 80% accuracy over
  arbitrary unseen reasoning problems.
- The mathematical reasoning tables report **average@16** for specified Qwen
  variants. Those scores do not measure transcript accuracy, religious
  knowledge, claim truth or source attribution.
- Appendix B.5 says **same-step SFT is four times more efficient**; the reported
  advantage reverses when comparing wall-clock time to reach selected target
  performances. A local system should measure both total preprocessing cost and
  per-query benefit rather than quoting one favorable speedup.
- The source's claims of reduced forgetting are experimental claims under its
  selected tasks and memory design. They do not establish indefinite retention,
  unlimited capacity or error-free self-improvement.

## Three different uses of “sleep”

| Work | Mechanism | Local status |
| --- | --- | --- |
| Google, *Language Models Need Sleep* (2026) | Expanded parametric memory, on-policy distillation, imitation learning and synthetic training | Literature reference; not reproduced by the source-card experiment |
| Lin et al., *Sleep-time Compute* (2025; Letta/UC Berkeley) | Precompute a transformed context before the user query arrives; amortize that work across later queries | Closer conceptual reference for offline source-card preparation; original benchmark is not reproduced |
| Google, *Nested Learning* / Hope (2025) | Nested optimization and memory components with different update frequencies | Architectural background; separate from both the 2026 Sleep method and an external retrieval index |

The Google paper itself makes the distinction from Lin et al. in Section 2.3 and
Appendix A.3. *Sleep-time Compute* evaluates stateful mathematical tasks and a
software-engineering case study; its offline context transformations are not
evidence that our summaries preserve every source qualification. Its authors
release [code and data](https://github.com/letta-ai/sleep-time-compute). No new
model-weight training is implied by the local term **source-card consolidation**.

## Related methods and standards

| Reference | Useful principle for this project | Limitation to retain |
| --- | --- | --- |
| [GraphRAG](https://arxiv.org/html/2404.16130v2) | Separate evidence extraction, typed relationships, graph communities and global summaries | LLM-extracted graph edges and summaries are fallible. Its inspected evaluation is global sensemaking over two roughly million-token corpora, not claim authentication |
| [HippoRAG](https://arxiv.org/html/2405.14831v3) | Graph-assisted multi-hop retrieval; inspect passage grounding and retrieval separately from final answers | Its embeddings, OpenIE and Personalized PageRank are a specific algorithm. Our provenance graph is not a reproduction merely because it has nodes and edges |
| [HippoRAG 2](https://arxiv.org/abs/2502.14802v2) | Check factual, associative and global sensemaking tasks separately | Abstract/metadata inspected here; its benchmark improvements are not transferred to this corpus. Graph structure can trade off performance across tasks |
| [RAPTOR](https://arxiv.org/abs/2401.18059) | Preserve multiple levels of abstraction and allow retrieval back to lower-level material | Abstract inspected; recursively summarized text can lose minority statements, dates and negation |
| [MMTEB](https://arxiv.org/html/2502.13595v4) | Use multiple task types, model versions, annotation metadata and reusable embedding caches | Task/language rankings differ. A broad benchmark leader is not automatically best for short spiritual texts or noisy long ASR |
| [Sentence-BERT](https://arxiv.org/abs/1908.10084) | Encode texts once and compare sentence representations efficiently | Cosine similarity is a retrieval signal, not an answer-equivalence or contradiction test |
| [Finding Contradictions in Text](https://aclanthology.org/P08-1118/) | Align the event/proposition, participants, time, modality and polarity before judging incompatibility | This is a foundational 2008 analysis, not a current SOTA model. Similar words, different numbers or a negation flag alone can generate false conflicts |
| [Whisper](https://arxiv.org/abs/2212.04356) | Treat recognition as a learned, versioned measurement process | Foundational abstract inspected, not a current SOTA ranking; stronger capacity and model disagreement do not prove accuracy without reference transcription |
| [Datasheets for Datasets](https://arxiv.org/abs/1803.09010v8) | Document motivation, composition, collection, transformations, recommended uses and limitations | Documentation makes limitations inspectable; it does not remove them |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | Distinguish evidence entities, transformation activities, responsible agents and derivation relationships | A provenance graph describes how an artifact was made; it does not establish the truth of its content. No RDF conformance is claimed without validation |

## Cross-field connections that can be tested

**Information retrieval and memory systems.** A precomputed card is a cache of
source interpretation. The relevant test is whether it retrieves the right
evidence with less repeated work while preserving qualifications. Compare raw
chunks, cards and a hybrid over the same source universe. Freeze cards and query
definitions separately; never append evaluated question text or answer-key flags
to the card index. Report preprocessing cost, source-hit limits, index size and
known-support retrieval. Unjudged results are not automatically wrong.

**Oral history and measurement science.** Audio, codec, transcript, corrected
transcript and reading notes are different editions. A larger ASR model should
produce a new edition, not overwrite the previous account. Paired audio spans
permit edit-distance, name/negation retention and downstream rank-stability
comparisons. Those are model-disagreement diagnostics until independent audio
transcription supplies a reference. Human word accuracy and unknown speaker
identity remain separate gaps.

**Argumentation and textual inference.** Compare propositions rather than broad
topics. A table should show the common question, scoped claims, evidence spans,
conditions, dates and what would make the claims compatible. Retain categories
such as compatible, qualified tension, explicit scoped conflict and insufficient
context. An apparently opposite prediction may concern a different time,
conditional branch, meaning of “contact,” or narrated speaker. No automatic
claim-truth score follows from an NLI or embedding output.

**Digital humanities and network science.** Use a typed, bipartite graph of
source editions and attributed labels, with separate derived proposition and
topic nodes. Degree often measures how much material was collected. Compare
within-medium versus cross-medium neighbors, and expose the denominators before
interpreting a dense community as a shared doctrine. Two source descriptions
using the same supernatural name do not establish a shared physical being.

**Continual learning and data versioning.** After a new transcript or correction,
track which cards, answers and graph edges need rebuilding. Test whether earlier
question support and previously recorded qualifications survive an index update.
For a static retrieval index this is a regression test of knowledge-bank
maintenance, not a measurement of neural catastrophic forgetting.

**Cross-domain analogy and scientific hypotheses.** Compare a practice described
by a medium with a separately sourced psychological or information-processing
construct only as an analogy until a discriminating test exists. For example,
“attention changes interpretation” and “attention creates external events” are
different claims. A source-bound thematic bridge can generate a research question;
it cannot import empirical support from one field into an unrelated mechanism.

## Proposed experiments, not unearned findings

[experiments-proposed.json](experiments-proposed.json) records falsifiable designs,
appropriate units, required comparisons, useful plots and invalid interpretations.
The actual execution ledger is maintained separately by the integration owner.
The following priorities are feasible without changing model weights:

1. Paired ASR editions on identical preselected spans; runtime and downstream
   stability, with accuracy left unmeasured without independent references.
2. Lexical versus dense retrieval and neighbor overlap over identical source
   units; inspect failure cases rather than choosing the prettiest projection.
3. Raw versus source-card versus hybrid retrieval, preserving input provenance
   and disclosed source-informed question construction.
4. Scoped answer comparisons with retained uncertainty and an explicit abstain
   category; similarities are candidate-selection tools.
5. Consolidation regression: citation completeness, qualifier retention, source
   diversity and earlier-question support before/after an index update.

A two-dimensional embedding plot can aid navigation, but its axes and distances
are not common units across separately fitted models. Prefer a shared projection,
explicit alignment with distortion diagnostics, or side-by-side views plus
neighbor-overlap/rank-change matrices. Word TF-IDF, document embeddings and
sentence embeddings should have separate labels and denominators. These choices
prevent an attractive overlay from becoming a misleading comparison.
