#!/usr/bin/env python3
"""Receipt-bound, session-level exploratory comparison of Ra and Bashar contexts.

No acquisition, speech recognition, upload, or claim-truth inference is performed.
Full text, question records and input paths remain in private outputs only.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import datetime as dt
import hashlib
import inspect
import json
import math
from pathlib import Path
import re
import sqlite3
import os
import unicodedata
from urllib.parse import urlsplit, urlunsplit
import warnings

SCHEMA = 1
MAX_DOCUMENTS = 1500
MAX_CHARS = 30_000_000
TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)
HASH = re.compile(r'^[a-f0-9]{64}$')
KINDS = {'publisher_transcript', 'machine_asr', 'authored_reference'}
ROLES = {'questioner', 'response', 'other', 'unknown'}
SEEDS = (11, 23, 47)
FILLERS = {'okay','ok','yeah','yes','uh','um','oh','right','well','really','actually','basically',
           'gonna','wanna','got','gets','getting','just','like','know','said','say','says','saying',
           "i'm","it's","that's","you're","we're","they're","there's","let's","you've","i've",'thank','thanks'}
NAMES = {'ra','bashar','darryl','anka','carla','rueckert','don','elkins','jim','mccarty',
         'llresearch','ll','research','questioner','instrument','adoni','adonai'}
KEYWORDS = {
 'ontology': ['reality','realities','existence','exists','consciousness','awareness','creation','creator','density','densities'],
 'agency_free_will': ['choice','choices','choose','choosing','chosen','will','freedom','free','permission','responsibility'],
 'ethics_polarity': ['service','self','others','polarity','polarities','positive','negative','compassion','acceptance','judgment'],
 'fear': ['fear','fears','afraid','anxiety','anxious','worry','worried','doubt','doubts','trust'],
 'practices': ['meditation','meditate','meditating','practice','practices','breath','breathing','visualization','ritual','exercise'],
 'time_probability': ['time','times','future','past','present','probability','probabilities','parallel','timeline','timelines','possibility','possible'],
 'contact': ['contact','contacts','contacted','alien','aliens','extraterrestrial','extraterrestrials','ufo','ufos','channeling','channelling'],
 'healing_body': ['healing','heal','health','body','bodies','physical','illness','disease','pain','energy','energies'],
 'knowing_uncertainty': ['know','knowing','knowledge','understand','understanding','believe','belief','beliefs','perhaps','possibly','uncertain'],
 'relationships': ['love','loving','relationship','relationships','partner','partners','family','friend','friends','forgiveness'],
}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def safe_path(value, *, private=False, exists=True):
    if not isinstance(value,(str,Path)) or not str(value) or '\0' in str(value):raise ValueError('An absolute local path is required')
    path=Path(value)
    if not path.is_absolute() or '..' in path.parts:raise ValueError('Paths must be absolute without parent traversal')
    for parent in (path,*path.parents):
        if parent.is_symlink():raise ValueError('Symlink paths are not admitted')
        marker=parent/'.git'
        if private and marker.exists() and not (marker.is_dir() and not any(marker.iterdir())):
            raise ValueError('Full text and analysis outputs must remain outside Git')
    if exists and not path.is_file():raise ValueError('Expected source file is missing')
    return path

def read_json(path, *, private=False, limit=32*1024**2):
    path=safe_path(path,private=private)
    if path.stat().st_size>limit:raise ValueError('Input JSON exceeds its declared bound')
    return json.loads(path.read_text(encoding='utf8'))

def fixture(value):
    if isinstance(value,dict):return value.get('fixture_only') is True or any(fixture(v) for v in value.values())
    if isinstance(value,list):return any(fixture(v) for v in value)
    return False

def artifact(row, *, private=False, cache=None):
    if not isinstance(row,dict):raise ValueError('Artifact binding must be an object')
    path=safe_path(row.get('path'),private=private)
    size,digest=row.get('bytes'),row.get('sha256')
    if isinstance(size,bool) or not isinstance(size,int) or size<1 or not isinstance(digest,str) or not HASH.fullmatch(digest):
        raise ValueError('Artifact requires a positive byte count and SHA256')
    st=path.stat();key=(str(path),st.st_size,st.st_mtime_ns,st.st_ino)
    if st.st_size!=size:raise ValueError('Source artifact size changed')
    actual=cache.get(key) if cache is not None else None
    if actual is None:
        actual=sha(path)
        if cache is not None:cache[key]=actual
    if actual!=digest:raise ValueError('Source artifact hash changed')
    return path

def tokens(text):
    return TOKEN.findall(unicodedata.normalize('NFKC',text).replace('’',"'").lower())

def safe_url(value):
    p=urlsplit(str(value or ''))
    if p.scheme not in {'https','http'} or not p.hostname or p.username or p.password:return None
    return urlunsplit((p.scheme,p.netloc,p.path,'',''))

def number(value,name, *, allow_none=True):
    if value is None and allow_none:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError(name+' must be finite and nonnegative')
    return value

def validate_derivation(row,text_doc,evidence):
    """Verify the concrete extraction/ASR contract, not merely a caller's label."""
    roles=defaultdict(list)
    for ref in evidence:roles[ref['role']].append(ref)
    sid=row['source_id'];kind=row['source_kind']
    if kind=='machine_asr':
        if len(roles['asr_receipt'])!=1 or len(roles['source_audio'])!=1:raise ValueError('One completed ASR receipt and exact original audio are required')
        receipt=read_json(roles['asr_receipt'][0]['path'])
        if receipt.get('status')!='completed' or receipt.get('sourceId')!=sid or receipt.get('sourceAudioSha256')!=roles['source_audio'][0]['sha256']:
            raise ValueError('ASR completion, identity or media binding differs')
        outputs=roles['asr_output'];expected={x['name']:x for x in receipt.get('outputs',[])}
        for ref in outputs:
            name=Path(ref['path']).name
            if name not in expected or any(ref[k]!=expected[name][k] for k in ('bytes','sha256')):raise ValueError('ASR output binding differs from completed receipt')
        segment_refs=[r for r in outputs if Path(r['path']).name=='segments.jsonl']
        if len(segment_refs)!=1:raise ValueError('Original ASR segment stream is required')
        original=[json.loads(line) for line in Path(segment_refs[0]['path']).read_text().splitlines() if line.strip()]
        normalized=text_doc.get('turns',[])
        if len(original)!=len(normalized) or receipt.get('segments')!=len(original):raise ValueError('ASR segment count changed during normalization')
        for source,turn in zip(original,normalized):
            if source['text']!=turn['text'] or turn['role']!='unknown':raise ValueError('ASR text or speaker identity was changed during normalization')
            if turn.get('start_seconds')!=source['start'] or turn.get('end_seconds')!=source['end']:raise ValueError('ASR timestamp changed during normalization')
        if receipt.get('words')!=len(text_doc['text'].split()):raise ValueError('ASR whitespace word count differs')
    elif kind=='publisher_transcript':
        if len(roles['extraction_receipt'])!=1:raise ValueError('Publisher text requires its extraction receipt')
        receipt=read_json(roles['extraction_receipt'][0]['path'])
        if receipt.get('source_id')!=sid or receipt.get('edition_id')!=row['edition_id']:raise ValueError('Publisher extraction source or edition differs')
        norm=receipt.get('normalized',{})
        if any(norm.get(k)!=row['text_artifact'].get(k) for k in ('path','bytes','sha256')):raise ValueError('Publisher normalized artifact differs from extraction receipt')
        source=receipt.get('source',{})
        if not any(all(ref.get(k)==source.get(k) for k in ('path','bytes','sha256')) for ref in roles['source']):raise ValueError('Publisher original page differs from extraction receipt')
        if receipt.get('turns')!=len(text_doc.get('turns',[])) or receipt.get('whitespace_words')!=len(text_doc['text'].split()):raise ValueError('Publisher extraction counts changed')

