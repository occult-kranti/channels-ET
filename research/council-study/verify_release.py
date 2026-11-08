#!/usr/bin/env python3
"""Verify public council-study denominators, source joins, matrices and figures."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path


def fail(condition,message):
    if not condition:raise ValueError(message)


def privacy(value):
    if isinstance(value,dict):
        fail(not ({'path','text','raw_segments','password','access_token','refresh_token'} & value.keys()),'Private field in public analysis')
        for child in value.values():privacy(child)
    elif isinstance(value,list):
        for child in value:privacy(child)
    elif isinstance(value,str):
        fail(not any(x in value for x in ('/workspace/','/tmp/','/dev/shm/','ghp_','github_pat_','-----BEGIN PRIVATE KEY')),'Private location or credential marker')
    elif isinstance(value,float):fail(math.isfinite(value),'Non-finite number')


def close(left,right):return math.isclose(left,right,rel_tol=1e-8,abs_tol=1e-10)


def matrix(values,ids):
    n=len(ids);fail(len(set(ids))==n and len(values)==n,'Matrix source order differs')
    for i,row in enumerate(values):
        fail(len(row)==n,'Matrix is not square')
        for j,x in enumerate(row):
            fail(isinstance(x,(int,float)) and math.isfinite(x) and -1e-9<=x<=1+1e-8,'Cosine outside bounds')
            fail(close(x,values[j][i]),'Asymmetric similarity')
        fail(close(row[i],1.0) or close(row[i],0.0),'Non-unit/nonempty diagonal')


def validate_data(d):
    privacy(d);fail(d['schema_version']==1,'Unknown schema')
    enrichment=d.get('annotation_enrichment')
    if enrichment:
        fail(enrichment['changed_fields']==['supplemental_readings'] and enrichment['numerical_refit_performed'] is False,'Metadata enrichment scope changed')
        fail(enrichment['source_analysis_bytes']>0 and len(enrichment['source_analysis_sha256'])==64 and len(enrichment['enrichment_script_sha256'])==64,'Metadata enrichment bindings invalid')
    docs=d['documents'];by_id={x['source_id']:x for x in docs};c=d['coverage']
    fail(len(by_id)==len(docs)==c['documents'],'Document denominator differs')
    fail(sum(x['words'] for x in docs)==c['words'],'Word denominator differs')
    fail(c['mediums']==len({x['medium_id'] for x in docs if x['medium_id']}),'Medium denominator differs')
    fail(c['council_labels']==len({x['council_label_exact'] for x in docs}),'Council-label denominator differs')
    fail(c['all_youtube_uploads'] is None,'Unknown upload denominator became known')
    fail(c['duration_policy']=={'non_bashar_minimum_seconds':0,'bashar_minimum_seconds':300},'Duration policy differs')
    fail(c['reused_existing_audio_text_editions']==sum(x['reused_from_existing_collection'] for x in docs),'Reused-text denominator differs')
    if 'source_editions_inspected' in c:fail(c['source_editions_inspected']==len(docs)+len(d['excluded_and_aliases']),'Edition denominator differs')
    if 'new_audio_asr_editions_selected' in c:fail(c['new_audio_asr_editions_selected']==sum(x['acquisition_origin']=='new_council_pilot' for x in docs),'New-ASR denominator differs')
    keys=[]
    for group in c['groups']:
        key=(group['medium_id'],group['council_label_exact']);keys.append(key)
        chosen=[x for x in docs if (x['medium_id'] or '',x['council_label_exact'])==key]
        fail(len(chosen)==group['documents'] and sum(x['words'] for x in chosen)==group['words'],'Group denominator differs')
    fail(len(set(keys))==len(keys) and sum(x['documents'] for x in c['groups'])==len(docs),'Groups overlap or omit sources')
    for doc in docs:
        fail(doc['speaker_identity_verified'] is False and doc['audio_alignment_verified'] is False and doc['audio_listened'] is False,'Unsupported verification claim')
        fail(doc['identified_answers']==0,'Unsupported answer identification')
        if doc.get('acquisition_origin'):
            fail(doc['reused_from_existing_collection']==(doc['acquisition_origin']=='reused_prior_verified_frame'),'Reused acquisition origin differs')
        for key in ('text_content_sha256','text_artifact_sha256'):fail(len(doc[key])==64 and all(x in '0123456789abcdef' for x in doc[key]),'Invalid text hash')
        fail(doc['source_url'].startswith('https://'),'Non-HTTPS source URL')
    lex=d['lexical']
    if lex['status']=='fitted':
        ids=lex['source_ids'];fail(set(ids)<=set(by_id),'Unknown matrix source')
        matrix(lex['matrix'],ids);matrix(lex['unmasked_matrix'],ids)
        win=lex['window_300_source_ids'];fail(set(win)<=set(ids),'Unknown window source');matrix(lex['window_300_matrix'],win)
        fail(len(lex['pairs'])==len(ids)*(len(ids)-1)//2,'Pair denominator differs')
        seen=set()
        for p in lex['pairs']:
            i,j=ids.index(p['source']),ids.index(p['target']);fail(i<j and (i,j) not in seen,'Pair repeated/reversed');seen.add((i,j))
            fail(close(p['cosine'],lex['matrix'][i][j]) and close(p['unmasked_cosine'],lex['unmasked_matrix'][i][j]),'Pair score differs')
            a,b=by_id[p['source']],by_id[p['target']]
            same=bool(a['medium_id'] and a['medium_id']==b['medium_id']);label=a['council_label_exact'].casefold()==b['council_label_exact'].casefold()
            category='same_medium_same_label' if same and label else 'same_medium_different_label' if same else 'different_medium_same_label' if label else 'different_medium_different_label'
            fail(p['same_medium']==same and p['same_exact_label']==label and p['category']==category,'Pair category differs')
        fail({x['category'] for x in lex['pair_summaries']}=={x['category'] for x in lex['pairs']},'Pair-summary categories differ')
        for group in lex['pair_summaries']:
            pairs=[x for x in lex['pairs'] if x['category']==group['category']]
            fail(group['pairs']==len(pairs),'Category pair count differs')
            for a,b in (('mean_cosine','cosine'),('mean_unmasked_cosine','unmasked_cosine')):
                fail(close(group[a],sum(x[b] for x in pairs)/len(pairs)),'Pair mean differs')
    keywords=d['keywords'];fail({x['source_id'] for x in keywords['rows']}==set(by_id),'Keyword source set differs')
    for r in keywords['rows']:
        fail(r['analysis_tokens']==by_id[r['source_id']]['analysis_tokens'],'Keyword denominator differs')
        fail(set(r['rates'])==set(r['counts'])==set(keywords['dictionary']),'Keyword themes differ')
        for k,value in r['counts'].items():fail(isinstance(value,int) and value>=0 and close(r['rates'][k],1000*value/r['analysis_tokens']),'Keyword rate differs')
    fail(d['qa']['question_punctuation_count']==sum(x['question_punctuation_count'] for x in docs) and d['qa']['identified_answers']==0 and d['qa']['speaker_diarization'] is False,'QA scope differs')
    for name in ('topics','clusters'):
        model=d[name]
        if model['status']=='exploratory_fit':
            fail(len(lex['source_ids'])>=5,'Topic/cluster minimum not met')
            records=model['weights'] if name=='topics' else model['assignments']
            fail([x['source_id'] for x in records]==lex['source_ids'],'Model source order differs')
            if name=='topics':
                for x in records:fail(len(x['weights'])==model['k'] and all(v>=0 for v in x['weights']) and (close(sum(x['weights']),1) or close(sum(x['weights']),0)),'Invalid factor weights')
            else:
                fail(all(1<=x['cluster']<=model['k'] for x in records),'Invalid cluster')
                fail(all(-1<=x['medium_ARI']<=1 for x in model['seeds']),'Invalid source-medium ARI')
    reading=d.get('reading',{})
    if reading.get('readings'):
        used=set()
        for r in reading['readings']:
            fail(r['question_type']=='analyst_constructed_comparison_not_a_verified_spoken_question','Constructed reading mislabeled')
            for s in r['supports']:
                fail(s['source_id'] in by_id and s['text_artifact_sha256']==by_id[s['source_id']]['text_artifact_sha256'],'Reading source hash differs')
                fail(s['role']=='unknown' and s['audio_alignment_verified'] is False,'Reading speaker/alignment claim changed');used.add(s['source_id'])
        reading_matrix=reading.get('reading_matrix',{});columns={x['id'] for x in reading_matrix.get('columns',[])}
        for row in reading_matrix.get('rows',[]):
            fail(row['source_id'] in by_id and row['title']==by_id[row['source_id']]['title'] and set(row['cells'])==columns,'Reading matrix identity/columns differ')
            for cell in row['cells'].values():
                for s in cell['supports']:
                    fail(s['source_id'] in by_id and s['text_artifact_sha256']==by_id[s['source_id']]['text_artifact_sha256'],'Reading matrix source hash differs')
                    fail(s['role']=='unknown' and s['audio_alignment_verified'] is False and s['end_seconds']>=s['start_seconds']>=0,'Reading matrix locators invalid');used.add(s['source_id'])
        fail(reading['coverage']['documents_read_in_full']==len(used) and reading['coverage']['asr_words_read']==sum(by_id[x]['words'] for x in used),'Reading coverage differs')
    for r in d.get('supplemental_readings',[]):
        fail(r['source_id'] in by_id,'Unknown supplemental reading source')
        source=by_id[r['source_id']];coverage=r['coverage'];spans=coverage['spans']
        fail(r['title']==source['title'] and r['text_artifact_sha256']==source['text_artifact_sha256'] and r['source_url']==source['source_url'],'Supplemental reading edition differs')
        fail(coverage['human_annotation'] is False and coverage['audio_listened'] is False,'Supplemental reading verification claim changed')
        fail(spans and coverage['words_read']==sum(x['words'] for x in spans),'Supplemental reading denominator differs')
        previous=0
        for span in spans:
            fail(span['end_character']>span['start_character']>=previous and len(span['span_sha256'])==64,'Supplemental reading spans overlap or invalid')
            previous=span['end_character']
        if coverage['full_document_read']:fail(len(spans)==1 and spans[0]['start_character']==0 and coverage['words_read']==source['words'],'Full-reading coverage differs')
        for observation in r['observations']:
            fail(bool(observation['supports']),'Unsupported supplemental paraphrase')
            for s in observation['supports']:
                fail(s['role']=='unknown' and s['audio_alignment_verified'] is False,'Supplemental reading role/alignment claim changed')
                fail(any(span['start_character']<=s['start_character']<s['end_character']<=span['end_character'] for span in spans),'Supplemental support outside coverage')
                fail(len(s['span_sha256'])==64 and s['words']>=0,'Invalid supplemental support binding')
    retrieval=d['lexical_retrieval']
    if retrieval.get('documents_searched'):
        fail(retrieval['documents_searched']==292 and retrieval['documents_with_hits']==len(retrieval['hits']),'Accepted-corpus retrieval frame differs')
        for query in retrieval['query_counts']:
            q=query['query'];fail(query['documents']==sum(h['counts'][q]>0 for h in retrieval['hits']) and query['occurrences']==sum(h['counts'][q] for h in retrieval['hits']),'Retrieval count differs')
            fail(all(h['attribution_status']=='unverified_phrase_retrieval_only' for h in retrieval['hits']),'Mention promoted to attribution')
        reviews=retrieval.get('context_reviews',[])
        if reviews:
            hits={h['source_id']:h for h in retrieval['hits']}
            for review in reviews:
                fail(review['source_id'] in hits and review['text_artifact_sha256']==hits[review['source_id']]['text_artifact_sha256'] and review['source_url']==hits[review['source_id']]['source_url'],'Retrieval context source binding differs')
                fail(review['speaker_role']=='unknown' and review['human_annotation'] is False and review['audio_listened'] is False,'Retrieval context verification claim changed')
            rc=retrieval['context_review_coverage'];fail(rc['windows_read']==len(reviews) and rc['words_in_windows']==sum(r['context_words_read'] for r in reviews) and rc['full_documents_read_for_this_annotation']==0,'Retrieval context reading coverage differs')
    return {'documents':len(docs),'words':c['words'],'mediums':c['mediums'],'council_labels':c['council_labels']}


def verify(root):
    raw=(root/'analysis.json').read_bytes();d=json.loads(raw);counts=validate_data(d)
    names=[]
    for artifact in d['figures']:
        p=Path(artifact['file']);fail(not p.is_absolute() and p.name==str(p),'Invalid figure filename');names.append(p.name)
        full=root/'figures'/p
        if not full.exists():full=root/p
        body=full.read_bytes();fail(len(body)==artifact['bytes'] and hashlib.sha256(body).hexdigest()==artifact['sha256'],'Figure artifact changed')
    fail(len(set(names))==len(names),'Duplicate figure record')
    return {'status':'passed',**counts,'figures':len(names),'analysis_sha256':hashlib.sha256(raw).hexdigest(),
            'scope':'Public accounting, metadata joins, numerical consistency and artifact integrity; independent source reading/refit is separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--site',type=Path);g.add_argument('--public-dir',type=Path)
    args=p.parse_args();root=args.public_dir if args.public_dir else args.site/'dist/council-study';print(json.dumps(verify(root)))
