#!/usr/bin/env python3
"""Independent expansion checks; never imports analysis producer or its helpers.

Uses pairwise absolute differences for Gini, stdlib quantiles, direct vector dots,
and explicit pair enumeration. SHA pins describe the particular inspected files.
"""
from __future__ import annotations
import ast, collections, hashlib, itertools, json, math, pathlib, re, statistics, unicodedata
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXP=ROOT/'research/expansion'
SOURCE=ROOT/'dist/analysis/data.json'
RESULT=EXP/'analysis/results.json'
d=json.loads(SOURCE.read_text()); r=json.loads(RESULT.read_text()); checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,label,actual=None,expected=None):
 checks.append({'check':label,'passed':bool(ok),'actual':actual,'expected':expected})
def eq(a,b,label,tol=1e-9):
 if a is None or b is None:check(a is b,label,a,b)
 elif isinstance(a,(int,float)) and isinstance(b,(int,float)):check(math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol),label,a,b)
 else:check(a==b,label,a,b)
def qlinear(xs,p):
 x=sorted(xs);pos=(len(x)-1)*p;i=int(pos);f=pos-i
 return x[i]+f*(x[min(i+1,len(x)-1)]-x[i])
def stats(xs):
 return {'n':len(xs),'mean':statistics.mean(xs),'median':statistics.median(xs),'q1':qlinear(xs,.25),'q3':qlinear(xs,.75),'min':min(xs),'max':max(xs)} if xs else {'n':0,'mean':None,'median':None,'q1':None,'q3':None,'min':None,'max':None}
def checkstats(actual,values,label,tol=1e-9):
 for k,v in stats(values).items():eq(actual[k],v,label+'.'+k,tol)
vs=d['videos']; by=collections.defaultdict(list)
for v in vs:by[v.get('channelId')].append(v)
check(len(vs)==len({v['id'] for v in vs}),'Unique source video IDs')
eq(sha(SOURCE),r['source']['sha256'],'snapshot hash')
eq(sha(EXP/'analysis/protocol.json'),r['source']['protocolSha256'],'protocol hash')
eq(len(vs),r['coverage']['uploads'],'upload denominator')
counts=[len(x) for cid,x in by.items() if cid is not None]; N=sum(counts);K=len(counts)
s=sorted(counts,reverse=True);hhi=sum((x/N)**2 for x in counts)
gini=sum(abs(x-y) for x in counts for y in counts)/(2*K*N)
c=r['concentration']
for k,v in {'accountGroupsWithUploads':K,'attributedUploads':N,'unattributedUploads':len(by[None]),'gini':gini,'hhi':hhi,'effectiveEquallyRepresentedAccounts':1/hhi}.items():eq(c[k],v,'concentration.'+k)
for k in [1,5,10,20]:eq(c[f'top{k}Share'],sum(s[:k])/N,f'top{k}Share')
pilot={x['videoId'] for x in d['transcripts']['rows']};pilot_cids={v['channelId'] for v in vs if v['id'] in pilot};dur=lambda v:v.get('durationSeconds') is not None and v['durationSeconds']>0
sets={'captionPilotKnownDuration':[v for v in vs if v['id'] in pilot and dur(v)],'otherIndexedKnownDuration':[v for v in vs if v['id'] not in pilot and dur(v)],'otherUploadsInPilotAccountsKnownDuration':[v for v in vs if v['id'] not in pilot and v.get('channelId') in pilot_cids and dur(v)]}
for k,rows in sets.items():checkstats(r['captionSelection'][k],[v['durationSeconds']/60 for v in rows],'selection.'+k)
eq(r['captionSelection']['pilotAccounts'],len(pilot_cids),'pilot accounts')
positive=sum(dur(v) for v in vs);eligible=sum(bool(v.get('titleEligible')) for v in vs)
missing={x['measure']:x for x in r['coverage']['missingness']}
for name,num in [('Publishing account resolved',N),('Positive upload duration',positive),('Exact upload date',sum(bool(v.get('date')) for v in vs)),('English-likely eligible title',eligible),('Frozen English caption pilot',len(pilot))]:
 x=missing[name];eq(x['available'],num,'missingness '+name);eq(x['unavailable'],len(vs)-num,'missing count '+name)
