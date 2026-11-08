#!/usr/bin/env python3
"""Publish only reviewed aggregates; full source text/media stay private.

Collection is a dated snapshot, not a browser-side view of the private archive.
Run again with the final compact-audio manifest after acquisition completes.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def has_retained_text(record):
    return bool(record.get('text_artifact')) and record.get('collection_status') in {'retrieved', 'completed'}


def safe_public(data):
    serialized = json.dumps(data, ensure_ascii=False)
    for forbidden in ('/workspace/', '/home/agent/', 'Bearer ', 'X-Amz-Signature=', 'access_token='):
        if forbidden in serialized:
            raise ValueError(f'Private material in public projection: {forbidden}')
    def inspect(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in {'text', 'question_text', 'answer_text', 'raw_text', 'transcript_text'}:
                    raise ValueError(f'Unapproved full-text field: {k}')
                inspect(v)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(data)


def publish(private, output, ra_audio=None, bashar_audio=None, bashar_speech=None, paired_editions=None, bashar_dispositions=None):
    run = private / 'analysis/run-04'
    data = read(run / 'analysis.json')
    if digest(run / 'analysis.json') != 'e9e88095a5264ff588c52e9d9edb23bbffa57ca1e86b24b997057e08035aa476':
        raise ValueError('Independently reviewed run04 changed')
    if data.get('synthetic_fixture_run') or len(data['documents']) != 130:
        raise ValueError('Unexpected reviewed analysis frame')
    reading_path = private / 'reading/public-comparisons.json'
    reading = read(reading_path)
    if digest(reading_path) != '89bd1ea85ce90ecd1ccdaa9f083f7eef99e0ce4a3af1ce89904d9d51ff58ed85':
        raise ValueError('Reviewed reading projection changed')
    for obj in (data, reading):
        safe_public(obj)
    output.mkdir(parents=True, exist_ok=True)
    figures = output / 'figures'
    figures.mkdir(exist_ok=True)
    for item in data['figures']:
        path = run / item['file']
        if Path(item['file']).name != item['file'] or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('Figure verification failed')
        shutil.copyfile(path, figures / item['file'])
    shutil.copyfile(run / 'analysis.json', output / 'data.json')
    shutil.copyfile(reading_path, output / 'reading.json')
    followon = private / 'official-analysis/final-01/official-speech.json'
    if followon.is_file():
        if digest(followon) != '68e4c40a34fa0bd7efcea13a32ea501b0f7bfd55643935f01e2d8a7a68907b01':
            raise ValueError('Reviewed official speech analysis changed')
        supplement = read(followon)
        safe_public(supplement)
        destination = output / 'official-figures'
        destination.mkdir(exist_ok=True)
        for item in supplement['figures']:
            source = followon.parent / item['file']
            if Path(item['file']).name != item['file'] or source.stat().st_size != item['bytes'] or digest(source) != item['sha256']:
                raise ValueError('Supplementary figure verification failed')
            shutil.copyfile(source, destination / item['file'])
        shutil.copyfile(followon, output / 'official-speech.json')
    ra = read(private / 'ra/complete-transcript-manifest.json')
    frame = read(private / 'ra/audio-inventory-complete.json')
    pilot = read(private / 'ra/audio-pilot/receipt.json')
    bashar = read(private / 'bashar/corpus/manifest.json')
    excerpt = read(private / 'bashar/official-excerpt-corpus/manifest.json')
    captions = read(private / 'bashar/official-platform-captions/manifest.json')
    census = read(private / 'bashar/discovery/vimeo-oembed-census.json')
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    sources = {}
    ra_stats = {
        'audio_downloaded': 1, 'unique_audio_sources': 1, 'retained_audio_files': 1, 'video_downloaded': 0,
        'transcripts_downloaded': len(ra['records']),
        'transcript_editions': len(ra['records']), 'unique_transcribed_sources': len(ra['records']),
        'inventory_audio_total': frame['published_audio_segments'],
        'inventory_video_total': None,
        'original_audio_retained': 1, 'compact_audio_retained': 0,
        'retained_audio_encoding': 'Original pilot MP3; full-length compact Opus collection in progress',
        'inventory_original_bytes': 6620288811, 'media_bytes': pilot['bytes'],
        'audio_hours': None, 'download_status': 'acquisition_in_progress',
        'scope': '106 complete published Lightly Edited texts. Audio counts are segments, not continuous tapes. The finite original-audio frame has 2,620 links. Historical missing/overwritten recordings are not reconstructed.',
        'updated_at': now,
    }
    auxiliary = private / 'ra/compact-local-pilot/001-000.opus'
    if auxiliary.is_file():
        ra_stats.update(auxiliary_validation_audio_files=1, auxiliary_validation_audio_bytes=auxiliary.stat().st_size,
            auxiliary_validation_audio_sha256=digest(auxiliary),
            auxiliary_scope='Separate local conversion-test copy of source1.0, outside canonical source/file/duration totals.')
    if ra_audio:
        media = read(ra_audio)
        if media['kind'] != 'verified-ra-published-recording-compact-copies' or media['source_count'] != 2620:
            raise ValueError('Unexpected compact collection frame')
        rows = media['records']
        if len({r['source_id'] for r in rows}) != len(rows) or len(rows) != media['verified_segments']:
            raise ValueError('Duplicate or inconsistent retained audio count')
        for r in rows:
            p = Path(r['retained']['path'])
            if r['status'] != 'verified_compact_copy' or not p.is_file() or p.stat().st_size != r['retained']['bytes']:
                raise ValueError('Retained compact file is missing or changed in size')
        unique = {r['source_id'] for r in rows} | {pilot['source_id']}
        pilot_duration = float(pilot['probe']['format']['duration']) if 'format' in pilot['probe'] else float(pilot['probe']['duration_seconds'])
        ra_stats.update(audio_downloaded=len(unique), unique_audio_sources=len(unique),
            retained_audio_files=len(rows) + 1, compact_audio_retained=len(rows),
            media_bytes=media['retained_bytes'] + pilot['bytes'],
            audio_hours=(media['duration_seconds'] + (pilot_duration if pilot['source_id'] not in {r['source_id'] for r in rows} else 0)) / 3600,
            download_status=media['status'],
            retained_audio_encoding='Full-length 48 kbps CBR Ogg Opus (lossy); original pilot MP3 also preserved',
            original_bytes_verified_before_conversion=media['original_verified_bytes'],
            manifest_sha256=digest(ra_audio), failed_segments=len(media['failures']))
        by_session = {}
        for r in rows:
            by_session.setdefault(r['session_id'], []).append(r)
        for r in ra['records']:
            clips = by_session.get(r['session_id'], [])
            sources[r['source_id']] = {'published_text': 'retained', 'compact_audio_segments': len(clips),
                'compact_audio_bytes': sum(c['retained']['bytes'] for c in clips), 'video_downloaded': False}
    old = bashar['summary']
    new = excerpt['summary']
    bashar_stats = {
        'audio_downloaded': old['retained_recordings'] + new['recordings'],
        'unique_audio_sources': old['retained_recordings'] + new['recordings'],
        'retained_audio_files': old['retained_recordings'] + new['recordings'],
        'video_downloaded': 0,
        'transcripts_downloaded': len(bashar['records']) + len(excerpt['records']) + len(captions['records']),
        'transcript_editions': len(bashar['records']) + len(excerpt['records']) + len(captions['records']),
        'unique_transcribed_sources': len({r['session_id'] for r in bashar['records'] + excerpt['records'] + captions['records']}),
        'inventory_audio_total': old['retained_recordings'] + census['eligible_count'],
        'inventory_video_total': census['eligible_count'],
        'official_profile_ids': census['count'], 'duration_eligible_profile_ids': census['eligible_count'],
        'original_audio_retained': old['retained_recordings'] + new['recordings'], 'compact_audio_retained': 0,
        'retained_audio_encoding': 'Publisher audio encodings; formats and editions recorded separately',
        'media_bytes': old['audio_bytes'] + new['audio_bytes'],
        'audio_hours': (old['audio_seconds'] + new['audio_seconds']) / 3600,
        'publisher_automatic_caption_tracks': len(captions['records']),
        'local_machine_transcripts': len(bashar['records']) + len(excerpt['records']),
        'download_status': 'acquisition_in_progress', 'updated_at': now,
        'scope': '19 retained mixed-context recordings plus official public publications. The Vimeo frame has 307 IDs and 87 advertised at least five minutes; actual decoded duration determines admission. Unique audio sources here means publication IDs, while exact encoded-audio families are reported separately. Excerpts, greetings and promotions are not full paid sessions. Counts do not cover every historic Bashar upload. No count cap in this new study.',
    }
    for r in bashar['records'] + excerpt['records']:
        sources[r['source_id']] = {'audio_downloaded': True, 'audio_bytes': r['audio_bytes'],
            'local_machine_transcript': True, 'video_downloaded': False,
            'human_accuracy_validated': False}
    if bool(bashar_audio) != bool(bashar_speech):
        raise ValueError('Supply both audio dispositions and preferred text dispositions for the official frame')
    extra_inputs = {}
    if bashar_audio:
        acquisition = read(bashar_audio)
        speech = read(bashar_speech)
        if len(acquisition['records']) != 87 or len(speech['records']) != 87:
            raise ValueError('Final official frame must retain all 87 dispositions, including explicit failures/holds')
        audio_rows = [r for r in acquisition['records'] if r['status'] == 'completed']
        if len({r['video_id'] for r in acquisition['records']}) != 87:
            raise ValueError('Duplicate official audio source')
        if bashar_dispositions:
            # The corrected selection can supersede a preserved incomplete
            # encoding. Never derive current bytes from its older batch row.
            selected = read(bashar_dispositions)['records']
            audio_rows = [{'video_id': r['recording_id'].split(':')[-1], 'status': 'completed',
                'audio': r['audio_artifact'], 'duration_seconds': r['audio_duration_seconds'],
                'source_format': r['source_format']} for r in selected if r['collection_status'] == 'retrieved']
        for r in audio_rows:
            p = Path(r['audio']['path'])
            if not p.is_file() or p.stat().st_size != r['audio']['bytes']:
                raise ValueError('Official source audio missing/changed')
        editions = {}
        all_texts = bashar['records'] + excerpt['records'] + captions['records'] + speech['records']
        if paired_editions:
            all_texts += read(paired_editions)['records']
            extra_inputs['paired_editions_manifest_sha256'] = digest(paired_editions)
        for r in all_texts:
            if not has_retained_text(r):
                continue
            key = (r['source_id'], r['edition_id'])
            if key in editions and editions[key]['text_artifact']['sha256'] != r['text_artifact']['sha256']:
                raise ValueError('Conflicting transcript edition')
            editions[key] = r
        audio_ids = {f"vimeo:{r['video_id']}" for r in audio_rows}
        for r in speech['records']:
            recording = r.get('recording_id', r['session_id'])
            sources[r['source_id']] = {'audio_downloaded': recording in audio_ids,
                'text_edition_retained': has_retained_text(r),
                'text_kind': r['source_kind'], 'collection_status': r.get('collection_status'),
                'video_downloaded': False, 'human_accuracy_validated': False}
        bashar_stats.update(audio_downloaded=old['retained_recordings'] + len(audio_rows),
            unique_audio_sources=old['retained_recordings'] + len(audio_rows),
            retained_audio_files=old['retained_recordings'] + len(audio_rows),
            original_audio_retained=old['retained_recordings'] + len(audio_rows),
            media_bytes=old['audio_bytes'] + sum(r['audio']['bytes'] for r in audio_rows),
            audio_hours=(old['audio_seconds'] + sum(r['duration_seconds'] for r in audio_rows)) / 3600,
            transcripts_downloaded=len(editions), transcript_editions=len(editions),
            unique_transcribed_sources=len({r.get('recording_id', r['session_id']) for r in editions.values()}),
            local_machine_transcripts=sum(any(e.get('role') == 'asr_receipt' for e in r.get('evidence', [])) for r in editions.values()),
            official_audio_retained=len(audio_rows), official_text_dispositions=len(speech['records']),
            download_status='completed_observed_public_frame' if len(audio_rows) == 87 else 'partial_observed_public_frame',
            audio_acquisition_manifest_sha256=digest(bashar_audio), preferred_speech_manifest_sha256=digest(bashar_speech))
        old_hashes = {e['sha256'] for r in bashar['records'] for e in r['evidence'] if e['role'] == 'source_audio'}
        bashar_stats['unique_encoded_audio_hashes'] = len(old_hashes | {r['audio']['sha256'] for r in audio_rows})
        bashar_stats['official_unique_encoded_audio_hashes'] = len({r['audio']['sha256'] for r in audio_rows})
        bashar_stats['exact_media_duplicate_publications'] = len(audio_rows) - bashar_stats['official_unique_encoded_audio_hashes']
        if bashar_dispositions:
            dispositions = read(bashar_dispositions)['records']
            if len(dispositions) != 87 or len({r['recording_id'] for r in dispositions}) != 87:
                raise ValueError('Invalid resolved audio disposition frame')
            admitted = [r for r in dispositions if r['collection_status'] == 'retrieved']
            excluded = [r for r in dispositions if r['collection_status'] == 'excluded']
            unresolved = [r for r in dispositions if r['collection_status'] not in {'retrieved', 'excluded'}]
            if {r['recording_id'] for r in admitted} != audio_ids:
                raise ValueError('Disposition and acquisition source sets differ')
            unadmitted = [r for r in dispositions if r.get('retained_unadmitted_artifact')]
            preserved = {r['retained_unadmitted_artifact']['path']: {
                'source_id': r['recording_id'], 'disposition': r['eligibility_status'],
                'artifact': r['retained_unadmitted_artifact']} for r in unadmitted}
            for item in acquisition.get('superseded_media', []):
                preserved[item['artifact']['path']] = {'source_id': item['publication_id'],
                    'disposition': item['disposition'], 'artifact': item['artifact']}
            for item in preserved.values():
                artifact = item['artifact']
                p = Path(artifact['path'])
                if not p.is_file() or p.stat().st_size != artifact['bytes'] or digest(p) != artifact['sha256']:
                    raise ValueError('Preserved excluded/superseded media changed')
            for r in unadmitted:
                artifact = r['retained_unadmitted_artifact']
                p = Path(artifact['path'])
                if not p.is_file() or p.stat().st_size != artifact['bytes'] or digest(p) != artifact['sha256']:
                    raise ValueError('Preserved unadmitted artifact changed')
            bashar_stats.update(collection_resolution_status='all_candidate_dispositions_resolved' if not unresolved else 'unresolved_sources_remain',
                qualifying_audio_status='all_current_qualifying_sources_retained' if not unresolved else 'partial',
                download_status='resolved_with_explicit_exclusions' if not unresolved and excluded else bashar_stats['download_status'],
                unadmitted_audio_files=len(preserved),
                unadmitted_audio_bytes=sum(r['artifact']['bytes'] for r in preserved.values()),
                unadmitted_audio_editions=[{'source_id': r['source_id'], 'disposition': r['disposition'],
                    'bytes': r['artifact']['bytes'], 'sha256': r['artifact']['sha256']} for r in preserved.values()],
                superseded_transcript_editions=sum(bool(r.get('asr_result')) for r in acquisition.get('superseded_media', [])),
                excluded_publications=len(excluded), unresolved_publications=len(unresolved),
                exclusions=[{k: r.get(k) for k in ['source_id', 'source_url', 'eligibility_status', 'advertised_duration_seconds', 'observed_duration_seconds']} for r in excluded])
            extra_inputs['official_audio_dispositions_manifest_sha256'] = digest(bashar_dispositions)
        extra_inputs.update(official_audio_manifest_sha256=digest(bashar_audio),
            preferred_speech_manifest_sha256=digest(bashar_speech))
    collection = {'schema_version': 1, 'updated_at': now, 'corpora': {'ra': ra_stats, 'bashar': bashar_stats},
        'source_statuses': sources,
        'storage': {'destination': 'Private managed cloud workspace', 'permanent_chatgpt_account_storage': False,
            'google_drive_uploads': 0, 'public_media_uploads': 0},
        'scope': 'Dated receipt-based collection snapshot. The frozen primary statistical study remains 106 Ra sessions and 19 Bashar-related contexts. New acquisitions have separate analysis coverage.',
        'inputs': {f: digest(private / f) for f in ['ra/complete-transcript-manifest.json',
            'ra/audio-inventory-complete.json', 'bashar/corpus/manifest.json',
            'bashar/official-excerpt-corpus/manifest.json', 'bashar/official-platform-captions/manifest.json',
            'bashar/discovery/vimeo-oembed-census.json']}}
    collection['inputs'].update(extra_inputs)
    if (output / 'official-speech.json').is_file():
        supplemental = read(output / 'official-speech.json')
        safe_public(supplemental)
        if supplemental.get('schema_version') != 1 or supplemental.get('synthetic_fixture_run'):
            raise ValueError('Invalid supplemental release')
        collection['supplementary_studies'] = {'official_speech': 'official-speech.json'}
        collection['supplementary_sha256'] = digest(output / 'official-speech.json')
    safe_public(collection)
    (output / 'collection.json').write_text(json.dumps(collection, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'analysis_sha256': digest(output / 'data.json'), 'reading_sha256': digest(output / 'reading.json'),
        'figures': len(data['figures']), 'collection_sha256': digest(output / 'collection.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ra-audio', type=Path)
    parser.add_argument('--bashar-audio', type=Path)
    parser.add_argument('--bashar-speech', type=Path)
    parser.add_argument('--paired-editions', type=Path)
    parser.add_argument('--bashar-dispositions', type=Path)
    args = parser.parse_args()
    publish(args.private, args.output, args.ra_audio, args.bashar_audio, args.bashar_speech, args.paired_editions, args.bashar_dispositions)
