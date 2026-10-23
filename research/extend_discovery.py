"""Merge provenance-preserving link discovery and produce downloadable CSVs."""
import csv,hashlib,io,json,re,unicodedata,zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote,urlunparse
ROOT=Path(__file__).resolve().parent.parent
CHECKED='2026-10-23'
NAMES={'Athina Król (also rendered Krol)':'Athina Król','Athina Krol':'Athina Król','Vanessa Widergren':'Vanessa Lisle Widergren','Arkayla (public name)':'Arkayla','Lyssa Royal-Holt':'Lyssa Royal Holt','Suzy Ward':'Suzanne (Suzy) Ward'}
DEPTH={'repository_metadata':1,'search_metadata':2,'page_metadata':3,'browser_metadata':4,'page_text':5}

def arr(x):return x if isinstance(x,list) else [] if x is None else [x]
def uniq(xs):return list(dict.fromkeys(x for x in xs if x not in (None,'')))
def person_name(n):return NAMES.get(n,n)
def yt_host(u):return u.netloc.lower().removeprefix('www.') in ('youtube.com','m.youtube.com','music.youtube.com','youtu.be')
def identity(raw,kind=None):
 u=urlparse(raw);host=u.netloc.lower().removeprefix('www.');q=parse_qs(u.query);path=unquote(u.path).rstrip('/')
 if yt_host(u):
  if kind=='playlist' or path=='/playlist':
   pl=q.get('list',[None])[0]
   return 'playlist:'+pl if pl else 'yt:'+path
  vid=None
  if host=='youtu.be':vid=path.lstrip('/').split('/')[0]
  elif path=='/watch':vid=q.get('v',[None])[0]
  elif path.split('/')[1:2] and path.split('/')[1] in ('live','shorts','embed','podcast'):vid=path.split('/')[2] if len(path.split('/'))>2 else None
  if vid:return 'video:'+vid
  path=re.sub(r'/(videos|featured|streams|shorts|about|playlists|podcasts|community)$','',path)
  if path.startswith('/@'):path=path.lower()
  return 'account:'+path
 return host+path+('?' + u.query if u.query else '')
def canonical(raw,kind):
 k=identity(raw,kind)
 if k.startswith('video:'):return 'https://www.youtube.com/watch?v='+k[6:]
 if k.startswith('playlist:'):return 'https://www.youtube.com/playlist?list='+k[9:]
 if k.startswith('account:'):return 'https://www.youtube.com'+k[8:]
 return raw

def base_part(data):
 sm={s['id']:s for s in data['sources']};ps={p['id']:p for p in data['profiles']};rows=[];people=[]
 def pname(p):
  if p['id'] in ('hr-ra','hr-quo','hr-hatonn'):return 'L/L Research (Ra, Q’uo and Hatonn lineages)'
  if p['id']=='hr-seth':return 'Jane Roberts (Seth archive)'
  if p['id']=='hr-ashtar':return 'George W. Van Tassel (archive)'
  if p['id']=='hr-bailey':return 'Alice A. Bailey (archive)'
  return person_name(p.get('channeler') or p['name'])
 def pnames(ids):return uniq(pname(ps[i]) for i in ids if i in ps)
 def sources(ids):return uniq(sm[i]['url'] for i in ids if i in sm)
 for p in data['profiles']:
  svc=next((s for s in data.get('services',[]) if s['profileId']==p['id']),{})
  people.append({'name':pname(p),'entities':[p['entity']],'civilizations':[],'website':svc.get('bookingUrl'),'notes':p['summary']+' '+('Historical or institutional lineage; not counted as a currently active person. ' if p['id'].startswith('hr-') else '')+'Retained from the first source-led atlas sample; activity remains a separately scoped audit.','sourceUrls':sources(p['sourceIds'])})
 am={a['id']:a for a in data['youtube']['accounts']}
 for a in am.values():rows.append({'kind':'account','title':a['title'],'url':a['url'],'personNames':pnames(a['profileIds']),'entityLabels':a['entityLabels'],'civilizations':[],'publisher':a['title'],'accountUrl':a['url'],'relationship':a['relationship'],'publishedAt':None,'dateBasis':'Account route; not a publication date.','accessDepth':'page_metadata','discoveryQuery':'First atlas account ledger','sourceUrls':sources(a['sourceIds']),'notes':a['verification']})
 for v in data['youtube']['videos']:
  a=am.get(v.get('accountId'),{})
  rows.append({'kind':'video','title':v['title'],'url':v['url'],'personNames':pnames(v['profileIds']),'entityLabels':v['entityLabels'],'civilizations':[],'publisher':a.get('title'),'accountUrl':a.get('url'),'relationship':a.get('relationship','unresolved'),'publishedAt':v.get('publishedAt'),'dateBasis':v.get('dateBasis'),'accessDepth':'page_metadata','discoveryQuery':'First atlas individual-video ledger','sourceUrls':sources(v['sourceIds']),'notes':v.get('contentBasis','')+' '+v.get('notes',''),'contentType':v.get('format')})
 return {'workstream':'first_atlas_sample','people':people,'records':rows,'queries':[],'gaps':[]}