def load_manifests(paths, *, allow_fixtures=False):
    docs=[];excluded=[];aliases=[];audit=[];cache={};seen={};families={};texts={};char_count=0;rows_seen=0
    for supplied in paths:
        path=safe_path(supplied,private=True);manifest=read_json(path,private=True)
        if manifest.get('schema_version')!=SCHEMA or not isinstance(manifest.get('records'),list):raise ValueError('Expected a versioned records manifest')
        if fixture(manifest) and not allow_fixtures:raise ValueError('Synthetic inputs are not actual observations')
        expected=manifest.get('expected_source_ids')
        if expected is not None:
            if not isinstance(expected,list) or not all(isinstance(s,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:_.-]{0,199}',s) for s in expected) or len(expected)!=len(set(expected)):
                raise ValueError('Expected source identifiers must be a unique valid list')
            observed=[r.get('source_id') for r in manifest['records']]
            if any(not isinstance(s,str) for s in observed) or set(expected)!=set(observed):
                raise ValueError('Declared expected source set differs from manifest records; missing sources require explicit status rows')
        audit.append({'path':str(path),'sha256':sha(path),'record_count':len(manifest['records']),
                      'expected_source_ids':manifest.get('expected_source_ids'),'scope':manifest.get('scope')})
        for row in manifest['records']:
            rows_seen+=1
            if rows_seen>MAX_DOCUMENTS:raise ValueError('Too many source records')
            sid=row.get('source_id')
            if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:_.-]{0,199}',sid):raise ValueError('Invalid source identifier')
            if row.get('corpus') not in {'ra','bashar'} or row.get('source_kind') not in KINDS:raise ValueError('Unsupported corpus or source kind')
            if row.get('collection_status')!='retrieved' or row.get('coverage_status')!='full':
                excluded.append({'source_id':sid,'corpus':row['corpus'],'source_kind':row['source_kind'],'source_format':row.get('source_format'),'reason':'not_full_retained_text','collection_status':row.get('collection_status'),'coverage_status':row.get('coverage_status')});continue
            if row.get('language')!='en':
                excluded.append({'source_id':sid,'reason':'not_declared_English'});continue
            text_path=artifact(row.get('text_artifact'),private=True,cache=cache)
            text_doc=read_json(text_path,private=True)
            if fixture(text_doc) and not allow_fixtures:raise ValueError('Synthetic text cannot lose its fixture marker')
            if text_doc.get('source_id')!=sid or not isinstance(text_doc.get('text'),str):raise ValueError('Normalized text identity differs')
            evidence=row.get('evidence')
            if not isinstance(evidence,list) or not evidence:raise ValueError('Original acquisition or ASR evidence is required')
            for ref in evidence:
                p=artifact(ref,cache=cache)
                if not isinstance(ref.get('role'),str):raise ValueError('Evidence role is required')
                if p.suffix=='.json' and p.stat().st_size<=16*1024**2 and fixture(read_json(p)) and not allow_fixtures:
                    raise ValueError('Fixture marker in upstream evidence cannot be erased')
            text=text_doc['text'];turns=text_doc.get('turns',[])
            if not isinstance(turns,list):raise ValueError('Turns must be an array')
            turn_ids=set()
            for turn in turns:
                if not isinstance(turn,dict) or turn.get('role') not in ROLES or not isinstance(turn.get('text'),str):raise ValueError('Invalid normalized turn')
                tid=turn.get('turn_id')
                if not isinstance(tid,str) or not tid or tid in turn_ids:raise ValueError('Turn identifiers must be unique within a document')
                turn_ids.add(tid)
            if turns and text!='\n'.join(t['text'] for t in turns):raise ValueError('Full text differs from its ordered turns')
            validate_derivation(row,text_doc,evidence)
            session=row.get('session_id');edition=row.get('edition_id');family=row.get('duplicate_family_id')
            if not all(isinstance(v,str) and 0<len(v)<250 for v in (session,edition,family)):raise ValueError('Session, edition and duplicate family are required')
            digest=hashlib.sha256(text.encode()).hexdigest();identity=(row['corpus'],session,row['source_kind'])
            if sid in seen:
                if seen[sid]!=(digest,edition):raise ValueError('Same source ID has conflicting editions or text')
                aliases.append({'source_id':sid,'reason':'repeated_source_record','retained_as':sid});continue
            seen[sid]=(digest,edition)
            if identity in families:
                previous=families[identity]
                if previous['digest']!=digest:raise ValueError('Multiple text editions of one session require an explicit separate comparison')
                aliases.append({'source_id':sid,'reason':'same_session_edition_duplicate','retained_as':previous['source_id']});continue
            if digest in texts:
                aliases.append({'source_id':sid,'reason':'exact_text_duplicate','retained_as':texts[digest]});continue
            families[identity]={'digest':digest,'source_id':sid};texts[digest]=sid
            tt=tokens(text)
            if len(tt)<30:
                excluded.append({'source_id':sid,'reason':'fewer_than_30_tokens'});continue
            char_count+=len(text)
            if char_count>MAX_CHARS:raise ValueError('Corpus exceeds the declared character bound')
            summary={k:row.get(k) for k in ('source_id','corpus','session_id','duplicate_family_id','edition_id','source_kind','source_format','publisher',
                'title','published_at','speaker_attribution_status','original_session_identity','source_editing_notes','audio_completeness_notice')}
            summary.update(source_url=safe_url(row.get('source_url')),language='en',coverage_status='full',
                attribution_status=row.get('speaker_attribution_status','not_verified'),whitespace_words=len(text.split()),token_count=len(tt),
                turn_count=len(turns),duration_seconds=number(row.get('duration_seconds',row.get('audio_duration_seconds')),'Duration'),
                text_sha256=digest,text_artifact_sha256=row['text_artifact']['sha256'],
                evidence_sha256=[r['sha256'] for r in evidence],human_accuracy_validated=False,
                unit='reference_document' if row['source_kind']=='authored_reference' else 'published_session_or_recording')
            docs.append({'summary':summary,'text':text,'tokens':tt,'turns':turns})
    docs.sort(key=lambda d:(d['summary']['corpus'],d['summary']['published_at'] or '',d['summary']['source_id']))
    codes=Counter()
    for d in docs:
        c=d['summary']['corpus'];codes[c]+=1;d['summary']['short_id']=('R' if c=='ra' else 'B')+f'{codes[c]:03d}'
    return docs,excluded,aliases,audit

def keyword_rates(tt):
    counts=Counter(tt)
    return {key:{'mentions':sum(counts[w] for w in words),'per_1000_tokens':sum(counts[w] for w in words)*1000/len(tt)} for key,words in KEYWORDS.items()}

