#!/usr/bin/env python3
"""Verify released round-12 outputs without weights, Torch or neural replay."""
import collections,hashlib,json,pathlib,re,zipfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(name):return json.loads((HERE/name).read_text())
def sha(name):return hashlib.sha256((HERE/name).read_bytes()).hexdigest()
def main():
 checks=0
 def check(ok,msg):
  nonlocal checks
  checks+=1
  if not ok:raise AssertionError(msg)
 original=read('content-label-predictions.json')['records'];order=read('option-order-predictions.json')['records'];modern=read('qwen35-content-label-predictions.json')['records']
 op=read('option-order-protocol.json');os=read('option-order-results.json');mp=read('qwen35-content-label-protocol.json');ms=read('qwen35-content-label-results.json');lex=read('conditional-lexicon-sensitivity.json');comparison=read('annotation-comparison.json')
 check([r['id'] for r in original]==[r['id'] for r in order]==[r['id'] for r in modern], 'All three conditions use the exact same ordered twelve IDs')
 check(op['originalPredictionsSha256']==sha('content-label-predictions.json')==mp['originalPredictionsSha256'],'Original annotation bytes unchanged')
 check(op['reversedSystemPrompt'].replace('unclear, other, cosmology, personal_practice, or contact_forecast','contact_forecast, personal_practice, cosmology, other, or unclear')==op['originalSystemPrompt'],'Only theme order changes')
 check(mp['systemPrompt']==op['originalSystemPrompt'],'Current family receives exact original system prompt')
 check(op['generation']['maxNewTokens']==mp['maxNewTokens']==96 and not mp['doSample'] and not mp['enableThinking'],'Same budget/greedy sampling with explicit thinking mode')
 for old,rev,new in zip(original,order,modern):
  for row in [rev,new]:
   check(all(row[k]==old[k] for k in ['id','videoId','sourceGroupId','sourceUrl','sourceSha256','sourcePointer','question','answerGist']),'Same source text/provenance')
  for row,parsed_key,raw_key,valid_key in [(rev,'reversedParsed','reversedRawOutput','reversedEvidenceSpanExactAndShort'),(new,'parsed','rawModelOutput','evidenceSpanExactAndShort')]:
   parsed=row[parsed_key]
   if parsed:
    match=re.search(r'\{.*\}',row[raw_key],re.S);check(json.loads(match.group(0))==parsed,'Raw JSON matches parsed output')
    check(row[valid_key]==bool(parsed['evidence'] and parsed['evidence'] in row['answerGist'] and len(parsed['evidence'].split())<=8),'Exact source/length criterion')
   else:check(bool(row['parseError']),'Parse failure retained')
   check(row['generatedTokens']<=96 and row['humanReviewed'] is False,'Output cap and no human labels')
 paired=[r for r in order if r['originalParsed'] and r['reversedParsed']]
 check(os['pairedParsedRecords']==len(paired)==8,'Paired parse denominator')
 check(os['pairedThemeChangedCount']==sum(r['originalParsed']['theme']!=r['reversedParsed']['theme'] for r in paired)==6,'Paired change count')
 check(os['reversedFirstOptionCount']==sum(r['reversedParsed'] and r['reversedParsed']['theme']=='unclear' for r in order if r['reversedParsed'])==0,'No reversed first-option choices')
 check(os['reversedThemeCounts']==dict(collections.Counter(r['reversedParsed']['theme'] for r in order if r['reversedParsed'])),'Reversed theme counts')
 source=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records']
 old_count=sum(bool(re.search(lex['originalRegex'],r['answerGist'],re.I)) for r in source);new_count=sum(bool(re.search(lex['stricterRegex'],r['answerGist'],re.I)) for r in source)
 check(old_count==lex['originalConditionalCount']==60 and new_count==lex['stricterConditionalCount']==58,'Replay both regex strings across949 sources')
 changed=[r for r in source if bool(re.search(lex['originalRegex'],r['answerGist'],re.I))!=bool(re.search(lex['stricterRegex'],r['answerGist'],re.I))]
 check([r['id'] for r in changed]==[r['id'] for r in lex['changedRecords']] and len(changed)==2,'Changed lexical candidates')
 check(ms['parsedRecords']==12 and ms['parseFailures']==0,'Current-family parse denominators')
 check(ms['sourceSpanExactAndShortCount']==sum(r['evidenceSpanExactAndShort'] for r in modern)==5,'Current-family combined span criterion')
 check(ms['conditionalMethodAgreementCount']==sum(r['parsed']['conditional']==r['dictionaryConditional'] for r in modern)==6,'Current-family method concordance')
 check(all(r['parsed']['conditional']=='yes' for r in modern),'Current-family all-yes pattern disclosed')
 for condition,binding in zip(comparison['conditions'],comparison['sourceBindings']):
  check(sha(binding['file'])==binding['sha256'],'Annotation-comparison source binding')
  check(condition['maxNewTokens']==96,'Annotation budget is96, not QA40')
 newer=next(c for c in comparison['conditions'] if c['id']=='qwen35_original')
 check(newer['sourceSpanExactCount']==10 and newer['sourceSpanExactButOverLengthCount']==5 and newer['sourceSpanNonexactCount']==2,'Exactness/overlength disaggregation')
 check(newer['conditionalAlwaysYesBaselineAgreementCount']==newer['conditionalMethodAgreementCount']==6,'Always-yes baseline equals current concordance')
 package=read('adapter-package.json')
 check(sha(package['archive'])==package['sha256'],'Released ZIP hash')
 with zipfile.ZipFile(HERE/package['archive']) as z:
  for file in package['files']:check(hashlib.sha256(z.read(file['file'])).hexdigest()==file['sha256'],'Released ZIP member hash')
  training=read('training-receipt.json');weight=next(f for f in training['adapterFiles'] if f['name']=='adapter_model.safetensors')
  check(hashlib.sha256(z.read('adapter_model.safetensors')).hexdigest()==weight['sha256'],'Released weights equal trained adapter')
  manifest=json.loads(z.read('training-source-manifest.json'))
  check(manifest['splitSha256']==sha('split.json') and manifest['protocolSha256']==sha('protocol.json'),'Released training source pins')
 smoke=read('current-family-smoke.json');model=read('qwen35-manifest.json')
 check(smoke['revision']==model['revision']==mp['revision']==ms['revision'],'Current-family revision pin')
 check(smoke['status']=='completed' and smoke['schemaInstructionFollowed'] and not smoke['imageOrVideoInputUsed'],'Actual text-only smoke receipt retained')
 initial=read('full-verification-round10.json')
 check(initial['predictionsSha256']==sha('predictions.json') and initial['benchmarkResultsSha256']==sha('benchmark-results.json'),'Primary50 predictions/metrics unchanged')
 receipt={'status':'PASS','checks':checks,'verificationMode':'released-source-only; no neural inference replay',
  'primary50Unchanged':True,'original12AnnotationBytesUnchanged':True,'reversedPairedParsedN':len(paired),'reversedPairedChanged':6,
  'currentFamilyParseN':12,'currentFamilyExactSpans':10,'currentFamilyExactShortSpans':5,'alwaysYesConditionalConcordanceCount':6,
  'modelRevision':model['revision'],'adapterZipSha256':package['sha256'],'humanAccuracyValidated':False,'stateOfTheArtEstablished':False,
  'bindings':{name:sha(name) for name in ['option-order-results.json','conditional-lexicon-sensitivity.json','qwen35-content-label-results.json','annotation-comparison.json','current-family-smoke.json']}}
 (HERE/'round12-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
