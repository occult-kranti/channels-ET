#!/usr/bin/env python3
"""Bind a separately reviewed final official-excerpt study to the living paper."""
import argparse,hashlib,json,shutil
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--analysis',required=True,type=Path);p.add_argument('--expect-sha256',required=True)
 p.add_argument('--review-status',choices=['draft','accepted-model-agent-audit'],default='draft')
 a=p.parse_args();source=a.analysis.resolve()
 if digest(source)!=a.expect_sha256:raise SystemExit('Official analysis hash mismatch')
 d=json.loads(source.read_text());root=Path(__file__).resolve().parent;snapshot=json.loads((root/'snapshot.json').read_text())
 if d['run_scope']['phase']!='final':raise SystemExit('Pilot cannot replace final-study metadata')
 if d['baseline_binding']['analysis_sha256']!=snapshot['analysis_sha256']:raise SystemExit('Supplement does not bind this baseline')
 figures=[]
 for f in d['figures']:
  name=f['file']
  if Path(name).name!=name:raise SystemExit('Invalid figure basename')
  if Path(name).suffix not in {'.png','.pdf'}:continue
  src=source.parent/name
  if digest(src)!=f['sha256'] or src.stat().st_size!=f['bytes']:raise SystemExit('Official figure evidence mismatch')
  figures.append(f)
 if not figures:raise SystemExit('No official figures')
 if 'supplementary_excerpt_manifest_sha256' in snapshot:
  snapshot['historical_official_pilot']={'manifest_sha256':snapshot.pop('supplementary_excerpt_manifest_sha256'),'publication_documents':snapshot.pop('supplementary_excerpt_documents'),'whitespace_words':snapshot.pop('supplementary_excerpt_words'),'status':'historical_pilot_not_final_frame'}
 snapshot['official_follow_on']={'status':a.review_status,'analysis_run':source.parent.name,'analysis_sha256':digest(source),'analysis_script_sha256':d['script_sha256'],'run_scope':{k:v for k,v in d['run_scope'].items() if k!='source_frame'},'source_frame_sha256':d['run_scope']['source_frame']['sha256'],'coverage':d['coverage'],'input_manifest_hashes':[x['sha256'] for x in d['inputs']],'integrity_audit_sha256':d['integrity_audit']['audit_sha256'],'figures':figures,'human_reviewed':False}
 for f in figures:shutil.copyfile(source.parent/f['file'],root/'figures'/f['file'])
 (root/'snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
 print('Copied and hash-bound',len(figures),'official-study figure files; narrative still requires review.')
if __name__=='__main__':main()
