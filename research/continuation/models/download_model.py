#!/usr/bin/env python3
"""Download official pinned public model artifacts and verify Hub metadata hashes."""
import argparse, hashlib, json, pathlib, urllib.request, time
HERE=pathlib.Path(__file__).resolve().parent
FILES=['LICENSE','README.md','config.json','generation_config.json','merges.txt','model.safetensors','tokenizer.json','tokenizer_config.json','vocab.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',default='Qwen/Qwen2.5-0.5B-Instruct');p.add_argument('--revision',default='7ae557604adf67be50417f59c2c2f167def9a775');p.add_argument('--cache',type=pathlib.Path,default=pathlib.Path('/workspace/channels-et-model-cache/qwen2.5-0.5b'));p.add_argument('--manifest',default='model-manifest.json');a=p.parse_args()
 meta=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{a.model}/revision/{a.revision}?blobs=true',timeout=30));assert meta['sha']==a.revision
 siblings={x['rfilename']:x for x in meta['siblings']};a.cache.mkdir(parents=True,exist_ok=True);records=[]
 chosen=FILES+[name for name in siblings if name.endswith('.safetensors') or name in ['model.safetensors.index.json','chat_template.jinja','preprocessor_config.json','processor_config.json']]
 for name in dict.fromkeys(chosen):
  if name not in siblings:continue
  info=siblings[name];target=a.cache/name;start=time.monotonic()
  if not target.exists():
   temp=target.with_suffix(target.suffix+'.partial')
   with urllib.request.urlopen(f'https://huggingface.co/{a.model}/resolve/{a.revision}/{name}',timeout=120) as response,temp.open('wb') as out:
    while chunk:=response.read(4*1024*1024):out.write(chunk)
   temp.rename(target)
  sha=hashlib.sha256();git=hashlib.sha1();git.update(f'blob {target.stat().st_size}\0'.encode())
  with target.open('rb') as f:
   while chunk:=f.read(4*1024*1024):sha.update(chunk);git.update(chunk)
  expected=info.get('lfs',{}).get('sha256')
  if expected:assert sha.hexdigest()==expected,f'{name}: SHA256 mismatch'
  else:assert git.hexdigest()==info['blobId'],f'{name}: Git blob mismatch'
  assert target.stat().st_size==info['size']
  records.append({'file':name,'bytes':target.stat().st_size,'sha256':sha.hexdigest(),'verifiedAgainst':'official_Hub_LFS_SHA256' if expected else 'official_Hub_Git_blob_SHA1','seconds':round(time.monotonic()-start,3)})
  print(json.dumps(records[-1]),flush=True)
 (HERE/a.manifest).write_text(json.dumps({'model':a.model,'revision':a.revision,'license':meta.get('cardData',{}).get('license'),'cachePath':str(a.cache),'files':records,'trustRemoteCode':False,'status':'verified'},indent=2)+'\n')
if __name__=='__main__':main()