def qa_records(doc):
    s=doc['summary'];turns=doc['turns'];pairs=[];candidates=[];unpaired=0
    if s['source_kind']=='publisher_transcript':
        for i,turn in enumerate(turns):
            if turn['role']!='questioner':continue
            responses=[]
            for following in turns[i+1:]:
                if following['role']=='questioner':break
                if following['role']=='response':
                    if turn.get('question_id') and following.get('question_id') and turn['question_id']!=following['question_id']:break
                    responses.append(following)
            if responses:
                pairs.append({'pair_id':s['source_id']+':'+turn['turn_id'],'source_id':s['source_id'],'session_id':s['session_id'],
                    'question_id':turn.get('question_id'),'question_turn_id':turn['turn_id'],'response_turn_ids':[r['turn_id'] for r in responses],
                    'question_text':turn['text'],'response_text':'\n'.join(r['text'] for r in responses),
                    'pair_kind':'publisher_labeled_prompt_response','question_mark_present':'?' in turn['text'],
                    'question_text_available':not bracket_only(turn['text']),
                    'human_substantive_question_validation':False,'speaker_or_entity_identity_verified':False})
            else:unpaired+=1
    if s['source_kind']=='machine_asr':
        for i,t in enumerate(turns):
            if '?' in t['text']:
                candidates.append({'candidate_id':s['source_id']+':'+t['turn_id'],'source_id':s['source_id'],'session_id':s['session_id'],
                    'turn_id':t['turn_id'],'text':t['text'],'following_context':turns[i+1]['text'] if i+1<len(turns) else None,
                    'kind':'unverified_ASR_punctuation_candidate','answer_identified':False})
    question_ids={t.get('question_id') for t in turns if t['role']=='questioner'}
    return pairs,candidates,{'publisher_prompt_response_pairs':len(pairs),'publisher_prompts_with_question_mark':sum(p['question_mark_present'] for p in pairs),
        'publisher_pairs_with_missing_question_text':sum(not p['question_text_available'] for p in pairs),
        'bracket_only_turns':sum(bracket_only(t['text']) for t in turns),
        'responses_without_present_questioner_turn':sum(t['role']=='response' and t.get('question_id') not in question_ids for t in turns),
        'unpaired_publisher_prompts':unpaired,'punctuation_candidates':len(candidates),'verified_substantive_questions':0}

def bracket_only(text):
    return bool(re.fullmatch(r'(?:\s*\[[^\]]*\]\s*)+',text))

def token_variant(doc,variant):
    tt=doc['tokens']
    if variant=='response_only' and doc['summary']['corpus']=='ra':tt=tokens('\n'.join(t['text'] for t in doc['turns'] if t['role']=='response'))
    if variant=='matched_length':
        if len(tt)<1500:return []
        start=(len(tt)-1500)//2;tt=tt[start:start+1500]
    if variant=='bracket_removed':tt=tokens(re.sub(r'\[[^\]]*\]',' ',doc['text']))
    if variant in {'content','name_masked','matched_length','response_only','bracket_removed'}:tt=[x for x in tt if x not in FILLERS]
    if variant in {'name_masked','matched_length','response_only','bracket_removed'}:tt=[x for x in tt if x not in NAMES]
    return tt

def fit_lexical(docs,variant):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    chosen=[(d,token_variant(d,variant)) for d in docs]
    chosen=[(d,tt) for d,tt in chosen if len(tt)>=30]
    ids=[d['summary']['source_id'] for d,tt in chosen]
    if len(chosen)<2:return {'status':'insufficient_documents','source_ids':ids,'cosine_matrix':None},None,None,chosen
    stop=set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}
    vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,stop_words=sorted(stop),
        ngram_range=(1,2),sublinear_tf=True,norm='l2',smooth_idf=True,min_df=2 if len(chosen)>=5 else 1,max_df=1.0,max_features=12000)
    try:X=vec.fit_transform(' '.join(tt) for d,tt in chosen)
    except ValueError:return {'status':'empty_vocabulary','source_ids':ids,'cosine_matrix':None},None,None,chosen
    if X.shape[1]<2 or (np.asarray(X.sum(axis=1)).ravel()==0).any():
        return {'status':'empty_document_vector','source_ids':ids,'cosine_matrix':None},None,None,chosen
    names=vec.get_feature_names_out();cos=np.clip(cosine_similarity(X),0,1);groups=defaultdict(list)
    for i in range(len(chosen)):
        for j in range(i+1,len(chosen)):
            a=chosen[i][0]['summary']['corpus'];b=chosen[j][0]['summary']['corpus']
            groups[a+'_within' if a==b else 'between_corpora'].append(float(cos[i,j]))
    pair_summary={k:{'pairs':len(v),'mean':float(np.mean(v)),'minimum':min(v),'maximum':max(v)} for k,v in groups.items()}
    top={ids[i]:[str(names[j]) for j in X.getrow(i).toarray().ravel().argsort()[-12:][::-1] if X[i,j]>0] for i in range(len(ids))}
    neg={w:w in set(names) for w in ('no','not','never','nor')}
    result={'status':'fitted','variant':variant,'source_ids':ids,'features':len(names),'cosine_matrix':cos.tolist(),
        'pair_summary':pair_summary,'top_terms_by_source':top,'negation_unigram_retained':neg,
        'scope':'Shared vocabulary; pair values are dependent and are not agreement, belief, accuracy or origin probabilities.'}
    return result,X,vec,chosen

