#!/usr/bin/env python3
"""Reproducible first-pass metadata analysis. No live retrieval or random sampling."""
import argparse, collections, csv, hashlib, json, math, pathlib, re, sys, unicodedata
from urllib.parse import urlparse, parse_qs
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[2]
IN=ROOT/'research/analysis/inputs'; OUT=ROOT/'dist/analysis'; OUT.mkdir(exist_ok=True)
CUTOFF='2026-10-23'
TOPICS=[
 ('contact','ET contact & disclosure',r'\b(contact|disclos\w*|alien\w*|extraterrestrial\w*|ufo\w*|uap\w*|hybrid\w*)\b'),
 ('agency','Choice, beliefs & manifestation',r'\b(manifest\w*|belief\w*|believ\w*|choice\w*|choose|choosing|creat\w*|excitement|passion\w*|purpose)\b'),
 ('healing','Healing & wellbeing',r'\b(heal\w*|health\w*|anxiety|trauma\w*|fear\w*|stress\w*|wellbeing|wellness|emotional\w*)\b'),
 ('consciousness','Consciousness & awakening',r'\b(conscious\w*|awaken\w*|ascen\w*|awareness|enlighten\w*|soul\w*|spiritual\w*)\b'),
 ('energy','Energy & frequency',r'\b(energy|energies|energetic\w*|frequenc\w*|vibrat\w*|light|portal\w*|activat\w*)\b'),
 ('society','Collective & world events',r'\b(collective|world|humanity|global|society|social|government\w*|politic\w*|election\w*|war|peace)\b'),
 ('relationships','Love & relationships',r'\b(love|loving|relationship\w*|partner\w*|family|families|compassion\w*|forgiv\w*)\b'),
 ('practice','Meditation & practice',r'\b(meditat\w*|practic\w*|breath\w*|exercise\w*|technique\w*|ritual\w*|yoga)\b'),
 ('time','Time, dimensions & realities',r'\b(timeline\w*|dimension\w*|parallel|realit\w*|future|past|time|quantum)\b')]
IDENTITY='bashar darryl anka athina krol król ashtar ryok ryokah tyler ellison daniel scranton pleiadian pleiadians arcturian arcturians sirius sirian sirians yahyel sassani essassani zeta orion andromedan andromedans federation galactic council channeled channelled channeling channelling channel transmission message messages official'.split()
STOP=set(ENGLISH_STOP_WORDS)|set(IDENTITY)|{'2026','2025','2024','2023','new','full','episode','youtube','live','video','part','today','october','september','january','february','march','april','may','june','july','august','november','december'}

def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
def load(p):return json.loads(p.read_text())
def uid(s,prefix='ch-'):return prefix+hashlib.sha256(s.encode()).hexdigest()[:12]
def route(u):
 if not u or not isinstance(u,str):return None
 p=urlparse(u if '://' in u else 'https://www.youtube.com/'+u)
 path=p.path.rstrip('/');a=path.split('/')
 if len(a)>2 and a[1] in ['channel','user','c']:path='/'.join(a[:3])
 elif len(a)>1 and a[1].startswith('@'):path='/'+a[1].lower()
 else:return None
 return 'https://www.youtube.com'+path

def videoid(u):
 if not u:return None
 p=urlparse(u);v=parse_qs(p.query).get('v',[''])[0]
 if not v and p.netloc.endswith('youtu.be'):v=p.path.strip('/')
 if not v and any(x in p.path for x in ['/shorts/','/embed/','/live/']):v=p.path.strip('/').split('/')[1]
 return v if re.fullmatch('[A-Za-z0-9_-]{11}',v or '') else None
class Union:
 def __init__(self):self.p={}
 def find(self,x):
  if x not in self.p:self.p[x]=x
  if self.p[x]!=x:self.p[x]=self.find(self.p[x])
  return self.p[x]
 def join(self,a,b):
  if a and b:self.p[self.find(b)]=self.find(a)

def valid_date(s):
 if not s or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',s):return None
 import datetime
 try:datetime.date.fromisoformat(s)
 except ValueError:return None
 return s if s<=CUTOFF else None

def title_ok(s):return bool(s and len(s.split())>=2 and not re.search(r'title not recorded|title paraphrased|video link|unknown title|unnamed video',s,re.I))
def clean(s):
 s=unicodedata.normalize('NFKC',s).lower()
 s=re.sub(r'https?://\S+',' ',s)
 s=re.sub(r'\b(?:'+ '|'.join(map(re.escape,IDENTITY))+r')\b',' ',s)
 s=re.sub(r'[^a-z\s]',' ',s)
 return ' '.join(w for w in s.split() if w not in STOP and len(w)>2)
