#!/usr/bin/env python3
"""Audit retained publisher/ASR bytes locally without publishing transcript text."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
HARVEST = HERE.parent
RAW = Path('/workspace/channels-et-raw').resolve()
checks = 0


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)


def load(path):
    return json.loads(path.read_text())


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-running-publisher-snapshot', action='store_true')
parser.add_argument('--publisher-only', action='store_true')
args = parser.parse_args()
publisher_path = HARVEST/'publisher_sources/publisher-summary.json'
publisher_sha = sha(publisher_path)
publisher = load(publisher_path)
check(args.allow_running_publisher_snapshot or publisher.get('terminal') is True,
      'Wait for a terminal publisher ledger before final verification')
plans = [p for p in (HARVEST/'publisher_sources').glob('*plan.json') if sha(p) == publisher['plan_sha256']]
check(len(plans) == 1, 'Exactly one retained plan matches the publisher ledger')
plan_path = plans[0]
plan = load(plan_path)
planned = {r['source_id']: r for r in plan['records']}
check(publisher['plan_sha256'] == sha(plan_path), 'Publisher plan binding')
saved = []
eligible_statuses = {'completed', 'saved_complete_publisher_response_with_duration_warning'}
for row in publisher['records']:
    if row['status'] not in eligible_statuses:
        continue
    ident = row['source_id']; original = planned[ident]
    path = Path(row['raw_local_path']).resolve()
    check(path.is_relative_to(RAW) and path.is_file(), ident+': actual external media')
    check(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], ident+': exact media bytes')
    check(0 < row['bytes'] <= publisher['per_file_cap_bytes'], ident+': per-file cap')
    for field in ('enclosure_url', 'episode_guid', 'feed_sha256', 'source_kind'):
        check(row[field] == original[field], ident+': '+field)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)], text=True))
    duration = float(probe['format']['duration'])
    check(math.isfinite(duration) and duration > 0 and any(x['codec_type']=='audio' for x in probe['streams']), ident+': finite audio')
    check(abs(duration-row['duration_seconds']) < .00001, ident+': duration receipt')
    check(row['original_index_edge']['youtube_edition_equivalence_verified'] is False, ident+': no automatic video-equivalence promotion')
    expected_size = original.get('rss_enclosure_length_bytes')
    warning = row.get('validation_outcome','').startswith('saved_complete_publisher_response_with_')
    if row['status'] == 'completed' and not warning:
        check(not expected_size or expected_size == row['bytes'], ident+': positive RSS size integrity')
        expected_duration = original.get('rss_duration_seconds')
        check(not expected_duration or abs(duration-expected_duration) <= max(10,expected_duration*.01), ident+': RSS duration integrity')
    else:
        check(row.get('http_status') == 200 and row.get('resumed_from_bytes') == 0
              and row.get('response_declared_remaining_bytes') == row['bytes'], ident+': complete current HTTP body')
        check(row.get('strict_validation_status') == 'validation_mismatch'
              and row.get('content_or_youtube_edition_equivalence_verified') is False
              and bool(row.get('review_amendment')), ident+': source-specific warning and amendment preserved')
    saved.append({'source_id': ident, 'status': row['status'], 'bytes': row['bytes'], 'sha256': row['sha256'],
                  'duration_seconds': duration, 'rss_metadata_warning': warning,
                  'nonattached_video_streams': sum(x['codec_type']=='video' and not x.get('disposition',{}).get('attached_pic') for x in probe['streams'])})

check(len(saved) == publisher['completed_audio_files'], 'Publisher saved-file total')
check(sum(r['bytes'] for r in saved) == publisher['completed_audio_bytes'], 'Publisher saved-byte total')
check(abs(sum(r['duration_seconds'] for r in saved)-publisher['completed_audio_seconds']) < .000001, 'Publisher duration total')
check(sum(r['rss_metadata_warning'] for r in saved) == publisher.get('warning_audio_files',0), 'Publisher explicit warning total')
if args.publisher_only:
    check(publisher_sha == sha(publisher_path), 'Publisher ledger stable throughout audit')
    report = {'status':'PASS','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'checks_passed':checks,'publisher_summary_sha256':publisher_sha,'plan_sha256':sha(plan_path),
              'publisher_terminal':publisher.get('terminal'),'planned_jobs':publisher.get('planned_jobs'),
              'verified_files':len(saved),'verified_bytes':sum(r['bytes'] for r in saved),
              'verified_duration_seconds':sum(r['duration_seconds'] for r in saved),
              'rss_metadata_warnings':sum(r['rss_metadata_warning'] for r in saved),'records':saved,
              'source_network_requests':0,'verifier_sha256':sha(Path(__file__)),
              'scope':'Actual saved bytes/hash/ffprobe/source metadata only; current publisher editions are not verified YouTube editions or human-validated speech.'}
    (HERE/'publisher-final-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
    raise SystemExit(0)

asr_path = HARVEST/'asr/summary.json'; asr_sha = sha(asr_path); asr = load(asr_path)
model_path = HARVEST/'asr/model-manifest.json'; model = load(model_path)
cache = Path(model['localCache']).resolve()
for item in model['files']:
    path = (cache/item['path']).resolve()
    check(path.is_relative_to(cache) and path.is_file(), 'Model file boundary')
    check(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'Model file bytes')
by_source = {r['source_id']: r for r in publisher['records']}
transcripts = []
for row in asr['records']:
    ident = row['sourceId']; source = by_source[ident]; output = Path(row['transcriptDirectory']).resolve()
    check(source['status'] in eligible_statuses and row['sourceAudioSha256'] == source['sha256']
          and row['sourceUrl'] == source['enclosure_url'], ident+': eligible acquisition binding')
    check(output.is_relative_to(RAW) and output.is_dir(), ident+': private output boundary')
    check(row['modelId'] == model['modelId'] and row['modelRevision'] == model['revision'], ident+': model pin')
    protocol = row['executionProtocol']
    check(protocol['sourceId'] == ident and protocol['sourceUrl'] == row['sourceUrl']
          and protocol['audioSha256'] == row['sourceAudioSha256'], ident+': execution source fields')
    check(protocol['versions'] == row['versions'] and protocol['cpuThreads'] == row['cpuThreads']
          and protocol['decoding'] == row['decoding'], ident+': executed runtime/settings fields')
    check(protocol['modelManifestSha256'] == sha(model_path), ident+': model manifest hash')
    check(hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest() == row['executionSignature'], ident+': execution signature')
    executed = HARVEST/'asr/executed-sources'/(protocol['scriptSha256']+'.py')
    check(executed.is_file() and sha(executed) == protocol['scriptSha256'], ident+': executed source retained')
    check(row['humanReviewed'] is False and row['speakerDiarizationPerformed'] is False and row['youtubeVideoEditionVerified'] is False, ident+': validation boundaries')
    check(len(row['outputs']) == 3 and {r['name'] for r in row['outputs']} == {'segments.jsonl','transcript.txt','transcript.srt'}, ident+': exact output set')
    for item in row['outputs']:
        path = output/item['name']
        check(path.resolve().is_relative_to(RAW) and path.is_file() and not path.is_symlink(), ident+': output boundary')
        check(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], ident+': output bytes')
    private_receipt = load(output/'receipt.json')
    check(private_receipt == {k:v for k,v in row.items() if k != 'transcriptDirectory'}, ident+': private/public receipt agreement')
    segments = [json.loads(line) for line in (output/'segments.jsonl').read_text().splitlines() if line]
    check(len(segments) == row['segments'], ident+': segment count')
    previous = -1
    for segment in segments:
        check(math.isfinite(segment['start']) and math.isfinite(segment['end'])
              and 0 <= segment['start'] <= segment['end'] <= row['sourceAudioDurationSeconds']+2
              and segment['start'] >= previous, ident+': finite monotonic segment bounds')
        previous = segment['start']
    text = '\n'.join(r['text'] for r in segments)+'\n'
    check(text == (output/'transcript.txt').read_text(), ident+': same-segment text')
    words = len(' '.join(r['text'] for r in segments).split())
    check(words == row['words'], ident+': word count')
    transcripts.append({'source_id':ident,'segments':len(segments),'words':words,
                        'scope':row['transcribedScope'],'source_sha256':row['sourceAudioSha256']})
full = [r for r in transcripts if r['scope'] == 'full_decoded_audio']
check(len(full) == asr['completedFullTranscripts'] and len(transcripts)-len(full) == asr['diagnosticClips'], 'ASR scope counts')
check(sum(r['segments'] for r in full) == asr['totalSegments'], 'ASR segment total')
check(sum(r['words'] for r in full) == asr['totalWords'], 'ASR word total')
check(publisher_sha == sha(publisher_path) and asr_sha == sha(asr_path), 'Ledger bytes stable throughout audit')
report = {'status':'PASS','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'checks_passed':checks,'publisher_summary_sha256':publisher_sha,'asr_summary_sha256':asr_sha,
          'publisher_terminal':publisher.get('terminal'),'publisher_planned_jobs':publisher.get('planned_jobs'),
          'verified_saved_publisher_files':len(saved),'verified_saved_publisher_bytes':sum(r['bytes'] for r in saved),
          'saved_publisher_records':saved,'verified_asr_records':transcripts,'source_network_requests':0,
          'verifier_sha256':sha(Path(__file__)),
          'scope':'Actual local files and saved-output mechanics only; no inference rerun, raw speech publication, human accuracy, speaker or video-edition validation.'}
(HERE/'saved-artifacts-final-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['saved_publisher_records','verified_asr_records']},indent=2))