bands=[('Under 5m',0,300),('5–15m',300,900),('15–30m',900,1800),('30–60m',1800,3600),('60m+',3600,float('inf'))]
valid=[v for v in vs if v.get('titleEligible') and dur(v)];keyword={(x['topicId'],x['band']):x for x in r['keywordByDuration']};contrasts={x['topicId']:x for x in r['keywordContrasts']};direction=[]
for t in d['topics']:
 # Frozen JSON encodes regex backslashes twice; decoding one literal slash
 # level recovers intended word boundaries. Verify this explicitly.
 pattern=t['regex'].replace('\\\\','\\');rex=re.compile(pattern,re.IGNORECASE)
 check(rex.search('contact') is not None if t['id']=='contact' else True,'regex decoding '+t['id'])
 for label,lo,hi in bands:
  rows=[v for v in valid if lo<=v['durationSeconds']<hi];hit=sum(rex.search(v['title']) is not None for v in rows);out=keyword[t['id'],label]
  eq(out['matches'],hit,'keyword hits '+t['id']+' '+label);eq(out['eligibleTitles'],len(rows),'keyword denominator '+t['id']+' '+label);eq(out['share'],hit/len(rows) if rows else None,'keyword share '+t['id']+' '+label)
 short=[v for v in valid if v['durationSeconds']<1800];long=[v for v in valid if v['durationSeconds']>=1800]
 rate=lambda rows:sum(rex.search(v['title']) is not None for v in rows)/len(rows)
 pooled=rate(long)-rate(short);paired=[]
 for cid in by:
  if cid is None:continue
  ss=[v for v in short if v.get('channelId')==cid];ll=[v for v in long if v.get('channelId')==cid]
  if len(ss)>=3 and len(ll)>=3:paired.append(rate(ll)-rate(ss))
 out=contrasts[t['id']];eq(out['pooledLongMinusShortShare'],pooled,'pooled difference '+t['id']);eq(out['eligiblePairedAccounts'],len(paired),'paired accounts '+t['id']);checkstats(out['accountDifferenceSummary'],paired,'paired summary '+t['id'])
 sign=lambda x:0 if x==0 else (1 if x>0 else -1)
 match=sign(pooled)==sign(statistics.median(paired)) if paired else None;eq(out['sameDirectionAsPairedMedian'],match,'direction match '+t['id']);direction.append({'id':t['id'],'pooled':pooled,'paired_median':statistics.median(paired),'same_direction':match})
# Read a literal baseline mask; do not invoke its implementation.
tree=ast.parse((ROOT/'research/analysis/build_analysis.py').read_text());mask=None
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IDENTITY' for t in node.targets):mask=ast.literal_eval(node.value.func.value).split()
check(mask is not None,'baseline identity mask found')
def normalize(text,drop=()):
 text=unicodedata.normalize('NFKD',text).casefold();text=''.join(ch for ch in text if unicodedata.category(ch)!='Mn'); words=re.findall(r'\w+',text)
 excluded={unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode() for x in drop}
 return ' '.join(w for w in words if w not in excluded)
for mode,drop in [('normalized',()),('nameAndGenreMasked',mask)]:
 fam=collections.defaultdict(list)
 for v in vs:
  if v.get('titleEligible'):
   key=normalize(v['title'],drop)
   if key:fam[key].append(v)
 repeats=[x for x in fam.values() if len(x)>1]
 expected={'nonemptyEligibleTitleDocuments':sum(len(x) for x in fam.values()),'uniqueNormalizedStrings':len(fam),'repeatedStringFamilies':len(repeats),'documentsInRepeatedFamilies':sum(len(x) for x in repeats),'crossPublisherRepeatedFamilies':sum(len({v.get('channelId') for v in x})>1 for x in repeats)}
 for k,v in expected.items():eq(r['duplicateTitles']['variants'][mode][k],v,'dedup '+mode+' '+k)
