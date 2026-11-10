#!/usr/bin/env python3
"""Bind explicit public metadata, analysis and manuscript artifacts to one release."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile
import io

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('metadata_guard', HERE.parent/'youtube-archive/build_public.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
DATASET = ('dataset.json','documents.jsonl','editions.jsonl','media.jsonl',
           'youtube-accounts.jsonl','youtube-videos.jsonl','youtube-account-video-links.jsonl',
           'channels.csv','schema.json')
MODULES = {'dataset.json':'dataset','analysis.json':'analysis','venue.json':'venue','archive.json':'archive'}
EXTENSIONS = {'.json','.jsonl','.csv','.tsv','.md','.html','.css','.js','.svg','.png','.pdf','.zip',
              '.tex','.bib','.sty','.bst','.txt'}
ZIP_EXTENSIONS = {'.json','.jsonl','.csv','.tsv','.md','.tex','.bib','.sty','.bst','.svg','.png','.pdf','.py','.txt'}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def inspect(raw, name):
    suffix=Path(name).suffix
    if suffix not in EXTENSIONS: raise ValueError('Unexpected public artifact type: '+name)
    if suffix=='.json': guard.inspect(raw)
    elif suffix=='.jsonl':
        for line in raw.splitlines():
            if line.strip(): guard.inspect(line)
    elif suffix=='.pdf':
        if not raw.startswith(b'%PDF-'): raise ValueError('Invalid PDF')
    elif suffix=='.png':
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Invalid PNG')
    elif suffix=='.zip':
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist()
            if len(names)!=len(set(names)): raise ValueError('Duplicate ZIP member')
            for member in z.infolist():
                guard.safe('/bundle',member.filename)
                if member.is_dir(): continue
                if Path(member.filename).suffix not in ZIP_EXTENSIONS: raise ValueError('Unlisted ZIP member type')
                if member.file_size>50*1024**2: raise ValueError('Oversized public ZIP member')
                if Path(member.filename).suffix in {'.json','.jsonl'}: inspect(z.read(member),member.filename)
    elif suffix=='.svg' and (b'<script' in raw.lower() or b'javascript:' in raw.lower()):
        raise ValueError('Active script in research figure')

def verify(site):
    root=Path(site)/'dist/dataset-submission'
    manifest=guard.inspect((root/'manifest.json').read_bytes())
    refs=manifest['artifacts'];names=[r['file'] for r in refs]
    if len(names)!=len(set(names)): raise ValueError('Duplicate release filename')
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual!=set(names)|{'manifest.json'}: raise ValueError('Missing or unlisted release files: '+repr(actual^(set(names)|{'manifest.json'})))
    byname={r['file']:r for r in refs}
    for r in refs:
        path=guard.safe(root,r['file'])
        if (root/r['file']).is_symlink(): raise ValueError('Symlink artifact')
        raw=path.read_bytes()
        if len(raw)!=r['bytes'] or sha(raw)!=r['sha256']: raise ValueError('Artifact digest mismatch: '+r['file'])
        inspect(raw,r['file'])
    if 'dataset' not in manifest['modules']: raise ValueError('Missing core dataset module')
    for key,ref in manifest['modules'].items():
        if key!=MODULES.get(ref['file']): raise ValueError('Unexpected module binding')
        if {k:ref[k] for k in ('file','sha256','bytes')}!=byname[ref['file']]: raise ValueError('Module artifact mismatch')
        if ref['required']!=(key=='dataset'): raise ValueError('Invalid required module flag')
    return {'status':'passed_public_release_integrity','artifacts':len(refs),'modules':sorted(manifest['modules'])}

def build(site,producers,receipt=None):
    root=site/'dist/dataset-submission';root.mkdir(parents=True,exist_ok=True)
    refs={};copies=[];pending={}
    def include(path,name,expected=None):
        if path.is_symlink(): raise ValueError('Symlink producer output')
        raw=path.read_bytes();ref={'file':name,'bytes':len(raw),'sha256':sha(raw)}
        if expected and ref!={k:expected[k] for k in ('file','bytes','sha256')}: raise ValueError('Producer digest mismatch: '+name)
        inspect(raw,name)
        if name in refs and refs[name]!=ref: raise ValueError('Conflicting producer filename')
        guard.safe(root,name)
        refs[name]=ref;pending[name]=raw;copies.append({'source_path':str(path.resolve()),**ref})
    for name in DATASET: include(root/name,name)
    for folder in producers:
        listing=json.loads((folder/'output-manifest.json').read_text())['public_allowlist']
        if not listing or len({r['file'] for r in listing})!=len(listing): raise ValueError('Invalid producer allowlist')
        for ref in listing: include(guard.safe(folder,ref['file']),ref['file'],ref)
    for name in ('index.html','app.js','styles.css'): include(root/name,name)
    for path in sorted(HERE.glob('*.md')): include(path,'docs/'+path.name)
    extras={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-set(refs)-{'manifest.json'}
    if extras: raise ValueError('Unlisted files already in release: '+repr(sorted(extras)))
    # Verify the complete input plan before changing public artifacts. A stale producer
    # manifest therefore cannot leave a partially copied research edition behind.
    for name,raw in pending.items():
        target=guard.safe(root,name);target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.publishing');temp.write_bytes(raw);temp.replace(target)
    modules={MODULES[n]:{**r,'required':n=='dataset.json'} for n,r in refs.items() if n in MODULES}
    manifest={'schema_version':1,'title':'Channeling discourse dataset · research release',
              'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
              'scope':'Public metadata and derived research; full source text and media are private.',
              'dataset_version':json.loads((root/'dataset.json').read_text())['dataset_version'],
              'modules':modules,'artifacts':list(refs.values()),'builder_sha256':sha(Path(__file__).read_bytes())}
    raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode();(root/'manifest.json').write_bytes(raw)
    result=verify(site)
    if receipt:
        if receipt.resolve().is_relative_to(site.resolve()): raise ValueError('Private receipt is inside public repo')
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps({'manifest_sha256':sha(raw),'copies':copies,'verification':result},indent=2)+'\n')
    print(json.dumps({**result,'manifest_sha256':sha(raw)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True)
    p.add_argument('--producer',type=Path,action='append',default=[]);p.add_argument('--receipt',type=Path)
    a=p.parse_args();build(a.site,a.producer,a.receipt)
