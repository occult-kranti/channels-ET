#!/usr/bin/env python3
"""Source-first audit of a frozen analysis round (no producer code imported).

Usage: python check_source_precedence.py round3
Inputs are metadata only; no caption/transcript text is read or emitted.
"""
import csv,json,hashlib,datetime,collections,sys
from pathlib import Path
from urllib.parse import urlparse
HERE=Path(__file__).resolve().parent
ANALYSIS=HERE.parents[1]
ROUND=sys.argv[1] if len(sys.argv)>1 else 'round3'
if ROUND not in {'round1','round2','round3'}:raise SystemExit('Expected round1, round2 or round3')
DATA=ANALYSIS/'rounds'/ROUND/'data.json'
INPUT=ANALYSIS/'rounds'/ROUND/'fresh_metadata.json'
d=json.loads(DATA.read_text());channels={c['id']:c for c in d['channels']}
fresh=json.loads(INPUT.read_text())
acquired=collections.defaultdict(list)
for m in fresh:acquired[m['video_id']].append(m)
with (HERE/'raw-metadata/youtube_videos.csv').open(encoding='utf-8-sig',newline='') as f:raw={r['video_id']:r for r in csv.DictReader(f) if r['video_id']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def route(u):
    p=urlparse(u or '')
    path=p.path.rstrip('/')
    # YouTube handles are case-insensitive; numeric channel IDs are case-sensitive.
    return (p.netloc.lower().removeprefix('www.'),path if path.startswith('/channel/') else path.lower())
def seconds(s):return sum(x*60**i for i,x in enumerate(map(int,s.split(':')[::-1])))
def utcdate(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(datetime.timezone.utc).date().isoformat()
errors=[];counters=collections.Counter();fallback=[];duplicateAliases=[];aliases={}
for c in d['channels']:
    for a in c['aliases']:
        norm=route(a)
        if norm in aliases and aliases[norm]!=c['id']:duplicateAliases.append({'route':norm,'ids':[aliases[norm],c['id']]})
        aliases[norm]=c['id']
for v in d['videos']:
    used={p.get('htmlSha256') for p in v['provenance'] if p.get('kind')=='fresh_watch_metadata'}
    mm=[m for m in acquired[v['id']] if m.get('html_sha256') in used]
    if v.get('durationSource')=='fresh_watch_metadata':
        counters['freshDurations']+=1
        if not any(m.get('duration_seconds')==v['durationSeconds'] for m in mm):errors.append({'id':v['id'],'field':'fresh duration provenance/value'})
    if v.get('durationSource')=='claude_provider_metadata_unverified':
        counters['inheritedDurations']+=1;r=raw.get(v['id'])
        if not r or r['index_status']!='ok' or seconds(r['length'])!=v['durationSeconds']:errors.append({'id':v['id'],'field':'inherited duration source rule/value'})
    if v.get('dateSource')=='fresh_watch_metadata_UTC':
        counters['freshDates']+=1
        if not any(m.get('published_at') and utcdate(m['published_at'])==v['date'] for m in mm):errors.append({'id':v['id'],'field':'fresh UTC date provenance/value'})
    if v.get('titleSource')=='fresh_watch_metadata':
        counters['freshTitles']+=1
        if not any(m.get('title')==v['title'] for m in mm):errors.append({'id':v['id'],'field':'fresh title provenance/value'})
    if used:
        counters['freshAccountBindings']+=1;c=channels.get(v.get('channelId'))
        ar={route(a) for a in (c or {}).get('aliases',[])}
        matches=[m for m in mm if route(m.get('channel_url')) in ar or route('https://www.youtube.com/channel/'+(m.get('channel_id') or '')) in ar]
        if not matches:errors.append({'id':v['id'],'field':'fresh account route binding or frozen source missing','channelId':v.get('channelId')})
        if c and c['name'].startswith('Related account') and any(m.get('publisher') for m in matches):fallback.append(c['id'])
    if v.get('date') and v['date']>d['meta']['checkedAt']:errors.append({'id':v['id'],'field':'future publication date treated as observed','date':v['date']})
if duplicateAliases:errors.append({'field':'alias assigned to multiple account groups','duplicates':duplicateAliases})
vv={v['id']:v for v in d['videos']}
for vid in ['7wrxKKVLcBA','g88RqksSChM','t_OYRnFXEHQ','xxbzklPyRtg']:
    v=vv[vid]
    if v.get('titleSource')!='fresh_watch_metadata' or v['titleEligible'] or not v.get('titleVariants'):errors.append({'id':vid,'field':'localized-title provenance or English eligibility'})
if vv['MDdyY1WYmHY'].get('durationSource')!='fresh_watch_metadata' or vv['MDdyY1WYmHY']['durationSeconds']!=3206:errors.append({'id':'MDdyY1WYmHY','field':'fresh Athina duration'})
if ROUND=='round3':
    # A guest's name must not turn an interview publisher into the guest's account.
    guest=vv['KtvDmi4JWyc']; uploader=channels[guest['channelId']]
    if guest.get('observedPublisher')!='Multidimensional Soul' or any('UCQeHcVNo6CPWpgJaqEObrqA' in a for a in uploader['aliases']):
        errors.append({'id':'KtvDmi4JWyc','field':'Brad Johnson guest versus Multidimensional Soul uploader separation'})
report={'round':ROUND,'reviewMode':'fresh-context metadata-to-build audit','reviewedDataSha256':sha(DATA),'reviewedInputSha256':sha(INPUT),
 'rawVideoCsvSha256':sha(HERE/'raw-metadata/youtube_videos.csv'),'rawAccountCsvSha256':sha(HERE/'raw-metadata/youtube_channels.csv'),
 'metadataInputRecords':len(fresh),'checks':dict(counters),'errors':errors,'passed':not errors,
 'staleFallbackNames':sorted(set(fallback)),
 'boundary':'Same source acquisition reviewed by another worker; no claim of independent corroborating source. Durations marked unverified remain unverified.'}
(HERE/f'{ROUND}_source_precedence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='errors'},ensure_ascii=False,indent=2))
if errors:print(json.dumps({'errors':errors[:20],'errorCount':len(errors)},ensure_ascii=False,indent=2))
raise SystemExit(0 if report['passed'] else 1)
