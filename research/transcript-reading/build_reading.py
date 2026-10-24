#!/usr/bin/env python3
"""Build public paraphrase-only qualitative/Q&A artifacts from inspected windows."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, sqlite3

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=Path('/workspace/channels-et-raw/transcript-reading')
def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def merged_seconds(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if merged and start<=merged[-1][1]:merged[-1][1]=max(end,merged[-1][1])
        else:merged.append([start,end])
    return sum(end-start for start,end in merged)
def csv_file(path,rows):
    with Path(path).open('w',newline='')as f:
        columns=list(dict.fromkeys(k for r in rows for k in r))
        out=csv.DictWriter(f,fieldnames=columns);out.writeheader()
        out.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(list,dict))else v for k,v in r.items()}for r in rows)

CODEBOOK=[
 ('contact_disclosure','Contact and disclosure','Forecasts, readiness or conditions concerning alleged contact/disclosure; not verified events.'),
 ('belief_reality_agency','Beliefs, interpretation and agency','How beliefs, interpretations and personal action are said to shape experience; qualifications and dissent remain visible.'),
 ('emotion_fear_selfworth','Fear, feeling and self-worth','Fear, emotional interpretation, confidence or felt empowerment; no clinical efficacy inference.'),
 ('practice_enthusiasm_alignment','Practice and alignment','Suggested reflection, attention, enthusiasm, meditation or symbolic spiritual practice.'),
 ('ontology_consciousness_dimensions','Consciousness and ontology','Source accounts of reality, dimensions, incarnation, divine identity or consciousness; no physical validation.'),
 ('claimed_entity_identity','Claimed beings and identity','Named or described beings, lineage, origin or alleged communication roles; source attribution only.'),
 ('epistemic_validation_skepticism','Validation, qualification and criticism','How an experience is interpreted, uncertainty expressed, evidence invoked, or a claim criticized.'),
 ('health_healing_claims','Bodily or health-related claims','Subjective bodily experiences or health-related interpretation; advertisements and interview discussion must remain distinguishable.'),
 ('relationships_collective_ethics','Relationships and collective ethics','Relationships, shared needs, social responsibility or claims about collective development.'),
 ('publisher_promotion','Publisher framing and promotion','Advertising, subscriptions, programs or media calls to action. This code alone does not establish monetization.')
]

def main():
    docs=read(HERE/'documents.json')['documents'];bydoc={d['sourceId']:d for d in docs}
    packet=read(PRIVATE/'reading-packet.json');windows=packet['windows'];bywindow={w['windowId']:w for w in windows}
    manual=read(HERE/'annotations-manual.json')['records'];assert {r['sourceId']for r in manual}==set(bydoc)
    attestation=read(HERE/'reading-attestation.json')
    assert attestation['humanValidated']is False
    assert attestation['annotationsSha256']==sha(HERE/'annotations-manual.json'),'Manual annotations changed; review and update the explicit attestation'
    assert attestation['privatePacketSha256']==sha(PRIVATE/'reading-packet.json'),'The inspected private reading packet changed; semantic reinspection is required'
    assert attestation['inspectedWindowHashes']=={w['windowId']:w['textSha256']for w in windows},'Inspected window set changed'
    assert attestation['sourceTranscriptHashes']=={d['sourceId']:d['transcriptSha256']for d in docs},'Inspected source text changed'
    assert len(windows)==len(bywindow)==105 and len(docs)==36
    code_ids={x[0]for x in CODEBOOK};annotations=[];qas=[];coverage=[]
    for d in docs:
        sid=d['sourceId'];ws=[w for w in windows if w['sourceId']==sid]
        if d['modality']=='audio_asr':
            # The source file is discovered from its hash-bound ASR output receipt.
            receipt_path=ROOT/d['sourceReceipt'];receipt=read(receipt_path)
            if 'records'in receipt:receipt=next(r for r in receipt['records']if r['sourceId']==sid)
            segpath=Path(receipt['transcriptDirectory'])/'segments.jsonl'
            assert sha(segpath)==d['segmentsSha256'];segs=[json.loads(x)for x in segpath.read_text().splitlines()if x]
            selected={s for w in ws for s in w['segmentIds']};samplewords=sum(len(s['text'].split())for s in segs if s['id']in selected)
            interval_seconds=merged_seconds([(w['startSeconds'],w['endSeconds'])for w in ws])
            coverage.append({'sourceId':sid,'modality':d['modality'],'windowsInspected':len(ws),'uniqueSegmentsInspected':len(selected),
                             'sourceSegments':len(segs),'uniqueAsrWordsInspected':samplewords,'sourceWords':d['words'],
                             'wordCoverageFraction':samplewords/d['words'],'sampledIntervalSeconds':interval_seconds,
                             'audioDurationSeconds':d['durationSeconds'],'audioIntervalCoverageFraction':interval_seconds/d['durationSeconds'],
                             'coverageMeaning':'ASR text/interval coverage, not verified spoken-word recognition or human reading'})
            d['claimedGroupAsPublished']='Ashtar-attributed creator episode'if sid.startswith('athina-')else'Bashar-related context'
        else:
            samplewords=sum(w['words']for w in ws)
            coverage.append({'sourceId':sid,'modality':d['modality'],'windowsInspected':len(ws),'uniqueTextWordsInspected':samplewords,
                             'sourceWords':d['words'],'wordCoverageFraction':samplewords/d['words'],
                             'coverageMeaning':'first250whitespace words of each RSS item, or full retained Paul PDF extraction'})
            d['claimedGroupAsPublished']=d.get('sourceCategories',['Spiritual Guides (comparison)'])[-1]
        d['humanReadingCompleted']=False;d['aiWindowReadingCompleted']=True
    for row in manual:
        sid=row['sourceId'];d=bydoc[sid];support=[]
        for code,kinds in row['codes'].items():
            assert code in code_ids
            ids=[sid+':'+kind for kind in kinds];assert all(x in bywindow for x in ids)
            support.append({'codeId':code,'windowIds':ids})
        if sid.startswith('athina-'):
            support.extend([{'codeId':'ontology_consciousness_dimensions','windowIds':[sid+':nmf_jumps_context',sid+':nmf_sole_context']},
                            {'codeId':'practice_enthusiasm_alignment','windowIds':[sid+':purpose_stages_context']},
                            {'codeId':'emotion_fear_selfworth','windowIds':[sid+':full_ashtar_comparison']},
                            {'codeId':'health_healing_claims','windowIds':[sid+':full_ashtar_comparison']}])
        spelling_windows=[w['windowId']for w in windows if w['sourceId']==sid and w['kind'].startswith('entity_spelling_')]
        if spelling_windows:support.append({'codeId':'claimed_entity_identity','windowIds':spelling_windows})
        annotations.append({'sourceId':sid,'modality':d['modality'],'codes':sorted({s['codeId']for s in support}),'support':support,
                            'synthesisParaphrase':row['synthesis'],'narrativePosition':row['position'],
                            'annotationMethod':'AI-agent semantic reading of sampled passages','reviewStatus':'provisional_human_validation_TBD',
                            'humanValidated':False,'speakerAttribution':'unknown_unsegmented','sourceTranscriptSha256':d['transcriptSha256']})
        kind='query_rich'if d['modality']=='audio_asr'else'full_text'if sid=='paul-birmingham-pdf'else'opening_250_words'
        w=bywindow[sid+':'+kind]
        candidate={'candidateId':'reading-qa-'+hashlib.sha256((sid+':'+row['qaKind']).encode()).hexdigest()[:12],
                   'sourceId':sid,'modality':d['modality'],'publisher':d['publisher'],'practitionerContext':d['practitionerContext'],
                   'claimedGroupAsPublished':d['claimedGroupAsPublished'],'candidateKind':row['qaKind'],
                   'questionParaphrase':row['question'],'answerParaphrase':row['answer'],'promptFamily':row['family'],
                   'questionForm':row['questionForm'],'answerScope':row['scope'],'supportWindowId':w['windowId'],
                   'supportTextSha256':w['textSha256'],'sourceTranscriptSha256':d['transcriptSha256'],
                   'sourceReceipt':d['sourceReceipt'],'sourceUrl':d['sourceUrl'],
                   'speakerAttribution':'unknown_unsegmented','boundaryStatus':'question_answer_turns_unsegmented',
                   'humanValidated':False,'exactQuotePublished':False,'semanticEquivalenceValidated':False}
        if d['modality']=='audio_asr':candidate.update(startSeconds=w['startSeconds'],endSeconds=w['endSeconds'],supportSegmentIds=w['segmentIds'],sourceSegmentsSha256=d['segmentsSha256'],sourceAudioSha256=d['sourceAudioSha256'])
        else:candidate.update(startChar=w['startChar'],endChar=w['endChar'])
        qas.append(candidate)
    sid='athina-ashtar-20230206-5d144c22';d=bydoc[sid];w=bywindow[sid+':purpose_stages_context']
    qas.append({'candidateId':'reading-qa-ashtar-purpose-stages','sourceId':sid,'modality':'audio_asr','publisher':d['publisher'],
                'practitionerContext':d['practitionerContext'],'claimedGroupAsPublished':d['claimedGroupAsPublished'],
                'candidateKind':'rhetorical_guidance_question_candidate','questionForm':'rhetorical listener question in a source-presented channeled address; speaker transition unverified',
                'questionParaphrase':'How does a listener identify and enact a personal life purpose?',
                'answerParaphrase':'The address distinguishes accepting that a purpose exists, seeking to identify it, and putting it into practice. It also recommends community, learning and spiritual assistance during that process. These are source teachings, not validated guidance or proof of an entity speaker.',
                'promptFamily':'practical_guidance','answerScope':'bounded passage located after deliberate full reading of the single comparison recording',
                'supportWindowId':w['windowId'],'supportTextSha256':w['textSha256'],'sourceTranscriptSha256':d['transcriptSha256'],
                'sourceSegmentsSha256':d['segmentsSha256'],'sourceAudioSha256':d['sourceAudioSha256'],
                'sourceReceipt':d['sourceReceipt'],'sourceUrl':d['sourceUrl'],'startSeconds':w['startSeconds'],'endSeconds':w['endSeconds'],
                'supportSegmentIds':w['segmentIds'],'speakerAttribution':'unknown_unsegmented','boundaryStatus':'question_answer_turns_unsegmented',
                'humanValidated':False,'exactQuotePublished':False,'semanticEquivalenceValidated':False})
    methods={'annotationMethod':'AI-agent semantic close reading; no external model inference or human annotation',
             'sampling':'Fixed beginning/middle/ending30second targets and one60second question-marker/topic-keyword enriched target per ASR; segment boundaries can extend targets; first250whitespace words per Daniel item; full Paul PDF extraction; three post-hoc NMF-term windows, deliberate full reading plus a bounded purpose-guidance window in the single Athina comparison source, and four post-hoc entity-spelling contexts',
             'wordCountMethod':'Python str.split whitespace tokens for both numerator and denominator; differs from regex counts in some inherited primary metadata',
             'quotePolicy':'No raw source text or verbatim quotations in public reading/Q&A artifacts; full windows remain private',
             'qaMeaning':'AI paraphrase candidates. Interview, fragmentary, rhetorical/self-question, secondary-report and analyst-constructed authored prompts are separate kinds.',
             'comparisonMeaning':'Prompt-family membership is an AI analytic grouping, not validated question equivalence, answer agreement, entity identity, or independent evidence.'}
    dump(HERE/'documents.json',{'schemaVersion':1,'wordCountMethod':methods['wordCountMethod'],'documents':docs})
    dump(HERE/'codebook.json',{'schemaVersion':1,'codingUnit':'inspected source window; overlapping codes aggregated to source-document presence','codes':[{'codeId':i,'label':label,'definition':desc}for i,label,desc in CODEBOOK],**methods})
    dump(HERE/'qualitative-codes.json',{'schemaVersion':1,'methods':methods,'records':annotations})
    dump(HERE/'qa-candidates.json',{'schemaVersion':1,'methods':methods,'records':qas})
    csv_file(HERE/'qa-candidates.csv',qas);csv_file(HERE/'qualitative-codes.csv',annotations)
    public_windows=[{k:v for k,v in w.items()if k!='text'}for w in windows]
    dump(HERE/'reading-windows.json',{'schemaVersion':1,'readStatus':'AI_inspected_sample_windows','allPreparedWindowsInspected':True,
                                   'humanValidated':False,'privatePacketSha256':sha(PRIVATE/'reading-packet.json'),
                                   'methods':methods,'windows':public_windows,'coverageByDocument':coverage})
    families=defaultdict(list)
    for q in qas:families[q['promptFamily']].append(q)
    family_rows=[{'promptFamily':family,'candidateIds':[q['candidateId']for q in qs],
                  'sourceIds':[q['sourceId']for q in qs],'candidateKinds':dict(Counter(q['candidateKind']for q in qs)),
                  'modalityCounts':dict(Counter(q['modality']for q in qs)),
                  'meaning':'coarse AI analytic comparison family; no validated prompt equivalence or doctrinal agreement'}for family,qs in sorted(families.items())]
    dump(HERE/'prompt-family-comparisons.json',{'schemaVersion':1,'records':family_rows})
    audio_cov=[c for c in coverage if c['modality']=='audio_asr'];text_cov=[c for c in coverage if c['modality']=='publisher_text']
    summary={'schemaVersion':1,'status':'executed_provisional_AI_reading_and_candidate_extraction',
             'documents':36,'audioAsrDocuments':20,'publisherTextDocuments':16,'fixedSampleWindows':96,'adaptiveNmfWindows':3,'additionalFullComparisonAndLocatorWindows':2,'adaptiveEntitySpellingWindows':4,
             'inspectedWindows':105,'packetWordsRead':sum(w['words']for w in windows),'packetWordCountIncludesOverlappingWindows':True,'packetWordsByModality':dict(Counter({m:sum(w['words']for w in windows if bydoc[w['sourceId']]['modality']==m)for m in ('audio_asr','publisher_text')})),
             'uniqueAsrSegmentsRead':sum(c['uniqueSegmentsInspected']for c in audio_cov),'asrSegmentsTotal':sum(c['sourceSegments']for c in audio_cov),
             'uniqueAsrWordsRead':sum(c['uniqueAsrWordsInspected']for c in audio_cov),'asrWordsTotal':sum(c['sourceWords']for c in audio_cov),
             'uniquePublisherTextWordsRead':sum(c['uniqueTextWordsInspected']for c in text_cov),'publisherTextWordsTotal':sum(c['sourceWords']for c in text_cov),
             'sampledAsrIntervalSeconds':sum(c['sampledIntervalSeconds']for c in audio_cov),'audioDurationSeconds':sum(c['audioDurationSeconds']for c in audio_cov),
             'qaCandidateRecords':len(qas),'qaCandidateKinds':dict(Counter(q['candidateKind']for q in qas)),'promptFamilies':len(families),
             'manualCodebookCodes':len(CODEBOOK),'documentCodeAssignments':sum(len(a['codes'])for a in annotations),
             'codePresenceByModality':{m:dict(Counter(code for a in annotations if a['modality']==m for code in a['codes']))for m in ('audio_asr','publisher_text')},
             'humanValidated':False,'speakerDiarizationPerformed':False,'videoEditionVerified':False,'newYoutubeVideos':0,
             'newExternalModelInferenceRuns':0,'publicRawTranscriptText':False,'methods':methods,
             'limits':['Nineteen audio records are Bashar-related publisher contexts; the twentieth is a single Ashtar-attributed creator episode, not balanced ET groups.',
                       'The15Daniel posts are one publisher/practitioner and multiple source-attributed groups; Paul is a spiritual comparison source.',
                       'Sample selection is purposeful and query-enriched, so code percentages are not full-corpus theme prevalence.',
                       'Paraphrases, question boundaries, entity names, speaker attribution and answer equivalence require human validation.',
                       'Advertisements, publisher framing, skeptical reported speech and ASR errors can drive lexical similarity.']}
    summary['asrWordCoverageFraction']=summary['uniqueAsrWordsRead']/summary['asrWordsTotal']
    summary['publisherTextWordCoverageFraction']=summary['uniquePublisherTextWordsRead']/summary['publisherTextWordsTotal']
    dump(HERE/'summary.json',summary)
    dbpath=HERE/'qa-candidates.sqlite';temp=HERE/'qa-candidates.sqlite.tmp'
    if temp.exists():temp.unlink()
    with sqlite3.connect(temp)as db:
        db.executescript('''PRAGMA foreign_keys=ON;
          CREATE TABLE documents(source_id TEXT PRIMARY KEY,modality TEXT NOT NULL,publisher TEXT,title TEXT,transcript_sha256 TEXT NOT NULL,record_json TEXT NOT NULL);
          CREATE TABLE windows(window_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES documents(source_id),kind TEXT NOT NULL,start_seconds REAL,end_seconds REAL,start_char INTEGER,end_char INTEGER,text_sha256 TEXT NOT NULL,record_json TEXT NOT NULL);
          CREATE TABLE codes(code_id TEXT PRIMARY KEY,label TEXT NOT NULL,definition TEXT NOT NULL);
          CREATE TABLE document_codes(source_id TEXT NOT NULL REFERENCES documents(source_id),code_id TEXT NOT NULL REFERENCES codes(code_id),support_window_ids_json TEXT NOT NULL,PRIMARY KEY(source_id,code_id));
          CREATE TABLE qa_candidates(candidate_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES documents(source_id),candidate_kind TEXT NOT NULL,prompt_family TEXT NOT NULL,question_paraphrase TEXT NOT NULL,answer_paraphrase TEXT NOT NULL,support_window_id TEXT NOT NULL REFERENCES windows(window_id),human_validated INTEGER NOT NULL CHECK(human_validated=0),record_json TEXT NOT NULL);
          CREATE TABLE methodology(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);''')
        for d in docs:db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)',(d['sourceId'],d['modality'],d['publisher'],d['title'],d['transcriptSha256'],json.dumps(d,ensure_ascii=False)))
        for w in public_windows:db.execute('INSERT INTO windows VALUES(?,?,?,?,?,?,?,?,?)',(w['windowId'],w['sourceId'],w['kind'],w.get('startSeconds'),w.get('endSeconds'),w.get('startChar'),w.get('endChar'),w['textSha256'],json.dumps(w,ensure_ascii=False)))
        db.executemany('INSERT INTO codes VALUES(?,?,?)',CODEBOOK)
        for a in annotations:
            combined=defaultdict(set)
            for s in a['support']:combined[s['codeId']].update(s['windowIds'])
            for code,ids in combined.items():db.execute('INSERT INTO document_codes VALUES(?,?,?)',(a['sourceId'],code,json.dumps(sorted(ids))))
        for q in qas:db.execute('INSERT INTO qa_candidates VALUES(?,?,?,?,?,?,?,?,?)',(q['candidateId'],q['sourceId'],q['candidateKind'],q['promptFamily'],q['questionParaphrase'],q['answerParaphrase'],q['supportWindowId'],0,json.dumps(q,ensure_ascii=False)))
        for k,v in methods.items():db.execute('INSERT INTO methodology VALUES(?,?)',(k,json.dumps(v)))
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()
    temp.replace(dbpath)
    print(json.dumps({k:v for k,v in summary.items()if k not in ('methods','limits','codePresenceByModality')}))

if __name__=='__main__':main()
