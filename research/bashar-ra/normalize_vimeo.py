"""Portable successor: freeze retained acquisition and preferred text dispositions.

The initial batch used a separate immutable private execution snapshot, whose
recorded hash remains its provenance; this successor does not replace it.
"""
import argparse,collections,importlib.util,json,pathlib
from audit_vimeo_media import require_pass
parser=argparse.ArgumentParser(description='Validate retained Vimeo acquisitions/transcript editions and freeze one preferred text disposition per publication.')
parser.add_argument('--private-root',type=pathlib.Path,required=True)
parser.add_argument('--media-manifest',type=pathlib.Path,help='Corrected raw-compatible acquisition manifest')
parser.add_argument('--media-integrity-audit',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True,help='Fresh private normalized output directory')
parser.add_argument('--audio-core',type=pathlib.Path,required=True)
parser.add_argument('--asr-manifest',type=pathlib.Path,help='Finalized queue manifest; defaults to private-root/vimeo-bulk-asr/manifest.json')
parser.add_argument('--boundary-exclusion',type=pathlib.Path,help='Optional independently measured duration-exclusion receipt')
args=parser.parse_args()
CORE=args.audio_core.resolve();sp=importlib.util.spec_from_file_location('a',CORE);A=importlib.util.module_from_spec(sp);sp.loader.exec_module(A)
R=A.private_path(args.private_root);D=R/'discovery';OUT=A.private_path(args.output)
def read(p):return json.loads(pathlib.Path(p).read_text())
def artifact(p,role):p=pathlib.Path(p);return {'path':str(p),'sha256':A.sha256(p),'bytes':p.stat().st_size,'role':role}
def verify(a):
 p=pathlib.Path(a['path'])
 if A.sha256(p)!=a['sha256'] or p.stat().st_size!=a['bytes']:raise ValueError('Retained artifact bytes changed')
 return p
frame=read(D/'vimeo-player-census.json')['records'];byid={r['video_id']:r for r in frame}
media_manifest=args.media_manifest or R/'vimeo-audio-collection/manifest.json';media_data=read(media_manifest);audio_rows={r['video_id']:r for r in media_data['records']}
queue_manifest=args.asr_manifest or R/'vimeo-bulk-asr/manifest.json';queue=read(queue_manifest);dispositions={r['video_id']:r for r in queue['records']}
if len(byid)!=len(frame) or set(byid)!=set(audio_rows) or set(byid)!=set(dispositions):raise ValueError('Frame/audio/transcript disposition identities differ')
exclusion_path=args.boundary_exclusion or R/'vimeo-boundary-exclusion.json';exclusion=read(exclusion_path) if exclusion_path.exists() else {'video_id':None,'unadmitted_retained_artifact':{'bytes':0}}
unadmitted=media_data.get('superseded_media',media_data.get('unadmitted_retained_editions',[]))
if not unadmitted and exclusion['video_id']:unadmitted=[{'publication_id':exclusion['source_id'],'disposition':exclusion['status'],'artifact':exclusion['unadmitted_retained_artifact']}]
for item in unadmitted:verify(item['artifact'])
caption_manifest=R/'official-platform-captions/manifest.json';captions={r['session_id'].split(':')[1]:r for r in read(caption_manifest)['records']}
pilot=read(R/'official-excerpt-corpus/manifest.json')['records'][0]
OUT.mkdir(mode=0o700)
def common(vid):
 f=byid[vid];m=audio_rows[vid];sid='vimeo:'+vid
 out={'corpus':'bashar','recording_id':sid,'session_id':sid,'session_id_basis':'Vimeo public publication ID; historical full channeling-session identity unresolved',
  'source_family_id':None,'source_family_basis':'Historical full-session family unresolved; title/product-link similarity only a discovery lead',
  'original_session_identity':'unresolved','source_format':f['source_format'],'title':f['title'],'publisher':'Bashar Communications','source_url':f['source_url'],
  'published_at':None,'publication_date_status':'Unresolved; copyright/year in title not silently used as release date',
  'source_publication_scope':'Public excerpt, greeting, event or product publication according to publisher metadata',
  'original_session_coverage':'Partial or unresolved; no paid full-session equivalence','explicit_translation_label':f['explicit_translation_label'],
  'speaker_attribution_status':'Publisher attribution only; unknown mixed speakers, no independent voice identity or diarization',
  'human_reviewed':False,'youtube_video_edition_verified':False,'audio_collection_status':m['status'],'eligibility_status':'qualifying_actual_duration' if m['status']=='completed' else 'unresolved','hold_reason':None}
 if m['status']=='completed':
  acqpath=verify(m['receipt']);acq=read(acqpath);verify(acq['audio'])
  if acq['source_id']!=sid or acq['status']!='completed':raise ValueError('Acquisition identity/status differs')
  out['media_integrity_audit']=require_pass(args.media_integrity_audit,sid,acq['audio']['sha256'])
  out.update(duplicate_family_id='exact-media:'+acq['audio']['sha256'],duplicate_family_basis='Exact retained encoded audio bytes only; broader historical-session overlap unresolved',audio_artifact=acq['audio'],audio_bytes=acq['audio']['bytes'],audio_duration_seconds=acq['duration_seconds'],observed_duration_seconds=acq['duration_seconds'],
   acquisition_receipt=artifact(acqpath,'acquisition_receipt'),audio_encoding=acq.get('encoding','Original-language high audio track retained from initial pilot'))
 if vid==exclusion['video_id']:
  verify(exclusion['unadmitted_retained_artifact']);out.update(audio_collection_status=exclusion['status'],eligibility_status='excluded_below_actual_duration',advertised_duration_seconds=exclusion['advertised_duration_seconds'],observed_duration_seconds=exclusion['measured_duration_seconds'],retained_unadmitted_artifact=exclusion['unadmitted_retained_artifact'],unadmitted_audio_duration_seconds=exclusion['measured_duration_seconds'],boundary_exclusion_receipt=artifact(exclusion_path,'boundary_exclusion'))
 return out

