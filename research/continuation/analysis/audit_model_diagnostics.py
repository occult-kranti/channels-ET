#!/usr/bin/env python3
"""Independent post-hoc metric and local structured-label diagnostics audit."""
import collections,hashlib,json,pathlib,random,re
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=ROOT/'research/continuation/models'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def score(a,b):
    A=collections.Counter(re.findall('[a-z0-9]+',a.lower()));B=collections.Counter(re.findall('[a-z0-9]+',b.lower()));return 2*sum((A&B).values())/(sum(A.values())+sum(B.values())) if A and B else 0.
def strip(s):return re.sub(r'\[D\d+\]','',s)
checks=[]
def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
def near(a,b,label):check(abs(a-b)<5.1e-7,label)
pred=json.loads((M/'predictions.json').read_text())['records'];post=json.loads((M/'posthoc-diagnostics.json').read_text());split=json.loads((M/'split.json').read_text());qa=json.loads((ROOT/'research/expansion/qa/qa-candidates.json').read_text())['records'];byid={r['id']:r for r in qa};train={r['id']:r for r in split['train']};test={r['id']:r for r in split['test']};pattern=post['refusalPhrasePattern'];armrows=[]
check(post['refusalPatternDefinedAfterInspectingOutputs'] is True,'Refusal diagnostic explicitly post-hoc')
for arm in post['arms']:
    pp=[p for p in pred if p['arm']==arm['arm']];cc=[p for p in pp if p['control']];qq=[p for p in pp if not p['control']];strict=sum('INSUFFICIENT_EVIDENCE' in p['output'].upper() for p in cc);phrase=sum(bool(re.search(pattern,p['output'],re.I)) for p in cc);content=float(np.mean([score(strip(p['output']),strip(p['referenceAnswerGist'])) for p in qq]));raw=float(np.mean([score(p['output'],p['referenceAnswerGist']) for p in qq]));cap=sum(p['generatedTokens']==40 for p in qq)
    check(strict==arm['strictMarkerCount'] and phrase==arm['posthocRefusalPhraseCount'],arm['arm']+' strict/posthoc phrase counts');near(content,arm['contentOnlyTokenF1'],arm['arm']+' citation-stripped overlap');near(raw,arm['originalMeanTokenF1'],arm['arm']+' raw score retained');check(cap==arm['qaGenerationCapHits'],arm['arm']+' generation censoring count');check(len(cc)==arm['controlN'] and len(qq)==arm['qaN'],arm['arm']+' separate denominators')
    armrows.append({'id':arm['arm'],'questions':len(qq),'controls':len(cc),'strictMarkerOutputs':strict,'posthocRefusalPhraseOutputs':phrase,'rawTokenF1':raw,'citationStrippedTokenF1':content,'generation40TokenCapHits':cap,'anyRetrievedEvidenceQuestions':sum(bool(p['retrievedEvidence']) for p in qq)})
positives=post['citationPositiveControls'];check(len(positives)==4,'Four answer-present positive outputs, two prompts × two arms');positive_rows=[]
for p in positives:
    check(p['candidateId'] in train and p['candidateId'] not in test,'Positive control is explicitly training source '+p['candidateId']);src=train[p['candidateId']];check(p['question']==src['question'] and p['suppliedAnswerGist']==src['answerGist'],'Positive source question/answer binding '+p['arm']+'/'+p['candidateId']);check(p['heldoutEvaluation'] is False and p['entailmentHumanValidated'] is False,'Positive task not relabeled heldout or human entailment');check(p['validSourceLabelPresent']==('[D1]' in p['output']),'Positive citation membership replay');near(score(strip(p['output']),strip(src['answerGist'])),p['tokenF1ToSuppliedGist'],'Positive content overlap replay');positive_rows.append({'arm':p['arm'],'candidateId':p['candidateId'],'labelPresent':p['validSourceLabelPresent'],'contentTokenF1':score(strip(p['output']),strip(src['answerGist']))})
lp=json.loads((M/'content-label-predictions.json').read_text())['records'];lr=json.loads((M/'content-label-results.json').read_text());protocol=json.loads((M/'content-label-protocol.json').read_text());groups=split['videoGroupMap'];selected=[];used=set();rng=random.Random(42)
for wanted in [True,False]:
    pool=sorted([r for r in qa if ('conditional' in r['answerModalityMarkers'])==wanted],key=lambda r:r['id']);rng.shuffle(pool);n=0
    for row in pool:
        g=groups[row['videoId']]
        if g in used:continue
        selected.append(row['id']);used.add(g);n+=1
        if n==6:break