def topic_and_clusters(X,vec,chosen):
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    from sklearn.decomposition import NMF, TruncatedSVD
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score,adjusted_rand_score
    from sklearn.metrics.pairwise import cosine_similarity
    n,p=X.shape;ids=[d['summary']['source_id'] for d,tt in chosen];terms=vec.get_feature_names_out()
    maxk=min(8,n-1,p-1)
    if maxk<2:return {'status':'insufficient_documents'}, {'status':'insufficient_documents'}
    candidates=[];models={};cluster_candidates=[];cluster_models={}
    for k in range(2,maxk+1):
        fitted=[];labels=[];sil=[]
        for seed in SEEDS:
            with warnings.catch_warnings(record=True) as notices:
                warnings.simplefilter('always');model=NMF(n_components=k,init='nndsvdar',random_state=seed,max_iter=800,tol=1e-4)
                W=model.fit_transform(X)
            fitted.append((model,W,len(notices)>0))
            km=KMeans(n_clusters=k,n_init=10,random_state=seed,max_iter=500);lab=km.fit_predict(X)
            unique=len(set(lab));score=float(silhouette_score(X,lab,metric='cosine')) if 1<unique<n else None
            labels.append(lab);sil.append(score)
        stable=[]
        for a in range(len(SEEDS)):
            for b in range(a+1,len(SEEDS)):
                m=cosine_similarity(fitted[a][0].components_,fitted[b][0].components_);rr,cc=linear_sum_assignment(-m);stable.append(float(m[rr,cc].mean()))
        model,W,warn=fitted[0];mass=W.sum(axis=0);concentration=[]
        for t in range(k):
            weights=W[:,t]/mass[t] if mass[t]>0 else np.zeros(n)
            concentration.append({'effective_documents':float(1/np.sum(weights**2)) if np.sum(weights**2)>0 else 0,
                                  'maximum_document_share':float(weights.max())})
        candidates.append({'k':k,'reconstruction_errors':[float(m.reconstruction_err_) for m,w,warning in fitted],
            'iterations':[int(m.n_iter_) for m,w,warning in fitted],'any_convergence_warning':any(warning for m,w,warning in fitted),
            'seed_component_matching_mean':float(np.mean(stable)),'component_concentration':concentration})
        models[k]=(model,W)
        aris=[float(adjusted_rand_score(labels[a],labels[b])) for a in range(len(SEEDS)) for b in range(a+1,len(SEEDS))]
        cluster_candidates.append({'k':k,'cosine_silhouettes':sil,'seed_adjusted_rand_mean':float(np.mean(aris)),
            'cluster_sizes':dict(Counter(str(int(x)) for x in labels[0])),'singleton_clusters':sum(v==1 for v in Counter(labels[0]).values())})
        cluster_models[k]=labels[0]
    display_k=min(4,maxk);model,W=models[display_k];sums=W.sum(axis=1,keepdims=True);shares=np.divide(W,sums,out=np.zeros_like(W),where=sums>0)
    components=[]
    for index,row in enumerate(model.components_):
        components.append({'component':index+1,'terms':[str(terms[j]) for j in row.argsort()[-14:][::-1]],
            'source_context_means':{c:float(shares[[i for i,(d,t) in enumerate(chosen) if d['summary']['corpus']==c],index].mean()) for c in sorted({d['summary']['corpus'] for d,t in chosen})}})
    topics={'status':'exploratory_fits','candidate_diagnostics':candidates,'displayed_k':display_k,'seeds':list(SEEDS),
        'selection_rule':'Display four components where available, declared for readability; no optimal topic count or validated labels claimed.',
        'components':components,'document_weights':[{'source_id':sid,'weights':shares[i].tolist()} for i,sid in enumerate(ids)]}
    eligible=[r for r in cluster_candidates if r['cosine_silhouettes'][0] is not None]
    if not eligible:return topics,{'status':'no_valid_partition','candidates':cluster_candidates}
    best=max(eligible,key=lambda r:(r['cosine_silhouettes'][0],-r['k']));lab=cluster_models[best['k']]
    svd=TruncatedSVD(n_components=2,random_state=11);coords=svd.fit_transform(X)
    clusters={'status':'exploratory_partition','candidates':cluster_candidates,'selected_k':best['k'],
        'selection_rule':'Maximum seed-11 cosine silhouette among k=2..8; no corpus/entity labels used for fitting or selection.',
        'assignments':[{'source_id':sid,'cluster':int(lab[i])+1,'x':float(coords[i,0]),'y':float(coords[i,1])} for i,sid in enumerate(ids)],
        'svd_explained_variance_ratio':svd.explained_variance_ratio_.tolist(),
        'scope':'SVD positions visualize lexical vectors. Stable partitions can reflect editorial form, hosts, source kind, dates or vocabulary.'}
    return topics,clusters

def network(lexical,docs):
    ids=lexical.get('source_ids',[]);matrix=lexical.get('cosine_matrix');lookup={d['summary']['source_id']:d['summary'] for d in docs}
    if matrix is None:return {'status':'unavailable','nodes':[],'edges':[]}
    def edges_at(threshold):
        found={}
        for i,sid in enumerate(ids):
            nearest=sorted((j for j in range(len(ids)) if j!=i),key=lambda j:(-matrix[i][j],ids[j]))[:3]
            for j in nearest:
                if matrix[i][j]>=threshold:
                    a,b=sorted((i,j));found[(a,b)]={'source':ids[a],'target':ids[b],'cosine':matrix[a][b],
                        'cross_corpus':lookup[ids[a]]['corpus']!=lookup[ids[b]]['corpus']}
        return list(found.values())
    return {'status':'constructed','rule':'Undirected union of three nearest lexical neighbors with cosine >=0.15; schematic positions.',
        'nodes':[{'source_id':sid,'short_id':lookup[sid]['short_id'],'corpus':lookup[sid]['corpus']} for sid in ids],
        'edges':edges_at(.15),'threshold_sensitivity':[{'minimum_cosine':t,'edges':len(edges_at(t)),'cross_corpus_edges':sum(e['cross_corpus'] for e in edges_at(t))} for t in (.10,.15,.20,.25,.30,.40,.50)]}

def keyword_comparison(docs):
    rows=[]
    for corpus in ('bashar','ra'):
        group=[d for d in docs if d['summary']['corpus']==corpus]
        if not group:continue
        total=sum(len(d['tokens']) for d in group)
        for key in KEYWORDS:
            values=[d['summary']['keyword_rates'][key]['per_1000_tokens'] for d in group]
            mentions=sum(d['summary']['keyword_rates'][key]['mentions'] for d in group)
            rows.append({'corpus':corpus,'keyword_group':key,'documents':len(group),'equal_session_mean_per_1000':sum(values)/len(values),
                'pooled_token_rate_per_1000':mentions*1000/total,'minimum_session_rate':min(values),'maximum_session_rate':max(values),
                'documents_with_mentions':sum(v>0 for v in values),'total_mentions':mentions,'total_tokens':total})
    return rows

def near_duplicate_diagnostics(docs):
    """Observed five-token overlap; flags are not confirmed repost identities."""
    sets=[]
    for d in docs:
        tt=d['tokens'];sets.append({tuple(tt[i:i+5]) for i in range(max(0,len(tt)-4))})
    rows=[]
    for i in range(len(docs)):
        for j in range(i+1,len(docs)):
            a,b=sets[i],sets[j]
            if not a or not b:continue
            intersection=len(a&b);union=len(a)+len(b)-intersection
            rows.append({'a':docs[i]['summary']['source_id'],'b':docs[j]['summary']['source_id'],
                'same_corpus':docs[i]['summary']['corpus']==docs[j]['summary']['corpus'],
                'five_token_jaccard':intersection/union,'smaller_document_shingle_containment':intersection/min(len(a),len(b)),
                'shared_distinct_shingles':intersection})
    ordered=sorted(rows,key=lambda x:(-x['smaller_document_shingle_containment'],-x['five_token_jaccard']))
    return {'method':'Exact normalized five-token set overlap across primary documents; no approximate hashing.',
        'pairs_checked':len(rows),'highest_overlap_pairs':ordered[:30],
        'flagged_pairs':[r for r in ordered if r['five_token_jaccard']>=.20 or r['smaller_document_shingle_containment']>=.50],
        'scope':'Screening leads only. Shared teaching, repeated formulae, ads and editorial boilerplate can cause overlap; no automatic source removal or confirmed syndication assignment.'}

