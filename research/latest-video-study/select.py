#!/usr/bin/env python3
"""Select first eligible upload from each captured yt-dlp channel listing.

Does not make network requests: a source listing must be obtained through the
project's approved, access-gated collection workflow. Preserve raw listings privately.
"""
import argparse, datetime, json, re
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('listing',type=Path,nargs='+',help='Full metadata channel listings in newest-first order')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=[]; seen=set()
    for path in a.listing:
        data=json.loads(path.read_text(encoding='utf-8'))
        channel=data.get('channel') or data.get('uploader') or data.get('title')
        selection=None
        for entry in data.get('entries',[]):
            if not isinstance(entry,dict): continue
            vid=entry.get('id',''); duration=entry.get('duration'); status=entry.get('live_status'); title=entry.get('title','')
            # Ambiguous live state, Shorts and insufficient metadata are held.
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid): continue
            if entry.get('media_type')!='video' or entry.get('is_short') is True or '#shorts' in title.lower(): continue
            if status in ('is_live','is_upcoming','post_live') or not isinstance(duration,(int,float)) or duration<300: continue
            selection={'id':vid,'channel':channel,'title':title,'url':'https://www.youtube.com/watch?v='+vid,'duration':duration,'listing_file':path.name,'selection':'first eligible recorded upload in provided listing order; subject to fresh runner verification'}; break
        if selection:
            if selection['id'] in seen: selection['duplicate_video_id']=True
            seen.add(selection['id'])
            result.append(selection)
        else: result.append({'channel':channel,'listing_file':path.name,'status':'no_eligible_video_in_listing'})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'selection_time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':[r for r in result if 'id' in r],'excluded':[r for r in result if 'id' not in r]},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Selected',sum('id' in r for r in result),'of',len(result),'channels; runner must verify metadata before downloading')
if __name__=='__main__': main()
