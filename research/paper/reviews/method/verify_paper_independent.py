#!/usr/bin/env python3
"""Independent paper diagnostics; reads the frozen published feature data only."""
from pathlib import Path
import json, hashlib, math, statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
p=ROOT/'dist/analysis/data.json'; d=json.loads(p.read_text())

def rank(x):
 idx=sorted(range(len(x)),key=lambda i:x[i]);out=np.zeros(len(x));j=0
 while j<len(x):
  k=j+1
  while k<len(x) and x[idx[k]]==x[idx[j]]:k+=1
  for n in range(j,k):out[idx[n]]=(j+k-1)/2+1
  j=k
 return out

def mapping(s):return {tuple(sorted((v['a'],v['b']))):v['cosine'] for v in s['pairs']}
a=mapping(d['matchedTitleSimilarity']);b=mapping(d['matchedCaptionSimilarity']);keys=sorted(a.keys()&b.keys());groups=sorted({x for pair in keys for x in pair});rows=[]
for group in groups:
 kk=[k for k in keys if group not in k];rho=float(np.corrcoef(rank([a[k] for k in kk]),rank([b[k] for k in kk]))[0,1]);rows.append({'leftOutChannelId':group,'remainingAccounts':len(groups)-1,'pairCount':len(kk),'spearmanRankCorrelation':rho})
result={'inputSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reviewer':'/root/method_panel','method':'Independently rank exported rounded pair scores with average ties; remove each publisher and incident pairs, then correlate matched title/caption ranks. Descriptive influence only.','originalAccounts':len(groups),'originalPairs':len(keys),'originalRho':float(np.corrcoef(rank([a[k] for k in keys]),rank([b[k] for k in keys]))[0,1]),'minLopoRho':min(r['spearmanRankCorrelation'] for r in rows),'maxLopoRho':max(r['spearmanRankCorrelation'] for r in rows),'rows':rows}
out=Path(__file__).parent/'round4-lopo-independent.json';out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
assert result['originalAccounts']==11 and result['originalPairs']==55
assert all(r['remainingAccounts']==10 and r['pairCount']==45 for r in rows)
