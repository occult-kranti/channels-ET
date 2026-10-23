#!/usr/bin/env python3
"""Download exactly the model artifacts pinned by the committed manifest."""
import argparse,pathlib,json,hashlib,urllib.request
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
manifest=json.loads((pathlib.Path(__file__).parent/'inputs/model_manifest.json').read_text())
args.output.mkdir(parents=True,exist_ok=True)
for f in manifest['files']:
 dest=args.output/f['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==f['sha256']:continue
 url=f"https://huggingface.co/{manifest['model']}/resolve/{manifest['revision']}/{f['path']}"
 with urllib.request.urlopen(url,timeout=120) as response,dest.open('wb') as out:
  while chunk:=response.read(1024*1024):out.write(chunk)
 if hashlib.sha256(dest.read_bytes()).hexdigest()!=f['sha256']:raise RuntimeError('Downloaded artifact hash mismatch: '+f['path'])
 print(f['path'],dest.stat().st_size)
(args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
