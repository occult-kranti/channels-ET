#!/usr/bin/env python3
"""Archive every accepted alternative without changing the frozen selected frame."""
import argparse, collections, importlib.util, json, sqlite3
from pathlib import Path
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('build_dataset.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def materialize(private):
    s=b.load_sources();framepath=private/'frame.json';frozen=b.sha(framepath.read_bytes());frame=b.read(framepath)
    candidatepath=private/'legacy-candidates.json'
    if not candidatepath.exists():
        work=private/'alternate-loader';work.mkdir(exist_ok=True)
        candidates,inputs,dispositions=s.gather(work)
        b.dump(candidatepath,{'records':candidates,'inputs':inputs,'dispositions':dispositions})
    legacy=b.read(candidatepath);by={}
    for r in legacy['records']:
        eid=r['edition_id']
        if eid in by and by[eid]['body_sha256']!=r['body_sha256']:raise ValueError('Edition ID collision')
        by[eid]=r
    for line in (private/'new-editions.jsonl').read_text().splitlines():
        item=json.loads(line);r=item['record'];by[r['selected_edition_id']]=r
    out=[];closure={r['path']:r for r in map(json.loads,(private/'physical-assets.jsonl').read_text().splitlines())}
    for e in frame['alternate_editions']:
        r=by[e['edition_id']];text=s.body(r['text_artifact'],r['body_transform']);digest=b.sha(text.encode())
        if digest!=e['body_sha256'] or len(text.split())!=e['words']:raise ValueError('Edition/body mismatch: '+e['edition_id'])
        ref=r['text_artifact'];row={'edition_id':e['edition_id'],'source_id':e['source_id'],'selected':e['selected'],
            'text_origin':e['text_origin'],'body_sha256':digest,'words':e['words'],'text_artifact':ref,
            'body_transform':r['body_transform'],'text':text,'retention_state':'retained_verified_full_body'}
        out.append(row)
        p=ref['path'];c=closure.setdefault(p,{'path':p,'kind':'text_edition','bytes':Path(p).stat().st_size,
            'sha256':ref['sha256'],'source_ids':[],'edition_ids':[],'verification':'verified_text_sha256_and_selected_normalized_body'})
        if e['source_id']not in c['source_ids']:c['source_ids'].append(e['source_id'])
        if e['edition_id']not in c['edition_ids']:c['edition_ids'].append(e['edition_id'])
    b.jsonl(private/'edition-bodies.jsonl',out);b.jsonl(private/'physical-assets-complete-text.jsonl',list(closure.values()))
    db=sqlite3.connect(private/'corpus.sqlite');db.executescript('DROP TABLE IF EXISTS edition_bodies; CREATE TABLE edition_bodies(edition_id TEXT PRIMARY KEY,source_id TEXT,selected INTEGER,body_sha256 TEXT,words INTEGER,text TEXT,metadata_json TEXT);')
    for r in out:db.execute('INSERT INTO edition_bodies VALUES(?,?,?,?,?,?,?)',(r['edition_id'],r['source_id'],int(r['selected']),r['body_sha256'],r['words'],r['text'],json.dumps({k:v for k,v in r.items()if k!='text'},ensure_ascii=False)))
    db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';db.close()
    assert b.sha(framepath.read_bytes())==frozen
    receipt={'schema_version':1,'frame_sha256':frozen,'selected_documents_unchanged':len(frame['records']),
        'retained_verified_edition_bodies':len(out),'selected_editions':sum(r['selected']for r in out),
        'alternate_editions':sum(not r['selected']for r in out),'words_across_editions_nonindependent':sum(r['words']for r in out),
        'body_exact_hashes':len({r['body_sha256']for r in out}),
        'edition_jsonl':b.artifact(private/'edition-bodies.jsonl'),'sqlite':b.artifact(private/'corpus.sqlite'),
        'asset_closure':b.artifact(private/'physical-assets-complete-text.jsonl'),
        'counts_not_additive':'694 editions are renditions of 683 selected units, not 694 independent observations'}
    b.dump(private/'editions-receipt.json',receipt);print(json.dumps({k:v for k,v in receipt.items()if not isinstance(v,dict)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',type=Path,default=b.BASE/'dataset-submission-2026-11');materialize(p.parse_args().private)
