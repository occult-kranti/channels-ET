#!/usr/bin/env python3
"""Deterministic source-bound profiles and typed question evidence, without inferred answers."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unicodedata

HERE=Path(__file__).resolve().parent
POLICY='transcript-knowledge-extraction-v2'
TYPES=['observed_question_answer','unverified_question_candidate','generated_reading_prompt','curated_comparison']
TOKEN=re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*",re.UNICODE)
STOP=set('the and that this with from have what when where which would could should about there their they them then than does will your you are was were been being also only some such into more most much very just like know think thing things question answer says said say please tell well because how who why can our out all any not yes for but its has had did doing these those something anything really means mean want need now one two'.split())
CONDITION=re.compile(r'\b(?:if|unless|provided|depending|may|might|could|conditional|perhaps|possibly|sometimes)\b',re.I)
TIME=re.compile(r'\b(?:today|tomorrow|yesterday|year|years|month|months|week|weeks|future|past|now|later|before|after)\b',re.I)
NEGATION=re.compile(r"\b(?:no|not|never|nor|cannot)\b|\b[^\W\d_]+n['’]t\b",re.I)
REFUSAL=re.compile(r'\b(?:cannot|can\s+not|may\s+not|will\s+not|unable\s+to)\s+(?:answer|respond|provide|tell|give|say)\b|\b(?:do\s+not|don[’\']t)\s+know\b',re.I)
COMMERCIAL=re.compile(r'\b(?:sponsor|sponsored|subscribe|subscription|discount|coupon|checkout|purchase|sale|advertisement|merchandise)\b',re.I)
QUESTIONS=re.compile(r'[^.!?]*\?+')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def encoded(obj):return (json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def save(path,obj):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(obj))
def ref(path,relative=None):p=Path(path);return {'file':str(p.relative_to(relative)) if relative else p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def normalized(text):return unicodedata.normalize('NFKC',text).strip()
def words(text):return [m.group().casefold().replace('’',"'") for m in TOKEN.finditer(text)]


def source_loader():
    spec=importlib.util.spec_from_file_location('canonical_sources',HERE.parent/'channel-lab/sources.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def span(text,start,end,role,**extra):
    if not 0<=start<end<=len(text):raise ValueError('Invalid evidence boundary')
    return {'start_character':start,'end_character':end,'span_sha256':sha(text[start:end].encode()),'role':role,**extra}


def trimmed(text,start,end):
    while start<end and text[start].isspace():start+=1
    while end>start and text[end-1].isspace():end-=1
    return start,end


def identifier(kind,r,supports,extra=''):
    seed={'policy':POLICY,'type':kind,'source_id':r['source_id'],'selected_edition_id':r['selected_edition_id'],
          'body_sha256':r['body_sha256'],'spans':[(s['start_character'],s['end_character'],s['role']) for s in supports],'extra':extra}
    return 'tk-'+sha(encoded(seed))[:24]


def terms(text,weights=None,n=3):
    count=Counter(w for w in words(text) if len(w)>2 and w not in STOP)
    return sorted(count,key=lambda w:(-(weights or {}).get(w,0),-count[w],w))[:n]


def surface_cues(text):
    return {'question_marks':text.count('?'),'conditional_modal_cues':len(CONDITION.findall(text)),
        'temporal_cues':len(TIME.findall(text)),'negation_cues':len(NEGATION.findall(text)),
        'digit_sequences':len(re.findall(r'\b\d+(?:[.,]\d+)*\b',text)),
        'refusal_uncertainty_cues':len(REFUSAL.findall(text)),
        'scope':'Surface patterns only; no resolution of logical scope, event dates, certainty or factual accuracy.'}


def sentence_candidates(text,max_words=60):
    """Complete punctuation-delimited units when short; explicitly flagged windows otherwise."""
    boundaries=[0]+[m.end() for m in re.finditer(r'(?<=[.!?])\s+|\n\s*\n',text)]+[len(text)]
    out=[]
    for a,b in zip(boundaries,boundaries[1:]):
        a,b=trimmed(text,a,b)
        if a>=b:continue
        ww=list(re.finditer(r'\S+',text[a:b]))
        if len(ww)<=max_words:
            out.append(span(text,a,b,'extractive_digest',complete_sentence_or_paragraph=True,words=len(ww)))
        else:
            for offset in range(0,len(ww),max_words):
                part=ww[offset:offset+max_words];start=a+part[0].start();end=a+part[-1].end()
                out.append(span(text,start,end,'extractive_digest',complete_sentence_or_paragraph=False,words=len(part)))
    return out


def extractive_digest(text,weights,max_total_words=180):
    candidates=sentence_candidates(text);selected=[];selected_sets=[];budget=max_total_words
    # One candidate from each positional third; within it, reward source TF-IDF terms
    # and penalize lexical overlap with already selected passages. No new model fit.
    for region in range(3):
        pool=[s for s in candidates if min(2,int(3*((s['start_character']+s['end_character'])/2)/max(1,len(text))))==region and s['words']<=budget]
        if not pool:continue
        def rank(s):
            ts=set(words(text[s['start_character']:s['end_character']]))
            relevance=sum(weights.get(t,0) for t in ts)
            redundancy=max((len(ts&old)/len(ts|old) if ts|old else 0 for old in selected_sets),default=0)
            return (relevance-.25*redundancy,-s['start_character'])
        best=max(pool,key=rank);selected.append(best);selected_sets.append(set(words(text[best['start_character']:best['end_character']])))
        budget-=best['words']
    if not selected and candidates:selected=[candidates[0]]
    selected.sort(key=lambda x:x['start_character'])
    if sum(s['words'] for s in selected)>max_total_words:raise ValueError('Digest word budget exceeded')
    for s in selected:
        a,b=s['start_character'],s['end_character']
        s['omitted_context']=a>0 or b<len(text)
        s['standalone_faithfulness_validated']=False
        before_start=max(0,a-200);after_end=min(len(text),b+200)
        s['context_before_span']=span(text,before_start,a,'neighboring_context_not_part_of_digest') if before_start<a else None
        s['context_after_span']=span(text,b,after_end,'neighboring_context_not_part_of_digest') if b<after_end else None
        s['context_scope']='Neighboring up-to200-character locators are navigation aids; inspect the full source to resolve antecedents and conditions.'
    return selected


def question_record(r,text,kind,qspan,aspans=None,context=None,origin='asr_punctuation',printed_id=None,weights=None):
    aspans=aspans or [];support=[qspan]+aspans+([context] if context else [])
    q=text[qspan['start_character']:qspan['end_character']]
    answer='\n'.join(text[s['start_character']:s['end_character']] for s in aspans) if aspans else None
    topic=terms(q,weights);available=bool(re.sub(r'\[[^\]]*\]','',q).strip())
    display=('Printed prompt '+str(printed_id)+': ' if kind=='observed_question_answer' else 'Question candidate about ')+(' / '.join(topic) or 'unspecified content')
    if not available:display='Publisher prompt text unavailable ('+str(printed_id)+')'
    flags=[]
    if any(c in q for c in ['"','“','”','‘']):flags.append('quotation_characters_present_not_speaker_identification')
    if '\n' in q:flags.append('source_line_wrap_preserved')
    if len(q.split())>120:flags.append('long_punctuation_unit_may_contain_multiple_utterances')
    if COMMERCIAL.search(q+(text[context['start_character']:context['end_character']] if context else '')):flags.append('commercial_surface_cue_present')
    if REFUSAL.search(answer or ''):flags.append('response_contains_refusal_or_uncertainty_cue')
    record={'record_id':identifier(kind,r,support),'type':kind,'source_id':r['source_id'],
        'selected_edition_id':r['selected_edition_id'],'body_sha256':r['body_sha256'],
        'question_origin':origin,'display_question':display,'question_text_available':available,
        'answer_status':'publisher_labeled_response_not_truth_validation' if aspans else 'not_identified',
        'answer_paraphrase':None,'speaker_status':'publisher_printed_roles_unverified' if origin=='publisher_printed' else 'unknown',
        'addressed_to_claimed_entity_verified':False,'topic_terms':topic,'printed_question_id':printed_id,
        'reading_status':'automatic_layout_extraction_not_human_verified' if origin=='publisher_printed' else 'automatic_punctuation_candidate_not_validated_question',
        'question_span':qspan,'answer_spans':aspans,'context_span':context,'flags':flags,
        'question_boundary_scope':'Publisher printed prompt boundary' if origin=='publisher_printed' else 'Punctuation-delimited cue may include fragments, quoted speech or multiple utterances; line wraps are preserved.',
        'context_boundary_scope':'At most600following characters; fixed truncation, not an answer boundary' if context else None,
        'conditions_status':'not_interpreted','time_scope_status':'not_interpreted',
        'question_text':q,'answer_text':answer,'context_text':text[context['start_character']:context['end_character']] if context else None,
        'supports':[{**s,'text':text[s['start_character']:s['end_character']]} for s in support]}
    return record


def align_turns(text,turns):
    cursor=0;out=[]
    for t in turns:
        body=normalized(t['text'])
        if not body:continue
        start=text.find(body,cursor)
        if start<0 or text[cursor:start].strip():raise ValueError('Printed turn cannot be bound exactly in canonical body')
        end=start+len(body);out.append((t,span(text,start,end,t['role'],turn_id=t['turn_id'])))
        cursor=end
    if text[cursor:].strip():raise ValueError('Printed turn stream does not cover body')
    return out


def documentary_records(r,text,weights):
    raw=load(r['text_artifact']['path']);turns=align_turns(text,raw['turns']);out=[];unpaired=0
    for i,(t,qspan) in enumerate(turns):
        if t['role']!='questioner':continue
        responses=[]
        for following,locator in turns[i+1:]:
            if following['role']=='questioner':break
            if following['role']!='response':break
            if t.get('question_id')!=following.get('question_id'):break
            responses.append(locator)
        aspans=[span(text,responses[0]['start_character'],responses[-1]['end_character'],'publisher_response',
                     turn_ids=[x['turn_id'] for x in responses])] if responses else []
        kind='observed_question_answer' if aspans else 'unverified_question_candidate'
        unpaired+=not bool(aspans)
        out.append(question_record(r,text,kind,qspan,aspans,origin='publisher_printed',printed_id=t.get('question_id'),weights=weights))
    return out,{'printed_questioner_turns':sum(t['role']=='questioner' for t,_ in turns),
        'printed_response_turns':sum(t['role']=='response' for t,_ in turns),'unpaired_printed_prompts':unpaired,
        'responses_without_present_questioner_turn':sum(t['role']=='response' and t.get('question_id') not in {q.get('question_id') for q,_ in turns if q['role']=='questioner'} for t,_ in turns)}


def punctuation_records(r,text,weights):
    out=[];skipped=[]
    machine=r['text_origin'] in {'local_asr','machine_asr','retained_local_asr','platform_auto_caption','linked_publisher_caption'} or 'asr' in r['document_kind']
    for m in QUESTIONS.finditer(text):
        a,b=trimmed(text,m.start(),m.end());q=text[a:b]
        if not words(q):
            skipped.append({'start_character':a,'end_character':b,'reason':'no_lexical_tokens'});continue
        qspan=span(text,a,b,'question_candidate')
        ca,cb=trimmed(text,b,min(len(text),b+600));context=span(text,ca,cb,'following_context_not_an_identified_answer') if ca<cb else None
        out.append(question_record(r,text,'unverified_question_candidate',qspan,context=context,
            origin='machine_or_publisher_caption_punctuation' if machine else 'written_punctuation',weights=weights))
    return out,{'punctuation_matches':len(out)+len(skipped),'skipped_short_cues':skipped}


def public_record(record):
    # Shard header carries canonical source/edition/body fields once.
    return {k:v for k,v in record.items() if k not in {'source_id','selected_edition_id','body_sha256','question_text','answer_text','context_text','supports'}}


def make_source(doc,analysis_doc,topics):
    r,text=doc['record'],doc['text'];keywords=analysis_doc['keywords'];weights={x['term']:x['weight'] for x in keywords if ' ' not in x['term']}
    digest=extractive_digest(text,weights)
    if r['channel_id']=='ra-law-of-one':records,disposition=documentary_records(r,text,weights)
    else:records,disposition=punctuation_records(r,text,weights)
    top=[x['term'] for x in keywords[:5]]
    generated='When reading this source, how are '+(' / '.join(top[:3]) or 'its main subjects')+' framed, and which conditions or uncertainties qualify those statements?'
    generated_record={'record_id':identifier('generated_reading_prompt',r,digest,generated),'type':'generated_reading_prompt',
        'source_id':r['source_id'],'selected_edition_id':r['selected_edition_id'],'body_sha256':r['body_sha256'],
        'question_origin':'generated_template_not_observed_speech','display_question':generated,'question_text_available':False,
        'answer_status':'not_identified','answer_paraphrase':None,'speaker_status':'not_applicable_generated_prompt',
        'addressed_to_claimed_entity_verified':False,'topic_terms':top[:3],'printed_question_id':None,
        'reading_status':'machine_generated_reading_task_not_a_source_claim','question_span':None,'answer_spans':[],
        'context_span':None,'flags':[],'conditions_status':'reader_review_required','time_scope_status':'reader_review_required',
        'question_text':generated,'answer_text':None,'context_text':None,
        'supports':[{**s,'text':text[s['start_character']:s['end_character']]} for s in digest]}
    records.append(generated_record);counts={t:sum(x['type']==t for x in records) for t in TYPES}
    summary=(f"Automatic source profile: {r['words']:,} words in the selected {r['document_kind'].replace('_',' ')} edition were processed. "
        +'Ranked lexical cues: '+(', '.join(top) if top else 'none available')+'. '
        +f"The extractor found {counts['observed_question_answer']} publisher-labeled prompt/response pairs and {counts['unverified_question_candidate']} unverified question candidates. "
        +'This is a structured lexical outline, not a close reading or an interpretation of speaker claims.')
    profile={k:r.get(k) for k in ['source_id','selected_edition_id','body_sha256','title','source_url','channel_id','channel_name','creator_id','creator_name','publisher_id','publisher_name','claimed_labels','document_kind','text_origin','publication_date','words']}
    profile.update(profile_id='profile-'+sha((r['source_id']+r['body_sha256']+POLICY).encode())[:24],summary_kind='automatic_source_profile',summary=summary,
        top_terms=keywords,topic_profile=[{'topic_id':t['topic_id'],'label':t['label'],'weight':w} for t,w in zip(topics,analysis_doc['topic_weights'])],
        topic_scope='Frozen NMF factor weights, not topic probabilities or verified doctrines.',cues=surface_cues(text),records_by_type=counts,
        representative_spans=digest,coverage={'processed_words':len(text.split()),'total_words':r['words'],'human_read':False,'audio_listened':False},
        reading_status='automatically_processed_not_close_read',extractive_digest_scope='Navigational excerpts, not a validated standalone summary: up to180words in three position-diverse, keyword-weighted low-redundancy passages. Long unpunctuated units are flagged windows; conditions/coreference can require omitted context.',
        extraction_disposition=disposition)
    private_profile={**profile,'extractive_summary':[{**s,'text':text[s['start_character']:s['end_character']]} for s in digest]}
    return profile,private_profile,records


def run(frame_path,analysis_path,output,source_ids=None,resume=False):
    output=Path(output).resolve();frame_path=Path(frame_path);analysis_path=Path(analysis_path)
    if not str(output).startswith('/dev/shm/transcript-knowledge-2026-11/'):raise ValueError('New extraction must stage in its declared RAM workspace')
    code_sha=sha(Path(__file__).read_bytes());frame_sha=sha(frame_path.read_bytes());analysis_sha=sha(analysis_path.read_bytes())
    analysis=load(analysis_path)
    if analysis['bindings']['frame_sha256']!=frame_sha:raise ValueError('Analytic keywords are bound to another canonical edition frame')
    docs=source_loader().load_frame(frame_path);all_count=len(docs);requested=set(source_ids or [])
    if requested:
        if not requested<={d['record']['source_id'] for d in docs}:raise ValueError('Unknown pilot source ID')
        docs=[d for d in docs if d['record']['source_id'] in requested]
    contract={'policy':POLICY,'script_sha256':code_sha,'frame_sha256':frame_sha,'analysis_sha256':analysis_sha,
        'selected_source_ids':[d['record']['source_id'] for d in docs]}
    if output.exists():
        if not resume:raise ValueError('Extraction editions are immutable; choose fresh output or explicit resume')
        if load(output/'contract-private.json')!=contract:raise ValueError('Resume contract differs')
        if (output/'output-manifest.json').exists():
            manifest=load(output/'output-manifest.json')
            for item in manifest['public_allowlist']:
                p=output/item['file']
                if p.stat().st_size!=item['bytes'] or sha(p.read_bytes())!=item['sha256']:raise ValueError('Completed output changed')
            pm=manifest['private_manifest'];p=output/pm['file']
            if p.stat().st_size!=pm['bytes'] or sha(p.read_bytes())!=pm['sha256']:raise ValueError('Completed private manifest changed')
            private_manifest=load(p)
            for item in [private_manifest['question_bank'],private_manifest['profiles']]:
                p=output/item['file']
                if p.stat().st_size!=item['bytes'] or sha(p.read_bytes())!=item['sha256']:raise ValueError('Completed private bank changed')
            print(json.dumps({'status':'verified_complete_cache_hit','sources':len(docs),'inference_runs':0}));return
    else:output.mkdir(parents=True);save(output/'contract-private.json',contract)
    by={d['source_id']:d for d in analysis['documents']};profiles=[];private_profiles=[];all_records=[];sources=[];cache_hits=0
    for d in docs:
        r=d['record'];cache=output/'private/sources'/(r['source_id']+'.json')
        if cache.exists():
            cached=load(cache)
            if cached['body_sha256']!=r['body_sha256'] or cached['script_sha256']!=code_sha:raise ValueError('Cached source edition differs')
            profile,private_profile,records=cached['profile'],cached['private_profile'],cached['records'];cache_hits+=1
        else:
            profile,private_profile,records=make_source(d,by[r['source_id']],analysis['topics'])
            save(cache,{'body_sha256':r['body_sha256'],'script_sha256':code_sha,'profile':profile,'private_profile':private_profile,'records':records})
        for rec in records:
            for s in rec['supports']:
                raw=d['text'][s['start_character']:s['end_character']]
                if raw!=s['text'] or sha(raw.encode())!=s['span_sha256']:raise ValueError('Extracted evidence changed')
        profiles.append(profile);private_profiles.append(private_profile);all_records.extend(records)
        path=output/'records'/(r['source_id']+'.json')
        save(path,{'source_id':r['source_id'],'body_sha256':r['body_sha256'],'selected_edition_id':r['selected_edition_id'],'records':[public_record(x) for x in records]})
        sources.append({'source_id':r['source_id'],'counts':profile['records_by_type'],'shard':ref(path,output)})
    ids=[r['record_id'] for r in all_records]
    if len(set(ids))!=len(ids):raise ValueError('Record identity collision')
    coverage={'canonical_frame_sources':all_count,'processed_sources':len(docs),'processed_words':sum(p['words'] for p in profiles),
        'records':len(all_records),'counts_by_type':dict(Counter(r['type'] for r in all_records)),
        'sources_without_unverified_candidates':sum(p['records_by_type']['unverified_question_candidate']==0 for p in profiles),
        'sources_without_documentary_pairs':sum(p['records_by_type']['observed_question_answer']==0 for p in profiles),
        'human_close_read_sources':0,'new_audio_listening_sessions':0,'question_candidates_are_answers':False}
    bindings={'frame_sha256':frame_sha,'registry_sha256':analysis['bindings']['registry_sha256'],'analysis_sha256':analysis_sha,'producer_sha256':code_sha,'policy':POLICY}
    save(output/'profiles.json',{'schema_version':1,'bindings':bindings,'coverage':coverage,'profiles':profiles})
    lightkeys=['record_id','type','source_id','display_question','topic_terms','answer_status','reading_status']
    save(output/'bank-index.json',{'schema_version':1,'bindings':bindings,'coverage':coverage,'record_types':TYPES,'sources':sources,
        'records':[{k:r[k] for k in lightkeys} for r in all_records],
        'limitations':['Publisher prompt-response boundaries are documentary layout evidence, not authenticated identity or factual validation.',
            'Automatic question cues can be rhetorical, quoted, promotional, or transcription errors; their following context is never labeled an answer.',
            'Generated reading prompts are research tasks, not questions observed in the source.',
            'Automatic source outlines and selected extracts do not imply manual understanding of every recording.',
            'Public records omit exact source questions/answers/context. The local private bank retains bound evidence for authorized source inspection.']})
    save(output/'private/profiles-private.json',{'profiles':private_profiles,'bindings':bindings})
    bank=output/'private/question-bank.jsonl'
    with bank.open('wb') as stream:
        for r in all_records:stream.write(encoded(r))
    save(output/'private-manifest.json',{'bindings':bindings,'question_bank':ref(bank,output),'profiles':ref(output/'private/profiles-private.json',output),
        'source_cache_hits':cache_hits,'newly_processed_sources':len(docs)-cache_hits})
    allow=[ref(output/'profiles.json',output),ref(output/'bank-index.json',output)]+[s['shard'] for s in sources]
    save(output/'output-manifest.json',{'status':'completed','public_allowlist':allow,'private_manifest':ref(output/'private-manifest.json',output)})
    from verify_extraction import verify
    verify(output)
    print(json.dumps({'status':'completed','coverage':coverage,'public_bytes':sum(r['bytes'] for r in allow),'private_bank_bytes':bank.stat().st_size,'output':str(output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frame',required=True,type=Path);p.add_argument('--analysis',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--source-id',action='append');p.add_argument('--resume',action='store_true')
    a=p.parse_args();run(a.frame,a.analysis,a.output,a.source_id,a.resume)
