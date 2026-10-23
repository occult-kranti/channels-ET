#!/usr/bin/env python3
"""Independent aggregate verifier frozen before reading producer code.
Checks data.json contract agreed 2026-10-23, does not import producer code.
"""
import json, sys, math, statistics, collections, datetime, hashlib
from pathlib import Path
p=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/sites/channeling-atlas/dist/analysis/data.json')
d=json.loads(p.read_text()); vv=d['videos'];cc=d['channels']; issues=[];checks=[]

def check(ok,message):
 checks.append(message)
 if not ok: issues.append(message)

def close(actual,expected,label):
 if expected is None:
  check(actual is None,f'{label}: unavailable result must be null, got {actual!r}')
 else:
  check(isinstance(actual,(int,float)) and math.isfinite(actual) and abs(actual-expected)<=0.0011,f'{label}: got {actual!r}; independently computed {expected!r}')

def qlinear(v,p):
 v=sorted(v); h=(len(v)-1)*p;lo=int(h);hi=math.ceil(h)
 return v[lo]+(v[hi]-v[lo])*(h-lo)

check(len(vv)==len({r['id'] for r in vv}),'Unique video IDs')
check(len(cc)==len({r['id'] for r in cc}),'Unique channel IDs')
by=collections.defaultdict(list)
for v in vv:
 by[v.get('channelId')].append(v)
 if v.get('durationSeconds') is not None: check(isinstance(v['durationSeconds'],(int,float)) and v['durationSeconds']>0 and math.isfinite(v['durationSeconds']),f"Positive finite duration {v['id']}")
 if v.get('date'):
  try: datetime.date.fromisoformat(v['date']);ok=True
  except (ValueError,TypeError):ok=False
  check(ok,f"Exact ISO date {v['id']}")
for c in cc:
 rows=by[c['id']];lens=[v['durationSeconds']/60 for v in rows if isinstance(v.get('durationSeconds'),(int,float)) and v['durationSeconds']>0]
 n=len(lens);lab=c['id']
 close(c.get('videoCount'),len(rows),f'{lab} video count')
 close(c.get('durationCount'),n,f'{lab} duration count')
 close(c.get('meanMinutes'),statistics.mean(lens) if n else None,f'{lab} mean minutes')
 close(c.get('medianMinutes'),statistics.median(lens) if n else None,f'{lab} median minutes')
 close(c.get('q1Minutes'),qlinear(lens,.25) if n else None,f'{lab} Q1 minutes')
 close(c.get('q3Minutes'),qlinear(lens,.75) if n else None,f'{lab} Q3 minutes')
 close(c.get('dateCount'),sum(bool(v.get('date')) for v in rows),f'{lab} exact date count')
 close(c.get('titleCount'),sum(bool(v.get('titleEligible')) for v in rows),f'{lab} eligible title count')
 # coverage can be ratio or percent; producer units must be documented separately.
 coverage=c.get('durationCoverage')
 if rows: check(coverage is not None and (abs(coverage-n/len(rows))<=0.0011 or abs(coverage-100*n/len(rows))<=0.0011),f'{lab} duration coverage denominator')
 else: check(coverage in (None,0),f'{lab} empty coverage')
known=set(c['id'] for c in cc)
check(all(v.get('channelId') in known or v.get('channelId') is None for v in vv),'All non-null publisher channel IDs resolve')
r={'reviewer':'/root/method_panel','input':str(p),'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checks':len(checks),'issues':issues,'status':'PASS' if not issues else 'FAIL','video_count':len(vv),'channel_count':len(cc)}
out=Path('/workspace/scratch/9ec421627a96/analysis_work/panel/numeric-review.json');out.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));sys.exit(bool(issues))
