# channels-ET

Channeling Atlas is the cross-channel ET channeling research project. **Continue this analysis in `occult-kranti/channels-ET`.** The original [Bashar Index](https://github.com/occult-kranti/bashar-index) remains preserved and focused on Bashar. The existing copy of the Atlas in that repository is retained as history.

## Current analytical release — 23 October 2026

The analysis merges the original atlas with the supplied Claude archive: **925 unique uploads**, **881 usable durations**, **178 publishing groups with measured lengths**, and a **30-document English-caption pilot**. These are convenience-sample records, not counts of unique or currently active human mediums. The historical discovery and service-audit layers described below remain available.

- Interactive per-account duration tables, titles, captions and learned embeddings: `#/analysis`.
- Source-linked report: `dist/analysis/report.html`.
- Complete working paper: `dist/analysis/channeling-atlas-paper.pdf`.
- Importable LaTeX source: `dist/analysis/channeling-atlas-overleaf.zip`.
- Data/code and first three review rounds: `research/analysis/`.
- Paper source, 28-source scholarly register, generated figures, three further review rounds and update protocol: `research/paper/`.

The dashboard analysis was published before paper work began. The manuscript uses the official AAAI 2027 preprint template and marks human authorship, construct validation, institutional ethics determination and checklist completion as TBD. It has not been submitted.

## Handoff: resume here

**Status:** both requested phases are complete: analysis rounds 1–3, then manuscript rounds 4–6. The next phase is planned, not executed. The scientific snapshot was originally released as [`bbe4801`](https://github.com/occult-kranti/bashar-index/commit/bbe4801a09c28f07eeea6f0fe7e9f0d61e4d791f). Its complete project files are preserved here at import commit [`07724b1`](https://github.com/occult-kranti/channels-ET/commit/07724b1b92a116bc231fe701629912260e3f64bd) on `release/channeling-atlas-2026-10-23`. The repository split updates continuation guidance and future output links; reviewed data, figures, PDF and ZIPs retain their original bytes. See [migration provenance](research/maintenance/MIGRATION.md).

| Start with | Purpose |
|---|---|
| [Live dashboard](https://channeling-atlas.whatswrong-inc.chatgpt.site) | Per-account statistics, discovery index, timeline, services and analysis |
| [Research report](dist/analysis/report.html) | Interpretation, source access and limitations |
| [Paper PDF](dist/analysis/channeling-atlas-paper.pdf) / [Overleaf ZIP](dist/analysis/channeling-atlas-overleaf.zip) | Reviewed 12-page working manuscript and compilation source |
| [Analysis protocol](research/analysis/protocol.json) / [paper protocol](research/paper/protocol.json) | Units, scope, release state and completed rounds |
| [Final review ledger](research/paper/reviews/coordinator-completion.json) | Six workstream receipts tied to exact PDF and snapshot hashes |
| [Scholarly register](research/paper/literature/annotated-bibliography.md) | 28 references, reading depth and access limitations; 23 cited in the paper |
| [Skill panel ledger](research/analysis/panel/skill-panel.json) | Transferable practices from the available custom skills and inapplicable domain-specific instructions |
| [Branch register](research/maintenance/branch-register.json) | Repository layout, baseline commits and branch roles |

**Do not conflate the units.** 925 uploads, 178 account groups with durations, 30 English caption documents, and 22 videos from 11 accounts in the matched centroid comparison are different denominators. None is a worldwide active-medium count. The older activity/service layer has its own October 22 cutoff; the analytical release is dated October 23. Prices and future events need a new source check before being described as current.

**Retained evidence:** public metadata, source links, numeric vectors, code, figure inputs, frozen rounds and review receipts are committed. Raw captions, retrieved author-message bodies and model weights are excluded. Offline reproduction uses frozen derivatives; inference replay needs authorized local caption text and the pinned model. An earlier scratch path is not a durable dependency.

**Release pins:**

```text
Analysis data SHA-256
f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc
Paper PDF SHA-256
c9e7b736f1604b1801b3dfe48919a7e4604343c92a7a29fde79c9574b7ac9716
Overleaf ZIP SHA-256
f35108542cfad5e4ff5d6f9984d3334885875c180c07a3d23019eee132e6ac98
```

### Repository and branch workflow

The GitHub repository `occult-kranti/channels-ET` contains this project directly at its root: `dist/` is the website and downloadable artifacts; `research/` contains the data pipelines, source records and paper. Run commands from this repository root. The existing Sites deployment is a separate checkout and history; its private hosting identity is intentionally excluded from this export. The original `occult-kranti/bashar-index` repository is preserved, including its cross-channel historical copy and experiment branch.

| Branch in channels-ET | Role | Maintenance rule |
|---|---|---|
| `main` | Reviewed import and current continuation documentation | Merge bounded reviewed changes; verify the latest head before pushing |
| `release/channeling-atlas-2026-10-23` | Exact project import at `07724b1` | Keep pinned; create a new dated release branch for later scientific releases |
| `research/channeling-atlas-next` | Continuation branch, including this repository handoff | Start the next bounded research task here; use ordinary commits |

The earlier Bashar repository branch audit is retained in [the origin branch register](research/maintenance/branch-register-bashar-origin-2026-10-23.json). It does not describe this repository's branches. The frequency-of-place experiment remains in `bashar-index`; it was not imported as a new experiment here. Branch protection is not configured by this import; the release pin is a documented convention.

Use task branches such as `research/atlas-identity-audit`, `analysis/atlas-speaker-segments`, `paper/atlas-next-draft` and `fix/atlas-<issue>` only when starting that work. Preserve prior snapshots and never reuse old review receipts to certify a changed artifact. Avoid force-pushing shared branches. Before merging an experiment, compare changed paths, check overlapping root files and run its own domain and build checks.

### First actions in a fresh checkout

For this GitHub checkout, select `research/channeling-atlas-next` and remain at the repository root. There is no nested `channeling-atlas/` directory here. Inspect status before changing branches or generating files.

```sh
git status --short
python3 research/validate.py
python3 research/validate_discovery.py
node --check dist/app.js
sha256sum dist/analysis/data.json dist/analysis/channeling-atlas-paper.pdf dist/analysis/channeling-atlas-overleaf.zip
```

These validators cover the retained historical atlas/discovery layers; they do not certify new activity evidence or the entire paper. Their date assumptions must be reviewed when the cutoff changes. Read the analysis and paper READMEs before selecting the relevant build layer.

For an offline paper reproduction, use a **disposable worktree or copy**. From that copy's Channeling Atlas root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r research/analysis/requirements.txt
python research/paper/scripts/analyze_paper.py
python research/paper/scripts/generate_results.py
bash research/paper/build.sh
python research/paper/scripts/package_paper.py
python research/analysis/build_report.py
```

Install the TeX dependencies listed in [the paper README](research/paper/README.md). The offline commands reuse the saved pooling experiment and do not rerun raw-caption inference. Compare numerical outputs, inspect all changed figures and the rendered PDF, then record a new receipt. PDF timestamps can alter binary hashes on recompilation; the distributed PDF hash identifies the original reviewed artifact.

**Write behavior matters:** `build.sh` replaces the public PDF; `package_paper.py` replaces public paper exports and the Overleaf ZIP; `build_analysis.py` writes analytical outputs and its language cache. `compile.py` writes the historical atlas layer and must not be used as a generic first step. `close_reviews.py` is a historical rounds 4–6 closure utility, not a general completion command. Several old verifier scripts also overwrite their named receipts. Run reproductions in isolation and create new round directories for new work.

## Roadmap: next research phase

All items below are **planned**. Use the six established workstreams as roles, not as evidence of independent human review. Start with N1; expand collection only after its inclusion and identity rules are written.

| Priority / ID | Next task and lead roles | Concrete completion evidence |
|---|---|---|
| P0 / N1 | Define the sampling frame and audit practitioner ↔ uploader ↔ entity ↔ original-session identities. Provenance + corpus. | Versioned inclusion/exclusion rules, alias table, unresolved cases and original/repost classifications. A human count must have deduplicated identities and dated supporting records. |
| P1 / N2 | Refresh 30-day and 365-day activity, official services, next sessions and prices at an explicit new cutoff. Corpus + provenance; depends on N1. | Per-source check time, event date/time zone, currency, free/paid/access status and original/repost distinction. Report verified sample minima and unknowns; retain superseded observations. |
| P1 / N3 | Expand the caption pilot with a predeclared stratified selection rule and access log. Corpus + methods; depends on N1 and initial N4 findings. | Fixed selection order/seed, per-account target, language/format strata, failures and coverage. Track title eligibility separately from caption availability and contributing account thresholds. |
| P1 / N4 | Validate caption accuracy and label host/message/promotion segments; distinguish topical overlap from answer agreement. Methods + human reviewers; start on the existing 30-document pilot after N1 and appropriate ethics determination, then extend to N3. | Written codebook, auditable annotation subset, disagreement handling and an appropriate agreement/error measure. Keep human labels separate from model-agent labels. |
| P2 / N5 | Resolve original-session reuse and compare formats before interpreting entity-label groupings. Provenance + analysis; depends on N1/N4. | Session-family and format annotations, matched reanalysis and explicit records of unresolved edits/reposts. |
| P2 / N6 | Compare the lexical baseline, pinned MiniLM and a contemporary or multilingual encoder on identical validated items. Analysis + methods; depends on N4/N5. | Model revisions/licenses, held-out human judgments, matched denominators, weighting/threshold/language sensitivity and a record of failed or negative results. Do not infer domain performance from benchmark rank alone. |
| P2 / N7 | Update dashboard, report and living paper with new evidence. Implementation + literature + design; depends on relevant completed items above. | New frozen snapshot and deliberate input repin, regenerated tables/plots, caption/denominator audit, PDF inspection, isolated reproduction and fresh review receipts. Keep rounds 1–6 intact. |
| P3 / N8 | Prepare a concrete submission only after authorship and validation decisions. Human authors + literature/methods. | Authorship/affiliations, ethics determination, rights review, current venue instructions, completed checklist and disclosure placement. All remain TBD in the present draft. |

Candidate hypotheses to investigate: upload format may explain more variation than attributed-entity labels; host/promotion segmentation may change nearest neighbors; original-session reuse may inflate similarity; matched titles may retain broad vocabulary while losing answer-level content. These are testable questions, not established findings. Predefine the comparison unit and a disconfirming outcome before testing each one.

### Next release acceptance

Freeze collection and model versions; preserve source access levels and nulls; regenerate only affected layers; compare all changed claims with underlying rows; inspect every changed figure and PDF page; record independent workstream findings and corrections; then push the reviewed source and artifacts, publish the Site, and create a new dated release branch. Record GitHub and Site commits separately. Publish new cross-channel work to `channels-ET`; keep Bashar-specific changes in `bashar-index`. This README establishes the continuation process; it does not schedule unattended updates.

## Earlier atlas and discovery layers

A static research website with 26 public practitioner/lineage profiles, 49 documentary timeline entries, 190 source records and 14 selected community discussions. The expanded YouTube index contains 25 account records and 58 unique videos; the earlier 14 video/channel/catalog routes remain available. Original profile/activity cutoff: October 22, 2026. Deep-discovery expansion checked October 23, 2026.

The October 23 expansion contains 873 unique linked records: 482 videos, 169 playlists, 157 account routes and 65 websites, grouped under 106 practitioner/lineage/partial-name records. It includes the complete extracted YouTube-link metadata from the pinned `occult-kranti/bashar-index` repository plus manual browser searches and species-led web discovery. Explicit account aliases are merged; unresolved aliases remain visible. The 191 search/seed entries include failed Exa requests, not 191 successful source reviews.

`#/discovery` is the main expanded index. `dist/exports/channeling-research-csv.zip` includes master and type-specific CSVs, a person/practice table, query ledger, provenance summary, upstream MIT license, unresolved-attribution links and 106 individual files under `by-channeler/`. These entries include historical lineages, partial names, possible aliases, narrators, music/light-language and non-ET guide context; they are not a unique-human or annual-active census.

Ra is the central entry point. The earlier-history timeline includes Spiritualism, Theosophy, Alice Bailey, Van Tassel's Ashtar material and Seth. Featured contemporary profiles are Darryl Anka / Bashar, Athina Król / Ashtar and Tyler Ellison / Ryokah.

## Content boundaries

A source record documents an attributed claim and how its text or metadata was accessed. It does not validate extraterrestrial origins, spiritual identities or medical/financial outcomes. The public-source sample is curated, not exhaustive. YouTube access levels and source-date conflicts are retained. Private communications, closed groups and paid recordings were not accessed.

The comparison groups are editorial categories, not astronomical maps or verified species. Shared names do not establish shared origins or direct influence. Predictions remain in a separate forecast register rather than appearing as future historical occurrences.

The annual activity window is October 22, 2025–October 22, 2026. The reviewed sample supports 13 distinct named humans with dated ET-associated material, including messages, recordings and channeling-related interviews. It is a confirmed minimum within the sample, not a worldwide census or a count limited to new YouTube performances. The Elan project has January 2026 material, but the cited exchange does not identify its human channeler; it remains unconfirmed outside the named-human count.

Service audits cover 14 contemporary ET-associated candidates, including Elan. Five have verified future public session dates and one has a displayed future private opening. Displayed prices, currency uncertainty, free replays, paid live access and private booking availability are distinguished. The schedule uses the late-evening October 22, 2026 New York cutoff; an offer is not evidence that a session occurred, and an undated or stale listing is not a confirmed future date.

## Files and reproducibility

- `dist/`: published buildless HTML, CSS, JavaScript and JSON.
- `research/*.json`: bounded source-led workstreams, including source-access notes.
- `research/deep/*.json`: source/query-led discovery workstreams; `repo_raw/` retains the pinned input audit and upstream license.
- `research/extend_discovery.py`: deduplicates media IDs and explicitly linked account aliases, retains provenance, and generates CSVs/ZIP.
- `research/validate_discovery.py`: checks URL/media identity, source trails, practitioner links, every CSV and archive integrity.
- `research/youtube/*.json`: YouTube accounts, individual videos, annual activity evidence and supplementary service audits.
- `research/compile.py`: deduplicates and compiles the published dataset with editorial synthesis.
- `research/extend_youtube.py`: merges the expanded index, dated activity checks and service audits into the compiled dataset.
- `research/validate.py`: validates references, source identity, chronology, required caveats and named profile anchors.

Run the validators for the layer being changed. `research/compile.py` is a writer for the historical atlas, not a general validation command; use it only when rebuilding that layer and follow its extension steps. See the handoff above for a safe starting sequence. Serve `dist/` for local development. The root `index.html` forwards to `dist/`; the static app itself remains in `dist/`. The existing Sites hosting configuration is maintained separately and is not included in this GitHub export.

## Verification

Research data validation checks all source and profile references and keeps anticipated occurrences outside the documentary timeline. Independent editorial checks of the initial profiles and the current activity/service update found no blocking count, date, attribution or currency issue. Initial browser checks and their limits are preserved in `research/qa.md`; the expanded index, session filters, chart navigation, detail records and CSV exports also passed rendered-browser checks. A separate narrow-viewport browser run was unavailable.
