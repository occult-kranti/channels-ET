#!/usr/bin/env python3
"""New joint study of accepted source contexts; private text, public summaries only."""
from __future__ import annotations
import argparse,collections,datetime as dt,hashlib,html,importlib.util,json,re,sqlite3,sys
from pathlib import Path
import numpy as np
BASE=Path('/workspace/channels-et-private/bashar-ra-2026-11')
SCREEN=Path('/workspace/channels-et-private/subscription-screening-2026-11')
HELPER=Path(__file__).resolve().parents[1]/'bashar-ra'/'analyze.py'
HELPER_SHA='6f4d9ab73ad479b7d84e7a299a5c74276847d961030d98cdb2ad059b40b30506'
spec=importlib.util.spec_from_file_location('accepted_analysis',HELPER);A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
ACCEPTED=[(BASE/'analysis/run-04/analysis.json','e9e88095a5264ff588c52e9d9edb23bbffa57ca1e86b24b997057e08035aa476'),(BASE/'official-analysis/final-01/official-speech.json','68e4c40a34fa0bd7efcea13a32ea501b0f7bfd55643935f01e2d8a7a68907b01'),(SCREEN/'text-analysis/run-01/source-topics.json','6dceb3c3a48c16d69dc0e373e88aa4501563ea75a9f5dd64fd2a3176f446d145')]
MANIFESTS=[(BASE/'ra/complete-transcript-manifest.json','1f303635eaee27db96a25bd227a779940a14e7c60f80ac95bcb0cb35482d417d'),(BASE/'bashar/corpus/manifest.json','0c1f1df4f93bccfedb2744da66b7c78feb1e76d6c5973339928f96d8c70d3b60'),(BASE/'bashar/official-vimeo-corpus-reviewed/manifest.json','633a9254fd493e566ebb553cd4c3a893e432f59b63ea6bbca364421526ab621c'),(SCREEN/'second14-texts/manifest.json','e9f48461d7ebe063251d563918bbd3fa405cf885b150afc50f981dcd95305b0b')]
LABELS={'ra_published':'Ra edited sessions','bashar_context':'Bashar-related interviews / commentary','official_excerpt':'Official Bashar excerpts','official_promotion':'Official promotion / product','official_greeting':'Official greetings','tracy_kumbera':'Tracy publisher captions','magenta_pixie':'Magenta transcript PDFs'}
ORDER=list(LABELS)
COLORS=['#65D6C4','#FAAE72','#BCA7FF','#F482A0','#7ED1F3','#F1D66D','#94CA82']
MASK=A.NAMES|{'tracy','kumbera','magenta','pixie'}
EXPECTED={'ra_published':106,'bashar_context':19,'official_excerpt':75,'official_promotion':4,'official_greeting':3,'tracy_kumbera':70,'magenta_pixie':15}
LIMITS=[
'Source-context comparison, not attribution of every utterance to a medium, channellee or civilization. Most machine-text speaker roles are unknown.',
'Selected accessible sources have different dates, genres, publication lengths, recognition errors and editorial histories; no random sample of channeling or of uploads.',
'Exact media or text aliases were collapsed in accepted studies. Repost, excerpt and historical-session dependence beyond those exact hashes is unresolved.',
'TF-IDF cosine measures shared vocabulary. NMF weights are descriptive factors, not topic probabilities; clusters are not validated entity classes.',
'Punctuation candidates and adjacent text are not identified questions and answers. Only Ra has documentary printed prompt-response pairing; no voice or claimed-entity identity verified.',
'No p-values, causal influence, origin probabilities, sentiment of an entity, trained weights or new neural inference are asserted. Prior neural studies retain their own input preprocessing.',
'Future ingestion uses no non-Bashar minimum duration and a 300-second Bashar minimum. This frozen accepted-text snapshot does not retroactively repair historical sampling or represent all uploaded videos.'
]

