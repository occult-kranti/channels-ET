#!/usr/bin/env python3
"""Derive paper diagnostics from the frozen published pilot without changing it."""
import csv,hashlib,json,pathlib,math
import numpy as np
from scipy.stats import spearmanr
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'research/paper/generated';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'dist/analysis/data.json'
PINNED='f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc'

def pairs(s):return {tuple(sorted([x['a'],x['b']])):x['cosine'] for x in s['pairs']}
def compare(a,b):
 x,y=pairs(a),pairs(b);keys=sorted(set(x)&set(y))
 return {'nPairs':len(keys),'rho':float(spearmanr([x[k] for k in keys],[y[k] for k in keys]).statistic),'pairs':[{'a':k[0],'b':k[1],'titleCosine':x[k],'captionCosine':y[k]} for k in keys]}
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
def writecsv(p,rs,fields):
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rs)
def main():
 h=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
 if h!=PINNED:raise RuntimeError(f'Expected published snapshot {PINNED}; got {h}. Review and explicitly repin a changed corpus.')
 d=json.loads(SOURCE.read_text());channels={x['id']:x for x in d['channels']};videos={x['id']:x for x in d['videos']}
 a=d['matchedTitleSimilarity'];b=d['matchedCaptionSimilarity'];assert a['channelIds']==b['channelIds']
 matched=compare(a,b);lopo=[]
 for excluded in a['channelIds']:
  rows=[p for p in matched['pairs'] if excluded not in (p['a'],p['b'])]
  lopo.append({'omittedChannelId':excluded,'omittedPublisher':channels[excluded]['name'],'retainedPublishers':len(a['channelIds'])-1,'retainedPairs':len(rows),'rho':float(spearmanr([p['titleCosine'] for p in rows],[p['captionCosine'] for p in rows]).statistic)})
 rows=d['transcripts']['rows'];lengths=np.array([r['wordCount'] for r in rows]);longest=max(rows,key=lambda r:r['wordCount']);shortest=min(rows,key=lambda r:r['wordCount'])
 eligible_matched=[r for r in rows if videos[r['videoId']]['titleEligible'] and videos[r['videoId']]['channelId']]
 contributing=[r for r in eligible_matched if r['channelId'] in a['channelIds']]
 assert len(contributing)==22 and len(eligible_matched)==25
 focal_ids=['ch-73032cea690b','ch-4deae3e4c229','ch-3ccbf336c582','ch-4f327ca79023','ch-e7ffb2da4c80','ch-ff85f37eb9b1','ch-033701dde894','ch-aaaebac2693b']
 display={'ch-73032cea690b':'Bashar (official)','ch-4deae3e4c229':'Athina Król','ch-3ccbf336c582':'The Galactic Guide','ch-4f327ca79023':'RIZ & Lady O','ch-e7ffb2da4c80':'Lorie Ladd','ch-ff85f37eb9b1':'Divine Insights','ch-033701dde894':'Bashar Channeling Podcast','ch-aaaebac2693b':'Daniel Scranton'}
 focal=[{k:channels[i][k] for k in ['id','name','url','videoCount','durationCount','meanMinutes','medianMinutes','q1Minutes','q3Minutes','longFormatShare','durationSourceSummary']}|{'displayName':display[i]} for i in focal_ids]
 language=dict(d['transcripts']['captionLanguages']);caption_english=sum(language.get(k,0) for k in ['en','en-US'])
 coverage={'indexedVideos':d['coverage']['videoCount'],'watchMetadataSuccesses':878,'durationKnown':d['coverage']['durationCount'],'durationFresh':d['coverage']['freshDurationCount'],'durationInherited':d['coverage']['inheritedDurationCount'],'dateKnown':d['coverage']['dateCount'],'attributedVideos':d['coverage']['attributedVideoCount'],'routeGroups':d['coverage']['channelCount'],'groupsWithVideos':d['coverage']['channelGroupsWithVideos'],'groupsWithDurations':d['coverage']['channelGroupsWithDurations'],'englishLikelyTitles':d['coverage']['titleCount'],'embeddedTitles':d['coverage']['embeddedTitleCount'],'titleGroupsMinFive':len(d['semanticSimilarity']['channelIds']),'captionAttempted':d['transcripts']['attempted'],'captionAvailable':d['transcripts']['available'],'captionEnglish':caption_english,'captionPilot':len(rows),'captionPublishers':len({r['channelId'] for r in rows}),'captionComparisonPublishers':len(d['transcripts']['similarity']['channelIds']),'captionComparisonDocuments':sum(r['channelId'] in d['transcripts']['similarity']['channelIds'] for r in rows),'matchedEligibleDocuments':len(eligible_matched),'matchedContributingDocuments':len(contributing),'matchedPublishers':len(a['channelIds']),'matchedPairs':matched['nPairs']}
 diag=d['diagnostics'];sens=[{'comparison':'Raw vs identity-masked titles','cohort':'Title publishers','publishers':len(d['semanticSimilarity']['channelIds']),'pairs':diag['rawVsMaskedTitles']['pairCount'],'rho':diag['rawVsMaskedTitles']['spearmanRankCorrelation']},{'comparison':'All vs deduplicated titles','cohort':'Title publishers','publishers':len(d['semanticSimilarity']['channelIds']),'pairs':diag['deduplicatedVsAllTitles']['pairCount'],'rho':diag['deduplicatedVsAllTitles']['spearmanRankCorrelation']},{'comparison':'Full vs positionally trimmed captions','cohort':'Caption publishers','publishers':len(d['transcripts']['similarity']['channelIds']),'pairs':diag['captionFullVsTrimmed']['pairCount'],'rho':diag['captionFullVsTrimmed']['spearmanRankCorrelation']},{'comparison':'Matched titles vs matched captions','cohort':'Matched publishers','publishers':len(a['channelIds']),'pairs':matched['nPairs'],'rho':matched['rho']}]
 # Quantify nearest-neighbor changes, separate from rank correlation.
 def nearest(s):
  M=np.array(s['matrix']);np.fill_diagonal(M,-np.inf);return {i:s['channelIds'][int(np.argmax(M[j]))] for j,i in enumerate(s['channelIds'])}
 nn1,nn2=nearest(d['transcripts']['similarity']),nearest(d['transcripts']['trimmedSimilarity']);neighbor_changes=sum(nn1[k]!=nn2[k] for k in nn1)
 out={'source':{'path':'dist/analysis/data.json','sha256':h,'checkedAt':d['meta']['checkedAt'],'phase':'paper-round4','software':{'numpy':np.__version__}},'coverage':coverage,'focalDurations':focal,'sensitivity':sens,'matched':matched,'leaveOnePublisherOut':{'method':'For each publisher, remove every channel-pair comparison containing that publisher, then recompute Spearman rank correlation across retained off-diagonal cosine pairs. No resampling; no independence assumption or inferential interval.','rangeMeaning':'Minimum and maximum across these deterministic omissions; descriptive sensitivity range, not a confidence interval.','minRho':min(x['rho'] for x in lopo),'maxRho':max(x['rho'] for x in lopo),'rows':lopo},'captionLengths':{'unit':"Tokens matching [A-Za-z]+(?:'[A-Za-z]+)?; contractions count once",'n':len(lengths),'sum':int(lengths.sum()),'mean':float(lengths.mean()),'median':float(np.median(lengths)),'q1':float(np.percentile(lengths,25)),'q3':float(np.percentile(lengths,75)),'min':int(lengths.min()),'max':int(lengths.max()),'longest':{'videoId':longest['videoId'],'publisher':channels[longest['channelId']]['name'],'words':longest['wordCount']},'shortest':{'videoId':shortest['videoId'],'publisher':channels[shortest['channelId']]['name'],'words':shortest['wordCount']},'rows':[{'videoId':r['videoId'],'channelId':r['channelId'],'publisher':channels[r['channelId']]['name'],'words':r['wordCount'],'automaticCaptions':r['automaticCaptions']} for r in rows]},'captionTrimNearestNeighborChanges':{'changed':neighbor_changes,'eligiblePublishers':len(nn1)},'withinBetween':{k:{kk:vv for kk,vv in v.items() if kk!='values'} for k,v in diag['captionWithinBetween'].items() if isinstance(v,dict)},'limitations':['Purposive, incomplete upload samples. No channel-population mean, census or posting rate is estimated.','Uploader accounts and human practitioners are distinct. Route groups can include unresolved aliases.','The 55 pairwise observations share 11 publishers and are not independent; no p-values or confidence intervals are reported.','Twenty-five videos have eligible matched text; only 22 in publishers with at least two videos support the matched channel-matrix comparison.','Language detection and caption-track language labels are not manual content verification.','Equal chunk pooling overweights a short final chunk relative to token weighting; this is a method sensitivity candidate, not a reason to infer an ontological source.']}
 dump(OUT/'paper-results.json',out)
 writecsv(OUT/'leave-one-publisher-out.csv',lopo,['omittedChannelId','omittedPublisher','retainedPublishers','retainedPairs','rho'])
 writecsv(OUT/'matched-pair-cosines.csv',matched['pairs'],['a','b','titleCosine','captionCosine'])
 writecsv(OUT/'caption-lengths.csv',out['captionLengths']['rows'],['videoId','channelId','publisher','words','automaticCaptions'])
 writecsv(OUT/'focal-durations.csv',focal,['id','name','url','videoCount','durationCount','meanMinutes','medianMinutes','q1Minutes','q3Minutes','longFormatShare'])
 print(json.dumps({'coverage':coverage,'matchedRho':matched['rho'],'lopoRange':[out['leaveOnePublisherOut']['minRho'],out['leaveOnePublisherOut']['maxRho']],'captionLengths':{k:v for k,v in out['captionLengths'].items() if k not in ['rows','unit']}}))
if __name__=='__main__':main()