def inherited(vid,record):
 verify(record['text_artifact'])
 for e in record['evidence']:verify(e)
 c=common(vid);out={**record,**c,'transcript_source_format':record['source_format'],'collection_status':'retrieved',
  'transcript_origin':'platform_automatic_captions' if vid in captions else 'local_whisper_asr',
  'available_publication_text_coverage':'Available automatic caption track; audible completeness unverified' if vid in captions else 'Full available public excerpt decoded; VAD/recognition may omit speech',
  'language_analysis_group':'mixed_translation' if c['explicit_translation_label'] else 'english_assumption_or_platform_label'}
 if 'audio_artifact' in out:out['evidence']=list(out['evidence'])+[out['audio_artifact'],out['acquisition_receipt'],out['media_integrity_audit']]
 return out

def local(vid,result,alternate=False):
 run=result['asr_result'];rp=pathlib.Path(run['receipt_path'])
 if A.sha256(rp)!=run['receipt_sha256']:raise ValueError('ASR receipt changed')
 rec=read(rp)
 if rec['status']!='completed' or rec['source_id']!='vimeo:'+vid:raise ValueError('ASR status/identity differs')
 A.verify_completed(rp,rec['binding']);A.validate_record(rec['binding']['source'])
 if A.local_model_binding(pathlib.Path(rec['binding']['asr']['model']['path']))!=rec['binding']['asr']['model']:raise ValueError('Model cache changed')
 source=common(vid)
 if source['audio_artifact']['sha256']!=rec['binding']['source']['sha256']:raise ValueError('ASR source differs from acquired edition')
 segpath=rp.parent/'segments.json';seg=read(segpath);segments=seg['segments'];text='\n'.join(x['text'] for x in segments)
 if text!=seg['text'] or len(text.split())!=rec['asr']['whitespace_word_count']:raise ValueError('ASR text/counts differ')
 sid='vimeo:'+vid+':local-asr:'+rec['binding_sha256'][:16];dest=OUT/(sid+'.json')
 A.atomic_json(dest,{'source_id':sid,'text':text,'turns':[{'turn_id':sid+':segment:'+str(i+1),'role':'unknown','text':x['text'],'start_seconds':x['start_seconds'],'end_seconds':x['end_seconds']} for i,x in enumerate(segments)],
  'normalization':'Exact localASR segment strings/order; newline joining only, no corrections or speaker inference'})
 evidence=[source['media_integrity_audit'],artifact(rp,'asr_receipt'),artifact(segpath,'asr_segments'),artifact(result['source_input'],'asr_input'),source['acquisition_receipt']]
 evidence.extend(artifact(x['local_path'],x['kind']) for x in rec['verified_artifacts'] if x.get('retained',True))
 proof=rec['binding']['source']['verification_receipt'];evidence.append(artifact(proof['path'],'source_verification'))
 out={**source,'source_id':sid,'edition_id':rec['binding_sha256'],'source_kind':'machine_asr','asr_receipt_source_id':'vimeo:'+vid,'transcript_origin':'local_whisper_asr',
  'duplicate_family_id':source['duplicate_family_id'],'duplicate_family_basis':source['duplicate_family_basis'],
  'collection_status':'retrieved','coverage_status':'partial','coverage_scope':'Full public recording decoded forASR, partial original historicalsession; recognition completeness unverified',
  'available_publication_text_coverage':'Full decoded public recording submitted; localVAD and recognition may omit speech',
  'text_artifact':artifact(dest,'normalized_text'),'evidence':evidence,'asr_words':len(text.split()),'asr_segments':len(segments),
  'language':'mul' if source['explicit_translation_label'] else 'en','language_basis':rec['asr']['language_plan'],
  'language_analysis_group':'mixed_translation' if source['explicit_translation_label'] else 'english_assumption_or_platform_label',
  'asr_model':rec['binding']['asr']['model'],'asr_language_reported':rec['asr']['language_reported'],
  'speaker_diarization_performed':False,'retained_new_decoded_pcm':False,
  'unretained_derivatives':[x for x in rec['verified_artifacts'] if not x.get('retained',True)],
  'rights_and_access_basis':'Public original-publisher media; private research retention, no unrestricted transcript republication/training license',
  'alternate_edition_only':alternate}
 return out