def bound(path,digest=None):
    p=A.safe_path(path,private=True);actual=A.sha(p)
    if digest and digest!=actual:raise ValueError('Accepted snapshot hash differs: '+p.name)
    obj=A.read_json(p,private=True)
    if A.fixture(obj):raise ValueError('Synthetic fixtures cannot be observed corpus')
    return obj,{'path':str(p),'sha256':actual,'bytes':p.stat().st_size}

def mask_tokens(text):return [t for t in A.tokens(text) if t not in MASK and t not in A.FILLERS]

def load_accepted():
    if A.sha(HELPER)!=HELPER_SHA:raise ValueError('Accepted helper changed')
    studies=[];bindings=[]
    for p,digest in ACCEPTED:
        d,b=bound(p,digest);studies.append(d);bindings.append(b)
    records={}
    for p,digest in MANIFESTS:
        d,b=bound(p,digest);bindings.append(b)
        for r in d['records']:
            if r['source_id'] in records:raise ValueError('Source ID collision between accepted manifests')
            records[r['source_id']]=r
    selections=[(s,s['stratum']) for s in studies[1]['documents'] if s.get('included_in_model')]
    selections.extend((s,s['medium_id']) for s in studies[2]['documents'] if s.get('included_in_model'))
    docs=[];checks=[]
    for s,group in selections:
        sid=s['source_id'];r=records[sid];ref=r['text_artifact'];p=A.artifact(ref,private=True)
        if ref['sha256']!=s['text_artifact_sha256']:raise ValueError('Accepted text edition changed')
        n=A.read_json(p,private=True)
        if n['source_id']!=sid or A.fixture(n):raise ValueError('Normalized source identity invalid')
        if len(n['text'].split())!=s['whitespace_words']:raise ValueError('Accepted word count differs')
        raw=n['text'];text=html.unescape(re.sub(r'<[^>]*>','',raw)) if r.get('source_format')=='srt' else raw
        role='publisher_printed_roles_unverified' if group=='ra_published' else 'unknown_mixed_speakers'
        summary={k:s.get(k) for k in ('source_id','title','source_url','source_format','source_kind','published_at','whitespace_words','text_artifact_sha256')}
        summary.update(group_id=group,corpus=group,source_role=role,short_id=sid,language=r.get('language'),text_origin=s.get('transcription_origin',r.get('source_kind')),duration_seconds=s.get('duration_seconds',r.get('duration_seconds_publisher')),duplicate_family_id=r.get('duplicate_family_id',r.get('publication_family_id')),speaker_attribution_verified=False)
        docs.append({'summary':summary,'text':text,'tokens':mask_tokens(text),'turns':n.get('turns',[])})
        checks.append({'source_id':sid,'text_artifact':ref,'accepted_text_artifact_sha256':s['text_artifact_sha256']})
    docs.sort(key=lambda d:(ORDER.index(d['summary']['group_id']),d['summary']['source_id']))
    if dict(collections.Counter(d['summary']['group_id'] for d in docs))!=EXPECTED:raise ValueError('Accepted model denominator changed')
    if len({d['summary']['source_id'] for d in docs})!=len(docs):raise ValueError('Duplicate fitted source')
    return docs,{'inputs':bindings,'normalized_texts':checks,'reuse_scope':'Accepted model admission and prior independent checks reused; normalized text hash, ID and words rechecked. No raw media download or ASR rerun.'},studies

def centered(text,n=600):
    tt=A.tokens(text)
    if len(tt)<n:return None
    start=(len(tt)-n)//2
    return ' '.join(t for t in tt[start:start+n] if t not in MASK and t not in A.FILLERS)

