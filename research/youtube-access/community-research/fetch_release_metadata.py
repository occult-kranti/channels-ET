#!/usr/bin/env python3
"""Final bounded public-source operation: official Brave release checksum metadata."""
import hashlib
import json
from pathlib import Path
from fetch_sources import HERE, fetch

target = HERE / 'brave-release-receipt.json'
if target.exists():
    raise SystemExit('Release metadata operation already recorded')
row = fetch(('brave-official-release', 'official_release_metadata', 'https://api.github.com/repos/brave/brave-browser/releases/tags/v1.98.60'))
report = {'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'shared_fetcher_sha256': hashlib.sha256((HERE / 'fetch_sources.py').read_bytes()).hexdigest(),
          'new_operations': 1, 'cumulative_source_operations': 10, 'youtube_operations': 0, 'record': row}
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: row.get(k) for k in ['id', 'status', 'http_status', 'bytes', 'error']}, indent=2))
