#!/usr/bin/env python3
"""Select the first provably eligible upload from newest-first local listings.

The downloader retains the final, source-bound admission decision. Unknown
newer entries hold a channel instead of falsely selecting an older upload.
No network requests are made by this script.
"""
import argparse
import datetime
import hashlib
import json
import math
import re
from pathlib import Path

VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
SHORT_TITLE = re.compile(r'(?i)#shorts?\b')


def classify(entry, channel_id):
    """Return eligible, excluded, or unresolved and a reason."""
    if not isinstance(entry, dict):
        return 'unresolved', 'non_object_listing_entry'
    vid = entry.get('id')
    if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
        return 'unresolved', 'missing_or_invalid_video_id'
    title = entry.get('title') or ''
    if not isinstance(title, str):
        return 'unresolved', 'invalid_title'
    urls = ' '.join(str(entry.get(k) or '') for k in ('webpage_url', 'original_url', 'url'))
    kind = entry.get('media_type')
    status = entry.get('live_status')
    duration = entry.get('duration')
    if entry.get('is_short') is True or kind == 'short' or '/shorts/' in urls or SHORT_TITLE.search(title):
        return 'excluded', 'short'
    if status in ('is_live', 'is_upcoming', 'post_live') or entry.get('is_live') is True:
        return 'excluded', 'live_or_upcoming'
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and 0 < duration < 300:
        return 'excluded', 'duration_below_five_minutes'
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(duration) or duration <= 0:
        return 'unresolved', 'unknown_duration'
    if channel_id and entry.get('channel_id') and entry['channel_id'] != channel_id:
        return 'unresolved', 'channel_id_mismatch'
    if kind != 'video' and not (kind == 'livestream' and status in ('was_live', 'not_live')):
        return 'unresolved', 'unknown_recorded_video_format'
    return 'eligible', 'eligible_subject_to_fresh_runner_review'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('listing', type=Path, nargs='+', help='Full metadata channel listings in newest-first order')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    records, excluded, seen = [], [], set()
    for path in a.listing:
        raw = path.read_bytes()
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('entries'), list):
            raise ValueError(f'{path}: expected a channel listing with entries list')
        channel = data.get('channel') or data.get('uploader') or data.get('title') or 'unknown'
        base = {'channel': channel, 'listing_file': path.name, 'listing_sha256': hashlib.sha256(raw).hexdigest(),
                'listing_retrieved_at': data.get('retrieved_at')}
        for entry in data['entries']:
            state, reason = classify(entry, data.get('channel_id'))
            if state == 'excluded':
                continue
            if state == 'unresolved':
                excluded.append({**base, 'status': 'held_unresolved_newer_entry', 'reason': reason,
                                 'video_id': entry.get('id') if isinstance(entry, dict) else None})
                break
            vid = entry['id']
            if vid in seen:
                excluded.append({**base, 'video_id': vid, 'status': 'duplicate_selected_video'})
                break
            seen.add(vid)
            records.append({**base, 'id': vid, 'title': entry.get('title') or '',
                            'url': 'https://www.youtube.com/watch?v=' + vid, 'duration': entry['duration'],
                            'selection': 'first provably eligible recorded upload in provided listing order; subject to fresh runner verification'})
            break
        else:
            excluded.append({**base, 'status': 'no_eligible_video_in_listing'})
    result = {'selection_time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'records': records, 'excluded': excluded}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Selected {len(records)} of {len(a.listing)} channels; runner must verify metadata before downloading')


if __name__ == '__main__':
    main()