def enrich_discovery(data):
 files=sorted((ROOT/'research/deep').glob('*.json'))
 parts=[base_part(data)]+[json.loads(f.read_text()) for f in files if isinstance(json.loads(f.read_text()),dict) and 'records' in json.loads(f.read_text())]
 raw=[dict(r,workstream=p['workstream']) for p in parts for r in p.get('records',[])]
 # Only explicitly exposed aliases are unified. Shared names alone are insufficient.
 parent={}
 def find(k):
  parent.setdefault(k,k)
  if parent[k]!=k:parent[k]=find(parent[k])
  return parent[k]
 def union(a,b):
  aa,bb=find(a),find(b)
  if aa!=bb:parent[aa]=bb
 for r in raw:
  if r.get('kind')=='account' and r.get('accountUrl') and identity(r['url'],'account').startswith('account:') and identity(r['accountUrl'],'account').startswith('account:'):
   union(identity(r['url'],'account'),identity(r['accountUrl'],'account'))
  for alias in arr(r.get('aliases'))+arr(r.get('urlAliases')):
   if isinstance(alias,str) and alias.startswith(('http://','https://')) and r.get('kind')=='account':union(identity(alias,'account'),identity(r['url'],'account'))
 def rowkey(r):
  k=identity(r['url'],r['kind']);return find(k) if r['kind']=='account' else k
 merged={}
 for r in raw:
  if not r.get('url') or not r['url'].startswith(('https://','http://')):raise ValueError(('Invalid link',r))
  r['personNames']=uniq(person_name(n) for n in arr(r.get('personNames')))
  k=rowkey(r);prior=merged.setdefault(k,[]);prior.append(r)
 rows=[]
 for k,group in merged.items():
  group.sort(key=lambda r:(DEPTH.get(r.get('accessDepth'),0),len(r.get('title',''))),reverse=True)
  best=group[0];out={field:best.get(field) for field in ['kind','title','publisher','relationship','accessDepth','contentType']}
  out['id']='disc-'+hashlib.sha256(k.encode()).hexdigest()[:14]
  out['url']=canonical(best['url'],best['kind']) if best['kind']!='account' else 'https://www.youtube.com'+k[8:]
  for f in ['personNames','entityLabels','civilizations','sourceUrls']:out[f]=uniq(x for r in group for x in arr(r.get(f)))
  out['workstreams']=uniq(r['workstream'] for r in group)
  out['aliases']=uniq(x for r in group for x in [r['url'],*arr(r.get('aliases')),*arr(r.get('urlAliases'))] if isinstance(x,str) and x!=out['url'])
  out['publishers']=uniq(r.get('publisher') for r in group)
  out['accountUrls']=uniq(canonical(r['accountUrl'],'account') for r in group if r.get('accountUrl'))
  out['accountUrl']=out['accountUrls'][0] if out['accountUrls'] else None
  if out['accountUrl']:
   ak=find(identity(out['accountUrl'],'account'));out['accountUrl']='https://www.youtube.com'+ak[8:] if ak.startswith('account:') else out['accountUrl']
  exact=uniq(r.get('publishedAt') for r in group if r.get('publishedAt') and re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['publishedAt']))
  out['publishedAt']=exact[0] if len(exact)==1 else None
  date_row=next((r for r in group if r.get('publishedAt')==out['publishedAt'] and out['publishedAt']),best)
  out['dateBasis']=date_row.get('dateBasis') or 'Exact publication date not established.'
  if len(exact)>1:out['dateBasis']='Conflicting exact dates in source records: '+ '; '.join(exact)+'. Kept unresolved.'
  out['notes']=' | '.join(uniq(r.get('notes') for r in group))
  out['discoveryQuery']=' | '.join(uniq(r.get('discoveryQuery') for r in group))
  if all(r.get('relationship')=='unresolved' for r in group):out['relationship']='unresolved'
  elif best.get('relationship')=='unresolved':out['relationship']=next((r['relationship'] for r in group if r.get('relationship')!='unresolved'),'unresolved')
  out['provenance']=[{f:r.get(f) for f in ['workstream','url','title','publisher','accountUrl','relationship','accessDepth','publishedAt','dateBasis','sourceUrls','notes','discoveryQuery']} for r in group]
  rows.append(out)
 # An explicitly self-published single-practitioner account can enrich its linked videos.
 account_people={identity(r['url'],'account'):r['personNames'] for r in rows if r['kind']=='account' and r['relationship']=='official' and len(r['personNames'])==1}
 for r in rows:
  if not r['personNames'] and r.get('accountUrl') and r['relationship'] in ('official','unresolved'):
   r['personNames']=account_people.get(find(identity(r['accountUrl'],'account')),[])
 people_map={}
 for part in parts:
  for p in part.get('people',[]):
   name=person_name(p['name']);prior=people_map.setdefault(name,{'name':name,'entities':[],'civilizations':[],'websites':[],'sourceUrls':[],'notesList':[]})
   for f in ['entities','civilizations','sourceUrls']:prior[f]=uniq(prior[f]+arr(p.get(f)))
   prior['websites']=uniq(prior['websites']+arr(p.get('website')))
   prior['notesList']=uniq(prior['notesList']+arr(p.get('notes')))
 for r in rows:
  for name in r['personNames']:
   p=people_map.setdefault(name,{'name':name,'entities':[],'civilizations':[],'websites':[],'sourceUrls':[],'notesList':['Name attribution from linked public metadata; identity and direct performance require source-level checks.']})
   p['entities']=uniq(p['entities']+r['entityLabels']);p['civilizations']=uniq(p['civilizations']+r['civilizations']);p['sourceUrls']=uniq(p['sourceUrls']+r['sourceUrls'])
 people=[]
 for name,p in sorted(people_map.items()):
  p['id']='person-'+hashlib.sha256(name.encode()).hexdigest()[:12];p['website']=next(iter(p['websites']),None)
  p['notes']=' | '.join(p.pop('notesList'));p['recordIds']=[r['id'] for r in rows if name in r['personNames']]
  if name in ('IvET-ka','Ivet (surname unresolved)'):p['notes']+=' Possible same public persona as the other IvET-ka/Ivet record; numeric/handle equivalence remains unproved. Not two verified unique humans.'
  if name in ('David Nicholas','Dave Akira'):p['notes']+=' GFL contributor alias relationship unresolved; these are attribution records, not verified separate humans.'
  people.append(p)
 queries=[];seen=set()
 for part in parts:
  for q in part.get('queries',[]):
   q=dict(q);q['workstream']=part['workstream'];k=(q.get('query'),q.get('method'),q.get('url'))
   if k not in seen:seen.add(k);queries.append(q)
 gaps=uniq(g for part in parts for g in part.get('gaps',[]))
 rows.sort(key=lambda r:('; '.join(r['personNames']).casefold(),r['kind'],str(r['title']).casefold()))
 stats=dict(Counter(r['kind'] for r in rows));stats.update({'records':len(rows),'peopleEntries':len(people),'queryEntries':len(queries),'rawRecords':len(raw),'duplicateRowsMerged':len(raw)-len(rows),'manualBrowserQueries':sum(q.get('method')=='youtube_browser' for q in queries),'repositoryOnlyRecords':sum(r['accessDepth']=='repository_metadata' for r in rows)})
 meta={'checkedAt':CHECKED,'scope':'All-years discovery, including official projects, interview publishers, reposts, narrations, archival material and explicitly unresolved leads. Person/practice entries include partial names, possible aliases, historical lineages and non-ET context; they are not a census of unique or currently active mediums.','repoCommit':'457dc2f2da10399bda2786573b7a77ec3fe34f62','limitations':['Account counts refer to indexed routes after explicitly documented alias merges. Unproved numeric/handle aliases can remain separate.','Civilization and entity names are publisher/practitioner labels, not independently established species or origins.','Titles and uploader metadata do not establish original performance, voice authenticity, current availability or recording date. No complete recordings were systematically reviewed.','The original 13-person yearly audit remains scoped to its first reviewed sample; this expansion includes older material and is not a new annual census.','Exa credit exhaustion prevented that search path. GitHub, browser searches, regular web search and primary-page inspection supplied the executed expansion.','Full text, audio and video were not redistributed. Repository-derived link metadata retains its MIT attribution and pinned-source provenance.'],'aliasRule':'Only exact video/playlist IDs and explicitly linked account aliases are merged. Generic name similarity does not prove account identity.'}
 data['meta']['date']=CHECKED
 data['meta']['edition']='Research edition 03: deeper YouTube, civilization and repository discovery'
 data['meta']['limits'].append('The October 23 discovery expansion imports the pinned Bashar-index repository and records manual YouTube searches plus selected multilingual web directories. It includes account routes, playlists, narration and unresolved practitioner leads; its people/practice count is not a unique-human or annual-active census. The original activity and service audit remains pinned to October 22.')
 data['discovery']={'meta':meta,'people':people,'records':rows,'queries':queries,'gaps':gaps,'stats':stats}
 export_csvs(data['discovery'])
 return data

