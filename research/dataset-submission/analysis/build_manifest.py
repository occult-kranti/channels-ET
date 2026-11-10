#!/usr/bin/env python3
"""Explicit public analytical artifact allowlist, after computation and verification."""
import argparse
import hashlib
import json
from pathlib import Path

def main(directory):
    p=Path(directory)
    verified=json.loads((p/'verification.json').read_text())
    if verified['status']!='passed':raise ValueError('Analysis verification must pass')
    exact={'analysis.json','results.json','verification.json','METHODS.md'}
    files=[]
    for x in sorted(p.rglob('*')):
        if not x.is_file():continue
        rel=x.relative_to(p)
        if str(rel) in exact or (rel.parts[0]=='tables' and x.suffix=='.csv') or (rel.parts[0]=='figures' and x.suffix in {'.pdf','.svg','.png'}):
            files.append({'file':str(rel),'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()})
    (p/'output-manifest.json').write_text(json.dumps({'schema_version':'dataset-analysis-producer-1','public_allowlist':files},indent=2)+'\n')
    print(json.dumps({'public_files':len(files),'bytes':sum(f['bytes'] for f in files)}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('directory',type=Path);main(a.parse_args().directory)
