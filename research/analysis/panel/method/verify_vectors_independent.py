import json,math,hashlib,sys,collections
from pathlib import Path
import numpy as np
base=Path('/workspace/sites/channeling-atlas/dist/analysis');d=json.loads((base/'data.json').read_text());vmap={v['id']:v for v in d['videos']};issues=[];checks=0

def check(b,msg):
 global checks
 checks+=1
 if not b:issues.append(msg)

runs=[('titles',base/'title-embeddings.npz',d['semanticSimilarity'],'vectors',vmap),('captions',base/'caption-embeddings.npz',d['transcripts']['similarity'],'vectors',{r['videoId']:r for r in d['transcripts']['rows']}),('trimmed_captions',base/'caption-embeddings.npz',d['transcripts']['trimmedSimilarity'],'trimmed_vectors',{r['videoId']:r for r in d['transcripts']['rows']})]
summary=[]
for name,p,s,key,mapping in runs:
 z=np.load(p);ids=z['video_ids'].tolist();a=z[key];check(a.shape==(len(ids),384),name+'384Dshape');check(len(ids)==len(set(ids)),name+'uniqueIDs');check(np.isfinite(a).all(),name+'finite');check(np.allclose(np.linalg.norm(a,axis=1),1,atol=1e-5),name+'unitnorm');check(all(x in mapping for x in ids),name+'resolvingIDs')
 grouped=collections.defaultdict(list)
 for i,vid in enumerate(ids):
  r=mapping[vid];grouped[r['channelId']].append(a[i])
  if name=='titles':check(r.get('titleEligible') is True and r.get('channelId') is not None,name+'eligible '+vid)
 for ch in s['channelIds']:
  m=np.mean(grouped[ch],axis=0);m/=np.linalg.norm(m)
  observed=np.array(s['channelVectors'][ch]);check(np.allclose(m,observed,atol=2e-6),name+'centroid '+ch)
 cm=np.array([s['channelVectors'][c] for c in s['channelIds']]);expected=cm@cm.T;actual=np.array(s['matrix']);check(np.allclose(actual,expected,atol=2e-6),name+'cosines');check(np.allclose(actual,actual.T),name+'symmetric');check(np.allclose(np.diag(actual),1,atol=2e-6),name+'diagonal');check(np.max(actual)<=1.000002 and np.min(actual)>=-1.000002,name+'range');check(len(s['pairs'])==len(s['channelIds'])*(len(s['channelIds'])-1)//2,name+'paircount')
 summary.append({'name':name,'documents':len(ids),'accounts_compared':len(s['channelIds']),'dims':a.shape[1]})
r={'reviewer':'/root/method_panel','input_sha256':hashlib.sha256((base/'data.json').read_bytes()).hexdigest(),'checks':checks,'issues':issues,'summary':summary,'status':'PASS' if not issues else 'FAIL'}
Path('/workspace/scratch/9ec421627a96/analysis_work/panel/vector-review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));sys.exit(bool(issues))
