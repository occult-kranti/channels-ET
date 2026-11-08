#!/usr/bin/env python3
"""Bind an applied review after independent critique without refitting old models."""
import argparse,hashlib,json,shutil
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def finalize(src,dst,review):
    if dst.exists():raise ValueError('Never overwrite prior run')
    r=json.loads((src/'analysis.json').read_text());q=json.loads((src/'qa-private.json').read_text());rv=json.loads(review.read_text());lookup={x['id']:x for x in q['items']};annotations={x['id']:x for x in r['qa_leads']}
    for row in rv['reviews']:
        actual=annotations[row['id']];assert actual['target_id']==row['target_id']
        assert hashlib.sha256(lookup[row['id']]['question'].encode()).hexdigest()==row['query_text_sha256']
        assert hashlib.sha256(lookup[row['target_id']]['question'].encode()).hexdigest()==row['target_text_sha256']
        for k in ['status','question_paraphrase','response_paraphrase','comparison','accepted_same_question','audio_reviewed']:assert actual[k]==row[k]
    dst.mkdir(parents=True,mode=0o700)
    for p in src.iterdir():
        if p.is_file():shutil.copy2(p,dst/p.name)
    shutil.copy2(review,dst/'qa-review.json');shutil.copy2(Path(__file__),dst/'executed-finalize-joint.py')
    binding={'review_file':'qa-review.json','review_sha256':sha(review),'original_fit_analysis_sha256':sha(src/'analysis.json'),'finalizer_sha256':sha(Path(__file__)),'scope':'Postrun provenance binding only. Every already-applied annotation and exact query/target text hash independently matched; no models, scores or annotation content changed.'}
    r['annotation_binding']=binding;write(dst/'analysis.json',r)
    provenance=json.loads((dst/'provenance-private.json').read_text());provenance['annotation_binding']=binding;write(dst/'provenance-private.json',provenance)
    manifest=json.loads((dst/'output-manifest.json').read_text())
    for x in manifest['public_allowlist']:
        if x['file']=='analysis.json':x.update(sha256=sha(dst/'analysis.json'),bytes=(dst/'analysis.json').stat().st_size)
    manifest['private_outputs']+=['qa-review.json','executed-finalize-joint.py'];write(dst/'output-manifest.json',manifest);print(json.dumps({'status':'complete','analysis_sha256':sha(dst/'analysis.json'),'annotation_binding':binding}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--review',type=Path,required=True);a=p.parse_args();finalize(a.source,a.output,a.review)
