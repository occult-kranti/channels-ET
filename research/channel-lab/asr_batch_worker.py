#!/usr/bin/env python3
"""One warm, one-thread CPU model consuming a bounded parent-owned chunk queue."""
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import resource
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(raw)
    return h.hexdigest()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.writing')
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')
    tmp.replace(path)


def worker(request, jobs, results, state_path):
    began = time.time()
    state = {'pid': os.getpid(), 'status': 'loading', 'started_at_unix': began,
             'current_job': None, 'completed_chunks': 0, 'script_sha256': digest(__file__),
             'cpu_threads': 1, 'request_sha256': request['request_sha256']}
    atomic(Path(state_path), state)
    try:
        if state['script_sha256'] != request['worker_sha256']:
            raise ValueError('Actual worker code differs from frozen request')
        for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            os.environ[key] = '1'
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
        names = [x['file'] for x in request['model_files']]
        required = {'config.json', 'generation_config.json', 'model.safetensors',
                    'processor_config.json', 'tokenizer.json', 'tokenizer_config.json'}
        if set(names) != required or len(names) != len(set(names)):
            raise ValueError('Exact model bindings required')
        for binding in request['model_files']:
            path = Path(request['model_path'])/binding['file']
            if path.stat().st_size != binding['bytes'] or digest(path) != binding['sha256']:
                raise ValueError('Pinned model bytes differ')
        state['model_validation_seconds'] = time.time()-began
        load_start = time.time()
        import numpy as np
        import torch
        from transformers import AutoModelForTDT, AutoProcessor
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        processor = AutoProcessor.from_pretrained(request['model_path'], local_files_only=True, trust_remote_code=False)
        model = AutoModelForTDT.from_pretrained(request['model_path'], dtype=torch.float32,
                                              local_files_only=True, trust_remote_code=False).to('cpu').eval()
        state.update(model_load_seconds=time.time()-load_start, status='idle',
                     learned_parameter_elements=sum(p.numel() for p in model.parameters()),
                     actual_device=str(model.device), actual_dtype=str(model.dtype),
                     model_implementation_sha256=digest(inspect.getfile(type(model))),
                     software={x: importlib.metadata.version(x) for x in ('torch', 'transformers', 'numpy', 'librosa')})
        atomic(Path(state_path), state)
        while True:
            job = jobs.get()
            if job is None:
                break
            raw = job.pop('s16_bytes')
            if (not raw or len(raw) % 2 or len(raw) > 960000
                    or hashlib.sha256(raw).hexdigest() != job['s16_sha256']
                    or len(raw)//2 != job['end_sample']-job['start_sample']):
                raise ValueError('Queued PCM bytes or exact window bounds differ')
            samples = np.frombuffer(raw, dtype='<i2').astype('<f4')/np.float32(32768)
            if not np.isfinite(samples).all():
                raise ValueError('Nonfinite model input')
            started = time.time(); cpu = time.process_time()
            state.update(status='recognizing', current_job={'job_id': job['job_id'], 'started_at_unix': started})
            atomic(Path(state_path), state)
            with torch.inference_mode():
                inputs = processor(samples, sampling_rate=16000, return_tensors='pt')
                generated = model.generate(**inputs, return_dict_in_generate=True)
                decoded = processor.decode(generated.sequences, skip_special_tokens=True)
            text = decoded[0] if isinstance(decoded, list) else decoded
            if not isinstance(text, str) or generated.durations is None or generated.durations.shape != generated.sequences.shape:
                raise ValueError('Invalid generated text/duration evidence')
            durations = generated.durations.detach().cpu().tolist()
            valid = model.encoder._get_subsampling_output_length(inputs['attention_mask'].sum(-1)).detach().cpu().tolist()
            advances = [sum(row) for row in durations]
            if (not valid or any(x <= 0 for x in valid) or len(advances) != len(valid)
                    or any(x < 0 for row in durations for x in row)
                    or any(a < b for a, b in zip(advances, valid))):
                raise ValueError('Generation did not exhaust the valid encoder frames')
            ended = time.time()
            rms = float(np.sqrt(np.mean(samples.astype('float64')**2)))
            output = {**job, 'status': 'completed', 'text': text, 'words': len(text.split()),
                      'sample_rate': 16000, 'speaker_role': 'unknown', 'accuracy_verified': False,
                      'timestamp_scope': 'Fixed audio-window boundaries, not word alignment or speaker turns',
                      'f32_sha256': hashlib.sha256(samples.tobytes()).hexdigest(),
                      'encoder_valid_frames': valid, 'encoder_frame_advances': advances,
                      'generation_frame_durations': durations,
                      'token_ids': generated.sequences.detach().cpu().tolist(),
                      'encoder_exhausted': True, 'explicit_max_new_tokens': None,
                      'rms_dbfs': float(20*np.log10(rms)) if rms else None,
                      'rms_zero': rms == 0, 'peak_amplitude': float(np.max(np.abs(samples))),
                      'wall_start_unix': started, 'wall_end_unix': ended,
                      'inference_seconds': ended-started, 'cpu_seconds': time.process_time()-cpu,
                      'real_time_factor': (ended-started)/(len(samples)/16000),
                      'worker_pid': os.getpid(), 'worker_script_sha256': digest(__file__),
                      'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            path = Path(request['cache_root'])/job['edition_id']/(job['job_id']+'.json')
            if path.exists():
                raise ValueError('An admitted cache artifact would be overwritten')
            atomic(path, output)
            results.put({'status': 'completed', 'job_id': job['job_id'], 'edition_id': job['edition_id'],
                         'artifact': {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}})
            state['completed_chunks'] += 1
            state.update(status='idle', current_job=None, max_rss_kib=output['max_rss_kib'])
            atomic(Path(state_path), state)
        state.update(status='completed', finished_at_unix=time.time(), wall_seconds=time.time()-began)
        atomic(Path(state_path), state)
    except BaseException as exc:
        state.update(status='failed', failure_type=type(exc).__name__, failure_message=str(exc)[:400],
                     finished_at_unix=time.time())
        atomic(Path(state_path), state)
        results.put({'status': 'failed', 'pid': os.getpid(), 'error': str(exc)[:400]})
        raise
