# Dataset builder and counting contract

This package freezes the existing accepted corpus and the 192 new OmNa publisher-written editions into **683 selected publication/text units, 694 edition-lineage records and 1,599,556 selected whitespace-delimited words**. These are a convenience sample, not all uploads of a YouTube channel. The 26 publisher contexts and 14 creator contexts are not independent, speaker-verified people or entity identities.

## Build and validation

```sh
python3 research/dataset-submission/dataset/build_dataset.py
python3 research/dataset-submission/dataset/test_dataset.py
```

The builder requires the private accepted source artifacts. It reads and verifies their recorded text hashes, source-page hashes, byte lengths and selected word counts. It does not download, infer speakers, or rewrite the accepted source files. It writes the frozen private `frame.json`, source-bound `texts.jsonl`, searchable `corpus.sqlite`, `new-editions.jsonl`, media rows and a physical asset closure to `/workspace/channels-et-private/dataset-submission-2026-11/`. The `research/channel-lab/sources.py` function `load_frame` remains compatible and verifies every selected body on load. Media references are checked for physical presence and recorded size; complete media digest verification is a separate archive validation step and must be reported from that receipt.

The public `dist/dataset-submission/dataset.json` provides summary, publisher-context denominators, document metadata, edition lineage, media metadata, source bindings, limitations and download descriptors. Separate JSONL files preserve the 2,812 observed YouTube IDs, 297 account references and account/video links. `channels.csv` is a publisher-context table; it must not be labeled a verified YouTube-channel upload census. Unknown lifetime totals are JSON null / empty CSV fields. The public corpus contains no full bodies or private paths.

## Observation hierarchy

| Field | Meaning | Must not imply |
| --- | --- | --- |
| `source_id` | Stable canonical publication/body component | Independent person, recording or verified statement |
| `publication_id` | Existing source identifier or canonical individual URL hash | A unique YouTube upload |
| `selected_edition_id` | Selected textual rendition | Verbatim audio transcript |
| `recording_id` | Encoded file SHA-256 identity | Semantic recording equivalence across codecs |
| `channel_id` | Publisher context | Verified uploader account |
| `creator_id` | Source-attributed medium/context, sometimes mixed interview speakers | Diarized or authenticated speaker |
| `claimed_label` | Publisher/title-attributed claimed entity | Proven identity shared with another medium |
| `body_sha256` | NFKC-normalized text, outer whitespace stripped | Case/paragraph-insensitive semantic equivalence |

## Reconciliation

The old selected frame has 493 units and 502 cataloged editions. There are 192 new written editions, each with a verified private body. Two new OmNa article URLs match existing selected publications. Their respective 783- and 824-word bodies are exactly equal after whitespace collapse, while their strict normalized body hashes differ because paragraph spacing differs. The old selected edition is preserved; the new edition and newly retained audio are linked as alternatives/associated media. Thus 493 + 192 − 2 = 683 selected units, while 502 + 192 = 694 edition records. The two joins require both an individual OmNa article URL and whitespace-folded body equality. Site roots/container URLs do not qualify, and substantive same-article differences halt the build for edition review. Similarity and matching topic labels never merge medium or claimed-entity identities.

All 192 new audio files retain their original-source and current-encoding provenance, 16 kHz mono PCM fingerprint, duration and exact source-page relationship. This establishes cooccurrence on the page, not word alignment or YouTube media equivalence. The selected frame has 533 physically present joined media files. Ra's 2,620 linked audio segments are a separate legacy collection denominator and are not 2,620 extra canonical text documents. Legacy collection tables, account observations, excluded source references and archive files remain available separately.

## Quality and rights

Publisher-written bodies, edited published transcripts, linked captions, platform auto captions and local ASR remain separate origins. The new written editions are not counted as speech-to-text output. ASR word error rate is unmeasured because there is no independent human reference test set; publication/body admission is not accuracy validation. Three hundred selected documents lack an accepted publication date. No human validation or speaker authentication is inferred from AI inspection.

The metadata release does not grant permission to redistribute third-party media, transcripts, captions or books. Full source content is retained privately pending a documented source-specific redistribution basis. Any later licensed public subset must carry explicit license/permission evidence and include a reproducible inclusion query. Public availability of a source, a downloader's success, and a GitHub upload authorization are not a source license. Dataset curators' code and derived metadata must use their own explicit license separately from source content.

## Loader example

```python
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('sources', 'research/channel-lab/sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)
docs = sources.load_frame(Path('/workspace/channels-et-private/dataset-submission-2026-11/frame.json'))
# Each item is {'record': source_bound_metadata, 'text': verified_selected_body}.
```

Never create a completion percentage with observed IDs as a denominator for a lifetime upload count. Never add segment counts, publication counts and encoding counts. Topic similarity is descriptive and is not evidence that two claimed identities are the same, that an entity exists, or that paranormal claims are true.
