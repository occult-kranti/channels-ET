#!/usr/bin/env python3
"""Run one bounded full-recording Parakeet worker using independent nonoverlapping sample windows."""
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import inspect
import json
import os
import re
from pathlib import Path
import resource
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def run(request_path, output):
    invocation_start=time.monotonic()
    if not output.resolve().is_relative_to(Path('/workspace/channels-et-private/knowledge-bank-2026-11/asr')):
        raise ValueError('Full recognition outputs must remain in this private study archive')
    if output.exists(): raise ValueError('Use a fresh worker output directory')
    output.mkdir(parents=True)
    request_raw = request_path.read_bytes(); request = json.loads(request_raw)
    if not 1 <= len(request['clips']) <= 400: raise ValueError('Bounded clip frame required')
    if request['cpu_threads'] != 1: raise ValueError('This experiment reserves one CPU thread per worker')
    ids=[x['clip_id'] for x in request['clips']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',x) for x in ids):
        raise ValueError('Clip IDs must be unique path-safe identifiers')
    required={'parakeet_transformers':{'config.json','generation_config.json','model.safetensors',
              'processor_config.json','tokenizer.json','tokenizer_config.json'},
              'faster_whisper':{'config.json','model.bin','tokenizer.json','vocabulary.txt'}}
    bindings=request.get('model_files',[])
    names=[x['file'] for x in bindings]
    if request['engine'] not in required or not required[request['engine']].issubset(names) or len(names)!=len(set(names)):
        raise ValueError('Required model-file bindings are missing or duplicated')
    if any(Path(x).name!=x for x in names): raise ValueError('Model binding path is not a filename')
    for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['MPLCONFIGDIR'] = '/dev/shm/channels-et-knowledge-2026-11/asr/mpl'
    import numpy as np
    model_path = Path(request['model_path'])
    for binding in request['model_files']:
        path = model_path / binding['file']
        if path.stat().st_size != binding['bytes'] or digest(path) != binding['sha256']:
            raise ValueError('Model artifact differs from pinned request')
    start = time.monotonic(); wall = time.time()
    receipt = {'status': 'loading_model', 'pid': os.getpid(), 'engine': request['engine'],
               'model_id': request['model_id'], 'model_revision': request.get('model_revision'),
               'request_sha256': hashlib.sha256(request_raw).hexdigest(),
               'script_sha256': digest(__file__), 'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'cpu_threads': 1, 'speaker_roles': 'unknown', 'records': [],
               'preload_validation_seconds': time.monotonic()-invocation_start,
               'scope': 'Full recording sample coverage through independent nonoverlapping windows; context across chunk boundaries is absent and word accuracy unmeasured.'}
    dump(output/'receipt.json', receipt)
    try:
        if request['engine'] == 'parakeet_transformers':
            import torch
            from transformers import AutoModelForTDT, AutoProcessor
            torch.set_num_threads(1); torch.set_num_interop_threads(1)
            processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
            model = AutoModelForTDT.from_pretrained(model_path, dtype=torch.float32,
                    local_files_only=True, trust_remote_code=False).to('cpu').eval()
            receipt['software'] = {x: importlib.metadata.version(x) for x in ('torch', 'transformers', 'numpy', 'safetensors','librosa','scipy','numba')}
            receipt['model_implementation_sha256']=digest(inspect.getfile(type(model)))
            receipt['learned_parameter_elements']=sum(p.numel() for p in model.parameters())
            receipt['actual_device'] = str(model.device); receipt['actual_dtype'] = str(model.dtype)
            receipt['cuda_available'] = torch.cuda.is_available()
            receipt['generation_configuration'] = model.generation_config.to_dict()
        elif request['engine'] == 'faster_whisper':
            from faster_whisper import WhisperModel
            model = WhisperModel(str(model_path), device='cpu', compute_type='int8',
                    cpu_threads=1, num_workers=1, local_files_only=True)
            receipt['software'] = {x: importlib.metadata.version(x) for x in ('faster-whisper', 'ctranslate2', 'numpy')}
            receipt['actual_device'] = 'cpu'; receipt['actual_dtype'] = 'int8'
            receipt['generation_configuration'] = request['transcribe_options']
        else: raise ValueError('Unknown engine')
        receipt['model_load_seconds'] = time.monotonic()-start
        receipt['status'] = 'transcribing'; dump(output/'receipt.json', receipt)
        for clip in request['clips']:
            p=Path(clip['pcm']['path'])
            if p.stat().st_size != clip['pcm']['bytes'] or digest(p) != clip['pcm']['sha256']:
                raise ValueError('PCM artifact differs from pinned request')
            samples=np.fromfile(p,dtype='<f4')
            if len(samples)!=clip['samples'] or not np.isfinite(samples).all():
                raise ValueError('PCM sample count or values invalid')
            if len(samples)/16000 != clip['duration_seconds'] or not 0<len(samples)<=480000 or clip['end_sample']-clip['start_sample']!=len(samples):
                raise ValueError('Full-recording window or partial-tail sample count invalid')
            t=time.monotonic(); cpu=time.process_time(); began=time.time()
            receipt['current_clip']={'clip_id':clip['clip_id'],'started_at_unix':began}
            dump(output/'receipt.json',receipt)
            if request['engine']=='parakeet_transformers':
                with torch.inference_mode():
                    inputs=processor(samples, sampling_rate=16000, return_tensors='pt')
                    generated=model.generate(**inputs, return_dict_in_generate=True)
                    decoded=processor.decode(generated.sequences, skip_special_tokens=True)
                text=decoded[0] if isinstance(decoded,list) else decoded
                if not isinstance(text,str): raise ValueError('Unexpected decoder output')
                token_ids=generated.sequences.detach().cpu().tolist()
                if generated.durations is None or generated.durations.shape!=generated.sequences.shape or generated.durations.numel()==0:
                    raise ValueError('Missing or mismatched generation-duration evidence')
                if not bool((generated.durations>=0).all()):raise ValueError('Invalid negative encoder-frame advance')
                valid_frames=model.encoder._get_subsampling_output_length(inputs['attention_mask'].sum(-1)).detach().cpu().tolist()
                advanced=generated.durations.sum(-1).detach().cpu().tolist()
                if not valid_frames or not all(x>0 for x in valid_frames):raise ValueError('Missing positive encoder-frame bound')
                details={'token_ids':token_ids,'encoder_valid_frames':valid_frames,
                         'generation_frame_durations':generated.durations.detach().cpu().tolist(),
                         'encoder_frame_advances':advanced,
                         'encoder_exhausted':all(a>=b for a,b in zip(advanced,valid_frames)),
                         'explicit_max_new_tokens':None,'generation_steps':len(token_ids[0])-1,
                         'last_token_id':token_ids[0][-1],
                         'timestamp_scope':'Window boundaries only; token alignment is not inferred.'}
            else:
                segments,info=model.transcribe(samples,**request['transcribe_options'])
                turns=[{'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,
                        'no_speech_prob':s.no_speech_prob,'compression_ratio':s.compression_ratio} for s in segments]
                text=' '.join(s['text'].strip() for s in turns).strip()
                details={'segments':turns,'detected_language':info.language,'language_probability':info.language_probability,
                         'inference_stream_exhausted':True,
                         'timestamp_scope':'Unverified model-relative segment times within isolated window.'}
            elapsed=time.monotonic()-t
            result={'clip_id':clip['clip_id'],'source_id':clip['source_id'],
                    'audio_start_seconds':clip['start_seconds'],'audio_end_seconds':clip['end_sample']/16000,'start_sample':clip['start_sample'],'end_sample':clip['end_sample'],
                    'pcm_sha256':clip['pcm']['sha256'],'text':text,'words':len(text.split()),
                    'inference_seconds':elapsed,'cpu_seconds':time.process_time()-cpu,
                    'wall_start_unix':began,'wall_end_unix':time.time(),'real_time_factor':elapsed/clip['duration_seconds'],
                    'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'speaker_role':'unknown',**details}
            file=output/(clip['clip_id']+'.json');dump(file,result)
            txt=output/(clip['clip_id']+'.txt');txt.write_text(text+'\n')
            receipt['records'].append({k:v for k,v in result.items() if k not in ('text','token_ids','segments','generation_frame_durations')})
            receipt['records'][-1]['output']={'path':str(file),'bytes':file.stat().st_size,'sha256':digest(file)}
            receipt['records'][-1]['text_output']={'path':str(txt),'bytes':txt.stat().st_size,'sha256':digest(txt)}
            receipt['current_clip']=None
            dump(output/'receipt.json',receipt)
            print(json.dumps({'clip':clip['clip_id'],'words':len(text.split()),'seconds':elapsed,'rss_kib':result['max_rss_kib']}),flush=True)
            if request['engine']=='parakeet_transformers' and not result['encoder_exhausted']:
                raise ValueError('Unadmitted incomplete encoder traversal; private output retained for diagnosis')
            if elapsed>180: raise RuntimeError('Single-window inference exceeded prospective 180-second stop')
        receipt['status']='completed'
    except Exception as exc:
        receipt['status']='failed';receipt['failure_type']=type(exc).__name__
        receipt['failure_message']=str(exc)[:400]
        dump(output/'receipt.json',receipt);raise
    receipt['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    receipt['worker_wall_seconds']=time.time()-wall
    receipt['invocation_seconds_including_validation']=time.monotonic()-invocation_start
    receipt['max_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    receipt['completed_clips']=len(receipt['records'])
    dump(output/'receipt.json',receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.request,a.output)
