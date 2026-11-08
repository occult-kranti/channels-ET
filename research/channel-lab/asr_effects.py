#!/usr/bin/env python3
"""Paired recognition sensitivity in the frozen Channel Lab representation spaces."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import numpy as np
from scipy.sparse import load_npz,save_npz,vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import analyze_corpus as A
from analyze_encoder import LabEncoder
import sources as F

NEGATION={'no','not','never','nor','cannot'}
NUMBER_WORDS=set('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion trillion first second third fourth fifth sixth seventh eighth ninth tenth'.split())
DIGIT=re.compile(r'(?<!\w)[+-]?\d+(?:[,.]\d+)*(?!\w)')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def ref(path):p=Path(path);return {'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size}
def normalized(text):return unicodedata.normalize('NFKC',text).strip()
def hash_text(text):return hashlib.sha256(text.encode()).hexdigest()


def load_bound(reference):
    raw=F.check_artifact(reference)
    return json.loads(raw)


def old_body(reference, expected_sha):
    raw=F.check_artifact(reference).decode()
    text=json.loads(raw)['text'] if Path(reference['path']).suffix=='.json' else raw
    choices=[('NFKC_strip',normalized(text)),('HTML_clean_NFKC_strip',normalized(html.unescape(re.sub(r'<[^>]*>','',text))))]
    matches=[(kind,value) for kind,value in choices if hash_text(value)==expected_sha]
    if not matches:raise ValueError('Old counterpart cannot reproduce its accepted normalized body')
    return matches[0]


def cues(text):
    lexical=A.words(text);negation=sum(t in NEGATION or t.endswith("n't") for t in lexical)
    number_words=sum(t in NUMBER_WORDS for t in lexical);digit_tokens=len(DIGIT.findall(text))
    denom=len(lexical)
    return {'whitespace_words':len(text.split()),'lexical_tokens':denom,'negation_cues':negation,
            'number_word_cues':number_words,'digit_number_cues':digit_tokens,
            'negation_per_1000_lexical_tokens':1000*negation/denom if denom else None,
            'number_cues_per_1000_lexical_tokens':1000*(number_words+digit_tokens)/denom if denom else None}


def cue_change(old,new):
    a,b=cues(old),cues(new)
    return {'before':a,'after':b,'delta':{k:b[k]-a[k] if a[k] is not None and b[k] is not None else None for k in a}}


def frozen_vectorizer(features,idf):
    v=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,
        ngram_range=(1,2),sublinear_tf=True,min_df=2,max_features=24000,stop_words=A.STOP,
        vocabulary={str(term):i for i,term in enumerate(features)})
    v.idf_=np.asarray(idf)
    return v


def selected_cosines(before,after):
    result=[]
    for i in range(before.shape[0]):
        left=before.getrow(i) if hasattr(before,'getrow') else before[i:i+1]
        right=after.getrow(i) if hasattr(after,'getrow') else after[i:i+1]
        a=float(left.multiply(left).sum()) if hasattr(left,'multiply') else float(np.sum(left*left))
        b=float(right.multiply(right).sum()) if hasattr(right,'multiply') else float(np.sum(right*right))
        result.append(float(np.clip(cosine_similarity(left,right)[0,0],-1,1)) if a>1e-24 and b>1e-24 else None)
    return result


def neighbor_impact(before,replacements,indices,ids,k=5):
    """Replace all selected rows simultaneously; all other source representations stay fixed."""
    if len(set(indices))!=len(indices):raise ValueError('Repeated replacement row')
    if hasattr(before,'tocsr'):
        by={owner:i for i,owner in enumerate(indices)}
        after=vstack([replacements[by[i]] if i in by else before[i] for i in range(len(ids))],format='csr')
    else:
        after=np.asarray(before).copy();after[indices]=replacements
    old_matrix,old_available=A.matrix_for(before);new_matrix,new_available=A.matrix_for(after)
    common=np.flatnonzero(old_available&new_available).tolist()
    old_neighbors=A.neighbors(old_matrix,ids,k,common);new_neighbors=A.neighbors(new_matrix,ids,k,common)
    scores=[A.overlap(old_neighbors[i],new_neighbors[i]) if i in common else None for i in range(len(ids))]
    changed=set(indices);unchanged=[i for i in common if i not in changed]
    def pack(i):
        return {'source_id':ids[i],'jaccard':scores[i],
                'before':[{'source_id':ids[j],'cosine':float(old_matrix[i,j])} for j in old_neighbors[i]],
                'after':[{'source_id':ids[j],'cosine':float(new_matrix[i,j])} for j in new_neighbors[i]]}
    public={'k':k,'available_common_sources':len(common),'changed_sources':len(indices),
        'mean_jaccard_changed_sources':A.mean([scores[i] for i in indices if scores[i] is not None]),
        'mean_jaccard_all_sources':A.mean([x for x in scores if x is not None]),
        'mean_jaccard_unchanged_sources':A.mean([scores[i] for i in unchanged]),
        'unchanged_sources_with_changed_neighbor_set':sum(scores[i]<1 for i in unchanged),
        'rows':[pack(i) for i in indices],
        'scope':'Nine selected source representations replaced simultaneously; all other representations and the common candidate universe remain fixed. Neighbor changes are descriptive, not independent statistical trials.'}
    def padded(rows):
        values=np.full((len(rows),k),-1,dtype=np.int32)
        for i,row in enumerate(rows):values[i,:len(row)]=row
        return values
    return public,{'before_neighbors':padded(old_neighbors),'after_neighbors':padded(new_neighbors),
                   'jaccard':np.asarray([np.nan if v is None else v for v in scores])}


def execute(frame_path,analysis_path,witness_path,asr_path,model_path,output):
    start=time.monotonic();code_sha=sha(__file__);output=Path(output).resolve()
    if output.exists() or not str(output).startswith('/dev/shm/'):raise ValueError('Fresh RAM output required')
    analysis=json.loads(Path(analysis_path).read_text());frame=json.loads(Path(frame_path).read_text())
    if analysis['bindings']['frame_sha256']!=sha(frame_path):raise ValueError('Frozen model is bound to another frame')
    if sha(HERE/'analyze_corpus.py')!=analysis['bindings']['script_sha256']:raise ValueError('Frozen masking/tokenization helper implementation differs')
    docs=F.load_frame(frame_path);records=[d['record'] for d in docs];ids=[r['source_id'] for r in records]
    core=np.load(Path(witness_path)/'core-vectors.npz',allow_pickle=False);X=load_npz(Path(witness_path)/'lexical.npz');S=core['semantic']
    if core['source_ids'].tolist()!=ids or X.shape[0]!=len(ids) or S.shape!=(len(ids),384):raise ValueError('Frozen witness source order differs')
    phrases=analysis['methods']['identity_mask_phrases']
    if phrases!=sorted({p for r in records for p in r.get('mask_phrases',[]) if p and p.lower() not in ('unknown','unresolved')}):raise ValueError('Identity mask differs')
    manifest=json.loads(Path(asr_path).read_text())
    if manifest['status']!='completed_full_batch' or len(manifest['sources'])!=9:raise ValueError('Nine complete verified recognition editions required')
    receipts={r['edition_id']:r for r in [load_bound(x) for x in manifest['editions']]}
    if len(receipts)!=9:raise ValueError('Recognition editions duplicated')
    indices=[];new_texts=[];old_texts=[];pairs=[];bindings=[]
    for source in manifest['sources']:
        selected=[i for i,r in enumerate(records) if r.get('publication_id')==source['publication_id'] or source['publication_id'] in r['legacy_source_ids']]
        if len(selected)!=1:raise ValueError('Publication does not resolve uniquely')
        i=selected[0];r=records[i];receipt=receipts[source['edition_id']]
        if r['recording_id']!=source['recording_id'] or receipt['audio_artifact']['sha256']!=r['audio_sha256']:raise ValueError('Same-audio binding differs')
        n=load_bound(receipt['text_artifact']);coverage=receipt['coverage']
        if len(n['text'].split())!=n['words']:raise ValueError('New recognition word count differs')
        if receipt['status']!='completed_full_chunked_asr' or not all(coverage[k] for k in ['contiguous','starts_at_zero','ends_at_sample_count','all_encoder_exhausted']):raise ValueError('Incomplete source recognition')
        if coverage['covered_samples']!=coverage['input_samples'] or n['recording_id']!=r['recording_id']:raise ValueError('Full recognition source coverage differs')
        old_ref=source['old_text_artifact']
        candidates=[a for a in frame['alternate_editions'] if a['source_id']==r['source_id'] and a['text_artifact_sha256']==old_ref['sha256']]
        if len(candidates)!=1:raise ValueError('Old same-audio edition not in accepted alias ledger')
        alternate=candidates[0];transform,old=old_body(old_ref,alternate['body_sha256']);new=normalized(n['text'])
        same_primary=hash_text(old)==r['body_sha256']
        indices.append(i);old_texts.append(old);new_texts.append(new)
        pairs.append({'source_id':r['source_id'],'channel_id':r['channel_id'],'title':r['title'],
            'recording_id':r['recording_id'],'audio_sha256':r['audio_sha256'],'publication_date':r['publication_date'],
            'selected_edition_id':r['selected_edition_id'],'selected_body_sha256':r['body_sha256'],
            'selected_text_origin':r['text_origin'],'old_asr_edition_id':alternate['edition_id'],
            'old_asr_body_sha256':hash_text(old),'new_asr_edition_id':source['edition_id'],'new_asr_body_sha256':hash_text(new),
            'old_asr_artifact_sha256':old_ref['sha256'],'new_asr_artifact_sha256':receipt['text_artifact']['sha256'],
            'old_asr_is_selected_canonical':same_primary,
            'canonical_comparison_type':'same_audio_ASR_edition_change' if same_primary else 'publisher_written_vs_new_ASR_origin_confounded',
            'same_audio_cue_change':cue_change(old,new),'canonical_cue_change':cue_change(docs[i]['text'],new)})
        bindings.append({'source_id':r['source_id'],'old_text_artifact':old_ref,'old_transform':transform,
            'new_text_artifact':receipt['text_artifact'],'receipt_sha256':next(x['sha256'] for x in manifest['editions'] if load_bound(x)['edition_id']==source['edition_id'])})
    if len(set(indices))!=9:raise ValueError('Nine recordings must resolve to nine distinct canonical units')
    vectorizer=frozen_vectorizer(core['features'],core['idf'])
    def lexical(texts):return vectorizer.transform(' '.join(A.words(A.masked(t,phrases))) for t in texts)
    newX=lexical(new_texts);oldX=lexical(old_texts)
    reused=[j for j,p in enumerate(pairs) if p['old_asr_is_selected_canonical']]
    for j in reused:
        diff=oldX[j]-X[indices[j]]
        if diff.nnz and np.max(np.abs(diff.data))>1e-12:raise ValueError('Reconstructed frozen lexical transform differs')
    extras=[j for j in range(9) if j not in reused]
    encode_jobs=[('new:'+p['new_asr_edition_id'],A.masked(t,phrases)) for p,t in zip(pairs,new_texts)]
    encode_jobs += [('old:'+pairs[j]['old_asr_edition_id'],A.masked(old_texts[j],phrases)) for j in extras]
    encoder=LabEncoder(model_path)
    if encoder.binding['model_manifest_sha256']!=analysis['bindings']['model_manifest_sha256']:raise ValueError('Encoder weights/tokenizer revision differs')
    if sha(HERE/'analyze_encoder.py')!=analysis['bindings']['encoder_script_sha256']:raise ValueError('Encoder pooling implementation differs')
    vectors,_,encoding=encoder.encode_all(encode_jobs,output.parent/(output.name+'-encoder-cache'),batch_size=8)
    newS=vectors[:9];oldS=np.zeros((9,384))
    for j in reused:oldS[j]=S[indices[j]]
    for pos,j in enumerate(extras):oldS[j]=vectors[9+pos]
    same_lex=selected_cosines(oldX,newX);same_sem=selected_cosines(oldS,newS)
    primary_lex=selected_cosines(X[indices],newX);primary_sem=selected_cosines(S[indices],newS)
    for j,p in enumerate(pairs):
        p['same_audio_cosines']={'lexical':same_lex[j],'semantic':same_sem[j]}
        p['canonical_cosines']={'lexical':primary_lex[j],'semantic':primary_sem[j]}
    lexical_neighbors,lw=neighbor_impact(X,newX,indices,ids);semantic_neighbors,sw=neighbor_impact(S,newS,indices,ids)
    result={'schema_version':1,'status':'executed_frozen_space_ASR_sensitivity','created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'bindings':{'frame_sha256':sha(frame_path),'registry_sha256':analysis['bindings']['registry_sha256'],
            'analysis_sha256':sha(analysis_path),'asr_manifest_sha256':sha(asr_path),'model_manifest_sha256':encoder.binding['model_manifest_sha256'],
            'baseline_vectors_sha256':sha(Path(witness_path)/'core-vectors.npz'),'baseline_lexical_sha256':sha(Path(witness_path)/'lexical.npz'),
            'producer_sha256':code_sha,'encoder_script_sha256':sha(HERE/'analyze_encoder.py'),
            'mask_and_tokenization_helper_sha256':sha(HERE/'analyze_corpus.py')},
        'coverage':{'candidate_sources':len(ids),'changed_sources':9,'old_same_audio_comparisons':9,
            'canonical_written_vs_ASR_comparisons':len(extras),'canonical_ASR_vs_ASR_comparisons':len(reused),
            'encoded_new_texts':9,'encoded_old_ASR_texts_absent_from_primary':len(extras),'reused_old_baseline_vectors':len(reused),
            'full_corpus_reencoded':False,'vocabulary_or_IDF_refit':False,'canonical_frame_changed':False},
        'pairs':pairs,'neighbors':{'lexical':lexical_neighbors,'semantic':semantic_neighbors},
        'methods':{'selection':'Previously frozen nine full recordings: five retained OmNa audios plus shortest eligible official Bashar, Tracy, Multidimensional Soul and Athina recordings; not a random sample.',
            'representations':'Frozen canonical TF-IDF vocabulary/IDF and masked full-body MiniLM weights/pooling. Only nine new texts and five unmatched old ASRs encoded; four old canonical vectors reused.',
            'counterfactual':'One simultaneous replacement of the nine canonical representations; all other 484 vectors remain unchanged. This is a sensitivity calculation, not adoption of new editions.',
            'same_audio_scope':'Old and new recognition editions from the exact same retained encoded audio; decoding/window/model settings differ. This does not isolate model architecture causally.',
            'canonical_scope':'Five selected OmNa primary editions are publisher-written messages, not old ASRs; their comparison is explicitly confounded by text origin/editorial treatment.',
            'negation_cues':"Casefolded lexical no/not/never/nor/cannot or token ending n't; surface cue counts, not resolved logical negation.",
            'number_cues':'Digit sequences plus listed number/ordinal words; lexical counters, not checked factual claims. Rates use lexical-token denominator.',
            'number_word_dictionary':sorted(NUMBER_WORDS),'top_k':5,'tie_break':'Descending cosine, then stable canonical source ID'},
        'performance':{'encoded_texts':len(encode_jobs),'encoder_chunks':encoding['chunks'],
            'encoding_seconds':encoding['invocation_encoding_seconds'],'total_seconds':time.monotonic()-start,'cpu_threads':1},
        'limitations':['No listening reference, WER, human accuracy measurement or correctness ranking is available.',
            'Similarity and stable neighbors do not imply identical answers, preserved qualifiers, truth, or verified entity identities.',
            'Negation and number cue differences can reflect recognition, wording, editing, punctuation or scope; no automatic semantic judgment follows.',
            'The small purposive set and dependent neighbors do not support population-level accuracy claims or significance tests.',
            'Old evidence cards and locators remain bound to their original editions. No card, claim or interpretation is automatically transferred.'],
        'figures':[]}
    output.mkdir();witness=output/'private-witness';witness.mkdir()
    np.savez(witness/'replacement-vectors.npz',source_ids=np.asarray(ids),indices=np.asarray(indices),new_semantic=newS,old_asr_semantic=oldS,
        lexical_before_neighbors=lw['before_neighbors'],lexical_after_neighbors=lw['after_neighbors'],lexical_jaccard=lw['jaccard'],
        semantic_before_neighbors=sw['before_neighbors'],semantic_after_neighbors=sw['after_neighbors'],semantic_jaccard=sw['jaccard'])
    save_npz(witness/'new-lexical.npz',newX);save_npz(witness/'old-asr-lexical.npz',oldX)
    save(witness/'execution-private.json',{'frame_path':str(frame_path),'analysis_path':str(analysis_path),'baseline_witness':str(witness_path),
        'asr_manifest_path':str(asr_path),'bindings':bindings,'encoding':encoding,'script_sha256':code_sha})
    make_figure(result,output)
    if sha(__file__)!=code_sha:raise ValueError('Effect analysis code changed during execution')
    save(output/'asr-effects.json',result)
    from verify_asr_effects import verify
    verify(output)
    allow=[ref(output/'asr-effects.json')]+result['figures']
    if sum(x['bytes'] for x in allow)>500000:raise ValueError('Public effect output exceeds500KB')
    save(output/'output-manifest.json',{'status':'completed','public_allowlist':allow})
    print(json.dumps({'coverage':result['coverage'],'neighbors':{k:{x:v for x,v in z.items() if x!='rows'} for k,z in result['neighbors'].items()},'output':str(output)}))


def make_figure(r,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pairs=r['pairs'];fig,axes=plt.subplots(1,3,figsize=(15,6),sharey=True)
    y=np.arange(len(pairs));labels=[('OmNa: '+p['title'][:33]) if p['channel_id']=='natalie-glasson-omna' else p['channel_id'] for p in pairs]
    for ax,key,title in [(axes[0],'same_audio_cosines','Old ASR → new ASR'),(axes[1],'canonical_cosines','Canonical text → new ASR')]:
        for field,color,offset in [('lexical','#147d92',-.13),('semantic','#9b4c9f',.13)]:
            ax.scatter([p[key][field] for p in pairs],y+offset,label=field,color=color,s=33)
        ax.set_xlim(0,1.03);ax.set_title(title);ax.set_xlabel('Cosine similarity');ax.grid(axis='x',alpha=.18)
    for field,color,offset in [('lexical','#147d92',-.13),('semantic','#9b4c9f',.13)]:
        axes[2].scatter([x['jaccard'] for x in r['neighbors'][field]['rows']],y+offset,color=color,s=33)
    axes[2].set_xlim(-.03,1.03);axes[2].set_title('Canonical replacement: neighbors');axes[2].set_xlabel('Top-five Jaccard');axes[2].grid(axis='x',alpha=.18)
    axes[0].set_yticks(y,labels);axes[0].invert_yaxis();axes[0].legend(loc='lower left',fontsize=9)
    fig.suptitle('Recognition sensitivity with fixed vocabulary, IDF and encoder',fontsize=14)
    fig.text(.02,.015,'Nine purposively selected recordings. Five OmNa canonical texts are written editions: origin-confounded. Similarity is not accuracy; no evidence cards transferred.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94));path=out/'asr-edition-sensitivity.svg';fig.savefig(path,metadata={'Date':None});plt.close(fig)
    r['figures']=[ref(path)]


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['frame','analysis','witness','asr-manifest','model','output']:p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args();execute(a.frame,a.analysis,a.witness,a.asr_manifest,a.model,a.output)
