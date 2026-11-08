#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from build_public import verify, inspect, sha
from verify_inventory import verify as verify_inventory
from verify_text_recovery import verify as verify_text_recovery
from verify_publisher_media import verify as verify_publisher_media


def verify_publisher_text_union(root):
    media = inspect((root / 'publisher-media.json').read_bytes())
    recovery = inspect((root / 'publisher-text-recovery.json').read_bytes())
    editions = {}; media_keys = set()
    for row in media['records']:
        key = (row['record_id'], row['page_url'], row['page_sha256']); media_keys.add(key)
        if row['written']['status'] == 'retained_publisher_written_edition':
            editions[key] = (row['written']['sha256'], row['written']['words'])
    matched = 0
    for row in recovery['records']:
        if row['status'] != 'publisher_written_message_recovered': continue
        key = (row['record_id'], row['page_url'], row['page_sha256'])
        value = (row['body_sha256'], row['words'])
        if key in editions and editions[key] != value:
            raise ValueError('Conflicting written-body edition in publisher overlay')
        editions[key] = value; matched += key in media_keys
    return {'distinct_publisher_written_editions': len(editions),
        'words': sum(value[1] for value in editions.values()), 'recovery_editions_with_exact_media_page_join': matched,
        'scope': 'Exact page/record body availability; not word-aligned transcripts, ASR or acoustic equivalence.'}


def verify_cross_bindings(site):
    root = Path(site) / 'dist/youtube-archive'
    inventory_raw = (root / 'inventory.json').read_bytes()
    inventory = inspect(inventory_raw)
    collection = inspect((root / 'collector-status.json').read_bytes())
    discovery_raw = (root / 'publisher-discovery.json').read_bytes()
    discovery = inspect(discovery_raw)
    binding = collection['inventory_binding']
    if binding['sha256'] != sha(inventory_raw) or binding['bytes'] != len(inventory_raw):
        raise ValueError('Collector does not bind this exact inventory')
    aids = {a['account_id'] for a in inventory['accounts']}
    vids = {v['video_id'] for v in inventory['videos']}
    if len(aids) != len(inventory['accounts']) or len(vids) != len(inventory['videos']):
        raise ValueError('Duplicate inventory identities')
    if len(aids) != inventory['coverage']['accounts'] or len(vids) != inventory['coverage']['unique_observed_video_ids']:
        raise ValueError('Inventory coverage arithmetic differs')
    collector_accounts = {a['account_id'] for a in collection['accounts']}
    if len(collector_accounts) != len(collection['accounts']):
        raise ValueError('Duplicate collector account identities')
    if collector_accounts != aids:
        raise ValueError('Collector account set differs from input inventory')
    collected_ids = {v['video_id'] for v in collection['videos']}
    if len(collected_ids) != len(collection['videos']):
        raise ValueError('Duplicate collector video identities')
    if not vids <= collected_ids or len(collected_ids) != collection['coverage']['distinct_observed_video_ids']:
        raise ValueError('Collector omitted indexed IDs or mismatched its denominator')
    if {v['identity'] for v in discovery['videos']} - vids:
        raise ValueError('Published inventory omits this discovery edition IDs')
    if not any(r['sha256'] == sha(discovery_raw) for r in inventory['inputs']):
        raise ValueError('Inventory does not bind this exact discovery edition')
    if collection['network_gate']['status'] != 'passed':
        if any(collection['coverage'].get(k, 0) for k in ('tab_requests_this_run', 'metadata_requests_this_run', 'media_requests_this_run', 'caption_requests_this_run')):
            raise ValueError('Current-run requests proceeded after shared gateway gate')
    video_map = {v['video_id']: v for v in collection['videos']}
    for account in collection['accounts']:
        for kind in ('retained_video_ids', 'retained_audio_ids', 'retained_caption_ids', 'retained_transcript_ids'):
            for vid in account[kind]:
                owner = video_map[vid]['verified_owner_channel_id']
                if not owner or owner != account['channel_id']:
                    raise ValueError('Retained artifact credited to an unverified uploader')
    return {'inventory_accounts': len(aids), 'inventory_video_ids': len(vids),
        'collector_video_ids': len(collected_ids), 'discovery_ids': len({v['identity'] for v in discovery['videos']}),
        'scope': 'Exact producer editions, ID inclusion, account sets, stage denominators and uploader-credit checks.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Verify published archive metadata, exact allowlist and module bindings.')
    p.add_argument('--site', required=True, type=Path)
    site = p.parse_args().site
    result = {**verify(site), 'inventory': verify_inventory(site / 'dist/youtube-archive'),
        'cross_bindings': verify_cross_bindings(site)}
    if (site / 'dist/youtube-archive/publisher-text-recovery.json').exists():
        result['publisher_text'] = verify_text_recovery(site / 'dist/youtube-archive')
    if (site / 'dist/youtube-archive/publisher-media.json').exists():
        result['publisher_media'] = verify_publisher_media(site / 'dist/youtube-archive')
        if 'publisher_text' in result:
            result['publisher_text_union'] = verify_publisher_text_union(site / 'dist/youtube-archive')
    print(json.dumps(result))
