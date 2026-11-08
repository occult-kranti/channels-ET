#!/usr/bin/env python3
"""Standard-library checks for the public paired-recognition sensitivity artifact."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def close(a,b):return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)


def verify(root):
    root=Path(root);path=root/'asr-effects.json';raw=path.read_text();r=json.loads(raw)
    if any(x in raw for x in ('/workspace/','/dev/shm/','/tmp/','"text":')):raise ValueError('Private source data/path exposed')
    if r['status']!='executed_frozen_space_ASR_sensitivity':raise ValueError('Analysis not executed')
    coverage=r['coverage'];pairs=r['pairs'];ids={p['source_id'] for p in pairs}
    if len(ids)!=9 or len(pairs)!=9 or coverage['changed_sources']!=9 or coverage['candidate_sources']!=493:raise ValueError('Study denominators differ')
    if any(coverage[x] for x in ('full_corpus_reencoded','vocabulary_or_IDF_refit','canonical_frame_changed')):raise ValueError('Frozen-space contract violated')
    old_selected=sum(p['old_asr_is_selected_canonical'] for p in pairs)
    if old_selected!=coverage['canonical_ASR_vs_ASR_comparisons'] or 9-old_selected!=coverage['canonical_written_vs_ASR_comparisons']:raise ValueError('Comparison type denominator differs')
    for p in pairs:
        if not p['recording_id'].startswith('audio-sha256:') or p['recording_id'].split(':',1)[1]!=p['audio_sha256']:raise ValueError('Recording binding differs')
        for kind in ('same_audio_cosines','canonical_cosines'):
            for value in p[kind].values():
                if value is not None and (not math.isfinite(value) or not -1<=value<=1):raise ValueError('Invalid cosine')
        if p['old_asr_is_selected_canonical']:
            if p['old_asr_body_sha256']!=p['selected_body_sha256']:raise ValueError('Canonical counterpart binding differs')
            for field in ('lexical','semantic'):
                a,b=p['same_audio_cosines'][field],p['canonical_cosines'][field]
                if a is None or b is None:
                    if a!=b:raise ValueError('Representation availability differs')
                elif not close(a,b):raise ValueError('Same primary comparison differs')
        for kind in ('same_audio_cue_change','canonical_cue_change'):
            change=p[kind]
            for field,value in change['delta'].items():
                before,after=change['before'][field],change['after'][field]
                if before is None or after is None:
                    if value is not None:raise ValueError('Missing cue rate invented')
                elif not close(value,after-before):raise ValueError('Cue delta differs')
            for side in ('before','after'):
                q=change[side];tokens=q['lexical_tokens']
                if tokens:
                    if not close(q['negation_per_1000_lexical_tokens'],1000*q['negation_cues']/tokens):raise ValueError('Negation rate differs')
                    if not close(q['number_cues_per_1000_lexical_tokens'],1000*(q['number_word_cues']+q['digit_number_cues'])/tokens):raise ValueError('Number cue rate differs')
    for metric,data in r['neighbors'].items():
        if data['k']!=5 or {x['source_id'] for x in data['rows']}!=ids:raise ValueError('Neighbor source/count mismatch')
        scores=[]
        for row in data['rows']:
            sets=[]
            for side in ('before','after'):
                n=row[side];near=[x['source_id'] for x in n]
                if len(near)>5 or len(set(near))!=len(near) or row['source_id'] in near:raise ValueError('Neighbor identity/count invalid')
                expected=sorted(n,key=lambda x:(-x['cosine'],x['source_id']))
                if expected!=n:raise ValueError('Neighbor ordering differs')
                sets.append(set(near))
            score=len(sets[0]&sets[1])/len(sets[0]|sets[1]) if sets[0]|sets[1] else None
            if score is None:
                if row['jaccard'] is not None:raise ValueError('Unavailable neighbor score invented')
            else:
                if not close(score,row['jaccard']):raise ValueError('Jaccard differs')
                scores.append(score)
        if scores and not close(sum(scores)/len(scores),data['mean_jaccard_changed_sources']):raise ValueError('Mean changed-source Jaccard differs')
        for field in ('mean_jaccard_all_sources','mean_jaccard_unchanged_sources'):
            if data[field] is not None and not 0<=data[field]<=1:raise ValueError('Jaccard outside bounds')
    for f in r['figures']:
        p=(root/f['file']).resolve()
        if not p.is_relative_to(root.resolve()):raise ValueError('Figure path leaves public root')
        if not p.is_file():p=(root/'figures'/f['file']).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or p.stat().st_size!=f['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Figure binding differs')
    registry=root/'registry.json'
    if registry.exists():
        raw=registry.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['bindings']['registry_sha256']:raise ValueError('Published registry differs')
        doc_ids={x['source_id'] for x in json.loads(raw)['documents']}
        if not ids<=doc_ids:raise ValueError('Unknown changed source')
        for x in r['neighbors'].values():
            if any(n['source_id'] not in doc_ids for row in x['rows'] for side in ['before','after'] for n in row[side]):raise ValueError('Unknown neighbor')
    return {'status':'passed_public_ASR_effect_checks','changed_sources':len(ids),'candidate_sources':coverage['candidate_sources']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);print(json.dumps(verify(p.parse_args().root)))
