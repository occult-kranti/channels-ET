#!/usr/bin/env python3
"""One finite completion watch, frozen descriptive refit, guarded metadata release.

No downloads or inference are started here. Run only after a reviewed clean commit.
--dry-run stages and verifies privately; --no-push creates a local commit only.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
EXECUTED_SOURCE = Path(__file__).read_bytes()
PRIVATE = Path('/workspace/channels-et-private')
BASE = PRIVATE / 'subscription-screening-2026-11'
PYTHON = Path('/workspace/channels-et-analysis-venv/bin/python')
FLOOR = 2 * 1024**3 + 128 * 1024**2
FIGURES = {f'collected-{kind}.{ext}' for kind in ('coverage', 'similarity') for ext in ('png', 'svg', 'pdf')}
ALLOWLIST = {
    'dist/channeling-network/acquisition.json',
    'dist/channeling-network/collected-audio-analysis.json',
    'dist/subscription-audit/acquisition.json',
    'dist/subscription-audit/data.json',
    'research/subscription-screening/publisher-audio-acquisition.json',
    *(f'dist/channeling-network/collected-audio-figures/{f}' for f in FIGURES),
}
RUNNING = {'snapshot_started', 'waiting_for_asr_lock', 'source_specific_recognition_hold_applied', 'terminal_display_end_repaired'}
V4_RUNNING = RUNNING | {'source_specific_recognition_quarantined','snapshot_halted_for_diagnostic_review'}
TERMINAL = {'frame_complete', 'selected_frame_complete_with_recognition_holds'}
FALLBACK_PUBLICATIONS = ('@akanksshaa:rss:f35e0cfac4d68e2c','@akanksshaa:rss:b9fd4b8c29ce9611')
COMMIT_MESSAGE = 'Refresh completed publisher audio snapshot and descriptive analysis'
COMMIT_BODY = ('Freeze the finite acquisition and reviewed recognition dispositions; update source-context '
               'coverage, lexical analyses and figures. Preserve prior fitted studies and private source texts.')

class ReviewRequired(RuntimeError):
    """Safe event code only: never interpolate raw subprocess output or credentials."""

def require(condition, code):
    if not condition:
        raise ReviewRequired(code)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha(path):
    return digest(Path(path).read_bytes())

def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def safe_file(path):
    path = Path(path).absolute()
    require('..' not in path.parts, 'parent_traversal_rejected')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink_rejected')
    require(path.is_file(), 'required_file_missing')
    return path

def bound(ref):
    p = safe_file(ref['path'])
    require(p.is_relative_to(PRIVATE), 'artifact_outside_private_root')
    raw = p.read_bytes()
    require(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'artifact_binding_mismatch')
    return raw

def env():
    e = {k:v for k,v in os.environ.items() if not k.startswith(('GIT_TRACE', 'GIT_CONFIG_', 'GIT_CURL_VERBOSE')) and k not in
         ('GIT_DIR','GIT_COMMON_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','PYTHONOPTIMIZE')}
    e.update(GIT_TERMINAL_PROMPT='0', CHANNELS_ET_BUILD_EXPANSION='0', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return e

def run(args, *, cwd=ROOT, timeout=1800):
    try:
        p = subprocess.run([str(x) for x in args], cwd=cwd, env=env(), capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise ReviewRequired('command_unavailable_or_timed_out') from None
    require(p.returncode == 0, 'command_failed_' + Path(str(args[0])).name)
    return p.stdout

def git(args, repo=ROOT):
    return run(['git', *args], cwd=repo, timeout=90).decode().strip()

def remote_head(repo=ROOT):
    # An explicit destination avoids a changed pushURL silently redirecting publication.
    url = git(['remote', 'get-url', 'origin'], repo)
    require(url in ('https://github.com/occult-kranti/channels-ET.git', 'https://github.com/occult-kranti/channels-ET',
                    'git@github.com:occult-kranti/channels-ET.git'), 'unexpected_origin')
    require(git(['remote', 'get-url', '--push', 'origin'], repo) == url, 'unexpected_push_origin')
    lines = git(['ls-remote', '--exit-code', 'origin', 'refs/heads/main'], repo).splitlines()
    require(len(lines) == 1 and lines[0].split()[1:] == ['refs/heads/main'], 'remote_main_unresolved')
    return lines[0].split()[0]

def git_guard(expected, repo=ROOT, remote=True):
    require(bool(re.fullmatch('[0-9a-f]{40}', expected)), 'expected_head_must_be_full_sha')
    require(git(['rev-parse', 'HEAD'], repo) == expected, 'head_changed')
    require(git(['branch', '--show-current'], repo) == 'main', 'main_branch_required')
    require(not git(['status', '--porcelain=v1', '--untracked-files=all'], repo), 'worktree_not_clean')
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'index.lock'):
        location = Path(git(['rev-parse', '--git-path', name], repo))
        require(not (location if location.is_absolute() else repo/location).exists(), 'git_operation_in_progress')
    if remote:
        require(remote_head(repo) == expected, 'remote_main_changed')

def disk_guard(path, additional=0):
    require(shutil.disk_usage(path).free >= FLOOR + additional, 'insufficient_disk_reserve')

def memory_headroom():
    root=Path('/sys/fs/cgroup')
    try:
        limit=(root/'memory.max').read_text().strip();used=int((root/'memory.current').read_text())
        return max(0,int(limit)-used) if limit != 'max' else 0
    except (OSError,ValueError):return 0

def reviewed_fallback(fallback, review, held, expected_publication=None):
    if not fallback.exists() or not review.exists():return None
    fraw=safe_file(fallback).read_bytes();f=json.loads(fraw)
    if f.get('status') in ('running','single_experimental_retry_running'):return None
    rraw=safe_file(review).read_bytes();r=json.loads(rraw)
    require(r.get('schema_version')==1 and r.get('manifest_sha256')==digest(fraw),'fallback_review_stale')
    require(r.get('publication_id') in held and (expected_publication is None or r['publication_id']==expected_publication),'fallback_scope_mismatch')
    admitted=[]
    if r.get('status')=='accepted_for_analysis':
        require(f.get('status')=='single_experimental_retry_completed_pending_review' and len(f.get('records',[]))==1,'fallback_admission_mismatch')
        item=f['records'][0]
        require(item.get('status')=='completed' and item['publication_id']==r['publication_id'],'fallback_receipt_identity')
        receipt=safe_file(Path(item['outputs']['normalized']['path']).parent/'receipt.json')
        require(json.loads(receipt.read_bytes())==item and sha(receipt)==r.get('receipt_sha256'),'fallback_receipt_review_mismatch')
        admitted=[item]
    else:
        require(r.get('status')=='accepted_unadmitted_hold' and f.get('status') in
                ('experimental_retry_unadmitted','single_experimental_retry_failed') and not f.get('records') and
                r.get('receipt_sha256') is None,'fallback_requires_review')
    return fraw,rraw,admitted

def validate_v4_policy(review_path, ledger_path=None):
    raw=safe_file(review_path).read_bytes();review=json.loads(raw)
    require(review.get('schema_version')==1 and review.get('status')=='accepted_v4_timestamp_quarantine_policy','v4_policy_unreviewed')
    code=ROOT/'research/subscription-screening/continue_publisher_asr_v4.py'
    code_raw=safe_file(code).read_bytes()
    require(digest(code_raw)==review.get('policy_code_sha256'),'v4_policy_code_changed')
    executed=BASE/'publisher-asr-v2/executed-asr-queue-v4.py'
    require(safe_file(executed).read_bytes()==code_raw,'v4_executed_policy_changed')
    initial_raw=bound(review['initial_hold_ledger']);initial=json.loads(initial_raw)
    require(initial.get('status')=='reviewed_source_specific_recognition_holds','v4_initial_holds_unreviewed')
    if ledger_path is not None:
        ledger_raw=safe_file(ledger_path).read_bytes();ledger=json.loads(ledger_raw)
        require((digest(ledger_raw)==digest(initial_raw)) or
                (ledger.get('status')=='policy_validated_source_specific_recognition_holds' and
                 ledger.get('initial_ledger_sha256')==digest(initial_raw) and ledger.get('policy_code_sha256')==digest(code_raw)),
                'v4_ledger_policy_binding_changed')
        by_id={r['source_id']:r for r in ledger['records']};initial_ids={r['source_id'] for r in initial['records']}
        require(len(by_id)==len(ledger['records']) and all(by_id.get(r['source_id'])==r for r in initial['records']),'v4_initial_hold_changed')
        for sid,h in by_id.items():
            if sid not in initial_ids:
                require(h.get('review_status')=='automatic_reviewed_policy_not_manual_source_review' and
                        h.get('quarantine_policy_sha256')==digest(code_raw) and h.get('human_reviewed') is False and
                        h.get('audio_content_listened') is False,'v4_automatic_hold_scope_changed')
        spec=importlib.util.spec_from_file_location('reviewed_v4_policy',code);policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
        require(policy.EXECUTION_SHA==digest(code_raw),'v4_loaded_policy_changed')
        require(set(policy.validate_holds(ledger_path))==set(by_id),'v4_hold_validator_disagrees')
        require(safe_file(code).read_bytes()==code_raw and safe_file(review_path).read_bytes()==raw,'v4_policy_changed_during_validation')
    return {'hold-review.json':raw,'initial-holds.json':initial_raw,'executed-hold-policy.py':code_raw}

def read_state(acquisition, queue, fallback, review, hold_review, additional_fallbacks=(), policy_review=None):
    """Read one hash-coherent terminal tuple. None means recognized running state."""
    paths = [acquisition, queue]
    initial = {str(p): safe_file(p).read_bytes() for p in paths}
    a, q = (json.loads(initial[str(p)]) for p in paths)
    require(a.get('status') in ('running', 'frame_complete'), 'acquisition_requires_review')
    version=q.get('queue_version');require(version in (3,4),'queue_version_unreviewed')
    policy_sources={}
    if version==4:
        require(policy_review is not None,'v4_policy_review_required')
        policy_sources=validate_v4_policy(policy_review)
    require(q.get('status') in (V4_RUNNING if version==4 else RUNNING) | TERMINAL, 'queue_requires_review')
    if a['status'] != 'frame_complete' or q['status'] not in TERMINAL:
        return None
    rows = a.get('records', [])
    ids = [r['publication_id'] for r in rows]
    require(len(rows) == a.get('completed_count') == a.get('frame_count') == 229, 'finite_frame_incomplete')
    require(len(set(ids)) == len(ids) and all(r.get('status') == 'completed' for r in rows), 'invalid_acquisition_rows')
    require(not a.get('errors') and not a.get('stop'), 'acquisition_errors')
    frame_raw = bound(a['source_frame']); frame = json.loads(frame_raw)
    frame_by_id = {r['source_id']:r for r in frame}
    require(len(frame_by_id) == len(frame) == len(rows) and
            {r['source_id'] for r in rows} == set(frame_by_id) and
            all(r['source'] == frame_by_id[r['source_id']] for r in rows), 'acquisition_frame_mismatch')
    asr_raw = bound(q['asr_manifest']); s = json.loads(asr_raw)
    require(s.get('status') == 'selected_snapshot_complete', 'asr_manifest_not_complete')
    selected_raw = bound(s['input']); selected = json.loads(selected_raw)
    require(selected.get('unfiltered_acquisition_sha256') == digest(initial[str(acquisition)]), 'stale_selected_snapshot')
    hold_raw = bound(q['hold_ledger']); holds = json.loads(hold_raw)
    if version==3:
        review_raw=safe_file(hold_review).read_bytes();reviewed=json.loads(review_raw)
        require(reviewed.get('status')=='accepted_for_continuation_with_explicit_hold' and
                reviewed.get('hold_ledger_sha256')==digest(hold_raw),'hold_review_missing_or_stale')
        require(holds.get('status')=='reviewed_source_specific_recognition_holds','hold_ledger_unreviewed')
    else:
        policy_sources=validate_v4_policy(policy_review,Path(q['hold_ledger']['path']))
        review_raw=policy_sources['hold-review.json'];hold_review=policy_review
    held = {r['publication_id'] for r in holds['records']}
    require(len(held)==len(holds['records']),'duplicate_hold_publication')
    require(bound(selected['recognition_hold_ledger'])==hold_raw,'selected_hold_ledger_changed')
    projected_holds=[{k:h[k] for k in ('source_id','publication_id','disposition','reason_code')} for h in holds['records']]
    require(sorted(q.get('recognition_holds',[]),key=lambda h:h['source_id'])==
            sorted(projected_holds,key=lambda h:h['source_id']),'queue_hold_projection_changed')
    captions = {r['publication_id'] for r in rows if r.get('caption_link')}
    recognized = [r['publication_id'] for r in s['records']]
    require(len(set(recognized)) == len(recognized) and all(r.get('status') in ('completed', 'completed_empty_recognition') for r in s['records']), 'invalid_asr_rows')
    require(not (held & captions or held & set(recognized) or captions & set(recognized)), 'source_partition_overlaps')
    require(set(ids) == held | captions | set(recognized), 'source_partition_incomplete')
    expected_selected = [r for r in rows if r['publication_id'] not in held]
    require(selected['records'] == expected_selected and selected['completed_count'] == len(expected_selected), 'selected_source_rows_changed')
    require(q.get('source_count') == len(rows) and q.get('asr_candidate_count') == len(recognized) and
            q.get('exact_caption_linked_count') == len(captions) and q.get('recognition_hold_count') == len(held), 'terminal_counts_mismatch')
    require(s.get('candidate_count') == len(recognized), 'asr_candidate_count_mismatch')
    if version==3:
        require(not additional_fallbacks and len(held)==1,'fallback_scope_mismatch')
    else:
        require(len(additional_fallbacks)==1 and additional_fallbacks[0][2]==FALLBACK_PUBLICATIONS[1] and
                set(FALLBACK_PUBLICATIONS)<=held,'v4_finite_fallback_scope_changed')
    sources = {'acquisition.json':initial[str(acquisition)], 'source-frame.json':frame_raw, 'queue.json':initial[str(queue)], 'standard-asr.json':asr_raw,
               'selected-acquisition.json':selected_raw, 'holds.json':hold_raw, 'hold-review.json':review_raw,**policy_sources}
    admitted=[];alternate_editions=[];fallback_checks=[]
    for i,(manifest_path,review_path,publication) in enumerate([(fallback,review,FALLBACK_PUBLICATIONS[0] if version==4 else None),*additional_fallbacks],1):
        result=reviewed_fallback(manifest_path,review_path,held,publication)
        if result is None:return None
        fraw,rraw,accepted=result;admitted.extend(accepted)
        filename='fallback.json' if i==1 else f'fallback-{i}.json'
        review_filename='fallback-review.json' if i==1 else f'fallback-{i}-review.json'
        sources[filename]=fraw;sources[review_filename]=rraw
        alternate_editions.append({'snapshot_file':filename,'sha256':digest(fraw),'bytes':len(fraw),
                                   'independent_review_sha256':digest(rraw),'accepted_receipts':len(accepted)})
        fallback_checks.extend([(manifest_path,fraw),(review_path,rraw)])
    require(len({r['publication_id'] for r in admitted})==len(admitted),'duplicate_fallback_publication')
    # Every mutable source must still match the bytes just validated.
    for path, raw in [(acquisition,sources['acquisition.json']), (queue,sources['queue.json']),
                      (Path(q['asr_manifest']['path']),asr_raw), (hold_review,review_raw),*fallback_checks]:
        require(safe_file(path).read_bytes() == raw, 'source_changed_during_snapshot')
    merged = {'schema_version':1,'status':'reviewed_completion_merge','records':s['records'] + admitted,
              'accepted_recognition_receipt_count':len(s['records'])+len(admitted),
              'standard_edition':{'snapshot_file':'standard-asr.json','sha256':digest(asr_raw),'bytes':len(asr_raw),
                                  'candidate_count':s['candidate_count'],'selected_input':s['input']},
              'alternate_editions':alternate_editions,
              'unadmitted_publications':sorted(held-{x['publication_id'] for x in admitted}),
              'scope':'Explicit union of completed standard receipts and the separately reviewed alternate edition. The fallback was not in the standard selected ASR input; all held failed editions remain preserved separately.'}
    sources['merged-asr.json'] = (json.dumps(merged, indent=2, ensure_ascii=False)+'\n').encode()
    return sources

def repetition_screen(asr):
    rows = []
    for item in asr['records']:
        if item['status'] != 'completed':
            continue
        n = json.loads(bound(item['outputs']['normalized']))
        texts = [t['text'].strip() for t in n['turns']]
        count = collections.Counter(texts).most_common(1)[0][1] if texts else 0
        require(not (count >= 100 and count / len(texts) > .5), 'recognition_repetition_requires_review')
        rows.append({'source_id':item['source_id'], 'segments':len(texts), 'max_identical_segment_count':count})
    return {'scope':'Exact repeated-segment diagnostic only; not recognition accuracy.', 'rows':rows}

def privacy_check(path):
    safe_file(path)
    require(path.suffix in ('.json', '.svg', '.png', '.pdf'), 'unexpected_public_file_type')
    raw = path.read_bytes()
    for marker in (b'/workspace/', b'/tmp/', b'/dev/shm/', b'access_token=', b'X-Amz-Signature=', b'-----BEGIN PRIVATE KEY', b'ghp_', b'github_pat_'):
        require(marker not in raw, 'private_data_in_public_output')
    if path.suffix == '.json':
        def walk(value):
            if isinstance(value, dict):
                require(not ({'text', 'raw_segments', 'password', 'access_token', 'refresh_token'} & value.keys()), 'private_text_key_in_public_output')
                if 'turns' in value:
                    require(type(value['turns']) is int and value['turns'] >= 0, 'private_turn_stream_in_public_output')
                for v in value.values(): walk(v)
            elif isinstance(value, list):
                for v in value: walk(v)
        walk(json.loads(raw))

def copy_plan(entries):
    plan = {}
    for source, destination in entries:
        require(destination in ALLOWLIST and destination not in plan, 'duplicate_or_unapproved_destination')
        source = Path(source); privacy_check(source)
        plan[destination] = {'source':source, 'sha256':sha(source)}
    require(set(plan) == ALLOWLIST, 'publication_allowlist_incomplete')
    require(plan['dist/channeling-network/acquisition.json']['sha256'] == plan['dist/subscription-audit/acquisition.json']['sha256'], 'acquisition_public_copies_differ')
    return plan

def closed_public_shape(value, examples, path=''):
    """Use the reviewed previous public edition as a closed structural contract.

    Lists combine all prior record shapes. Empty arrays stay empty unless the
    explicit descriptive alias disposition contract below supplies their shape.
    Numeric counts/IDs may change; unrecognized payload fields require review.
    """
    if isinstance(value,dict):
        objects=[x for x in examples if isinstance(x,dict)]
        if path=='.records[].asr_failed_editions[]':
            # Explicit reviewed v4 projection extension; not arbitrary new source fields.
            objects.append({'review_status':None,'quarantine_policy_sha256':None,'human_reviewed':None})
            if 'review_status' in value:
                require(value['review_status'] in (None,'not_recorded_in_original_ledger','pending_independent_source_review',
                        'automatic_reviewed_policy_not_manual_source_review'),'unknown_public_hold_review_status')
            if 'human_reviewed' in value:require(value['human_reviewed'] is None or value['human_reviewed'] is False,'unverified_human_review_claim')
            if value.get('quarantine_policy_sha256') is not None:
                require(isinstance(value['quarantine_policy_sha256'],str) and bool(re.fullmatch('[0-9a-f]{64}',value['quarantine_policy_sha256'])),'invalid_public_policy_digest')
        allowed=set().union(*(x.keys() for x in objects)) if objects else set()
        require(set(value) <= allowed,'unknown_public_field')
        for key,item in value.items():closed_public_shape(item,[x[key] for x in objects if key in x],path+'.'+key)
    elif isinstance(value,list):
        choices=[item for x in examples if isinstance(x,list) for item in x]
        if not choices and path == '.excluded_and_aliases':
            choices=[{'source_id':'id','selected_source_id':'id','reason':'descriptive exclusion'}]
        require(not value or bool(choices),'unreviewed_public_array_shape')
        for item in value:closed_public_shape(item,choices,path+'[]')
    else:
        require(not any(isinstance(value,t) for t in (dict,list)), 'unexpected_public_structure')
        primitive=[x for x in examples if not isinstance(x,(dict,list))]
        require(bool(primitive), 'unexpected_public_scalar')
        if isinstance(value,str):require(len(value)<=4096,'oversized_public_string')

def validate_public_shapes(plan,repo=ROOT):
    for relative,item in plan.items():
        if item['source'].suffix == '.json':
            prior=json.loads(safe_file(repo/relative).read_bytes())
            closed_public_shape(json.loads(item['source'].read_bytes()),[prior])

def canonical_audit_binding(audit, projection):
    value=json.loads(audit.read_bytes());bindings=value['source_bindings']
    canonical='research/subscription-screening/publisher-audio-acquisition.json'
    require(bindings.get(projection.name)==sha(projection) and canonical not in bindings,'audit_projection_binding_mismatch')
    bindings[canonical]=bindings.pop(projection.name)
    dump(audit,value)

def stage(expected, sources, output, repo=ROOT, python=PYTHON):
    disk_guard(repo, sum(len(v) for v in sources.values()) + 32*1024**2)
    disk_guard(output.parent, sum(len(v) for v in sources.values()) + 32*1024**2)
    output.mkdir(mode=0o700)
    require(Path(__file__).read_bytes()==EXECUTED_SOURCE,'refresh_code_changed')
    (output/'executed-refresh-pipeline.py').write_bytes(EXECUTED_SOURCE)
    frozen = output / 'inputs'; frozen.mkdir(mode=0o700)
    for name, raw in sources.items(): (frozen/name).write_bytes(raw)
    dump(output/'input-bindings.json', {k:{'sha256':digest(v),'bytes':len(v)} for k,v in sources.items()})
    dump(output/'recognition-diagnostic.json', repetition_screen(json.loads(sources['merged-asr.json'])))
    ram = Path('/dev/shm')
    use_ram = ram.is_dir() and shutil.disk_usage(ram).free >= FLOOR+512*1024**2 and memory_headroom() >= 2*1024**3
    work = ram/('channels-et-refresh-'+digest(str(output).encode())[:20]) if use_ram else output/'work'
    require(not work.exists(), 'fresh_stage_required')
    disk_guard(ram if use_ram else output, 512*1024**2)
    work.mkdir(mode=0o700)
    dump(output/'work-location-private.json', {'path':str(work),'temporary_ram_stage':use_ram})
    scripts = repo/'research/expanded-channeling'; sub = repo/'research/subscription-screening'
    run([python,scripts/'analyze_collected_audio.py','--acquisition',frozen/'acquisition.json','--asr',frozen/'merged-asr.json','--output',work/'fit'],cwd=repo)
    require(sum(p.stat().st_size for p in (work/'fit').rglob('*') if p.is_file()) <= 128*1024**2,'analysis_exceeded_artifact_budget')
    disk_guard(work,256*1024**2)
    if use_ram:require(memory_headroom() >= 1024**3,'insufficient_memory_headroom')
    run([python,scripts/'refine_collected_audio.py','--source',work/'fit','--output',work/'final'],cwd=repo)
    # Stage the existing site first, preserving historical studies and index references.
    disk_guard(work,256*1024**2)
    site = work/'site'
    dump(output/'site-location-private.json', {'path':str(site),'temporary_ram_stage':site.is_relative_to(ram)})
    run([python,repo/'scripts/pages/stage_site.py','--output',site],cwd=repo)
    projection = output/'acquisition.json'
    run([python,sub/'project_publisher_audio.py','--acquisition',frozen/'acquisition.json','--asr',frozen/'merged-asr.json','--holds',frozen/'holds.json','--snapshot-dir',output/'projection-inputs','--output',projection],cwd=repo)
    projected = json.loads(projection.read_bytes())
    require(projected['summary']['pending_local_asr'] == 0, 'projection_has_unresolved_sources')
    for name,kind in (('hold-review.json','hold_policy_independent_review'),('fallback-review.json','first_fallback_independent_review'),('fallback-2-review.json','second_fallback_independent_review')):
        if name in sources:projected['input_snapshots'].append({'kind':kind,'sha256':digest(sources[name]),'bytes':len(sources[name])})
    projected['limitations'].append('Failed-edition review_status preserves its original ledger annotation, including a formerly pending review. Separately bound independent policy/fallback decisions govern current admission; automatic policy application is not individual human review.')
    dump(projection,projected)
    audit = site/'dist/subscription-audit/data.json'
    run([python,sub/'build_audit.py','--repo',repo,'--research',sub/'first14.json','--research',sub/'second14.json','--output',audit,'--acquisition',projection],cwd=repo)
    canonical_audit_binding(audit,projection)
    # The regenerated historical video index must not change in a completion refresh.
    require(sha(audit.parent/'publisher-video-index.json') == sha(repo/'dist/subscription-audit/publisher-video-index.json'), 'historical_video_index_changed')
    manifest = json.loads((work/'final/output-manifest.json').read_bytes())
    require(manifest.get('complete') is True and {f['file'] for f in manifest['public_allowlist']} == FIGURES|{'collected-audio-analysis.json'} and len(manifest['public_allowlist']) == 7, 'analysis_outputs_unexpected')
    entries = [(projection,'dist/channeling-network/acquisition.json'),(projection,'dist/subscription-audit/acquisition.json'),
               (projection,'research/subscription-screening/publisher-audio-acquisition.json'),(audit,'dist/subscription-audit/data.json')]
    for f in manifest['public_allowlist']:
        p = work/'final'/f['file']
        require(sha(p) == f['sha256'] and p.stat().st_size == f['bytes'], 'output_manifest_mismatch')
        relative = 'dist/channeling-network/' + (f['file'] if f['file'].endswith('.json') else 'collected-audio-figures/'+f['file'])
        entries.append((p,relative))
    plan = copy_plan(entries)
    validate_public_shapes(plan,repo)
    for relative, item in plan.items():
        if not relative.startswith('dist/'):continue
        target = site/relative; target.parent.mkdir(parents=True,exist_ok=True)
        if target != item['source']: shutil.copyfile(item['source'],target)
    # Bind the private proposed release exactly, including its changed metadata.
    m = json.loads((site/'deployment-manifest.json').read_bytes())
    for f in m['files']:
        p=site/f['path'];f.update(bytes=p.stat().st_size,sha256=sha(p))
    m.update(total_bytes=sum(f['bytes'] for f in m['files']),static_inputs_dirty=True)
    dump(site/'deployment-manifest.json',m)
    run([python,repo/'scripts/pages/verify_site.py','--directory',site,'--serve-prefix','/channels-ET/'],cwd=repo)
    for relative in ('research/bashar-ra/verify_release.py','research/subscription-screening/verify_release.py'):
        run([python,repo/relative,'--site',site],cwd=repo)
    for name in ('verify_outputs.py','verify_pilot.py','verify_registry.py','verify_collected_audio.py','verify_semantic.py','verify_paper.py'):
        run([python,scripts/name,'--public-dir',site/'dist/channeling-network'],cwd=repo)
    # Preserve the executed study and all public proposal bytes durably; RAM is not archival.
    raw_fit_files=['collected-audio-analysis.json','output-manifest.json',*sorted(FIGURES)]
    required=sum(p.stat().st_size for p in (work/'final').rglob('*') if p.is_file())
    required+=sum((work/'fit'/p).stat().st_size for p in raw_fit_files)+sum(x['source'].stat().st_size for x in plan.values())
    disk_guard(output,required+8*1024**2)
    shutil.copytree(work/'final',output/'analysis-final')
    (output/'analysis-raw').mkdir(mode=0o700)
    for name in raw_fit_files:shutil.copyfile(work/'fit'/name,output/'analysis-raw'/name)
    durable=[]
    for relative in sorted(plan):
        source=site/relative if relative.startswith('dist/') else projection
        target=output/'approved-public'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        require(sha(target)==plan[relative]['sha256'],'durable_public_copy_changed')
        durable.append((target,relative))
    finalplan = copy_plan(durable)
    dump(output/'approved-publication.json',{'expected_head':expected,'files':[{'path':p,'sha256':x['sha256']} for p,x in finalplan.items()]})
    return finalplan

def changed_paths(repo):
    changed = set(git(['diff','--name-only','HEAD'],repo).splitlines())
    changed.update(git(['ls-files','--others','--exclude-standard'],repo).splitlines())
    return changed - {''}

def publish(plan, expected, no_push=False, repo=ROOT):
    git_guard(expected,repo)
    baseline = {p:sha(safe_file(repo/p)) for p in plan}
    changed = {p for p in plan if plan[p]['sha256'] != baseline[p]}
    require(changed, 'no_changed_outputs')
    disk_guard(repo, sum(plan[p]['source'].stat().st_size for p in changed))
    for p in sorted(changed):
        require(git(['rev-parse','HEAD'],repo) == expected, 'head_changed_during_copy')
        require(changed_paths(repo) <= changed and sha(repo/p) == baseline[p], 'worktree_changed_during_copy')
        item=plan[p];require(sha(safe_file(item['source'])) == item['sha256'], 'staged_source_changed')
        target=repo/p;safe_file(target)
        # No silent restoration/reset on a race: leave our explicitly listed changes for review.
        with target.open('r+b') as f:
            require(digest(f.read()) == baseline[p], 'target_changed_before_write')
            f.seek(0);f.write(item['source'].read_bytes());f.truncate();f.flush();os.fsync(f.fileno())
    require(git(['rev-parse','HEAD'],repo) == expected and changed_paths(repo) == changed, 'unexpected_public_changes')
    require(not git(['diff','--cached','--name-only'],repo), 'index_changed_during_staging')
    require(all(sha(repo/p) == plan[p]['sha256'] for p in plan), 'public_output_changed')
    require(remote_head(repo) == expected, 'remote_main_changed_before_commit')
    git(['add','--',*sorted(changed)],repo)
    require(set(git(['diff','--cached','--name-only'],repo).splitlines()) == changed, 'unexpected_staged_paths')
    for p in changed:
        require(digest(run(['git','show',':'+p],cwd=repo)) == plan[p]['sha256'], 'staged_blob_changed')
    require(git(['rev-parse','HEAD'],repo) == expected and not git(['diff','--name-only'],repo), 'race_before_commit')
    git(['-c','core.hooksPath=/dev/null','commit','-m',COMMIT_MESSAGE,'-m',COMMIT_BODY],repo)
    commit=git(['rev-parse','HEAD'],repo)
    require(git(['rev-parse','HEAD^'],repo) == expected, 'commit_parent_changed')
    require(set(git(['diff-tree','--no-commit-id','--name-only','-r',commit],repo).splitlines()) == changed, 'commit_paths_changed')
    for p in plan:
        require(digest(run(['git','show',commit+':'+p],cwd=repo)) == plan[p]['sha256'], 'committed_blob_changed')
    git_guard(commit,repo,remote=False)
    if not no_push:
        require(remote_head(repo) == expected, 'remote_main_changed_before_push')
        git(['push','https://github.com/occult-kranti/channels-ET.git',commit+':refs/heads/main'],repo)
        require(remote_head(repo) == commit, 'remote_push_unconfirmed')
    return {'commit':commit,'pushed':not no_push,'paths':sorted(changed)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--expected-head',required=True)
    p.add_argument('--output',type=Path,required=True,help='Fresh directory under channels-et-private; never a repository path')
    p.add_argument('--dry-run',action='store_true');p.add_argument('--no-push',action='store_true')
    p.add_argument('--once',action='store_true',help='Check once; a running queue exits without publishing')
    p.add_argument('--max-wait-hours',type=float,default=48)
    args=p.parse_args(argv);os.umask(0o077)
    require('..' not in args.output.parts, 'parent_traversal_rejected')
    output=args.output.absolute()
    require(output.is_relative_to(PRIVATE) and not output.exists() and not any(x.is_symlink() for x in output.parents), 'fresh_private_output_required')
    require(0 < args.max_wait_hours <= 168, 'bounded_wait_required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with (PRIVATE/'.publisher-completion-refresh.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ReviewRequired('another_refresh_is_running') from None
        git_guard(args.expected_head);disk_guard(ROOT);deadline=time.monotonic()+args.max_wait_hours*3600
        while True:
            git_guard(args.expected_head,remote=False)
            sources=read_state(BASE/'publisher-audio-v3/manifest.json',BASE/'publisher-asr-v2/queue-status.json',
                               BASE/'publisher-asr-fallback-v1/manifest.json',BASE/'publisher-asr-fallback-v1/independent-review.json',
                               PRIVATE/'expanded-channeling-2026-11/review/asr-queue-v3-hold-independent.json',
                               additional_fallbacks=((BASE/'publisher-asr-fallback-v2/manifest.json',BASE/'publisher-asr-fallback-v2/independent-review.json',FALLBACK_PUBLICATIONS[1]),),
                               policy_review=PRIVATE/'expanded-channeling-2026-11/review/asr-queue-v4-policy-independent.json')
            if sources is not None:break
            if args.once:raise ReviewRequired('finite_pipeline_still_running_or_review_pending')
            require(time.monotonic()<deadline,'watch_deadline_reached_requires_review')
            print(json.dumps({'status':'waiting_for_finite_completion_and_review','at':dt.datetime.now(dt.timezone.utc).isoformat()}),flush=True)
            time.sleep(30)
        git_guard(args.expected_head)
        plan=stage(args.expected_head,sources,output)
        git_guard(args.expected_head)
        result={'status':'private_stage_verified','dry_run':args.dry_run,'expected_head':args.expected_head}
        if not args.dry_run:result.update(publish(plan,args.expected_head,args.no_push))
        if not args.dry_run:
            try:
                disk_guard(output,16*1024**2)
                run([PYTHON,ROOT/'research/subscription-screening/private_portal.py','--root',output/'private-archive',
                     '--acquisition',output/'inputs/acquisition.json','--asr',output/'inputs/merged-asr.json','--text-bundle'])
                result.update(private_archive='private-archive/index.html',private_archive_status='created')
            except ReviewRequired as error:
                result.update(private_archive_status='requires_review',private_archive_error=str(error))
        dump(output/'completion.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    try:main()
    except ReviewRequired as e:
        print(json.dumps({'status':'stopped_requires_review','code':str(e)}),flush=True)
        raise SystemExit(2)
    except Exception as e:
        # Raw exceptions may contain source URLs, transcripts or credentials.
        print(json.dumps({'status':'stopped_requires_review','code':'unexpected_'+type(e).__name__}),flush=True)
        raise SystemExit(2)
