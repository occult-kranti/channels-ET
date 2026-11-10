#!/usr/bin/env python3
"""Freeze exactly the dataset engineer's receipt-bound package before archiving."""
import argparse
import hashlib
from pathlib import Path
import archive


def freeze(source, output):
    source=Path(source); output=Path(output)
    receipt_path=source/'package-receipt.json'
    receipt_binding=archive.binding(receipt_path); receipt=archive.read(receipt_path)
    items=[receipt['frozen_frame'],*receipt['private_artifacts']]
    names=[r['name'] for r in items]
    if len(names)!=len(set(names)):raise ValueError('Duplicate package paths')
    if output.exists():raise ValueError('Fresh package destination required')
    total=sum(r['bytes'] for r in items)
    output.parent.mkdir(parents=True,exist_ok=True)
    if archive.shutil.disk_usage(output.parent).free-total<archive.PRIVATE_FLOOR:
        raise ValueError('Insufficient capacity above reserve')
    output.mkdir()
    for row in items:
        relative=archive.allowed_relative(row['name'])
        src=source/relative; dest=output/relative
        if src.is_symlink():raise ValueError('Symlinked package source rejected')
        dest.parent.mkdir(parents=True,exist_ok=True)
        before=src.stat(); digest=hashlib.sha256(); count=0
        with src.open('rb') as reader,dest.open('xb') as writer:
            for block in iter(lambda:reader.read(4*1024**2),b''):
                writer.write(block);digest.update(block);count+=len(block)
        after=src.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('Source package changed while frozen')
        if count!=row['bytes'] or digest.hexdigest()!=row['sha256']:
            raise ValueError('Package bytes do not match engineer receipt: '+row['name'])
        dest.chmod(0o444)
    if archive.binding(receipt_path)!=receipt_binding:raise ValueError('Receipt changed while copied')
    (output/'package-receipt.json').write_bytes(receipt_path.read_bytes())
    archive.dump(output/'frozen-package.json',{'created_at':archive.now(),
        'package_receipt_binding':receipt_binding,'files_copied':len(items),'bytes_copied':total,
        'verification':'Every copied byte matches engineer package-receipt SHA-256; originals preserved.',
        'source_root_label':'dataset-submission-2026-11'})
    return {'files':len(items),'bytes':total,'receipt':receipt_binding}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(freeze(a.source,a.output))
