#!/usr/bin/env python3
"""Text-only CPU smoke test for hash-verified official Qwen3.5 small weights."""
import hashlib,importlib.metadata,json,pathlib,resource,time
HERE=pathlib.Path(__file__).resolve().parent
def main():
 import torch
 from transformers import AutoModelForImageTextToText,AutoTokenizer
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
 manifest=json.loads((HERE/'qwen35-manifest.json').read_text());assert manifest['status']=='verified'
 path=pathlib.Path(manifest['cachePath']);start=time.monotonic()
 tokenizer=AutoTokenizer.from_pretrained(str(path),local_files_only=True,trust_remote_code=False)
 model=AutoModelForImageTextToText.from_pretrained(str(path),local_files_only=True,trust_remote_code=False,dtype=torch.float32,attn_implementation='eager');model.eval()
 load_seconds=time.monotonic()-start
 source=json.loads((HERE/'split.json').read_text())['train'][0]
 prompt='Return JSON only with keys source_type and speaker_verified. This excerpt is an AI-generated digest, and speaker turns are unverified. Use source_type="AI_digest" and speaker_verified=false. Excerpt: '+source['answerGist']
 rendered=tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
 inputs=tokenizer(rendered,return_tensors='pt');start=time.monotonic()
 with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=32,do_sample=False,pad_token_id=tokenizer.eos_token_id)
 elapsed=time.monotonic()-start;generated=out.shape[1]-inputs['input_ids'].shape[1];text=tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
 result={'status':'completed','model':manifest['model'],'revision':manifest['revision'],'license':manifest['license'],
   'class':'AutoModelForImageTextToText','taskActuallyRun':'text-only generation','imageOrVideoInputUsed':False,
   'device':'cpu','cudaAvailable':torch.cuda.is_available(),'torchThreads':2,'dtype':'float32','trustRemoteCode':False,
   'versions':{p:importlib.metadata.version(p) for p in ['torch','transformers','huggingface-hub','tokenizers']},
   'environment':'separate modern venv; CPU Torch reused read-only from baseline venv through explicit package symlinks (without exposing old Transformers/PEFT)',
   'loadSeconds':round(load_seconds,6),'generationSeconds':round(elapsed,6),'generatedTokens':generated,'maxNewTokens':32,
   'peakProcessRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'prompt':prompt,'rawOutput':text,
   'sourceCandidateId':source['id'],'sourceUrl':source['sourceUrl'],'sourceSha256':source['sourceSha256'],'sourcePointer':source['sourcePointer'],
   'stateOfTheArtEstablished':False,'factualAccuracyValidated':False,
   'limitations':['A single 32-token text-only provenance-schema instruction probe is not a domain benchmark.','The image-text architecture was not tested on images, video or speech.','No GPU comparison or Qwen3.5 fine-tuning was run.','The separate Qwen2.5 CPU LoRA benchmark is not interchangeable with this newer-family smoke test.']}
 try:
  import re
  match=re.search(r'\{.*\}',text,re.S);parsed=json.loads(match.group(0) if match else text)
  result['parsedOutput']=parsed;result['jsonParseSuccess']=True
  result['schemaInstructionFollowed']=parsed.get('source_type')=='AI_digest' and parsed.get('speaker_verified') is False
 except Exception as e:
  result['jsonParseSuccess']=False;result['schemaInstructionFollowed']=False;result['parseError']=type(e).__name__
 (HERE/'current-family-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  (HERE/'current-family-smoke-failure.json').write_text(json.dumps({'status':'failed','errorType':type(e).__name__,'error':str(e)[:1500],'stateOfTheArtEstablished':False},indent=2)+'\n');raise
