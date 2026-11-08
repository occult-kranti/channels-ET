#!/usr/bin/env python3
"""Read-only checks for public pilot metadata, numerical shape and figure hashes."""
import argparse,hashlib,json,math
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 r=json.loads((root/'new-message-pilot.json').read_text());assert r['schema_version']==1
 assert r['coverage']=={'documents':20,'words':20829,'mediums':4,'comparison_labels':11}
 ids=[x['source_id'] for x in r['documents']];assert len(set(ids))==20
 assert len({x['text_sha256'] for x in r['documents']})==20
 assert sum(x['words'] for x in r['documents'])==20829
 assert len(r['pairs'])==190 and sum(p['same_comparison_label'] and not p['same_medium'] for p in r['pairs'])==12
 for key in ['matrix','window_300_matrix']:
  m=r[key];assert len(m)==20
  for i,row in enumerate(m):
   assert len(row)==20
   for j,v in enumerate(row):assert math.isfinite(v) and -.00000001<=v<=1.00000001 and abs(v-m[j][i])<1e-10
 assert r['reading']['coverage']['messages_read']==9
 assert r['reading']['coverage']['primary_body_words_read']==11274
 assert r['reading']['coverage']['additional_Lyssa_question_words_read']==71
 assert all(p['identity_equivalence'] is False for p in r['pairs'])
 assert '/workspace/' not in json.dumps(r)
 for f in r['figures']:
  candidates=[root/'pilot-figures'/f['file'],root/'figures'/f['file'],root/f['file']]
  p=next((p for p in candidates if p.is_file()),candidates[0])
  assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes']
 return {'status':'passed','documents':20,'pairs':190,'figures':len(r['figures']),'sha256':sha(root/'new-message-pilot.json')}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.public_dir)))