class FrozenEncoder:
    """Pinned MiniLM, complete nonoverlapping chunks, verified local numeric cache."""
    def __init__(self,model_dir,cache_dir):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np=np;self.cache=safe_path(cache_dir,private=True,exists=False);self.cache.mkdir(parents=True,exist_ok=True)
        model_dir=safe_path(model_dir,private=True,exists=False);self.manifest=read_json(model_dir/'manifest.json',private=True)
        if self.manifest.get('model')!='sentence-transformers/all-MiniLM-L6-v2' or self.manifest.get('revision')!='1110a243fdf4706b3f48f1d95db1a4f5529b4d41':
            raise ValueError('Only the explicitly pinned MiniLM edition is supported')
        for row in self.manifest['files']:
            if Path(row['path']).is_absolute() or '..' in Path(row['path']).parts:raise ValueError('Unsafe model path')
            artifact({'path':str(model_dir/row['path']),**{k:row[k] for k in ('bytes','sha256')}},private=True)
        self.binding={'model_manifest_sha256':sha(model_dir/'manifest.json'),'encoder_code_sha256':hashlib.sha256((inspect.getsource(FrozenEncoder.__init__)+inspect.getsource(FrozenEncoder.encode)).encode()).hexdigest(),
            'chunk_content_wordpieces':240,'document_pooling':'content-token-weighted normalized chunk vectors; final L2 normalization',
            'equal_chunk_sensitivity':True,'token_pooling':'attention-mask mean, including CLS/SEP as pinned pooling contract',
            'intra_op_threads':2,'inter_op_threads':1,'batch_size':16,'onnxruntime':ort.__version__}
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(model_dir/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.tokenizer=Tokenizer.from_file(str(model_dir/'tokenizer.json'));self.tokenizer.no_truncation();self.tokenizer.no_padding()
        if [self.tokenizer.token_to_id(t) for t in ('[PAD]','[CLS]','[SEP]')]!=[0,101,102]:raise ValueError('Unexpected tokenizer special IDs')
        self.input_names={x.name for x in self.session.get_inputs()}
    def encode(self,records):
        np=self.np;results={};pending=[];bykey={};requested={}
        for rid,text in records:
            text_hash=hashlib.sha256(text.encode()).hexdigest();binding={**self.binding,'input_text_sha256':text_hash};key=hashlib.sha256(encoded(binding).encode()).hexdigest()
            if rid in requested:raise ValueError('Duplicate semantic record identifier')
            requested[rid]=key
            if key in bykey:bykey[key]['rids'].append(rid);continue
            path=self.cache/(key+'.npz');receipt_path=self.cache/(key+'.json')
            if path.exists() or receipt_path.exists():
                if not(path.is_file() and receipt_path.is_file()):raise ValueError('Incomplete semantic cache entry remains for inspection')
                receipt=read_json(receipt_path,private=True)
                if receipt.get('binding')!=binding or sha(path)!=receipt.get('vectors_sha256'):raise ValueError('Semantic cache binding or vector bytes changed')
                loaded=np.load(path,allow_pickle=False)
                results[rid]=(loaded['weighted'],loaded['equal'],receipt['coverage']);continue
            ids=self.tokenizer.encode(text,add_special_tokens=False).ids
            chunks=[ids[start:start+240] for start in range(0,len(ids),240)]
            if not chunks:raise ValueError('Empty semantic input')
            row={'rids':[rid],'chunks':chunks,'path':path,'receipt_path':receipt_path,'binding':binding,'vectors':[],'lengths':[len(c) for c in chunks]}
            pending.append(row);bykey[key]=row
        seq=[];owners=[]
        for i,row in enumerate(pending):
            for chunk in row['chunks']:seq.append([101]+chunk+[102]);owners.append(i)
        for start in range(0,len(seq),16):
            batch=seq[start:start+16];width=max(map(len,batch));ids=np.zeros((len(batch),width),dtype=np.int64);mask=np.zeros_like(ids)
            for j,values in enumerate(batch):ids[j,:len(values)]=values;mask[j,:len(values)]=1
            inputs={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
            token=self.session.run(None,{k:v for k,v in inputs.items() if k in self.input_names})[0]
            vectors=(token*mask[:,:,None]).sum(axis=1)/mask.sum(axis=1)[:,None]
            vectors=vectors/np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-12)
            for owner,vector in zip(owners[start:start+16],vectors):pending[owner]['vectors'].append(vector)
            if start%512==0:print(json.dumps({'stage':'embedding_chunks','completed':min(start+16,len(seq)),'total':len(seq)}),flush=True)
        for row in pending:
            vectors=np.array(row['vectors']);weighted=np.average(vectors,axis=0,weights=row['lengths']);equal=vectors.mean(axis=0)
            weighted/=max(np.linalg.norm(weighted),1e-12);equal/=max(np.linalg.norm(equal),1e-12)
            coverage={'content_wordpieces':sum(row['lengths']),'processed_content_wordpieces':sum(row['lengths']),'chunks':len(row['lengths']),
                'minimum_chunk_content_tokens':min(row['lengths']),'maximum_chunk_content_tokens':max(row['lengths']),'truncated_content_wordpieces':0}
            np.savez_compressed(row['path'],weighted=weighted.astype('float32'),equal=equal.astype('float32'))
            write_json(row['receipt_path'],{'binding':row['binding'],'coverage':coverage,'vectors_sha256':sha(row['path'])})
            for rid in row['rids']:results[rid]=(weighted,equal,coverage)
        return results

def mask_source_markers(text):
    """Mask complete word tokens, preserving straight and curly contractions.

    Word boundaries treat apostrophes as boundaries: Don/LL would otherwise
    match inside don't/we'll and corrupt negation or future constructions.
    """
    return re.sub(r"[A-Za-z]+(?:['’][A-Za-z]+)*",lambda match:' ' if match.group().lower() in NAMES else match.group(),text)

def semantic_analysis(docs,pairs,candidates,model_dir,cache_dir):
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from scipy.stats import spearmanr
    if model_dir is None:return {'status':'not_run','reason':'No verified local embedding model supplied; lexical scores are not semantic agreement.'}
    encoder=FrozenEncoder(model_dir,cache_dir)
    encoded_docs=encoder.encode([(d['summary']['source_id'],mask_source_markers(d['text'])) for d in docs]);ids=[d['summary']['source_id'] for d in docs]
    weighted=np.vstack([encoded_docs[sid][0] for sid in ids]);equal=np.vstack([encoded_docs[sid][1] for sid in ids])
    wm=np.clip(cosine_similarity(weighted),-1,1);em=np.clip(cosine_similarity(equal),-1,1);upper=np.triu_indices(len(ids),1)
    differences=np.abs(wm[upper]-em[upper]);rho=float(spearmanr(wm[upper],em[upper]).statistic) if len(upper[0])>2 else None
    qa_inputs=[];ra_queries=[];bashar_queries=[];qa_pairs=[]
    for p in pairs:
        if p['question_text_available'] and p['question_mark_present'] and len(tokens(p['question_text']))>=8:
            qid='q:'+p['pair_id'];aid='a:'+p['pair_id'];qa_inputs.extend([(qid,mask_source_markers(p['question_text'])),(aid,mask_source_markers(p['response_text']))]);ra_queries.append((qid,p));qa_pairs.append((qid,aid,p))
    for c in candidates:
        if len(tokens(c['text']))>=8:
            qid='q:'+c['candidate_id'];qa_inputs.append((qid,mask_source_markers(c['text'])));bashar_queries.append((qid,c))
    qa_vectors=encoder.encode(qa_inputs) if qa_inputs else {};nearest=[];paired=[]
    if ra_queries and bashar_queries:
        rv=np.vstack([qa_vectors[qid][0] for qid,p in ra_queries]);bv=np.vstack([qa_vectors[qid][0] for qid,c in bashar_queries]);scores=cosine_similarity(bv,rv)
        for i,(qid,c) in enumerate(bashar_queries):
            j=int(np.argmax(scores[i]));_,p=ra_queries[j]
            nearest.append({'bashar_source_id':c['source_id'],'bashar_candidate_id':c['candidate_id'],'bashar_turn_id':c['turn_id'],
                'ra_source_id':p['source_id'],'ra_pair_id':p['pair_id'],'ra_question_id':p['question_id'],'cosine':float(scores[i,j]),
                'interpretation':'Nearest retrieval lead; no validated question equivalence or Bashar answer.'})
        nearest.sort(key=lambda row:-row['cosine'])
    bysession=defaultdict(list)
    for qid,aid,p in qa_pairs:bysession[p['source_id']].append((qid,aid,p))
    for sid,rows in bysession.items():
        actual=[float(np.dot(qa_vectors[q][0],qa_vectors[a][0])) for q,a,p in rows]
        shifted=[float(np.dot(qa_vectors[rows[i][0]][0],qa_vectors[rows[(i+1)%len(rows)][1]][0])) for i in range(len(rows))] if len(rows)>1 else []
        paired.append({'source_id':sid,'eligible_pairs':len(rows),'mean_matched_prompt_response_cosine':float(np.mean(actual)),
            'mean_within_session_cyclic_response_cosine':float(np.mean(shifted)) if shifted else None,
            'scope':'Descriptive linkage diagnostic; a single cyclic shift is not a significance test or independent sample.'})
    return {'status':'frozen_local_inference_complete','model':encoder.manifest,
        'processing':{**encoder.binding,'source_mask':'Complete apostrophe-aware lexical tokens; straight/curly negative and future contractions preserved.',
            'source_mask_code_sha256':hashlib.sha256(inspect.getsource(mask_source_markers).encode()).hexdigest(),
            'cache_storage_dtype':'float32','cache_replay_precision':'Cached vectors use float32; tiny numerical differences from first-inference in-memory pooling are possible.'},'source_ids':ids,'cosine_matrix':wm.tolist(),
        'coverage':[{'source_id':sid,**encoded_docs[sid][2]} for sid in ids],
        'pooling_sensitivity':{'pair_count':len(upper[0]),'mean_absolute_cosine_change':float(differences.mean()),'maximum_absolute_cosine_change':float(differences.max()),'spearman_pair_rank':rho},
        'qa':{'eligible_ra_prompts':len(ra_queries),'eligible_bashar_punctuation_candidates':len(bashar_queries),
            'selection':'Available source-printed Ra questioner prompts and ASR candidates containing ? and at least8 analysis tokens; placeholders excluded. No human question validation.',
            'retrieval_leads':nearest,'response_linkage_by_ra_session':paired,
            'processed_items':len(qa_inputs),'processed_content_wordpieces':sum(v[2]['content_wordpieces'] for v in qa_vectors.values()),
            'truncated_content_wordpieces':0},
        'limitations':['Frozen English general-purpose MiniLM is an established baseline, not validated channeling-domain semantic ground truth.',
            'All content wordpieces are processed in bounded chunks; pooling still loses order between chunks and can obscure contradictions.',
            'Name/source-marker masking does not eliminate genre, edition, publisher, speaker, time-period or ASR-error confounding.',
            'Prompt retrieval is exploratory and multiple comparisons favor some close matches; scores are not probabilities of equivalent beliefs or accurate claims.']}

def sqlite_qa(path,docs,pairs,candidates):
    with sqlite3.connect(path) as con:
        con.executescript('''CREATE TABLE documents(source_id TEXT PRIMARY KEY,corpus TEXT,session_id TEXT,source_kind TEXT,title TEXT,text TEXT);
          CREATE TABLE turns(source_id TEXT,turn_id TEXT,role TEXT,question_id TEXT,text TEXT,PRIMARY KEY(source_id,turn_id));
          CREATE TABLE prompt_response_pairs(pair_id TEXT PRIMARY KEY,source_id TEXT,question_id TEXT,kind TEXT,question TEXT,response TEXT,question_text_available INTEGER,question_mark_present INTEGER);
          CREATE TABLE asr_question_candidates(candidate_id TEXT PRIMARY KEY,source_id TEXT,turn_id TEXT,text TEXT,following_context TEXT,answer_identified INTEGER);''')
        for d in docs:
            s=d['summary'];con.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)',(s['source_id'],s['corpus'],s['session_id'],s['source_kind'],s['title'],d['text']))
            con.executemany('INSERT INTO turns VALUES(?,?,?,?,?)',[(s['source_id'],t['turn_id'],t['role'],t.get('question_id'),t['text']) for t in d['turns']])
        con.executemany('INSERT INTO prompt_response_pairs VALUES(?,?,?,?,?,?,?,?)',[(p['pair_id'],p['source_id'],p['question_id'],p['pair_kind'],p['question_text'],p['response_text'],int(p['question_text_available']),int(p['question_mark_present'])) for p in pairs])
        con.executemany('INSERT INTO asr_question_candidates VALUES(?,?,?,?,?,?)',[(p['candidate_id'],p['source_id'],p['turn_id'],p['text'],p['following_context'],0) for p in candidates])
        return {'documents':con.execute('SELECT count(*) FROM documents').fetchone()[0],
                'turns':con.execute('SELECT count(*) FROM turns').fetchone()[0],
                'publisher_prompt_response_pairs':con.execute('SELECT count(*) FROM prompt_response_pairs').fetchone()[0],
                'asr_punctuation_candidates':con.execute('SELECT count(*) FROM asr_question_candidates').fetchone()[0]}

