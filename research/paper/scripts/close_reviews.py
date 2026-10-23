"""Bind completion to actual review receipts and preserved snapshots."""
from pathlib import Path
import json, hashlib
r=Path(__file__).resolve().parents[3];p=r/'research/paper'
paths=['reviews/corpus/round6-review.json','reviews/design/round6-final.json','reviews/method/round6-final-receipt.json','reviews/provenance/round6-review.json','reviews/implementation/round6-pdf-review.json','literature/round6-review-receipt.json']
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
pdfhash=sha(p/'rounds/round6/main.pdf')
receipts=[]
for f in paths:
    b=(p/f).read_bytes();assert pdfhash in b.decode(),f
    receipts.append({'path':f,'sha256':sha(p/f)})
for n in [4,5,6]:
    m=json.loads((p/f'rounds/round{n}/manifest.json').read_text())['files']
    pairs=m.items() if isinstance(m,dict) else ((x['path'],x['sha256']) for x in m)
    for f,h in pairs:assert sha(p/f'rounds/round{n}'/f)==h,(n,f)
ledger={'status':'completed','asOf':'2026-10-23','rounds':[
 {'round':4,'summary':'Full draft, expanded literature and generated diagnostics; source/method/corpus/provenance/design reviews identified corrections.','pdfSha256':sha(p/'rounds/round4/main.pdf')},
 {'round':5,'summary':'Corrected figures, precise methods and literature; actual pooling experiment; six workstream reviews; two minor fixes queued.','pdfSha256':sha(p/'rounds/round5/main.pdf')},
 {'round':6,'summary':'Two final prose/bibliography fixes, frozen PDF, six completed workstream checks, isolated offline and package compilation checks.','pdfSha256':pdfhash}],
 'finalReceipts':receipts,'allSnapshotFileHashesVerified':True,
 'additionalChecks':['reviews/implementation/round6-offline-reproduction.json','reviews/overleaf-build-check.json','reviews/browser-integration.json'],
 'disclosure':'Differentiated model-agent reviews; not independent human expert review or human construct validation.',
 'provenanceP16Closure':'Coordinator verified all six actual final receipts against the delivered PDF hash; completed-tense manuscript review disclosure is now supported.'}
(p/'reviews/coordinator-completion.json').write_text(json.dumps(ledger,indent=2)+'\n')
d=json.loads((p/'protocol.json').read_text());d['status']='reviewed_working_manuscript';d['rounds'][2]['state']='completed';d['rounds'][2]['pdfSha256']=pdfhash;d['completionLedger']='reviews/coordinator-completion.json';d['delivery']={'paper':'dist/analysis/channeling-atlas-paper.pdf','overleaf':'dist/analysis/channeling-atlas-overleaf.zip','sourceRegisterEntries':28,'citedReferences':23,'physicalPages':12,'referencesEndPage':11};(p/'protocol.json').write_text(json.dumps(d,indent=2)+'\n')
a=r/'research/analysis/protocol.json';d=json.loads(a.read_text());d['nextPhase']['state']='completed';d['nextPhase']['completionLedger']='research/paper/reviews/coordinator-completion.json';a.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'finalReceipts':len(receipts),'allSnapshotHashesVerified':True,'pdfSha256':pdfhash}))
