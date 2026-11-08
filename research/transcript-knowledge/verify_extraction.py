#!/usr/bin/env python3
"""Standard-library integrity and privacy gate for public extraction artifacts."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

TYPES={'observed_question_answer','unverified_question_candidate','generated_reading_prompt','curated_comparison'}
FORBIDDEN={'question_text','answer_text','context_text','text','extractive_summary'}


def check_public(obj):
    if isinstance(obj,dict):
        if FORBIDDEN&obj.keys():raise ValueError('Exact source text field leaked into public output')
        for value in obj.values():check_public(value)
    elif isinstance(obj,list):
        for value in obj:check_public(value)
    elif isinstance(obj,str) and any(x in obj for x in ['/workspace/','/dev/shm/','/tmp/']):raise ValueError('Private path leaked')


def verify(root):
    root=Path(root);profiles=json.loads((root/'profiles.json').read_text());index=json.loads((root/'bank-index.json').read_text())
    check_public(profiles);check_public(index)
    if profiles['bindings']!=index['bindings'] or profiles['coverage']!=index['coverage']:raise ValueError('Extraction provenance differs')
    ps={p['source_id']:p for p in profiles['profiles']};coverage=index['coverage']
    if len(ps)!=len(profiles['profiles']) or len(ps)!=coverage['processed_sources']:raise ValueError('Profile denominator differs')
    if sum(p['words'] for p in ps.values())!=coverage['processed_words']:raise ValueError('Processed word denominator differs')
    light={r['record_id']:r for r in index['records']};seen=set();counts=Counter()
    if len(light)!=len(index['records']):raise ValueError('Repeated global record')
    if {s['source_id'] for s in index['sources']}!=set(ps):raise ValueError('Source shard membership differs')
    for entry in index['sources']:
        source_id=entry['source_id'];p=ps[source_id];binding=entry['shard'];path=(root/binding['file']).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('Shard path leaves release')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=binding['sha256'] or len(raw)!=binding['bytes']:raise ValueError('Shard bytes changed')
        shard=json.loads(raw);check_public(shard)
        for key in ['source_id','selected_edition_id','body_sha256']:
            if shard[key]!=p[key]:raise ValueError('Shard edition differs')
        local=Counter()
        for r in shard['records']:
            rid=r['record_id'];typ=r['type']
            if rid in seen or rid not in light or typ not in TYPES:raise ValueError('Record identity/type differs')
            seen.add(rid);counts[typ]+=1;local[typ]+=1
            for k in ['type','display_question','topic_terms','answer_status','reading_status']:
                if r[k]!=light[rid][k]:raise ValueError('Light index differs from full record')
            if light[rid]['source_id']!=source_id:raise ValueError('Global source join differs')
            if r['addressed_to_claimed_entity_verified']:raise ValueError('Unsupported speaker attribution')
            if typ=='observed_question_answer':
                if not r['answer_spans'] or r['question_origin']!='publisher_printed':raise ValueError('Documentary pair lacks boundaries')
            elif typ in {'unverified_question_candidate','generated_reading_prompt'}:
                if r['answer_spans'] or r['answer_status']!='not_identified' or r['answer_paraphrase'] is not None:raise ValueError('Unverified source acquired an answer')
            if typ=='generated_reading_prompt' and r['question_span'] is not None:raise ValueError('Generated prompt presented as observed words')
            for s in ([r['question_span']] if r['question_span'] else [])+r['answer_spans']+([r['context_span']] if r['context_span'] else []):
                if not 0<=s['start_character']<s['end_character'] or not re.fullmatch('[0-9a-f]{64}',s['span_sha256']):raise ValueError('Invalid locator')
        if any(local[t]!=entry['counts'][t] or local[t]!=p['records_by_type'][t] for t in TYPES):raise ValueError('Source record count differs')
        if p['coverage']['processed_words']!=p['words'] or p['coverage']['total_words']!=p['words'] or p['coverage']['human_read'] or p['coverage']['audio_listened']:raise ValueError('Automatic coverage overclaimed')
        if p['summary_kind']!='automatic_source_profile' or p['reading_status']!='automatically_processed_not_close_read':raise ValueError('Automatic outline mislabeled')
        if sum(s['words'] for s in p['representative_spans'])>180:raise ValueError('Extractive digest exceeds word budget')
    if seen!=set(light) or len(seen)!=coverage['records'] or dict(counts)!=coverage['counts_by_type']:raise ValueError('Global record denominator differs')
    return {'status':'passed_public_extraction_checks','sources':len(ps),'records':len(seen),'counts_by_type':dict(counts)}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);print(json.dumps(verify(p.parse_args().root)))
