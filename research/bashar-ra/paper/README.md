# Living Bashar–Ra research paper

This is an AI-assisted manuscript with human authorship, annotation and expert review explicitly TBD. It reports descriptive document analysis and source-linked interpretation, not verification of attributed entities or physical/medical claims.

The canonical editable text is `paper.md`; `paper.tex` is generated with Pandoc. `references.bib` records bibliographic details and abstract-only access where relevant. Approved numerical figures are retained as paired PNG/PDF files, with vector PDF images used in the compiled paper. `snapshot.json` pins their source analysis and hashes. No full source text or media is included.

Build from this directory with:

```sh
./build.sh
```

Dependencies: Pandoc with citeproc, pdfLaTeX, Python 3, and standard LaTeX packages including booktabs, longtable, hyperref, microtype and caption. The build writes the public PDF, source and figure bundle to `dist/bashar-ra/report/`. Build intermediates stay in `.build/` and must not be committed.

Update analysis snapshots explicitly before revising conclusions. Preserve the original fitted document frame; newly acquired excerpts belong in a separately declared supplementary study until an inclusion rule and updated result are documented. The source-reading companion `../READING.md` describes the exact bounded inspection coverage and counterexamples.

To refresh figures and metadata from an explicitly reviewed future run, use:

```sh
python3 refresh_snapshot.py --analysis /path/to/run/analysis.json --expect-sha256 EXPECTED_SHA256 --review-status draft
```

The command checks the selected analysis hash and every figure hash/size before copying. It does not rewrite narrative claims or declare human validation. Review the manuscript's values, source-reading coverage and supplementary metadata before rebuilding. Use `accepted-model-agent-audit` only when that specific run has actually completed the stated code/data review.

The final official-publication study is bound separately from the primary analysis. Refresh its figures and metadata with:

```sh
python3 refresh_official_supplement.py --analysis /path/to/final/official-speech.json --expect-sha256 EXPECTED_SHA256 --review-status draft
```

This rejects pilot output and a mismatched baseline hash. It preserves the historical 15-publication pilot, validates every copied figure, and records publication-versus-model-unit counts. Independent model-agent acceptance is distinct from human peer review. Revise the manuscript's supplemental methods, results and limitations before rebuilding.
