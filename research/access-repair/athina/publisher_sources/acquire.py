#!/usr/bin/env python3
"""One isolated, explicitly configured execution of the pinned audited collector.

The module's H/R/RAW_ROOT/RAW/CAP/RESERVE/BUDGET constants are adapted below and
published in execution-config.json before execution. No methods are replaced.
"""
import datetime
import hashlib
import importlib.util
import json
import pathlib
import sys

H = pathlib.Path(__file__).resolve().parent
R = H.parents[3]
MODULE = H / 'executed-sources/publisher-collector.py'
PLAN = H / 'plan.json'
MODULE_SHA = '9f3e6e15606ae059b30108acbb390e211847e004b1575fefec71a872b34da864'
PLAN_SHA = 'fbdc074270ac626113f8870d832276fc983872054c255c67efe8d4a25b93409a'
HELD = {
    'research/harvest/publisher_sources/publisher-summary.json': 'a021c6cc7fb3c082b164ed6aee25d6f436810f2afdd2fb23ac6cded412c296c3',
    'research/harvest/publisher_sources/publisher-attempts.jsonl': 'fced53fb869e891f21f127f9b694d0cc53922166364c308df9cd1bf3ad15523c',
    'research/harvest/publisher_sources/expanded-plan.json': '784ffec18b99182286007d132e2837908047aecefd4c42d4277a44e0d13b9712',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 1:
        raise SystemExit('This adapter accepts no overrides or subset retries')
    if any((H / name).exists() for name in ['execution-config.json', 'publisher-summary.json', 'publisher-attempts.jsonl']):
        raise SystemExit('One isolated attempt already recorded; no implicit retry')
    if sha(MODULE) != MODULE_SHA or sha(PLAN) != PLAN_SHA:
        raise SystemExit('Pinned collector/plan hash mismatch')
    if any(sha(R / path) != expected for path, expected in HELD.items()):
        raise SystemExit('Held nineteen-source evidence changed before isolated execution')
    plan = json.loads(PLAN.read_text())
    if len(plan['records']) != 1:
        raise SystemExit('Adapter is restricted to one frozen source row')
    raw = pathlib.Path('/workspace/channels-et-raw/primary-audio')
    target = raw / (plan['records'][0]['source_id'] + '.mp3')
    if target.exists() or target.with_suffix('.mp3.part').exists():
        raise SystemExit('One fresh attempt requires absent target/partial')
    spec = importlib.util.spec_from_file_location('isolated_publisher_collector', MODULE)
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    defaults = {key: str(getattr(collector, key)) if isinstance(getattr(collector, key), pathlib.Path) else getattr(collector, key)
                for key in ['H', 'R', 'RAW_ROOT', 'RAW', 'CAP', 'RESERVE', 'BUDGET']}
    adapted = {'H': H, 'R': R, 'RAW_ROOT': pathlib.Path('/workspace/channels-et-raw'), 'RAW': raw,
               'CAP': 128 * 1024 ** 2, 'RESERVE': 6 * 1024 ** 3, 'BUDGET': 20 * 1024 ** 3}
    for key, value in adapted.items():
        setattr(collector, key, value)
    config = {'schema_version': 1, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'module_path': str(MODULE.relative_to(R)), 'module_sha256': MODULE_SHA,
              'wrapper_path': str(pathlib.Path(__file__).relative_to(R)), 'wrapper_sha256': sha(pathlib.Path(__file__)),
              'plan_path': str(PLAN.relative_to(R)), 'plan_sha256': PLAN_SHA,
              'original_module_constants': defaults,
              'adapted_constants': {key: str(value) if isinstance(value, pathlib.Path) else value for key, value in adapted.items()},
              'method_replacements': [], 'module_thread_pool_limit': 2, 'frozen_jobs': 1,
              'attempts_authorized': 1, 'implicit_retries': False, 'youtube_requests': 0, 'asr_requests': 0,
              'shared_process_lock': '/workspace/channels-et-raw/.collection-worker.lock',
              'tls_and_proxy': 'Unmodified audited module uses Python default verified TLS and inherited proxy.',
              'held_nineteen_source_files': [{'path': path, 'sha256': expected} for path, expected in HELD.items()]}
    (H / 'execution-config.json').write_text(json.dumps(config, indent=2) + '\n')
    code = 1
    error = None
    try:
        sys.argv = [str(MODULE), '--plan', str(PLAN)]
        code = collector.main()
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:250]
    finally:
        unchanged = all(sha(R / path) == expected for path, expected in HELD.items())
        receipt = {'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'module_sha256': sha(MODULE), 'wrapper_sha256': sha(pathlib.Path(__file__)),
                   'plan_sha256': sha(PLAN), 'configuration_sha256': sha(H / 'execution-config.json'),
                   'collector_exit_code': code, 'error': error, 'held_nineteen_source_files_unchanged': unchanged,
                   'youtube_requests': 0, 'asr_requests': 0}
        for name in ['publisher-summary.json', 'publisher-attempts.jsonl']:
            if (H / name).is_file():
                receipt[name + '_sha256'] = sha(H / name)
        (H / 'execution-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if not unchanged:
            raise RuntimeError('Held nineteen-source evidence changed during isolated execution')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
