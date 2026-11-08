#!/usr/bin/env python3
"""Read-only public release checks, without requiring private source texts."""
import argparse,hashlib,json,math
from pathlib import Path
EXPECTED={'ra_published':106,'bashar_context':19,'official_excerpt':75,'official_promotion':4,'official_greeting':3,'tracy_kumbera':70,'magenta_pixie':15}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
    r=json.loads((root/'analysis.json').read_text());assert r['schema_version']==1
    assert {g['id']:g['documents'] for g in r['coverage']['groups']}==EXPECTED
    assert r['coverage']['model_documents']==len(r['documents'])==292
    assert r['coverage']['model_words']==sum(d['whitespace_words'] for d in r['documents'])==774110
    ids={d['source_id'] for d in r['documents']};assert len(ids)==292
    for key in ['matrix','window_matrix']:
        m=r['similarities'][key];assert len(m)==7
        for i,row in enumerate(m):
            assert len(row)==7
            for j,v in enumerate(row):assert v is None or (math.isfinite(v) and 0<=v<=1 and abs(v-m[j][i])<1e-10)
    for row in r['clusters']['assignments']:assert row['source_id'] in ids
    assert r['qa']['documentary_pairs']==2523 and r['qa']['missing_question_text']==4
    assert r['qa']['eligible_candidates']==r['qa']['retrieval_leads']+r['qa']['abstentions']
    assert r['qa']['identified_non_Ra_answers']==0
    for q in r['qa_leads']:assert q['question_source_id'] in ids and q['response_source_id'] in ids
    text=json.dumps(r);assert '/workspace/' not in text and '"question_text"' not in text and '"response_text"' not in text
    for f in r['figures']:
        p=root/'figures'/f['file']
        if not p.exists():p=root/f['file']
        assert p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],f['file']
    return {'status':'passed','documents':292,'figures':len(r['figures']),'analysis_sha256':sha(root/'analysis.json')}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public-dir',required=True,type=Path);a=p.parse_args();print(json.dumps(verify(a.public_dir)))
