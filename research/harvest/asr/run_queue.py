#!/usr/bin/env python3
"""Bounded publisher-audio ASR dispatcher; no transcript text is printed.

Resume is between audio files. An interrupted file is restarted by transcribe.py;
completed files are reused only after complete source/protocol/artifact checks.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.parse

HERE = Path(__file__).resolve().parent
RAW = Path('/workspace/channels-et-raw')
TRANSCRIBER = HERE / 'transcribe.py'
OUTPUTS = {'segments.jsonl', 'transcript.txt', 'transcript.srt'}
DECODING = {'language': 'en', 'beam_size': 1, 'vad_filter': True, 'condition_on_previous_text': False}
PUBLISHER_TERMINAL = {'completed', 'failed', 'blocked', 'quota_stopped', 'validation_mismatch'}
JOB_TERMINAL = {'completed', 'reused_existing', 'asr_failed', 'prior_asr_failed', 'acquisition_failed', 'invalid_source'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, data):
    if path.is_symlink():
        raise ValueError('Refusing symlink output')
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    if temporary.is_symlink():
        raise ValueError('Refusing symlink temporary output')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def load(path):
    return json.loads(path.read_text())


def plan_rows(path, expected):
    data = path.read_bytes()
    rows = json.loads(data)['records']
    if len(rows) != expected:
        raise ValueError('expanded_plan_not_ready')
    ids = [r['source_id'] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate_plan_source_id')
    for row in rows:
        if not re.fullmatch(r'[a-z0-9-]+', row['source_id']):
            raise ValueError('unsafe_source_id')
        url = urllib.parse.urlsplit(row['enclosure_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('invalid_public_https_source_url')
    return {r['source_id']: r for r in rows}, hashlib.sha256(data).hexdigest()


def context(python):
    manifest_path = HERE / 'model-manifest.json'
    model = load(manifest_path)
    command = [str(python), '-c', 'import importlib.metadata,json;print(json.dumps({p:importlib.metadata.version(p) for p in ["faster-whisper","ctranslate2","av"]}))']
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
    return {'model': model, 'model_manifest_sha256': sha(manifest_path), 'versions': json.loads(result.stdout)}


def validate_audio(row, planned):
    if row.get('status') != 'completed' or row.get('source_id') != planned['source_id'] or row.get('enclosure_url') != planned['enclosure_url']:
        raise ValueError('completed_source_id_or_url_mismatch')
    if not re.fullmatch(r'[a-f0-9]{64}', str(row.get('sha256', ''))):
        raise ValueError('invalid_audio_sha256')
    original = Path(row['raw_local_path'])
    audio = original.resolve()
    if RAW.resolve() != RAW or original.is_symlink() or not audio.is_relative_to(RAW) or not audio.is_file():
        raise ValueError('invalid_external_audio_path')
    if not isinstance(row.get('bytes'), int) or row['bytes'] <= 0 or audio.stat().st_size != row['bytes'] or sha(audio) != row['sha256']:
        raise ValueError('audio_hash_or_size_mismatch')
    return audio


def receipt_valid(row, planned, ctx, required_script_sha=None):
    """Accept old executed code if its retained bytes and complete signature match."""
    try:
        audio = validate_audio(row, planned)
        audio_hash = row['sha256']
        folder = RAW / 'transcripts' / audio_hash[:20]
        if folder.resolve() != folder or not folder.is_dir():
            return False, 'no_safe_full_transcript_directory', None
        private_path = folder / 'receipt.json'
        if private_path.is_symlink() or not private_path.is_file():
            return False, 'no_private_completed_receipt', None
        prior = load(private_path)
        if (prior.get('status') != 'completed' or prior.get('transcribedScope') != 'full_decoded_audio'
                or prior.get('clipSeconds') is not None or prior.get('sourceId') != planned['source_id']
                or prior.get('sourceUrl') != planned['enclosure_url'] or prior.get('sourceAudioSha256') != audio_hash
                or Path(prior['sourceAudioPath']).resolve() != audio
                or prior.get('modelId') != ctx['model']['modelId'] or prior.get('modelRevision') != ctx['model']['revision']
                or prior.get('versions') != ctx['versions'] or prior.get('cpuThreads') != 2
                or prior.get('device') != 'cpu' or prior.get('computeType') != 'int8' or prior.get('decoding') != DECODING):
            return False, 'receipt_source_scope_or_protocol_mismatch', None
        acquisition = {'sourceId': planned['source_id'], 'audioSha256': audio_hash, 'enclosureUrl': planned['enclosure_url']}
        if prior.get('publisherAcquisitionRecord') != acquisition:
            return False, 'receipt_acquisition_binding_mismatch', None
        protocol = prior.get('executionProtocol', {})
        executed_sha = protocol.get('scriptSha256', '')
        if not re.fullmatch(r'[a-f0-9]{64}', executed_sha):
            return False, 'missing_executed_source_hash', None
        executed_source = HERE / 'executed-sources' / (executed_sha + '.py')
        if executed_source.is_symlink() or not executed_source.is_file() or sha(executed_source) != executed_sha:
            return False, 'retained_executed_source_missing_or_changed', None
        if required_script_sha is not None and executed_sha != required_script_sha:
            return False, 'executed_entrypoint_changed_during_dispatch', None
        expected = {'sourceId': planned['source_id'], 'sourceUrl': planned['enclosure_url'], 'audioSha256': audio_hash,
                    'modelManifestSha256': ctx['model_manifest_sha256'], 'versions': ctx['versions'],
                    'cpuThreads': 2, 'decoding': DECODING, 'scriptSha256': executed_sha}
        signature = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
        if protocol != expected or prior.get('executionSignature') != signature:
            return False, 'execution_signature_mismatch', None
        artifacts = prior.get('outputs', [])
        if len(artifacts) != 3 or {r.get('name') for r in artifacts} != OUTPUTS:
            return False, 'exact_three_artifacts_required', None
        for item in artifacts:
            artifact = folder / item['name']
            if artifact.is_symlink() or not artifact.is_file() or not isinstance(item.get('bytes'), int) or item['bytes'] <= 0 or artifact.stat().st_size != item['bytes'] or sha(artifact) != item['sha256']:
                return False, 'transcript_artifact_hash_or_size_mismatch', None
        duration = prior['sourceAudioDurationSeconds']
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0 or prior.get('segments', 0) <= 0 or prior.get('words', 0) <= 0:
            return False, 'empty_or_invalid_transcription_receipt', None
        if not 0 < prior['lastSegmentEndSeconds'] <= duration + 2:
            return False, 'invalid_final_segment_time', None
        public_path = HERE / (audio_hash[:20] + '-receipt.json')
        public = {**prior, 'transcriptDirectory': str(folder)}
        if public_path.exists() and (public_path.is_symlink() or load(public_path) != public):
            return False, 'public_private_receipt_mismatch', None
        return True, 'all_source_protocol_artifact_and_executed_code_checks_pass', {'receipt': prior, 'public_path': public_path, 'public': public, 'audio': audio}
    except (KeyError, ValueError, TypeError, AttributeError, OSError, json.JSONDecodeError):
        return False, 'receipt_validation_exception', None


def retain_entrypoint():
    content = TRANSCRIBER.read_bytes()
    value = hashlib.sha256(content).hexdigest()
    target = HERE / 'executed-sources' / (value + '.py')
    target.parent.mkdir(exist_ok=True)
    if target.is_symlink():
        raise ValueError('unsafe_executed_source_path')
    if target.exists():
        if target.read_bytes() != content:
            raise ValueError('executed_source_archive_collision')
    else:
        # Exclusive creation prevents overwriting retained execution evidence.
        with target.open('xb') as stream:
            stream.write(content)
    if sha(TRANSCRIBER) != value:
        raise ValueError('entrypoint_changed_before_launch')
    return value


def refresh_summary(python, log):
    with log.open('ab') as stream:
        result = subprocess.run([str(python), str(HERE / 'build_summary.py')], stdout=stream, stderr=stream, timeout=60)
    return {'status': 'completed' if result.returncode == 0 else 'failed', 'returncode': result.returncode, 'checked_at': now()}


def pending_promotions(planned):
    """A reviewed pending promotion keeps that source open, not ASR-eligible."""
    pending = set()
    for path in sorted((HERE.parent / 'publisher_sources').glob('*amendment*.json')):
        document = load(path)
        amendments = document.get('records', [document])
        for amendment in amendments:
            if (str(amendment.get('status', '')).startswith('approved_pending')
                    and amendment.get('source_id') in planned):
                pending.add(amendment['source_id'])
    return pending


def run(args):
    began = time.monotonic(); deadline = began + args.watch_seconds
    ctx = context(args.python)
    if args.check_only:
        planned, plan_sha = plan_rows(args.plan, args.expected_jobs)
        summary = load(args.publisher_summary)
        if summary.get('planned_jobs') != args.expected_jobs or summary.get('plan_sha256') != plan_sha:
            raise ValueError('publisher_summary_not_bound_to_expanded_plan')
        completed = [r for r in summary.get('records', []) if r.get('status') == 'completed' and r.get('source_id') in planned]
        diagnostics = []
        for row in completed:
            valid, reason, detail = receipt_valid(row, planned[row['source_id']], ctx)
            diagnostics.append({'source_id': row['source_id'], 'existing_verified_result': valid, 'reason': reason,
                                'executed_source_sha256': detail['receipt']['executionProtocol']['scriptSha256'] if detail else None})
        print(json.dumps({'status': 'check_only_no_launch', 'planned_jobs': len(planned), 'completed_audio_records': len(completed), 'verified_reusable_receipts': sum(x['existing_verified_result'] for x in diagnostics), 'records': diagnostics}))
        return 0

    RAW.mkdir(parents=True, exist_ok=True)
    lock = (RAW / '.asr-dispatcher.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    logs = RAW / 'asr-queue-logs' / run_id
    logs.mkdir(parents=True, exist_ok=False)
    prior = load(args.state) if args.state.is_file() else {}
    prior_records = {r['source_id']: r for r in prior.get('records', [])}
    jobs = {}; active = {}; planned = None; plan_sha = None; publisher_terminal = False; stopped = []; awaiting_promotions = set()
    events = []; summary_refresh = None; last_wait_reason = 'waiting_for_expanded_plan'
    def request_stop(signum, frame):
        stopped.append('signal_' + str(signum))
    signal.signal(signal.SIGTERM, request_stop); signal.signal(signal.SIGINT, request_stop)
    def event(kind, **fields):
        row = {'at': now(), 'event': kind, **fields}; events.append(row)
        with (HERE / 'queue-attempts.jsonl').open('a') as stream:
            stream.write(json.dumps({'run_id': run_id, **row}) + '\n')
    def snapshot(status):
        values = list(jobs.values())
        state = {'schema_version': 1, 'run_id': run_id, 'updated_at': now(), 'status': status,
                 'planned_jobs': args.expected_jobs, 'plan_sha256': plan_sha, 'publisher_terminal': publisher_terminal,
                 'concurrency_limit': args.concurrency, 'cpu_threads_per_process': 2, 'watch_seconds_limit': args.watch_seconds,
                 'elapsed_seconds': round(time.monotonic() - began, 3), 'attempted_this_run': sum(r.get('attempted_this_run', False) for r in values),
                 'completed_new_this_run': sum(r['status'] == 'completed' for r in values), 'reused_existing': sum(r['status'] == 'reused_existing' for r in values),
                 'verified_completed_total': sum(r['status'] in {'completed', 'reused_existing'} for r in values),
                 'asr_failed': sum(r['status'] in {'asr_failed', 'prior_asr_failed'} for r in values),
                 'acquisition_failed': sum(r['status'] == 'acquisition_failed' for r in values),
                 'invalid_sources': sum(r['status'] == 'invalid_source' for r in values),
                 'awaiting_approved_promotions': sorted(awaiting_promotions), 'in_flight': sorted(active),
                 'records': sorted(values, key=lambda r: r['source_id']), 'last_wait_reason': last_wait_reason,
                 'summary_refresh': summary_refresh, 'raw_transcript_text_printed_or_published': False,
                 'resume_scope': 'Between completed audio files; an interrupted audio file restarts ASR rather than resuming decoded segments.'}
        save(args.state, state)
        return state
    try:
        while time.monotonic() < deadline and not stopped:
            # Plan is bound once. A changed cohort is a new run, not silent growth.
            if planned is None:
                try:
                    candidate, candidate_sha = plan_rows(args.plan, args.expected_jobs)
                    publisher = load(args.publisher_summary)
                    if publisher.get('planned_jobs') != args.expected_jobs or publisher.get('plan_sha256') != candidate_sha:
                        raise ValueError('waiting_for_expanded_summary')
                    planned, plan_sha = candidate, candidate_sha
                    jobs = {ident: {'source_id': ident, 'status': 'waiting_audio', 'attempted_this_run': False} for ident in planned}
                    event('expanded_plan_bound', plan_sha256=plan_sha, planned_jobs=len(planned))
                except (OSError, ValueError, KeyError, TypeError):
                    last_wait_reason = 'waiting_for_matching_expanded_plan_and_summary'; snapshot('waiting_for_plan')
                    time.sleep(min(args.poll_seconds, max(0, deadline - time.monotonic()))); continue
            if sha(args.plan) != plan_sha:
                stopped.append('plan_changed_during_run'); break
            publisher = load(args.publisher_summary)
            if publisher.get('plan_sha256') != plan_sha or publisher.get('planned_jobs') != args.expected_jobs:
                stopped.append('publisher_cohort_changed_during_run'); break
            publisher_terminal = publisher.get('terminal') is True
            records = {r['source_id']: r for r in publisher.get('records', []) if r.get('source_id') in planned}
            awaiting_promotions = {ident for ident in pending_promotions(planned) if records.get(ident, {}).get('status') != 'completed'}
            if len(records) != len([r for r in publisher.get('records', []) if r.get('source_id') in planned]):
                stopped.append('duplicate_publisher_summary_source_id'); break
            # Reap actual processes before dispatching any newly available source.
            for ident, running in list(active.items()):
                code = running['process'].poll()
                if code is None:
                    continue
                running['log'].close(); del active[ident]
                valid, reason, detail = receipt_valid(running['source'], planned[ident], ctx, running['script_sha256'])
                jobs[ident].update(status='completed' if code == 0 and valid else 'asr_failed', finished_at=now(), returncode=code, validation=reason)
                event('asr_finished', source_id=ident, status=jobs[ident]['status'], returncode=code, receipt_valid=valid)
                summary_refresh = refresh_summary(args.python, logs / 'summary-builder.log')
            for ident in sorted(planned):
                row = records.get(ident)
                if jobs[ident]['status'] == 'acquisition_failed' and row and row.get('status') == 'completed':
                    jobs[ident].update(status='waiting_audio', recovered_acquisition_at=now())
                    event('acquisition_recovered_to_completed', source_id=ident)
                if ident in awaiting_promotions and ident not in active and jobs[ident]['status'] not in {'completed', 'reused_existing'}:
                    jobs[ident].update(status='awaiting_approved_promotion', reason='reviewed_source_is_not_ASR_eligible_until_publisher_record_is_completed')
                    continue
                if jobs[ident]['status'] in JOB_TERMINAL or ident in active:
                    continue
                if jobs[ident]['status'] == 'ready' and len(active) >= args.concurrency:
                    continue
                if not row or row.get('status') not in PUBLISHER_TERMINAL:
                    if publisher_terminal:
                        jobs[ident].update(status='acquisition_failed', reason='missing_terminal_completed_acquisition')
                    continue
                if row.get('status') != 'completed':
                    jobs[ident].update(status='acquisition_failed', acquisition_status=row.get('status'))
                    continue
                try:
                    audio = validate_audio(row, planned[ident])
                except (OSError, ValueError, KeyError, TypeError):
                    jobs[ident].update(status='invalid_source', reason='acquisition_audio_identity_hash_size_or_path_validation_failed')
                    event('source_rejected', source_id=ident); continue
                valid, reason, detail = receipt_valid(row, planned[ident], ctx)
                jobs[ident].update(audio_sha256=row['sha256'], existing_receipt_validation=reason)
                if valid:
                    # Restore a missing public metadata mirror after a prior interrupted finalization.
                    if not detail['public_path'].exists():
                        save(detail['public_path'], detail['public'])
                    jobs[ident].update(status='reused_existing', verified_at=now(), executed_source_sha256=detail['receipt']['executionProtocol']['scriptSha256'])
                    event('verified_result_reused', source_id=ident, audio_sha256=row['sha256']); continue
                if sum(r.get('status') == 'completed' and r.get('sha256') == row['sha256'] for r in records.values()) > 1:
                    jobs[ident].update(status='invalid_source', reason='duplicate_audio_hash_requires_source_identity_review'); continue
                private_receipt = RAW / 'transcripts' / row['sha256'][:20] / 'receipt.json'
                if private_receipt.is_file() and load(private_receipt).get('sourceId') != ident:
                    jobs[ident].update(status='invalid_source', reason='existing_audio_receipt_bound_to_another_source_id'); continue
                previous = prior_records.get(ident, {})
                if previous.get('status') in {'asr_failed', 'prior_asr_failed'} and previous.get('audio_sha256') == row['sha256'] and not args.retry_failed:
                    jobs[ident].update(status='prior_asr_failed', reason='use_retry_failed_for_an_explicit_new_attempt'); continue
                if len(active) >= args.concurrency:
                    jobs[ident]['status'] = 'ready'; continue
                script_sha = retain_entrypoint()
                logfile = logs / (ident + '.log')
                handle = logfile.open('ab')
                command = [str(args.python), str(TRANSCRIBER), '--audio', str(audio), '--source-id', ident,
                           '--source-url', planned[ident]['enclosure_url'], '--source-sha256', row['sha256'], '--cpu-threads', '2']
                process = subprocess.Popen(command, stdout=handle, stderr=handle)
                active[ident] = {'process': process, 'log': handle, 'source': row, 'script_sha256': script_sha}
                jobs[ident].update(status='running', attempted_this_run=True, started_at=now(), pid=process.pid,
                                   executed_source_sha256=script_sha, private_log_path=str(logfile))
                event('asr_started', source_id=ident, audio_sha256=row['sha256'], executed_source_sha256=script_sha)
            last_wait_reason = 'waiting_for_running_asr_or_publisher_audio'
            snapshot('running')
            if publisher_terminal and not active and all(r['status'] in JOB_TERMINAL for r in jobs.values()):
                summary_refresh = refresh_summary(args.python, logs / 'summary-builder.log')
                state = snapshot('completed' if all(r['status'] in {'completed', 'reused_existing'} for r in jobs.values()) else 'completed_with_failures')
                print(json.dumps({k: state[k] for k in ['status', 'planned_jobs', 'attempted_this_run', 'completed_new_this_run', 'reused_existing', 'verified_completed_total', 'asr_failed', 'acquisition_failed']}))
                return int(state['status'] != 'completed')
            time.sleep(min(args.poll_seconds, max(0, deadline - time.monotonic())))
    except Exception as error:
        stopped.append('dispatcher_error_' + type(error).__name__)
        event('dispatcher_failed', error_type=type(error).__name__)
    finally:
        for ident, running in list(active.items()):
            running['process'].terminate()
        for ident, running in list(active.items()):
            try:
                running['process'].wait(timeout=3)
            except subprocess.TimeoutExpired:
                running['process'].kill(); running['process'].wait(timeout=3)
            running['log'].close()
            jobs[ident].update(status='interrupted', finished_at=now(), reason=stopped[0] if stopped else 'bounded_watch_deadline')
            event('asr_interrupted', source_id=ident, reason=jobs[ident]['reason'])
        active.clear()
        fcntl.flock(lock, fcntl.LOCK_UN); lock.close()
    summary_refresh = refresh_summary(args.python, logs / 'summary-builder.log')
    last_wait_reason = stopped[0] if stopped else 'bounded_watch_deadline'
    state = snapshot('dispatcher_failed' if any(x.startswith('dispatcher_error_') for x in stopped) else 'interrupted' if stopped else 'deadline_reached')
    print(json.dumps({k: state[k] for k in ['status', 'planned_jobs', 'attempted_this_run', 'completed_new_this_run', 'reused_existing', 'verified_completed_total', 'asr_failed', 'acquisition_failed']}))
    return 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=HERE.parent / 'publisher_sources/expanded-plan.json')
    parser.add_argument('--publisher-summary', type=Path, default=HERE.parent / 'publisher_sources/publisher-summary.json')
    parser.add_argument('--python', type=Path, default=Path('/workspace/channels-et-asr-venv/bin/python'))
    parser.add_argument('--state', type=Path, default=HERE / 'queue-state.json')
    parser.add_argument('--expected-jobs', type=int, default=19)
    parser.add_argument('--concurrency', type=int, choices=[1, 2], default=2)
    parser.add_argument('--watch-seconds', type=float, default=1200)
    parser.add_argument('--poll-seconds', type=float, default=3)
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--check-only', action='store_true', help='Validate current sources/receipts; launch nothing and write no queue state')
    arguments = parser.parse_args()
    if not 1 <= arguments.expected_jobs <= 100 or not math.isfinite(arguments.watch_seconds) or not 0 < arguments.watch_seconds <= 1200 or not math.isfinite(arguments.poll_seconds) or not 0 < arguments.poll_seconds <= 10:
        parser.error('Require1..100jobs, positive watch<=1200seconds and poll<=10seconds')
    raise SystemExit(run(arguments))
