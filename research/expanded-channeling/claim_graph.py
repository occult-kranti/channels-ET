#!/usr/bin/env python3
"""Typed source-claim statistics with practice dependence and text missingness."""
import argparse,collections,hashlib,json
from pathlib import Path
DIRECT={'channels_named_entity','channels_collective','claims_to_channel'}
PILOT_LABEL_CROSSWALK={'et-group-pleiadian':'pleiadian','et-group-arcturian':'arcturian','et-group-andromedan':'andromedan','et-group-sassani':'sassani','tr-group-mary':'mother_mary','tr-group-magdalene':'mary_magdalene','tr-group-michael':'archangel_michael','tr-group-jesus':'jeshua_jesus_related','tr-group-isis':'isis','tr-group-quanyin':'quan_yin'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(paths,pilot=None):
    sources={};mediums={};entities={};claims=[];groups=[];bindings=[]
    for path in paths:
        d=json.loads(path.read_text());bindings.append({'file':path.name,'sha256':sha(path)})
        for name,target in [('sources',sources),('mediums',mediums),('channellees',entities)]:
            for x in d[name]:
                if x['id'] in target:
                    old=target[x['id']]
                    for key in (['name'] if name=='mediums' else ['url'] if name=='sources' else ['label','kind']):
                        if old.get(key) and x.get(key) and old[key].casefold()!=x[key].casefold():raise ValueError('Conflicting immutable registered identity: '+x['id'])
                    for key,value in x.items():
                        if isinstance(value,list):old[key]=list({json.dumps(v,sort_keys=True):v for v in old.get(key,[])+value}.values())
                        elif key not in old or old[key] is None:old[key]=value
                    continue
                target[x['id']]=dict(x)
        claims+=d['claims'];groups+=d.get('comparison_groups',[])
    group_lookup={g['id']:g for g in groups}
    for eid,entity in entities.items():
        group_id=entity.get('comparison_group_id')
        if group_id:
            if group_id not in group_lookup:raise ValueError('Declared comparison-group reference does not exist')
            group=group_lookup[group_id];group['channellee_ids']=sorted(set(group['channellee_ids'])|{eid})
    seen=set()
    for c in claims:
        if c['id'] in seen:raise ValueError('Duplicate claim identifier')
        seen.add(c['id'])
        if c['medium_id'] not in mediums or c['channellee_id'] not in entities or any(s not in sources for s in c['source_ids']):raise ValueError('Claim has unresolved references')
    docs=json.loads(pilot.read_text())['documents'] if pilot else []
    out=[]
    for g in groups:
        ee=set(g['channellee_ids']);cc=[c for c in claims if c['channellee_id'] in ee];direct=[c for c in cc if c['relation'] in DIRECT];people=set(c['medium_id'] for c in direct);practices=set(mediums[mid].get('collaboration_group_id') or mid for mid in people);comparison_label=PILOT_LABEL_CROSSWALK.get(g['id']);texts=[x for x in docs if x['label_id'] in ee or (comparison_label and x['comparison_label']==comparison_label)]
        out.append({'id':g['id'],'label':g['label'],'kind':g.get('kind','unspecified'),'identity_equivalence':False,'channellee_ids':sorted(ee),'all_claims':len(cc),'relation_counts':dict(collections.Counter(c['relation'] for c in cc)),'direct_claim_medium_records':len(people),'declared_practice_groups':len(practices),'independence_established':False,'medium_ids':sorted(people),'source_ids':sorted(set(s for c in cc for s in c['source_ids'])),'pilot_coverage_basis':'Explicit cross-register comparison-label mapping, preserving source-specific label IDs; no shared identity asserted.','pilot_comparison_label':comparison_label,'pilot_source_ids':[x['source_id'] for x in texts],'new_attributed_message_documents':len(texts),'new_attributed_message_mediums':len(set(x['medium_id'] for x in texts)),'text_comparison_status':'available_purposive_pilot' if len(set(x['medium_id'] for x in texts))>=2 else 'insufficient_cross_medium_attributed_text','note':g.get('note',g.get('notes'))})
    name_records=collections.defaultdict(list)
    for mid,m in mediums.items():name_records[m['name'].casefold()].append(mid)
    return {'schema_version':1,'inputs':bindings,'source_records':len(sources),'medium_records':len(mediums),'channellee_records':len(entities),'claims':len(claims),'edges':[{k:c[k] for k in ['id','medium_id','channellee_id','relation','source_ids','scope'] if k in c} for c in claims],'comparison_groups':out,'pilot_label_crosswalk':PILOT_LABEL_CROSSWALK,'same_named_person_multiple_register_ids':[{'name':name,'medium_ids':ids,'automatic_identity_merge':False} for name,ids in name_records.items() if len(ids)>1],'limitations':['Only direct-channeling relations enter direct-medium counts; category, affiliation, contact, series-listing and repost edges remain separate.','Declared collaboration grouping removes Pia/Cullen practice duplication but does not establish independent origins of any practice.','Text coverage counts only source-local attributed pilot messages, not biographies or mixed-speaker interviews. Missing comparable text is insufficient data, never zero similarity.','Registers may use separate IDs for the same named person; potential duplicates are flagged without an unsupported identity merge.','Shared-name and related-name groups remain distinct from broad civilization groups; neither verifies physical entity identity.']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--register',type=Path,action='append',required=True);p.add_argument('--pilot',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build(a.register,a.pilot);a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'groups':len(r['comparison_groups']),'claims':r['claims']}))
