#!/usr/bin/env python3
"""Stop an identified v2 collector and inventory its immutable handoff to v3."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

SPEC=importlib.util.spec_from_file_location('collector_transition',Path(__file__).with_name('acquire_publisher_audio.py'))
C=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(C)

def alive(pid):
    stat=Path(f'/proc/{pid}/stat')
    return stat.exists() and stat.read_text().split(') ',1)[1][0]!='Z'

def run(phase,pid=None):
    phase=phase.resolve()
    target=phase/'transition-to-v3.json'
    if target.exists():raise ValueError('Existing transition must not be overwritten')
    stop={'requested_pid':pid,'requested_signal':None,'children_before_stop':[]}
    if pid is not None:
        args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
        if not any(a.endswith('/acquire_publisher_audio.py') for a in args):raise ValueError('PID is not the identified v2collector')
        output=Path(args[args.index('--output')+1]).resolve()
        if output!=phase:raise ValueError('PID output differs from requested private phase')
        child_path=Path(f'/proc/{pid}/task/{pid}/children')
        children=[int(x) for x in child_path.read_text().split()] if child_path.exists() else []
        stop.update(requested_signal='SIGINT',command=args,children_before_stop=children,requested_at=C.now())
        os.kill(pid,signal.SIGINT)
        deadline=time.monotonic()+45
        while any(alive(x) for x in [pid,*children]):
            if time.monotonic()>deadline:raise RuntimeError('Collector/child remains active; no transition admitted')
            time.sleep(.2)
        stop.update(process_and_observed_children_stopped=True,observed_at=C.now())
    with (phase/'.collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old_manifest=phase/'manifest.json';old=json.loads(old_manifest.read_text());frame=json.loads((phase/'frame.json').read_text())
        byid={x['source_id']:x for x in frame};accepted={};held=[];orphan=[]
        listed={r['source_id'] for r in old['records']}
        for folder in sorted((phase/'items').iterdir()):
            if not folder.is_dir():continue
            receipt=folder/'receipt.json'
            if receipt.exists():
                try:
                    r=C.completed(receipt)
                    if r['source']!=byid[r['source_id']]:raise ValueError('Receipt frame differs')
                except Exception:
                    # Never silently downgrade a previously admitted artifact.
                    raise
                accepted[r['source_id']]=r
                if r['source_id'] not in listed:orphan.append({'source_id':r['source_id'],'receipt':C.artifact(receipt)})
                if (folder/'original.partial').exists():
                    held.append({'reason':'completed_derivative_with_retained_new_original_after_interrupt','artifact':C.artifact(folder/'original.partial')})
            else:
                held.append({'reason':'interrupted_unadmitted_item','directory':str(folder),
                             'artifacts':[C.artifact(p) for p in sorted(folder.rglob('*')) if p.is_file()]})
        if not listed<=set(accepted):raise ValueError('Previously admitted source missing from actual receipt files')
        records=[accepted[x['source_id']] for x in frame if x['source_id'] in accepted]
        inherited=C.summary(records,frame,'stopped_for_parallel_successor')
        inherited.update(previous_manifest=C.artifact(old_manifest),source_frame=C.artifact(phase/'frame.json'),
                         validated_orphan_receipts=orphan,held_extra_artifacts=held)
        inherited_path=phase/'transition-inherited-manifest.json';C.dump(inherited_path,inherited)
        executed=phase/'executed-transition.py';executed.write_bytes(Path(__file__).read_bytes())
        all_files=[C.artifact(p) for p in sorted((phase/'items').rglob('*')) if p.is_file()]
        result={'schema_version':1,'status':'previous_phase_stopped_and_inventoried','created_at':C.now(),'stop':stop,
                'original_manifest':C.artifact(old_manifest),'inherited_manifest':C.artifact(inherited_path),
                'frame':C.artifact(phase/'frame.json'),'executed_transition':C.artifact(executed),
                'validated_completed_sources':len(records),'validated_orphan_receipts':orphan,'held_extra_artifacts':held,
                'all_item_files':all_files,'all_item_file_bytes':sum(a['bytes'] for a in all_files),
                'no_files_removed_or_modified':True}
        C.dump(target,result)
        print(json.dumps({'completed':len(records),'held_groups':len(held),'transition':str(target)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',type=Path,required=True);p.add_argument('--stop-pid',type=int)
    a=p.parse_args();run(a.phase,a.stop_pid)
