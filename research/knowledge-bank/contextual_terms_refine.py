#!/usr/bin/env python3
"""Render collision-free term labels without changing fitted token-state results."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from contextual_terms import figure,save,digest


def projection(value):
    value=copy.deepcopy(value);value.pop('figures',None);value.pop('visual_revision',None)
    return digest(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())


def refine(parent,out):
    parent=Path(parent);out=Path(out)
    if out.exists() or not out.resolve().is_relative_to(Path('/workspace/channels-et-private/knowledge-bank-2026-11')):
        raise ValueError('Fresh private output required')
    body=(parent/'contextual-terms.json').read_bytes();r=json.loads(body);before=projection(r)
    for ref in r['figures']:
        raw=(parent/ref['file']).read_bytes()
        if digest(raw)!=ref['sha256'] or len(raw)!=ref['bytes']:raise ValueError('Parent figure changed')
    out.mkdir(parents=True);r['figures']=[];figure(r,out)
    if projection(r)!=before:raise ValueError('Numerical projection changed')
    r['visual_revision']={'parent_sha256':digest(body),'unchanged_numerical_projection_sha256':before,
        'refiner_sha256':digest(Path(__file__).read_bytes()),
        'renderer_sha256':digest((Path(__file__).parent/'contextual_terms.py').read_bytes()),
        'scope':'Figure-label offsets only; token selection, source spans, vectors, scores, coordinates and clusters are unchanged.'}
    save(out/'contextual-terms.json',r)
    save(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'contextual-terms.json',
        'sha256':digest((out/'contextual-terms.json').read_bytes()),'bytes':(out/'contextual-terms.json').stat().st_size}]+r['figures']})
    print(json.dumps({'sha256':digest((out/'contextual-terms.json').read_bytes()),'numeric_sha256':before}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();refine(a.parent,a.output)
