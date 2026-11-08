#!/usr/bin/env python3
"""Separate, provenance-bound study of publisher-selected Bashar speech clips.

Projects excerpts into the frozen baseline; never promotes an excerpt to a full
session. No acquisition, ASR, training, public full text or identity inference.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import gzip
import html
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata
import warnings
import numpy as np
import analyze as A

BASELINE_SHA='e9e88095a5264ff588c52e9d9edb23bbffa57ca1e86b24b997057e08035aa476'
BASELINE_CODE_SHA='6f4d9ab73ad479b7d84e7a299a5c74276847d961030d98cdb2ad059b40b30506'
AUDIO_VERIFIER_SHA='7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64'
KNOWN_INCOMPLETE_MEDIA={
    '054f659907612604c5b133cf41f3d5a705a9c1bcc0cadbcb7da0efa1130b150d':{
        'publication_id':'vimeo:204089777','reason':'HTTP 503 during acquisition and a missing packet interval of 5.994667 seconds; strict reacquisition required.',
        'download_log_sha256':'d3496c1cd74e372e2a2bd9f27f9f32d50168aa703e92eaf9be280df4e46ee9eb',
        'packet_audit_sha256':'a04ecd79c28c38cf8f9a72484f4f39e1bccb1c62be8cdbcb596d18aec6f6e4e8'}}
COLORS={'ra_published':'#286571','bashar_context':'#91512f','official_excerpt':'#765192',
        'official_promotion':'#ad7731','official_greeting':'#728248','official_other':'#6c7078','official_translated':'#567098'}
LABELS={'ra_published':'Ra edited','bashar_context':'Bashar-related','official_excerpt':'Official excerpts',
        'official_promotion':'Official promo/product','official_greeting':'Official greetings','official_other':'Official unclassified','official_translated':'Translated excerpts'}

def bounded_seconds(value):
    p=value.split(':')
    if len(p) not in (2,3):raise ValueError('Invalid caption timestamp')
    p=list(map(float,p));v=p[-1]+p[-2]*60+(p[-3]*3600 if len(p)==3 else 0)
    if not math.isfinite(v) or v<0 or p[-1]>=60 or p[-2]>=60:raise ValueError('Invalid caption timestamp')
    return v

def parse_vtt(raw,duration):
    text=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    if not text.startswith('WEBVTT'):raise ValueError('Caption source is not WebVTT')
    rows=[];previous=-1
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines()
        if not lines or lines[0].startswith(('WEBVTT','NOTE','STYLE','REGION')):continue
        pos=next((i for i,line in enumerate(lines[:2]) if '-->' in line),None)
        if pos is None:raise ValueError('Unknown WebVTT block')
        left,right=lines[pos].split('-->',1);start=bounded_seconds(left.strip());end=bounded_seconds(right.strip().split()[0])
        if start<previous or end<start or end>duration+2:raise ValueError('Caption timestamps exceed ordered excerpt coverage')
        body=html.unescape(re.sub(r'<[^>]*>','','\n'.join(lines[pos+1:]))).strip()
        if body:rows.append({'start_seconds':start,'end_seconds':end,'text':body})
        previous=start
    if not rows:raise ValueError('Empty caption stream')
    return rows

def validate_turns(turns,original,duration):
    if len(turns)!=len(original):raise ValueError('Normalized segment count differs')
    seen=set();previous=-1
    for turn,source in zip(turns,original):
        if turn.get('role')!='unknown' or not turn.get('turn_id') or turn['turn_id'] in seen:raise ValueError('Speaker role or turn identity changed')
        seen.add(turn['turn_id'])
        for key in ('text','start_seconds','end_seconds'):
            if turn.get(key)!=source.get(key):raise ValueError('Normalized source text or timing changed')
        start=A.number(turn['start_seconds'],'Start',allow_none=False);end=A.number(turn['end_seconds'],'End',allow_none=False)
        if start<previous or end<start or end>duration+2:raise ValueError('ASR time outside ordered excerpt')
        previous=start

def evidence_by_role(row,cache,allow_fixtures):
    roles=defaultdict(list)
    for ref in row.get('evidence',[]):
        p=A.artifact(ref,private=True,cache=cache)
        if not isinstance(ref.get('role'),str):raise ValueError('Evidence role required')
        if p.suffix=='.json' and p.stat().st_size<16*1024**2 and A.fixture(A.read_json(p)) and not allow_fixtures:raise ValueError('Fixture evidence cannot become an observation')
        if not any(same_artifact(ref,old) for old in roles[ref['role']]):roles[ref['role']].append(ref)
    return roles

def one(roles,key):
    if len(roles[key])!=1:raise ValueError('Exactly one '+key+' is required')
    return roles[key][0]

def same_artifact(a,b):return all(a.get(k)==b.get(k) for k in ('path','bytes','sha256'))

def check_media_integrity(digest):
    if digest in KNOWN_INCOMPLETE_MEDIA:raise ValueError('Known incomplete encoded media; use a new strictly acquired edition')

def check_decode_duration(source_duration,decoded_duration):
    if abs(source_duration-decoded_duration)>2:raise ValueError('Decoded/source duration gap exceeds 2 seconds and requires independent source-integrity review')

def check_packet_continuity(probe,tolerance=.05):
    rows=probe.get('packets',[])
    if not rows:raise ValueError('Positive integrity audit requires audio packets')
    durations=[float(p.get('duration_time',0)) for p in rows]
    positive=[v for v in durations if v>0 and math.isfinite(v)]
    if not positive:raise ValueError('Packet durations unavailable')
    fallback=statistics.median(positive);previous_start=None;previous_end=None
    for p,duration in zip(rows,durations):
        start=float(p['pts_time']);duration=duration or fallback
        if not math.isfinite(start) or not math.isfinite(duration) or duration<0:raise ValueError('Nonfinite or negative packet timing')
        if previous_start is not None and start<previous_start-.001:raise ValueError('Audio packet timestamp order changed')
        if previous_end is not None and start-previous_end>tolerance:raise ValueError('Packet gap in a claimed passed audio edition')
        previous_start=start;previous_end=start+duration
    container=A.number(float(probe.get('format',{}).get('duration','nan')),'Packet container duration',allow_none=False)
    if container<=0 or abs(float(rows[0]['pts_time']))>tolerance:raise ValueError('Audio packet initial boundary differs from zero')
    if abs(previous_end-container)>tolerance:raise ValueError('Audio packet terminal boundary differs from container duration')
    return len(rows)

def verify_integrity_audit(path,publications):
    audit=A.read_json(path,private=True);cache={}
    if audit.get('schema_version')!=1 or audit.get('kind')!='publisher-audio-fragment-and-packet-audit' or A.fixture(audit):raise ValueError('A real versioned media-integrity audit is required')
    tolerance=audit.get('protocol',{}).get('gap_tolerance_seconds')
    if isinstance(tolerance,bool) or not isinstance(tolerance,(int,float)) or not 0<=tolerance<=.05:raise ValueError('Packet gap tolerance cannot exceed 50 milliseconds')
    for key in ('code','helper_code','source_manifest'):A.artifact(audit[key],cache=cache)
    records=defaultdict(list)
    for row in audit.get('records',[]):records[(row.get('publication_id'),row.get('audio_sha256'))].append(row)
    checked_media={};accepted=[]
    for d in publications:
        s=d['summary'];digest=s.get('source_audio_sha256');matches=records[(s['publication_id'],digest)]
        if not digest or len(matches)!=1:raise ValueError('Every admitted publication/media edition requires one exact integrity-audit record')
        row=matches[0]
        if row.get('disposition')!='passed' or row.get('integrity_status')!='passed' or row.get('transport_error_recorded') is not False:raise ValueError('Official source edition has no passed acquisition-integrity audit')
        audio=row['source_audio'];A.artifact(audio,private=True,cache=cache)
        if audio['sha256']!=digest:raise ValueError('Integrity-audit audio binding differs')
        acquisition=row.get('acquisition_receipt');A.artifact(acquisition,private=True,cache=cache)
        original=A.read_json(acquisition['path'])
        if original.get('source_id')!=s['publication_id'] or not same_artifact(original.get('audio',{}),audio):raise ValueError('Audit publication/acquisition binding differs')
        log=row.get('download_log')
        if log:
            p=A.artifact(log,private=True,cache=cache)
            if re.search(r'HTTP Error\s+[45][0-9][0-9]|unavailable fragment|Skipping fragment|Got error',p.read_text(),re.I):raise ValueError('Transport-error log cannot pass unchanged')
        elif row.get('log_path') and A.safe_path(row['log_path'],private=True,exists=False).exists():raise ValueError('An unbound downloader log appeared after audit')
        if digest not in checked_media:
            packet=A.artifact(row['raw_packet_probe'],private=True,cache=cache)
            with gzip.open(packet,'rb') as stream:raw=stream.read(32*1024**2+1)
            if len(raw)>32*1024**2 or len(raw)!=row.get('raw_uncompressed_bytes') or hashlib.sha256(raw).hexdigest()!=row.get('raw_uncompressed_sha256'):raise ValueError('Raw packet evidence bytes changed')
            count=check_packet_continuity(json.loads(raw),tolerance)
            if count!=row.get('packet_summary',{}).get('packet_count'):raise ValueError('Packet-audit summary count differs')
            checked_media[digest]=count
        accepted.append({'publication_id':s['publication_id'],'audio_sha256':digest,'packet_count':checked_media[digest]})
    return {'status':'all_admitted_media_verified','audit_sha256':A.sha(path),'audit_edition_rows':len(audit['records']),
        'admitted_publications_verified':len(accepted),'distinct_media_verified':len(checked_media),'packet_gap_tolerance_seconds':tolerance,
        'verified_publications':accepted,'scope':'Exact media bytes, retained logs and every first-audio-stream packet interval including initial/terminal boundaries; not historical session completeness, transcript accuracy or voice identity.'}

def verify_audio_completion(path,binding):
    """Reuse the pinned, read-only producer verifier including PCM disposition."""
    module_path=Path(__file__).resolve().parents[1]/'batch-media'/'audio.py'
    if A.sha(module_path)!=AUDIO_VERIFIER_SHA:raise ValueError('Pinned ASR completion verifier changed; explicit review required')
    spec=importlib.util.spec_from_file_location('bashar_ra_audio_completion_verifier',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.verify_completed(Path(path),binding)

def validate_caption(row,doc,roles):
    ref=one(roles,'caption_acquisition_receipt');receipt=A.read_json(ref['path']);source=one(roles,'source_caption');player=one(roles,'player_metadata')
    if receipt.get('source_id')!=row['source_id'] or receipt.get('http_status')!=200 or receipt.get('caption_language_label')!='en-x-autogen':raise ValueError('Caption identity, status or machine-language label differs')
    if not same_artifact(receipt.get('caption_artifact',{}),source) or not same_artifact(receipt.get('player_metadata',{}),player):raise ValueError('Caption receipt source bindings differ')
    metadata=A.read_json(player['path']);vid=row['session_id'].split(':')[-1]
    if str(metadata.get('id'))!=vid or metadata.get('uploader_id')!='basharcommunications':raise ValueError('Publisher player identity differs')
    duration=A.number(receipt.get('duration_seconds'),'Caption duration',allow_none=False)
    if abs(duration-float(metadata.get('duration',-1)))>2:raise ValueError('Player/caption duration mismatch')
    original=parse_vtt(Path(source['path']).read_bytes(),duration);validate_turns(doc['turns'],original,duration)
    if receipt.get('cues')!=len(original) or receipt.get('words')!=len(doc['text'].split()):raise ValueError('Caption receipt counts differ')
    if row.get('edition_id')!=source['sha256']:raise ValueError('Caption edition hash differs')
    media_sha=None;measured_duration=None
    if str(row.get('duplicate_family_id','')).startswith('exact-media:'):
        audio=one(roles,'source_audio');acquisition=A.read_json(one(roles,'acquisition_receipt')['path'])
        if acquisition.get('source_id')!=row['session_id'] or acquisition.get('status')!='completed' or not same_artifact(acquisition.get('audio',{}),audio):raise ValueError('Caption publication acquired-media binding differs')
        if row['duplicate_family_id']!='exact-media:'+audio['sha256']:raise ValueError('Caption exact-media family not bound to retained audio')
        check_media_integrity(audio['sha256'])
        media_sha=audio['sha256'];measured_duration=A.number(acquisition.get('duration_seconds'),'Measured source duration',allow_none=False)
        if abs(measured_duration-duration)>2:raise ValueError('Acquired audio and caption-player duration differ')
    return {'transcription_origin':'platform_auto_caption','model':'Unknown Vimeo automatic caption model',
            'duration_seconds':measured_duration or duration,'source_audio_sha256':media_sha,'decoded_duration_seconds':None,'duration_after_vad_seconds':None,
            'language_basis':row.get('language_basis'),'original_text_sha256':source['sha256']}

def validate_local_asr(row,doc,roles,cache):
    receipt_ref=one(roles,'asr_receipt');receipt=A.read_json(receipt_ref['path']);source=one(roles,'asr_segments')
    execution_id=row.get('asr_receipt_source_id',row['source_id'])
    if execution_id!=row['session_id']:raise ValueError('Executed ASR source must map to the declared publication')
    if row['source_id']!=execution_id and row['source_id']!=execution_id+':local-asr:'+str(receipt.get('binding_sha256',''))[:16]:raise ValueError('ASR edition ID must identify the executed binding without rewriting source receipts')
    if receipt.get('kind')!='source-bound-audio-analysis' or receipt.get('status')!='completed' or receipt.get('source_id')!=execution_id:raise ValueError('Completed local ASR identity required')
    binding=receipt.get('binding',{});bound_source=binding.get('source',{})
    check_media_integrity(bound_source.get('sha256'))
    if hashlib.sha256(A.encoded(binding).encode()).hexdigest()!=receipt.get('binding_sha256'):raise ValueError('Executed ASR binding hash differs')
    if bound_source.get('source_id')!=execution_id or bound_source.get('provider')!='publisher_audio':raise ValueError('ASR is not bound to the official publication')
    proof_ref=one(roles,'source_verification');proof=A.read_json(proof_ref['path']);link=bound_source.get('verification_receipt',{})
    if link.get('path')!=proof_ref['path'] or link.get('sha256')!=proof_ref['sha256']:raise ValueError('Executed publisher verification proof differs')
    if not any(p.get('source_id')==execution_id and p.get('sha256')==bound_source.get('sha256') and p.get('local_path')==bound_source.get('local_path') and p.get('status')=='verified' for p in proof.get('verified_artifacts',[])):raise ValueError('Publisher proof does not bind original media')
    acquisition=one(roles,'acquisition_receipt');link=proof.get('acquisition_receipt',{})
    if link.get('path')!=acquisition['path'] or link.get('sha256')!=acquisition['sha256']:raise ValueError('Publisher acquisition proof differs')
    verify_audio_completion(receipt_ref['path'],binding)
    expected=[]
    for item in receipt.get('verified_artifacts',[]):
        if item.get('retained',True) is False:continue
        ref={'path':item.get('local_path'),'bytes':item.get('bytes'),'sha256':item.get('sha256')}
        expected.append(ref)
    if not any(same_artifact(source,item) for item in expected):raise ValueError('ASR segment artifact not in executed receipt')
    if not any(item.get('path')==bound_source.get('local_path') and item.get('sha256')==bound_source.get('sha256') and item.get('bytes')==bound_source.get('bytes') for item in expected):raise ValueError('Original media missing from ASR receipt')
    original=A.read_json(source['path'])
    if original.get('source_id')!=execution_id or original.get('text')!=doc['text']:raise ValueError('ASR original full text changed')
    duration=A.number(receipt.get('decoded_duration_seconds'),'Decoded duration',allow_none=False)
    validate_turns(doc['turns'],original.get('segments',[]),duration)
    info=receipt.get('asr',{})
    if info.get('segments')!=len(doc['turns']) or info.get('whitespace_word_count')!=len(doc['text'].split()):raise ValueError('ASR receipt counts differ')
    source_duration=A.number(bound_source.get('duration_seconds'),'Source duration',allow_none=False)
    check_decode_duration(source_duration,duration)
    if row.get('duplicate_family_id') and row['duplicate_family_id']!='exact-media:'+bound_source['sha256']:raise ValueError('Local-ASR exact-media family differs from executed audio')
    return {'transcription_origin':'local_asr','model':binding.get('asr',{}).get('model',{}).get('model_name'),
            'source_audio_sha256':bound_source['sha256'],
            'executed_source_id':execution_id,'executed_binding_sha256':receipt['binding_sha256'],'completion_verifier_sha256':AUDIO_VERIFIER_SHA,
            'decoded_pcm_retained':not any(x.get('retained',True) is False for x in receipt.get('verified_artifacts',[])),
            'model_files_sha256':binding.get('asr',{}).get('model',{}).get('files_sha256'),
            'model_language_mode':binding.get('asr',{}).get('model',{}).get('language_mode'),
            'asr_settings':{k:binding.get('asr',{}).get(k) for k in ('device','compute_type','beam_size','temperature','vad_filter','min_silence_duration_ms')},
            'duration_seconds':source_duration,'decoded_duration_seconds':duration,'container_minus_decoded_seconds':source_duration-duration,
            'duration_tolerance':'Analysis admission additionally requires decoded/container difference at most 2 seconds; this is not timestamp equivalence or a completeness guarantee.',
            'timestamp_clock':'Local ASR uses the decoded PCM sample clock, not a validated alignment to source container presentation timestamps.',
            'duration_after_vad_seconds':info.get('duration_after_vad_seconds'),
            'language_basis':info.get('language_plan'),'original_text_sha256':source['sha256']}

def classify(row):
    value=str(row.get('source_format') or '')
    if row.get('explicit_translation_label') or 'translated' in value:return 'official_translated'
    if any(word in value for word in ('promo','trailer','advertisement','product_introduction','product_explainer')):return 'official_promotion'
    if any(word in value for word in ('greeting','holiday_message')):return 'official_greeting'
    if 'excerpt' in value:return 'official_excerpt'
    return 'official_other'

def timing_coverage(turns,duration):
    intervals=sorted((t['start_seconds'],min(t['end_seconds'],duration)) for t in turns);total=0;last=-1
    for start,end in intervals:
        total+=max(0,end-max(start,last));last=max(last,end)
    return {'cue_interval_union_seconds':total,'cue_interval_fraction':total/duration if duration else None,
            'first_cue_seconds':intervals[0][0] if intervals else None,'last_cue_seconds':max((b for a,b in intervals),default=None),
            'interpretation':'Cue interval coverage is not recognized-speech recall; silence, music, VAD omissions and caption gaps are unresolved.'}

def edit_disagreement(caption,local):
    """Token edit distance between two machine editions, not accuracy/WER."""
    a=A.tokens(caption);b=A.tokens(local);previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    distance=previous[-1]
    return {'caption_tokens':len(a),'local_asr_tokens':len(b),'token_edit_distance':distance,
        'distance_per_caption_token':distance/len(a) if a else None,
        'normalization':'Baseline NFKC, lowercase ASCII letter tokens with internal straight apostrophes; punctuation removed, no stopword removal.',
        'interpretation':'Machine-to-machine edition disagreement. Neither transcript is verified ground truth; this is not ASR accuracy.'}

def load_official(paths,*,allow_fixtures=False):
    docs=[];held=[];audit=[];cache={};seen=set();editions=defaultdict(list)
    for path in paths:
        path=A.safe_path(path,private=True);manifest=A.read_json(path)
        if manifest.get('schema_version')!=1 or not isinstance(manifest.get('records'),list):raise ValueError('Versioned official source records required')
        if A.fixture(manifest) and not allow_fixtures:raise ValueError('Synthetic manifest cannot be analyzed as actual speech')
        audit.append({'path':str(path),'sha256':A.sha(path),'kind':manifest.get('kind'),'records':len(manifest['records'])})
        for row in manifest['records']:
            sid=row.get('source_id');pub=row.get('session_id')
            if not isinstance(sid,str) or not re.fullmatch(r'vimeo:\d+(?::[A-Za-z0-9_.:-]+)?',sid) or not isinstance(pub,str) or not re.fullmatch(r'vimeo:\d+',pub):raise ValueError('Explicit Vimeo source/publication identifiers required')
            if sid in seen:raise ValueError('Duplicate source ID; supply one explicit edition record')
            seen.add(sid)
            if row.get('collection_status')!='retrieved' or not row.get('text_artifact'):
                held.append({'source_id':sid,'publication_id':pub,'status':row.get('collection_status'),'reason':row.get('hold_reason','No retained transcript artifact')});continue
            if row.get('source_kind')!='machine_asr' or row.get('corpus')!='bashar':raise ValueError('Official speech study accepts documentary machine text only')
            if row.get('language')!='en':
                held.append({'source_id':sid,'publication_id':pub,'collection_status':row.get('collection_status'),'language':row.get('language'),'source_format':row.get('source_format'),'reason':'Excluded from English analysis; not a failed acquisition or transcription claim.'});continue
            p=A.artifact(row['text_artifact'],private=True,cache=cache);doc=A.read_json(p)
            if A.fixture(doc) and not allow_fixtures:raise ValueError('Synthetic normalized text rejected')
            if doc.get('source_id')!=sid or not isinstance(doc.get('text'),str) or not isinstance(doc.get('turns'),list) or doc['text']!='\n'.join(t['text'] for t in doc['turns']):raise ValueError('Normalized identity or ordered full text changed')
            roles=evidence_by_role(row,cache,allow_fixtures)
            proof=validate_caption(row,doc,roles) if roles['source_caption'] else validate_local_asr(row,doc,roles,cache)
            tt=A.tokens(doc['text'])
            if len(tt)<30:
                held.append({'source_id':sid,'publication_id':pub,'reason':'Fewer than 30 analysis tokens'});continue
            summary={k:row.get(k) for k in ('source_id','source_kind','source_format','title','publisher','published_at','edition_id','coverage_status','coverage_scope','duplicate_family_id','duplicate_family_basis','original_session_identity','speaker_attribution_status','session_id_basis')}
            summary.update(publication_id=pub,session_id=pub,corpus='bashar',stratum=classify(row),source_url=A.safe_url(row.get('source_url')),
                token_count=len(tt),whitespace_words=len(doc['text'].split()),turn_count=len(doc['turns']),
                source_family_id=row.get('source_family_id'),source_family_basis=row.get('source_family_basis'),product_url=A.safe_url(row.get('product_url')),
                text_sha256=hashlib.sha256(doc['text'].encode()).hexdigest(),text_artifact_sha256=row['text_artifact']['sha256'],evidence_sha256=[x['sha256'] for x in row['evidence']],
                human_accuracy_validated=False,unit='publisher_selected_public_clip',**proof,
                timing=timing_coverage(doc['turns'],proof['duration_seconds']))
            d={'summary':summary,'text':doc['text'],'tokens':tt,'turns':doc['turns']};editions[pub].append(d)
    suppressed=[]
    for pub,values in sorted(editions.items()):
        # A deterministic edition choice is not an accuracy claim. All editions
        # remain in the private manifests; publication-level fits count one.
        values.sort(key=lambda d:(d['summary']['transcription_origin']!='platform_auto_caption',d['summary']['source_id']))
        docs.append(values[0])
        for other in values[1:]:
            item={'publication_id':pub,'retained_source_id':values[0]['summary']['source_id'],'alternate_source_id':other['summary']['source_id'],'alternate_text_artifact_sha256':other['summary']['text_artifact_sha256'],'reason':'One edition per publication; platform track preferred by declared policy, not validated accuracy.'}
            if values[0]['summary']['transcription_origin']=='platform_auto_caption' and other['summary']['transcription_origin']=='local_asr':item['machine_edition_disagreement']=edit_disagreement(values[0]['text'],other['text'])
            suppressed.append(item)
    return docs,held,suppressed,audit

def mask(text):return A.mask_source_markers(text)

def window_tokens(doc,n=400):
    if len(doc['tokens'])<n:return None
    start=(len(doc['tokens'])-n)//2;return doc['tokens'][start:start+n]

def window_text(doc,n=400):
    """Contiguous token-bounded source span; keep interior punctuation/numbers."""
    text=unicodedata.normalize('NFKC',doc['text']).replace('’',"'")
    matches=list(A.TOKEN.finditer(text))
    if len(matches)!=len(doc['tokens']):raise ValueError('Source offsets differ from declared analysis tokenization')
    if len(matches)<n:return None
    start=(len(matches)-n)//2
    return text[matches[start].start():matches[start+n-1].end()]

def disposition_counts(clips,held):
    admitted={d['summary']['publication_id'] for d in clips};held_ids={r['publication_id'] for r in held}
    return {'admitted_publications':len(admitted),'held_publications':len(held_ids-admitted),
            'held_editions':len(held),'observed_publication_dispositions':len(admitted|held_ids)}

def collapse_exact_media(publications):
    """One model unit per verified encoded-media hash; preserve all uploads."""
    groups=defaultdict(list)
    for d in publications:
        s=d['summary'];key=('media:'+s['source_audio_sha256']) if s.get('source_audio_sha256') else 'publication:'+s['publication_id']
        groups[key].append(d)
    chosen=[];aliases=[];families=[]
    for key,rows in sorted(groups.items()):
        rows.sort(key=lambda d:(d['summary']['transcription_origin']!='platform_auto_caption',d['summary']['source_id']))
        keep=rows[0];sid=keep['summary']['source_id']
        if len({d['summary']['stratum'] for d in rows})>1:raise ValueError('An exact-media family has conflicting source-genre labels; explicit review required')
        chosen.append(keep)
        for d in rows:
            d['summary'].update(model_unit_source_id=sid,included_in_model=d is keep)
            if d is not keep:aliases.append({'source_id':d['summary']['source_id'],'publication_id':d['summary']['publication_id'],'model_unit_source_id':sid,'reason':'Identical verified encoded audio bytes; one model unit, all publication records preserved.'})
        if key.startswith('media:'):families.append({'audio_sha256':key.removeprefix('media:'),'publication_ids':[d['summary']['publication_id'] for d in rows],'source_ids':[d['summary']['source_id'] for d in rows],'model_unit_source_id':sid})
    chosen.sort(key=lambda d:d['summary']['source_id'])
    return chosen,aliases,families

def stratified_pairs(matrix,docs,valid=None):
    valid=[True]*len(docs) if valid is None else valid
    rows=defaultdict(list)
    for i in range(len(docs)):
        for j in range(i+1,len(docs)):
            if not valid[i] or not valid[j]:continue
            key=tuple(sorted((docs[i]['summary']['stratum'],docs[j]['summary']['stratum'])))
            rows[key].append(float(matrix[i,j]))
    return [{'strata':list(k),'pairs':len(v),'mean':float(np.mean(v)),'minimum':min(v),'maximum':max(v)} for k,v in sorted(rows.items())]

def keywords(docs):
    rows=[]
    for key,group in group_by_stratum(docs).items():
        total=sum(len(d['tokens']) for d in group)
        for theme in A.KEYWORDS:
            rates=[A.keyword_rates(d['tokens'])[theme] for d in group];mentions=sum(r['mentions'] for r in rates)
            rows.append({'stratum':key,'keyword_group':theme,'documents':len(group),'mentions':mentions,'analysis_tokens':total,
                'equal_document_mean_per_1000':float(np.mean([r['per_1000_tokens'] for r in rates])),
                'pooled_token_rate_per_1000':mentions*1000/total,'documents_with_mentions':sum(r['mentions']>0 for r in rates)})
    return rows

def group_by_stratum(docs):
    result=defaultdict(list)
    for d in docs:result[d['summary']['stratum']].append(d)
    return result

def projection_result(matrix,docs,baseline_count,valid=None):
    valid=[True]*len(docs) if valid is None else valid
    ids=[d['summary']['source_id'] for d in docs];nearest=[]
    for i in range(baseline_count,len(docs)):
        rows=[]
        for target in ('ra_published','bashar_context'):
            jj=[j for j in range(baseline_count) if valid[i] and valid[j] and docs[j]['summary']['stratum']==target]
            for j in sorted(jj,key=lambda j:-matrix[i,j])[:3]:rows.append({'source_id':ids[j],'stratum':target,'cosine':float(matrix[i,j])})
        nearest.append({'source_id':ids[i],'neighbors':rows})
    return {'source_ids':ids,'cosine_matrix':matrix.tolist(),'pair_summary':stratified_pairs(matrix,docs,valid),'nearest_baseline_sources':nearest,
            'zero_vector_source_ids':[sid for sid,ok in zip(ids,valid) if not ok],
            'zero_vector_convention':'Zero-norm rows, if present, use library zero matrix values but are excluded from pair summaries and nearest-source retrieval.',
            'interpretation':'Dependent document pairs and nearest reading leads; neither belief agreement nor probabilities.'}

def figures(output,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    artifacts=[]
    def save(fig,name,caption):
        fig.tight_layout()
        for ext in ('png','svg','pdf'):
            p=output/(name+'.'+ext);fig.savefig(p,dpi=170,metadata={'Title':caption});artifacts.append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'caption':caption})
        plt.close(fig)
    groups=result['coverage']['by_stratum'];labels=list(groups);x=np.arange(len(labels))
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for ax,key,title in zip(axes,('documents','whitespace_words'),('Documentary units','Whitespace words')):
        ax.bar(x,[groups[k][key] for k in labels],color=[COLORS.get(k,'#6c7078') for k in labels]);ax.set_xticks(x,[LABELS.get(s,s) for s in labels],rotation=25,ha='right');ax.set_title(title)
    save(fig,'official-coverage','Separate documentary model units: complete published sessions, mixed-context recordings and publisher-selected public clips; verified identical official encoded-media families count once. Publication counts remain separate in the data.')
    fig,ax=plt.subplots(figsize=(12,5));themes=list(A.KEYWORDS);lookup={(r['stratum'],r['keyword_group']):r for r in result['keyword_comparison']};width=.8/max(1,len(labels))
    for i,label in enumerate(labels):ax.bar(np.arange(len(themes))+(i-(len(labels)-1)/2)*width,[lookup[(label,t)]['equal_document_mean_per_1000'] for t in themes],width,color=COLORS.get(label,'#6c7078'),label=LABELS.get(label,label))
    ax.set_xticks(np.arange(len(themes)),[t.replace('_',' ') for t in themes],rotation=30,ha='right');ax.set_ylabel('Mean word-form occurrences / 1,000 tokens');ax.legend(fontsize=8)
    save(fig,'official-keywords','Fixed keyword dictionaries applied separately; negation, speaker mixing and polysemy prevent interpreting rates as validated beliefs.')
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True)
    for ax,field,title in zip(axes,('full_projection','window_400_projection'),('All available transcript text','Centered 400-token windows')):
        rows=[r for r in result['lexical'][field]['pair_summary'] if any(s.startswith('official_') for s in r['strata']) and len(set(r['strata']))>1]
        ax.barh(range(len(rows)),[r['mean'] for r in rows],color='#765192');ax.set_yticks(range(len(rows)),[' / '.join(LABELS.get(s,s) for s in r['strata']) for r in rows],fontsize=8);ax.set_xlabel('Mean TF-IDF cosine; shared scale');ax.set_title(title)
    save(fig,'official-projection','Official clips are projected into frozen baseline vocabulary/IDF; equal-length windows are a sensitivity, not matched speakers or historical contexts.')
    sem=result.get('semantic',{})
    if sem.get('status')=='frozen_local_inference_complete':
        fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(sem['cosine_matrix'],vmin=-1,vmax=1,cmap='coolwarm');fig.colorbar(im,ax=ax,label='Frozen MiniLM cosine');ax.set_title('Baseline + official clips: complete chunk coverage');ax.set_xlabel('Document index; strata in data');ax.set_ylabel('Document index')
        save(fig,'official-semantic','General-purpose embeddings are a separate sensitivity; no equivalence, agreement probability or claimed-identity validation.')
    return artifacts

def study(baseline_json,baseline_manifests,official_manifests,model_dir,cache_dir,output,*,phase='pilot',expected_publications=None,source_frame=None,integrity_audit=None):
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import NMF
    if A.sha(baseline_json)!=BASELINE_SHA or A.sha(Path(A.__file__))!=BASELINE_CODE_SHA:raise ValueError('Frozen baseline analysis/code changed')
    baseline=A.read_json(baseline_json);allbase,_,_,base_audit=A.load_manifests(baseline_manifests)
    original_base_rows={r['source_id']:r for p in baseline_manifests for r in A.read_json(p)['records']}
    base=[d for d in allbase if d['summary']['source_kind']!='authored_reference'];expected={d['source_id']:d for d in baseline['documents'] if d['unit']!='reference_document'}
    if {d['summary']['source_id'] for d in base}!=set(expected):raise ValueError('Baseline source set differs')
    for d in base:
        s=d['summary']
        if s['text_sha256']!=expected[s['source_id']]['text_sha256']:raise ValueError('Baseline text edition changed')
        s['stratum']='ra_published' if s['corpus']=='ra' else 'bashar_context'
        s.update(model_unit_source_id=s['source_id'],included_in_model=True)
        if s['corpus']=='bashar':
            ref=next(r for r in original_base_rows[s['source_id']]['evidence'] if r['role']=='asr_receipt');receipt=A.read_json(ref['path'])
            s.update(transcription_origin='retained_local_asr',model=receipt.get('modelId'),model_revision=receipt.get('modelRevision'),asr_settings=receipt.get('decoding'),reported_language=receipt.get('reportedLanguage'))
    clips,held,editions,audit=load_official(official_manifests)
    if not clips:raise ValueError('No validated official clip text')
    observed={d['summary']['publication_id'] for d in clips}|{r['publication_id'] for r in held}
    if phase=='final' and (expected_publications is None or len(observed)!=expected_publications):raise ValueError('Final study requires explicit dispositions for every expected publication')
    frame_binding=None
    if source_frame is not None:
        frame=A.read_json(source_frame);expected_ids={'vimeo:'+str(r['video_id']) for r in frame['records'] if r.get('status')=='retrieved' and r.get('duration_seconds',0)>=300}
        if phase=='final' and observed!=expected_ids:raise ValueError('Final publication dispositions differ from frozen player source frame')
        if not observed<=expected_ids:raise ValueError('Official publication absent from source frame')
        frame_binding={'sha256':A.sha(source_frame),'expected_publication_ids':sorted(expected_ids),'classification_scope':'Publisher-title/description screening, not verified historical full-session identity.'}
        frame_rows={'vimeo:'+str(r['video_id']):r for r in frame['records']}
        for d in clips:
            s=d['summary'];source=frame_rows[s['publication_id']]
            if s['duration_seconds']<300:raise ValueError('An admitted clip is below the measured five-minute threshold; preserve an explicit exclusion')
            if abs(s['duration_seconds']-float(source['duration_seconds']))>2:raise ValueError('Measured media duration differs from frozen player duration; source-integrity review required')
            s['source_format']=source['source_format'];s['stratum']=classify(source)
    elif phase=='final':raise ValueError('Final publication coverage needs a frozen player source frame')
    if phase=='final' and integrity_audit is None:raise ValueError('Final study requires the positive media-fragment/log integrity audit')
    integrity=verify_integrity_audit(integrity_audit,clips) if integrity_audit is not None else {'status':'not_run_in_initial_pilot'}
    publications=clips;clips,media_aliases,media_families=collapse_exact_media(publications)
    docs=base+clips;output=A.safe_path(output,private=True,exists=False)
    if output.exists() and any(output.iterdir()):raise ValueError('Choose fresh study output')
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    oldfit,X,vec,chosen=A.fit_lexical(base,'name_masked')
    if X is None or not np.allclose(oldfit['cosine_matrix'],baseline['lexical']['variants']['name_masked']['cosine_matrix'],atol=1e-12):raise ValueError('Frozen lexical fit could not be reproduced')
    allX=vec.transform(' '.join(A.token_variant(d,'name_masked')) for d in docs);full=projection_result(np.clip(cosine_similarity(allX),0,1),docs,len(base),np.asarray(allX.getnnz(axis=1)>0).ravel())
    eligible=[d for d in docs if window_tokens(d) is not None];windowX=vec.transform(' '.join(t for t in window_tokens(d) if t not in A.NAMES and t not in A.FILLERS) for d in eligible)
    win=projection_result(np.clip(cosine_similarity(windowX),0,1),eligible,sum(d in base for d in eligible),np.asarray(windowX.getnnz(axis=1)>0).ravel());win['excluded_short_source_ids']=[d['summary']['source_id'] for d in docs if window_tokens(d) is None]
    model=NMF(n_components=baseline['topics']['displayed_k'],init='nndsvdar',random_state=11,max_iter=800,tol=1e-4)
    with warnings.catch_warnings(record=True) as fit_warnings:
        warnings.simplefilter('always');W=model.fit_transform(X)
    totals=W.sum(axis=1,keepdims=True);baseline_shares=np.divide(W,totals,out=np.zeros_like(W),where=totals>0)
    expected_shares=np.asarray([r['weights'] for r in baseline['topics']['document_weights']])
    if not np.allclose(baseline_shares,expected_shares,atol=1e-10):raise ValueError('Frozen baseline NMF shares could not be reproduced')
    with warnings.catch_warnings(record=True) as projection_warnings:
        warnings.simplefilter('always');clipW=model.transform(allX[len(base):])
    den=clipW.sum(axis=1,keepdims=True);shares=np.divide(clipW,den,out=np.zeros_like(clipW),where=den>0)
    topic_clips=[d for d in clips if d['summary']['stratum']=='official_excerpt']
    ownlex,ownX,ownvec,ownchosen=A.fit_lexical(topic_clips,'name_masked');own_topics,own_clusters=A.topic_and_clusters(ownX,ownvec,ownchosen) if ownX is not None else ({'status':'unavailable'},{'status':'unavailable'})
    own_topics['fit_scope']='Official excerpt model units after exact encoded-media grouping; greetings, product introductions/explainers and event promotions excluded. Clips remain dependent and selected.'
    print(json.dumps({'stage':'official_lexical_complete','clip_documents':len(clips)}),flush=True)
    encoder=A.FrozenEncoder(model_dir,cache_dir);encoded=encoder.encode([(d['summary']['source_id'],mask(d['text'])) for d in docs]);vectors=np.vstack([encoded[d['summary']['source_id']][0] for d in docs]);sem=projection_result(np.clip(cosine_similarity(vectors),-1,1),docs,len(base))
    baseline_cache_difference=float(np.max(np.abs(np.asarray(sem['cosine_matrix'])[:len(base),:len(base)]-np.asarray(baseline['semantic']['cosine_matrix']))))
    if baseline_cache_difference>2e-6:raise ValueError('Frozen baseline semantic vectors differ beyond cache precision')
    window_encoded=encoder.encode([('window400:'+d['summary']['source_id'],mask(window_text(d))) for d in eligible]);wv=np.vstack([window_encoded['window400:'+d['summary']['source_id']][0] for d in eligible]);wsem=projection_result(np.clip(cosine_similarity(wv),-1,1),eligible,sum(d in base for d in eligible))
    wsem['input_transformation']='Contiguous source span bounded by centered 400 analysis tokens; Unicode NFKC and curly-to-straight apostrophe normalization; interior punctuation, numbers and case retained; complete-token source mask. Shorter documents excluded.'
    sem.update(status='frozen_local_inference_complete',model=encoder.manifest,processing={**encoder.binding,'cache_storage_dtype':'float32','source_mask':baseline['semantic']['processing']['source_mask'],'source_mask_code_sha256':baseline['semantic']['processing']['source_mask_code_sha256'],'baseline_cache_maximum_absolute_cosine_difference':baseline_cache_difference},coverage=[{'source_id':sid,**v[2]} for sid,v in encoded.items()],window_400={**wsem,'coverage':[{'source_id':sid.removeprefix('window400:'),**v[2]} for sid,v in window_encoded.items()]})
    groups=group_by_stratum(docs);bystratum={k:{'documents':len(v),'whitespace_words':sum(d['summary']['whitespace_words'] for d in v),'analysis_tokens':sum(len(d['tokens']) for d in v)} for k,v in groups.items()}
    titles=defaultdict(list);families=defaultdict(list);text_families=defaultdict(list)
    for d in publications:
        s=d['summary'];titles[' '.join(A.tokens(s['title'] or ''))].append(s['source_id'])
        text_families[s['text_sha256']].append(s['source_id'])
        if s.get('source_family_id'):families[s['source_family_id']].append(s['source_id'])
    qa=[]
    for d in publications:
        _,c,counts=A.qa_records(d);qa.extend(c);d['summary']['qa']=counts
    result={'schema_version':1,'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':A.sha(Path(__file__)),
        'baseline_binding':{'analysis_sha256':BASELINE_SHA,'analysis_code_sha256':BASELINE_CODE_SHA,'primary_documents':len(base)},
        'run_scope':{'phase':phase,'expected_publications':expected_publications,**disposition_counts(publications,held),'model_clip_units':len(clips),'exact_media_aliases':len(media_aliases),'full_original_sessions_claimed':0,'source_frame':frame_binding},
        'documents':[d['summary'] for d in base+publications],'held':held,'edition_selection':editions,'media_aliases':media_aliases,
        'integrity_exclusions':[{'audio_sha256':k,**v} for k,v in KNOWN_INCOMPLETE_MEDIA.items()],
        'integrity_audit':integrity,
        'inputs':[{'sha256':r['sha256'],'kind':r.get('kind'),'records':r.get('records',r.get('record_count'))} for r in base_audit+audit],
        'coverage':{'by_stratum':bystratum,'unit':'Baseline session/recording units and official units after verified exact-media grouping.',
                    'official_publication_transcription_origins':dict(Counter(d['summary']['transcription_origin'] for d in publications)),
                    'official_transcription_origins':dict(Counter(d['summary']['transcription_origin'] for d in clips)),
                    'official_source_formats':dict(Counter(d['summary']['source_format'] for d in clips)),
                    'admitted_publication_whitespace_words':sum(d['summary']['whitespace_words'] for d in publications),
                    'modeled_clip_whitespace_words':sum(d['summary']['whitespace_words'] for d in clips)},
        'keyword_comparison':keywords(docs),'lexical':{'full_projection':full,'window_400_projection':win,'vocabulary_features':len(vec.get_feature_names_out()),'fit_scope':'Only the frozen 125 baseline documents fit vocabulary/IDF; official clips are projections.'},
        'topics':{'frozen_baseline_projection':{'components':baseline['topics']['components'],'document_weights':[{'source_id':d['summary']['source_id'],'weights':shares[i].tolist()} for i,d in enumerate(clips)],'baseline_refit_iterations':int(model.n_iter_),'baseline_refit_warning_count':len(fit_warnings),'projection_warning_count':len(projection_warnings),'fit_scope':'Frozen baseline NMF components; projected shares are not probabilities or evidence of equivalent topics.'},'official_only':own_topics,'official_only_clusters':own_clusters},
        'semantic':sem,'duplicate_diagnostics':A.near_duplicate_diagnostics(publications),
        'families':{'declared_source_families':dict(families),'exact_media_families':media_families,'unresolved_original_session_publications':sum(d['summary'].get('original_session_identity') in (None,'unresolved') for d in publications),
            'exact_text_families':[{'text_sha256':k,'source_ids':v} for k,v in text_families.items() if len(v)>1],
            'same_normalized_title_candidates':[{'title_key':k,'source_ids':v} for k,v in titles.items() if len(v)>1],
            'scope':'Publication IDs and exact media families are not independent historical sessions. Same-title and shingle-overlap candidates do not establish common product/session identity.'},
        'qa':{'unverified_punctuation_candidates':len(qa),'model_unit_punctuation_candidates':sum(d['summary']['qa']['punctuation_candidates'] for d in clips),'identified_answers':0,'speaker_diarization_performed':False},
        'limitations':['All official clips are publisher-selected public excerpts, promotions or greetings; complete paid/original session coverage is not claimed.',
            'Platform automatic captions and local English ASR have unvalidated errors, different models and unresolved language assumptions; mixed speakers are not diarized.',
            'Retained context ASR uses tiny.en beam 1; new English excerpt ASR uses tiny.en beam 5; platform settings are unknown. Recognition and source-stratum effects cannot be separated here.',
            'The 400-token window sensitivity equalizes selected text length only, not genre, date, host, editorial selection or source family dependence.',
            'Joint source strata and overlap pairs are dependent; no independent creator-population, p-values, origin probabilities or causal conclusions are estimated.',
            'Frozen MiniLM and lexical similarity are retrieval diagnostics, not equivalent beliefs, true predictions, identity verification or matched answers.']}
    A.write_json(output/'provenance-private.json',{'baseline':base_audit,'official':audit,'integrity_audit':{'path':str(integrity_audit),'sha256':A.sha(integrity_audit)} if integrity_audit else None});A.write_json(output/'qa-private.json',{'unverified_official_asr_question_candidates':qa})
    result['qa']['database_counts']=A.sqlite_qa(output/'official-questions.sqlite',publications,[],qa)
    result['figures']=figures(output,result);A.write_json(output/'official-speech.json',result)
    A.write_json(output/'output-manifest.json',{'script_sha256':A.sha(Path(__file__)),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':A.sha(p),'private_content':p.name in ('provenance-private.json','qa-private.json','official-questions.sqlite')} for p in sorted(output.iterdir()) if p.is_file()]})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-json',type=Path,required=True);p.add_argument('--baseline-manifest',type=Path,action='append',required=True);p.add_argument('--official-manifest',type=Path,action='append',required=True);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--semantic-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--phase',choices=('pilot','final'),default='pilot');p.add_argument('--expected-publications',type=int);p.add_argument('--source-frame',type=Path);p.add_argument('--integrity-audit',type=Path)
    a=p.parse_args();r=study(a.baseline_json,a.baseline_manifest,a.official_manifest,a.model_dir,a.semantic_cache,a.output,phase=a.phase,expected_publications=a.expected_publications,source_frame=a.source_frame,integrity_audit=a.integrity_audit);print(json.dumps({'scope':r['run_scope'],'coverage':r['coverage']}))
if __name__=='__main__':main()
