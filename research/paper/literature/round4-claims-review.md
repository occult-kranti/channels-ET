# Manuscript round 4: literature and interpretation review

Reviewed 23 October 2026. The exact frozen inputs and SHA-256 values are in `round4-reviewed-inputs.json`. This review covers the argument, source claims, citation metadata and captions in the LaTeX source. It does not claim a rendered-layout inspection or independent human peer review.

## Findings requiring correction in round 5

1. **Qualify the 2023 protocol.** The frozen related-work paragraph correctly distinguishes quantitative US n=7 from qualitative total n=15, but calls all ten prompts “scientific questions” and describes fixed order/unequal timing without a site qualifier. Use “scientist-supplied questions” and “In the US protocol, the conditions followed a fixed order with different response-time allowances.” The corpus reviewer read the full article and independently reported the same issue.
2. **Acknowledge the closest existing account-embedding method.** Tube2Vec already averages MiniLM-derived upload metadata into account vectors. Cite `boesinger2024tube2vec` and place novelty in the bounded provenance audit, matched title/caption comparison, and sensitivity analysis. The manuscript currently makes no explicit first-method claim, so this is contextual strengthening rather than a retraction.
3. **Add the AI-mediated direct-domain comparator carefully.** `wahbeh2026records` compares pairs of UFODex-generated answers to matched questions, not direct pairs of raw corpora. A short sentence or paragraph must retain that intermediate layer. Do not pool its cosine magnitudes with ours or cite it as corroboration of independent entities.
4. **Bibliography fixes applied in the live round-5 bibliography:** `June` normalized to `jun`; official ICLR2025 MMTEB conference metadata replaces the arXiv-only entry; Starbird pages 365–374 added. The frozen round-4 bibliography is intentionally unchanged. The live bibliography now contains 28 relevant entries; there is no requirement to cite all of them.

## Claims that are adequately bounded

- The paper treats people, uploaders, uploads, original sessions and attributed labels as different units. It does not present an account count as a count of mediums.
- The matched-ranking result uses 22 contributing videos, 11 accounts and 55 dependent pairs; 25 videos refers to the wider matched-indicator pool. This is more precise than the earlier dashboard eligibility headline.
- Rank sensitivity is described as descriptive, without independent-pair p-values or population confidence intervals. Caption trimming is not called diarization.
- Similarity is not treated as agreement, credibility, origin verification, a diagnosis, or a measure of spiritual effectiveness.
- The 2026 prospective studies' publisher-access limits and incomplete public supplement are explicitly disclosed. They are not described as replicated or independent companion experiments.
- The statement that current MiniLM is an auditable baseline, not state of the art, is supported. Broader benchmark citations do not validate this corpus.

## Remaining limitations to preserve

Automatic captions are not corrected against audio, the pilot is purposive, and repeated sessions are unresolved. These are measurement limits, not merely reasons to run a larger encoder. Human validation remains TBD. Repeated model agents are not independent human reviewers. The nearest-neighbor labels should remain exploratory even when broad rank correlation is high.

## Review disposition

Proceed to round 5 after the protocol wording and close-comparator context are revised. No numerical rerun is requested by this review. No publication readiness, ethics approval, or source-authenticity conclusion follows from this disposition.
