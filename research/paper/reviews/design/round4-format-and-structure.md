# Manuscript round 4: verified format and design contract

Status: working draft, not submission-ready. Verified 2026-10-23 against the current official ICWSM 2027 page.

## Venue requirements (summary, under 200 words)

The initial full-paper limit is 11 pages including references (8 recommended); R&R and camera-ready limits are 12. Use English, US Letter, AAAI two-column, high-resolution PDF. Full papers use double-blind review. The complete, unaltered paper checklist follows references and precedes optional appendices; both checklist and appendices are outside the page limit. Reviewers need not assess appendices. Omitted checklist causes desk rejection. Content-generation AI use must be disclosed in Acknowledgements; AI cannot be an author. Basic spelling/grammar, translation, and standard reference management are exempt. The same page bars acknowledgements in review copies: disclosure placement therefore needs venue clarification before any submission. Author identities, funding, conflicts, human ethics determination, and checklist answers remain human responsibilities, currently TBD. Next listed full-paper round is January 15, 2027 AoE.

Source: https://www.icwsm.org/2027/submit/ (Formatting, Full papers, Paper Checklist, Anonymity, Generative AI Disclosure). Do not substitute AAAI main-track 7+references rules.

## Template provenance and working-draft preamble

Official archive: https://aaai.org/wp-content/uploads/2026/05/AuthorKit27.zip . Source/license manifest and hashes are in `../../vendor/source-license-manifest.json`. Official files remain unchanged. The official 2027 page links this kit and an older 2026 Overleaf template; the directly retrieved 2027 kit is used here. No blanket CC-BY claim is made for the 2027 kit; its BST explicitly permits LPPL 1-or-later redistribution. Style notices prohibit modification for AAAI publications.

Use the style's supported `[draft]` option for a visible working draft with copyright disabled. Use an explicit working-draft author placeholder; do not assert actual authorship. The `[submission]` option carries a submission-only footer, so it is inappropriate for a public working draft. Use PDFLaTeX. The2027 style loads fonts itself: do not import `times`, `helvet`, or `courier`. Load natbib and caption without options. The style selects `aaai2027.bst` automatically. Avoid a second bibliography-style declaration and any margin/font/spacing overrides. Supported draft styling is not a claim of compliance or acceptance.

```tex
\documentclass[letterpaper]{article}
\usepackage[draft]{aaai2027}
\usepackage[hyphens]{url}
\usepackage{graphicx}
\urlstyle{rm}
\def\UrlFont{\rm}
\usepackage{natbib}
\usepackage{caption}
\usepackage{booktabs}
\frenchspacing
\pdfinfo{/TemplateVersion (2027.1)}
\author{Working Draft --- Human Authors TBD}
\affiliations{}
```

Set `TEXINPUTS=vendor/AuthorKit27//:` and `BSTINPUTS=vendor/AuthorKit27//:` from `research/paper/`. The untouched style uses newtxtext and requires PDFLaTeX. If any dependency is missing, install its official TeX package rather than altering the style.

## Primary full-paper design examples

- Boesinger et al., Tube2Vec (ICWSM 2024), official 7-page PDF: https://ojs.aaai.org/index.php/ICWSM/article/download/31450/33610/35506 . Its flow introduces a sharply illustrated semantic-versus-social distinction, then data, embeddings/evaluation, results, limitations and ethics, references, checklist. Compact validation figures precede interpretation. Relevant design lesson: define similarity operationally and show what validates it; our pilot lacks their crowdsourced validation, so cannot inherit their claims.
- Chen et al., The Digital Landscape of God (ICWSM 2026), official 18-page PDF: https://ojs.aaai.org/index.php/ICWSM/article/download/42649/50209/46750 . Its body uses introduction with explicit RQs, related work, data/methods, results, discussion/limitations, conclusion, ethics, references, checklist, appendices. Appendix carries detailed tables. Relevant design lesson: connect every visual to a question and distinguish content coding from interpretation. Its human validation, comment analysis, and sample cannot be attributed to our study. Published total length includes extras and does not set our initial-submission page budget.
- TubeCensus (ICWSM 2026) is a **dataset paper**, not a full-paper exemplar: https://ojs.aaai.org/index.php/ICWSM/article/view/42782 . Its abstract supports attention to coverage and identifier resolution, but I have not read its complete PDF and do not claim a full structural audit of it.

## Proposed figure and layout contract (our design inference)

1. Lead the results with collection-to-analysis coverage and explicit units (video IDs versus publisher IDs versus medium identities).
2. Duration: measured n, mean and median, minutes, convenience-sample qualifier. Retain missingness; do not title it population average.
3. Similarity: state representation, cosine unit, paired-video sample, channel/publisher grouping, document count, and corpus exclusions. A diagonal of1 is a construction, not evidence.
4. Sensitivity: preserve negative values; show leave-one-publisher-out or truncation results as sensitivity, not inferential proof.
5. Prefer two-column width for comparisons with several labels, single-column for simple coverage/duration charts. Keep labels readable at final print size; no raster screenshot of a dashboard.
6. Every caption should independently identify unit, denominator, data layer, transformation, and the main boundary on interpretation; move procedural detail to methods.
7. Cite each figure before or near it. Put the methods needed to interpret a result in the main body; optional appendices hold export schemas and exhaustive tables.
8. Review actual rendered pages for clipped content, tiny labels, caption-figure separation, orphaned headings, table overflow, and reference formatting. Extracted text alone cannot establish visual quality.

## Review schedule and honest completion criterion

Round4: inspect first compiledPDF and record specific page/figure findings. Round5: verify fixes and review revised flow. Round6: re-render final revision and verify remaining layout/caption issues. None of these rounds can be called visually passed until images have been inspected. Parent owns main.tex, body.tex, build, and any publication decision.
