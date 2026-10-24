#!/usr/bin/env python3
"""Independent local-file audit; no acquisition, browser navigation or inference."""
import datetime
import hashlib
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import ssl
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
FOLLOW = ROOT / 'research/access-repair'
RAW = Path('/workspace/channels-et-raw')
checks = []
bindings = {}


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(relative):
    path = ROOT / relative
    bindings[relative] = sha(path)
    return json.loads(path.read_text())


def ck(condition, label):
    checks.append({'check': label, 'passed': bool(condition)})


def private(item, label):
    path = Path(item['raw_local_path'])
    ck(path.resolve().is_relative_to(RAW) and not path.is_symlink() and path.is_file(), label + ' private path')
    ck(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], label + ' exact bytes/hash')
    return path


def word_count(text):
    return len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", text))


class Render(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        value = re.sub(r'\s+', ' ', data).strip()
        if value and not set(self.stack).intersection({'script', 'style', 'noscript', 'head'}):
            self.parts.append(value)


meta = read('research/access-repair/primary-sources/metadata.json')
expanded = read('research/access-repair/primary-sources/expanded-metadata.json')
records = {r['source_id']: r for r in meta['records']}
ck(meta['network_requests'] == 3 and expanded['new_network_requests'] == 2 and expanded['cumulative_publisher_network_requests'] == 5,
   'five recorded publisher operations, not a claim of five HTTP transactions including redirects')
for row in [*meta['records'], expanded['paul'], expanded['athina']]:
    ck(row['http_status'] == 200 and row['status'] == 'retrieved' and row['tls_certificate_verification_enabled'] is True,
       row['source_id'] + ' recorded verified-TLS HTTP200 outcome')
    private(row['response'], row['source_id'] + ' response')
    if 'text' in row:
        path = private(row['text'], row['source_id'] + ' extracted text')
        ck(word_count(path.read_text()) == row['text']['word_count'], row['source_id'] + ' mechanical word count')
    for pointer in row.get('source_pointers', []):
        ck(sha(ROOT / pointer['path']) == pointer['sha256'], row['source_id'] + ' inherited source hash')
        node = json.loads((ROOT / pointer['path']).read_text())
        for part in pointer['json_pointer'].strip('/').split('/'):
            node = node[int(part)] if isinstance(node, list) else node[part]
        ck(node['id'] == pointer['source_id'], row['source_id'] + ' inherited source pointer identity')
ck(sha(ROOT / 'research/access-repair/primary-sources/fetch.py') == meta['collector_sha256'], 'executed text collector source pin')
ck(sha(ROOT / 'research/access-repair/primary-sources/expand.py') == expanded['collector_sha256'], 'executed linked-source collector pin')
ck(sha(ROOT / 'research/access-repair/primary-sources/metadata.json') == expanded['original_fetch_metadata_sha256'], 'follow-up metadata binds first requests')

feed = ET.fromstring(Path(records['daniel-feed']['response']['raw_local_path']).read_bytes()).find('channel')
items = feed.findall('item')
ck(len(items) == expanded['daniel']['items_extracted'] == 15, 'fifteen Daniel RSS items')
ck(len({x.findtext('guid') for x in items}) == 15, 'Daniel GUID uniqueness in saved snapshot')
for row, item in zip(expanded['daniel']['items'], items):
    path = private(row['text'], 'Daniel item ' + str(row['item_index']))
    text = path.read_text()
    ck(word_count(text) == row['text']['word_count'], 'Daniel item mechanical words ' + str(row['item_index']))
    ck(row['guid'] == item.findtext('guid') and row['title'] == item.findtext('title'), 'Daniel item actual feed identity ' + str(row['item_index']))
    parser = Render()
    parser.feed(item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or item.findtext('description') or '')
    ck(text == '\n'.join(parser.parts), 'Daniel independently rendered saved RSS body ' + str(row['item_index']))
ck(sum(row['text']['word_count'] for row in expanded['daniel']['items']) == expanded['daniel']['total_rendered_item_words'] == 10998,
   '10998 rendered Daniel words include publisher promotions')

paul = expanded['paul']
pdf = Path(paul['response']['raw_local_path'])
ck(pdf.read_bytes().startswith(b'%PDF-') and pdf.stat().st_size == 49941, 'actual Paul valid PDF magic/size')
info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
ck(int(re.search(r'^Pages:\s+(\d+)', info, re.M).group(1)) == paul['pages'] == 4, 'independent four-page PDF probe')
text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
ck(text == Path(paul['text']['raw_local_path']).read_text() and word_count(text) == 2577, 'independent Paul extraction exact 2577 words')
ck('The Expression of the True Self' in text and 'July 15, 2017' in text, 'actual Paul PDF header title/date')
ck(paul['requested_url'] in Path(records['paul-birmingham']['response']['raw_local_path']).read_text(), 'official Paul page explicitly contains exact PDF link')
ck('spiritual' in paul['scope'].casefold() and 'not biological ET' in paul['scope'], 'Paul comparison-source boundary retained')

athina = expanded['athina']
ck(athina['requested_url'] in Path(records['athina-ashtar']['response']['raw_local_path']).read_text(), 'creator page explicitly links exact feed')
rss = ET.fromstring(Path(athina['response']['raw_local_path']).read_bytes()).find('channel')
matched = [x for x in rss.findall('item') if (x.findtext('link') or '').rstrip('/') == records['athina-ashtar']['requested_url'].rstrip('/')]
ck(len(rss.findall('item')) == athina['feed_item_count'] == 212 and len(matched) == 1, '212-item feed with one exact creator URL match')
source = matched[0]
ck(source.findtext('guid') == athina['exact_episode_matches'][0]['guid'], 'Athina exact RSS GUID')

config = read('research/access-repair/athina/publisher_sources/execution-config.json')
executed = read('research/access-repair/athina/publisher_sources/execution-receipt.json')
publisher = read('research/access-repair/athina/publisher_sources/publisher-summary.json')
plan = read('research/access-repair/athina/publisher_sources/plan.json')
for key in ('module', 'wrapper', 'plan'):
    ck(sha(ROOT / config[key + '_path']) == config[key + '_sha256'] == executed[key + '_sha256'], 'Athina ' + key + ' execution source pin')
ck(config['method_replacements'] == [] and config['adapted_constants']['CAP'] == 128 * 1024 ** 2, 'audited collector methods and 128MiB cap')
ck(publisher['terminal'] and publisher['completed_audio_files'] == publisher['planned_jobs'] == len(publisher['records']) == 1, 'separate single-source completed ledger')
row = publisher['records'][0]
audio = Path(row['raw_local_path'])
ck(audio.resolve().is_relative_to(RAW) and not audio.is_symlink(), 'new audio remains external private file')
ck(sha(audio) == row['sha256'] == '310c6d538a438cee6ba4372e337184e8b96c9d9de385779f9dbf68bc4dec76cf', 'actual Athina audio SHA256')
ck(audio.stat().st_size == row['bytes'] == row['response_declared_remaining_bytes'] == row['rss_enclosure_length_bytes'] == 26928318, '26928318 body bytes match HTTP/RSS/audio')
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(audio)]))
duration = float(probe['format']['duration'])
ck(duration == row['duration_seconds'] == 1682.99102 and any(s['codec_type'] == 'audio' for s in probe['streams']), 'actual finite audio duration and stream')
ck(row['enclosure_url'] == source.find('enclosure').get('url') and row['episode_guid'] == source.findtext('guid'), 'audio artifact bound to exact creator RSS item')
journal = [json.loads(x) for x in (FOLLOW / 'athina/publisher_sources/publisher-attempts.jsonl').read_text().splitlines()]
ck(len(journal) == 1 and journal[0] == row, 'one recorded audio attempt, no retries')
for name in ('publisher-summary.json', 'publisher-attempts.jsonl'):
    ck(sha(FOLLOW / 'athina/publisher_sources' / name) == executed[name + '_sha256'], 'audio receipt binds ' + name)
