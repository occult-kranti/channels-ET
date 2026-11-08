#!/usr/bin/env python3
"""Attach exact-source reading metadata to a verified fit without changing its numbers."""
import argparse
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


A=module('council_analysis','analyze.py');V=module('council_verify','verify_release.py')


def run(source,output,readings):
    source=A.private_path(source,exists=False);output=A.private_path(output,exists=False)
    if output.exists():raise ValueError('Choose a fresh metadata-enriched release')
    checked=V.verify(source);base=json.loads((source/'analysis.json').read_text())
    if A.sha(A.__file__)!=base['script_sha256']:raise ValueError('Retain the executed analyzer for exact-source metadata validation')
    manifest=json.loads((source/'output-manifest.json').read_text())
    for artifact in manifest['public_allowlist']:
        name=artifact['file']
        if Path(name).name!=name:raise ValueError('Invalid bound output name')
        if A.sha(source/name)!=artifact['sha256'] or (source/name).stat().st_size!=artifact['bytes']:raise ValueError('Prior output artifact changed')
    output.mkdir(parents=True,mode=0o700)
    inputs=[]
    for bound in base['input_bindings']:
        name=bound['snapshot_file']
        if Path(name).name!=name or A.sha(source/name)!=bound['sha256']:raise ValueError('Frozen input changed')
        inputs.append(source/name)
    docs,bindings,exclusions=A.load(inputs,output)
    if [d['summary'] for d in docs]!=base['documents'] or bindings!=base['input_bindings'] or exclusions!=base['excluded_and_aliases']:
        raise ValueError('Metadata enrichment would change the selected corpus')
    result=copy.deepcopy(base)
    result['supplemental_readings']=[A.supplemental_reading(path,docs) for path in readings]
    if {k:v for k,v in result.items() if k!='supplemental_readings'}!={k:v for k,v in base.items() if k!='supplemental_readings'}:
        raise ValueError('Metadata-only enrichment changed another field')
    result['annotation_enrichment']={
        'source_analysis_sha256':checked['analysis_sha256'],
        'source_analysis_bytes':(source/'analysis.json').stat().st_size,
        'enrichment_script_sha256':A.sha(__file__),
        'enriched_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'changed_fields':['supplemental_readings'],
        'numerical_refit_performed':False,
        'scope':'Exact-source reading metadata only; existing document, numerical, keyword, source-reading and figure fields are unchanged.'}
    for artifact in base['figures']:shutil.copyfile(source/artifact['file'],output/artifact['file'])
    shutil.copyfile(source/'executed-analyze.py',output/'executed-analyze.py')
    shutil.copyfile(__file__,output/'executed-enrich-readings.py')
    A.write(output/'analysis.json',result)
    allowed=[{'file':'analysis.json','sha256':A.sha(output/'analysis.json'),'bytes':(output/'analysis.json').stat().st_size}]+result['figures']
    A.write(output/'output-manifest.json',{'complete':True,'public_allowlist':allowed})
    A.write(output/'annotation-parent-private.json',{'path':str(source),'analysis_sha256':checked['analysis_sha256']})
    return V.verify(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reading',type=Path,action='append',required=True)
    args=p.parse_args();print(json.dumps(run(args.source,args.output,args.reading)))
