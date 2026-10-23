#!/usr/bin/env python3
"""Independent audit of actual local Qwen/LoRA/RAG pilot predictions and scores."""
import collections,hashlib,json,pathlib,re,zipfile
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=ROOT/'research/continuation/models'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
split=json.loads((M/'split.json').read_text());pred=json.loads((M/'predictions.json').read_text())['records'];result=json.loads((M/'benchmark-results.json').read_text());training=json.loads((M/'training-receipt.json').read_text());train={r['id']:r for r in split['train']};test={r['id']:r for r in split['test']+split['controlRecords']};families={r['videoId']:r['sourceGroupId'] for r in json.loads((HERE/'generated/source-family-map.json').read_text())['records']};checks=[]
def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
def near(a,b,label,tol=5.1e-7):check(abs(a-b)<tol,label)
def score(a,b):
    x=collections.Counter(re.findall('[a-z0-9]+',a.lower()));y=collections.Counter(re.findall('[a-z0-9]+',b.lower()));shared=sum((x&y).values());return 2*shared/(sum(x.values())+sum(y.values())) if x and y else 0.
check(len(pred)==50,'Actual prediction denominator: five arms × ten prompts');check(not set(train)&set(test),'Train/test candidate IDs disjoint');check(not {families[r['videoId']] for r in train.values()}&{families[r['videoId']] for r in test.values() if r.get('videoId')},'Independently grouped source partitions disjoint')
tr=split['train'];V=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True);X=V.fit_transform([r['question'] for r in tr]);observed=[]
for arm in result['arms']:
    name=arm['id'];pp=[p for p in pred if p['arm']==name];check(len(pp)==10 and {p['id'] for p in pp}==set(test),name+' identical prompt cohort');qa=[p for p in pp if not p['control']];controls=[p for p in pp if p['control']];check(len(qa)==8 and len(controls)==2,name+' QA/control denominator')
    for p in pp:
        target=test[p['id']];check(p['question']==target['question'] and p['referenceAnswerGist']==target.get('answerGist'),name+'/'+p['id']+' source question/reference binding')
        abstain='INSUFFICIENT_EVIDENCE' in p['output'].upper();check(p['abstained']==abstain,name+'/'+p['id']+' explicit abstention score')
        if not p['control']:near(score(p['output'],p['referenceAnswerGist']),p['tokenF1ToHeldoutDigest'],name+'/'+p['id']+' independent token F1')
        supplied={d['label'] for d in p['retrievedEvidence']};cited=set(re.findall(r'\[(D\d+)\]',p['output']));check(p['validCitationPresent']==bool(cited&supplied) and p['invalidCitationPresent']==bool(cited-supplied),name+'/'+p['id']+' citation label membership')
        if p['citationTaskApplicable']:
            sim=(V.transform([p['question']])@X.T).toarray()[0];order=sorted(range(len(tr)),key=lambda i:(-sim[i],tr[i]['id']))[:2];expected=[tr[i]['id'] for i in order if sim[i]>=.1];check([d['candidateId'] for d in p['retrievedEvidence']]==expected,name+'/'+p['id']+' independently replayed train-only retrieval')
        for doc in p['retrievedEvidence']:
            check(doc['candidateId'] in train and doc['candidateId'] not in test,name+'/'+p['id']+' retrieved ID train-only')
            source=train[doc['candidateId']];check(doc['answerGist']==source['answerGist'] and doc['question']==source['question'],name+'/'+p['id']+' evidence text source binding')
            check(families[doc['videoId']] not in {families[t['videoId']] for t in test.values() if t.get('videoId')},name+'/'+p['id']+' retrieved family held-out exclusion')
        if not p['citationTaskApplicable']:check(not p['retrievedEvidence'],name+'/'+p['id']+' closed mode receives no supplied retrieval')
    f1=float(np.mean([score(p['output'],p['referenceAnswerGist']) for p in qa]));seconds=float(np.mean([p['seconds'] for p in pp]));abstained=sum('INSUFFICIENT_EVIDENCE' in p['output'].upper() for p in controls);near(f1,arm['meanTokenF1'],name+' aggregated F1');near(seconds,arm['meanSeconds'],name+' aggregated response wall time');near(abstained/len(controls),arm['abstentionRateOnControls'],name+' control abstention');cited=sum(p['validCitationPresent'] for p in qa);invalid=sum(p['invalidCitationPresent'] for p in qa)
    if arm['validCitationRate'] is not None:near(cited/len(qa),arm['validCitationRate'],name+' supplied-label rate');near(invalid/len(qa),arm['invalidCitationRate'],name+' invalid-label rate')
    observed.append({'id':name,'questions':len(qa),'controls':len(controls),'meanTokenF1':f1,'controlStrictMarkerOutputs':abstained,'heldoutStrictMarkerOutputs':sum(p['abstained'] for p in qa),'validCitationOutputs':cited if arm['validCitationRate'] is not None else None,'meanResponseSeconds':seconds,'perQuestionTokenF1':[{'id':p['id'],'score':score(p['output'],p['referenceAnswerGist'])} for p in qa]})
