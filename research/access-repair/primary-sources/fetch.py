#!/usr/bin/env python3
"""One ordinary HTTPS request for each of three explicit publisher leads.

Full source bodies and text remain outside Git. No retry, cookies, alternative
egress, YouTube request or audio acquisition is performed.
"""
import datetime
import hashlib
import html.parser
import json
import pathlib
import re
import shutil
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

R = pathlib.Path(__file__).resolve().parents[3]
H = pathlib.Path(__file__).resolve().parent
RAW = pathlib.Path('/workspace/channels-et-raw/primary-publications')
SOURCE = R / 'research/harvest/inventory/sourcepins/channels-ET/dist/data.json'
CAP = 8 * 1024 * 1024
NS = {'content': 'http://purl.org/rss/1.0/modules/content/',
      'dc': 'http://purl.org/dc/elements/1.1/'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.entry = []
        self.titles = []
        self.h1 = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == 'a' and attr.get('href'):
            self.links.append({'href': attr['href'], 'text': ''})
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append((tag, attr.get('class', '')))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        data = re.sub(r'\s+', ' ', data).strip()
        if not data:
            return
        tags = {t for t, _ in self.stack}
        if 'title' in tags:
            self.titles.append(data)
        if 'h1' in tags:
            self.h1.append(data)
        if tags.intersection({'script', 'style', 'noscript', 'head'}):
            return
        self.text.append(data)
        if any('entry-content' in classes.split() for _, classes in self.stack):
            self.entry.append(data)
        if 'a' in tags and self.links:
            self.links[-1]['text'] += (' ' if self.links[-1]['text'] else '') + data


class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise RuntimeError('Non-HTTPS publisher redirect refused')
        return super().redirect_request(request, fp, code, message, headers, newurl)


def private_file(ident, suffix, body):
    path = RAW / (ident + suffix)
    with path.open('xb') as stream:
        stream.write(body)
    return {'raw_local_path': str(path), 'bytes': len(body), 'sha256': digest(body)}


def text_receipt(ident, text, scope):
    body = text.encode('utf-8')
    return {**private_file(ident, '.txt', body), 'word_count': len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", text)),
            'text_scope': scope, 'human_transcription_or_accuracy_verified': False}


def main():
    if (H / 'metadata.json').exists():
        raise SystemExit('One-attempt metadata already exists; no implicit retry permitted')
    RAW.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(RAW).free < 6 * 1024 ** 3:
        raise SystemExit('Six-GiB free reserve unavailable')
    sources = json.loads(SOURCE.read_text())['sources']
    jobs = [
        ('daniel-feed', 'https://danielscranton.com/feed/', [52, 53]),
        ('paul-birmingham', sources[131]['url'], [128, 131]),
        ('athina-ashtar', sources[34]['url'], [34, 35, 37]),
    ]
    records = []
    for ident, url, pointers in jobs:
        row = {'source_id': ident, 'requested_url': url, 'attempted_at': now(),
               'source_pointers': [{'path': str(SOURCE.relative_to(R)), 'json_pointer': '/sources/' + str(i),
                                    'source_id': sources[i]['id'], 'sha256': digest(SOURCE.read_bytes())} for i in pointers],
               'source_kind': 'independent_original_publisher_text_or_episode_page',
               'proxy_configuration': 'inherited_session_configuration', 'tls_certificate_verification_enabled': True,
               'network_attempts': 1, 'retry': False, 'audio_or_video_edition_equivalence_verified': False,
               'redistribution_license': 'not_established', 'full_text_publicly_rehosted': False}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'channels-ET-research/1.0 primary-publisher-source-inspection'})
            opener = urllib.request.build_opener(HTTPSOnly(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            with opener.open(request, timeout=45) as response:
                raw = response.read(CAP + 1)
                if len(raw) > CAP:
                    raise RuntimeError('Publisher text response exceeds eight-MiB cap')
                row.update(status='retrieved', http_status=response.status, content_type=response.headers.get_content_type(),
                           final_url=response.url, response=private_file(ident, '.body', raw))
            if ident == 'daniel-feed':
                channel = ET.fromstring(raw).find('channel')
                row.update(feed_title=channel.findtext('title'), publisher_site=channel.findtext('link'),
                           feed_item_count=len(channel.findall('item')))
                exact = [x for x in channel.findall('item') if x.findtext('guid') == 'https://danielscranton.com/?p=385080']
                if len(exact) != 1:
                    row['exact_previously_identified_item_status'] = 'not_uniquely_present_in_current_feed'
                else:
                    item = exact[0]
                    page = Page()
                    page.feed(item.findtext('content:encoded', namespaces=NS) or item.findtext('description') or '')
                    row.update(title=item.findtext('title'), publication_timestamp=item.findtext('pubDate'),
                               guid=item.findtext('guid'), creator=item.findtext('dc:creator', namespaces=NS),
                               publisher_item_url=item.findtext('link'), exact_previously_identified_item_status='present',
                               text=text_receipt(ident, '\n'.join(page.text), 'publisher RSS item rendered text, including any embedded marketing; not verified speech transcription'),
                               audio_enclosures=len(item.findall('enclosure')))
            else:
                page = Page()
                page.feed(raw.decode('utf-8', errors='replace'))
                row.update(title=' '.join(page.h1) or ' '.join(page.titles), html_title=' '.join(page.titles),
                           text=text_receipt(ident, '\n'.join(page.entry or page.text),
                                             'HTML entry-content text' if page.entry else 'whole visible publisher-page text; includes navigation/boilerplate'))
                links = []
                for link in page.links:
                    absolute = urllib.parse.urljoin(url, link['href'])
                    # Only retain explicit transcript/RSS links. Never follow a
                    # YouTube embed, audio enclosure or signed delivery URL.
                    if urllib.parse.urlsplit(absolute).scheme == 'https' and (
                        re.search(r'transcript|\.pdf(?:$|\?)|(?:/feed/?$)|rss', absolute, re.I)
                        or re.search(r'transcript|rss|podcast feed', link['text'], re.I)
                    ):
                        links.append({'url': absolute, 'label': link['text'], 'followed': False})
                row['explicit_transcript_or_feed_links'] = list({x['url']: x for x in links}.values())
                row['session_date_from_inherited_record'] = '2017-07-15' if ident == 'paul-birmingham' else None
                row['publication_date_from_inherited_record'] = '2023-02-06' if ident == 'athina-ashtar' else None
        except Exception as error:
            row.update(status='failed', error_type=type(error).__name__,
                       error=re.sub(r'https?://\S+', '[endpoint omitted]', str(error))[:350])
            if isinstance(error, urllib.error.HTTPError):
                row['http_status'] = error.code
                row['error_response'] = private_file(ident, '.error-body', error.read(CAP))
        row['finished_at'] = now()
        records.append(row)
    output = {'schema_version': 1, 'recorded_at': now(), 'collector_sha256': digest(pathlib.Path(__file__).read_bytes()),
              'network_requests': len(records), 'youtube_requests': 0, 'new_audio_jobs': 0,
              'fixed_nineteen_episode_study_changed': False, 'records': records}
    (H / 'metadata.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{k: x.get(k) for k in ['source_id', 'status', 'http_status', 'title', 'error']} for x in records], indent=2))


if __name__ == '__main__':
    main()
