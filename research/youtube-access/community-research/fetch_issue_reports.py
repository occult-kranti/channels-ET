#!/usr/bin/env python3
"""One syntax-corrected issue search after the recorded 422 validation error."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from fetch_sources import HERE, fetch

target = HERE / 'github-issue-receipt.json'
if target.exists():
    raise SystemExit('Corrected query already recorded; no implicit rerun')
prior = json.loads((HERE / 'fetch-receipts.json').read_text())
initial = next(r for r in prior['records'] if r['id'] == 'github-tunnel-issues')
if initial.get('http_status') != 422:
    raise SystemExit('Only the recorded GitHub query-validation error authorizes this correction')
query = 'repo:yt-dlp/yt-dlp is:issue "Tunnel connection failed"'
url = 'https://api.github.com/search/issues?' + urlencode({'q': query, 'sort': 'updated', 'order': 'desc', 'per_page': 3})
row = fetch(('github-tunnel-issues-corrected', 'public_issue_reports_not_verified_fixes', url))
report = {'reason': "Initial 422 requires explicit is:issue or is:pull-request; corrected validation syntax only.",
          'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'shared_fetcher_sha256': hashlib.sha256((HERE / 'fetch_sources.py').read_bytes()).hexdigest(),
          'new_operations': 1, 'cumulative_source_operations': 9, 'youtube_operations': 0, 'record': row}
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: row.get(k) for k in ['id', 'status', 'http_status', 'bytes', 'error']}, indent=2))