# Direct double-precision vector dot products; no sklearn cosine or producer code.
ca=np.load(ROOT/'dist/analysis/caption-embeddings.npz');ta=np.load(ROOT/'dist/analysis/title-embeddings.npz');ci={str(v):i for i,v in enumerate(ca['video_ids'])};ti={str(v):i for i,v in enumerate(ta['video_ids'])};common=sorted(set(ci)&set(ti));cids={v['id']:v.get('channelId') for v in vs}
for rep,z,index,ids in [('matchedCaption',ca,ci,common),('matchedTitle',ta,ti,common),('allCaption',ca,ci,sorted(ci))]:
 v=np.array([z['vectors'][index[id]] for id in ids],dtype=np.float64);v/=np.sqrt(np.sum(v*v,axis=1))[:,None];same=[];diff=[];pairs=[]
 for a,b in itertools.combinations(range(len(ids)),2):
  cos=float(sum(v[a]*v[b]));(same if cids[ids[a]]==cids[ids[b]] else diff).append(cos);pairs.append((a,b,cos))
 out=r['embeddingWithinBetween'][rep];eq(out['documents'],len(ids),'embedding '+rep+' documents');eq(out['publishers'],len({cids[id] for id in ids}),'embedding '+rep+' publishers');check(all(cids[id] is not None for id in ids),'matched publisher labels resolved '+rep)
 checkstats(out['within'],same,rep+' within',tol=5e-7);checkstats(out['between'],diff,rep+' between',tol=5e-7);eq(out['meanDifference'],statistics.mean(same)-statistics.mean(diff),rep+' mean difference',tol=5e-7)
 # New equal-account and omission diagnostics, independently from direct pairs.
 groups=collections.defaultdict(list)
 for ix,id in enumerate(ids):groups[cids[id]].append(ix)
 balanced=[];balanced_rows={x['publisherId']:x for x in out['accountBalanced']['rows']}
 for cid,ixs in groups.items():
  if len(ixs)<2:continue
  within_values=[cos for a,b,cos in pairs if a in ixs and b in ixs]
  other_means=[]
  for other,jxs in groups.items():
   if other==cid:continue
   cross=[float(sum(v[i]*v[j])) for i in ixs for j in jxs];other_means.append(statistics.mean(cross))
  w=statistics.mean(within_values);b=statistics.mean(other_means);balanced.append(w-b);row=balanced_rows[cid]
  eq(row['documents'],len(ixs),rep+' balanced documents '+cid);eq(row['withinPairs'],len(within_values),rep+' balanced pairs '+cid)
  eq(row['withinMean'],w,rep+' balanced within '+cid,tol=5e-7);eq(row['betweenOtherAccountMean'],b,rep+' balanced between '+cid,tol=5e-7);eq(row['difference'],w-b,rep+' balanced difference '+cid,tol=5e-7)
 eq(out['accountBalanced']['eligiblePublishers'],len(balanced),rep+' balanced publishers');eq(out['accountBalanced']['meanDifference'],statistics.mean(balanced),rep+' balanced separation',tol=5e-7)
 eq(out['publishersWithWithinPairs'],len(balanced),rep+' non-singleton publishers');eq(out['singletonPublishers'],sum(len(x)==1 for x in groups.values()),rep+' singleton publishers')
 omissions=[];omission_rows={x['omittedPublisherId']:x for x in out['leaveOnePublisherOut']['rows']}
 for cid,ixs in groups.items():
  keep=[i for i in range(len(ids)) if i not in ixs];w=[cos for a,b,cos in pairs if a in keep and b in keep and cids[ids[a]]==cids[ids[b]]];b=[cos for a,b,cos in pairs if a in keep and b in keep and cids[ids[a]]!=cids[ids[b]]];gap=statistics.mean(w)-statistics.mean(b);omissions.append(gap);row=omission_rows[cid]
  eq(row['retainedDocuments'],len(keep),rep+' omitted documents '+cid);eq(row['withinPairs'],len(w),rep+' omitted within-pairs '+cid);eq(row['betweenPairs'],len(b),rep+' omitted between-pairs '+cid);eq(row['meanDifference'],gap,rep+' omitted difference '+cid,tol=5e-7)
 checkstats(out['leaveOnePublisherOut']['summary'],omissions,rep+' omission summary',tol=5e-7)
 labels=[cids[id] for id in ids];rng=np.random.default_rng(42);null=[]
 for _ in range(2000):
  sh=rng.permutation(labels);within=[c for a,b,c in pairs if sh[a]==sh[b]];between=[c for a,b,c in pairs if sh[a]!=sh[b]];null.append(statistics.mean(within)-statistics.mean(between))
 checkstats(out['permutationReference'],null,rep+' permutation',tol=5e-7)
 eq(out['observedReferencePercentile'],sum(x<statistics.mean(same)-statistics.mean(diff) for x in null)/len(null),rep+' descriptive percentile')
 check(out['referencePermutations']==2000 and out['referenceSeed']==42,'permutation count/seed '+rep)
 check('not a population p-value' in out['referenceMeaning'],'permutation interpretation '+rep)
