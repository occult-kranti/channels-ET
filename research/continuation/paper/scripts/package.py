#!/usr/bin/env python3
import hashlib,json,pathlib,zipfile
p=pathlib.Path(__file__).resolve().parents[1];z=p/'channels-et-source.zip'
files=[p/'main.tex',p/'body.tex',p/'appendices.tex',p/'references.bib',p/'input-manifest.json',p/'README.md',p/'tex-dependencies.json']+list((p/'generated').rglob('*'))+list((p/'vendor').rglob('*'))
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as out:
 for f in sorted(files):
  if f.is_file():
   name=str(f.relative_to(p));name=f.name if f.parent==p/'vendor' else name
   info=zipfile.ZipInfo(name,date_time=(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;out.writestr(info,f.read_bytes())
m={'pdf_sha256':hashlib.sha256((p/'channels-et-paper.pdf').read_bytes()).hexdigest(),'source_zip_sha256':hashlib.sha256(z.read_bytes()).hexdigest(),'source_files':sum(f.is_file() for f in files),'style':'Unmodified official AAAI2027 preprint; living draft, not venue-compliance certification','status':'working_draft'}
(p/'artifact-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
