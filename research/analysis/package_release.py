"""Package the source-linked public release, excluding raw speech and credentials."""
from pathlib import Path
import hashlib, json, zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'dist/analysis'
files=[]
for base in [ROOT/'research/analysis',ROOT/'dist']:
    for p in sorted(base.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts: continue
        if p.suffix in {'.zip','.sqlite','.pyc','.pdf'} or p.name.startswith('queue.sqlite'): continue
        if p.name=='release-manifest.json':continue
        files.append(p)
manifest={'asOf':'2026-10-23','scope':'Public metadata, derived text features, source code and review records. No raw caption text or model weights.','files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(OUT/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
files.append(OUT/'release-manifest.json')
with zipfile.ZipFile(OUT/'channeling-analysis-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,Path('channeling-atlas')/p.relative_to(ROOT))
print(json.dumps({'files':len(files),'bundle':str(OUT/'channeling-analysis-bundle.zip'),'bytes':(OUT/'channeling-analysis-bundle.zip').stat().st_size}))
