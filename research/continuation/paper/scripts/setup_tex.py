#!/usr/bin/env python3
"""Prepare verified standard font dependencies in a local tree, not global TeX."""
import hashlib,json,os,pathlib,shutil,subprocess,urllib.request,zipfile

root=pathlib.Path('/workspace/channels-et-tex');tree=root/'texmf'
packages=[
 ('newtx.zip','fonts/newtx.zip','bbe07d4ad91ade9f61326e59f2f3bf389b4ace1c0c1ef2e8c85377e4e2535f4e'),
 ('mweights.zip','macros/latex/contrib/mweights.zip','635a099afeb4d8db63d073fd4d06c0a6cefcdb90cc2379a5e7211cf4cab7e831'),
 ('kastrup.zip','macros/generic/kastrup.zip','c3ec4e73ca69bc2f8e813c01618b670a936e24a465228ccf06b8c6ae28f7220e'),
 ('tex-gyre.zip','fonts/tex-gyre.zip','1773c470f9e388e087b68e3426e115af2cd236845a7e05ceb25b2a503409a7a3')]
archive_dir=root/'archives';archive_dir.mkdir(parents=True,exist_ok=True);receipts=[]
for name,path,expected in packages:
 archive=archive_dir/name
 if archive.exists():blob=archive.read_bytes()
 else:
  # Mirrors are standard CTAN distribution endpoints. Every artifact must match its pin.
  failure=None
  for prefix in ['https://mirrors.ctan.org/','https://mirror.clarkson.edu/ctan/','https://mirrors.mit.edu/CTAN/']:
   try:blob=urllib.request.urlopen(prefix+path,timeout=50).read();break
   except Exception as error:failure=error
  else:raise failure
 actual=hashlib.sha256(blob).hexdigest()
 if actual!=expected:raise ValueError(f'Checksum mismatch for {name}; verified dependencies must be restored before use')
 archive.write_bytes(blob);source=root/'source'/archive.stem;source.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for member in z.infolist():
   if not (source/member.filename).resolve().is_relative_to(source.resolve()):raise ValueError('Unsafe archive path')
  z.extractall(source)
 receipts.append({'name':name,'url':'https://mirrors.ctan.org/'+path,'sha256':actual,'bytes':len(blob)})
suffixes={'.sty':'tex/latex','.fd':'tex/latex','.tex':'tex/latex','.clo':'tex/latex','.tfm':'fonts/tfm','.vf':'fonts/vf','.pfb':'fonts/type1','.enc':'fonts/enc/dvips','.map':'fonts/map/dvips','.otf':'fonts/opentype','.afm':'fonts/afm'}
for package in (root/'source').iterdir():
 for item in package.rglob('*'):
  if item.is_file() and item.suffix.lower() in suffixes:
   dest=tree/suffixes[item.suffix.lower()]/package.name/item.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(item,dest)
ins=next((root/'source/kastrup').rglob('binhex.ins'))
subprocess.run(['tex','-interaction=nonstopmode',ins.name],cwd=ins.parent,check=True,stdout=subprocess.DEVNULL)
dest=tree/'tex/latex/kastrup/binhex.tex';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ins.parent/'binhex.tex',dest)
for directory in [root/'var',root/'config']:directory.mkdir(exist_ok=True)
env=dict(os.environ,TEXMFHOME=str(tree),TEXMFVAR=str(root/'var'),TEXMFCONFIG=str(root/'config'))
subprocess.run(['mktexlsr',str(tree)],env=env,check=True,stdout=subprocess.DEVNULL)
result=subprocess.run(['updmap-user','--enable','Map=newtx.map','--enable','Map=qtm.map'],env=env,capture_output=True,text=True)
(root/'updmap.log').write_text(result.stdout+result.stderr);result.check_returncode()
(root/'download-receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('Verified standard TeX dependencies prepared locally at',tree)
