#!/usr/bin/env python3
"""Current-family text-only annotation on the same fixed twelve digest excerpts."""
import ast,collections,hashlib,json,pathlib,re,time,resource
HERE=pathlib.Path(__file__).resolve().parent
def main():
 originals=json.loads((HERE/'content-label-predictions.json').read_text())['records'];assert len(originals)==12
 tree=ast.parse((HERE/'run_content_labels.py').read_text());systems=[n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='system' for t in n.targets) and isinstance(n.value,ast.Constant)];assert len(systems)==1;system=systems[0]
 manifest=json.loads((HERE/'qwen35-manifest.json').read_text());assert manifest['status']=='verified'
 protocol={'stage':'Current-family same-item method comparison, defined before this run',
  'model':manifest['model'],'revision':manifest['revision'],'license':manifest['license'],
  'selectedIds':[r['id'] for r in originals],'originalPredictionsSha256':hashlib.sha256((HERE/'content-label-predictions.json').read_bytes()).hexdigest(),
  'systemPrompt':system,'themeOrder':['contact_forecast','personal_practice','cosmology','other','unclear'],
  'class':'AutoModelForImageTextToText','taskActuallyRun':'text-only digest annotation','imageOrVideoInputUsed':False,
  'maxNewTokens':96,'doSample':False,'seed':42,'torchThreads':2,'dtype':'float32','enableThinking':False,'trustRemoteCode':False,
  'operationalDifferences':['Qwen3.5 uses its own tokenizer/chat template and Transformers5.20.2; baseline uses Qwen2.5/Transformers4.51.3.',
    'The image-text architecture receives text only; no image/video/speech capability is measured.',
    'A common96-token cap is not an identical word budget across different tokenizers.',
    'Reference PyTorch linear-attention/convolution kernels are used; no GPU is exposed.'],
  'humanGroundTruth':False,'sourceTruthValidation':False}
 (HERE/'qwen35-content-label-protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
 import torch
 from transformers import AutoModelForImageTextToText,AutoTokenizer
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
 cache=manifest['cachePath'];tokenizer=AutoTokenizer.from_pretrained(cache,local_files_only=True,trust_remote_code=False)
 model=AutoModelForImageTextToText.from_pretrained(cache,local_files_only=True,trust_remote_code=False,dtype=torch.float32,attn_implementation='eager');model.eval();rows=[]
 for row in originals:
  rendered=tokenizer.apply_chat_template([{'role':'system','content':system},{'role':'user','content':'Question: '+row['question']+'\nAnswer gist: '+row['answerGist']}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  inputs=tokenizer(rendered,return_tensors='pt');start=time.monotonic()
  with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=96,do_sample=False,pad_token_id=tokenizer.eos_token_id)
  raw=tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True);parsed=None;error=None
  try:
   match=re.search(r'\{.*\}',raw,re.S);parsed=json.loads(match.group(0) if match else raw)
   if parsed.get('theme') not in protocol['themeOrder'] or parsed.get('conditional') not in ['yes','no','unclear'] or not isinstance(parsed.get('evidence'),str):raise ValueError('Invalid label/schema')
  except Exception as e:error=type(e).__name__+': '+str(e)[:150];parsed=None
  exact=bool(parsed and parsed['evidence'] and parsed['evidence'] in row['answerGist'] and len(parsed['evidence'].split())<=8)
  r={'id':row['id'],'videoId':row['videoId'],'sourceGroupId':row['sourceGroupId'],'sourceUrl':row['sourceUrl'],'sourceSha256':row['sourceSha256'],'sourcePointer':row['sourcePointer'],
    'question':row['question'],'answerGist':row['answerGist'],'rawModelOutput':raw,'parsed':parsed,'parseError':error,'seconds':time.monotonic()-start,
    'generatedTokens':out.shape[1]-inputs['input_ids'].shape[1],'generationCapHit':out.shape[1]-inputs['input_ids'].shape[1]==96,
    'dictionaryConditional':row['dictionaryConditional'],'dictionaryThemeIndicators':row['dictionaryThemeIndicators'],
    'conditionalMethodAgreement':parsed['conditional']==row['dictionaryConditional'] if parsed else None,
    'primaryThemeMatchesAnyDictionaryIndicator':parsed['theme'] in row['dictionaryThemeIndicators'] if parsed else None,
    'evidenceSpanExactAndShort':exact,'humanReviewed':False,'sourceKind':'Existing AI-generated digest paraphrase'}
  rows.append(r);print(json.dumps({'id':r['id'],'parsed':parsed,'spanValid':exact,'seconds':r['seconds']}),flush=True)
 valid=[r for r in rows if r['parsed']]
 result={'status':'completed','model':manifest['model'],'revision':manifest['revision'],'license':manifest['license'],
  'n':12,'parsedRecords':len(valid),'parseFailures':12-len(valid),'sourceSpanExactAndShortCount':sum(r['evidenceSpanExactAndShort'] for r in rows),'sourceSpanEvaluableRecords':len(valid),
  'conditionalMethodAgreementCount':sum(r['conditionalMethodAgreement'] is True for r in rows),'conditionalMethodAgreementDenominator':len(valid),
  'conditionalMethodAgreementRate':sum(r['conditionalMethodAgreement'] is True for r in rows)/len(valid) if valid else None,
  'primaryThemeDictionaryConcordanceCount':sum(r['primaryThemeMatchesAnyDictionaryIndicator'] is True for r in rows),
  'themeCounts':dict(collections.Counter(r['parsed']['theme'] for r in valid)),'conditionalLabelCounts':dict(collections.Counter(r['parsed']['conditional'] for r in valid)),
  'meanSeconds':sum(r['seconds'] for r in rows)/12,'generationCapHits':sum(r['generationCapHit'] for r in rows),
  'peakProcessRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'maxNewTokens':96,'enableThinking':False,'device':'cpu',
  'baselineComparison':{'model':'Qwen/Qwen2.5-0.5B-Instruct','parsedRecords':sum(r['parsed'] is not None for r in originals),'sourceSpanExactAndShortCount':sum(r['evidenceSpanExactAndShort'] for r in originals)},
  'limitations':['Same-item parse/span compliance comparison, not human annotation accuracy or factual truth.',
    'Different model architectures, tokenizers and required runtime versions prevent isolating parameter scale as the cause.',
    'Twelve balanced purposive digest excerpts from one practitioner context cannot support a general model ranking.',
    'Exact short substrings support traceability but do not validate the semantic label or the original speech.',
    'No images, video, audio, GPU fine-tuning or Qwen3.5 fine-tuning was run.']}
 (HERE/'qwen35-content-label-predictions.json').write_text(json.dumps({'records':rows},ensure_ascii=False,indent=2)+'\n')
 (HERE/'qwen35-content-label-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
