#!/usr/bin/env python3
"""Independently verify released digest-Q&A joins, counts and lexical neighbors.

No import of build_qa or its classifiers/vectorizers. TF-IDF constructed directly
from counts; sklearn contributes only its documented fixed English stopword set.
"""
from __future__ import annotations
import collections, csv, hashlib, itertools, json, math, pathlib, re, sqlite3
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
HERE=pathlib.Path(__file__).resolve().parent;ATLAS=HERE.parents[2];REPO=ATLAS;Q=ATLAS/'research/expansion/qa'
rows=json.loads((Q/'qa-candidates.json').read_text())['records'];summary=json.loads((Q/'summary.json').read_text());checks=[]
def check(ok,label,actual=None,expected=None):checks.append({'check':label,'passed':bool(ok),'actual':actual,'expected':expected})
def eq(a,b,label):check(a==b,label,a,b)
def norm(t):return ' '.join(re.findall(r'[a-z0-9]+',t.casefold()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_files=sorted((REPO/'data/digests').glob('*.json')); expected=[]
for p in source_files:
 s=json.loads(p.read_text());expected.extend((f"qa-{s['video_id']}-{i:03d}",s['video_id'],i,p,x) for i,x in enumerate(s.get('qa_topics',[])))
eq(len(rows),len(expected),'all digest pairs retained');eq(len({x['id'] for x in rows}),len(rows),'candidate IDs unique')
for row,(id,vid,i,p,src) in zip(rows,expected):
 eq(row['id'],id,'source id '+id);eq(row['question'],src['question'].strip(),'question exact digest join '+id);eq(row['answerGist'],src['answer_gist'].strip(),'answer exact digest join '+id);eq(row['sourcePointer'],f'/qa_topics/{i}','source pointer '+id);eq(row['sourceSha256'],sha(p),'source hash '+id)
 check(row['speakerVerified'] is False and row['humanReviewed'] is False and row['timestampSeconds'] is None and row['entityIsSpeaker'] is None,'unverified speech fields '+id)
 eq(row['evidenceType'],'ai_digest_paraphrase','candidate provenance '+id)
counts={'digestVideos':len(source_files),'videosWithQACandidates':len({x['videoId'] for x in rows}),'qaCandidates':len(rows),'practitionersWithQA':len({p for x in rows for p in x['practitionerNames']}),'publishingAccountsWithQA':len({x['publisherId'] for x in rows if x['publisherId'] is not None}),'candidatesWithoutResolvedPublisherId':sum(x['publisherId'] is None for x in rows)}
for k,v in counts.items():eq(summary['coverage'][k],v,k)
code=json.loads((Q/'codebook.json').read_text())
for t in code['themes']:
 regex=re.compile(t['regex'],re.I);q=sum(bool(regex.search(x['question'])) for x in rows);a=sum(bool(regex.search(x['answerGist'])) for x in rows);either=sum(bool(regex.search(x['question'])) or bool(regex.search(x['answerGist'])) for x in rows);actual=next(x for x in summary['themes'] if x['id']==t['id'])
 for k,v in [('questionCount',q),('answerCount',a),('eitherCount',either)]:eq(actual[k],v,'theme '+t['id']+' '+k)
families=collections.defaultdict(list)
for x in rows:families[norm(x['question'])].append(x)
eq(summary['coverage']['distinctNormalizedQuestions'],len(families),'normalized question count');eq(summary['coverage']['repeatedNormalizedQuestions'],sum(len(v)>1 for v in families.values()),'repeated question families')
# Explicit smooth-IDF/sublinear TF/L2 word+bigram transform.
def tfidf(texts):
 docs=[];df=collections.Counter()
 for txt in texts:
  words=[w for w in re.findall(r'(?u)\b\w\w+\b',txt.lower()) if w not in ENGLISH_STOP_WORDS];terms=words+[' '.join(x) for x in zip(words,words[1:])];c=collections.Counter(terms);docs.append(c);df.update(c.keys())
 vocab={term:i for i,term in enumerate(sorted(df))};rr=[];cc=[];vv=[]
 for i,c in enumerate(docs):
  weights={term:(1+math.log(tf))*(math.log((1+len(docs))/(1+df[term]))+1) for term,tf in c.items()};length=math.sqrt(sum(w*w for w in weights.values()))
  for term,w in weights.items():rr.append(i);cc.append(vocab[term]);vv.append(w/length if length else 0)
 return csr_matrix((vv,(rr,cc)),shape=(len(docs),len(vocab)))
qm=tfidf([x['question'] for x in rows]);am=tfidf([x['answerGist'] for x in rows]);qs=(qm@qm.T).toarray();asims=(am@am.T).toarray();selected=[]
for i,j in itertools.combinations(range(len(rows)),2):
 if rows[i]['videoId']!=rows[j]['videoId'] and qs[i,j]>=.4:selected.append((rows[i]['id'],rows[j]['id'],round(float(qs[i,j]),6),round(float(asims[i,j]),6)))
actual=json.loads((Q/'question-pairs.json').read_text())['records'];lookup={(x['leftId'],x['rightId']):x for x in actual}
eq(len(actual),len(selected),'lexical pairs >=.40');eq(set(lookup),{(a,b) for a,b,_,_ in selected},'lexical pair membership')
for a,b,q,a_cos in selected:
 x=lookup[a,b];check(abs(x['questionCosine']-q)<1.1e-6,'question cosine '+a+' '+b,x['questionCosine'],q);check(abs(x['answerCosine']-a_cos)<1.1e-6,'answer cosine '+a+' '+b,x['answerCosine'],a_cos);eq(x['answerAgreement'],'not_assessed','agreement boundary '+a+' '+b)
# Threshold-grid and upload-pair concentration independently from recreated pairs.
by_id={x['id']:x for x in rows};paircounts=collections.Counter(tuple(sorted((by_id[a]['videoId'],by_id[b]['videoId']))) for a,b,q,a_cos in selected)
for threshold in summary['sensitivity']['retrievalThresholds']:
 t=threshold['minimumQuestionCosine'];subset=[(a,b) for a,b,q,a_cos in selected if q>=t];eq(threshold['candidatePairs'],len(subset),'retrieval threshold count '+str(t));eq(threshold['distinctUploadPairs'],len({tuple(sorted((by_id[a]['videoId'],by_id[b]['videoId']))) for a,b in subset}),'retrieval threshold upload-pairs '+str(t))
con=summary['sensitivity']['uploadPairConcentration'];top3=sum(sorted(paircounts.values(),reverse=True)[:3]);eq(con['distinctUploadPairs'],len(paircounts),'retrieval distinct upload-pairs');eq(con['totalQuestionPairs'],len(selected),'retrieval question pairs');eq(con['topThreeUploadPairCandidateMatches'],top3,'top3 upload-pair matches');check(abs(con['topThreeUploadPairShare']-top3/len(selected))<1e-6,'top3 upload-pair share');eq(len(summary['questionPairs']),min(100,len(selected)),'summary preview distinct from full pair denominator')
# CSV explicitly preserves false and unknown timestamp semantics.
with (Q/'qa-candidates.csv').open(newline='') as f:csvrows=list(csv.DictReader(f))
eq(len(csvrows),len(rows),'CSV all rows');check(all(x['speakerVerified']=='false' and x['humanReviewed']=='false' for x in csvrows),'CSV false flags explicit');check(all(x['timestampSeconds']=='' and x['entityIsSpeaker']=='' for x in csvrows),'CSV unknown speech fields blank, not zero')
# Paired close reading follows its purposive top-ranked selection; meanings remain model outputs.
paired=json.loads((Q/'pair-close-reading.json').read_text());selected_ranked=sorted(selected,key=lambda p:(-p[2],p[0],p[1]));seen=set();expected_paired=[]
for a,b,q,ac in selected_ranked:
 text=by_id[a]['question']
 if text in seen:continue
 seen.add(text);expected_paired.append((a,b))
 if len(expected_paired)==12:break
eq([(x['leftId'],x['rightId']) for x in paired['records']],expected_paired,'12 paired close reading declared selection');check(paired['humanReview'] is False,'paired close reading nonhuman label')
for x in paired['records']:
 check(x['classification']['humanValidated'] is False and x['classification']['answerAgreement']=='undetermined','paired interpretation unresolved '+x['leftId'])
 for side,key in [('left','leftId'),('right','rightId')]:
  original=by_id[x[key]]
  for field in ['sourceUrl','sourcePath','sourceSha256','sourcePointer']:eq(x[side+'Source'][field],original[field],'paired source '+x[key]+' '+field)
source_manifest=json.loads((Q/'source-manifest.json').read_text())['records'];eq(len(source_manifest),len(source_files),'manifest all digests')
for s in source_manifest:eq(sha(REPO/s['sourcePath']),s['sourceSha256'],'manifest hash '+s['videoId'])
review=json.loads((Q/'close-reading.json').read_text());ids=[x['id'] for x in rows];first=[]
for vid,g in itertools.groupby(rows,key=lambda x:x['videoId']):first.append(next(g)['id'])
expected_review=[first[round(i*(len(first)-1)/19)] for i in range(20)]
eq([x['candidateId'] for x in review['records']],expected_review,'close reading declared deterministic subset');check(all(x['candidateId'] in ids for x in review['records']),'close reading valid IDs')
db=sqlite3.connect('file:'+str(Q/'qa-candidates.sqlite')+'?mode=ro',uri=True)
eq(db.execute('PRAGMA integrity_check').fetchone()[0],'ok','SQLite integrity');eq(db.execute('PRAGMA foreign_key_check').fetchall(),[],'SQLite foreign keys')
for table,n in [('sources',len(source_files)),('qa_candidates',len(rows)),('question_pairs',len(actual)),('model_close_reading',20),('practitioner_coverage',106)]:eq(db.execute('SELECT count(*) FROM '+table).fetchone()[0],n,'SQLite rows '+table)
eq(db.execute('SELECT count(*) FROM qa_candidates WHERE speaker_verified!=0 OR human_reviewed!=0 OR timestamp_seconds IS NOT NULL OR entity_is_speaker IS NOT NULL').fetchone()[0],0,'SQLite speech evidence boundaries');db.close()
failed=[x for x in checks if not x['passed']];report={'status':'PASS' if not failed else 'FAIL','checks':len(checks),'failures':failed,'role':'AI independent methods reviewer; no human validity inference','summarySha256':sha(Q/'summary.json'),'candidatesSha256':sha(Q/'qa-candidates.json'),'pairsSha256':sha(Q/'question-pairs.json'),'sqliteSha256':sha(Q/'qa-candidates.sqlite'),'producerSha256':sha(Q/'build_qa.py'),'independence':'No producer import. Source joins checked against all original digest fields. Regex reexecuted from released codebook. TF-IDF constructed from explicit counts, smooth IDF, sublinear TF and L2 normalization, not TfidfVectorizer.','all_checks':checks,'limitations':['Verifies digest-derived extraction and arithmetic, not original transcript fidelity, question completeness, speaker identity or meaning.','Only one inherited practitioner context; no cross-medium comparison.','Pairs can reuse original sessions; neither question nor answer cosine measures agreement.']}
(HERE/'independent-qa-verification.json').write_text(json.dumps(report,indent=2,default=lambda x:sorted(x) if isinstance(x,set) else str(x)));print(json.dumps({k:report[k] for k in ['status','checks','failures']},indent=2));raise SystemExit(bool(failed))
