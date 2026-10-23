# Tool research and primary publishing sources

The [operating recommendations](RECOMMENDATIONS.md) cover current supported yt-dlp/EJS setup, captions, archive/resume semantics, fragment concurrency, failure diagnosis, resource planning and GitHub storage. The [18-source register](source-register.json) retains exact current official URLs, Git commits, retrieved hashes, reading depth and limitations. These are software/platform references, not peer-reviewed empirical findings. Raw documentation/feed snapshots stay in the ignored local `source-cache/`.

Decisive implementation points:

- Full YouTube extraction needs a compatible EJS package and JS runtime; Node must be selected explicitly. These requirements do not repair the recorded pre-TLS proxy CONNECT denial.
- A single manual+automatic subtitle command can shadow the automatic track in the same language. Preserve separate track types and ledgers.
- A media archive is not a caption/metadata success ledger; fragment concurrency is not video-worker concurrency. Check real artifacts rather than process exit alone.
- Keep shared raw-budget reservations/locking, `.part` files, hashes and ffprobe checks. Generic binary MIME still requires validated audio and available integrity checks.
- Git/Pages should carry source, manifests and bounded results. Large raw media stay outside Git; LFS does not serve Pages and does not supply redistribution rights.

[Primary source notes](PRIMARY-SOURCES.md) document the independent Apple-catalog → original publisher RSS → episode GUID → enclosure chain. The bounded implementation and results are in `../publisher_sources/`. Nineteen current publisher podcast responses were saved across thirteen shows, with four source-specific reviewed RSS-metadata warnings. Two indexed Apple-linked entries are excluded and one remains unmatched; no YouTube download is claimed. All recordings concern the original Darryl Anka-related index context, with skeptical commentary and promotional material explicitly separated from interviews.

Actual local speech recognition is a separate workstream under `../asr/`; it must remain bound to the saved audio hashes and inherit source/edition warnings. Its machine transcripts are not human transcript or speaker validation. This tool investigation does not rewrite or recertify the earlier paper rounds.
