#!/usr/bin/env python3
"""Derive paper diagnostics from the frozen published pilot without changing it."""
import csv,hashlib,json,pathlib,math,argparse,sys,os
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
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--chunk-weighting',action='store_true')
 parser.add_argument('--model-dir',type=pathlib.Path)
 parser.add_argument('--corpus-file',type=pathlib.Path)
 args=parser.parse_args()
 if args.chunk_weighting and not (args.model_dir and args.corpus_file):parser.error('--chunk-weighting requires --model-dir and --corpus-file')
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
 coverage={'indexedVideos':d['coverage']['videoCount'],'watchMetadataSuccesses':sum(r.get('status')=='success' for r in json.loads((ROOT/'research/analysis/inputs/fresh_metadata.json').read_text())),'durationKnown':d['coverage']['durationCount'],'durationFresh':d['coverage']['freshDurationCount'],'durationInherited':d['coverage']['inheritedDurationCount'],'dateKnown':d['coverage']['dateCount'],'attributedVideos':d['coverage']['attributedVideoCount'],'routeGroups':d['coverage']['channelCount'],'groupsWithVideos':d['coverage']['channelGroupsWithVideos'],'groupsWithDurations':d['coverage']['channelGroupsWithDurations'],'englishLikelyTitles':d['coverage']['titleCount'],'embeddedTitles':d['coverage']['embeddedTitleCount'],'titleGroupsMinFive':len(d['semanticSimilarity']['channelIds']),'captionAttempted':d['transcripts']['attempted'],'captionAvailable':d['transcripts']['available'],'captionEnglish':caption_english,'captionPilot':len(rows),'captionPublishers':len({r['channelId'] for r in rows}),'captionComparisonPublishers':len(d['transcripts']['similarity']['channelIds']),'captionComparisonDocuments':sum(r['channelId'] in d['transcripts']['similarity']['channelIds'] for r in rows),'matchedEligibleDocuments':len(eligible_matched),'matchedContributingDocuments':len(contributing),'matchedPublishers':len(a['channelIds']),'matchedPairs':matched['nPairs']}
 diag=d['diagnostics'];sens=[{'comparison':'Raw vs name-and-genre-masked titles','cohort':'Title publishers','publishers':len(d['semanticSimilarity']['channelIds']),'pairs':diag['rawVsMaskedTitles']['pairCount'],'rho':diag['rawVsMaskedTitles']['spearmanRankCorrelation']},{'comparison':'All vs deduplicated titles','cohort':'Title publishers','publishers':len(d['semanticSimilarity']['channelIds']),'pairs':diag['deduplicatedVsAllTitles']['pairCount'],'rho':diag['deduplicatedVsAllTitles']['spearmanRankCorrelation']},{'comparison':'Full vs positionally trimmed captions','cohort':'Caption publishers','publishers':len(d['transcripts']['similarity']['channelIds']),'pairs':diag['captionFullVsTrimmed']['pairCount'],'rho':diag['captionFullVsTrimmed']['spearmanRankCorrelation']},{'comparison':'Matched titles vs matched captions','cohort':'Matched publishers','publishers':len(a['channelIds']),'pairs':matched['nPairs'],'rho':matched['rho']}]
 # Quantify nearest-neighbor changes, separate from rank correlation.
 def nearest(s):
  M=np.array(s['matrix']);np.fill_diagonal(M,-np.inf);return {i:s['channelIds'][int(np.argmax(M[j]))] for j,i in enumerate(s['channelIds'])}
 nn1,nn2=nearest(d['transcripts']['similarity']),nearest(d['transcripts']['trimmedSimilarity']);neighbor_changes=sum(nn1[k]!=nn2[k] for k in nn1)
 out={'source':{'path':'dist/analysis/data.json','sha256':h,'checkedAt':d['meta']['checkedAt'],'phase':'paper-round4','software':{'numpy':np.__version__}},'coverage':coverage,'focalDurations':focal,'sensitivity':sens,'matched':matched,'leaveOnePublisherOut':{'method':'For each publisher, remove every channel-pair comparison containing that publisher, then recompute Spearman rank correlation across retained off-diagonal cosine pairs. No resampling; no independence assumption or inferential interval.','rangeMeaning':'Minimum and maximum across these deterministic omissions; descriptive sensitivity range, not a confidence interval.','minRho':min(x['rho'] for x in lopo),'maxRho':max(x['rho'] for x in lopo),'rows':lopo},'captionLengths':{'unit':"Tokens matching [A-Za-z]+(?:'[A-Za-z]+)?; contractions count once",'n':len(lengths),'sum':int(lengths.sum()),'mean':float(lengths.mean()),'median':float(np.median(lengths)),'q1':float(np.percentile(lengths,25)),'q3':float(np.percentile(lengths,75)),'min':int(lengths.min()),'max':int(lengths.max()),'longest':{'videoId':longest['videoId'],'publisher':channels[longest['channelId']]['name'],'words':longest['wordCount']},'shortest':{'videoId':shortest['videoId'],'publisher':channels[shortest['channelId']]['name'],'words':shortest['wordCount']},'rows':[{'videoId':r['videoId'],'channelId':r['channelId'],'publisher':channels[r['channelId']]['name'],'words':r['wordCount'],'automaticCaptions':r['automaticCaptions']} for r in rows]},'captionTrimNearestNeighborChanges':{'changed':neighbor_changes,'eligiblePublishers':len(nn1)},'withinBetween':{k:{kk:vv for kk,vv in v.items() if kk!='values'} for k,v in diag['captionWithinBetween'].items() if isinstance(v,dict)},'limitations':['Purposive, incomplete upload samples. No channel-population mean, census or posting rate is estimated.','Uploader accounts and human practitioners are distinct. Route groups can include unresolved aliases.','The 55 pairwise observations share 11 publishers and are not independent; no p-values or confidence intervals are reported.','Twenty-five videos have eligible matched text; only 22 in publishers with at least two videos support the matched channel-matrix comparison.','Language detection and caption-track language labels are not manual content verification.','Equal chunk pooling overweights a short final chunk relative to token weighting; this is a method sensitivity candidate, not a reason to infer an ontological source.']}
 if args.chunk_weighting:
  out['chunkWeighting']=chunk_weighting(d,args.model_dir,args.corpus_file)
 elif (OUT/'chunk-weighting.json').exists():
  out['chunkWeighting']=json.loads((OUT/'chunk-weighting.json').read_text())
 if 'chunkWeighting' in out:
  assert out['chunkWeighting']['sourceSnapshotSha256']==h,'Cached pooling sensitivity uses a different source snapshot'
  out['source']['phase']='paper-round5'
  out['limitations'][-1]='The chunk-weighting diagnostic changes only the relative contribution of a short final chunk. It supplies no human-judgment validation and does not isolate speaker composition.'
 dump(OUT/'paper-results.json',out)
 writecsv(OUT/'leave-one-publisher-out.csv',lopo,['omittedChannelId','omittedPublisher','retainedPublishers','retainedPairs','rho'])
 writecsv(OUT/'matched-pair-cosines.csv',matched['pairs'],['a','b','titleCosine','captionCosine'])
 writecsv(OUT/'caption-lengths.csv',out['captionLengths']['rows'],['videoId','channelId','publisher','words','automaticCaptions'])
 writecsv(OUT/'focal-durations.csv',focal,['id','name','url','videoCount','durationCount','meanMinutes','medianMinutes','q1Minutes','q3Minutes','longFormatShare'])
 print(json.dumps({'coverage':coverage,'matchedRho':matched['rho'],'lopoRange':[out['leaveOnePublisherOut']['minRho'],out['leaveOnePublisherOut']['maxRho']],'captionLengths':{k:v for k,v in out['captionLengths'].items() if k not in ['rows','unit']}}))
