"""Portable successor to the frozen November 2026 ASR queue execution.

This file did not execute the initial batch. The private execution snapshot and
its hash remain the evidence for that batch.

One local ASR worker consumes source-verified public publisher audio receipts.
No network/model download here. Existing captions/localpilot reused; originals retained.
"""
import argparse,datetime,hashlib,importlib.util,json,pathlib,subprocess,time
from audit_vimeo_media import require_pass
parser=argparse.ArgumentParser(description="Run one source-bound local ASR worker over an inspected public Vimeo acquisition frame; no downloads or model installation.")
parser.add_argument('--private-root',type=pathlib.Path,required=True,help='Private Bashar acquisition root containing discovery/ and acquisition manifests')
parser.add_argument('--acquisition-dir',type=pathlib.Path,help='Corrected acquisition directory containing manifest.json and progress.json')
parser.add_argument('--media-integrity-audit',type=pathlib.Path,required=True,help='Positive exact-edition packet/log audit; failed or superseded encodings are rejected')
parser.add_argument('--output',type=pathlib.Path,required=True,help='Fresh private run directory; previous run remains unchanged')
parser.add_argument('--audio-core',type=pathlib.Path,required=True)
parser.add_argument('--expected-core-sha256',required=True,help='Reviewed exact audio.py SHA-256 to execute')
parser.add_argument('--asr-python',type=pathlib.Path,required=True)
parser.add_argument('--english-model',type=pathlib.Path,required=True,help='Existing local English CTranslate2 model; no implicit download')
parser.add_argument('--multilingual-ready',type=pathlib.Path,help='Optional model selection JSON: model_path and hash-bound verification_receipt')
parser.add_argument('--min-free-bytes',type=int,default=6*1024**3)
parser.add_argument('--reuse-run',type=pathlib.Path,help='Prior finalized queue manifest: reuse verified completed sources in a fresh run')
parser.add_argument('--skip-paired-sensitivity',action='store_true')
args=parser.parse_args()
CORE=args.audio_core.resolve();SPEC=importlib.util.spec_from_file_location('a',CORE);A=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(A)
if A.sha256(CORE)!=args.expected_core_sha256:raise ValueError('Reviewed ASR core hash differs')
if args.min_free_bytes<0:raise ValueError('Reserve cannot be negative')
R=A.private_path(args.private_root);D=R/'discovery';C=A.private_path(args.acquisition_dir or R/'vimeo-audio-collection');O=A.private_path(args.output)
O.mkdir(mode=0o700)
frame=json.loads((D/'vimeo-player-census.json').read_text())['records'];byid={r['video_id']:r for r in frame}
caption_manifest=R/'official-platform-captions/manifest.json';caption_records=json.loads(caption_manifest.read_text())['records'];caption_ids={r['session_id'].split(':')[1] for r in caption_records}&set(byid)
pilot='392834325';known_mixed={r['video_id'] for r in frame if r['explicit_translation_label']};done={};pending_reuse={};reserve=args.min_free_bytes
if args.reuse_run:
 prior=json.loads(A.private_path(args.reuse_run,exists=True).read_text())
 for item in prior['records']:
  vid=item['video_id']
  if vid not in byid:continue
  if item.get('status')=='completed':
   run=item['asr_result'];rp=A.private_path(run['receipt_path'],exists=True)
   if A.sha256(rp)!=run['receipt_sha256']:raise ValueError('Prior receipt hash differs')
   receipt=json.loads(rp.read_text());A.verify_completed(rp,receipt['binding']);A.validate_record(receipt['binding']['source'])
   if receipt['source_id']!='vimeo:'+vid:raise ValueError('Prior source identity differs')
   pending_reuse[vid]={**item,'reused_prior_execution':True}
base={'schema_version':1,'asr_workers':1,'cpu_threads':2,'new_pcm_retained':False,'min_free_bytes':reserve,'core_sha256':A.sha256(CORE),'queue_sha256':A.sha256(pathlib.Path(__file__)),
 'media_integrity_audit':{'path':str(args.media_integrity_audit),'sha256':A.sha256(args.media_integrity_audit)},
 'scope':'Full available public publications; known translations require multilingual model; language and ASR accuracy unverified.'}
