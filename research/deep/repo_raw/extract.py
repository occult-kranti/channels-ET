import json,re,hashlib,csv
from pathlib import Path
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'repo.json'
COMMIT='457dc2f2da10399bda2786573b7a77ec3fe34f62'
BASE='https://github.com/occult-kranti/bashar-index/blob/'+COMMIT+'/'
V=json.loads((ROOT/'data/videos.json').read_text());D=json.loads((ROOT/'data/divine_light_vibes_channel.json').read_text());P=json.loads((ROOT/'data/podcasts.json').read_text())
records={};occurrences=0
OFF='https://www.youtube.com/@BasharChanneledbyDarrylAnka'
DV=D['channel_url']
def add(r):
 global occurrences
 occurrences+=1
 key=r['url']
 if key in records:
  old=records[key]
  old['sourceUrls']=sorted(set(old['sourceUrls']+r['sourceUrls']))
  for field in ['notes','dateBasis']:
   if r[field] and r[field] not in old[field]:old[field]+=' '+r[field]
  if not old.get('accountUrl') and r.get('accountUrl'):old['accountUrl']=r['accountUrl']
  if not old.get('publisher') and r.get('publisher'):old['publisher']=r['publisher']
 else:records[key]=r

def base(kind,title,url,path,**kw):
 return dict(kind=kind,title=title,url=url,personNames=['Darryl Anka'],entityLabels=['Bashar'],civilizations=['Essassani'],publisher=None,accountUrl=None,relationship='unresolved',publishedAt=None,dateBasis='Exact YouTube upload date not exposed by this repository metadata; no title/session/podcast date is substituted.',accessDepth='repository_metadata',discoveryQuery='Audit of occult-kranti/bashar-index at '+COMMIT,sourceUrls=[BASE+path],notes='Imported link metadata from the user-specified repository; YouTube availability, present uploader and media contents not freshly checked.',**kw)

for v in V:
 relation='official' if v.get('official') else 'interview/publisher' if 'Interview' in v.get('content_type','') else 'community/reupload'
 r=base('video',v['title'],v['url'],'data/videos.json');r.update(publisher=v.get('channel'),relationship=relation,accountUrl=OFF if v.get('official') else DV if v.get('channel')=='Divine Light Vibes' else None)
 r['contentType']=v.get('content_type');r['recordingYear']=v.get('year');r['recordingYearReliable']=v.get('year_reliable');r['repositoryYearBasis']=v.get('year_basis');r['repositorySessionDate']=v.get('session_date_or_event')
 r['notes']+=' Repository content label: '+str(v.get('content_type'))+'. '
 if v.get('researcher_note'):r['notes']+=v['researcher_note']
 if v.get('year') is not None:r['dateBasis']+=' Repository year '+str(v['year'])+' (reliable='+str(v.get('year_reliable'))+'); year basis: '+str(v.get('year_basis'))+'.'
 if v.get('podcast_date'):r['dateBasis']+=' Repository podcast date '+str(v['podcast_date'])+'; not treated as a YouTube upload date.'
 add(r)

for v in D['videos']:
 r=base('video',v['title'],v['url'],'data/divine_light_vibes_channel.json');confirmed=v['video_id']=='nyj_SuIkL0c'
 r.update(publisher='Divine Light Vibes (repository attribution)' if confirmed else 'Divine Light Vibes (tentative repository attribution)',accountUrl=DV if confirmed else None,relationship='community/reupload' if confirmed else 'unresolved',contentType='channeling clip / attributed repost')
 r['notes']+=' '+v.get('notes','')+' '+('Repository reports uploader confirmation through an older transcript page.' if confirmed else 'Repository warns uploader association mostly follows the Bashar Twin Flame title pattern; it may be a sister channel. Do not treat this association as verified.')
 add(r)

