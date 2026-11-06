#!/usr/bin/env python3
"""Create transparent per-publisher sample metrics from frozen Atlas evidence."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = ROOT / 'dist/analysis/channel-metrics.csv'
VIDEOS = ROOT / 'dist/analysis/video-observations.csv'
OUT = Path(__file__).resolve().parent


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value, integer=False):
    if value in ('', None):
        return None
    return int(value) if integer else float(value)


def main():
    channels, videos = read_csv(CHANNELS), read_csv(VIDEOS)
    if len({v['id'] for v in videos}) != len(videos):
        raise ValueError('Duplicate video IDs in frozen input')
    per = {}
    for v in videos:
        if v['channelId']:
            per.setdefault(v['channelId'], []).append(v)
    result = []
    for ch in channels:
        group = per.get(ch['id'], [])
        count = number(ch['videoCount'], True)
        durations = number(ch['durationCount'], True)
        if count != len(group):
            raise ValueError(f"Video count mismatch for {ch['id']}: {count} != {len(group)}")
        if durations != sum(bool(v['durationSeconds']) for v in group):
            raise ValueError(f"Duration count mismatch for {ch['id']}")
        dated = [v for v in group if v['date']]
        newest = max(dated, key=lambda v: (v['date'], v['id'])) if dated else None
        result.append({
            'channel_id': ch['id'], 'channel_name': ch['name'], 'channel_url': ch['url'],
            'indexed_sample_video_count': count, 'known_duration_count': durations,
            'duration_coverage': number(ch['durationCoverage']),
            'mean_minutes': number(ch['meanMinutes']), 'median_minutes': number(ch['medianMinutes']),
            'sample_first_date': ch['firstDate'] or None, 'sample_last_date': ch['lastDate'] or None,
            'newest_indexed_video_url': newest['url'] if newest else None,
            'newest_indexed_video_title': newest['title'] if newest else None,
            'caption_sample_count': number(ch['transcriptCount'], True),
            'metadata_source_status': ch['sourceStatus'],
        })
    result.sort(key=lambda c: (-c['indexed_sample_video_count'], c['channel_name'].casefold()))
    output = {
        'evidence_checked_at': '2026-10-23',
        'scope': 'Frozen purposive sample of indexed YouTube videos, not a census or current per-channel upload totals.',
        'limitations': [
            'Counts describe indexed sample videos associated with a publisher, not all videos available on YouTube.',
            'A publishing account, human medium and claimed entity are distinct units; some uploads are reposts or interviews.',
            'Most recent indexed video is the latest dated item in this sample, not verified latest on the channel.',
            'Means and medians use only known durations; empty values mean unknown, not zero.',
            'Caption counts are a purposively selected pilot, not the number of channel transcripts available.',
        ],
        'sources': [{'path':str(p.relative_to(ROOT)), 'sha256':digest(p)} for p in [CHANNELS,VIDEOS]],
        'summary': {'unique_indexed_video_ids':len(videos),
                    'assigned_indexed_video_ids':sum(c['indexed_sample_video_count'] for c in result),
                    'unassigned_indexed_video_ids':sum(not v['channelId'] for v in videos),
                    'publisher_rows':len(result), 'publishers_with_indexed_videos':sum(c['indexed_sample_video_count']>0 for c in result),
                    'publishers_with_known_durations':sum(c['known_duration_count']>0 for c in result),
                    'videos_with_known_durations':sum(bool(v['durationSeconds']) for v in videos)},
        'channels':result,
    }
    (OUT/'channel_metrics.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'channel_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0])); w.writeheader(); w.writerows(result)
    print(json.dumps(output['summary']))

if __name__ == '__main__':
    main()
