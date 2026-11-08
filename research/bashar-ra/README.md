# Bashar and the Ra Contact — acquisition and comparative analysis

This is a new, exploratory study, begun on 7 November 2026. It preserves the earlier Bashar index, papers, source archives and Crimson Circle collection. The user's current request is a complete inventory and acquisition of available Ra recordings and transcripts, acquisition of Bashar audio/transcripts, and a substantive topic, cluster and contextual comparison. Source-level acquisition coverage is reported against a finite inventory; "all" is not treated as an observed census of the entire web.

## Source frame and current distinctions

- **Ra:** the 106 numbered Ra Contact sessions, dated 1981–1984. The accessible lawofone.info publication is an authorized republication maintained by Tobey Wheelock; its default Lightly Edited text is an explicitly named edition. Original, Relistened, Lightly Edited and the 2018 Ra Contact editions must not be pooled as independent sessions. Published original-audio segments, continuous tapes, later narrated audiobooks and videos are different formats. Missing or overwritten historical recordings are documented separately from the availability of written text.
- **Bashar:** retained publisher recordings, newly accessible public first-party material and a source inventory of unavailable or paid sessions. The 19 retained audio-ASR records contain 17 interviews, one promotional interview and one skeptical commentary. They are Bashar-related contexts, **not 19 verified channeling sessions**. Source labels do not establish which speaker supplied each utterance or that a podcast is the same edition as a YouTube upload. Official written messages, principles and PDF handouts form a separate authored-reference stratum.
- **Acquisition state:** source catalogs, actual downloaded media, machine transcripts, publisher-edited transcripts and locally extracted/OCR text have separate counts. Nothing is counted as a retrieved recording merely because its URL or transcript exists. Previous YouTube CONNECT failures do not establish the status of independently hosted publisher material.

## Research questions and units

1. What audio, video and text are actually retained, and which canonical sessions, editions or recording families do they cover?
2. Which lexical themes appear within each source stratum, and how do they change under ritual/name/filler removal, equalized sampling and alternative topic or cluster settings?
3. How much do clusters and apparent similarities reflect corpus imbalance, source format, transcription, speaker mixture or promotional language?
4. Which printed Ra questions and unverified Bashar question candidates can be retrieved as related reading leads? Do inspected answers support a substantive similarity, a distinction or an unresolved comparison?
5. How do the inspected sources frame agency, ethics, ontology, fear, practice, time, contact, healing and uncertainty? Semantic resemblance is not agreement, independent corroboration, or evidence of a claimed entity's identity.

The primary computational unit is a canonical session or distinct recording family. Question/answer turns, chunks, editions, reposts and audio segments do not create independent mediums. The source populations and time periods are strongly confounded. Results are exploratory descriptions of these retained materials, with model-assisted reading explicitly distinguished from human validation.

## Planned outputs and verification

The workstreams provide acquisition manifests and reusable collectors, complete-coverage text analyses, robust topic/cluster diagnostics, lexical and neural similarity sensitivities, source-linked reading notes, a static comparison dashboard, a living report and an organized private media/text index. Status changes to completed only after the corresponding artifact exists and its validation succeeds. No new public release of copyrighted full text or raw media is implied; public output uses source metadata, computed aggregates and labeled paraphrases.

Raw sources live under `/workspace/channels-et-private/bashar-ra-2026-11/`; already-retained Bashar recordings are referenced by hash and reused in place. Old source receipts and archives are not rewritten. The managed workspace is not permanent account storage. The new acquisition path reserves 3 GiB plus 256 MiB of working space; legacy 6 GiB defaults remain unchanged. Ra originals total 6,620,288,811 bytes. New retention uses full-length 48 kbps CBR Opus copies with independently validated source/output hashes, channel counts and decoded durations; these are lossy derivatives. The original MP3 pilot is preserved. New Bashar acquisition selects available publisher audio encodings and removes only newly generated temporary PCM after successful transcription verification. The exact cleanup and conversion policies are in the storage plan.

## Acquisition scope after the cap change

The user explicitly removed the earlier 100-recording Bashar limit for this study. Historical capped selection manifests remain unchanged. The current official public Vimeo profile inventory contains 307 IDs, of which 87 are at least five minutes long; all 87 expose public audio formats. The earlier exclusion of short clips remains. This is an observed publisher frame, not a claim to every Bashar upload or a complete paid-session archive. Excerpts, translated material, greetings, promotions and product introductions are labeled separately. Direct platform captions and locally generated ASR remain separate transcript editions; their counts must not be summed as unique recordings.

The Ra frame comprises 106 complete published Lightly Edited texts and 2,620 explicitly linked original-recording MP3 segments. Ten printed QIDs have no published audio link. Edited text can reconstruct gaps in surviving recordings, so coverage of the selected text and linked audio frame cannot establish a complete historical tape archive. Synthetic narrated audiobooks are excluded from original-recording counts.

The standalone comparison is [under `dist/bashar-ra/`](../../dist/bashar-ra/). A receipt-based collection snapshot is distinct from the frozen primary model input. New official Bashar speech receives a separate follow-on analysis. Source text, full Q&A, model files and media are private; the public page contains derived measurements, source metadata and bounded paraphrases.

## Local navigation and release

The completed receipt-backed frame now contains all 2,620 published Ra audio links (414,322.668 decoded seconds; 2,518,498,970 Opus bytes) and 106 selected edited session texts. One original MP3 pilot is retained in addition to its compact derivative. All 87 Bashar duration candidates were resolved: 86 qualify; one advertised as 300 seconds decodes below the threshold and remains held. One incomplete HLS encoding was detected, preserved as superseded and repaired; the accepted current manifests live in `official-vimeo-corpus-reviewed/`. Whole-frame packet continuity and independent source checks precede the final official-speech analysis.

The baseline remains 106 Ra texts plus 19 Bashar-related contexts. The official follow-on fits 82 English exact-media units after duplicate and language handling, with 67,536 words. Its clusters are weak and unstable; see [the follow-on methods/results](OFFICIAL-STUDY.md). The [living paper](paper/README.md) is a 28-page AI-assisted research draft with human validation explicitly pending.

`private_index.py` builds a searchable private HTML navigator and CSV from explicit acquisition manifests, without copying media. Its index may contain several transcript editions or many segments from one session. `publish.py` copies the independently reviewed numerical release and verifies figure hashes; it creates a separate collection snapshot from acquisition receipts. No browser page reads the private archive or claims it is permanent storage.

Run the static dashboard through a local HTTP server and use `dashboard_check.mjs` for real-browser validation. See [DASHBOARD.md](DASHBOARD.md) for the source-filter, network, export and accessibility checks. Publication must follow the final numerical and source review; a browser pass on an earlier analysis file is not a scientific validation of a later one.

See [METHODS.md](METHODS.md), [RA-SOURCES.md](RA-SOURCES.md), [BASHAR-SOURCES.md](BASHAR-SOURCES.md), [READING.md](READING.md), [REFERENCES.md](REFERENCES.md), and [STORAGE-PLAN.md](STORAGE-PLAN.md) as those workstreams complete. Pending source restrictions and absent recordings remain visible rather than being replaced with invented data.
