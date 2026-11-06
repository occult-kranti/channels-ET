# Transcript comparison: publisher sensitivity

## What this experiment uses

This is a new descriptive regrouping of the existing [source table](../transcript-analysis/tables/sources.csv) and [audio cosine-pair table](../transcript-analysis/tables/audio-cosine-pairs.csv). It does not download, transcribe or analyze a new YouTube video. The source material comprises 20 publisher-audio ASR documents: 19 Bashar-context interviews or related items and one Athina Król/Ashtar-context episode. Source-context labels do not identify every speaker; hosts, guests and advertising were not separated. Prior processing and TF-IDF specifications are described in the [underlying analysis](../transcript-analysis/README.md).

## Results

| Pair group | Unique pairs | Mean lexical cosine | Median |
|---|---:|---:|---:|
| Bashar-context, same publisher | 6 | 0.495 | 0.517 |
| Bashar-context, different publishers | 165 | 0.393 | 0.394 |
| Ashtar-context recording paired with other recordings | 19 | 0.195 | 0.193 |

Six publishers each contribute one same-publisher pair. The same-publisher mean ranges from 0.480 to 0.519 when one pair at a time is removed. This sensitivity is a small descriptive check, not a confidence interval. The 190 unique pairs reuse only 20 recordings, so the pairwise observations are dependent.

The within-publisher mean is higher in this convenience sample, consistent with a possible contribution from common format, host, subject or repeated material. These factors are entangled; the result does not identify a causal publisher effect. The Ashtar-context group represents a **single recording**, so its lower mean cannot establish a difference between channelers, entities or communities. Similarity compares word use and does not establish agreement, truth or the identity of a claimed entity.

## Next experiment when new access is available

1. Use a preregistered time window and one eligible original recording per identified practitioner, noting channel ownership and selection uncertainty. Record excluded, blocked, unavailable, reuploaded, non-channeling and non-English items, rather than treating missing uploads as zero.
2. Retain hashes, original timestamps, ASR model/version, transcript provenance and segment times. Human-check a small stratified audio sample, including entity names and negations, before interpreting topic labels.
3. Distinguish practitioner speech from hosts, advertisements and introductory commentary. Test a matched-duration segment analysis and a within-versus-cross-publisher comparison with source-level or publisher-level resampling; do not treat pair edges as independent.
4. Report the inclusion denominator and coverage by language, duration and channel. Compare full-document and matched-length results; interpret topic models only with representative checked excerpts or manually reviewed labels and retained uncertainty.

## Reproduce

Run `python research/new-round/transcript_sensitivity.py`. It checks that all source pairs are unique and complete and writes [transcript-sensitivity.json](transcript-sensitivity.json), with source-file hashes and group statistics. The procedure uses only public derived tables and does not require source audio.
