#!/usr/bin/env python3
"""Build the separate source-bound transcript explorer, without raw source text."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASELINE='0a20688c500ec6b0761f28340590c6beee58941e'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/transcripts')
    args=parser.parse_args();out=args.output.resolve()
    manifest=json.loads((HERE/'inputs.json').read_text())
    if args.candidate:
        if (ROOT/'dist') in out.parents:raise SystemExit('Candidate builds must use a preview directory outside public dist')
    elif manifest['releaseState']!='final_owner_holds_and_reviewed':
        raise SystemExit('Final owner holds/review are required before public export')
    bundle={'schemaVersion':1,'releaseStatus':'candidate'if args.candidate else'final','displayDate':'23 October 2026','displayTimeZone':'America/New_York','artifacts':[]}
    checked=[]
    for item in manifest['inputs']:
        source=ROOT/item['source'];raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=item['sha256']:raise SystemExit('Input changed; obtain owner final/candidate signal and rebind: '+item['source'])
        checked.append((item,raw,digest))
        if item.get('key'):
            value=json.loads(raw);parts=item['key'].split('.');cursor=bundle
            for p in parts[:-1]:cursor=cursor.setdefault(p,{})
            cursor[parts[-1]]=value
    # Explicit allowlist only. No glob of raw files, private windows, caches or models.
    out.mkdir(parents=True,exist_ok=True)
    for filename in ('index.html','styles.css','lib.js','charts.js','app.js'):
        shutil.copyfile(HERE/filename,out/filename)
    for item,raw,digest in checked:
        target=out/item['target'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        bundle['artifacts'].append({'path':item['target'],'source':item['source'],'sha256':digest,'bytes':len(raw),'label':item['label'],'kind':item['kind']})
    (out/'data.json').write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':'),allow_nan=False))
    if not args.candidate:
        index=subprocess.check_output(['git','show',BASELINE+':dist/research/index.html'],cwd=ROOT,text=True)
        needle='<nav aria-label="Project">'
        if index.count(needle)!=1:raise SystemExit('Historical shell changed; review navigation insertion')
        (ROOT/'dist/research/index.html').write_text(index.replace(needle,needle+'<a href="../transcripts/">Transcript study</a>'))
    print(json.dumps({'status':'candidate'if args.candidate else'final','output':str(out),'artifacts':len(checked)}))

if __name__=='__main__':main()
