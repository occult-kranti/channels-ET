#!/usr/bin/env python3
"""Time a verified completed-edition resume from process start through exit."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from asr_batch_prepare import artifact, digest, read_bound


def check_resume(manifest_path, runner, run_id, output):
    if output.exists():
        raise ValueError('Resume invocation receipts are immutable')
    full = json.loads(manifest_path.read_text())
    if full['status'] != 'completed_full_batch':
        raise ValueError('A completed full batch is required')
    inference = json.loads(read_bound(full['stage_receipt']).read_text())
    if digest(runner) != inference['script_sha256']:
        raise ValueError('Resume must use the exact completed controller code')
    if digest(runner.parent/'asr_batch_worker.py') != inference['worker_sha256']:
        raise ValueError('Resume worker fingerprint differs')
    for ref in full['editions']:
        receipt = json.loads(read_bound(ref).read_text())
        if receipt['status'] != 'completed_full_chunked_asr':
            raise ValueError('An edition is incomplete; this is not a no-inference check')
    frame = read_bound(full['frame'])
    command = [sys.executable, str(runner), '--frame', str(frame), '--run-id', run_id]
    start = time.time(); monotonic = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        # Preconditions guarantee all editions existed with the same code/protocol;
        # this check must not be used as an inference launcher.
        process.terminate(); process.communicate(timeout=5)
        raise
    elapsed = time.monotonic()-monotonic; ended = time.time()
    if process.returncode:
        raise ValueError('Resume check failed: '+stderr.decode(errors='replace')[-500:])
    private_root = manifest_path.parents[2]
    receipt_path = private_root/'runs'/run_id/'inference-receipt.json'
    resume = json.loads(receipt_path.read_text())
    if (resume['status'] != 'completed' or resume['workers'] or resume['submitted_chunks']
            or resume['completed_new_chunks'] or resume['verified_complete_cache_hits'] != len(full['editions'])):
        raise ValueError('Invocation did not prove a no-inference completed-edition cache hit')
    for ref in full['editions']:
        read_bound(ref)
    data = {'status': 'verified_no_inference_resume', 'command': command, 'pid': process.pid,
            'started_at_unix': start, 'finished_at_unix': ended,
            'whole_process_wall_seconds': elapsed, 'returncode': process.returncode,
            'scope': 'Subprocess start through exit, including module imports, source hashing and complete output validation; no model workers launched.',
            'verified_complete_editions': len(full['editions']), 'new_inference_chunks': 0,
            'unchanged_completed_receipt_hashes': [x['sha256'] for x in full['editions']],
            'resume_inference_receipt': artifact(receipt_path), 'full_manifest': artifact(manifest_path),
            'runner_sha256': digest(runner), 'timer_script_sha256': digest(__file__),
            'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k: data[k] for k in ('status', 'whole_process_wall_seconds', 'verified_complete_editions', 'new_inference_chunks')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--runner', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    check_resume(args.manifest, args.runner, args.run_id, args.output)
