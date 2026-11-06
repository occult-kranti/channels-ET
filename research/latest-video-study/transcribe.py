#!/usr/bin/env python3
"""Transcribe explicitly selected local, ffprobe-validated recordings; never download."""
import argparse, datetime, hashlib, importlib.metadata, json, os, subprocess, sys
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path, help='JSON list of source records')
    p.add_argument('--output', required=True, type=Path, help='Private output directory outside Git')
    p.add_argument('--model', default='tiny', help='Whisper model name or local model path')
    p.add_argument('--device', default='cpu')
    p.add_argument('--compute-type', default='int8')
    p.add_argument('--language', default=None)
    args=p.parse_args()
    records=json.loads(args.input.read_text(encoding='utf-8'))
    if not isinstance(records,list): raise ValueError('Input must be a JSON list')
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip()).resolve()
    out=args.output.resolve()
    if out==root or root in out.parents: raise ValueError('Output must be outside the Git checkout')
    out.mkdir(parents=True,exist_ok=True)
    from faster_whisper import WhisperModel
    model=WhisperModel(args.model,device=args.device,compute_type=args.compute_type)
    results=[]; seen=set()
    for row in records:
        vid=row['video_id']; channel=row['channel']; source=Path(row['media_path']).resolve()
        if len(vid)!=11 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in vid): raise ValueError('Invalid video ID')
        if vid in seen: raise ValueError('Duplicate video ID: '+vid)
        seen.add(vid)
        record={'video_id':vid,'channel':channel,'title':row.get('title',''),'source_url':'https://www.youtube.com/watch?v='+vid,'transcript_source':'faster-whisper ASR','status':'failed'}
        try:
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(source)],text=True,stderr=subprocess.PIPE,timeout=60))
            if not any(s.get('codec_type')=='audio' for s in info.get('streams',[])): raise ValueError('No audio stream')
            duration=float(info['format']['duration'])
            if duration<=0: raise ValueError('Nonpositive duration')
            media_hash=digest(source)
            if row.get('sha256') and row['sha256']!=media_hash: raise ValueError('Media hash mismatch')
            segments, meta=model.transcribe(str(source),beam_size=5,language=args.language,vad_filter=True)
            lines=[]; timings=[]
            for s in segments:
                t=s.text.strip()
                if t: lines.append(t); timings.append({'start':s.start,'end':s.end,'text':t})
            if not lines: raise ValueError('No speech segments')
            target=out/(vid+'.txt'); target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            (out/(vid+'.segments.json')).write_text(json.dumps(timings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            record.update(status='ok',transcript_path=str(target),transcript_sha256=digest(target),media_sha256=media_hash,duration_seconds=duration,language=meta.language,language_probability=meta.language_probability,model=args.model,device=args.device,compute_type=args.compute_type,asr_version=importlib.metadata.version('faster-whisper'))
        except Exception as e:
            record['error']=str(e)[:500]
        results.append(record)
        (out/'transcription-manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"{vid}: {record['status']}",flush=True)
    print('Completed:',sum(r['status']=='ok' for r in results),'/',len(results))
    return int(any(r['status']!='ok' for r in results))
if __name__=='__main__': sys.exit(main())
