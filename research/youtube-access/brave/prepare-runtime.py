#!/usr/bin/env python3
"""Fetch one official, checksum-pinned Brave package without system installation."""
import hashlib,json,os,subprocess,ssl,urllib.request
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNTIME=Path('/workspace/channels-et-brave-runtime')
URL='https://github.com/brave/brave-browser/releases/download/v1.98.60/brave-browser_1.98.60_amd64.deb'
EXPECTED_SHA='812a001d7631b5ab49e55dec6148a0bc2d459e9fc03106c286295ee03fd062fc'
EXPECTED_BYTES=153190012

def main():
    if not(os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')):
        raise SystemExit('Inherited session proxy required; do not use a direct external route')
    RUNTIME.mkdir(exist_ok=True,mode=0o700)
    asset=RUNTIME/'brave-browser_1.98.60_amd64.deb'
    receipt={'schemaVersion':1,'checkedAt':datetime.now(timezone.utc).isoformat(),
      'source':'official brave/brave-browser GitHub release v1.98.60',
      'sourceUrl':URL,'expectedBytes':EXPECTED_BYTES,'expectedSha256':EXPECTED_SHA,
      'proxy':'inherited session configuration','tlsVerificationEnabled':True,
      'systemInstallationPerformed':False,'runtimeOutsideRepository':True}
    if not asset.exists():
        temporary=asset.with_suffix('.partial')
        request=urllib.request.Request(URL,headers={'User-Agent':'channels-ET-official-browser-diagnostic/1.0'})
        with urllib.request.urlopen(request,timeout=180,context=ssl.create_default_context()) as response,temporary.open('wb') as output:
            receipt['httpStatus']=response.status
            while block:=response.read(1024*1024):output.write(block)
        temporary.rename(asset)
        receipt['downloadedThisRun']=True
    else:receipt['downloadedThisRun']=False
    receipt['bytes']=asset.stat().st_size
    receipt['sha256']=hashlib.file_digest(asset.open('rb'),'sha256').hexdigest()
    if receipt['bytes']!=EXPECTED_BYTES or receipt['sha256']!=EXPECTED_SHA:
        receipt['status']='checksum_or_size_mismatch'
        (HERE/'runtime-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        raise SystemExit('Official package checksum/size mismatch; no extraction or execution')
    extracted=RUNTIME/'extracted'
    extracted.mkdir(exist_ok=True)
    subprocess.run(['dpkg-deb','--extract',str(asset),str(extracted)],check=True)
    binary=extracted/'opt/brave.com/brave/brave'
    receipt['browserVersion']=subprocess.check_output([str(binary),'--version'],text=True).strip()
    receipt['packageMetadata']=subprocess.check_output(['dpkg-deb','--field',str(asset),'Package','Version','Architecture','Depends'],text=True).strip()
    deps=subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=True).stdout
    receipt['missingDynamicLibraries']=[x.strip()for x in deps.splitlines()if'not found'in x]
    receipt['status']='verified'if not receipt['missingDynamicLibraries']else'missing_dependencies'
    (HERE/'runtime-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    if receipt['missingDynamicLibraries']:raise SystemExit(1)

if __name__=='__main__':main()
