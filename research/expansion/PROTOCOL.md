# Expansion protocol: channel discovery, questions and research coverage

This is the continuation of the 23 October 2026 release at GitHub commit
`1d6eb36379ed7730dc0cb2e85d83b9e77205b07b`. The original scientific snapshot
and manuscript rounds 1–6 remain preserved. The expansion is exploratory;
this document is an execution plan, not retrospective preregistration.

## Questions and units

1. Which practitioners, publishing accounts and attributed entities are present
   in the retained discovery frame, and which joins remain unresolved?
2. What does channel/search acquisition actually retrieve, and where do network,
   caption, language, availability and sampling losses occur?
3. How do upload lengths, title vocabulary and available-caption selection vary
   across publishing accounts in this indexed sample?
4. Which questions recur in the available digest material, and how does question
   similarity differ from similarity of the associated answer summaries?
5. What additional evidence would permit comparisons across practitioners or
   attributed entities, with original sessions and speaker roles resolved?

An upload, original session, publisher, human practitioner, attributed entity,
caption segment and digest Q&A candidate are separate units. Counts of upload
IDs are never counts of people or sessions. Keyword hits and embeddings measure
text properties; neither establishes answer agreement or the origin of a claim.

## Collection and analysis boundaries

The retained sampling frame is the existing discovery index, analytical metadata,
caption derivatives and source-linked digests. It is a convenience sample. Query
plans enumerate person/entity aliases with source provenance; an executed query
is distinct from a planned query and a retrieved result. Collection begins with
a bounded ordinary-access pilot, retains failures and stops on policy denials,
403/429 blocks or authentication requirements. Open-source software may improve
parsing and reproducibility but does not authorize circumventing a denial.

New raw captions belong outside Git at `/workspace/channeling-raw`. Public
outputs contain derived records and short source-linked paraphrases rather than
raw caption corpora. Digest question/answer summaries are AI-derived secondary
material and remain labeled as such. Missing timestamps and uncertain speakers
remain null. Model-agent reading is distinct from human/audio validation.

No newly downloaded video, transcript, model inference, human annotation,
comprehensive crawl or peer-reviewed novelty is claimed without a corresponding
artifact and execution record. Proposed work remains separate from results.

## Three new panel rounds

The panel comprises model-agent roles for acquisition/provenance, literature and
methods, Q&A extraction, analysis, manuscript, dashboard and a coordinating
skeptic. These are independent task executions, not independent human reviewers.

| Round | Artifact reviewed | Required resulting revision |
|---|---|---|
| 7 / expansion 1 | Prior release and handoff | Identity/search protocol, evidence-aware Q&A database, new analysis and first complete rewritten artifacts |
| 8 / expansion 2 | First expansion outputs | Correct actual methodological, attribution, numerical, manuscript and interaction defects |
| 9 / expansion 3 | Revised candidate | Independently reproduce decisive values, inspect rendered deliverables, close findings and freeze exact hashes |

Reviews state inspected paths/hashes, evidence, severity, decision and acceptance
checks. A completed round requires an implementation or a documented,
evidence-backed no-change decision after review. Earlier receipts cannot certify
new artifacts. The coordinator keeps `reviews/decision-ledger.json` and
`reviews/completion.json` with performed, blocked and deferred work separate.

## Acceptance criteria

- Every released Q&A candidate resolves to an exact source file/hash/pointer and
  video URL; no inferred timestamp or verified speaker is invented.
- Source-layer denominators are explicit. Unsupported cross-practitioner answer
  comparisons display an unavailable state rather than a synthetic comparison.
- Acquisition logs distinguish policy denial, platform failure, no captions,
  successful metadata and successful offered captions. Queries with no execution
  have no implied result count.
- Analyses run from pinned retained inputs; plots identify units and cohort.
  Sensitivity and influence ranges are not confidence intervals.
- A complete rewritten manuscript and explorer build from the same expansion
  results. Source references retain actual access depth and tool versions.
- Automated functional checks, source/number audits and rendered inspection cover
  changed deliverables. Human annotation and direct audio accuracy remain pending
  unless actually completed by humans.
- Preserve the original root Bashar Index, previous snapshots and branch history.
  GitHub updates and hosted publication are separate actions with separate checks.

## Initial observed constraints

The GitHub checkout omits historical `research/validate.py`,
`research/validate_discovery.py`, the old Sites source and `.openai/hosting.json`
mentioned in the README. Their absent paths cannot validate this checkout or
establish hosted publication access. The available tools do not expose Sites
publication. The Data shared runtime/reference provider is also unavailable;
the existing static app can be extended and browser-tested locally, with that
limitation recorded rather than represented as a shared-runtime build.
