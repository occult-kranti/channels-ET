#!/usr/bin/env python3
"""Snapshot receipt-bound newly collected publisher audio/caption/ASR contexts."""
from __future__ import annotations
import argparse,collections,datetime as dt,difflib,hashlib,importlib.util,json,re,sqlite3
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('joint',Path(__file__).with_name('analyze.py'));J=importlib.util.module_from_spec(spec);spec.loader.exec_module(J)
A=J.A
LABELS={'tr-medium-natalie-glasson':'Natalie / OmNa recording context','tracy_kumbera_publisher':'Tracy publisher episode context','akanksshaa_publisher':'Multidimensional Soul episode context'}

def is_timestamp_repaired(status):
    return status not in (None, '', 'unadjusted')

def snapshot(path,out,name):
    path=A.safe_path(path,private=True);raw=path.read_bytes();data=json.loads(raw)
    if A.fixture(data):raise ValueError('Synthetic data cannot be observed collection')
    (out/name).write_bytes(raw)
    return data,{'path':str(path),'snapshot_file':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def validate_text(ref,source_id=None,duration=None,asr=False):
    p=A.artifact(ref,private=True);n=A.read_json(p,private=True)
    if A.fixture(n) or (source_id and n.get('source_id')!=source_id):raise ValueError('Text identity mismatch')
    turns=n.get('turns',[])
    if not turns or n.get('text')!='\n'.join(t['text'] for t in turns):raise ValueError('Turn/text stream mismatch')
    previous=-1;seen_turns=set()
    for t in turns:
        if not isinstance(t.get('turn_id'),str) or not t['turn_id'] or t['turn_id'] in seen_turns:raise ValueError('Unique turn identifier required')
        seen_turns.add(t['turn_id'])
        if t.get('role')!='unknown':raise ValueError('New machine text cannot acquire a speaker identity')
        start=t.get('start_seconds',t.get('start'));end=t.get('end_seconds',t.get('end'))
        start=A.number(start,'Segment start',allow_none=False);end=A.number(end,'Segment end',allow_none=False)
        if start<previous or end<start or (duration is not None and end>duration+2):raise ValueError('Ordered segment bounds invalid')
        previous=start
    if asr and (n.get('speaker_identity_verified') is not False or n.get('no_answer_identified') is not True):raise ValueError('ASR attribution/answer uncertainty must remain explicit')
    return n

def load(acquisition,asr_manifests,out):
    acq,acq_ref=snapshot(acquisition,out,'acquisition-snapshot.json');audio={};bindings=[acq_ref]
    prior,prior_ref=snapshot(J.ACCEPTED[2][0],out,'previous-caption-study.json')
    if prior_ref['sha256']!=J.ACCEPTED[2][1]:raise ValueError('Accepted previous caption study changed')
    bindings.append(prior_ref);prior_texts={d['text_artifact_sha256']:d for d in prior['documents']}
    for row in acq.get('records',[]):
        if row.get('status')!='completed':continue
        pid=row['publication_id']
        if pid in audio:raise ValueError('Duplicate completed publication')
        if row.get('input_representation')!='full_duration_lossy_opus_derivative':raise ValueError('This study requires declared retained derivative lineage')
        d=row['decoded_16k_mono']
        if not d.get('natural_eof') or d.get('decoder_returncode')!=0:raise ValueError('Incomplete audio decode cannot enter source frame')
        audio_path=A.artifact(row['audio'],private=True);receipt_path=audio_path.parent/'receipt.json'
        if not receipt_path.is_file() or A.read_json(receipt_path,private=True)!=row:raise ValueError('Collection row differs from immutable item receipt')
        audio[pid]=row
    editions=collections.defaultdict(list);dispositions=[];checks=[]
    for i,path in enumerate(asr_manifests):
        data,ref=snapshot(path,out,'asr-snapshot-'+str(i+1)+'.json');bindings.append(ref)
        for row in data.get('records',[]):
            if row.get('status')!='completed':continue
            normalized_path=Path(row['outputs']['normalized']['path']);receipt_candidates=[normalized_path.parent/'receipt.json',normalized_path.parent.parent/'receipt.json'];matches=[p for p in receipt_candidates if p.is_file() and A.read_json(p,private=True)==row]
            if len(matches)!=1:raise ValueError('ASR row must match one immutable item receipt')
            pid=row['publication_id']
            if pid not in audio:dispositions.append({'source_id':row['source_id'],'reason':'ASR completed after acquisition snapshot or outside this acquisition frame'});continue
            p=A.artifact(row['acquisition_receipt'],private=True);receipt=A.read_json(p,private=True)
            if receipt.get('publication_id')!=pid or receipt.get('audio',{}).get('sha256')!=audio[pid]['audio']['sha256']:raise ValueError('ASR acquisition receipt binds another media edition')
            if row.get('asr',{}).get('language_reported')!='en':dispositions.append({'source_id':row['source_id'],'reason':'Non-English or unknown recognition language excluded from English lexical model'});continue
            d=row['decoder']
            if not d.get('natural_eof') or d.get('decoder_returncode')!=0:raise ValueError('ASR decoded input incomplete')
            if any(d.get(k)!=audio[pid]['decoded_16k_mono'].get(k) for k in ['raw_pcm_sha256','sample_count','duration_seconds']):raise ValueError('ASR PCM does not match verified retained-audio decode')
            n=validate_text(row['outputs']['normalized'],row['source_id'],d['duration_seconds'],True)
            if len(n['text'].split())!=row['whitespace_words'] or len(n['turns'])!=row['segment_count']:raise ValueError('ASR declared words/segments changed')
            editions[pid].append({'row':row,'normalized':n,'text_artifact':row['outputs']['normalized'],'kind':'local_asr','created_at':row.get('created_at','')})
            checks.append({'source_id':row['source_id'],'text_artifact':row['outputs']['normalized'],'acquisition_receipt':row['acquisition_receipt']})
    for pid,row in audio.items():
        link=row.get('caption_link')
        if not link:continue
        if link.get('status')!='exact_guid_enclosure_link_not_audio_accuracy_validation':raise ValueError('Caption/publication exact-link receipt required')
        for caption in link['records']:
            n=validate_text(caption['text_artifact'],caption['source_id'],row['duration_seconds'])
            A.artifact(caption['raw_artifact'],private=True)
            editions[pid].append({'row':caption,'normalized':n,'text_artifact':caption['text_artifact'],'kind':'linked_publisher_caption','created_at':''})
    docs=[];seen_text={};seen_audio={}
    for pid,options in sorted(editions.items()):
        options.sort(key=lambda e:(e['kind']=='linked_publisher_caption',e['created_at'],e['row']['source_id']),reverse=True);pick=options[0];row=audio[pid];source=row['source'];n=pick['normalized'];sid=pick['row']['source_id'];text=J.html.unescape(re.sub(r'<[^>]*>','',n['text']));text_sha=hashlib.sha256(text.encode()).hexdigest();family=row['duplicate_family_id']
        for old in options[1:]:dispositions.append({'source_id':old['row']['source_id'],'selected_source_id':sid,'reason':'Alternative edition of same publication; exact linked publisher caption preferred, otherwise latest completed ASR receipt. Accuracy is not ranked.'})
        if family in seen_audio or text_sha in seen_text:
            dispositions.append({'source_id':sid,'selected_source_id':seen_audio.get(family,seen_text.get(text_sha)),'reason':'Exact original-audio family or exact normalized text alias'});continue
        seen_audio[family]=sid;seen_text[text_sha]=sid;group=source['medium_context_id'];tokens=J.mask_tokens(text)
        summary={'source_id':sid,'publication_id':pid,'group_id':group,'group_label':LABELS.get(group,group),'source_url':source['source_url'],'title':source['title'],'publisher':source.get('publisher'),'source_origin':source['source_origin'],'text_origin':pick['kind'],'source_role':'unknown_speakers_recording_context_only','claimed_entity_attribution':None,'words':len(n['text'].split()),'token_count':len(tokens),'turns':len(n['turns']),'duration_seconds':row['decoded_16k_mono']['duration_seconds'],'retained_audio_sha256':row['audio']['sha256'],'text_artifact_sha256':pick['text_artifact']['sha256'],'text_content_sha256':text_sha,'exact_original_family_id':family,'language':'en','human_accuracy_verified':False,'audio_text_alignment_verified':False,'publication_date':source.get('published_at'),'in_existing_frozen_models':None if pick['kind']=='linked_publisher_caption' else False,'same_source_old_written_pilot_possible':bool(source.get('linked_written_text')),'timestamp_normalization':pick['row'].get('normalization_status'),'timestamp_quality':pick['row'].get('normalization_recovery',{}).get('quality')}
        # Linked captions may already be fitted in the old Tracy corpus; no assertion of new recognition.
        previous=prior_texts.get(pick['text_artifact']['sha256']) if pick['kind']=='linked_publisher_caption' else None
        summary['publication_date_raw']=summary['publication_date'];summary['date_status']='publisher_metadata_unverified' if summary['publication_date'] else 'unknown'
        if pid=='@tracykumbera:rss:a213ea57efabb655':summary['publication_date']=None;summary['date_status']='known_unix_epoch_placeholder_not_chronology'
        summary['previous_study_source_id']=previous['source_id'] if previous else None;summary['previous_study_model_unit_id']=previous.get('model_unit_source_id') if previous else None;summary['in_existing_frozen_models']=bool(previous and previous.get('model_unit_source_id'))
        summary['prior_model_overlap']='Exact normalized-text hash matched accepted Tracy/Magenta Run01; reused text, not a new unique cross-study observation.' if previous else 'No exact admitted caption-edition match to previous Tracy/Magenta Run01.'
        summary['new_text_status']='new_local_recognition_edition' if pick['kind']=='local_asr' else 'reused_previously_acquired_publisher_caption_now_linked_to_retained_audio'
        docs.append({'summary':summary,'text':text,'tokens':tokens,'turns':n['turns']})
    return docs,audio,{'inputs':bindings,'verified_texts':checks,'dispositions':dispositions,'acquisition_status_at_snapshot':acq.get('status'),'finite_frame_count':acq.get('frame_count'),'retained_publications_at_snapshot':len(audio)}

def study(acquisition,asrs,out):
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import NMF
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    out=A.safe_path(out,private=True,exists=False)
    if out.exists():raise ValueError('Choose a fresh snapshot output')
    out.mkdir(parents=True,mode=0o700);code=A.sha(Path(__file__));(out/'executed-analyze-collected-audio.py').write_bytes(Path(__file__).read_bytes());docs,audio,audit=load(acquisition,asrs,out);A.write_json(out/'provenance-private.json',audit)
    modeldocs=[d for d in docs if len(d['tokens'])>=30];keywords=[]
    for d in docs:
        rates=A.keyword_rates(A.tokens(d['text']));keywords.append({'source_id':d['summary']['source_id'],'group_id':d['summary']['group_id'],'rates':rates})
    lexical={'status':'insufficient_documents','source_ids':[],'matrix':[]};topics={'status':'insufficient_documents','minimum_documents':5};clusters={'status':'insufficient_documents','minimum_documents':5}
    if len(modeldocs)>=2:
        vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=12000,stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}));X=vec.fit_transform(' '.join(d['tokens']) for d in modeldocs);lexical={'status':'fitted','source_ids':[d['summary']['source_id'] for d in modeldocs],'matrix':cosine_similarity(X).tolist(),'features':X.shape[1],'top_terms':[{'source_id':d['summary']['source_id'],'terms':[str(vec.get_feature_names_out()[j]) for j in X[i].toarray().ravel().argsort()[-12:][::-1]]} for i,d in enumerate(modeldocs)],'scope':'Whole recognized/caption text TF-IDF; source style, recognition and length confounded. No channellee attribution.'}
        spans=[(d,J.centered(d['text'],300)) for d in modeldocs];spans=[(d,t) for d,t in spans if t is not None]
        lexical['window_300_source_ids']=[d['summary']['source_id'] for d,t in spans];lexical['window_300_matrix']=cosine_similarity(vec.transform([t for d,t in spans])).tolist() if spans else [];lexical['window_rule']='Centered300tokens before masking, fixed full-fit vocabulary/IDF; shorter texts excluded, not padded.'
        if len(modeldocs)>=5:
            k=min(3,len(modeldocs)-1,X.shape[1]-1);nmf=NMF(n_components=k,init='nndsvdar',random_state=11,max_iter=800);W=nmf.fit_transform(X);shares=W/np.maximum(W.sum(axis=1,keepdims=True),1e-20);topics={'status':'exploratory_fit','k':k,'selection':'Display at most3factors when at least5eligible documents; not optimalcount or validatedtopics.','iterations':int(nmf.n_iter_),'components':[{'id':i+1,'terms':[str(vec.get_feature_names_out()[j]) for j in row.argsort()[-12:][::-1]]} for i,row in enumerate(nmf.components_)],'weights':[{'source_id':d['summary']['source_id'],'weights':shares[i].tolist()} for i,d in enumerate(modeldocs)]};km=KMeans(n_clusters=k,n_init=10,random_state=11).fit(X);clusters={'status':'exploratory_fit','k':k,'silhouette':float(silhouette_score(X,km.labels_,metric='cosine')) if len(set(km.labels_))>1 else None,'assignments':[{'source_id':d['summary']['source_id'],'cluster':int(km.labels_[i])+1} for i,d in enumerate(modeldocs)]}
    with sqlite3.connect(out/'source-text-private.sqlite') as db:
        db.executescript('CREATE TABLE documents(source_id TEXT PRIMARY KEY,publication_id TEXT,group_id TEXT,text_origin TEXT,text TEXT); CREATE TABLE turns(source_id TEXT,turn_id TEXT,role TEXT,text TEXT,start REAL,end REAL);')
        for d in docs:
            s=d['summary'];db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(s['source_id'],s['publication_id'],s['group_id'],s['text_origin'],d['text']))
            for t in d['turns']:db.execute('INSERT INTO turns VALUES(?,?,?,?,?,?)',(s['source_id'],t['turn_id'],'unknown',t['text'],t.get('start_seconds',t.get('start')),t.get('end_seconds',t.get('end'))))
    paired_written=[]
    for d in docs:
        s=d['summary'];source=audio[s['publication_id']]['source'];linked=source.get('linked_written_text')
        if not linked:continue
        path=A.artifact(linked,private=True);written=path.read_text();left=A.tokens(d['text']);right=A.tokens(written);matcher=difflib.SequenceMatcher(None,left,right,autojunk=False);matched=sum(block.size for block in matcher.get_matching_blocks())
        paired_written.append({'source_id':s['source_id'],'publication_id':s['publication_id'],'text_words':s['words'],'linked_written_words':len(written.split()),'linked_written_sha256':linked['sha256'],'matched_ordered_token_count':matched,'token_sequence_ratio':matcher.ratio(),'audio_alignment_verified':False,'scope':'Sequence overlap between publication-associated editions; introductions, omissions, rewording and recognition errors are mixed. This is not word error rate or recognition accuracy.'})
    groups=[]
    for g in sorted(set(r['source']['medium_context_id'] for r in audio.values())):
        acquired=[r for r in audio.values() if r['source']['medium_context_id']==g];selected=[d for d in docs if d['summary']['group_id']==g];groups.append({'id':g,'label':LABELS.get(g,g),'retained_audio_publications':len(acquired),'selected_text_units':len(selected),'new_local_asr_units':sum(d['summary']['text_origin']=='local_asr' for d in selected),'previously_modeled_caption_units':sum(d['summary']['in_existing_frozen_models'] for d in selected),'reused_caption_units':sum(d['summary']['text_origin']=='linked_publisher_caption' for d in selected),'words':sum(d['summary']['words'] for d in selected),'audio_seconds':sum(r['decoded_16k_mono']['duration_seconds'] for r in acquired),'analyzed_text_audio_seconds':sum(d['summary']['duration_seconds'] for d in selected)})
    r={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':code,'snapshot_bindings':[{'snapshot_file':x['snapshot_file'],'sha256':x['sha256'],'bytes':x['bytes']} for x in audit['inputs']],'scope':'Separate bounded snapshot of completed publisher audio with ASR and publisher-caption editions; never changes earlier292unit or20message fits. All-upload YouTube totals unknown.','coverage':{'finite_publisher_frame':audit['finite_frame_count'],'collection_status_at_snapshot':audit['acquisition_status_at_snapshot'],'retained_audio_publications':len(audio),'selected_text_units':len(docs),'timestamp_display_repaired_units':sum(is_timestamp_repaired(d['summary']['timestamp_normalization']) for d in docs),'lexical_model_units':len(modeldocs),'words':sum(d['summary']['words'] for d in docs),'groups':groups,'all_uploaded_youtube_videos':None,'duration_policy':{'non_bashar_min_seconds':0,'bashar_min_seconds':300}},'documents':[d['summary'] for d in docs],'excluded_and_aliases':audit['dispositions'],'keywords':keywords,'keyword_dictionaries':A.KEYWORDS,'keyword_dictionary_helper_sha256':J.HELPER_SHA,'keyword_scope':'Exact dictionary word forms per1000analysis tokens; polysemy, quoted/negated wording and recognition errors remain; no validated belief prevalence.','lexical':lexical,'topics':topics,'clusters':clusters,'paired_written_editions':paired_written,'qa':{'unverified_punctuation_turns':sum('?' in t['text'] for d in docs for t in d['turns']),'identified_answers':0,'speaker_diarization':False},'limitations':['All speaker roles are unknown; a linked page naming a claimed being does not identify every introduction, guest or transcript utterance.','Retained full-duration lossy audio does not make VAD/ASR text complete or accurate. Publisher captions and local ASR are different uncertain editions.','The snapshot includes only completed receipts at its recorded cutoff. Running collection and later successful transcripts need a new analysis edition.','Linked publisher captions may overlap the earlier Tracy study; new-audio and new-text counts remain separate. Written OmNa pilot messages are separate editions, not independent speakers.','Whole-text lexical models are sensitive to duration, source format, publisher repetition and unequal coverage. No semantic equivalence, significance or entity-origin probabilities are estimated.'],'figures':[]}
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,5));x=np.arange(len(groups));names=[g['label'].replace(' episode context','').replace(' recording context','') for g in groups];axes[0].bar(x-.18,[g['retained_audio_publications'] for g in groups],.36,label='Retained audio');axes[0].bar(x+.18,[g['selected_text_units'] for g in groups],.36,label='Selected text units');axes[0].set_xticks(x,names,rotation=25,ha='right');axes[0].set_ylabel('Publications / selected text units');axes[0].legend();axes[1].bar(names,[g['words'] for g in groups],color='#337d8b');axes[1].tick_params(axis='x',rotation=25);axes[1].set_ylabel('Words in selected text');fig.suptitle('Completed publisher collection snapshot');fig.tight_layout()
    for ext in ['png','svg','pdf']:
        p=out/('collected-coverage.'+ext);fig.savefig(p,dpi=150);r['figures'].append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'title':'Retained audio versus available analyzed text','alt':'Bounded completion snapshot; missing text is not zero topic prevalence, and the finite publisher frame is not all YouTube uploads.'})
    plt.close(fig)
    if lexical['status']=='fitted':
        fig,axes=plt.subplots(1,2,figsize=(11,5));fig.subplots_adjust(left=.08,right=.87,bottom=.15,wspace=.4)
        for ax,key,idskey,title in zip(axes,['matrix','window_300_matrix'],['source_ids','window_300_source_ids'],['Whole selected text','Centered300-token spans']):
            values=np.array(lexical[key]);ids=lexical[idskey]
            if not ids:ax.text(.5,.5,'Insufficient length',ha='center');ax.axis('off');continue
            im=ax.imshow(values,vmin=0,vmax=1,cmap='viridis');ax.set_xticks(range(len(ids)),range(1,len(ids)+1));ax.set_yticks(range(len(ids)),range(1,len(ids)+1));ax.set_title(title);ax.set_xlabel('Selected text unit, see JSON source order')
        cbax=fig.add_axes([.90,.2,.02,.6]);fig.colorbar(im,cax=cbax,label='TF-IDF cosine')
        for ext in ['png','svg','pdf']:
            p=out/('collected-similarity.'+ext);fig.savefig(p,dpi=150);r['figures'].append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'title':'New transcript vocabulary and length control','alt':'Whole selected ASR/caption text and centered300token spans, fixed vocabulary and IDF; positions identify publisher recording contexts, not claimed entities.'})
        plt.close(fig)
    if A.sha(Path(__file__))!=code:raise ValueError('Code changed during run')
    A.write_json(out/'collected-audio-analysis.json',r);A.write_json(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'collected-audio-analysis.json','sha256':A.sha(out/'collected-audio-analysis.json'),'bytes':(out/'collected-audio-analysis.json').stat().st_size}]+r['figures']});print(json.dumps({'coverage':r['coverage'],'sha256':A.sha(out/'collected-audio-analysis.json')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--asr',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();study(a.acquisition,a.asr,a.output)
