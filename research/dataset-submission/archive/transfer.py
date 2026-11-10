#!/usr/bin/env python3
"""One-shard RAM staging, resumable private transfer, full remote-byte verification."""
import argparse
import fcntl
from pathlib import Path
import archive


def transfer(inventory_path,plan_path,stage,receipts,repo,tag,prefix='shard'):
    if not archive.re.fullmatch(r'[A-Za-z0-9_-]+',prefix):raise ValueError('Unsafe shard prefix')
    destination=archive.repository(repo)
    archive.release_info(repo,tag)  # Release must already exist in the private repo.
    inv=archive.read(inventory_path); plan=archive.read(plan_path)
    inv_ref=archive.binding(inventory_path); plan_ref=archive.binding(plan_path)
    if plan['inventory_binding']!=inv_ref: raise ValueError('Plan binding differs')
    stage=Path(stage); receipts=Path(receipts)
    stage.mkdir(parents=True,exist_ok=True); receipts.mkdir(parents=True,exist_ok=True)
    completed=[]
    with (receipts/'transfer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for shard in plan['shards']:
            name=f"{prefix}-{shard['number']:03d}.tar.zst"
            path=stage/name; local_receipt=receipts/(name+'.receipt.json')
            remote_receipt=receipts/(name+'.remote.json')
            if remote_receipt.exists():
                previous=archive.read(remote_receipt)
                if previous.get('inventory_binding')!=inv_ref or previous.get('plan_binding')!=plan_ref:
                    raise ValueError('Existing receipt belongs to different inventory/plan')
                remote=archive.verify_remote(repo,tag,previous['local_asset'])
                remote.update(local_asset=previous['local_asset'],inventory_binding=inv_ref,plan_binding=plan_ref)
                archive.dump(remote_receipt,remote)
            else:
                if path.exists():
                    if not local_receipt.exists():
                        # Recover a completed build interrupted before receipt copying.
                        staged_receipt=path.with_suffix(path.suffix+'.receipt.json')
                        archive.dump(local_receipt,archive.read(staged_receipt))
                    receipt=archive.read(local_receipt)
                    if receipt['inventory_binding']!=inv_ref or receipt['plan_binding']!=plan_ref:
                        raise ValueError('Existing staging file belongs to different inventory/plan')
                    if {k:receipt[k] for k in ('file','bytes','sha256')}!=archive.binding(path):
                        raise ValueError('Existing staging bytes differ')
                else:
                    receipt=archive.build_shard(inventory_path,plan_path,shard['number'],path)
                    archive.dump(local_receipt,receipt)
                remote=archive.upload(repo,tag,path,remote_receipt)
                remote.update(inventory_binding=inv_ref,plan_binding=plan_ref)
                archive.dump(remote_receipt,remote)
            # Only newly generated staging objects are removed, after durable verification.
            if path.exists():
                if archive.binding(path)!=remote['local_asset']: raise ValueError('Staging changed before cleanup')
                path.unlink()
            completed.append(remote)
            archive.dump(receipts/'transfer-status.json',{'updated_at':archive.now(),
                'destination':destination,'tag':tag,'inventory_binding':inv_ref,'plan_binding':plan_ref,
                'planned_shards':len(plan['shards']),'verified_shards':len(completed),
                'verified_remote_bytes':sum(r['downloaded_bytes'] for r in completed),
                'complete_shard_transfer':len(completed)==len(plan['shards']),
                'metadata_and_final_supplement_require_separate_verification':True})
            print(f"Verified shard {shard['number']}/{len(plan['shards'])}: {remote['downloaded_bytes']} remote bytes",flush=True)
    return completed


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','plan','stage','receipts'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--repo',required=True);p.add_argument('--tag',required=True)
    p.add_argument('--prefix',default='shard');a=p.parse_args()
    transfer(a.inventory,a.plan,a.stage,a.receipts,a.repo,a.tag,a.prefix)