preferred=[]
for f in frame:
 vid=f['video_id'];state=dispositions[vid]
 if vid in captions:record=inherited(vid,captions[vid])
 elif vid=='392834325':record=inherited(vid,pilot)
 elif state.get('status')=='completed':record=local(vid,state)
 else:record={**common(vid),'source_id':'vimeo:'+vid+':text-unavailable','source_kind':'machine_asr','collection_status':'not_retrieved','hold_reason':exclusion['status'] if vid==exclusion['video_id'] else state['status'],'text_artifact':None,'evidence':[]}
 preferred.append(record)
paired=[];pairs=[]
for item in queue.get('paired_sensitivity',[]):
 vid=item['video_id']
 if item['status']=='completed':
  alt=local(vid,item,alternate=True);paired.append(alt);pairs.append({'session_id':'vimeo:'+vid,'preferred_source_id':next(r['source_id'] for r in preferred if r['session_id']=='vimeo:'+vid),'alternate_source_id':alt['source_id']})
A.atomic_json(OUT/'paired-editions-manifest.json',{'schema_version':1,'kind':'caption-local-ASR-sensitivity-editions','records':paired,'pairs':pairs,'selection':queue['paired_selection'],
 'scope':'Two machine transcript editions of the same public recording; disagreement is not accuracy or ground-truth WER.'})
A.atomic_json(OUT/'audio-dispositions-manifest.json',{'schema_version':1,'kind':'adjudicated-public-Vimeo-audio-acquisition','records':[{'source_id':'vimeo:'+r['video_id'],**common(r['video_id']),'original_acquisition_status':audio_rows[r['video_id']]['status'],'collection_status':'retrieved' if audio_rows[r['video_id']]['status']=='completed' else ('excluded' if r['video_id']==exclusion['video_id'] else 'unresolved')} for r in frame],'source_manifest':artifact(media_manifest,'selected_acquisition_manifest'),'superseded_media':unadmitted,'media_integrity_audit':artifact(args.media_integrity_audit,'media_integrity_audit'),'boundary_exclusion':artifact(exclusion_path,'boundary_exclusion') if exclusion['video_id'] else None,'scope':'Original acquisition receipts unchanged; boundary artifact remains physically retained but unadmitted.'})
summary={'publication_count':len(preferred),'audio_retained_count':sum(r['audio_collection_status']=='completed' for r in preferred),'audio_retained_bytes':sum(r.get('audio_bytes',0) for r in preferred),
 'unadmitted_audio_retained_count':len(unadmitted),'unadmitted_audio_retained_bytes':sum(x['artifact']['bytes'] for x in unadmitted),
 'distinct_qualifying_audio_hashes':len({r['audio_artifact']['sha256'] for r in preferred if r.get('audio_artifact')}),
 'preferred_text_count':sum(r['collection_status']=='retrieved' for r in preferred),'preferred_text_words':sum(r.get('asr_words',0) for r in preferred),
 'preferred_transcript_origins':dict(collections.Counter(r.get('transcript_origin','unavailable') for r in preferred)),
 'language_groups':dict(collections.Counter(r.get('language_analysis_group','unavailable') for r in preferred)),
 'source_formats':dict(collections.Counter(r['source_format'] for r in preferred)),'alternative_local_ASR_editions':len(paired)}
A.atomic_json(OUT/'manifest.json',{'schema_version':1,'kind':'official-public-Vimeo-publications-selected-text','records':preferred,'summary':summary,
 'created_at':A.now(),'source_manifests':[artifact(media_manifest,'audio_acquisition_frame'),artifact(queue_manifest,'local_ASR_dispositions'),artifact(caption_manifest,'platform_caption_editions')],
 'media_integrity_audit':artifact(args.media_integrity_audit,'media_integrity_audit'),'unadmitted_retained_editions':unadmitted,'normalization_code':artifact(pathlib.Path(__file__),'executed_code'),'validation_core':artifact(CORE,'validation_code'),'paired_editions':artifact(OUT/'paired-editions-manifest.json','sensitivity_manifest'),
 'scope':'All inspected public-profile publication dispositions, one preferred text edition where available; mixed translation/context formats explicit, no all-historical-Bashar/full-session claim.'})
print(json.dumps(summary,indent=2))