def grouped(matrix,docs):
    groups=[g for g in ORDER if any(d['summary']['group_id']==g for d in docs)];means=[];counts=[]
    for a in groups:
        row=[];nr=[]
        for b in groups:
            ii=[i for i,d in enumerate(docs) if d['summary']['group_id']==a];jj=[i for i,d in enumerate(docs) if d['summary']['group_id']==b]
            vals=[float(matrix[i,j]) for i in ii for j in jj if a!=b or i<j]
            row.append(float(np.mean(vals)) if vals else None);nr.append(len(vals))
        means.append(row);counts.append(nr)
    return {'groups':groups,'matrix':means,'pair_counts':counts}

def lexical_network(cos,docs):
    edges=[]
    for i,a in enumerate(docs):
        for j in range(i+1,len(docs)):
            if a['summary']['group_id']!=docs[j]['summary']['group_id']:
                edges.append({'source':a['summary']['source_id'],'target':docs[j]['summary']['source_id'],'source_group':a['summary']['group_id'],'target_group':docs[j]['summary']['group_id'],'cosine':float(cos[i,j])})
    edges.sort(key=lambda r:(-r['cosine'],r['source'],r['target']))
    return {'rule':'Top 25 cross-context TF-IDF pairs, not independent corroboration or attributed-entity agreement. No threshold selected for inference.','edges':edges[:25],'threshold_sensitivity':[{'threshold':t,'cross_context_pairs':sum(e['cosine']>=t for e in edges)} for t in [.1,.2,.3,.4,.5]],'possible_near_duplicates':[e for e in edges if e['cosine']>=.75]}

def qa_items(docs):
    items=[]
    for d in docs:
        s=d['summary'];sid=s['source_id']
        if s['group_id']=='ra_published':
            paired,_,_=A.qa_records({'summary':{**s,'corpus':'ra','session_id':sid},'turns':d['turns']})
            for q in paired:
                items.append({'id':q['pair_id'],'source_id':sid,'group_id':s['group_id'],'source_url':s['source_url']+'#'+q['question_id'],'question_id':q['question_id'],'question':q['question_text'],'response':q['response_text'],'context':None,'role':'publisher_printed_question_response','question_available':q['question_text_available'],'answer_identified':True,'source_turn_ids':[q['question_turn_id']]+q['response_turn_ids']})
        else:
            for pos,t in enumerate(d['turns']):
                if '?' not in t['text']:continue
                # One cue/page can include several candidates; sentence extraction does not assert a speaker turn.
                for k,match in enumerate(re.finditer(r'[^.!?]*\?',t['text'])):
                    q=match.group().strip()
                    if not q:continue
                    items.append({'id':sid+':candidate:'+str(pos)+':'+str(k),'source_id':sid,'group_id':s['group_id'],'source_url':s['source_url'],'question_id':None,'question':q,'response':None,'context':' '.join(x['text'] for x in d['turns'][max(0,pos-1):pos+3]),'role':'unverified_punctuation_unknown_speaker','question_available':True,'answer_identified':False,'source_turn_ids':[t['turn_id']],'start_seconds':t.get('start_seconds',t.get('start')),'page':t.get('page')})
    return items

