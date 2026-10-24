#!/usr/bin/env python3
"""Build a bounded source register and independently audit held Brave evidence locally."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import ssl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BRAVE = HERE.parent / 'brave'
checks = []


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


class Plain(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.off = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript'}:
            self.off.append(tag)

    def handle_endtag(self, tag):
        if tag in self.off:
            self.off.remove(tag)

    def handle_data(self, text):
        if not self.off:
            self.parts.append(text)


initial = json.loads((HERE / 'fetch-receipts.json').read_text())
corrected = json.loads((HERE / 'github-issue-receipt.json').read_text())
release_fetch = json.loads((HERE / 'brave-release-receipt.json').read_text())
rows = initial['records'] + [corrected['record'], release_fetch['record']]
ck(len(rows) == 10 and sum(x['attempts'] for x in rows) == 10, 'ten bounded source operations, one attempt each')
saved = {r['id']: r for r in rows}
texts = {}
for row in rows:
    if 'private_body_path' in row:
        path = Path(row['private_body_path'])
        ck(not path.resolve().is_relative_to(ROOT) and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['id'] + ' retained private response hash/size')
        texts[row['id']] = path.read_text(errors='replace')


def source(ident, title, locator, quote, relevance, source_date=None):
    row = saved[ident]
    raw = texts[ident]
    parser = Plain()
    parser.feed(raw)
    normalized = re.sub(r'\s+', ' ', ' '.join(parser.parts)) if '<html' in raw.lower() or '<!doctype' in raw.lower() else re.sub(r'\s+', ' ', raw)
    ck(re.sub(r'\s+', ' ', quote) in normalized, ident + ' selected exact excerpt verified')
    return {'id': ident, 'title': title, 'url': row['final_url'], 'authority': row['kind'],
            'retrieved_at': row['finished_at'], 'source_date': source_date,
            'snapshot_sha256': row['sha256'], 'access_depth': 'Selected quoted section read in saved response; not all linked guidance followed.',
            'locator': locator, 'excerpt': quote, 'assessment': relevance,
            'verified_fix_for_current_environment': False}


entries = [
    source('yt-dlp-readme', 'yt-dlp README', 'Dependencies, lines 203–215 in saved Markdown',
           'Required for full YouTube support.',
           'EJS, a supported JavaScript runtime and ffmpeg are extractor/media prerequisites already installed here. They operate after transport access and do not establish a denied CONNECT tunnel.'),
    source('yt-dlp-faq', 'yt-dlp FAQ', 'Heading about HTTP403 on an issue labeled Cloudflare-related, lines 166–170',
           'The 403 errors are coming from Cloudflare;',
           'This statement is explicitly scoped to Cloudflare-related origin/site issues. Our target-bound tunnel response identifies Envoy before origin TLS, so the FAQ does not diagnose this case. Cookie/challenge/IP recipes were not used.'),
    source('brave-shields', "Brave: How do I check if a site's connection is secure?", 'Security information and certificate-error sections; numeric article ID360018185871',
           'Brave will alert you if you can’t visit the site safely or privately.',
           'Official certificate/security guidance supports distinguishing trust errors from tunnel errors. The requested guessed slug did not determine the article: the actual returned title is recorded here.',
           'Updated November 13, 2025 22:06 as displayed in saved article'),
    source('chromium-network-errors', 'Chromium network error definitions', 'net/base/net_error_list.h lines191–193, NET_ERROR(TUNNEL_CONNECTION_FAILED, -111)',
           'A tunnel connection through the proxy could not be established.',
           'Official source matches Brave ERR_TUNNEL_CONNECTION_FAILED. It locates the failed stage, not the policy/authentication/internal reason. This is a current-branch source snapshot, not the exact installed engine revision.'),
    source('rfc9110-connect', 'RFC9110 HTTP Semantics', 'Section9.3.6 paragraph7',
           'Any response other than a successful response indicates that the tunnel has not yet been formed.',
           'A non-successful CONNECT response is not an origin YouTube HTTP response; no underlying denial cause follows from this protocol fact.', 'June2022'),
]

issues = json.loads(texts['github-tunnel-issues-corrected'])
ck(issues['total_count'] == 15 and len(issues['items']) == 3, 'GitHub query returned three of fifteen matching reports')
for number, quote, assessment in [
    (8276, 'Also the proxy is fully functional, I can confirm that it works on other sites',
     'Reporter describes a Twitter proxy444 despite other sites working. This illustrates that a working control is not destination access proof. Different provider/status/site; comments and a validated repair were not retrieved. Closed state is not proof of a fix.'),
    (11185, 'Tunnel connection failed: 503 Service Unavailable',
     'The supplied log has proxy503 during release-info retrieval while later YouTube format enumeration succeeds. It concerns different hosts/stages and client-format behavior, not our Envoy403 tunnel. No proposed extractor-client change was adopted.'),
]:
    index, item = next((i, x) for i, x in enumerate(issues['items']) if x['number'] == number)
    ck(quote in item['body'], 'GitHub issue ' + str(number) + ' excerpt verified')
    entries.append({'id': 'github-issue-' + str(number), 'title': item['title'], 'url': item['html_url'],
                    'authority': 'public_user_report_not_verified_fix', 'source_created_at': item['created_at'],
                    'source_updated_at': item['updated_at'], 'source_state': item['state'],
                    'retrieved_at': saved['github-tunnel-issues-corrected']['finished_at'],
                    'snapshot_sha256': saved['github-tunnel-issues-corrected']['sha256'], 'locator': '/items/' + str(index),
                    'access_depth': 'Issue metadata/body returned by GitHub search read; comments and subsequent linked fixes not retrieved.',
                    'excerpt': quote, 'assessment': assessment, 'verified_fix_for_current_environment': False})

release = json.loads(texts['brave-official-release'])
asset = next(x for x in release['assets'] if x['name'] == 'brave-browser_1.98.60_amd64.deb')
entries.append({'id': 'brave-official-release', 'title': 'Official Brave v1.98.60 release', 'url': release['html_url'],
                'authority': 'official_release_metadata', 'source_published_at': release['published_at'],
                'retrieved_at': saved['brave-official-release']['finished_at'], 'snapshot_sha256': saved['brave-official-release']['sha256'],
                'access_depth': 'Release metadata and exact amd64.deb asset checksum/size inspected.',
                'asset': {k: asset[k] for k in ('name', 'size', 'digest', 'browser_download_url')},
                'assessment': 'Independently matches the actually retained official package checksum and size. Browser provenance is verified; access is assessed separately.',
                'verified_fix_for_current_environment': False})
for ident, title, assessment in [
    ('reddit-youtubedl-search', 'r/youtubedl search for proxy CONNECT403',
     'One ordinary request returned HTTP403 and a network-security block page. No post or solution was accessed. The response alone does not identify the blocking infrastructure.'),
    ('substack-simon-willison', 'Simon Willison Substack feed (attempted identifiable publication)',
     'One ordinary request failed proxy CONNECT403 before feed content. No article, quoted advice, author-feed metadata confirmation or verified solution is claimed.'),
]:
    row = saved[ident]
    entries.append({'id': ident, 'title': title, 'url': row['requested_url'], 'authority': 'unavailable_community_source',
                    'attempted_at': row['started_at'], 'status': row['status'], 'http_status': row.get('http_status'),
                    'error': row['error'], 'snapshot_sha256': row.get('sha256'),
                    'access_depth': 'No usable community source content retrieved.', 'assessment': assessment,
                    'verified_fix_for_current_environment': False})
ck(len(entries) == 10, 'ten curated evidence entries maximum')

manifest = json.loads((BRAVE / 'source-manifest.json').read_text())
ck(manifest['status'] == 'HOLD' and len(manifest['files']) == 13, 'Brave source owner holds thirteen-file manifest')
for name, row in manifest['files'].items():
    ck((BRAVE / name).stat().st_size == row['bytes'] and sha(BRAVE / name) == row['sha256'], 'held Brave source/receipt ' + name)
runtime = json.loads((BRAVE / 'runtime-receipt.json').read_text())
control = json.loads((BRAVE / 'control-receipt.json').read_text())
baseline = json.loads((BRAVE / 'baseline-control-receipt.json').read_text())
watch = json.loads((BRAVE / 'watch-receipt.json').read_text())
ck(runtime['sha256'] == asset['digest'].split(':')[1] and runtime['bytes'] == asset['size'] == 153190012, 'runtime expected checksum/size independently match official release API')
package = Path('/workspace/channels-et-brave-runtime/brave-browser_1.98.60_amd64.deb')
ck(package.stat().st_size == asset['size'] and sha(package) == runtime['sha256'], 'actual retained Brave package exact upstream checksum')
ck(release['tag_name'] == 'v1.98.60' and release['published_at'] == '2026-10-21T09:09:05Z' and not release['draft'] and not release['prerelease'], 'official release identity/date/state')
ck('ERR_CERT_AUTHORITY_INVALID' in baseline.get('navigationError', ''), 'fresh-profile certificate error retained separately')
ck(control['passed'] and control['ignoreHTTPSErrors'] is False and control['actualAcquisitionDashboardRendered'], 'recorded allowed control renders with TLS verification')
ck(any(x['status'] == 200 and x['tls']['protocol'] == 'TLS 1.3' for x in control['responses']), 'recorded Pages HTTP200/TLS1.3')
ck(watch['ordinaryWatchNavigations'] == 1 and len(watch['pageRequests']) == 1 and not watch['responses'], 'one recorded watch document operation and no origin response')
ck(watch['outcome'] == 'navigation_failed' and 'ERR_TUNNEL_CONNECTION_FAILED' in watch['navigationError'], 'watch navigation is explicitly failed, not a source-access success')
ck(watch['proxyConfigurationPreserved'] and watch['ignoreHTTPSErrors'] is False, 'watch retains inherited proxy and TLS checking')
ck(watch['engine']['revision'] == '@52db4b25c0aa3038e9a1c6021428b136cc3cb5f' and watch['engine']['product'] == 'Chrome/156.0.8078.48', 'actual recorded engine exact revision')
netlog_path = Path('/workspace/channels-et-brave-profile/watch-netlog.json')
log = json.loads(netlog_path.read_text())
names = {v: k for k, v in log['constants']['logEventTypes'].items()}
sends = [e for e in log['events'] if names[e['type']] == 'HTTP_TRANSACTION_SEND_TUNNEL_HEADERS'
         and re.match(r'^CONNECT www\.youtube\.com:443 HTTP/\d', e.get('params', {}).get('line', ''))]
ck(len(sends) == watch['targetConnectRequestsObserved'] == 1, 'actual private NetLog one exact target CONNECT')
source_ids = {e['source']['id'] for e in sends}
responses = [e for e in log['events'] if e['source']['id'] in source_ids and names[e['type']] == 'HTTP_TRANSACTION_READ_TUNNEL_RESPONSE_HEADERS']
ck(len(responses) == 1, 'one same-network-source tunnel response')
headers = responses[0]['params']['headers']
ck(any(re.match(r'^HTTP/\d(?:\.\d)? 403 ', x) for x in headers) and any(x.lower() == 'server: envoy' for x in headers), 'private target-bound response really is Envoy403')
marker = json.loads(Path('/workspace/channels-et-brave-profile/youtube-watch-navigation-started.json').read_text())
ck(marker['startedAt'] == watch['checkedAt'] and marker['ordinaryNavigationBudget'] == 1, 'private one-navigation guard binds actual attempt')
cert = ssl.PEM_cert_to_DER_cert(Path('/usr/local/share/ca-certificates/environment-proxy-ca.crt').read_text())
db = sqlite3.connect('file:/workspace/channels-et-brave-profile/Default/ServerCertificate?mode=ro&immutable=1', uri=True)
ck(db.execute('SELECT sha256hash_hex,der_cert,trust_settings FROM certificates').fetchall()
   == [(hashlib.sha256(cert).hexdigest(), cert, bytes.fromhex('0a020803'))], 'actual Brave profile trusts exactly configured public CA')
db.close()
probe = (BRAVE / 'probe.cjs').read_text()
ck('ignoreHTTPSErrors:false' in probe and 'ignore-certificate-errors' not in probe and "url===target" in probe and "flag:'wx'" in probe, 'source has no TLS bypass and keeps target/retry guards')

register = {'checked_at': datetime.now(timezone.utc).isoformat(), 'source_operation_count': 10,
            'successful_document_operations': sum(r['status'] == 'retrieved' for r in rows),
            'failed_document_operations': sum(r['status'] != 'retrieved' for r in rows),
            'initial_github_validation_error_corrected_once': True, 'youtube_requests_by_this_reviewer': 0,
            'community_fix_verified_for_environment': False, 'entries': entries,
            'excluded_search_result': {'issue': 'https://github.com/yt-dlp/yt-dlp/issues/10893',
                                       'reason': 'Returned title/body mix Twitter and YouTube context and lack a complete relevant diagnostic. Not used as repair evidence.'}}
(HERE / 'source-register.json').write_text(json.dumps(register, indent=2) + '\n')
failed = [x for x in checks if not x['passed']]
report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'FAIL' if failed else 'PASS_WITH_EXPLICIT_LIMITS',
          'checks_passed': len(checks) - len(failed), 'checks_total': len(checks), 'failures': failed,
          'review_script_sha256': sha(Path(__file__)), 'brave_source_manifest_sha256': sha(BRAVE / 'source-manifest.json'),
          'brave_watch_receipt_sha256': sha(BRAVE / 'watch-receipt.json'), 'private_netlog_sha256': sha(netlog_path),
          'source_register_sha256': sha(HERE / 'source-register.json'), 'source_document_operations': 10,
          'new_youtube_operations_by_reviewer': 0, 'new_browser_runs_by_reviewer': 0, 'new_media_downloads_by_reviewer': 0,
          'conclusion': 'Official Brave genuinely ran and its allowed TLS control succeeded; one exact target CONNECT received Envoy403 and no origin response. The underlying proxy refusal/fault cause remains unknown; no video/audio/caption acquisition or verified community repair is claimed.',
          'limits': ['Only the explicitly identified document sections and selected issue bodies were reviewed; comments and linked repairs were not fetched.',
                     'A closed GitHub issue is not verified resolution; Reddit and Substack yielded no usable post/article.',
                     'Source hashes identify retrieved snapshots; current-branch documentation is not an exact installed-code revision.',
                     'Ten documentation operations include one syntax-corrected API query; no denied destination request was repeated.'], 'all_checks': checks}
(HERE / 'independent-brave-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks_passed', 'checks_total', 'failures', 'conclusion']}, indent=2))
raise SystemExit(bool(failed))
