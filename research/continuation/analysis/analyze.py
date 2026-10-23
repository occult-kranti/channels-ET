#!/usr/bin/env python3
"""Source-aware continuation diagnostics; no retrieval, model training or truth labels."""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, pathlib, re
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import rankdata, spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
def stats(x):
    a=np.asarray(x,dtype=float)
    return {'n':len(a),'mean':float(a.mean()) if len(a) else None,'median':float(np.median(a)) if len(a) else None,'q1':float(np.percentile(a,25)) if len(a) else None,'q3':float(np.percentile(a,75)) if len(a) else None,'min':float(a.min()) if len(a) else None,'max':float(a.max()) if len(a) else None}
def corr(a,b):return float(spearmanr(a,b).statistic) if len(a)>2 and len(set(a))>1 and len(set(b))>1 else None
def normq(s):return ' '.join(re.findall('[a-z0-9]+',s.casefold()))
def table(p,rows):
    if not rows:return
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def union_groups(videoids,edges):
    parent={v:v for v in videoids}
    def find(v):
        while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
        return v
    for a,b in sorted(edges):
        ra,rb=find(a),find(b)
        if ra!=rb:parent[max(ra,rb)]=min(ra,rb)
    families=collections.defaultdict(list)
    for v in sorted(videoids):families[find(v)].append(v)
    return [{'groupId':'src-'+hashlib.sha256('|'.join(vs).encode()).hexdigest()[:12],'videoIds':vs,'uploadCount':len(vs)} for _,vs in sorted(families.items())]
def partial_rank(a,b,controls):
    A=rankdata(a);B=rankdata(b);Z=np.column_stack([np.ones(len(a))]+[rankdata(x) for x in controls]);ar=A-Z@np.linalg.lstsq(Z,A,rcond=None)[0];br=B-Z@np.linalg.lstsq(Z,B,rcond=None)[0]
    return float(np.corrcoef(ar,br)[0,1])
