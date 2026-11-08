#!/usr/bin/env python3
"""Re-recognize four retained Council recordings in complete, independent sample windows."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import asr_orchestrate as O

ROOT=Path('/workspace/channels-et-private')
FULL=O.PRIVATE/'full-council-01'
PCM=O.RAM/'full-council-pcm-01'


def artifact(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':O.sha(p)}


def checked(ref):
    p=Path(ref['path'])
    if p.stat().st_size!=ref['bytes'] or O.sha(p)!=ref['sha256']:raise ValueError('Bound artifact changed')
    return p


def prepare():
    import numpy as np
    if FULL.exists() or PCM.exists():raise ValueError('Full-run preparation requires fresh paths')
    FULL.mkdir(parents=True);PCM.mkdir(parents=True)
    (FULL/'executed-asr_full.py').write_bytes(Path(__file__).read_bytes())
    knowledge=ROOT/'knowledge-bank-2026-11/knowledge/frame-01.json'
    old_records={x['source_id']:x for x in json.loads(knowledge.read_text())['records']}
    documents=[];bindings=[artifact(knowledge)];clips=[]
    for relative in ['contact/text-manifest-private.json','media/new-text-manifest.json']:
        p=ROOT/'council-study-2026-11'/relative;bindings.append(artifact(p))
        for doc in json.loads(p.read_text())['documents']:
            if doc['source_id'] not in old_records or old_records[doc['source_id']]['text_artifact']['sha256']!=doc['text_artifact']['sha256']:
                raise ValueError('Counterpart ID or old text differs from accepted knowledge frame')
            checked(doc['text_artifact']);source=checked(doc['audio_artifact'])
            old_receipt=json.loads(checked(doc['asr_receipt']).read_text());decoder=old_receipt['decoder']
            if not decoder['natural_eof'] or decoder['decoder_returncode']!=0:raise ValueError('Old decoder reference incomplete')
            index=len(documents)+1
            command=['ffmpeg','-nostdin','-v','error','-xerror','-threads','1','-i',str(source),'-map','0:a:0',
                     '-vn','-sn','-dn','-ac','1','-ar','16000','-c:a','pcm_s16le','-threads','1','-f','s16le','pipe:1']
            if command!=decoder['command']:raise ValueError('Full decode command differs from old canonical decoder')
            stderr=PCM/f'source-{index:02d}-decode.log';chunks=[];s16=hashlib.sha256();f32=hashlib.sha256();samples=0
            with stderr.open('wb') as log:
                process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=log)
                try:
                    while True:
                        raw=process.stdout.read(480000*2)
                        if not raw:break
                        if len(raw)%2:raise ValueError('Odd canonical PCM byte count')
                        s16.update(raw);count=len(raw)//2
                        values=(np.frombuffer(raw,dtype='<i2').astype('<f4')/np.float32(32768)).astype('<f4',copy=False)
                        if not np.isfinite(values).all():raise ValueError('Nonfinite PCM values')
                        body=values.tobytes();f32.update(body)
                        cid=f'full-{index:02d}-chunk-{len(chunks)+1:04d}';path=PCM/(cid+'.f32');path.write_bytes(body)
                        clip={'clip_id':cid,'source_id':doc['source_id'],'publication_id':doc['publication_id'],
                            'start_sample':samples,'end_sample':samples+count,'start_seconds':samples/16000,
                            'duration_seconds':count/16000,'samples':count,'sample_rate':16000,'channels':1,'dtype':'little_endian_float32',
                            'pcm':artifact(path),'canonical_s16_sha256':hashlib.sha256(raw).hexdigest(),
                            'source_audio_sha256':doc['audio_artifact']['sha256']}
                        chunks.append(clip);clips.append(clip);samples+=count
                        if samples>decoder['sample_count']:raise ValueError('Decoded source exceeded canonical sample count')
                    code=process.wait(timeout=30)
                    if code:raise ValueError('Full decode did not terminate successfully')
                finally:
                    if process.poll() is None:process.terminate();process.wait(timeout=5)
            if samples!=decoder['sample_count'] or s16.hexdigest()!=decoder['raw_pcm_sha256']:
                raise ValueError('Canonical full S16 samples differ from old ASR input')
            documents.append({'source_id':doc['source_id']+':parakeet-tdt-v3-full30-20261108',
                'counterpart_source_id':doc['source_id'],'publication_id':doc['publication_id'],
                'title':doc['title'],'source_url':doc['canonical_url'],'medium_id':doc['medium_id'],'medium':doc['medium_name'],
                'claimed_label':doc['council_label'],'attribution_scope':doc['attribution_scope'],
                'old_text_artifact':doc['text_artifact'],'old_asr_receipt':doc['asr_receipt'],
                'audio_artifact':{k:doc['audio_artifact'][k] for k in ('path','bytes','sha256')},
                'canonical_s16_pcm':{'sha256':s16.hexdigest(),'sample_count':samples,'duration_seconds':samples/16000,
                    'sample_rate':16000,'channels':1,'format':'s16le','matches_old_decoder':True},
                'decoded_pcm':{'sha256':f32.hexdigest(),'sample_count':samples,'duration_seconds':samples/16000,
                    'sample_rate':16000,'channels':1,'format':'f32le','conversion':'int16 /32768'},
                'decode':{'command':command,'returncode':code,'natural_eof':True,'stderr':artifact(stderr)},
                'chunk_ids':[c['clip_id'] for c in chunks]})
    if len(documents)!=4:raise ValueError('Expected exactly four Council counterparts')
    frame={'schema_version':1,'status':'prepared_full_sample_coverage','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256':O.sha(__file__),'bindings':bindings,'documents':documents,'clips':clips,
        'source_recordings':4,'chunk_count':len(clips),'total_samples':sum(d['decoded_pcm']['sample_count'] for d in documents),
        'total_audio_seconds':sum(d['decoded_pcm']['duration_seconds'] for d in documents),
        'scope':'Every canonical decoded sample in four existing recordings, partitioned into independent nonoverlapping <=30-second windows including each final partial tail. Full input coverage does not establish word accuracy or preserve cross-window context.'}
    O.dump(FULL/'frame.json',frame)
    print(json.dumps({k:frame[k] for k in ('status','source_recordings','chunk_count','total_samples','total_audio_seconds')}))


def run():
    p=FULL/'frame.json';frame=json.loads(p.read_text());binding={'path':str(p),'sha256':O.sha(p)}
    groups=[frame['clips'][::2],frame['clips'][1::2]]
    requests=[]
    for group in groups:
        request=O.request(group,'parakeet_transformers',binding)
        request['scope']='Complete canonical input sample coverage in independent <=30-second chunks; no cross-window conditioning or word-accuracy claim.'
        requests.append(request)
    O.supervise(requests,FULL/'run-01',worker_filename='asr_full_worker.py',private_budget_root=FULL,max_stage_seconds=1800)
    finalize()


def finalize():
    frame_path=FULL/'frame.json';frame=json.loads(frame_path.read_text());stage_path=FULL/'run-01/stage-receipt.json'
    stage=json.loads(stage_path.read_text())
    if stage['status']!='completed':raise ValueError('Full stage not completed')
    records={};worker_bindings=[]
    for w in stage['workers']:
        receipt_path=checked(w['receipt']) if 'bytes' in w['receipt'] else Path(w['receipt']['path'])
        if O.sha(receipt_path)!=w['receipt']['sha256']:raise ValueError('Worker receipt hash changed')
        receipt=json.loads(receipt_path.read_text());request_path=Path(w['request']['path'])
        if receipt['status']!='completed' or O.sha(request_path)!=w['request']['sha256'] or receipt['request_sha256']!=w['request']['sha256']:
            raise ValueError('Incomplete or mismatched full worker')
        if receipt['script_sha256']!=stage['worker_sha256']:raise ValueError('Executed full worker code differs')
        request=json.loads(request_path.read_text())
        if request['frame_binding']['sha256']!=O.sha(frame_path):raise ValueError('Worker used different full frame')
        worker_bindings.append(artifact(receipt_path))
        for row in receipt['records']:
            value=json.loads(checked(row['output']).read_text())
            if value['clip_id'] in records or not value.get('encoder_exhausted'):raise ValueError('Duplicate or incomplete recognition window')
            if value['words']!=len(value['text'].split()):raise ValueError('Output word count mismatch')
            if [sum(x) for x in value['generation_frame_durations']]!=value['encoder_frame_advances']:
                raise ValueError('Raw duration-token sum mismatch')
            records[value['clip_id']]=(value,row['output'])
    planned={c['clip_id']:c for c in frame['clips']}
    if set(records)!=set(planned):raise ValueError('Completed set differs from exact full coverage plan')
    documents=[]
    for doc in frame['documents']:
        checked(doc['audio_artifact']);checked(doc['old_text_artifact']);checked(doc['old_asr_receipt'])
        source_rows=[];turns=[];offset=0;parts=[];concatenated_pcm=hashlib.sha256()
        for cid in doc['chunk_ids']:
            clip=planned[cid];value,output_ref=records[cid]
            if clip['start_sample']!=offset or value['start_sample']!=clip['start_sample'] or value['end_sample']!=clip['end_sample']:
                raise ValueError('Gap, overlap or changed sample boundaries')
            if value['source_id']!=doc['counterpart_source_id'] or value['pcm_sha256']!=clip['pcm']['sha256']:
                raise ValueError('Source/PCM mismatch')
            pcm_path=checked(clip['pcm']);concatenated_pcm.update(pcm_path.read_bytes());offset=clip['end_sample'];parts.append(value['text'].strip())
            turns.append({'id':cid,'start':clip['start_sample']/16000,'end':clip['end_sample']/16000,
                'start_sample':clip['start_sample'],'end_sample':clip['end_sample'],
                'text':value['text'],'speaker_role':'unknown','unit':'fixed_audio_window_not_verified_speaker_turn'})
            source_rows.append({'clip_id':cid,'start_sample':clip['start_sample'],'end_sample':clip['end_sample'],
                'samples':clip['samples'],'pcm_sha256':clip['pcm']['sha256'],'asr_output':output_ref,
                'words':value['words'],'encoder_exhausted':True,'inference_seconds':value['inference_seconds']})
        expected=doc['decoded_pcm']['sample_count']
        if offset!=expected or concatenated_pcm.hexdigest()!=doc['decoded_pcm']['sha256']:
            raise ValueError('Final partial tail or concatenated full PCM hash differs')
        text=' '.join(parts).strip();folder=FULL/('document-'+hashlib.sha256(doc['source_id'].encode()).hexdigest()[:16]);folder.mkdir()
        normalized={'source_id':doc['source_id'],'counterpart_source_id':doc['counterpart_source_id'],
            'text':text,'words':len(text.split()),'turns':turns,'speaker_role':'unknown',
            'scope':'Ordered concatenation of independent chunk outputs, without overlap deduplication, punctuation repair, speaker inference or claims of complete linguistic accuracy.'}
        O.dump(folder/'transcript.json',normalized);(folder/'transcript.txt').write_text(text+'\n')
        coverage={'input_samples':expected,'covered_samples':offset,'chunk_count':len(source_rows),
            'contiguous':True,'starts_at_zero':True,'ends_at_sample_count':True,'all_encoder_exhausted':True}
        receipt={'status':'completed_full_chunked_asr','source_id':doc['source_id'],'counterpart_source_id':doc['counterpart_source_id'],
            'model_id':'nvidia/parakeet-tdt-0.6b-v3','model_revision':'541d1f99c6b0c3cd0b11a95167540bb8edefd82b',
            'speaker_role':'unknown','accuracy_verified':False,'audio_artifact':doc['audio_artifact'],
            'canonical_s16_pcm':doc['canonical_s16_pcm'],'decoded_pcm':doc['decoded_pcm'],'coverage':coverage,
            'words':normalized['words'],'text_artifact':artifact(folder/'transcript.json'),
            'plain_text_artifact':artifact(folder/'transcript.txt'),'chunks':source_rows,
            'full_frame':artifact(frame_path),'stage_receipt':artifact(stage_path),'worker_receipts':worker_bindings}
        O.dump(folder/'receipt.json',receipt)
        documents.append({**doc,'status':'completed_full_chunked_asr','speaker_role':'unknown','accuracy_verified':False,
            'coverage':coverage,'words':normalized['words'],'text_artifact':receipt['text_artifact'],
            'plain_text_artifact':receipt['plain_text_artifact'],'asr_receipt':artifact(folder/'receipt.json'),'chunks':source_rows})
    manifest={'schema_version':1,'status':'completed_full_chunked_asr','created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':frame['scope'],'model_id':'nvidia/parakeet-tdt-0.6b-v3','model_revision':'541d1f99c6b0c3cd0b11a95167540bb8edefd82b',
        'documents':documents,'recordings':4,'words':sum(x['words'] for x in documents),'chunks':len(records),
        'covered_audio_seconds':frame['total_audio_seconds'],'input_frame':artifact(frame_path),
        'stage_receipt':artifact(stage_path),'finalizer_sha256':O.sha(__file__),'previous_full_editions_preserved':True}
    if O.tree_bytes(FULL)+len(json.dumps(manifest).encode())>5_000_000:raise ValueError('Full durable artifact budget would be exceeded')
    O.dump(FULL/'manifest.json',manifest)
    print(json.dumps({k:manifest[k] for k in ('status','recordings','words','chunks','covered_audio_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run','finalize']);a=p.parse_args()
    {'prepare':prepare,'run':run,'finalize':finalize}[a.action]()
