#!/usr/bin/env python3
"""Validate source/window joins, exact coverage and paraphrase-only release bounds."""
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,sqlite3,tempfile,shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=Path('/workspace/channels-et-raw/transcript-reading')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]
def check(value,label):
    assert value,label
    checks.append(label)

docs=read(HERE/'documents.json')['documents'];bydoc={d['sourceId']:d for d in docs}
summary=read(HERE/'summary.json');windows=read(HERE/'reading-windows.json')['windows'];bywindow={w['windowId']:w for w in windows}
packet=read(PRIVATE/'reading-packet.json')['windows'];privatewindows={w['windowId']:w for w in packet}
manifest=read(HERE/'source-manifest.json');annotations=read(HERE/'qualitative-codes.json')['records'];qa=read(HERE/'qa-candidates.json')['records']
check(len(docs)==len(bydoc)==36,'36 unique source IDs')
check(Counter(d['modality']for d in docs)=={'audio_asr':20,'publisher_text':16},'Separate20audio/16text strata')
for source,expected in manifest['receiptPins'].items():check(sha(ROOT/source)==expected,'Receipt pin '+source)
for f in manifest['privateFiles']:
    p=Path(f['path']);check(p.stat().st_size==f['bytes']and sha(p)==f['sha256'],'Private output hash '+p.name+':'+f['sha256'][:12])
check(len(manifest['privateFiles'])==76,'60ASR outputs plus16text files verified')
source_segments={};source_text={}
primary=read(ROOT/'research/access-repair/primary-sources/expanded-metadata.json')
for d in docs:
    sid=d['sourceId']
    if d['modality']=='audio_asr':
        receipt=read(ROOT/d['sourceReceipt'])
        if'records'in receipt:receipt=next(r for r in receipt['records']if r['sourceId']==sid)
        directory=Path(receipt['transcriptDirectory']);source_text[sid]=(directory/'transcript.txt').read_text()
        source_segments[sid]=[json.loads(x)for x in(directory/'segments.jsonl').read_text().splitlines()if x]
        check(sha(directory/'transcript.txt')==d['transcriptSha256']and sha(directory/'segments.jsonl')==d['segmentsSha256'],'ASR document hashes '+sid)
        check(receipt['sourceAudioSha256']==d['sourceAudioSha256'],'ASR/audio receipt join '+sid)
    else:
        f=primary['paul']['text']if sid=='paul-birmingham-pdf'else primary['daniel']['items'][int(sid.rsplit('-',1)[1])]['text']
        source_text[sid]=Path(f['raw_local_path']).read_text();check(sha(f['raw_local_path'])==d['transcriptSha256'],'Authored text hash '+sid)
    check(len(source_text[sid].split())==d['words'],'Whitespace denominator '+sid)
check(len(windows)==len(bywindow)==len(packet)==105,'105 unique private/public inspected windows')
for w in windows:
    sid=w['sourceId'];private=privatewindows[w['windowId']]
    check('text'not in w,'No public window body '+w['windowId'])
    if bydoc[sid]['modality']=='audio_asr':
        chosen=[s for s in source_segments[sid]if s['id']in set(w['segmentIds'])];text=' '.join(s['text'].strip()for s in chosen)
        check([s['id']for s in chosen]==w['segmentIds']and chosen[0]['start']==w['startSeconds']and chosen[-1]['end']==w['endSeconds'],'Exact ASR segment/time locator '+w['windowId'])
    else:text=source_text[sid][w['startChar']:w['endChar']]
    check(text==private['text']and hashlib.sha256(text.encode()).hexdigest()==w['textSha256'],'Reconstructed window text hash '+w['windowId'])
    check(len(text.split())==w['words'],'Window token count '+w['windowId'])
audio_unique=0;segments_unique=0;text_unique=0
for sid,d in bydoc.items():
    ws=[w for w in windows if w['sourceId']==sid]
    if d['modality']=='audio_asr':
        ids={i for w in ws for i in w['segmentIds']};segments_unique+=len(ids)
        audio_unique+=sum(len(s['text'].split())for s in source_segments[sid]if s['id']in ids)
    else:text_unique+=sum(w['words']for w in ws)
check(audio_unique==11992==summary['uniqueAsrWordsRead'],'Deduplicated ASR word numerator')
check(segments_unique==1112==summary['uniqueAsrSegmentsRead'],'Deduplicated ASR segment numerator')
check(text_unique==6319==summary['uniquePublisherTextWordsRead'],'Authored word numerator')
check(summary['asrWordsTotal']==226093 and summary['publisherTextWordsTotal']==13656,'Consistent full-text denominators')
check(summary['packetWordsRead']==sum(w['words']for w in windows)==19603 and summary['packetWordCountIncludesOverlappingWindows']is True,'Packet overlap explicitly distinguished')
check(summary['asrWordCoverageFraction']==audio_unique/226093 and summary['publisherTextWordCoverageFraction']==text_unique/13656,'Coverage fractions recomputed')
codes={x['codeId']for x in read(HERE/'codebook.json')['codes']}
check(len(codes)==10 and len(annotations)==36,'Codebook/document counts')
for a in annotations:
    check(a['humanValidated']is False and a['speakerAttribution']=='unknown_unsegmented','No human/speaker validation '+a['sourceId'])
    check(set(a['codes'])=={s['codeId']for s in a['support']}<=codes,'Code/support coverage '+a['sourceId'])
    check(all(bywindow[w]['sourceId']==a['sourceId']for s in a['support']for w in s['windowIds']),'Same-source code windows '+a['sourceId'])
