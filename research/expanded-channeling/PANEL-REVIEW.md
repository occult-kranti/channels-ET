# Expanded channeling study: AI panel review

Status: **core research accepted with stated limits; media expansion in progress**.
This record describes five AI work roles, not a panel
of human subject experts, human annotation, or external validation. Review
rounds are recorded only for work actually inspected. The source frame is a
purposive expansion from the screened subscriptions and named search leads,
not a census of YouTube or religious traditions.

## Round 1 — requirements and concrete risk review (8 November 2026)

The independent critic read the UAP research skill, its provenance codebook
and review gates, the existing compact publisher-audio contract, and the
existing RSS resource plan. The critic independently verified that the
accepted legacy audio core still hashes to
`7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64`.
The following objections were delivered directly to the four other panel
roles before their new outputs were finalized.

| Owner | Objection / required correction | Round 1 disposition |
| --- | --- | --- |
| ET sources | A shared civilization/name is not a verified entity identity, independent origin, or additional physical observation. Reposter accounts must not count as independent mediums. Royukh/Ryokah spelling and historical Ra versus modern Ra claims require explicit provenance. | Accepted for implementation; actual register audit pending. |
| Traditions sources | Hosts, directory members and demonstrated channelers are different roles. Kristin Davies versus Kristin Davis and an Erik connection need direct evidence. Contemporary channeling claims do not represent endorsement by a religion; Jesus/Jeshua/Christ-consciousness and deity/aspect labels cannot be silently merged. | Researcher accepted: no Kristin–Erik edge; dated episode evidence required for Erik mediums, distinct Magdalen/aspect labels planned. Actual sources/register audit pending. |
| Methods | Existing accepted analyses must retain their original denominators. New joint fits must expose document length, format, publisher, duplicates and missingness. Biographies cannot assign a mixed-speaker transcript to a claimed being. Q/A cues and cosine retrieval are candidates, not verified answers or doctrinal agreement. | Accepted requirements; executed output audit pending. |
| Dashboard | Every view must distinguish discovered publications, retained media, transcript editions and analyzed units. Unknown upload totals must remain unknown. Typed claim edges, source access depth, empty states, keyboard operation and mobile source inspection are required. | Delivered; working page and browser checks pending. |

### Acquisition review

The old planning receipt has 224 RSS entries but only 223 eligible entries
because it applied a five-minute threshold to all publishers. The user's new
rule includes the 299-second non-Bashar episode. That changes the executable
frame to **224 entries**; the former frozen study remains a historical
snapshot. No claim of new RSS acquisition follows from this count.

The contract proposes one download/transcode worker, up to two ASR workers,
a 2 GiB free-space floor, 448 MiB scratch/provenance reserve and a 1.62 GB
retained-audio cap. At the critic's initial check, available disk was
4,255,776,768 bytes, only 18,531,072 bytes above the proposed start requirement
of 4,237,245,696 bytes. These are observed planning quantities, not guarantees
of completion. Source sizes and durations are publisher declarations until
measured. Concurrent writes, incomplete attempts, headers, decoded PCM and
provenance files must be covered by enforced bounds. A capped decoder must
fail on reaching the cap, never label a truncated decode complete.

**Initial collector gate: passed after correction.** The critic inspected the
new collector and requested repeated-field source/sample validation, a
single-run lock and immutable executed-code binding. These corrections were
implemented. Eight collector tests passed independently, together with two
additional real-FFmpeg adverse checks: a compact-output byte cap rejects and
preserves its partial, and a full-decode duration cap fails closed.
Accepted legacy code and previously retained media must remain
unchanged. A full-duration lossy Opus derivative must retain original-source
hash/size provenance and its own decoded duration proof; it is not an original
publisher encoding. Exact caption-to-GUID/enclosure linkage can suppress
redundant ASR but does not validate caption accuracy.

## Round 2 — actual artifacts (in progress)

The critic independently checked six saved publisher pages against their
acquisition hashes and inspected the decisive normalized-text locations:
Kristin Davies' About page; Jeshua's identity page; Tom Kenyon's Magdalen
introduction; the 2015 Kim Babcock introduction; and two March 2024 Channeling
Erik episode descriptions. The private review receipt records raw-page and
normalized-text hashes and inspected locations. This is a targeted source
audit, not a full-corpus review or audio/video inspection.

These checks support the following corrections:

- Kristin Davies' About page supports generic angel-mediumship claims, not
  an Erik attribution. No Kristin–Erik edge should be admitted from it.
- The Jeshua publisher narrative distinguishes Jeshua, Jesus and Christ
  consciousness. Its normalized page also contains reader comments; those
  comments must be excluded from publisher assertions and any publisher-only
  text analysis.