def make_figures(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    docs=result['documents'];byid={d['source_id']:d for d in docs};artifacts=[]
    colors={'ra':'#286571','bashar':'#91512f'}
    display={'ra':'Ra edited','bashar':'Bashar-related'}
    def save(fig,name,caption):
        fig.tight_layout()
        for ext in ('svg','png','pdf'):
            p=out/(name+'.'+ext);fig.savefig(p,dpi=170,metadata={'Title':caption});artifacts.append({'file':p.name,'caption':caption,'sha256':sha(p),'bytes':p.stat().st_size})
        plt.close(fig)
    groups=result['counts']['corpora'];labels=list(groups)
    fig,axes=plt.subplots(1,3,figsize=(12,3.5))
    for ax,key,label in zip(axes,('documents','whitespace_words','tokens'),('Retained documents','Whitespace words','Analysis tokens')):
        ax.bar([display[c] for c in labels],[groups[c][key] for c in labels],color=[colors[c] for c in labels]);ax.set_title(label);ax.ticklabel_format(axis='y',style='plain')
    fig.suptitle('All admitted text: 106 Ra sessions, 19 Bashar-related recordings, 5 written references')
    save(fig,'corpus-coverage','All admitted documents and words include 106 Ra edited sessions, 19 Bashar-related ASR publication contexts and 5 official written Bashar references. Only the 125 session/recording documents enter primary fits; counts are not independent creators or verified speakers.')
    kc=result['keyword_comparison'];keys=list(KEYWORDS);x=np.arange(len(keys));fig,ax=plt.subplots(figsize=(12,5))
    for i,c in enumerate(labels):
        lookup={r['keyword_group']:r for r in kc if r['corpus']==c};ax.bar(x+(i-.5)*.38,[lookup[k]['equal_session_mean_per_1000'] for k in keys],width=.38,color=colors[c],label=display[c])
    ax.set_xticks(x,[k.replace('_',' ') for k in keys],rotation=35,ha='right');ax.set_ylabel('Equal-document mean mentions / 1,000 tokens');ax.legend();ax.set_title('Declared keyword groups — not validated beliefs')
    save(fig,'keyword-comparison','Each session contributes equally within its corpus; pooled-token sensitivity and complete dictionaries accompany the figure.')
    lexical=result['lexical']['variants'];fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    for ax,key,title in zip(axes,('content','name_masked'),('Filler-filtered vocabulary','Fixed names and source markers removed')):
        r=lexical[key];im=ax.imshow(r['cosine_matrix'],vmin=0,vmax=1,cmap='viridis');ax.set_title(title);ax.set_xlabel('Document index');ax.set_ylabel('Document index');fig.colorbar(im,ax=ax,label='TF-IDF cosine')
    save(fig,'lexical-similarity','Index order and exact source IDs are in the data; cosine represents vocabulary overlap, not agreement or origin.')
    topics=result['topics'];clusters=result['clusters']
    if topics.get('candidate_diagnostics'):
        fig,axes=plt.subplots(1,3,figsize=(12,3.7));rows=topics['candidate_diagnostics'];ks=[r['k'] for r in rows]
        axes[0].plot(ks,[r['reconstruction_errors'][0] for r in rows],'o-');axes[0].set_ylabel('NMF reconstruction error')
        axes[1].plot(ks,[r['seed_component_matching_mean'] for r in rows],'o-');axes[1].set_ylabel('Matched term-vector seed similarity');axes[1].set_ylim(0,1)
        cr=clusters.get('candidates',[]);axes[2].plot([r['k'] for r in cr],[r['cosine_silhouettes'][0] for r in cr],'o-');axes[2].set_ylabel('KMeans cosine silhouette')
        for ax in axes:ax.set_xlabel('Candidate component / cluster count')
        fig.suptitle('Exploratory model diagnostics; no semantic ground truth')
        save(fig,'topic-diagnostics','Different diagnostics answer different questions; reconstruction error decreases with additional model capacity.')
        fig,ax=plt.subplots(figsize=(10,4));weights=topics['document_weights'];k=topics['displayed_k'];x=np.arange(k)
        for i,c in enumerate(labels):
            means=np.mean([w['weights'] for w in weights if byid[w['source_id']]['corpus']==c],axis=0);ax.bar(x+(i-.5)*.36,means,width=.36,label=display[c],color=colors[c])
        ax.set_xticks(x,['Component '+str(i+1) for i in range(k)]);ax.set_ylabel('Mean normalized NMF weight');ax.legend();ax.set_title('Lexical component weights by source context')
        save(fig,'topic-weights','Weights are decomposition shares, not topic probabilities. Component terms and concentration diagnostics are in the data.')
    if clusters.get('assignments'):
        fig,ax=plt.subplots(figsize=(8,6))
        for c in labels:
            rs=[r for r in clusters['assignments'] if byid[r['source_id']]['corpus']==c];ax.scatter([r['x'] for r in rs],[r['y'] for r in rs],label=display[c],c=colors[c],s=35,alpha=.75)
        ax.set_xlabel('SVD coordinate 1');ax.set_ylabel('SVD coordinate 2');ax.legend();ax.set_title('Two-dimensional view of lexical vectors')
        save(fig,'cluster-map','Colors show source context only; clustering assignments and seed sensitivity are separate data fields. Axes are not spiritual dimensions.')
    net=result['network'];n=len(net['nodes']);positions={node['source_id']:(math.cos(2*math.pi*i/n),math.sin(2*math.pi*i/n)) for i,node in enumerate(net['nodes'])} if n else {}
    fig,ax=plt.subplots(figsize=(8,8))
    for e in net['edges']:
        a,b=positions[e['source']],positions[e['target']];ax.plot([a[0],b[0]],[a[1],b[1]],color='#c26636' if e['cross_corpus'] else '#aaa',alpha=.35,lw=.7)
    for c in labels:
        ns=[node for node in net['nodes'] if node['corpus']==c];ax.scatter([positions[v['source_id']][0] for v in ns],[positions[v['source_id']][1] for v in ns],label=display[c],c=colors[c],s=25,zorder=3)
    ax.axis('off');ax.legend();ax.set_title('Three-nearest-neighbor lexical graph (cosine ≥ 0.15)')
    save(fig,'lexical-network','Circular placement is schematic; orange edges cross source contexts, not claimed entities or physical civilizations.')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,key,title in zip(axes,('publisher_prompt_response_pairs','punctuation_candidates'),('Publisher-labeled prompt / response pairs','Unverified ASR question-mark candidates')):
        ax.bar([display[c] for c in labels],[sum(d['qa'][key] for d in docs if d['corpus']==c) for c in labels],color=[colors[c] for c in labels]);ax.set_title(title,fontsize=11)
    fig.suptitle('Different evidence types; no inferred ASR answers')
    save(fig,'qa-structure','Published speaker-role structure and machine punctuation are distinct units and cannot be compared as verified substantive-question rates.')
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=False)
    for ax,c in zip(axes,labels):
        group=[d for d in docs if d['corpus']==c and d['source_kind']!='authored_reference' and d.get('published_at')]
        dates=[dt.date.fromisoformat(d['published_at'][:10]) for d in group]
        ax.plot(dates,[d['token_count'] for d in group],'.-',color=colors[c]);ax.set_title(display[c]+(' source-printed session dates' if c=='ra' else ' publisher recording release dates'));ax.set_ylabel('Analysis tokens');ax.set_xlabel('Source-reported calendar date; separate horizontal scales')
    save(fig,'chronology','Primary session/recording documents only; five undated written references are excluded. Ra session dates and contemporary recording publication dates are distinct temporal measures, on separate scales, not aligned natural experiments.')
    sem=result.get('semantic',{})
    if sem.get('status')=='frozen_local_inference_complete':
        fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(sem['cosine_matrix'],vmin=-1,vmax=1,cmap='coolwarm');fig.colorbar(im,ax=ax,label='Frozen MiniLM cosine');ax.set_title('Complete-text chunk-pooled embedding similarity');ax.set_xlabel('Primary document index');ax.set_ylabel('Primary document index')
        save(fig,'semantic-similarity','Frozen general-purpose embeddings process all content wordpieces; scores are neither agreement probabilities nor directly comparable to TF-IDF cosine scale.')
        pairs=sem['qa']['response_linkage_by_ra_session'];pairs=[p for p in pairs if p['mean_within_session_cyclic_response_cosine'] is not None]
        session_numbers=[int(byid[p['source_id']]['session_id'].rsplit(':',1)[1]) for p in pairs]
        fig,ax=plt.subplots(figsize=(11,4));ax.plot(session_numbers,[p['mean_matched_prompt_response_cosine'] for p in pairs],label='Printed paired prompt/response',color=colors['ra']);ax.plot(session_numbers,[p['mean_within_session_cyclic_response_cosine'] for p in pairs],label='One cyclic response shift within session',color='#817768');ax.set_ylabel('Session mean embedding cosine');ax.set_xlabel('Numbered Ra session (at least two eligible exchanges)');ax.legend();ax.set_title('Published exchange linkage — descriptive diagnostic')
        save(fig,'question-response-linkage','One within-session cyclic shift is a reference comparison, not a hypothesis test; question eligibility and missing-text exclusions are documented.')
    return artifacts

