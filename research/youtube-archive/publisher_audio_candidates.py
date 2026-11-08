#!/usr/bin/env python3
"""Separate explicit audio eligibility from availability of a validated text template."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from publisher_discovery import bind, sha, write
from publisher_media_candidates import Template


def build(run, old_manifest, output):
    if output.exists():raise ValueError('Use a fresh immutable candidate edition')
    source=run/'discovery-private.json';data=json.loads(source.read_text())
    old=json.loads(old_manifest.read_text());old_urls={r.get('source',{}).get('audio_url') for r in old['records']}
    pilot_paths=[run.parent/'publisher-audio-candidate-01.json',run.parent/'additional-media-candidates-01.json']
    pilot_first=json.loads(pilot_paths[0].read_text());pilot_additional=json.loads(pilot_paths[1].read_text())
    pilot_urls=set(pilot_first['audio'])|{r['audio_url'] for r in pilot_additional['candidates']}
    if len(pilot_urls)!=3:raise ValueError('Expected three exact independently inspected pilot audio URLs')
    receipts={(r['publisher_id'],r['url']):r for r in data['page_receipts']}
    candidates=[];dispositions=[];seen={}
    for lead in sorted(data['paired_publisher_media_leads'],key=lambda r:r['page_url']):
        if lead['publisher_id']!='natalie-glasson-omna' or not lead['youtube_ids']:continue
        r=receipts[(lead['publisher_id'],lead['page_url'])];page=run/r['artifact_file'];raw=page.read_bytes()
        if sha(raw)!=r['sha256'] or len(raw)!=r['bytes']:raise ValueError('Retained source page changed')
        t=Template();t.feed(raw.decode('utf-8',errors='replace'))
        mp3={urljoin(r['url'],a['url']):a['label'] for a in t.anchors if re.search(r'\.mp3(?:$|\?)',a['url'],re.I)}
        problems=[];audio=None;label=None
        if len(mp3)!=1:problems.append('not_exactly_one_explicit_mp3_anchor')
        if len(lead['youtube_ids'])!=1:problems.append('not_exactly_one_observed_youtube_id')
        if re.search(r'/(?:shop|store|product|cart|checkout)(?:/|$)',urlsplit(r['url']).path):problems.append('shop_or_transaction_page_not_message')
        if len(mp3)==1:
            audio,label=next(iter(mp3.items()))
            if 'download' not in label.lower() or 'audio' not in label.lower():problems.append('explicit_download_audio_label_absent')
            if urlsplit(audio).hostname!='omna-shop.s3.eu-west-2.amazonaws.com':problems.append('unreviewed_audio_storage_host')
            if audio in old_urls:problems.append('exact_audio_url_already_in_old_229_manifest')
            if audio in seen:problems.append('exact_audio_url_duplicate_in_this_frame')
            if audio in pilot_urls:problems.append('exact_audio_url_in_separately_reviewed_pilots')
        if problems:
            dispositions.append({'page_url':r['url'],'page_sha256':r['sha256'],'audio_url':audio,'youtube_ids':lead['youtube_ids'],'reasons':problems});continue
        seen[audio]=r['url'];text_problems=[]
        if any(len(t.blocks.get(k,[]))!=1 for k in ('a959f86','8d74e16','0143f75')):
            text_problems.append('body_closing_or_attribution_template_mismatch')
        else:
            body=t.blocks['a959f86'][0];closing=t.blocks['8d74e16'][0];attribution=t.blocks['0143f75'][0]
            if len(body.split())<100 or not closing or 'Natalie Glasson' not in attribution or 'omna.org' not in attribution:
                text_problems.append('substantive_body_or_attribution_check_failed')
        text_ready=not text_problems
        candidates.append({'page_url':r['url'],'page_path':str(page),'page_sha256':r['sha256'],'page_bytes':r['bytes'],'title':r['title'],
            'audio_url':audio,'audio_link_label':label,'youtube_ids':lead['youtube_ids'],
            'audio_admission':'one_explicit_Download_Audio_MP3_link_on_retained_publisher_message_page',
            'text_status':'validated_template_available' if text_ready else 'publisher_text_pending_template_review',
            'text_hold_reasons':text_problems,'body_block_ids':['a959f86'] if text_ready else [],
            'closing_block_ids':['8d74e16'] if text_ready else [],'attribution_block_ids':['0143f75'] if text_ready else [],
            'template_visible_body_words':len(body.split()) if text_ready else None,
            'template_visible_closing_words':len(closing.split()) if text_ready else None,
            'full_body_manually_read_by_ai':False,'human_validated':False,'not_in_old_retained_audio_urls':True,
            'language_basis':'Publisher English-site context only; no new full manual reading or audio listening.',
            'edition_relation':'Exact page-offered publisher audio; co-located YouTube reference is not waveform equivalence or uploader verification.'})
    value={'schema_version':1,'status':'explicit_audio_candidates_with_separate_text_state','source_manifest':bind(source),'old_audio_manifest':bind(old_manifest),
        'pilot_audio_bindings':[bind(p) for p in pilot_paths], 'pilot_exclusion_key':'exact_audio_url_only; no YouTube-ID equivalence assumption',
        'producer_sha256':sha(Path(__file__).read_bytes()),'candidates':candidates,'dispositions':dispositions,
        'counts':{'audio_candidates':len(candidates),'validated_text_templates':sum(c['text_status']=='validated_template_available' for c in candidates),
                  'text_pending':sum(c['text_status']=='publisher_text_pending_template_review' for c in candidates),
                  'excluded_pages':len(dispositions),'media_requests':0},
        'limits':['Page-offered audio can be retained even while written-body extraction remains pending.',
                  'No title-based identity or acoustic equivalence was inferred; exact URL/source hashes bind the lead.',
                  'Every candidate still requires actual media retrieval, complete decoding and derivative verification by the media worker.']}
    write(output,value);print(json.dumps({'output':str(output),'sha256':sha(output.read_bytes()),**value['counts']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--old-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.run,a.old_manifest,a.output)
