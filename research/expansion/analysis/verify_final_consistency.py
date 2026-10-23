#!/usr/bin/env python3
"""Bind final manuscript inputs and figure copies to verified analytical artifacts."""
import hashlib, json, pathlib, re, subprocess
HERE=pathlib.Path(__file__).resolve().parent;P=HERE.parent;ATLAS=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'paper/input-manifest.json').read_text());qa=json.loads((P/'qa/summary.json').read_text());result=json.loads((HERE/'results.json').read_text());pdf=P/'paper/channeling-atlas-expansion-paper.pdf';text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode();checks=[]
def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
for f,h in manifest['inputs'].items():check(sha(ATLAS/f)==h,'Paper input exact hash: '+f)
figure_hashes={}
for name in ['coverage','concentration','caption-selection','keyword-duration','publisher-similarity','negative-control']:
    src=HERE/'generated/figures'/f'{name}.pdf';dst=P/'paper/generated/figures'/f'{name}.pdf'
    check(src.read_bytes()==dst.read_bytes(),'Paper authoritative figure copy: '+name);figure_hashes[name]=sha(src)
for row in qa['sensitivity']['retrievalThresholds']:
    pattern=rf"{row['minimumQuestionCosine']:.2f}\s+{row['candidatePairs']}\s+{row['distinctUploadPairs']}"
    check(re.search(pattern,text) is not None,'Rendered PDF exact threshold row: '+str(row['minimumQuestionCosine']))
for pattern,label in [(r'11 same-publisher and 289 different-publisher','Matched pair denominators'),(r'11 eligible focal publishers','Equal-account eligibility'),(r'0\.121[–-]0\.179','Caption omission range'),(r'not confidence intervals','Influence range qualification'),(r'not a population p-value','Permutation scope'),(r'30 matches \(23\.6%\)','Upload-pair concentration'),(r'100 of the 127 retained pairs','Preview/full denominator distinction'),(r'0\.154 for captions and 0\.229 for titles','Matched pooled separation'),(r'no caption-\s*selection resampling','Selection deterministic method')]:check(re.search(pattern,text) is not None,'Rendered PDF: '+label)
check(sha(HERE/'results.json')=='97e4afb15e07cbaf8bca90cd8f1b125af41197c284fa613b0250aead6a4bc216','Analytics numeric results unchanged since reviewed first candidate')
out={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'details':checks,'inputs':{f:sha(P/f) for f in ['analysis/results.json','qa/summary.json','qa/question-pairs.json','qa/qa-candidates.csv','paper/channeling-atlas-expansion-paper.pdf','paper/input-manifest.json']},'figurePdfHashes':figure_hashes,'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL'}
(HERE/'generated/final-source-consistency.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['details','figurePdfHashes']}));raise SystemExit(out['status']!='PASS')