def csvout(name,rows,fields):
 with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader()
  for r in rows:
   row={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()}
   for k,v in row.items():
    if isinstance(v,str) and v[:1] in '=+@-':row[k]="'"+v
   w.writerow(row)

def assemble(metadata_file=None):
 atlas=load(ROOT/'dist/data.json')['discovery'];zv=load(IN/'claude_videos.json');za=load(IN/'claude_accounts.json')
 u=Union();acc=[]
 for r in atlas['records']:
  if r['kind']=='account':
   rr=route(r['url'])
   if not rr:continue
   u.find(rr)
   for a in r.get('aliases',[]):u.join(rr,route(a))
   acc.append({'route':rr,'name':r['title'],'relationship':r.get('relationship'),'source':'atlas','provenance':r.get('sourceUrls',[])})
 for r in za:
  rr=route(r.get('url'))
  if not rr:continue
  u.find(rr)
  if r.get('channelId'):u.join(rr,route('https://www.youtube.com/channel/'+r['channelId']))
  if r.get('handle'):u.join(rr,route('https://www.youtube.com/'+r['handle']))
  acc.append({'route':rr,'name':r['title'] or r.get('personName'),'relationship':r.get('roleReported'),'source':'claude_supplied','provenance':r.get('sourceUrlsReported',[])})
 vids={}
 for r in atlas['records']:
  if r['kind']!='video':continue
  v=videoid(r['url'])
  if not v:continue
  rr=route(r.get('accountUrl'));u.find(rr) if rr else None
  vids[v]={'id':v,'url':'https://www.youtube.com/watch?v='+v,'title':r['title'],'channelRoute':rr,'publisher':r.get('publisher'),'durationSeconds':None,'durationSource':None,'date':valid_date(r.get('publishedAt')),'dateSource':'prior_atlas_exact' if valid_date(r.get('publishedAt')) else None,'titleEligible':title_ok(r['title']),'titleSource':'prior_atlas_metadata','provenance':[{'kind':'prior_atlas','recordId':r['id'],'sources':r.get('sourceUrls',[])}],'conflicts':[],'people':r.get('personNames',[]),'entities':r.get('entityLabels',[])}
 for r in zv:
  if not r.get('validVideoId'):continue
  v=r['videoId'];rr=route(r.get('channelUrl'));u.find(rr) if rr else None
  q=vids.setdefault(v,{'id':v,'url':r['url'],'title':r['title'],'channelRoute':rr,'publisher':r.get('channelHandle'),'durationSeconds':None,'durationSource':None,'date':None,'dateSource':None,'titleEligible':r.get('titleEligibleSecondary',title_ok(r['title'])),'titleSource':'claude_supplied','provenance':[],'conflicts':[],'people':[r.get('personName')],'entities':[r.get('entityLabelReported')]})
  q['provenance'].append(r['provenance'])
  if not q['channelRoute']:q['channelRoute']=rr
  elif rr and u.find(rr)!=u.find(q['channelRoute']):q['conflicts'].append('Different uploader routes in supplied and prior records.');q['channelRoute']=None
  if r.get('durationEligiblePrimary'):
   q['durationSeconds']=r['durationSeconds'];q['durationSource']='claude_provider_metadata_unverified'
  date=valid_date(r.get('publishedAtReported'))
  if date and q['date'] and date!=q['date']:q['date']=None;q['dateSource']='conflict';q['conflicts'].append('Conflicting exact dates')
  elif date and not q['date']:q['date']=date;q['dateSource']='claude_supplied_exact'
  q['relativeDateText']=r.get('publishedRelativeText');q['relativeDateAsOf']=r.get('relativeDateAsOf')
  q['titleEligible']=q['titleEligible'] and title_ok(q['title'])
 # Fresh public watch metadata supersedes inherited fields, with variants preserved.
 for m in load(metadata_file or IN/'fresh_metadata.json') if pathlib.Path(metadata_file or IN/'fresh_metadata.json').exists() else []:
  v=m.get('video_id')
  if v not in vids:continue
  q=vids[v];q['retrievalStatus']=m.get('status')
  if m.get('publisher'):q['observedPublisher']=m['publisher']
  if m.get('status')!='success':continue
  rr=route(m.get('channel_url'))
  if rr and m.get('channel_id'):u.join(rr,route('https://www.youtube.com/channel/'+m['channel_id']))
  if rr:
   q['channelRoute']=rr;acc.append({'route':rr,'name':m.get('publisher') or rr,'relationship':'current uploader','source':'fresh_watch_metadata','provenance':[m.get('source_url')]})
  if m.get('title'):
   q.setdefault('titleVariants',[])
   if q['title']!=m['title']:q['titleVariants'].append({'title':q['title'],'source':q['titleSource']});q['titleChanged']=True
   q['title']=m['title'];q['titleSource']='fresh_watch_metadata';q['titleEligible']=title_ok(m['title'])
  if m.get('duration_seconds') is not None and m['duration_seconds']>0:
   if q['durationSeconds'] is not None and abs(q['durationSeconds']-m['duration_seconds'])>2:q['conflicts'].append('Duration changed from '+str(q['durationSeconds'])+' to '+str(m['duration_seconds']))
   q['durationSeconds']=m['duration_seconds'];q['durationSource']='fresh_watch_metadata'
  if m.get('published_at'):
   from datetime import datetime,timezone
   try:day=datetime.fromisoformat(m['published_at']).astimezone(timezone.utc).date().isoformat()
   except ValueError:day=m['published_at'][:10]
   if valid_date(day):
    if q['date'] and q['date']!=day:q['conflicts'].append('Date comparison: inherited '+q['date']+'; fresh UTC '+day+' (may reflect timezone conversion)' )
    q['date']=day;q['dateSource']='fresh_watch_metadata_UTC';q['publishedTimestamp']=m['published_at']
  q['provenance'].append({'kind':'fresh_watch_metadata','url':m.get('source_url'),'retrievedAt':m.get('retrieved_at'),'htmlSha256':m.get('html_sha256')})
 # Include every observed route, even if no indexed video is attributable.
 channels={}
 for a in acc:
  rr=u.find(a['route']);cid=uid(rr)
  c=channels.setdefault(cid,{'id':cid,'name':a['name'] or rr,'url':rr,'aliases':[],'relationship':a['relationship'],'sources':[]})
  if a['source']=='fresh_watch_metadata':
   c.setdefault('nameAliases',[]).append(c['name']);c['name']=a['name'];c['publisherVerified']=True
  c['aliases']=sorted(set(c['aliases']+[a['route']]))
  c['sources'].append(a['source'])
  c['sources']=sorted(set(c['sources']))
  if c.get('nameAliases'):c['nameAliases']=sorted(set(c['nameAliases'])-{c['name']})
 for q in vids.values():
  rr=u.find(q['channelRoute']) if q['channelRoute'] else None
  q['channelId']=uid(rr) if rr else None;q.pop('channelRoute')
  if rr and q['channelId'] not in channels:channels[q['channelId']]={'id':q['channelId'],'name':q['publisher'] or rr,'url':rr,'aliases':[rr],'relationship':'unresolved','sources':['video_metadata']}
 return list(vids.values()),list(channels.values()),u

