#!/usr/bin/env python3
"""Resumable bounded Parakeet queue with immutable verified full-text editions."""
import argparse
import collections
import fcntl
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import selectors
import shutil
import statistics
import subprocess
import time
import uuid

import asr_batch_worker as W
from asr_batch_prepare import artifact, canonical_command, digest, read_bound

RAM = Path('/dev/shm/channels-et-channel-lab-2026-11/asr')
PRIVATE = Path('/workspace/channels-et-private/channel-lab-2026-11/asr')
OLD_RAM = Path('/dev/shm/channels-et-knowledge-2026-11/asr')
MODEL_RECEIPT = Path('/workspace/channels-et-private/knowledge-bank-2026-11/asr/model-download.json')
OWNED_DECODERS = set()
SETTINGS = {'sample_rate': 16000, 'channels': 1, 'canonical_format': 's16le',
            'model_conversion': 'int16 /32768 to float32', 'window_samples': 480000,
            'window_context': 'independent nonoverlapping windows; final partial included',
            'workers': 2, 'cpu_threads_per_worker': 1, 'prefetch_chunks': 4,
            'model_precision': 'float32', 'device': 'cpu', 'generation': 'greedy TDT; no explicit token cap',
            'speaker_roles': 'unknown', 'model_language_selection': 'pretrained multilingual model; no forced English',
            'max_input_seconds': 14400, 'max_recordings': 64, 'max_stage_seconds': 3600,
            'max_chunk_seconds': 180, 'max_setup_seconds': 240,
            'max_asr_memory_bytes': 18*1024**3, 'durable_byte_cap': 10_000_000,
            'disk_floor_bytes': 2*1024**3}


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def tree_bytes(root):
    total = 0
    if root.exists():
        for path in root.rglob('*'):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                # An atomic worker checkpoint may have just been renamed.
                continue
    return total


def binding_json(ref):
    return json.loads(read_bound(ref).read_text())


def edition_id(source, model, worker_sha):
    protocol = hashlib.sha256(encoded({'settings': SETTINGS, 'worker_sha256': worker_sha})).hexdigest()
    key = hashlib.sha256(encoded({'source_audio_sha256': source['audio_artifact']['sha256'],
                                  'canonical_pcm_sha256': source['canonical_s16_pcm']['sha256'],
                                  'model_revision': model['revision'], 'protocol_sha256': protocol})).hexdigest()
    return 'parakeet-' + key[:32], protocol


def validate_chunk(value, source, edition, protocol, expected=None):
    if (value.get('status') != 'completed' or value.get('edition_id') != edition
            or value.get('protocol_sha256') != protocol or value.get('source_id') != source['source_id']
            or value.get('source_audio_sha256') != source['audio_artifact']['sha256']
            or value.get('speaker_role') != 'unknown' or not value.get('encoder_exhausted')
            or value.get('worker_script_sha256') != source['worker_sha256']
            or value.get('model_revision') != source['model_revision']):
        raise ValueError('Cached output identity/protocol/completion mismatch')
    count = value['end_sample']-value['start_sample']
    if not 0 < count <= SETTINGS['window_samples'] or value['words'] != len(value['text'].split()):
        raise ValueError('Cached sample or word count differs')
    durations = value['generation_frame_durations']; tokens = value['token_ids']
    valid = value['encoder_valid_frames']; advanced = value['encoder_frame_advances']
    if (not durations or not valid or len(durations) != len(tokens) or len(valid) != len(durations)
            or len(advanced) != len(valid) or any(x <= 0 for x in valid)
            or any(not d or len(d) != len(t) for d, t in zip(durations, tokens))
            or any(x < 0 for d in durations for x in d)):
        raise ValueError('Cached raw duration/token dimensions are invalid')
    if [sum(x) for x in durations] != advanced:
        raise ValueError('Raw duration evidence differs')
    if any(a < b for a, b in zip(value['encoder_frame_advances'], value['encoder_valid_frames'])):
        raise ValueError('Cached encoder traversal incomplete')
    if expected and any(value[k] != expected[k] for k in ('job_id', 'start_sample', 'end_sample', 's16_sha256')):
        raise ValueError('Cache does not match this exact decoded PCM window')
    return value


