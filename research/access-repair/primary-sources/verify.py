#!/usr/bin/env python3
"""Independent local artifact checks; no producer import or network access."""
import email.utils
import hashlib
import json
import pathlib
import re
import subprocess

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
meta = json.loads((H / 'metadata.json').read_text())
expanded = json.loads((H / 'expanded-metadata.json').read_text())
checks = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


def artifact(row, label, words=False):
    path = pathlib.Path(row['raw_local_path'])
    raw = path.read_bytes()
    ck(sha(raw) == row['sha256'] and len(raw) == row['bytes'], label + ' retained hash and size')
    ck(not path.is_relative_to(R), label + ' full body remains outside repository')
    if words:
        ck(len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", raw.decode())) == row['word_count'], label + ' rendered word count')
    return raw


for row in meta['records']:
    artifact(row['response'], row['source_id'] + ' response')
    artifact(row['text'], row['source_id'] + ' rendered page/item', words=True)
for ident in ['paul', 'athina']:
    artifact(expanded[ident]['response'], ident + ' follow-up response')
paul = expanded['paul']
pdf = pathlib.Path(paul['response']['raw_local_path'])
ck(pdf.read_bytes().startswith(b'%PDF-'), 'Paul response PDF magic')
info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, check=True).stdout.decode()
ck(re.search(r'^Pages:\s+4\s*$', info, re.M) is not None and paul['pages'] == 4, 'Paul independently probed four pages')
text = artifact(paul['text'], 'Paul extracted publisher transcript', words=True).decode()
ck('The Expression of the True Self' in text and 'July 15, 2017' in text, 'Paul actual PDF title and session date')
ck(expanded['daniel']['items_extracted'] == 15 and len(expanded['daniel']['items']) == 15, 'all fifteen saved Daniel RSS items have records')
guids = [x['guid'] for x in expanded['daniel']['items']]
ck(len(set(guids)) == 15, 'Daniel item GUIDs are unique within this snapshot')
for item in expanded['daniel']['items']:
    artifact(item['text'], 'Daniel item ' + str(item['item_index']), words=True)
ck(sum(x['text']['word_count'] for x in expanded['daniel']['items']) == expanded['daniel']['total_rendered_item_words'] == 10998,
   'Daniel aggregate rendered word total; includes promotions')
matches = expanded['athina']['exact_episode_matches']
ck(len(matches) == 1 and matches[0]['link'].rstrip('/') == meta['records'][2]['requested_url'].rstrip('/'), 'Athina exact creator-episode URL match')
ck(email.utils.parsedate_to_datetime(matches[0]['publication_timestamp']).date().isoformat() == '2023-02-06', 'Athina explicit RSS episode date')
ck(matches[0]['guid'] == 'lightleaders.podbean.com/5d144c22-ae55-37bb-b83b-5edfb61e45db' and matches[0]['enclosure']['requested'] is False,
   'Athina actual GUID retained and enclosure not requested')
held = R / 'research/harvest/publisher_sources/publisher-summary.json'
ck(sha(held.read_bytes()) == 'a021c6cc7fb3c082b164ed6aee25d6f436810f2afdd2fb23ac6cded412c296c3', 'frozen nineteen-episode study summary unchanged')
ck(meta['network_requests'] + expanded['new_network_requests'] == 5 and expanded['youtube_requests'] == expanded['audio_acquisitions'] == 0,
   'bounded request ledger totals five publisher requests, zero YouTube or audio')
failed = [x for x in checks if not x['passed']]
result = {'status': 'FAIL' if failed else 'PASS', 'checks': len(checks), 'failures': failed,
          'verifier_sha256': sha(pathlib.Path(__file__).read_bytes()),
          'metadata_sha256': sha((H / 'metadata.json').read_bytes()),
          'expanded_metadata_sha256': sha((H / 'expanded-metadata.json').read_bytes()),
          'network_requests_by_verifier': 0, 'all_checks': checks}
(H / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['status', 'checks', 'failures']}, indent=2))
raise SystemExit(bool(failed))
