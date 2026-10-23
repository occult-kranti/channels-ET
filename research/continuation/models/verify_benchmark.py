#!/usr/bin/env python3
"""Audit executed output/source splits and deterministic metric bookkeeping."""
import argparse,collections,hashlib,importlib.util,json,math,pathlib,re,zipfile
HERE=pathlib.Path(__file__).resolve().parent
def words(s):return collections.Counter(re.findall(r'[a-z0-9]+',s.lower()))
def overlap(a,b):
 x,y=words(a),words(b);return 2*sum((x&y).values())/(sum(x.values())+sum(y.values())) if x and y else 0.
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true',help='Verify released outputs/adapter ZIP only; explicitly skip external tokenizer cache')
 options=parser.parse_args()
 split=json.loads((HERE/'split.json').read_text());result=json.loads((HERE/'benchmark-results.json').read_text());rr=json.loads((HERE/'predictions.json').read_text())['records'];training=json.loads((HERE/'training-receipt.json').read_text());checks=0
 def check(ok,message):
  nonlocal checks
  checks+=1
  if not ok:raise AssertionError(message)
 train={x['id']:x for x in split['train']};test={x['id']:x for x in split['test']};controls={x['id']:x for x in split['controlRecords']}
 check(not set(train)&set(test),'Disjoint example IDs')
 check(not {x['videoId'] for x in train.values()}&{x['videoId'] for x in test.values()},'Disjoint upload IDs')
 check(not {x['sourceGroupId'] for x in train.values()}&{x['sourceGroupId'] for x in test.values()},'Disjoint source-proxy groups')
 check(len(rr)==50,'Five arms each execute eight questions and two controls')
 check(training['status']=='completed' and training['examples']==48 and training['microsteps']==48 and training['optimizerSteps']==12,'Actual bounded CPU LoRA steps completed')
 check(len(training['losses'])==48 and all(math.isfinite(x['loss']) for x in training['losses']),'Finite actual training losses')
 check(0<training['trainableParameters']<training['totalParameters']*.01,'Small trainable LoRA subset')
 for p in rr:
  check(p['id'] in test or p['id'] in controls,'Predicted heldout/control IDs only')
  check(all(d['candidateId'] in train for d in p['retrievedEvidence']),'RAG evidence drawn from training only')
  check(not {d['candidateId'] for d in p['retrievedEvidence']}&set(test),'No heldout answer in evidence')
  check(p['seconds']>=0 and p['generatedTokens']<=40,'Recorded timing and generation bounds')
  if not p['control']:check(abs(overlap(p['output'],p['referenceAnswerGist'])-p['tokenF1ToHeldoutDigest'])<.000001,'Independently recomputed token F1')
 for arm in result['arms']:
  rows=[x for x in rr if x['arm']==arm['id']];qa=[x for x in rows if not x['control']];cc=[x for x in rows if x['control']]
  check(len(qa)==8 and len(cc)==2,'Every arm has the same evaluation denominator')
  check(abs(sum(x['tokenF1ToHeldoutDigest'] for x in qa)/8-arm['meanTokenF1'])<.000001,'Mean token overlap agrees')
  check(abs(sum(x['seconds'] for x in rows)/10-arm['meanSeconds'])<.000001,'Mean response timing agrees')
  check(sum(x['abstained'] for x in cc)/2==arm['abstentionRateOnControls'],'Control abstention agrees')
 source_sha=hashlib.sha256((HERE/'run_benchmark.py').read_bytes()).hexdigest()
 package=json.loads((HERE/'adapter-package.json').read_text());archive=HERE/package['archive']
 check(hashlib.sha256(archive.read_bytes()).hexdigest()==package['sha256'],'Released adapter ZIP hash')
 with zipfile.ZipFile(archive) as zipped:
  for file in package['files']:check(hashlib.sha256(zipped.read(file['file'])).hexdigest()==file['sha256'],'Released adapter member hash')
  sources=json.loads(zipped.read('training-source-manifest.json'))
  trained_weight=next(f for f in training['adapterFiles'] if f['name']=='adapter_model.safetensors')
  check(hashlib.sha256(zipped.read('adapter_model.safetensors')).hexdigest()==trained_weight['sha256'],'Released matrix equals actual trained adapter')
  check(json.loads(zipped.read('training-manifest.json'))=={k:v for k,v in training.items() if k not in ['adapterPath','adapterFiles']},'Released training receipt equals recorded run')
  check(sources['sourceQaSha256']==split['sourceQaSha256'],'Adapter training source hash')
  check(sources['splitSha256']==hashlib.sha256((HERE/'split.json').read_bytes()).hexdigest(),'Adapter split hash')
  check(sources['protocolSha256']==hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),'Adapter protocol hash')
  check(sources['train']==[{'candidateId':r['id'],'sourcePath':r['sourcePath'],'sourceSha256':r['sourceSha256'],'sourcePointer':r['sourcePointer']} for r in split['train']],'All 48 adapter source pointers')
 cache=pathlib.Path('/workspace/channels-et-model-cache/qwen2.5-0.5b')
 can_tokenize=not options.offline and (cache/'tokenizer.json').exists() and importlib.util.find_spec('transformers') is not None
 if can_tokenize:
  from transformers import AutoTokenizer
  from run_benchmark import SYSTEM
  tokenizer=AutoTokenizer.from_pretrained(str(cache),local_files_only=True,trust_remote_code=False);truncations=[]
  for row,loss in zip(split['train'],training['losses']):
   prompt=tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':'Question: '+row['question']}],tokenize=False,add_generation_prompt=True)
   prefix=tokenizer(prompt,add_special_tokens=False)['input_ids'];target=tokenizer('The digest states: '+row['answerGist']+tokenizer.eos_token,add_special_tokens=False)['input_ids']
   used=max(0,min(len(target),192-len(prefix)))
   check(loss['tokens']==min(192,len(prefix)+len(target)),'Recorded training cap matches exact prompt/target tokenization')
   truncations.append({'candidateId':row['id'],'prefixTokens':len(prefix),'answerTokensAvailable':len(target),'answerTokensUsed':used,'answerTruncated':used<len(target)})
  tokenizer_audit={'state':'executed','records':len(truncations),'externalCacheRequired':True}
 else:
  length=json.loads((HERE/'length-audit.json').read_text());truncations=length['trainingRecords']
  check(len(truncations)==48,'Retained length-audit record count (not recomputed tokenization)')
  tokenizer_audit={'state':'skipped','reason':'--offline requested' if options.offline else 'External tokenizer cache or Transformers unavailable',
                   'retainedLengthAuditSha256':hashlib.sha256((HERE/'length-audit.json').read_bytes()).hexdigest(),
                   'recordsFromRetainedAudit':len(truncations),'tokenizationRecomputed':False}
 caps={a['id']:{'generationCapHits':sum(p['generatedTokens']==40 for p in rr if p['arm']==a['id']),
                 'promptTruncations':sum(p.get('promptTruncated',False) for p in rr if p['arm']==a['id'])} for a in result['arms']}
 length={'trainingAnswerTruncatedCount':sum(x['answerTruncated'] for x in truncations),'trainingRecords':truncations,'generationCapsByArm':caps,
         'interpretation':'System requests under 40 words, but generation is limited to 40 tokens; cap hits and training truncation can lower lexical overlap. Neither is an accuracy measure.'}
 if can_tokenize:(HERE/'length-audit.json').write_text(json.dumps(length,indent=2)+'\n')
 receipt={'status':'PASS','checks':checks,'runSourceSha256':source_sha,'predictionsSha256':hashlib.sha256((HERE/'predictions.json').read_bytes()).hexdigest(),
          'benchmarkResultsSha256':hashlib.sha256((HERE/'benchmark-results.json').read_bytes()).hexdigest(),'trainingReceiptSha256':hashlib.sha256((HERE/'training-receipt.json').read_bytes()).hexdigest(),
          'trainingAnswerTruncatedCount':length['trainingAnswerTruncatedCount'],'generationCapsByArm':caps,'factualAccuracyValidated':False,'humanGroundTruth':False,
          'tokenizerAudit':tokenizer_audit,'adapterVerification':'released ZIP/member hashes, source pointers and split/protocol hashes',
          'neuralInferenceReplayed':False,'modelWeightsRequiredForThisCheck':False}
 output='verification.json' if can_tokenize else 'verification-offline.json'
 (HERE/output).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