for p in P:
 if not p.get('youtube_url'):continue
 r=base('video',p.get('episode_title') or p['show'],p['youtube_url'],'data/podcasts.json');r.update(publisher=p.get('show'),relationship='interview/publisher',contentType=p.get('type','interview'))
 r['notes']+=' Repository interview/podcast record; a conversation about channeling is not proof a live channeling performance occurs.'
 if p.get('date'):r['dateBasis']+=' Repository episode date '+p['date']+'; original YouTube upload timestamp not exposed.';r['episodeDate']=p['date']
 add(r)

r=base('account','Bashar Channeled by Darryl Anka',OFF,'data/official_channels.md');r.update(publisher=r['title'],accountUrl=OFF,relationship='official',urlAliases=['https://www.youtube.com/BasharChanneledbyDarrylAnka','https://www.youtube.com/@BasharChanneledbyDarrylAnka/videos'],channelId='UCiDZy_rfSodwFaVL_imGWgQ');r['notes']+=' Repository ledger identifies official site linkage and this exact channel ID. Historical repository verification, not a fresh check.';add(r)
r=base('account','Divine Light Vibes',DV,'data/divine_light_vibes_channel.json');r.update(publisher=r['title'],accountUrl=DV,relationship='community/reupload',channelId=D['channel_id'],urlAliases=[D['channel_id_url']]);r['notes']+=' Nonofficial Bashar clip distributor in repository; partial list only. Video-to-account attribution for most listed clips remains tentative.';add(r)
r=base('account','Bashar Channeled by Darryl Anka 2025 (look-alike)', 'https://www.youtube.com/channel/UCPvbIxYNi98uEpSDuJs9G6A','data/official_channels.md');r.update(publisher=r['title'],accountUrl=r['url'],relationship='unresolved',channelId='UCPvbIxYNi98uEpSDuJs9G6A');r['notes']+=' Historical ledger says this differs from the official channel ID and is not linked by bashar.org. Affiliation, availability and relation to Divine Insights unverified.';add(r)
for p in D['playlists']:
 r=base('playlist',p['title'],p['url'],'data/divine_light_vibes_channel.json');r.update(publisher=p['owner'],accountUrl=DV,relationship='community/reupload',playlistId=p['playlist_id'])
 r['notes']+=' '+p.get('notes','')+' Repository reported '+str(p.get('video_count'))+' entries historically; list was not enumerated and current count/availability is unverified. This number is not added to indexed video counts.'
 add(r)

# Every exact YouTube URL in the selected files must be represented as a row or recorded alias.
pattern=re.compile(r'https?://[^\s<>"\'`]+')
all_urls=set()
for f in list((ROOT/'data').iterdir())+[ROOT/'README.md',ROOT/'LICENSE']:
 if not f.is_file() or f.name=='extract.py':continue
 if f.suffix=='.csv':
  all_urls|={r['url'] for r in csv.DictReader(f.read_text().splitlines())};continue
 all_urls|={u.rstrip('.,;)') for u in pattern.findall(f.read_text()) if 'youtube.com' in u or 'youtu.be' in u}
