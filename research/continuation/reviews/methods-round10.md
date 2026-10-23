# Methods and literature panel — continuation round 10

Baseline: new `occult-kranti/channels-ET` checkout at `faefa36`, with the prior expansion copied additively. This workstream writes only `research/continuation/literature/` and its review files. The original Bashar repository and inherited 28-source register were not edited.

The continuation now has a fresh, source-pinned methods base rather than inheriting the prior environment's failed requests. The runtime policy file reports unrestricted HTTP access; runtime readiness remains an observation, not universal authorization. Actual ordinary scholarly requests succeeded. Current publisher fulltexts for the two World Futures papers still returned HTTP 403, distinct from the previous environment's proxy tunnel denials. Their institutional abstracts and public supplements remain clearly different access layers.

Implementation produced:

- `source-register.json`: 18 freshly inspected/rechecked scholarly records, exact primary URLs, download hashes, selected reading locations, publication/access classes, supported use and non-transfer limitations. Prior 28 sources are preserved.
- `additions.bib`: nine new references, including official ACL BibTeX for six papers; other entries trace to official proceedings or the authors' repository citation. An accompanying TeX passage is ready for the paper.
- `RELATED-WORK.md`, `MODEL-EVALUATION.md`, and `ICWSM-STRUCTURE.md`: direct-study and YouTube precedents, source-grounded RAG/LoRA design, leakage/evaluation controls, and actual current venue rules.
- Retrieval receipts and `artifact-evidence.json`: 49 retrieved documents including pages, PDFs, BibTeX and supplements, kept outside Git with hashes. This is not 49 fully read papers. Exact reading depth is stated per source. No study was independently replicated by reading it.
- `venue-check.json`: official ICWSM 2027 Submit requirements and AuthorKit27/source/style hashes. The living draft may be long under the user's instruction; no venue-compliance claim follows.

| Finding | Evidence | Decision and observable acceptance |
|---|---|---|
| New policy warrants fresh source attempts | Actual source receipts after unrestricted policy observation | Implemented: official YouTube-method and RAG/FT papers retrieved; persistent publisher denials remain recorded. |
| Source speech, summaries and AI-mediated archival answers differ | JSE 2023 methods; JSE 2026 methods and public prompt supplement | Adopt typed units; never combine generated archival answers with observed speaker turns. Shared positive prompt framing and default-tokenization limitations retained as alternative explanations. |
| Existing account embeddings and topic overlap are not novel algorithms or answer agreement | Tube2Vec Sections 2–4; direct channeling studies | Paper contribution framed as proposed resource/integration value; no first-ever or origin claim. |
| Borrowing a paper's human validation would overstate this panel | Chen 2026 methods, ARES judge calibration | Own labels remain model outputs; human annotation/ethics/authorship stay TBD. No imported reliability statistic. |
| Retrieval lookup, RAG and LoRA require different execution evidence | Lewis/REALM/Hu parameterizations; Ovadia FT design | Later review must inspect actual retrieved contexts, generated outputs and trained adapter updates; an unrun arm cannot acquire metrics. |
| Exact-question/answer and source reuse can leak across evaluation splits | Lee 2022 dedup; inherited repeated-question/source families | Report known-record lookup separately, freeze splits and audit exact/near duplicate families; unresolved independence is explicit. |
| Long context or overlap score is insufficient substantive validation | Lost in the Middle; RAGAs; ARES | Token/evidence-position budget, source support, abstentions, and automatic-overlap proxy labels required; no human accuracy or truth claim. |
| Current template/guidance needs exact checks | Official ICWSM Submit and AuthorKit27 | Unmodified style; independent living-paper scope; authorship, ethics, rights, human labels and final checklist TBD. |

The source selection is targeted, not systematic. Publisher access depth, source arithmetic problems, data dependence and unexecuted comparisons remain visible. Round 10 establishes the baseline diagnosis and implements the methods/literature layer. Formal round 11 review waits for the root's frozen first continuation candidate; later iterations must inspect changed artifacts and record targeted corrections rather than re-certify this baseline.

Fresh official style comparison found that the retained historical `aaai2027.sty` differs from the current linked kit. The current official style hash is `01990f8d3716f8e39c5b28a7478f3ac6e28630d1161de6105a7217f5e7f60e43`; the earlier style hash is `391bce82815bf698b8e382dd3ae7e30c75d7ab46df140cb295b1266016bc8623`. The difference concerns title-footnote/copyright float handling. Paper ownership received the fresh unmodified bytes for the continuation build; historical files must remain unchanged.
