#!/usr/bin/env python3
"""Eight bounded public documentation/community fetches; never probe YouTube."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener, proxy_bypass
import urllib.error

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/workspace/channels-et-private/community-research')
CAP = 4 * 1024 * 1024
SOURCES = [
    ('yt-dlp-readme', 'official_project_documentation', 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/README.md'),
    ('yt-dlp-faq', 'official_project_documentation', 'https://raw.githubusercontent.com/wiki/yt-dlp/yt-dlp/FAQ.md'),
    ('brave-shields', 'official_browser_guidance', 'https://support.brave.com/hc/en-us/articles/360018185871-How-do-I-use-Shields-while-browsing'),
    ('github-tunnel-issues', 'public_issue_reports_not_verified_fixes', 'https://api.github.com/search/issues?' + urlencode({'q': 'repo:yt-dlp/yt-dlp "Tunnel connection failed"', 'sort': 'updated', 'order': 'desc', 'per_page': 3})),
    ('chromium-network-errors', 'official_source_code', 'https://raw.githubusercontent.com/chromium/chromium/main/net/base/net_error_list.h'),
    ('reddit-youtubedl-search', 'public_community_search', 'https://www.reddit.com/r/youtubedl/search.json?' + urlencode({'q': 'proxy CONNECT 403', 'restrict_sr': 1, 'sort': 'new', 'limit': 3})),
    ('substack-simon-willison', 'identifiable_technical_author_feed_not_assumed_fix', 'https://simonw.substack.com/feed'),
    ('rfc9110-connect', 'standards_protocol_reference', 'https://www.rfc-editor.org/rfc/rfc9110.html'),
]


def now():
    return datetime.now(timezone.utc).isoformat()


class HTTPSOnly(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, target):
        parts = urlsplit(target)
        if parts.scheme != 'https' or parts.username or parts.password:
            raise ValueError('Non-HTTPS/auth-bearing redirect refused')
        if parts.hostname and (parts.hostname == 'youtube.com' or parts.hostname.endswith('.youtube.com') or parts.hostname.endswith('.googlevideo.com')):
            raise ValueError('No documentation request may navigate to YouTube/media')
        if proxy_bypass(parts.hostname):
            raise ValueError('Direct proxy-bypassed documentation target refused')
        return super().redirect_request(request, fp, code, message, headers, target)


def fetch(source):
    ident, kind, url = source
    result = {'id': ident, 'kind': kind, 'requested_url': url, 'started_at': now(),
              'attempts': 1, 'retry': False, 'proxy': 'inherited_session_configuration',
              'tls_verification_enabled': True, 'body_cap_bytes': CAP}
    try:
        if proxy_bypass(urlsplit(url).hostname):
            raise ValueError('Direct proxy-bypassed documentation target refused')
        opener = build_opener(HTTPSOnly(), HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(Request(url, headers={'User-Agent': 'channels-ET-evidence-review/1.0', 'Accept': '*/*'}), timeout=25) as response:
            data = response.read(CAP + 1)
            if len(data) > CAP:
                raise ValueError('Document response exceeded retained-body cap')
            result.update(status='retrieved', http_status=response.status, final_url=response.url,
                          content_type=response.headers.get('Content-Type'), last_modified=response.headers.get('Last-Modified'),
                          etag=response.headers.get('ETag'))
    except Exception as error:
        data = b''
        result.update(status='failed', error_type=type(error).__name__, error=str(error)[:350])
        if isinstance(error, urllib.error.HTTPError):
            result['http_status'] = error.code
            data = error.read(CAP)
        result['proxy_tunnel_denied'] = 'Tunnel connection failed: 403' in str(error)
    if data:
        path = PRIVATE / (ident + '.body')
        with path.open('xb') as stream:
            stream.write(data)
        result.update(private_body_path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    result['finished_at'] = now()
    return result


def main():
    if (HERE / 'fetch-receipts.json').exists():
        raise SystemExit('Bounded fetches already recorded; no implicit rerun')
    if not (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')):
        raise SystemExit('Inherited HTTPS proxy required')
    PRIVATE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, SOURCES))
    report = {'checked_at': now(), 'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'operation_count': len(rows), 'max_concurrency': 3, 'youtube_operations': 0,
              'scope': 'One ordinary request operation per listed public source; redirects may add HTTP transactions; no media, browser or inference requests.',
              'records': rows}
    (HERE / 'fetch-receipts.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{k: r.get(k) for k in ['id', 'status', 'http_status', 'bytes', 'error']} for r in rows], indent=2))


if __name__ == '__main__':
    main()
