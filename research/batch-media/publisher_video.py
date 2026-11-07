#!/usr/bin/env python3
"""Download an explicitly linked independent-publisher video into private storage.

No discovery, account login, proxy replacement, retry loop or YouTube extraction.
A retained publisher page and its hash bind the Download link. An interrupted
transfer can resume only with a pinned partial hash and an unchanged HTTP validator.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener, proxy_bypass

MAX_BYTES = 1_000_000_000
RESERVE = 6 * 1024**3


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.chmod(0o600)
    os.replace(temporary, path)


def private_path(path):
    candidate = Path(path).absolute()
    if any(p.is_symlink() for p in [candidate, *candidate.parents]):
        raise ValueError('Private output cannot use symlinks')
    # Managed /workspace may contain an empty .git placeholder. Reject real
    # repository HEADs and worktree gitdir files, not an empty platform marker.
    for parent in [candidate.parent, *candidate.parents]:
        marker = parent / '.git'
        if (marker.is_dir() and (marker / 'HEAD').is_file()) or (marker.is_file() and marker.stat().st_size < 4096 and marker.read_text().startswith('gitdir:')):
            raise ValueError('Original media and receipts must remain outside Git')
    return candidate


def https_url(value):
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443) or p.fragment:
        raise ValueError('Expected a credential-free HTTPS URL without fragment')
    if any(p.hostname == d or p.hostname.endswith('.' + d) for d in ('youtube.com', 'youtu.be', 'youtube-nocookie.com', 'googlevideo.com')):
        raise ValueError('This independent publisher adapter does not fetch YouTube or its media')
    return p


class DownloadLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'download' in attrs and attrs.get('href'):
            self.links.add(attrs['href'])


def validate_link(source_page, source_sha256, source_url, media_url):
    https_url(source_url)
    parsed = https_url(media_url)
    if parsed.path.lower().rsplit('.', 1)[-1] not in ('mp4', 'webm', 'mov', 'mkv'):
        raise ValueError('Only an explicit progressive video download is supported')
    if digest(source_page) != source_sha256:
        raise ValueError('Retained source page changed')
    parser = DownloadLinks()
    parser.feed(Path(source_page).read_text(encoding='utf-8', errors='replace'))
    if media_url not in parser.links:
        raise ValueError('Exact media URL is not an explicit Download link in the retained publisher page')


class SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, hostname):
        self.hostname = hostname

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if https_url(newurl).hostname != self.hostname:
            raise ValueError('Media redirect left the recorded HTTPS host')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def ordinary_opener(media_url):
    host = https_url(media_url).hostname
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not proxy or proxy_bypass(host):
        raise ValueError('This cloud adapter requires the inherited HTTPS proxy; direct fallback is disabled')
    return build_opener(SameHostRedirect(host), ProxyHandler({'https': proxy}), HTTPSHandler(context=ssl.create_default_context()))


def inspect_video(path, max_height=720):
    try:
        result = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration:stream=codec_type,codec_name,width,height', '-of', 'json', str(path)
        ], text=True, stderr=subprocess.PIPE, timeout=60))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise ValueError('ffprobe could not decode and validate the downloaded video') from error
    duration = float(result.get('format', {}).get('duration', 0))
    streams = result.get('streams', [])
    if not math.isfinite(duration) or duration < 300:
        raise ValueError('Video duration must be at least 300 seconds')
    if not all(any(s.get('codec_type') == kind for s in streams) for kind in ('video', 'audio')):
        raise ValueError('Complete video must contain both audio and video streams')
    videos = [s for s in streams if s.get('codec_type') == 'video']
    if any(not isinstance(s.get('height'), int) or not 1 <= s['height'] <= max_height for s in videos):
        raise ValueError('Decoded video height exceeds the declared bound or is unavailable')
    return {'ffprobe_duration_seconds': duration, 'streams': streams, 'max_height': max_height}


def download(*, source_page, source_sha256, source_url, media_url, target,
             source_id, medium_id, channel_id, max_bytes=MAX_BYTES, reserve_free=RESERVE,
             max_height=720, expected_bytes=None, resume=False, opener=None, verifier=inspect_video):
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError('Per-source bound must be between 1 and 1,000,000,000 bytes')
    if not isinstance(reserve_free, int) or isinstance(reserve_free, bool) or reserve_free < 0:
        raise ValueError('Invalid free-space reserve')
    if expected_bytes is not None and (isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or not 1 <= expected_bytes <= max_bytes):
        raise ValueError('Expected source length must fit the per-source bound')
    if max_height not in (360, 480, 720):
        raise ValueError('Expected a 360, 480 or 720 height bound')
    for field in (source_id, medium_id, channel_id):
        if not isinstance(field, str) or not 1 <= len(field) <= 200 or any(ord(c) < 32 for c in field):
            raise ValueError('A bounded explicit source, medium and channel identity is required')
    validate_link(source_page, source_sha256, source_url, media_url)
    target = private_path(target)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    partial = private_path(target.with_name(target.name + '.partial'))
    state_path = private_path(target.with_name(target.name + '.transfer.json'))
    receipt_path = private_path(target.with_name(target.name + '.receipt.json'))
    binding = {'source_page_sha256': source_sha256, 'source_url': source_url,
               'media_url': media_url, 'local_path': str(target), 'source_id': source_id,
               'medium_id': medium_id, 'channel_id': channel_id, 'provider': 'publisher_video',
               'max_bytes': max_bytes, 'max_height': max_height, 'expected_bytes': expected_bytes}
    if target.exists():
        if not resume or not receipt_path.is_file():
            raise ValueError('Existing target is never overwritten; resume requires its verified receipt')
        old = json.loads(receipt_path.read_text())
        if old.get('binding') != binding or old.get('status') != 'verified' or old.get('sha256') != digest(target) or old.get('bytes') != target.stat().st_size:
            raise ValueError('Existing completed source does not match its exact receipt')
        return {**old, 'current_operation': 'verified_existing_no_network'}
    start = 0
    state = {'binding': binding, 'status': 'pending'}
    if partial.exists() or state_path.exists():
        if not resume or not partial.is_file() or not state_path.is_file():
            raise ValueError('Interrupted files require explicit receipt-bound resume')
        state = json.loads(state_path.read_text())
        if state.get('binding') != binding or state.get('partial_bytes') != partial.stat().st_size or state.get('partial_sha256') != digest(partial):
            raise ValueError('Partial transfer binding or bytes changed')
        if not state.get('validator') or not state.get('total_bytes'):
            raise ValueError('HTTP validator and total length are required to resume')
        start = partial.stat().st_size
        if not 0 < start < state['total_bytes'] <= max_bytes:
            raise ValueError('Invalid partial length')
    origin = urlsplit(source_url)
    headers = {'Referer': f'{origin.scheme}://{origin.netloc}/', 'User-Agent': 'Mozilla/5.0'}
    if start:
        headers.update({'Range': f'bytes={start}-', 'If-Range': state['validator']})
    try:
        active = opener or ordinary_opener(media_url)
        with active.open(Request(media_url, headers=headers), timeout=30) as response:
            expected_status = 206 if start else 200
            if response.status != expected_status:
                raise ValueError('Response is not the required complete/range transfer; no restart or overwrite')
            content_type = response.headers.get('content-type', '').split(';')[0].strip()
            if not content_type.startswith('video/') and content_type != 'application/octet-stream':
                raise ValueError('Response is not video bytes')
            length = int(response.headers.get('content-length') or 0)
            total = length
            if start:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('content-range', ''))
                if not match or int(match[1]) != start or int(match[3]) != state['total_bytes'] or int(match[2]) != int(match[3]) - 1 or length != int(match[3]) - start:
                    raise ValueError('Returned range does not match the preserved partial file')
                total = int(match[3])
            if expected_bytes is not None and total != expected_bytes:
                raise ValueError('Remote complete length changed from the finite batch reservation')
            if not 0 < total <= max_bytes:
                raise ValueError('Known complete length must fit the per-video byte budget')
            etag = response.headers.get('etag')
            validator = etag if etag and not etag.startswith('W/') else response.headers.get('last-modified')
            if start and validator != state['validator']:
                raise ValueError('Remote HTTP validator changed')
            if shutil.disk_usage(target.parent).free - (total - start) < reserve_free:
                raise ValueError('Transfer would violate the local free-space reserve')
            state.update(total_bytes=total, validator=validator, status='downloading', http_status=response.status)
            with partial.open('ab' if start else 'xb') as handle:
                partial.chmod(0o600)
                got = start
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    if got + len(block) > total or got + len(block) > max_bytes or shutil.disk_usage(target.parent).free - len(block) < reserve_free:
                        raise ValueError('Transfer exceeded its length, byte budget or free-space reserve')
                    handle.write(block)
                    got += len(block)
            if got != total:
                raise ValueError('Incomplete transfer; partial file retained')
        validation = verifier(partial, max_height)
        if digest(source_page) != source_sha256:
            raise ValueError('Source page changed during transfer')
        media_hash = digest(partial)
        partial.rename(target)
        receipt = {'schema_version': 1, 'status': 'verified', 'provider': 'publisher_video',
                   'source_id': source_id, 'binding': binding, 'bytes': total, 'sha256': media_hash,
                   'local_path': str(target), 'validation': validation, 'completed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'source_page_path': str(Path(source_page).resolve()), 'new_youtube_downloads': 0,
                   'scope': 'Independent explicit publisher download; no YouTube edition identity, voice attribution or transcript accuracy inferred.'}
        atomic_json(receipt_path, receipt)
        atomic_json(state_path, {**state, 'status': 'complete', 'sha256': media_hash})
        return receipt
    except Exception as error:
        state.update(status='failed_no_automatic_retry', error_type=type(error).__name__)
        if isinstance(error, HTTPError):
            state['http_status'] = error.code
        if partial.is_file():
            state.update(partial_bytes=partial.stat().st_size, partial_sha256=digest(partial))
        atomic_json(state_path, state)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source-page', 'source-sha256', 'source-url', 'media-url', 'target', 'source-id', 'medium-id', 'channel-id'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--max-bytes', type=int, default=MAX_BYTES)
    p.add_argument('--expected-bytes', type=int, help='Bind a finite batch size reservation to the observed complete length')
    p.add_argument('--reserve-free-bytes', type=int, default=RESERVE)
    p.add_argument('--max-height', type=int, choices=[360, 480, 720], default=720)
    p.add_argument('--resume', action='store_true')
    a = vars(p.parse_args())
    a['reserve_free'] = a.pop('reserve_free_bytes')
    receipt = download(**a)
    print(json.dumps({'status': receipt['status'], 'bytes': receipt['bytes'], 'sha256': receipt['sha256'],
                      'local_path': receipt['local_path'], 'new_youtube_downloads': 0}, indent=2))


if __name__ == '__main__':
    main()
