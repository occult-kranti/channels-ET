#!/usr/bin/env python3
"""Source-only audit of local-model annotation and post-hoc diagnostics."""
import collections,hashlib,json,pathlib,re
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def words(s):return collections.Counter(re.findall(r'[a-z0-9]+',s.lower()))
def f1(a,b):
 x,y=words(a),words(b);return 2*sum((x&y).values())/(sum(x.values())+sum(y.values())) if x and y else 0.
def main():
 checks=0
 def check(ok,msg):
  nonlocal checks
  checks+=1
  if not ok:raise AssertionError(msg)
 source={r['id']:r for r in json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records']}
 split=json.loads((HERE/'split.json').read_text());train={r['id']:r for r in split['train']}
 rows=json.loads((HERE/'content-label-predictions.json').read_text())['records'];summary=json.loads((HERE/'content-label-results.json').read_text());diag=json.loads((HERE/'posthoc-diagnostics.json').read_text());base=json.loads((HERE/'predictions.json').read_text())['records']
 check(len(rows)==12 and len({r['sourceGroupId'] for r in rows})==12,'Twelve excerpts from distinct proxy groups')
 check(sum(r['dictionaryConditional']=='yes' for r in rows)==6,'Fixed balanced dictionary-conditional selection')
 for row in rows:
  original=source[row['id']]
  check(row['question']==original['question'] and row['answerGist']==original['answerGist'],'Exact source excerpts')
  check(row['sourceSha256']==original['sourceSha256'] and row['sourcePointer']==original['sourcePointer'],'Source hash/pointer')
  check(row['sourceGroupId']==split['videoGroupMap'][row['videoId']],'Source group join')
  parsed=row['parsed']
  if parsed:
   match=re.search(r'\{.*\}',row['rawModelOutput'],re.S);check(json.loads(match.group(0))==parsed,'Parsed JSON equals raw model text')
   exact=bool(parsed['evidence'] and parsed['evidence'] in row['answerGist'] and len(parsed['evidence'].split())<=8)
   check(exact==row['evidenceSpanExactAndShort'],'Evidence span validity is literal-source check')
   check(row['conditionalMethodAgreement']==(parsed['conditional']==row['dictionaryConditional']),'Method concordance bookkeeping')
  else:check(bool(row['parseError']),'Parse failure retained')
 valid=[r for r in rows if r['parsed']]
 check(summary['parsedRecords']==len(valid) and summary['parseFailures']==len(rows)-len(valid),'Parse denominators')
 check(summary['conditionalMethodAgreementCount']==sum(r['conditionalMethodAgreement'] is True for r in rows),'Concordance numerator')
 check(summary['conditionalMethodAgreementDenominator']==len(valid),'Concordance denominator')
 check(summary['sourceSpanExactAndShortCount']==sum(r['evidenceSpanExactAndShort'] for r in rows),'Span count')
 check(summary['themeCounts']==dict(collections.Counter(r['parsed']['theme'] for r in valid)),'Theme-label collapse visible')
 for arm in diag['arms']:
  rr=[r for r in base if r['arm']==arm['arm']];controls=[r for r in rr if r['control']];qa=[r for r in rr if not r['control']]
  check(arm['strictMarkerCount']==sum(r['abstained'] for r in controls),'Primary strict marker count preserved')
  check(arm['posthocRefusalPhraseCount']==sum(bool(re.search(diag['refusalPhrasePattern'],r['output'],re.I)) for r in controls),'Posthoc phrase count')
  check(abs(arm['contentOnlyTokenF1']-sum(f1(re.sub(r'\[D\d+\]','',r['output']),r['referenceAnswerGist']) for r in qa)/len(qa))<1e-8,'Content-only score sensitivity')
 for control in diag['citationPositiveControls']:
  original=train[control['candidateId']]
  check(control['question']==original['question'] and control['suppliedAnswerGist']==original['answerGist'],'Positive control exact training source')
  check(control['heldoutEvaluation'] is False and control['entailmentHumanValidated'] is False,'Positive control cannot become heldout/human validation')
  check(control['validSourceLabelPresent']==('[D1]' in control['output']),'Positive control source-label parser')
 old=json.loads((HERE/'full-verification-round10.json').read_text())
 check(old['predictionsSha256']==hashlib.sha256((HERE/'predictions.json').read_bytes()).hexdigest(),'All primary predictions unchanged')
 check(old['benchmarkResultsSha256']==hashlib.sha256((HERE/'benchmark-results.json').read_bytes()).hexdigest(),'All primary metrics unchanged')
 receipt={'status':'PASS','checks':checks,'contentRecords':12,'parsed':len(valid),'parseFailures':len(rows)-len(valid),
          'contentSpanValidCount':sum(r['evidenceSpanExactAndShort'] for r in rows),'positiveCitationControlRecords':len(diag['citationPositiveControls']),
          'positiveControlValidCitationCount':sum(c['validSourceLabelPresent'] for c in diag['citationPositiveControls']),
          'primaryPredictionsUnchanged':True,'neuralInferenceReplayed':False,'humanAccuracyValidated':False,
          'contentResultsSha256':hashlib.sha256((HERE/'content-label-results.json').read_bytes()).hexdigest(),
          'diagnosticsSha256':hashlib.sha256((HERE/'posthoc-diagnostics.json').read_bytes()).hexdigest()}
 (HERE/'round11-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
