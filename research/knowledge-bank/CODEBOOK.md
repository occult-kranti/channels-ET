# Source, question and comparison codebook

The knowledge bank is a new annotation layer over 25 previously retained text
editions: 20 publisher-written pilot messages and five Council-study texts. There
are 47,280 whitespace words and six medium contexts. Exact NFKC-normalized body
hashes and declared publication families were checked; none of the 25 candidates
were excluded as duplicates. This is not 25 new downloads or a representative
sample of channeling traditions. The 228-recording completion fit remains separate.

## Identity and editions

Each record keeps its existing source ID, original text-artifact hash, normalized
body hash, publisher URL, edition type, date and attribution scope. Character
offsets refer to `Unicode NFKC(text).strip()`, use Python Unicode characters, and
have an exclusive end. ASR JSON hashes are distinct from normalized plain-body
hashes. When available, bound turn IDs and times are verified against the retained
recognition edition; that check does not establish spoken-word accuracy.

Medium IDs are normalized from the known printed person name. This explicitly
joins Daniel Scranton's existing pilot and Council-control metadata; Pamela
Aaralyn and Pamela Rose Kribbe remain separate people. Printed council/personality
labels are retained exactly. Broad Pleiadian/Arcturian groupings are comparison
categories, not evidence of the same speaker. Graph label nodes are local to the
medium and exact printed name. Neither repeated names nor graph edges authenticate
beings, organizations, religious figures or supernatural mechanisms.

## Questions and source reading

Eight questions are analyst-constructed after source reading. They organize
contact definitions, timing, mediation, practices, distress, change, agency and
council descriptions. They were not observed as shared audience questions across
mediums and are not a held-out retrieval test set.

Five additional questions are paraphrases of explicit printed question/response
pairs in a Lyssa Royal Holt / Sasha publisher excerpt. All five printed pairs
are retained; their question hash, source-artifact hash, paragraph indices and
response-body range are bound. The public database contains paraphrases, while
the private database retains the documentary wording. Publisher layout supports
this turn attribution; no audio diarization or entity identity is verified.

The 25 claim/answer cards retain conditions, temporal scope, qualifications and
exact evidence ranges. Close reading covered 15,795 unique body words across 14
source contexts: ten complete written bodies and selected passages in four ASRs.
Those reading counts are separate from the 47,280-word model frame. Five printed
questions add 65 question-field whitespace words outside the response-only model
body, excluding printed speaker markers. Earlier
reading work informs selection but does not inflate this round's inspected spans.

## Comparison relations

| Relation | Operational use | What it does not establish |
| --- | --- | --- |
| `shared_proposition` | The bound passages express a common, narrowly stated practical proposition. | Equal answers overall, a shared external speaker, or true claims. |
| `compatible` | The scoped propositions can coexist without a necessary conflict. | Identical meaning, logical entailment, or agreement on every implication. |
| `different_focus` | A broad topic overlaps, but definitions, practical suggestions or emphases differ. | A contradiction. |
| `conditional_tension` | A practical tension could arise under an explicitly stated extension or condition. | The source itself asserted both incompatible propositions under one case. |
| `explicit_contradiction` | Same proposition, referent, conditions and time are established, and the assertions cannot both hold under that scope. | An inferred score from embedding distance or an authenticated dispute between entities. |
| `unresolved` | Referents, conditions or evidence do not permit the requested equivalence/conflict assessment. | Zero similarity or universal ignorance. |

The selected eleven comparisons contain four compatible pairs, three differences
of focus, one narrow shared proposition, one conditional practical tension and
two unresolved comparisons. No explicit scoped contradiction was established.
That zero is a result for this purposeful set, not a claim that the full corpus
contains no contradictions. Pairs reuse sources and are not independent samples.

The Mother Mary comparison is carefully scoped: one message discusses distrust
of the Universe/Creator's support, while the other discusses draining interpersonal
situations. A conflict can be manufactured by silently changing the first referent.
The recorded tension is a possible practical extension, not a direct source
contradiction. Likewise, optional Andromedan invocation can coexist with Jeshua's
nonhierarchical account, and voluntary recentering can coexist with rejection of a
required universal formula. These qualifiers remain part of the cards.

## Retrieval, consolidation and cross-field hypotheses

Do not index the analyst question text as if it were answer evidence when testing
card retrieval. `card_search` indexes only answer paraphrases, conditions and
qualifications; `question_search` is a separate interface convenience. Root's
prospectively frozen retrieval-audit queries are distinct from these thirteen
questions and were not inspected by this card author before card freezing.
Source-informed AI relevance judgments remain an exploratory diagnostic, not
human ground truth or independent population accuracy.

Three graph nodes propose methodological connections: memory-style consolidation
and qualifier retention; natural-language inference and source-critical comparison;
and stylometry/source confounding in knowledge graphs. Their edges are explicitly
methodological examples or hypotheses. They are not empirical findings that brain
sleep, channeling, AI weight training or biological mechanisms are equivalent.

## Executed review corrections

Independent review required four changes, recorded in a fresh annotation edition:
an exact Lyssa skills paragraph was added to support a skills claim; Mary's trust
referent was narrowed to Universe/Creator; the Contact card retained its near-term
isolated-contact assertion; and the Pamela card retained specific election
expectations alongside their conditional status. A later locator check extended
one Pamela support to the complete final ASR turn, adding five inspected words;
the builder now rejects partial turn boundaries. The original annotation files are
preserved. Neither retrieval-query wording nor model rankings informed these
source corrections. Independent AI criticism is not human annotation reliability.

## Build and query

```bash
python3 research/knowledge-bank/knowledge_build.py \
  --frame /workspace/channels-et-private/knowledge-bank-2026-11/knowledge/frame-01.json \
  --annotations /workspace/channels-et-private/knowledge-bank-2026-11/knowledge/annotations-03.json \
  --output /workspace/channels-et-private/knowledge-bank-2026-11/knowledge/FRESH-RELEASE

python3 research/knowledge-bank/question_query.py \
  --database /path/to/questions.sqlite --query 'optional'
python3 research/knowledge-bank/question_query.py \
  --database /path/to/questions.sqlite --relation conditional_tension
```

The build validates all source hashes, support ranges, reading coverage, ASR turn
bindings and documentary joins, then checks SQLite integrity and foreign keys.
Only `knowledge.json`, `questions.sqlite` and `question-bank.md` appear in the
public allowlist. `knowledge-private.sqlite` contains the source bodies and exact
evidence text and must remain private. No prior corpus or accepted fit is changed.