def verify_edition(path, source, edition, protocol):
    receipt = json.loads(path.read_text())
    if (receipt.get('status') != 'completed_full_chunked_asr' or receipt.get('edition_id') != edition
            or receipt.get('protocol_sha256') != protocol
            or receipt['audio_artifact'] != source['audio_artifact']
            or receipt['canonical_s16_pcm'] != source['canonical_s16_pcm']
            or receipt['model_revision'] != source['model_revision'] or receipt['settings'] != SETTINGS
            or receipt['recording_id'] != source['recording_id']):
        raise ValueError('Completed edition binding differs')
    normalized = binding_json(receipt['text_artifact'])
    plain = read_bound(receipt['plain_text_artifact']).read_text()
    cursor = 0; texts = []; turns = []
    for ref in receipt['chunks']:
        value = validate_chunk(binding_json(ref), source, edition, protocol)
        if value['start_sample'] != cursor:
            raise ValueError('Completed edition has a sample gap or overlap')
        cursor = value['end_sample']; texts.append(value['text'].strip())
        turns.append({'id': value['job_id'], 'start': value['start_sample']/16000,
                      'end': value['end_sample']/16000, 'start_sample': value['start_sample'],
                      'end_sample': value['end_sample'], 'text': value['text'], 'speaker_role': 'unknown',
                      'unit': 'fixed_audio_window_not_verified_speaker_turn'})
    text = ' '.join(texts).strip()
    if (cursor != source['canonical_s16_pcm']['sample_count'] or text != normalized['text']
            or plain != text+'\n' or normalized['turns'] != turns
            or normalized['words'] != len(text.split())
            or normalized['edition_id'] != edition or normalized['publication_id'] != source['publication_id']):
        raise ValueError('Completed edition text or full coverage differs')
    expected_coverage = {'input_samples': cursor, 'covered_samples': cursor, 'contiguous': True,
                         'starts_at_zero': True, 'ends_at_sample_count': True,
                         'all_encoder_exhausted': True, 'chunk_count': len(turns)}
    if receipt['coverage'] != expected_coverage or normalized['speaker_role'] != 'unknown':
        raise ValueError('Completed edition coverage or speaker metadata differs')
    return receipt


def pcm_windows(source, monitor):
    """Stream at most one PCM window; queue backpressure limits prefetch."""
    process = subprocess.Popen(canonical_command(source['audio_artifact']['path']),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    OWNED_DECODERS.add(process.pid)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, 'pcm')
    selector.register(process.stderr, selectors.EVENT_READ, 'error')
    pending = bytearray(); errors = bytearray(); whole = hashlib.sha256(); samples = 0
    deadline = time.monotonic()+60
    try:
        while selector.get_map():
            monitor()
            if time.monotonic() > deadline:
                raise TimeoutError('Owned decoder produced no output for 60 seconds')
            for key, _ in selector.select(timeout=0.2):
                raw = os.read(key.fd, 65536)
                if not raw:
                    selector.unregister(key.fileobj)
                elif key.data == 'error':
                    errors.extend(raw)
                    if len(errors) > 65536:
                        raise ValueError('Decoder error log exceeded bound')
                else:
                    deadline = time.monotonic()+60
                    whole.update(raw); pending.extend(raw)
                    while len(pending) >= 960000:
                        chunk = bytes(pending[:960000]); del pending[:960000]
                        yield samples, chunk
                        samples += len(chunk)//2
                        # Intentional queue backpressure is not a decoder idle timeout.
                        deadline = time.monotonic()+60
        code = process.wait(timeout=5)
        if code or len(pending) % 2:
            raise ValueError('Source decoder failed or emitted a partial sample')
        if pending:
            yield samples, bytes(pending)
            samples += len(pending)//2
        if (samples != source['canonical_s16_pcm']['sample_count']
                or whole.hexdigest() != source['canonical_s16_pcm']['sha256']):
            raise ValueError('Full streamed canonical PCM differs from frozen frame')
    finally:
        selector.close()
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)
        process.stdout.close(); process.stderr.close(); OWNED_DECODERS.discard(process.pid)