- Kenyon's introduction explicitly distinguishes his claimed Magdalen aspect
  and spelling from other channels. It also restricts redistribution; the
  public artifact should contain source metadata and bounded paraphrase.
- Kim Babcock's introduction is a **2015 test-session announcement**. The
  Jennifer Doran and Courtney Dillon records are **2024 episode metadata**,
  distinguish Elisa Medhus as host from medium/interpreter roles, and do not
  expose the spoken episode content. Directory membership and series roles
  must not become an invented statement that the reviewer heard a session.

The traditions researcher accepted these distinctions, including a separate
`listed_series_medium` relation where only series metadata supports the role.

### ET attribution corrections

Six additional publisher pages were independently checked against saved
hashes: Elan Interactions' About page, Wendy Kennedy's biography, Tyler
Ellison's homepage, Shaun Swanson's About page, Wieteke Koolhof's homepage and
Sam the Illusionist's archive homepage. The critic found a specific drift:
the Elan publisher says **Bashar** trained Andrew for two years and claims
Darryl confirmed this. It does not establish a direct human Andrew–Darryl
teacher relationship. The register was corrected accordingly. The Sassani
comparison was also narrowed to Elan and RYOKAH, whose affiliations had
explicit support in this source frame; Bashar was not assumed into it.

Structural checks found unique IDs and resolved source references in both
registers. Further corrections requested and accepted include a common
Daniel Scranton role label, explicit shared-name versus source-specific
record scope, and source-list deduplication. Series-directory membership,
category labels, contactee claims and secondary repost attributions must
remain distinct from explicit channeling attributions.

### Joint text study

The critic independently instantiated the documented TF-IDF estimators and
recomputed **98 full-text/window matrix cells and pair counts**, using the
hash-checked loader for **292 model units / 774,110 words**. All **411 eligible
question retrieval scores, runner-up margins, shared-content counts and
lead/abstention decisions** matched. The underlying item database contains
2,523 documentary Ra pairings, including four missing printed questions, and
2,629 unverified sentence/cue punctuation candidates. It contains no
identified non-Ra answers. These candidate units differ from earlier
cue-level counts and must not be presented as newly discovered true Q/A.

The methods role's first inspection found generic-fragment false matches.
The revised exploratory rule requires more content tokens, preserves rare
question vocabulary and requires shared content words. Its one surviving
lead was rejected after bounded reading: an interview fragment about the
present era versus earlier history was paired with a Ra question about an
ancient visitor's name. The critic read the retained 38-word interview
context and 43-word Ra question/answer and confirmed the mismatch.

A missing immutable binding for `qa-review.json` was repaired with a
documented postrun finalizer. The final JSON differs from the executed
run-04 JSON only by this binding; annotation content and all model results
are unchanged. The critic verified the copied review, question hashes,
finalizer hash and all 16 public asset hashes. Final analysis SHA-256:
`003e040638ac8945b2435bd221d731d332e278d2583dd1600006f316d0d0454c`.
NMF/KMeans were not independently refit by the critic; their descriptive
scope and artifact hashes were checked, without claiming independent
statistical validation.

### Actual acquisition pilot and remaining ASR gate

The new explicit publisher frame contains **224 RSS enclosures and five
OmNa page-linked recordings**, not a YouTube upload census. The first OmNa
pilot was independently rehashed and fully decoded: **685.139625 seconds**,
4,164,092 retained Opus bytes, with provenance for 8,382,001 original bytes.
The retained PCM hash and sample count reproduced exactly, channels matched,
and cleanup removed only the new temporary original after verified receipt
creation. The removed original was not independently decoded again by the
critic. The frozen collector hash is
`2663bef91d36ecb2ce1b9e7ba13edcb958716c6faa000ec90f77450d98a59165`.
The bounded frame may proceed within dynamic resource guards; this review
does not promise that all 229 records fit or succeed.

The separate ASR successor was corrected to pin its collector validator,
validate normalized identities/counts/timestamps, distinguish empty
recognition and stop scheduling after an observed worker failure. Six tests
passed independently, including real decoder checks and explicitly mocked
recognition semantics. These tests are **not real inference or accuracy
evidence**. The initial one-worker ASR pilot was subsequently executed and
reviewed as described below. The accepted legacy audio core was not
edited.

### Actual dashboard review

The critic inspected the desktop shared-label matrix: Erik shows one direct
channeling attribution and eight linked medium records across all evidence
types; Kryon shows one direct attribution and two linked records. This
exposes weaker directory/category links rather than counting them as
verified named-speaker sessions. The inspected Q/A card correctly marks its
pair as reviewed and non-equivalent. Mobile navigation, keyboard opening of
a graph node, Escape and focus return worked without browser errors or
whole-page horizontal overflow.

