#!/usr/bin/env python3
"""Remove CDN delivery path/query values from existing public metadata.

Stable RSS source/enclosure URLs and empirical media bytes/hashes are unchanged.
The receipt stores only pre/post file hashes, never removed signed values.
"""
import datetime
import fcntl
import hashlib
import importlib.util
import json
import pathlib

H = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('publisher_redaction', H / 'download.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def endpoint(value):
    result = module.safe_endpoint(value.get('origin') or value.get('url_without_query') or '')
    result['query_keys_only'] = value.get('query_keys_only', result['query_keys_only'])
    if 'http_status' in value:
        result['http_status'] = value['http_status']
    return result


def scrub(value):
    if isinstance(value, dict):
        return {k: endpoint(v) if k == 'final_endpoint' and isinstance(v, dict)
                else [endpoint(x) for x in v] if k == 'redirect_chain' and isinstance(v, list)
                else scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(x) for x in value]
    return value


with (module.RAW_ROOT / '.collection-worker.lock').open('a+') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    changes = []
    for name in ['publisher-summary.json', 'publisher-attempts.jsonl']:
        path = H / name
        raw = path.read_bytes()
        if path.suffix == '.jsonl':
            rows = [scrub(json.loads(line)) for line in raw.decode().splitlines() if line.strip()]
            updated = ''.join(json.dumps(row) + '\n' for row in rows).encode()
        else:
            updated = (json.dumps(scrub(json.loads(raw)), indent=2) + '\n').encode()
        path.write_bytes(updated)
        changes.append({'path': 'research/harvest/publisher_sources/' + name,
                        'before_sha256': digest(raw), 'after_sha256': digest(updated),
                        'changed': raw != updated})
    receipt = {'status': 'completed', 'redacted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'scope': 'Delivery endpoints only: redact full CDN path and query values; preserve stable original RSS source URLs and observed media quantities.',
               'removed_values_retained': False, 'raw_media_bytes_changed': False, 'network_requests': 0,
               'historical_journal_change': 'Security redaction only; strict errors, source identity, byte/hash/duration and success/failure events preserved.',
               'files': changes}
    (H / 'delivery-redaction-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
