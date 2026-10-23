import json,re,hashlib,pathlib,collections,sys
base=pathlib.Path('/workspace/scratch/9ec421627a96/analysis_work/corpus');p=pathlib.Path('/workspace/sites/channeling-atlas/dist/analysis/data.json');d=json.loads(p.read_text());issues=[];checks=0
for r in d['transcripts']['rows']:
 srcpath=base/(r['videoId']+'.transcript.json');src=json.loads(srcpath.read_text());texts=[s['text'] for s in src['segments']]
 variants={'space':' '.join(texts),'newline':'\n'.join(texts),'collapse':re.sub(r'\s+',' ',' '.join(texts)).strip()}
 matches=[(k,t) for k,t in variants.items() if hashlib.sha256(t.encode()).hexdigest()==r['textSha256']];checks+=2
 if hashlib.sha256(srcpath.read_bytes()).hexdigest()!=r['captionArtifactSha256']:issues.append('sourcefilehash:'+r['videoId'])
 if not matches:issues.append('analysistexthash:'+r['videoId']);continue
 k,t=matches[0];n=len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",t));checks+=1
 if n!=r['wordCount']:issues.append({'id':r['videoId'],'field':'words','actual':r['wordCount'],'expected':n})
 for topic in d['topics']:
  actual=next(x for x in r['topics'] if x['id']==topic['id']);count=len(re.findall(topic['regex'],t,re.I));checks+=2
  if count!=actual['count']:issues.append({'id':r['videoId'],'topic':topic['id'],'field':'count','actual':actual['count'],'expected':count})
  if abs(actual['per1000Words']-count/n*1000)>1e-6:issues.append({'id':r['videoId'],'topic':topic['id'],'field':'rate'})
r={'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checks':checks,'issues':issues,'status':'PASS' if not issues else 'FAIL','definition':'Exact caption artifact and normalized analysis-text hashes; declared contraction-preserving alphabetic tokenizer; independent topic regex counts and per1000 rates.'}
pathlib.Path('/workspace/scratch/9ec421627a96/analysis_work/panel/final-caption-review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));sys.exit(bool(issues))