A visual check found that shrinking the entire network made mobile node
labels and targets too small. The designer corrected this with a
readable graph/list presentation. Two additional wording corrections were
requested: a rejected retrieval record must not be presented as an accepted
Q/A lead; a document's largest NMF factor is not validated topic support.
The mobile correction was retested: the graph keeps a readable 760-pixel
canvas inside a 352-pixel local scroll region, with no whole-page overflow,
and offers a full-size table alternative. The 20-message pilot and its
explicit analyst-composed comparison questions were inspected in the actual
mobile page without runtime errors. The traditions role additionally ran
nine targeted Chromium checks, all passing: label distinctions, Erik's
one-direct/eight-linked counts, an inspectable host-only Elisa profile,
source content kinds and attribution locations/paraphrases. The designer's
complete browser receipts were independently inspected: **199 network checks,
15 screenshots and 15 CSV exports**, plus **967 subscription checks,
12 screenshots and 12 CSV exports**. All assertions pass, no runtime errors
were recorded, and before/after source hashes match the inspected files.
These are executed interface checks, not evidence that source claims are true.

### New named-message pilot and cross-register grouping

The critic verified **20 unique text hashes / 20,829 words**, independently
recomputed 800 full-text and 300-token-window matrix cells and all 190 pair
classifications/scores. The 12 same-label cross-medium pairs include broad
Pleiadian/Arcturian labels as well as the two specific Mary/Magdalene label
pairs; these are not all comparisons of the same claimed personality.
There are 49 different-label within-medium pairs. Pair values are dependent,
and no inferential significance is claimed.

The critic read both complete Mother Mary message bodies (2,216 words) and
confirmed the published comparison: one emphasizes inward trust/love;
the other emphasizes inner-child care, boundaries and, where appropriate,
leaving a draining situation. These are differing emphases in selected
messages, not answers to one observed audience question or a demonstrated
logical contradiction.

The traditions role identified surviving council-title signatures in the
partial name-token mask. A separate exact-title masking sensitivity was
executed without replacing the original models; the critic independently
recomputed its 400 matrix cells, removal counts and grouped means. Shared-label
cross-medium mean cosine changes from 0.03636 to 0.03648; different-label
within-medium mean changes from 0.06588 to 0.06538. Publisher style, dates,
genre, translation and selection remain plausible explanations. The final
pilot SHA-256 is
`2fd5c74456ffe522f382d3ba800c128c8d8316abd2b8fd42e719877d0cc2d8b6`.

An actual cross-register mismatch was also corrected: Natalie's Pleiadian
and Arcturian claimed-name records were included in pilot-text coverage but
initially omitted from the corresponding network groups. Explicit researcher
group declarations now include those IDs and their claim edges without
merging identities. All **69 edges / 19 comparison groups** were checked;
Pleiadian labels have 11 direct-attribution human records but 10 declared
practices because Pia/Cullen are one joint practice. Arcturian labels have
two direct-attribution records. Declared practices do not establish
independent origins. The critic initially misread an aggregate Andromedan
pilot count as Daniel's text; the source-level correction identifies Natalie
as that message's medium and preserves Daniel's weaker category-only edge.

The joint study's final-02 edition changes only three similarity-figure files
and adds a visual-revision binding to fix a colorbar overlap. All numerical
and annotation fields remain identical to the independently checked edition.
Final joint-study SHA-256:
`34ac7bbeb61d83f8d782392008c39e252a335381b8b481c88258c1130e7a6722`.

### Inventory correction and publication boundary

The critic rehashed all 23 Magenta publisher archive pages and independently
parsed the video links. This found one omitted explicit YouTube Shorts URL,
which matters under the new non-Bashar duration policy. Replaying the saved
HTML with a repaired parser yields **1,114 unique linked IDs**. This remains
publisher metadata: upload ownership, current availability and the total
YouTube upload count are not verified, and this crawl downloaded no YouTube
media. The earlier 1,113-ID edition is preserved privately.

The actual first ASR pilot completed locally: 852 recognized words and 71
segments from 685.139625 seconds of audio. The critic verified code bindings,
output hashes, identities/counts/timestamps, agreement with acquisition PCM
proof and cleanup of only the new temporary PCM. This validates processing
provenance, not recognition accuracy, diarization or speaker identity.
A later recording correctly halted on a terminal timestamp overrun; its raw
diagnostic and failed attempt remain separate pending a reviewed recovery
edition. Parallel RAM-staged collection is a separate implementation gate.

**Core publication decision:** the source registers, accepted joint and pilot
analyses, typed network, plots and corrected interface may be published with
the declared limitations and a hash-bound acquisition snapshot. Ongoing
media/ASR work must be labeled by its actual status and timestamp; neither
this review nor a static dashboard release implies that every channel,
recording, transcript, religion or future arrival has been collected or
analyzed. Acquisition/recovery gates remain independent of this core decision.
