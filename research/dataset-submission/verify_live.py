#!/usr/bin/env python3
"""Check the deployed manifest and every named artifact against the local release."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen

def digest(raw): return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site',type=Path,required=True);p.add_argument('--base-url',required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    root=a.site/'dist/dataset-submission';local=(root/'manifest.json').read_bytes()
    manifest=json.loads(local);base=a.base_url.rstrip('/')+'/'
    def fetch(name):
        request=Request(base+quote(name,safe='/'),headers={'User-Agent':'ChannelingAtlas-ReleaseVerification/1.0','Cache-Control':'no-cache'})
        with urlopen(request,timeout=60) as r:
            if r.status!=200: raise ValueError('Unexpected HTTP status')
            return r.read()
    remote=fetch('manifest.json')
    if remote!=local: raise ValueError('Live manifest differs from reviewed local release')
    def check(ref):
        name=ref['file'];path=Path(name)
        if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name: raise ValueError('Unsafe release path')
        raw=fetch(name)
        if len(raw)!=ref['bytes'] or digest(raw)!=ref['sha256']: raise ValueError('Live artifact mismatch: '+name)
        return {'file':name,'bytes':len(raw),'sha256':digest(raw),'verified':True}
    with ThreadPoolExecutor(max_workers=4) as pool: artifacts=list(pool.map(check,manifest['artifacts']))
    result={'status':'verified_live_bytes','checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'base_url':base,'manifest_sha256':digest(remote),'artifacts':artifacts,
            'count':len(artifacts),'bytes':sum(r['bytes'] for r in artifacts)}
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='artifacts'}))

if __name__=='__main__':main()
