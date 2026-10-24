#!/usr/bin/env python3
"""Independent full locator/coverage/export audit; no claim of semantic truth labels."""
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;READING=ROOT/'research/transcript-reading'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def union_seconds(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if not merged or start>merged[-1][1]:merged.append([start,end])
        else:merged[-1][1]=max(merged[-1][1],end)
    return sum(end-start for start,end in merged)
def audit():
    raw={};segments={};pins={}
    for r in load(ROOT/'research/harvest/asr/summary.json')['records']+[load(ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json')]:
        directory=Path(r['transcriptDirectory']);raw[r['sourceId']]=(directory/'transcript.txt').read_text();segments[r['sourceId']]=[json.loads(x) for x in (directory/'segments.jsonl').read_text().splitlines() if x]
    primary=load(ROOT/'research/access-repair/primary-sources/expanded-metadata.json')
    for r in primary['daniel']['items']:raw[f"daniel-item-{r['item_index']:02d}"]=Path(r['text']['raw_local_path']).read_text()
    raw['paul-birmingham-pdf']=Path(primary['paul']['text']['raw_local_path']).read_text()
    files={name:READING/name for name in ('documents.json','reading-windows.json','qa-candidates.json','qualitative-codes.json','prompt-family-comparisons.json','summary.json','qa-candidates.sqlite','qa-candidates.csv','codebook.json')}
    pins={str(p.relative_to(ROOT)):sha(p) for p in files.values()}
    docs={r['sourceId']:r for r in load(files['documents.json'])['documents']};window_data=load(files['reading-windows.json']);windows=window_data['windows'];bywindow={w['windowId']:w for w in windows};qas=load(files['qa-candidates.json'])['records'];summary=load(files['summary.json'])
    checks=0
    def check(ok,label):
        nonlocal checks
        checks+=1;assert ok,label
    check(set(docs)==set(raw),'complete source identity join')
    for sid,doc in docs.items():check(hashlib.sha256(raw[sid].encode()).hexdigest()==doc['transcriptSha256'],'source byte hash:'+sid)
    check(len(bywindow)==len(windows),'unique window IDs');texts={}
    for window in windows:
        sid=window['sourceId']
        if sid in segments:
            lookup={r['id']:r for r in segments[sid]};selected=[lookup[i] for i in window['segmentIds']]
            text=' '.join(r['text'].strip() for r in selected)
            check(window['startSeconds']==selected[0]['start'] and window['endSeconds']==selected[-1]['end'],'window ASR boundary')
            check(window['firstSegmentId']==selected[0]['id'] and window['lastSegmentId']==selected[-1]['id'],'segment boundary IDs')
            check([r['id'] for r in selected]==sorted(set(r['id'] for r in selected)),'ordered unique segment IDs')
        else:
            check(0<=window['startChar']<=window['endChar']<=len(raw[sid]),'character bounds');text=raw[sid][window['startChar']:window['endChar']]
        check(hashlib.sha256(text.encode()).hexdigest()==window['textSha256'],'window text hash:'+window['windowId'])
        check(len(text.split())==window['words'],'window words');texts[window['windowId']]=text
    unique_asr_words=0;unique_asr_segments=0;unique_authored_words=0;seconds=0;coverage={r['sourceId']:r for r in window_data['coverageByDocument']}
    for sid,doc in docs.items():
        chosen=[w for w in windows if w['sourceId']==sid];row=coverage[sid]
        check(row['windowsInspected']==len(chosen),'windows per document');check(row['sourceWords']==len(raw[sid].split()),'coverage source denominator')
        if sid in segments:
            selected={i for w in chosen for i in w['segmentIds']};count=sum(len(s['text'].split()) for s in segments[sid] if s['id'] in selected)
            interval=union_seconds((w['startSeconds'],w['endSeconds']) for w in chosen)
            check(row['uniqueSegmentsInspected']==len(selected) and row['sourceSegments']==len(segments[sid]),'unique segments')
            check(row['uniqueAsrWordsInspected']==count,'overlap-deduplicated ASR words')
            check(abs(row['sampledIntervalSeconds']-interval)<1e-7,'deduplicated interval seconds')
            unique_asr_words+=count;unique_asr_segments+=len(selected);seconds+=interval
        else:
            # Every authored document currently has one source-aligned prefix/full window.
            check(len(chosen)==1,'authored single interval assumption');count=len(texts[chosen[0]['windowId']].split())
            check(row['uniqueTextWordsInspected']==count,'authored coverage');unique_authored_words+=count
        check(abs(row['wordCoverageFraction']-count/len(raw[sid].split()))<1e-12,'word coverage fraction')
    check(unique_asr_words==summary['uniqueAsrWordsRead'] and unique_asr_segments==summary['uniqueAsrSegmentsRead'],'ASR coverage totals')
    check(unique_authored_words==summary['uniquePublisherTextWordsRead'],'authored coverage total')
    check(abs(seconds-summary['sampledAsrIntervalSeconds'])<1e-7,'interval total')
    check(sum(w['words'] for w in windows)==summary['packetWordsRead'],'overlapping packet count')
    check(len(qas)==len({q['candidateId'] for q in qas})==summary['qaCandidateRecords'],'unique QA IDs')
    for q in qas:
        w=bywindow[q['supportWindowId']];doc=docs[q['sourceId']]
        check(w['sourceId']==q['sourceId'] and w['textSha256']==q['supportTextSha256'],'QA support exact source/hash')
        check(q['sourceTranscriptSha256']==doc['transcriptSha256'],'QA source transcript')
        check(q['speakerAttribution']=='unknown_unsegmented' and q['boundaryStatus']=='question_answer_turns_unsegmented','no fabricated turn or speaker boundary')
        check(q['humanValidated'] is False and q['exactQuotePublished'] is False and q['semanticEquivalenceValidated'] is False,'QA validation flags')
        if q['sourceId'] in segments:
            check(q['startSeconds']==w['startSeconds'] and q['endSeconds']==w['endSeconds'] and q['supportSegmentIds']==w['segmentIds'],'QA time/segment anchors')
            check(q['sourceAudioSha256']==doc['sourceAudioSha256'] and q['sourceSegmentsSha256']==doc['segmentsSha256'],'QA audio/segment hash')
        else:check(q['startChar']==w['startChar'] and q['endChar']==w['endChar'] and q['candidateKind']=='authored_comparison_prompt','authored constructed prompt/character anchors')
    codes=load(files['qualitative-codes.json'])['records'];codebook={r['codeId'] for r in load(files['codebook.json'])['codes']}
    check(sum(len(r['codes']) for r in codes)==summary['documentCodeAssignments'],'code assignment totals')
    for row in codes:
        check(set(row['codes']).issubset(codebook),'codebook join')
        for support in row['support']:
            check(support['codeId'] in row['codes'],'supported code membership')
            check(all(bywindow[w]['sourceId']==row['sourceId'] for w in support['windowIds']),'code support source')
    family_duplicates=[];byqa={q['candidateId']:q for q in qas}
    for family in load(files['prompt-family-comparisons.json'])['records']:
        subset=[byqa[i] for i in family['candidateIds']]
        check([x['sourceId'] for x in subset]==family['sourceIds'],'prompt-family candidates')
        check(dict(Counter(x['candidateKind'] for x in subset))==family['candidateKinds'],'prompt kinds by family')
        if len(set(family['sourceIds']))!=len(family['sourceIds']):family_duplicates.append({'family':family['promptFamily'],'candidate_count':len(subset),'unique_source_count':len(set(family['sourceIds']))})
    with sqlite3.connect(files['qa-candidates.sqlite'].as_uri()+'?mode=ro',uri=True) as db:
        check(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall(),'SQLite integrity/foreign keys')
        expected={'documents':len(docs),'windows':len(windows),'codes':len(codebook),'document_codes':summary['documentCodeAssignments'],'qa_candidates':len(qas)}
        for table,n in expected.items():check(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==n,'SQLite row count:'+table)
        for candidate_id,record in db.execute('SELECT candidate_id,record_json FROM qa_candidates'):check(json.loads(record)==byqa[candidate_id],'SQLite/JSON exact QA join')
    with files['qa-candidates.csv'].open() as f:csvrows=list(csv.DictReader(f))
    check(len(csvrows)==len(qas),'CSV row count')
    for row in csvrows:check(row['questionParaphrase']==byqa[row['candidateId']]['questionParaphrase'] and row['answerParaphrase']==byqa[row['candidateId']]['answerParaphrase'],'CSV paraphrase source binding')
    public_bytes=b'\n'.join(p.read_bytes() for p in files.values())
    check(all(text.encode() not in public_bytes for text in texts.values() if len(text)>80),'no entire inspected source window in public reading exports')
    return {'schema_version':1,'status':'pass','method':'Independent source reconstruction for all windows and QA anchors, overlap-deduplicated coverage, DB/CSV/source joins; no author helper imports',
            'checks':checks,'pins':pins,'sources':len(docs),'windows':len(windows),'qa_candidates':len(qas),'qa_kinds':dict(Counter(q['candidateKind'] for q in qas)),
            'unique_asr_words_inspected':unique_asr_words,'unique_asr_segments_inspected':unique_asr_segments,'unique_authored_words_inspected':unique_authored_words,
            'overlapping_packet_words':sum(w['words'] for w in windows),'asr_word_coverage':summary['asrWordCoverageFraction'],'authored_word_coverage':summary['publisherTextWordCoverageFraction'],
            'fully_covered_asr_sources':[sid for sid,row in coverage.items() if sid in segments and row['wordCoverageFraction']==1],
            'family_source_duplicates':family_duplicates,'semantic_support_review':'Purposeful qualitative subset is reviewed separately; locator validity does not validate paraphrase meaning',
            'network_requests':0,'new_llm_or_asr_inference':False,'raw_text_published':False}
if __name__=='__main__':
    result=audit();(HERE/'reading-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
