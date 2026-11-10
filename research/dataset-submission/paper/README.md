# Channeling Atlas dataset paper

This is a complete working manuscript, not a conference submission or acceptance. The verified target is the ICWSM 2027 Datasets track, **15 January 2027, 23:59 AoE**. The official call requires a dataset DOI and an unchanged completed checklist. Human authorship, institutional determination, final source rights/access arrangements and DOI remain unresolved.

Build from this directory with `bash build.sh` using PDFLaTeX, BibTeX and a complete TeX installation including the unmodified AAAI2027 template dependencies (newtx, natbib, caption, graphicx, booktabs, amsmath). The cloud build can reuse the existing external font tree. The script writes `paper.pdf`, `overleaf-source.zip`, and `build-receipt.json`. The ZIP imports into Overleaf: select `paper.tex` as the main document and PDFLaTeX as compiler. It does not download source material or run models.

The manuscript reports the frozen, reconciled selected-publication frame. `generated/frame-binding.json` records its SHA and denominators. `generated/` contains numerical inputs and explicitly admitted figures. The main body and references must fit within ten pages; the separate checklist follows references. Every question is preserved, with working evidence-based answers and explicit pending items rather than invented approval.

Venue facts and literature access depth are recorded in `../venue/`. The public data package excludes raw audio and full source text. The paper must distinguish metadata/derived-output reproduction from full text or speech recomputation using authorized retained artifacts. No source license is replaced by the repository's own code or document license.

Before an actual submission, human authors must review the text, claims, checklist, author list, institutional requirements, participant/privacy and asset rights, final dataset deposit/DOI, availability to reviewers, final PDF, duplicate-publication rules, and the then-current venue call. Generative-AI assistance is disclosed in the paper. Model-agent review is not human annotation or external peer review.
