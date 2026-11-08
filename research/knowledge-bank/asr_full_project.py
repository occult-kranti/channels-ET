#!/usr/bin/env python3
"""Publish metadata for a completed full-input Council ASR edition, without source text."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import statistics


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def checked(ref):
    p=Path(ref['path']);raw=p.read_bytes()
    if len(raw)!=ref.get('bytes',len(raw)) or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('Bound artifact changed')
    return json.loads(raw)


def project(manifest_path,output):
    if output.exists():raise ValueError('Use a fresh output path')
    manifest=json.loads(manifest_path.read_text())
    if manifest['status']!='completed_full_chunked_asr' or len(manifest['documents'])!=4:
        raise ValueError('Only the complete four-recording edition can be projected')
    frame=checked(manifest['input_frame']);stage=checked(manifest['stage_receipt'])
    if stage['status']!='completed' or len(stage['workers'])!=2:raise ValueError('Expected completed two-worker full stage')
    windows=[];runtimes=[];worker_loads=[];learned_counts=[]
    for worker in stage['workers']:
        receipt=checked(worker['receipt'])
        if receipt['status']!='completed' or receipt['cpu_threads']!=1:raise ValueError('Worker incomplete or thread count differs')
        windows.append([(r['wall_start_unix'],r['wall_end_unix']) for r in receipt['records']])
        runtimes.extend(r['real_time_factor'] for r in receipt['records'])
        worker_loads.append(receipt['model_load_seconds']);learned_counts.append(receipt['learned_parameter_elements'])
    overlap=sum(max(0,min(a[1],b[1])-max(a[0],b[0])) for a in windows[0] for b in windows[1])
    if overlap<=0 or len(set(learned_counts))!=1:raise ValueError('Missing concurrency evidence or model parameter mismatch')
    documents=[]
    for doc in manifest['documents']:
        old=checked(doc['old_text_artifact']);new=checked(doc['text_artifact']);receipt=checked(doc['asr_receipt'])
        old_receipt=checked(doc['old_asr_receipt']);canonical=doc['canonical_s16_pcm']
        if canonical['sha256']!=old_receipt['decoder']['raw_pcm_sha256'] or canonical['sample_count']!=old_receipt['decoder']['sample_count']:
            raise ValueError('Canonical old/new waveform differs')
        coverage=doc['coverage'];chunks=doc['chunks']
        if coverage['input_samples']!=coverage['covered_samples'] or not all(coverage[k] for k in ('contiguous','starts_at_zero','ends_at_sample_count','all_encoder_exhausted')):
            raise ValueError('Incomplete full input coverage')
        if len(chunks)!=coverage['chunk_count'] or len(new['turns'])!=len(chunks):raise ValueError('Chunk denominator mismatch')
        cursor=0
        for chunk in chunks:
            if chunk['start_sample']!=cursor or not chunk['encoder_exhausted']:raise ValueError('Chunk gap/overlap/incomplete traversal')
            cursor=chunk['end_sample']
        if cursor!=canonical['sample_count'] or doc['words']!=len(new['text'].split()):raise ValueError('Source totals mismatch')
        documents.append({'source_id':doc['source_id'],'counterpart_source_id':doc['counterpart_source_id'],
            'publication_id':doc['publication_id'],'title':doc['title'],'source_url':doc['source_url'],
            'medium':doc['medium'],'claimed_label':doc['claimed_label'],'attribution_scope':doc['attribution_scope'],
            'old_words':len(old['text'].split()),'new_words':doc['words'],'chunks':len(chunks),
            'empty_text_chunks':sum(c['words']==0 for c in chunks),
            'duration_seconds':canonical['duration_seconds'],'sample_count':canonical['sample_count'],
            'last_chunk_seconds':chunks[-1]['samples']/16000,'coverage':coverage,
            'audio_sha256':doc['audio_artifact']['sha256'],'canonical_s16_pcm_sha256':canonical['sha256'],
            'model_f32_pcm_sha256':doc['decoded_pcm']['sha256'],
            'old_text_artifact_sha256':doc['old_text_artifact']['sha256'],
            'new_text_artifact_sha256':doc['text_artifact']['sha256'],'new_asr_receipt_sha256':doc['asr_receipt']['sha256'],
            'speaker_role':'unknown','accuracy_verified':False})
    if sum(d['chunks'] for d in documents)!=manifest['chunks']:raise ValueError('Full chunk count mismatch')
    data={'schema_version':1,'status':'completed_full_chunked_asr','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':manifest['scope'],'summary':{'recordings':4,'chunks':manifest['chunks'],
            'covered_audio_seconds':manifest['covered_audio_seconds'],'covered_samples':sum(d['sample_count'] for d in documents),
            'new_words':sum(d['new_words'] for d in documents),'old_words':sum(d['old_words'] for d in documents),
            'empty_text_chunks':sum(d['empty_text_chunks'] for d in documents),
            'new_audio_downloads':0,'old_editions_preserved':True,'full_text_editions_retranscribed':4},
        'model':{'id':manifest['model_id'],'revision':manifest['model_revision'],'device':'cpu','precision':'float32',
            'learned_parameter_elements':learned_counts[0],'model_storage':'Temporary RAM-backed cloud cache; not permanent account storage'},
        'recognition_protocol':{'window_seconds':30,'last_partial_windows_included':True,'nonoverlapping':True,
            'canonical_audio':'Same 16kHz mono S16 PCM hash and sample count as each old full ASR; F32 input is int16/32768.',
            'context':'Each chunk recognized independently; no cross-chunk decoder conditioning.',
            'assembly':'Ordered verbatim chunk-output concatenation; no overlap deduplication, punctuation stitching or speaker inference.',
            'timestamp_scope':'Fixed sample-window boundaries, not word-aligned times or verified speaker turns.'},
        'performance':{'workers':2,'cpu_threads_per_worker':1,'stage_wall_seconds':stage['end_to_end_wall_seconds'],
            'model_load_seconds_by_worker':worker_loads,'actual_inference_overlap_seconds':overlap,
            'median_chunk_real_time_factor':statistics.median(runtimes),
            'max_conservative_asr_memory_bytes':max(r['conservative_asr_bytes'] for r in stage['resource_samples']),
            'timing_scope':'Shared cloud workload; worker stage includes hash checks, loading and inference. Download/preparation/final projection are outside this measured stage. No matched serial speedup claim.'},
        'documents':documents,'limitations':['Complete sample coverage and encoder exhaustion do not verify every word, speaker identity or channeled attribution.',
            'Independent30-second chunk boundaries can split words/sentences and lose conversational context; boundary accuracy has not been measured.',
            'Old and new models differ in architecture, language handling, decoding, precision and context; word-count or retrieval changes are sensitivity findings, not accuracy improvement.',
            'These four recordings are reused from earlier collections; no additional media downloads or complete YouTube channel census is implied.',
            'The primary25-text knowledge-bank fit and its old-source card locators remain frozen. This is a separate four-edition sensitivity layer requiring fresh annotation for new locators.'],
        'provenance':{'private_manifest_sha256':sha(manifest_path),'input_frame_sha256':manifest['input_frame']['sha256'],
            'stage_receipt_sha256':manifest['stage_receipt']['sha256'],'projection_script_sha256':sha(__file__)}}
    raw=json.dumps(data,indent=2,ensure_ascii=False)+'\n'
    if '/workspace/' in raw or '/dev/shm/' in raw or len(raw.encode())>1_000_000:raise ValueError('Private path or oversized public projection')
    if sum(p.stat().st_size for p in manifest_path.parent.rglob('*') if p.is_file())+len(raw.encode())>5_000_000:
        raise ValueError('Actual full-run durable bytes plus projection exceed the admitted five-megabyte budget')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(raw)
    print(json.dumps(data['summary']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();project(a.manifest,a.output)
