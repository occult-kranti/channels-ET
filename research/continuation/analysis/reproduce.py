#!/usr/bin/env python3
"""Regenerate numerical outputs in isolation and bind the generic receipt to now."""
import hashlib,json,pathlib,subprocess,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='channels-et-analysis-reproduction-') as scratch:
    other=pathlib.Path(scratch)
    subprocess.run([sys.executable,str(HERE/'analyze.py'),'--output',str(other)],check=True,capture_output=True,text=True)
    files=[]
    for p in sorted(other.rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(other);current=HERE/relative
        files.append({'path':str(relative),'sha256':sha(current) if current.exists() else None,'reproducedSha256':sha(p),'identical':current.exists() and current.read_bytes()==p.read_bytes()})
    status='PASS' if files and all(f['identical'] for f in files) else 'FAIL'
    receipt={'status':status,'scope':'Fresh temporary output directory; same source inputs and audited model receipts. No new model inference, training or acquisition.','pythonVersion':sys.version.split()[0],'currentResultsSha256':sha(HERE/'results.json'),'files':files}
    path=HERE/'generated/reproduction.json';path.write_text(json.dumps(receipt,indent=2))
    # The receipt itself is checked against every current output after writing.
    saved=json.loads(path.read_text());bound=saved['currentResultsSha256']==sha(HERE/'results.json') and all(f['sha256']==sha(HERE/f['path']) for f in saved['files'])
    if not bound:raise RuntimeError('Current output changed while the reproduction receipt was written')
    print(json.dumps({'status':status,'files':len(files),'currentResultsSha256':receipt['currentResultsSha256'],'currentBindingVerified':bound}))
    raise SystemExit(status!='PASS')
