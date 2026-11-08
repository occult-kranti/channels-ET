# YouTube collection ledger: design contract

Design Partner's create, accessibility and verification workflow guides this additive operational page. Existing analytical workbenches stay intact. The primary job is to see which actual YouTube accounts have been enumerated, what the account-specific evidence supports, and which assets are actually retained.

The entry view is a searchable account census with account/medium/claimed-label filters, followed by account detail pages. Detail views expose observed video IDs, tab-pagination coverage, policy decisions, asset states and provenance. Collection activity distinguishes global gateway diagnostics from attempted video jobs. Storage and exports distinguish private managed-workspace retention, public metadata and any verified external destination.

Unknown platform totals are not zero, observed IDs are not a complete channel census, and publisher media is not a YouTube download. A global access failure cannot be copied into fake per-video failures. Availability requires direct evidence; untested IDs are not private, deleted or unavailable by inference. Bashar's five-minute rule applies separately from non-Bashar material, which has no duration floor or item cap.

Static UI modules and per-account ID lists must bind to the root manifest. No credentials, raw media or private file paths belong in public exports. Filtered CSV/JSON must preserve source, policy and denominator meanings. Initial skeletons contain no invented collection observations.

Final acceptance requires actual module arithmetic, account/ID filtering and exports, unknown/zero distinctions, error handling, hash-bound details, keyboard provenance dialogs and visual inspection at 320/390/1440 pixels. Browser evidence is kept outside the public site.

## Implemented distinctions and navigation

The census counts reconciled account references: resolved YouTube channel IDs and unresolved literal routes. They are not necessarily distinct people or authenticated channels. Historical watch-page uploader bindings are displayed separately from weaker route/publisher associations. Main filters cover account text, attributed medium, claimed label and inclusion status. Passing duration/exclusion screening is explicitly separate from relevance screening or verified channeling content.

The Video inventory view retains all observed IDs, including IDs with no account association. Its global/unassigned filter and account detail lists share the same metadata rows, searchable ID/title fields, pagination and provenance inspector. Account-filter exports union observed IDs and preserve overlapping memberships. Null uploaded totals remain null in JSON and blank in clearly named CSV fields; the rendered UI says Unknown.

Collection activity uses the actual collector's gate and stage ledger. Proxy CONNECT status, absent origin response and the checked time remain visible. Retained video, audio, caption and transcript sets differ from queued/completed ASR and analyzed IDs. The account stage counts are scoped to that collector ledger rather than retroactively joining unrelated publisher files.

First-party publisher-page discovery, inspected tool references and new independent publisher audio/written editions have separate activity panels. Publisher links do not verify uploader ownership, current availability or YouTube-content equivalence. New written editions are not ASR or aligned speech. Existing canonical research, new publisher editions and exact YouTube assets stay distinct in storage views.

The reconciliation table distinguishes selected units with verified media within each publisher context from distinct resolved media paths globally. Historical Ra audio segments, publication rows and encoded families retain their original names and denominators. No grand total adds incompatible units. Disk capacity is dated to the source reconciliation receipt; the static page does not imply live monitoring or permanent ChatGPT-account storage.

Supplementary publisher-text recovery is an independent source-bound module. The current availability summary unions original retained bodies with recovered written editions by exact record ID, page URL and page SHA-256, requiring body hash and word-count agreement on overlaps. Conflicting or incomplete bindings produce an unresolved count rather than an assumed total. This union includes text whose audio remains unretained. Original acquisition-stage pending-text observations stay visible alongside exact matching supplementary bodies; unmatched recoveries remain reachable in their own complete table. AI readings and automatic recoveries retain separate labels, and neither implies human validation, ASR or word alignment.

## Executed final verification

The seven actual published modules passed 28 browser check groups on 8 November 2026. Successful-data checks used no request interception. Two separate fault scenarios verified explicit handling of an unavailable required module and a same-size payload with a wrong SHA-256. The reusable runner is `research/youtube-archive/browser_check.mjs`; the final local run used `--faults yes --expect_final yes`.

The browser independently checked 297 account references, 2,812 inventory IDs, 2,181 account-associated IDs, 631 unassigned IDs and 878 historical uploader bindings. Every account detail route rendered. Filtered CSV and JSON, account pagination, exact ID search, provenance dialogs and Escape/focus restoration passed. Two schema defects found during review were corrected and regression-tested: account inspectors now use the actual historical identity-link fields, and attributed-medium arrays containing multiple names flatten into names rather than evidence prose.

The final UI preserves zero verified YouTube-edition downloads and the global pre-origin hold while separately exposing 192 retained publisher audios. Current written availability is exactly 192 editions and 189,717 words: 43 original retained bodies plus 149 supplementary recoveries, with zero overlapping identities and zero unresolved body/word conflicts. Original pending observations remain visible beside accepted recovery evidence. Retained lossy Opus derivatives are explicitly labeled; original publisher download links do not imply that original MP3 bytes remain stored. The 493-source analytical frame is unchanged.

Actual census, account, activity and storage screenshots were inspected, including the recovered-body overlay and current text union. Core views fit 320, 390 and 1,440 pixel viewports without page-level horizontal overflow; wide evidence tables scroll locally. No browser runtime errors occurred. The first local load was observed at 780 ms in this one run, not a network or device benchmark.

The test bound app SHA-256 `45dfbfcc1a09d1923af10bb4cf0260a98c9fc5b0e561f1a99818e26f3feb57e9`, index `ef1c5fa5f2e8f6eff26d30525ee09a2150408033c6a82c0bcefe779d67e575a1`, and stylesheet `b2a13ffd5eb93846c6e37c91ebcb2b4c6dcfd55040d523cf6965c20466d8b284`. The tested module manifest was `ba205b225a22e75037d6c147f17d3486133232734fe902f82bd580ab0b6656c2`; publication may refresh document/artifact bindings after this design note is copied without changing those tested UI bytes or scientific inputs. Browser receipts and screenshots are private verification artifacts.