def fit_qa(items,out):
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    # Distinct values prevent duplicated question wording from acquiring extra TF/IDF mass.
    stop=set(ENGLISH_STOP_WORDS)|{'did','does','doing','want','tell','could','would','please','mean','meaning','correct','question','happen','happened'}
    content=lambda text:set(mask_tokens(text))-stop
    eligible=[q for q in items if q['question_available'] and 6<=len(mask_tokens(q['question']))<=80 and len(content(q['question']))>=4]
    texts=[' '.join(mask_tokens(q['question'])) for q in eligible]
    vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,ngram_range=(1,2),sublinear_tf=True,min_df=1,stop_words=sorted(stop-{'no','not','nor','never'}))
    vec.fit(sorted(set(texts)));X=vec.transform(texts)
    targets=[i for i,q in enumerate(eligible) if q['role']=='publisher_printed_question_response'];queries=[i for i,q in enumerate(eligible) if q['role']!='publisher_printed_question_response']
    scores=cosine_similarity(X[queries],X[targets]);results=[]
    for ri,idx in enumerate(queries):
        rank=np.argsort(-scores[ri],kind='stable');best=int(rank[0]);q=eligible[idx];r=eligible[targets[best]];score=float(scores[ri,best]);gap=score-float(scores[ri,rank[1]]) if len(rank)>1 else score
        shared=len(content(q['question'])&content(r['question']))
        results.append({'shared_content_unigrams':shared,'query_id':q['id'],'target_id':r['id'],'score':score,'runner_up_gap':gap,'status':'review_lead' if score>=.35 and gap>=.03 and shared>=3 else 'abstain','source_group':q['group_id'],'source_id':q['source_id'],'target_source_id':r['source_id'],'question_id':r['question_id']})
    results.sort(key=lambda x:(-x['score'],x['query_id']))
    with sqlite3.connect(out/'qa-private.sqlite') as db:
        db.executescript('CREATE TABLE items(id TEXT PRIMARY KEY,source_id TEXT,group_id TEXT,source_url TEXT,question_id TEXT,question TEXT,response TEXT,context TEXT,role TEXT,question_available INTEGER,answer_identified INTEGER,source_turn_ids TEXT); CREATE TABLE retrieval(query_id TEXT,target_id TEXT,score REAL,runner_up_gap REAL,status TEXT);')
        for q in items:db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(q.get(k) for k in ['id','source_id','group_id','source_url','question_id','question','response','context','role','question_available','answer_identified'])+(json.dumps(q['source_turn_ids']),))
        for r in results:db.execute('INSERT INTO retrieval VALUES(?,?,?,?,?)',tuple(r[k] for k in ['query_id','target_id','score','runner_up_gap','status']))
    lookup={q['id']:q for q in items};selected=[];pergroup=collections.Counter()
    for r in results:
        if r['status']!='review_lead' or pergroup[r['source_group']]>=2:continue
        q=lookup[r['query_id']];t=lookup[r['target_id']];pergroup[r['source_group']]+=1
        selected.append({'id':r['query_id'],'target_id':r['target_id'],'question_source_id':q['source_id'],'question_context':LABELS[q['group_id']],'question_url':q['source_url'],'response_source_id':t['source_id'],'response_context':'Ra printed question '+str(t['question_id'])+' and response','response_url':t['source_url'],'score':r['score'],'runner_up_gap':r['runner_up_gap'],'status':'unreviewed_lexical_candidate_no_answer_equivalence','question_paraphrase':None,'response_paraphrase':None,'limitations':['Query speaker and answer unknown; Ra pairing is documentary attribution.','High lexical score can reflect generic wording; source reading required.']})
    A.write_json(out/'qa-private.json',{'items':items,'retrieval':results,'selected_reading_items':[{'lead':l,'query':lookup[l['id']],'target':lookup[l['target_id']]} for l in selected]})
    review_path=Path(__file__).with_name('qa-review.json')
    if review_path.exists():
        reviews=json.loads(review_path.read_text())
        for lead in selected:
            for review in reviews['reviews']:
                if (lead['id'],lead['target_id'])==(review['id'],review['target_id']):
                    query=lookup[lead['id']];target=lookup[lead['target_id']]
                    if hashlib.sha256(query['question'].encode()).hexdigest()!=review['query_text_sha256'] or hashlib.sha256(target['question'].encode()).hexdigest()!=review['target_text_sha256']:raise ValueError('Reviewed question edition changed')
                    lead.update({k:review[k] for k in ['status','question_paraphrase','response_paraphrase','comparison','accepted_same_question','audio_reviewed']})
    counts={'total_items':len(items),'documentary_pairs':sum(q['answer_identified'] for q in items),'missing_question_text':sum(not q['question_available'] for q in items),'unverified_punctuation_candidates':sum(not q['answer_identified'] for q in items),'eligible_documentary_questions':len(targets),'eligible_candidates':len(queries),'retrieval_leads':sum(r['status']=='review_lead' for r in results),'abstentions':sum(r['status']=='abstain' for r in results),'identified_non_Ra_answers':0,'reviewed_candidates':sum(x.get('accepted_same_question') is not None for x in selected),'accepted_same_question_pairs':sum(x.get('accepted_same_question') is True for x in selected),'rule':'Question-only common TF-IDF (1,2)-grams,6–80 masked tokens and≥4distinct non-stop unigrams; min_df1; best Ra prompt, cosine≥0.35, margin≥0.03, and≥3shared content unigrams to yield a review lead. Heuristic thresholds have no precision estimate; not an answer recommendation.','threshold_sensitivity':[{'threshold':t,'margin':.03,'leads':sum(r['score']>=t and r['runner_up_gap']>=.03 and r['shared_content_unigrams']>=3 for r in results)} for t in [.25,.35,.45,.55]],'by_group':dict(collections.Counter(q['group_id'] for q in items))}
    return counts,selected

