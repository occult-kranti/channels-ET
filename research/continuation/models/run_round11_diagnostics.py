#!/usr/bin/env python3
"""Post-hoc refusal/overlap diagnostics and answer-present citation controls.

Original heldout metrics are never overwritten or relabeled as factual accuracy.
"""
import collections,json,pathlib,re,time
HERE=pathlib.Path(__file__).resolve().parent
REFUSAL=r"insufficient[\s_]+evidence|\bnot available\b|\bnot provided\b|\bcannot determine\b|\bcan't determine\b|\bdo not have\b|\bdon't have\b"
def words(s):return collections.Counter(re.findall(r'[a-z0-9]+',s.lower()))
def f1(a,b):
 x,y=words(a),words(b);return 2*sum((x&y).values())/(sum(x.values())+sum(y.values())) if x and y else 0.
def main():
 predictions=json.loads((HERE/'predictions.json').read_text())['records'];split=json.loads((HERE/'split.json').read_text());armwise=[]
 for arm in sorted({r['arm'] for r in predictions}):
  rows=[r for r in predictions if r['arm']==arm];cc=[r for r in rows if r['control']];qa=[r for r in rows if not r['control']]
  armwise.append({'arm':arm,'controlN':len(cc),'strictMarkerCount':sum(r['abstained'] for r in cc),
     'posthocRefusalPhraseCount':sum(bool(re.search(REFUSAL,r['output'],re.I)) for r in cc),
     'posthocRefusalPhraseRate':sum(bool(re.search(REFUSAL,r['output'],re.I)) for r in cc)/len(cc),
     'contentOnlyTokenF1':sum(f1(re.sub(r'\[D\d+\]','',r['output']),r['referenceAnswerGist']) for r in qa)/len(qa),
     'originalMeanTokenF1':sum(r['tokenF1ToHeldoutDigest'] for r in qa)/len(qa),
     'qaN':len(qa),'qaGenerationCapHits':sum(r['generatedTokens']==40 for r in qa),
     'qaWithAnyRetrievedEvidence':sum(bool(r['retrievedEvidence']) for r in qa)})
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import PeftModel
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
 tokenizer=AutoTokenizer.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False)
 model=AutoModelForCausalLM.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32,attn_implementation='eager');model.eval()
 selected=sorted(split['train'],key=lambda r:r['id'])[:2];controls=[]
 for arm in ['base_rag_positive_control','lora_rag_positive_control']:
  if arm.startswith('lora'):model=PeftModel.from_pretrained(model,'/workspace/channels-et-model-cache/lora-pilot');model.eval()
  for row in selected:
   prompt=tokenizer.apply_chat_template([{'role':'system','content':'Summarize only the supplied digest claim, without endorsing it. Include the source label [D1]. Answer in one short sentence.'},
    {'role':'user','content':'Question: '+row['question']+'\n[D1] '+row['answerGist']+'\nAnswer using [D1] only, and cite [D1].'}],tokenize=False,add_generation_prompt=True)
   inputs=tokenizer(prompt,return_tensors='pt');start=time.monotonic()
   with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=48,do_sample=False,pad_token_id=tokenizer.eos_token_id)
   output=tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
   r={'arm':arm,'candidateId':row['id'],'sourceGroupId':row['sourceGroupId'],'sourceUrl':row['sourceUrl'],
      'question':row['question'],'suppliedAnswerGist':row['answerGist'],'output':output,'seconds':time.monotonic()-start,
      'generatedTokens':out.shape[1]-inputs['input_ids'].shape[1],'validSourceLabelPresent':'[D1]' in output,
      'tokenF1ToSuppliedGist':f1(re.sub(r'\[D\d+\]','',output),row['answerGist']),
      'heldoutEvaluation':False,'controlType':'answer-present exact training-source query','entailmentHumanValidated':False}
   controls.append(r);print(json.dumps(r),flush=True)
 result={'status':'completed','classification':'post-hoc method diagnostic; primary benchmark metrics unchanged',
    'refusalPhrasePattern':REFUSAL,'refusalPatternDefinedAfterInspectingOutputs':True,
    'arms':armwise,'citationPositiveControls':controls,
    'unsupportedTemperatureExample':next(r for r in predictions if r['arm']=='qwen_lora_closed' and r['id']=='control-studio-temperature'),
    'limitations':['Refusal phrase detection is another lexical heuristic, not human intent/answer-quality annotation.',
     'Positive citation controls deliberately expose an exact training-source answer; they cannot estimate heldout generalization.',
     'Source-label membership does not establish entailment, factual accuracy or speaker authenticity.',
     'Content-only overlap removes citation tokens as a diagnostic; original benchmark scores remain unchanged.',
     'Unsupported23°C assertion is unsupported by this prompt/archive evidence, not a measured studio temperature.']}
 (HERE/'posthoc-diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