def similarities(videos,channels,text_key='title',name='title'):
 docs=[v for v in videos if v.get('channelId') and v.get('titleEligible') and len(clean(v[text_key]).split())>=2]
 if len(docs)<5:return {},{},None
 texts=[clean(v[text_key]) for v in docs]
 vectorizer=TfidfVectorizer(stop_words=sorted(STOP),ngram_range=(1,2),min_df=2,max_df=.90,sublinear_tf=True)
 X=vectorizer.fit_transform(texts);idx=collections.defaultdict(list)
 for i,v in enumerate(docs):idx[v['channelId']].append(i)
 eligible=[c for c in channels if len(idx[c['id']])>=5];eligible.sort(key=lambda c:c['name'].lower())
 cents=np.vstack([np.asarray(X[idx[c['id']]].mean(axis=0)).ravel() for c in eligible]) if eligible else np.empty((0,X.shape[1]))
 M=cosine_similarity(cents) if len(cents) else np.empty((0,0));pairs=[]
 for i,a in enumerate(eligible):
  for j in range(i+1,len(eligible)):
   b=eligible[j];pairs.append({'a':a['id'],'b':b['id'],'cosine':round(float(M[i,j]),6),'nA':len(idx[a['id']]),'nB':len(idx[b['id']])})
 pairs.sort(key=lambda r:-r['cosine']);terms=vectorizer.get_feature_names_out()
 tops={}
 for c in channels:
  if idx[c['id']]:
   cen=np.asarray(X[idx[c['id']]].mean(axis=0)).ravel();tops[c['id']]=[{'term':terms[j],'weight':round(float(cen[j]),5)} for j in np.argsort(cen)[::-1][:10] if cen[j]>0]
 sim={'method':'L2-normalized title TF-IDF unigram/bigram channel centroid cosine','minTitles':5,'channelIds':[c['id'] for c in eligible],'matrix':np.round(M,6).tolist(),'pairs':pairs,'documents':len(docs),'vocabularySize':len(terms),'identityMasked':True,'textLevel':'video titles','samplingNote':'Purposive metadata sample; no population inference. Same video ID appears once. Distinct reposts can share underlying sessions.'}
 return sim,tops,{'docs':docs,'texts':texts,'idx':idx,'eligible':eligible,'X':X}

