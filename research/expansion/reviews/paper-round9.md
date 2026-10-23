# Paper round 9: final sensitivity and artifact verification

This is the third new expansion review loop, following frozen rounds 7 and 8. Model-agent review is not human peer review.

## Implemented final corrections

- Added the actually executed Q&A retrieval-cutoff sensitivity table: cutoffs 0.40/0.50/0.60/0.70/0.80/0.90 retain 127/73/47/34/24/18 candidate question pairs and 71/34/19/11/11/9 distinct upload pairs.
- Explained that 30/127 retrieval matches (23.6%) arise from the three leading upload pairs. This is retrieval concentration, not a session-independence or repost estimate.
- Distinguished the 100-row summary preview from all 127 released pair records and clarified explicit false versus null CSV fields.
- Kept version-1 schema scope as inherited digest candidates; verified transcript turns and human validation remain absent.
- Refreshed the exact final Q&A and acquisition input hashes after the external-raw-directory and CSV-null corrections. The acquired-data count remains zero.
- Added informative PDF title/status metadata, fixed PDF date metadata to the evidence-date build epoch, and fixed ZIP entry metadata. The epoch is a reproducible-build setting, not a collection timestamp.

## Final artifact

Paper: `paper/channeling-atlas-expansion-paper.pdf`, **25 pages**, SHA-256:

`9eb942301eab65212b1c1f0aaae9c938e7f86b01d6e7ca7c9e6e90e7a8bd64e1`

Standalone source ZIP SHA-256:

`c0bf5184a71029fe7f1fbe38d5ca259d4a789866a69622b300665e3d6a5fa4d4`

## Executed checks

1. Two consecutive builds in the same machine/path produce byte-identical PDF and ZIP, recorded in `paper/repeatability.json`. This does not claim identical binaries across TeX versions/machines.
2. A fresh ZIP extraction compiled with PDFLaTeX, BibTeX and two further PDFLaTeX passes; every command returned zero and extracted page text was exactly identical to the delivered PDF.
3. All 25 final PDF pages rendered. The full contact sheet was inspected, with full-size page 14 checked for threshold-table values and interpretation limits. The corrected figure page was inspected for legend collision. No clipping or overlapping content was observed.
4. Final LaTeX pass has zero overfull boxes and no undefined citations/references.
5. All eight paper input-manifest hashes match current evidence files; all six copied figure PDFs match their analytical sources.
6. Independent methods and quantitative roles inspected the definitive PDF, including actual cutoff values, source/hash closure, paired versus pooled cohorts, and no answer-agreement overclaim. Their receipts are separately recorded in the expansion reviews/literature workstreams.

`paper/verification.json` binds commands and actual render paths to the final artifact. The source package compiles the frozen paper and contains no raw captions or model weights.

## Remaining limits

No new YouTube records or captions were acquired; planned searches/crawls remain unexecuted after the recorded policy block. The database contains one practitioner context and derivative digest paraphrases. New speech comprehension, speaker verification, caption-accuracy audit, cross-practitioner answer agreement, human annotation, ethics determination and submission are not completed. Proposed analyses remain visibly unexecuted.

Status: final paper implementation and bounded artifact verification complete. Publication and repository integration are separate coordinator actions.
