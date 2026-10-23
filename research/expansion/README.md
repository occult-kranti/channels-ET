# Channeling Atlas: from uploads to questions

This extension was migrated additively from Bashar Index commit `151efb2` into
`channels-ET`. Historical review archives preserve their original paths and hashes.
Current build scripts use the new repository root.

This extension preserves the original 925-upload scientific release and manuscript
rounds 1–6. It adds a reproducible collection tool, identity/search frame, a
source-addressable digest Q&A database, new diagnostics, a rewritten manuscript
and an evidence explorer. It is exploratory computational research, not an
accepted paper or a human annotation study.

## Read and inspect

- [Protocol and acceptance criteria](PROTOCOL.md).
- [Evidence explorer](../../dist/expansion/index.html).
- [Complete rewritten paper](paper/channeling-atlas-expansion-paper.pdf) and
  [LaTeX source ZIP](paper/channeling-atlas-expansion-source.zip).
- [SQLite Q&A database](qa/qa-candidates.sqlite), [JSON](qa/qa-candidates.json),
  [CSV](qa/qa-candidates.csv), [codebook](qa/codebook.json), and
  [model-assisted close reading](qa/close-reading.json).
- [Collection instructions](acquisition/README.md),
  [planned queries](acquisition/collection-plan.json), and
  [identity links](acquisition/identity-publisher-links.json).
- [Executed diagnostics](analysis/README.md), [results](analysis/results.json),
  and [figure exports](analysis/generated/figures).
- [Methods and literature](literature/METHODS.md),
  [scholarly access register](literature/scholarly-register.json), and
  [software register](literature/software-register.json).

The Q&A release contains **949 AI-digest paraphrase candidates**, from **67
Q&A-bearing uploads among 75 digests**, all in one Darryl Anka-related practitioner
context. It resolves 27 publisher IDs and retains seven unresolved publisher-name
groups (105 candidates). The inherited roster contains 106 practitioner, lineage
and partial-name candidates; it is neither 106 verified humans nor 106 Q&A corpora.
Missing Q&A for the other identities remains visible. The database cannot support
cross-practitioner answer comparisons yet.

The caption pilot, title vectors and digest Q&A are separate evidence layers.
Model-agent close reading concerns the available summaries; it is not watching
videos, listening to audio, validating captions or conducting human peer review.

## Collection state

The collector is installed and locally tested. The current execution ledger
records one ordinary YouTube watch preflight denied by the environment's outbound
proxy and zero successful new source collections. The 590 keyword searches, 157
account routes and 215 caption candidates are **planned operations**. They are
not a newly crawled dataset. Frozen derivatives cannot recover the excluded raw
caption text.

Required YouTube and scholarly-source destinations were saved to the environment
configuration draft. Review/save the relevant changes in environment settings and
publish the environment before retrying. The collector supports ordinary public
access, bounded batches and resume; it stops on an access denial. Its README
contains exact commands. Raw captions stay outside Git. No cookies, private access,
rotating proxies or access-control workarounds are part of the pipeline.

## Rebuild the executed extension

Run from the `channels-ET/` repository root. Cloud tasks
are already isolated; do not create a worktree unless explicitly requested. The
commands regenerate only the new extension. Preserve user edits before rebuilding.

```sh
source .venv/bin/activate
export MPLCONFIGDIR=/workspace/setup-validation/matplotlib
export XDG_CACHE_HOME=/workspace/setup-validation/cache
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
python research/expansion/qa/build_qa.py
python research/expansion/qa/verify_qa.py
python research/expansion/analysis/analyze.py
python research/expansion/analysis/figures.py
python research/expansion/analysis/verify.py
python research/expansion/paper/scripts/generate_paper.py
bash research/expansion/paper/build.sh
python research/expansion/paper/scripts/package_paper.py
python research/expansion/dashboard/build_dashboard.py
python research/expansion/verify_release.py
```

Python uses the original pinned `research/analysis/requirements.txt`, with collector
dependencies pinned separately in `acquisition/requirements.txt`. The paper uses
PDFLaTeX and standard article packages. No model download is needed for retained
feature recomputation. Full speech inference needs authorized local captions and
the existing hash-verified model workflow, not this frozen-feature build.

For a fresh Python environment, install `research/expansion/requirements.txt`;
it includes both sets of pinned direct dependencies. The single offline rebuild
entry point is `python research/expansion/build.py`. It does not execute live
searches or change the preserved original analytical release.

Serve `dist/` with a standard static server. The explorer is `expansion/index.html`.
Keep source and static export copies synchronized with `build_dashboard.py`.
Previous routes and the original root Bashar Index remain available.

## Review and release records

New review cycles are rounds 7–9, with model-agent findings in `reviews/` and
immutable candidate archives/manifests in `rounds/`. Each review concerns an actual
changed artifact. Earlier scientific receipts do not certify this extension.
Independent source-lineage, numerical, SQLite, lexical-retrieval and browser checks
are technical verification, not accuracy judgments about the original speech or
evidence of extraterrestrial claims.

This migrated GitHub checkout does not contain the old Sites checkout, its hosting identity
or the two historical atlas validators referenced by the earlier handoff. Current
tools expose no Sites deployment operation. Local artifact verification and a
GitHub branch update therefore remain separate from live-site publication. The
shared Data app runtime/reference was unavailable; the explorer extends the
existing static stack and is tested in a browser. It is not claimed as a verified
shared-runtime Data app.
