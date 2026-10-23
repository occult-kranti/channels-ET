#!/usr/bin/env python3
"""Independent explicit TF-IDF and shared-question-support verification."""
import collections,hashlib,json,math,pathlib,re,statistics
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
H=pathlib.Path(__file__).resolve().parent;R=H.parents[2];A=R/'research/continuation/analysis';rows=json.loads((R/'research/expansion/qa/qa-candidates.json').read_text())['records'];pairs=json.loads((A/'generated/question-neighbor-pairs.json').read_text());result=json.loads((A/'results.json').read_text());checks=[]
def ck(ok,label,a=None,b=None):checks.append({'check':label,'passed':bool(ok),'actual':a,'expected':b})
def eq(a,b,label):ck(a==b if a is None or b is None or not isinstance(a,(int,float)) else abs(a-b)<1e-7,label,a,b)
def mat(texts):
 docs=[];df=collections.Counter()
 for t in texts:
  w=[x for x in re.findall(r'(?u)\b\w\w+\b',t.lower()) if x not in ENGLISH_STOP_WORDS];c=collections.Counter(w+[' '.join(z) for z in zip(w,w[1:])]);docs.append(c);df.update(c.keys())
 vocab={w:i for i,w in enumerate(sorted(df))};ri=[];ci=[];v=[]
 for i,c in enumerate(docs):
  ws={w:(1+math.log(f))*(1+math.log((1+len(docs))/(1+df[w]))) for w,f in c.items()};n=math.sqrt(sum(x*x for x in ws.values()))
  for w,x in ws.items():ri.append(i);ci.append(vocab[w]);v.append(x/n if n else 0)
 return csr_matrix((v,(ri,ci)),shape=(len(docs),len(vocab)))
Q=mat([r['question'] for r in rows]);B=mat([r['answerGist'] for r in rows]);ids={x['id']:i for i,x in enumerate(rows)};mapping=json.loads((R/'research/continuation/models/split.json').read_text())['videoGroupMap'];calc=[]
for p in pairs:
 i,j=ids[p['leftId']],ids[p['rightId']];q=float(Q[i].multiply(Q[j]).sum());a=float(B[i].multiply(B[j]).sum());same=mapping[p['leftVideoId']]==mapping[p['rightVideoId']];eq(p['questionCosine'],q,'questiondot '+p['leftId']+' '+p['rightId']);eq(p['answerCosine'],a,'answerdot '+p['leftId']+' '+p['rightId']);eq(p['sameQuarantineGroup'],same,'groupjoin '+p['leftId']+' '+p['rightId']);calc.append((q,a,same))
x=result['questionAnswerAlignment'];eq(len(calc),127,'neighborpool127');eq(x['neighborAnswerCosine']['mean'],statistics.mean(a for q,a,s in calc),'allneighboranswermean');eq(x['crossQuarantineNeighborAnswerCosine']['mean'],statistics.mean(a for q,a,s in calc if not s),'crossneighboranswermean')
y=x['commonSupportStandardization'];shared=[]
for b in y['bins']:
 v=[(q,a,s) for q,a,s in calc if b['lowerInclusive']<=q<b['upperExclusive']];w=[a for q,a,s in v if s];c=[a for q,a,s in v if not s];both=bool(w and c);eq(b['withinPairs'],len(w),'binwithincount '+b['label']);eq(b['crossPairs'],len(c),'bincrosscount '+b['label']);eq(b['withinMeanAnswerCosine'],statistics.mean(w) if w else None,'binwithinmean '+b['label']);eq(b['crossMeanAnswerCosine'],statistics.mean(c) if c else None,'bincrossmean '+b['label']);eq(b['commonSupport'],both,'binsupport '+b['label'])
 if both:shared.append((len(v),statistics.mean(w),statistics.mean(c)))
n=sum(v[0] for v in shared);sw=sum(k/n*a for k,a,b in shared);sc=sum(k/n*b for k,a,b in shared);eq(y['includedNeighborPairs'],n,'sharedpoolsize');eq(y['excludedNeighborPairs'],len(calc)-n,'excludedpoolsize');eq(y['standardizedWithinMean'],sw,'standardizedwithin');eq(y['standardizedCrossMean'],sc,'standardizedcross');eq(y['standardizedWithinMinusCross'],sw-sc,'standardizedgap');ck(all(b['crossPairs']==0 and not b['commonSupport'] for b in y['bins'] if b['lowerInclusive']>=.7),'highquestionbinslackcrosssupport')
fail=[c for c in checks if not c['passed']];report={'round':11,'status':'PASS' if not fail else 'FAIL','checks':len(checks),'failures':fail,'results_sha256':hashlib.sha256((A/'results.json').read_bytes()).hexdigest(),'pairsha256':hashlib.sha256((A/'generated/question-neighbor-pairs.json').read_bytes()).hexdigest(),'method':'Explicit counts/smoothIDF/sublinearTF/L2 and direct sparse dot; no producer/vectorizer import. Recomputed group bin weighting.','decisive':{'all_neighbor_mean':statistics.mean(a for q,a,s in calc),'cross_group_mean':statistics.mean(a for q,a,s in calc if not s),'shared_pairs':n,'standardized_within':sw,'standardized_cross':sc,'standardized_gap':sw-sc},'limitations':['Question-defined groupselection remains noncausal; coarsening cannot remove allwithin-bin variation.','93sharedsupportpairs differ from original127; highsimilaritybins have nocrossgroupstratum.','No semantic agreement,humanvalidity or proven originalsessionreuse inferred.'],'all_checks':checks};(H/'independent-alignment-control.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['status','checks','failures','decisive']},indent=2));raise SystemExit(bool(fail))
