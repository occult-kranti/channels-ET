#!/usr/bin/env python3
"""Independent downstream verification of the frozen round-5 pooling experiment.
Does not import pipeline functions or repeat raw-text neural inference.
"""
from pathlib import Path
import json, hashlib, csv
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
P=ROOT/'research/paper/rounds/round5'
G=P/'generated'
OUT=Path(__file__).resolve().parent
checks=[]
def check(name,truth):
 checks.append({'check':name,'pass':bool(truth)})
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ranks(values):
 order=sorted(range(len(values)),key=lambda i:values[i]);r=np.empty(len(values));start=0
 while start<len(values):
  stop=start+1
  while stop<len(values) and values[order[stop]]==values[order[start]]:stop+=1
  for k in range(start,stop):r[order[k]]=(start+stop+1)/2
  start=stop
 return r
base=json.loads((ROOT/'dist/analysis/data.json').read_text())
supplied=json.loads((G/'chunk-weighting.json').read_text())
vectors=np.load(G/'chunk-weighted-embeddings.npz')
frozen=np.load(ROOT/'dist/analysis/caption-embeddings.npz')
ids=vectors['video_ids'].tolist(); frozenids=frozen['video_ids'].tolist()
check('30 unique video IDs',len(ids)==30 and len(set(ids))==30)
check('same videos as published caption vectors',set(ids)==set(frozenids))
original=np.array([frozen['vectors'][frozenids.index(v)] for v in ids],dtype=float)
equal=np.array(vectors['equal_chunk_vectors'],dtype=float)
weighted=np.array(vectors['token_weighted_vectors'],dtype=float)
max_replay=float(np.max(np.abs(equal-original)))
check('equal-chunk replay agrees with published float32 archive',max_replay<1e-8)
check('both archives are finite 30x384 matrices',equal.shape==(30,384) and weighted.shape==(30,384) and np.isfinite(equal).all() and np.isfinite(weighted).all())
check('both vector sets have unit norm within float32 tolerance',np.allclose(np.linalg.norm(equal,axis=1),1,atol=2e-7) and np.allclose(np.linalg.norm(weighted,axis=1),1,atol=2e-7))
lookup={r['videoId']:r['channelId'] for r in base['transcripts']['rows']}
counts=Counter(lookup[v] for v in ids); groups=sorted(g for g,n in counts.items() if n>=2)
check('13 groups and 26 contributing documents',len(groups)==13 and sum(counts[g] for g in groups)==26)
def centroid_matrix(matrix):
 rows=[]
 for g in groups:
  z=matrix[[i for i,v in enumerate(ids) if lookup[v]==g]].mean(axis=0)
  rows.append(z/np.linalg.norm(z))
 rows=np.array(rows)
 return rows@rows.T
A=centroid_matrix(equal);B=centroid_matrix(weighted)
pairs=[(groups[i],groups[j],round(float(A[i,j]),6),round(float(B[i,j]),6)) for i in range(len(groups)) for j in range(i+1,len(groups))]
a=[x[2] for x in pairs];b=[x[3] for x in pairs];rho=float(np.corrcoef(ranks(a),ranks(b))[0,1])
check('78 unordered pairs',len(pairs)==78)
check('rho matches supplied value',abs(rho-supplied['rankCorrelation'])<1e-12)
fromcsv={tuple(sorted((r['a'],r['b']))):r for r in csv.DictReader((G/'chunk-weighting-pairs.csv').open(encoding='utf-8-sig'))}
check('CSV contains same complete pair set',set(fromcsv)=={(x[0],x[1]) for x in pairs})
for g,h,av,bv in pairs:
 row=fromcsv[g,h]
 check(f'pair baseline {g}/{h}',av==float(row['equalChunkCosine']))
 check(f'pair weighted {g}/{h}',bv==float(row['tokenWeightedCosine']))
 changes=[]
for i,g in enumerate(groups):
 aa=A[i].copy();bb=B[i].copy();aa[i]=-np.inf;bb[i]=-np.inf
 ga=groups[int(np.argmax(aa))];gb=groups[int(np.argmax(bb))]
 if ga!=gb:changes.append({'channelId':g,'equalChunkNeighbor':ga,'tokenWeightedNeighbor':gb})
check('two neighbor changes',len(changes)==2)
reported={x['channelId']:x for x in supplied['nearestNeighbors'] if x['changed']}
check('changed neighbor identities match',all(all(row[k]==reported[row['channelId']][k] for k in row) for row in changes) and set(reported)=={x['channelId'] for x in changes})
detail=supplied['documentsDetail'];check('chunk records cover all 30 IDs',set(x['videoId'] for x in detail)==set(ids) and len(detail)==30)
for row in detail:
 sizes=row['chunkSizes'];v=row['videoId']
 check(f'{v} chunk-count and length arithmetic',len(sizes)==row['chunks'] and sum(sizes)==row['contentWordpieces'] and all(x==240 for x in sizes[:-1]) and 1<=sizes[-1]<=240)
 check(f'{v} terminal chunk weights',sizes[-1]==row['tailContentWordpieces'] and abs(row['tailEqualWeight']-1/len(sizes))<1e-12 and abs(row['tailTokenWeight']-sizes[-1]/sum(sizes))<1e-12)
check('320 chunks and 73170 content wordpieces',sum(x['chunks'] for x in detail)==320 and sum(x['contentWordpieces'] for x in detail)==73170)
check('one single chunk record; 1 to 46 chunks',sum(x['chunks']==1 for x in detail)==1 and min(x['chunks'] for x in detail)==1 and max(x['chunks'] for x in detail)==46)
diffs=np.abs(np.array(a)-np.array(b))
check('mean and max absolute cosine changes match',abs(float(diffs.mean())-supplied['meanAbsoluteCosineChange'])<1e-12 and abs(float(diffs.max())-supplied['maxAbsoluteCosineChange'])<1e-12)
result={'round':5,'reviewer':'/root/method_panel','inputs':{str(p.relative_to(ROOT)):sha(p) for p in [P/'main.pdf',P/'body.tex',G/'paper-results.json',G/'chunk-weighting.json',G/'chunk-weighted-embeddings.npz',ROOT/'dist/analysis/data.json',ROOT/'dist/analysis/caption-embeddings.npz']},'method':'Independent arithmetic and centroids from stored video vectors, custom average-tie ranks on six-decimal pair cosines, direct nearest-neighbor reconstruction. No pipeline code imported. No raw-caption neural rerun.','results':{'documents':len(ids),'contributingDocuments':sum(counts[g] for g in groups),'publishers':len(groups),'pairs':len(pairs),'rankCorrelation':rho,'equalReplayFloat32MaxCoordinateDelta':max_replay,'equalReplayPreSerializationDeltaReportedByPipeline':supplied['equalChunkReplayMaxAbsoluteCoordinateDelta'],'meanAbsoluteCosineChange':float(diffs.mean()),'maxAbsoluteCosineChange':float(diffs.max()),'nearestNeighborChanges':changes},'checks':checks,'checkCount':len(checks),'failures':sum(not x['pass'] for x in checks),'limitation':'The stored float32 replay comparison establishes numerical equivalence of derivative archives; the more precise 7.4095e-9 pre-serialization delta is a pipeline replay receipt, not independently re-derived from raw text here.'}
(OUT/'round5-numeric-independent.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','inputs']},indent=2))
assert result['failures']==0
