#!/usr/bin/env python3
"""Independent source joins, lexical grouping, conditioning and benchmark split audit."""
import collections,hashlib,json,pathlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import rankdata
from sklearn.feature_extraction.text import TfidfVectorizer
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2];r=json.loads((HERE/'results.json').read_text());rows=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records'];checks=[]
def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
def near(a,b,label,tol=1e-7):check(abs(a-b)<tol,label)
for key,path in [('metadataSha256','dist/analysis/data.json'),('qaCandidatesSha256','research/expansion/qa/qa-candidates.json'),('captionEmbeddingsSha256','dist/analysis/caption-embeddings.npz'),('titleEmbeddingsSha256','dist/analysis/title-embeddings.npz')]:check(r['source'][key]==hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'Pinned source '+key)
q=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform([p['question'] for p in rows]);a=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform([p['answerGist'] for p in rows]);QM=(q@q.T).toarray();AM=(a@a.T).toarray();i,j=np.triu_indices(len(rows),1);keep=np.array([rows[x]['videoId']!=rows[y]['videoId'] for x,y in zip(i,j)]);i,j=i[keep],j[keep];qc=QM[i,j];ac=AM[i,j];check(len(i)==r['questionAnswerAlignment']['allDistinctUploadCandidatePairs'],'All distinct-upload pair count')
selected=json.loads((HERE/'generated/question-neighbor-pairs.json').read_text());ix={x['id']:k for k,x in enumerate(rows)};expected={(rows[x]['id'],rows[y]['id']) for x,y,v in zip(i,j,qc) if v>=.4};check(expected=={(p['leftId'],p['rightId']) for p in selected},'All and only question-neighbor pairs retained')
for p in selected:
    x,y=ix[p['leftId']],ix[p['rightId']];near(QM[x,y],p['questionCosine'],p['leftId']+'/'+p['rightId']+' question score');near(AM[x,y],p['answerCosine'],p['leftId']+'/'+p['rightId']+' answer score')
for g in r['lexicalGraph']['thresholdRows']:
    mask=qc>=g['minimumQuestionCosine'];matrix=coo_matrix((np.ones(int(mask.sum())),(i[mask],j[mask])),shape=(len(rows),len(rows)));components,labels=connected_components(matrix,directed=False);sizes=collections.Counter(labels)
    check(int(mask.sum())==g['edges'] and components==g['connectedComponents'],'Graph edges/components '+str(g['minimumQuestionCosine']));check(max(sizes.values())==g['largestComponentCandidates'],'Graph largest component '+str(g['minimumQuestionCosine']));check(sum(n for n in sizes.values() if n>1)==g['linkedCandidates'],'Graph linked nodes '+str(g['minimumQuestionCosine']))
guard=r['lexicalGraph']['benchmarkGuard'];groups=guard['groups'];mapping={v:g['groupId'] for g in groups for v in g['videoIds']};check(len(mapping)==67 and len(groups)==55,'Quarantine group partition denominator');cross=np.array([mapping[rows[x]['videoId']]!=mapping[rows[y]['videoId']] for x,y in zip(i,j)]);check(int(np.sum((qc>=.4)&cross))==r['questionAnswerAlignment']['crossQuarantineNeighborPairs'],'Cross-quarantine neighbor count');near(float(ac[(qc>=.4)&cross].mean()),r['questionAnswerAlignment']['crossQuarantineNeighborAnswerCosine']['mean'],'Cross-quarantine answer mean')
near(float(ac[qc>=.4].mean()),r['questionAnswerAlignment']['neighborAnswerCosine']['mean'],'Original all-neighbor mean preserved')
support=r['questionAnswerAlignment'].get('commonSupportStandardization')
if support:
    common=[]
    for b in support['bins']:
        idx=(qc>=b['lowerInclusive'])&(qc<b['upperExclusive']);w=idx&~cross;c=idx&cross;check(int(w.sum())==b['withinPairs'] and int(c.sum())==b['crossPairs'],'Common-support bin source counts '+b['label']);shared=bool(w.any() and c.any());check(shared==b['commonSupport'],'Common-support eligibility '+b['label'])
        if shared:common.append((b,w,c))
        else:check(b['crossMeanAnswerCosine'] is None and b['standardizationWeight'] is None,'Unsupported bin remains null '+b['label'])
    denominator=sum(int((w|c).sum()) for b,w,c in common);within=0.;between=0.
    for b,w,c in common:
        weight=float((w|c).sum()/denominator);near(weight,b['standardizationWeight'],'Common-support shared pooled weight '+b['label']);near(float(ac[w].mean()),b['withinMeanAnswerCosine'],'Common-support within mean '+b['label']);near(float(ac[c].mean()),b['crossMeanAnswerCosine'],'Common-support cross mean '+b['label']);within+=weight*ac[w].mean();between+=weight*ac[c].mean()
    check(denominator==support['includedNeighborPairs'] and len(selected)-denominator==support['excludedNeighborPairs'],'Common-support retained/excluded denominator');near(within,support['standardizedWithinMean'],'Common-support standardized within mean');near(between,support['standardizedCrossMean'],'Common-support standardized cross mean');near(within-between,support['standardizedWithinMinusCross'],'Common-support contrast');check(support['positiveAdvantageDisconfirmed']==(within<=between),'Common-support disconfirming direction reported')
