#!/usr/bin/env python3
"""Bind independently read semantic leads without changing inference outputs."""
import argparse,collections,hashlib,json,shutil,statistics
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def finalize(src,dst,reading):
 if dst.exists():raise ValueError('New edition required')
 r=json.loads((src/'semantic-pilot.json').read_text());review=json.loads(reading.read_text());assert review['model_run_binding']['semantic_pilot_json_sha256']==sha(src/'semantic-pilot.json');docs={d['source_id']:d for d in r['documents']};leads={(x['source'],x['target']):x for x in r['reading_leads']}
 for row in review['inspected_sources']:assert docs[row['source_id']]['text_sha256']==row['text_sha256']
 assert len(review['reviews'])==len(leads)==6
 for row in review['reviews']:
  pair=leads[row['source_id'],row['target_id']];assert docs[row['source_id']]['text_sha256']==row['source_text_sha256'] and docs[row['target_id']]['text_sha256']==row['target_text_sha256']
  for key in ['semantic_cosine','equal_chunk_cosine','window_300_cosine','strict_lexical_cosine']:assert abs(row[key]-pair[key])<1e-12
 groups=collections.defaultdict(list)
 for pair in r['pairs']:
  if pair['comparison_kind']=='same_label_cross_medium':groups[pair['source_label']].append(pair)
 r['label_summary']=[{'comparison_label':label,'comparison_level':rows[0]['comparison_level'],'pairs':len(rows),'full_mean':statistics.mean(p['semantic_cosine'] for p in rows),'window_300_mean':statistics.mean(p['window_300_cosine'] for p in rows),'equal_chunk_mean':statistics.mean(p['equal_chunk_cosine'] for p in rows)} for label,rows in sorted(groups.items())]
 r['reading']=review;r['reading_binding']={'file':'semantic-reading.json','sha256':sha(reading),'executed_semantic_analysis_sha256':sha(src/'semantic-pilot.json'),'finalizer_sha256':sha(Path(__file__)),'scope':'Post-inference source-reading attachment and per-label aggregation only. All vectors, matrices, pair scores, model settings and coverage unchanged.'}
 dst.mkdir(parents=True,mode=0o700)
 for p in src.iterdir():
  if p.is_file():shutil.copy2(p,dst/p.name)
 shutil.copy2(reading,dst/'semantic-reading.json');shutil.copy2(Path(__file__),dst/'executed-finalize-semantic.py');write(dst/'semantic-pilot.json',r);m=json.loads((dst/'output-manifest.json').read_text())
 for f in m['public_allowlist']:
  p=dst/f['file'];f.update(sha256=sha(p),bytes=p.stat().st_size)
 write(dst/'output-manifest.json',m);print(json.dumps({'sha256':sha(dst/'semantic-pilot.json'),'reading_sha256':sha(reading)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reading',type=Path,required=True);a=p.parse_args();finalize(a.source,a.output,a.reading)
