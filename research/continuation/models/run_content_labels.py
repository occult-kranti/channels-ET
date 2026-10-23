#!/usr/bin/env python3
"""Local-Qwen content labels compared with dictionary indicators, never accuracy."""
import collections,hashlib,json,pathlib,random,re,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def main():
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
 rows=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records'];split=json.loads((HERE/'split.json').read_text());groups=split['videoGroupMap']
 selected=[];used=set();rng=random.Random(42)
 for wanted in [True,False]:
  pool=[r for r in rows if ('conditional' in r['answerModalityMarkers'])==wanted];pool.sort(key=lambda r:r['id']);rng.shuffle(pool);count=0
  for r in pool:
   g=groups[r['videoId']]
   if g in used:continue
   selected.append({**r,'sourceGroupId':g});used.add(g);count+=1
   if count==6:break
 assert len(selected)==12
 prompt_definition={'task':'Primary answer orientation and conditional wording from supplied digest text',
  'primaryThemes':['contact_forecast','personal_practice','cosmology','other','unclear'],
  'conditionalLabels':['yes','no','unclear'],
  'selection':'Fixed seed42, six dictionary-conditional and six dictionary-nonconditional examples, all12 from distinct conservative source-proxy groups; purposive balanced method comparison',
  'humanLabels':False,'truthLabels':False,'source':'AI-generated digest paraphrases only'}
 (HERE/'content-label-protocol.json').write_text(json.dumps({**prompt_definition,'selectedIds':[r['id'] for r in selected]},indent=2)+'\n')
 tokenizer=AutoTokenizer.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False)
 model=AutoModelForCausalLM.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32,attn_implementation='eager');model.eval()
 system='Read only the supplied digest excerpt. Classify the primary answer theme as contact_forecast, personal_practice, cosmology, other, or unclear. Classify conditional wording as yes, no, or unclear. Return JSON only with keys theme, conditional, evidence. Evidence must be an exact substring of the answer, at most eight words. These are reported claims, not verified facts.'
 outputs=[]
 for row in selected:
  text=tokenizer.apply_chat_template([{'role':'system','content':system},{'role':'user','content':'Question: '+row['question']+'\nAnswer gist: '+row['answerGist']}],tokenize=False,add_generation_prompt=True)
  encoded=tokenizer(text,return_tensors='pt');start=time.monotonic()
  with torch.inference_mode():out=model.generate(**encoded,max_new_tokens=96,do_sample=False,pad_token_id=tokenizer.eos_token_id)
  raw=tokenizer.decode(out[0,encoded['input_ids'].shape[1]:],skip_special_tokens=True);seconds=time.monotonic()-start
  parsed=None;error=None
  try:
   match=re.search(r'\{.*\}',raw,re.S);parsed=json.loads(match.group(0) if match else raw)
   if parsed.get('theme') not in prompt_definition['primaryThemes'] or parsed.get('conditional') not in prompt_definition['conditionalLabels'] or not isinstance(parsed.get('evidence'),str):raise ValueError('Invalid label/schema')
  except Exception as e:error=type(e).__name__+': '+str(e)[:150];parsed=None
  exact=bool(parsed and parsed['evidence'] and parsed['evidence'] in row['answerGist'] and len(parsed['evidence'].split())<=8)
  reference='yes' if 'conditional' in row['answerModalityMarkers'] else 'no'
  themes=set(row['answerThemes']);dictionary=set()
  if themes&{'contact','prediction'}:dictionary.add('contact_forecast')
  if themes&{'excitement','belief','practice'}:dictionary.add('personal_practice')
  if 'consciousness' in themes:dictionary.add('cosmology')
  if not dictionary:dictionary.add('other')
  r={'id':row['id'],'videoId':row['videoId'],'sourceGroupId':row['sourceGroupId'],'sourceUrl':row['sourceUrl'],'sourceSha256':row['sourceSha256'],'sourcePointer':row['sourcePointer'],
     'question':row['question'],'answerGist':row['answerGist'],'rawModelOutput':raw,'parsed':parsed,'parseError':error,'seconds':round(seconds,6),
     'dictionaryConditional':reference,'dictionaryThemeIndicators':sorted(dictionary),'conditionalMethodAgreement':parsed['conditional']==reference if parsed else None,
     'primaryThemeMatchesAnyDictionaryIndicator':parsed['theme'] in dictionary if parsed else None,'evidenceSpanExactAndShort':exact,
     'generatedTokens':out.shape[1]-encoded['input_ids'].shape[1],'evidenceType':'local_model_annotation_of_AI_digest','humanReviewed':False}
  outputs.append(r);print(json.dumps({'id':r['id'],'parsed':parsed,'spanValid':exact,'seconds':r['seconds']}),flush=True)
 valid=[r for r in outputs if r['parsed']];summary={'status':'completed','model':'Qwen/Qwen2.5-0.5B-Instruct','revision':'7ae557604adf67be50417f59c2c2f167def9a775','adapterUsed':False,
  **prompt_definition,'n':len(outputs),'parsedRecords':len(valid),'parseFailures':len(outputs)-len(valid),
  'conditionalMethodAgreementCount':sum(r['conditionalMethodAgreement'] is True for r in outputs),
  'conditionalMethodAgreementDenominator':len(valid),'conditionalMethodAgreementRate':sum(r['conditionalMethodAgreement'] is True for r in outputs)/len(valid) if valid else None,
  'primaryThemeDictionaryConcordanceCount':sum(r['primaryThemeMatchesAnyDictionaryIndicator'] is True for r in outputs),
  'sourceSpanExactAndShortCount':sum(r['evidenceSpanExactAndShort'] for r in outputs),'sourceSpanEvaluableRecords':len(valid),
  'sourceSpanInvalidParsedCount':sum(not r['evidenceSpanExactAndShort'] for r in valid),
  'conditionalLabelCounts':dict(collections.Counter(r['parsed']['conditional'] for r in valid)),
  'unknownConditionalCount':sum(r['parsed']['conditional']=='unclear' for r in valid),
  'meanSeconds':sum(r['seconds'] for r in outputs)/len(outputs),
  'themeCounts':dict(collections.Counter(r['parsed']['theme'] for r in valid)),
  'limitations':['Method concordance is not human annotation accuracy or factual correctness.','Balanced12-example selection is purposive, not representative corpus prevalence.','Primary-theme labels are forced single labels; dictionary categories overlap.','Invalid or unsupported evidence spans are retained as failures, not silently corrected.','No original speech, turn boundaries or entity authenticity were validated.']}
 (HERE/'content-label-predictions.json').write_text(json.dumps({'records':outputs},ensure_ascii=False,indent=2)+'\n')
 (HERE/'content-label-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
