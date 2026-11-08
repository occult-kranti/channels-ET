# Direct publisher audio and written messages

Completed acquisition retained **192 publisher audio files**: three original MP3s
and 189 verified Opus derivatives, totaling **942,245,703 bytes and
160,392.925125 seconds (44.55 hours)**. The pipeline verified 2,345,054,442 source
MP3 bytes before the larger originals were replaced by checked derivatives.
All 32 earlier resource holds were resolved by the measured continuation; no
current audio candidate remains deferred in this finite frame.

The associated written editions total **192 messages and 189,717 words**:
43 editions retained with the audio runs plus 149 in the separate text-recovery
supplement. Nine complete selected messages were read by AI agents; 183 were
automatically extracted. These represent one publisher/medium context, not 192
independent mediums. New YouTube downloads, new ASR editions and additions to
the frozen 493-source analytical frame are all **zero**.

The OmNa publisher offers an explicit **Download Audio MP3** link next to its
written message and an embedded YouTube reference. These are usable first-party
publication links. They are separate from YouTube channel enumeration and
YouTube downloads: no YouTube endpoint is requested by this collector.

The first inspected pilot retained the original 7,227,747-byte MP3, independently
verified its full decode (596.1143125 seconds), and retained a separate
673-word publisher-written message. The independent reviewer reread the complete
selected message and reproduced the audio hash, sample count and PCM hash. Two
additional manually inspected messages then ran with two workers: 20,435,530
audio bytes, 1,662.1191875 decoded seconds and 2,128 written words. These finite
acquisitions do not add documents to the frozen 493-source analytical frame.

The next completed and independently checked batch retained **40 Opus files**:
170,798,373 bytes, 29,022.0759375 decoded seconds and 36,665 automatically
extracted written words. The reviewer rehashed and fully decoded all retained
Opus files and reconstructed every selected text/page binding. Original MP3
hashes in this derivative batch are supported by executed acquisition/decode
receipts; the discarded originals could not be independently rehashed later.

The discovery frame subsequently admitted **149 further exact audio links** whose
written template initially differed. Their audio run records that original
`written_message_pending` observation. A separate, immutable publisher-text
recovery module can resolve text availability by exact record ID, page URL and
page hash. This preserves original acquisition observations without turning a
publisher-written edition into ASR or claiming audio/text equivalence. The final
release preserves those acquisition-time observations, and the later recovery
remains separately bound. The dashboard joins them only by exact record ID,
page URL and page hash.

For the remaining 149 files, the independent reviewer rehashed every retained
Opus file and checked its source/selection/download/decode bindings. A fixed
shortest, longest and sorted-middle sample received a second full PCM decode.
Thus the pipeline fully decoded all 192 files, while independent duplicate
decoding covered the first 43 plus those three later samples. This does not
establish speech-recognition accuracy, semantic equivalence or claim truth.

## Boundaries and provenance

Each candidate binds the retained publisher HTML by SHA-256, the exact audio
`href`, and selected Elementor block identifiers. The current inspected template
uses `a959f86` for the message, `8d74e16` for its closing, and `0143f75` for the
separate publisher attribution. Extraction retains inline punctuation and
paragraph breaks; whitespace-separated word counts can differ from a scraper
that inserts a space at every inline tag boundary.

Raw HTML, audio, written bodies and detailed request/decode receipts remain in
private storage. The public module contains identifiers, source URLs, hashes,
counts, stages and limitations. The written edition is labeled
**`written_message` / `publisher_written`**. It is neither ASR nor an audio-aligned
transcript. No new recognition model or semantic analysis is run in this lane.

The first three message bodies and six messages in the separate recovery study
were read by AI agents. The other template matches are explicitly labeled
**automatically extracted, not manually read**; human validation remains false.
Automatic selector checks establish
structural boundaries, not semantic accuracy or adequate interpretation.

