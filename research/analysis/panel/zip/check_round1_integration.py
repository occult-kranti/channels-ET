#!/usr/bin/env python3
"""Independent raw-archive acceptance checks for the round1 analytical union."""
import csv,json,re,statistics,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SNAPSHOT=ROOT.parents[1]/'rounds/round1/data.json'
data=json.loads(SNAPSHOT.read_text());vv={v['id']:v for v in data['videos']};cc={c['id']:c for c in data['channels']}
with (ROOT/'raw-metadata/youtube_videos.csv').open(encoding='utf-8-sig',newline='') as f:raw=list(csv.DictReader(f))
with (ROOT/'raw-metadata/youtube_channels.csv').open(encoding='utf-8-sig',newline='') as f:rawaccounts={r['person_id']:r for r in csv.DictReader(f)}
checks=[]
def check(name,condition,evidence):
    checks.append({'name':name,'passed':bool(condition),'evidence':evidence})

valid=[r for r in raw if re.fullmatch(r'[A-Za-z0-9_-]{11}',r['video_id'])]
check('Linked ZIP video inclusion',all(r['video_id'] in vv for r in valid),{'validZipIds':len(valid),'found':sum(r['video_id'] in vv for r in valid)})
check('No unlinked draft placeholders counted',all(re.fullmatch(r'[A-Za-z0-9_-]{11}',v['id']) for v in data['videos']),{'unionRows':len(data['videos'])})
check('Unique video IDs',len(vv)==len(data['videos']),{'unique':len(vv),'rows':len(data['videos'])})
expected={}
for r in raw:
    if r['index_status']!='ok' or not r['length'] or not r['video_id']:continue
    a=list(map(int,r['length'].split(':')))
    expected[r['video_id']]=a[-1]+60*a[-2]+(3600*a[-3] if len(a)==3 else 0)
actual={k:v['durationSeconds'] for k,v in vv.items() if v['durationSeconds'] is not None}
check('Round1 duration eligibility exactly matches source rule',actual==expected,{'expectedN':len(expected),'actualN':len(actual),'mismatchIds':[k for k in expected if actual.get(k)!=expected[k]]})
check('Schema-derived Athina duration excluded before fresh verification',vv['MDdyY1WYmHY']['durationSeconds'] is None,{'durationSeconds':vv['MDdyY1WYmHY']['durationSeconds']})
editorial=['fZmY4xS_qXE','T5QtncJq1Jc','KtvDmi4JWyc']
rawtitles={r['video_id']:r['title'] for r in raw if r['video_id']}
check('Editorial descriptions excluded unless replaced from another source',all(not vv[k]['titleEligible'] or (vv[k]['title']!=rawtitles[k] and vv[k]['titleSource']!='claude_supplied') for k in editorial),{'ids':editorial,'flags':[vv[k]['titleEligible'] for k in editorial],'titleSources':[vv[k]['titleSource'] for k in editorial]})
bindings=[]
for r in valid:
    if r['video_id'] not in expected:continue
    v=vv[r['video_id']]; c=cc.get(v['channelId']); handle=r['channel_handle'].lower()
    aliases=[a.lower().rstrip('/') for a in (c or {}).get('aliases',[])]
    numeric=rawaccounts[r['person_id']]['channel_id'].lower()
    okay=c is not None and any(a.endswith('/'+handle) or (numeric and a.endswith('/channel/'+numeric)) for a in aliases)
    if not okay:bindings.append({'videoId':r['video_id'],'handle':handle,'channelId':(c or {}).get('id'),'aliases':aliases})
check('Duration rows bind to supplied account route',not bindings,{'examined':len(expected),'mismatches':bindings})
bad=[]; examined=0
for c in data['channels']:
    a=[v['durationSeconds']/60 for v in data['videos'] if v['channelId']==c['id'] and v['durationSeconds'] is not None]
    if not a:
        if c['meanMinutes'] is not None or c['medianMinutes'] is not None:bad.append(c['id'])
        continue
    examined+=1
    if c['durationCount']!=len(a) or not math.isclose(c['meanMinutes'],sum(a)/len(a),abs_tol=.00001) or not math.isclose(c['medianMinutes'],statistics.median(a),abs_tol=.00001):bad.append(c['id'])
check('Available-case mean/median/n and missingness',not bad,{'measuredChannels':examined,'mismatches':bad})
result={'round':1,'mode':'fresh-context source-to-build review','input':str(SNAPSHOT),'checks':checks,'passed':all(x['passed'] for x in checks)}
(ROOT/'round1_integration_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'checks':[{'name':x['name'],'passed':x['passed']} for x in checks]},ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed'] else 1)
