#!/usr/bin/env python3
"""Bounded CPU Qwen/LoRA and train-only retrieval reconstruction pilot.

Targets are pre-existing AI digest paraphrases, not human or factual ground truth.
"""
from __future__ import annotations
import collections, hashlib, importlib.metadata, json, os, pathlib, random, re, resource, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=pathlib.Path('/workspace/channels-et-model-cache/qwen2.5-0.5b')
ADAPTER=pathlib.Path('/workspace/channels-et-model-cache/lora-pilot')
SYSTEM="You summarize claims in a channeling archive, without endorsing them. Keep answers under 40 words. If evidence is insufficient say INSUFFICIENT_EVIDENCE."
def write(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def normalize(s):return ' '.join(re.findall(r'[a-z0-9]+',s.lower()))
def tokens(s):return re.findall(r'[a-z0-9]+',s.lower())
def f1(a,b):
 a,b=collections.Counter(tokens(a)),collections.Counter(tokens(b));shared=sum((a&b).values())
 return 2*shared/(sum(a.values())+sum(b.values())) if a and b else 0.0
def make_split():
 rows=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records']
 pairs=json.loads((ROOT/'research/expansion/qa/question-pairs.json').read_text())['records']
 parent={r['videoId']:r['videoId'] for r in rows}
 def find(x):
  while parent[x]!=x:x=parent[x]
  return x
 counts=collections.Counter(tuple(sorted((p['leftVideoId'],p['rightVideoId']))) for p in pairs)
 for p in pairs:
  if p['sameNormalizedQuestion'] or p['questionCosine']>=.8 or counts[tuple(sorted((p['leftVideoId'],p['rightVideoId'])))]>=3:
   a,b=find(p['leftVideoId']),find(p['rightVideoId']);parent[max(a,b)]=min(a,b)
 groups=collections.defaultdict(list)
 for r in rows:groups[find(r['videoId'])].append(r)
 rng=random.Random(42);keys=sorted(groups);rng.shuffle(keys)
 test_groups=keys[:8];train_groups=keys[8:]
 test=[sorted(groups[g],key=lambda r:r['id'])[0] for g in test_groups]
 train=[]
 # Two rounds over source families keep the 48-example pilot dispersed.
 for offset in range(2):
  for g in train_groups:
   choices=sorted(groups[g],key=lambda r:r['id'])
   if offset<len(choices):train.append(choices[offset])
   if len(train)==48:break
  if len(train)==48:break
 controls=[{'id':'control-studio-temperature','question':'What exact room temperature in Celsius was measured in the recording studio during this session?','answerGist':None,'videoId':None,'control':True},
           {'id':'control-unpublished-hash','question':'What is the SHA-256 digest of the unpublished original audio master for this session?','answerGist':None,'videoId':None,'control':True}]
 result={'seed':42,'sourceQaSha256':hashlib.sha256((ROOT/'research/expansion/qa/qa-candidates.json').read_bytes()).hexdigest(),
   'sourceScope':'949 inherited AI digest pairs; Darryl Anka/Bashar context only',
   'groupRule':'Union upload IDs if any exact normalized question, any question cosine>=0.80, or >=3 cross-upload retrieval pairs at cosine>=0.40; conservative proxy, not known original sessions',
   'groupCount':len(groups),'trainExamples':len(train),'testQuestions':len(test),'controls':len(controls),
   'trainGroupIds':sorted(set(find(r['videoId']) for r in train)),'testGroupIds':test_groups,
   'train':[{**r,'sourceGroupId':find(r['videoId'])} for r in train],
   'test':[{**r,'sourceGroupId':find(r['videoId'])} for r in test], 'controlRecords':controls,
   'videoGroupMap':{v:find(v) for v in sorted(parent)},
   'ragCorpus':'training examples only; no heldout question or answer provided as RAG evidence'}
 assert not set(result['trainGroupIds'])&set(result['testGroupIds'])
 assert not {r['videoId'] for r in train}&{r['videoId'] for r in test}
 assert not {normalize(r['question']) for r in train}&{normalize(r['question']) for r in test}
 write('split.json',result);return result

def main():
 import numpy as np,torch
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import LoraConfig,get_peft_model
 from sklearn.feature_extraction.text import TfidfVectorizer
 from sklearn.metrics.pairwise import cosine_similarity
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42);np.random.seed(42);random.seed(42)
 hardware={'device':'cpu','torchThreads':torch.get_num_threads(),'cudaAvailable':torch.cuda.is_available(),
           'logicalCpus':os.cpu_count(),'cpuQuota':pathlib.Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
           'memoryLimit':pathlib.Path('/sys/fs/cgroup/memory.max').read_text().strip(),
           'versions':{p:importlib.metadata.version(p) for p in ['torch','transformers','peft','accelerate','numpy','scikit-learn']}}
 write('hardware.json',hardware);split=make_split();train,test=split['train'],split['test']+split['controlRecords']
 write('run-status.json',{'status':'loading_verified_local_model','hardware':hardware})
 tokenizer=AutoTokenizer.from_pretrained(str(CACHE),local_files_only=True,trust_remote_code=False)
 model=AutoModelForCausalLM.from_pretrained(str(CACHE),local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32,attn_implementation='eager')
 model.config.use_cache=True;tokenizer.pad_token=tokenizer.eos_token
 vector=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True,norm='l2')
 matrix=vector.fit_transform([r['question'] for r in train])
 predictions=[]
 def retrieve(q):
  sim=cosine_similarity(vector.transform([q]),matrix)[0];order=sorted(range(len(train)),key=lambda i:(-sim[i],train[i]['id']))[:2]
  return [{'label':f'D{rank+1}','candidateId':train[i]['id'],'videoId':train[i]['videoId'],'sourceGroupId':train[i]['sourceGroupId'],
           'sourceUrl':train[i]['sourceUrl'],'question':train[i]['question'],'answerGist':train[i]['answerGist'],'cosine':round(float(sim[i]),6)}
          for rank,i in enumerate(order) if sim[i]>=.10]
 def prompt(q,evidence=None):
  user='Question: '+q
  if evidence is not None:
   user+='\nUse only the following supplied evidence. Cite an evidence label such as [D1]. If it does not answer the question, say INSUFFICIENT_EVIDENCE.\n'
   user+='\n'.join('['+d['label']+'] Q: '+d['question']+' A: '+d['answerGist'] for d in evidence) if evidence else 'NO EVIDENCE AVAILABLE.'
  return tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':user}],tokenize=False,add_generation_prompt=True)
 def predict(arm,row,mode):
  start=time.monotonic();evidence=retrieve(row['question']) if mode in ['rag','lexical'] else []
  retrieval_seconds=time.monotonic()-start;generated=0;prompt_tokens=None;prompt_truncated=False
  if mode=='lexical':
   answer=evidence[0]['answerGist']+' [D1]' if evidence else 'INSUFFICIENT_EVIDENCE'
  else:
   p=prompt(row['question'],evidence if mode=='rag' else None)
   original_tokens=len(tokenizer(p)['input_ids']);prompt_truncated=original_tokens>512
   inputs=tokenizer(p,return_tensors='pt',truncation=True,max_length=512)
   prompt_tokens=inputs['input_ids'].shape[1]
   with torch.inference_mode():
    output=model.generate(**inputs,max_new_tokens=40,do_sample=False,pad_token_id=tokenizer.eos_token_id)
   generated=output.shape[1]-inputs['input_ids'].shape[1]
   answer=tokenizer.decode(output[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
  seconds=time.monotonic()-start;cited=re.findall(r'\[(D\d+)\]',answer);valid={e['label'] for e in evidence} if mode in ['rag','lexical'] else set()
  r={'arm':arm,'id':row['id'],'question':row['question'],'control':row.get('control',False),
     'referenceAnswerGist':row.get('answerGist'),'referenceSourceId':row.get('id'),'referenceVideoId':row.get('videoId'),
     'output':answer,'seconds':round(seconds,6),'generatedTokens':generated,'retrievedEvidence':evidence if mode in ['rag','lexical'] else [],
     'retrievalSeconds':round(retrieval_seconds,6),
     'promptTokens':prompt_tokens,'promptTruncated':prompt_truncated,
     'tokenF1ToHeldoutDigest':None if row.get('control') else round(f1(answer,row['answerGist']),6),
     'abstained':'INSUFFICIENT_EVIDENCE' in answer.upper(),
     'citedLabels':cited,'validCitationPresent':bool(set(cited)&valid),'invalidCitationPresent':bool(set(cited)-valid),
     'citationTaskApplicable':mode in ['rag','lexical'],'groundTruthType':'AI digest paraphrase reconstruction; not verified truth'}
  predictions.append(r)
  with (HERE/'predictions.jsonl').open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
  print(json.dumps({'arm':arm,'id':row['id'],'seconds':round(seconds,2),'tokenF1':r['tokenF1ToHeldoutDigest'],'abstained':r['abstained']}),flush=True)
  return r
 # The immutable base is evaluated before adapter training on the same model.
 (HERE/'predictions.jsonl').write_text('')
 for arm,mode in [('lexical_retrieval','lexical'),('qwen_base_closed','closed'),('qwen_base_rag','rag')]:
  model.eval()
  for row in test:predict(arm,row,mode)
 write('run-status.json',{'status':'training_cpu_lora','basePredictionsComplete':30})
 config=LoraConfig(r=4,lora_alpha=8,lora_dropout=0.0,target_modules=['q_proj','v_proj'],bias='none',task_type='CAUSAL_LM')
 model=get_peft_model(model,config);model.config.use_cache=False;model.train()
 params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=2e-4)
 training=[];start=time.monotonic();optimizer.zero_grad();active=0
 for step,row in enumerate(train):
  prefix=prompt(row['question']);target='The digest states: '+row['answerGist']+tokenizer.eos_token
  a=tokenizer(prefix,add_special_tokens=False)['input_ids'];b=tokenizer(target,add_special_tokens=False)['input_ids']
  ids=(a+b)[:192];labels=([-100]*len(a)+b)[:192]
  if all(x==-100 for x in labels):raise ValueError('Training sequence truncates all answer tokens')
  tensor=torch.tensor([ids]);label=torch.tensor([labels]);out=model(input_ids=tensor,attention_mask=torch.ones_like(tensor),labels=label)
  loss=out.loss;assert torch.isfinite(loss);(loss/4).backward();active+=1
  if active%4==0 or step==len(train)-1:optimizer.step();optimizer.zero_grad()
  training.append({'microstep':step+1,'candidateId':row['id'],'sourceGroupId':row['sourceGroupId'],'tokens':len(ids),'loss':round(float(loss.detach()),6)})
  if (step+1)%4==0:print(json.dumps({'trainingMicrostep':step+1,'loss':training[-1]['loss'],'elapsed':round(time.monotonic()-start,2)}),flush=True)
 training_seconds=time.monotonic()-start;ADAPTER.mkdir(parents=True,exist_ok=True);model.save_pretrained(str(ADAPTER),safe_serialization=True)
 receipt={'status':'completed','device':'cpu','examples':len(train),'epochs':1,'microsteps':active,'optimizerSteps':(active+3)//4,
          'sequenceMaxTokens':192,'gradientAccumulation':4,'learningRate':2e-4,'seed':42,'loraRank':4,'loraAlpha':8,'targetModules':['q_proj','v_proj'],
          'trainableParameters':sum(p.numel() for p in params),'totalParameters':sum(p.numel() for p in model.parameters()),
          'trainingSeconds':round(training_seconds,3),'peakProcessRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'losses':training,'adapterPath':str(ADAPTER),'adapterFiles':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(ADAPTER.iterdir()) if p.is_file()],
          'gpuTraining':'not_available_no_CUDA_device','comparisonLimit':'No GPU vs CPU timing comparison was executed'}
 write('training-receipt.json',receipt)
 model.config.use_cache=True;model.eval()
 for arm,mode in [('qwen_lora_closed','closed'),('qwen_lora_rag','rag')]:
  for row in test:predict(arm,row,mode)
 arms=[]
 for name in ['lexical_retrieval','qwen_base_closed','qwen_base_rag','qwen_lora_closed','qwen_lora_rag']:
  rr=[r for r in predictions if r['arm']==name];qa=[r for r in rr if not r['control']];controls=[r for r in rr if r['control']]
  arms.append({'id':name,'kind':'lexical' if name=='lexical_retrieval' else 'local_language_model','n':len(qa),'controlN':len(controls),
    'meanTokenF1':round(sum(r['tokenF1ToHeldoutDigest'] for r in qa)/len(qa),6),'meanSeconds':round(sum(r['seconds'] for r in rr)/len(rr),6),
    'validCitationRate':round(sum(r['validCitationPresent'] for r in qa)/len(qa),6) if any(r['citationTaskApplicable'] for r in qa) else None,
    'invalidCitationRate':round(sum(r['invalidCitationPresent'] for r in qa)/len(qa),6) if any(r['citationTaskApplicable'] for r in qa) else None,
    'abstentionRateOnControls':sum(r['abstained'] for r in controls)/len(controls),
    'abstentionRateOnHeldoutQuestions':sum(r['abstained'] for r in qa)/len(qa)})
 manifest=json.loads((HERE/'model-manifest.json').read_text())
 result={'status':'completed','model':{'id':manifest['model'],'revision':manifest['revision'],'license':manifest['license'],'parameterScale':'0.5B family; bounded CPU baseline, not established state of the art'},
         'hardware':hardware,'split':{k:v for k,v in split.items() if k not in ['train','test','controlRecords','videoGroupMap']},
         'arms':arms,'training':{k:v for k,v in receipt.items() if k not in ['losses','adapterFiles']},
         'generation':{'maxNewTokens':40,'doSample':False,'promptMaxTokens':512,'dtype':'float32'},
         'metrics':{'meanTokenF1':'Multiset alphanumeric-token overlap with heldout AI digest gist; lexical reconstruction, not factual correctness',
                    'validCitationRate':'Fraction of heldout outputs naming at least one supplied evidence label; ID membership only, not entailment',
                    'meanSeconds':'Wall time per response including query retrieval when used, prompt tokenization and generation; excludes one-time model loading/index fitting',
                    'abstentionRateOnControls':'Fraction of two unanswerable studio-temperature/audio-hash probes explicitly emitting INSUFFICIENT_EVIDENCE'},
         'limitations':['Eight heldout questions and two controls are a pilot, not a reliable comparative ranking.',
            'All training and reference targets are model-generated digest paraphrases from one practitioner context.',
            'Proxy source families reduce known question/repost leakage but cannot establish independent original sessions.',
            'RAG searches only the 48 training examples; retrieval evidence may not answer a heldout question.',
            'Token overlap and source-label membership do not validate semantic agreement, provenance entailment or factual truth.',
            'One short CPU LoRA epoch is an adaptation smoke test, not an optimized fine-tuning study.',
            'CUDA/GPU comparison is unavailable; CPU latency includes this shared machine and short outputs.',
            'No human construct labels, speech transcription or new multi-practitioner answers were created.']}
 write('predictions.json',{'records':predictions});write('benchmark-results.json',result);write('run-status.json',{'status':'completed','predictions':len(predictions),'trainingSeconds':receipt['trainingSeconds']})
 print(json.dumps({'status':'completed','arms':arms,'trainingSeconds':training_seconds}),flush=True)
if __name__=='__main__':main()
