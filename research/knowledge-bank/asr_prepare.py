#!/usr/bin/env python3
"""Freeze a deterministic eight-recording, sixteen-window speech-model comparison."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT=Path('/workspace/channels-et-private')


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def artifact(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}


def read(p,bindings):
    bindings.append(artifact(p));return json.loads(p.read_text())


def selected_sources():
    bindings=[];rows=[]
    for name in ['contact/text-manifest-private.json','media/new-text-manifest.json']:
        d=read(ROOT/'council-study-2026-11'/name,bindings)
        for x in d['documents']:
            rows.append({'source_id':x['source_id'],'publication_id':x['publication_id'],
                'title':x['title'],'source_url':x['canonical_url'],'context':x['medium_name'],
                'audio':{k:x['audio_artifact'][k] for k in ('path','bytes','sha256')},
                'duration_seconds':x['decoded_audio_seconds'],'selection_frame':'four retained Council recordings',
                'legacy_transcript_sha256':x['text_artifact']['sha256'],
                'attribution_scope':x['attribution_scope']})
    ra=read(ROOT/'bashar-ra-2026-11/ra/audio-compact/audio-manifest.json',bindings)
    eligible=sorted([x for x in ra['records'] if x['status']=='verified_compact_copy' and
                     x['retained']['decoded_duration_seconds']>=240],key=lambda x:x['source_id'])
    x=eligible[0]
    rows.append({'source_id':x['source_id'],'publication_id':x['source_id'],
        'title':f"Ra session {x['session_number']}, linked segment {x['segment_number']}",
        'source_url':x['url'],'context':'Ra linked recording context',
        'audio':{k:x['retained'][k] for k in ('path','bytes','sha256')},
        'duration_seconds':x['retained']['decoded_duration_seconds'],
        'selection_frame':f'Lexicographically first source_id among {len(eligible)} >=240-second retained Ra segments in pinned compact manifest',
        'legacy_transcript_sha256':None,'attribution_scope':'Published Ra audio segment; speakers and accuracy unverified; no word-aligned reference used.'})
    official=read(ROOT/'bashar-ra-2026-11/bashar/official-vimeo-corpus-reviewed/manifest.json',bindings)
    eligible=sorted([x for x in official['records'] if x.get('integrity_status')=='passed' and
        x.get('eligibility_status')=='qualifying_actual_duration' and x.get('audio_duration_seconds',0)>=300],key=lambda x:x['source_id'])
    x=eligible[0]
    rows.append({'source_id':x['source_id'],'publication_id':x['session_id'],'title':x['title'],
        'source_url':x['source_url'],'context':'Official Bashar publication context',
        'audio':{k:x['audio_artifact'][k] for k in ('path','bytes','sha256')},
        'duration_seconds':x['audio_duration_seconds'],
        'selection_frame':f'Lexicographically first eligible source_id among {len(eligible)} reviewed >=300-second official Bashar publications',
        'legacy_transcript_sha256':x.get('text_artifact',{}).get('sha256'),
        'attribution_scope':'Official public publication, not necessarily a complete historical channeling session; utterance speakers unknown.'})
    pubs=read(ROOT/'subscription-screening-2026-11/publisher-audio-v3/manifest.json',bindings)
    for key,label in [('tr-medium-natalie-glasson','Natalie / OmNa recording context'),('akanksshaa_publisher','Multidimensional Soul episode context')]:
        eligible=sorted([x for x in pubs['records'] if x.get('status')=='completed' and
            x['source'].get('medium_context_id')==key and x['decoded_16k_mono']['duration_seconds']>=120],key=lambda x:x['publication_id'])
        if not eligible:raise ValueError('Expected publisher context absent: '+key)
        x=eligible[0]
        rows.append({'source_id':x['source_id'],'publication_id':x['publication_id'],'title':x['source']['title'],
            'source_url':x['source']['source_url'],'context':label,
            'audio':{k:x['audio'][k] for k in ('path','bytes','sha256')},
            'duration_seconds':x['decoded_16k_mono']['duration_seconds'],
            'selection_frame':f'Lexicographically first publication_id among {len(eligible)} retained >=120-second recordings in this context',
            'legacy_transcript_sha256':None,'attribution_scope':'Publisher recording context; no per-utterance entity or speaker authentication.'})
    if len(rows)!=8 or len({x['audio']['sha256'] for x in rows})!=8:raise ValueError('Unexpected source count or exact media duplicate')
    return rows,bindings


def prepare(output,pcm_root):
    if output.exists() or pcm_root.exists():raise ValueError('Use fresh preparation paths')
    if not pcm_root.resolve().is_relative_to(Path('/dev/shm')):raise ValueError('PCM must remain in temporary RAM storage')
    rows,bindings=selected_sources();pcm_root.mkdir(parents=True);clips=[]
    for i,row in enumerate(rows):
        source=Path(row['audio']['path'])
        if source.stat().st_size!=row['audio']['bytes'] or sha(source)!=row['audio']['sha256']:raise ValueError('Retained source changed')
        starts=[math.floor(row['duration_seconds']*q-15) for q in (.25,.75)]
        if starts[0]<0 or starts[0]+30>starts[1] or starts[1]+30>row['duration_seconds']:raise ValueError('Invalid window selection')
        for j,start in enumerate(starts):
            cid=f'audio-{i+1:02d}-window-{j+1:02d}';p=pcm_root/(cid+'.f32')
            cmd=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(source),'-ss',str(start),
                 '-t','30','-map','0:a:0','-vn','-ac','1','-ar','16000','-f','f32le','-c:a','pcm_f32le',str(p)]
            result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,check=False)
            log=pcm_root/(cid+'-decode.log');log.write_bytes(result.stderr)
            if result.returncode or p.stat().st_size!=30*16000*4:raise ValueError('Incomplete or failed window decode')
            clips.append({'clip_id':cid,'source_id':row['source_id'],'publication_id':row['publication_id'],
                'context':row['context'],'source_audio_sha256':row['audio']['sha256'],
                'source_duration_seconds':row['duration_seconds'],'start_seconds':start,'duration_seconds':30,
                'samples':480000,'sample_rate':16000,'channels':1,'dtype':'little_endian_float32',
                'pcm':artifact(p),'decode':{'command':cmd,'returncode':result.returncode,'log':artifact(log)}})
    frame={'schema_version':1,'status':'prepared','at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256':sha(__file__),'source_bindings':bindings,'sources':rows,'clips':clips,
        'selection_rule':'All four Council audios plus first eligible source IDs in four other specified contexts; two nonoverlapping 30-second windows centered at25%/75%, rounded down to whole seconds, selected before new recognition.',
        'recordings':8,'source_contexts':len({x['context'] for x in rows}),'unique_audio_seconds':480,
        'scope':'Eight minutes of selected windows, not eight complete retranscribed recordings. Existing transcript editions remain unchanged.'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(frame,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:frame[k] for k in ('status','recordings','source_contexts','unique_audio_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--pcm-root',type=Path,required=True)
    a=p.parse_args();prepare(a.output,a.pcm_root)
