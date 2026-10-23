#!/usr/bin/env python3
"""Same-excerpt theme-option reversal and separate lexical codebook sensitivity."""
import ast,collections,hashlib,json,pathlib,re,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD_ORDER='contact_forecast, personal_practice, cosmology, other, or unclear'
NEW_ORDER='unclear, other, cosmology, personal_practice, or contact_forecast'
STRICT_CONDITIONAL=r'\b(?:if|unless|depends?|depending|provided|as long as)\b'
def main():
 originals=json.loads((HERE/'content-label-predictions.json').read_text())['records'];assert len(originals)==12
 tree=ast.parse((HERE/'run_content_labels.py').read_text())
 systems=[node.value.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='system' for t in node.targets) and isinstance(node.value,ast.Constant)]
 assert len(systems)==1;original_system=systems[0];assert original_system.count(OLD_ORDER)==1
 reversed_system=original_system.replace(OLD_ORDER,NEW_ORDER)
 source_rows=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records']
 codebook=json.loads((ROOT/'research/expansion/qa/codebook.json').read_text())
 old_regex=next(x['regex'] for x in codebook['modality'] if x['id']=='conditional')
 sensitivity=[]
 for row in source_rows:
  old='conditional' in row['answerModalityMarkers'];assert old==bool(re.search(old_regex,row['answerGist'],re.I))
  new=bool(re.search(STRICT_CONDITIONAL,row['answerGist'],re.I))
  if old!=new:sensitivity.append({'id':row['id'],'sourceUrl':row['sourceUrl'],'sourceSha256':row['sourceSha256'],'sourcePointer':row['sourcePointer'],
    'answerGist':row['answerGist'],'originalConditionalIndicator':old,'stricterConditionalIndicator':new})
 lexical={'classification':'Post-hoc lexicon sensitivity after inspecting dependency false positive; not human validation',
   'sourceQaSha256':hashlib.sha256((ROOT/'research/expansion/qa/qa-candidates.json').read_bytes()).hexdigest(),
   'originalRegex':old_regex,'stricterRegex':STRICT_CONDITIONAL,'n':len(source_rows),
   'originalConditionalCount':sum('conditional' in r['answerModalityMarkers'] for r in source_rows),
   'stricterConditionalCount':sum(bool(re.search(STRICT_CONDITIONAL,r['answerGist'],re.I)) for r in source_rows),
   'changedCount':len(sensitivity),'changedRecords':sensitivity,
   'limitations':['The narrower rule excludes dependency/dependence forms but remains an unvalidated lexical indicator.',
     'Words such as provided can be nonconditional; neither rule establishes actual uncertainty, intent or factual truth.',
     'The original codebook, selection and benchmark labels remain unchanged.']}
 (HERE/'conditional-lexicon-sensitivity.json').write_text(json.dumps(lexical,ensure_ascii=False,indent=2)+'\n')
 protocol={'stage':'exploratory prompt sensitivity, specified before reversed-order generations','model':'Qwen/Qwen2.5-0.5B-Instruct',
   'revision':'7ae557604adf67be50417f59c2c2f167def9a775','selectedIds':[r['id'] for r in originals],
   'originalThemeOrder':['contact_forecast','personal_practice','cosmology','other','unclear'],
   'reversedThemeOrder':['unclear','other','cosmology','personal_practice','contact_forecast'],
   'originalSystemPrompt':original_system,'reversedSystemPrompt':reversed_system,
   'originalPredictionsSha256':hashlib.sha256((HERE/'content-label-predictions.json').read_bytes()).hexdigest(),
   'onlyPromptDifference':'Theme option order; conditional options, labels, evidence request and all excerpts unchanged',
   'hypothesis':'If the collapse follows the first offered label, reversal should favor unclear; persistence of contact_forecast would not support that simple position-only account.',
   'generation':{'maxNewTokens':96,'doSample':False,'torchThreads':2,'seed':42,'dtype':'float32'},
   'humanGroundTruth':False,'originalOutputsOverwritten':False}
 (HERE/'option-order-protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
 tokenizer=AutoTokenizer.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False)
 model=AutoModelForCausalLM.from_pretrained('/workspace/channels-et-model-cache/qwen2.5-0.5b',local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32,attn_implementation='eager');model.eval();records=[]
 for row in originals:
  prompt=tokenizer.apply_chat_template([{'role':'system','content':reversed_system},{'role':'user','content':'Question: '+row['question']+'\nAnswer gist: '+row['answerGist']}],tokenize=False,add_generation_prompt=True)
  inputs=tokenizer(prompt,return_tensors='pt');start=time.monotonic()
  with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=96,do_sample=False,pad_token_id=tokenizer.eos_token_id)
  raw=tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True);parsed=None;error=None
  try:
   match=re.search(r'\{.*\}',raw,re.S);parsed=json.loads(match.group(0) if match else raw)
   if parsed.get('theme') not in protocol['originalThemeOrder'] or parsed.get('conditional') not in ['yes','no','unclear'] or not isinstance(parsed.get('evidence'),str):raise ValueError('Invalid label/schema')
  except Exception as e:error=type(e).__name__+': '+str(e)[:150];parsed=None
  strict='yes' if re.search(STRICT_CONDITIONAL,row['answerGist'],re.I) else 'no'
  record={'id':row['id'],'videoId':row['videoId'],'sourceGroupId':row['sourceGroupId'],'sourceUrl':row['sourceUrl'],'sourceSha256':row['sourceSha256'],'sourcePointer':row['sourcePointer'],
    'question':row['question'],'answerGist':row['answerGist'],'originalParsed':row['parsed'],'reversedRawOutput':raw,'reversedParsed':parsed,'parseError':error,
    'seconds':time.monotonic()-start,'generatedTokens':out.shape[1]-inputs['input_ids'].shape[1],
    'pairedThemeChanged':row['parsed']['theme']!=parsed['theme'] if row['parsed'] and parsed else None,
    'originalDictionaryConditional':row['dictionaryConditional'],'stricterDictionaryConditional':strict,
    'reversedEvidenceSpanExactAndShort':bool(parsed and parsed['evidence'] and parsed['evidence'] in row['answerGist'] and len(parsed['evidence'].split())<=8),
    'humanReviewed':False}
  records.append(record);print(json.dumps({'id':record['id'],'parsed':parsed,'changed':record['pairedThemeChanged']}),flush=True)
 valid=[r for r in records if r['reversedParsed']];paired=[r for r in records if r['originalParsed'] and r['reversedParsed']]
 result={'status':'completed','classification':'Prompt-order sensitivity, not annotation accuracy','n':12,'model':protocol['model'],'revision':protocol['revision'],
   'originalParsedRecords':sum(r['originalParsed'] is not None for r in records),'reversedParsedRecords':len(valid),'reversedParseFailures':12-len(valid),'pairedParsedRecords':len(paired),
   'originalThemeCounts':dict(collections.Counter(r['originalParsed']['theme'] for r in records if r['originalParsed'])),
   'reversedThemeCounts':dict(collections.Counter(r['reversedParsed']['theme'] for r in valid)),
   'pairedThemeChangedCount':sum(r['pairedThemeChanged'] for r in paired),
   'originalFirstOptionCount':sum(bool(r['originalParsed'] and r['originalParsed']['theme']=='contact_forecast') for r in records),
   'reversedFirstOptionCount':sum(r['reversedParsed']['theme']=='unclear' for r in valid),
   'reversedEvidenceSpanValidCount':sum(r['reversedEvidenceSpanExactAndShort'] for r in records),
   'meanSeconds':sum(r['seconds'] for r in records)/12,
   'lexiconSensitivity':{k:lexical[k] for k in ['n','originalConditionalCount','stricterConditionalCount','changedCount']},
   'limitations':['Option-order effects are a local model/prompt diagnostic, not evidence of source-topic prevalence.',
     'Paired label changes exclude parse failures; both denominators and raw failures remain visible.',
     'The lexicon comparison is a separate post-hoc indicator sensitivity, not a corrected human reference.',
     'No factual truth, speech authenticity or human annotation accuracy is established.']}
 (HERE/'option-order-predictions.json').write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n')
 (HERE/'option-order-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
