# ET channeling source register and incremental text pilot

The [source register](et-register.json) records **20 publicly named people or pseudonyms, 31 source-specific channellee labels, 32 attributed relationships, and nine comparison groups**. Its 61 source records include failed, rejected, historical and current sources; they are not 61 verified channeling sources. This is a bounded exploratory source map, not a census of YouTube, religions or extraterrestrial civilizations. Claims describe what publishers say. They do not authenticate an external speaker.

The source frame expands the user's accounts with publisher-linked candidates already documented in this repository and fresh ordinary public website inspection on 8 November 2026. The register separates a person, their channel account, a claimed named entity, a named collective and a civilization label. Search-indexed YouTube metadata is marked as metadata. No YouTube body requests or alternate proxy routes were used in this pass; the existing CONNECT restriction remains separate from individual publisher HTTP failures.

## Useful comparisons

| Comparison | Source-supported participants | What can be compared |
|---|---|---|
| Bashar | Darryl Anka; Andrew of Elan Interactions | Two explicit attributed mediums using the same name. Andrew's publisher says **Bashar** trained Andrew and Darryl confirmed this; it does not establish direct human mentorship or independent origins. |
| Sassani / Essassani vocabulary | Tyler Ellison → RYOKAH; Andrew → Elan; Daniel Scranton → Ashanti | Different named beings associated with this vocabulary. Preserve Elan's *planet Essassani* wording and the other publishers' *Sassani* wording. Bashar's specific civilization affiliation is not assumed from his popularity. |
| Pleiadian labels | Barbara Marciniak, Wendy Kennedy, Nora Herold, Daniel Scranton, Sam, Arkayla, Rob Gauthier, Lyssa Royal Holt, Pia Orleane and Cullen Baird Smith | Distinct named councils, individuals and unnamed collectives. Pia and Cullen are one declared joint practice. Aridif's publisher says “Ancient Pleiadian from Deneb”; the dataset preserves that claim without reconciling it astronomically. |
| Yahyel | Wieteke Koolhof → Arjun; Shaun Swanson → Ishuwa | Different named individuals associated with one civilization label. |
| Arcturian labels | Daniel Scranton; Wendy Kennedy; Sam | Unequal scopes: named council, “works with” affiliation, and archive-category association respectively. Only the first is a directly inspected named-council claim in this register. |
| Zeta labels | Daniel Scranton; Paul Hamden | Channeling attribution versus reported communications/contact. Syann's collaboration does not automatically create a second medium. William Treurniet's authorship is not a medium attribution. |
| Ra / RA | Carla Rueckert in historical L/L Research material; Sam's modern archive category | Distinct source traditions. Sam's corresponding session body was not read; this is not an assertion that modern material is historical Ra or the Egyptian deity. |
| Kryon | Lee Carroll; Sam's archive category | A named entity label, not a civilization. Sam remains category-only; David Brown and Sabine Sangitar are unresolved leads. |
| Andromedan labels | Alex Collier; Daniel Scranton's archive category | A contactee description versus a product-category association. Neither warrants a shared named speaker claim. |

Magenta Pixie's **White Winged Collective Consciousness of Nine** is explicitly registered. Phyllis Schlemmer's proposed Council of Nine comparison stays a lead: no inspected primary passage established the relationship, and the two labels are not merged. The user's **Royukh** spelling remains unresolved. RYOKAH and RYO appear in Tyler's official branding; Riok/Ryok occur in testimonials and indexed titles and remain search variants without an invented renaming chronology.

Account links are attached only at their inspected evidence depth. A reposter such as Divine Light Vibes is not a second medium. Jamie Butler remains excluded from acquisition at the user's request; the register does not label her a comedian. Kristin Davies/Erik and the religious/deity comparisons are addressed in the complementary traditions register.

## Keyword discovery and extraction

The JSON includes the exact executed query strings, URLs, dates, response status and hashes. Queries combined `channeling` with Sassani/Ryokah/Royukh, Pleiadians, Arcturians, Yahyel, Zeta, Andromedan, Ra, Kryon and Nine. First-page organic results were used for discovery and spelling checks. Five Brave queries returned 429 and were not retried; four Bing results were unrelated and discarded. Search-engine summaries and ranked result totals did not become evidence or upload denominators. A peer-reviewed-literature query was unproductive; no literature review is claimed from it.

