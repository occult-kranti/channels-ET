#!/usr/bin/env python3
"""Build a text-free public status from retained, hash-verified private evidence."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sqlite3

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def binding(path):
    p=Path(path)
    return {'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size}

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded

def public_audio_metrics(metrics):
    # No arbitrary text, locations or future upstream metadata crosses this boundary.
    fields=('sample_rate_hz','channels','sample_count','decoded_duration_seconds',
        'rms_dbfs','sample_peak_dbfs','near_full_scale_samples',
        'near_full_scale_sample_fraction','quiet_window_milliseconds',
        'quiet_threshold_dbfs','quiet_sample_fraction','quiet_duration_seconds',
        'longest_contiguous_quiet_seconds')
    out={}
    for key in fields:
        if key not in metrics:continue
        value=metrics[key]
        if value is None and key in ('rms_dbfs','sample_peak_dbfs'):
            out[key]=None;continue
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('Public audio metric must be a finite number')
        out[key]=value
    return out

def verify_archive(ar,audio):
    if ar.get('kind')!='batch-local-archive' or ar.get('status')!='completed' or ar.get('exact_file_set_verified') is not True:
        raise ValueError('Only a completed exact-file-set local archive can be published as complete')
    root=audio.private_path(ar.get('actual_root'))
    if not root.is_dir():raise ValueError('Actual archive directory is missing')
    rows=ar.get('records',[]);expected={}
    for row in rows:
        relative=Path(row.get('relative_path',''))
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() in ('','.'):raise ValueError('Invalid archive path')
        key=relative.as_posix()
        if key in expected:raise ValueError('Duplicate archived path')
        target=audio.private_path(root/relative,exists=True)
        if target.stat().st_size!=row.get('bytes') or sha(target)!=row.get('sha256'):
            raise ValueError('Actual archive file changed')
        expected[key]=row
    found=set()
    for target in root.rglob('*'):
        if target.is_symlink():raise ValueError('Archive must not contain symlinks')
        if target.is_file():found.add(target.relative_to(root).as_posix())
    if found!=set(expected) or not found:raise ValueError('Actual archive file set differs')
    if sum(r['bytes'] for r in rows)!=ar.get('verified_bytes'):raise ValueError('Archive byte total differs')
    return {(r['sha256'],r['bytes']) for r in rows}

def build(args):
    audio=module('batch_audio_validation','audio.py')
    analysis=module('batch_analysis_validation','analyze.py')
    plan=read(args.selection);access=read(args.access)
    media=read(args.media_input)
    sources={};media_hashes=set();expected_artifacts=set();bindings=[binding(p) for p in [args.selection,args.access,args.media_input]]
    for raw in media.get('records',[]):
        record,probe=audio.validate_record(raw)
        sid=record['source_id']
        expected_artifacts.add((record['sha256'],record['bytes']))
        if sid in sources:raise ValueError('Duplicate source ID in verified media input')
        if record['sha256'] in media_hashes:raise ValueError('Exact media bytes repeat under different source IDs')
        media_hashes.add(record['sha256'])
        if record['provider']!='publisher_video':raise ValueError('This release keeps independent creator videos distinct from its separate YouTube ledger')
        sources[sid]={'sourceId':sid,'provider':record['provider'],'title':record.get('title',sid),
            'publishedDate':record.get('published_date'),'mediumId':record['medium_id'],
            'publisherId':record['channel_id'],'claimedEntityLabel':record.get('claimed_entity_label'),
            'speakerScope':record.get('speaker_scope','Publisher-attributed context; mixed speakers may occur.'),
            'sourceUrl':analysis.safe_source_url(record.get('source_url')),'durationSeconds':probe['duration_seconds'],
            'bytes':record['bytes'],'mediaSHA256':record['sha256'],'asr':None}
    documents,excluded,aliases,audit=analysis.load_documents(args.asr_run)
    if aliases:raise ValueError('Duplicate ASR source or exact-media alias in publication inputs')
    validated={d['summary']['source_id']:d['summary'] for d in documents}
    for run_path in args.asr_run:
        run=read(run_path);bindings.append(binding(run_path))
        for r in run.get('records',[]):
            if r.get('status')!='completed':continue
            sid=r['source_id']
            if sid not in validated:raise ValueError('Completed ASR lacks a validated nonempty transcript')
            if sid not in sources:raise ValueError('ASR source is absent from this media input')
            if sources[sid]['asr'] is not None:raise ValueError('Duplicate ASR receipt for one source')
            p=Path(r['receipt_path'])
            if sha(p)!=r['receipt_sha256']:raise ValueError('ASR receipt hash mismatch')
            rec=read(p)
            if rec['source_id']!=sid or rec['binding']['source']['sha256']!=sources[sid]['mediaSHA256']:
                raise ValueError('ASR does not bind this original video')
            for a in rec['verified_artifacts']:
                ap=Path(a['local_path'])
                if ap.stat().st_size!=a['bytes'] or sha(ap)!=a['sha256']:raise ValueError('ASR output/source changed')
                expected_artifacts.add((a['sha256'],a['bytes']))
            a=rec['asr'];metrics=rec['audio_metrics']
            sources[sid]['asr']={'status':rec['status'],'segments':a['segments'],
                'whitespaceWords':a['whitespace_word_count'],'language':a.get('language_reported'),
                'durationAfterVADSeconds':a.get('duration_after_vad_seconds'),
                'humanReviewed':False,'diarizationPerformed':False,
                'timingQuality':validated[sid]['asr_timing_quality'],
                'receiptSHA256':r['receipt_sha256'],'audioMetrics':public_audio_metrics(metrics)}
    if not args.youtube_ledger.is_file():raise ValueError('Original reconciled YouTube ledger is required; never recreate it here')
    with sqlite3.connect(args.youtube_ledger.resolve().as_uri()+'?mode=ro',uri=True) as c:
        yt=c.execute("SELECT count(distinct source_id) FROM artifacts WHERE kind='video' AND status='verified_quarantine'").fetchone()[0]
        slots=c.execute('SELECT count(*) FROM bashar_slots').fetchone()[0]
        attempts=c.execute('SELECT sum(attempts) FROM jobs').fetchone()[0]
    archive={'status':'pending','destination':'private managed cloud workspace','mode':None,'driveUploadsThisRun':0}
    if args.archive_receipt:
        ar=read(args.archive_receipt);bindings.append(binding(args.archive_receipt))
        archived=verify_archive(ar,audio)
        if not expected_artifacts.issubset(archived):raise ValueError('Completed archive does not contain every displayed source and ASR artifact')
        archive.update(status='completed',mode=ar.get('mode',ar.get('storage_mode',ar.get('local_mode'))),
            files=len(ar.get('records',[])),logicalVerifiedBytes=ar['verified_bytes'],
            newUniqueFileBytes=ar.get('new_unique_file_bytes'),linkedFiles=ar.get('linked_files'),
            copiedFiles=ar.get('copied_files'),receiptSHA256=sha(args.archive_receipt))
    records=sorted(sources.values(),key=lambda x:(x.get('publishedDate') or '',x['sourceId']))
    out={'schemaVersion':1,'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),
        'title':'First video batch and private archive','selection':plan['summary'],
        'youtubeAccess':{'status':access['watch_probe_status'],'stage':access['stage'],
            'connectStatus':int(access['transport_diagnostic']['connect_code']),
            'originResponseReceived':access['youtube_origin_response_received'],'checkedAt':access['checked_at'],
            'rootCause':access['root_cause']},
        'execution':{'youtubeVideosInReconciledLedger':yt,'youtubeJobAttemptsInLedger':attempts,
            'basharSlotsUsed':slots,'independentCreatorVideos':len(records),
            'creatorContexts':len({r['mediumId'] for r in records}),
            'creatorMediaBytes':sum(r['bytes'] for r in records),
            'creatorDurationSeconds':sum(r['durationSeconds'] for r in records),
            'asrCompletedSources':sum(r['asr'] is not None for r in records),
            'asrWhitespaceWords':sum(r['asr']['whitespaceWords'] for r in records if r['asr'])},
        'archive':archive,'records':records,'sourceBindings':bindings,
        'limitations':['Independent creator downloads are separate from YouTube uploads and their unfilled per-medium quotas.',
            'These recordings belong to one publisher/creator series; ten videos are not ten independently sampled mediums.',
            'Automatic ASR may omit or misrecognize speech and does not identify speakers or authenticate an entity.',
            'A publisher reference transcript and ASR of the same recording are two versions of one source.',
            'The private cloud archive persists with the execution environment; it is not permanent account storage.',
            'Hardlink archives share underlying files with their source paths and are not independent backups.'],
        'builderSHA256':sha(__file__)}
    if any(r['asr'] and (r['asr']['timingQuality'].get('timestamp_repaired_segment_count') or 0)>0 for r in records):
        out['limitations'].append('A source-specific timestamp correction is disclosed in the affected recording. Correcting an endpoint does not validate its terminal words or alignment against the audio.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',type=Path,default=HERE/'plan/proposed-batch.json')
    p.add_argument('--access',type=Path,required=True)
    p.add_argument('--media-input',type=Path,required=True)
    p.add_argument('--asr-run',type=Path,action='append',default=[])
    p.add_argument('--youtube-ledger',type=Path,required=True)
    p.add_argument('--archive-receipt',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=build(args)
    print(json.dumps({'execution':r['execution'],'archive':r['archive']},indent=2))
if __name__=='__main__':main()
