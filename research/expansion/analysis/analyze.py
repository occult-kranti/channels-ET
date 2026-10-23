#!/usr/bin/env python3
"""Exploratory frozen-snapshot diagnostics; does not retrieve videos or captions."""
from __future__ import annotations
import argparse, ast, collections, csv, hashlib, json, math, pathlib, re, unicodedata
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
PIN = 'f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc'
BANDS = [('Under 5m', 0, 300), ('5–15m', 300, 900), ('15–30m', 900, 1800), ('30–60m', 1800, 3600), ('60m+', 3600, math.inf)]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False))
def table(p, rows):
    if not rows: return
    with p.open('w', newline='') as f:
        w=csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
def summary(x):
    a=np.asarray(x,dtype=float)
    return {'n':len(a),'mean':float(a.mean()) if len(a) else None,'median':float(np.median(a)) if len(a) else None,'q1':float(np.percentile(a,25)) if len(a) else None,'q3':float(np.percentile(a,75)) if len(a) else None,'min':float(a.min()) if len(a) else None,'max':float(a.max()) if len(a) else None}
def identity_words():
    tree=ast.parse((ROOT/'research/analysis/build_analysis.py').read_text())
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IDENTITY' for t in n.targets):
            return ast.literal_eval(n.value.func.value).split()
    raise AssertionError('Documented mask not found')
def normalized(title, mask=()):
    s=unicodedata.normalize('NFKD',title).casefold()
    words=re.findall(r'\w+', ''.join(c for c in s if not unicodedata.combining(c)))
    excluded={unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode() for x in mask}
    return ' '.join(w for w in words if w not in excluded)
