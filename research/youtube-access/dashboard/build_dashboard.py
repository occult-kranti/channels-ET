#!/usr/bin/env python3
"""Layer the current collection supplement onto the retained research build.

Only explicit, reviewed metadata inputs are published. No collector, browser,
OAuth, raw-media, transcript or model execution occurs during this build.
"""
from pathlib import Path
import hashlib,json,runpy,shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'dist/research'
manifest=json.loads((HERE/'input-manifest.json').read_text())
if manifest.get('release_state')!='reviewed_final':
    raise SystemExit('Current supplement is awaiting finalized owner exports; no public files changed')
inputs={}
for item in manifest['inputs']:
    source=ROOT/item['source']
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=item['sha256']:
        raise SystemExit('Reviewed supplement input changed; obtain final owner export and rebind: '+item['source'])
    if item.get('key'):
        inputs[item['key']]=json.loads(raw)

# The retained authoring sources and historical source artifacts stay untouched.
# Running their deterministic build restores the same base before each layer.
runpy.run_path(str(ROOT/'research/continuation/dashboard/build_dashboard.py'),run_name='__main__')
bundle=json.loads((OUT/'data.json').read_text())
bundle['harvest']['currentSupplement']={'schemaVersion':1,'sources':inputs}
for item in manifest['inputs']:
    source=ROOT/item['source'];target=OUT/item['target']
    shutil.copyfile(source,target)
    bundle['artifacts'].append({'path':item['target'],'bytes':target.stat().st_size,
      'sha256':item['sha256'],'source':item['source'],'label':item['label'],'kind':item['kind']})
shutil.copyfile(HERE/'youtube-access.js',OUT/'youtube-access.js')
shutil.copyfile(HERE/'youtube-access.css',OUT/'youtube-access.css')
index=(OUT/'index.html').read_text()
needle='<script src="app.js"></script>'
if index.count(needle)!=1:raise SystemExit('Retained shell changed; review new component integration')
index=index.replace(needle,'<script src="youtube-access.js"></script>'+needle)
index=index.replace('<link rel="stylesheet" href="styles.css">','<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="youtube-access.css">')
(OUT/'index.html').write_text(index)
(OUT/'data.json').write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':'),allow_nan=False))
print(json.dumps({'output':str(OUT),'currentSupplementInputs':len(inputs),'artifacts':len(bundle['artifacts'])}))