A.atomic_json(O/'execution.json',base)
def save():
 p=O/'progress.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({**base,'updated_at':A.now(),'records':list(done.values()),'completed':len(done),'frame_count':len(frame)},indent=2)+'\n');tmp.replace(p)
def current():
 try:return json.loads((C/'progress.json').read_text())['records']
 except (FileNotFoundError,json.JSONDecodeError):return []
def model_selection():
 p=args.multilingual_ready or R/'multilingual-model-ready.json'
 if p.exists():
  d=json.loads(A.private_path(p,exists=True).read_text());proof=d['verification_receipt'];proof_path=A.private_path(proof['path'],exists=True)
  if A.sha256(proof_path)!=proof['sha256']:raise ValueError('Multilingual model verification receipt changed')
  path=pathlib.Path(d['model_path'])
  if path.is_dir():
   checked=json.loads(proof_path.read_text())
   if checked.get('model_path')!=str(path) or checked.get('binding')!=A.local_model_binding(path):raise ValueError('Pinned multilingual model files changed')
   return path
 return None
def process(media,*,sensitivity=False):
 vid=media['video_id'];row=byid[vid];folder=O/(vid+('-paired' if sensitivity else ''));folder.mkdir(mode=0o700)
 receipt_path=pathlib.Path(media['receipt']['path'])
 if A.sha256(receipt_path)!=media['receipt']['sha256']:raise ValueError('Acquisition receipt changed')
 acq=json.loads(receipt_path.read_text());audio=pathlib.Path(acq['audio']['path'])
 if A.sha256(audio)!=acq['audio']['sha256'] or audio.stat().st_size!=acq['audio']['bytes']:raise ValueError('Acquired audio bytes changed')
 integrity=require_pass(args.media_integrity_audit,'vimeo:'+vid,acq['audio']['sha256'])
 if vid in known_mixed:
  model=model_selection()
  if model is None:return {'video_id':vid,'status':'held_multilingual_model_unavailable','acquisition_receipt':media['receipt']}
  language='auto';source_lang='unknown';language_status='conflicting';note='Publisher explicitly labels Japanese translation; multilingual auto detection, mixed-segment completeness unverified.'
 else:
  model=args.english_model;language='en';source_lang='unknown';language_status='missing';note='Explicit English-only inference assumption; no spoken-language audit.'
 record={'provider':'publisher_audio','source_id':'vimeo:'+vid,'medium_id':'bashar-publisher-attribution','channel_id':'vimeo-basharcommunications','kind':'audio',
  'local_path':str(audio),'sha256':A.sha256(audio),'bytes':audio.stat().st_size,'duration_seconds':acq['duration_seconds'],'source_url':row['source_url'],
  'source_language':source_lang,'source_language_status':language_status,'language_note':note,'publication_format':row['source_format']}
 proof=folder/'source-proof.json';verified={**record,'status':'verified','validation':{'ffprobe_duration_seconds':A.probe_media(audio)['duration_seconds'],
  'source_id':record['source_id'],'acquisition_receipt_sha256':A.sha256(receipt_path)}}
 A.atomic_json(proof,{'schema_version':1,'verified_artifacts':[verified],'acquisition_receipt':{'path':str(receipt_path),'sha256':A.sha256(receipt_path)},'queue_sha256':base['queue_sha256'],'media_integrity_audit':integrity})
 record['verification_receipt']={'path':str(proof),'sha256':A.sha256(proof)};A.validate_record(record)
 input_path=folder/'input.json';A.atomic_json(input_path,{'schema_version':1,'batch_id':'vimeo-'+vid+('-paired' if sensitivity else ''),'records':[record]})
 cmd=[str(args.asr_python),str(CORE),'--input',str(input_path),'--output',str(folder/'analysis'),'--transcribe','--language',language,'--model',str(model),
  '--min-free-bytes',str(reserve),'--discard-decoded-audio']
 if A.sha256(CORE)!=base['core_sha256']:raise ValueError('Executed core changed during queue')
 with (folder/'execution.log').open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=log,timeout=600)
 run=json.loads((folder/'analysis/audio-run.json').read_text())['records'][0]
 return {'video_id':vid,'status':run['status'],'returncode':result.returncode,'asr_result':run,'source_input':str(input_path),'language_selection':language,
  'known_translation_label':vid in known_mixed,'sensitivity_only':sensitivity,'acquisition_receipt':media['receipt']}
