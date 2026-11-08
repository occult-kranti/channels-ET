#!/usr/bin/env python3
"""Audit published Ra MP3 headers without downloading bodies.

Portable successor to the privately frozen 7 November 2026 execution helper.
This code is not represented as the source of that earlier receipt. A new run
uses a new private output directory and preserves any unsuccessful responses.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from acquire_ra import audio_url_parts, parse_audio_links, private_root

PAUSE_STATUSES={401,403,407,429,451}

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    tmp=path.with_suffix(path.suffix+'.partial')
    with tmp.open('x') as stream:
        os.chmod(tmp,0o600);json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    os.replace(tmp,path)

def input_path(value):
    p=Path(value)
    if not p.is_absolute() or '..' in p.parts or any(q.is_symlink() for q in (p,*p.parents)):
        raise ValueError('An absolute non-symlink input path is required')
    if not p.is_file():raise ValueError('Input artifact is missing')
    return p

def frame_items(path):
    path=input_path(path);frame=json.loads(path.read_text())
    pages=frame.get('records',[])
    if frame.get('fixture_only') or frame.get('source_page_count')!=106 or len(pages)!=106 or frame.get('failures'):
        raise ValueError('A complete canonical actual-source player-page frame is required')
    if {p.get('session_number') for p in pages}!=set(range(1,107)):
        raise ValueError('Canonical sessions1 through106 must occur once each')
    items=[];seen=set()
    for page in pages:
        n=page['session_number'];raw=input_path(page['path'])
        if page.get('http_status')!=200 or page.get('source_page')!=f'https://www.lawofone.info/s/{n}?au=1':
            raise ValueError('Player-page source identity or response status differs')
        if raw.stat().st_size!=page['bytes'] or sha(raw)!=page['sha256']:
            raise ValueError('Frozen player-page bytes changed')
        urls=page['audio_urls']
        if len(urls)!=len(set(urls)) or set(parse_audio_links(raw.read_bytes(),n))!=set(urls):
            raise ValueError('Frame URLs differ from the actual published links')
        for url in urls:
            session,segment=audio_url_parts(url)
            if session!=n or url in seen:raise ValueError('Duplicate or misassigned audio source')
            seen.add(url);items.append({'session_number':n,'session_id':f'ra:session:{n:03d}',
                'segment_number':segment,'url':url,'source_page_sha256':page['sha256']})
    if not items or len(items)!=frame.get('published_audio_segments'):
        raise ValueError('Declared segment coverage differs from the source URLs')
    return sorted(items,key=lambda x:(x['session_number'],x['segment_number']))

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

class Gate:
    def __init__(self,rate,stop):self.interval=1/rate;self.stop=stop;self.lock=threading.Lock();self.last=0
    def before(self):
        with self.lock:
            if self.stop.is_set():return False
            if self.stop.wait(max(0,self.interval-(time.monotonic()-self.last))):return False
            self.last=time.monotonic();return True

def fetch_head(item,gate,stop):
    row={**item,'method':'HEAD','requested_at':None,'status':None,'content_length':None,'bytes':None,
        'content_type':None,'last_modified':None,'etag':None,'accept_ranges':None,'body_bytes_read':0}
    if not gate.before():return {**row,'retrieval_status':'not_attempted_after_global_pause'}
    row['requested_at']=now();response=None
    try:
        try:
            response=build_opener(NoRedirect()).open(Request(item['url'],method='HEAD',
                headers={'User-Agent':'Channels-ET-private-audio-inventory/1.0'}),timeout=30)
        except HTTPError as error:response=error
        row['status']=response.code
        row['content_type']=(response.headers.get('Content-Type') or '').split(';',1)[0].strip().lower()
        length=response.headers.get('Content-Length')
        row['content_length']=int(length) if length and re.fullmatch(r'[0-9]+',length.strip()) else None
        row['bytes']=row['content_length']
        for name,key in [('Last-Modified','last_modified'),('ETag','etag'),('Accept-Ranges','accept_ranges')]:
            value=response.headers.get(name);row[key]=value[:500] if value is not None else None
        row['retrieval_status']='head_verified' if row['status']==200 and row['content_type'] in {'audio/mpeg','audio/mp3'} and isinstance(row['content_length'],int) and 0<row['content_length']<=256*1024**2 else 'header_ineligible'
        if row['status'] in PAUSE_STATUSES:row['retrieval_status']='global_pause_http';stop.set()
        elif row['status']==503:row['retrieval_status']='isolated_503_no_retry'
        elif row['status'] in {301,302,303,307,308}:row['retrieval_status']='redirect_not_followed'
    except (URLError,TimeoutError,OSError) as error:
        row.update(retrieval_status='global_pause_transport',error_type=type(error).__name__)
        stop.set()
    finally:
        if response is not None:response.close()
    row['checked_at']=now();return row

def audit(frame_path,output,workers=2,requests_per_second=5):
    if workers not in (1,2) or not 0<requests_per_second<=6:
        raise ValueError('Use one or two workers and at most six requests per second')
    frame_path=input_path(frame_path);items=frame_items(frame_path);frame_hash=sha(frame_path)
    output=Path(output)
    if output.exists():raise ValueError('Choose a new private output directory; failed evidence is not overwritten')
    output=private_root(output);stop=threading.Event();gate=Gate(requests_per_second,stop)
    started_at=now();started=time.monotonic();records=[]
    config={'schema_version':1,'frame_sha256':frame_hash,'script_sha256':sha(Path(__file__)),
        'source_parser_sha256':sha(Path(__file__).with_name('acquire_ra.py')),
        'workers':workers,'maximum_global_requests_per_second':requests_per_second,'timeout_seconds':30,
        'method':'HEAD','automatic_retries':0,'body_reads':False,'redirects_followed':False,
        'scope':'Ordinary configured HTTPS/proxy/CA; no authentication, cookie collection or alternate egress.'}
    write(output/'configuration.json',config)
    def summary(final=False):
        good=[r for r in records if r['retrieval_status']=='head_verified'];known=sum(r['content_length'] for r in good)
        missing=len(items)-len(good)
        result={'schema_version':1,'kind':'ra-audio-head-inventory',
            'status':'paused' if stop.is_set() else 'completed' if final else 'running',
            'started_at':started_at,'checked_at':now(),
            'frame':{'path':str(frame_path),'sha256':frame_hash,'source_pages':106,'unique_published_urls':len(items)},
            'workers':workers,'maximum_global_requests_per_second':requests_per_second,
            'record_count':len(records),'attempted_urls':sum(r['requested_at'] is not None for r in records),
            'eligible_header_count':len(good),'missing_or_ineligible_header_count':missing,
            'known_total_bytes':known,'published_total_upper_bound_bytes':known if not missing else None,
            'upper_bound_scope':'Header-advertised compressed bytes at audit time; actual transfer must reverify sizes and enforce budgets. Missing headers prevent a complete observed bound.',
            'status_counts':dict(Counter(str(r['status']) for r in records)),
            'body_bytes_read':0,'downloads_performed':0,'automatic_retries':0,
            'paused_on_transport_rate_or_auth_failure':stop.is_set(),'elapsed_seconds':time.monotonic()-started,
            'script_sha256':config['script_sha256'],'source_parser_sha256':config['source_parser_sha256']}
        if final:result['records']=sorted(records,key=lambda x:(x['session_number'],x['segment_number']))
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(fetch_head,item,gate,stop) for item in items]
        for future in as_completed(futures):
            row=future.result();records.append(row)
            with (output/'header-results.jsonl').open('a') as stream:
                os.chmod(output/'header-results.jsonl',0o600);stream.write(json.dumps(row)+'\n')
            if len(records)%100==0:write(output/'progress.json',summary())
    if sha(frame_path)!=frame_hash:raise ValueError('Source frame changed during the header audit')
    result=summary(final=True);write(output/'head-inventory.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=2);parser.add_argument('--requests-per-second',type=float,default=5)
    args=parser.parse_args();result=audit(args.frame,args.output,args.workers,args.requests_per_second)
    print(json.dumps({k:v for k,v in result.items() if k not in {'records','frame','upper_bound_scope'}}))
    return 0 if result['missing_or_ineligible_header_count']==0 else 2

if __name__=='__main__':raise SystemExit(main())