cross=r['embeddingWithinBetween']['crossLayerContrast'];cap=r['embeddingWithinBetween']['matchedCaption'];tit=r['embeddingWithinBetween']['matchedTitle']
eq(cross['matchedDocuments'],len(common),'crosslayer matched documents');eq(cross['matchedPublishers'],len({cids[x] for x in common}),'crosslayer matched publishers');eq(cross['captionMinusTitlePooledMeanDifference'],cap['meanDifference']-tit['meanDifference'],'crosslayer pooled gap');eq(cross['captionMinusTitleAccountBalancedDifference'],cap['accountBalanced']['meanDifference']-tit['accountBalanced']['meanDifference'],'crosslayer account gap')
for path,key in [(ROOT/'dist/analysis/caption-embeddings.npz','captionEmbeddingsSha256'),(ROOT/'dist/analysis/title-embeddings.npz','titleEmbeddingsSha256')]:eq(sha(path),r['source'][key],key)
failed=[x for x in checks if not x['passed']]
report={'role':'independent AI methods reviewer; technical verification, not human construct validation','source_sha256':sha(SOURCE),'result_sha256':sha(RESULT),'producer_sha256':sha(EXP/'analysis/analyze.py'),'checks':len(checks),'failures':failed,'status':'PASS' if not failed else 'FAIL','independence':'No producer import. Gini via pairwise absolute differences; summaries via stdlib; cosine via double-precision direct dot; exact publisher-label null regenerated.','decisive_results':{'top10_share':sum(s[:10])/N,'gini':gini,'hhi':hhi,'pilot_median_minutes':statistics.median([v['durationSeconds']/60 for v in sets['captionPilotKnownDuration']]),'other_median_minutes':statistics.median([v['durationSeconds']/60 for v in sets['otherIndexedKnownDuration']]),'matched_documents':len(common),'matched_publishers':len({cids[x] for x in common}),'keyword_direction_comparison':direction},'limitations':['Checks validate arithmetic and implemented definitions, not caption correctness, semantic validity, identity joins or representativeness.','Permutation reference is a diagnostic under hypothetical label exchangeability, not an inferential p-value.','Paired medians can be zero; pooled-versus-paired direction mismatch must not be called direction reversal.'],'all_checks':checks}
(HERE/'independent-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['status','checks','failures','decisive_results']},indent=2));raise SystemExit(bool(failed))
