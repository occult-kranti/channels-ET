# Independent three-round transcript-study review

This workstream preserves the earlier collection runner and reads source-owner artifacts without editing them. The three reviews cover method design, independent source/numerical/construct checks, then the actual paper/dashboard candidates and release bindings. They are AI-assisted technical reviews, not human peer review, transcription validation or annotation-accuracy measurement.

`round-1-methods.md` records the initial unit, sampling and interpretation constraints. `round-2-findings.md` records executed calculations, substantive counterexamples and addressed issues. The final round and release manifest bind the actual reviewed PDF, source bundle and dashboard exports; a review of an earlier candidate does not certify later bytes.

The source baseline directly checks the 20 ASR and 16 authored-text materials. Numerical auditing uses an independently written count/TF–IDF/normalization/cosine/silhouette calculation, selected statistical refits, and original lexical dictionaries as declared measurement inputs. It never imports the author builder. Reading auditing reconstructs all source windows, source hashes, support anchors, overlap-deduplicated denominators and DB/CSV joins. Eight purposeful qualitative spot checks are kept separate from locator integrity and are not an accuracy estimate. Storage auditing directly hashed 99 original files and 200 copied archive files, then reused that audit for a coverage-only revision with unchanged source inputs.

The review retained the 19:1 audio imbalance, selected singleton partition, weak separate authored clustering, contradictory/critical source context, incomplete negation retention and post-hoc unvalidated spelling retrieval. Full computation over a document is distinct from AI close reading of selected windows. The original transcripts, publication bodies, metadata with signed URLs and audio remain private.

From the repository root, with the matching lawful private snapshots present, source and calculation checks can be rerun offline:

```sh
python3 research/transcript-review/source_baseline.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/channels-et-analysis-venv/bin/python research/transcript-review/audit_numeric.py
python3 research/transcript-review/audit_reading.py
python3 research/transcript-review/audit_spelling.py
python3 research/transcript-review/audit_storage_binding.py
```

`audit_storage.py` is the more expensive full private-source/archive hash audit; rerun it when its input pins or retained copies change. `audit_storage_binding.py` explicitly reuses the completed raw-byte evidence when only final coverage metadata changes. Public clones lack those private third-party materials; stored receipts permit review of completed checks without falsely claiming that every source is publicly redistributed.

`verify_paper_release.py` independently compiles the actual standalone ZIP with pdfLaTeX/BibTeX and checks the released PDF text, embedded fonts, input hashes and corrected claims. It requires the prepared TeX environment, not network access. `audit_ui_binding.py --directory PATH` compares actual exported dashboard bytes and nested objects to all source inputs. Rendered interaction evidence is supplied separately by the independent UI reviewer, with its exact candidate hashes.

The validation workflow follows the available `data-analytics:validate-data` skill. Its linked shared-resource pages could not be read in this session; the supplied workflow's source-fitness, independent calculation, presentation and conclusion checks were applied using local records. No new network acquisition or LLM/ASR run was performed by this review.
