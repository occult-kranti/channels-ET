#!/usr/bin/env python3
"""Recreate the analysis supplement's frozen inputs from its producer receipt."""
import argparse
from pathlib import Path
import shutil
import archive


def freeze(private, public, output):
    private=Path(private); public=Path(public); output=Path(output)
    receipt=private/'analysis-receipt.json'; ref=archive.binding(receipt); data=archive.read(receipt)
    if output.exists():raise ValueError('Fresh analysis destination required')
    total=sum(r['bytes'] for group in ('private_files','public_files') for r in data[group])
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free-total<archive.PRIVATE_FLOOR:raise ValueError('Insufficient staging reserve')
    output.mkdir()
    for group,source in [('private_files',private),('public_files',public)]:
        names=set()
        for row in data[group]:
            rel=archive.allowed_relative(row['file'])
            if str(rel) in names:raise ValueError('Duplicate analysis source')
            names.add(str(rel));src=source/rel;dst=output/group/rel
            if src.is_symlink():raise ValueError('Symlinked analysis input rejected')
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            if archive.binding(dst)!={'file':dst.name,'bytes':row['bytes'],'sha256':row['sha256']}:
                raise ValueError('Analysis bytes differ from producer receipt: '+str(rel))
    if archive.binding(receipt)!=ref:raise ValueError('Analysis producer receipt changed')
    shutil.copy2(receipt,output/'analysis-receipt.json')
    return {'files':sum(len(data[k]) for k in ('private_files','public_files'))+1,'producer_receipt':ref}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('private','public','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(freeze(a.private,a.public,a.output))
