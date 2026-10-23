"""Compile the dated YouTube, activity and booking research into the atlas."""
import json,re
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
ROOT=Path(__file__).resolve().parent.parent

def video_id(url):
 u=urlparse(url);host=u.netloc.lower().removeprefix('www.')
 if host=='youtu.be':return u.path.strip('/').split('/')[0]
 if host in ('youtube.com','m.youtube.com','music.youtube.com'):
  if u.path=='/watch':return parse_qs(u.query).get('v',[None])[0]
  parts=u.path.strip('/').split('/')
  if len(parts)>1 and parts[0] in ('live','shorts','embed','podcast'):return parts[1]
 return None

def key(url):
 vid=video_id(url)
 if vid:return 'yt-video:'+vid
 u=urlparse(url);host=u.netloc.lower().removeprefix('www.')
 path=unquote(u.path).rstrip('/')
 if host in ('youtube.com','m.youtube.com'):
  path=re.sub(r'/(videos|featured|streams|shorts|about)$','',path)
  if path.startswith('/@'):path=path.lower()
 return host+path+('?' +u.query if u.query else '')

def enrich(data):
 parts=[json.loads((ROOT/'research/youtube'/f'{name}.json').read_text()) for name in ['focus','et','guides','history_recent']]
 core=json.loads((ROOT/'research/services_core.json').read_text())
 extra=json.loads((ROOT/'research/youtube/services_extra.json').read_text())
 # Merge source IDs against the existing ledger; all consumer references are remapped.
 all_sources=data['sources']+[s for p in parts for s in p.get('sources',[])]+core['sources']+extra['sources']
 sources=[];by_key={};source_alias={}
 for s in all_sources:
  for field in ['ref','webRef','retrievalRef']:s.pop(field,None)
  k=key(s['url'])
  if k in by_key:
   old=by_key[k];source_alias[s['id']]=old['id']
   note=s.get('notes','')
   if note and note not in old.get('notes',''):
    old['notes']=old.get('notes','')+' '+note
  else:by_key[k]=s;sources.append(s)
 def refs(ids):return list(dict.fromkeys(source_alias.get(i,i) for i in ids))
 data['sources']=sources
 accounts=[];by_account={};account_alias={}
 for account in [a for p in parts for a in p.get('accounts',[])]:
  k=account.get('channelId') or key(account['url'])
  if k in by_account:
   prior=by_account[k];account_alias[account['id']]=prior['id']
   for field in ['profileIds','entityLabels','sourceIds']:prior[field]=list(dict.fromkeys(prior.get(field,[])+account.get(field,[])))
  else:by_account[k]=account;accounts.append(account)
 videos=[];by_video={}
 for video in [v for p in parts for v in p.get('videos',[])]:
  vid=video_id(video['url']);assert vid,video
  video['videoId']=vid
  if video.get('accountId'):video['accountId']=account_alias.get(video['accountId'],video['accountId'])
  if vid in by_video:
   prior=by_video[vid]
   for field in ['profileIds','entityLabels','sourceIds']:prior[field]=list(dict.fromkeys(prior.get(field,[])+video.get(field,[])))
   if not prior.get('publishedAt') and video.get('publishedAt'):
    for field in ['publishedAt','dateBasis']:prior[field]=video[field]
  else:by_video[vid]=video;videos.append(video)
 records=[a for p in parts for a in p.get('activity',[])]
 amap={a['profileId']:a for a in records}
 for p in data['profiles']:
  if p['id'] not in amap:
   amap[p['id']]={'profileId':p['id'],'etAssociated':False,'status':'not ET-focused','publishedAt':None,'datePrecision':None,'dateBasis':'This comparison concerns ET-associated practitioners; this profile is retained in the broader guide/mediumship directory.','evidenceTitle':'Profile classification','evidenceUrl':None,'notes':'No claim of inactivity is made. General spirit-guide or afterlife work is not automatically counted as ET channeling.','sourceIds':p['sourceIds']}
 # The January2026 Elan exchange establishes new project material, but that page
 # does not name the human channeler. Do not inflate the named-human count.
 elan=amap['em-elan'];elan['status']='unconfirmed'
 elan['notes']='Official text reports an Elan exchange in January2026, but does not name its human channeler or show a publication timestamp. Kept as an additional active-material lead outside the confirmed named-human count. Its YouTube series is remastered archival material.'
 elan['dateBasis']='Reported exchange month January2026; exact publication date and current human attribution unresolved.'
 # Mark the kind of qualifying activity so interviews are not mistaken for performances.
 for a in amap.values():
  a['evidenceType']='publication / message'
  if a['profileId'] in ['ba-bashar','ar-athina-ashtar','ar-ryok']:a['evidenceType']='YouTube channeling excerpt'
  if a['profileId'] in ['lk-wendy','lk-rob','lk-daniel','lk-shaun']:a['evidenceType']='published podcast with channeling'
  if a['profileId']=='lk-brad':a['evidenceType']='interview about claimed contact; channeling performance unverified'
  if a['status']=='historical':a['evidenceType']='historical / institutional archive'
  if a['profileId'] in ['hr-quo','hr-hatonn']:
   a['notes']='Living L/L contributors may continue this lineage. This entity/institutional profile is not a separate named human and is excluded from the person count.'
 services=core['services']+extra['services']
 for s in services:
  if s['profileId']=='lk-lyssa':
   s['nextTime']='21:00–22:30';s['timeZone']='America/New_York (EDT)'
   s['notes'].insert(0,'Original listing: October31,18:00–19:30 Arizona / November1,10:00–11:30 Japan. The specific guide is not promised.')
  if s['profileId']=='lk-wendy':s['nextTime']='13:00'
  # Improve spacing in research shorthand without changing dates or amounts.
  for f in ['nextTime','priceLabel','privateLabel','freeLabel','sessionType','notes']:
   def clean(t):
    t=re.sub(r'(?<=[A-Za-z])(?=\$|[0-9])',' ',t)
    t=re.sub(r'(?<=[0-9])(?=[A-Za-z])',' ',t)
    for old,new in [('oneperson','one-person'),('Oneperson','One-person'),('hourchanneling','hour channeling'),('hourtraining','hour training'),('hourZoom','hour Zoom'),('privateZoom','private Zoom'),('fromFebruary','from February'),('orSoulName','or Soul Name'),('paidPatreon','paid Patreon'),('startsUS','starts US'),('MP 3','MP3')]:
     t=t.replace(old,new)
    t=re.sub(r':(?=\$)', ': ', t)
    t=re.sub(r';(?=\$)', '; ', t)
    t=re.sub(r'(?<=\d),(?=20\d{2}\b)', ', ', t)
    t=re.sub(r'\b(20\d{2}),(?=\d)', r'\1, ', t)
    return t
   if isinstance(s.get(f),list):s[f]=[clean(x) for x in s[f]]
   elif isinstance(s.get(f),str):s[f]=clean(s[f])
  if s['profileId']=='ba-bashar':s['priceLabel']='€36 live + limited replay; €66 live + recording (EUR displayed)'
  if s['profileId']=='lk-daniel':s['priceLabel']='Pay what you want; minimum $11.11'
  if s['profileId']=='ar-ryok':s['priceLabel']='$400 for one-hour channeling; dollar currency code not explicit'
  s['activityStatus']=amap[s['profileId']]['status']
  s['profileEtAssociated']=True
 gaps=[g for p in parts for g in p.get('gaps',[])]
 data['youtube']={'accounts':accounts,'videos':videos,'gaps':gaps,'meta':{'checkedAt':'2026-10-22','start':'2025-10-22','end':'2026-10-22','scope':'Curated public-source index, including historical archives and non-ET guide traditions. Counts describe collection coverage, not the total videos on YouTube.','dateRule':'Only exposed exact upload dates populate publishedAt. Unknown dates stay null. A webpage/session date is not silently substituted for a YouTube upload.','accessRule':'Records primarily use titles, uploader metadata, descriptions and official embedded links. One short Bashar automatic-caption transcript was read earlier. Full video content was not systematically reviewed.','relationshipRule':'Official account means a practitioner/site-linked source; interviews, archives, community presentations and unresolved attributions are labeled separately.'}}
 data['activity']={'meta':{'start':'2025-10-22','end':'2026-10-22','scope':'Confirmed minimum within the reviewed corpus, not a worldwide census. Each named human counts once when an attributed ET-channeling practice has dated public material in the window. This includes channeling-related interviews as well as messages and recordings; a separate label identifies evidence type.','unknownRule':'Unconfirmed is an evidence gap, not a finding of inactivity. Elan has January2026 material but this specific text does not identify the current human channeler. Historical/institutional profiles and non-ET traditions are excluded.','claimedSourceRule':'These are activity/publication checks, not verification of extraterrestrial identities.'},'records':list(amap.values())}
 data['services']=services
 # Extend comparative entity links without asserting that same star labels mean the same source.
 for e in data['entities']:
  if e['id']=='ent-arcturian':
   e['name']='Arcturian-associated sources';e['profileIds']+=['ac-marilyn'];e['description']='Scranton and Raffaele present differently named Arcturian-associated collectives; the shared label does not establish a common source.'
  if e['id']=='ent-pleiadian':e['profileIds']+=['ac-christine','ac-valerie']
  if e['id']=='ent-sassani':e['profileIds']+=['ac-alexandra']
 for key_name in ['profiles','events','entities','communityItems','videoItems','insights','forecasts','services']:
  for row in data.get(key_name,[]):row['sourceIds']=refs(row.get('sourceIds',[]))
 for kind in ['accounts','videos']:
  for row in data['youtube'][kind]:row['sourceIds']=refs(row.get('sourceIds',[]))
 for row in data['activity']['records']:row['sourceIds']=refs(row.get('sourceIds',[]))
 data['meta']['edition']='Research edition02: YouTube, activity & sessions'
 data['meta']['limits']=[x for x in data['meta']['limits'] if not x.startswith('Current prices, session')]
 data['meta']['limits']+=['Session and price listings were checked October22,2026. Some booking pages are stale or omit a year; uncertain dates are not treated as confirmed future sessions. Displayed currencies are preserved without exchange-rate conversion.','The annual activity count includes dated messages, recordings and channeling-related interviews across platforms. It is not a count of independently authenticated contacts or only new YouTube performances.','Two historical profiles have no securely attributed original channeling video in this index. Community readings and namesake accounts remain distinguishable from original recordings and official accounts.']
 return data