Co-occurrence on a publisher page does not establish equivalence between its
audio, written edition and YouTube video. In particular, some different OmNa
pages reuse an embedded YouTube ID. Such references remain page-level evidence;
they must not merge recordings, establish uploader identity, or inflate a
YouTube download count. Exact old retained audio URLs are excluded from the new
candidate frame. Different URLs alone do not prove different acoustic content.
The 192 new audio sources have 192 distinct original-byte fingerprints and
192 distinct canonical 16 kHz mono PCM fingerprints, but their pages reference
only 190 distinct YouTube IDs. Exact fingerprint distinctions are not a semantic
near-duplicate analysis or evidence that the YouTube versions were retrieved.

## Acquisition and validation

`publisher_media.py` uses the ordinary configured network route with TLS
verification, a descriptive user agent and no redirected requests. It accepts
only the explicitly inspected OmNa S3 audio host, HTTPS `.mp3` paths without
credentials or signed query strings. It verifies the exact link against the
bound HTML before requesting media. There is no proxy relay, browser extension,
cookie export or YouTube-origin request.

Each response must be HTTP 200, nonempty, within a 64 MiB staging limit and equal
to its declared content length when supplied. A timeout applies to blocking
network operations; it is not a guaranteed whole-download wall deadline. The
original compressed bytes receive a SHA-256 hash. `ffprobe` must identify one
audio stream and no video stream. A full `ffmpeg` error-sensitive decode is
streamed to 16 kHz mono signed-16-bit PCM, counted and hashed without storing the
PCM. Error output, empty/odd sample bytes or a material container/decoded-duration
discrepancy prevent successful admission. Decoding establishes readable audio,
not listening verification, speech accuracy or truth of the source's claims.

For the larger resource-bounded batch, the original is decoded first and then
transcoded to Opus with a **48 kbps target, variable bitrate**. The Opus file is
also fully decoded and its duration compared with the source. Only after both
checks succeed is that candidate's newly staged original removed. Source-byte
hash, byte count, decode witness and request receipt remain. All older originals
remain untouched. Opus retention is lossy and its byte/PCM hashes are distinct;
the collector does not claim lossless preservation or unchanged recognition.

The finite eligible publisher frame runs with two workers and a 600 MiB retained
audio budget **per resource-bounded invocation**. Initial immutable runs use a
2 GiB free-space guard. Following a measured capacity review, a fresh continuation
may explicitly use `--minimum-free-gib 1.5`; the original runs and any earlier
resource deferrals remain unchanged. Each later run records its actual configured
guard, starting/ending free bytes and staging plan. These are operational
reserves, not a permanent archive-size or source-count cap.
Staging checks reserve up to two 64 MiB originals and metadata headroom. The
later extension additionally reserves a finite derivative-size estimate from
the decoded duration, accounts for it during concurrent download writes, and
monitors derivative size/free space while encoding. Exceeding that estimate
defers admission rather than allowing unbounded growth. After the invocation's
output budget is reached, further jobs
stay unacquired; at most one already running second worker can finish, and any
bounded overrun is reported. Failed, structurally mismatched and deferred pages
remain distinguishable from completed media. The current code fails closed on
an existing output edition directory instead of overwriting a prior run.

## Verification controls

Twelve synthetic controls passed: exact selected-text and inline-punctuation
behavior, changed page hash, missing audio href, missing/duplicate/overlapping
blocks, disallowed URL shapes without network access, empty/HTML/corrupt media,
an actual short synthetic PCM decode, actual Opus duration preservation, explicit
audio-only admission without inventing a written edition, and
sanitized failed-candidate publication with zero success counts. These small
fixtures are not real acquisitions and do not establish whole-archive coverage.
The additional controls verify an explicit resource-policy override and that a
completed continuation resolves an earlier hold while changed artifact bytes
still prevent publication.

Run the controls with:

```sh
python research/youtube-archive/test_publisher_media.py
```

The stdlib-only `verify_publisher_media.py` recomputes public record accounting,
audio-byte and duration totals, source-run joins, unique candidates, resolved
historical holds and zero YouTube/ASR claims. It does not access private media.
The valid final module and 12 artificial counter/provenance mutations passed
`test_publisher_media_verify.py`; the altered fixtures were all rejected.

The producer's private selection JSON is required for actual acquisition. Public
`publisher-media.json` and its explicit hash/size allowlist are the only collector
outputs admitted to the website. The dashboard must keep publisher files,
written editions, ASR editions, YouTube retention and analyzed sources separate.
