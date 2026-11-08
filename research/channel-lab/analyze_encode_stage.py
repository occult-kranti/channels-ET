#!/usr/bin/env python3
"""Prepare exact-input model caches while the immutable-body metadata review finishes."""
import argparse
import hashlib
import json
from pathlib import Path
from analyze_corpus import load_inputs,masked,bounded,RAM
from analyze_encoder import LabEncoder


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frame',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    a=p.parse_args();docs=load_inputs(a.frame);records=[d['record'] for d in docs];ids=[r['source_id'] for r in records]
    phrases=sorted({p for r in records for p in r.get('mask_phrases',[]) if p and p.lower() not in ('unknown','unresolved')})
    raw_windows=[bounded(d['text'])[0] for d in docs]
    encoder=LabEncoder(a.model);receipts={}
    for name,texts in [('full',[masked(d['text'],phrases) for d in docs]),
                       ('bounded',[masked(t,phrases) for t in raw_windows]),('unmasked_bounded',raw_windows)]:
        _,_,receipt=encoder.encode_all(list(zip(ids,texts)),RAM/'encoder-cache',8);receipts[name]=receipt
        print(json.dumps({'stage':name,'sources':len(ids),'chunks':receipt['chunks'],'seconds':receipt['seconds']}),flush=True)
    value={'frame_path':str(a.frame),'frame_sha256':hashlib.sha256(a.frame.read_bytes()).hexdigest(),
           'ordered_body_manifest':[(r['source_id'],r['body_sha256']) for r in records],
           'mask_phrases':phrases,'receipts':receipts}
    (RAM/'encoder-stage.json').write_text(json.dumps(value,indent=2)+'\n')
