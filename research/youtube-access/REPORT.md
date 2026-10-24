# Collection and storage follow-up — 24 October 2026

The current collection plan applies the user's **five-minute minimum, no Shorts,
and at most 100 Bashar YouTube videos across all accounts combined**. Other
practitioners have no count cap. The plan, executable collection controls,
browser diagnostic and private-storage workflow are maintained in this
repository. The separate `bashar-index` checkout remains preserved.

## Observed results and planned work

| Layer | Observed state | Interpretation |
| --- | --- | --- |
| Indexed YouTube uploads | 942 distinct IDs | Inherited convenience frame; not a complete crawl |
| Eligible inherited lengths | 748 IDs | At least 300 seconds, without unresolved duration conflicts |
| Default selection | 733 IDs: 100 Bashar-associated and 633 other-labeled | Planned collection; fresh metadata is still required |
| Bashar source associations | 173 explicit IDs; 15 additional ambiguous contextual IDs held | Metadata association, not verified speaker identity |
| Bashar-relevant literal routes | 68, including six with zero indexed IDs | Routes overlap; zero indexed records does not mean empty channels |
| Complete lifetime channel totals | Unknown | No successful current live enumeration |
| Requested official Brave test | One watch navigation; one Envoy CONNECT 403 | No YouTube-origin page, media or caption response |
| New YouTube collection | Zero downloaded videos | The failed diagnostic is not 942 item attempts |
| Independently published audio | 20 retained recordings and 20 full-audio ASR passes | Separate publications; YouTube-edition equivalence unverified |
| Drive archive preparation | 99 existing artifacts, 1,703,635,307 bytes | Locally rehashed; no authenticated remote upload |
| Actual Drive state | Zero observed authorized remotes/tools, folders and uploads | Choosing an Apps option did not supply OAuth access |

The requested roughly 1,000 videos remain a collection target. This snapshot
contains 942 distinct IDs before screening; it does not justify reporting 1,000
downloads or a worldwide complete channel inventory.

## Selection methodology and the account denominator

The [policy exports](../collection-policy/README.md) retain every indexed ID,
source pointer, duration observation, account/route association and decision.
Classification uses exact entity labels, practitioner records named Darryl
Anka, **keyword extraction from titles and publisher/practitioner observations**
(`Bashar` or `Darryl Anka`), and explicitly branded route associations. Positive
decisions retain the matched field and source evidence. A mixed interview
account's other uploads are not labeled Bashar merely because one guest was
Bashar-associated. Context-only links remain ambiguous until evidence resolves
them. This is metadata analysis, not manual comprehension of all video speech.

| Metadata stratum | Indexed IDs | Eligible | Under 300 s | Unknown duration | Conflicting duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Explicit Bashar association | 173 | 115 | 22 | 26 | 10 |
| Ambiguous Bashar context | 15 | 0 | 0 | 15 | 0 |
| Other available labels | 754 | 633 | 101 | 20 | 0 |
| All uploads | **942** | **748** | **123** | **61** | **10** |

The one inherited Shorts URL overlaps the under-five-minute group; it is not an
additional disjoint exclusion. Invalid numerical values and booleans fail
closed. Exactly 300 seconds meets the minimum. Unresolved duration alternatives
remain visible, even when every alternative would exceed the threshold.

The default selects 100 of the 115 eligible Bashar IDs using deterministic
round-robin ordering among inherited publisher groups, explicit route-alias
components and unresolved IDs. The other 633 eligible uploads remain selected.
This balances available groups without claiming random sampling or independent
original sessions. A video's caption and audio assets share its upload-ID slot.
The 19 existing independent RSS recordings are a different source type and do
not subtract from the default 100-video limit. A separately labeled conservative
all-material scenario reserves those 19 and selects 81 new Bashar IDs instead.

Of the 173 explicit Bashar IDs, 162 have at least one route and 11 have none.
There are 247 route edges, with 70 IDs linked to multiple routes and 85 edges
beyond the unique routed count. There are also 52 inherited analytical publisher
groups; neither these groups nor the 68 routes are verified counts of unique
people or current platform accounts. Per-route totals cannot be summed as
unique videos. Reposts are retained as distinct upload IDs; original-session
identity, recording dates and deduplication remain unresolved. Historical upload
dates are kept separate from original performance dates.

## Brave and community-source diagnosis

