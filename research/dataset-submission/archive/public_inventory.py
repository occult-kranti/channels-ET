#!/usr/bin/env python3
"""Export retained-object bookkeeping without source bodies or filesystem paths."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raw=a.inventory.read_bytes();x=json.loads(raw)
    aliases=Counter(r['sha256'] for r in x['files'])
    records=[{'sha256':o['sha256'],'bytes':o['bytes'],'logical_path_count':aliases[o['sha256']],
              'retained':True,'remote_transfer_verified':False} for o in x['objects']]
    assert len(records)==len({r['sha256'] for r in records})
    assert sum(r['logical_path_count'] for r in records)==len(x['files'])
    a.output.mkdir(parents=True,exist_ok=True)
    target=a.output/'archive-objects.jsonl'
    target.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in records))
    summary={'schema_version':1,'source_inventory_sha256':hashlib.sha256(raw).hexdigest(),
             'objects':len(records),'logical_paths':len(x['files']),
             'unique_bytes':sum(r['bytes'] for r in records),
             'object_file':'archive-objects.jsonl',
             'scope':'Retained file objects, including media, text, source evidence and research artifacts. These are not counts of videos or independent observations.',
             'public_content':'Hashes, byte sizes, logical alias counts and transfer state only; no source bodies, filenames, credentials or local paths.',
             'transfer_cutoff':'No full-source archive uploads verified at this snapshot.'}
    (a.output/'archive-object-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