def owned_stop(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=5)
        if process.is_alive():
            process.kill(); process.join(timeout=5)


def finalize(source, edition, protocol, frame_ref, model, stage_ref):
    destination = PRIVATE/'editions'/edition
    if destination.exists():
        return verify_edition(destination/'receipt.json', source, edition, protocol)
    paths = sorted((RAM/'cache'/edition).glob('*.json'))
    values = [validate_chunk(json.loads(p.read_text()), source, edition, protocol) for p in paths]
    cursor = 0
    for value in values:
        if value['start_sample'] != cursor:
            raise ValueError('Full edition has missing or duplicated windows')
        cursor = value['end_sample']
    if cursor != source['canonical_s16_pcm']['sample_count'] or len(values) != source['planned_chunks']:
        raise ValueError('Full edition final tail missing')
    text = ' '.join(x['text'].strip() for x in values).strip()
    turns = [{'id': x['job_id'], 'start': x['start_sample']/16000, 'end': x['end_sample']/16000,
              'start_sample': x['start_sample'], 'end_sample': x['end_sample'], 'text': x['text'],
              'speaker_role': 'unknown', 'unit': 'fixed_audio_window_not_verified_speaker_turn'} for x in values]
    normalized = {'source_id': source['source_id']+':asr:'+edition,
                  'counterpart_source_id': source.get('old_counterpart_source_id'),
                  'publication_id': source['publication_id'], 'recording_id': source['recording_id'],
                  'edition_id': edition, 'text': text, 'words': len(text.split()), 'turns': turns,
                  'speaker_role': 'unknown', 'accuracy_verified': False}
    estimated = sum(p.stat().st_size for p in paths)+len(encoded(normalized))+len(text.encode())+200000
    if tree_bytes(PRIVATE)+estimated > SETTINGS['durable_byte_cap']:
        raise ValueError('Durable private output budget would be exceeded')
    if shutil.disk_usage(PRIVATE).free-estimated < SETTINGS['disk_floor_bytes']:
        raise ValueError('Two-GiB disk floor would be crossed')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name+'.pending-'+uuid.uuid4().hex)
    staging.mkdir()
    refs = []
    for path in paths:
        copied = staging/'chunks'/path.name
        copied.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, copied)
        if digest(copied) != digest(path):
            raise ValueError('Copied chunk differs')
        refs.append({**artifact(copied), 'path': str(destination/'chunks'/path.name)})
    W.atomic(staging/'transcript.json', normalized)
    (staging/'transcript.txt').write_text(text+'\n')
    receipt = {'status': 'completed_full_chunked_asr', 'source_id': normalized['source_id'],
               'original_source_id': source['source_id'], 'publication_id': source['publication_id'],
               'recording_id': source['recording_id'], 'edition_id': edition, 'protocol_sha256': protocol,
               'audio_artifact': source['audio_artifact'], 'canonical_s16_pcm': source['canonical_s16_pcm'],
               'old_text_artifact': source.get('old_text_artifact'), 'input_frame': frame_ref,
               'model_id': model['repo'], 'model_revision': model['revision'], 'settings': SETTINGS,
               'coverage': {'input_samples': cursor, 'covered_samples': cursor, 'contiguous': True,
                            'starts_at_zero': True, 'ends_at_sample_count': True,
                            'all_encoder_exhausted': True, 'chunk_count': len(values)},
               'speaker_role': 'unknown', 'accuracy_verified': False, 'chunks': refs,
               'text_artifact': {**artifact(staging/'transcript.json'), 'path': str(destination/'transcript.json')},
               'plain_text_artifact': {**artifact(staging/'transcript.txt'), 'path': str(destination/'transcript.txt')},
               'stage_receipt': stage_ref}
    W.atomic(staging/'receipt.json', receipt)
    staging.rename(destination)
    return verify_edition(destination/'receipt.json', source, edition, protocol)


