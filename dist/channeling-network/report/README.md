# Expanded channeling companion paper

This is a separate living research draft. It does not replace the existing Bashar–Ra paper. Human authorship, human annotation, substantive religious/platform literature review and external peer review remain TBD.

The fixed evidence includes the accepted 292-unit joint study (774,110 words), the separate 20-message pilot (20,829 words), and the 69-relation/19-group source graph. `snapshot.json` binds the exact public inputs. Ongoing acquisition and ASR counts are deliberately excluded from this edition.

Build the supplied Markdown, LaTeX and vector figures locally:

```sh
bash build.sh
```

Requirements: Bash, Python 3, Pandoc with citeproc, and pdfLaTeX with standard article, font, table, microtype, caption, float and xcolor packages. The build is local and needs no network or private corpus. It generates `paper.tex`, `paper.pdf` and a per-file SHA-256 `build-manifest.json`. A rebuild records its own output hashes; byte-identical PDFs across toolchains are not promised.

The six original plot families were copied from accepted model outputs unchanged. Two additional source/coverage figures can be regenerated with Python and Matplotlib:

```sh
python3 plot_snapshot.py
bash build.sh
```

That optional command reads only the supplied snapshot and fits no model. It does not regenerate the accepted topic/similarity figures, refit either corpus, download media or transcribe audio. Those operations have separate source permissions and private-input requirements described in the project methods.

The public manuscript contains derived statistics, source metadata and bounded paraphrases. No raw transcripts, complete copyrighted messages, private media, credentials or signed media URLs are included. Review corrections and remaining limits are described in the paper and its review note.