def chunk_weighting(d,model_dir,corpus_file):
 """Compare content-token-weighted chunks to the published equal-chunk baseline."""
 from sklearn.preprocessing import normalize
 from sklearn.metrics.pairwise import cosine_similarity
 vendor=os.environ.get('CHANNELING_ANALYSIS_VENDOR')
 if vendor:sys.path.append(vendor)
 import onnxruntime as ort
 from tokenizers import Tokenizer
 sys.path.insert(0,str(ROOT/'research/analysis'))
 from build_analysis import IDENTITY
 from semantic_analysis import semantic_mask
 manifest=json.loads((model_dir/'manifest.json').read_text())
 expected=json.loads((ROOT/'research/analysis/inputs/model_manifest.json').read_text())
 assert manifest==expected,'Model manifest differs from phase1'
 for f in manifest['files']:
  assert hashlib.sha256((model_dir/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
 corpus=json.loads(corpus_file.read_text());sources={r['video_id']:r for r in corpus['records']};rows=d['transcripts']['rows']
 tok=Tokenizer.from_file(str(model_dir/'tokenizer.json'));tok.no_truncation();tok.no_padding()
 opt=ort.SessionOptions();opt.intra_op_num_threads=2;opt.inter_op_num_threads=1
 sess=ort.InferenceSession(str(model_dir/'onnx/model.onnx'),sess_options=opt,providers=['CPUExecutionProvider'])
 input_names={x.name for x in sess.get_inputs()};sequences=[];owners=[];sizes=[];per_doc=[]
 for j,r in enumerate(rows):
  text=sources[r['videoId']]['text'];assert hashlib.sha256(text.encode()).hexdigest()==r['textSha256']
  ids=tok.encode(semantic_mask(text,IDENTITY),add_special_tokens=False).ids
  chunks=[ids[i:i+240] for i in range(0,len(ids),240)]
  assert chunks
  chunk_sizes=[len(c) for c in chunks]
  per_doc.append({'videoId':r['videoId'],'channelId':r['channelId'],'wordCount':r['wordCount'],'contentWordpieces':len(ids),'chunks':len(chunks),'chunkSizes':chunk_sizes,'tailContentWordpieces':chunk_sizes[-1],'tailEqualWeight':1/len(chunks),'tailTokenWeight':chunk_sizes[-1]/len(ids)})
  for c in chunks:sequences.append([101]+c+[102]);owners.append(j);sizes.append(len(c))
 vectors={j:[] for j in range(len(rows))};weights={j:[] for j in range(len(rows))}
 for start in range(0,len(sequences),16):
  batch=sequences[start:start+16];width=max(map(len,batch));ids=np.zeros((len(batch),width),dtype=np.int64);mask=np.zeros_like(ids)
  for j,seq in enumerate(batch):ids[j,:len(seq)]=seq;mask[j,:len(seq)]=1
  feed={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)};output=sess.run(None,{k:v for k,v in feed.items() if k in input_names})[0]
  pooled=normalize((output*mask[:,:,None]).sum(axis=1)/mask.sum(axis=1)[:,None])
  for owner,size,vec in zip(owners[start:start+16],sizes[start:start+16],pooled):vectors[owner].append(vec);weights[owner].append(size)
 equal=np.vstack([normalize(np.mean(vectors[j],axis=0,keepdims=True))[0] for j in range(len(rows))])
 weighted=np.vstack([normalize(np.average(np.array(vectors[j]),axis=0,weights=weights[j])[None,:])[0] for j in range(len(rows))])
 baseline=np.load(ROOT/'dist/analysis/caption-embeddings.npz');mapping={v:i for i,v in enumerate(baseline['video_ids'])}
 retained=np.vstack([baseline['vectors'][mapping[r['videoId']]] for r in rows]);max_delta=float(np.max(np.abs(equal-retained)))
 assert max_delta<1e-6,f'Equal-chunk replay differs: {max_delta}'
 selected=d['transcripts']['similarity']['channelIds'];by={c:[j for j,r in enumerate(rows) if r['channelId']==c] for c in selected}
 wc=normalize(np.vstack([weighted[by[c]].mean(axis=0) for c in selected]));W=cosine_similarity(wc);B=np.array(d['transcripts']['similarity']['matrix']);newpairs=[];oldvalues=[];newvalues=[]
 for i,a in enumerate(selected):
  for j in range(i+1,len(selected)):
   b=selected[j];old=float(B[i,j]);new=round(float(W[i,j]),6);oldvalues.append(old);newvalues.append(new);newpairs.append({'a':a,'b':b,'equalChunkCosine':old,'tokenWeightedCosine':new,'delta':new-old})
 bdiag=B.copy();wdiag=W.copy();np.fill_diagonal(bdiag,-np.inf);np.fill_diagonal(wdiag,-np.inf);nearest=[]
 names={c['id']:c['name'] for c in d['channels']}
 for i,c in enumerate(selected):
  old=selected[int(np.argmax(bdiag[i]))];new=selected[int(np.argmax(wdiag[i]))];nearest.append({'channelId':c,'publisher':names[c],'equalChunkNeighbor':old,'tokenWeightedNeighbor':new,'changed':old!=new})
 out={'sourceSnapshotSha256':PINNED,'localCaptionCorpusSha256':hashlib.sha256(corpus_file.read_bytes()).hexdigest(),'modelRevision':manifest['revision'],'model':'sentence-transformers/all-MiniLM-L6-v2','method':'Same masked English caption text, tokenizer, 240-content-wordpiece chunks, token-level attention-mask mean pooling and chunk L2 normalization. Alternative video vector weights each chunk by its number of content wordpieces, excluding CLS/SEP; publisher vectors still weight videos equally. No new retrieval, training, translation or speaker segmentation.','equalChunkReplayMaxAbsoluteCoordinateDelta':max_delta,'documents':len(rows),'publishersCompared':len(selected),'pairsCompared':len(newpairs),'totalContentWordpieces':sum(x['contentWordpieces'] for x in per_doc),'totalChunks':len(sequences),'singleChunkDocuments':sum(x['chunks']==1 for x in per_doc),'minChunks':min(x['chunks'] for x in per_doc),'maxChunks':max(x['chunks'] for x in per_doc),'rankCorrelation':float(spearmanr(oldvalues,newvalues).statistic),'meanAbsoluteCosineChange':float(np.mean(np.abs(np.array(newvalues)-oldvalues))),'maxAbsoluteCosineChange':float(np.max(np.abs(np.array(newvalues)-oldvalues))),'nearestNeighborChanges':sum(x['changed'] for x in nearest),'nearestNeighbors':nearest,'documentsDetail':per_doc,'pairs':newpairs,'channelIds':selected,'matrix':np.round(W,6).tolist(),'interpretation':'This isolates one pooling choice on the same selected documents. Agreement is a sensitivity result, not validation against truth, human topic judgments or a representative population.'}
 dump(OUT/'chunk-weighting.json',out)
 np.savez_compressed(OUT/'chunk-weighted-embeddings.npz',video_ids=np.array([r['videoId'] for r in rows]),equal_chunk_vectors=equal.astype('float32'),token_weighted_vectors=weighted.astype('float32'))
 writecsv(OUT/'chunk-weighting-pairs.csv',newpairs,['a','b','equalChunkCosine','tokenWeightedCosine','delta'])
 writecsv(OUT/'chunk-weighting-documents.csv',per_doc,['videoId','channelId','wordCount','contentWordpieces','chunks','tailContentWordpieces','tailEqualWeight','tailTokenWeight'])
 return out

if __name__=='__main__':main()