check(selected==protocol['selectedIds']==[p['id'] for p in lp],'Independent balanced twelve-item selection');check(len({groups[p['videoId']] for p in lp})==12,'Twelve separate quarantine groups in local-label comparison');parsed_n=0;concord=0;theme_concord=0;exact_n=0;themes=collections.Counter();labelrows=[]
for p in lp:
    src=byid[p['id']];check(p['question']==src['question'] and p['answerGist']==src['answerGist'],'Local label source text '+p['id']);check(p['sourceSha256']==src['sourceSha256'] and p['sourcePointer']==src['sourcePointer'],'Local label digest provenance '+p['id']);parsed=None
    try:
        raw=p['rawModelOutput'];parsed=json.loads(raw[raw.find('{'):raw.rfind('}')+1]);assert parsed['theme'] in protocol['primaryThemes'] and parsed['conditional'] in protocol['conditionalLabels'] and isinstance(parsed['evidence'],str)
    except Exception:parsed=None
    check(parsed==p['parsed'],'Local raw-output parse replay '+p['id']);dictionary='yes' if 'conditional' in src['answerModalityMarkers'] else 'no';check(dictionary==p['dictionaryConditional'],'Local conditional reference is source heuristic '+p['id']);exact=bool(parsed and parsed['evidence'] and parsed['evidence'] in src['answerGist'] and len(parsed['evidence'].split())<=8);check(exact==p['evidenceSpanExactAndShort'],'Exact answer-only span requirement '+p['id']);exact_n+=exact
    if parsed:
        parsed_n+=1;concord+=parsed['conditional']==dictionary;themes[parsed['theme']]+=1;dt=set();original=set(src['answerThemes'])
        if original&{'contact','prediction'}:dt.add('contact_forecast')
        if original&{'excitement','belief','practice'}:dt.add('personal_practice')
        if 'consciousness' in original:dt.add('cosmology')
        if not dt:dt.add('other')
        theme_concord+=parsed['theme'] in dt;check(sorted(dt)==p['dictionaryThemeIndicators'],'Local overlapping theme heuristic '+p['id'])
    labelrows.append({'candidateId':p['id'],'parsed':parsed is not None,'modelTheme':parsed['theme'] if parsed else None,'dictionaryConditional':dictionary,'modelConditional':parsed['conditional'] if parsed else None,'exactAnswerSpan':exact})
check(parsed_n==lr['parsedRecords'] and len(lp)-parsed_n==lr['parseFailures'],'Label parsed/failure denominators');check(concord==lr['conditionalMethodAgreementCount'] and parsed_n==lr['conditionalMethodAgreementDenominator'],'Conditional method concordance denominator');check(theme_concord==lr['primaryThemeDictionaryConcordanceCount'] and dict(themes)==lr['themeCounts'],'Local theme collapse/concordance counts');check(exact_n==lr['sourceSpanExactAndShortCount'],'Exact span failure count')
files=['predictions.json','split.json','posthoc-diagnostics.json','content-label-predictions.json','content-label-results.json','content-label-protocol.json','run_round11_diagnostics.py','run_content_labels.py']
out={'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'inputs':{f:sha(M/f) for f in files},'metricSensitivity':armrows,'citationPositiveControls':{'outputs':len(positives),'distinctTrainingQuestions':len({p['candidateId'] for p in positives}),'sourceLabelsPresent':sum(p['validSourceLabelPresent'] for p in positives),'heldoutEvaluation':False,'rows':positive_rows},'localTextLabels':{'n':len(lp),'parsed':parsed_n,'parseFailures':len(lp)-parsed_n,'conditionalMethodConcordance':concord,'conditionalMethodDenominator':parsed_n,'themeDictionaryConcordance':theme_concord,'exactAnswerEvidenceSpans':exact_n,'parsedThemeCounts':dict(themes),'rows':labelrows},'limits':['The broader refusal pattern was defined after output inspection and is not human refusal or correctness annotation.','The positive-control source answers are intentionally supplied from training; their overlap/citation scores are not held-out generalization.','The twelve text-label examples are balanced on a dictionary heuristic; method concordance is not accuracy or corpus prevalence.','All nine parsed themes collapse to contact_forecast; do not use this failed probe as empirical theme distribution.','No exact answer evidence spans passed the specified source-substring rule.','Citation-stripped overlap preserves the original scores as separate metrics; no model parameters are optimized on this diagnostic.','Generation cap hits document censoring; no longer-budget generation experiment was executed.']}
(HERE/'model-diagnostics-audit.json').write_text(json.dumps(out,indent=2));main=json.loads((HERE/'results.json').read_text());main['modelDiagnosticsAudit']=out;(HERE/'results.json').write_text(json.dumps(main,ensure_ascii=False,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in out.items() if k not in ['inputs','metricSensitivity','citationPositiveControls','localTextLabels','limits']}));raise SystemExit(out['status']!='PASS')
