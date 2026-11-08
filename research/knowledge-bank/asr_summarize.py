#!/usr/bin/env python3
"""Project a completed paired ASR pilot to public metadata and disagreement metrics."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def checked(ref):
    p=Path(ref['path'])
    if p.stat().st_size!=ref.get('bytes',p.stat().st_size) or sha(p)!=ref['sha256']:
        raise ValueError('Bound artifact has changed')
    return p


def words(text):
    text=unicodedata.normalize('NFKC',text).casefold().replace('’',"'")
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*",text,flags=re.UNICODE)


def edit_distance(a,b):
    previous=list(range(len(b)+1))
    for i,token in enumerate(a,1):
        current=[i]
        for j,other in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(token!=other)))
        previous=current
    return previous[-1]


def longest_run(tokens):
    best=current=0;previous=None
    for token in tokens:
        current=current+1 if token==previous else 1
        best=max(best,current);previous=token
    return best


def compare(a,b):
    x,y=words(a),words(b);union=set(x)|set(y)
    negations={"no","not","never","without","cannot","can't","won't","don't","doesn't","isn't","aren't","wasn't","weren't","didn't","hasn't","haven't","wouldn't","couldn't","shouldn't"}
    datewords={'january','february','march','april','may','june','july','august','september','october','november','december',
               'monday','tuesday','wednesday','thursday','friday','saturday','sunday'}
    return {'symmetric_normalized_word_edit_distance':edit_distance(x,y)/max(len(x),len(y),1),
        'baseline_longest_identical_token_run':longest_run(x),
        'upgraded_longest_identical_token_run':longest_run(y),
        'baseline_longest_identical_token_run_ratio':longest_run(x)/max(len(x),1),
        'upgraded_longest_identical_token_run_ratio':longest_run(y)/max(len(y),1),
        'token_set_jaccard':len(set(x)&set(y))/len(union) if union else 1.0,
        'baseline_analysis_tokens':len(x),'upgraded_analysis_tokens':len(y),
        'baseline_negation_cues':sum(w in negations for w in x),'upgraded_negation_cues':sum(w in negations for w in y),
        'baseline_numeric_tokens':sum(any(c.isdigit() for c in w) for w in x),
        'upgraded_numeric_tokens':sum(any(c.isdigit() for c in w) for w in y),
        'baseline_calendar_word_cues':sum(w in datewords for w in x),
        'upgraded_calendar_word_cues':sum(w in datewords for w in y)}


def stage_rows(path,frame):
    stage=json.loads(path.read_text())
    if stage['status']!='completed' or len(stage['workers'])!=2:raise ValueError('A completed two-worker stage is required')
    result={};all_intervals=[];software=[];loads=[];worker_windows=[]
    frame_hash=sha(frame)
    for w in stage['workers']:
        request=json.loads(checked(w['request']).read_text())
        if request['frame_binding']['sha256']!=frame_hash:raise ValueError('Worker used another frame')
        receipt=json.loads(checked(w['receipt']).read_text())
        if receipt['status']!='completed' or receipt['cpu_threads']!=1:raise ValueError('Worker is incomplete or has different thread budget')
        if receipt['request_sha256']!=w['request']['sha256']:raise ValueError('Request hash mismatch')
        if receipt['script_sha256']!=stage['worker_sha256']:raise ValueError('Executed code hash mismatch')
        requests={x['clip_id']:x for x in request['clips']}
        if len(receipt['records'])!=len(requests):raise ValueError('Incomplete selected clip set')
        local=[]
        for r in receipt['records']:
            output=json.loads(checked(r['output']).read_text());checked(r['text_output'])
            c=requests[output['clip_id']]
            if output['clip_id'] in result or output['pcm_sha256']!=c['pcm']['sha256'] or output['source_id']!=c['source_id']:
                raise ValueError('Duplicate or mismatched clip')
            if output['audio_start_seconds']!=c['start_seconds'] or output['audio_end_seconds']!=c['start_seconds']+30:
                raise ValueError('Output time frame changed')
            if output['words']!=len(output['text'].split()):raise ValueError('Word count mismatch')
            if receipt['engine']=='parakeet_transformers' and output.get('encoder_exhausted') is not True:
                raise ValueError('Incomplete encoder traversal')
            if receipt['engine']=='faster_whisper' and output.get('inference_stream_exhausted') is not True:
                raise ValueError('Incomplete decoder iterator')
            if not math.isclose(output['inference_seconds']/30,output['real_time_factor'],rel_tol=1e-10):raise ValueError('RTF mismatch')
            result[output['clip_id']]=output
            interval=(output['wall_start_unix'],output['wall_end_unix']);local.append(interval);all_intervals.append(interval)
        worker_windows.append(local);software.append(receipt['software']);loads.append(receipt['model_load_seconds'])
    overlap=sum(max(0,min(a[1],b[1])-max(a[0],b[0])) for a in worker_windows[0] for b in worker_windows[1])
    if overlap<=0:raise ValueError('No observed simultaneous inference; cannot label parallel execution')
    performance={'workers':2,'cpu_threads_per_worker':1,'actual_inference_overlap_seconds':overlap,
        'model_files':request['model_files'],
        'outer_stage_wall_seconds':stage['end_to_end_wall_seconds'],'model_load_seconds_by_worker':loads,
        'max_conservative_asr_memory_bytes':max(r['conservative_asr_bytes'] for r in stage['resource_samples']),
        'median_window_inference_seconds':statistics.median(x['inference_seconds'] for x in result.values()),
        'median_real_time_factor':statistics.median(x['real_time_factor'] for x in result.values()),
        'sum_window_inference_seconds':sum(x['inference_seconds'] for x in result.values()),
        'recognized_whitespace_words':sum(x['words'] for x in result.values()),
        'max_worker_rss_kib':max(x['max_rss_kib'] for x in result.values()),
        'software':software[0],'stage_receipt_sha256':sha(path)}
    if software[0]!=software[1]:raise ValueError('Worker software differs')
    return result,performance


def summarize(frame_path,baseline,upgraded,model_receipt,output):
    if output.exists():raise ValueError('Use a fresh public projection path')
    frame=json.loads(frame_path.read_text());old,oldperf=stage_rows(baseline,frame_path);new,newperf=stage_rows(upgraded,frame_path)
    ids={x['clip_id'] for x in frame['clips']}
    if set(old)!=ids or set(new)!=ids:raise ValueError('Model clip sets differ')
    model=json.loads(model_receipt.read_text())
    if model['status']!='downloaded_and_hash_verified':raise ValueError('Model download incomplete')
    source_lookup={x['source_id']:x for x in frame['sources']};rows=[]
    for clip in frame['clips']:
        cid=clip['clip_id'];a=old[cid];b=new[cid];source=source_lookup[clip['source_id']]
        if a['pcm_sha256']!=b['pcm_sha256']:raise ValueError('Models received different PCM')
        rows.append({'clip_id':cid,'source_id':clip['source_id'],'publication_id':clip['publication_id'],
            'title':source['title'],'source_url':source['source_url'],'context':source['context'],
            'recording_duration_seconds':source['duration_seconds'],'start_seconds':clip['start_seconds'],
            'end_seconds':clip['start_seconds']+30,'duration_seconds':30,'pcm_sha256':clip['pcm']['sha256'],
            'source_audio_sha256':source['audio']['sha256'],
            'baseline_words':a['words'],'upgraded_words':b['words'],
            'baseline_inference_seconds':a['inference_seconds'],'upgraded_inference_seconds':b['inference_seconds'],
            'baseline_real_time_factor':a['real_time_factor'],'upgraded_real_time_factor':b['real_time_factor'],
            'baseline_segment_end_overruns':sum(x['end']>clip['duration_seconds'] for x in a.get('segments',[])),
            'baseline_max_segment_end_overrun_seconds':max([0]+[x['end']-clip['duration_seconds'] for x in a.get('segments',[])]),
            'baseline_text_sha256':hashlib.sha256(a['text'].encode()).hexdigest(),
            'upgraded_text_sha256':hashlib.sha256(b['text'].encode()).hexdigest(),**compare(a['text'],b['text'])})
    summary={'recordings':len(frame['sources']),'source_contexts':len({x['context'] for x in rows}),
        'paired_windows':len(rows),'unique_audio_seconds':sum(x['duration_seconds'] for x in rows),
        'model_window_inferences':len(rows)*2,
        'median_symmetric_normalized_word_edit_distance':statistics.median(x['symmetric_normalized_word_edit_distance'] for x in rows),
        'mean_symmetric_normalized_word_edit_distance':statistics.mean(x['symmetric_normalized_word_edit_distance'] for x in rows),
        'median_token_set_jaccard':statistics.median(x['token_set_jaccard'] for x in rows),
        'windows_with_negation_count_difference':sum(x['baseline_negation_cues']!=x['upgraded_negation_cues'] for x in rows),
        'windows_with_numeric_count_difference':sum(x['baseline_numeric_tokens']!=x['upgraded_numeric_tokens'] for x in rows)}
    summary['baseline_windows_with_timestamp_overrun']=sum(x['baseline_segment_end_overruns']>0 for x in rows)
    summary['baseline_raw_segment_end_overruns']=sum(x['baseline_segment_end_overruns'] for x in rows)
    summary['baseline_max_timestamp_overrun_seconds']=max(x['baseline_max_segment_end_overrun_seconds'] for x in rows)
    summary['posthoc_baseline_token_run_ge10_windows']=sum(x['baseline_longest_identical_token_run']>=10 for x in rows)
    summary['posthoc_upgraded_token_run_ge10_windows']=sum(x['upgraded_longest_identical_token_run']>=10 for x in rows)
    data={'schema_version':1,'status':'completed_paired_window_pilot','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':frame['scope'],'summary':summary,'selection_rule':frame['selection_rule'],
        'model':{'id':model['repo'],'revision':model['revision'],'published_family':'0.6B-class',
            'floating_state_elements':627057286,'state_count_scope':'Hub F32 state-tensor element count includes normalization buffers; not an exact trainable-parameter count.',
            'downloaded_bytes':model['selected_bytes'],'files':[{k:x[k] for k in ('file','bytes','sha256')} for x in model['files']],
            'model_card_url':f"https://huggingface.co/{model['repo']}/blob/{model['revision']}/README.md",
            'device':'cpu','compute_type':'float32','runtime_storage':'Temporary RAM-backed cloud model cache; reproducible download, not durable account storage'},
        'baseline':{'id':'Systran/faster-whisper-tiny.en','device':'cpu','compute_type':'int8',
            'revision':None,'model_files':oldperf['model_files'],
            'scope':'Controlled rerun of the cached tiny.en checkpoint on identical PCM; not the historical whole-recording ASR outputs.',
            'beam_size':5,'language':'en','vad_filter':False,'condition_on_previous_text':False},
        'hardware':{'cpu_quota_cores':4,'memory_limit_bytes':34359738368,'cuda_available':False,
            'timing_scope':'Shared cloud host with concurrent research/UI tasks; measured execution, not an isolated hardware or matched serial-versus-parallel speedup benchmark.'},
        'baseline_performance':oldperf,'upgraded_performance':newperf,'clips':rows,
        'measurement':{'accuracy_measured':False,'reference_transcript':'No independently word-aligned reference for these windows',
            'word_edit_metric':'Levenshtein distance between NFKC/casefolded Unicode word-token sequences divided by the larger sequence length; symmetric transcript disagreement, not WER or an accuracy estimate.',
            'token_set_jaccard':'Intersection/union of normalized distinct word tokens; ignores order, frequency and proposition meaning.',
            'cue_counts':'Literal negation tokens, digit-bearing tokens and month/day words are review cues; count differences do not prove changed meaning or correctness. Calendar forms include ambiguous words such as may; these are not recognized dates.',
            'timestamp_diagnostic':'Tiny raw segment end estimates are retained unchanged, including estimates beyond the selected 30-second input. They do not establish speech outside that input. Parakeet has window boundaries only; timestamp accuracy is not compared.'},
        'posthoc_repetition_diagnostic':{'rule':'Longest run of identical normalized word tokens >=10, added after inspecting the largest model-disagreement example.',
            'flagged_windows':[{k:r[k] for k in ('clip_id','source_id','context','baseline_longest_identical_token_run','upgraded_longest_identical_token_run')} for r in rows if max(r['baseline_longest_identical_token_run'],r['upgraded_longest_identical_token_run'])>=10],
            'interpretation':'These are triage flags, not verified hallucinations or proof that the other model is correct.',
            'scope':'No output is excluded from the main paired metrics. Legitimate spoken repetition could also trigger this unvalidated screen.'},
        'limitations':['Eight selected recordings and sixteen windows are not a representative full-corpus accuracy benchmark.',
            'Window boundaries can split sentences and remove conversational context; counts cover the complete selected PCM windows, not complete recording transcripts.',
            'Different architecture, language handling, precision and decoding algorithms are confounded; larger/newer model capacity does not establish better domain accuracy.',
            'Source audio encodings, accents, background sound, speakers and recording conditions differ; source-context labels do not identify per-utterance speakers.',
            'Model disagreement and shared wording cannot verify facts, entity identity, answers or contradictions. Proper names, negation and dates require source listening or independent reference annotation.',
            'Timing includes a shared cloud workload. Observed worker overlap establishes concurrent execution; no causal parallel-speedup claim follows.',
            'RAM-backed model/dependency files can disappear with the execution environment. Full texts remain private; older corpus fits remain unchanged.'],
        'provenance':{'frame_sha256':sha(frame_path),'model_download_receipt_sha256':sha(model_receipt),'producer_sha256':sha(__file__)}}
    raw=json.dumps(data,indent=2,ensure_ascii=False)+'\n'
    if '/workspace/' in raw or '/dev/shm/' in raw or len(raw.encode())>1_000_000:raise ValueError('Public projection leaks private paths or exceeds cap')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(raw)
    print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frame','baseline','upgraded','model-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();summarize(a.frame,a.baseline,a.upgraded,a.model_receipt,a.output)
