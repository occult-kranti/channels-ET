#!/usr/bin/env python3
"""Bounded, replayable first-party indexing. Never requests a YouTube endpoint."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET
from urllib.robotparser import RobotFileParser

USER_AGENT = 'ChannelingAtlasResearch/1.0 (+https://github.com/occult-kranti/channels-ET)'
VIDEO = re.compile(r'^[A-Za-z0-9_-]{11}$')
UC = re.compile(r'^UC[A-Za-z0-9_-]{22}$')
YT_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com', 'youtu.be', 'www.youtu.be'}
BAD = re.compile(r'\.(?:pdf|zip|mp[34]|wav|ogg|webm|jpg|jpeg|png|svg|gif|woff2?|css|js)(?:$|\?)', re.I)
SKIP = re.compile(r'/(?:cart|checkout|my-account|wp-admin|wp-json|comments|tag|author|product|shop|store|login|register|privacy|terms)(?:/|$)', re.I)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
def bind(path):
    raw = path.read_bytes(); return {'file': path.name, 'bytes': len(raw), 'sha256': sha(raw)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.links = []; self.title = []; self.in_title = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title': self.in_title = True
        for key in ('href', 'src', 'data-src', 'data-video-url', 'data-url'):
            if attrs.get(key): self.links.append((attrs[key], tag + ':' + key))
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, value):
        if self.in_title: self.title.append(value)


def youtube_identity(url):
    p = urlsplit(html.unescape(url)); host = (p.hostname or '').lower()
    if p.scheme not in {'https', 'http'} or host not in YT_HOSTS: return None
    parts = [x for x in p.path.split('/') if x]
    value = None
    if host in {'youtu.be', 'www.youtu.be'} and parts: value = parts[0]
    elif p.path == '/watch': value = parse_qs(p.query).get('v', [None])[0]
    elif len(parts) >= 2 and parts[0] in {'embed', 'shorts', 'live', 'v'}: value = parts[1]
    if value and VIDEO.fullmatch(value) and value != 'videoseries':
        return 'video', value, 'https://www.youtube.com/watch?v=' + value
    if len(parts) >= 2 and parts[0] == 'channel' and UC.fullmatch(parts[1]):
        return 'channel', parts[1], 'https://www.youtube.com/channel/' + parts[1]
    if parts and parts[0].startswith('@') and re.fullmatch(r'@[A-Za-z0-9_.-]+', parts[0]):
        return 'handle', parts[0], 'https://www.youtube.com/' + parts[0]
    if len(parts) >= 2 and parts[0] in {'user', 'c'} and re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1]):
        return 'legacy_account', '/'.join(parts[:2]), 'https://www.youtube.com/' + '/'.join(parts[:2])
    return None


def extract(raw, page_url, content_type=''):
    text = raw.decode('utf-8', errors='replace'); parser = Links(); parser.feed(text)
    links = list(parser.links)
    # JSON-escaped URLs are explicit publisher mentions, not inferred video ownership.
    normalized = html.unescape(text.replace('\\/', '/').replace('\\u0026', '&'))
    for m in re.finditer(r'(?:https?:)?//(?:www\.|m\.)?(?:youtube(?:-nocookie)?\.com|youtu\.be)/[^\s<>"\'\\]+', normalized):
        links.append((m.group(), 'explicit_url_in_publisher_markup'))
    xml_status = None
    if 'xml' in content_type or text.lstrip().startswith('<?xml'):
        try:
            xml = ET.fromstring(raw); xml_status = xml.tag.split('}')[-1]
            for node in xml.iter():
                name = node.tag.split('}')[-1]
                if name in {'loc', 'link', 'player_loc', 'content_loc'} and node.text:
                    links.append((node.text.strip(), 'xml:' + name))
                if name in {'enclosure', 'link'}:
                    for key in ('url', 'href'):
                        if node.get(key): links.append((node.get(key), 'xml:' + name + ':' + key))
                # Feed descriptions contain escaped first-party embed markup.
                if name in {'description', 'encoded', 'content'} and node.text:
                    nested = Links(); nested.feed(node.text); links.extend(nested.links)
        except ET.ParseError: xml_status = 'invalid_xml'
    if urlsplit(page_url).path == '/robots.txt':
        for match in re.finditer(r'^Sitemap:\s*(https?://\S+)', text, re.I | re.M):
            links.append((match.group(1), 'robots:sitemap'))
    mentions = {}; resolved = set(); media = set()
    for href, kind in links:
        url = urljoin(page_url, href.strip()); ident = youtube_identity(url)
        if ident:
            typ, value, canonical = ident
            entry = mentions.setdefault((typ, value), {'kind': typ, 'identity': value, 'url': canonical, 'evidence_kinds': set()})
            entry['evidence_kinds'].add(kind)
        else:
            p = urlsplit(url)
            if p.scheme in {'http', 'https'} and p.hostname:
                resolved.add(urlunsplit((p.scheme, p.netloc.lower(), p.path or '/', p.query, '')))
                if re.search(r'\.(?:mp3|m4a|ogg|opus|wav|vtt|srt|pdf)(?:$|\?)', url, re.I): media.add(url)
    return {'title': ' '.join(' '.join(parser.title).split())[:240],
            'mentions': [{**m, 'evidence_kinds': sorted(m['evidence_kinds'])} for m in mentions.values()],
            'links': sorted(resolved), 'xml_root': xml_status, 'linked_media_or_transcripts': sorted(media)}


def permitted(url, publisher):
    p = urlsplit(url)
    return p.scheme in {'http', 'https'} and p.hostname in publisher['allowed_hosts'] and not p.username and not p.password


def fetch(url, publisher, work):
    receipt = {'publisher_id': publisher['publisher_id'], 'url': url, 'retrieved_at': stamp(), 'redirect_chain': []}
    key = sha((publisher['publisher_id']+'\n'+url).encode())[:24]
    current = url; start = time.monotonic(); opener = build_opener(NoRedirect)
    try:
        for _ in range(5):
            if not permitted(current, publisher): raise ValueError('Redirect leaves declared publisher hosts')
            parts = urlsplit(current)
            wire_url = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe='/%:@'),
                                  quote(parts.query, safe='=&%/:?@+;,'), ''))
            try:
                response = opener.open(Request(wire_url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'}), timeout=18)
            except HTTPError as exc:
                if exc.code in {301, 302, 303, 307, 308} and exc.headers.get('Location'):
                    target = urljoin(current, exc.headers['Location']); receipt['redirect_chain'].append({'from': current, 'status': exc.code, 'to': target})
                    current = target; continue
                receipt['http_status'] = exc.code
                errbody = exc.read(2000); receipt['error_body_prefix_sha256'] = sha(errbody)
                raise
            with response:
                content_type = response.headers.get('Content-Type', '')
                if not any(s in content_type.lower() for s in ('html', 'xml', 'text/plain', 'application/json')):
                    raise ValueError('Non-document content type: '+content_type)
                raw = response.read(6_000_001)
                if len(raw) > 6_000_000: raise ValueError('Per-page resource budget exceeded')
                receipt.update(status='retrieved', http_status=response.status, final_url=current, content_type=content_type,
                               bytes=len(raw), sha256=sha(raw), artifact_file='pages/'+key+'.bin')
                (work/receipt['artifact_file']).write_bytes(raw)
                parsed = extract(raw, current, content_type)
                receipt.update(title=parsed['title'], xml_root=parsed['xml_root'])
                break
        else: raise ValueError('Redirect count exceeded')
    except Exception as exc:
        receipt.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:300], final_url=current)
        parsed = {'mentions': [], 'links': []}
    receipt['elapsed_seconds'] = time.monotonic()-start
    return receipt, parsed


def follow(url, kind, depth, publisher):
    if not permitted(url, publisher) or BAD.search(url) or SKIP.search(urlsplit(url).path): return False
    query = parse_qs(urlsplit(url).query)
    if set(query) - {'page', 'paged', 'start', 'offset'}: return False
    if depth > publisher['max_depth']: return False
    if any(re.search(pattern, url, re.I) for pattern in publisher.get('excluded_path_patterns', [])): return False
    path = urlsplit(url).path
    if re.search(r'(?:sitemap|/feed/?$|\.rss$|/rss/?$)', path, re.I): return True
    return any(re.search(pattern, path, re.I) for pattern in publisher['follow_path_patterns'])


def run(config_path, output, max_pages, seconds, replay=None, reuse=None, retry_failed=False, max_source_bytes=512_000_000):
    if output.exists(): raise ValueError('Use a fresh immutable output directory')
    config = json.loads(config_path.read_text()); publishers = {p['publisher_id']: p for p in config['publishers']}
    output.mkdir(parents=True); (output/'pages').mkdir()
    executed_code = Path(__file__).read_bytes(); (output/'executed-publisher_discovery.py').write_bytes(executed_code)
    started = stamp(); monotonic = time.monotonic(); receipts = []; observations = {}; accounts = {}; visited = set(); queued = set()
    pending = []; robots = {}; excluded = Counter(); paired_pages = []
    for p in publishers.values():
        for url in p['seed_urls']:
            if not permitted(url, p): raise ValueError('Seed outside publisher boundary')
        u = urlsplit(p['seed_urls'][0]); robots_url = urlunsplit((u.scheme, u.netloc, '/robots.txt', '', ''))
        pending.append((p['publisher_id'], robots_url, 0, None)); queued.add((p['publisher_id'], robots_url))
    replay_lookup = {}; cache = replay or reuse
    if replay and reuse: raise ValueError('Choose offline replay or partial verified-cache reuse')
    if retry_failed and not reuse: raise ValueError('Failed-receipt retry requires a declared cache parent')
    if cache:
        previous = json.loads((cache/'discovery-private.json').read_text())
        if previous['config_binding']['sha256'] != bind(config_path)['sha256']: raise ValueError('Cache configuration differs')
        replay_lookup = {(r['publisher_id'], r['url']): r for r in previous['page_receipts']}
    stop = 'declared_queue_exhausted'
    while pending:
        if len(receipts) >= max_pages or time.monotonic()-monotonic >= seconds or sum(r.get('bytes',0) for r in receipts) >= max_source_bytes:
            stop = 'finite_execution_budget_reached'; break
        size = min(2, max_pages-len(receipts)); batch = pending[:size]; pending = pending[size:]
        def one(item):
            pid, url, depth, parent = item
            if replay and (pid,url) not in replay_lookup: raise ValueError('Replay missing a visited receipt')
            if (pid,url) in replay_lookup and not (retry_failed and replay_lookup[pid,url]['status']=='failed'):
                rec = dict(replay_lookup[pid, url])
                if rec['status'] == 'retrieved':
                    raw = (cache/rec['artifact_file']).read_bytes()
                    if sha(raw) != rec['sha256'] or len(raw) != rec['bytes']: raise ValueError('Replay source bytes changed')
                    (output/rec['artifact_file']).write_bytes(raw)
                    parsed = extract(raw, rec['final_url'], rec['content_type'])
                else: parsed = {'mentions': [], 'links': []}
                rec['reused_verified_receipt'] = True
            else: rec, parsed = fetch(url, publishers[pid], output)
            rec.update(depth=depth, discovered_from=parent)
            return rec, parsed
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(one, batch))
        for rec, parsed in results:
            pid = rec['publisher_id']; visited.add((pid, rec['url'])); receipts.append(rec)
            if urlsplit(rec['url']).path == '/robots.txt':
                policy = RobotFileParser(); policy.set_url(rec['url'])
                if rec['status'] == 'retrieved':
                    policy.parse((output/rec['artifact_file']).read_text(errors='replace').splitlines())
                elif rec.get('http_status') == 404: policy.allow_all = True
                else: policy.disallow_all = True
                robots[pid] = policy
                rec['robots_policy'] = 'parsed' if rec['status']=='retrieved' else 'allow_after_404' if rec.get('http_status')==404 else 'held_after_unavailable_policy'
                for url in publishers[pid]['seed_urls']:
                    if policy.can_fetch(USER_AGENT, url):
                        if (pid,url) not in queued:
                            pending.append((pid,url,0,rec['url']));queued.add((pid,url))
                    else: excluded['robots_disallowed_or_unavailable'] += 1
            for mention in parsed['mentions']:
                target = observations if mention['kind'] == 'video' else accounts
                key = (pid, mention['kind'], mention['identity'])
                row = target.setdefault(key, {'publisher_id': pid, **mention, 'evidence': []})
                row['evidence'].append({'page_url': rec['url'], 'final_url': rec['final_url'], 'page_sha256': rec['sha256'],
                                        'retrieved_at': rec['retrieved_at'], 'evidence_kinds': mention['evidence_kinds']})
            accepted = []
            if parsed['mentions'] and parsed.get('linked_media_or_transcripts'):
                paired_pages.append({'publisher_id':pid,'page_url':rec['url'],'page_sha256':rec['sha256'],
                                     'youtube_ids':sorted(m['identity'] for m in parsed['mentions'] if m['kind']=='video'),
                                     'linked_media_or_transcripts':parsed['linked_media_or_transcripts'],
                                     'identity_scope':'Co-occurrence on publisher page only; equivalence and item-level relationship require manual review.'})
            for url in parsed['links']:
                if follow(url, None, rec['depth']+1, publishers[pid]):
                    if not robots[pid].can_fetch(USER_AGENT,url):
                        excluded['robots_disallowed_or_unavailable'] += 1; continue
                    accepted.append(url)
                    if (pid, url) not in queued:
                        pending.append((pid, url, rec['depth']+1, rec['url'])); queued.add((pid, url))
                elif permitted(url,publishers[pid]):
                    excluded['same_publisher_depth_or_path_outside_declared_scope'] += 1
            rec['eligible_links'] = accepted
            rec['youtube_video_ids'] = sorted(m['identity'] for m in parsed['mentions'] if m['kind'] == 'video')
            rec['terminal_in_declared_scope'] = rec['status']=='retrieved' and rec.get('xml_root')!='invalid_xml' and not accepted
        if len(receipts) % 20 == 0 or not pending:
            print(json.dumps({'pages': len(receipts), 'publisher_video_associations': len(observations), 'unique_video_ids': len({k[2] for k in observations}), 'queued_pages': len(pending)}), flush=True)
        if not replay and any(not rec.get('reused_verified_receipt') for rec,_ in results): time.sleep(0.7)
    data = {'schema_version': 1, 'status': stop, 'started_at': started, 'completed_at': stamp(),
            'config_binding': bind(config_path), 'script_sha256': sha(executed_code),
            'execution_limits': {'max_pages':max_pages,'soft_wall_seconds':seconds,'soft_source_bytes':max_source_bytes,
                                 'per_response_bytes':6_000_000,'max_workers':2,'network_batch_pause_seconds':0.7},
            'cache_parent_sha256': sha((cache/'discovery-private.json').read_bytes()) if cache else None,
            'time_cutoff_scope': 'Publisher pages as retrieved at recorded timestamps; individual upload dates not inferred.',
            'counts': {'pages_attempted': len(receipts), 'pages_retrieved': sum(r['status']=='retrieved' for r in receipts),
                       'publisher_video_associations': len(observations), 'distinct_video_ids': len({k[2] for k in observations}),
                       'account_link_associations': len(accounts), 'pages_pending': len(pending), 'youtube_requests': 0, 'media_downloads': 0},
            'verified_cached_receipts_reused': sum(r.get('reused_verified_receipt',False) for r in receipts),
            'scope_exclusions': dict(excluded), 'failed_pages': sum(r['status']=='failed' for r in receipts),
            'invalid_xml_pages': sum(r.get('xml_root')=='invalid_xml' for r in receipts),
            'paired_publisher_media_leads': paired_pages,
            'page_receipts': receipts, 'videos': sorted(observations.values(), key=lambda x:(x['publisher_id'],x['identity'])),
            'account_links': sorted(accounts.values(), key=lambda x:(x['publisher_id'],x['identity'])),
            'pending': [{'publisher_id': a, 'url': b, 'depth': c, 'discovered_from': d} for a,b,c,d in pending],
            'publisher_scopes': list(publishers.values()),
            'limitations': ['First-party embedded/linked IDs are discovery observations, not upload ownership, availability, complete channel enumeration, downloaded audio or analyzed text.',
                            'A linked-scope terminal page is not evidence of a terminal YouTube uploads playlist.',
                            'No duration or video-count filter applied to discovery; Bashar minimum duration belongs to later acquisition eligibility.',
                            'Only listed publisher hosts and path/depth rules were followed. Budget stops and pending URLs remain explicit.',
                            'No direct alternate publisher audio was downloaded or substituted for YouTube media.']}
    write(output/'discovery-private.json',data)
    public = dict(data); public['page_receipts'] = [{k:v for k,v in r.items() if k not in {'artifact_file'}} for r in receipts]
    write(output/'publisher-discovery.json',public)
    write(output/'output-manifest.json',{'schema_version':1,'public_allowlist':[bind(output/'publisher-discovery.json')]})
    print(json.dumps(data['counts']),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--max-pages',type=int,default=600)
    p.add_argument('--seconds',type=float,default=900);p.add_argument('--replay',type=Path);p.add_argument('--reuse',type=Path)
    p.add_argument('--retry-failed',action='store_true')
    p.add_argument('--max-source-bytes',type=int,default=512_000_000)
    a=p.parse_args();run(a.config,a.output,a.max_pages,a.seconds,a.replay,a.reuse,a.retry_failed,a.max_source_bytes)