check(training['status']=='completed' and len(training['losses'])==48,'Actual 48 training microsteps completed');check(training['optimizerSteps']==12,'Actual twelve optimizer steps');check({p['candidateId'] for p in training['losses']}==set(train),'Training receipt uses selected train examples only');check(all(np.isfinite(p['loss']) for p in training['losses']),'Training losses finite');check(training['device']=='cpu' and training['gpuTraining']=='not_available_no_CUDA_device','Hardware limitation truthful')
package_path=M/'adapter-package.json'
if package_path.exists():
    package=json.loads(package_path.read_text());archive=M/package['archive'];check(archive.exists() and sha(archive)==package['sha256'],'Portable adapter archive exact hash')
    with zipfile.ZipFile(archive) as z:
        check(set(z.namelist())=={f['file'] for f in package['files']},'Portable adapter member set matches manifest')
        for f in package['files']:
            info=z.getinfo(f['file']);check(info.file_size==f['bytes'] and info.file_size<32*1024*1024,'Portable adapter bounded member size: '+f['file']);check(hashlib.sha256(z.read(f['file'])).hexdigest()==f['sha256'],'Portable adapter member hash: '+f['file'])
        expected=next(f for f in training['adapterFiles'] if f['name']=='adapter_model.safetensors')['sha256'];check(hashlib.sha256(z.read('adapter_model.safetensors')).hexdigest()==expected,'Portable adapter weights match executed training receipt')
else:
    for f in training['adapterFiles']:
        p=pathlib.Path(training['adapterPath'])/f['name'];check(p.exists() and sha(p)==f['sha256'],'Executed adapter artifact hash: '+f['name'])
out={'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','executionStatus':result['status'],'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'inputs':{f:sha(M/f) for f in ['split.json','predictions.json','benchmark-results.json','training-receipt.json','run_benchmark.py']},'model':result['model'],'controlOutputs':[{'arm':p['arm'],'id':p['id'],'output':p['output'],'strictMarkerPresent':p['abstained']} for p in pred if p['control']],'arms':observed,'training':{k:training[k] for k in ['device','examples','optimizerSteps','trainableParameters','trainingSeconds']},'interpretation':['These are eight held-out AI-digest reconstruction questions and two deliberately unsupported controls, not a model quality ranking.','Train-only RAG intentionally excludes the target source group and answer; this is sparse-source transfer, not an ordinary answer-present RAG comparison.','Token F1 measures lexical overlap. Supplied-label membership does not establish entailment or factual correctness.','Control counts require the literal INSUFFICIENT_EVIDENCE marker. A spaced refusal such as Insufficient evidence. scores zero; this is formatting compliance, not general refusal accuracy.','The 40-new-token generation cap and 192-token training cap can affect lexical scores; length and citation-normalized sensitivities remain separate checks.','Observed split quarantine does not rule out pretrained-model contamination or unknown source-session overlap.','One LoRA closed control output invents an exact studio temperature (23°C); this is a concrete unsupported response, not inferred from lexical scores.']}
if package_path.exists():
    out['inputs']['adapter-package.json']=sha(package_path);out['inputs'][package['archive']]=sha(archive)
    out['adapterVerification']='Portable archive/member hashes verified; adapter weight bytes match the original training receipt. Package README/config normalization is described by its separate manifest. No external model cache is required for this audit.'
(HERE/'benchmark-audit.json').write_text(json.dumps(out,indent=2));main=json.loads((HERE/'results.json').read_text());main['benchmarkAudit']=out;(HERE/'results.json').write_text(json.dumps(main,ensure_ascii=False,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in out.items() if k not in ['arms','inputs','interpretation','controlOutputs']}));raise SystemExit(out['status']!='PASS')
