# Paper review and implementation: round 12

This is an implemented model-agent review cycle after frozen round 11, not human peer review. Historical papers and the original Bashar Index were not edited by this workstream.

The final manuscript is 16 pages, with ten figures and seven tables in the unmodified official AAAI 2027 preprint style. It is a living draft; human authorship, construct validation, institutional determination, rights review, venue choice and submission compliance remain TBD.

## Corrections implemented

- The abstract now gives one measured result: matched title/caption rank association 0.249 before and 0.129 after measured length conditioning, explicitly descriptive. Source reuse remains a possible explanation rather than a verified session relation.
- The same-item option-order probe reports nine parsed outputs in each condition, eight paired parses and six changed themes, with zero selections of the reversed first option. This disconfirms simple first-option copying while preserving local prompt sensitivity.
- The post-hoc conditionality dictionary sensitivity changes 60 to 58 flags among 949 source gists; it is not human validity and does not revise primary labels or the original split.
- The Qwen3.5 same-twelve annotation run is distinct from the Qwen2.5 five-arm pilot and trivial JSON compatibility probe. Its table separates 12/12 parsing, 10 literal source spans and five exact spans within eight words. Five literal spans exceed the length limit and two are nonexact; combined failures are not all invented spans. All twelve conditional outputs are yes, so 6/12 dictionary concordance equals the always-yes baseline.
- Model/tokenizer/runtime differences remain uncontrolled. The annotation comparison is a local compliance diagnostic, not a human accuracy or general model ranking result. Training-only retrieval, unequal extractive/generative budgets, strict marker versus broader post-hoc phrase scoring, output caps, citation failure and unsupported numeric output caveats remain explicit.
- Appendix A.4 points to the twenty single and twelve paired retained model-assisted digest readings with source hashes/pointers. These ledgers contain no human validation or raw-media viewing; paired agreement remains undetermined. Appendix A.3 now has explanatory prose even when its table floats.
- The input manifest binds all final prompt/order/regex/new-family/comparison artifacts and the current numerical results. Pinned standalone analysis interpreter instructions replace historical environment references.

## Executed final validation

- Two consecutive final-source builds produced identical PDF, source ZIP and input-manifest hashes. See `paper/repeatability.json`.
- The clean extracted source ZIP compiled successfully through PDFLaTeX, BibTeX and two final PDFLaTeX passes. Extracted page text matches the repository-built PDF exactly.
- All 16 final pages rendered and were visually inspected in four labeled contact sheets. No clipping, label collision or table collision was observed. This is model-agent visual inspection, not human peer review.
- All fonts are embedded; no Type 3 fonts, undefined references/citations or overfull boxes remain.
- All 33 input hashes are current, all six copied continuation analysis PDFs are byte-identical to source figures, and all 26 source ZIP members match their current manuscript files.

Definitive PDF SHA256: `590460ca284cd1a3de98eefff71a5dbb2bbdf76296f8b2a868fba3a9d7e00cda`.

Definitive source ZIP SHA256: `497f8a05bc3fde86cff3c2d86a630711fbdc9068062c49cbbfab14ad12b12326`.

Final analysis results SHA256: `14992d2f820d6cf3bf06af73fbf9b8716002cd8e4c5d34c8bc0a8d18827ac0dd`.

The manuscript is locally built and reviewable. This receipt does not claim a successful new YouTube acquisition, human peer review, venue compliance, submission or publication.