represented=set(records)|{a for r in records.values() for a in r.get('urlAliases',[])}
assert all_urls<=represented,sorted(all_urls-represented)
assert len([r for r in records.values() if r['kind']=='video'])==len({parse_qs(urlparse(r['url']).query).get('v',[None])[0] for r in records.values() if r['kind']=='video'})
people=[{'id':'darryl-anka','name':'Darryl Anka','entities':['Bashar'],'civilizations':['Essassani'],'website':'https://www.bashar.org/','notes':'One human channeler; third-party distribution channels and interview publishers are not additional mediums. Repository metadata is historical, not fresh YouTube availability verification.','sourceUrls':[BASE+'data/official_channels.md',BASE+'data/videos.json']}]
channels=sorted({x['channel'] for x in V})
gaps=['All imported records carry repository_metadata access depth; exact upload dates are left null.','Full catalog has 684 records but none contains YouTube URLs, so catalog session count does not inflate YouTube video count.','The 48 podcast records contain 20 exact YouTube links; date fields are episode dates rather than verified YouTube timestamps.','The 27 Divine Light Vibes candidates are not a complete channel inventory; all except nyj_SuIkL0c lack repository-level direct uploader confirmation.','38 uploader labels appear in the 75-video corpus, but most do not have exact account URLs in the retrieved files. They remain publisher names rather than invented channel links.','75-record CSV duplicates videos.json and does not contribute new videos.','Official channel handle, custom route and /videos route are merged as aliases; Divine Light Vibes numeric and handle routes are merged as aliases.','Repository metadata may describe removed or unavailable videos. No availability assertion is made.']
queries=[{'query':'Audit supplied repository tree and listed media metadata files','method':'repository','url':'https://github.com/occult-kranti/bashar-index/tree/'+COMMIT,'checkedAt':'2026-10-23','notes':'Initial pass fetched videos.json, recordings.csv, official_channels.md, Divine Light Vibes data, README and license.'},{'query':'Enrich repository-derived uploader and playlist leads; inspect podcast and catalog schemas','method':'repository','url':BASE+'data/podcasts.json','checkedAt':'2026-10-23','notes':'Second pass fetched podcasts.json and catalog_sessions.json; compared date meanings and deduplicated IDs.'}]
out={'workstream':'bashar_repository_audit','queries':queries,'people':people,'records':list(records.values()),'gaps':gaps,'summary':f'Imported {len(records)} deduplicated link records: '+str(sum(r['kind']=='video' for r in records.values()))+' videos, 3 account identities and 1 exact playlist, drawn from 9 pinned repository files. All actual YouTube URLs in these files are preserved directly or as known account aliases.','uploaderLabelsWithoutResolvedAccountUrl':[c for c in channels if c not in ['Bashar Channeled by Darryl Anka','Divine Light Vibes']]}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
files=[]
for f in sorted(ROOT.rglob('*')):
 if f.is_file() and f.name not in ['extract.py','manifest.json']:
  raw=f.read_bytes();files.append({'path':str(f.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gitBlobSha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'sourceUrl':BASE+str(f.relative_to(ROOT))})
manifest={'repository':'occult-kranti/bashar-index','requestedCommit':COMMIT,'retrievedAt':'2026-10-23','access':'GitHub connector fetch_file with explicit commit ref; local bytes match returned Git blob SHA','files':files,'counts':{'videoDigestRows':len(V),'videoUploaderLabels':len(channels),'divineLightCandidateVideos':len(D['videos']),'playlistRows':len(D['playlists']),'podcastRows':len(P),'podcastRowsWithYouTube':sum(bool(p.get('youtube_url')) for p in P),'catalogRows':len(json.loads((ROOT/'data/catalog_sessions.json').read_text())),'uniqueVideoRecords':sum(r['kind']=='video' for r in records.values()),'uniqueAccountIdentities':3,'uniquePlaylistRecords':1,'uniqueExactYouTubeUrlsBeforeAliasMerge':len(all_urls),'recordOccurrencesBeforeDeduplication':occurrences,'finalRecords':len(records)},'license':'MIT covers derived repository metadata/code; original Bashar media is not licensed or reproduced. Preserve LICENSE when redistributing these derived metadata.','schemaNotes':{'videos.json':'75 digest-derived metadata rows; year/year_reliable are historical content/year labels and are not exposed exact YouTube upload timestamps.','recordings.csv':'Same 75 videos; no added unique URLs.','divine_light_vibes_channel.json':'27 candidate clips, 2 equivalent account routes, 1 favorites playlist; most uploader associations tentative.','podcasts.json':'48 interview appearances, 20 with exact YouTube link; dates are episode dates.','catalog_sessions.json':'684 catalog entries with official/store/archive sources; no exact YouTube links.'},'deduplication':'Exact YouTube video IDs; official handle/custom route and Divine Light numeric/handle routes merged as declared aliases; no session-title dedupe across distinct video IDs.'}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['counts'],indent=2))
