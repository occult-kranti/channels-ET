# Claude ZIP: round 1 audit

The supplied README explicitly labels this draft unreviewed. The normalized files preserve that status.

- 466 video rows; 457 valid distinct IDs; 9 unlinked leads.
- 449 primary-eligible supplied durations across 16 accounts. One extra schema-derived Athina duration is excluded.
- 453 relative publication-age labels; 3 exact dates, only 1 with a video ID.
- 92 directory entries, 53 channel routes, 16 reported recent-upload samples.
- 443 candidate new video IDs beyond the existing atlas, 14 overlap.
- Zero full transcript files; source notes are not a speech corpus.

## Corrections required

**Z01 (high)** Supplied draft is unreviewed; provider-read statuses cannot be promoted to fresh source verification. Retain supplied-summary access and reported acquisition method.

**Z02 (high)** 92 channel-directory entries contain only 53 actual channel URLs; 31 no_youtube and 6 of 7 not_found cases reflect exhausted credits rather than completed absence searches. Show unresolved/no acquisition, never absence or zero videos.

**Z03 (high)** Nine video rows lack IDs and URLs. Keep research leads separate from linked-video totals; do not deduplicate all blank IDs into a supposed video.

**Z04 (high)** Athina 53:26 is explicitly copied from schema example/notes. Exclude from primary duration estimates until independently checked; preserve as supplied value.

**Z05 (high)** Samples are capped at 30 recent uploads and mix clips, full sessions, promotion, teaching and non-ET context. Label means as sampled-upload means; show n, coverage and median; do not infer all-channel mean, publishing rate or total spoken-topic prevalence.

**Z06 (high)** Relative age labels are heavily coarsened, with only three exact dates (two belong to unlinked videos). Keep date precision; use ranges or relative-age buckets and avoid precise upload-frequency inference.

**Z07 (medium)** Entity field sometimes reflects channel framing or content described by notes rather than literal title occurrence. Call these reported entity labels; separate title lexical counts from entity attribution.

**Z08 (medium)** No full transcript files are included; notes contain excerpts/paraphrases and links to third-party transcripts. Do not run those notes as a spoken transcript corpus or treat metadata topics as semantic speech results.

**Z09 (medium)** Audience figure is a supplied snapshot; Aluna row refers to a 1-video 1.58K backup account, not the 84.2K main account described in notes. Label actual account title/handle and mark unverified counters; no combined person audience.

**Z10 (medium)** Timeline contains mixed precision, scheduled future events, claimed predictions and lightly deduplicated historical events. Keep draft chronology separately until event type, dates and source claims are reviewed.

**Z11 (medium)** Original entity plot ranks counts across unequal samples and labels every row as latest uploads, though the source rollup also includes notes-only examples. Recompute plot from explicit eligibility rules; show numerator and denominator and distinguish context entities.

## Analysis contract

Use channel-level available-case means and medians with n. Preserve nulls for unobserved channels. Treat durations as supplied metadata until checked. Model title topics separately from transcripts. Do not infer total posting rates from a right-censored 30-upload convenience sample or coarsened relative timestamps.

## Next discriminating records

Retrieve independent duration metadata for Athina and a stratified sample of the 16 accounts; acquire source-permitted transcripts with video linkage and language information; inspect account routes before merging person identities.

## Skill application

Investigative-evidence-research and trace-temporal-evidence-v1 were read with their required evidence/temporal contracts. Their provenance, unknown-value, date-precision and source-first review controls apply; financial/legal mechanisms do not.