while True:
 rows=current();ready={r['video_id']:r for r in rows if r['status']=='completed'}
 for vid in ready:
  if vid in pending_reuse and vid not in done:
   prior=pending_reuse.pop(vid);prior_receipt=json.loads(pathlib.Path(prior['asr_result']['receipt_path']).read_text())
   current_acquisition=json.loads(pathlib.Path(ready[vid]['receipt']['path']).read_text())
   if A.sha256(pathlib.Path(ready[vid]['receipt']['path']))!=ready[vid]['receipt']['sha256']:raise ValueError('Current acquisition receipt changed')
   if prior_receipt['binding']['source']['sha256']==current_acquisition['audio']['sha256']:
    require_pass(args.media_integrity_audit,'vimeo:'+vid,current_acquisition['audio']['sha256'])
    done[vid]=prior;save()
  if vid not in done and (vid in caption_ids or vid==pilot):
   acq=json.loads(pathlib.Path(ready[vid]['receipt']['path']).read_text());require_pass(args.media_integrity_audit,'vimeo:'+vid,acq['audio']['sha256'])
   done[vid]={'video_id':vid,'status':'existing_platform_captions' if vid in caption_ids else 'existing_local_pilot_asr','acquisition_receipt':ready[vid]['receipt']};save()
 candidates=[vid for vid in ready if vid not in done and (vid not in known_mixed or model_selection() is not None)]
 if candidates:
  vid=sorted(candidates,key=lambda x:(x in known_mixed,int(x)))[0]
  try:done[vid]=process(ready[vid])
  except Exception as exc:done[vid]={'video_id':vid,'status':'failed_not_admitted','error_type':type(exc).__name__}
  save();print(json.dumps({'stage':'local_asr','video_id':vid,'status':done[vid]['status'],'disposed':len(done),'total':len(frame)}),flush=True);continue
 if (C/'manifest.json').exists():
  for row in json.loads((C/'manifest.json').read_text())['records']:
   vid=row['video_id']
   if vid not in done:done[vid]={'video_id':vid,'status':'held_multilingual_model_unavailable' if vid in known_mixed and row['status']=='completed' else 'audio_not_available','acquisition_status':row['status']}
  save();break
 time.sleep(2)
# Deterministic two-publication caption/local-model sensitivity, after main queue.
caption_rows=[byid[v] for v in caption_ids];pair_ids=([min(caption_ids,key=int),sorted(caption_rows,key=lambda r:(r['duration_seconds'],int(r['video_id'])))[len(caption_rows)//2]['video_id']] if caption_rows else [])
paired=[];ready={r['video_id']:r for r in current() if r['status']=='completed'}
for vid in ([] if args.skip_paired_sensitivity else dict.fromkeys(pair_ids)):
 if vid in ready:
  try:paired.append(process(ready[vid],sensitivity=True))
  except Exception as exc:paired.append({'video_id':vid,'status':'failed_not_admitted','error_type':type(exc).__name__,'sensitivity_only':True})
A.atomic_json(O/'manifest.json',{**base,'completed_at':A.now(),'records':[done[r['video_id']] for r in frame],'paired_sensitivity':paired,
 'paired_selection':'Lowest numericID and upper-median duration item among14captioned publications; ties numericID. Machine-transcript disagreement, not reference accuracy.'})
print(json.dumps({'stage':'queue_complete','statuses':dict(__import__('collections').Counter(r['status'] for r in done.values())),'paired':len(paired)}))