def plotlabel(c,limit=40):
 name=c['name']
 if sum(ord(x)>127 for x in name)>len(name)/4:name=c['url'].split('/')[-1]
 return name if len(name)<=limit else name[:limit-1]+'…'

def makeplots(data):
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.facecolor':'#fffef9','figure.facecolor':'#fffef9','text.color':'#233c34','axes.labelcolor':'#233c34','svg.fonttype':'none','svg.hashsalt':'channeling-atlas-analysis-v1'})
 figs=[]
 def save(fig,id,title,caption):
  fig.tight_layout();path='analysis/figures/'+id+'.svg';fig.savefig(ROOT/'dist'/path,bbox_inches='tight',metadata={'Date':None,'Creator':'Channeling Atlas analysis pipeline'});fig.savefig(ROOT/'dist'/path.replace('.svg','.png'),bbox_inches='tight',dpi=150);plt.close(fig);figs.append({'id':id,'path':path,'title':title,'caption':caption+' Metadata checked 23 October 2026; current and inherited source layers are marked in exports.','dataPath':'analysis/'+({'duration':'channel-metrics.csv','coverage':'channel-metrics.csv','title-topics':'title-topic-indicators.csv','lexical-similarity':'title-similarity-pairs.csv','caption-topics':'caption-topic-indicators.csv','caption-similarity':'caption-similarity-pairs.csv','title-caption-indicators':'matched-title-caption-indicators.csv','caption-within-between':'caption-pair-diagnostics.csv','duration-format':'channel-metrics.csv'}.get(id,'video-observations.csv'))})
 cs=sorted([c for c in data['channels'] if c['durationCount']>=5],key=lambda c:c['medianMinutes'])
 if cs:
  fig,ax=plt.subplots(figsize=(10,max(5,len(cs)*.34)))
  yy=np.arange(len(cs));med=np.array([c['medianMinutes'] for c in cs]);lo=np.array([c['q1Minutes'] for c in cs]);hi=np.array([c['q3Minutes'] for c in cs])
  ax.errorbar(med,yy,xerr=[med-lo,hi-med],fmt='o',color='#345b4b',capsize=3,label='Median and middle 50%')
  ax.scatter([c['meanMinutes'] for c in cs],yy,marker='D',facecolors='none',edgecolors='#a16633',s=28,label='Mean')
  ax.set_yticks(yy,[f"{plotlabel(c)} ({c['durationCount']}/{c['videoCount']})" for c in cs]);ax.set_xlabel('Video duration (minutes)');ax.set_xlim(left=0);ax.grid(axis='x',alpha=.2);ax.legend(loc='lower right');ax.set_title('Observed video durations by publisher')
  save(fig,'duration','Observed duration by channel','Each row uses available duration metadata for unique indexed video IDs. Labels show measured/indexed counts. Dots are medians; whiskers are the 25th–75th percentiles, not confidence intervals; diamonds are means. Only channels with at least five durations are plotted. These are convenience samples, often capped by source listings, not channel-wide averages.')
 top=sorted(data['channels'],key=lambda c:-c['videoCount'])[:20]
 fig,ax=plt.subplots(figsize=(10,7));y=np.arange(len(top));ax.barh(y,[c['videoCount'] for c in top],color='#d9dfd5',label='Indexed');ax.barh(y,[c['durationCount'] for c in top],color='#345b4b',label='Duration available');ax.set_yticks(y,[plotlabel(c) for c in top]);ax.invert_yaxis();ax.set_xlabel('Unique indexed videos');ax.legend();ax.set_title('Duration coverage in the 20 largest indexed samples');save(fig,'coverage','Duration coverage','Counts refer to the merged research index. The pale portion includes videos without usable duration metadata. Channel order reflects sample size, not popularity, activity or the size of the entire account.')
 cs=sorted([c for c in data['channels'] if c['titleCount']>=5],key=lambda c:-c['titleCount'])[:20]
 if cs:
  vals=np.array([[t['share'] for t in c['topics']] for c in cs]);fig,ax=plt.subplots(figsize=(11,8));im=ax.imshow(vals,vmin=0,vmax=1,cmap='YlGn',aspect='auto');ax.set_yticks(range(len(cs)),[f"{plotlabel(c,32)} (n={c['titleCount']})" for c in cs]);ax.set_xticks(range(len(TOPICS)),[t[1].replace(' & ',' /\n') for t in TOPICS],rotation=45,ha='right');fig.colorbar(im,ax=ax,label='Share of sampled titles with a keyword match');ax.set_title('Transparent title keyword indicators');save(fig,'title-topics','Title topic indicators','A cell is the fraction of eligible sampled titles matching at least one predefined English keyword in that topic. Topics overlap and are not validated semantic classes. This measures headline vocabulary, not the contents of a session; multilingual and short titles can be missed. The 20 largest eligible title samples are shown.')
 sim=data.get('similarity',{});ids=sim.get('channelIds',[])
 if ids:
  cmap={c['id']:c for c in data['channels']};sel=sorted(range(len(ids)),key=lambda i:-cmap[ids[i]]['titleCount'])[:18];M=np.array(sim['matrix'])[np.ix_(sel,sel)]
  fig,ax=plt.subplots(figsize=(10,9));im=ax.imshow(M,vmin=0,vmax=1,cmap='YlGn');names=[plotlabel(cmap[ids[i]],26) for i in sel];ax.set_yticks(range(len(sel)),names);ax.set_xticks(range(len(sel)),names,rotation=60,ha='right');fig.colorbar(im,ax=ax,label='Cosine similarity');ax.set_title('Shared title vocabulary after identity masking');save(fig,'lexical-similarity','Shared title vocabulary','Cosines compare equal-video-weight TF-IDF centroids after masking common channeling identity terms. Values are descriptive similarity scores, not probabilities or evidence of shared origins. Each account has at least five eligible titles. The 18 largest samples are plotted; exact matrices are exported. Diagonal self-comparisons equal1 by construction.')
 # Caption analyses remain separate from title metrics.
 tcs=sorted([c for c in data['channels'] if c.get('transcriptCount',0)>=2],key=lambda c:c['name'].lower())
 if tcs:
  vals=np.array([[t['per1000Words'] for t in c['transcriptTopics']] for c in tcs]);fig,ax=plt.subplots(figsize=(11,7));im=ax.imshow(vals,cmap='YlGn',aspect='auto',vmin=0);ax.set_yticks(range(len(tcs)),[f"{plotlabel(c,30)} (n={c['transcriptCount']})" for c in tcs]);ax.set_xticks(range(len(TOPICS)),[t[1].replace(' & ',' /\n') for t in TOPICS],rotation=45,ha='right');fig.colorbar(im,ax=ax,label='Keyword matches per 1,000 words');ax.set_title('Caption keyword rates, equally weighted by video');save(fig,'caption-topics','Caption keyword rates','English caption pilot only, at least two videos per publisher. Each video contributes equally after dividing its keyword matches by its own word count. These transparent overlapping indicators are unvalidated; automatic captions are uncorrected and voices are not separated. Longer sessions do not receive greater channel weight.')
  sm=data['transcripts']['similarity'];mp={c['id']:c for c in data['channels']};names=[plotlabel(mp[i],26) for i in sm['channelIds']];fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(sm['matrix'],vmin=0,vmax=1,cmap='YlGn');ax.set_yticks(range(len(names)),names);ax.set_xticks(range(len(names)),names,rotation=60,ha='right');fig.colorbar(im,ax=ax,label='MiniLM cosine');ax.set_title('Caption similarity in a bounded English pilot');save(fig,'caption-similarity','Caption semantic similarity','Pinned all-MiniLM-L6-v2, 384 dimensions: non-overlapping 240-token chunks are averaged within each video, then video vectors are averaged equally within each publisher. Common identity words are masked. At least two captioned videos per publisher. Similarity can reflect genre, narration, shared teachings or ASR, and does not test claims of extraterrestrial origin. Diagonal self-comparisons equal1 by construction.')
 dg=data.get('diagnostics',{})
 if dg:
  paired=dg['matchedTitleCaptionIndicators'];fig,ax=plt.subplots(figsize=(10,6));y=np.arange(len(paired));ax.barh(y-.18,[x['titleShare'] for x in paired],height=.34,color='#345b4b',label='Title has a keyword');ax.barh(y+.18,[x['captionShare'] for x in paired],height=.34,color='#b6a278',label='Caption has a keyword');ax.set_yticks(y,[x['label'] for x in paired]);ax.set_xlim(0,1);ax.set_xlabel('Fraction of matched videos');ax.legend();ax.set_title('What matched titles reveal about caption vocabulary');save(fig,'title-caption-indicators','Matched title and caption indicators','Same English pilot videos in both bars. A match is at least one dictionary keyword; this is vocabulary presence, not semantic agreement. Captions are much longer than titles and therefore have more opportunities to match. Higher caption fractions show that title-only keyword matching omits vocabulary present in captions; they do not quantify topic emphasis.')
  wb=dg['captionWithinBetween'];fig,ax=plt.subplots(figsize=(7,5));ax.boxplot([wb['within']['values'],wb['between']['values']],tick_labels=[f"Same publisher\n{wb['within']['nPairs']} pairs",f"Different publishers\n{wb['between']['nPairs']} pairs"],showfliers=True);ax.set_ylim(-0.1,1);ax.set_ylabel('Caption-vector cosine');ax.set_title('Within- and between-publisher similarity');save(fig,'caption-within-between','Caption similarity by publisher pairing','Each point-pair compares two caption-document vectors. Boxes mark the middle 50%, central lines medians, whiskers the usual 1.5×IQR range. Pairs share documents and are dependent; no significance test or population conclusion is warranted. Similarities may arise from genre, prompt structure, host language and boilerplate.')
  cs=[c for c in data['channels'] if c['durationCount']>=5];fig,ax=plt.subplots(figsize=(8,5));ax.scatter([c['longFormatShare'] for c in cs],[c['meanMedianGapMinutes'] for c in cs],color='#345b4b',s=35);ax.axhline(0,color='#999',lw=.8);ax.set_xlabel('Share of measured videos at least 30 minutes');ax.set_ylabel('Mean minus median duration (minutes)');ax.set_title('Duration summaries depend on sampled format mix');save(fig,'duration-format','Format mix and mean–median difference','Each point is an account with at least five known durations. The x-axis is the sample share lasting at least 30 minutes, an operational format indicator; the y-axis compares two summaries of the same sample. This descriptive relationship is partly mathematical and does not show a behavioral cause.')
 return figs

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--metadata-file',type=pathlib.Path,default=IN/'fresh_metadata.json')
 parser.add_argument('--recompute-text',action='store_true',help='Re-run pinned model; requires --model-dir and --corpus-file. Default reuses frozen numeric derivatives with fingerprint validation.')
 parser.add_argument('--model-dir',type=pathlib.Path)
 parser.add_argument('--corpus-file',type=pathlib.Path)
 args=parser.parse_args()
 if args.recompute_text and not (args.model_dir and args.corpus_file):parser.error('--recompute-text requires --model-dir and --corpus-file')
 vs,cs,u=assemble(args.metadata_file);by=collections.defaultdict(list)
 from semantic_analysis import language
 for v in vs:
  v['metadataTitleEligible']=v['titleEligible'];v['titleLanguage']=language(v['title'])
  v['titleEligible']=v['titleEligible'] and v['titleLanguage']['code']=='en' and v['titleLanguage']['probability']>=.80 and len(re.findall('[A-Za-z]+',v['title']))>=4
 for v in vs:by[v['channelId']].append(v)
 sim,tops,ctx=similarities(vs,cs)
 for c in cs:
  a=by[c['id']];ds=np.array([v['durationSeconds']/60 for v in a if v.get('durationSeconds') is not None]);ts=[v for v in a if v['titleEligible']];dates=[v['date'] for v in a if v.get('date')];months=collections.Counter(d[:7] for d in dates)
  c['sourceStatus']='Fresh + inherited metadata' if any(v.get('durationSource')=='fresh_watch_metadata' for v in a) else 'Inherited metadata only';c['durationSourceSummary']=dict(collections.Counter(v.get('durationSource') for v in a if v.get('durationSeconds') is not None))
  c['meanMedianGapMinutes']=float(np.mean(ds)-np.median(ds)) if len(ds) else None;c['longFormatShare']=float(np.mean(ds>=30)) if len(ds) else None;c['lexicalTitleCount']=sum(v['titleEligible'] and len(clean(v['title']).split())>=2 for v in a);c['embeddingTitleCount']=sum(v['titleEligible'] for v in a);c['metadataTitleCount']=sum(v.get('metadataTitleEligible',False) for v in a)
  c.update(videoCount=len(a),durationCount=len(ds),durationCoverage=len(ds)/len(a) if a else None,meanMinutes=float(np.mean(ds)) if len(ds) else None,medianMinutes=float(np.median(ds)) if len(ds) else None,q1Minutes=float(np.percentile(ds,25)) if len(ds) else None,q3Minutes=float(np.percentile(ds,75)) if len(ds) else None,minMinutes=float(min(ds)) if len(ds) else None,maxMinutes=float(max(ds)) if len(ds) else None,dateCount=len(dates),titleCount=len(ts),firstDate=min(dates) if dates else None,lastDate=max(dates) if dates else None,monthly=[{'month':m,'count':n} for m,n in sorted(months.items())],durationBins=[{'label':label,'count':int(np.sum((ds>=lo)&(ds<hi)))} for label,lo,hi in [('Under 5m',0,5),('5–15m',5,15),('15–30m',15,30),('30–60m',30,60),('60m+',60,float('inf'))]],topics=[{'id':tid,'label':label,'count':sum(bool(re.search(p,v['title'],re.I)) for v in ts),'share':sum(bool(re.search(p,v['title'],re.I)) for v in ts)/len(ts) if ts else None} for tid,label,p in TOPICS],topTerms=tops.get(c['id'],[]))
 cs.sort(key=lambda c:(-c['videoCount'],c['name'].lower()))
 data={'meta':{'version':'round3','checkedAt':CUTOFF,'scope':'Merged purposive research index; account routes, not a census of mediums.','durationDefinition':'Arithmetic mean of available eligible video durations in the indexed sample.','frequencyDefinition':'Counts of indexed videos with exact reported upload dates; not a channel posting rate.','textMethod':'Transparent English keyword indicators; identity-masked title TF-IDF baseline; pinned all-MiniLM-L6-v2 title and caption embeddings with sensitivity checks.','transcriptStatus':'Separate bounded caption pilot; see transcripts section.', 'titleLanguagePolicy':'langdetect1.0.9 seed42: English probability≥0.80 and≥4alphabetic words. Statistical heuristic; short titles may be excluded. Current watch-page titles supersede supplied translations, with variants retained.','sourceSnapshotSha256':hashlib.sha256((ROOT/'dist/data.json').read_bytes()).hexdigest()},'coverage':{'videoCount':len(vs),'channelCount':len(cs),'attributedVideoCount':sum(bool(v['channelId']) for v in vs),'unattributedVideoCount':sum(not v['channelId'] for v in vs),'durationCount':sum(v['durationSeconds'] is not None for v in vs),'dateCount':sum(bool(v['date']) for v in vs),'titleCount':sum(v['titleEligible'] for v in vs),'transcriptCount':0},'channels':cs,'videos':vs,'topics':[{'id':i,'label':l,'regex':p} for i,l,p in TOPICS],'similarity':sim,'limitations':['Search and curated research samples are nonrandom and incomplete. No population prevalence or channel-wide posting rate is estimated.','Durations imported from the supplied Claude draft retain their unverified-provider provenance.','Missing duration and date values remain null; relative dates are not converted to exact dates.','Account routes are only merged using explicit aliases/IDs; unresolved aliases can split an account.','Distinct uploads can repeat the same original session. Video-ID deduplication does not establish recording-level independence.','Title vocabulary reflects publishers and upload packaging; it is not transcript content or evidence about the ontological source of channeling.'],'robustness':[]}
 from semantic_analysis import Encoder,analyze,diagnostics,LANG_CACHE
 fingerprint=hashlib.sha256(json.dumps(sorted([[v['id'],v['title'],v['channelId'],v['titleEligible']] for v in vs]),ensure_ascii=False).encode()).hexdigest()
 feature_path=IN/'derived_text_features.json'
 feature_keys=['semanticSimilarity','transcripts','titleRawSimilarity','deduplicatedTitleSimilarity','matchedTitleSimilarity','matchedCaptionSimilarity','diagnostics','robustness']
 if args.recompute_text:
  encoder=Encoder(args.model_dir);data=analyze(data,encoder,IDENTITY,TOPICS,args.corpus_file);data=diagnostics(data,encoder,IDENTITY)
  bundle={k:data[k] for k in feature_keys};bundle['observationFingerprint']=fingerprint
  bundle['channelFeatures']={c['id']:{k:c[k] for k in ['transcriptCount','retrievedCaptionCount','transcriptTopics'] if k in c} for c in data['channels']}
  dump(feature_path,bundle);dump(IN/'model_manifest.json',encoder.manifest)
 else:
  if not feature_path.exists():raise RuntimeError('No frozen numeric text features. Run --recompute-text with explicit local model and corpus paths.')
  bundle=load(feature_path)
  if bundle['observationFingerprint']!=fingerprint:raise RuntimeError('Metadata or title language changed: frozen embedding features do not match. Recompute text explicitly.')
  for k in feature_keys:data[k]=bundle[k]
  for c in data['channels']:c.update(bundle['channelFeatures'].get(c['id'],{}))
  data['coverage']['transcriptCount']=data['transcripts']['available'];data['coverage']['englishPilotCount']=data['transcripts']['englishPilotCount']
 dump(IN/'language_cache.json',LANG_CACHE)
 data['meta']['reproducibility']='Default build uses frozen metadata, language decisions and numeric text features, fingerprint-checked. --recompute-text runs the pinned ONNX model against a separately obtained local caption corpus; no raw captions are distributed.'
 data['meta']['wordTokenizer']="[A-Za-z]+(?:'[A-Za-z]+)?; contractions are one token"
 data['coverage']['freshDurationCount']=sum(v['durationSource']=='fresh_watch_metadata' for v in vs)
 data['coverage']['inheritedDurationCount']=sum(v['durationSource']=='claude_provider_metadata_unverified' for v in vs)
 data['coverage']['freshDateCount']=sum(v['dateSource']=='fresh_watch_metadata_UTC' for v in vs)
 data['coverage']['channelGroupsWithVideos']=sum(c['videoCount']>0 for c in cs)
 data['coverage']['channelGroupsWithDurations']=sum(c['durationCount']>0 for c in cs)
 data['coverage']['embeddedTitleCount']=data['semanticSimilarity']['documentCount']
 data['coverage']['attributedTitleCount']=sum(v['titleEligible'] and bool(v['channelId']) for v in vs)
 data['figures']=makeplots(data);dump(OUT/'data.json',data)
 csvout('channel-metrics.csv',cs,['id','name','url','videoCount','durationCount','durationCoverage','meanMinutes','medianMinutes','q1Minutes','q3Minutes','minMinutes','maxMinutes','dateCount','titleCount','firstDate','lastDate','sourceStatus','durationSourceSummary','meanMedianGapMinutes','longFormatShare','lexicalTitleCount','embeddingTitleCount','transcriptCount'])
 csvout('video-observations.csv',vs,['id','url','title','channelId','publisher','observedPublisher','durationSeconds','durationSource','date','dateSource','titleEligible','titleSource','relativeDateText','relativeDateAsOf','conflicts','provenance'])
 csvout('title-similarity-pairs.csv',sim.get('pairs',[]),['a','b','cosine','nA','nB'])
 csvout('title-topic-indicators.csv',[dict(channelId=c['id'],channelName=c['name'],titleCount=c['titleCount'],**t) for c in cs for t in c['topics']],['channelId','channelName','titleCount','id','label','count','share'])
 csvout('semantic-title-pairs.csv',data.get('semanticSimilarity',{}).get('pairs',[]),['a','b','cosine','nA','nB'])
 csvout('caption-documents.csv',data.get('transcripts',{}).get('rows',[]),['videoId','channelId','url','wordCount','language','automaticCaptions','captionArtifactSha256','textSha256','selection'])
 csvout('caption-similarity-pairs.csv',data.get('transcripts',{}).get('similarity',{}).get('pairs',[]),['a','b','cosine','nA','nB'])
 csvout('caption-topic-indicators.csv',[dict(videoId=r['videoId'],channelId=r['channelId'],wordCount=r['wordCount'],**t) for r in data.get('transcripts',{}).get('rows',[]) for t in r['topics']],['videoId','channelId','wordCount','id','label','count','per1000Words'])
 csvout('matched-title-caption-indicators.csv',data.get('diagnostics',{}).get('matchedTitleCaptionIndicators',[]),['id','label','videoCount','titleMatchCount','captionMatchCount','titleShare','captionShare'])
 csvout('caption-pair-diagnostics.csv',[{'pairType':kind,'cosine':v} for kind,x in data.get('diagnostics',{}).get('captionWithinBetween',{}).items() if isinstance(x,dict) for v in x['values']],['pairType','cosine'])
 csvout('balanced-title-stability.csv',data.get('diagnostics',{}).get('equalFiveTitleStability',[]),['channelId','mostFrequentNearestChannel','repeatShare','iterations','sampledTitlesPerChannel'])
 csvout('monthly-indexed-counts.csv',[dict(channelId=c['id'],channelName=c['name'],**m) for c in cs for m in c['monthly']],['channelId','channelName','month','count'])
 print(json.dumps(data['coverage']));print('figures',len(data['figures']))
if __name__=='__main__':main()
