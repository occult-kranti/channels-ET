# Publisher text acquisition

All 91 explicitly linked files were acquired and extracted into private workspace storage: 71 Tracy Kumbera SRT caption tracks and 20 Magenta Pixie PDFs. The public [metadata manifest](second14-text-acquisition.json) contains source links, hashes, sizes, extraction counts and qualifications. No source text or PDF is redistributed here.

| Source stratum | Publication files | Extracted words | Scope |
|---|---:|---:|---|
| Tracy publisher-hosted captions | 71 | 147,004 | 15,623 timestamped cues; generation process unverified |
| Magenta English transcript PDFs | 15 | 60,706 | 237 pages; publisher-labeled transcripts |
| Magenta Portuguese transcript PDF | 1 | 3,233 | 7 pages; alternate language edition |
| Magenta other reference and ritual PDFs | 4 | 6,248 | 21 pages; includes one third-party republished article |
| Total | 91 | 217,191 | Publication-level total before exact-caption deduplication |

Two Tracy episode records contain identical caption bytes, leaving 70 unique caption files. Their audio and original-session identities remain unresolved. One of those records has an epoch-like 1970 feed date; its raw metadata is retained and the analytical publication date is unset. Caption timestamps were parsed completely, with no reversed ordering or overlaps, but this does not establish accuracy against the audio.

One 85-page Magenta transcript explicitly states that it originated from YouTube automated captions. It contributes 23,969 words and needs a separate source-removal sensitivity because it accounts for about 39.5% of the English transcript PDF words. A separate official-hosted PDF credits an article to Kat; its authorship is not silently reassigned to Magenta. The first 65 extracted words on each PDF's first page were inspected for language and provenance, totaling 1,300 words. This was a bounded model-assisted check, not complete semantic reading, image inspection or human review.

The original [publisher discovery inventory](second14-source-inventory.json) remains a historical link/count snapshot. This acquisition is outside the Bashar–Ra fitted baselines and will enter only a separately declared study. Byte retrieval and text extraction do not verify the teachings, purported communicators, health claims or predictions.
