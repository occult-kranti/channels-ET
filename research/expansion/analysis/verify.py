#!/usr/bin/env python3
"""Independently reconcile expansion rows to frozen inputs without importing producer."""
import collections, hashlib, json, pathlib, re, statistics
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[3];HERE=pathlib.Path(__file__).resolve().parent
d=json.loads((ROOT/'dist/analysis/data.json').read_text());r=json.loads((HERE/'results.json').read_text());checks=[]
def check(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
def near(a,b,label,tol=1e-7):check(abs(a-b)<tol,label)
vs=d['videos'];caps={x['videoId'] for x in d['transcripts']['rows']};by=collections.Counter(v.get('channelId') for v in vs)
check(len(vs)==925 and len({v['id'] for v in vs})==925,'Exact distinct upload denominator')
check(r['source']['sha256']==hashlib.sha256((ROOT/'dist/analysis/data.json').read_bytes()).hexdigest(),'Snapshot byte hash')
check(sum(c['uploads'] for c in r['channels'])+by[None]==len(vs),'Account totals plus unresolved reconcile')
for c in r['channels']:
    vv=[v for v in vs if v.get('channelId')==c['id']];known=[v['durationSeconds']/60 for v in vv if isinstance(v.get('durationSeconds'),(int,float)) and v['durationSeconds']>0]
    check(c['uploads']==len(vv) and c['knownDurations']==len(known),f"{c['id']} source-derived counts")
    check(c['captionPilotDocuments']==sum(v['id'] in caps for v in vv),f"{c['id']} caption ID join")
    if known:near(c['medianMinutes'],statistics.median(known),f"{c['id']} empirical duration median")
for row in r['coverage']['missingness']:check(row['available']+row['unavailable']==925,f"{row['measure']} denominator")
check(sum(b['uploads'] for b in r['durationBands'])==881,'Positive-duration bands reconcile to measured uploads')
check(sum(b['captionPilotDocuments'] for b in r['durationBands'])==30,'Caption selected rows reconcile across duration bands')
shares=sorted([n for c,n in by.items() if c is not None],reverse=True);near(sum(shares[:10])/sum(shares),r['concentration']['top10Share'],'Top-ten share from raw account labels')
for key,condition in [('captionPilotKnownDuration',lambda v:v['id'] in caps),('otherIndexedKnownDuration',lambda v:v['id'] not in caps)]:
    x=[v['durationSeconds']/60 for v in vs if condition(v) and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    near(statistics.median(x),r['captionSelection'][key]['median'],key+' median');check(len(x)==r['captionSelection'][key]['n'],key+' count')
for topic in d['topics']:
    # Decode the serialized frozen regex exactly once; this check does not use analyzer helpers.
    pattern=topic['regex'].replace('\\\\','\\');rx=re.compile(pattern,re.I)
    eligible=[v for v in vs if v.get('titleEligible') and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    rows=[x for x in r['keywordByDuration'] if x['topicId']==topic['id']]
    check(sum(x['eligibleTitles'] for x in rows)==len(eligible),topic['id']+' title band denominator')
    check(sum(x['matches'] for x in rows)==sum(bool(rx.search(v['title'])) for v in eligible),topic['id']+' regex hits reconcile')
    for x in rows:near(x['share'],x['matches']/x['eligibleTitles'],topic['id']+' band share')
ca=np.load(ROOT/'dist/analysis/caption-embeddings.npz');ta=np.load(ROOT/'dist/analysis/title-embeddings.npz');cm={str(v):j for j,v in enumerate(ca['video_ids'])};tm={str(v):j for j,v in enumerate(ta['video_ids'])};ids=sorted(set(cm)&set(tm));labels={v['id']:v['channelId'] for v in vs};groups=collections.Counter(labels[v] for v in ids)
check(len(ids)==25 and len(groups)==14,'Matched document and publisher denominators')
for kind,archive,index in [('matchedCaption',ca,cm),('matchedTitle',ta,tm)]:
    x=np.array([archive['vectors'][index[v]] for v in ids]);x=x/np.linalg.norm(x,axis=1,keepdims=True);M=x@x.T
    within=[];between=[]
    for i in range(len(ids)):
        for j in range(i+1,len(ids)):(within if labels[ids[i]]==labels[ids[j]] else between).append(float(M[i,j]))
    got=r['embeddingWithinBetween'][kind];check(len(within)==got['within']['n'] and len(between)==got['between']['n'],kind+' independent pair counts')
    near(statistics.mean(within)-statistics.mean(between),got['meanDifference'],kind+' direct normalized-dot separation',1e-6)
    check(got['publishersWithWithinPairs']==sum(n>=2 for n in groups.values()),kind+' eligible within publisher counts')
    account_d=[]
    for c,n in groups.items():
        idx=[j for j,v in enumerate(ids) if labels[v]==c]
        if n<2:continue
        w=statistics.mean(float(M[i,j]) for i in idx for j in idx if i<j)
        b=statistics.mean(statistics.mean(float(M[i,j]) for i in idx for j,v in enumerate(ids) if labels[v]==other) for other in groups if other!=c)
        account_d.append(w-b)
    near(statistics.mean(account_d),got['accountBalanced']['meanDifference'],kind+' equal-account sensitivity',1e-6)
    check(len(got['permutationValues'])==2000,kind+' exact negative-control draws')
contrast=r['embeddingWithinBetween']['crossLayerContrast'];near(contrast['captionMinusTitlePooledMeanDifference'],r['embeddingWithinBetween']['matchedCaption']['meanDifference']-r['embeddingWithinBetween']['matchedTitle']['meanDifference'],'Cross-layer sign and magnitude')
manifest=json.loads((HERE/'generated/figure-captions.json').read_text())
for f in manifest:
    for ext,path in f['paths'].items():check((ROOT/path).exists() and (ROOT/path).stat().st_size>1000,f['id']+' '+ext+' export present')
out={'review':'Independent calculation reconciliation, not human construct validation','checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'snapshotSha256':r['source']['sha256'],'resultsSha256':hashlib.sha256((HERE/'results.json').read_bytes()).hexdigest(),'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','details':checks}
(HERE/'generated/verification.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='details'}));raise SystemExit(bool(out['failed']))
