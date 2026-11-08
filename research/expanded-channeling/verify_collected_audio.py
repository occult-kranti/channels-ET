#!/usr/bin/env python3
import argparse,hashlib,json,math
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 r=json.loads((root/'collected-audio-analysis.json').read_text());docs=r['documents'];c=r['coverage'];assert r['schema_version']==1
 assert c['selected_text_units']==len(docs)==len({d['source_id'] for d in docs})
 assert c['words']==sum(d['words'] for d in docs)==sum(g['words'] for g in c['groups'])
 assert sum(g['selected_text_units'] for g in c['groups'])==len(docs)
 assert c['retained_audio_publications']==sum(g['retained_audio_publications'] for g in c['groups'])<=c['finite_publisher_frame']
 assert all(d['source_role']=='unknown_speakers_recording_context_only' and d['claimed_entity_attribution'] is None for d in docs)
 assert r['qa']['identified_answers']==0 and r['qa']['speaker_diarization'] is False
 assert c['all_uploaded_youtube_videos'] is None
 assert '/workspace/' not in json.dumps(r) and '/dev/shm/' not in json.dumps(r)
 if r['lexical']['status']=='fitted':
  ids=r['lexical']['source_ids'];matrix=r['lexical']['matrix'];assert len(ids)==len(matrix)==c['lexical_model_units']
  for i,row in enumerate(matrix):
   assert len(row)==len(ids)
   for j,value in enumerate(row):assert math.isfinite(value) and -.0000001<=value<=1.0000001 and abs(value-matrix[j][i])<1e-10
 if r['topics']['status']=='exploratory_fit':assert c['lexical_model_units']>=5
 for f in r['figures']:
  p=root/'collected-audio-figures'/f['file']
  if not p.exists():p=root/'figures'/f['file']
  if not p.exists():p=root/f['file']
  assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
 return {'status':'passed','documents':len(docs),'words':c['words'],'retained_audio_snapshot':c['retained_audio_publications'],'sha256':sha(root/'collected-audio-analysis.json')}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.public_dir)))
