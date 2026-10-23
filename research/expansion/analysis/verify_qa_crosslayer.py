#!/usr/bin/env python3
"""Bounded cross-workstream audit; never imports the Q&A producer."""
import collections, csv, hashlib, json, pathlib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
P=pathlib.Path(__file__).resolve().parents[1];REPO=P.parents[1];q=P/'qa'
rows=json.loads((q/'qa-candidates.json').read_text())['records'];pairs=json.loads((q/'question-pairs.json').read_text())['records'];summary=json.loads((q/'summary.json').read_text());checks=[]
def check(ok,label): checks.append({'check':label,'passed':bool(ok)})
for r in rows:
    path=REPO/r['sourcePath'];raw=path.read_bytes();source=json.loads(raw);index=int(r['sourcePointer'].split('/')[-1]);item=source['qa_topics'][index]
    check(hashlib.sha256(raw).hexdigest()==r['sourceSha256'],r['id']+' digest byte hash')
    check(item['question']==r['question'] and item['answer_gist']==r['answerGist'],r['id']+' pointer preserves question and answer gist')
    check(not r['speakerVerified'] and r['timestampSeconds'] is None,r['id']+' unresolved speech evidence preserved')
Q=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform([r['question'] for r in rows]);M=(Q@Q.T).toarray();index={r['id']:i for i,r in enumerate(rows)};ii,jj=np.triu_indices(len(rows),1);distinct=np.array([rows[i]['videoId']!=rows[j]['videoId'] for i,j in zip(ii,jj)]);expected={(rows[i]['id'],rows[j]['id']) for i,j in zip(ii[distinct],jj[distinct]) if M[i,j]>=.4}
check(expected=={(p['leftId'],p['rightId']) for p in pairs},'All and only distinct-upload pairs above .40 are retained')
for p in pairs:check(abs(M[index[p['leftId']],index[p['rightId']]]-p['questionCosine'])<5.1e-7,p['leftId']+'/'+p['rightId']+' independent question cosine')
counter=collections.Counter(tuple(sorted([p['leftVideoId'],p['rightVideoId']])) for p in pairs)
if 'retrievalThresholds' in summary['sensitivity']:
    for threshold in summary['sensitivity']['retrievalThresholds']:
        t=threshold['minimumQuestionCosine'];selected=[(i,j) for i,j in zip(ii[distinct],jj[distinct]) if M[i,j]>=t]
        check(len(selected)==threshold['candidatePairs'],f'Threshold {t} candidate count from independent matrix')
        check(len({tuple(sorted([rows[i]['videoId'],rows[j]['videoId']])) for i,j in selected})==threshold['distinctUploadPairs'],f'Threshold {t} upload-pair denominator')
    c=summary['sensitivity']['uploadPairConcentration']
    check(c['distinctUploadPairs']==len(counter) and c['totalQuestionPairs']==len(pairs),'Retrieval concentration denominators')
    check(c['topThreeUploadPairCandidateMatches']==sum(n for k,n in counter.most_common(3)),'Top-three upload pair match count')
    check(abs(c['topThreeUploadPairShare']-sum(n for k,n in counter.most_common(3))/len(pairs))<5.1e-7,'Top-three concentration share')
    preview=summary['questionPairsPreview'];check(preview['shown']==len(summary['questionPairs']) and preview['total']==len(pairs) and preview['truncated']==(preview['shown']<preview['total']),'Summary preview count disclosure')
with (q/'qa-candidates.csv').open() as f:csvrows=list(csv.DictReader(f))
check(len(csvrows)==len(rows),'CSV candidate denominator')
check(all(c['speakerVerified']=='false' and c['humanReviewed']=='false' for c in csvrows),'CSV literal false status preserved')
check(all(c['timestampSeconds']=='' for c in csvrows),'CSV unavailable timestamps remain empty')
out={'review':'Cross-workstream numerical and provenance audit, not human or audiovisual validation','inputs':{f:hashlib.sha256((q/f).read_bytes()).hexdigest() for f in ['qa-candidates.json','question-pairs.json','summary.json']},'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'questionPairs':len(pairs),'distinctUploadPairs':len(counter),'threeLargestUploadPairsQuestionPairCount':sum(n for k,n in counter.most_common(3)),'upperThresholdSensitivity':[{'threshold':t,'retainedPairs':sum(M[ii,jj][distinct]>=t)} for t in [.4,.5,.6,.7,.8,.9]],'summaryPreviewPairs':len(summary['questionPairs']),'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL'}
for x in out['upperThresholdSensitivity']:x['retainedPairs']=int(x['retainedPairs'])
(pathlib.Path(__file__).resolve().parent/'generated/qa-crosslayer-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out));raise SystemExit(bool(out['failed']))
