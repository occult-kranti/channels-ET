"""Integrity checks for provenance, URL deduplication and delivered CSV coverage."""
import csv,json,re,zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parent.parent
x=json.loads((ROOT/'dist/data.json').read_text())['discovery'];rows=x['records'];people=x['people'];ids={r['id'] for r in rows}
assert len(ids)==len(rows)
assert len({r['url'] for r in rows})==len(rows)
assert len({p['name'] for p in people})==len(people)
assert len({p['id'] for p in people})==len(people)
vids=[];pls=[]
for r in rows:
 assert r['kind'] in ('account','playlist','video','website'),r
 assert r['url'].startswith(('http://','https://')) and r['title'],r
 assert r['sourceUrls'] and all(u.startswith(('http://','https://')) for u in r['sourceUrls']),r
 assert r['provenance'] and r['workstreams'] and r['accessDepth'] and r['dateBasis'],r
 assert r['relationship'] in ('official','organization/archive','interview/publisher','community/reupload','unresolved'),r
 assert all(n in {p['name'] for p in people} for n in r['personNames']),r
 if r['publishedAt']:assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['publishedAt']) and r['publishedAt']<='2026-10-23',r
 if r['kind']=='video':
  vid=parse_qs(urlparse(r['url']).query).get('v',[None])[0];assert vid and re.fullmatch(r'[A-Za-z0-9_-]{11}',vid),r;vids.append(vid)
 if r['kind']=='playlist':
  pl=parse_qs(urlparse(r['url']).query).get('list',[None])[0];assert pl and re.fullmatch(r'[A-Za-z0-9_-]+',pl),r;pls.append(pl)
assert len(vids)==len(set(vids)) and len(pls)==len(set(pls))
counts=Counter(r['kind'] for r in rows)
for k,n in counts.items():assert x['stats'][k]==n
assert x['stats']['rawRecords']-x['stats']['duplicateRowsMerged']==len(rows)
for p in people:
 assert set(p['recordIds'])<=ids,p
 file=ROOT/'dist'/p['csvPath'];assert file.exists(),p
 with file.open(encoding='utf-8-sig',newline='') as f:export=list(csv.DictReader(f))
 assert len(export)==len(p['recordIds']),p
 assert {r['id'] for r in export}==set(p['recordIds']),p
for kind,file in [(None,'channeling-links.csv'),('account','accounts.csv'),('playlist','playlists.csv'),('video','videos.csv'),('website','websites.csv')]:
 with (ROOT/'dist/exports'/file).open(encoding='utf-8-sig',newline='') as f:export=list(csv.DictReader(f))
 selected=rows if kind is None else [r for r in rows if r['kind']==kind]
 assert len(export)==len(selected) and {r['id'] for r in export}=={r['id'] for r in selected},file
with zipfile.ZipFile(ROOT/'dist/exports/channeling-research-csv.zip') as z:
 assert z.testzip() is None
 assert 'BASHAR-INDEX-LICENSE.txt' in z.namelist()
 assert sum(n.startswith('by-channeler/') for n in z.namelist())==len(people)
 assert 'channeling-links.csv' in z.namelist() and 'search-log.csv' in z.namelist()
assert any(q.get('query')=='Yahyel channeling' and q.get('method')=='youtube_browser' for q in x['queries'])
assert any(r['accessDepth']=='repository_metadata' for r in rows)
assert any('gflstation' in r['url'].lower() and r['kind']=='account' for r in rows)
assert next(r for r in rows if r['url']=='https://www.youtube.com/watch?v=1OP677fduwQ')['entityLabels']==['Bashar']
print(json.dumps({'records':len(rows),'types':dict(counts),'practitionerOrLineageEntries':len(people),'peopleWithoutLinkedRecords':[p['name'] for p in people if not p['recordIds']],'queryEntries':len(x['queries']),'perPractitionerCSVs':len(people),'zipIntegrity':'passed'},indent=2))