cap=np.load(ROOT/'dist/analysis/caption-embeddings.npz');title=np.load(ROOT/'dist/analysis/title-embeddings.npz');cm={str(v):n for n,v in enumerate(cap['video_ids'])};tm={str(v):n for n,v in enumerate(title['video_ids'])};metadata={v['id']:v for v in json.loads((ROOT/'dist/analysis/data.json').read_text())['videos']};pairrows=r['representationNuisance']['pairRows'];check(len(pairrows)==300,'Matched pair count')
for p in pairrows:
    av,bv=p['leftVideoId'],p['rightVideoId']
    for k,ar,mp in [('captionCosine',cap,cm),('titleCosine',title,tm)]:
        avc=ar['vectors'][mp[av]].astype(float);bvc=ar['vectors'][mp[bv]].astype(float);near(float(avc@bvc/np.linalg.norm(avc)/np.linalg.norm(bvc)),p[k],av+'/'+bv+' '+k,2e-6)
    near(abs(np.log(metadata[av]['durationSeconds']/metadata[bv]['durationSeconds'])),p['absoluteLogDurationRatio'],av+'/'+bv+' duration join')
controls=np.column_stack([np.ones(len(pairrows))]+[rankdata([p[k] for p in pairrows]) for k in r['representationNuisance']['controls']]);res=[]
for k in ['titleCosine','captionCosine']:
    v=rankdata([p[k] for p in pairrows]);res.append(v-controls@np.linalg.pinv(controls)@v)
near(float(np.corrcoef(*res)[0,1]),r['representationNuisance']['partialRankCorrelation'],'Independent pseudoinverse partial rank')
split_path=ROOT/'research/continuation/models/split.json';split_audit={'status':'not_available'}
if split_path.exists():
    split=json.loads(split_path.read_text());train,test=split['train'],split['test'];tx={p['id'] for p in train};vx={p['id'] for p in test};check(not tx&vx,'Model train/test candidate disjoint');check(not {p['videoId'] for p in train}&{p['videoId'] for p in test},'Model train/test upload disjoint');check(not {mapping[p['videoId']] for p in train}&{mapping[p['videoId']] for p in test},'Independent quarantine groups disjoint across model split')
    modelpartition={frozenset(v for v,g in split['videoGroupMap'].items() if g==key) for key in set(split['videoGroupMap'].values())};ours={frozenset(g['videoIds']) for g in groups};check(modelpartition==ours,'Independently reconstructed model quarantine partition');check(split['sourceQaSha256']==r['source']['qaCandidatesSha256'],'Model split source hash')
    for p in train+test:check(p['question']==rows[ix[p['id']]]['question'] and p['answerGist']==rows[ix[p['id']]]['answerGist'],'Model example source binding '+p['id'])
    split_audit={'status':'PASS' if all(c['passed'] for c in checks[-(len(train)+len(test)+5):]) else 'FAIL','splitSha256':hashlib.sha256(split_path.read_bytes()).hexdigest(),'trainExamples':len(train),'testQuestions':len(test),'sourceGroups':len(groups),'trainGroups':len({mapping[p['videoId']] for p in train}),'testGroups':len({mapping[p['videoId']] for p in test}),'ragScope':'Training examples only according to inspected executable benchmark code; actual prediction evidence will be checked when available.','limits':['Grouping uses observed question similarities and cannot rule out unknown original-session or pretrained-model contamination.','One selected question per eight held-out groups is a tiny pilot, not reliable generalization or semantic validation.']}
audit_path=HERE/'benchmark-audit.json'
if audit_path.exists():
    audit=json.loads(audit_path.read_text());check(audit['status']=='PASS','Independent actual model audit passes')
    for f,h in audit['inputs'].items():check(hashlib.sha256((ROOT/'research/continuation/models'/f).read_bytes()).hexdigest()==h,'Actual model audit input '+f)
    split_audit['ragScope']='Train-only retrieval independently replayed for every actual applicable prediction in audit_benchmark.py; no held-out evidence IDs or quarantine groups supplied.'
diagnostics_path=HERE/'model-diagnostics-audit.json'
if diagnostics_path.exists():
    audit=json.loads(diagnostics_path.read_text());check(audit['status']=='PASS','Independent model diagnostics audit passes')
    for f,h in audit['inputs'].items():check(hashlib.sha256((ROOT/'research/continuation/models'/f).read_bytes()).hexdigest()==h,'Actual model diagnostic input '+f)
prompt_path=HERE/'prompt-sensitivity-audit.json'
if prompt_path.exists():
    audit=json.loads(prompt_path.read_text());check(audit['status']=='PASS','Independent prompt and current-family audit passes')
    for f,h in audit['inputs'].items():check(hashlib.sha256((ROOT/'research/continuation/models'/f).read_bytes()).hexdigest()==h,'Prompt/current-family input '+f)
manifest=json.loads((HERE/'generated/figure-captions.json').read_text())
for f in manifest:
    for ext,p in f['paths'].items():check((ROOT/p).exists() and (ROOT/p).stat().st_size>1000,f['id']+' '+ext+' present')
out={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'resultsSha256':hashlib.sha256((HERE/'results.json').read_bytes()).hexdigest(),'modelSplitAudit':split_audit,'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','details':checks};(HERE/'generated/verification.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='details'}));raise SystemExit(out['status']!='PASS')