def common_support(pairs):
    edges=[.4,.5,.6,.7,.8,.9,1.000001];bins=[];selected=[]
    for lo,hi in zip(edges,edges[1:]):
        inside=[p for p in pairs if lo<=p['questionCosine']<hi];within=[p for p in inside if p['sameQuarantineGroup']];cross=[p for p in inside if not p['sameQuarantineGroup']];common=bool(within and cross)
        row={'label':f'{lo:.2f}–<{hi:.2f}' if hi<1 else f'{lo:.2f}–1.00','lowerInclusive':lo,'upperExclusive':hi,'withinPairs':len(within),'crossPairs':len(cross),'withinMeanQuestionCosine':float(np.mean([p['questionCosine'] for p in within])) if within else None,'crossMeanQuestionCosine':float(np.mean([p['questionCosine'] for p in cross])) if cross else None,'withinMeanAnswerCosine':float(np.mean([p['answerCosine'] for p in within])) if within else None,'crossMeanAnswerCosine':float(np.mean([p['answerCosine'] for p in cross])) if cross else None,'commonSupport':common,'standardizationWeight':None}
        bins.append(row)
        if common:selected+=inside
    total=len(selected);included=[r for r in bins if r['commonSupport']]
    for row in included:row['standardizationWeight']=(row['withinPairs']+row['crossPairs'])/total
    wi=[p for p in pairs if p['sameQuarantineGroup']];cr=[p for p in pairs if not p['sameQuarantineGroup']];swi=[p for p in selected if p['sameQuarantineGroup']];scr=[p for p in selected if not p['sameQuarantineGroup']]
    sw=sum(row['standardizationWeight']*row['withinMeanAnswerCosine'] for row in included);sc=sum(row['standardizationWeight']*row['crossMeanAnswerCosine'] for row in included)
    return {'bins':bins,'commonSupportBins':len(included),'includedNeighborPairs':total,'excludedNeighborPairs':len(pairs)-total,'withinIncludedPairs':len(swi),'crossIncludedPairs':len(scr),'originalWithinAnswerCosine':stats([p['answerCosine'] for p in wi]),'originalCrossAnswerCosine':stats([p['answerCosine'] for p in cr]),'unweightedSharedSupportWithinMean':float(np.mean([p['answerCosine'] for p in swi])),'unweightedSharedSupportCrossMean':float(np.mean([p['answerCosine'] for p in scr])),'standardizedWithinMean':sw,'standardizedCrossMean':sc,'standardizedWithinMinusCross':sw-sc,'positiveAdvantageDisconfirmed':sw<=sc,'weightDefinition':'Within the bins containing both quarantine strata, weight each bin by its pooled neighbor-pair count, then apply the identical weights to the separate group means.','limitations':['Quarantine is constructed from question similarity; unsupported high-similarity bins cannot identify a cross-quarantine comparison.','The retained common-support pool differs from all127neighbors. Standardization does not replace the original all-neighbor/cross-group descriptive summaries.','Coarse bins leave within-bin question-similarity, length, topic and source selection differences. No causal session-reuse or answer-agreement claim follows.','Neighbor pairs share candidates/uploads; no independent-pair confidence interval or inferential p-value is reported.']}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,default=HERE);args=ap.parse_args();out=args.output;gen=out/'generated';gen.mkdir(parents=True,exist_ok=True)
    qpath=ROOT/'research/expansion/qa/qa-candidates.json';qdoc=json.loads(qpath.read_text());rows=qdoc['records'];dpath=ROOT/'dist/analysis/data.json';d=json.loads(dpath.read_text());videos={v['id']:v for v in d['videos']};assert len(rows)==949 and len(videos)==925
    Q=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform([r['question'] for r in rows]);A=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform([r['answerGist'] for r in rows]);QM=(Q@Q.T).toarray();AM=(A@A.T).toarray();ii,jj=np.triu_indices(len(rows),1);cross=np.array([rows[i]['videoId']!=rows[j]['videoId'] for i,j in zip(ii,jj)]);ii,jj=ii[cross],jj[cross];q=QM[ii,jj];a=AM[ii,jj];vids=sorted({r['videoId'] for r in rows});vididx={v:i for i,v in enumerate(vids)};vi=np.array([vididx[r['videoId']] for r in rows]);codes=np.minimum(vi[ii],vi[jj])*len(vids)+np.maximum(vi[ii],vi[jj]);cnt=np.bincount(codes);qs=np.bincount(codes,weights=q);ans=np.bincount(codes,weights=a);bins=np.flatnonzero(cnt);uploadpairs=[{'leftVideoId':vids[c//len(vids)],'rightVideoId':vids[c%len(vids)],'candidatePairs':int(cnt[c]),'meanQuestionCosine':float(qs[c]/cnt[c]),'meanAnswerCosine':float(ans[c]/cnt[c])} for c in bins]
    high=q>=.4;sourcepairs=collections.defaultdict(list);threshold_rows=[];components=[]
    for threshold in [.4,.5,.6,.7,.8,.9]:
        mask=q>=threshold;si,sj=ii[mask],jj[mask];matrix=coo_matrix((np.ones(len(si)),(si,sj)),shape=(len(rows),len(rows)));ncomp,lab=connected_components(matrix,directed=False);sizes=np.bincount(lab);nonempty=[k for k,s in enumerate(sizes) if s>1]
        threshold_rows.append({'minimumQuestionCosine':threshold,'edges':int(mask.sum()),'connectedComponents':int(ncomp),'nonSingletonComponents':len(nonempty),'linkedCandidates':int(sum(sizes[k] for k in nonempty)),'largestComponentCandidates':int(sizes.max()),'isolatedCandidates':int(np.sum(sizes==1))})
        if threshold==.4:
            for k in nonempty:
                idx=np.flatnonzero(lab==k);vv=sorted({rows[i]['videoId'] for i in idx});components.append({'componentId':'lex-'+str(k),'candidates':len(idx),'uploadCount':len(vv),'videoIds':vv,'candidateIds':[rows[i]['id'] for i in idx]})
    for i,j,qc,ac in zip(ii[high],jj[high],q[high],a[high]):sourcepairs[tuple(sorted([rows[i]['videoId'],rows[j]['videoId']]))].append({'leftId':rows[i]['id'],'rightId':rows[j]['id'],'questionCosine':float(qc),'answerCosine':float(ac),'exactQuestion':normq(rows[i]['question'])==normq(rows[j]['question'])})
    sensitivity=[];allfamilies={}
    for threshold in [.7,.8,.9]:
        edges=[key for key,rs in sourcepairs.items() if sum(r['questionCosine']>=threshold for r in rs)>=2];groups=union_groups(vids,edges);allfamilies[str(threshold)]=groups;sensitivity.append({'minimumQuestionCosine':threshold,'requiredQuestionPairLinks':2,'uploadLinks':len(edges),'sourceGroups':len(groups),'multiUploadGroups':sum(r['uploadCount']>1 for r in groups),'largestGroupUploads':max(r['uploadCount'] for r in groups),'uploadsInMultiUploadGroups':sum(r['uploadCount'] for r in groups if r['uploadCount']>1)})
    # Independently specified benchmark guard: more conservative than the two-link study sensitivity.
    guarded_edges=[key for key,rs in sourcepairs.items() if any(r['exactQuestion'] or r['questionCosine']>=.8 for r in rs) or len(rs)>=3];guard=union_groups(vids,guarded_edges);guardmap={v:g['groupId'] for g in guard for v in g['videoIds']}
    unrelated=np.array([guardmap[rows[i]['videoId']]!=guardmap[rows[j]['videoId']] for i,j in zip(ii,jj)]);sameq=np.array([normq(rows[i]['question'])==normq(rows[j]['question']) for i,j in zip(ii,jj)])
    rng=np.random.default_rng(42);reference=[float(a[rng.choice(len(a),size=int(high.sum()),replace=False)].mean()) for _ in range(1000)]
    selected_pairs=[{'leftId':rows[i]['id'],'rightId':rows[j]['id'],'leftVideoId':rows[i]['videoId'],'rightVideoId':rows[j]['videoId'],'questionCosine':float(qc),'answerCosine':float(ac),'sameQuarantineGroup':guardmap[rows[i]['videoId']]==guardmap[rows[j]['videoId']],'sameNormalizedQuestion':normq(rows[i]['question'])==normq(rows[j]['question'])} for i,j,qc,ac in zip(ii[high],jj[high],q[high],a[high])]
    # Retain a seeded source-addressable plot subset; all-neighbor and upload-pair aggregates remain complete.
    sampled=rng.choice(len(a),size=min(4000,len(a)),replace=False);plotpairs=[{'leftId':rows[ii[k]]['id'],'rightId':rows[jj[k]]['id'],'questionCosine':float(q[k]),'answerCosine':float(a[k]),'stratum':'seeded_cross_upload_reference'} for k in sampled]+[dict(p,stratum='question_neighbor') for p in selected_pairs]
    alignment={'candidates':len(rows),'qaUploads':len(vids),'allDistinctUploadCandidatePairs':len(a),'questionNeighborThreshold':.4,'questionNeighborPairs':int(high.sum()),'allPairRankCorrelation':corr(q,a),'uploadPairBalancedRankCorrelation':corr([p['meanQuestionCosine'] for p in uploadpairs],[p['meanAnswerCosine'] for p in uploadpairs]),'neighborAnswerCosine':stats(a[high]),'allCrossUploadAnswerCosine':stats(a),'exactQuestionPairs':int(sameq.sum()),'exactQuestionAnswerCosine':stats(a[sameq]),'crossQuarantineNeighborPairs':int(np.sum(high&unrelated)),'crossQuarantineNeighborAnswerCosine':stats(a[high&unrelated]),'crossQuarantinePairRankCorrelation':corr(q[unrelated],a[unrelated]),'sizeMatchedRandomReference':{'draws':1000,'seed':42,'statistic':'Mean answer-gist cosine in127uniformly sampled distinct-upload candidate pairs; count-matched descriptive baseline, not a calibrated null.','summary':stats(reference),'observedAboveReferenceFraction':float(np.mean(np.array(reference)<a[high].mean()))}}
    cap=np.load(ROOT/'dist/analysis/caption-embeddings.npz');title=np.load(ROOT/'dist/analysis/title-embeddings.npz');ci={str(v):j for j,v in enumerate(cap['video_ids'])};ti={str(v):j for j,v in enumerate(title['video_ids'])};common=sorted(set(ci)&set(ti));C=cosine_similarity(np.array([cap['vectors'][ci[v]] for v in common]));T=cosine_similarity(np.array([title['vectors'][ti[v]] for v in common]));words={r['videoId']:r['wordCount'] for r in d['transcripts']['rows']};nrows=[]
    for i in range(len(common)):
        for j in range(i+1,len(common)):
            av,bv=videos[common[i]],videos[common[j]];ad,bd=av['durationSeconds'],bv['durationSeconds'];assert ad>0 and bd>0;nrows.append({'leftVideoId':common[i],'rightVideoId':common[j],'leftPublisher':av['channelId'],'rightPublisher':bv['channelId'],'samePublisher':av['channelId']==bv['channelId'],'titleCosine':float(T[i,j]),'captionCosine':float(C[i,j]),'absoluteLogDurationRatio':abs(float(np.log(ad/bd))),'meanLogDuration':float((np.log(ad/60)+np.log(bd/60))/2),'absoluteLogCaptionWordRatio':abs(float(np.log(words[common[i]]/words[common[j]])))})
    fields=['titleCosine','captionCosine','absoluteLogDurationRatio','absoluteLogCaptionWordRatio','meanLogDuration'];arrays={f:np.array([r[f] for r in nrows]) for f in fields};controls=[arrays[f] for f in fields[2:]];R=np.column_stack([np.ones(len(nrows))]+controls);same=np.array([r['samePublisher'] for r in nrows]);seps={}
    rankZ=np.column_stack([np.ones(len(nrows))]+[rankdata(x) for x in controls])
    for f in ['titleCosine','captionCosine']:
        ranked=rankdata(arrays[f]);res=ranked-rankZ@np.linalg.lstsq(rankZ,ranked,rcond=None)[0]
        for row,value in zip(nrows,res):row[f.replace('Cosine','RankResidual')]=float(value)
    for name in ['titleCosine','captionCosine']:
        raw=arrays[name];res=raw-R@np.linalg.lstsq(R,raw,rcond=None)[0];seps[name]={'rawMeanWithinMinusBetween':float(raw[same].mean()-raw[~same].mean()),'nuisanceResidualMeanWithinMinusBetween':float(res[same].mean()-res[~same].mean()),'method':'OLS projection on intercept, absolute log duration ratio, mean log duration in minutes, and absolute log caption word-count ratio; within-minus-between means of residual cosine. Descriptive conditioning, not a causal or speaker effect.'}
    lopo=[]
    for pub in sorted({videos[v]['channelId'] for v in common}):
        keep=np.array([r['leftPublisher']!=pub and r['rightPublisher']!=pub for r in nrows]);lopo.append({'omittedPublisher':pub,'retainedPairs':int(keep.sum()),'partialRankCorrelation':partial_rank(arrays['titleCosine'][keep],arrays['captionCosine'][keep],[x[keep] for x in controls])})
    nuisance={'matchedDocuments':len(common),'publishers':len({videos[v]['channelId'] for v in common}),'pairs':len(nrows),'withinPairs':int(same.sum()),'betweenPairs':int((~same).sum()),'rawTitleCaptionRankCorrelation':corr(arrays['titleCosine'],arrays['captionCosine']),'partialRankCorrelation':partial_rank(arrays['titleCosine'],arrays['captionCosine'],controls),'partialRankDefinition':'Pearson correlation of title and caption rank residuals after separate OLS projection on intercept and ranked nuisance variables. No p-value or independent-pair uncertainty interval.','controls':fields[2:],'rankCorrelationMatrix':[[corr(arrays[f],arrays[g]) for g in fields] for f in fields],'matrixFields':fields,'publisherSeparations':seps,'leaveOnePublisherOut':{'summary':stats([p['partialRankCorrelation'] for p in lopo]),'rows':lopo,'meaning':'Deterministic influence range, not a confidence interval.'},'pairRows':nrows}
    source={'metadataSha256':sha(dpath),'qaCandidatesSha256':sha(qpath),'captionEmbeddingsSha256':sha(ROOT/'dist/analysis/caption-embeddings.npz'),'titleEmbeddingsSha256':sha(ROOT/'dist/analysis/title-embeddings.npz'),'protocolSha256':sha(HERE/'protocol.json'),'newRetrieval':False,'newEncoderInference':False,'versions':{'numpy':np.__version__,'scipy':__import__('scipy').__version__,'scikitLearn':__import__('sklearn').__version__}}
    alignment['commonSupportStandardization']=common_support(selected_pairs)
    table(gen/'question-cosine-common-support.csv',alignment['commonSupportStandardization']['bins'])
    result={'source':source,'coverage':{'uploads':len(videos),'qaCandidates':len(rows),'qaUploads':len(vids),'practitionerContexts':1,'captionDocuments':len(ci),'matchedCaptionTitleDocuments':len(common)},'questionAnswerAlignment':alignment,'lexicalGraph':{'thresholdRows':threshold_rows,'componentsAt040':sorted(components,key=lambda r:-r['candidates']),'sourceFamilySensitivity':sensitivity,'benchmarkGuard':{'rule':'Link uploads if any exactly normalized question repeats, any question cosine>=0.80, OR at least three cross-upload question pairs cosine>=0.40. Connected components are conservative quarantine groups, not proven original-session families.','sourceGroups':len(guard),'uploadLinks':len(guarded_edges),'multiUploadGroups':sum(g['uploadCount']>1 for g in guard),'largestGroupUploads':max(g['uploadCount'] for g in guard),'groups':guard}},'representationNuisance':nuisance,'benchmarkAudit':{'status':'awaiting_executed_model_outputs','claim':'No benchmark result is imputed from package installation or planned arms.'},'limitations':['AI digest questions and answer gists are a one-practitioner paraphrase source, not literal turns or independently verified answers.','Pair scores share questions, uploads and publishers; numerical association is descriptive, not independent human evidence.','Question lexical components and quarantine links do not establish semantic equivalence or repeated original sessions.','The count-matched random reference does not match publisher, format or word-length distributions and is not a calibrated null.','Partial ranks and residual cosine condition on observed length variables only; they do not establish causal mediation or isolate speaker identity.','Frozen caption/title vectors use the historical masked MiniLM representations; no new encoder was executed.']}

    audit=HERE/'benchmark-audit.json'
    if audit.exists():
        result['benchmarkAudit']=json.loads(audit.read_text())
        result['source']['newLanguageModelInference']=result['benchmarkAudit'].get('executionStatus')=='completed'
        for filename,expected in result['benchmarkAudit']['inputs'].items():
            assert sha(ROOT/'research/continuation/models'/filename)==expected, 'Model audit must be refreshed after '+filename+' changes'
    diagnostics=HERE/'model-diagnostics-audit.json'
    if diagnostics.exists():
        result['modelDiagnosticsAudit']=json.loads(diagnostics.read_text())
        for filename,expected in result['modelDiagnosticsAudit']['inputs'].items():
            assert sha(ROOT/'research/continuation/models'/filename)==expected, 'Model diagnostic audit must be refreshed after '+filename+' changes'
    prompt_audit=HERE/'prompt-sensitivity-audit.json'
    if prompt_audit.exists():
        result['promptSensitivityAudit']=json.loads(prompt_audit.read_text())
        for filename,expected in result['promptSensitivityAudit']['inputs'].items():
            assert sha(ROOT/'research/continuation/models'/filename)==expected, 'Prompt sensitivity audit must be refreshed after '+filename+' changes'
    save(out/'results.json',result);save(gen/'question-neighbor-pairs.json',selected_pairs);save(gen/'question-answer-plot-pairs.json',plotpairs);save(gen/'upload-pair-mean-cosines.json',uploadpairs);save(gen/'source-family-map.json',{'method':result['lexicalGraph']['benchmarkGuard']['rule'],'sourceSha256':source['qaCandidatesSha256'],'records':[{'videoId':v,'sourceGroupId':guardmap[v]} for v in vids],'groups':guard});save(gen/'strict-source-family-sensitivity.json',allfamilies);table(gen/'question-neighbor-pairs.csv',selected_pairs);table(gen/'upload-pair-mean-cosines.csv',uploadpairs);table(gen/'matched-representation-pairs.csv',nrows);table(gen/'lexical-graph-thresholds.csv',threshold_rows);table(gen/'strict-source-family-sensitivity.csv',sensitivity);table(gen/'source-family-map.csv',[{'videoId':v,'sourceGroupId':guardmap[v]} for v in vids]);print(json.dumps({'alignment':alignment,'nuisance':{k:v for k,v in nuisance.items() if k not in ['pairRows','rankCorrelationMatrix','leaveOnePublisherOut']},'guardGroups':len(guard),'lexicalGraph':threshold_rows}))
if __name__=='__main__':main()
