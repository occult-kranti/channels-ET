#!/usr/bin/env python3
"""Publish an exact local commit via GitHub's supported Git-data API.

Uses existing gh authentication, immutable object hashes and a non-forced ref
update. Does not read credentials or alter local commits/remotes. Default is
offline inspection; --publish performs the explicitly authorized publication.
"""
from pathlib import Path
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import subprocess
import tempfile

REPO = Path('/workspace/channels-ET')
API = 'repos/occult-kranti/channels-ET/git/'
STATE = Path('/workspace/setup-validation')

def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args])

def api(method, endpoint, body=None):
    with tempfile.TemporaryDirectory(prefix='github-object-request-',dir=STATE) as temp:
        command=['gh','api','--method',method,API+endpoint]
        if body is not None:
            path=Path(temp)/'request.json'
            path.write_text(json.dumps(body,ensure_ascii=False))
            command+=['--input',str(path)]
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode:
            # API error metadata only. No request content or credential is emitted.
            raise RuntimeError(f'GitHub {method} {endpoint} failed: '+result.stderr[:400])
        return json.loads(result.stdout)

def tree(commit):
    result={}
    for row in git('ls-tree','-r','-z',commit).split(b'\0'):
        if not row:continue
        header,name=row.split(b'\t',1)
        mode,kind,sha=header.decode().split()
        result[name.decode()]={'path':name.decode(),'mode':mode,'type':kind,'sha':sha}
    return result

def identity(value):
    match=re.fullmatch(r'(.*) <([^<>]+)> (\d+) ([+-]\d{4})',value)
    if not match:raise ValueError('Unsupported commit identity')
    name,email,seconds,offset=match.groups()
    shift=(int(offset[1:3])*60+int(offset[3:]))*(1 if offset[0]=='+' else -1)
    date=datetime.fromtimestamp(int(seconds),timezone(timedelta(minutes=shift))).isoformat()
    return {'name':name,'email':email,'date':date}

def inspect(commit):
    commit=git('rev-parse','--verify',commit+'^{commit}').decode().strip()
    raw=git('cat-file','commit',commit)
    assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==commit
    headers,message=raw.split(b'\n\n',1)
    values={}
    for line in headers.decode().splitlines():
        key,value=line.split(' ',1)
        if key not in ('tree','parent','author','committer'):raise ValueError('Signed/encoded/multiline commit requires a different transport')
        if key in values:raise ValueError('Only a single-parent commit is supported')
        values[key]=value
    base=values['parent']
    before,after=tree(base),tree(commit)
    edits=[row for name,row in after.items() if before.get(name)!=row]
    edits += [{'path':name,'mode':row['mode'],'type':row['type'],'sha':None} for name,row in before.items() if name not in after]
    if any(row['type']!='blob' or row['mode'] not in ('100644','100755') for row in edits):
        raise ValueError('Changed symlink/submodule or unexpected mode is outside this publication')
    body={'message':message.decode(),'tree':values['tree'],'parents':[base],
          'author':identity(values['author']),'committer':identity(values['committer'])}
    return commit,base,values['tree'],edits,body

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit',default='HEAD')
    p.add_argument('--publish',action='store_true')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--workers',type=int,choices=(1,2,3,4),default=4)
    args=p.parse_args()
    commit,base,target_tree,edits,commit_body=inspect(args.commit)
    report={'started_at':datetime.now(timezone.utc).isoformat(),'local_commit':commit,'base':base,
            'target_tree':target_tree,'changed_paths':len(edits),'mode':'publish' if args.publish else 'offline_inspection',
            'uploaded_blobs':[],'ref_updated':False,'credentials_read':False,'local_history_modified':False}
    receipt=STATE/('git-data-publish-'+commit+'.json')
    if not args.publish:
        print(json.dumps({k:v for k,v in report.items() if k!='uploaded_blobs'}));return
    if receipt.exists() and not args.resume:
        raise ValueError('Publication receipt already exists; use --resume to preserve its verified-object ledger')
    if args.resume:
        previous=json.loads(receipt.read_text())
        if previous['local_commit']!=commit or previous['target_tree']!=target_tree:
            raise ValueError('Resume receipt does not match the reviewed commit/tree')
        expected={row['sha'] for row in edits if row['sha'] is not None}
        if any(row['sha'] not in expected for row in previous['uploaded_blobs']):
            raise ValueError('Unexpected cached object identity')
        if previous.get('status') in ('published_exact_local_commit','already_published_exact_commit'):
            if api('GET','ref/heads/main')['object']['sha']!=commit:
                raise ValueError('Completed receipt preserved but remote changed; reconcile before a new publication')
            print(json.dumps({'status':'already_published_exact_commit','local_commit':commit,
                              'completed_receipt_preserved':True}));return
        report['uploaded_blobs']=previous['uploaded_blobs']
        report['prior_error']=previous.get('error')
        report['resumed_verified_objects']=len(previous['uploaded_blobs'])
    def checkpoint():receipt.write_text(json.dumps(report,indent=2)+'\n')
    checkpoint()
    try:
        remote=api('GET','ref/heads/main')['object']['sha']
        if remote==commit:
            report['status']='already_published_exact_commit';checkpoint();print(json.dumps(report));return
        if remote!=base:raise ValueError('Remote advanced; preserve local commits and reconcile before publication')
        blobs={row['sha'] for row in edits if row['sha'] is not None}-{row['sha'] for row in report['uploaded_blobs']}
        def upload(sha):
            body=git('cat-file','blob',sha)
            if len(body)>8*1024**2:raise ValueError('Unexpected object size; bounded uploader stopped')
            request={'encoding':'base64','content':base64.b64encode(body).decode()}
            try:
                text_request={'encoding':'utf-8','content':body.decode('utf-8')}
                if len(json.dumps(text_request,ensure_ascii=False).encode())<len(json.dumps(request).encode()):request=text_request
            except UnicodeDecodeError:pass
            response=api('POST','blobs',request)
            if response['sha']!=sha:raise ValueError('Uploaded blob identity mismatch')
            return {'sha':sha,'bytes':len(body)}
        errors=[]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks={pool.submit(upload,sha):sha for sha in sorted(blobs)}
            for task in as_completed(tasks):
                try:report['uploaded_blobs'].append(task.result());checkpoint()
                except Exception as error:errors.append(str(error))
        if errors:raise RuntimeError('; '.join(errors[:4]))
        response=api('POST','trees',{'base_tree':git('rev-parse',base+'^{tree}').decode().strip(),'tree':edits})
        if response['sha']!=target_tree:raise ValueError('Remote tree differs from the reviewed local tree')
        response=api('POST','commits',commit_body)
        report['created_commit']=response['sha'];checkpoint()
        if response['sha']!=commit:raise ValueError('API commit identity differs; main remains unchanged')
        if api('GET','ref/heads/main')['object']['sha']!=base:raise ValueError('Remote advanced during upload; no forced update')
        report['main_ref_write_attempted']=True;checkpoint()
        response=api('PATCH','refs/heads/main',{'sha':commit,'force':False})
        if response['object']['sha']!=commit:raise ValueError('Ref update response mismatch')
        report['ref_updated']=True
        if api('GET','ref/heads/main')['object']['sha']!=commit:raise ValueError('Final remote ref check differs')
        report['status']='published_exact_local_commit'
    except Exception as error:
        report['status']='stopped_check_recorded_ref_write_state';report['error']=str(error);raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat();checkpoint()
    print(json.dumps({k:v for k,v in report.items() if k!='uploaded_blobs'}))

if __name__=='__main__':main()