ck(row['http_status'] == 200 and row['tls_verified'] and row['resumed_from_bytes'] == 0, 'recorded fresh verified-TLS audio response')
for old in config['held_nineteen_source_files']:
    ck(sha(ROOT / old['path']) == old['sha256'], 'original19 unchanged ' + Path(old['path']).name)
ck(sha(ROOT / 'research/harvest/asr/summary.json') == 'd6fd855158ddf714b8b9125571d0814514f1fd3c3e630908c6cbad154ddb2aba', 'original19 ASR summary unchanged')

adapter = read('research/access-repair/athina/asr/adapter-execution.json')
receipt = read('research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json')
model = read('research/access-repair/athina/asr/model-manifest.json')
ck(sha(ROOT / adapter['corePath']) == adapter['coreSha256'] == sha(FOLLOW / 'athina/asr' / ('executed-core-' + adapter['coreSha256'] + '.py')), 'actual retained ASR core source pin')
ck(sha(FOLLOW / 'athina/run_asr.py') == adapter['adapterSha256'], 'actual source-ledger ASR adapter pin')
ck(sha(FOLLOW / 'athina/publisher_sources/publisher-summary.json') == adapter['sourceLedgerSha256'], 'ASR adapter binds isolated publisher ledger')
ck(sha(FOLLOW / 'athina/asr/310c6d538a438cee6ba4-receipt.json') == adapter['publicReceiptSha256'], 'ASR adapter binds completed receipt')
ck(receipt['sourceId'] == row['source_id'] and receipt['sourceUrl'] == row['enclosure_url'] and receipt['sourceAudioSha256'] == row['sha256'], 'ASR source identity URL/hash agree')
protocol = receipt['executionProtocol']
ck(hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest() == receipt['executionSignature'], 'ASR execution signature reproduced')
ck(protocol['scriptSha256'] == adapter['coreSha256'] and protocol['modelManifestSha256'] == sha(FOLLOW / 'athina/asr/model-manifest.json'), 'ASR signature binds exact model/core')
ck(receipt['versions'] == {'faster-whisper': '1.2.1', 'ctranslate2': '4.8.3', 'av': '16.1.0'}, 'supported recorded ASR runtime versions')
ck(receipt['transcribedScope'] == 'full_decoded_audio' and receipt['clipSeconds'] is None and receipt['decoding'] == {'language': 'en', 'beam_size': 1, 'vad_filter': True, 'condition_on_previous_text': False}, 'unclipped pinned decoding settings')
ck(model['modelId'] == receipt['modelId'] == 'Systran/faster-whisper-tiny.en' and model['revision'] == receipt['modelRevision'] == '0d3d19a32d3338f10357c0889762bd8d64bbdeba', 'official pinned tiny.en model identity')
for item in model['files']:
    path = Path(model['localCache']) / item['path']
    ck(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'actual cached model file ' + item['path'])
