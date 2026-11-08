#!/usr/bin/env python3
"""Source-bound exploratory text study; separate from every Bashar/Ra model."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import copy,datetime as dt,hashlib,html,inspect,json,math,re,sqlite3,sys,unicodedata,warnings
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bashar-ra'))
import analyze as A
BASE_CODE_SHA='6f4d9ab73ad479b7d84e7a299a5c74276847d961030d98cdb2ad059b40b30506'
SOURCE_NAMES={'tracy','kumbera','magenta','pixie'}
PRIMARY_KINDS={'publisher_hosted_caption_origin_unverified','publisher_labeled_transcript_pdf'}
LABELS={'tracy_kumbera':'Tracy captions','magenta_pixie':'Magenta transcript PDFs'}
COLORS={'tracy_kumbera':'#286571','magenta_pixie':'#91512f'}
TIME_RE=re.compile(r'^(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$')

def parse_srt(data):
    text=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n');rows=[];last=-1
    for i,block in enumerate(re.split(r'\n\s*\n',text.strip()),1):
        lines=block.splitlines();pos=1 if lines and lines[0].strip().isdigit() else 0
        m=TIME_RE.fullmatch(lines[pos].strip()) if len(lines)>pos else None
        if m is None:raise ValueError('Every nonempty SRT block needs a valid timecode')
        h,mn,s,ms,eh,em,es,ems=map(int,m.groups())
        if max(mn,s,em,es)>=60:raise ValueError('SRT minute/second component out of range')
        start=h*3600+mn*60+s+ms/1000;end=eh*3600+em*60+es+ems/1000;body='\n'.join(lines[pos+1:]).strip()
        if start<last or end<start or not body:raise ValueError('SRT order, duration or text invalid')
        rows.append({'turn_id':f'cue:{i:05d}','role':'unknown','start':start,'end':end,'text':body});last=start
    if not rows:raise ValueError('Empty caption stream')
    return rows

def pdf_pages(text,expected):
    pages=text.split('\f')
    if pages and not pages[-1].strip():pages.pop()
    if len(pages)!=expected:raise ValueError('PDF page-count/text extraction mismatch')
    return [{'turn_id':f'page:{i:03d}','role':'unknown','page':i,'text':p.strip()} for i,p in enumerate(pages,1)]

def same(a,b):return all(a.get(k)==b.get(k) for k in ('path','bytes','sha256'))
def clean_text(text,fmt):return html.unescape(re.sub(r'<[^>]*>','',text)) if fmt=='srt' else text

def load_manifest(path,*,expected_count,allow_fixtures=False):
    manifest=A.read_json(path,private=True)
    if A.fixture(manifest) and not allow_fixtures:raise ValueError('Fixture input cannot be published as observed data')
    rows=manifest.get('records',[])
    if manifest.get('schema_version')!=1 or len(rows)!=expected_count or manifest.get('counts',{}).get('requested')!=expected_count:raise ValueError('Explicit complete source-frame count required')
    cache={};docs=[];seen=set();checks=[]
    acq=A.read_json(A.artifact(manifest['acquisition_manifest'],private=True,cache=cache));original={r['source_id']:r for r in acq['records']}
    if len(original)!=expected_count or set(original)!={r['source_id'] for r in rows}:raise ValueError('Acquisition source frame changed')
    for row in rows:
        sid=row['source_id']
        if sid in seen:raise ValueError('Duplicate source identifier')
        seen.add(sid)
        if row.get('coverage_status')!='complete_text_extraction_unvalidated':raise ValueError('Incomplete collection requires explicit disposition before fitting')
        for key in ('raw_artifact','text_artifact'):
            if not same(row[key],original[sid][key]):raise ValueError('Metadata step changed raw or normalized source binding')
        raw=A.artifact(row['raw_artifact'],private=True,cache=cache);p=A.artifact(row['text_artifact'],private=True,cache=cache);n=A.read_json(p,private=True)
        evid=[A.artifact(r,private=True,cache=cache) for r in row['evidence']]
        receipts=[A.read_json(p) for p in evid if p.suffix=='.json' and 'receipt' in p.name]
        if len(receipts)!=1:raise ValueError('One acquisition receipt is required')
        rec=receipts[0]
        if (A.fixture(rec) or A.fixture(n)) and not allow_fixtures:raise ValueError('Fixture source evidence cannot become observed text')
        if rec.get('source_id')!=sid or rec.get('status')!=200 or rec.get('error') or not same(rec.get('raw_artifact',{}),row['raw_artifact']) or not same(rec.get('normalized_artifact',{}),row['text_artifact']):raise ValueError('Acquisition receipt does not bind source text')
        if rec.get('extraction')!=row.get('extraction') or rec.get('received_bytes')!=raw.stat().st_size:raise ValueError('Extraction receipt changed')
        fmt=row['source_format'];ex=row['extraction']
        if fmt=='srt':
            turns=parse_srt(raw.read_bytes());duration=A.number(row.get('duration_seconds_publisher'),'Publisher duration',allow_none=False)
            if max(t['end'] for t in turns)>duration+2:raise ValueError('Caption timing exceeds publisher duration')
        elif fmt=='pdf':
            if not raw.read_bytes().startswith(b'%PDF-'):raise ValueError('PDF signature missing')
            extracted=A.artifact(ex['extracted_artifact'],private=True,cache=cache);info=A.artifact(ex['pdfinfo_artifact'],private=True,cache=cache)
            m=re.search(r'^Pages:\s+(\d+)\s*$',info.read_text(),re.M)
            if not m or int(m.group(1))!=ex['pages_reported']:raise ValueError('PDF metadata page count changed')
            turns=pdf_pages(extracted.read_text(),ex['pages_reported']);duration=None
        else:raise ValueError('Unsupported source format')
        if n.get('source_id')!=sid or n.get('turns')!=turns or n.get('text')!='\n'.join(t['text'] for t in turns):raise ValueError('Normalized text differs from exact source extraction')
        if len(turns)!=row['turn_count'] or len(n['text'].split())!=row['whitespace_words'] or hashlib.sha256(n['text'].encode()).hexdigest()!=row['text_content_sha256']:raise ValueError('Source word/turn/text hash declaration changed')
        text=clean_text(n['text'],fmt);tt=A.tokens(text);corpus=row['medium_id'];primary=row['source_kind'] in PRIMARY_KINDS and row['language']=='en'
        reason=None if primary else ('non_English_transcript' if row['language']!='en' else 'reference_or_republication_not_transcript')
        summary={k:row.get(k) for k in ('source_id','title','source_kind','source_format','published_at','date_status','language','language_basis','medium_id','publisher_id','medium_attribution','claimed_entities','caption_generation_provenance','transcript_generation_provenance','text_completeness','original_session_family_status','publication_family_id')}
        summary.update(corpus=corpus,short_id=sid.split(':')[-1][:12],source_url=A.safe_url(row['source_url']),download_url=A.safe_url(row['download_url']),unit='caption_publication' if fmt=='srt' else 'publisher_document',
            source_artifact_sha256=row['raw_artifact']['sha256'],text_artifact_sha256=row['text_artifact']['sha256'],text_content_sha256=row['text_content_sha256'],whitespace_words=row['whitespace_words'],analysis_tokens=len(tt),turn_count=len(turns),duration_seconds_publisher=duration,
            primary_eligible=primary,included_in_model=primary,model_unit_source_id=sid if primary else None,exclusion_reason=reason,keyword_rates=A.keyword_rates(tt),human_semantic_reading_complete=False,speaker_roles_verified=False)
        docs.append({'summary':summary,'text':text,'raw_text':n['text'],'tokens':tt,'turns':turns,'private_path':str(p)})
        checks.append({'source_id':sid,'text_artifact':row['text_artifact'],'raw_artifact':row['raw_artifact'],'evidence':row['evidence'],'extraction':ex})
    if sum(d['summary']['whitespace_words'] for d in docs)!=manifest['counts']['whitespace_words']:raise ValueError('Manifest total words mismatch')
    return docs,{'manifest_path':str(path),'manifest_sha256':A.sha(path),'artifacts':checks,'acquisition_manifest':manifest['acquisition_manifest']}

def collapse_exact_text(docs):
    groups=defaultdict(list)
    for d in docs:
        if d['summary']['primary_eligible']:groups[(d['summary']['corpus'],d['summary']['source_format'],d['summary']['source_artifact_sha256'])].append(d)
    units=[];aliases=[]
    for _,group in sorted(groups.items()):
        group.sort(key=lambda d:d['summary']['source_id']);first=group[0];units.append(first)
        for d in group:
            if d['raw_text']!=first['raw_text']:raise ValueError('Identical raw source bytes produced different text')
            d['summary']['included_in_model']=d is first;d['summary']['model_unit_source_id']=first['summary']['source_id']
            if d is not first:aliases.append({'source_id':d['summary']['source_id'],'model_unit_source_id':first['summary']['source_id'],'basis':'Exact raw caption/PDF bytes within publisher and format; audio identity and original performance are unresolved.'})
    return sorted(units,key=lambda d:(d['summary']['corpus'],d['summary']['source_id'])),aliases

def mask(text):return re.sub(r"[A-Za-z]+(?:['’][A-Za-z]+)*",lambda m:' ' if m.group().lower() in SOURCE_NAMES else m.group(),text)
def masked_docs(docs):return [{**d,'tokens':[t for t in d['tokens'] if t not in SOURCE_NAMES]} for d in docs]

def window(d,count=600):
    text=unicodedata.normalize('NFKC',d['text']).replace('’',"'");matches=list(A.TOKEN.finditer(text))
    if len(matches)!=len(d['tokens']):raise ValueError('Window token/source offsets differ')
    if len(matches)<count:return None
    start=(len(matches)-count)//2;return text[matches[start].start():matches[start+count-1].end()]

def matrix_result(matrix,docs):
    values=defaultdict(list);ids=[d['summary']['source_id'] for d in docs]
    for i in range(len(docs)):
        for j in range(i+1,len(docs)):
            a,b=sorted((docs[i]['summary']['corpus'],docs[j]['summary']['corpus']));values[a+'_within' if a==b else 'between_corpora'].append(float(matrix[i,j]))
    return {'source_ids':ids,'cosine_matrix':matrix.tolist(),'pair_summary':{k:{'pairs':len(v),'mean':float(np.mean(v)),'minimum':min(v),'maximum':max(v)} for k,v in values.items()},'scope':'Dependent source-text comparisons; not accuracy, belief agreement, causal influence or entity identity.'}

def keywords(docs):
    out=[]
    for corpus in sorted({d['summary']['corpus'] for d in docs}):
        group=[d for d in docs if d['summary']['corpus']==corpus];total=sum(len(d['tokens']) for d in group)
        for k in A.KEYWORDS:
            rates=[A.keyword_rates(d['tokens'])[k] for d in group];hits=sum(r['mentions'] for r in rates)
            out.append({'corpus':corpus,'keyword_group':k,'model_units':len(group),'tokens':total,'mentions':hits,'units_with_mentions':sum(r['mentions']>0 for r in rates),'equal_unit_mean_per_1000':float(np.mean([r['per_1000_tokens'] for r in rates])),'pooled_token_rate_per_1000':hits*1000/total})
    return out

def component_perturbation(X,k=4):
    from sklearn.decomposition import NMF
    from sklearn.metrics.pairwise import cosine_similarity
    from scipy.optimize import linear_sum_assignment
    baseline=NMF(n_components=k,init='nndsvdar',random_state=11,max_iter=800,tol=1e-4);baseline.fit(X);rows=[]
    for seed in range(101,109):
        ii=np.sort(np.random.default_rng(seed).choice(X.shape[0],size=int(.8*X.shape[0]),replace=False))
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter('always');fit=NMF(n_components=k,init='nndsvdar',random_state=seed,max_iter=800,tol=1e-4);fit.fit(X[ii])
        sim=cosine_similarity(baseline.components_,fit.components_);rr,cc=linear_sum_assignment(-sim)
        rows.append({'seed':seed,'included_row_indices':ii.tolist(),'component_matched_cosines':sim[rr,cc].tolist(),'mean_matched_cosine':float(sim[rr,cc].mean()),'iterations':int(fit.n_iter_),'warning':bool(notices)})
    return {'trials':rows,'mean_matched_cosine':float(np.mean([r['mean_matched_cosine'] for r in rows])),'scope':'Eight 80%-of-source-unit subsets, fixed full-corpus vocabulary/IDF and Hungarian component matching. Conditional perturbation diagnostic, not independent-session sampling, significance or reliability coefficient.'}

def reading_candidates(topics,units):
    lookup={d['summary']['source_id']:d for d in units};public=[];private=[]
    for component in topics.get('components',[]):
        index=component['component']-1;terms=set(t for t in component['terms'] if ' ' not in t)
        for corpus in sorted({d['summary']['corpus'] for d in units}):
            candidates=[r for r in topics['document_weights'] if lookup[r['source_id']]['summary']['corpus']==corpus]
            for rank,row in enumerate(sorted(candidates,key=lambda r:(-r['weights'][index],r['source_id']))[:2],1):
                d=lookup[row['source_id']];turns=d['turns'];scores=[sum(t in terms for t in A.tokens(x['text']))/max(1,len(A.tokens(x['text']))) for x in turns];position=int(np.argmax(scores))
                start=max(0,position-5) if d['summary']['source_format']=='srt' else position;end=min(len(turns),start+12) if d['summary']['source_format']=='srt' else start+1;selection=turns[start:end]
                rec={'component':index+1,'corpus':corpus,'rank_within_corpus':rank,'source_id':row['source_id'],'component_share':row['weights'][index],'turn_ids':[t['turn_id'] for t in selection],'text_artifact_sha256':d['summary']['text_artifact_sha256'],'words':sum(len(t['text'].split()) for t in selection),'selection':'High component share then highest top-word-density turn; context included for captions. Purposeful reading lead, not representative prevalence or validated semantic label.'}
                public.append(rec);private.append({**rec,'private_path':d['private_path'],'selected_turns':selection})
    return public,private

def qa_database(path,docs):
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE documents(source_id TEXT PRIMARY KEY,corpus TEXT,format TEXT,included_in_model INTEGER,text_sha256 TEXT); CREATE TABLE turns(source_id TEXT,turn_id TEXT,role TEXT,text TEXT,start REAL,end REAL,page INTEGER,PRIMARY KEY(source_id,turn_id)); CREATE TABLE punctuation_candidates(source_id TEXT,turn_id TEXT,question_marks INTEGER,status TEXT);')
        for d in docs:
            s=d['summary'];db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(s['source_id'],s['corpus'],s['source_format'],s['included_in_model'],s['text_artifact_sha256']))
            for t in d['turns']:
                db.execute('INSERT INTO turns VALUES(?,?,?,?,?,?,?)',(s['source_id'],t['turn_id'],'unknown',t['text'],t.get('start'),t.get('end'),t.get('page')))
                if '?' in t['text']:db.execute('INSERT INTO punctuation_candidates VALUES(?,?,?,?)',(s['source_id'],t['turn_id'],t['text'].count('?'),'unverified_punctuation_in_unknown_speaker_source'))
        counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('documents','turns','punctuation_candidates')}
    return {**counts,'verified_questions':0,'identified_answers':0,'scope':'Caption cues and PDF pages are not speaker-diarized turns; punctuation includes rhetorical questions and cue fragments.'}

def make_figures(out,r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    arts=[]
    def save(fig,name,caption):
        fig.tight_layout()
        for ext in ('png','svg','pdf'):
            p=out/(name+'.'+ext);fig.savefig(p,dpi=170,metadata={'Title':caption});arts.append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'caption':caption})
        plt.close(fig)
    rows=r['coverage']['primary_by_corpus'];keys=sorted(rows);fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,key,title in zip(axes,('model_units','whitespace_words'),('Exact-text model units','Words in model units')):
        ax.bar([LABELS[k] for k in keys],[rows[k][key] for k in keys],color=[COLORS[k] for k in keys]);ax.set_title(title);ax.spines[['top','right']].set_visible(False)
    save(fig,'text-coverage','Separate publisher/format strata; one exact Tracy caption-byte duplicate collapsed. Counts do not establish independent recordings or source identities.')
    fig,ax=plt.subplots(figsize=(11,6));themes=list(A.KEYWORDS);look={(x['corpus'],x['keyword_group']):x for x in r['keywords']['full']}
    for i,k in enumerate(keys):
        y=np.arange(len(themes))+(i-.5)*.23;equal=[look[k,t]['equal_unit_mean_per_1000'] for t in themes];pooled=[look[k,t]['pooled_token_rate_per_1000'] for t in themes]
        ax.hlines(y,np.minimum(equal,pooled),np.maximum(equal,pooled),color=COLORS[k]);ax.scatter(equal,y,c=COLORS[k],marker='o',label=LABELS[k]+' · equal unit');ax.scatter(pooled,y,c=COLORS[k],marker='x',label=LABELS[k]+' · pooled tokens')
    ax.set_yticks(range(len(themes)),[t.replace('_',' ') for t in themes]);ax.set_xlabel('Exact word forms / 1,000 analysis tokens');ax.legend(fontsize=8);ax.spines[['top','right']].set_visible(False)
    save(fig,'text-keywords','Equal-unit versus pooled-token keyword rates. Dictionary words may be polysemous, negated, quoted or recognition errors; not validated beliefs.')
    assignments=r['clusters'].get('assignments',[]);lookup={d['source_id']:d for d in r['documents']};fig,ax=plt.subplots(figsize=(8,6))
    for k in keys:
        group=[x for x in assignments if lookup[x['source_id']]['corpus']==k];ax.scatter([x['x'] for x in group],[x['y'] for x in group],c=COLORS[k],s=35,alpha=.8,label=LABELS[k],marker='o' if k==keys[0] else 's')
    ax.set_xlabel('TF-IDF SVD component 1');ax.set_ylabel('TF-IDF SVD component 2');ax.legend();ax.set_title('Source vocabulary map · not semantic ground truth')
    save(fig,'text-map','Two-dimensional SVD of name-masked TF-IDF. Source format, language preparation and dates confound publisher differences; projection is not a map of entity identities.')
    weights=r['topics']['document_weights'];fig,ax=plt.subplots(figsize=(11,5));im=ax.imshow(np.array([x['weights'] for x in weights]).T,aspect='auto',vmin=0,vmax=1,cmap='viridis');fig.colorbar(im,ax=ax,label='Normalized NMF weight');ax.set_yticks(range(r['topics']['displayed_k']),['Component '+str(i+1) for i in range(r['topics']['displayed_k'])]);ax.set_xlabel('Model source unit · Magenta then Tracy');ax.set_title('Exploratory components · four displayed, not an optimal count')
    save(fig,'text-topics','Component shares are normalized factor weights, not topic probabilities. Full candidate, seed and source-subset diagnostics are in the data.')
    fig,ax=plt.subplots(figsize=(10,5));series=[('Full TF-IDF',r['lexical']['name_masked']['pair_summary']),('600-token spans',r['lexical']['window_600']['pair_summary']),('Longest PDF removed',r['lexical']['leave_longest_out']['pair_summary'])];pairkeys=list(series[0][1]);x=np.arange(len(pairkeys))
    for i,(label,data) in enumerate(series):ax.bar(x+(i-1)*.24,[data[k]['mean'] for k in pairkeys],.24,label=label)
    ax.set_xticks(x,[k.replace('_within',' within').replace('_',' ') for k in pairkeys]);ax.set_ylabel('Mean TF-IDF cosine');ax.legend();ax.set_title('Length and influential-document sensitivity')
    save(fig,'text-sensitivity','Fixed full-corpus vocabulary/IDF for centered 600-token spans; longest-PDF removal refits vocabulary/IDF. These are exploratory controls, not matched discourse or inferential tests.')
    return arts

def study(manifest,output,expected_count,model_dir=None,semantic_cache=None):
    from sklearn.metrics.pairwise import cosine_similarity
    if A.sha(Path(A.__file__))!=BASE_CODE_SHA:raise ValueError('Pinned analysis helper changed')
    docs,audit=load_manifest(manifest,expected_count=expected_count);units,aliases=collapse_exact_text(docs)
    output=A.safe_path(output,private=True,exists=False)
    if output.exists():raise ValueError('Preserve earlier study outputs; choose a fresh output')
    output.mkdir(parents=True,mode=0o700)
    raw,*_=A.fit_lexical(units,'raw');content,*_=A.fit_lexical(units,'content');masked=masked_docs(units);lex,X,vec,chosen=A.fit_lexical(masked,'content');lex['variant']='publisher_name_masked'
    if X is None or len(chosen)!=len(units):raise ValueError('Every selected primary text must have a nonempty model vector')
    topics,clusters=A.topic_and_clusters(X,vec,chosen);perturbation=component_perturbation(X)
    leaders,private_leaders=reading_candidates(topics,units);A.write_json(output/'reading-leads-private.json',private_leaders)
    print(json.dumps({'stage':'lexical_complete_reading_leads_ready','model_units':len(units)}),flush=True)
    longest=max((d for d in units if d['summary']['source_format']=='pdf'),key=lambda d:len(d['tokens']))
    minus=[d for d in units if d is not longest];leave,*_=A.fit_lexical(masked_docs(minus),'content')
    spans=[(d,window(d)) for d in units];eligible=[(d,t) for d,t in spans if t is not None];winX=vec.transform(' '.join(t for t in A.tokens(text) if t not in SOURCE_NAMES and t not in A.FILLERS) for d,text in eligible)
    if np.any(np.asarray(winX.getnnz(axis=1)).ravel()==0):raise ValueError('A matched window has no vocabulary; requires explicit exclusion')
    win=matrix_result(np.clip(cosine_similarity(winX),0,1),[d for d,t in eligible]);win['excluded_short_source_ids']=[d['summary']['source_id'] for d,t in spans if t is None]
    semantic={'status':'not_run'}
    if model_dir:
        if semantic_cache is None:raise ValueError('Semantic cache path required')
        enc=A.FrozenEncoder(model_dir,semantic_cache);full=enc.encode([(d['summary']['source_id'],mask(d['text'])) for d in units]);neural_window=enc.encode([('window600:'+d['summary']['source_id'],mask(t)) for d,t in eligible])
        semantic={'status':'frozen_full_coverage_inference','model':enc.manifest,'processing':enc.binding,'full':matrix_result(cosine_similarity(np.stack([full[d['summary']['source_id']][0] for d in units])),units),'window_600':matrix_result(cosine_similarity(np.stack([neural_window['window600:'+d['summary']['source_id']][0] for d,t in eligible])),[d for d,t in eligible]),'coverage':[{'source_id':d['summary']['source_id'],**full[d['summary']['source_id']][2]} for d in units],'window_coverage':[{'source_id':d['summary']['source_id'],**neural_window['window600:'+d['summary']['source_id']][2]} for d,t in eligible]}
    leaders,private_leaders=reading_candidates(topics,units);counts=qa_database(output/'source-questions.sqlite',docs)
    coverage={}
    for c in sorted({d['summary']['corpus'] for d in units}):
        group=[d for d in units if d['summary']['corpus']==c];pubs=[d for d in docs if d['summary']['corpus']==c and d['summary']['primary_eligible']]
        coverage[c]={'primary_publications':len(pubs),'model_units':len(group),'whitespace_words':sum(d['summary']['whitespace_words'] for d in group),'publication_whitespace_words':sum(d['summary']['whitespace_words'] for d in pubs),'analysis_tokens':sum(len(d['tokens']) for d in group)}
    r={'schema_version':1,'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':A.sha(Path(__file__)),'helper_sha256':BASE_CODE_SHA,'input_manifest_sha256':A.sha(manifest),
        'coverage':{'observed_publications':len(docs),'expected_publications':expected_count,'primary_publications':sum(d['summary']['primary_eligible'] for d in docs),'primary_model_units':len(units),'excluded_from_English_transcript_fits':sum(not d['summary']['primary_eligible'] for d in docs),'primary_by_corpus':coverage,'all_publication_words':sum(d['summary']['whitespace_words'] for d in docs)},
        'documents':[d['summary'] for d in docs],'aliases':aliases,'lexical':{'raw':raw,'content':content,'name_masked':lex,'window_600':win,'leave_longest_out':leave},'topics':topics,'topic_source_subset_sensitivity':perturbation,'clusters':clusters,'network':A.network(lex,units),'keywords':{'dictionaries':A.KEYWORDS,'full':keywords(units),'leave_longest_out':keywords(minus)},
        'long_document_sensitivity':{'excluded_source_id':longest['summary']['source_id'],'title':longest['summary']['title'],'words':longest['summary']['whitespace_words'],'share_of_publisher_transcript_words':longest['summary']['whitespace_words']/coverage[longest['summary']['corpus']]['whitespace_words'],'scope':'Declared full frame retained; leave-one-source-out refits TF-IDF and recomputes keyword denominators. Selected by greatest transcript-PDF token count.'},
        'semantic':semantic,'reading_leads':leaders,'qa':counts,'transformations':{'analysis_tokenization':'Unicode NFKC, lowercase ASCII words with optional internal apostrophe; digits/punctuation excluded from lexical tokens. Negation stopwords retained.','source_name_mask':sorted(SOURCE_NAMES),'caption_markup':'HTML-style tags removed and entities unescaped for analysis only; raw caption bytes and normalized cue text unchanged.','semantic_inputs':'Case/punctuation retained, source names masked as whole apostrophe-aware words; centered600 spans use contiguous normalized source offsets.','pdf_scope':'Extracted text only, not visual/layout/diagram interpretation.'},
        'limitations':['Only two publisher contexts have newly acquired text here; this study does not claim text coverage of all28 screened accounts.','Publisher, medium and claimed entity attribution are separate metadata, not authenticated speaker/entity identity.','Captions/PDF pages are dependent parts of source publications; original recording/session families remain unresolved.','One exact caption-byte duplicate is grouped; identical text does not prove identical audio. Re-encoding, paraphrase and overlapping sessions remain possible.','Publisher and source format are confounded. Caption generation is unknown except one Magenta PDF explicitly declaring automated YouTube captions; extracted text is not audio-verified.','Portuguese and four reference/republication documents remain visible but are excluded from English transcript fits.','Word counts, clusters, embeddings and model-selected reading leads do not validate source assertions or quantify belief agreement.','Four displayed components are a readability choice; seed/subset agreement and silhouette are descriptive diagnostics, not optimal K or statistical reliability.','No model fine-tuning, weight editing, speaker diarization, verified semantic question answering, or full-document human close reading was performed.']}
    r['figures']=make_figures(output,r);A.write_json(output/'source-topics.json',r);A.write_json(output/'provenance-private.json',audit);A.write_json(output/'reading-leads-private.json',private_leaders)
    artifacts=[{'file':p.name,'bytes':p.stat().st_size,'sha256':A.sha(p),'public':p.name=='source-topics.json' or p.suffix in {'.png','.svg','.pdf'}} for p in sorted(output.iterdir())]
    A.write_json(output/'output-manifest.json',{'schema_version':1,'artifacts':artifacts,'input_manifest_sha256':A.sha(manifest),'script_sha256':A.sha(Path(__file__))});return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-count',type=int,required=True);p.add_argument('--model-dir',type=Path);p.add_argument('--semantic-cache',type=Path);a=p.parse_args();r=study(a.manifest,a.output,a.expected_count,a.model_dir,a.semantic_cache);print(json.dumps(r['coverage']))
if __name__=='__main__':main()
