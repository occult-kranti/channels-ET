# Continuation handoff — 23 October 2026

## Destination and preservation

Continue cross-channel ET research in `occult-kranti/channels-ET`. The separate
`occult-kranti/bashar-index` checkout is preserved at
`151efb25824dd54768edef7b71ca2a22f1c6d1ac`. No tracked or untracked files there
were changed during this continuation. The new repository baseline was
`faefa36cbd2e55fdfb2f0508e5cb6b3bf5c54a5d`; its original Atlas remains accessible.
The migrated expansion has a separate `MIGRATION.json`; historical archives and
review identities were retained rather than re-certified as new observations.

## Current evidence

| Layer | Executed and inspectable | Boundary |
|---|---|---|
| Source index | 925 uploads, 881 positive durations; typed publishing/practitioner/entity records | Purposive union; original performance dates and complete channel coverage unknown |
| Captions | 30 retained English-caption vectors; 25 uploads matched to title vectors | Raw caption documents absent; no new encoder run or recovered speech |
| Q&A | 949 AI-digest candidates, 67 Q&A-bearing uploads, source hashes/pointers, SQLite | One practitioner context; no validated speaker turns, literal quotations or multi-practitioner answers |
| Literature | Newly checked source register with PDF hashes/page locators and fresh official ICWSM guidance | Abstract-only and inaccessible full texts identified individually |
| Analysis | Source quarantine, question/answer lexical resemblance, common-support sensitivity, duration conditioning, six figure families | Exploratory; lexical resemblance is not agreement or truth; pairs are dependent |
| Models | Five-arm 50-output CPU pilot; 48 training examples/12 optimizer updates; 270,336 LoRA parameters | Eight held-out questions, two controls; sparse train-only RAG; unequal response caps; no human accuracy validation |
| Annotation | Twelve fixed excerpts tested with original/reversed label order: nine parsed per condition; six of eight jointly parsed themes changed; neither condition has a valid short answer quote | Prompt sensitivity; reversed first-option copying is disconfirmed; not a corpus topic estimate |
| Newer Qwen | Qwen3.5-0.8B CPU provenance-JSON smoke plus actual same-twelve-excerpt annotation: twelve parsed, five exact short evidence spans; about 5.4 GiB peak RSS | All-yes conditional labels equal the always-yes dictionary baseline; no human accuracy, SOTA or audiovisual claim |
| Acquisition | Search plans, resumable channel/caption/media software, SQLite inventory, quotas and adversarial checks | New YouTube proxy CONNECT 403 and independent author HTTP 403; zero successful new raw transcript/video downloads |

The inherited strict `INSUFFICIENT_EVIDENCE` parser does not count plain
“Insufficient evidence.” as a marker match. Original scores are preserved and a
separate post-hoc phrase check is clearly labeled. Four answer-present training
query controls omit source labels; they are excluded from held-out evaluation.
One adapted closed-book response invents a studio temperature. These negative
outputs remain available in the dashboard and paper.

## Reproduction and local services

Use `/workspace/channels-et-analysis-venv/bin/python research/continuation/build.py`
from the repository root for the retained-source build. It checks source/metric
bindings, rebuilds figures, compiles papers and refreshes public assets. It never
silently reruns collection, inference or training. Exact tokenizer reconstruction
is explicitly skipped in offline mode; retained length receipts remain available.
See [README.md](README.md), [models/README.md](models/README.md) and
[paper/README.md](paper/README.md) for separate replay and clean-package commands.

Base weights and model runtime caches live outside the repository at
`/workspace/channels-et-model-cache`. CPU model environments are
`/workspace/channels-et-model-venv` and `/workspace/channels-et-modern-venv`.
No CUDA device/runtime was detected. Font dependencies are checksum-pinned under
`/workspace/channels-et-tex`. Processes must restart after environment restoration.
A static server at the repository root supplies the research UI and legacy routes.

## Review and next studies

Rounds 10–12 continue the same acquisition, methods, extraction/model, analysis,
paper, dashboard and coordinating-skeptic roles. These are AI-agent technical
reviews, not human peer review. Distinct snapshots and exact artifact manifests
are under `rounds/`; review decisions are under `reviews/`. Exact final closure
is recorded in [FINAL-RELEASE.json](FINAL-RELEASE.json), created after the third
candidate is frozen, and the [decision ledger](reviews/DECISIONS.md).

Priority future work is source acquisition through genuinely available public
access, attributable answers from multiple practitioners, human prompt-equivalence
and entailment judgments, original-session resolution, equal-evidence/length
model comparisons and larger grouped held-out evaluation. New hypotheses and
falsifiers are specified in the manuscript, including shared-question answer
matrices, context-window effects, reuse collapse, temporal change and human
validation of retrieval/generation. None is labeled an executed empirical result.

Human authorship/affiliations, institutional determination, release rights,
construct validation and a concrete venue submission remain TBD. The long living
draft is not a compliant ICWSM submission by virtue of using the official style.
Hosted Sites/Overleaf publication has not been performed. Desired unrestricted
network configuration is already present; observed HTTP denials remain recorded
without assuming a single cause or advising duplicate configuration changes.
