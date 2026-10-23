#!/usr/bin/env python3
"""Fetch named public documentation through inherited proxy and verified TLS."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import urllib.error
import urllib.request

H = pathlib.Path(__file__).resolve().parent
CACHE = H / 'source-cache'
CACHE.mkdir(exist_ok=True)
YTDLP = 'fa9886678eb65103303c627b8e013f13f8999b41'
EJS = '6f8587bb7009a1fc81038538071d2cb66b8b8ed0'
SOURCES = [
    ('yt-dlp-readme', f'https://raw.githubusercontent.com/yt-dlp/yt-dlp/{YTDLP}/README.md'),
    ('yt-dlp-license', f'https://raw.githubusercontent.com/yt-dlp/yt-dlp/{YTDLP}/LICENSE'),
    ('yt-dlp-version', f'https://raw.githubusercontent.com/yt-dlp/yt-dlp/{YTDLP}/yt_dlp/version.py'),
    ('ejs-readme', f'https://raw.githubusercontent.com/yt-dlp/ejs/{EJS}/README.md'),
    ('ejs-license', f'https://raw.githubusercontent.com/yt-dlp/ejs/{EJS}/LICENSE'),
    ('yt-dlp-pypi', 'https://pypi.org/pypi/yt-dlp/json'),
    ('github-large-files', 'https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github'),
    ('github-repository-limits', 'https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits'),
    ('github-lfs', 'https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage'),
    ('github-releases', 'https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases'),
    ('github-lfs-billing', 'https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage'),
]


def fetch(pair):
    key, url = pair
    r = {'id': key, 'requested_url': url, 'attempted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'proxy': 'inherited_session_configuration', 'tls_verification': True}
    request = urllib.request.Request(url, headers={'User-Agent': 'channels-ET-research/1.0 documentation audit'})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            raw = response.read(12 * 1024 * 1024)
            r.update(status='retrieved', http_status=response.status, final_url=response.url,
                     content_type=response.headers.get_content_type())
    except urllib.error.HTTPError as error:
        raw = error.read(512 * 1024)
        r.update(status='http_error', http_status=error.code, final_url=error.url, error_type='HTTPError')
    except Exception as error:
        raw = b''
        r.update(status='failed', error_type=type(error).__name__, error=str(error)[:400])
    r.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if raw:
        (CACHE / key).write_bytes(raw)
    return r


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, SOURCES))
    result = {'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'yt_dlp_commit': YTDLP, 'ejs_commit': EJS,
              'scope': 'Public documentation only; no media/download authentication or proxy/TLS override.',
              'records': rows}
    (H / 'fetch-receipts.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: r[k] for k in ['id', 'status', 'bytes', 'sha256']} for r in rows], indent=2))