output = Path(receipt['transcriptDirectory'])
ck(output.resolve().is_relative_to(RAW) and not output.is_symlink(), 'new transcript directory remains outside Git')
ck({x['name'] for x in receipt['outputs']} == {'segments.jsonl', 'transcript.txt', 'transcript.srt'}, 'exact three transcript artifacts')
for item in receipt['outputs']:
    path = output / item['name']
    ck(path.is_file() and not path.is_symlink() and path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'actual ASR output ' + item['name'])
private_receipt = json.loads((output / 'receipt.json').read_text())
ck({k: v for k, v in receipt.items() if k != 'transcriptDirectory'} == private_receipt, 'public/private receipt agrees exactly')
segments = [json.loads(x) for x in (output / 'segments.jsonl').read_text().splitlines()]
ck(len(segments) == receipt['segments'] == adapter['segments'] == 259, '259 actual ASR segments')
for i, segment in enumerate(segments):
    ck(math.isfinite(segment['start']) and math.isfinite(segment['end']) and 0 <= segment['start'] <= segment['end'] <= duration + 2
       and (i == 0 or segment['start'] >= segments[i - 1]['start']), 'actual segment finite bounds/monotonic start ' + str(i))
ck(len(' '.join(x['text'] for x in segments).split()) == receipt['words'] == adapter['words'] == 3394, '3394 actual whitespace ASR words')
ck((output / 'transcript.txt').read_text() == '\n'.join(x['text'] for x in segments) + '\n', 'text derives from same retained segment rows')
ck(receipt['humanReviewed'] is False and receipt['speakerDiarizationPerformed'] is False and receipt['youtubeVideoEditionVerified'] is False, 'ASR validation limits retained')

baseline = read('research/access-repair/browser/baseline-receipt.json')
trust = read('research/access-repair/browser/trust-store-receipt.json')
browser = read('research/access-repair/browser/verification-receipt.json')
browser_manifest = read('research/access-repair/browser/source-manifest.json')
for name, digest in browser_manifest['files'].items():
    ck(sha(FOLLOW / 'browser' / name) == digest, 'browser source/receipt manifest ' + name)
