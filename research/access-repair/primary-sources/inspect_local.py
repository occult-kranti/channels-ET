#!/usr/bin/env python3
"""Inspect already saved publisher text; never performs network requests."""
import datetime
import hashlib
import json
import pathlib
import re

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
meta = json.loads((H / 'metadata.json').read_text())
by_id = {x['source_id']: x for x in meta['records']}
checks = []


def sha(body):
    return hashlib.sha256(body).hexdigest()


def ck(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})


for record in meta['records']:
    for kind in ['response', 'text']:
        receipt = record[kind]
        raw = pathlib.Path(receipt['raw_local_path']).read_bytes()
        ck(sha(raw) == receipt['sha256'] and len(raw) == receipt['bytes'], record['source_id'] + ' ' + kind + ' hash and size')

daniel = pathlib.Path(by_id['daniel-feed']['text']['raw_local_path']).read_text()
opening = '“Greetings. We are The Arcturian Council.'
closing = 'We are the Arcturian Council, and we have enjoyed connecting with you.”'
ck(daniel.count(opening) == 1 and daniel.count(closing) == 1, 'unique explicit publisher message quote boundaries')
body = daniel[daniel.index(opening):daniel.index(closing) + len(closing)]
body_bytes = body.encode('utf-8')
private = pathlib.Path(by_id['daniel-feed']['text']['raw_local_path']).with_name('daniel-arcturian-published-message.txt')
with private.open('xb') as stream:
    stream.write(body_bytes)

paul = pathlib.Path(by_id['paul-birmingham']['text']['raw_local_path']).read_text()
pdf = 'https://s3.us-east-2.amazonaws.com/pstranscripts/The+Expression+of+the+True+Self.pdf'
ck(any(x['url'] == pdf and x['label'] == 'DOWNLOAD TRANSCRIPT' for x in by_id['paul-birmingham']['explicit_transcript_or_feed_links']), 'official Paul page explicitly links named transcript PDF')
ck('July 15, 2017' in paul and 'Birmingham, England' in paul, 'Paul session date and place explicit in actual fetched text')
athina_body = pathlib.Path(by_id['athina-ashtar']['response']['raw_local_path']).read_text()
feed = 'https://feed.podbean.com/athinakrol/feed.xml'
ck('type="application/rss+xml" rel="alternate" href="' + feed + '"' in athina_body, 'Athina actual creator page explicitly declares the publisher RSS URL')
athina_text = pathlib.Path(by_id['athina-ashtar']['text']['raw_local_path']).read_text()
ck('Feb 6, 2023' in athina_text and '28 min' in athina_text and 'Ashtar Live Channelling' in athina_text, 'Athina exact episode title/date/duration present in actual fetched text')
held = R / 'research/harvest/publisher_sources/publisher-summary.json'
ck(sha(held.read_bytes()) == 'a021c6cc7fb3c082b164ed6aee25d6f436810f2afdd2fb23ac6cded412c296c3', 'frozen nineteen-episode publisher summary unchanged')
report = {
    'schema_version': 1, 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'PASS' if all(x['passed'] for x in checks) else 'FAIL',
    'checks': len(checks), 'failures': [x for x in checks if not x['passed']],
    'inspection_script_sha256': sha(pathlib.Path(__file__).read_bytes()),
    'metadata_sha256': sha((H / 'metadata.json').read_bytes()), 'network_requests_by_inspection': 0,
    'daniel_message': {
        'title': by_id['daniel-feed']['title'], 'guid': by_id['daniel-feed']['guid'],
        'publication_timestamp': by_id['daniel-feed']['publication_timestamp'],
        'private_text_path': str(private), 'bytes': len(body_bytes), 'sha256': sha(body_bytes),
        'word_count': len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", body)),
        'extraction_rule': 'Unique author-published opening and closing quotation boundaries, selected by assistant inspection of the retained RSS text; marketing/title/footer excluded.',
        'source_response_sha256': by_id['daniel-feed']['response']['sha256'],
        'scope': 'author-published attributed message; not verified audiovisual transcription',
        'accuracy_or_entity_origin_verified': False,
    },
    'paul_transcript_lead': {
        'official_page_url': by_id['paul-birmingham']['requested_url'], 'explicit_pdf_url': pdf,
        'pdf_followed': False, 'full_transcript_acquired': False,
        'page_content_scope': 'Official catalog page includes a duplicated short excerpt and boilerplate; its 550-word rendered page count is not a transcript length.',
        'explicit_session_date': '2017-07-15', 'source_frame': 'spiritual mediumship comparison; not recoded as biological ET',
    },
    'athina_podcast_lead': {
        'official_page_url': by_id['athina-ashtar']['requested_url'], 'explicit_rss_url': feed,
        'feed_followed': False, 'audio_acquired': False,
        'explicit_episode_title': 'Ashtar Live Channelling | The 3 Phases of Soul Purpose & Earth’s Dimensional Upgrades',
        'explicit_publication_date': '2023-02-06', 'displayed_duration_minutes': 28,
        'page_content_scope': 'Creator episode description and show/marketing text; not a full spoken transcript.',
    },
    'interpretation_limits': [
        'Three independently published source-page/RSS requests succeeded; this does not demonstrate YouTube access.',
        'No audio/video acquisition, new study cohort or redistribution license is established.',
        'Full source responses and extracted text remain outside Git and public hosting.',
    ], 'all_checks': checks,
}
(H / 'inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks', 'failures', 'daniel_message']}, ensure_ascii=False, indent=2))
raise SystemExit(report['status'] != 'PASS')
