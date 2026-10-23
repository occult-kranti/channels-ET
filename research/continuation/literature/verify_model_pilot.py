#!/usr/bin/env python3
"""Independent arithmetic/split/adapter audit of saved pilot outputs; no inference."""
import argparse,collections,hashlib,json,math,pathlib,re,statistics,struct,zipfile
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=ROOT/'research/continuation/models';checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(ok,label,a=None,b=None):checks.append({'check':label,'passed':bool(ok),'actual':a,'expected':b})
def eq(a,b,label,tol=1e-6):
 ck(math.isclose(a,b,abs_tol=tol,rel_tol=tol) if isinstance(a,(int,float)) and isinstance(b,(int,float)) else a==b,label,a,b)
def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',s.lower()))
def f1(a,b):
 x=collections.Counter(norm(a).split());y=collections.Counter(norm(b).split());n=sum((x&y).values());return 2*n/(sum(x.values())+sum(y.values())) if x and y else 0
pred=json.loads((M/'predictions.json').read_text())['records'];sp=json.loads((M/'split.json').read_text());result=json.loads((M/'benchmark-results.json').read_text());tr=json.loads((M/'training-receipt.json').read_text());original={x['id']:x for x in json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records']};families=sp['videoGroupMap'];train=sp['train'];test=sp['test'];trainids={x['id'] for x in train};testids={x['id'] for x in test}
eq(len(train),48,'48 adaptation examples');eq(len(test),8,'8 heldout questions');eq(len(pred),50,'5arms*10outputs')
ck(not trainids&testids,'candidate ID partitions disjoint');ck(not {x['videoId'] for x in train}&{x['videoId'] for x in test},'upload partitions disjoint');ck(not {x['sourceGroupId'] for x in train}&{x['sourceGroupId'] for x in test},'proxy-family partitions disjoint');ck(not {norm(x['question']) for x in train}&{norm(x['question']) for x in test},'normalized questions disjoint')
# Independently rebuild upload-proxy connected components from raw released pairs.
pairs=json.loads((ROOT/'research/expansion/qa/question-pairs.json').read_text())['records'];adj=collections.defaultdict(set);counts=collections.Counter(tuple(sorted((p['leftVideoId'],p['rightVideoId']))) for p in pairs)
for p in pairs:
 if p['sameNormalizedQuestion'] or p['questionCosine']>=.8 or counts[tuple(sorted((p['leftVideoId'],p['rightVideoId'])))]>=3:
  a,b=p['leftVideoId'],p['rightVideoId'];adj[a].add(b);adj[b].add(a)
seen=set();labels={}
for vid in sorted({x['videoId'] for x in original.values()}):
 if vid in seen:continue
 todo=[vid];group=set()
 while todo:
  cur=todo.pop()
  if cur in group:continue
  group.add(cur);todo.extend(adj[cur]-group)
 seen|=group
 for member in group:labels[member]=min(group)
eq(labels,families,'proxy graph independently reconstructed')
for row in train+test:
 eq(row['question'],original[row['id']]['question'],'original sourcequestion '+row['id']);eq(row['answerGist'],original[row['id']]['answerGist'],'original referencegist '+row['id'])
cap=[]
for p in pred:
 if not p['control']:eq(p['tokenF1ToHeldoutDigest'],f1(p['output'],p['referenceAnswerGist']),'savedF1 '+p['arm']+' '+p['id'])
 eq(p['abstained'],'INSUFFICIENT_EVIDENCE' in p['output'].upper(),'strictmarker '+p['arm']+' '+p['id'])
 cited=re.findall(r'\[(D\d+)\]',p['output']);valid={e['label'] for e in p['retrievedEvidence']};eq(p['validCitationPresent'],bool(set(cited)&valid),'citationID membership '+p['arm']+' '+p['id'])
 ck(all(e['candidateId'] in trainids and e['candidateId'] not in testids for e in p['retrievedEvidence']),'trainonly retrieved IDs '+p['arm']+' '+p['id'])
 if p['arm']!='lexical_retrieval':ck(p['generatedTokens']<=40 and p['promptTokens']<=512,'tokenlimits '+p['arm']+' '+p['id'])
 if p['generatedTokens']==40:cap.append({'arm':p['arm'],'id':p['id']})
for arm in result['arms']:
 rr=[p for p in pred if p['arm']==arm['id']];qa=[p for p in rr if not p['control']];controls=[p for p in rr if p['control']];eq(arm['n'],len(qa),'armdenominator '+arm['id']);eq(arm['controlN'],len(controls),'controldenominator '+arm['id']);eq(arm['meanTokenF1'],statistics.mean(f1(p['output'],p['referenceAnswerGist']) for p in qa),'armmeanF1 '+arm['id']);eq(arm['meanSeconds'],statistics.mean(p['seconds'] for p in rr),'armlatency '+arm['id']);eq(arm['abstentionRateOnControls'],sum(p['abstained'] for p in controls)/len(controls),'armstrictcontrol '+arm['id'])
eq(tr['microsteps'],len(tr['losses']),'actualtraininglossrecords');eq(tr['optimizerSteps'],math.ceil(tr['microsteps']/tr['gradientAccumulation']),'optimizerupdatecount');ck(all(math.isfinite(x['loss']) for x in tr['losses']),'alltraininglossfinite');eq(tr['trainableParameters'],270336,'rank4qvtrainables');eq(tr['trainableParameters']/tr['totalParameters'],270336/494303104,'trainablefraction')
# Inspect actual saved safe-tensor B matrices; LoRA initializes B=0 by default.
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adapter-path',type=pathlib.Path,default=M/'adapter-export/adapter_model.safetensors');args=parser.parse_args();adapter=args.adapter_path
package=M/'qwen-digest-lora-pilot.zip';packmeta=json.loads((M/'adapter-package.json').read_text());expected=next(x for x in packmeta['files'] if x['file']=='adapter_model.safetensors')
if adapter.is_file():data=adapter.read_bytes();route='raw_adapter_file'
else:
 with zipfile.ZipFile(package) as archive:data=archive.read('adapter_model.safetensors')
 route='packaged_zip_member_fallback'
ck(hashlib.sha256(data).hexdigest()==expected['sha256'],'adapter bytes equal packaged source manifest');ck(len(data)==expected['bytes'],'adapter byte count matches packaged source manifest');ck(sha(package)==packmeta['sha256'],'adapter ZIP sha matches package manifest')
adapter_source={'route':route,'requested_raw_path':str(adapter),'raw_path_exists':adapter.exists(),'package':str(package.relative_to(ROOT)),'package_sha256':sha(package),'member':'adapter_model.safetensors','member_sha256':hashlib.sha256(data).hexdigest(),'member_bytes':len(data)}
headerlen=struct.unpack('<Q',data[:8])[0];header=json.loads(data[8:8+headerlen]);bs=[]
for name,item in header.items():
 if '.lora_B.' not in name:continue
 start,end=item['data_offsets'];dtype={'F32':'<f4','F16':'<f2'}[item['dtype']];a=np.frombuffer(data[8+headerlen+start:8+headerlen+end],dtype=dtype);bs.append({'name':name,'elements':len(a),'nonzero':int(np.count_nonzero(a)),'finite':bool(np.all(np.isfinite(a)))})
ck(bool(bs) and all(x['nonzero']>0 and x['finite'] for x in bs),'savedLoRA Bmatrices nonzero finite (defaultzero-init adaptation evidence)')
failed=[x for x in checks if not x['passed']];report={'round':11,'status':'PASS' if not failed else 'FAIL','checks':len(checks),'failures':failed,'network_or_inference_runs':0,'input_sha256':{p.name:sha(p) for p in [M/'predictions.json',M/'split.json',M/'benchmark-results.json',M/'training-receipt.json']},'capHits':cap,'adapterSource':adapter_source,'adapterBmatrices':bs,'limitations':['Saved-output verification does not establish heldoutsource answerability,semantic entailment,humanquality or trueclaims.','Group thresholds depend on question similarity; groups are sourceproxies,not verified recordingfamilies.','Lexical copiedanswers have no40token generationcap,so length/access confound comparisons.','Exactmarker and suppliedcitationID compliance are narrow operational measures.','Base pretraining contamination remains unknown.'],'all_checks':checks};(HERE/'independent-model-pilot.json').write_text(json.dumps(report,indent=2,default=str));print(json.dumps({'status':report['status'],'checks':len(checks),'failures':failed,'capHits':cap},indent=2));raise SystemExit(bool(failed))