def pair_diagnostic(ids, vectors, channels, rng, nperm=2000):
    m=cosine_similarity(vectors); ii,jj=np.triu_indices(len(ids),1); vals=m[ii,jj]
    labels=np.asarray([channels[v] for v in ids]); same=labels[ii]==labels[jj]
    observed=float(vals[same].mean()-vals[~same].mean())
    ref=[]
    for _ in range(nperm):
        sh=rng.permutation(labels); w=sh[ii]==sh[jj]
        ref.append(float(vals[w].mean()-vals[~w].mean()))
    rows=[{'a':ids[i],'b':ids[j],'publisherA':channels[ids[i]],'publisherB':channels[ids[j]],'samePublisher':bool(channels[ids[i]]==channels[ids[j]]),'cosine':float(m[i,j])} for i,j in zip(ii,jj)]
    account_rows=[];lopo=[];unique=sorted(set(labels))
    for c in unique:
        idx=np.flatnonzero(labels==c);within_idx=[(i,j) for i in idx for j in idx if i<j]
        if within_idx:
            # Equal other-account means, then equal eligible focal-account means.
            within_c=float(np.mean([m[i,j] for i,j in within_idx]))
            between_c=float(np.mean([m[np.ix_(idx,np.flatnonzero(labels==other))].mean() for other in unique if other!=c]))
            account_rows.append({'publisherId':str(c),'documents':len(idx),'withinPairs':len(within_idx),'withinMean':within_c,'betweenOtherAccountMean':between_c,'difference':within_c-between_c})
        retain=(labels[ii]!=c)&(labels[jj]!=c)
        if np.any(retain&same) and np.any(retain&~same):
            lopo.append({'omittedPublisherId':str(c),'retainedDocuments':len(ids)-len(idx),'withinPairs':int(np.sum(retain&same)),'betweenPairs':int(np.sum(retain&~same)),'meanDifference':float(vals[retain&same].mean()-vals[retain&~same].mean())})
    return {'documents':len(ids),'publishers':len(unique),'publishersWithWithinPairs':len(account_rows),'singletonPublishers':int(sum(np.sum(labels==c)==1 for c in unique)),'within':summary(vals[same]),'between':summary(vals[~same]),'meanDifference':observed,'accountBalanced':{'eligiblePublishers':len(account_rows),'meanDifference':float(np.mean([r['difference'] for r in account_rows])),'method':'Within-publisher unordered pair mean minus equal-other-publisher cross-pair mean, then equal-weight mean across focal publishers with at least two documents. Singleton publishers contribute only to between-publisher reference.','rows':account_rows},'leaveOnePublisherOut':{'summary':summary([r['meanDifference'] for r in lopo]),'rows':lopo,'meaning':'Deterministic influence range after omitting each publisher; not a confidence interval.'},'referencePermutations':nperm,'referenceSeed':42,'permutationReference':summary(ref),'observedReferencePercentile':float(np.mean(np.asarray(ref)<observed)),'referenceMeaning':'Publisher-label permutations preserve exact group sizes on fixed vectors. This is a descriptive negative control, not a population p-value, semantic validation, or independent-pair experiment.','permutationValues':ref},rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,default=HERE);args=ap.parse_args()
    dest=args.output; gen=dest/'generated';gen.mkdir(parents=True,exist_ok=True)
    source=ROOT/'dist/analysis/data.json';assert digest(source)==PIN,'Input repin requires explicit new review'
    d=json.loads(source.read_text()); vs=d['videos'];cs=d['channels'];lookup={c['id']:c for c in cs};by=collections.defaultdict(list)
    for v in vs:by[v.get('channelId')].append(v)
    pilot={r['videoId'] for r in d['transcripts']['rows']}
    channels=[]
    for c in cs:
        vv=by[c['id']];measured=[v['durationSeconds']/60 for v in vv if v.get('durationSeconds') is not None and v['durationSeconds']>0]
        channels.append({'id':c['id'],'name':c['name'],'url':c.get('url'),'uploads':len(vv),'knownDurations':len(measured),'eligibleTitles':sum(bool(v.get('titleEligible')) for v in vv),'captionPilotDocuments':sum(v['id'] in pilot for v in vv),'meanMinutes':float(np.mean(measured)) if measured else None,'medianMinutes':float(np.median(measured)) if measured else None,'missingDurations':len(vv)-len(measured)})
    missing=[{'measure':'Publishing account resolved','available':sum(v.get('channelId') is not None for v in vs),'total':len(vs)}, {'measure':'Positive upload duration','available':sum(v.get('durationSeconds') is not None and v['durationSeconds']>0 for v in vs),'total':len(vs)}, {'measure':'Exact upload date','available':sum(bool(v.get('date')) for v in vs),'total':len(vs)}, {'measure':'English-likely eligible title','available':sum(bool(v.get('titleEligible')) for v in vs),'total':len(vs)}, {'measure':'Frozen English caption pilot','available':len(pilot),'total':len(vs)}]
    for r in missing:r['unavailable']=r['total']-r['available'];r['availableShare']=r['available']/r['total']
    counts=np.array(sorted([r['uploads'] for r in channels if r['uploads']],reverse=True),dtype=float);attributed=int(counts.sum());shares=counts/attributed;n=len(counts)
    asc=np.sort(counts);gini=float((2*np.arange(1,n+1)-n-1)@asc/(n*asc.sum()));hhi=float(shares@shares)
    concentration={'accountGroupsWithUploads':n,'attributedUploads':attributed,'unattributedUploads':len(vs)-attributed,'gini':gini,'hhi':hhi,'effectiveEquallyRepresentedAccounts':1/hhi,'top1Share':float(shares[:1].sum()),'top5Share':float(shares[:5].sum()),'top10Share':float(shares[:10].sum()),'top20Share':float(shares[:20].sum()),'interpretation':'Concentration of indexed convenience-sample uploads by publishing-account group, not platform audience, practitioner prevalence or a complete channel crawl.'}
    rank=sorted([r for r in channels if r['uploads']],key=lambda r:(-r['uploads'],r['name']))
    cumulative=0
    for i,r in enumerate(rank):cumulative+=r['uploads'];r['rank']=i+1;r['cumulativeUploadShare']=cumulative/attributed
    matched_accounts={v['channelId'] for v in vs if v['id'] in pilot}
    selected=[v['durationSeconds']/60 for v in vs if v['id'] in pilot and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    rest=[v['durationSeconds']/60 for v in vs if v['id'] not in pilot and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    within_rest=[v['durationSeconds']/60 for v in vs if v['id'] not in pilot and v.get('channelId') in matched_accounts and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    selection={'captionPilotKnownDuration':summary(selected),'otherIndexedKnownDuration':summary(rest),'otherUploadsInPilotAccountsKnownDuration':summary(within_rest),'pilotAccounts':len(matched_accounts),'scope':'Empirical descriptive comparison. Caption selection was purposive; differences are not availability effects or population estimates.'}
    duration_rows=[]
    for label,lo,hi in BANDS:
        eligible=[v for v in vs if v.get('durationSeconds') is not None and v['durationSeconds']>0 and lo<=v['durationSeconds']<hi]
        duration_rows.append({'band':label,'uploads':len(eligible),'captionPilotDocuments':sum(v['id'] in pilot for v in eligible),'captionPilotShare':sum(v['id'] in pilot for v in eligible)/len(eligible) if eligible else None})
    keyword=[]; contrasts=[];topic_defs=d['topics']
    valid=[v for v in vs if v.get('titleEligible') and v.get('durationSeconds') is not None and v['durationSeconds']>0]
    for t in topic_defs:
        patt=re.compile(t['regex'],re.I)
        # Source JSON stores literal doubled slashes? Compile after verifying direct interpretation.
        if '\\\\b' in t['regex']:patt=re.compile(t['regex'].replace('\\\\','\\'),re.I)
        for band,lo,hi in BANDS:
            vv=[v for v in valid if lo<=v['durationSeconds']<hi];k=sum(bool(patt.search(v['title'])) for v in vv)
            keyword.append({'topicId':t['id'],'topic':t['label'],'band':band,'matches':k,'eligibleTitles':len(vv),'share':k/len(vv) if vv else None})
        short=[v for v in valid if v['durationSeconds']<1800];long=[v for v in valid if v['durationSeconds']>=1800]
        pooled=float(np.mean([bool(patt.search(v['title'])) for v in long])-np.mean([bool(patt.search(v['title'])) for v in short]))
        paired=[]
        for cid in sorted(by,key=lambda x:x or ''):
            if cid is None:continue
            vv=[v for v in valid if v.get('channelId')==cid];s=[v for v in vv if v['durationSeconds']<1800];l=[v for v in vv if v['durationSeconds']>=1800]
            if len(s)>=3 and len(l)>=3:paired.append(float(np.mean([bool(patt.search(v['title'])) for v in l])-np.mean([bool(patt.search(v['title'])) for v in s])))
        contrasts.append({'topicId':t['id'],'topic':t['label'],'shortTitles':len(short),'longTitles':len(long),'pooledLongMinusShortShare':pooled,'eligiblePairedAccounts':len(paired),'accountDifferenceSummary':summary(paired),'sameDirectionAsPairedMedian':bool(np.sign(pooled)==np.sign(np.median(paired))) if paired else None})
    duplicate=[];dup_stats={}
    for mode,mask in [('normalized',()),('nameAndGenreMasked',identity_words())]:
        families=collections.defaultdict(list)
        for v in vs:
            if v.get('titleEligible'):
                key=normalized(v['title'],mask)
                if key:families[key].append(v)
        repeats=[vv for vv in families.values() if len(vv)>1]
        dup_stats[mode]={'nonemptyEligibleTitleDocuments':sum(map(len,families.values())),'uniqueNormalizedStrings':len(families),'repeatedStringFamilies':len(repeats),'documentsInRepeatedFamilies':sum(map(len,repeats)),'crossPublisherRepeatedFamilies':sum(len({v.get('channelId') for v in vv})>1 for vv in repeats)}
        for vv in repeats:
            duplicate.append({'normalization':mode,'normalizedTitle':normalized(vv[0]['title'],mask),'documents':len(vv),'publishers':len({v.get('channelId') for v in vv}),'videoIds':'|'.join(v['id'] for v in vv)})
    capfile=ROOT/'dist/analysis/caption-embeddings.npz';titlefile=ROOT/'dist/analysis/title-embeddings.npz';ca=np.load(capfile);ta=np.load(titlefile)
    ci={str(v):i for i,v in enumerate(ca['video_ids'])};ti={str(v):i for i,v in enumerate(ta['video_ids'])};common=sorted(set(ci)&set(ti));vchan={v['id']:v['channelId'] for v in vs};rng=np.random.default_rng(42)
    cap,cp=pair_diagnostic(common,np.array([ca['vectors'][ci[v]] for v in common]),vchan,rng)
    tit,tp=pair_diagnostic(common,np.array([ta['vectors'][ti[v]] for v in common]),vchan,np.random.default_rng(42))
    allcap,apairs=pair_diagnostic(sorted(ci),np.array([ca['vectors'][ci[v]] for v in sorted(ci)]),vchan,np.random.default_rng(42))
    # A source-independent reconciliation catches accidental upload-order joins.
    old=d['diagnostics']['captionWithinBetween'];assert allcap['within']['n']==old['within']['nPairs'];assert abs(allcap['within']['median']-old['within']['median'])<1e-6
    for r in cp:r['representation']='caption'
    for r in tp:r['representation']='title'
    labels=[{'videoId':v,'publisherId':vchan[v],'publisher':lookup[vchan[v]]['name']} for v in common]
    result={'source':{'snapshot':'dist/analysis/data.json','sha256':PIN,'captionEmbeddingsSha256':digest(capfile),'titleEmbeddingsSha256':digest(titlefile),'protocolSha256':digest(HERE/'protocol.json'),'checkedAt':d['meta']['checkedAt'],'newRetrieval':False,'software':{'numpy':np.__version__}},'coverage':{'uploads':len(vs),'accountGroups':len(cs),'captionPilotDocuments':len(pilot),'missingness':missing},'channels':channels,'concentration':concentration,'publisherRanks':rank,'captionSelection':selection,'durationBands':duration_rows,'keywordByDuration':keyword,'keywordContrasts':contrasts,'duplicateTitles':{'method':'English-likely eligible titles; NFKD accent removal, casefold, Unicode word tokens, punctuation collapsed. Mask variant additionally removes the frozen baseline name-and-genre word list. Title families are not original-session families.','variants':dup_stats,'publishedEmbeddingDeduplication':d['diagnostics']['deduplicatedVsAllTitles'],'publishedMaskSensitivity':d['diagnostics']['rawVsMaskedTitles']},'embeddingWithinBetween':{'matchedCaption':cap,'matchedTitle':tit,'allCaption':allcap,'matchedItems':labels},'limitations':['Frozen convenience-sample upload index, not a comprehensive channel crawl or active-practitioner census.','The caption pilot is purposive; raw text and audio are unavailable for new speaker or accuracy validation.','Publisher, practitioner, claimed entity and original recording are distinct units.','Dictionary keyword indicators are overlapping unvalidated lexical detections; upload titles do not establish spoken content.','Upload duration bands are length strata, not manually verified performance-format labels.','Publisher-label permutation is descriptive; dependent cosine pairs do not provide independent inferential observations.','No question-answer agreement, truth or extraterrestrial provenance is inferred.']}
    result['source']['embeddingMethod']='Frozen all-MiniLM-L6-v2 384D derivative arrays from the published semantic_analysis.py pipeline. Titles and captions use the baseline name-and-genre semantic mask; caption documents use equal 240-wordpiece chunk pooling. No new inference or raw-text access.'
    result['embeddingWithinBetween']['crossLayerContrast']={'matchedDocuments':len(common),'matchedPublishers':len(set(vchan[v] for v in common)),'captionMinusTitlePooledMeanDifference':cap['meanDifference']-tit['meanDifference'],'captionMinusTitleAccountBalancedDifference':cap['accountBalanced']['meanDifference']-tit['accountBalanced']['meanDifference'],'meaning':'Difference of within-minus-between cosine separations in two different text representations on identical upload IDs; cosine scales are representation-specific, so this is a descriptive sensitivity, not a calibrated semantic effect.'}
    result['hypothesisOutcomes']=[{'id':'E1','result':'pilot_median_larger' if selection['captionPilotKnownDuration']['median']>selection['otherIndexedKnownDuration']['median'] else 'pilot_median_not_larger','status':'descriptive_executed'},{'id':'E2','result':'top10_exceeds_half' if concentration['top10Share']>.5 else 'top10_does_not_exceed_half','status':'descriptive_executed'},{'id':'E3','result':f"{sum(r['sameDirectionAsPairedMedian'] for r in contrasts)} of {len(contrasts)} pooled directions match paired-account median directions; zeros count only when both zero",'status':'descriptive_executed'},{'id':'E4','result':'matched_caption_difference_above_reference_median' if cap['meanDifference']>cap['permutationReference']['median'] else 'matched_caption_difference_not_above_reference_median','status':'negative_control_executed'},{'id':'E5','result':'repeated_title_strings_present' if dup_stats['normalized']['repeatedStringFamilies'] else 'no_repeated_title_strings','status':'descriptive_executed'}]
    save(dest/'results.json',result);table(gen/'publisher-coverage.csv',channels);table(gen/'publisher-concentration.csv',rank);table(gen/'missingness.csv',missing);table(gen/'duration-bands.csv',duration_rows);table(gen/'keyword-duration.csv',keyword);table(gen/'repeated-titles.csv',duplicate);table(gen/'matched-embedding-pairs.csv',cp+tp);table(gen/'matched-items.csv',labels)
    save(gen/'figure-inputs.json',{'missingness':missing,'publisherRanks':rank,'captionSelection':selection,'durationBands':duration_rows,'keywordByDuration':keyword,'embedding':{'caption':cap,'title':tit}})
    print(json.dumps({'uploads':len(vs),'pilot':len(pilot),'top10Share':concentration['top10Share'],'matchedDocuments':len(common),'matchedCaptionDifference':cap['meanDifference'],'matchedTitleDifference':tit['meanDifference']}))

if __name__=='__main__':main()
