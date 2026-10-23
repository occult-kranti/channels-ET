#!/usr/bin/env python3
"""Retain local readable documentation and a pinned official-wiki receipt."""
import datetime
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import subprocess

H = pathlib.Path(__file__).resolve().parent
C = H / 'source-cache'


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.skip = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.active = True
        if self.active and tag in ['script', 'style']:
            self.skip += 1
        if self.active and tag in ['p', 'h1', 'h2', 'h3', 'h4', 'li', 'tr']:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in ['script', 'style'] and self.active:
            self.skip = max(0, self.skip - 1)
        if tag == 'main':
            self.active = False

    def handle_data(self, data):
        if self.active and not self.skip:
            self.out.append(data)


for path in C.glob('github-*'):
    if path.suffix == '.txt':
        continue
    parser = MainText()
    parser.feed(path.read_text())
    text = '\n'.join(' '.join(s.split()) for s in ''.join(parser.out).splitlines() if s.strip())
    path.with_suffix('.txt').write_text(text + '\n')

wiki = pathlib.Path('/tmp/channels-et-ytdlp-wiki-research')
commit = subprocess.check_output(['git', '-C', str(wiki), 'rev-parse', 'HEAD'], text=True).strip()
records = []
for name in ['EJS.md', 'FAQ.md', 'Installation.md']:
    raw = (wiki / name).read_bytes()
    (C / ('wiki-' + name)).write_bytes(raw)
    records.append({'id': 'wiki-' + name[:-3].lower(), 'source_url': 'https://github.com/yt-dlp/yt-dlp/wiki/' + name[:-3],
                    'git_url': 'https://github.com/yt-dlp/yt-dlp.wiki.git', 'commit': commit,
                    'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'retrieval': 'ordinary shallow git clone through inherited proxy; no credential extraction'})
(H / 'wiki-receipt.json').write_text(json.dumps({'records': records}, indent=2) + '\n')
print(json.dumps(records, indent=2))
