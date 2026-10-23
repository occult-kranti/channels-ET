#!/usr/bin/env python3
"""Build a metadata-only corpus index; never infer transcript text from vectors."""
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())


def main():
    snapshot_path = ROOT / 'dist/analysis/data.json'
    baseline = load(snapshot_path)
    plan = load(ROOT / 'research/expansion/acquisition/collection-plan.json')
    frame = load(ROOT / 'research/expansion/acquisition/practitioner-frame.json')['people']
    preflight = load(HERE / 'preflight-2026-10-23T2109.json')
    author = load(HERE / 'author-preflight-2026-10-23.json')
    output = HERE / 'corpus-index.sqlite'
    temporary = HERE / 'corpus-index.new.sqlite'
    if temporary.exists(): temporary.unlink()
    con = sqlite3.connect(temporary)
    con.executescript('''
    PRAGMA foreign_keys=ON;
    CREATE TABLE videos(video_id TEXT PRIMARY KEY, title TEXT, source_url TEXT NOT NULL,
      publisher_group_id TEXT, publisher_metadata TEXT, duration_seconds REAL,
      metadata_date TEXT, context_entities_json TEXT NOT NULL, context_people_json TEXT NOT NULL,
      text_status TEXT NOT NULL, actual_speaker_status TEXT NOT NULL, evidence_type TEXT NOT NULL,
      baseline_snapshot_sha256 TEXT NOT NULL);
    CREATE TABLE practitioner_candidates(candidate_id TEXT PRIMARY KEY, name TEXT NOT NULL,
      entity_labels_json TEXT NOT NULL, identity_status TEXT NOT NULL);
    CREATE TABLE candidate_account_routes(candidate_id TEXT REFERENCES practitioner_candidates(candidate_id),
      source_url TEXT NOT NULL, attribution_status TEXT NOT NULL, PRIMARY KEY(candidate_id,source_url));
    CREATE TABLE collection_operations(operation_id TEXT PRIMARY KEY, source_url TEXT NOT NULL,
      source_kind TEXT NOT NULL, retrieved_at TEXT, status TEXT NOT NULL,
      failure_class TEXT, error TEXT, new_text_available INTEGER NOT NULL);
    CREATE TABLE transcript_artifacts(artifact_id TEXT PRIMARY KEY, video_id TEXT REFERENCES videos(video_id),
      source_url TEXT NOT NULL, language_code TEXT, is_generated INTEGER, segment_count INTEGER,
      source_sha256 TEXT NOT NULL, actual_speaker_status TEXT NOT NULL, collection_status TEXT NOT NULL);
    CREATE INDEX video_publisher ON videos(publisher_group_id);
    CREATE INDEX video_text_status ON videos(text_status);
    ''')
    source_hash = digest(snapshot_path)
    for v in sorted(baseline['videos'], key=lambda x: x['id']):
        con.execute('INSERT INTO videos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (v['id'], v.get('title'), v['url'], v.get('channelId'), v.get('observedPublisher') or v.get('publisher'),
                     v.get('durationSeconds'), v.get('date'), json.dumps(v.get('entities', []), ensure_ascii=False),
                     json.dumps(v.get('people', []), ensure_ascii=False), 'raw_caption_text_unavailable_in_current_workspace',
                     'unknown_not_audio_verified', 'inherited_public_upload_metadata', source_hash))
    for p in sorted(frame, key=lambda x: x['id']):
        con.execute('INSERT INTO practitioner_candidates VALUES(?,?,?,?)',
                    (p['id'], p['name'], json.dumps(p.get('entities', []), ensure_ascii=False), 'inherited_candidate_not_revalidated'))
        for url in sorted(set(p.get('accountUrls', []))):
            con.execute('INSERT INTO candidate_account_routes VALUES(?,?,?)', (p['id'], url, 'inherited_explicit_route_not_verified_speaker'))
    for index, r in enumerate(preflight['records']):
        con.execute('INSERT INTO collection_operations VALUES(?,?,?,?,?,?,?,?)',
                    ('youtube-preflight-' + str(index), r['url'], 'public_YouTube_watch_preflight', r['retrieved_at'],
                     r['status'], 'proxy_CONNECT_denial', r.get('error'), 0))
    con.execute('INSERT INTO collection_operations VALUES(?,?,?,?,?,?,?,?)',
                ('author-preflight-1', author['source_url'], author['source_kind'], author['retrieved_at'],
                 author['status'], 'HTTP403_origin_or_intermediary_not_determined', author.get('error'), 0))
    con.commit()
    assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    counts = {name: con.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0] for name in
              ['videos', 'practitioner_candidates', 'candidate_account_routes', 'collection_operations', 'transcript_artifacts']}
    con.close(); temporary.replace(output)
    candidate_status = []
    for person in frame:
        queries = [q for q in plan['searches'] if q['person_id'] == person['id']]
        channels = [c for c in plan['accounts'] if person['id'] in c.get('person_ids', [])]
        candidate_status.append({'candidate_id': person['id'], 'name': person['name'],
                                 'requested_plan_queries': len(queries), 'requested_channel_routes': len(channels),
                                 'keyword_queries_attempted': 0, 'channel_crawls_attempted': 0,
                                 'caption_video_requests_attempted': 0, 'caption_tracks_retrieved': 0,
                                 'collection_status': 'not_attempted_after_general_access_probe_denial',
                                 'actual_speaker_status': 'unknown_not_audio_verified',
                                 'source_record_ids_inherited': person.get('recordIds', [])})
    status = {'schema_version': 1, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'network_desired': 'unrestricted', 'network_observation_state': 'unknown',
              'observed_access': 'public_YouTube_proxy_CONNECT403_and_separate_author_HTTP403',
              'note': 'Desired unrestricted policy is not proof of destination access; no request to enable settings again is inferred.',
              'new_public_watch_attempts': len(preflight['records']), 'new_author_transcript_attempts': 1,
              'successful_new_operations': 0, 'new_raw_caption_documents': 0, 'new_media_downloads': 0,
              'new_live_yt_dlp_operations': 0, 'new_live_transcript_api_operations': 0,
              'planned_keyword_queries': plan['units']['keyword_queries'], 'planned_account_routes': plan['units']['account_routes'],
              'selected_caption_candidates': plan['units']['caption_candidates'],
              'baseline_uploads_indexed': counts['videos'], 'actual_transcript_artifacts_indexed': counts['transcript_artifacts'],
              'database': {'path': 'corpus-index.sqlite', 'sha256': digest(output), 'tables': counts,
                           'text_release': 'Metadata and source hashes only; no raw speech text.', 'integrity': 'ok'},
              'candidate_status': candidate_status,
              'source_sha256': {'baseline_data': source_hash, 'collection_plan': digest(ROOT / 'research/expansion/acquisition/collection-plan.json'),
                               'YouTube_preflight': digest(HERE / 'preflight-2026-10-23T2109.json'),
                               'author_preflight': digest(HERE / 'author-preflight-2026-10-23.json')}}
    (HERE / 'acquisition-status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'database_tables': counts, 'candidate_status_records': len(candidate_status), 'successful_new_operations': 0}))


if __name__ == '__main__': main()
