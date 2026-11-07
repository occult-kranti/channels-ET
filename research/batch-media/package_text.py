#!/usr/bin/env python3
"""Create a private portable text/reference bundle from a completed local archive.

Video and decoded audio stay in the full archive. This tool never uploads data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from audio import private_path

ALLOWED={'.txt','.srt','.json','.jsonl','.pdf','.csv','.svg','.png','.md','.py'}
RESERVE=6*1024**3

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def package(receipt_path,output):
    receipt_path=private_path(receipt_path,exists=True)
    output=private_path(output)
    if output.exists() or output.with_suffix('.receipt.json').exists():
        raise ValueError('Choose a fresh output; completed bundles are never replaced')
    receipt=json.loads(receipt_path.read_text())
    if receipt.get('kind')!='batch-local-archive' or receipt.get('status')!='completed' or not receipt.get('exact_file_set_verified'):
        raise ValueError('A completed local archive receipt is required')
    root=private_path(receipt['actual_root'])
    if output.is_relative_to(root):raise ValueError('Do not mutate the finalized archive')
    rows=[];excluded=[];names=set()
    for row in receipt['records']:
        rel=Path(row['relative_path'])
        if rel.is_absolute() or '..' in rel.parts or rel.as_posix() in names:
            raise ValueError('Unsafe or duplicate bundle member')
        names.add(rel.as_posix())
        if rel.suffix.lower() not in ALLOWED:
            excluded.append({k:row[k] for k in ('relative_path','bytes','sha256')});continue
        path=private_path(root/rel,exists=True)
        if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
            raise ValueError('Retained archive bytes changed')
        rows.append({k:row[k] for k in ('relative_path','bytes','sha256')})
    estimate=sum(row['bytes'] for row in rows)+2*1024**2
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free<RESERVE+estimate:
        raise ValueError('Bundle would consume the 6 GiB free-space reserve')
    description={
        'kind':'private-text-reference-bundle','archive_receipt_sha256':sha(receipt_path),
        'included_files':rows,'excluded_files':excluded,
        'scope':'Publisher reference PDFs, machine transcripts, derived analyses and provenance; no video or decoded audio.',
        'limitations':['Machine transcripts are unverified and have no diarization.',
            'Full-archive paths in provenance records refer to retained originals outside this portable bundle.',
            'The complete private archive index links the original videos; this bundle excludes that index to avoid broken media links.']}
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('BUNDLE-README.md','# Private text and reference bundle\n\n'+description['scope']+'\n\n'
            +'These files describe ten recordings from one Crimson Circle context. They are not ten independent mediums. '
            +'Publisher texts and ASR are versions of the same events. Full video and audio remain in the separate cloud archive.\n\n'
            +'See BUNDLE-MANIFEST.json for every included and excluded file and its SHA-256.\n')
        z.writestr('BUNDLE-MANIFEST.json',json.dumps(description,indent=2)+'\n')
        for row in rows:z.write(root/row['relative_path'],row['relative_path'])
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity verification failed')
        if set(z.namelist())!={r['relative_path'] for r in rows}|{'BUNDLE-README.md','BUNDLE-MANIFEST.json'}:
            raise ValueError('Bundle member set changed')
        for row in rows:
            h=hashlib.sha256();size=0
            with z.open(row['relative_path']) as stream:
                for block in iter(lambda:stream.read(1024**2),b''):h.update(block);size+=len(block)
            if size!=row['bytes'] or h.hexdigest()!=row['sha256']:raise ValueError('Compressed member hash mismatch')
    result={'kind':'private-portable-bundle-receipt','status':'verified','path':str(output),
        'bytes':output.stat().st_size,'sha256':sha(output),'included_source_files':len(rows),
        'excluded_files':len(excluded),'archive_receipt_sha256':sha(receipt_path),
        'script_sha256':sha(Path(__file__)),'network_requests':0}
    output.with_suffix('.receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(package(args.archive_receipt,args.output),indent=2))
