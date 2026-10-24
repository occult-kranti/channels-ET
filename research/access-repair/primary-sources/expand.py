#!/usr/bin/env python3
"""Two explicitly authorized publisher-linked requests and local RSS extraction.

No audio acquisition, YouTube requests, retries, cookies or alternate egress.
All full documents and extracted text are kept outside Git.
"""
import datetime
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
RAW = pathlib.Path('/workspace/channels-et-raw/primary-publications')
CAP = 16 * 1024 * 1024
spec = importlib.util.spec_from_file_location('primary_fetch', H / 'fetch.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
metadata = json.loads((H / 'metadata.json').read_text())
prior = {x['source_id']: x for x in metadata['records']}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save_private(name, raw):
    path = RAW / name
    with path.open('xb') as stream:
        stream.write(raw)
    return {'raw_local_path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def get(ident, url, suffix, source):
    row = {'source_id': ident, 'requested_url': url, 'attempted_at': now(), 'source_link_provenance': source,
           'proxy_configuration': 'inherited_session_configuration', 'tls_certificate_verification_enabled': True,
           'network_attempts': 1, 'retry': False, 'audio_or_video_edition_equivalence_verified': False,
           'redistribution_license': 'not_established', 'full_text_publicly_rehosted': False}
    try:
        if shutil.disk_usage(RAW).free < 6 * 1024 ** 3:
            raise RuntimeError('Six-GiB free reserve unavailable')
        request = urllib.request.Request(url, headers={'User-Agent': 'channels-ET-research/1.0 explicit-primary-publisher-source'})
        opener = urllib.request.build_opener(f.HTTPSOnly(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(request, timeout=45) as response:
            declared = response.headers.get('Content-Length')
            if declared is not None and int(declared) > CAP:
                raise RuntimeError('Declared publisher document exceeds sixteen-MiB cap')
            raw = response.read(CAP + 1)
            if len(raw) > CAP:
                raise RuntimeError('Publisher document exceeds sixteen-MiB cap')
            if declared is not None and len(raw) != int(declared):
                raise RuntimeError('Incomplete declared publisher document body')
            row.update(status='retrieved', http_status=response.status, content_type=response.headers.get_content_type(),
                       final_url=response.url, response=save_private(ident + suffix, raw))
    except Exception as error:
        row.update(status='failed', error_type=type(error).__name__, error=re.sub(r'https?://\S+', '[endpoint omitted]', str(error))[:350])
        if isinstance(error, urllib.error.HTTPError):
            row.update(http_status=error.code, error_response=save_private(ident + '.error-body', error.read(CAP)))
    row['finished_at'] = now()
    return row


def text_receipt(name, text):
    return {**save_private(name, text.encode('utf-8')), 'word_count': len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", text))}


def main():
    if (H / 'expanded-metadata.json').exists():
        raise SystemExit('Bounded follow-up metadata already exists; no implicit retry')
    pdf_url = 'https://s3.us-east-2.amazonaws.com/pstranscripts/The+Expression+of+the+True+Self.pdf'
    paul = get('paul-birmingham-pdf', pdf_url, '.pdf',
               {'publisher_page_url': prior['paul-birmingham']['requested_url'],
                'publisher_page_sha256': prior['paul-birmingham']['response']['sha256'], 'link_label': 'DOWNLOAD TRANSCRIPT'})
    if paul['status'] == 'retrieved':
        path = pathlib.Path(paul['response']['raw_local_path'])
        try:
            if not path.read_bytes().startswith(b'%PDF-'):
                raise RuntimeError('Publisher response is not PDF magic')
            info = subprocess.run(['pdfinfo', str(path)], capture_output=True, check=True, timeout=45)
            pages = re.search(r'^Pages:\s+(\d+)', info.stdout.decode(), flags=re.M)
            if not pages or int(pages.group(1)) < 1:
                raise RuntimeError('No finite PDF page count')
            result = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, check=True, timeout=45)
            text = result.stdout.decode('utf-8')
            if not text.strip():
                raise RuntimeError('Empty publisher PDF text extraction')
            paul.update(pdf_magic_verified=True, pages=int(pages.group(1)),
                        pdfinfo=save_private('paul-birmingham-pdf.pdfinfo.txt', info.stdout),
                        text=text_receipt('paul-birmingham-pdf.txt', text),
                        title='The Expression of the True Self', session_date='2017-07-15',
                        title_and_date_basis='Explicit official publisher linking page; PDF text separately retained for inspection',
                        source_kind='publisher_issued_spiritual_Guides_transcript',
                        scope='Spiritual mediumship comparison source, not biological ET; publisher transcript has not been checked against the recording',
                        human_transcription_or_speaker_accuracy_verified=False)
        except Exception as error:
            paul.update(document_validation_status='failed', document_validation_error=str(error)[:350])
    feed_url = 'https://feed.podbean.com/athinakrol/feed.xml'
    athina = get('athina-feed', feed_url, '.rss',
                 {'publisher_page_url': prior['athina-ashtar']['requested_url'],
                  'publisher_page_sha256': prior['athina-ashtar']['response']['sha256'],
                  'link_relation': 'Explicit application/rss+xml alternate link and visible same URL'})
    if athina['status'] == 'retrieved':
        try:
            channel = ET.fromstring(pathlib.Path(athina['response']['raw_local_path']).read_bytes()).find('channel')
            matches = []
            for index, item in enumerate(channel.findall('item')):
                if (item.findtext('link') or '').rstrip('/') != prior['athina-ashtar']['requested_url'].rstrip('/'):
                    continue
                enclosure = item.find('enclosure')
                enc = None
                if enclosure is not None:
                    original = enclosure.get('url', '')
                    parts = urllib.parse.urlsplit(original)
                    enc = {'url': urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, '', '')),
                           'query_values_redacted': bool(parts.query), 'query_keys': sorted(urllib.parse.parse_qs(parts.query)),
                           'type': enclosure.get('type'), 'length_as_published': enclosure.get('length'), 'requested': False}
                matches.append({'feed_item_index': index, 'title': item.findtext('title'), 'guid': item.findtext('guid'),
                                'link': item.findtext('link'), 'publication_timestamp': item.findtext('pubDate'),
                                'duration_as_published': item.findtext('{http://www.itunes.com/dtds/podcast-1.0.dtd}duration'),
                                'enclosure': enc, 'match_method': 'Exact indexed creator-episode URL, excluding trailing slash only'})
            athina.update(feed_title=channel.findtext('title'), publisher_site=channel.findtext('link'),
                          publisher_author=channel.findtext('{http://www.itunes.com/dtds/podcast-1.0.dtd}author'),
                          feed_item_count=len(channel.findall('item')), exact_episode_matches=matches,
                          unique_exact_episode_present=len(matches) == 1, audio_acquired=False)
        except Exception as error:
            athina.update(feed_validation_status='failed', feed_validation_error=str(error)[:350])
    # This feed was already saved by the first request. No additional fetch.
    feed_raw = pathlib.Path(prior['daniel-feed']['response']['raw_local_path']).read_bytes()
    if sha(feed_raw) != prior['daniel-feed']['response']['sha256']:
        raise RuntimeError('Previously saved Daniel RSS hash changed')
    channel = ET.fromstring(feed_raw).find('channel')
    items = []
    for index, item in enumerate(channel.findall('item')):
        rendered = f.Page()
        html = item.findtext('content:encoded', namespaces=f.NS) or item.findtext('description') or ''
        rendered.feed(html)
        text = '\n'.join(rendered.text)
        guid = item.findtext('guid')
        filename = 'daniel-item-' + str(index).zfill(2) + '-' + sha((guid or item.findtext('link') or str(index)).encode())[:12] + '.txt'
        items.append({'item_index': index, 'title': item.findtext('title'), 'guid': guid, 'url': item.findtext('link'),
                      'publication_timestamp': item.findtext('pubDate'), 'creator': item.findtext('dc:creator', namespaces=f.NS),
                      'categories_as_published': [c.text for c in item.findall('category')], 'audio_enclosures': len(item.findall('enclosure')),
                      'text': text_receipt(filename, text),
                      'promotion_terms_present_heuristic': bool(re.search(r'\b(register|buy|book|course|session|healing event)\b', text, re.I)),
                      'rendered_text_mentions_video_heuristic': bool(re.search(r'watch me channel|click the pic|youtube|video', text, re.I)),
                      'content_scope': 'Full publisher RSS item rendered text includes any title, attributed message, promotions and footer; no semantic message separation or audiovisual alignment verified',
                      'entity_origin_or_transcription_accuracy_verified': False})
    output = {'schema_version': 1, 'recorded_at': now(), 'collector_sha256': sha(pathlib.Path(__file__).read_bytes()),
              'original_fetch_metadata_sha256': sha((H / 'metadata.json').read_bytes()),
              'new_network_requests': 2, 'cumulative_publisher_network_requests': 5,
              'youtube_requests': 0, 'audio_acquisitions': 0, 'fixed_nineteen_episode_study_changed': False,
              'paul': paul, 'athina': athina,
              'daniel': {'source_feed_sha256': sha(feed_raw), 'source_feed_url': prior['daniel-feed']['requested_url'],
                         'new_network_requests': 0, 'items_extracted': len(items),
                         'total_rendered_item_words': sum(x['text']['word_count'] for x in items), 'items': items}}
    (H / 'expanded-metadata.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'paul': {k: paul.get(k) for k in ['status', 'http_status', 'pages', 'document_validation_error']},
                      'athina': {k: athina.get(k) for k in ['status', 'http_status', 'unique_exact_episode_present', 'feed_item_count']},
                      'daniel_items': len(items), 'daniel_rendered_words': output['daniel']['total_rendered_item_words']}, indent=2))


if __name__ == '__main__':
    main()
