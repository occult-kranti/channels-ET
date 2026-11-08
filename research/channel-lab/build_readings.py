#!/usr/bin/env python3
"""Validate actual inspected spans and publish bounded qualitative paraphrases."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELATIONS = {'shared_proposition','compatible','different_focus','conditional_tension','explicit_contradiction','unresolved'}


def digest(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def merge(spans):
    result=[]
    for start,end in sorted(spans):
        if result and start<=result[-1][1]: result[-1][1]=max(end,result[-1][1])
        else: result.append([start,end])
    return result


def build(frame_path, inspection_path, cases_path, selection_path, output):
    output=Path(output).resolve()
    if output.exists(): raise ValueError('Use a fresh reading release directory')
    if not (str(output).startswith('/dev/shm/') or output.is_relative_to(Path('/workspace/channels-et-private'))):
        raise ValueError('Release privately, then publish the exact allowlist')
    spec=importlib.util.spec_from_file_location('channel_reading_sources',ROOT/'research/channel-lab/sources.py')
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    docs=source.load_frame(frame_path);frame=read(frame_path)
    records={d['record']['source_id']:d['record'] for d in docs};bodies={d['record']['source_id']:d['text'] for d in docs}
    aliases=defaultdict(set)
    for r in records.values():
        for old in r['legacy_source_ids']+[r['selected_edition_id']]: aliases[old].add(r['source_id'])
    inspections=read(inspection_path);case_specs=read(cases_path);selection=read(selection_path)
    ids=[x['evidence_id'] for x in inspections['spans']]
    if len(ids)!=len(set(ids)): raise ValueError('Repeated evidence ID')
    proofs={};private_proofs=[];ranges=defaultdict(list);alt_ranges=defaultdict(list);alt_bodies={}
    source_id_by_legacy={}
    for item in inspections['spans']:
        legacy=item['legacy_source_id'];anchor=item.get('legacy_counterpart_id',legacy)
        candidates=aliases.get(anchor,set())
        join_basis='declared_legacy_source_id'
        if not candidates and item.get('allow_exact_body_alias'):
            candidates={sid for sid,r in records.items() if r['body_sha256']==item['body_sha256']}
            join_basis='exact_complete_normalized_body_alias_explicitly_reviewed'
        if len(candidates)!=1: raise ValueError(f'Cannot uniquely join inspected source {anchor}: {candidates}')
        sid=next(iter(candidates));r=records[sid];source_id_by_legacy[legacy]=sid
        if item['body_sha256']==r['body_sha256']:
            body=bodies[sid];kind='same_edition';ranges[sid].append([item['start_character'],item['end_character']])
        else:
            if not item.get('alternative_edition',False):
                raise ValueError(f'Canonical edition differs; re-read before binding: {legacy}')
            body=source.body(item['text_artifact'],item['body_transform'])
            if digest(body.encode())!=item['body_sha256']: raise ValueError('Alternative body changed')
            key=(sid,item['body_sha256']);kind='alternative_edition_not_canonical'
            alt_ranges[key].append([item['start_character'],item['end_character']]);alt_bodies[key]=body
        lo,hi=item['start_character'],item['end_character']
        if not 0<=lo<hi<=len(body): raise ValueError('Invalid reading span')
        text=body[lo:hi]
        if digest(text.encode())!=item['span_sha256'] or text!=item['text'] or len(text.split())!=item['words']:
            raise ValueError('Inspected span bytes/words differ: '+item['evidence_id'])
        proof={'evidence_id':item['evidence_id'],'source_id':sid,'channel_id':r['channel_id'],
            'source_url':item.get('source_url') or r['source_url'],'source_title':r['title'],
            'selected_edition_id':r['selected_edition_id'],'inspected_edition_id':legacy,
            'canonical_join_basis':join_basis,
            'edition_text_sha256':item['body_sha256'],'selected_body_sha256':r['body_sha256'],
            'edition_join':kind,'reading_kind':item['reading_kind'],'read_scope':item['read_scope'],
            'locator':{'start_character':lo,'end_character':hi,'span_sha256':item['span_sha256'],'words':item['words']},
            'speaker_identity_verified':False,'audio_alignment_verified':False,'human_validated':False}
        for key in ['question_id','turn_ids','start_seconds','end_seconds','existing_card_id','existing_question_id']:
            if key in item: proof[key]=item[key]
        if 'existing_card_id' in proof and kind!='same_edition':raise ValueError('Cannot inherit a card on changed text')
        if item.get('existing_card_id'):
            original=next(c for c in read(inspections['accepted_knowledge']['path'])['cards'] if c['card_id']==item['existing_card_id'])
            if not any(s['body_sha256']==item['body_sha256'] and s['span_sha256']==item['span_sha256'] and s['start_character']==lo and s['end_character']==hi for s in original['supports']):
                raise ValueError('Reused card support differs')
        proofs[item['evidence_id']]=proof;private_proofs.append({**proof,'text':text})
    knowledge_raw=Path(inspections['accepted_knowledge']['path']).read_bytes()
    if digest(knowledge_raw)!=inspections['accepted_knowledge']['sha256']:raise ValueError('Accepted knowledge artifact changed')
    selected_ids={x['case_id'] for x in selection['candidates']};cases=[];dispositions=[]
    for case in case_specs['cases']:
        if case['case_id'] not in selected_ids:raise ValueError('Unfrozen case ID')
        if case['relation'] not in RELATIONS:raise ValueError('Unknown relation')
        evidence=[proofs[e] for e in case['evidence_ids']]
        if any(e['edition_join']!='same_edition' for e in evidence):raise ValueError('Primary case requires canonical-edition evidence')
        sids=sorted({e['source_id'] for e in evidence});cids=sorted({e['channel_id'] for e in evidence})
        c={key:value for key,value in case.items() if key not in {'evidence_ids'}}
        c.update(source_ids=sids,channel_ids=cids,evidence=evidence,selection_disposition='retained_after_source_reading')
        c['existing_question_ids']=sorted({e['existing_question_id'] for e in evidence if e.get('existing_question_id')})
        for statement in c['statements']:
            statement['source_id']=source_id_by_legacy[statement.pop('legacy_source_id')]
            if statement['source_id'] not in sids:raise ValueError('Statement is not bound to case evidence')
        if not all(c.get(x) for x in ['question','reading','conditions','counter_reading','limitations']):raise ValueError('Missing interpretive qualification')
        cases.append(c);dispositions.append({'case_id':case['case_id'],'status':'retained','reason':'Required source scope and evidence inspected; relation is a purposive interpretation, not a prevalence claim'})
    for failed in case_specs.get('failed_candidates',[]):
        if failed['case_id'] not in selected_ids:raise ValueError('Unfrozen failure')
        dispositions.append(failed)
    if {x['case_id'] for x in dispositions}!=selected_ids:raise ValueError('Every frozen candidate needs a disposition')
    bindings=[];new_words=0;complete=0
    for sid,spans in ranges.items():
        r=records[sid];intervals=merge(spans);body=bodies[sid];words=sum(len(body[a:b].split()) for a,b in intervals);new_words+=words
        full=intervals==[[0,len(body)]];complete+=full
        bindings.append({'source_id':sid,'channel_id':r['channel_id'],'title':r['title'],'source_url':r['source_url'],
            'selected_edition_id':r['selected_edition_id'],'body_sha256':r['body_sha256'],'text_artifact_sha256':r['text_artifact']['sha256'],
            'body_words':r['words'],'unique_words_inspected':words,'merged_intervals':intervals,'complete_body_inspected':full,
            'document_kind':r['document_kind'],'text_origin':r['text_origin'],'attribution_scope':r['attribution_scope'],
            'audio_listened':False,'human_validated':False})
    alt=[]
    for key,spans in alt_ranges.items():
        sid,hashed=key;intervals=merge(spans);alt.append({'source_id':sid,'channel_id':records[sid]['channel_id'],
            'inspected_body_sha256':hashed,'unique_words_inspected':sum(len(alt_bodies[key][a:b].split()) for a,b in intervals),
            'merged_intervals':intervals,'edition_join':'alternative_edition_not_canonical',
            'scope':'Additional inspected recognition edition; excluded from canonical reading-word totals and primary cases'})
    notes=[]
    for cid in sorted({r['channel_id'] for r in records.values()}):
        rows=[r for r in records.values() if r['channel_id']==cid];read_ids=sorted(r['source_id'] for r in rows if r['source_id'] in ranges)
        related=[c for c in cases if cid in c['channel_ids']];specific=case_specs['channel_notes'].get(cid,{})
        notes.append({'channel_id':cid,'channel_name':rows[0]['channel_name'],
            'reading_status':'bounded_examples_read' if read_ids else 'not_close_read_in_this_pass',
            'frame_source_units':len(rows),'reviewed_source_ids':read_ids,'unreviewed_source_units':len(rows)-len(read_ids),
            'unique_words_inspected':sum(x['unique_words_inspected'] for x in bindings if x['channel_id']==cid),
            'case_ids':[c['case_id'] for c in related],
            'qualitative_theme_keys':sorted({t for c in related for t in c['qualitative_theme_keys']}),
            'summary':specific.get('summary','No substantive source-reading summary is supplied for this context in this pass.'),
            'conditions':specific.get('conditions','Computed features and historical annotations do not establish a fresh close reading of these sources.'),
            'unreviewed_scope':'Other retained editions and the remainder of partly inspected bodies are unreviewed here; whole-channel prevalence and lifetime uploads are unknown.'})
    result={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'status':'completed_bounded_source_reading','scope':'Source-attributed discourse interpretation; no verification of claimed entities, events, effects, speaker identity or recognition accuracy.',
        'input_bindings':{name:{'sha256':digest(Path(p).read_bytes()),'bytes':Path(p).stat().st_size} for name,p in [('frame',frame_path),('inspection',inspection_path),('cases',cases_path),('selection',selection_path)]},
        'coverage':{'frame_source_units':len(records),'frame_words':sum(r['words'] for r in records.values()),
            'primary_sources_read':len(ranges),'primary_unique_words_read':new_words,'primary_complete_bodies_read':complete,
            'primary_reading_spans':sum(1 for p in proofs.values() if p['edition_join']=='same_edition'),
            'additional_edition_sources_read':len(alt),'additional_unique_words_read':sum(x['unique_words_inspected'] for x in alt),
            'case_count':len(cases),'failed_candidates':len(case_specs.get('failed_candidates',[])),
            'read_channel_contexts':sum(bool(n['reviewed_source_ids']) for n in notes),'modeled_channel_contexts':len(notes),
            'relation_counts':dict(Counter(c['relation'] for c in cases)),
            'audio_listened_seconds':0,'human_validated':False,'question_origin':'All case questions are analyst comparisons; documentary Ra question IDs are retained separately.'},
        'source_bindings':bindings,'additional_edition_readings':alt,
        'channel_notes':notes,'cases':cases,'candidate_dispositions':dispositions,
        'additional_evidence':[p for p in proofs.values() if p['edition_join']!='same_edition'],
        'reading_method':inspections['method'],
        'limitations':case_specs['limitations'],'script_sha256':digest(Path(__file__).read_bytes())}
    raw=json.dumps(result,ensure_ascii=False)
    if '/workspace/' in raw or 'text_artifact' in raw.replace('text_artifact_sha256',''):raise ValueError('Private path/body reference leaked')
    output.mkdir(parents=True)
    write(output/'readings.json',result);write(output/'reading-evidence-private.json',{'proofs':private_proofs,'source_inspection':inspections})
    public=output/'readings.json';write(output/'output-manifest.json',{'schema_version':1,'complete':True,'public_allowlist':[{'file':public.name,'bytes':public.stat().st_size,'sha256':digest(public.read_bytes())}]})
    print(json.dumps({'coverage':result['coverage'],'public_sha256':digest(public.read_bytes())},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['frame','inspection','cases','selection','output']:p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();build(args.frame,args.inspection,args.cases,args.selection,args.output)
