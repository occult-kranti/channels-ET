# Channeling discourse dataset — public metadata release

Version: 2026-11-08. This downloadable package contains public metadata and provenance, not the full-text/media corpus. The frozen selected frame has 683 publication/body units, 694 edition-lineage rows and 1,599,556 selected words. There are 26 publisher contexts and 14 source-attributed creator contexts. The discovery inventory contains 2,812 observed YouTube IDs and 297 account references; no complete lifetime upload denominator was observed. Zero YouTube downloads are attributed to this inventory.

## Files

- dataset.json: self-contained summary, document metadata, publisher-context coverage, edition lineage, joined media metadata, caveats and input bindings.
- documents.jsonl: one selected publication/body record per line; full text is excluded.
- editions.jsonl: all 694 accepted edition records, including 11 unselected alternatives.
- media.jsonl: 533 physically retained encoded media linked to selected publications; source hashes and relationships, not file bytes. Ra segment archives are a separate collection denominator.
- youtube-accounts.jsonl, youtube-videos.jsonl, youtube-account-video-links.jsonl: all discovery observations and source-bound links; unresolved routes remain unresolved.
- channels.csv: publisher-context denominators, not a verified YouTube uploader census; blank lifetime totals mean unknown.
- schema.json: observation units, normalization, identity rules and public/private separation.
- DATASHEET.md and RIGHTS.md: collection, scope, limitations, sensitive-content considerations and rights.
- deposit-metadata.json: repository deposit draft; authors, author identifiers and DOI remain explicitly unresolved. It is not a completed DOI registration.
- checksums.txt: SHA-256 hashes for every other member.

## Integrity and use

Run `sha256sum -c checksums.txt` after extraction. Read JSONL line by line with any JSON parser; the bundle requires no downloader or local model. Full private source-bound texts and the searchable SQLite database are excluded. The selected frame SHA-256 is 3eb35b14a9067e9e162862ed030c15d5b7646a38b3060ac85686f4604eb2c9c4.

Do not interpret publisher context as speaker identity, a claimed entity as authenticated, written editions as verbatim speech, or topic similarity as identity/causal evidence. ASR word error rate is unmeasured. Unknown date/total fields are not zero. Two new OmNa editions were joined to existing articles only after exact individual-URL and whitespace-folded body equality; all alternatives remain preserved.

Source and build code: https://github.com/occult-kranti/channels-ET/tree/main/research/dataset-submission
Dashboard: https://occult-kranti.github.io/channels-ET/dist/dataset-submission/