Keyword-based extraction was also tested against Daniel Scranton's public WordPress API. This exposed an important failure mode: a search for *Pleiadian* returned Arcturian messages that mention Pleiadians or contain promotional Pleiadian links. The message title, opening and closing attribution controlled the label. Navigation, donation requests, advertisements and course promotions were excluded from the fitted body. The query term alone never assigned a speaker.

## New privately retained text

Eight newly collected publisher texts contain **6,578 primary-analysis words**:

- Three Pleiadian High Council of Seven messages attributed to Daniel Scranton, published 7–9 April 2016: 1,683 words.
- Three 9D Arcturian Council messages attributed to Daniel Scranton, published 22 and 25 October and 8 November 2026: 1,856 words.
- One Ashanti/Sassani message attributed to Daniel Scranton, published 9 June 2026: 368 words.
- One *Preparedness* excerpt (#138), headed “Sasha through Lyssa Royal,” dated 23 July 1993: 2,671 response-only words.

The complete five-page Lyssa excerpt has 2,742 normalized words. It is retained separately from the response-only derivative and five printed question/answer pairs. Question paragraphs are explicitly marked in the document. Attribution of subsequent response paragraphs follows the printed layout, not an acoustic identity test. The body explicitly describes Sasha's own Pleiadian community; only after reading that passage was Sasha added to the Pleiadian grouping.

All seven Daniel bodies were bounded by the publisher's opening and closing message paragraphs. Their exact WordPress post IDs and source URLs are retained. The private manifest binds raw sources, body spans, dates, hashes, word counts, attribution scope, language and extraction rules. Its SHA-256 is `d7f7d01e49fee1dafdcb5fba1515e54e03d42a0f573d9416ebbb268160792f37`.

Sam's exact sessions 256, 254 and 250 each returned HTTP 403. No transcripts were fabricated from their titles or homepage categories. The old and new publisher bodies are not a random sample; dates, genre, length and medium are strongly confounded. Cross-medium topic or lexical comparisons are descriptive pilots, and broad Pleiadian/Arcturian groupings do not equate the named collectives. Public deliverables contain source metadata and analysis, while full bodies remain private.

## Actual panel rounds and corrections

These were model-agent review exchanges, not human expert endorsements or peer review.

| Round | Observation | Implemented response |
|---|---|---|
| 1: source researcher, methods and skeptic guidance | Named beings, civilizations, accounts and joint practices were liable to be conflated. | Source-specific labels, explicit relationship types, account evidence, collaboration identifiers and uncertain leads were created. |
| 2: skeptic source inspection | The Andrew note implied Darryl personally trained Andrew. | Corrected to the publisher's claim that Bashar trained Andrew and Darryl confirmed it; direct human mentorship remains unestablished. |
| 2: skeptic schema inspection | A private absolute directory appeared in the draft; Bashar was included in a Sassani group without equivalent direct affiliation evidence. | Removed the private path and removed Bashar from that civilization grouping. The separately sourced repeated Bashar-name comparison remains. |
| 2: design integration | Shared people had incompatible role vocabulary. | Normalized confirmed channelers to `medium`, joint participants to `joint_practice_medium`; contactee and communicator roles remain distinct. |
| 2: methods body review | Keyword matches could mislabel an entire message; Lyssa's transcript mixed prompts with responses. | Labels now follow actual title/body attribution. Five exact question paragraphs were separated; mixed text, response-only text and Q/A records remain individually bound. |
| 2: added primary evidence | Sasha's civilization affiliation was only a lead. | Read the offered PDF and added the affiliation only after an explicit body passage; Ashanti's explicit Sassani message also expanded the group. |

Executed structural checks found unique IDs, valid claim/source joins and group membership references, and no `/workspace/` or `/tmp/` paths in the public JSON. Remaining uncertainties—Royukh spelling, category-only Sam labels, unresolved Nine connections, unavailable publisher bodies, limited sampling and source dependence—are preserved rather than converted into successful findings.
