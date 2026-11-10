#!/usr/bin/env python3
"""Freeze source-bound texts without promoting reference counts into upload totals.

Full text and physical paths stay in --private. Public output contains metadata only.
Legacy selected texts remain selected when a new publisher edition differs only in
whitespace at the same article URL. No speaker or supernatural identity is inferred.
"""
from __future__ import annotations
import argparse, collections, copy, csv, datetime as dt, hashlib, importlib.util, json, re, sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
BASE = Path('/workspace/channels-et-private')
OLD = BASE/'channel-lab-2026-11/frame-02/frame.json'
ACQ = BASE/'youtube-archive-2026-11'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def dump(p,obj):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def jsonl(p,rows):
    with Path(p).open('w') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def artifact(p):
    p=Path(p);raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':sha(raw)}
def load_sources():
    spec=importlib.util.spec_from_file_location('channel_sources',ROOT/'research/channel-lab/sources.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def edition_link(old,new,text,oldtext):
    """Only individually addressed OmNa articles are eligible for this URL join."""
    s=load_sources();url=s.canonical_url(new['publication_url'])
    if not url.startswith('https://omna.org/') or url.count('/')!=3 or url=='https://omna.org/':return None
    if s.canonical_url(old['publication_url'])!=url:return None
    if re.sub(r'\s+',' ',text)!=re.sub(r'\s+',' ',oldtext):
        raise ValueError('Same-article new edition differs substantively; manual edition review required')
    return {'left_edition_id':old['selected_edition_id'],'right_edition_id':new['selected_edition_id'],
            'basis':'exact_individual_article_URL_and_whitespace_folded_body_equality','value':url,
            'selection':'retain_previously_selected_edition; preserve_new_edition_and_media_link'}

def public_record(r):
    keys=['source_id','selected_edition_id','publication_id','publication_url','publication_urls','source_url','title',
          'recording_id','recording_family_id','media_sha256','media_hash_kind','audio_sha256','duration_seconds',
          'publication_date','publication_date_raw','channel_id','channel_name','creator_id','creator_name',
          'publisher_id','publisher_name','publisher_url','document_kind','text_origin','coverage_scope','attribution_scope',
          'speaker_role','claimed_label','claimed_labels','language','language_eligible','language_basis','cohorts',
          'legacy_source_ids','body_sha256','words','body_normalization','selection_rule','speaker_identity_verified',
          'audio_alignment_verified','original_contexts','cross_context_alias','edition_count','row_index',
          'media_state','text_state','analysis_state','mask_phrases','rights','asr_quality','admission_state','associated_media_ids',
          'claimed_label_provenance','youtube_ids','media_text_association']
    out={k:r.get(k) for k in keys}
    # Field quotations in source scope can be text excerpts: omit these from the metadata-only release.
    if isinstance(out.get('coverage_scope'),dict):out['coverage_scope']='body_only_publisher_message; source extraction boundaries retained privately'
    return out

def build(private,public):
    private.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    s=load_sources();previous=read(OLD);old=s.load_frame(OLD)
    media_path=ACQ/'accepted/publisher-media/publisher-media.json';media=read(media_path)
    recovery_path=ACQ/'accepted/publisher-text/private-manifest.json';recovery={r['record_id']:r for r in read(recovery_path)['records']}
    inv_path=ACQ/'accepted/inventory/inventory.json';inventory=read(inv_path)
    upstream_path=ROOT/'dist/channel-lab/collection-coverage.json';upstream=read(upstream_path)
    rights={'source_license':'not_established_for_redistribution','public_full_text_release':'withheld_pending_rights_basis',
            'private_retention':'research_archive','permission_claimed':False}
    records=[copy.deepcopy(x['record']) for x in old];texts={x['record']['source_id']:x['text'] for x in old}
    editions=copy.deepcopy(previous['alternate_editions']);links=copy.deepcopy(previous['merge_links'])
    byurl={s.canonical_url(r['publication_url']):r for r in records}
    closure={};media_rows=[];new_bodies=[];new_overlaps=[]
    def add_asset(ref,kind,source_id,edition_id=None):
        if not ref:return None
        p=Path(ref['path']);key=str(p)
        if not p.is_file():raise FileNotFoundError('Accepted artifact absent: '+key)
        row=closure.setdefault(key,{'path':key,'kind':kind,'bytes':p.stat().st_size,'sha256':ref.get('sha256'),
                                    'source_ids':[],'edition_ids':[],'verification':'path_and_size_present; digest_from_accepted_manifest'})
        if ref.get('bytes') is not None and ref['bytes']!=p.stat().st_size:raise ValueError('Artifact byte mismatch: '+key)
        if source_id not in row['source_ids']:row['source_ids'].append(source_id)
        if edition_id and edition_id not in row['edition_ids']:row['edition_ids'].append(edition_id)
        return row
    def media_row(r,ref,origin,association):
        asset=add_asset(ref,'source_media',r['source_id'])
        if not asset:return
        media_rows.append({'media_id':r.get('recording_id') or 'media-sha256:'+ref['sha256'],
            'source_id':r['source_id'],'channel_id':r['channel_id'],'bytes':asset['bytes'],'sha256':ref['sha256'],
            'duration_seconds':r.get('duration_seconds'),'origin':origin,'association':association,
            'retention_status':'physically_present','path':ref['path'],'source_url':r.get('source_url'),
            'audio_text_alignment_verified':False})
    for r in records:
        r['publication_id']=r.get('publication_id') or 'publication-url-sha256:'+sha(r['publication_url'].encode())
        r['rights']=rights.copy();r['asr_quality']='unmeasured; no human word-error-rate reference' if 'asr' in r['text_origin'].lower() else 'not_applicable_to_written_or_caption_origin; accuracy_not_newly_validated'
        r['admission_state']='selected_canonical_publication';r['associated_media_ids']=[]
        r['claimed_label_provenance']='inherited_source_context_attribution; not_identity_authentication'
        add_asset(r['text_artifact'],'selected_text',r['source_id'],r['selected_edition_id'])
        media_row(r,r.get('media_artifact'),'legacy_accepted_media','inherited_source_link_not_word_alignment')
        if r.get('recording_id'):r['associated_media_ids'].append(r['recording_id'])
    run_for={rid:run['run_id'] for run in media['source_runs'] for rid in run['successful_record_ids']}
    for m in media['records']:
        rid=m['record_id'];folder=ACQ/run_for[rid]/rid;rr=recovery.get(rid)
        textpath=(ACQ/'accepted/publisher-text'/rr['body_artifact']['file']) if rr else folder/'publisher-written.txt'
        ref=artifact(textpath);expected=rr['body_artifact'] if rr else m['written']
        if ref['sha256']!=expected['sha256'] or ref['bytes']!=expected['bytes']:raise ValueError('New written body drift: '+rid)
        text=s.normalize(textpath.read_text());url=s.canonical_url(m['page_url']);sid='doc-'+sha(url.encode())[:20]
        label=re.split(r'\s+by\s+',m['title'],flags=re.I)[-1].strip() if re.search(r'\s+by\s+',m['title'],re.I) else None
        eid='publisher-written:'+rid+':'+ref['sha256'][:12]
        audiofile=folder/('publisher-original.mp3' if m['audio']['retention']=='original_publisher_bytes' else 'publisher-retained.opus')
        aref={'path':str(audiofile),'sha256':m['audio']['sha256'],'bytes':m['audio']['bytes']}
        page=artifact(folder/'publisher-page.html')
        if page['sha256']!=m['page_sha256']:raise ValueError('Exact media page changed: '+rid)
        r={'source_id':sid,'selected_edition_id':eid,'publication_id':'publication-url-sha256:'+sha(url.encode()),
            'publication_url':url,'publication_urls':[url],'source_url':m['page_url'],'title':m['title'],
            'recording_id':'audio-sha256:'+m['audio']['sha256'],'recording_family_id':None,'audio_sha256':m['audio']['sha256'],
            'media_sha256':m['audio']['sha256'],'media_hash_kind':'encoded_audio_file','media_artifact':aref,
            'duration_seconds':m['audio']['decoded_duration_seconds'],'publication_date':None,'publication_date_raw':None,
            **s.OMNA,'document_kind':'publisher_written_message','text_origin':'publisher_written',
            'coverage_scope':'publisher_message_body; boilerplate/notices separated where documented; no ASR or word alignment',
            'attribution_scope':'publisher article title and per-page Natalie Glasson attribution; claimed speaker not authenticated',
            'speaker_role':'publisher_attributed_channeling_context','claimed_label':label,'claimed_labels':[label] if label else [],
            'claimed_label_provenance':{'basis':'exact_publisher_article_title_by_clause','page_sha256':m['page_sha256'],'field':'title','verified_identity':False},
            'language':'en','language_eligible':True,'language_basis':rr['language_basis'] if rr else 'English publisher-written message; acquisition admission, no human validation',
            'text_artifact':ref,'body_transform':'plain_text','body_sha256':sha(text.encode()),'words':len(text.split()),
            'body_normalization':s.NORMALIZATION,'selection_rule':'retain previous selected text for whitespace-equivalent same-article editions; otherwise admit verified publisher body',
            'cohorts':['publisher_media192_written'],'legacy_source_ids':[rid],'speaker_identity_verified':False,'audio_alignment_verified':False,
            'original_contexts':[{'channel_id':s.OMNA['channel_id'],'creator_id':s.OMNA['creator_id'],'publisher_id':s.OMNA['publisher_id']}],
            'cross_context_alias':False,'edition_count':1,'media_state':'retained_audio','text_state':'available_selected_edition','analysis_state':'eligible_frozen_frame',
            'admission_state':'selected_canonical_publication','rights':rights.copy(),'asr_quality':'not_ASR; written_audio_equivalence_unverified',
            'associated_media_ids':['audio-sha256:'+m['audio']['sha256']],'mask_phrases':['Natalie Glasson','Natalie Glasson / OmNa']+([label]if label else []),
            'youtube_ids':m['linked_youtube_ids'],'media_text_association':'cooccurring_on_exact_publisher_page; content_equivalence_unverified'}
        prior=byurl.get(url);merge=edition_link(prior,r,text,texts[prior['source_id']]) if prior else None
        if prior and not merge:raise ValueError('Unresolved publication URL collision')
        if merge:
            r['source_id']=prior['source_id'];links.append(merge);new_overlaps.append(merge)
            prior['associated_media_ids'].append(r['recording_id']);prior['youtube_ids']=m['linked_youtube_ids']
            prior['media_text_association']=r['media_text_association'];prior['edition_count']+=1
            # Physical retained audio is joined, not treated as a second independent body.
            for k in ['recording_id','audio_sha256','media_sha256','media_hash_kind','media_artifact','duration_seconds','media_state']:prior[k]=r[k]
            r['admission_state']='alternate_whitespace_equivalent_same_publication'
        else:
            records.append(r);texts[r['source_id']]=text;byurl[url]=r
        add_asset(ref,'text_edition',r['source_id'],eid);add_asset(page,'publisher_source_page',r['source_id'])
        media_row(r,aref,'publisher_linked_audio','cooccurring_page_links_not_content_or_word_alignment')
        media_rows[-1].update({'decoded_pcm_sha256':m['audio']['decoded_pcm_sha256'],
            'retention':m['audio']['retention'],'original_source_sha256':m['audio'].get('source_original',m['audio']).get('sha256'),
            'original_source_retained':m['audio']['retention']=='original_publisher_bytes','publisher_record_id':rid})
        editions.append({'source_id':r['source_id'],'edition_id':eid,'selected':not bool(merge),'cohort':'publisher_media192_written',
            'text_artifact_sha256':ref['sha256'],'body_sha256':r['body_sha256'],'words':r['words'],'text_origin':'publisher_written',
            'publication_url':url,'publication_id':r['publication_id'],'audio_sha256':r['audio_sha256'],'media_sha256':r['media_sha256'],
            'media_hash_kind':r['media_hash_kind'],'claimed_label':label,'channel_id':r['channel_id'],
            'reason':merge['selection'] if merge else 'New individually addressed publisher message; exact body/source hashes bound'})
        new_bodies.append({'record':r,'text':text})
    for i,r in enumerate(records):r['row_index']=i
    if len({r['source_id']for r in records})!=len(records) or len({r['body_sha256']for r in records})!=len(records):raise ValueError('Selected identity/body duplicate')
    for r in records:
        selected=[e for e in editions if e['source_id']==r['source_id'] and e['selected']]
        if len(selected)!=1 or selected[0]['edition_id']!=r['selected_edition_id']:raise ValueError('Edition selection not one-to-one')
    coverage={'documents':len(records),'words':sum(r['words'] for r in records),'text_editions':len(editions),
        'legacy_selected_editions':len(old),'new_publisher_editions':len(new_bodies),'new_publication_units':len(new_bodies)-len(new_overlaps),
        'new_editions_same_publication':len(new_overlaps),'publisher_contexts':len({r['channel_id']for r in records}),
        'creator_contexts':len({r['creator_id']for r in records}),'youtube_uploaded_total':None,'youtube_downloads':0,
        'youtube_observed_video_ids':len(inventory['videos']),'youtube_account_references':len(inventory['accounts']),
        'selected_linked_media_rows':len(media_rows),'selected_unique_encoded_media':len({m['sha256']for m in media_rows}),
        'new_publisher_audio_files':len(media['records']),'new_publisher_audio_bytes':sum(m['audio']['bytes']for m in media['records']),
        'new_publisher_audio_seconds':sum(m['audio']['decoded_duration_seconds']for m in media['records']),
        'text_origin_counts':dict(collections.Counter(r['text_origin']for r in records)),
        'date_missing_documents':sum(not r.get('publication_date')for r in records)}
    inputs=[artifact(p)for p in [OLD,media_path,recovery_path,inv_path,upstream_path,ROOT/'research/channel-lab/sources.py',Path(__file__)]]
    frame={'schema_version':'dataset-frame-1','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':'Finite source-bound convenience frame; selected publication units, not independent speakers or all channel uploads',
        'coverage':coverage,'records':records,'alternate_editions':editions,'merge_links':links,
        'new_merge_links':new_overlaps,'upstream_dispositions':previous['upstream_dispositions'],'inputs':inputs}
    dump(private/'frame.json',frame);jsonl(private/'texts.jsonl',[{'record':r,'text':texts[r['source_id']]}for r in records])
    jsonl(private/'new-editions.jsonl',new_bodies);jsonl(private/'physical-assets.jsonl',list(closure.values()));jsonl(private/'media.jsonl',media_rows)
    # selected corpus database: full bodies deliberately stay private.
    dbpath=private/'corpus.sqlite';db=sqlite3.connect(dbpath)
    db.executescript('DROP TABLE IF EXISTS documents; DROP TABLE IF EXISTS editions; DROP TABLE IF EXISTS media; DROP TABLE IF EXISTS documents_fts; CREATE TABLE documents(source_id TEXT PRIMARY KEY,publication_id TEXT,selected_edition_id TEXT UNIQUE,channel_id TEXT,creator_id TEXT,publisher_id TEXT,text_origin TEXT,body_sha256 TEXT UNIQUE,words INTEGER,text TEXT,metadata_json TEXT); CREATE TABLE editions(edition_id TEXT PRIMARY KEY,source_id TEXT,selected INTEGER,metadata_json TEXT); CREATE TABLE media(media_id TEXT,source_id TEXT,sha256 TEXT,metadata_json TEXT); CREATE VIRTUAL TABLE documents_fts USING fts5(source_id UNINDEXED,title,text);')
    for r in records:
        body=texts[r['source_id']];db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)',(r['source_id'],r['publication_id'],r['selected_edition_id'],r['channel_id'],r['creator_id'],r['publisher_id'],r['text_origin'],r['body_sha256'],r['words'],body,json.dumps(r,ensure_ascii=False)))
        db.execute('INSERT INTO documents_fts VALUES(?,?,?)',(r['source_id'],r['title'],body))
    for e in editions:db.execute('INSERT INTO editions VALUES(?,?,?,?)',(e['edition_id'],e['source_id'],int(e['selected']),json.dumps(e,ensure_ascii=False)))
    for m in media_rows:db.execute('INSERT INTO media VALUES(?,?,?,?)',(m['media_id'],m['source_id'],m['sha256'],json.dumps(m,ensure_ascii=False)))
    db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';db.close()
    upby={c['channel_id']:c for c in upstream['channels']};channels=[]
    for cid in sorted({r['channel_id']for r in records}):
        rows=[r for r in records if r['channel_id']==cid];mr=[m for m in media_rows if m['channel_id']==cid]
        channels.append({'channel_id':cid,'channel_name':rows[0]['channel_name'],'creator_id':rows[0]['creator_id'],'creator_name':rows[0]['creator_name'],
            'publisher_id':rows[0]['publisher_id'],'publisher_name':rows[0]['publisher_name'],'source_ids':[r['source_id']for r in rows],
            'selected_publications':len(rows),'text_editions':sum(e['channel_id']==cid for e in editions),'selected_words':sum(r['words']for r in rows),
            'retained_media_rows_joined':len(mr),'unique_encoded_media_joined':len({m['sha256']for m in mr}),
            'joined_media_seconds':sum(m['duration_seconds'] or 0 for m in mr),'origin_counts':dict(collections.Counter(r['text_origin']for r in rows)),
            'youtube_observed_ids_linked_to_documents':len({v for r in rows for v in r.get('youtube_ids',[])}),'youtube_uploaded_total':None,
            'youtube_downloaded_videos':0,'analyzed_publications':None,'analysis_state':'awaiting_dataset_analysis_snapshot',
            'legacy_collection_denominators':upby.get(cid),
            'denominator_note':'Publisher context, not a verified uploader identity; media segments, publications and observed YouTube IDs are distinct units',
            'rights':rights.copy()})
    docs=[public_record(r)for r in records]
    pmedia=[{k:v for k,v in m.items()if k!='path'}for m in media_rows]
    limits=['No channel lifetime upload total has been observed; unknown is null, never zero or a completion percentage.',
        'The 2,812 video IDs and 297 account references are discovery observations, not a current complete crawl.',
        'Zero YouTube downloads in this inventory; publisher audio is not recategorized as a YouTube download.',
        'Source-attributed medium and claimed-entity labels do not authenticate identities or independent speakers.',
        'Written editions are not ASR transcripts; publisher-page cooccurrence establishes no audiovisual equivalence or timing alignment.',
        'ASR accuracy has no held-out human reference; word error rate is unmeasured.',
        'Many dates are missing and channels have severely unequal convenience sampling; apparent topic differences are descriptive.',
        'Full media/text redistribution requires a documented rights basis; this release exports public metadata and derived annotations only.',
        'Legacy caption references whose original bodies cannot be verified remain metadata observations; absent, lost, and unknown are not retained text.',
        'Ra audio segments and preserved duplicate encodings remain distinct from full session textual units; do not sum all denominators.']
    payload={'schema_version':1,'dataset_version':'2026-11-08','generated_at':frame['generated_at'],
        'frame_sha256':sha((private/'frame.json').read_bytes()),'summary':coverage,'channels':channels,'documents':docs,
        'text_editions':editions,'merge_links':links,'new_merge_links':new_overlaps,'media':pmedia,
        'account_summary':inventory['coverage'],'rights':rights,'limitations':limits,
        'input_bindings':[{'input_id':'input-'+x['sha256'][:20],'sha256':x['sha256'],'bytes':x['bytes'],'role':Path(x['path']).name}for x in inputs],
        'downloads':[{'file':n,'label':label,'access':'public_metadata'}for n,label in [('documents.jsonl','Document metadata'),('editions.jsonl','Edition lineage'),('channels.csv','Publisher context coverage'),('youtube-accounts.jsonl','YouTube account observations'),('youtube-videos.jsonl','YouTube video observations'),('youtube-account-video-links.jsonl','Account/video attribution links'),('media.jsonl','Joined physical media metadata'),('schema.json','Schema and counting rules')]]}
    dump(public/'dataset.json',payload);jsonl(public/'documents.jsonl',docs);jsonl(public/'editions.jsonl',editions);jsonl(public/'media.jsonl',pmedia)
    jsonl(public/'youtube-accounts.jsonl',inventory['accounts']);jsonl(public/'youtube-videos.jsonl',inventory['videos']);jsonl(public/'youtube-account-video-links.jsonl',inventory['account_video_links'])
    with (public/'channels.csv').open('w')as f:
        fields=['channel_id','channel_name','selected_publications','text_editions','selected_words','retained_media_rows_joined','unique_encoded_media_joined','joined_media_seconds','youtube_observed_ids_linked_to_documents','youtube_uploaded_total','youtube_downloaded_videos','analyzed_publications']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:c[k]for k in fields}for c in channels)
    schema={'schema_version':1,'unit':'one selected edition per canonical publication/body component',
        'identity_fields':{'source_id':'Stable selected publication/body component, inherited for old records','publication_id':'Source-issued publication identifier when inherited; otherwise SHA256 of canonical individual URL','selected_edition_id':'One selected text edition per source_id','recording_id':'SHA256 of encoded media bytes; encoding identity, not semantic recording equivalence','channel_id':'Publisher context; not necessarily a YouTube account','creator_id':'Source-attributed medium/context, including mixed-speaker guest contexts','claimed_label':'Source attribution; does not prove an entity exists or is shared across mediums'},
        'null_policy':'Unknown, absent join or unmeasured; never impute zero from null','text_normalization':s.NORMALIZATION,
        'deduplication':'Existing frozen components retained; new individual OmNa article URLs join only after whitespace-folded body equality. All original edition hashes retained. Similarity alone never merges identities.',
        'private_artifacts':['frame.json','texts.jsonl','new-editions.jsonl','corpus.sqlite','physical-assets.jsonl'],
        'public_body_policy':'No full corpus bodies or private filesystem paths in public output','rights':rights,
        'required_document_fields':['source_id','publication_id','selected_edition_id','body_sha256','words','channel_id','text_origin','rights']}
    dump(public/'schema.json',schema)
    for p in public.glob('*'):
        if p.suffix in {'.json','.jsonl','.csv'}:
            raw=p.read_text()
            if any(z in raw for z in ['/workspace/','/dev/shm/','/tmp/','"text":']):raise ValueError('Private path/body leakage: '+str(p))
    s.load_frame(private/'frame.json')
    dump(private/'build-receipt.json',{'frame':artifact(private/'frame.json'),'sqlite':artifact(dbpath),'public_module':artifact(public/'dataset.json'),'coverage':coverage,'status':'passed_source_hash_identity_public_boundary_checks'})
    print(json.dumps(coverage,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--private',type=Path,default=BASE/'dataset-submission-2026-11');a.add_argument('--public',type=Path,default=ROOT/'dist/dataset-submission');args=a.parse_args();build(args.private,args.public)
