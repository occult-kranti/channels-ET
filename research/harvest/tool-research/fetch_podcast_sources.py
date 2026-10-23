#!/usr/bin/env python3
"""Screen indexed podcast shows through their Apple-catalog publisher RSS links.

Metadata only. No YouTube requests, audio download, proxy change or TLS override.
Keyword candidates are not accepted episode identities until manually screened.
"""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
INDEX = R / 'research/deep/repo_raw/data/podcasts.json'
NS = {'i': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'channels-ET-research/1.0 public podcast source audit'})
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(16 * 1024 * 1024)
        return raw, response.status, response.url


def collect(job):
    ident, original_rows = job
    row = {'catalog_collection_id': int(ident), 'original_index_rows': original_rows,
           'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'tls_verification': True, 'proxy': 'inherited_session_configuration'}
    try:
        url = 'https://itunes.apple.com/lookup?id=' + ident + '&entity=podcast'
        raw, code, final = get(url)
        (H / 'source-cache' / ('apple-extra-' + ident)).write_bytes(raw)
        catalog = json.loads(raw)['results']
        assert len(catalog) == 1 and str(catalog[0]['collectionId']) == ident
        item = catalog[0]
        row['catalog'] = {k: item.get(k) for k in ['collectionId', 'collectionName', 'artistName', 'feedUrl', 'collectionViewUrl']}
        row['catalog_receipt'] = {'url': url, 'http_status': code, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        raw, code, final = get(item['feedUrl'])
        (H / 'source-cache' / ('feed-extra-' + ident)).write_bytes(raw)
        channel = ET.fromstring(raw).find('channel')
        row['feed_receipt'] = {'url': item['feedUrl'], 'final_url': final, 'http_status': code,
                               'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        row.update(status='retrieved', feed_title=channel.findtext('title'), feed_link=channel.findtext('link'),
                   feed_author=channel.findtext('i:author', namespaces=NS), copyright=channel.findtext('copyright'))
        episodes = channel.findall('item')
        row['item_count'] = len(episodes)
        candidates = []
        for n, ep in enumerate(episodes):
            title = ep.findtext('title', '')
            if not re.search(r'\b(?:Darr?yl\s+Anka|Bashar)\b', title, re.I):
                continue
            enclosure = ep.find('enclosure')
            candidates.append({'feed_item_index': n, 'title': title, 'guid': ep.findtext('guid'), 'link': ep.findtext('link'),
                               'pub_date': ep.findtext('pubDate'), 'duration': ep.findtext('i:duration', namespaces=NS),
                               'episode_number': ep.findtext('i:episode', namespaces=NS),
                               'enclosure': dict(enclosure.attrib) if enclosure is not None else None,
                               'description_excerpt': re.sub('<[^>]+>', ' ', ep.findtext('description', ''))[:350]})
        row['candidate_episodes'] = candidates
    except Exception as error:
        row.update(status='failed', error_type=type(error).__name__, error=str(error)[:300])
    return row


if __name__ == '__main__':
    index = json.loads(INDEX.read_text())
    already = {'988576741', '1349934168', '1435178031', '1841496060', '1560904383', '1465014169'}
    jobs = {}
    excluded = []
    for n, item in enumerate(index):
        if re.search(r'unofficial|re-upload|third-party.*re-distribut', item['show'] + ' ' + item.get('description', ''), re.I):
            excluded.append({'original_index_row': n, 'show': item['show'], 'reason': 'explicitly indexed unofficial redistribution; excluded from original-publisher acquisition'})
            continue
        match = re.search(r'/id(\d+)', item.get('apple_url') or '')
        if match and match[1] not in already:
            jobs.setdefault(match[1], []).append(n)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(collect, jobs.items()))
    result = {'source_index_path': str(INDEX.relative_to(R)), 'source_index_sha256': hashlib.sha256(INDEX.read_bytes()).hexdigest(),
              'scope': 'Additional original-index catalog/feed metadata only; exact episode identity still needs screening.',
              'excluded_sources': excluded, 'records': records}
    (H / 'podcast-additional-receipts.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{'id': r['catalog_collection_id'], 'status': r['status'], 'feed_title': r.get('feed_title'),
                       'items': r.get('item_count'), 'candidates': r.get('candidate_episodes'), 'error': r.get('error')} for r in records], indent=2))
