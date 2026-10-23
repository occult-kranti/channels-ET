"""Pinned ONNX sentence embeddings and English-language filtering for the pilot.
Full caption text remains at a user-controlled local path, never copied to dist.
"""
import os,sys,json,pathlib,hashlib,collections,re
import numpy as np
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
VENDOR=os.environ.get('CHANNELING_ANALYSIS_VENDOR')
if VENDOR:sys.path.append(VENDOR)
CACHE_PATH=pathlib.Path(__file__).resolve().parent/'inputs/language_cache.json'
LANG_CACHE=json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
def language(text):
 key=hashlib.sha256(text.encode()).hexdigest()
 if key in LANG_CACHE:return LANG_CACHE[key]
 try:
  from langdetect import detect_langs, DetectorFactory
  DetectorFactory.seed=42
  x=detect_langs(text)[0];r={'code':x.lang,'probability':round(x.prob,5),'method':'langdetect 1.0.9 seed42; short titles uncertain'}
 except ImportError:raise RuntimeError('Install pinned analysis requirements to classify newly changed titles.')
 except Exception:r={'code':'unknown','probability':0,'method':'langdetect failed'}
 LANG_CACHE[key]=r;return r
class Encoder:
 def __init__(self,path):
  import onnxruntime as ort
  from tokenizers import Tokenizer
  self.path=pathlib.Path(path);self.manifest=json.loads((self.path/'manifest.json').read_text())
  opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
  self.sess=ort.InferenceSession(str(self.path/'onnx/model.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
  self.tok=Tokenizer.from_file(str(self.path/'tokenizer.json'));self.tok.no_truncation();self.tok.no_padding()
  self.cache_dir=self.path/'cache';self.cache_dir.mkdir(exist_ok=True)
 def encode(self,texts,chunked=False):
  result=[];missing=[];out=[]
  for i,s in enumerate(texts):
   k=hashlib.sha256((self.manifest['revision']+'|'+str(chunked)+'|'+s).encode()).hexdigest();p=self.cache_dir/(k+'.npy')
   if p.exists():result.append(np.load(p))
   else:result.append(None);missing.append((i,s,p))
  sequences=[];owners=[]
  for i,s,p in missing:
   ids=self.tok.encode(s,add_special_tokens=False).ids
   chunks=[ids[j:j+240] for j in range(0,len(ids),240)] if chunked else [ids[:254]]
   if not chunks:chunks=[[]]
   for chunk in chunks:sequences.append([101]+chunk+[102]);owners.append(i)
  vecs=collections.defaultdict(list)
  for j in range(0,len(sequences),16):
   batch=sequences[j:j+16];n=max(map(len,batch));ids=np.zeros((len(batch),n),dtype=np.int64);mask=np.zeros_like(ids)
   for k,a in enumerate(batch):ids[k,:len(a)]=a;mask[k,:len(a)]=1
   inputs={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)};inputs={k:v for k,v in inputs.items() if k in [x.name for x in self.sess.get_inputs()]}
   token=self.sess.run(None,inputs)[0];emb=(token*mask[:,:,None]).sum(axis=1)/np.maximum(mask.sum(axis=1)[:,None],1);emb=normalize(emb)
   for own,vec in zip(owners[j:j+16],emb):vecs[own].append(vec)
  for i,s,p in missing:
   v=normalize(np.array(vecs[i]).mean(axis=0,keepdims=True))[0];result[i]=v;np.save(p,v)
  return np.array(result)

def centroid_similarity(vectors,docs,channels,min_docs,method,text_level):
 by=collections.defaultdict(list)
 for i,d in enumerate(docs):by[d['channelId']].append(i)
 selected=sorted([c for c in channels if len(by[c['id']])>=min_docs],key=lambda c:c['name'].lower())
 if not selected:return {'method':method,'textLevel':text_level,'channelIds':[],'matrix':[],'pairs':[],'minTitles':min_docs}
 cents=normalize(np.vstack([vectors[by[c['id']]].mean(axis=0) for c in selected]));M=cosine_similarity(cents);pairs=[]
 for i,a in enumerate(selected):
  for j in range(i+1,len(selected)):
   b=selected[j];pairs.append({'a':a['id'],'b':b['id'],'cosine':round(float(M[i,j]),6),'nA':len(by[a['id']]),'nB':len(by[b['id']])})
 return {'method':method,'textLevel':text_level,'minTitles':min_docs,'channelIds':[c['id'] for c in selected],'matrix':np.round(M,6).tolist(),'pairs':sorted(pairs,key=lambda x:-x['cosine']),'dimensions':int(vectors.shape[1]),'documentCount':len(docs),'channelVectors':{c['id']:np.round(v,7).tolist() for c,v in zip(selected,cents)}}

def semantic_mask(s,identity):
 return re.sub(r'\b(?:'+'|'.join(map(re.escape,identity))+r')\b',' ',s,flags=re.I)

def analyze(data,encoder,identity,topics,corpus_path):
 docs=[v for v in data['videos'] if v.get('titleEligible') and v.get('channelId')]
 texts=[semantic_mask(v['title'],identity) for v in docs];vecs=encoder.encode(texts)
 sim=centroid_similarity(vecs,docs,data['channels'],5,'all-MiniLM-L6-v2 384D; masked title mean centroids','English-likely video titles');sim['model']=encoder.manifest;sim['identityMasked']=True
 data['semanticSimilarity']=sim
 data['semanticSimilarity']['inputTextHashes']={v['id']:hashlib.sha256(s.encode()).hexdigest() for v,s in zip(docs,texts)}
 # Derived vectors are numeric, no text reconstruction or full transcripts exported.
 np.savez_compressed(pathlib.Path(__file__).resolve().parents[2]/'dist/analysis/title-embeddings.npz',video_ids=np.array([d['id'] for d in docs]),vectors=vecs.astype('float32'))
 corpus=json.loads(pathlib.Path(corpus_path).read_text()) if pathlib.Path(corpus_path).exists() else {'records':[]}
 all_rows=corpus['records'];en=[r for r in all_rows if r.get('transcript_status')=='success' and r.get('language_code','').split('-')[0]=='en' and not r.get('selection','').startswith('Additional')]
 vids={v['id']:v for v in data['videos']};en=[r for r in en if r['video_id'] in vids and vids[r['video_id']].get('channelId')]
 td=[dict(id=r['video_id'],channelId=vids[r['video_id']]['channelId']) for r in en]
 fulltexts=[semantic_mask(r['text'],identity) for r in en]
 # Trim outer 10% of whitespace words to test dependence on opening/closing material.
 trimmed=[]
 for s in fulltexts:
  words=s.split();k=max(1,int(len(words)*.10));trimmed.append(' '.join(words[k:-k]) if len(words)>20 else s)
 tv=encoder.encode(fulltexts,chunked=True);trimv=encoder.encode(trimmed,chunked=True)
 tsim=centroid_similarity(tv,td,data['channels'],2,'all-MiniLM-L6-v2 384D; 240-token chunks → equal-video → channel centroid','English caption pilot')
 trim_sim=centroid_similarity(trimv,td,data['channels'],2,'all-MiniLM-L6-v2; outer 10% of each caption document removed','English caption sensitivity')
 rows=[];by=collections.defaultdict(list)
 for r,d in zip(en,td):
  words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",r['text']);wc=len(words);tr=[{'id':tid,'label':label,'count':len(re.findall(pattern,r['text'],re.I)),'per1000Words':1000*len(re.findall(pattern,r['text'],re.I))/wc if wc else 0} for tid,label,pattern in topics]
  row={'videoId':r['video_id'],'channelId':d['channelId'],'url':r['url'],'wordCount':wc,'language':r['language_code'],'automaticCaptions':r.get('is_generated'),'captionArtifactSha256':r.get('sha256'),'textSha256':hashlib.sha256(r['text'].encode()).hexdigest(),'topics':tr,'selection':r.get('selection')};rows.append(row);by[d['channelId']].append(row)
 for c in data['channels']:
  rs=by[c['id']];c['transcriptCount']=len(rs);c['retrievedCaptionCount']=sum(r.get('transcript_status')=='success' and vids.get(r['video_id'],{}).get('channelId')==c['id'] for r in all_rows);c['transcriptTopics']=[{'id':tid,'label':label,'per1000Words':float(np.mean([next(t['per1000Words'] for t in r['topics'] if t['id']==tid) for r in rs]))} for tid,label,_ in topics] if rs else []
 data['transcripts']={'method':'Purposive recent-video caption pilot. Automatic captions are uncorrected; host, advertisements, audience questions and reported channeling voices are not diarized.','selection':corpus.get('method'),'attempted':len(all_rows),'available':sum(r.get('transcript_status')=='success' for r in all_rows),'englishPilotCount':len(rows),'excludedNonEnglishCount':sum(r.get('transcript_status')=='success' and r.get('language_code','').split('-')[0]!='en' for r in all_rows),'excludedAdditionalCount':sum(r.get('transcript_status')=='success' and r.get('selection','').startswith('Additional') for r in all_rows),'captionLanguages':dict(collections.Counter(r.get('language_code','unavailable') for r in all_rows)),'rows':rows,'similarity':tsim,'trimmedSimilarity':trim_sim,'tokenization':'WordPiece; non-overlapping240-token chunks, CLS/SEP; attention-mask mean pooling; chunk vectors L2-normalized, equal chunk mean per video, normalized; equal-video channel mean, normalized.','topicDefinition':"Regex matches per1,000 tokens matching [A-Za-z]+(?:'[A-Za-z]+)?, computed per video then averaged equally within channel. Contractions count as one word. Topics overlap; dictionary indicators are unvalidated."}
 data['coverage']['transcriptCount']=data['transcripts']['available'];data['coverage']['englishPilotCount']=len(rows)
 np.savez_compressed(pathlib.Path(__file__).resolve().parents[2]/'dist/analysis/caption-embeddings.npz',video_ids=np.array([d['id'] for d in td]),vectors=tv.astype('float32'),trimmed_vectors=trimv.astype('float32'))
 return data

def diagnostics(data,encoder,identity):
 from scipy.stats import spearmanr
 docs=[v for v in data['videos'] if v.get('titleEligible') and v.get('channelId')]
 arr=np.load(pathlib.Path(__file__).resolve().parents[2]/'dist/analysis/title-embeddings.npz');vectors=arr['vectors'];ids=list(arr['video_ids']);lookup={v['id']:v for v in docs};docs=[lookup[i] for i in ids]
 raw=encoder.encode([d['title'] for d in docs]);raw_sim=centroid_similarity(raw,docs,data['channels'],5,'MiniLM raw title sensitivity','English-likely video titles')
 data['titleRawSimilarity']=raw_sim
 def pairs(m):return {tuple(sorted([p['a'],p['b']])):p['cosine'] for p in m.get('pairs',[])}
 def compare(a,b):
  aa,bb=pairs(a),pairs(b);keys=sorted(set(aa)&set(bb));rho=float(spearmanr([aa[k] for k in keys],[bb[k] for k in keys]).statistic) if len(keys)>2 else None
  return {'pairCount':len(keys),'spearmanRankCorrelation':rho,'medianAbsoluteCosineChange':float(np.median([abs(aa[k]-bb[k]) for k in keys])) if keys else None}
 key=lambda s:' '.join(re.findall('[a-z]+',semantic_mask(s,identity).lower()))
 counts=collections.Counter(key(d['title']) for d in docs);keep=[i for i,d in enumerate(docs) if counts[key(d['title'])]==1]
 dedup=centroid_similarity(vectors[keep],[docs[i] for i in keep],data['channels'],5,'MiniLM excluding repeated masked title strings','English title sensitivity');data['deduplicatedTitleSimilarity']=dedup
 by=collections.defaultdict(list)
 for i,d in enumerate(docs):by[d['channelId']].append(i)
 eligible=data['semanticSimilarity']['channelIds'];rng=np.random.default_rng(42);wins={c:collections.Counter() for c in eligible}
 for _ in range(50):
  cents=normalize(np.vstack([vectors[rng.choice(by[c],5,replace=False)].mean(axis=0) for c in eligible]));M=cosine_similarity(cents);np.fill_diagonal(M,-np.inf)
  for i,c in enumerate(eligible):wins[c][eligible[int(np.argmax(M[i]))]]+=1
 stability=[{'channelId':c,'mostFrequentNearestChannel':wins[c].most_common(1)[0][0],'repeatShare':wins[c].most_common(1)[0][1]/50,'iterations':50,'sampledTitlesPerChannel':5} for c in eligible]
 # Matched-video indicators measure headline omission, not topic intensity.
 rows=data['transcripts']['rows'];matchedRows=[r for r in rows if r['videoId'] in lookup];matched=[]
 for t in data['topics']:
  title_n=sum(bool(re.search(t['regex'],lookup.get(r['videoId'],{}).get('title',''),re.I)) for r in matchedRows)
  caption_n=sum(next(x['count'] for x in r['topics'] if x['id']==t['id'])>0 for r in matchedRows)
  matched.append({'id':t['id'],'label':t['label'],'videoCount':len(matchedRows),'titleMatchCount':title_n,'captionMatchCount':caption_n,'titleShare':title_n/len(matchedRows) if matchedRows else None,'captionShare':caption_n/len(matchedRows) if matchedRows else None})
 carr=np.load(pathlib.Path(__file__).resolve().parents[2]/'dist/analysis/caption-embeddings.npz');C=cosine_similarity(carr['vectors']);cd={r['videoId']:r for r in rows};cids=list(carr['video_ids']);within=[];between=[]
 for i,a in enumerate(cids):
  for j in range(i+1,len(cids)):
   b=cids[j];(within if cd[a]['channelId']==cd[b]['channelId'] else between).append(float(C[i,j]))
 title_indices={v:i for i,v in enumerate(ids)};caption_indices={v:i for i,v in enumerate(cids)}
 matched_docs=[lookup[r['videoId']] for r in matchedRows]
 matched_title=centroid_similarity(vectors[[title_indices[d['id']] for d in matched_docs]],matched_docs,data['channels'],2,'MiniLM matched-video titles','Titles of exactly the same English-caption pilot videos')
 matched_caption=centroid_similarity(carr['vectors'][[caption_indices[d['id']] for d in matched_docs]],matched_docs,data['channels'],2,'MiniLM matched-video captions','Captions of exactly the same matched pilot videos')
 data['matchedTitleSimilarity']=matched_title;data['matchedCaptionSimilarity']=matched_caption
 summary=lambda xs:{'nPairs':len(xs),'median':float(np.median(xs)) if xs else None,'q1':float(np.percentile(xs,25)) if xs else None,'q3':float(np.percentile(xs,75)) if xs else None,'values':xs}
 data['diagnostics']={'rawVsMaskedTitles':compare(raw_sim,data['semanticSimilarity']),'deduplicatedVsAllTitles':compare(dedup,data['semanticSimilarity']),'excludedRepeatedTitleDocuments':len(docs)-len(keep),'captionFullVsTrimmed':compare(data['transcripts']['similarity'],data['transcripts']['trimmedSimilarity']),'matchedTitleVsCaption':compare(matched_title,matched_caption),'matchedVideoCount':len(matchedRows),'equalFiveTitleStability':stability,'matchedTitleCaptionIndicators':matched,'captionWithinBetween':{'within':summary(within),'between':summary(between),'note':'Pair values reuse documents; not independent observations. No p-values or population inference.'}}
 data['robustness']=[{'check':'Identity masking','result':f"Raw versus masked title rankings compared on {data['diagnostics']['rawVsMaskedTitles']['pairCount']} channel pairs.",'details':data['diagnostics']['rawVsMaskedTitles']},{'check':'Duplicate title strings','result':f"Removed {len(docs)-len(keep)} repeated masked-title documents in sensitivity corpus.",'details':data['diagnostics']['deduplicatedVsAllTitles']},{'check':'Opening and closing text','result':'Removed outer 10% of words at each end of every English caption document; compared the resulting channel rankings.','details':data['diagnostics']['captionFullVsTrimmed']},{'check':'Unequal title sample size','result':'50 fixed-seed repetitions draw five titles without replacement per eligible publisher; nearest-neighbor repeat shares are descriptive stability, not probabilities.','details':{'eligibleChannels':len(eligible),'iterations':50}},{'check':'Channel attribution and source metadata','result':'Direct watch-page uploader IDs supersede inherited route assignments. Exact UTC dates supersede inherited dates; conflicts remain in video rows.','details':{'changedTitles':sum(v.get('titleChanged',False) for v in data['videos']),'videosWithConflicts':sum(bool(v['conflicts']) for v in data['videos'])}}]
 return data