def run(frame_path, run_id, max_new_chunks=None):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in run_id):
        raise ValueError('Run ID must be path-safe')
    if max_new_chunks is not None and not 1 <= max_new_chunks <= 1000:
        raise ValueError('A pilot needs a positive bounded new-chunk count')
    RAM.mkdir(parents=True, exist_ok=True); PRIVATE.mkdir(parents=True, exist_ok=True)
    lock = (RAM/'run.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    frame_ref = artifact(frame_path); frame = json.loads(frame_path.read_text())
    if (frame['status'] != 'frozen_full_recording_frame' or not 1 <= len(frame['sources']) <= SETTINGS['max_recordings']
            or sum(x['canonical_s16_pcm']['duration_seconds'] for x in frame['sources']) > SETTINGS['max_input_seconds']):
        raise ValueError('Frame exceeds resource admission')
    if len({x['recording_id'] for x in frame['sources']}) != len(frame['sources']):
        raise ValueError('Duplicate recording identity')
    model = json.loads(MODEL_RECEIPT.read_text()); worker_sha = digest(W.__file__)
    if (model.get('status') != 'downloaded_and_hash_verified'
            or model['repo'] != 'nvidia/parakeet-tdt-0.6b-v3'
            or model['revision'] != '541d1f99c6b0c3cd0b11a95167540bb8edefd82b'):
        raise ValueError('Unexpected model download binding')
    stage_dir = PRIVATE/'runs'/run_id; work = RAM/'runs'/run_id
    if stage_dir.exists() or work.exists():
        raise ValueError('Each attempt needs a fresh immutable run directory')
    stage_dir.mkdir(parents=True); work.mkdir(parents=True)
    sources = []; complete = {}; submitted = set(); received = set(); cached = 0
    for source in frame['sources']:
        read_bound(source['audio_artifact'])
        edition, protocol = edition_id(source, model, worker_sha)
        source = {**source, 'edition_id': edition, 'protocol_sha256': protocol,
                  'worker_sha256': worker_sha, 'model_revision': model['revision']}; sources.append(source)
        path = PRIVATE/'editions'/edition/'receipt.json'
        if path.exists():
            complete[edition] = verify_edition(path, source, edition, protocol)
    request = {'frame': frame_ref, 'model_path': model['output_path'],
               'model_files': [{k: x[k] for k in ('file', 'bytes', 'sha256')} for x in model['files']],
               'model_id': model['repo'], 'model_revision': model['revision'], 'worker_sha256': worker_sha,
               'settings': SETTINGS, 'cache_root': str(RAM/'cache')}
    request['request_sha256'] = hashlib.sha256(encoded(request)).hexdigest()
    W.atomic(stage_dir/'request.json', request)
    stage = {'status': 'running', 'run_id': run_id, 'frame': frame_ref, 'request': artifact(stage_dir/'request.json'),
             'script_sha256': digest(__file__), 'worker_sha256': worker_sha,
             'started_at_unix': time.time(), 'max_new_chunks': max_new_chunks,
             'verified_complete_cache_hits': len(complete), 'resource_samples': [], 'workers': []}
    W.atomic(stage_dir/'stage-receipt.json', stage)
    pending_sources = [x for x in sources if x['edition_id'] not in complete]
    processes = []; states = []; context = mp.get_context('spawn')
    jobs = context.Queue(maxsize=SETTINGS['prefetch_chunks']); results = context.Queue()
    old_ram_bytes = tree_bytes(OLD_RAM); last_resource = 0; decoded_complete = set()
    started = time.monotonic()
    def monitor():
        nonlocal last_resource
        while True:
            try:
                item = results.get_nowait()
            except queue.Empty:
                break
            if item['status'] != 'completed':
                raise RuntimeError('Owned recognition worker failed: '+str(item))
            if item['job_id'] not in submitted or item['job_id'] in received:
                raise ValueError('Unexpected or duplicate worker result')
            read_bound(item['artifact']); received.add(item['job_id'])
        now = time.time()
        if time.monotonic()-started > SETTINGS['max_stage_seconds']:
            raise TimeoutError('Owned batch exceeded its one-hour hard deadline')
        for process, path in zip(processes, states):
            if process.exitcode not in (None, 0):
                raise RuntimeError('Owned model process exited unsuccessfully')
            if not path.exists():
                if now-stage['started_at_unix'] > SETTINGS['max_setup_seconds']:
                    raise TimeoutError('Worker failed to initialize before deadline')
                continue
            state = json.loads(path.read_text()); current = state.get('current_job')
            if current and now-current['started_at_unix'] > SETTINGS['max_chunk_seconds']:
                raise TimeoutError('Owned inference exceeded 180-second hard deadline')
            if state['status'] == 'loading' and now-state['started_at_unix'] > SETTINGS['max_setup_seconds']:
                raise TimeoutError('Owned model load exceeded 240-second hard deadline')
            if state['status'] == 'failed':
                raise RuntimeError('Owned worker reported failure')
        if now-last_resource >= 2:
            rss = 0; auxiliary_rss = 0
            worker_pids = {p.pid for p in processes}
            for pid in worker_pids | OWNED_DECODERS | {os.getpid()}:
                p = Path(f'/proc/{pid}/status')
                if p.exists():
                    for line in p.read_text().splitlines():
                        if line.startswith('VmRSS:'):
                            if pid in worker_pids:
                                rss += int(line.split()[1])*1024
                            else:
                                auxiliary_rss += int(line.split()[1])*1024
            ram_bytes = old_ram_bytes+tree_bytes(RAM)
            memory = ram_bytes+rss+auxiliary_rss
            stage['resource_samples'].append({'at_unix': now, 'worker_rss_bytes': rss,
                                              'supervisor_decoder_rss_bytes': auxiliary_rss,
                                              'asr_ram_file_bytes': ram_bytes, 'conservative_asr_bytes': memory})
            if memory > SETTINGS['max_asr_memory_bytes']:
                raise MemoryError('Conservative ASR memory cap exceeded')
            if tree_bytes(PRIVATE) > SETTINGS['durable_byte_cap'] or shutil.disk_usage(PRIVATE).free < SETTINGS['disk_floor_bytes']:
                raise OSError('Private byte cap or disk floor violated')
            stage.update(submitted_chunks=len(submitted), completed_new_chunks=len(received), cached_chunks=cached)
            W.atomic(stage_dir/'stage-receipt.json', stage); last_resource = now
    try:
        if pending_sources:
            for index in range(SETTINGS['workers']):
                state = work/f'worker-{index+1}.json'; states.append(state)
                process = context.Process(target=W.worker, args=(request, jobs, results, str(state)))
                process.start(); processes.append(process)
                stage['workers'].append({'pid': process.pid, 'state_path': str(state)})
        stop_pilot = False
        for source in pending_sources:
            generator = pcm_windows(source, monitor)
            try:
                for start, raw in generator:
                    end = start+len(raw)//2
                    job_id = source['edition_id']+f'-{start:012d}'
                    job = {'job_id': job_id, 'edition_id': source['edition_id'],
                           'protocol_sha256': source['protocol_sha256'], 'source_id': source['source_id'],
                           'publication_id': source['publication_id'], 'source_audio_sha256': source['audio_artifact']['sha256'],
                           'start_sample': start, 'end_sample': end, 's16_sha256': hashlib.sha256(raw).hexdigest(),
                           'model_revision': model['revision']}
                    cache = RAM/'cache'/source['edition_id']/(job_id+'.json')
                    if cache.exists():
                        validate_chunk(json.loads(cache.read_text()), source, source['edition_id'], source['protocol_sha256'], job)
                        cached += 1
                        continue
                    if max_new_chunks is not None and len(submitted) >= max_new_chunks:
                        stop_pilot = True; break
                    submitted.add(job_id)
                    while True:
                        monitor()
                        try:
                            jobs.put({**job, 's16_bytes': raw}, timeout=0.2); break
                        except queue.Full:
                            continue
                else:
                    decoded_complete.add(source['edition_id'])
            finally:
                generator.close()
            if stop_pilot:
                break
        for _ in processes:
            while True:
                monitor()
                try:
                    jobs.put(None, timeout=0.2); break
                except queue.Full:
                    continue
        while any(p.is_alive() for p in processes) or len(received) < len(submitted):
            monitor(); time.sleep(0.1)
        for p in processes:
            p.join(timeout=5)
        monitor()
        stage.update(status='completed_sampled_pilot' if max_new_chunks is not None else 'completed',
                     finished_at_unix=time.time(), stage_wall_seconds=time.monotonic()-started,
                     submitted_chunks=len(submitted), completed_new_chunks=len(received), cached_chunks=cached,
                     decoded_complete_editions=sorted(decoded_complete))
        for row, path in zip(stage['workers'], states):
            row['state'] = json.loads(path.read_text())
        W.atomic(stage_dir/'stage-receipt.json', stage)
        # This evidence is immutable even if a later durable copy fails.
        W.atomic(stage_dir/'inference-receipt.json', stage)
        inference_ref = artifact(stage_dir/'inference-receipt.json')
        if max_new_chunks is None:
            for source in pending_sources:
                if source['edition_id'] not in decoded_complete:
                    raise ValueError('Source has not reached validated canonical EOF')
                complete[source['edition_id']] = finalize(source, source['edition_id'], source['protocol_sha256'],
                                                           frame_ref, model, inference_ref)
            manifest = {'status': 'completed_full_batch', 'frame': frame_ref, 'model_id': model['repo'],
                        'model_revision': model['revision'], 'settings': SETTINGS,
                        'stage_receipt': inference_ref,
                        'sources': sources, 'editions': [artifact(PRIVATE/'editions'/x['edition_id']/'receipt.json') for x in sources],
                        'reused_prior_editions_manifest': frame['reused_prior_editions_manifest'],
                        'reused_prior_editions': frame['reused_prior_editions'],
                        'scope': 'Full independent-window ASR editions of selected retained sources; previous texts unchanged.'}
            W.atomic(stage_dir/'manifest.json', manifest)
        print(json.dumps({k: stage[k] for k in ('status', 'run_id', 'submitted_chunks', 'completed_new_chunks',
                                               'cached_chunks', 'verified_complete_cache_hits', 'stage_wall_seconds')}), flush=True)
    except BaseException as exc:
        owned_stop(processes)
        stage.update(status='failed', failure_type=type(exc).__name__, failure_message=str(exc)[:500],
                     finished_at_unix=time.time(), stage_wall_seconds=time.monotonic()-started,
                     submitted_chunks=len(submitted), completed_new_chunks=len(received), cached_chunks=cached)
        W.atomic(stage_dir/'stage-receipt.json', stage)
        raise
    finally:
        owned_stop(processes)
        jobs.close(); results.close()
        fcntl.flock(lock, fcntl.LOCK_UN); lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--max-new-chunks', type=int)
    args = parser.parse_args()
    run(args.frame, args.run_id, args.max_new_chunks)
