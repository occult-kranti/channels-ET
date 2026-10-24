#!/usr/bin/env python3
"""Export inspected counterexamples and a post-hoc lexical spelling diagnostic."""
from pathlib import Path
import json,re,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(path):return json.loads(Path(path).read_text())
def dump(name,value):(HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

docs=read(HERE/'documents.json')['documents'];windows=read(HERE/'reading-windows.json')['windows']
bywindow={w['windowId']:w for w in windows};segments={}
for d in docs:
    if d['modality']!='audio_asr':continue
    receipt=read(ROOT/d['sourceReceipt'])
    if'records'in receipt:receipt=next(r for r in receipt['records']if r['sourceId']==d['sourceId'])
    p=Path(receipt['transcriptDirectory'])/'segments.jsonl';assert hashlib.sha256(p.read_bytes()).hexdigest()==d['segmentsSha256']
    segments[d['sourceId']]=[json.loads(x)for x in p.read_text().splitlines()if x]

families=[]
for label,canonical,variants in [
    ('Essassani/Sassani lexical family',['essassani','sassani'],['esasani','sasani']),
    ('Ashtar lexical family',['ashtar'],['ashta','ashtalt','ashtara','ashtah'])]:
    counts={};hits=[]
    for term in canonical+variants:
        matches=[]
        for sid,segs in segments.items():
            for s in segs:
                n=len(re.findall(r'\b'+re.escape(term)+r'\b',s['text'],re.I))
                if n:
                    supports=[w['windowId']for w in windows if w['sourceId']==sid and s['id']in w.get('segmentIds',[])]
                    matches.append({'sourceId':sid,'segmentId':s['id'],'startSeconds':s['start'],'endSeconds':s['end'],
                                    'occurrences':n,'sourceSegmentsSha256':next(d['segmentsSha256']for d in docs if d['sourceId']==sid),
                                    'inspectedSupportWindowIds':supports})
        counts[term]={'occurrences':sum(m['occurrences']for m in matches),'documents':len({m['sourceId']for m in matches})}
        if term in variants:hits.extend({'variant':term,**m}for m in matches)
    variantdocs={h['sourceId']for h in hits}
    families.append({'candidateFamily':label,'canonicalTerms':canonical,'posthocCandidateVariants':variants,'exactTokenCounts':counts,
                     'variantDocumentCount':len(variantdocs),'variantOccurrenceCount':sum(h['occurrences']for h in hits),
                     'variantHits':hits,'allVariantHitSegmentsCoveredByInspectedWindows':all(h['inspectedSupportWindowIds']for h in hits),
                     'manualTextContextAssessment':'Contexts describe a claimed being, civilization, species, people or world. This makes the spellings plausible text-recognition candidates; it does not verify pronunciation, canonical identity or a speaker.',
                     'audioChecked':False,'humanValidatedAlias':False,'mergedIntoPredeclaredCounts':False})
dump('posthoc-entity-spelling-review.json',{'schemaVersion':1,'method':'Post-hoc exact case-insensitive token counts in the20source-hashedASRtexts, followed by AI reading of timestamped contexts; no audio inspection',
     'scope':'Audio-ASR only; metadata labels and authored publications excluded from these counts',
     'predeclaredStrictLexiconChanged':False,'families':families,
     'limits':['Candidate variants were selected after strict lexical zeros, so these are sensitivity diagnostics rather than a new primary estimate.',
               'All Ashtar-family hits are in a single creator recording; more occurrences do not create more independent sources.',
               'The Essassani-family candidate contexts include skeptical secondary reporting; a mention does not imply endorsement.',
               'Unlisted ASR variants may remain; zero exact tokens does not establish absence of the subject.']})

findings=[
 {'findingId':'stance_not_similarity','label':'Shared words can accompany explicit disagreement',
  'paraphrase':'The skeptical source restates belief/reality guidance while criticizing its repetition and ambiguity. A similarity edge to an interview therefore cannot be interpreted as agreement.',
  'supportWindowIds':['rss-425328515-addbc47ecbd7:query_rich'],'type':'AI interpretive counterexample'},
 {'findingId':'ads_not_entity_topics','label':'Advertising and publisher framing are present in sampled source bodies',
  'paraphrase':'Retail advertising occurs in the temporal middle of one interview; health-service and software promotions bracket two others, and a podcast advertisement interrupts a brief organizational-role answer. Untreated document topics can therefore describe publishing infrastructure.',
  'supportWindowIds':['rss-988576741-1ecc5cb023cf:middle','rss-1763048673-1cf4301536f2:beginning','rss-1763048673-32a6fb8cd623:ending','rss-1546456269-353036e21117:query_rich'],'type':'AI interpretive counterexample'},
 {'findingId':'qualification_matters','label':'Broad agency and future-contact themes include qualifications',
  'paraphrase':'One source limits changes to an earthly-life framework, another refuses to treat rapid developments as a settled forecast, and another portrays a contact forecast as conditional and potentially influenced by attention to it. These distinctions would disappear in a simple shared-keyword count.',
  'supportWindowIds':['rss-1529629262-6e621316510d:query_rich','rss-1560904383-7f4e01fae0ff:query_rich','rss-1611118279-afab067a712d:query_rich'],'type':'AI interpretive comparison'},
 {'findingId':'singleton_topic_context','label':'A singleton component needs source-level interpretation',
  'paraphrase':'In the Ashtar-attributed recording, workers belongs to the spiritual compound lightworkers, jumps describes claimed timeline/vibration changes, and sole occurs where surrounding text suggests a possible recognition error involving soul. These observations explain how a component can combine genuine source-specific vocabulary and transcription noise.',
  'supportWindowIds':['athina-ashtar-20230206-5d144c22:nmf_workers_context','athina-ashtar-20230206-5d144c22:nmf_jumps_context','athina-ashtar-20230206-5d144c22:nmf_sole_context'],'type':'Post-hoc AI term-context inspection'},
 {'findingId':'same_family_not_same_question','label':'A broad question family does not make answers equivalent',
  'paraphrase':'Contact-readiness passages address different subjects: an individual preparing for an encounter, a collective described as unready, and a selected audience described as already prepared. Their shared theme is not enough to establish agreement or contradiction.',
  'supportWindowIds':['rss-1556820026-decefb87233c:query_rich','daniel-item-07:opening_250_words','daniel-item-02:opening_250_words'],'type':'AI comparison; human equivalence validation pending'},
 {'findingId':'purpose_process_comparison','label':'Practical guidance has different forms across the available sources',
  'paraphrase':'The Bashar-context exchange clarifies a general action-and-belief formula, while the complete single Ashtar comparison presents accepting, identifying and embodying a life purpose. Paul Selig and the Daniel posts offer additional spiritual framings, but these source types are not balanced evidence about separate civilizations.',
  'supportWindowIds':['impossible-dreams-21-20260310:query_rich','athina-ashtar-20230206-5d144c22:purpose_stages_context','paul-birmingham-pdf:full_text','daniel-item-09:opening_250_words'],'type':'AI interpretive comparison'}
]
for f in findings:
    assert all(w in bywindow for w in f['supportWindowIds'])
    f['sourceIds']=sorted({bywindow[w]['sourceId']for w in f['supportWindowIds']})
    f['humanValidated']=False;f['exactQuotesPublished']=False
dump('interpretive-findings.json',{'schemaVersion':1,'status':'provisional_AI_reading_findings','records':findings,
                                 'meaning':'Counterexamples and comparison leads grounded in inspected windows; not population estimates or physical-origin findings'})
print(json.dumps({'interpretiveFindings':len(findings),'spellingFamilies':len(families),'variantOccurrences':[f['variantOccurrenceCount']for f in families]}))
