#!/usr/bin/env python3
"""Bounded acquisition of public YouTube metadata or offered caption tracks.

Inputs: JSON list of {video_id: 11-character ID}, or {records: [...]}.
Examples:
  python acquire_youtube.py metadata ids.json metadata.json --workers 4
  python acquire_youtube.py captions pilot.json manifest.json --raw-dir /tmp/captions

Metadata access does not mean a video is playable. Caption text is kept only in
--raw-dir, which must be outside a Git checkout; the output contains no full text.
No proxies, credentials, cookies, retries, automatic translation or media downloads.
Requirements: captions mode needs youtube-transcript-api==1.2.4.
"""
from __future__ import annotations
import argparse, concurrent.futures, datetime, hashlib, json, pathlib, re, threading
import urllib.error, urllib.request

def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha256(blob):
    return hashlib.sha256(blob).hexdigest()

def metadata(video_id):
    url = 'https://www.youtube.com/watch?v=' + video_id
    result = {'video_id': video_id, 'source_url': url, 'retrieved_at': timestamp(),
              'access_type': 'public_watch_page_metadata'}
    raw = urllib.request.urlopen(url, timeout=25).read()
    page = raw.decode('utf-8')
    player = {}
    for marker in ('var ytInitialPlayerResponse = ', 'ytInitialPlayerResponse = '):
        if marker in page:
            try:
                player = json.JSONDecoder().raw_decode(page.split(marker, 1)[1])[0]
                break
            except (ValueError, TypeError):
                continue
    detail = player.get('videoDetails', {})
    micro = player.get('microformat', {}).get('playerMicroformatRenderer', {})
    if detail.get('videoId') != video_id:
        raise ValueError('Matching video metadata was not exposed')
    result.update(status='success', title=detail.get('title'),
                  channel_id=detail.get('channelId'), publisher=detail.get('author'),
                  channel_url=micro.get('ownerProfileUrl'),
                  duration_seconds=int(detail['lengthSeconds']) if detail.get('lengthSeconds') else None,
                  published_at=micro.get('publishDate'), uploaded_at=micro.get('uploadDate'),
                  playability_status=player.get('playabilityStatus', {}).get('status'),
                  html_sha256=sha256(raw))
    return result

def captions(video_id, raw_dir):
    from youtube_transcript_api import YouTubeTranscriptApi
    from requests import Session
    class TimeoutSession(Session):
        def request(self, *args, **kwargs):
            kwargs.setdefault('timeout', 25)
            # Do not reuse server cookies, and do not add authorization.
            self.cookies.clear()
            return super().request(*args, **kwargs)
    session = TimeoutSession()
    tracks = list(YouTubeTranscriptApi(http_client=session).list(video_id))
    if not tracks:
        raise ValueError('No offered caption track')
    # Prefer an offered English track, then any offered original track.
    # This does not request automatic translation.
    selected = next((t for t in tracks if t.language_code in ('en', 'en-US', 'en-GB')), tracks[0])
    fetched = selected.fetch()
    document = {'video_id': video_id, 'language': fetched.language,
                'language_code': fetched.language_code, 'is_generated': fetched.is_generated,
                'segments': fetched.to_raw_data()}
    blob = json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8')
    (raw_dir / (video_id + '.json')).write_bytes(blob)
    text = ' '.join(s['text'] for s in document['segments'])
    return {'video_id': video_id, 'status': 'success', 'source_type': 'youtube_captions',
            'source_url': 'https://www.youtube.com/watch?v=' + video_id,
            'retrieved_at': timestamp(), 'language_code': fetched.language_code,
            'is_generated': fetched.is_generated, 'segment_count': len(document['segments']),
            'whitespace_word_count': len(text.split()), 'character_count': len(text),
            'raw_sha256': sha256(blob), 'package': 'youtube-transcript-api==1.2.4',
            'rights': 'Raw text is local analysis only. Export derived features and source metadata.'}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('metadata', 'captions'))
    p.add_argument('input', type=pathlib.Path)
    p.add_argument('output', type=pathlib.Path)
    p.add_argument('--workers', type=int, choices=range(1, 7), default=4)
    p.add_argument('--max-requests', type=int, default=1000)
    p.add_argument('--raw-dir', type=pathlib.Path)
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    if args.mode == 'captions':
        if args.raw_dir is None:
            p.error('captions requires --raw-dir outside the Git checkout')
        raw_dir = args.raw_dir.resolve()
        if any((parent / '.git').exists() for parent in (raw_dir, *raw_dir.parents)):
            p.error('--raw-dir must be outside a Git checkout')
        raw_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.input.read_text())
    if isinstance(records, dict):
        records = records['records']
    ids = list(dict.fromkeys(r['video_id'] for r in records if re.fullmatch(r'[\w-]{11}', r.get('video_id', ''))))
    if args.max_requests < 1:
        p.error('--max-requests must be positive')
    log = args.output.with_suffix('.jsonl')
    previous = []
    if args.resume and log.exists():
        previous = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    elif log.exists():
        p.error('log already exists; choose a new output or explicitly --resume')
    existing = {r['video_id'] for r in previous}
    pending = [id for id in ids if id not in existing][:args.max_requests]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    stopped = threading.Event()
    def run(id):
        if stopped.is_set():
            return {'video_id': id, 'status': 'not_attempted_after_block'}
        try:
            record = metadata(id) if args.mode == 'metadata' else captions(id, raw_dir)
        except Exception as e:
            record = {'video_id': id, 'status': 'failed', 'retrieved_at': timestamp(),
                      'error_type': type(e).__name__, 'error': str(e)[:1000]}
            if (isinstance(e, urllib.error.HTTPError) and e.code in (403, 429)) or type(e).__name__ in ('RequestBlocked', 'IpBlocked'):
                stopped.set()
        with lock:
            with log.open('a') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        added = list(executor.map(run, pending))
    result = {'mode': args.mode, 'finished_at': timestamp(), 'input_unique_ids': len(ids),
              'selected_this_run': len(pending), 'blocked': stopped.is_set(),
              'records': previous + added}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))

if __name__ == '__main__':
    main()