FIELDS=['id','kind','title','url','personNames','entityLabels','civilizations','publisher','accountUrl','relationship','publishedAt','dateBasis','accessDepth','contentType','discoveryQuery','sourceUrls','notes','workstreams','aliases']
def cell(x):
 if isinstance(x,list):x='; '.join(str(v) for v in x)
 if x is None:x=''
 x=str(x)
 return "'"+x if x.startswith(('=','+','-','@')) else x
def write_csv(path,fields,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(fields)
  for r in rows:w.writerow([cell(r.get(k)) for k in fields])
def export_csvs(d):
 dest=ROOT/'dist/exports';dest.mkdir(exist_ok=True);by=dest/'by-channeler';by.mkdir(exist_ok=True)
 for old in by.glob('*.csv'):old.unlink()
 write_csv(dest/'channeling-links.csv',FIELDS,d['records'])
 for kind,file in [('account','accounts.csv'),('playlist','playlists.csv'),('video','videos.csv'),('website','websites.csv')]:write_csv(dest/file,FIELDS,[r for r in d['records'] if r['kind']==kind])
 for p in d['people']:
  linked=[r for r in d['records'] if r['id'] in p['recordIds']]
  for kind in ['account','playlist','video','website']:p[kind+'Urls']=[r['url'] for r in linked if r['kind']==kind]
  slug=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',p['name']).encode('ascii','ignore').decode().lower()).strip('-')[:85]
  p['csvPath']='exports/by-channeler/'+slug+'-'+p['id'][-6:]+'.csv';write_csv(ROOT/'dist'/p['csvPath'],FIELDS,linked)
 write_csv(dest/'people.csv',['id','name','entities','civilizations','website','websites','accountUrls','playlistUrls','videoUrls','websiteUrls','csvPath','sourceUrls','notes'],d['people'])
 write_csv(dest/'search-log.csv',['workstream','query','method','url','checkedAt','notes'],d['queries'])
 write_csv(dest/'unattributed-links.csv',FIELDS,[r for r in d['records'] if not r['personNames']])
 (dest/'research-summary.json').write_text(json.dumps({'meta':d['meta'],'stats':d['stats'],'gaps':d['gaps']},ensure_ascii=False,indent=2)+'\n')
 (dest/'README.txt').write_text('Channeling Atlas discovery expansion — 2026-10-23\n\nAll-links, type-specific and per-practitioner CSV tables contain link metadata, provenance, unknown dates and attribution limits. Person entries are not a unique-human or annual-active census. Account aliases are merged only when explicitly linked. by-channeler/ includes one CSV per practitioner/lineage/partial-name entry; unattributed-links.csv preserves unresolved narrators and distributors. See research-summary.json and search-log.csv for executed coverage.\n\nRepository seed: occult-kranti/bashar-index, commit 457dc2f2da10399bda2786573b7a77ec3fe34f62. Repository-derived metadata is reused under its MIT license (included). No transcripts or recordings are reproduced.\n')
 license_path=ROOT/'research/deep/repo_raw/LICENSE'
 if license_path.exists():(dest/'BASHAR-INDEX-LICENSE.txt').write_text(license_path.read_text())
 with zipfile.ZipFile(dest/'channeling-research-csv.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(dest.rglob('*')):
   if f.is_file() and f.suffix!='.zip':z.write(f,f.relative_to(dest))
