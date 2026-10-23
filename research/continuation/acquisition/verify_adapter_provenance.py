#!/usr/bin/env python3
"""Independent local adapter release bindings; not model-quality evaluation."""
import datetime as dt
import hashlib
import json
import pathlib
import zipfile

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MODELS=ROOT/'research/continuation/models'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())

def main():
    checks=[]
    def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
    package=load(MODELS/'adapter-package.json')
    split=load(MODELS/'split.json');manifest=load(MODELS/'model-manifest.json')
    archive=MODELS/package['archive']
    check(sha(archive)==package['sha256'],'Actual adapter ZIP matches packaging receipt')
    with zipfile.ZipFile(archive) as z:
        check(sum(i.file_size for i in z.infolist())<32*1024**2,'Uncompressed adapter archive below32MiB inspection budget')
        for r in package['files']:
            info=z.getinfo(r['file'])
            check(info.file_size<=16*1024**2,'Member bounded for local inspection:'+r['file'])
            if info.file_size<=16*1024**2:check(hashlib.sha256(z.read(r['file'])).hexdigest()==r['sha256'],'Member SHA256:'+r['file'])
        check(set(z.namelist())=={r['file'] for r in package['files']},'No unmanifested archive members')
        check('NOTICE.txt' in z.namelist() and 'training-source-manifest.json' in z.namelist(),'Source/license notice and training bindings included')
        source_bytes=z.read('training-source-manifest.json')
        source=json.loads(source_bytes)
        config=json.loads(z.read('adapter_config.json'))
        license_bytes=z.read('LICENSE.txt')
    check(config['base_model_name_or_path']==manifest['model']==package['baseModel'],'Base identifier consistent across package/config/model manifest')
    check(config['revision']==manifest['revision']==package['baseRevision'],'Exact base revision consistent across package/config/model manifest')
    license_record=next(r for r in manifest['files'] if r['file']=='LICENSE')
    check(hashlib.sha256(license_bytes).hexdigest()==license_record['sha256'],'Bundled base Apache license bytes match verified model manifest')
    check(source['splitSha256']==sha(MODELS/'split.json'),'Bundled training source manifest binds exact split')
    check(source['protocolSha256']==sha(MODELS/'protocol.json'),'Bundled training source manifest binds exact protocol')
    check(source['sourceQaSha256']==split['sourceQaSha256']==sha(ROOT/'research/expansion/qa/qa-candidates.json'),'Training source hash binds inherited candidate artifact')
    check([r['candidateId'] for r in source['train']]==[r['id'] for r in split['train']],'Training candidate IDs/order match split')
    check(len(source['train'])==48,'Pilot training manifest contains48 rows')
    for row in source['train']:
        path=(ROOT/row['sourcePath']).resolve()
        check(path.is_relative_to(ROOT.resolve()),'Source path remains within repository:'+row['candidateId'])
        if not path.is_relative_to(ROOT.resolve()):continue
        check(sha(path)==row['sourceSha256'],'Digest source hash:'+row['candidateId'])
        value=load(path)
        for token in row['sourcePointer'].lstrip('/').split('/'):
            token=token.replace('~1','/').replace('~0','~')
            value=value[int(token)] if isinstance(value,list) else value[token]
        check(isinstance(value,dict),'Digest JSON pointer resolves:'+row['candidateId'])
        check(not any(k in row for k in ['question','answer','answerGist','text','segments']),'Metadata-only source row:'+row['candidateId'])
    failures=[r['check'] for r in checks if not r['passed']]
    receipt={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL',
             'checks':len(checks),'failures':failures,'network_requests':0,'adapter_archive_sha256':sha(archive),
             'source_manifest_sha256':hashlib.sha256(source_bytes).hexdigest(),
             'basis':'Artifact bytes, declared licensing metadata and training-source bindings only; not quality, truth, human review or original speech rights validation.',
             'all_checks':checks}
    (HERE/'adapter-provenance-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='all_checks'}))
    return bool(failures)

if __name__=='__main__':raise SystemExit(main())
