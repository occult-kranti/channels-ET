#!/usr/bin/env python3
"""Verify the sanitized publisher-text recovery supplement without raw bodies."""
import hashlib
import json
from pathlib import Path
import sys

def verify(root):
 p=Path(root)/'publisher-text-recovery.json';d=json.loads(p.read_text());rows=d['records']
 assert d['schema_version']==1 and d['module']=='publisher_text_recovery'
 assert len({x['record_id'] for x in rows})==len(rows)
 recovered=[x for x in rows if x['status']=='publisher_written_message_recovered']
 assert d['counts']=={'attempted':len(rows),'recovered':len(recovered),'pending':len(rows)-len(recovered),'manually_read_messages':sum(x['full_body_manually_read_by_ai'] for x in rows),'recovered_words':sum(x['words'] for x in recovered)}
 for x in rows:
  assert x['page_url'].startswith('https://omna.org/') and len(x['page_sha256'])==64
  assert x['text_origin']=='publisher_written_message_not_ASR' and x['audio_equivalence']=='not_established' and not x['human_validated'] and x['no_youtube_download_claim']
  if x['status']=='publisher_written_message_recovered':
   assert x['words']>=50 and len(x['body_sha256'])==64 and x['body_bytes']>0
   assert x['locator']['publisher_author']=='Natalie Glasson'
   assert x['locator']['removed_exact_initial_paragraph'] in {'Download Audio MP3','Download Audio','Channeled Message\n\nDownload Audio MP3'}
   assert x['locator']['wrapper_html_char_interval'][0]<x['locator']['wrapper_html_char_interval'][1]
   assert (x['reading_status']=='manual_AI_complete_selected_message_reading')==x['full_body_manually_read_by_ai']
  else:assert x['status']=='written_message_pending' and x['hold_reason'] and not x['full_body_manually_read_by_ai']
 raw=p.read_text();assert '/workspace/' not in raw and '/dev/shm/' not in raw
 return {**d['counts'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
if __name__=='__main__':print(json.dumps(verify(sys.argv[1])))