def figures(out,r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    arts=[]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    short=['Ra','Bashar contexts','Bashar excerpts','Promotions','Greetings','Tracy captions','Magenta PDFs']
    def save(fig,name,title,alt):
        fig.tight_layout()
        for ext in ['svg','png','pdf']:
            p=out/(name+'.'+ext);fig.savefig(p,dpi=160,metadata={'Title':title});arts.append({'id':name,'title':title,'file':p.name,'alt':alt,'sha256':A.sha(p),'bytes':p.stat().st_size})
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5));rows=r['coverage']['groups']
    axes[0].barh(short,[x['documents'] for x in rows],color=COLORS);axes[0].set_xlabel('Accepted model units');axes[1].barh(short,[x['words'] for x in rows],color=COLORS);axes[1].set_xlabel('Words in retained texts')
    save(fig,'joint-coverage','What text is actually analyzed','292 source-context model units; many researched mediums have no source text in this frozen joint study.')
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax,key,title in zip(axes,['matrix','window_matrix'],['Entire retained text','Centered 600-token span']):
        vals=np.array(r['similarities'][key],dtype=float);im=ax.imshow(vals,vmin=0,vmax=1,cmap='viridis');ax.set_xticks(range(7),short,rotation=55,ha='right');ax.set_yticks(range(7),short);ax.set_title(title)
        for i in range(7):
            for j in range(7):ax.text(j,i,'—' if np.isnan(vals[i,j]) else f'{vals[i,j]:.2f}',ha='center',va='center',color='white' if vals[i,j]<.5 else 'black',fontsize=8)
    fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.6,label='Mean TF-IDF cosine');fig.subplots_adjust(right=.82,bottom=.25,wspace=.55)
    # Colorbar layout is placed by subplots_adjust rather than tight_layout.
    for ext in ['svg','png','pdf']:
        p=out/('joint-similarity.'+ext);fig.savefig(p,dpi=160);arts.append({'id':'joint-similarity','title':'Shared vocabulary and length sensitivity','file':p.name,'alt':'Same fixed vocabulary and IDF for entire-text and 600-token spans. Diagonal excludes self-pairs; zero is observed no lexical overlap.','sha256':A.sha(p),'bytes':p.stat().st_size})
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,6))
    for i,g in enumerate(ORDER):
        rows=[x for x in r['clusters']['assignments'] if x['group_id']==g];ax.scatter([x['x'] for x in rows],[x['y'] for x in rows],s=25,color=COLORS[i],alpha=.8,label=short[i])
    ax.set_xlabel('TF-IDF SVD component 1');ax.set_ylabel('TF-IDF SVD component 2');ax.legend(fontsize=8);save(fig,'joint-clusters','Source vocabulary map','SVD projection of lexical vectors; source form and topic variation can dominate. Positions are not entity identities.')
    fig,ax=plt.subplots(figsize=(10,5));matrix=np.array([[next(w['weight'] for w in t['group_weights'] if w['group_id']==g) for g in ORDER] for t in r['topics']]);im=ax.imshow(matrix,aspect='auto',cmap='magma',vmin=0,vmax=1);ax.set_xticks(range(7),short,rotation=35,ha='right');ax.set_yticks(range(len(r['topics'])),[' / '.join(x['term'] for x in t['terms'][:3]) for t in r['topics']]);fig.colorbar(im,ax=ax,label='Mean normalized factor weight');save(fig,'joint-topics','Exploratory lexical components','Four displayed NMF components; labels are top terms. Weights are not probabilities or validated beliefs.')
    fig,ax=plt.subplots(figsize=(10,5));vals=[[np.log10(max(1,x['whitespace_words'])) for x in r['documents'] if x['group_id']==g] for g in ORDER];ax.boxplot(vals,tick_labels=short,orientation='horizontal');ax.set_xlabel('log10 whitespace words');save(fig,'joint-lengths','Publication-length imbalance','Different recording, excerpt, caption and PDF units do not become comparable merely by pooling their text.')
    return arts