The [actual Brave diagnostic](brave/README.md) used the official v1.98.60 Linux
package. Its 153,190,012 bytes and SHA-256 match official release metadata.
DevTools reported Chromium 156.0.8078.48. The browser's isolated profile trusts
the configured public environment CA, with TLS verification enabled. The
published dashboard loaded successfully over TLS 1.3 before the one source test.

At `2026-10-24T00:32:17.511Z`, an ordinary watch navigation failed with
`ERR_TUNNEL_CONNECTION_FAILED`. The target-bound network log recorded exactly
one `CONNECT www.youtube.com:443`, HTTP 403 and `server: envoy`. No origin
response was received. **The underlying cause remains unknown**; this evidence
does not distinguish an internal proxy fault from a policy refusal, and does
not establish a YouTube-origin refusal. The private runtime/profile/NetLog stay
outside Git; public receipts contain allowlisted diagnostic metadata.

The [source register and independent review](community-research/README.md)
check official yt-dlp, Brave, Chromium and HTTP guidance, public GitHub issue
reports, and official release metadata. Ten bounded documentation operations
include a corrected GitHub query after an initial syntax error. The single
Reddit request returned HTTP 403; the identified Substack feed failed CONNECT
403. Those failures are unavailable evidence, not negative search findings or
community consensus. No verified agent-side repair emerged for this environment.
Downloader dependencies, JavaScript extraction support and browser trust are
separate from establishing the rejected HTTPS tunnel.

The runtime already reports desired unrestricted policy, with enforcement
observed as unknown. Repeated unchanged requests do not resolve that uncertainty.
A supported platform/proxy repair or other meaningful access change should be
followed by one ordinary verified-TLS watch probe and a bounded metadata/caption
pilot. The [new collection runner](../collection-runner/README.md) must enforce
the current policy before any bulk acquisition. Global diagnostics and per-ID
job attempts are separate ledgers.

## Private archive and reproducibility

The [Drive workflow](../storage-drive/README.md) rehashes the existing 20 audio
files, 60 ASR output files and 19 primary-source files. Its 99 canonical artifacts
have no exact-byte aliases. Another 101 provenance/manifest files were staged
outside Git: **200 planned uploads**, not 200 completed uploads. Local SHA-256
preserves source provenance; remote size and MD5 would verify an actual transfer.
Original publications and YouTube editions are not merged by title or assumed
session identity.

No callable Drive connector or authorized rclone remote appeared after the user's
Apps selection. No Drive identity, quota, effective permissions, folder or upload
was verified. The user's five-terabyte allowance remains unverified. Once the
proper account is connected, the authorized private folder/upload can proceed
using the documented account selector; another permission request is unnecessary.
The prepared workflow creates a new My Drive archive without requesting sharing,
overwriting or deleting remote data. Failed uploads may leave partial objects;
automatic resume/merge/cleanup is not implemented.

Git/Pages retain code, metadata, evidence ledgers and bounded derived outputs.
Full recordings, primary publisher PDFs/text, complete automatic transcripts,
browser profiles and base-model weights remain outside public Git. Local media
capacity and the shared storage budget remain relevant until remote storage is
actually connected.

## Scientific interpretation and further work

This update improves collection selection, provenance, execution controls and
access diagnosis. Those engineering changes do not establish a new scientific
finding about channelers or their claims. The separately dated publisher cohort
contains source-available speech and text, with recognition, speaker attribution,
edition equivalence and session identity still requiring validation. Authored
text word counts remain distinct from ASR speech counts.

The existing manuscript, 949 AI-digest Q&A candidates and CPU Qwen/RAG/LoRA
experiments retain their reviewed scientific snapshot. New acquisition records
have not silently become validated multi-practitioner questions/answers or model
accuracy results. New cross-practitioner comparisons should resolve source and
speaker identity, distinguish host/guest/advertising turns, retain timestamped
evidence, define prompt equivalence, and use source-group held-out evaluation.
Human authorship, construct validation and institutional determination remain
TBD. Current collection and storage checks are AI-agent technical reviews,
separate from human peer review.

The [current dashboard builder](dashboard/build_dashboard.py) layers this
collection supplement onto the retained site. It publishes source-bound
selection counts and the 942 → 748 → 733 figure without source collection,
inference or manuscript recomputation. The pinned GitHub Pages Action validates
static routes and download hashes, then deploys the result.
