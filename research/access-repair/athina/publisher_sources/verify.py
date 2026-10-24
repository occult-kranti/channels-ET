#!/usr/bin/env python3
"""Read-only independent verification of the isolated publisher artifact."""
import hashlib
import json
import math
import pathlib
import subprocess

H = pathlib.Path(__file__).resolve().parent
R = H.parents[3]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


checks = []


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


config = json.loads((H / 'execution-config.json').read_text())
receipt = json.loads((H / 'execution-receipt.json').read_text())
summary = json.loads((H / 'publisher-summary.json').read_text())
plan = json.loads((H / 'plan.json').read_text())
for key in ['module', 'wrapper', 'plan']:
    ck(sha(R / config[key + '_path']) == config[key + '_sha256'] == receipt[key + '_sha256'], key + ' exact executed source/configuration pin')
ck(sha(H / 'execution-config.json') == receipt['configuration_sha256'], 'explicit adapted configuration receipt binding')
for name in ['publisher-summary.json', 'publisher-attempts.jsonl']:
    ck(sha(H / name) == receipt[name + '_sha256'], name + ' execution receipt binding')
ck(summary['terminal'] and summary['run_status'] == 'completed' and summary['planned_jobs'] == summary['completed_audio_files'] == 1,
   'one terminal completed publisher source')
row = summary['records'][0]
journal = [json.loads(line) for line in (H / 'publisher-attempts.jsonl').read_text().splitlines()]
ck(len(journal) == 1 and journal[0] == row, 'one actual attempt and no hidden retry')
raw = pathlib.Path(row['raw_local_path'])
ck(not raw.is_relative_to(R) and raw.parent == pathlib.Path(config['adapted_constants']['RAW']), 'raw audio outside Git in isolated primary-audio directory')
ck(sha(raw) == row['sha256'] and raw.stat().st_size == row['bytes'], 'actual local audio hash and size')
ck(raw.stat().st_size == row['response_declared_remaining_bytes'] == row['rss_enclosure_length_bytes'] == 26928318,
   'HTTP declared, received and RSS byte sizes agree')
probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(raw)],
                                  capture_output=True, text=True, check=True).stdout)
duration = float(probe['format']['duration'])
ck(math.isfinite(duration) and abs(duration - row['duration_seconds']) < 1e-6 and any(s['codec_type'] == 'audio' for s in probe['streams']),
   'independent ffprobe actual audio and finite retained duration')
ck(abs(duration - row['rss_duration_seconds']) <= max(10, row['rss_duration_seconds'] * .01) and row['rss_duration_within_tolerance'],
   'RSS duration within unchanged audited tolerance')
ck(summary['per_file_cap_bytes'] == config['adapted_constants']['CAP'] == 128 * 1024 ** 2 and raw.stat().st_size <= summary['per_file_cap_bytes'],
   'explicit isolated 128-MiB cap respected')
ck(summary['total_raw_budget_bytes'] == 20 * 1024 ** 3 and summary['free_space_reserve_bytes'] == 6 * 1024 ** 3
   and summary['shared_collection_lock'] == '/workspace/channels-et-raw/.collection-worker.lock', 'shared raw budget/reserve/process lock retained')
ck(config['method_replacements'] == [] and receipt['collector_exit_code'] == 0 and receipt['error'] is None,
   'audited methods retained and actual collector exited successfully')
for old in config['held_nineteen_source_files']:
    ck(sha(R / old['path']) == old['sha256'], 'held nineteen-source file unchanged: ' + pathlib.Path(old['path']).name)
proof = plan['records'][0]['source_proof']
ck(sha(R / proof['path']) == proof['sha256'], 'exact publisher RSS source-proof artifact still bound')
ck(row['episode_guid'] == plan['records'][0]['episode_guid'] == 'lightleaders.podbean.com/5d144c22-ae55-37bb-b83b-5edfb61e45db',
   'actual saved artifact retains exact source GUID')
ck(row['tls_verified'] and row['http_status'] == 200 and row['resumed_from_bytes'] == 0, 'fresh verified-TLS HTTP200 response')
ck(summary['not_youtube_downloads'] and summary['youtube_requests'] == receipt['youtube_requests'] == receipt['asr_requests'] == 0,
   'publisher acquisition kept separate from YouTube and ASR')
failed = [x for x in checks if not x['passed']]
report = {'status': 'FAIL' if failed else 'PASS', 'checks': len(checks), 'failures': failed, 'network_requests_by_verifier': 0,
          'verifier_sha256': sha(pathlib.Path(__file__)), 'plan_sha256': sha(H / 'plan.json'),
          'summary_sha256': sha(H / 'publisher-summary.json'), 'actual_audio_sha256': sha(raw),
          'source_id': row['source_id'], 'bytes': raw.stat().st_size, 'duration_seconds': duration,
          'human_listening_or_speaker_validation': False, 'all_checks': checks}
(H / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ['status', 'checks', 'failures', 'bytes', 'duration_seconds']}, indent=2))
raise SystemExit(bool(failed))
