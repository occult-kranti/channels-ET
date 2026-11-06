#!/usr/bin/env python3
"""Export a private ASR input manifest from verified collection-runner artifacts."""
import argparse, hashlib, json, sqlite3
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1048576), b''): h.update(part)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True,type=Path)
    p.add_argument('--selection',required=True,type=Path)
    p.add_argument('--raw',required=True,type=Path,help='Existing collection runner raw root')
    p.add_argument('--output',required=True,type=Path,help='Private JSON manifest outside Git')
    a=p.parse_args()
    if not a.database.is_file(): raise SystemExit('Existing collection ledger not found; do not reset or recreate it.')
    selected=json.loads(a.selection.read_text()); rows=selected.get('records') if isinstance(selected,dict) else selected
    if not isinstance(rows,list): raise SystemExit('Expected list or records list')
    output=a.output.resolve()
    # Do not place private media paths or transcript manifests in public Git.
    if any((parent/'.git').exists() for parent in [output.parent,*output.parents]): raise SystemExit('Output must be outside a Git checkout')
    uri=a.database.resolve().as_uri()+'?mode=ro'
    with sqlite3.connect(uri,uri=True) as conn:
        conn.row_factory=sqlite3.Row
        records=[]; excluded=[]; seen=set()
        for candidate in rows:
            vid=candidate.get('video_id',candidate.get('id',''))
            if vid in seen: continue
            seen.add(vid)
            found=conn.execute("SELECT a.path,a.sha256,a.validation_json,i.metadata_json FROM artifacts a JOIN items i ON a.source_id=i.source_id WHERE i.video_id=? AND a.kind='video' AND a.status='verified_quarantine' ORDER BY a.rowid DESC",(vid,)).fetchall()
            accepted=None
            for item in found:
                raw=a.raw.resolve(); relative=Path(item['path'])
                if relative.is_absolute() or '..' in relative.parts: continue
                path=raw / relative
                if not path.resolve().is_relative_to(raw / 'quarantine'): continue
                if not path.is_file() or path.is_symlink() or sha256(path)!=item['sha256']: continue
                validation=json.loads(item['validation_json'])
                if validation.get('source_video_id')!=vid or not validation.get('ffprobe_duration_seconds'): continue
                metadata=json.loads(item['metadata_json'] or '{}')
                if metadata.get('id')!=vid: continue
                accepted={'video_id':vid,'channel':metadata.get('channel') or metadata.get('uploader') or candidate.get('channel','unknown'),'title':metadata.get('title',''),'media_path':str(path.resolve()),'sha256':item['sha256']};break
            if accepted: records.append(accepted)
            else: excluded.append({'video_id':vid,'reason':'no matching verified, hash-valid video in ledger'})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report=output.with_name(output.stem+'.excluded.json')
    report.write_text(json.dumps(excluded,indent=2)+'\n',encoding='utf-8')
    print(f'{len(records)} verified videos; {len(excluded)} excluded')
if __name__=='__main__': main()