def exclude_promotional_commentary(docs):
    return [d for d in docs if d['summary'].get('source_format') not in {
        'skeptical_commentary','promotional_interview','publisher_promotional_interview','promotion','commentary'}]

def analyse(manifests,output, *, figures=True,allow_fixtures=False,model_dir=None,semantic_cache=None):
    output=safe_path(output,private=True,exists=False)
    if output.exists() and any(output.iterdir()):raise ValueError('Choose a new empty output directory')
    docs,excluded,aliases,audit=load_manifests(manifests,allow_fixtures=allow_fixtures)
    if not docs:raise ValueError('No full retained English documents admitted')
    pairs=[];candidates=[]
    for d in docs:
        d['summary']['keyword_rates']=keyword_rates(d['tokens']);pp,cc,q=qa_records(d);pairs+=pp;candidates+=cc;d['summary']['qa']=q
    primary=[d for d in docs if d['summary']['source_kind']!='authored_reference']
    variants={};fits={}
    for variant in ('raw','content','name_masked','matched_length','response_only','bracket_removed'):
        r,X,vec,chosen=fit_lexical(primary,variant);variants[variant]=r;fits[variant]=(X,vec,chosen)
    restricted=exclude_promotional_commentary(primary)
    variants['exclude_promotional_commentary'],_,_,_=fit_lexical(restricted,'name_masked')
    X,vec,chosen=fits['name_masked']
    print(json.dumps({'stage':'lexical_variants_completed','documents':len(primary)}),flush=True)
    if X is None:topics,clusters={'status':'unavailable'},{'status':'unavailable'}
    else:topics,clusters=topic_and_clusters(X,vec,chosen)
    print(json.dumps({'stage':'topic_cluster_diagnostics_completed'}),flush=True)
    references=[d for d in docs if d not in primary];projection=[]
    if references and X is not None:
        from sklearn.metrics.pairwise import cosine_similarity
        ref_X=vec.transform(' '.join(token_variant(d,'name_masked')) for d in references);similarities=cosine_similarity(ref_X,X)
        for i,d in enumerate(references):
            neighbors=[]
            for corpus in ('ra','bashar'):
                eligible=[j for j,(source,tt) in enumerate(chosen) if source['summary']['corpus']==corpus]
                for j in sorted(eligible,key=lambda j:-similarities[i,j])[:3]:neighbors.append({'source_id':chosen[j][0]['summary']['source_id'],'corpus':corpus,'cosine':float(similarities[i,j])})
            projection.append({'source_id':d['summary']['source_id'],'neighbors':neighbors,'scope':'Written reference projected into primary-session vocabulary/IDF; not fitted as another session or direct voice.'})
    semantic=semantic_analysis(primary,pairs,candidates,model_dir,semantic_cache or output.parent/'semantic-cache')
    groups={}
    for corpus in ('bashar','ra'):
        group=[d for d in docs if d['summary']['corpus']==corpus]
        group_primary=[d for d in group if d in primary]
        groups[corpus]={'documents':len(group),'primary_session_documents':len(group_primary),'reference_documents':len(group)-len(group_primary),
            'primary_session_tokens':sum(len(d['tokens']) for d in group_primary),'primary_session_whitespace_words':sum(d['summary']['whitespace_words'] for d in group_primary),
            'tokens':sum(len(d['tokens']) for d in group),'whitespace_words':sum(d['summary']['whitespace_words'] for d in group),
            'source_kinds':dict(Counter(d['summary']['source_kind'] for d in group)),'source_formats':dict(Counter(d['summary']['source_format'] or 'unreported' for d in group))}
    import numpy,scipy,sklearn,matplotlib
    result={'schema_version':SCHEMA,'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'analysis_script_sha256':sha(Path(__file__)),
        'counts':{'admitted_documents':len(docs),'primary_session_documents':len(primary),'reference_documents':len(docs)-len(primary),'corpora':groups,
                  'excluded_records':len(excluded),'aliases':len(aliases),'nominal_source_contexts':len({d['summary']['corpus'] for d in primary})},
        'documents':[d['summary'] for d in docs],'excluded':excluded,'aliases':aliases,'dictionaries':KEYWORDS,'keyword_comparison':keyword_comparison(primary),
        'lexical':{'variants':variants},'topics':topics,'clusters':clusters,'network':network(variants['name_masked'],primary),
        'reference_projection':projection,'semantic':semantic,'near_duplicates':near_duplicate_diagnostics(primary),
        'qa':{'publisher_prompt_response_pairs':len(pairs),'publisher_pairs_with_missing_question_text':sum(not p['question_text_available'] for p in pairs),
            'asr_punctuation_candidates':len(candidates),'verified_substantive_questions':0},
        'methods':{'analysis_unit':'One retained full published session/recording per edition; reference texts separate. Turns are never independent model observations.',
            'tokenizer':'Unicode NFKC, curly-to-straight apostrophe, lowercase ASCII letter tokens with internal apostrophes.',
            'tfidf':'Unigrams/bigrams, sublinear TF, smooth IDF, L2 norm; min_df2 for >=5 docs; max_df1.0; max_features12000; English stopwords retaining no/not/nor/never.',
            'source_mask':sorted(NAMES),'spoken_fillers':sorted(FILLERS),'matched_length':'Centered contiguous1,500-token window before filler/name removal; shorter sessions excluded only from this sensitivity.',
            'response_only':'Ra source-labeled responses only; Bashar unknown-speaker ASR unchanged. This is an asymmetric editorial-structure sensitivity, not matched speaker text.',
            'inference':'Exploratory descriptions of selected documents. No p-values, estimated ET-origin probabilities, causal claims or validated topic classes.',
            'versions':{'numpy':numpy.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'matplotlib':matplotlib.__version__}},
        'limitations':['Bashar-related interviews, promotional speech and commentary are not authenticated full channelled Bashar sessions; hosts, guests and ads are unsegmented.',
            'Ra published edited text and machine ASR differ in speaker structure, editing, errors, dates, genre, source coverage and document length.',
            'Historical-session dependence and re-encoding/reposting duplicates may remain unresolved. Exact hashes do not establish independent performances.',
            'Source context labels are not labels for each utterance. Published role labels record the document attribution, not verified entity identity.',
            'Dictionary matches include negated, quoted and hypothetical uses. Cosine similarity cannot distinguish agreement from disagreement.',
            'Topic/cluster stability reflects numerical behavior in this corpus, not accuracy, novelty, psychological traits or supernatural truth.',
            'Source counts are highly unequal; joint vocabulary and IDF can be dominated by the larger corpus. Length and name controls do not resolve all confounding.',
            'Question-mark candidates have no verified answers. Published prompt/response pairs are not all substantive questions.',
            'This study analyzes claims and discourse; it does not authenticate claimed origins, healing effects or predictions.'],
        'inference':{'physical_origin_tested':False,'human_transcript_accuracy_validated':False,'causal_effect_estimated':False,'empirical_probabilities_estimated':False},
        'synthetic_fixture_run':allow_fixtures}
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    write_json(output/'provenance-private.json',{'inputs':audit,'source_paths_private':True})
    write_json(output/'qa-private.json',{'publisher_prompt_response_pairs':pairs,'unverified_asr_question_candidates':candidates})
    result['qa']['database_counts']=sqlite_qa(output/'questions-and-responses.sqlite',docs,pairs,candidates)
    result['figures']=make_figures(output,result) if figures and X is not None else []
    write_json(output/'analysis.json',result)
    manifest={'schema_version':SCHEMA,'analysis_script_sha256':sha(Path(__file__)),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'private_content':p.name in {'provenance-private.json','qa-private.json','questions-and-responses.sqlite'}} for p in sorted(output.iterdir()) if p.is_file()]}
    write_json(output/'output-manifest.json',manifest)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-figures',action='store_true');p.add_argument('--model-dir',type=Path);p.add_argument('--semantic-cache',type=Path)
    args=p.parse_args();r=analyse(args.manifest,args.output,figures=not args.no_figures,model_dir=args.model_dir,semantic_cache=args.semantic_cache)
    print(json.dumps({'counts':r['counts'],'qa':r['qa'],'figures':len(r['figures'])}))
if __name__=='__main__':main()
