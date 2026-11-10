#!/usr/bin/env python3
"""Refresh UI/docs from an intact published Git snapshot, without private raw inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import build_public as public

def digest(raw): return hashlib.sha256(raw).hexdigest()
def refresh(site,baseline,plan,receipt):
    commit=subprocess.check_output(['git','rev-parse','--verify',baseline+'^{commit}'],cwd=site,text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('Invalid baseline commit')
    def blob(name):
        public.guard.safe('/bundle',name)
        return subprocess.check_output(['git','show',commit+':dist/dataset-submission/'+name],cwd=site)
    manifest=public.guard.inspect(blob('manifest.json'))
    root=site/'dist/dataset-submission'
    doc_names={'docs/'+p.name for p in public.HERE.glob('*.md')}
    skip=set(public.DATASET)|{'index.html','app.js','styles.css','collection-plan.json'}|doc_names
    with tempfile.TemporaryDirectory(prefix='channeling-public-refresh-') as temporary:
        producer=Path(temporary);refs=[]
        for ref in manifest['artifacts']:
            name=ref['file'];raw=blob(name)
            if digest(raw)!=ref['sha256'] or len(raw)!=ref['bytes']: raise ValueError('Baseline digest differs: '+name)
            public.inspect(raw,name)
            if name in public.DATASET and (root/name).read_bytes()!=raw:
                raise ValueError('Refusing to alter or silently accept a changed frozen data file: '+name)
            if name in skip: continue
            target=public.guard.safe(producer,name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);refs.append(ref)
        raw=plan.read_bytes();public.inspect(raw,'collection-plan.json')
        (producer/'collection-plan.json').write_bytes(raw)
        refs.append({'file':'collection-plan.json','bytes':len(raw),'sha256':digest(raw)})
        (producer/'output-manifest.json').write_text(json.dumps({'public_allowlist':refs})+'\n')
        public.build(site,[producer],receipt)
    return commit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True)
    p.add_argument('--baseline-commit',default='HEAD');p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    commit=refresh(a.site.resolve(),a.baseline_commit,a.plan.resolve(),a.receipt.resolve())
    print(json.dumps({'baseline_commit':commit,'frozen_data_changed':False,'private_source_inputs_required':False}))
