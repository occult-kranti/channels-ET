#!/usr/bin/env python3
"""Prepare exact page-bound OmNa leads; performs no media or network request."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from publisher_discovery import bind, sha, write

PILOT_IDS = {'xsgGSzfdLaY','wnVpxf4SClg','1O3BcL4F6xc'}


class Template(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.depth=0; self.active=[]; self.blocks={};self.anchor=None;self.anchors=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='div':
            self.depth+=1
            if attrs.get('data-id') in {'a959f86','8d74e16','0143f75'}:
                self.active.append({'id':attrs['data-id'],'depth':self.depth,'parts':[]})
        if tag=='a' and attrs.get('href'):self.anchor={'url':attrs['href'],'parts':[]}
    def handle_endtag(self,tag):
        if tag=='div':
            for block in self.active[:]:
                if block['depth']==self.depth:
                    self.blocks.setdefault(block['id'],[]).append(' '.join(' '.join(block['parts']).split()));self.active.remove(block)
            self.depth-=1
        if tag=='a' and self.anchor:
            self.anchors.append({'url':self.anchor['url'],'label':' '.join(' '.join(self.anchor['parts']).split())});self.anchor=None
    def handle_data(self,value):
        for block in self.active:block['parts'].append(value)
        if self.anchor:self.anchor['parts'].append(value)


def build(run, old_audio_manifest, output):
    if output.exists():raise ValueError('Use a fresh candidate manifest')
    source=run/'discovery-private.json';data=json.loads(source.read_text())
    old=json.loads(old_audio_manifest.read_text());old_urls={r.get('source',{}).get('audio_url') for r in old['records']}
    receipts={(r['publisher_id'],r['url']):r for r in data['page_receipts']}
    accepted=[];dispositions=[];seen_audio={}
    for lead in data['paired_publisher_media_leads']:
        if lead['publisher_id']!='natalie-glasson-omna' or not lead['youtube_ids']:continue
        r=receipts[(lead['publisher_id'],lead['page_url'])];path=run/r['artifact_file'];raw=path.read_bytes()
        if sha(raw)!=r['sha256'] or len(raw)!=r['bytes']:raise ValueError('Publisher page changed')
        parsed=Template();parsed.feed(raw.decode('utf-8',errors='replace'))
        mp3={urljoin(r['url'],a['url']):a['label'] for a in parsed.anchors if re.search(r'\.mp3(?:$|\?)',a['url'],re.I)}
        reasons=[]
        if len(mp3)!=1:reasons.append('not_exactly_one_explicit_mp3_anchor')
        if len(lead['youtube_ids'])!=1:reasons.append('not_exactly_one_observed_youtube_id')
        if any(len(parsed.blocks.get(k,[]))!=1 for k in ('a959f86','8d74e16','0143f75')):reasons.append('body_closing_or_attribution_template_mismatch')
        if not reasons:
            audio,label=next(iter(mp3.items()));body=parsed.blocks['a959f86'][0];closing=parsed.blocks['8d74e16'][0];attribution=parsed.blocks['0143f75'][0]
            if 'download' not in label.lower() or 'audio' not in label.lower():reasons.append('download_audio_label_not_present')
            if urlsplit(audio).hostname!='omna-shop.s3.eu-west-2.amazonaws.com':reasons.append('unreviewed_direct_audio_host')
            if len(body.split())<100 or not closing or 'Natalie Glasson' not in attribution or 'omna.org' not in attribution:reasons.append('substantive_body_or_attribution_check_failed')
            if audio in old_urls:reasons.append('exact_audio_url_already_in_old_229_manifest')
            if set(lead['youtube_ids'])&PILOT_IDS:reasons.append('one_of_three_separately_reviewed_pilots')
            if audio in seen_audio:reasons.append('exact_audio_url_duplicate_in_this_frame')
        if reasons:
            dispositions.append({'page_url':r['url'],'page_sha256':r['sha256'],'reasons':reasons,'youtube_ids':lead['youtube_ids']});continue
        seen_audio[audio]=r['url']
        accepted.append({'page_url':r['url'],'page_path':str(path),'page_sha256':r['sha256'],'page_bytes':r['bytes'],
                         'title':r['title'],'audio_url':audio,'audio_link_label':label,'youtube_ids':lead['youtube_ids'],
                         'body_block_ids':['a959f86'],'closing_block_ids':['8d74e16'],'attribution_block_ids':['0143f75'],
                         'template_visible_body_words':len(body.split()),'template_visible_closing_words':len(closing.split()),
                         'reading_status':'automatic_template_check_not_manual_reading','full_body_manually_read_by_ai':False,'human_validated':False,
                         'language_basis':'Publisher English-site/template context; no new full manual reading or audio listening.',
                         'not_in_old_retained_audio_urls':True,
                         'edition_relation':'Same publisher page links written message, direct audio and YouTube ID; waveform/text equivalence not established.'})
    result={'schema_version':1,'status':'automatic_page_bound_candidates_not_downloads','source_manifest':bind(source),'old_audio_manifest':bind(old_audio_manifest),
            'producer_sha256':sha(Path(__file__).read_bytes()),'candidates':sorted(accepted,key=lambda r:r['page_url']),
            'dispositions':dispositions,'counts':{'accepted_candidates':len(accepted),'held_or_excluded_pages':len(dispositions),'media_requests':0},
            'limits':['Candidates are template checks, not new manual close readings or authenticated speakers.',
                      'The media owner must verify every original audio and completed derivative; these records are not retention receipts.',
                      'The three separately reviewed pilots and exact old audio URL matches are excluded; no title-only deduplication was used.']}
    write(output,result);print(json.dumps({'output':str(output),'sha256':sha(output.read_bytes()),**result['counts']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--old-audio-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.run,a.old_audio_manifest,a.output)
