#!/usr/bin/env python3
"""Public semantic pilot release checks, without loading model weights."""
import argparse,hashlib,json,math
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 r=json.loads((root/'semantic-pilot.json').read_text());assert r['schema_version']==1 and r['model']['revision']=='1110a243fdf4706b3f48f1d95db1a4f5529b4d41';assert r['processing']['intra_op_threads']==1
 assert r['totals']=={'documents':20,'full_wordpieces':24436,'full_chunks':113,'window_wordpieces':7028,'window_chunks':40,'truncated_wordpieces':0}
 assert len(r['source_ids'])==len(set(r['source_ids']))==20 and len(r['pairs'])==190
 for key in ['coverage','window_coverage']:
  assert len(r[key])==20
  assert all(x['content_wordpieces']==x['processed_content_wordpieces'] and x['truncated_content_wordpieces']==0 for x in r[key])
 for key in ['matrix','equal_chunk_matrix','window_300_matrix']:
  m=r[key];assert len(m)==20
  for i,row in enumerate(m):
   assert len(row)==20
   for j,v in enumerate(row):assert math.isfinite(v) and -1.0000001<=v<=1.0000001 and abs(v-m[j][i])<1e-10
 assert r['reading']['review_scope']['full_normalized_bodies_read']==7 and r['reading']['review_scope']['words_whitespace_read']==6219
 assert len(r['reading']['reviews'])==6 and all(x['identity_equivalence'] is False and x['shared_question_or_answer_verified'] is False for x in r['reading']['reviews'])
 assert '/workspace/' not in json.dumps(r)
 for f in r['figures']:
  candidates=[root/'semantic-pilot-figures'/f['file'],root/'semantic-figures'/f['file'],root/'figures'/f['file'],root/f['file']];p=next((p for p in candidates if p.is_file()),None);assert p and sha(p)==f['sha256'] and p.stat().st_size==f['bytes']
 return {'status':'passed','documents':20,'wordpieces':r['totals']['full_wordpieces'],'reviewed_pairs':6,'sha256':sha(root/'semantic-pilot.json')}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.public_dir)))