ck('ERR_CERT_AUTHORITY_INVALID' in baseline['controls'][0]['navigationError'], 'saved initial browser CA rejection')
ck(browser['passed'] and browser['ignoreHTTPSErrors'] is False and browser['inheritedProxyUsed'] is True, 'browser controls retain inherited proxy and TLS checks')
ck(all(x['status'] == 200 and x['tlsVerifiedResponse'] and x['tls']['protocol'] == 'TLS 1.3' for x in browser['controls']), 'two recorded browser HTTPS200/TLS1.3 controls')
negative = browser['unrelatedCertificateControl']
ck(negative['passed'] and negative['httpRequestsReachedFixture'] == 0 and negative['externalNavigations'] == 0 and 'ERR_CERT_AUTHORITY_INVALID' in negative['navigationError'], 'recorded local unrelated certificate rejection')
browser_source = (FOLLOW / 'browser/verify-browser.cjs').read_text()
ck('ignoreHTTPSErrors:true' not in browser_source and 'ignore-certificate-errors' not in browser_source and 'ignore-certificate-errors-spki-list' not in browser_source, 'browser source contains no TLS-ignore flags')
ck("url.hostname === '127.0.0.1' ? route.continue() : route.abort()" in browser_source and "--proxy-bypass-list=127.0.0.1" in browser_source, 'separate negative-control bypass/guard limited to literal loopback')
ck(os.environ.get('NODE_TLS_REJECT_UNAUTHORIZED') != '0', 'current Node TLS verification not disabled by environment')
profile = Path('/workspace/channels-et-browser-profile')
ca = Path('/usr/local/share/ca-certificates/environment-proxy-ca.crt')
der = ssl.PEM_cert_to_DER_cert(ca.read_text())
fingerprint = hashlib.sha256(der).hexdigest()
db = sqlite3.connect('file:' + str(profile / 'Default/ServerCertificate') + '?mode=ro&immutable=1', uri=True)
rows = db.execute('SELECT sha256hash_hex,der_cert,trust_settings FROM certificates').fetchall()
ck(rows == [(fingerprint, der, bytes.fromhex('0a020803'))] and fingerprint == trust['caSha256'], 'actual Chromium database trusts only exact configured managed public CA')
ck(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'private Chromium trust database integrity')
db.close()
ck(not profile.is_relative_to(ROOT) and profile.stat().st_mode & 0o077 == 0, 'browser profile remains outside repository and private')

watch = read('research/access-repair/diagnostics/revision6-watch-probe.json')
proxy = read('research/access-repair/diagnostics/revision6-proxy-response.json')
ck(watch['proxyTunnelDenied'] and watch['tlsVerificationEnabled'] and watch['runtimeObservationBeforeProbe']['specRevision'] == '6', 'new revision6 ordinary-watch receipt records CONNECT denial')
ck(proxy['proxyConnectStatus'] == 403 and proxy['originTlsStarted'] is False and proxy['safeResponseHeaders']['server'] == 'envoy', 'response diagnostic remains pre-origin Envoy403, opaque cause')
ck(not any(p.suffix.lower() in {'.pdf', '.mp3', '.m4a', '.wav', '.srt', '.pem', '.crt'} for p in FOLLOW.rglob('*') if p.is_file()), 'no new raw source audio/full PDF/subtitle/certificate artifacts under public research tree')

failures = [x for x in checks if not x['passed']]
report = {'schema_version': 1, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status': 'FAIL' if failures else 'PASS_WITH_EXPLICIT_LIMITS', 'checks_passed': len(checks) - len(failures),
          'checks_total': len(checks), 'failures': failures, 'verifier_sha256': sha(Path(__file__)),
          'source_network_requests_by_reviewer': 0, 'browser_navigation_by_reviewer': 0, 'neural_runs_by_reviewer': 0,
          'original_21567_checks_rerun': False,
          'verified_counts': {'daniel_rendered_items': 15, 'daniel_rendered_words_including_promotions': 10998,
                              'paul_pdf_pages': 4, 'paul_extracted_words': 2577,
                              'athina_audio_bytes': 26928318, 'athina_audio_seconds': duration,
                              'athina_asr_segments': 259, 'athina_asr_whitespace_words': 3394},
          'browser_youtube_zero_scope': 'Control automation has no explicit YouTube navigation/collection. Its literal youtubeRequests:0 is not an instrumented count of all subrequests.',
          'limits': ['Local byte/provenance/count verification; recorded HTTPS outcomes were inspected, not independently repeated.',
                     'No human listening, speech accuracy, speaker identity, entity origin or recording/YouTube-edition equivalence validation.',
                     'Daniel full rendered RSS item counts include publisher promotion; Paul is spiritual-Guides comparison text.',
                     'The separate new source cohort is not appended to the frozen nineteen-source ledger or earlier paper/model cohort.'],
          'input_hashes': bindings, 'all_checks': checks}
target = Path(__file__).with_name('independent-followup-verification.json')
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks_passed', 'checks_total', 'failures', 'verified_counts']}, indent=2))
raise SystemExit(bool(failures))
