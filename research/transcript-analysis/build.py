#!/usr/bin/env python3
"""Execute source-bound lexical analysis; full source bodies never enter outputs."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('MPLCONFIGDIR','/tmp/channels-et-transcript-mpl')
from pathlib import Path
import collections,csv,hashlib,itertools,json,re,unicodedata,warnings
from datetime import datetime,timezone
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from sklearn.decomposition import NMF,TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score,adjusted_rand_score
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
PRIVATE=Path('/workspace/channels-et-raw/transcript-analysis')
SEEDS=[11,23,47,71,97]; KS=list(range(2,7)); TOKEN=re.compile(r"\b[a-z]+(?:'[a-z]+)?\b")
FILLER=set("know yeah okay ok um uh gonna wanna gotta really just like sort thing things going said say says youre youve weve we're you're you've we've thats that's theres there's right".split())
STOP=sorted((set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'})|FILLER)
NAME_STOP={'bashar','darryl','daryl','anka','ashtar','athina','krol','daniel','scranton','paul','selig','alex','ferrari','danica','patrick','mayim','bialik','krystal','kelley','yasmeen','turayhi','kute','blackson','emilio','ortiz','aaron','alexander','lazar','ross','carrie'}
COMMERCIAL={'subscribe','subscription','subscribers','coupon','discount','discounts','sponsor','sponsors','sponsored','sponsorship','merchandise','patreon','purchase','purchases','checkout','mp3','sale','sales','newsletter','shop'}
THEMES={
 'contact_disclosure':[r'\bcontacts?\b',r'\bdisclosures?\b',r'\bufo\b',r'\bufos\b',r'\bextraterrestrials?\b',r'\baliens?\b'],
 'belief_reality_agency':[r'\bbeliefs?\b',r'\breality\b',r'\brealities\b',r'\bchoices?\b',r'\bmanifest(?:ation|ing|ed)?\b',r'\bempower(?:ment|ed)?\b'],
 'emotion_fear_selfworth':[r'\bfears?\b',r'\banxiety\b',r'\bemotions?\b',r'\bjoy\b',r'\blove\b',r'\bshame\b',r'\bself[- ]worth\b'],
 'practice_enthusiasm_alignment':[r'\bexcitement\b',r'\benthusiasm\b',r'\balign(?:ment|ing|ed)?\b',r'\bmeditat(?:ion|ing|e)\b',r'\bpractic(?:e|es|ing)\b',r'\bbreath(?:ing)?\b'],
 'ontology_consciousness_dimensions':[r'\bconsciousness\b',r'\bdimensions?\b',r'\bdimensional\b',r'\bfrequenc(?:y|ies)\b',r'\bvibrations?\b',r'\benergies\b',r'\benergy\b'],
 'claimed_entity_identity':[r'\bchannel(?:ing|ling|er|ers)?\b',r'\bentities\b',r'\bentity\b',r'\bguides?\b',r'\bhybrids?\b'],
 'epistemic_validation_skepticism':[r'\bevidence\b',r'\bproof\b',r'\bprove[ns]?\b',r'\bskeptic(?:al|ism|s)?\b',r'\bscientific\b',r'\bexperiment(?:s|al)?\b'],
 'health_healing_claims':[r'\bhealth\b',r'\bheal(?:ing|ed|s)?\b',r'\bdiseases?\b',r'\btrauma\b',r'\btherapy\b',r'\bmedical\b'],
 'relationships_collective_ethics':[r'\brelationships?\b',r'\bcollective\b',r'\bcommunity\b',r'\bcommunities\b',r'\bcompassion\b',r'\bethics?\b',r'\bkindness\b'],
 'commercial_promotion':[r'\b'+re.escape(x)+r'\b' for x in sorted(COMMERCIAL)]}
CIVILIZATIONS={
 'Arcturian / Arcturus':[r'\barcturians?\b',r'\barcturus\b'],
 'Pleiadian / Pleiades':[r'\bpleiadians?\b',r'\bpleiades\b'],
 'Sirian / Sirius':[r'\bsirians?\b',r'\bsirius\b'],
 'Essassani / Sassani':[r'\bessassani\b',r'\bsassani\b',r'\bessassanis\b'],
 'Andromedan / Andromeda':[r'\bandromedans?\b',r'\bandromeda\b'],
 'Orion':[r'\borion\b'],
 'Yahyel':[r'\byahyels?\b']}
ENTITY_NAMES={'Bashar':[r'\bbashar\b'],'Ashtar':[r'\bashtar\b'],'Saint Germain':[r'\bsaint germain\b',r'\bst\.? germain\b'],'The Creators':[r'\bthe creators\b'],'Thymus':[r'\bthymus\b'],'Ashanti':[r'\bashanti\b']}
POSTHOC_SPELLINGS={'Essassani / Sassani':{'kind':'claimed_civilization_name','variants':['esasani','sasani']},'Ashtar':{'kind':'entity_name_not_civilization','variants':['ashta','ashtalt','ashtara','ashtah']}}
COLORS={'Bashar-context':'#246a8d','Ashtar-attributed creator episode':'#bd6a13','Arcturian Council (source label)':'#6b5ba7','The Creators (source label)':'#9a657d','Saint Germain (source label)':'#7b8242','Ashanti (source label)':'#a84e42','Thymus (source label)':'#477e71','Spiritual Guides (comparison)':'#6a6a6a'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white','pdf.fonttype':42,'ps.fonttype':42,'svg.hashsalt':'channels-et-transcripts-v1'})

def norm(text):return unicodedata.normalize('NFKC',text).replace('’',"'").replace('‘',"'").lower()
def tokens(text):return TOKEN.findall(norm(text))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def verify_file(path,expected,size=None):
 p=Path(path);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==expected,str(p)
 if size is not None:assert len(b)==size,str(p)
 return b
def group_for_daniel(item):
 c=' '.join(item['categories_as_published'])
 for key,label in [('Arcturian','Arcturian Council (source label)'),('St. Germain','Saint Germain (source label)'),('Thymus','Thymus (source label)'),('Ashanti','Ashanti (source label)')]:
  if key in c:return label
 return 'The Creators (source label)'

def get_sources():
 raw=[];pins=[]
 def source_pin(path):pins.append({'path':str(path),'sha256':sha(ROOT/path),'bytes':(ROOT/path).stat().st_size})
 for p in ['research/harvest/asr/summary.json','research/harvest/publisher_sources/publisher-summary.json','research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json','research/access-repair/athina/publisher_sources/publisher-summary.json','research/access-repair/primary-sources/expanded-metadata.json']:source_pin(p)
 pub={r['source_id']:r for r in load(ROOT/'research/harvest/publisher_sources/publisher-summary.json')['records']}
 pub.update({r['source_id']:r for r in load(ROOT/'research/access-repair/athina/publisher_sources/publisher-summary.json')['records']})
 receipts=load(ROOT/'research/harvest/asr/summary.json')['records']+[load(ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json')]
 for receipt in receipts:
  assert receipt['status']=='completed' and receipt['transcribedScope']=='full_decoded_audio'
  p=pub[receipt['sourceId']];assert p['sha256']==receipt['sourceAudioSha256']
  files={f['name']:f for f in receipt['outputs']};t=files['transcript.txt'];s=files['segments.jsonl']
  text=verify_file(Path(receipt['transcriptDirectory'])/'transcript.txt',t['sha256'],t['bytes']).decode()
  segments=[json.loads(x)for x in verify_file(Path(receipt['transcriptDirectory'])/'segments.jsonl',s['sha256'],s['bytes']).decode().splitlines()if x]
  assert len(segments)==receipt['segments']
  athina=receipt['sourceId'].startswith('athina-')
  raw.append({'sourceId':receipt['sourceId'],'modality':'audio_asr','publisher':p['publisher_name'],'practitionerContext':'Athina Król' if athina else 'Darryl Anka / Bashar context','claimedGroup':'Ashtar-attributed creator episode' if athina else 'Bashar-context','title':p['episode_title'],'sourceUrl':p['enclosure_url'],'receiptWordCount':receipt['words'],'receiptWordCountDefinition':'ASR collector whitespace words','words':len(text.split()),'tokenCount':len(tokens(text)),'durationSeconds':receipt['sourceAudioDurationSeconds'],'audioBytes':p['bytes'],'sourceFormat':p['source_format'],'transcriptSha256':t['sha256'],'sourceAudioSha256':receipt['sourceAudioSha256'],'segmentSha256':s['sha256'],'sourceReceipt':'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json' if athina else 'research/harvest/asr/summary.json','speakerVerified':False,'youtubeEditionVerified':False,'text':text,'segments':segments})
 expanded=load(ROOT/'research/access-repair/primary-sources/expanded-metadata.json')
 for item in expanded['daniel']['items']:
  f=item['text'];text=verify_file(f['raw_local_path'],f['sha256'],f['bytes']).decode()
  raw.append({'sourceId':f"daniel-item-{item['item_index']:02d}",'modality':'publisher_text','publisher':'Daniel Scranton','practitionerContext':'Daniel Scranton','claimedGroup':group_for_daniel(item),'title':item['title'],'sourceUrl':item['url'],'receiptWordCount':f['word_count'],'receiptWordCountDefinition':'Publisher extractor original regex words','words':len(text.split()),'tokenCount':len(tokens(text)),'durationSeconds':None,'audioBytes':None,'sourceFormat':'authored_RSS_with_promotions_and_footer','transcriptSha256':f['sha256'],'sourceAudioSha256':None,'sourceReceipt':'research/access-repair/primary-sources/expanded-metadata.json','speakerVerified':False,'youtubeEditionVerified':False,'text':text,'segments':[]})
 p=expanded['paul'];f=p['text'];text=verify_file(f['raw_local_path'],f['sha256'],f['bytes']).decode()
 raw.append({'sourceId':p['source_id'],'modality':'publisher_text','publisher':'Paul Selig','practitionerContext':'Paul Selig','claimedGroup':'Spiritual Guides (comparison)','title':p['title'],'sourceUrl':p['requested_url'],'receiptWordCount':f['word_count'],'receiptWordCountDefinition':'Publisher extractor original regex words','words':len(text.split()),'tokenCount':len(tokens(text)),'durationSeconds':None,'audioBytes':None,'sourceFormat':'publisher_issued_Guides_transcript','transcriptSha256':f['sha256'],'sourceAudioSha256':None,'sourceReceipt':'research/access-repair/primary-sources/expanded-metadata.json','speakerVerified':False,'youtubeEditionVerified':False,'text':text,'segments':[]})
 raw.sort(key=lambda d:(d['modality']!='audio_asr',d['publisher'],d['sourceId']))
 for n,d in enumerate(raw):d['shortId']=('A' if d['modality']=='audio_asr' else 'T')+str(n+1 if n<20 else n-19).zfill(2)
 assert len(raw)==36 and len({d['sourceId']for d in raw})==36
 return raw,pins

def vectorize(texts,extra=()):
 v=TfidfVectorizer(lowercase=True,preprocessor=norm,token_pattern=r"(?u)\b[a-z][a-z']+\b",stop_words=sorted(set(STOP)|set(extra)),ngram_range=(1,2),min_df=2,max_df=.95,max_features=3000,sublinear_tf=True,norm='l2',smooth_idf=True)
 return v,v.fit_transform(texts)
def top_terms(vector,terms,n=10):
 a=np.asarray(vector).ravel();return [{'term':str(terms[i]),'weight':round(float(a[i]),8)}for i in np.argsort(-a)[:n]if a[i]>0]
def negation_diagnostic(vector,texts):
 vocab=set(vector.get_feature_names_out());words=['no','not','nor','never'];dfs={w:sum(w in set(tokens(t))for t in texts)for w in words}
 examples=[]
 for left,right in [('Alien contact is real','Alien contact is not real'),('Following excitement is safe','Following excitement is not safe')]:
  x=vector.transform([left,right]);examples.append({'synthetic':True,'left':left,'right':right,'leftNonzeroFeatures':x[0].nnz,'rightNonzeroFeatures':x[1].nnz,'cosine':float(cosine_similarity(x)[0,1])if x[0].nnz and x[1].nnz else None})
 return {'unigramDocumentFrequency':dfs,'unigramRetained':{w:w in vocab for w in words},'retainedBigramsContainingNegation':sum(any(w in t.split()for w in words)for t in vocab if' 'in t),'caveat':'Removing negation from the stoplist does not override minDf/maxDf/feature-cap filtering. Lexical cosine is not entailment or agreement.','syntheticControls':examples}
def nearest_indices(sim,k=1):
 return np.array([[j for j in np.argsort(-sim[i],kind='stable') if j!=i][:k]for i in range(len(sim))])
def topic_match(a,b):
 sim=cosine_similarity(a,b);i,j=linear_sum_assignment(-sim);return float(sim[i,j].mean())
def fit_nmf(x,k,seed=11):
 m=NMF(n_components=k,init='random',random_state=seed,max_iter=1500,solver='cd',tol=.0001)
 with warnings.catch_warnings(record=True) as caught:
  w=m.fit_transform(x)
 return m,w,[str(a.message)for a in caught]
def topic_models(x,terms,ids):
 candidates=[];selected=None
 for k in KS:
  base,w,warnings_=fit_nmf(x,k);stability=[topic_match(base.components_,fit_nmf(x,k,s)[0].components_)for s in SEEDS[1:]]
  candidates.append({'k':k,'seed':11,'reconstructionError':float(base.reconstruction_err_),'matchedTopicCosineMean':float(np.mean(stability)),'matchedTopicCosineMin':float(min(stability)),'stabilitySeeds':SEEDS[1:],'warnings':warnings_})
  if k==3:selected=(base,w)
 model,w=selected;weights=w/np.maximum(w.sum(axis=1,keepdims=True),1e-12)
 concentrations=[]
 for j in range(3):
  column=weights[:,j];total=column.sum();p=column/total if total else column
  concentrations.append({'topicId':f'topic-{j+1}','largestWeightSourceId':ids[int(np.argmax(column))],'largestDocumentWeight':float(column.max()),'documentsWithWeightAtLeast020':int(np.sum(column>=.2)),'effectiveSourceDocuments':float(np.exp(-np.sum(p[p>0]*np.log(p[p>0]))))if total else 0})
 return {'selectedK':3,'selectedKMeaning':'predeclared display choice; not true topic count','candidates':candidates,'terms':[{'topicId':f'topic-{i+1}','label':' / '.join(t['term']for t in top_terms(h,terms,3)),'terms':top_terms(h,terms,10)}for i,h in enumerate(model.components_)],'weights':[{'sourceId':s,'weights':r.tolist()}for s,r in zip(ids,weights)],'componentConcentration':concentrations,'stabilityDefinition':'Mean Hungarian-matched topic-term cosine against seed11; not semantic validity'},model,weights
def cluster_models(x,ids,audio_context=True):
  candidates=[];models={}
  for k in KS:
   m=KMeans(n_clusters=k,n_init=30,random_state=11);labels=m.fit_predict(x)
   silhouette=float(silhouette_score(x,labels,metric='cosine'))
   aris=[float(adjusted_rand_score(labels,KMeans(n_clusters=k,n_init=30,random_state=s).fit_predict(x)))for s in SEEDS[1:]]
   candidates.append({'k':k,'cosineSilhouette':silhouette,'seedAriMean':float(np.mean(aris)),'seedAriMin':min(aris),'inertia':float(m.inertia_),'seeds':SEEDS})
   models[k]=(m,labels)
  best=max(candidates,key=lambda a:(a['cosineSilhouette'],-a['k']));model,labels=models[best['k']]
  sizes=collections.Counter(int(v)for v in labels)
  return {'selectedK':best['k'],'selection':'highest seed11 cosine silhouette among2..6, exploratory','candidates':candidates,'labels':[{'sourceId':s,'cluster':int(l)}for s,l in zip(ids,labels)],'clusterSizes':[{'cluster':c,'documents':n,'sourceIds':[s for s,l in zip(ids,labels)if int(l)==c]}for c,n in sorted(sizes.items())],'singletonSourceIds':[s for s,l in zip(ids,labels)if sizes[int(l)]==1],'silhouetteInterpretation':('The selected2cluster result is a19-versus1 source-context/singleton partition. Stable ARI does not validate practitioner or ET separation.'if audio_context else'Separately fitted16publisher texts; source author, genre and promotions confound the clusters. No validated ET separation.')},model,labels
def lexical_counts(text,dictionary):
 text=norm(text);return {key:sum(len(re.findall(p,text))for p in patterns)for key,patterns in dictionary.items()}
def json_ready(value):
 if isinstance(value,np.ndarray):return value.tolist()
 if isinstance(value,np.generic):return value.item()
 return value
def write_csv(path,rows):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if not rows:return
 with path.open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def network_layout(n):
 angles=np.linspace(0,2*np.pi,n,endpoint=False);return np.c_[np.cos(angles),np.sin(angles)]
def label_points(ax,points,labels):
 """Deterministic screen-space placement, with callouts for crowded labels."""
 ax.figure.canvas.draw();renderer=ax.figure.canvas.get_renderer();occupied=[]
 marker_boxes=[]
 for point in points:
  x,y=ax.transData.transform(point);marker_boxes.append(Bbox.from_bounds(x-5,y-5,10,10))
 candidates=[(r*dx,r*dy)for r in [8,14,22,32,44,58]for dx,dy in [(1,1),(1,-1),(-1,1),(-1,-1),(1,0),(-1,0),(0,1),(0,-1)]]
 for point,label in zip(points,labels):
  chosen=None;best=None
  for dx,dy in candidates:
   a=ax.annotate(label,point,xytext=(dx,dy),textcoords='offset points',ha='left'if dx>=0 else'right',va='bottom'if dy>=0 else'top',fontsize=8)
   box=a.get_window_extent(renderer).expanded(1.12,1.2);score=sum(box.overlaps(b)for b in occupied+marker_boxes)
   a.remove()
   if best is None or score<best[0]:best=(score,dx,dy,box)
   if score==0:chosen=(dx,dy,box);break
  if chosen is None:chosen=best[1:]
  dx,dy,box=chosen;ax.annotate(label,point,xytext=(dx,dy),textcoords='offset points',ha='left'if dx>=0 else'right',va='bottom'if dy>=0 else'top',fontsize=8,arrowprops={'arrowstyle':'-','lw':.45,'color':'#83909a'}if abs(dx)+abs(dy)>20 else None);occupied.append(box)
def make_network(sim,docs):
 edges={}
 for i in range(len(docs)):
  for j in nearest_indices(sim,2)[i]:
   if sim[i,j]>=.2:
    a,b=sorted((i,int(j)));edges[a,b]={'source':docs[a]['sourceId'],'target':docs[b]['sourceId'],'cosine':float(sim[a,b])}
 thresholds=[]
 for t in [.15,.25,.35,.45,.55,.65,.75]:
  count=int(np.sum(np.triu(sim>=t,k=1)));thresholds.append({'threshold':t,'edges':count,'possiblePairs':len(docs)*(len(docs)-1)//2,'density':count/(len(docs)*(len(docs)-1)/2)})
 return {'nodes':[{'id':d['sourceId'],'label':d['shortId'],'publisher':d['publisher'],'claimedGroup':d['claimedGroup'],'words':d['words']}for d in docs],'edges':list(edges.values()),'edgeRule':'undirected union of top2 neighbors per document with cosine>=0.20','thresholdSensitivity':thresholds,'interpretation':'Lexical resemblance between source documents, not social links or agreement'}
def entity_network(docs,counts):
 out={}
 for modality in ['audio_asr','publisher_text']:
  subset=[d for d in docs if d['modality']==modality];keys=list(CIVILIZATIONS)
  ns=[{'id':key,'documents':sum(counts[d['sourceId']][key]>0 for d in subset),'mentions':sum(counts[d['sourceId']][key]for d in subset)}for key in keys]
  es=[{'source':a,'target':b,'documents':sum(counts[d['sourceId']][a]>0 and counts[d['sourceId']][b]>0 for d in subset)}for a,b in itertools.combinations(keys,2)]
  out[modality]={'denominatorDocuments':len(subset),'nodes':[n for n in ns if n['documents']],'edges':[e for e in es if e['documents']]}
 return {'cohorts':out,'interpretation':'Explicit dictionary co-mentions per source; includes possible astronomy/fiction/ASR ambiguities; no physical or social edges'}

def build():
 PRIVATE.mkdir(parents=True,exist_ok=True);(HERE/'figures').mkdir(exist_ok=True);(HERE/'tables').mkdir(exist_ok=True)
 docs,pins=get_sources();audio=[d for d in docs if d['modality']=='audio_asr'];authored=[d for d in docs if d['modality']=='publisher_text']
 texts=[d['text']for d in audio];ids=[d['sourceId']for d in audio]
 av,ax=vectorize(texts);at=av.get_feature_names_out();tv,tx=vectorize([d['text']for d in authored]);tt=tv.get_feature_names_out()
 sim=cosine_similarity(ax);tsim=cosine_similarity(tx)
 topics,nmf,weights=topic_models(ax,at,ids);clusters,km,labels=cluster_models(ax,ids)
 authored_topics,_,_=topic_models(tx,tt,[d['sourceId']for d in authored])
 authored_clusters,_,_=cluster_models(tx,[d['sourceId']for d in authored],audio_context=False)
 text_svd=TruncatedSVD(n_components=2,random_state=11);text_xy=text_svd.fit_transform(tx)
 authored_clusters['projection']={'method':'Publisher-text-only two-component TruncatedSVD','explainedVarianceRatio':text_svd.explained_variance_ratio_.tolist(),'publisherText':[{'sourceId':d['sourceId'],'x':float(p[0]),'y':float(p[1])}for d,p in zip(authored,text_xy)]}
 svd=TruncatedSVD(n_components=2,random_state=11);xy=svd.fit_transform(ax);projected=svd.transform(av.transform([d['text']for d in authored]))
 clusters['projection']={'method':'ASR-fitted two-component TruncatedSVD; raw component signs arbitrary','explainedVarianceRatio':svd.explained_variance_ratio_.tolist(),'audio':[{'sourceId':d['sourceId'],'x':float(p[0]),'y':float(p[1])}for d,p in zip(audio,xy)],'publisherComparison':[{'sourceId':d['sourceId'],'x':float(p[0]),'y':float(p[1])}for d,p in zip(authored,projected)]}
 theme_counts={d['sourceId']:lexical_counts(d['text'],THEMES)for d in docs};civ_counts={d['sourceId']:lexical_counts(d['text'],CIVILIZATIONS)for d in docs};name_counts={d['sourceId']:lexical_counts(d['text'],ENTITY_NAMES)for d in docs}
 rates=[{'sourceId':d['sourceId'],'tokenDenominator':d['tokenCount'],'counts':theme_counts[d['sourceId']],'rates':{k:1000*v/d['tokenCount']for k,v in theme_counts[d['sourceId']].items()}}for d in docs]
 groups=[]
 for group in sorted({d['claimedGroup']for d in docs}):
  sub=[d for d in docs if d['claimedGroup']==group];n=sum(d['tokenCount']for d in sub)
  groups.append({'group':group,'documents':len(sub),'modality':sub[0]['modality'],'sourceIds':[d['sourceId']for d in sub],'tokens':n,'equalDocumentMeanRates':{k:float(np.mean([1000*theme_counts[d['sourceId']][k]/d['tokenCount']for d in sub]))for k in THEMES},'pooledTokenRates':{k:1000*sum(theme_counts[d['sourceId']][k]for d in sub)/n for k in THEMES}})
 time_profiles=[];chunk_metadata=[]
 for d in audio:
  bins=[{'tokens':0,'counts':collections.Counter()}for _ in range(10)];chunk=[];chunk_tokens=0
  for segment in d['segments']:
   midpoint=(segment['start']+segment['end'])/2;index=min(9,int(10*midpoint/d['durationSeconds']));nt=len(tokens(segment['text']));bins[index]['tokens']+=nt;bins[index]['counts'].update(lexical_counts(segment['text'],THEMES));chunk.append(segment);chunk_tokens+=nt
   if chunk_tokens>=500:
    chunk_metadata.append({'sourceId':d['sourceId'],'startSeconds':chunk[0]['start'],'endSeconds':chunk[-1]['end'],'firstSegment':chunk[0]['id'],'lastSegment':chunk[-1]['id'],'tokens':chunk_tokens});chunk=[];chunk_tokens=0
  if chunk:chunk_metadata.append({'sourceId':d['sourceId'],'startSeconds':chunk[0]['start'],'endSeconds':chunk[-1]['end'],'firstSegment':chunk[0]['id'],'lastSegment':chunk[-1]['id'],'tokens':chunk_tokens})
  time_profiles.append({'sourceId':d['sourceId'],'bins':[{'index':i,'normalizedStart':i/10,'normalizedEnd':(i+1)/10,'tokenDenominator':b['tokens'],'rates':{k:1000*b['counts'][k]/b['tokens']if b['tokens']else None for k in THEMES}}for i,b in enumerate(bins)]})
 sensitivities=[];tri=np.triu_indices(len(audio),1)
 for name,extra in [('proper_names_excluded',NAME_STOP),('commercial_vocabulary_excluded',COMMERCIAL)]:
  v,x=vectorize(texts,extra);s=cosine_similarity(x);model,w,_=fit_nmf(x,3)
  # Compare topics only on the explicit shared vocabulary.
  common=sorted(set(at)&set(v.get_feature_names_out()));left={v:i for i,v in enumerate(at)};right={v:i for i,v in enumerate(v.get_feature_names_out())}
  topic_stability=topic_match(nmf.components_[:,[left[t]for t in common]],model.components_[:,[right[t]for t in common]])
  sensitivities.append({'name':name,'featureCount':x.shape[1],'cosinePairRankCorrelation':float(spearmanr(sim[tri],s[tri]).statistic),'nearestNeighborPreservedFraction':float(np.mean(nearest_indices(sim)[:,0]==nearest_indices(s)[:,0])),'matchedTopicCosineSharedVocabulary':topic_stability,'sharedFeatures':len(common),'excludedTokens':sorted(extra)})
 central=[' '.join(s['text']for s in d['segments']if .1*d['durationSeconds']<=(s['start']+s['end'])/2<=.9*d['durationSeconds'])for d in audio]
 cv,cx=vectorize(central);cs=cosine_similarity(cx)
 sensitivities.append({'name':'central80percent_audio_time','cosinePairRankCorrelation':float(spearmanr(sim[tri],cs[tri]).statistic),'nearestNeighborPreservedFraction':float(np.mean(nearest_indices(sim)[:,0]==nearest_indices(cs)[:,0])),'retainedAnalysisTokens':sum(len(tokens(t))for t in central),'baselineAnalysisTokens':sum(d['tokenCount']for d in audio),'interpretation':'Time-window proxy only; does not establish advertisement or host removal'})
 lopo=[]
 for publisher in sorted({d['publisher']for d in audio}):
  keep=np.array([d['publisher']!=publisher for d in audio]);model,_,_=fit_nmf(ax[keep],3)
  lopo.append({'excludedPublisher':publisher,'excludedDocuments':int((~keep).sum()),'remainingDocuments':int(keep.sum()),'matchedTopicCosine':topic_match(nmf.components_,model.components_)})
 sensitivities.append({'name':'leave_one_publisher_out_nmf_fixed_vocabulary','records':lopo,'minimumMatchedCosine':min(x['matchedTopicCosine']for x in lopo),'meanMatchedCosine':float(np.mean([x['matchedTopicCosine']for x in lopo])),'interpretation':'Fixed original ASR vocabulary/IDF, not an independently refitted preprocessing pipeline'})
 docnet=make_network(sim,audio);entitynet=entity_network(docs,civ_counts)
 channel_topic=[]
 for publisher in sorted({d['publisher']for d in audio}):
  indices=[i for i,d in enumerate(audio)if d['publisher']==publisher];channel_topic.append({'publisher':publisher,'documents':len(indices),'sourceIds':[ids[i]for i in indices],'topicWeights':weights[indices].mean(axis=0).tolist()})
 audio_display=top_terms(np.asarray(ax.mean(axis=0)),at,40);authored_display=top_terms(np.asarray(tx.mean(axis=0)),tt,40)
 amap={t:i for i,t in enumerate(at)};tmap={t:i for i,t in enumerate(tt)}
 tfidf_audio={'sourceIds':ids,'featureCount':ax.shape[1],'terms':audio_display,'displayTermWeights':[{'sourceId':d['sourceId'],'weights':ax[i,[amap[t['term']]for t in audio_display]].toarray().ravel().tolist()}for i,d in enumerate(audio)],'documents':[{'sourceId':d['sourceId'],'topTerms':top_terms(ax[i].toarray(),at,12)}for i,d in enumerate(audio)],'cosine':sim.tolist(),'negationDiagnostic':negation_diagnostic(av,texts)}
 tfidf_authored={'sourceIds':[d['sourceId']for d in authored],'featureCount':tx.shape[1],'terms':authored_display,'displayTermWeights':[{'sourceId':d['sourceId'],'weights':tx[i,[tmap[t['term']]for t in authored_display]].toarray().ravel().tolist()}for i,d in enumerate(authored)],'documents':[{'sourceId':d['sourceId'],'topTerms':top_terms(tx[i].toarray(),tt,12)}for i,d in enumerate(authored)],'cosine':tsim.tolist(),'topics':authored_topics,'clusters':authored_clusters,'negationDiagnostic':negation_diagnostic(tv,[d['text']for d in authored])}
 for sensitivity in sensitivities:sensitivity['cohort']='audio_asr'
 publisher_tri=np.triu_indices(16,1);_,publisher_control=vectorize([d['text']for d in authored],COMMERCIAL);publisher_cos=cosine_similarity(publisher_control)
 sensitivities.append({'name':'commercial_vocabulary_excluded','cohort':'publisher_text','cosinePairRankCorrelation':float(spearmanr(tsim[publisher_tri],publisher_cos[publisher_tri]).statistic),'nearestNeighborPreservedFraction':float(np.mean(nearest_indices(tsim)[:,0]==nearest_indices(publisher_cos)[:,0])),'excludedTokens':sorted(COMMERCIAL),'interpretation':'Vocabulary exclusion only; does not remove or identify all promotional sections'})
 cross=cosine_similarity(ax,av.transform([d['text']for d in authored]));cross_rows=[{'audioSourceId':audio[i]['sourceId'],'publisherSourceId':authored[j]['sourceId'],'cosine':float(cross[i,j])}for i,j in itertools.product(range(20),range(16))]
 public_sources=[{k:v for k,v in d.items()if k not in ('text','segments')}for d in docs]
 posthoc=[]
 for family,definition in POSTHOC_SPELLINGS.items():
  records=[]
  for d in audio:
   counts={variant:len(re.findall(r'\b'+re.escape(variant)+r'\b',norm(d['text'])))for variant in definition['variants']}
   strict=civ_counts[d['sourceId']][family]if definition['kind']=='claimed_civilization_name'else name_counts[d['sourceId']][family]
   records.append({'sourceId':d['sourceId'],'strictCanonicalMatches':strict,'candidateSpellingCounts':counts,'additionalCandidateMatches':sum(counts.values()),'validatedAgainstAudio':False})
  posthoc.append({'family':family,'kind':definition['kind'],'variants':definition['variants'],'records':records,'strictCanonicalMatches':sum(r['strictCanonicalMatches']for r in records),'additionalCandidateMatches':sum(r['additionalCandidateMatches']for r in records),'candidateBearingDocuments':sum(r['additionalCandidateMatches']>0 for r in records),'interpretation':'Post-hoc ASR spelling candidates, not verified aliases or revised primary counts; full audio/name validation remains required'})
 result={'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(),'summary':{'audioDocuments':20,'authoredDocuments':16,'basharContextAudioDocuments':19,'ashtarContextAudioDocuments':1,'audioPublishers':len({d['publisher']for d in audio}),'audioReceiptWords':sum(d['receiptWordCount']for d in audio),'audioCommonTokens':sum(d['tokenCount']for d in audio),'authoredReceiptWords':sum(d['receiptWordCount']for d in authored),'authoredCommonTokens':sum(d['tokenCount']for d in authored),'audioDurationSeconds':sum(d['durationSeconds']for d in audio),'audioBytes':sum(d['audioBytes']for d in audio),'timeBins':len(time_profiles)*10,'nonoverlappingSegmentChunks':len(chunk_metadata),'newYoutubeVideoDownloads':0,'speakerIdentityVerified':False,'rawTextPublished':False},'sources':public_sources,'tfidf':{'audio':tfidf_audio,'authored':tfidf_authored,'crossModalityProjection':{'fit':'ASR-only vocabulary and IDF; comparison is confounded by author, source and modality','rows':sorted(cross_rows,key=lambda x:-x['cosine'])}},'topics':topics,'clusters':clusters,'lexicons':{'themeDefinitions':THEMES,'civilizationDefinitions':CIVILIZATIONS,'entityNameDefinitions':ENTITY_NAMES,'themeRates':rates,'groupRates':groups,'civilizationCounts':[{'sourceId':d['sourceId'],'tokenDenominator':d['tokenCount'],'counts':civ_counts[d['sourceId']],'rates':{k:1000*v/d['tokenCount']for k,v in civ_counts[d['sourceId']].items()}}for d in docs],'entityNameCounts':[{'sourceId':d['sourceId'],'counts':name_counts[d['sourceId']]}for d in docs],'timeProfiles':time_profiles,'posthocSpellingSensitivity':posthoc},'networks':{'documentSimilarity':docnet,'publisherDocumentSimilarity':make_network(tsim,authored),'entityMention':entitynet,'channelTopic':channel_topic},'sensitivities':sensitivities,'chunkMetadata':chunk_metadata,'figures':[],'limits':load(HERE/'protocol.json')['inferenceLimits']}
 save(HERE/'sources.json',public_sources);save(HERE/'analysis.json',result);save(HERE/'input-manifest.json',{'files':pins,'privateSourceTextRehosted':False});np.savez_compressed(PRIVATE/'numeric-feature-matrices.npz',audio=ax.toarray(),authored=tx.toarray(),audio_terms=at,authored_terms=tt)
 write_csv(HERE/'tables/sources.csv',public_sources)
 write_csv(HERE/'tables/audio-cosine-pairs.csv',[{'source':ids[i],'target':ids[j],'cosine':float(sim[i,j])}for i,j in zip(*tri)])
 write_csv(HERE/'tables/topic-weights.csv',[{'sourceId':ids[i],**{f'topic{j+1}':float(v)for j,v in enumerate(row)}}for i,row in enumerate(weights)])
 write_csv(HERE/'tables/theme-rates.csv',[{'sourceId':r['sourceId'],'tokenDenominator':r['tokenDenominator'],**r['rates']}for r in rates])
 write_csv(HERE/'tables/civilization-mentions.csv',[{'sourceId':d['sourceId'],'tokenDenominator':d['tokenCount'],**civ_counts[d['sourceId']]}for d in docs])
 write_csv(HERE/'tables/nmf-candidates.csv',topics['candidates']);write_csv(HERE/'tables/cluster-candidates.csv',clusters['candidates']);write_csv(HERE/'tables/leave-one-publisher-out.csv',lopo)
 make_figures(result,audio,authored,xy,projected,sim,weights,labels)
 print(json.dumps({'status':'candidate_executed','summary':result['summary'],'nmfK':3,'clusterK':clusters['selectedK'],'bestSilhouette':max(x['cosineSilhouette']for x in clusters['candidates']),'figures':len(result['figures'])}))
 return result

def make_figures(result,audio,authored,xy,projected,sim,weights,labels):
 captions={}
 def emit(name,fig,caption):
  fig.tight_layout();paths=[]
  for ext in ['pdf','svg','png']:
   metadata={'Creator':'Channels ET reproducible transcript analysis','CreationDate':None,'ModDate':None}if ext=='pdf'else({'Creator':'Channels ET reproducible transcript analysis','Date':None}if ext=='svg'else{'Software':'Channels ET reproducible transcript analysis'})
   p=HERE/'figures'/f'{name}.{ext}';fig.savefig(p,dpi=180,bbox_inches='tight',metadata=metadata);paths.append(str(p.relative_to(HERE)))
  plt.close(fig);captions[name]=caption;result['figures'].append({'id':name,'paths':paths,'caption':caption})
 # 1. Modality and sample imbalance.
 fig,ax=plt.subplots(1,2,figsize=(11,4));groups=['Bashar-context audio','Ashtar creator audio','Daniel authored RSS','Paul publisher text'];counts=[19,1,15,1];ax[0].barh(groups,counts,color=['#246a8d','#bd6a13','#9a657d','#6a6a6a']);ax[0].set_xlabel('Source documents');ax[0].set_xlim(0,21)
 for i,v in enumerate(counts):ax[0].text(v+.15,i,str(v),va='center')
 ax[0].set_title('Observed source frame');a=[d['tokenCount']for d in audio];t=[d['tokenCount']for d in authored];ax[1].boxplot([a,t],tick_labels=['Audio ASR (20)','Publisher text (16)'],showfliers=True);ax[1].set_ylabel('Common analysis tokens per document');ax[1].set_title('Document-length distributions')
 emit('source-coverage',fig,'Thirty-six source documents are two distinct modalities. Nineteen of20audio recordings have Bashar context; the one Ashtar-attributed creator episode is a singleton. This is not a balanced sample of mediums or civilizations. Token counts use the common analytical tokenizer, not acquisition receipt word definitions.')
 # 2. Core source cosine heatmap.
 order=np.lexsort((np.arange(20),labels));fig,ax=plt.subplots(figsize=(9,8));im=ax.imshow(sim[np.ix_(order,order)],vmin=0,vmax=1,cmap='Blues');ax.set_xticks(range(20),[audio[i]['shortId']for i in order],rotation=90);ax.set_yticks(range(20),[audio[i]['shortId']for i in order]);ax.set_title('Audio-source TF-IDF cosine resemblance');fig.colorbar(im,ax=ax,label='Cosine similarity (0–1)',fraction=.045)
 emit('audio-cosine',fig,'Cosine resemblance of20complete unverified ASR documents in a shared audio-only TF-IDF fit, ordered by the exploratory KMeans labels. Diagonal values are self-similarity. Short IDs join sources.json; resemblance is not semantic agreement, independent origin or a speaker comparison.')
 # 3. Shared-space overlay, explicit modality markers.
 fig,ax=plt.subplots(figsize=(10,7))
 for dataset,coords,marker in [(audio,xy,'o'),(authored,projected,'^')]:
  for d,p in zip(dataset,coords):ax.scatter(*p,c=COLORS[d['claimedGroup']],marker=marker,s=65,edgecolors='white',linewidth=.6)
 ax.set_xlabel('ASR-fitted SVD component1');ax.set_ylabel('ASR-fitted SVD component2');ax.set_title('Source and modality overlay in the audio lexical space');handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor=c,label=g,markersize=7)for g,c in COLORS.items()];handles+=[Line2D([0],[0],marker='^',color='gray',linestyle='none',label='Publisher-text projection')];ax.legend(handles=handles,fontsize=8,loc='upper left',bbox_to_anchor=(1,1))
 label_points(ax,np.vstack([xy,projected]),[d['shortId']for d in audio+authored])
 emit('source-overlay',fig,'Two-component TruncatedSVD is fitted only to20audio-source TF-IDF rows. The16publisher texts are projected using that same vocabulary/IDF and SVD. Marker shape indicates modality; colors denote source context/claimed labels. Label callouts reduce overlap without changing point positions. Author, format, length and modality confounding prohibit civilization-level separation claims.')
 # 4. NMF weights.
 fig,ax=plt.subplots(figsize=(11,6));bottom=np.zeros(20)
 for j,c in enumerate(['#246a8d','#bd6a13','#6b5ba7']):ax.barh(range(20),weights[:,j],left=bottom,color=c,label=f"Topic{j+1}: "+result['topics']['terms'][j]['label']);bottom+=weights[:,j]
 ax.set_yticks(range(20),[d['shortId']for d in audio]);ax.set_xlim(0,1);ax.set_xlabel('Normalized document-topic weight');ax.set_title('Predeclared three-topic audio NMF display');ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(1,1));ax.invert_yaxis()
 emit('audio-topics',fig,'NMF is fit to the20audio document vectors. Three display topics were selected prospectively for readable exploration; candidates2–6and seed-matched stability remain available. Weights sum to1per document. Top-term labels describe model components, not validated themes or distinct belief systems.')
 # 5. Theme overlays across source-attributed groups.
 groups=result['lexicons']['groupRates'];keys=list(THEMES);values=np.array([[g['equalDocumentMeanRates'][k]for k in keys]for g in groups]);fig,ax=plt.subplots(figsize=(13,6));im=ax.imshow(values,cmap='YlGnBu',aspect='auto',vmin=0);ax.set_yticks(range(len(groups)),[g['group']+f" (n={g['documents']}; "+('ASR'if g['modality']=='audio_asr'else'text')+')'for g in groups]);ax.set_xticks(range(len(keys)),[k.replace('_','\n')for k in keys],rotation=45,ha='right',fontsize=8)
 for i,j in itertools.product(range(len(groups)),range(len(keys))):ax.text(j,i,f'{values[i,j]:.1f}',ha='center',va='center',fontsize=8,color='white'if values[i,j]>.6*values.max()else'#202020')
 fig.colorbar(im,ax=ax,label='Mean mentions per1000analysis tokens',fraction=.025);ax.set_title('Overlapping lexical themes by source context and modality')
 emit('theme-overlay',fig,'Overlapping predeclared keyword-family rates per1000common tokens, averaged equally across source documents within each labeled context. Counts are dictionary matches, not validated semantic coding. Source-attributed labels and modality are visible; singleton rows have no group-level uncertainty estimate. Promotion/footers and ASR error remain possible contributors.')
 # 6. Sparse nearest-neighbor source graph.
 fig,ax=plt.subplots(figsize=(8,8));pos=network_layout(20);lookup={d['sourceId']:i for i,d in enumerate(audio)}
 for e in result['networks']['documentSimilarity']['edges']:
  i,j=lookup[e['source']],lookup[e['target']];ax.plot(pos[[i,j],0],pos[[i,j],1],color='#a9b6c0',alpha=.7,lw=.4+2*e['cosine'],zorder=1)
 for i,d in enumerate(audio):ax.scatter(*pos[i],s=100+max(0,d['tokenCount'])/100,c=COLORS[d['claimedGroup']],edgecolors='white',zorder=2);ax.text(pos[i,0]*1.1,pos[i,1]*1.1,d['shortId'],ha='center',va='center')
 ax.set_aspect('equal');ax.axis('off');ax.set_title('Audio-source lexical nearest-neighbor network')
 emit('document-network',fig,'Undirected union of each audio document’s two nearest TF-IDF neighbors with cosine≥0.20. Nodes are publication documents, sized by analytical token count; circular positions are purely schematic. Edges encode lexical resemblance, not social relations or independently shared ET knowledge. Threshold sensitivity is exported.')
 # 7. Claimed civilization co-mention networks, modality separated.
 fig,axes=plt.subplots(1,2,figsize=(13,6));allkeys=list(CIVILIZATIONS);pos=network_layout(len(allkeys));index={k:i for i,k in enumerate(allkeys)}
 for modality,ax in zip(['audio_asr','publisher_text'],axes):
  n=result['networks']['entityMention']['cohorts'][modality]
  for e in n['edges']:
   i,j=index[e['source']],index[e['target']];ax.plot(pos[[i,j],0],pos[[i,j],1],color='#bac3ca',lw=.7+e['documents']*.35,zorder=1)
   midpoint=(pos[i]+pos[j])/2;ax.text(*midpoint,f"{e['documents']} "+('doc'if e['documents']==1 else'docs'),ha='center',va='center',fontsize=9,color='#293641',bbox={'facecolor':'white','edgecolor':'none','pad':2},zorder=3)
  for node in n['nodes']:
   i=index[node['id']];ax.scatter(*pos[i],s=80+node['documents']*30,color='#246a8d'if modality=='audio_asr'else'#9a657d',zorder=2);ax.annotate(node['id']+f"\nn={node['documents']}",pos[i]*1.15,ha='center',va='center',fontsize=9)
  ax.set_xlim(-1.65,1.65);ax.set_ylim(-1.5,1.5);ax.set_aspect('equal');ax.axis('off');ax.set_title(('Audio ASR'if modality=='audio_asr'else'Publisher text')+f" ({n['denominatorDocuments']}documents)")
 fig.suptitle('Claimed-civilization name-family co-mentions')
 emit('civilization-mentions',fig,'Nodes are explicit claimed-civilization/star-system dictionary families and labels give documents with at least one match. Edge labels give documents mentioning both families once per pair; audio and publisher-text panels remain separate. Zero-hit families are omitted from the drawing and retained in the complete count table. Positions are schematic. Star-system/Orion mentions can concern astronomy or fiction; ASR variants are not fuzzy-corrected. Bashar and Ashtar entity names are recorded separately and are not silently mapped to a civilization.')
 # 8. Topic/cluster diagnostics.
 fig,ax=plt.subplots(1,3,figsize=(13,4));n=result['topics']['candidates'];c=result['clusters']['candidates'];ax[0].plot(KS,[r['reconstructionError']for r in n],'o-',color='#246a8d');ax[0].set_ylabel('NMF reconstruction error');ax[1].plot(KS,[r['matchedTopicCosineMean']for r in n],'o-',color='#6b5ba7');ax[1].set_ylabel('Matched topic-term cosine');ax[1].set_ylim(0,1);ax[2].plot(KS,[r['cosineSilhouette']for r in c],'o-',color='#bd6a13');ax[2].axhline(0,color='#888',lw=.7);ax[2].set_ylabel('KMeans cosine silhouette')
 for a in ax:a.set_xlabel('Candidate K');a.set_xticks(KS)
 fig.suptitle('Model-choice diagnostics on20source documents')
 emit('model-diagnostics',fig,'NMF reconstruction decreases with model complexity and is not evidence that additional topics are substantively real. Topic stability is seed-matched term-vector cosine; KMeans selection exposes all candidate silhouettes. Neither stability nor a selected partition validates a medium or civilization ontology.')
 # 9. Audio normalized-time profiles.
 keys=['contact_disclosure','belief_reality_agency','practice_enthusiasm_alignment'];profiles={r['sourceId']:r['bins']for r in result['lexicons']['timeProfiles']};fig,axes=plt.subplots(1,3,figsize=(13,4))
 for key,ax in zip(keys,axes):
  for group in ['Bashar-context','Ashtar-attributed creator episode']:
   sub=[d for d in audio if d['claimedGroup']==group];values=np.array([[profiles[d['sourceId']][i]['rates'][key]or 0 for i in range(10)]for d in sub]);ax.plot(np.arange(10)*10+5,values.mean(axis=0),marker='o',ms=3,color=COLORS[group],label=f'{group} (n={len(sub)})')
  ax.set_title(key.replace('_',' '),fontsize=10);ax.set_xlabel('Decoded-audio time (%)');ax.set_ylabel('Mentions per1000tokens');ax.set_xlim(0,100)
 axes[0].legend(fontsize=7);emit('audio-time-profiles',fig,'Segments are assigned by their midpoint to ten equal decoded-audio-time bins. Each bin’s keyword occurrences are divided by its own common-token denominator; curves are equal-document means. The Ashtar curve represents one recording, not an estimated population trajectory. Bins are dependent and not independent observations; source intro/outro/advertising remains unsegmented.')
 result['figures']=result['figures'];save(HERE/'analysis.json',result);save(HERE/'captions.json',captions)

if __name__=='__main__':build()
