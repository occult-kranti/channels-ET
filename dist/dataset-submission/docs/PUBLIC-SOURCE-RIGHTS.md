# Public source-rights audit · 10 November 2026

The public research release uses the existing `occult-kranti/channels-ET`
repository. This bounded audit checks the underlying Ra, OmNa and official Bashar
source terms after the request to make the archive public. It separates the
user's publication preference from permissions stated by source publishers.
It does not decide fair use or clear every publisher in the corpus.

**Finding:** no blanket license for public redistribution of the entire retained
third-party audio/text archive was established. Project-owned code, analysis,
figures, paper, metadata and source links remain publishable research outputs.
The audit records restrictions, attribution conditions and unresolved scope;
it does not conclude that every research use is prohibited.

| Source context | Evidence inspected | What it establishes | What remains unresolved |
| --- | --- | --- | --- |
| Ra / Law of One | Lawofone.info homepage; linked L/L copyright endpoint | The site identifies L/L Research as a rights holder and says Tobey Wheelock has permission to republish its material. | That site-specific permission is not an express downstream license to this project. L/L's main copyright policy returned HTTP 403 and was not available for review. Audio and derivative redistribution remain unresolved. |
| Natalie Glasson / OmNa | Current homepage/FAQ and exact retained pages for all 192 accepted audio/written-edition records | 60 pages carry a reproduction-attribution condition identifying Natalie Glasson and OmNa. | The inspected notice does not clearly state a site-wide grant covering every recording, ASR edition or lossy Opus derivative. The other 132 accepted pages do not contain that specific notice in the bounded scan. |
| Official Bashar | Official policy sections 18–19, Vimeo terms, sampled official video pages and a retained official handout | Personal/nontransferable/noncommercial display terms, copying/distribution restrictions, and an express recognition of qualifying noncommercial fair use. Sample video pages reserve rights. | No blanket permission for an academic mirror of all recordings/transcripts was established. The 19 guest-source recordings have separate publishers and are not cleared by Bashar's terms. |

## Ra: owner-specific permission is not a general license

The [Law of One homepage](https://www.lawofone.info/) says the site is maintained
by Tobey Wheelock with permission from L/L Research to republish copyrighted
material. Its footer identifies copyrights in the original books, the newer
Ra Contact books and the site. The linked
[L/L Research copyright policy](https://www.llresearch.org/copyright) returned
HTTP 403 in this run. Its main policy was not inspected, and its contents must
not be invented from a footer or a search snippet.

The source units remain distinct: 106 selected session texts and 2,620 separately
retained linked audio segments. A permission applying to a website or a printed
edition cannot automatically be assumed to cover those audio copies or their
re-encoded derivatives.

## OmNa: retain the attribution condition and its scope

Sixty accepted source pages contain this notice:

> This is a Channeled Message by Natalie Glasson at OmNa Sanctuary – https://omna.org
>
> The above must be included on any reproduction of this material

An [example source page](https://omna.org/is-archangel-michael-shattering-your-boundaries-by-archangel-michael/)
is bound to retained page SHA-256
`4499b6f56ca18b7ba990f208d030dd5efd15ff8a474a78a83c039c7966cb6bdc`.
The count is based on a SHA-256 join to the 192 accepted records. The scan saw
224 physical page copies, including retry/held-run duplicates; those copies were
not counted as additional licensed publications.

The notice anticipates reproduction and imposes attribution. Its exact coverage
for text, audio, transcript generation and audio derivatives remains unspecified
in the inspected sources. It should neither be discarded nor expanded into an
unrestricted license. A later release relying on it must preserve the required
attribution rather than export only a cleaned body whose notice was separated.
The 192-row `source-rights-omna-records.json` keeps the observed condition and
unresolved media scope separate for each source.

## Bashar: noncommercial use is not a blanket archive grant

The [official policy](https://www.bashar.org/privacypolicy), revised 3 July 2025,
limits the display license to personal, nontransferable, noncommercial use and
restricts copying, storage, publication and distribution. Section 19 expressly
recognizes qualifying noncommercial fair use. That exception is not a finding
that a particular complete-corpus republication qualifies.

The current policy bytes match the policy retained on 7 November 2026:
`6cb1330235e159ecaed6950b4547b4205ed50336f860762c8daaafd2659dbcc1`.
The [Vimeo terms](https://vimeo.com/legal/terms.md) distinguish enabled streaming,
download and embedding from broader copying, redistribution and archiving.
Two sampled official pages reserve rights; their download settings differ.
An available download therefore does not by itself establish a mirror license.

A retained official *Spectrum of Fear* handout also states:

> Please do not copy or disseminate any information contained within this event to the public.

This item-level notice is relevant even though a source download is available.
The inventory distinguishes 87 discovered official Vimeo records, including an
unavailable record, from 86 retained publications and 84 encoded-media families.
Neither discovery nor successful retention resolves redistribution rights.

## Evidence and release interpretation

`source-rights.json` records source URLs, retrieval times, statuses, hashes,
short clauses and the bounded conclusions. Full policy/page snapshots and
verification receipts remain in the local source-evidence archive. No rights
holder was contacted and no permission was inferred from an academic-purpose
label, a public URL, transcription, or audio conversion.

Source-specific permission, an applicable open license, or a documented
fair-use basis can support a later asset-level decision. Until such a basis is
recorded, the public package should expose the research metadata, derived
analysis and original source links without calling the entire third-party
corpus openly licensed. The repository's own license does not replace publisher
rights in source material.

The dataset and manuscript retain their 8 November scientific snapshot. This
10 November note updates the publication context without changing corpus units,
model results, source hashes or claims of completed acquisition.
