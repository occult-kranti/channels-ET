# Dataset release and ICWSM manuscript plan

This plan implements the requested private full archive and public research release.
It preserves earlier studies and freezes a new, explicitly bounded dataset. A
working paper is not a conference submission or an accepted paper.

1. **Verify scope and venue.** Inspect the current official ICWSM call, retain the
   source, reconcile the user's date with the actual deadline, and document the
   template, checklist, DOI and access requirements. Keep author and institutional
   determinations unresolved until supplied by the responsible humans.
2. **Freeze the source frame.** Verify retained text and media, preserve alternative
   editions, and separate publications, recordings, segments, uploader references
   and claimed identities. Same-publication whitespace duplicates do not create
   independent documents. Publish metadata and hashes; retain full bodies privately.
3. **Package the private archive.** Build a content-addressed, resumable inventory
   of research assets, including source evidence, media, full text, databases and
   provenance. Exclude credentials, installed dependencies and reproducible model
   caches. Verify the destination is private before every upload. Use bounded RAM
   staging and GitHub release assets rather than oversized Git blobs. Verify remote
   asset bytes before claiming completion. Preserve local originals.
4. **Execute analysis.** Refit TF-IDF, topics, clusters and context networks on the
   frozen frame. Add source-origin, document-length, date-coverage, context-balance
   and semantic-comparator checks. Produce per-context and per-publication profiles,
   figures and tabular exports. Mark question/answer candidates as unvalidated.
5. **Write the dataset paper.** Use the verified venue template and cite inspected
   related work. Describe the released dataset, collection boundaries, provenance,
   quality, actual experiments, limitations, ethical considerations and applications.
   Build a PDF and portable source package. Include the unaltered required checklist;
   identify unfinished submission requirements rather than filling them with guesses.
6. **Build the dashboard.** Show the same frozen counts, per-context details,
   source filters, exploratory comparisons, plots, downloads and paper. Uploaded
   channel totals remain unknown when no channel census succeeded. Explain private
   source retention separately from public metadata availability.
7. **Independently review and publish.** Recompute consequential counts, inspect
   sensitive release boundaries, test interactive and failure states, verify all
   build artifacts and run the existing site gates. Push the public release and
   deploy Pages, then verify live hashes and links. Publish the private archive only
   after access is actually available. Record any remaining barrier explicitly.

## Parallel ownership and dependencies

| Lane | Owner | Output | Dependency |
| --- | --- | --- | --- |
| Venue and paper | dataset_venue | official requirements, LaTeX/PDF, citations | results for final claims |
| Data engineering | dataset_engineer | frozen frame, schemas, private DB, public metadata | retained source files |
| Archive | dataset_archive | exact closure, shards, private GitHub receipts | actual private repo access |
| Analysis | dataset_analysis | source-bound statistics, profiles, figures | frozen frame |
| Dashboard | dataset_dashboard | responsive explorer and browser checks | dataset/analysis contracts |
| Independent review | dataset_review | recomputation and milestone findings | each completed producer |
| Integration | root | release manifests, README, CI, deployment | reviewed outputs |

The lanes are AI-agent roles, not independent human experts. Review milestones
are recorded only after execution. Computation uses the available four-CPU quota;
bounded workers and one-thread numeric libraries prevent oversubscription.

## Current scope boundaries

- Official dataset deadline: **15 January 2027, 23:59 AoE**, per the inspected
  [ICWSM 2027 call](https://www.icwsm.org/2027/submit/).
- Selected frame: **683 publications, 694 text editions, 1,599,556 selected words**.
- Frozen collection policy: no item-count cap; Bashar alone retains a 300-second
  minimum; other included mediums have no duration floor.
- A fresh ordinary YouTube probe on 8 November 2026 at 22:53 UTC still failed at
  HTTPS CONNECT with HTTP 403, no origin response and no body. The collector does
  not multiply this known transport failure across every indexed video.
- The full archive destination is `occult-kranti/channels-et-dataset`, private.
  Repository creation returned HTTP 403; the user said they will create it and
  grant access. Intent is not counted as a successful upload.
- DOI deposition, final human author details, rights determinations and applicable
  institutional review are submission readiness items, not fabricated metadata.

## 10 November continuation

The user requested the existing repository and an organized folder, superseding
the separate-repository dependency. Public research is organized under `dataset/`,
`research/dataset-submission/` and `dist/dataset-submission/`. The earlier private
raw-source preference remains in force; an access-controlled archive route in the
existing repository is being verified before any source upload. Public deployment
continues independently.

The user then explicitly authorized public storage, superseding the earlier
private-source preference. Public research is pushed immediately. Full-source
publication is governed by documented redistribution terms and successful remote
byte verification, with no blanket copyright grant inferred from academic use.
