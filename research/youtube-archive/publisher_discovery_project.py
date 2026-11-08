#!/usr/bin/env python3
"""Verify saved first-party pages and publish compact discovery/delta metadata."""
import argparse
from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlsplit

from publisher_discovery import sha, bind, write

NAMES = {
    'magenta-pixie':'Magenta Pixie', 'elan-interactions':'Elan Interactions',
    'daniel-scranton':'Daniel Scranton', 'natalie-glasson-omna':'Natalie Glasson / OmNa',
    'channeling-erik-publisher':'Channeling Erik publisher site', 'laarkmaa':'Laarkmaa',
    'lyssa-royal-holt':'Lyssa Royal Holt', 'kristin-davies-medium':'Kristin Davies Medium',
    'bashar-official':'Bashar Communications', 'tracy-kumbera':'Tracy Kumbera',
    'athina-krol':'Athina Król', 'paul-selig':'Paul Selig', 'kryon-lee-carroll':'Kryon / Lee Carroll',
    'arkayla':'Arkayla', 'sam-the-illusionist':'Sam the Illusionist', 'crimson-circle':'Crimson Circle'}


def project(run, inventory, magenta, output):
    if output.exists(): raise ValueError('Use a fresh projection edition')
    source = run/'discovery-private.json'; data = json.loads(source.read_text())
    prior = {r['video_id'] for r in map(json.loads, inventory.read_text().splitlines()) if r}
    mag = {r['video_id'] for r in json.loads(magenta.read_text())['videos']}
    union = prior | mag; observed = {v['identity'] for v in data['videos']}
    if len(prior) != 942 or len(mag) != 1114 or len(union) != 2055:
        raise ValueError('Declared baseline changed; freeze a new comparison explicitly')
    receipts = {}; total_bytes = 0
    for r in data['page_receipts']:
        receipts[(r['publisher_id'],r['url'])] = r
        if r['status'] == 'retrieved':
            path = (run/r['artifact_file']).resolve()
            if not path.is_relative_to(run.resolve()): raise ValueError('Private page path escapes run')
            raw = path.read_bytes()
            if sha(raw) != r['sha256'] or len(raw) != r['bytes']: raise ValueError('Saved first-party source changed')
            total_bytes += len(raw)
    if len(receipts) != len(data['page_receipts']): raise ValueError('Repeated publisher/page receipt')
    for v in data['videos'] + data['account_links']:
        for e in v['evidence']:
            r = receipts[(v['publisher_id'],e['page_url'])]
            if r['status'] != 'retrieved' or e['page_sha256'] != r['sha256'] or e['retrieved_at'] != r['retrieved_at']:
                raise ValueError('Discovery evidence does not bind a retrieved source')
    result = dict(data)
    result['page_receipts'] = [{**{k:v for k,v in r.items() if k not in {'artifact_file','eligible_links'}},
                                'eligible_links_count':len(r['eligible_links'])} for r in data['page_receipts']]
    result['videos'] = [{**v,'not_in_two_declared_prior_ledgers':v['identity'] not in union,
                         'duration_seconds':None,'youtube_uploader_verified':False,'youtube_availability_verified':False,
                         'youtube_downloaded':False,'audio_downloaded_by_this_crawl':False} for v in data['videos']]
    result['baseline_comparison'] = {'baseline_scope':'Only the two named historical ID ledgers; not a claim that no other study ever mentioned an ID.',
                                    'inventory':bind(inventory),'magenta':bind(magenta),
                                    'inventory_ids':len(prior),'magenta_ids':len(mag),'overlap':len(prior&mag),'union_ids':len(union),
                                    'observed_distinct_ids':len(observed),'observed_already_in_union':len(observed&union),
                                    'observed_not_in_union':len(observed-union),'combined_observed_union':len(observed|union)}
    result['publisher_summaries'] = []
    for p in data['publisher_scopes']:
        pid=p['publisher_id']; rows=[r for r in data['page_receipts'] if r['publisher_id']==pid]
        vids={v['identity'] for v in data['videos'] if v['publisher_id']==pid}
        links=[v for v in data['account_links'] if v['publisher_id']==pid]
        normalized={(v['kind'],v['identity'].casefold() if v['kind']=='handle' else v['identity']) for v in links}
        result['publisher_summaries'].append({'publisher_id':pid,'publisher_name':NAMES[pid],'publisher_url':p['seed_urls'][0],
            'pages_attempted':len(rows),'pages_retrieved':sum(r['status']=='retrieved' for r in rows),
            'failed_pages':sum(r['status']=='failed' for r in rows),
            'sitemaps_retrieved':sum(r.get('xml_root') in {'sitemapindex','urlset'} for r in rows),
            'distinct_linked_youtube_ids':len(vids),'not_in_two_declared_prior_ledgers':len(vids-union),
            'literal_account_link_associations':len(links),'casefolded_account_route_associations':len(normalized),
            'youtube_uploads_total':None,'youtube_media_downloaded':0,
            'pages_pending':sum(r['publisher_id']==pid for r in data['pending'])})
    result['projection'] = {'private_source_manifest':bind(source),'producer_sha256':sha(Path(__file__).read_bytes()),
                            'all_retrieved_page_hashes_verified':True,'retained_source_page_bytes':total_bytes,
                            'link_lists_scope':'Full per-page eligible URL lists retained in the private source manifest; public receipts show exact counts.',
                            'resource_scope':'Wall-time and aggregate-byte thresholds are soft stops checked between batches; per-response limit and worker count are enforced.'}
    result['limitations'] += ['Literal account-link associations can contain case variants. Case-folded handle routes are not authenticated accounts or handle-to-UC resolutions.']
    output.mkdir(parents=True);write(output/'publisher-discovery.json',result)
    write(output/'output-manifest.json',{'schema_version':1,'module':'discovery','public_allowlist':[bind(output/'publisher-discovery.json')]})
    print(json.dumps({'output':str(output),'counts':result['counts'],'baseline_comparison':result['baseline_comparison'],
                      'artifact':bind(output/'publisher-discovery.json')}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True);p.add_argument('--magenta',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();project(a.run,a.inventory,a.magenta,a.output)
