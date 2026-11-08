#!/usr/bin/env python3
"""A separately fitted, source-bound council discourse study; full text stays private."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import textwrap
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path('/workspace/channels-et-private')
PRIOR_AUDIO = PRIVATE/'subscription-screening-2026-11/publisher-audio-v3/manifest.json'
PRIOR_AUDIO_SHA = '82c007e60fdddd3c970bd4831beb632dca8a3fe183bbca01a715de6d409de694'
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
QUERIES = ['Galactic Council', 'Council of Contract', 'Council of Contact',
           'Galactic Council of Light', 'Galactic Council of Twelve', 'Galactic Council of 12']
KEYWORDS = {
    'contact_and_disclosure': ['contact','disclosure','ship','ships','extraterrestrial','extraterrestrials','alien','aliens','telepathy','telepathic'],
    'choice_and_agency': ['choice','choices','choose','choosing','consent','permission','decision','decisions','sovereignty'],
    'emotion_and_self_care': ['fear','fears','love','loving','anxiety','peace','compassion','healing','heart'],
    'collective_change': ['collective','humanity','earth','planet','planetary','ascension','transition','transformation'],
    'practice_and_attention': ['meditate','meditation','breathe','breathing','practice','practices','attention','awareness','focus'],
    'contracts_and_incarnation': ['contract','contracts','soul','souls','incarnation','incarnations','incarnational'],
}
LIMITATIONS = [
    'A publisher title or message attribution is a source claim, not verification of a being or of every utterance in a recording.',
    'Exact council names remain source-specific; shared labels and the word council do not establish shared identity, stable membership, or independent origin.',
    'The purposive accessible source frame has unequal media, dates, lengths and text-generation methods. Results do not describe all channeling or all YouTube uploads.',
    'Machine transcripts have unknown speaker roles and unmeasured accuracy. Written messages are distinct editorial editions, not verified verbatim audio references.',
    'TF-IDF measures vocabulary overlap; NMF factors and clusters are exploratory descriptions, not doctrines, topic probabilities or paranormal validation.',
    'Keyword counts include negation, quotation and incidental mentions. They do not measure belief, factual truth, or the prevalence of an entity.',
    'No same-question equivalence or answer identification follows from punctuation, adjacent text, or a high similarity score.',
    'Existing-corpus phrase hits are retrieval leads only and are kept separate from newly inspected source attributions.',
]


def sha_bytes(raw): return hashlib.sha256(raw).hexdigest()
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024**2), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def private_path(value, exists=True):
    p = Path(value).absolute()
    if '..' in p.parts or not p.is_relative_to(PRIVATE) or any(x.is_symlink() for x in (p,*p.parents)):
        raise ValueError('Expected a non-symlink private archive path')
    if exists and not p.is_file(): raise ValueError('Private source artifact missing')
    return p


def checked(ref):
    p = private_path(ref['path'])
    if p.stat().st_size != ref['bytes'] or sha(p) != ref['sha256']:
        raise ValueError('Source artifact hash or byte count changed')
    return p


def tokens(text):
    return [x.replace('’', "'").casefold() for x in TOKEN.findall(unicodedata.normalize('NFKC', text))]


def phrase_pattern(value):
    parts = re.split(r'\s+', unicodedata.normalize('NFKC', value).strip())
    return re.compile(r'(?<!\w)' + r'[\s\-]+'.join(re.escape(x) for x in parts) + r'(?!\w)', re.I)


def mask_text(text, phrases):
    result = unicodedata.normalize('NFKC', text)
    for phrase in sorted(set(phrases), key=lambda x:(-len(x),x.casefold())):
        if phrase.strip(): result = phrase_pattern(phrase).sub(' ', result)
    return result


def centered_span(text, size=300):
    normalized = unicodedata.normalize('NFKC', text)
    matches = list(TOKEN.finditer(normalized))
    if len(matches) < size: return None
    start = (len(matches)-size)//2
    # Retain interstitial digits and punctuation until full title phrases are masked.
    return normalized[matches[start].start():matches[start+size-1].end()]


def recursive_bindings(value):
    if isinstance(value, dict):
        if {'path','bytes','sha256'} <= value.keys(): yield value
        else:
            for child in value.values(): yield from recursive_bindings(child)
    elif isinstance(value, list):
        for child in value: yield from recursive_bindings(child)


def select_editions(documents):
    selected,exclusions=[],[];families={};seen_text={}
    # A declared publisher message/audio pairing is an edition family, not two
    # independent communications. Prefer its bounded written message for fitting.
    for d in sorted(documents,key=lambda d:(d['summary']['source_format']=='normalized_asr',d['summary']['source_id'])):
        s=d['summary'];family=s['publication_family_id'];text_sha=s['text_content_sha256']
        if family and family in families:
            exclusions.append({'source_id':s['source_id'],'selected_source_id':families[family],'reason':'declared_publication_family_alternate_edition; publisher_written_message_preferred',
                               'publication_family_id':family,'words':s['words'],'text_content_sha256':text_sha,'text_origin':s['text_origin']});continue
        if text_sha in seen_text:
            exclusions.append({'source_id':s['source_id'],'selected_source_id':seen_text[text_sha],'reason':'exact_normalized_text_alias'});continue
        if family:families[family]=s['source_id']
        seen_text[text_sha]=s['source_id'];selected.append(d)
    return sorted(selected,key=lambda d:d['summary']['source_id']),exclusions


def load(manifests, output):
    documents, bindings, exclusions, seen_ids = [], [], [], set()
    prior_audio = None
    for number, path in enumerate(manifests):
        path = private_path(path); raw = path.read_bytes(); manifest = json.loads(raw)
        if manifest.get('synthetic') or manifest.get('fixture'): raise ValueError('Fixture is not an observed corpus')
        snapshot = 'input-manifest-'+str(number+1)+'.json'; (output/snapshot).write_bytes(raw)
        bindings.append({'snapshot_file':snapshot,'sha256':sha_bytes(raw),'bytes':len(raw)})
        for row in manifest.get('documents', manifest.get('records', [])):
            sid = row['source_id']
            if sid in seen_ids: raise ValueError('Source ID repeated across manifests')
            seen_ids.add(sid)
            for artifact in recursive_bindings(row): checked(artifact)
            text_ref = row['text_artifact']; p = checked(text_ref)
            if p.suffix == '.json':
                normalized = json.loads(p.read_text()); text = normalized['text']
                turns = normalized.get('turns', [])
            else: normalized = {}; text = p.read_text(); turns = []
            if not isinstance(text, str) or not text.strip():
                exclusions.append({'source_id':sid,'reason':'empty_text'}); continue
            if row.get('words') is not None and len(text.split()) != row['words']:
                raise ValueError('Declared source words differ from retained text')
            if row.get('asr_receipt'):
                receipt = json.loads(checked(row['asr_receipt']).read_text())
                acq = json.loads(checked(row['acquisition_receipt']).read_text())
                if receipt.get('status') != 'completed' or receipt['publication_id'] != acq['publication_id']:
                    raise ValueError('ASR/acquisition identity mismatch')
                if receipt['outputs']['normalized']['sha256'] != text_ref['sha256'] or normalized.get('source_id') != receipt['source_id']:
                    raise ValueError('ASR text edition differs from receipt')
                if len(text.split()) != receipt['whitespace_words'] or len(turns) != receipt['segment_count']:
                    raise ValueError('ASR word or segment count changed')
                if any(t.get('role') != 'unknown' for t in turns): raise ValueError('ASR cannot gain a verified speaker role')
                if receipt['acquisition_receipt']['sha256'] != row['acquisition_receipt']['sha256']:
                    raise ValueError('ASR bound another retained audio edition')
                if row.get('audio_artifact') and acq['audio']['sha256'] != row['audio_artifact']['sha256']:
                    raise ValueError('Audio artifact differs from acquisition receipt')
                if row.get('decoded_audio_seconds') is not None and not math.isclose(row['decoded_audio_seconds'],acq['decoded_16k_mono']['duration_seconds'],abs_tol=1e-7):
                    raise ValueError('Audio duration differs from acquisition receipt')
                if prior_audio is None:
                    if sha(PRIOR_AUDIO)!=PRIOR_AUDIO_SHA:raise ValueError('Prior audio frame changed')
                    prior_audio={r['publication_id']:r for r in json.loads(PRIOR_AUDIO.read_text())['records']}
                prior=prior_audio.get(acq['publication_id'])
                reused=bool(prior is not None and prior==acq)
                if prior is not None and not reused:raise ValueError('Prior publication ID now binds another acquisition edition')
                origin='reused_prior_verified_frame' if reused else 'new_council_pilot' if row.get('acquisition_origin')=='new_council_pilot' and private_path(row['acquisition_receipt']['path']).is_relative_to(PRIVATE/'council-study-2026-11') else 'unresolved_acquisition_origin'
                if row.get('acquisition_origin') and row['acquisition_origin']!=origin:raise ValueError('Declared acquisition origin differs from bound source frame')
                probe=acq['audio'].get('probe',{})
                raw_rate=(probe.get('raw',{}).get('format',{}) or {}).get('bit_rate')
                representation={'codec':probe.get('first_audio_codec'),'channels':probe.get('channels'),
                                'container_reported_bitrate_bps':int(raw_rate) if raw_rate is not None else None,
                                'scope':'Retained derivative metadata; container average bitrate is not a nominal encoder target or an accuracy measure.'}
                recognition={'receipt_sha256':row['asr_receipt']['sha256'],'model_files_sha256':receipt.get('model',{}).get('files_sha256'),
                             'language_mode':receipt.get('model',{}).get('language_mode'),'language_reported':receipt.get('asr',{}).get('language_reported'),
                             'condition_on_previous_text':receipt.get('asr',{}).get('settings',{}).get('condition_on_previous_text'),
                             'cpu_threads':receipt.get('asr',{}).get('cpu_threads'),
                             'scope':'Recognition configuration and source-format differences remain confounded with medium/context; no accuracy comparison.'}
            else:reused=False;origin='written_source_not_audio_acquisition';representation=None;recognition=None
            text = unicodedata.normalize('NFKC', text).strip()
            text_sha = sha_bytes(text.encode())
            medium = row.get('medium_name', row.get('medium', 'Unknown medium'))
            label = row.get('council_label_exact',row.get('council_label','Unresolved council label'))
            summary = {'source_id':sid,'primary_source_id':row.get('primary_source_id',sid),
                       'title':row['title'],'source_url':row.get('canonical_url',row.get('source_url')),
                       'medium_id':row.get('medium_id'),'medium':medium,'council_id':row.get('council_id'),
                       'council_label_exact':label,'attribution_scope':row.get('attribution_scope',row.get('source_local_attribution')),
                       'text_origin':row.get('source_type',row.get('text_origin','publisher_text')),
                       'corpus_kind':row.get('corpus_kind','publisher_attributed_recording_context' if row.get('asr_receipt') else 'publisher_attributed_written_message'),
                       'discussed_council_label':row.get('discussed_council_label'),
                       'text_scope':row.get('body_boundary',row.get('text_scope')),'access_depth':row.get('access_depth'),
                       'published_at':row.get('published_at'),'published_at_basis':row.get('published_at_basis','publisher_metadata_unverified'),
                       'words':len(text.split()),'analysis_tokens':len(tokens(text)),
                       'text_artifact_sha256':text_ref['sha256'],'text_content_sha256':text_sha,
                       'source_format':'normalized_asr' if row.get('asr_receipt') else 'publisher_written_message',
                       'speaker_identity_verified':False,'audio_alignment_verified':False,'audio_listened':False,
                       'decoded_audio_seconds':row.get('decoded_audio_seconds'),'retained_audio_sha256':(row.get('audio_artifact') or {}).get('sha256'),
                       'reused_from_existing_collection':reused,'acquisition_origin':origin,
                       'audio_representation':representation,'recognition':recognition,
                       'publication_family_id':row.get('publication_family_id'),
                       'timestamp_normalization':row.get('normalization_status'),
                       'question_punctuation_count':text.count('?'),'identified_answers':0}
            documents.append({'summary':summary,'text':text,'turns':turns})
    selected,aliases=select_editions(documents)
    return selected, bindings, exclusions+aliases


def existing_retrieval(output):
    helper = ROOT/'research/expanded-channeling/analyze.py'
    spec = importlib.util.spec_from_file_location('accepted_joint',helper)
    joint = importlib.util.module_from_spec(spec);spec.loader.exec_module(joint)
    docs, audit, _ = joint.load_accepted()
    write(output/'existing-corpus-provenance-private.json',audit)
    hits, private_hits = [], []
    for doc in docs:
        s = doc['summary']; counts = {q:len(list(phrase_pattern(q).finditer(doc['text']))) for q in QUERIES}
        if not any(counts.values()): continue
        hits.append({'source_id':s['source_id'],'title':s.get('title'),'source_url':s.get('source_url'),
                     'group_id':s['group_id'],'counts':counts,'total_phrase_matches':sum(counts.values()),
                     'text_artifact_sha256':s['text_artifact_sha256'],'attribution_status':'unverified_phrase_retrieval_only'})
        for query in QUERIES:
            for match in phrase_pattern(query).finditer(doc['text']):
                private_hits.append({'source_id':s['source_id'],'query':query,'start':match.start(),'end':match.end(),
                                     'context':doc['text'][max(0,match.start()-350):match.end()+350]})
    write(output/'existing-corpus-hits-private.json',private_hits)
    reviews=[];review_file=Path(__file__).with_name('retrieval-reading.json')
    if review_file.exists():
        for review in json.loads(review_file.read_text())['reviews']:
            matches=[h for h in private_hits if h['source_id']==review['source_id'] and h['query']==review['query'] and h['start']==review['matched_start_character'] and h['end']==review['matched_end_character']]
            if len(matches)!=1:raise ValueError('Retrieval reading does not identify one exact match window')
            context=matches[0]['context'];source=next(h for h in hits if h['source_id']==review['source_id'])
            if sha_bytes(context.encode())!=review['context_sha256'] or len(context.split())!=review['context_words_read'] or source['text_artifact_sha256']!=review['text_artifact_sha256'] or source['source_url']!=review['source_url']:
                raise ValueError('Retrieval interpretation source window changed')
            if review['speaker_role']!='unknown' or review['human_annotation'] is not False or review['audio_listened'] is not False:
                raise ValueError('Retrieval interpretation verification scope changed')
            reviews.append(review)
    return {'scope':'Exact phrase retrieval in the separately accepted 292-unit corpus. Hits are not new acquisitions or attributed council messages; overlapping nested phrases are counted separately.',
            'documents_searched':len(docs),'words_searched':sum(len(d['text'].split()) for d in docs),
            'queries':QUERIES,'documents_with_hits':len(hits),'hits':hits,
            'query_counts':[{'query':q,'documents':sum(h['counts'][q]>0 for h in hits),'occurrences':sum(h['counts'][q] for h in hits)} for q in QUERIES],
            'accepted_inputs':[{'sha256':b['sha256'],'bytes':b['bytes']} for b in audit['inputs']],
            'context_reviews':reviews,'context_review_coverage':{'windows_read':len(reviews),'words_in_windows':sum(r['context_words_read'] for r in reviews),'full_documents_read_for_this_annotation':0,'human_annotation':False,'audio_listened':False},
            'loader_sha256':sha(helper),'matched_excerpt_text_public':False}


def reviewed_reading(path,documents,bindings):
    if path is None:return {'status':'not_supplied'}
    p=private_path(path);raw=p.read_bytes();reading=json.loads(raw)
    if reading.get('source_manifest_sha256') not in {x['sha256'] for x in bindings}:
        raise ValueError('Reading binds a different text manifest')
    by_id={d['summary']['source_id']:d for d in documents}
    selected=set()
    def validate_support(support):
        d=by_id[support['source_id']];s=d['summary'];selected.add(s['source_id'])
        if support['text_artifact_sha256']!=s['text_artifact_sha256'] or support.get('canonical_url',s['source_url'])!=s['source_url']:
            raise ValueError('Reading source edition differs')
        turns={t['turn_id']:t for t in d['turns']}
        endpoints=support.get('turn_ids') or [support['first_turn_id'],support['last_turn_id']]
        first,last=(turns[x] for x in (endpoints[0],endpoints[-1]))
        if abs(first.get('start_seconds',first.get('start'))-support['start_seconds'])>1e-6 or abs(last.get('end_seconds',last.get('end'))-support['end_seconds'])>1e-6:
            raise ValueError('Reading locator differs from unknown-role ASR segments')
        if support.get('audio_alignment_verified') is not False or support.get('role')!='unknown':
            raise ValueError('Unsupported spoken-role or alignment assertion')
    for item in reading['readings']:
        if item.get('question_type')!='analyst_constructed_comparison_not_a_verified_spoken_question':
            raise ValueError('Reading question scope changed')
        for support in item['supports']:
            validate_support(support)
    matrix=reading.get('reading_matrix',{})
    columns={x['id'] for x in matrix.get('columns',[])}
    for row in matrix.get('rows',[]):
        if set(row['cells'])!=columns or row['title']!=by_id[row['source_id']]['summary']['title']:
            raise ValueError('Reading matrix rows or columns changed')
        for cell in row['cells'].values():
            for support in cell['supports']:validate_support(support)
    coverage=reading['coverage']
    if coverage['documents_read_in_full']!=len(selected) or coverage['asr_words_read']!=sum(by_id[s]['summary']['words'] for s in selected):
        raise ValueError('Reading coverage does not match supported source texts')
    if coverage['human_annotation'] is not False or coverage['audio_content_listened'] is not False:
        raise ValueError('Reading coverage provenance changed')
    return {**reading,'artifact_binding':{'sha256':sha_bytes(raw),'bytes':len(raw)}}


def supplemental_reading(path,documents):
    raw=private_path(path).read_bytes();reading=json.loads(raw)
    by_id={d['summary']['source_id']:d for d in documents}
    d=by_id[reading['source_id']];s=d['summary'];body=d['text']
    if reading['title']!=s['title'] or reading['text_artifact_sha256']!=s['text_artifact_sha256']:
        raise ValueError('Supplemental reading source edition differs')
    coverage=reading['coverage'];spans=coverage['spans'];last=0
    def validate_span(span):
        a,b=span['start_character'],span['end_character']
        if not isinstance(a,int) or not isinstance(b,int) or not 0<=a<b<=len(body):
            raise ValueError('Reading span outside retained source text')
        selected=body[a:b]
        if span['span_sha256']!=sha_bytes(selected.encode()) or span['words']!=len(selected.split()):
            raise ValueError('Reading span hash or word count differs')
    for span in spans:
        validate_span(span)
        if span['start_character']<last:raise ValueError('Reading coverage overlaps or is unordered')
        last=span['end_character']
    if not spans or coverage['words_read']!=sum(x['words'] for x in spans):
        raise ValueError('Reading coverage denominator differs')
    full=len(spans)==1 and spans[0]['start_character']==0 and spans[0]['end_character']==len(body)
    if coverage['full_document_read']!=full or coverage['human_annotation'] is not False or coverage['audio_listened'] is not False:
        raise ValueError('Reading coverage verification scope changed')
    for observation in reading['observations']:
        if not observation['supports']:raise ValueError('Supplemental paraphrase needs source support')
        for support in observation['supports']:
            validate_span(support)
            if not any(span['start_character']<=support['start_character']<support['end_character']<=span['end_character'] for span in spans):
                raise ValueError('Paraphrase support outside declared reading coverage')
            if support['role']!='unknown' or support['audio_alignment_verified'] is not False:
                raise ValueError('Supplemental reading cannot verify a speaker or audio alignment')
            if support.get('turn_ids'):
                turns={t['turn_id']:t for t in d['turns']};first,last=(turns[x] for x in (support['turn_ids'][0],support['turn_ids'][-1]))
                if not math.isclose(first.get('start_seconds',first.get('start')),support['start_seconds'],abs_tol=1e-6) or not math.isclose(last.get('end_seconds',last.get('end')),support['end_seconds'],abs_tol=1e-6):
                    raise ValueError('Supplemental reading turn/time locator differs')
    return {**reading,'source_url':s['source_url'],'artifact_binding':{'sha256':sha_bytes(raw),'bytes':len(raw)}}


def fit(documents):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    from sklearn.metrics import silhouette_score,adjusted_rand_score
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import NMF,TruncatedSVD
    from sklearn.cluster import KMeans
    phrases = sorted({d['summary']['council_label_exact'] for d in documents} | {d['summary']['medium'] for d in documents})
    selected = [d for d in documents if len(tokens(mask_text(d['text'],phrases))) >= 30]
    lexical = {'status':'insufficient_documents','source_ids':[],'matrix':[],'window_300_source_ids':[],'window_300_matrix':[], 'pairs':[], 'top_terms':[],
               'mask_phrases':phrases,'mask_rule':'Longest complete council-label and medium-name phrases only; no global deletion of contact, light, council, or other constituent words.'}
    topics = {'status':'insufficient_documents','minimum_documents':5}; clusters = {'status':'insufficient_documents','minimum_documents':5}
    if len(selected)<2:return lexical,topics,clusters
    vec = TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,ngram_range=(1,2),min_df=1,
                          sublinear_tf=True,max_features=12000,stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}))
    texts = [' '.join(tokens(mask_text(d['text'],phrases))) for d in selected]
    try:X = vec.fit_transform(texts)
    except ValueError:return {**lexical,'status':'insufficient_nonstop_vocabulary'},topics,clusters
    cosine = cosine_similarity(X)
    spans=[]
    for d in selected:
        span=centered_span(d['text'])
        if span is None:continue
        spans.append((d,' '.join(tokens(mask_text(span,phrases)))))
    windows=cosine_similarity(vec.transform([t for _,t in spans])) if spans else np.empty((0,0))
    rawvec=TfidfVectorizer(**vec.get_params());raw=cosine_similarity(rawvec.fit_transform([' '.join(tokens(d['text'])) for d in selected]))
    pairs=[]
    for i,left in enumerate(selected):
        for j in range(i+1,len(selected)):
            a,b=left['summary'],selected[j]['summary'];same_medium=bool(a['medium_id'] and a['medium_id']==b['medium_id'])
            same_label=a['council_label_exact'].casefold()==b['council_label_exact'].casefold()
            pairs.append({'source':a['source_id'],'target':b['source_id'],'cosine':float(cosine[i,j]),'unmasked_cosine':float(raw[i,j]),
                          'same_medium':same_medium,'same_exact_label':same_label,
                          'category':'same_medium_same_label' if same_medium and same_label else 'same_medium_different_label' if same_medium else 'different_medium_same_label' if same_label else 'different_medium_different_label'})
    summaries=[]
    for category in sorted({p['category'] for p in pairs}):
        rows=[p for p in pairs if p['category']==category]
        summaries.append({'category':category,'pairs':len(rows),'mean_cosine':float(np.mean([p['cosine'] for p in rows])),
                          'mean_unmasked_cosine':float(np.mean([p['unmasked_cosine'] for p in rows]))})
    lexical.update(status='fitted',source_ids=[d['summary']['source_id'] for d in selected],matrix=cosine.tolist(),
                   window_300_source_ids=[d['summary']['source_id'] for d,_ in spans],window_300_matrix=windows.tolist(),
                   unmasked_matrix=raw.tolist(),features=X.shape[1],pairs=pairs,pair_summaries=summaries,
                   window_rule='Centered 300 raw-token span before phrase masking; fixed masked whole-document vocabulary/IDF; short texts excluded.',
                   unmasked_sensitivity='Separately refitted unmasked vocabulary/IDF; same selected documents. Descriptive name-mask sensitivity, not a validation test.',
                   top_terms=[{'source_id':d['summary']['source_id'],'terms':[str(vec.get_feature_names_out()[j]) for j in X[i].toarray().ravel().argsort()[-10:][::-1]]} for i,d in enumerate(selected)],
                   pair_scope='Dependent document pairs; unequal length, source style, editions, speaker roles and label coverage remain confounded. No significance or agreement probability.')
    if len(selected)>=5 and X.shape[1]>=4:
        k=min(3,len(selected)-1,X.shape[1]-1);model=NMF(n_components=k,init='nndsvdar',random_state=11,max_iter=1000)
        W=model.fit_transform(X);W=W/np.maximum(W.sum(axis=1,keepdims=True),1e-20)
        topics={'status':'exploratory_fit','k':k,'selection':'At most three displayed factors with at least five eligible units; not an optimal or validated doctrine count.',
                'iterations':int(model.n_iter_),'max_iter':model.max_iter,'converged_before_iteration_limit':bool(model.n_iter_<model.max_iter),
                'components':[{'id':i+1,'terms':[str(vec.get_feature_names_out()[j]) for j in row.argsort()[-10:][::-1]]} for i,row in enumerate(model.components_)],
                'weights':[{'source_id':d['summary']['source_id'],'weights':W[i].tolist()} for i,d in enumerate(selected)]}
        seeds=[];labels=[]
        for seed in (11,23,47):
            y=KMeans(n_clusters=k,n_init=10,random_state=seed).fit_predict(X);labels.append(y)
            seeds.append({'seed':seed,'silhouette':float(silhouette_score(X,y,metric='cosine')) if 1<len(set(y))<len(selected) else None,
                          'medium_ARI':float(adjusted_rand_score([d['summary']['medium_id'] for d in selected],y))})
        svd=TruncatedSVD(n_components=2,random_state=11);xy=svd.fit_transform(X)
        clusters={'status':'exploratory_fit','k':k,'seeds':seeds,'silhouette':seeds[0]['silhouette'],'medium_ARI':seeds[0]['medium_ARI'],
                  'seed_pair_ARI':[{'left':(11,23,47)[i],'right':(11,23,47)[j],'ARI':float(adjusted_rand_score(labels[i],labels[j]))} for i in range(3) for j in range(i+1,3)],
                  'assignments':[{'source_id':d['summary']['source_id'],'cluster':int(labels[0][i])+1,'x':float(xy[i,0]),'y':float(xy[i,1])} for i,d in enumerate(selected)],
                  'svd_explained_variance_ratio':svd.explained_variance_ratio_.tolist(),
                  'scope':'Two-dimensional projection and seed11 clusters; source-medium ARI diagnoses confounding, not entity-class accuracy.'}
    return lexical,topics,clusters


def make_figures(output,result):
    import numpy as np
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    figures=[];docs=result['documents'];labels=[str(i+1) for i in range(len(docs))];by_id={d['source_id']:d for d in docs}
    def source_key(fig,source_ids):
        lines=['Source key (publisher attribution; speaker identity unverified):']
        for i,sid in enumerate(source_ids):
            d=by_id[sid];date=str(d['published_at'])[:10] if d.get('published_at') else 'date unknown'
            lines.extend(textwrap.wrap(f"{i+1}. {d['medium']} · {d['title']} · {date}",width=140,subsequent_indent='    '))
        extra=.16*len(lines)+.18;width,height=fig.get_size_inches();fig.set_size_inches(width,height+extra)
        fig.text(.018,.015,'\n'.join(lines),ha='left',va='bottom',fontsize=7.5,linespacing=1.25)
        return extra/(height+extra)+.025
    def save(fig,name,title,alt,source_ids=None):
        bottom=source_key(fig,source_ids) if source_ids else 0
        fig.tight_layout(rect=(0,bottom,1,1))
        for ext in ('svg','png','pdf'):
            p=output/(name+'.'+ext);fig.savefig(p,dpi=160)
            figures.append({'file':p.name,'title':title,'alt':alt,'sha256':sha(p),'bytes':p.stat().st_size})
        plt.close(fig)
    groups=result['coverage']['groups'];fig,axes=plt.subplots(1,2,figsize=(12,5))
    names=[g['label'] for g in groups];yy=np.arange(len(groups))
    axes[0].barh(yy,[g['documents'] for g in groups],color='#287767');axes[1].barh(yy,[g['words'] for g in groups],color='#af693c')
    for ax in axes:ax.set_yticks(yy,names);ax.invert_yaxis()
    axes[0].set_xlabel('Selected text editions');axes[1].set_xlabel('Whitespace words');fig.suptitle('What council material is actually analyzed')
    save(fig,'council-coverage','Council source coverage','Unequal selected text editions and words by medium and exact publisher council label; no upload-total denominator.')
    lex=result['lexical']
    if lex['status']=='fitted':
        fig=plt.figure(figsize=(12,5.5));bottom=source_key(fig,lex['source_ids'])
        grid=fig.add_gridspec(1,3,width_ratios=(1,1,.045),left=.06,right=.94,top=.87,bottom=bottom+.1,wspace=.27)
        axes=[fig.add_subplot(grid[0]),fig.add_subplot(grid[1])];cax=fig.add_subplot(grid[2])
        for ax,key,idkey,title in zip(axes,('matrix','window_300_matrix'),('source_ids','window_300_source_ids'),('Whole selected text','Centered 300-token span')):
            ids=lex[idkey]
            if not ids:ax.text(.5,.5,'Insufficient length',ha='center');ax.axis('off');continue
            im=ax.imshow(lex[key],vmin=0,vmax=1,cmap='viridis');numbers=[lex['source_ids'].index(s)+1 for s in ids]
            ax.set_xticks(range(len(ids)),numbers);ax.set_yticks(range(len(ids)),numbers);ax.set_title(title);ax.set_xlabel('Source number in model order')
        fig.colorbar(im,cax=cax,label='TF-IDF cosine');fig.suptitle('Shared vocabulary, not agreement')
        # Constrained manual layout avoids a shared colorbar entering a heatmap.
        for ext in ('svg','png','pdf'):
            p=output/('council-similarity.'+ext);fig.savefig(p,dpi=160,bbox_inches='tight');figures.append({'file':p.name,'title':'Whole-text and equal-length vocabulary comparison','alt':'Fixed zero-to-one scale; numbered sources preserve matrix order. Similarity is not identity or answer agreement.','sha256':sha(p),'bytes':p.stat().st_size})
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,max(4,len(docs)*.32)))
    themes=list(KEYWORDS);matrix=[[r['rates'][k] for k in themes] for r in result['keywords']['rows']]
    im=ax.imshow(matrix,aspect='auto',cmap='YlGnBu');ax.set_yticks(range(len(docs)),labels);ax.set_xticks(range(len(themes)),[x.replace('_',' ') for x in themes],rotation=25,ha='right');ax.set_ylabel('Source number in document order');fig.colorbar(im,ax=ax,label='Dictionary word-form hits / 1,000 tokens');ax.set_title('Explicit keyword measurement')
    save(fig,'council-keywords','Keyword rates in unmasked text','Exact declared word forms; includes negated, quoted and incidental uses, not belief prevalence.',[d['source_id'] for d in docs])
    if result['topics']['status']=='exploratory_fit':
        topics=result['topics'];weights=np.array([r['weights'] for r in topics['weights']]);fig,ax=plt.subplots(figsize=(11,max(4,len(weights)*.32)));left=np.zeros(len(weights));colors=['#287767','#b26d42','#676aa6']
        for i,c in enumerate(topics['components']):
            ax.barh(range(len(weights)),weights[:,i],left=left,color=colors[i],label=', '.join(c['terms'][:3]));left+=weights[:,i]
        ax.set_yticks(range(len(weights)),range(1,len(weights)+1));ax.invert_yaxis();ax.set_xlabel('Normalized exploratory NMF factor weight');ax.set_ylabel('Source number in model order');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=1);ax.set_title('Exploratory components')
        save(fig,'council-topics','Exploratory topic-factor profiles','Three display components; normalized factors are not probabilities or externally validated doctrines.',lex['source_ids'])
    return figures


def run(manifests,output,with_existing=True,reading_path=None,supplemental_paths=()):
    output=private_path(output,exists=False)
    if output.exists():raise ValueError('Choose a fresh immutable study output')
    output.mkdir(parents=True,mode=0o700);code=Path(__file__).read_bytes();(output/'executed-analyze.py').write_bytes(code)
    docs,bindings,exclusions=load(manifests,output)
    if not docs:raise ValueError('No observed source text')
    lexical,topics,clusters=fit(docs);groups=[]
    for key in sorted({(d['summary']['medium_id'] or '',d['summary']['council_label_exact']) for d in docs}):
        selected=[d for d in docs if (d['summary']['medium_id'] or '',d['summary']['council_label_exact'])==key]
        groups.append({'medium_id':key[0],'council_label_exact':key[1],'label':selected[0]['summary']['medium']+' · '+key[1],
                       'documents':len(selected),'words':sum(d['summary']['words'] for d in selected)})
    rates=[]
    for d in docs:
        count=collections.Counter(tokens(d['text']));n=sum(count.values());hits={k:sum(count[word] for word in words) for k,words in KEYWORDS.items()}
        rates.append({'source_id':d['summary']['source_id'],'analysis_tokens':n,'counts':hits,'rates':{k:1000*v/n if n else None for k,v in hits.items()}})
    with sqlite3.connect(output/'source-text-private.sqlite') as db:
        db.execute('CREATE TABLE documents(source_id TEXT PRIMARY KEY,medium_id TEXT,council_label TEXT,text TEXT,source_url TEXT)')
        db.executemany('INSERT INTO documents VALUES(?,?,?,?,?)',[(d['summary']['source_id'],d['summary']['medium_id'],d['summary']['council_label_exact'],d['text'],d['summary']['source_url']) for d in docs])
    result={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':sha_bytes(code),
            'runtime':{'python':sys.version.split()[0],**{p:importlib.metadata.version(p) for p in ('numpy','scikit-learn','matplotlib')},
                       'thread_limits':{k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}},
            'scope':'A separately fitted convenience sample of inspected council message texts and publisher-attributed recording contexts. Earlier studies are unchanged.',
            'input_bindings':bindings,'coverage':{'documents':len(docs),'words':sum(d['summary']['words'] for d in docs),'mediums':len({d['summary']['medium_id'] for d in docs if d['summary']['medium_id']}),
                'council_labels':len({d['summary']['council_label_exact'] for d in docs}),'groups':groups,'reused_existing_audio_text_editions':sum(d['summary']['reused_from_existing_collection'] for d in docs),'all_youtube_uploads':None,
                'source_editions_inspected':len(docs)+len(exclusions),'new_audio_asr_editions_selected':sum(d['summary']['acquisition_origin']=='new_council_pilot' for d in docs),
                'duration_policy':{'non_bashar_minimum_seconds':0,'bashar_minimum_seconds':300}},
            'acquisition_origin_rules':{'prior_audio_frame_sha256':PRIOR_AUDIO_SHA,'scope':'Reuse requires exact acquisition-receipt agreement with the pinned prior 229-publication frame. New ASR requires an explicit new-council-pilot declaration and a receipt in this private study. Unknown origin is not inferred as new.'},
            'documents':[d['summary'] for d in docs],'excluded_and_aliases':exclusions,'lexical':lexical,'topics':topics,'clusters':clusters,
            'keywords':{'dictionary':KEYWORDS,'rows':rates,'scope':'Unmasked NFKC/apostrophe-preserving word-form counts per 1,000 tokens; multiple meanings, negation and quotations are not disambiguated.'},
            'qa':{'question_punctuation_count':sum(d['text'].count('?') for d in docs),'identified_answers':0,'speaker_diarization':False,'scope':'No question or answer roles are inferred from punctuation or adjacency.'},
            'reading':reviewed_reading(reading_path,docs,bindings),
            'supplemental_readings':[supplemental_reading(path,docs) for path in supplemental_paths],
            'lexical_retrieval':existing_retrieval(output) if with_existing else {'status':'not_executed'},'limitations':LIMITATIONS,'figures':[]}
    result['figures']=make_figures(output,result)
    if Path(__file__).read_bytes()!=code:raise ValueError('Analysis source changed during execution')
    write(output/'analysis.json',result)
    allow=[{'file':'analysis.json','sha256':sha(output/'analysis.json'),'bytes':(output/'analysis.json').stat().st_size}]+result['figures']
    write(output/'output-manifest.json',{'complete':True,'public_allowlist':allow})
    print(json.dumps({'documents':len(docs),'words':result['coverage']['words'],'sha256':sha(output/'analysis.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--skip-existing-retrieval',action='store_true');p.add_argument('--reading',type=Path);p.add_argument('--supplemental-reading',type=Path,action='append',default=[])
    args=p.parse_args();run(args.manifest,args.output,not args.skip_existing_retrieval,args.reading,args.supplemental_reading)
