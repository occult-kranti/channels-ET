import json,hashlib,math,statistics,collections,sys
from pathlib import Path
import numpy as np
base=Path('/workspace/sites/channeling-atlas/dist/analysis');p=base/'data.json';d=json.loads(p.read_text());issues=[];checks=0

def check(x,msg):
 global checks
 checks+=1
 if not x:issues.append(msg)

def ranks(xs):
 order=sorted(range(len(xs)),key=lambda i:xs[i]);r=[0.0]*len(xs);j=0
 while j<len(order):
  k=j+1
  while k<len(order) and xs[order[k]]==xs[order[j]]:k+=1
  for q in range(j,k):r[order[q]]=(j+k-1)/2+1
  j=k
 return np.array(r)
def pdict(s):return {tuple(sorted([p['a'],p['b']])):p['cosine'] for p in s['pairs']}
comparisons=[('rawVsMaskedTitles',d['titleRawSimilarity'],d['semanticSimilarity']),('deduplicatedVsAllTitles',d['deduplicatedTitleSimilarity'],d['semanticSimilarity']),('captionFullVsTrimmed',d['transcripts']['similarity'],d['transcripts']['trimmedSimilarity']),('matchedTitleVsCaption',d['matchedTitleSimilarity'],d['matchedCaptionSimilarity'])]
summary={}
for key,a,b in comparisons:
 x=pdict(a);y=pdict(b);keys=sorted(x.keys()&y.keys());u=[x[k] for k in keys];v=[y[k] for k in keys];cor=float(np.corrcoef(ranks(u),ranks(v))[0,1]);delta=statistics.median(abs(x-y) for x,y in zip(u,v));obs=d['diagnostics'][key]
 check(len(keys)==obs['pairCount'],key+'pairs');check(abs(cor-obs['spearmanRankCorrelation'])<1e-9,key+'rankcorr');check(abs(delta-obs['medianAbsoluteCosineChange'])<1e-9,key+'delta');summary[key]={'pairs':len(keys),'rankCorrelation':cor,'medianAbsDelta':delta}
t=np.load(base/'title-embeddings.npz');c=np.load(base/'caption-embeddings.npz');ti={v:i for i,v in enumerate(t['video_ids'])};ci={v:i for i,v in enumerate(c['video_ids'])};common=sorted(ti.keys()&ci.keys());vmap={v['id']:v for v in d['videos']};check(len(common)==d['diagnostics']['matchedVideoCount'],'matchedVideoCount')
for key,z,ids in [('matchedTitleSimilarity',t,ti),('matchedCaptionSimilarity',c,ci)]:
 s=d[key];grp=collections.defaultdict(list)
 for vid in common:grp[vmap[vid]['channelId']].append(z['vectors'][ids[vid]])
 check(set(s['channelIds'])=={ch for ch,vv in grp.items() if len(vv)>=2},key+'eligiblegroups')
 for ch in s['channelIds']:
  vec=np.mean(grp[ch],axis=0);vec/=np.linalg.norm(vec);check(np.allclose(vec,s['channelVectors'][ch],atol=2e-6),key+'centroid'+ch)
# Independently reconstruct within/between document pair counts and distributions.
capmap={r['videoId']:r for r in d['transcripts']['rows']};vv=c['vectors'];w=[];b=[]
for i in range(len(vv)):
 for j in range(i+1,len(vv)):
  val=float(vv[i]@vv[j]);(w if capmap[str(c['video_ids'][i])]['channelId']==capmap[str(c['video_ids'][j])]['channelId'] else b).append(val)
for key,vals in [('within',w),('between',b)]:
 obs=d['diagnostics']['captionWithinBetween'][key];check(len(vals)==obs['nPairs'],key+'paircounts');check(abs(statistics.median(vals)-obs['median'])<1e-7,key+'median');check(np.allclose(sorted(vals),sorted(obs['values']),atol=1e-7),key+'pairvalues')
a=d['transcripts']['similarity'];b=d['transcripts']['trimmedSimilarity'];changed=0
for ch in a['channelIds']:
 n=[]
 for s in [a,b]:
  p=max((p for p in s['pairs'] if ch in (p['a'],p['b'])),key=lambda p:p['cosine']);n.append(p['a'] if p['b']==ch else p['b'])
 changed+=n[0]!=n[1]
summary['captionTrimNeighborChanges']={'changed':changed,'accounts':len(a['channelIds'])}
r={'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest() if isinstance(p,Path) else hashlib.sha256((base/'data.json').read_bytes()).hexdigest(),'checks':checks,'issues':issues,'status':'PASS' if not issues else 'FAIL','summary':summary,'matched_videos':len(common),'matched_accounts':len(d['matchedTitleSimilarity']['channelIds'])}
Path('/workspace/scratch/9ec421627a96/analysis_work/panel/final-robustness-review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));sys.exit(bool(issues))
