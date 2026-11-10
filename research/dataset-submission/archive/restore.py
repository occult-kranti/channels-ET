#!/usr/bin/env python3
"""Validate independent private shards and restore aliases into a fresh directory."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import archive


def restore(inventory_path, plan_path, shard_dir, receipts, output, hardlinks=False, prefix='shard'):
    if not archive.re.fullmatch(r'[A-Za-z0-9_-]+',prefix):raise ValueError('Unsafe shard prefix')
    inv = archive.read(inventory_path); plan = archive.read(plan_path)
    if plan['inventory_binding'] != archive.binding(inventory_path):
        raise ValueError('Plan does not bind this inventory')
    expected = {item['sha256']: item['bytes'] for item in inv['objects']}
    keys = [key for shard in plan['shards'] for key in shard['objects']]
    if len(keys) != len(set(keys)) or set(keys) != set(expected):
        raise ValueError('Plan does not close the unique object inventory')
    output = Path(output)
    if output.exists(): raise ValueError('A fresh restore directory is required')
    output.mkdir(parents=True)
    object_dir = output / '_objects'; object_dir.mkdir()
    for shard in plan['shards']:
        name = f"{prefix}-{shard['number']:03d}.tar.zst"
        path = Path(shard_dir) / name
        receipt = archive.read(Path(receipts) / (name+'.receipt.json'))
        if receipt['inventory_binding'] != archive.binding(inventory_path) or receipt['plan_binding'] != archive.binding(plan_path):
            raise ValueError('Shard receipt belongs to a different snapshot')
        if {k: receipt[k] for k in ('file','bytes','sha256')} != archive.binding(path):
            raise ValueError('Downloaded shard differs from frozen receipt')
        archive.check_shard(path, {key: expected[key] for key in shard['objects']})
        errors = tempfile.TemporaryFile()
        process = subprocess.Popen(['zstd','-dq','-c',str(path)], stdout=subprocess.PIPE, stderr=errors)
        try:
            with tarfile.open(fileobj=process.stdout, mode='r|') as tf:
                for member in tf:
                    key = member.name.removeprefix('objects/')
                    if not member.isfile() or not member.name.startswith('objects/') or not archive.HEX.fullmatch(key) or key not in shard['objects']:
                        raise ValueError('Unexpected archive object')
                    h=hashlib.sha256(); count=0
                    with (object_dir/key).open('xb') as dest, tf.extractfile(member) as src:
                        for block in iter(lambda:src.read(4*1024**2), b''):
                            dest.write(block); h.update(block); count+=len(block)
                    if h.hexdigest()!=key or count!=expected[key]: raise ValueError('Restored object mismatch')
                    (object_dir/key).chmod(0o444)
            for block in iter(lambda:process.stdout.read(65536),b''):
                if block.strip(b'\0'): raise ValueError('Nonzero trailing data')
            if process.wait()!=0: raise ValueError('Decompression failed')
        finally:
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close(); errors.close()
    restored=0
    for row in inv['files']:
        root=archive.allowed_relative(row['root'])
        if len(root.parts)!=1 or str(root)=='_objects': raise ValueError('Unsafe logical root')
        destination=output/root/archive.allowed_relative(row['relative_path'])
        if row['sha256'] not in expected or row['bytes']!=expected[row['sha256']]:
            raise ValueError('Alias does not match its content object')
        destination.parent.mkdir(parents=True,exist_ok=True)
        source=object_dir/row['sha256']
        if hardlinks: destination.hardlink_to(source)
        else:
            with source.open('rb') as src,destination.open('xb') as dest: shutil.copyfileobj(src,dest)
            destination.chmod(0o444)
        restored+=1
    archive.dump(output/'restore-receipt.json',{'created_at':archive.now(),
        'inventory_binding':archive.binding(inventory_path),'plan_binding':archive.binding(plan_path),
        'logical_paths_restored':restored,'unique_objects_verified':len(expected),
        'aliases_hardlinked':hardlinks,'symlinks_recreated':False,
        'file_modes':'Read-only 0444; original modes/timestamps retained in inventory, not applied.'})
    return restored


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','plan','shard-dir','receipts','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--hardlinks',action='store_true');p.add_argument('--prefix',default='shard'); a=p.parse_args()
    print(restore(a.inventory,a.plan,a.shard_dir,a.receipts,a.output,a.hardlinks,a.prefix))