def study(out):
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.metrics import adjusted_rand_score
    executed_code_sha=A.sha(Path(__file__))
    out=A.safe_path(out,private=True,exists=False)
    if out.exists():raise ValueError('Never overwrite a prior run')
    out.mkdir(parents=True,mode=0o700)
    (out/'executed-analyze.py').write_bytes(Path(__file__).read_bytes())
    docs,audit,accepted=load_accepted();A.write_json(out/'provenance-private.json',audit)
    print(json.dumps({'stage':'validated','model_units':len(docs)}),flush=True)
    lex,X,vec,chosen=A.fit_lexical(docs,'raw')
    if X is None or len(chosen)!=len(docs):raise ValueError('All selected text units must have a vector')
    cos=np.clip(cosine_similarity(X),0,1);full=grouped(cos,docs)
    spans=[(d,centered(d['text'])) for d in docs];spans=[(d,t) for d,t in spans if t is not None];winX=vec.transform([t for d,t in spans]);win=grouped(cosine_similarity(winX),[d for d,t in spans])
    if win['groups']!=full['groups']:raise ValueError('Window analysis lost a whole source stratum')
    topics,clusters=A.topic_and_clusters(X,vec,chosen)
    print(json.dumps({'stage':'models_fit','clusters_k':clusters['selected_k']}),flush=True)
    byid={d['summary']['source_id']:d['summary'] for d in docs};rows=[]
    for x in clusters['assignments']:x['group_id']=byid[x['source_id']]['group_id']
    for (cl,g),n in sorted(collections.Counter((x['cluster'],x['group_id']) for x in clusters['assignments']).items()):rows.append({'cluster':cl,'group_id':g,'documents':n})
    best=next(x for x in clusters['candidates'] if x['k']==clusters['selected_k']);clusters.update(method='TF-IDF KMeans + SVD display',k=clusters['selected_k'],silhouette=best['cosine_silhouettes'][0],rows=rows,source_context_adjusted_rand=float(adjusted_rand_score([d['summary']['group_id'] for d in docs],[x['cluster'] for x in clusters['assignments']])))
    pubtopics=[]
    for c in topics['components']:
        ix=c['component']-1;pubtopics.append({'id':'topic-'+str(c['component']),'label':' / '.join(c['terms'][:3]),'terms':[{'term':t,'weight':None} for t in c['terms']],'documents':int(sum(np.argmax(x['weights'])==ix for x in topics['document_weights'])),'group_weights':[{'group_id':g,'weight':v} for g,v in c['source_context_means'].items()]})
    qa,leads=fit_qa(qa_items(docs),out)
    coverage={'model_documents':len(docs),'model_words':sum(d['summary']['whitespace_words'] for d in docs),'groups':[],'excluded':[{'scope':'Official Bashar publications','exact_media_aliases':2,'non_English':2,'below_300_seconds':1},{'scope':'Tracy/Magenta files','exact_caption_aliases':1,'references':4,'non_English':1},{'scope':'Baseline','written_references_separate':5,'partial_handouts_separate':35}],'all_uploads_denominator':None,'source_groups_are_speakers':False,'duration_policy':{'bashar_minimum_seconds':300,'others_minimum_seconds':0,'applies_to':'future acquisitions; accepted historical model cohorts preserved'}}
    for g in ORDER:
        group=[d for d in docs if d['summary']['group_id']==g];coverage['groups'].append({'id':g,'label':LABELS[g],'documents':len(group),'words':sum(d['summary']['whitespace_words'] for d in group),'source_role':group[0]['summary']['source_role'],'text_origin':sorted(set(str(d['summary']['text_origin']) for d in group))})
    similarities={'metric':'Name-masked TF-IDF (1,2)-gram cosine','groups':full['groups'],'matrix':full['matrix'],'pair_counts':full['pair_counts'],'window_matrix':win['matrix'],'window_pair_counts':win['pair_counts'],'window_documents':len(spans),'window_excluded_source_ids':[d['summary']['source_id'] for d in docs if centered(d['text']) is None],'features':lex['features'],'limitations':['Entire-text and centered600 token spans use fixed full-fit vocabulary/IDF. Windows are not matched discourse. Within-source cells exclude self-pairs.']}
    # Genre sensitivity is explicit: exclude promotions, greetings and non-interview commentary from pooled evidence.
    core=[(i,d) for i,d in enumerate(docs) if d['summary']['group_id'] not in {'official_promotion','official_greeting'} and d['summary']['source_format'] not in {'skeptical_commentary','promotional_interview'}]
    sensitivity={'genre_restricted':grouped(cos[np.ix_([i for i,d in core],[i for i,d in core])],[d for i,d in core]),'genre_restricted_documents':len(core),'rule':'Omit official promotion/greeting strata and baseline skeptical-commentary/promotional-interview formats, fixed vocabulary/IDF. All remaining source-format confounds persist.'}
    longest=max(docs,key=lambda d:d['summary']['whitespace_words']);minus=[d for d in docs if d is not longest];ml,mx,mv,mc=A.fit_lexical(minus,'raw')
    sensitivity['longest_document_removed']={**grouped(cosine_similarity(mx),minus),'removed_source_id':longest['summary']['source_id'],'removed_words':longest['summary']['whitespace_words'],'refitted_vocabulary_and_idf':True,'model_documents':len(minus)}
    r={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':executed_code_sha,'helper_sha256':HELPER_SHA,'scope':'New joint exploratory fit of accepted, deduplicated English source-context units. Sources discussed in claim registers without retained admitted text are not silently included.','accepted_bindings':[{'file':p.name,'sha256':h} for p,h in ACCEPTED],'coverage':coverage,'documents':[d['summary'] for d in docs],'similarities':similarities,'topics':pubtopics,'topic_diagnostics':topics,'clusters':clusters,'network':lexical_network(cos,docs),'sensitivity':sensitivity,'qa':qa,'qa_leads':leads,'limitations':LIMITS,'figures':[]}
    if A.sha(Path(__file__))!=executed_code_sha:raise ValueError('Source changed during execution; freeze code and choose new run')
    r['figures']=figures(out,r);A.write_json(out/'analysis.json',r)
    A.write_json(out/'output-manifest.json',{'schema_version':1,'public_allowlist':[{'file':'analysis.json','sha256':A.sha(out/'analysis.json'),'bytes':(out/'analysis.json').stat().st_size}]+[{'file':x['file'],'sha256':x['sha256'],'bytes':x['bytes']} for x in r['figures']],'private_outputs':['executed-analyze.py','provenance-private.json','qa-private.json','qa-private.sqlite'],'complete':True})
    print(json.dumps({'stage':'complete','output':str(out),'model_units':len(docs),'qa':qa}),flush=True)
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();study(args.output)
