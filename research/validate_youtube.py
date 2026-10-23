"""Validate index attribution, windows, deduplication and booking-table completeness."""
import json,re
from pathlib import Path
from datetime import date
R=Path(__file__).resolve().parent.parent
d=json.loads((R/'dist/data.json').read_text());yt=d['youtube'];profiles={p['id']:p for p in d['profiles']};sources={s['id'] for s in d['sources']}
accounts={a['id']:a for a in yt['accounts']}
assert len(accounts)==len(yt['accounts'])
assert len({v['videoId'] for v in yt['videos']})==len(yt['videos'])
assert len({v['id'] for v in yt['videos']})==len(yt['videos'])
for kind in ['accounts','videos']:
 for row in yt[kind]:
  assert row['profileIds'] and set(row['profileIds'])<=profiles.keys(),row
  assert row['sourceIds'] and set(row['sourceIds'])<=sources,row
  assert row['url'].startswith('https://'),row
  if kind=='accounts':assert row['verification'],row
  else:
   assert re.fullmatch(r'[A-Za-z0-9_-]{11}',row['videoId']),row
   assert row.get('accountId') is None or row['accountId'] in accounts,row
   assert row.get('dateBasis') and row.get('contentBasis'),row
   dt=row.get('publishedAt')
   if dt:assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',dt) and date.fromisoformat(dt)<=date(2026,10,22),row
coverage={pid:0 for pid in profiles}
for video in yt['videos']:
 for pid in set(video['profileIds']):coverage[pid]+=1
for pid,n in coverage.items():
 assert n>0 or any(g.get('profileId')==pid for g in yt['gaps']),('Missing coverage note',pid)
a=d['activity'];assert a['meta']['start']=='2025-10-22' and a['meta']['end']=='2026-10-22'
records=a['records'];assert len({r['profileId'] for r in records})==len(records)==len(profiles)
confirmed=[r for r in records if r['status']=='confirmed' and r['etAssociated']]
for row in records:assert row['sourceIds'] and set(row['sourceIds'])<=sources,row
for row in confirmed:
 dt=row['publishedAt'];assert dt and '2025-10-22'<=dt<='2026-10-22',row
assert len(confirmed)==13
assert next(r for r in records if r['profileId']=='em-elan')['status']=='unconfirmed'
assert next(r for r in records if r['profileId']=='lk-brad')['evidenceType'].startswith('interview about')
services=d['services'];assert len({s['profileId'] for s in services})==len(services)==14
for s in services:
 assert s['sourceIds'] and set(s['sourceIds'])<=sources,s
 assert s['checkedAt']=='2026-10-22' and s['priceLabel'] and s['freeLabel'] and s['privateLabel'],s
 if s['nextStatus'].startswith('confirmed'):
  assert s['nextDate'] and s['nextDate']>'2026-10-22',s
 else:assert s['nextDate'] is None,s
assert next(s for s in services if s['profileId']=='ac-christine')['nextStatus']=='year unresolved'
assert next(s for s in services if s['profileId']=='ar-ryok')['nextStatus']=='confirmed private'
print(json.dumps({'profiles':len(profiles),'accounts':len(accounts),'uniqueVideos':len(yt['videos']),'profilesWithVideos':sum(n>0 for n in coverage.values()),'confirmedNamedAnnual':len(confirmed),'servicesReviewed':len(services),'confirmedPublicEvents':sum(s['nextStatus']=='confirmed public' for s in services),'confirmedPrivateOpenings':sum(s['nextStatus']=='confirmed private' for s in services)},indent=2))
