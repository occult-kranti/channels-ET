#!/usr/bin/env python3
"""Source-only, literal-span bookkeeping for the three executed annotation conditions."""
import hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def main():
 conditions=[];bindings=[];shared=None
 specs=[('qwen25_original','Qwen/Qwen2.5-0.5B-Instruct','content-label-predictions.json','parsed','original'),
        ('qwen25_reversed','Qwen/Qwen2.5-0.5B-Instruct','option-order-predictions.json','reversedParsed','reversed'),
        ('qwen35_original','Qwen/Qwen3.5-0.8B','qwen35-content-label-predictions.json','parsed','original')]
 for name,model,file,key,order in specs:
  path=HERE/file;rows=json.loads(path.read_text())['records'];ids=[r['id'] for r in rows]
  if shared is None:shared=ids
  assert ids==shared,'Same source excerpts/order required'
  valid=[r for r in rows if r[key]];exact=[r for r in valid if r[key]['evidence'] and r[key]['evidence'] in r['answerGist']]
  short=[r for r in valid if r[key]['evidence'] and len(r[key]['evidence'].split())<=8]
  both=[r for r in exact if len(r[key]['evidence'].split())<=8]
  def dictionary(r):return r.get('dictionaryConditional',r.get('originalDictionaryConditional'))
  yes=sum(r[key]['conditional']=='yes' for r in valid);always_yes=sum(dictionary(r)=='yes' for r in valid)
  agreement=sum(r[key]['conditional']==dictionary(r) for r in valid)
  conditions.append({'id':name,'model':model,'themeOptionOrder':order,'maxNewTokens':96,'n':len(rows),'parsedRecords':len(valid),'parseFailures':len(rows)-len(valid),
    'sourceSpanExactCount':len(exact),'sourceSpanAtMostEightWordsCount':len(short),'sourceSpanExactAndShortCount':len(both),
    'sourceSpanExactButOverLengthCount':len(exact)-len(both),'sourceSpanNonexactCount':len(valid)-len(exact),
    'conditionalYesCount':yes,'conditionalMethodAgreementCount':agreement,'conditionalParsedDenominator':len(valid),
    'conditionalAlwaysYesBaselineAgreementCount':always_yes,'conditionalAlwaysYesBaselineRate':always_yes/len(valid) if valid else None,
    'conditionalMethodAgreementRate':agreement/len(valid) if valid else None,'allParsedConditionalLabelsYes':yes==len(valid)})
  bindings.append({'file':file,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 result={'status':'completed_source_only_bookkeeping','conditions':conditions,'sameSourceIds':shared,'sourceBindings':bindings,
  'spanRule':'Nonempty case-sensitive contiguous substring of supplied answer gist; combined compliance additionally requires at most eight whitespace-separated words.',
  'conditionalReference':'Inherited unvalidated regex indicator, not human truth. Always-yes baseline uses the same parsed-row denominator.',
  'limitations':['Exact but overlength spans are length failures, not invented evidence.','The newer model and the original baseline both label every parsed conditional case yes; their concordance equals the always-yes baseline.',
    'Different architectures/tokenizers/runtimes prevent a parameter-scale-only causal interpretation.','Parsing and source-span compliance do not validate semantic labels, original speech or factual truth.']}
 (HERE/'annotation-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
