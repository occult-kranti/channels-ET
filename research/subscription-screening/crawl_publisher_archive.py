#!/usr/bin/env python3
"""Enumerate explicit Magenta Pixie publisher archive links; never request YouTube."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = 'https://www.magentapixie.com/video-archive.html'
ROUTE = re.compile(r'^/video-archive(?:---page-\d+)?\.html$')


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.current = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.current = [attrs['href'], []]
        if tag in ('iframe', 'embed') and attrs.get('src'):
            self.links.append((attrs['src'], 'Embedded video; title not extracted'))
    def handle_data(self, data):
        if self.current is not None: self.current[1].append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append((self.current[0], ' '.join(''.join(self.current[1]).split())))
            self.current = None


def extract(raw, page_url):
    parser = Links(); parser.feed(raw)
    pages, videos = set(), {}
    for href, title in parser.links:
        url = urljoin(page_url, href); p = urlsplit(url)
        if p.hostname == 'www.magentapixie.com' and ROUTE.fullmatch(p.path):
            pages.add('https://www.magentapixie.com' + p.path)
        video_id = None
        if p.hostname in ('www.youtube.com', 'youtube.com', 'www.youtube-nocookie.com'):
            if p.path == '/watch': video_id = parse_qs(p.query).get('v', [None])[0]
            elif any(p.path.startswith(prefix) for prefix in ('/embed/', '/shorts/', '/live/')):
                video_id = p.path.split('/')[2]
        elif p.hostname == 'youtu.be': video_id = p.path.strip('/')
        if video_id and re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            videos.setdefault(video_id, set()).add(title or 'Untitled publisher link')
    return pages, videos


def fetch(url, private):
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = {'url': url, 'checked_at': stamp}
    name = hashlib.sha256(url.encode()).hexdigest()[:20]
    try:
        request = Request(url, headers={'User-Agent': 'ChannelingAtlasResearch/1.0 (+https://github.com/occult-kranti/channels-ET)'})
        with urlopen(request, timeout=40) as response:
            final = urlsplit(response.url)
            if final.hostname != 'www.magentapixie.com' or final.scheme != 'https':
                raise ValueError('Publisher redirect left declared source host')
            raw = response.read(5_000_001)
            if len(raw) > 5_000_000: raise ValueError('Publisher HTML exceeds bounded response size')
            if 'text/html' not in response.headers.get('Content-Type', ''): raise ValueError('Expected publisher HTML')
            receipt.update(http_status=response.status, final_url=response.url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), status='retrieved')
        (private / (name + '.html')).write_bytes(raw)
        pages, videos = extract(raw.decode('utf-8', errors='replace'), url)
    except Exception as exc:
        receipt.update(status='failed', error=f'{type(exc).__name__}: {str(exc)[:250]}')
        pages, videos = set(), {}
    (private / (name + '.receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt, pages, videos


def crawl(private, output, replay=False):
    repo = Path(__file__).resolve().parents[2]
    if private.resolve().is_relative_to(repo): raise ValueError('Raw publisher pages must remain private')
    if not replay: private.mkdir(parents=True, exist_ok=False)
    pending, visited, sources, records = {ROOT}, set(), [], {}
    def collect(receipt, pages, videos):
        sources.append(receipt)
        for video_id, titles in videos.items():
            row = records.setdefault(video_id, {'video_id': video_id, 'url': 'https://www.youtube.com/watch?v=' + video_id, 'publisher_page_urls': set(), 'publisher_link_labels': set()})
            row['publisher_page_urls'].add(receipt['url']); row['publisher_link_labels'].update(titles)
    if replay:
        receipts = sorted(private.glob('*.receipt.json'))
        if not receipts: raise ValueError('Replay needs retained retrieval receipts')
        linked_pages = set()
        for path in receipts:
            receipt = json.loads(path.read_text()); visited.add(receipt['url'])
            if receipt['status'] == 'retrieved':
                raw = path.with_name(path.name.replace('.receipt.json', '.html')).read_bytes()
                if hashlib.sha256(raw).hexdigest() != receipt['sha256'] or len(raw) != receipt['bytes']:
                    raise ValueError('Retained publisher page binding changed')
                pages, videos = extract(raw.decode('utf-8', errors='replace'), receipt['url'])
            else: pages, videos = set(), {}
            linked_pages.update(pages); collect(receipt, pages, videos)
        if linked_pages - visited: raise ValueError('Reparsed archive exposes unvisited pages; explicit follow-up needed')
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            while pending:
                batch = sorted(pending); pending = set(); visited.update(batch)
                for receipt, pages, videos in pool.map(lambda url: fetch(url, private), batch):
                    collect(receipt, pages, videos)
                    pending.update(pages - visited)
    rows = [{**r, 'publisher_page_urls': sorted(r['publisher_page_urls']), 'publisher_link_labels': sorted(r['publisher_link_labels']), 'duration_seconds': None, 'youtube_uploader_reverified': False, 'downloaded_from_youtube': False} for r in records.values()]
    result = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(), 'publisher': 'Magenta Pixie', 'channel_id': 'magentapixie', 'seed_url': ROOT, 'method': 'Follow only explicitly linked video-archive pages on the publisher host; extract watch/embed/short-link IDs from retained HTML. Two concurrent ordinary HTTPS requests, no YouTube media requests.', 'source_pages': sources, 'counts': {'explicit_archive_pages_discovered': len(visited), 'archive_pages_retrieved': sum(s['status'] == 'retrieved' for s in sources), 'unique_youtube_ids_linked': len(rows), 'youtube_uploads_total': None, 'youtube_media_downloaded_this_crawl': 0}, 'videos': sorted(rows, key=lambda r: r['video_id']), 'limitations': ['The publisher archive is a finite linked frame, not a current YouTube channel census.', 'Dead, private, deleted, reposted or differently attributed videos have not been resolved through YouTube.', 'Publisher anchor labels are not verified YouTube titles. Duration, upload date and exact speaker identity remain unknown.', 'No non-Bashar duration minimum; unknown duration does not exclude discovery records.']}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    result['method'] += ' Recognizes /shorts/ and /live/ as well as watch/embed/youtu.be links; non-Bashar Shorts remain in discovery.'
    result['replayed_from_retained_pages'] = replay
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (private / ('parser-replay-manifest.json' if replay else 'manifest.json')).write_text(json.dumps({'public_output': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'counts': result['counts']}, indent=2) + '\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--private', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--replay', action='store_true', help='Reparse hash-verified retained HTML without network requests')
    a = p.parse_args(); crawl(a.private, a.output, a.replay)