check(sum(len(a['codes'])for a in annotations)==142==summary['documentCodeAssignments'],'142 overlapping source/code assignments')
check(len(qa)==len({q['candidateId']for q in qa})==37,'37 unique paraphrase candidates')
for q in qa:
    d=bydoc[q['sourceId']];w=bywindow[q['supportWindowId']]
    check(w['sourceId']==q['sourceId']and q['sourceTranscriptSha256']==d['transcriptSha256']and q['supportTextSha256']==w['textSha256'],'QA source/window hash join '+q['candidateId'])
    check(q['humanValidated']is False and q['exactQuotePublished']is False and q['semanticEquivalenceValidated']is False,'QA provisional paraphrase boundaries '+q['candidateId'])
    check(q['speakerAttribution']=='unknown_unsegmented'and q['boundaryStatus']=='question_answer_turns_unsegmented','No false QA turn attribution '+q['candidateId'])
    if d['modality']=='audio_asr':check(q['supportSegmentIds']==w['segmentIds']and q['startSeconds']==w['startSeconds']and q['endSeconds']==w['endSeconds'],'QA exact ASR locator '+q['candidateId'])
    else:check(q['candidateKind']=='authored_comparison_prompt'and q['startChar']==w['startChar']and q['endChar']==w['endChar'],'Constructed authored prompt/locator '+q['candidateId'])
check(Counter(q['candidateKind']for q in qa)==summary['qaCandidateKinds'],'Distinct question kinds reconcile')
with sqlite3.connect((HERE/'qa-candidates.sqlite').as_uri()+'?mode=ro',uri=True)as db:
    check(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'and not db.execute('PRAGMA foreign_key_check').fetchall(),'SQLite integrity and foreign keys')
    expected={'documents':36,'windows':105,'codes':10,'document_codes':142,'qa_candidates':37}
    for table,n in expected.items():check(db.execute(f'SELECT COUNT(*)FROM {table}').fetchone()[0]==n,'SQLite row count '+table)
    saved={r[0]:json.loads(r[1])for r in db.execute('SELECT candidate_id,record_json FROM qa_candidates')}
    check(saved=={q['candidateId']:q for q in qa},'SQLite/JSON QA byte-value consistency')
public=(HERE/'qa-candidates.json').read_text()+(HERE/'qualitative-codes.json').read_text()+(HERE/'reading-windows.json').read_text()
check(all(w['text']not in public for w in packet if len(w['text'])>=90),'No complete substantial source window is publicly reproduced')
spelling=read(HERE/'posthoc-entity-spelling-review.json')
check(spelling['predeclaredStrictLexiconChanged']is False,'Strict lexical counts remain unchanged')
for family in spelling['families']:
    check(not family['audioChecked']and not family['humanValidatedAlias']and not family['mergedIntoPredeclaredCounts'],'Spelling interpretation limits '+family['candidateFamily'])
    check(family['allVariantHitSegmentsCoveredByInspectedWindows'],'All proposed spelling contexts inspected '+family['candidateFamily'])
check([(f['variantOccurrenceCount'],f['variantDocumentCount'])for f in spelling['families']]==[(4,4),(14,1)],'Post-hoc candidate occurrence/document counts')

# The automatic build must not promote changed text/annotations as already read.
spec=importlib.util.spec_from_file_location('reading_guard_fixture',HERE/'build_reading.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for changed in ('annotations','packet','source_hash'):
    with tempfile.TemporaryDirectory(prefix='reading-attestation-guard-')as temp:
        t=Path(temp);private=t/'private';private.mkdir()
        for name in ('documents.json','annotations-manual.json','reading-attestation.json'):shutil.copyfile(HERE/name,t/name)
        shutil.copyfile(PRIVATE/'reading-packet.json',private/'reading-packet.json')
        if changed=='annotations':
            j=read(t/'annotations-manual.json');j['records'][0]['answer']='Changed synthetic fixture';dump=t/'annotations-manual.json';dump.write_text(json.dumps(j))
        elif changed=='packet':
            j=read(private/'reading-packet.json');j['windows'][0]['text']='Changed synthetic fixture';(private/'reading-packet.json').write_text(json.dumps(j))
        else:
            j=read(t/'documents.json');j['documents'][0]['transcriptSha256']='0'*64;(t/'documents.json').write_text(json.dumps(j))
        module.HERE=t;module.PRIVATE=private
        try:module.main()
        except AssertionError:check(True,'Changed '+changed+' rejected before publication')
        else:raise AssertionError('Changed '+changed+' incorrectly reused reading attestation')

files=[p for p in sorted(HERE.iterdir())if p.is_file()and p.name!='verification.json'and not p.name.endswith('.tmp')]
report={'schemaVersion':1,'checkedAt':datetime.now(timezone.utc).isoformat(),'status':'PASS','checksPassed':len(checks),
        'scope':'Source integrity, exact supporting locators, coverage, artifact joins, public text limits and frozen-reading guards; semantic paraphrases remain provisional',
        'privateFilesVerified':76,'sourceDocuments':36,'windowsReconstructed':105,'qaCandidatesJoined':37,'sqliteCounts':expected,
        'attestationMutationGuardsPassed':3,'networkRequests':0,'neuralInferenceRuns':0,'humanSemanticValidation':False,
        'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in files]}
(HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k!='files'}))
