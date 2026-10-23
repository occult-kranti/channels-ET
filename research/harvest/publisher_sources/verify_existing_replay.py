#!/usr/bin/env python3
"""Read-only replay of held source artifacts; block every network/export write."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import unittest.mock as mock

H = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('publisher_replay', H / 'download.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
summary_path = H / 'publisher-summary.json'
summary_before = summary_path.read_bytes()
journal_path = H / 'publisher-attempts.jsonl'
journal_before = journal_path.read_bytes()
plan_path = H / 'expanded-plan.json'
plan = json.loads(plan_path.read_text())
prior = {r['source_id']: r for r in json.loads(summary_before)['records']}
d.PRIOR.update(prior)
d.PLANNED_IDS.update(prior)
checks = []
original_open = pathlib.Path.open


def safe_open(path, mode='r', *args, **kwargs):
    if path == journal_path and mode == 'a':
        return io.StringIO()
    if any(character in mode for character in 'wax+'):
        raise AssertionError('Unexpected export/raw mutation during read-only replay')
    return original_open(path, mode, *args, **kwargs)


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


outputs = []
preserve = ['validation_outcome', 'warning', 'strict_validation_status', 'strict_validation_error',
            'rss_size_matches_actual', 'rss_size_delta_bytes', 'rss_duration_within_tolerance',
            'duration_delta_from_rss_seconds', 'review_amendment', 'started_at', 'finished_at',
            'elapsed_seconds', 'collector_sha256', 'source_format']
with mock.patch.object(d, 'snapshot', return_value=None), \
     mock.patch.object(d.urllib.request, 'build_opener', side_effect=AssertionError('Network forbidden in replay')), \
     mock.patch.object(pathlib.Path, 'open', safe_open), contextlib.redirect_stdout(io.StringIO()):
    for row in plan['records']:
        result = d.download(row, hashlib.sha256(plan_path.read_bytes()).hexdigest())
        old = prior[row['source_id']]
        ck(result['status'] == 'completed' and result.get('reused_existing_file'), 'local artifact reused ' + row['source_id'])
        ck(all(result.get(key) == old.get(key) for key in preserve), 'prior acquisition/validation lineage preserved ' + row['source_id'])
        ck(result.get('sha256') == old['sha256'] and result.get('bytes') == old['bytes'], 'unchanged audio identity ' + row['source_id'])
        outputs.append(result)
ck(sum(bool(r.get('validation_outcome')) for r in outputs) == 4, 'all four reviewed warnings survive nineteen-source replay')
ck(summary_path.read_bytes() == summary_before, 'held publisher summary byte-identical after replay')
ck(journal_path.read_bytes() == journal_before, 'held publisher journal byte-identical after replay')
failed = [c for c in checks if not c['passed']]
report = {'status': 'FAIL' if failed else 'PASS', 'checks': len(checks), 'failures': failed,
          'collector_sha256': hashlib.sha256((H / 'download.py').read_bytes()).hexdigest(),
          'held_summary_sha256': hashlib.sha256(summary_before).hexdigest(),
          'held_plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
          'source_artifacts_checked_read_only': len(outputs), 'warning_records_preserved': sum(bool(r.get('validation_outcome')) for r in outputs),
          'network_requests': 0, 'media_or_held_export_writes': 0, 'all_checks': checks}
(H / 'existing-replay-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks', 'failures', 'source_artifacts_checked_read_only', 'warning_records_preserved', 'network_requests', 'media_or_held_export_writes']}, indent=2))
raise SystemExit(bool(failed))
