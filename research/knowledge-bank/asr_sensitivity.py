#!/usr/bin/env python3
"""Paired ASR-edition sensitivity with a frozen lexical vocabulary and neural model."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS,TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from analyze import FrozenMiniLM,mask_text,tokens,nearest,jaccard
from knowledge_sources import load_frame

BASELINE_SHA='e1407aa84f8eb33375f15647a5635daae0e75b55c365e7771e3ab0b728e818df'
FRAME_SHA='95131882eaed23b9429d3beb6cdffcda3fa62b32569d36412cd013c206008aae'
WORD=re.compile(r"\w+(?:['’]\w+)*",re.UNICODE)
PRIVATE=Path('/workspace/channels-et-private/knowledge-bank-2026-11')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def check(ref):
    p=Path(ref['path']);raw=p.read_bytes()
    if sha(raw)!=ref['sha256'] or ('bytes' in ref and len(raw)!=ref['bytes']):raise ValueError('Changed source artifact')
    return raw


def edit_distance(left,right):
    """Exact unit-cost token Levenshtein using bit-vector dynamic programming."""
    if len(left)>len(right):left,right=right,left
    m=len(left)
    if not m:return len(right)
    equality={}
    for i,t in enumerate(left):equality[t]=equality.get(t,0)|(1<<i)
    mask=(1<<m)-1;top=1<<(m-1);positive=mask;negative=0;distance=m
    for token in right:
        eq=equality.get(token,0);x=eq|negative
        diagonal=(((eq&positive)+positive)^positive)|eq|negative
        hp=negative|~(diagonal|positive);hn=positive&diagonal
        if hp&top:distance+=1
        if hn&top:distance-=1
        hp=(hp<<1)|1;hn<<=1
        positive=(hn|~(diagonal|hp))&mask
        negative=(diagonal&hp)&mask
    return distance


def recognition_tokens(text):
    return [t.casefold().replace('’',"'") for t in WORD.findall(unicodedata.normalize('NFKC',text))]


def validate_new(frame_docs,manifest):
    if manifest.get('status')!='completed_full_chunked_asr':raise ValueError('Four-recording completion manifest required')
    if manifest.get('model_id')!='nvidia/parakeet-tdt-0.6b-v3' or manifest.get('model_revision')!='541d1f99c6b0c3cd0b11a95167540bb8edefd82b':
        raise ValueError('Unexpected full-manifest model binding')
    old={d['record']['source_id']:d for d in frame_docs};expected={sid for sid,d in old.items() if d['record']['document_kind']=='machine_transcript'}
    documents=manifest['documents'];actual=[d['counterpart_source_id'] for d in documents]
    if len(actual)!=4 or set(actual)!=expected:raise ValueError('Exactly the four frozen ASR counterparts are required')
    full_frame=json.loads(check(manifest['input_frame']))
    if full_frame['status']!='prepared_full_sample_coverage':raise ValueError('Missing prepared full-sample frame')
    frame_docs={r['source_id']:r for r in full_frame['documents']}
    planned_clips={r['clip_id']:r for r in full_frame['clips']}
    if len(planned_clips)!=len(full_frame['clips']):raise ValueError('Duplicate prepared audio windows')
    results=[]
    for d in documents:
        sid=d['counterpart_source_id'];source=old[sid]['record']
        if d['source_id']==sid:raise ValueError('Alternative ASR must use a distinct edition ID')
        if d['old_text_artifact']['sha256']!=source['text_artifact']['sha256']:raise ValueError('Wrong old text edition')
        check(d['old_text_artifact']);receipt=json.loads(check(d['old_asr_receipt']))
        acquisition=json.loads(check(receipt['acquisition_receipt']))
        audio=d['audio_artifact'];check(audio)
        if audio['sha256']!=acquisition['audio']['sha256']:raise ValueError('Different retained audio input')
        if d['publication_id']!=receipt['publication_id']:raise ValueError('Publication join differs')
        pcm=d['canonical_s16_pcm'];decoder=receipt['decoder']
        if pcm['sha256']!=decoder['raw_pcm_sha256'] or pcm['sample_count']!=decoder['sample_count']:
            raise ValueError('Canonical PCM differs from original inference')
        if pcm['format']!='s16le' or pcm['sample_rate']!=16000 or pcm['channels']!=1 or pcm['matches_old_decoder'] is not True:
            raise ValueError('Canonical PCM declaration invalid')
        if abs(pcm['duration_seconds']-pcm['sample_count']/16000)>1e-8:raise ValueError('Canonical PCM duration differs')
        f32=d['decoded_pcm']
        if (f32['format'],f32['sample_rate'],f32['channels'],f32['sample_count'])!=('f32le',16000,1,pcm['sample_count']):
            raise ValueError('Unexpected model input representation')
        if f32['conversion']!='int16 /32768':raise ValueError('Uncontrolled model-input conversion')
        coverage=d['coverage']
        if coverage['input_samples']!=pcm['sample_count'] or coverage['covered_samples']!=pcm['sample_count']:
            raise ValueError('Not all samples covered')
        if not all(coverage[k] is True for k in ('contiguous','starts_at_zero','ends_at_sample_count','all_encoder_exhausted')):
            raise ValueError('Incomplete chunk inference')
        chunks=d['chunks'];last=0
        if len(chunks)!=coverage['chunk_count']:raise ValueError('Chunk count differs')
        for chunk in chunks:
            if chunk['start_sample']!=last or not last<chunk['end_sample']<=pcm['sample_count']:
                raise ValueError('Chunk gap or overlap')
            if chunk['end_sample']-chunk['start_sample']>480000:raise ValueError('Chunk exceeds frozen 30-second rule')
            planned=planned_clips.get(chunk['clip_id'])
            if not planned or planned['source_id']!=sid:
                raise ValueError('Audio window is absent from the preparation plan')
            if (chunk['start_sample'],chunk['end_sample'],chunk['pcm_sha256'])!=(planned['start_sample'],planned['end_sample'],planned['pcm']['sha256']):
                raise ValueError('Audio window differs from prepared PCM')
            last=chunk['end_sample']
        if last!=pcm['sample_count']:raise ValueError('Incomplete final chunk')
        new_receipt=json.loads(check(d['asr_receipt']))
        if new_receipt['status']!='completed_full_chunked_asr' or new_receipt['model_id']!='nvidia/parakeet-tdt-0.6b-v3' or new_receipt['model_revision']!='541d1f99c6b0c3cd0b11a95167540bb8edefd82b':
            raise ValueError('Unexpected new recognition model or completion state')
        for key in ('source_id','counterpart_source_id','audio_artifact','canonical_s16_pcm','decoded_pcm','coverage','text_artifact','plain_text_artifact','chunks'):
            if new_receipt[key]!=d[key]:raise ValueError('New ASR receipt differs from manifest document')
        if new_receipt['full_frame']['sha256']!=manifest['input_frame']['sha256'] or d['source_id'] not in frame_docs:
            raise ValueError('New receipt binds another preparation frame')
        for key in ('counterpart_source_id','old_text_artifact','old_asr_receipt','audio_artifact','canonical_s16_pcm','decoded_pcm'):
            if d[key]!=frame_docs[d['source_id']][key]:raise ValueError('Prepared source or input changed')
        n=json.loads(check(d['text_artifact']));text=unicodedata.normalize('NFKC',n['text']).strip()
        if n['source_id']!=d['source_id'] or len(text.split())!=n['words']:raise ValueError('New text edition count/identity differs')
        if not text or not recognition_tokens(text):raise ValueError('Empty recognized edition cannot enter representation analysis')
        if n['counterpart_source_id']!=sid or n['speaker_role']!='unknown':raise ValueError('New text counterpart or speaker attribution differs')
        turns=n['turns']
        if len(turns)!=len(chunks) or n['text']!=' '.join(t['text'].strip() for t in turns).strip():raise ValueError('Chunk/text stream differs')
        for turn,chunk in zip(turns,chunks):
            if turn['speaker_role']!='unknown':raise ValueError('Unverified ASR speaker attribution')
            if abs(turn['start']-chunk['start_sample']/16000)>1e-8 or abs(turn['end']-chunk['end_sample']/16000)>1e-8:
                raise ValueError('Chunk locator differs')
            value=json.loads(check(chunk['asr_output']))
            if value['source_id']!=sid or value['clip_id']!=chunk['clip_id'] or value['text']!=turn['text'] or turn['id']!=chunk['clip_id']:
                raise ValueError('Text differs from completed raw inference window')
            for key in ('start_sample','end_sample'):
                if value[key]!=chunk[key]:raise ValueError('Raw inference sample range differs')
            if value['pcm_sha256']!=chunk['pcm_sha256'] or value.get('encoder_exhausted') is not True or chunk['encoder_exhausted'] is not True:
                raise ValueError('Raw inference input or completion differs')
            if len(value['text'].split())!=value['words'] or value['words']!=chunk['words']:
                raise ValueError('Raw inference word count differs')
        plain=check(d['plain_text_artifact']).decode()
        if unicodedata.normalize('NFKC',plain).strip()!=text:raise ValueError('Plain text differs from normalized edition')
        results.append({'source_id':sid,'new_edition_id':d['source_id'],'text':text,
            'old_text':old[sid]['text'],'old_text_sha256':source['body_sha256'],
            'new_text_sha256':sha(text.encode()),'new_text_artifact_sha256':d['text_artifact']['sha256'],
            'old_text_artifact_sha256':source['text_artifact']['sha256'],'audio_sha256':audio['sha256'],
            'canonical_s16_pcm_sha256':pcm['sha256'],'model_f32_pcm_sha256':f32['sha256'],
            'sample_count':pcm['sample_count'],'duration_seconds':pcm['duration_seconds'],'chunk_count':len(chunks),
            'new_asr_receipt_sha256':d['asr_receipt']['sha256'],'old_asr_receipt_sha256':d['old_asr_receipt']['sha256']})
    return sorted(results,key=lambda r:r['source_id'])


def study(frame_path,baseline_path,manifest_path,knowledge_path,model_path,out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(PRIVATE):raise ValueError('Fresh private output required')
    code_sha=sha(Path(__file__).read_bytes())
    if sha(Path(frame_path).read_bytes())!=FRAME_SHA or sha(Path(baseline_path).read_bytes())!=BASELINE_SHA:
        raise ValueError('Frozen baseline frame/analysis required')
    docs,frame=load_frame(frame_path);baseline=json.loads(Path(baseline_path).read_text())
    manifest=json.loads(Path(manifest_path).read_text());new=validate_new(docs,manifest)
    ids=[d['record']['source_id'] for d in docs];positions={sid:i for i,sid in enumerate(ids)}
    if ids!=baseline['lexical']['source_ids']:raise ValueError('Baseline source order differs')
    phrases=baseline['transformations']['exact_name_phrases']
    masked=[mask_text(d['text'],phrases) for d in docs]
    vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,
        ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=12000,
        stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}))
    oldX=vec.fit_transform(' '.join(tokens(t)) for t in masked);oldL=cosine_similarity(oldX)
    if not np.allclose(oldL,baseline['lexical']['matrix'],atol=1e-10,rtol=0):raise ValueError('Baseline lexical reconstruction differs')
    replacement=[mask_text(d['text'],phrases) for d in new];newX=vec.transform([' '.join(tokens(t)) for t in replacement])
    replacement_X=oldX.tolil(copy=True)
    for row,d in enumerate(new):replacement_X[positions[d['source_id']]]=newX[row]
    replacement_X=replacement_X.tocsr();newL=cosine_similarity(replacement_X)
    encoder=FrozenMiniLM(model_path)
    if encoder.binding['model_manifest_sha256']!=baseline['semantic']['model']['model_manifest_sha256']:
        raise ValueError('Different neural model')
    encoded=encoder.encode(list(zip(ids,masked))+[('replacement:'+d['source_id'],text) for d,text in zip(new,replacement)])
    oldS=np.stack([encoded[sid][0] for sid in ids]);oldM=cosine_similarity(oldS)
    if not np.allclose(oldM,baseline['semantic']['matrix'],atol=1e-10,rtol=0):raise ValueError('Baseline neural reconstruction differs')
    newS=oldS.copy()
    for d in new:newS[positions[d['source_id']]]=encoded['replacement:'+d['source_id']][0]
    newM=cosine_similarity(newS)
    for matrix in (oldL,newL,oldM,newM):np.fill_diagonal(matrix,1.)
    lists=[nearest(m,ids,5) for m in (oldL,newL,oldM,newM)]
    changed={d['source_id'] for d in new}
    neighbor_rows=[{'source_id':sid,'text_edition_changed':sid in changed,
        'old_lexical_ids':lists[0][i],'new_lexical_ids':lists[1][i],'old_semantic_ids':lists[2][i],'new_semantic_ids':lists[3][i],
        'lexical_jaccard':jaccard(lists[0][i],lists[1][i]),'semantic_jaccard':jaccard(lists[2][i],lists[3][i])} for i,sid in enumerate(ids)]
    analyzer=vec.build_analyzer();vocab=vec.vocabulary_
    rows=[]
    for ni,d in enumerate(new):
        i=positions[d['source_id']];oldtokens=recognition_tokens(d['old_text']);newtokens=recognition_tokens(d['text'])
        distance=edit_distance(oldtokens,newtokens);counts_old=collections.Counter(oldtokens);counts_new=collections.Counter(newtokens)
        intersection=sum((counts_old&counts_new).values());union=sum((counts_old|counts_new).values())
        lexicalterms=analyzer(' '.join(tokens(replacement[ni])))
        rows.append({k:v for k,v in d.items() if k not in ('text','old_text')}|{
            'title':docs[i]['record']['title'],'medium_name':docs[i]['record']['medium'],
            'old_words':len(d['old_text'].split()),'new_words':len(d['text'].split()),
            'old_recognition_tokens':len(oldtokens),'new_recognition_tokens':len(newtokens),
            'token_edit_distance':distance,'normalized_token_disagreement':distance/max(len(oldtokens),len(newtokens)),
            'token_multiset_jaccard':intersection/union if union else None,
            'paired_lexical_cosine':float(cosine_similarity(oldX[i],newX[ni])[0,0]),
            'paired_semantic_cosine':float(np.dot(oldS[i],newS[i])/(np.linalg.norm(oldS[i])*np.linalg.norm(newS[i]))),
            'new_lexical_term_occurrences':len(lexicalterms),'new_lexical_oov_occurrences':sum(t not in vocab for t in lexicalterms),
            'lexical_neighbor_jaccard':neighbor_rows[i]['lexical_jaccard'],'semantic_neighbor_jaccard':neighbor_rows[i]['semantic_jaccard']})
    knowledge=json.loads(Path(knowledge_path).read_text());known={x['source_id']:x for x in knowledge['sources']}
    for d in docs:
        if known[d['record']['source_id']]['body_sha256']!=d['record']['body_sha256']:raise ValueError('Knowledge bank source edition differs')
    affected=[]
    for card in knowledge['cards']:
        source_ids=({card['source_id']}|{s['source_id'] for s in card['supports']})&changed
        if source_ids:affected.append({'card_id':card['card_id'],'question_id':card['question_id'],'source_ids':sorted(source_ids),
            'status':'Old edition card retained; re-read and re-annotate before applying it to a new ASR edition.'})
    old_count=sum(d['record']['words'] for d in docs);new_count=old_count-sum(r['old_words'] for r in rows)+sum(r['new_words'] for r in rows)
    result={'schema_version':1,'status':'executed_paired_edition_sensitivity','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256':code_sha,'scope':'Four alternative ASR editions of the same retained audio, evaluated in a counterfactual 25-source index. The released 25-source analysis and every existing source card remain unchanged.',
        'bindings':{'frame_sha256':FRAME_SHA,'baseline_analysis_sha256':BASELINE_SHA,
            'new_manifest_sha256':sha(Path(manifest_path).read_bytes()),'knowledge_sha256':sha(Path(knowledge_path).read_bytes()),
            'model_manifest_sha256':encoder.binding['model_manifest_sha256']},
        'model_comparison':{'previous':'Existing Whisper tiny.en / multilingual tiny editions; source-specific receipts preserved',
            'new_model_id':manifest['model_id'],'new_model_revision':manifest['model_revision'],
            'new_segmentation':'Independent contiguous nonoverlapping windows of at most 30 seconds; final partial tails retained',
            'speaker_identity_verified':False,'recognition_accuracy_verified':False},
        'coverage':{'paired_recordings':4,'baseline_source_editions':25,'unchanged_source_editions':21,
            'baseline_words':old_count,'counterfactual_words':new_count,'old_paired_words':sum(r['old_words'] for r in rows),
            'new_paired_words':sum(r['new_words'] for r in rows),'audio_seconds':sum(r['duration_seconds'] for r in rows),
            'new_input_samples':sum(r['sample_count'] for r in rows),'new_chunks':sum(r['chunk_count'] for r in rows)},
        'method':{'lexical':'Frozen baseline 25-source phrase mask, vocabulary and IDF; transform new text only, no refit on new editions.',
            'semantic':'Same pinned MiniLM model and complete 240-wordpiece pooling contract as the baseline.',
            'recognition_disagreement':'Exact unit-cost Levenshtein over NFKC/casefolded Unicode word tokens retaining numbers/apostrophes; divide by longer token sequence. Both sides are machine outputs, so this is not WER or accuracy.',
            'canonical_audio':'Exact same retained Opus and verified original 16 kHz mono s16le PCM sample hashes; Parakeet float inputs are derived from these same samples.',
            'counterfactual':'Replace only four rows for sensitivity calculations, retaining logical source IDs to compare neighbors. These matrices are not a new preferred corpus release.'},
        'records':rows,'source_ids':ids,'counterfactual_lexical_matrix':newL.tolist(),'counterfactual_semantic_matrix':newM.tolist(),
        'neighbors':{'k':5,'rows':neighbor_rows},
        'summary':{'mean_paired_lexical_cosine':float(np.mean([r['paired_lexical_cosine'] for r in rows])),
            'mean_paired_semantic_cosine':float(np.mean([r['paired_semantic_cosine'] for r in rows])),
            'mean_all_source_lexical_neighbor_jaccard':float(np.mean([r['lexical_jaccard'] for r in neighbor_rows])),
            'mean_all_source_semantic_neighbor_jaccard':float(np.mean([r['semantic_jaccard'] for r in neighbor_rows])),
            'max_lexical_pair_change':float(np.abs(oldL-newL).max()),'max_semantic_pair_change':float(np.abs(oldM-newM).max())},
        'card_reannotation':{'affected_cards':len(affected),'records':affected,'cards_rewritten':0,
            'scope':'Existing annotations remain bound to their unchanged old edition evidence. New wording and locators need independent reading before a new edition can inherit any card.'},
        'limitations':['This changes the recognition pipeline, not just model weights: old Whisper VAD/context versus independent 30-second Parakeet windows, different decoding and punctuation behavior.',
            'Same input samples do not make either machine transcript ground truth. More words or higher cosine do not prove higher accuracy.',
            'Chunk boundaries can lose context or split speech; complete sample coverage does not establish complete or accurate recognized words.',
            'Four purposely selected Council recordings do not represent all retained media, languages, channels or speaker styles.',
            'The frozen lexical vocabulary treats new terms as out of vocabulary; scores measure a controlled representation change, not an improved topic model.',
            'Existing question and claim cards are not automatically transferred to the new text. No agreement or contradiction label is changed by cosine.'],
        'figures':[]}
    out.mkdir(parents=True,mode=0o700);(out/'executed-asr-sensitivity.py').write_bytes(Path(__file__).read_bytes())
    vector_path=Path('/dev/shm/channels-et-knowledge-2026-11/methods')/('asr-sensitivity-'+out.name+'-vectors.npz')
    vector_path.parent.mkdir(parents=True,exist_ok=True)
    if vector_path.exists():raise ValueError('Fresh private vector witness required')
    np.savez(vector_path,source_ids=np.asarray(ids),old_vectors=oldS,counterfactual_vectors=newS)
    write(out/'vectors-private.json',{'path':str(vector_path),'bytes':vector_path.stat().st_size,
        'sha256':sha(vector_path.read_bytes()),'old_shape':list(oldS.shape),'counterfactual_shape':list(newS.shape),
        'scope':'Executed representation arithmetic witness; not an independent neural re-encoding.'})
    figure(result,out)
    if sha(Path(__file__).read_bytes())!=code_sha:raise ValueError('Code changed during inference')
    write(out/'asr-sensitivity.json',result)
    write(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'asr-sensitivity.json','sha256':sha((out/'asr-sensitivity.json').read_bytes()),
        'bytes':(out/'asr-sensitivity.json').stat().st_size}]+result['figures']})
    print(json.dumps({'coverage':result['coverage'],'summary':result['summary'],'affected_cards':len(affected)}))
    return result


def figure(r,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import textwrap
    fig,axes=plt.subplots(1,2,figsize=(12,5));records=r['records'];x=np.arange(4)
    labels=[str(i+1)+'. '+textwrap.shorten(d['title'],width=34,placeholder='…') for i,d in enumerate(records)]
    axes[0].bar(x-.18,[d['old_words'] for d in records],.36,label='Previous ASR',color='#176d80')
    axes[0].bar(x+.18,[d['new_words'] for d in records],.36,label='New Parakeet edition',color='#ae5837')
    axes[0].set_ylabel('Recognized whitespace words');axes[0].legend(fontsize=8)
    axes[1].plot(x,[d['paired_lexical_cosine'] for d in records],'o',label='Paired TF-IDF cosine',color='#176d80')
    axes[1].plot(x,[d['paired_semantic_cosine'] for d in records],'s',label='Paired MiniLM cosine',color='#6555a5')
    axes[1].plot(x,[d['normalized_token_disagreement'] for d in records],'^',label='Normalized token disagreement',color='#ae5837')
    axes[1].set(ylim=(-.03,1.03),ylabel='Representation similarity / text disagreement');axes[1].legend(fontsize=8)
    for ax in axes:ax.set_xticks(x,labels,rotation=20,ha='right',fontsize=8)
    fig.suptitle('Four full recordings, two recognition pipelines: sensitivity, not accuracy')
    fig.text(.5,.01,'Identical canonical input samples; model, segmentation and context differ. Existing source cards remain bound to the older editions.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.95))
    for ext in ('png','svg','pdf'):
        p=out/('asr-edition-sensitivity.'+ext);fig.savefig(p,dpi=160)
        r['figures'].append({'file':p.name,'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,
            'title':'Paired ASR-edition sensitivity on four full recordings',
            'alt':'Recognized word counts, old/new representation cosines and normalized machine-text disagreement. Four same-audio pairs; neither edition is ground truth and pipeline segmentation differs.'})
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frame','baseline','manifest','knowledge','model','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();study(a.frame,a.baseline,a.manifest,a.knowledge,a.model,a.output)
