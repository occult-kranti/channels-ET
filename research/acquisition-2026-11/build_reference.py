#!/usr/bin/env python3
"""Build a resumable channel/video acquisition reference from current artifacts.

Observed inventory is not a full-channel census. uploaded_total remains null
unless an authoritative count exists. Actual audio/ASR states are joined from
hash-verified receipts; no progress is inferred from metadata alone.
"""
import csv
import datetime
import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(os.environ['CHANNELS_ET_AUDIT_ROOT'])
RAW = Path(os.environ['CHANNELS_ET_RAW_ROOT']) / 'youtube-audio'
OUT = ROOT / 'research/acquisition-2026-11'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_json(path):
    return json.loads(path.read_text())


def write_csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    accounts = jsonl(AUDIT / 'youtube-accounts.jsonl')
    videos = jsonl(AUDIT / 'youtube-videos.jsonl')
    plan = jsonl(ROOT / 'research/expansion-2026/acquisition/plan.jsonl')
    plan_by_id = {row['video_id']: row for row in plan}
    ledger_path = OUT / 'acquisition-ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'records': []}
    audio_by_id = {r.get('video_id', r.get('videoId')): r for r in ledger['records']}
    # Analysis state is joined from the analysis workstream's own verified
    # outputs; pending is the default and nothing is inferred from metadata.
    analyzed_ids = set()
    analysis_index = OUT / 'analysis' / 'sources-index.csv'
    analysis_verification = OUT / 'analysis' / 'verification.json'
    analysis_verified = False
    candidate_terminal = None
    if analysis_verification.exists():
        try:
            analysis_verified = json.loads(analysis_verification.read_text()).get('nFailed') == 0
        except Exception:
            analysis_verified = False
    if analysis_verified and analysis_index.exists():
        with analysis_index.open(newline='', encoding='utf-8') as handle:
            analyzed_ids = {row['video_id'] for row in csv.DictReader(handle)}
        analysis_payload = json.loads((OUT / 'analysis' / 'analysis.json').read_text())
        candidate_terminal = analysis_payload['validation']['terminalStateCounts']
    account_by_id = {a['account_id']: a for a in accounts}
    supplement_path = OUT / 'supplemental-candidates.json'
    if supplement_path.exists():
        for row in json.loads(supplement_path.read_text()):
            publisher = row['publisher']
            aid = next((aid for account in account_by_id.items()
                        if account.get('display_name') == publisher),
                       'supplement-' + re.sub(r'[^a-z0-9]+', '-', publisher.lower()).strip('-'))
            if aid not in account_by_id:
                account_by_id[aid] = {
                    'account_id': aid, 'display_name': publisher,
                    'urls': [], 'identity_status': 'supplemental_public_playlist',
                    'inclusion_reason': 'Official public playlist/feed candidate; not a complete channel census.',
                }
                accounts.append(account_by_id[aid])
            videos.append({
                'video_id': row['video_id'], 'source_url': row['source_url'],
                'title': row['title'], 'entity_labels': [row['entity']],
                'historical_watch_observations': [{'publisher': publisher}],
                'associated_account_ids': [aid],
                'duration_seconds': row.get('duration_seconds'),
                'policy_decision': {'status': 'eligible', 'bashar_attribution': False},
                'selection': row.get('selection'),
                'rightsStatus': row.get('rightsStatus', 'redistribution_review_required'),
            })
    deduped = {}
    for video in videos:
        vid = video['video_id']
        if vid not in deduped:
            deduped[vid] = video
            continue
        current = deduped[vid]
        def selection_score(row):
            selected = row.get('selection')
            if selected:
                return {'selected_default': 5, 'eligible': 4,
                        'candidate_unreviewed': 3, 'not_selected': 2}.get(selected, 1)
            return 5 if plan_by_id.get(row['video_id'], {}).get('counts_block', {}).get('selected') else 1
        if selection_score(video) > selection_score(current):
            base, other = video, current
        else:
            base, other = current, video
        preferred_selection = base.get('selection') or ('selected_default' if selection_score(base) >= 5 else other.get('selection'))
        base['selection'] = preferred_selection
        base['associated_account_ids'] = sorted(set(base.get('associated_account_ids', []) + other.get('associated_account_ids', [])))
        base['entity_labels'] = sorted(set(base.get('entity_labels', []) + other.get('entity_labels', [])))
        if not base.get('duration_seconds') and other.get('duration_seconds') is not None:
            base['duration_seconds'] = other['duration_seconds']
        observations = base.get('historical_watch_observations', []) + other.get('historical_watch_observations', [])
        unique_observations = {}
        for observation in observations:
            key = (observation.get('published_at'), observation.get('publisher'))
            unique_observations[key] = observation
        base['historical_watch_observations'] = list(unique_observations.values())
        deduped[vid] = base
    videos = list(deduped.values())
    video_rows = []
    for video in videos:
        vid = video['video_id']
        metadata_duration = video.get('duration_seconds')
        plan_row = plan_by_id.get(vid, {})
        selected = bool(plan_row.get('counts_block', {}).get('selected'))
        ledger_audio = audio_by_id.get(vid, {})
        measured_duration = ledger_audio.get('duration_seconds', ledger_audio.get('durationSeconds'))
        duration = metadata_duration if isinstance(metadata_duration, (int, float)) else measured_duration
        duration_source = ('inherited_metadata' if isinstance(metadata_duration, (int, float))
                           else 'ffprobe_acquired_audio' if isinstance(measured_duration, (int, float))
                           else 'unavailable')
        if not isinstance(duration, (int, float)):
            eligibility = 'held_duration_unknown'
        elif duration < 300:
            eligibility = 'excluded_under_300'
        elif video.get('policy_decision', {}).get('status') == 'excluded_duration':
            eligibility = 'excluded_duration'
        elif video.get('policy_decision', {}).get('status') != 'eligible':
            eligibility = 'held_policy_review'
        else:
            eligibility = 'eligible'
        bashar = (plan_row.get('classification') == 'explicit_bashar_association'
                  or bool(video.get('policy_decision', {}).get('bashar_attribution'))
                  or 'Bashar' in video.get('entity_labels', []))
        selection = video.get('selection') or ('selected_default' if selected else ('held_bashar_cap' if bashar and eligibility == 'eligible' else 'not_selected'))
        audio = audio_by_id.get(vid, {})
        audio_receipt = RAW / vid / 'acquisition.json'
        asr_receipt = RAW / vid / 'asr-receipt.json'
        asr = json.loads(asr_receipt.read_text()) if asr_receipt.exists() else {}
        rendered = RAW.parent / 'youtube-transcripts' / vid / 'transcript.json'
        rendered_exists = rendered.exists()
        upload_dates = [o.get('published_at') or o.get('retrieved_at') for o in video.get('historical_watch_observations', [])]
        upload_date = next((d for d in upload_dates if d), None)
        account = account_by_id.get((video.get('associated_account_ids') or [None])[0], {})
        audio_state = ('completed' if (RAW / vid / 'audio.mp3').exists()
                       else 'held_route_limit_over_150_minutes'
                       if selection == 'held_route_limit_over_150_minutes'
                       else audio.get('status', 'pending'))
        asr_state = (asr.get('status') if asr.get('status')
                     else 'not_applicable_under_300' if audio.get('status') == 'excluded_under_300'
                     else 'not_attempted_route_limit'
                     if selection == 'held_route_limit_over_150_minutes' else 'pending')
        if vid in analyzed_ids:
            analysis_state = 'analysis_completed'
        elif asr.get('status') == 'excluded_language_mismatch':
            analysis_state = 'analysis_excluded_language_mismatch'
        elif audio.get('status') == 'excluded_under_300':
            analysis_state = 'analysis_excluded_under_300'
        elif selection == 'held_route_limit_over_150_minutes':
            analysis_state = 'analysis_held_route_limit_over_150_minutes'
        else:
            analysis_state = 'pending_analysis'
        video_rows.append({
            'video_id': vid,
            'source_url': video.get('source_url') or f'https://www.youtube.com/watch?v={vid}',
            'title': video.get('title') or '',
            'publisher': (video.get('historical_watch_observations') or [{}])[0].get('publisher') or account.get('display_name') or '',
            'associated_account_ids': ';'.join(video.get('associated_account_ids') or []),
            'upload_date': upload_date or '',
            'duration_seconds': duration if duration is not None else '',
            'duration_source': duration_source,
            'entity_labels': ';'.join(video.get('entity_labels') or []),
            'eligibility': eligibility,
            'selection': selection,
            'bashar_associated': str(bashar).lower(),
            'audio_status': audio_state,
            'audio_bytes': (RAW / vid / 'audio.mp3').stat().st_size if (RAW / vid / 'audio.mp3').exists() else audio.get('bytes', 0),
            'audio_sha256': audio.get('sha256', audio.get('audioSha256', '')),
            'audio_duration_seconds': audio.get('duration_seconds', audio.get('durationSeconds', '')),
            'asr_status': asr_state,
            'asr_words': asr.get('wordCount', 0),
            'asr_segments': asr.get('segmentCount', 0),
            'rendered_subtitle_status': 'provider_rendered' if rendered_exists else 'not_established',
            'analysis_status': analysis_state,
            'rights_status': 'redistribution_review_required',
            'storage_audio': f'cloud-raw://youtube-audio/{vid}/audio.mp3' if (RAW / vid / 'audio.mp3').exists() else '',
            'storage_transcript': f'cloud-raw://youtube-audio/{vid}/asr-transcript.txt' if asr.get('status') == 'completed' else '',
        })
    candidate_rows = json.loads((OUT / 'all-candidates.json').read_text())
    reference_by_id = {row['video_id']: row for row in video_rows}
    selection_mismatch = [row['video_id'] for row in candidate_rows
                          if reference_by_id[row['video_id']]['selection'] != row['selection']]
    if selection_mismatch:
        raise RuntimeError(f'Candidate/reference selection mismatch: {selection_mismatch}')
    video_rows.sort(key=lambda r: (r['selection'] != 'selected_default', r['eligibility'] != 'eligible', r['associated_account_ids'], r['video_id']))
    channel_rows = []
    for account in accounts:
        vids = [v for v in video_rows if account['account_id'] in v['associated_account_ids'].split(';')]
        channel_rows.append({
            'account_id': account['account_id'],
            'display_name': account.get('display_name') or '',
            'urls': ';'.join(account.get('urls') or []),
            'identity_status': account.get('identity_status') or '',
            'observed_videos': len(vids),
            'eligible_videos': sum(v['eligibility'] == 'eligible' for v in vids),
            'selected_default_videos': sum(v['selection'] == 'selected_default' for v in vids),
            'audio_downloaded_videos': sum(v['audio_status'] == 'completed' for v in vids),
            'asr_completed_videos': sum(v['asr_status'] == 'completed' for v in vids),
            'rendered_subtitle_videos': sum(v['rendered_subtitle_status'] == 'provider_rendered' for v in vids),
            'analysis_completed_videos': sum(v['analysis_status'] == 'analysis_completed' for v in vids),
            'analysis_excluded_videos': sum(v['analysis_status'].startswith('analysis_excluded_') for v in vids),
            'route_limit_held_videos': sum(v['analysis_status'] == 'analysis_held_route_limit_over_150_minutes' for v in vids),
            'observed_duration_seconds': round(sum(v['duration_seconds'] for v in vids if isinstance(v['duration_seconds'], (int, float))), 3),
            'uploaded_total': '',
            'enumeration_status': 'observed_inventory_not_full_channel_census',
            'entity_labels': ';'.join(sorted({label for v in vids for label in v['entity_labels'].split(';') if label})),
            'notes': account.get('inclusion_reason') or '',
        })
    channel_rows.sort(key=lambda r: (-r['observed_videos'], r['display_name'], r['account_id']))
    account_sizes = [len([a for a in v['associated_account_ids'].split(';') if a]) for v in video_rows]
    multi_account_videos = sum(n > 1 for n in account_sizes)
    extra_memberships = sum(max(0, n - 1) for n in account_sizes)
    unattributed_videos = sum(n == 0 for n in account_sizes)
    named_memberships = sum(account_sizes)
    account_reconciliation = {
        'uniqueVideoRecords': len(video_rows),
        'namedAccountVideoMemberships': named_memberships,
        'unattributedVideoRecords': unattributed_videos,
        'membershipsIncludingUnattributedRow': named_memberships + unattributed_videos,
        'multiAccountVideos': multi_account_videos,
        'extraMembershipsFromMultiAccountVideos': extra_memberships,
        'formula': 'unique videos = named memberships + unattributed - extra multi-account memberships',
        'note': 'Account-row counts describe memberships and are not additive to unique-video headline totals.',
    }
    assert named_memberships + unattributed_videos - extra_memberships == len(video_rows)
    video_fields = ['video_id', 'source_url', 'title', 'publisher', 'associated_account_ids',
                    'upload_date', 'duration_seconds', 'duration_source', 'entity_labels', 'eligibility', 'selection',
                    'bashar_associated', 'audio_status', 'audio_bytes', 'audio_sha256',
                    'audio_duration_seconds', 'asr_status', 'asr_words', 'asr_segments',
                    'rendered_subtitle_status', 'analysis_status', 'rights_status',
                    'storage_audio', 'storage_transcript']
    channel_fields = ['account_id', 'display_name', 'urls', 'identity_status', 'observed_videos',
                      'eligible_videos', 'selected_default_videos', 'audio_downloaded_videos',
                      'asr_completed_videos', 'rendered_subtitle_videos', 'analysis_completed_videos',
                      'analysis_excluded_videos', 'route_limit_held_videos', 'observed_duration_seconds', 'uploaded_total', 'enumeration_status',
                      'entity_labels', 'notes']
    write_csv(OUT / 'video-reference.csv', video_fields, video_rows)
    write_csv(OUT / 'channel-reference.csv', channel_fields, channel_rows)
    summary = {
        'updatedAt': NOW,
        'observedVideos': len(video_rows),
        'observedAccounts': len(channel_rows),
        'eligibilityCounts': dict(Counter(v['eligibility'] for v in video_rows)),
        'selectionCounts': dict(Counter(v['selection'] for v in video_rows)),
        'audioStatusCounts': dict(Counter(v['audio_status'] for v in video_rows)),
        'asrStatusCounts': dict(Counter(v['asr_status'] for v in video_rows)),
        'renderedSubtitleCounts': dict(Counter(v['rendered_subtitle_status'] for v in video_rows)),
        'analysisStatusCounts': dict(Counter(v['analysis_status'] for v in video_rows)),
        'candidateTerminal': candidate_terminal,
        'accountReconciliation': account_reconciliation,
        'audioBytes': sum(v['audio_bytes'] for v in video_rows),
        'audioDurationSeconds': round(sum(v['audio_duration_seconds'] for v in video_rows if v['audio_status'] in ('completed', 'excluded_language_mismatch') and isinstance(v['audio_duration_seconds'], (int, float))), 3),
        'asrWords': sum(v['asr_words'] for v in video_rows),
        'asrSegments': sum(v['asr_segments'] for v in video_rows),
        'uploadedTotal': None,
        'rightsStatus': dict(Counter(v['rights_status'] for v in video_rows)),
        'caveats': [
            'Observed inventory is not a complete upload census; uploaded_total is null.',
            'Bashar cap is exactly 100 across all accounts combined; other channels have no cap.',
            'Raw audio and full third-party transcripts remain private research storage pending source-specific redistribution rights.',
        ],
    }
    (OUT / 'reference-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
