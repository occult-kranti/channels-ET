#!/usr/bin/env python3
"""Pinned one-thread MiniLM contrast for the frozen20-message pilot."""
import argparse,datetime as dt,hashlib,importlib.util,inspect,json,re,unicodedata
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('pilot',Path(__file__).with_name('analyze_pilot.py'));P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
A=P.A
MODEL='sentence-transformers/all-MiniLM-L6-v2';REV='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
class OneThreadEncoder(A.FrozenEncoder):
    def __init__(self,model_dir,cache_dir):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np=np;self.cache=A.safe_path(cache_dir,private=True,exists=False);self.cache.mkdir(parents=True,exist_ok=True);model_dir=A.safe_path(model_dir,private=True,exists=False);self.manifest=A.read_json(model_dir/'manifest.json',private=True)
        if self.manifest.get('model')!=MODEL or self.manifest.get('revision')!=REV:raise ValueError('Pinned MiniLM model required')
        for row in self.manifest['files']:
            if Path(row['path']).is_absolute() or '..' in Path(row['path']).parts:raise ValueError('Unsafe model path')
            A.artifact({'path':str(model_dir/row['path']),**{k:row[k] for k in ('bytes','sha256')}},private=True)
        self.binding={'model_manifest_sha256':A.sha(model_dir/'manifest.json'),'encoder_constructor_sha256':hashlib.sha256(inspect.getsource(OneThreadEncoder.__init__).encode()).hexdigest(),'accepted_encode_sha256':hashlib.sha256(inspect.getsource(A.FrozenEncoder.encode).encode()).hexdigest(),'accepted_helper_sha256':A.sha(Path(A.__file__)),'chunk_content_wordpieces':240,'document_pooling':'content-token-weighted normalized chunk vectors; final L2 normalization','equal_chunk_sensitivity':True,'token_pooling':'attention-mask mean including CLS/SEP, unchanged accepted encode routine','intra_op_threads':1,'inter_op_threads':1,'batch_size':16,'onnxruntime':ort.__version__,'cache_storage_dtype':'float32'}
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1;self.session=ort.InferenceSession(str(model_dir/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider']);self.tokenizer=Tokenizer.from_file(str(model_dir/'tokenizer.json'));self.tokenizer.no_truncation();self.tokenizer.no_padding()
        if [self.tokenizer.token_to_id(t) for t in ('[PAD]','[CLS]','[SEP]')]!=[0,101,102]:raise ValueError('Unexpected tokenizer IDs')
        self.input_names={x.name for x in self.session.get_inputs()}

def mask(text,names,patterns):
    for pattern in patterns:text=re.sub(pattern,' ',text,flags=re.I)
    return re.sub(r"[A-Za-z]+(?:['’][A-Za-z]+)*",lambda m:' ' if m.group().lower() in names else m.group(),text)
def raw_window(text,count=300):
    text=unicodedata.normalize('NFKC',text).replace('’',"'");matches=list(A.TOKEN.finditer(text))
    if len(matches)<count:raise ValueError('Pilot window must cover300tokens without padding')
    first=(len(matches)-count)//2;return text[matches[first].start():matches[first+count-1].end()]
def study(pilot_dir,model,out):
    from sklearn.metrics.pairwise import cosine_similarity
    out=A.safe_path(out,private=True,exists=False)
    if out.exists():raise ValueError('Fresh run required')
    out.mkdir(parents=True,mode=0o700);code=A.sha(Path(__file__));(out/'executed-semantic-pilot.py').write_bytes(Path(__file__).read_bytes())
    pilot=A.read_json(pilot_dir/'new-message-pilot.json',private=True);proof=A.read_json(pilot_dir/'provenance-private.json',private=True);ids=pilot['source_ids'];records={x['source_id']:x for x in proof['records']};names=set(pilot['transformations']['source_name_mask_tokens']);patterns=pilot['phrase_mask_sensitivity']['patterns'];texts={}
    if len(ids)!=20 or len(set(ids))!=20 or A.sha(Path(A.__file__))!=P.J.HELPER_SHA:raise ValueError('Frozen20-message inputs/helper required')
    for d in pilot['documents']:
        r=records[d['source_id']];path=A.artifact(r['text_artifact'],private=True)
        if r['text_artifact']['sha256']!=d['text_sha256']:raise ValueError('Pilot source edition changed')
        texts[d['source_id']]=path.read_text()
    encoder=OneThreadEncoder(model,out/'cache');full=encoder.encode([(sid,mask(texts[sid],names,patterns)) for sid in ids]);window=encoder.encode([('window300:'+sid,mask(raw_window(texts[sid]),names,patterns)) for sid in ids])
    weighted=np.stack([full[sid][0] for sid in ids]);equal=np.stack([full[sid][1] for sid in ids]);win=np.stack([window['window300:'+sid][0] for sid in ids]);cos=cosine_similarity(weighted);eq=cosine_similarity(equal);wc=cosine_similarity(win);ix={sid:i for i,sid in enumerate(ids)};pairs=[]
    for p in pilot['pairs']:
        i,j=ix[p['source']],ix[p['target']];pairs.append({k:p[k] for k in ['source','target','source_medium','target_medium','source_label','target_label','same_medium','same_comparison_label','comparison_kind','comparison_level']}|{'semantic_cosine':float(cos[i,j]),'equal_chunk_cosine':float(eq[i,j]),'window_300_cosine':float(wc[i,j]),'strict_lexical_cosine':pilot['phrase_mask_sensitivity']['matrix'][i][j],'identity_equivalence':False})
    summaries=[]
    for kind in sorted(set(p['comparison_kind'] for p in pairs)):
        pp=[p for p in pairs if p['comparison_kind']==kind];summaries.append({'kind':kind,'pairs':len(pp),'full_mean':float(np.mean([p['semantic_cosine'] for p in pp])),'window_300_mean':float(np.mean([p['window_300_cosine'] for p in pp])),'equal_chunk_mean':float(np.mean([p['equal_chunk_cosine'] for p in pp])),'inferential_test':None})
    leads=[]
    for kind in ['same_label_cross_medium','other']:
        candidates=[p for p in pairs if p['comparison_kind']==kind and p['source_medium']!=p['target_medium']]
        leads.extend(sorted(candidates,key=lambda p:(-p['semantic_cosine'],p['source'],p['target']))[:3])
    A.write_json(out/'reading-leads-private.json',{'selection':'Top3documentcosines amongsame-labelcross-medium andtop3othercross-medium, purposive retrieval audit, notrepresentative agreement.','pairs':[p|{'source_text_path':records[p['source']]['text_artifact']['path'],'target_text_path':records[p['target']]['text_artifact']['path']} for p in leads]})
    coverage=[{'source_id':sid,**full[sid][2]} for sid in ids];wcoverage=[{'source_id':sid,**window['window300:'+sid][2]} for sid in ids]
    if any(x['truncated_content_wordpieces'] or x['content_wordpieces']!=x['processed_content_wordpieces'] for x in coverage+wcoverage):raise ValueError('Incomplete encoding not admitted')
    np.savez_compressed(out/'vectors-private.npz',weighted=weighted.astype('float32'),equal=equal.astype('float32'),window=win.astype('float32'))
    r={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'script_sha256':code,'pilot_analysis_sha256':A.sha(pilot_dir/'new-message-pilot.json'),'scope':'Separate pinned neural embedding contrast onthe same20publisher-message source units; no training, no new weights, no physicalentity or answer-equivalence inference.','model':encoder.manifest,'processing':encoder.binding|{'mask':'Exact council-title phrases plus complete apostrophe-aware pilot source-name tokens; function words retained. Semantic and lexical models have different token weighting.','name_tokens':sorted(names),'title_patterns':patterns},'source_ids':ids,'documents':pilot['documents'],'coverage':coverage,'window_coverage':wcoverage,'totals':{'documents':20,'full_wordpieces':sum(x['content_wordpieces'] for x in coverage),'full_chunks':sum(x['chunks'] for x in coverage),'window_wordpieces':sum(x['content_wordpieces'] for x in wcoverage),'window_chunks':sum(x['chunks'] for x in wcoverage),'truncated_wordpieces':0},'matrix':cos.tolist(),'equal_chunk_matrix':eq.tolist(),'window_300_matrix':wc.tolist(),'pairs':pairs,'pair_summary':summaries,'reading_leads':leads,'pooling_maximum_pair_change':float(np.abs(cos-eq).max()),'limitations':['Embedding cosine is model-dependent language proximity, not semantic equivalence, doctrinal agreement, source independence or truth.','Small purposive sample, dependent pairs, mixed historicaldates/editorialpractices and unequal source lengths; no p-values or probabilities of entity origin.','Broadcivilization labels remain different fromsame named personality. Thereare onlytwo named-labelcross-medium pairs inthispilot.','No thresholds are tuned to claim accuracy; high nearest-neighbor scores require reading and may share only generic spiritual rhetoric.','All240wordpiece chunks are encoded without truncation; averaging still loses discourse structure and speaker/argument distinctions.','The accepted helperencode routine is unchanged; constructor explicitly limitsONNX tooneCPUthread. Previous neural models/cachekeys remainunchanged.'],'figures':[]}
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5));x=np.arange(len(summaries))
    for i,(key,label,color) in enumerate([('full_mean','Whole text','#336f85'),('window_300_mean','300-token span','#b36950'),('equal_chunk_mean','Equal chunk pooling','#6d6a9c')]):ax.bar(x+(i-1)*.23,[s[key] for s in summaries],.23,label=label,color=color)
    ax.set_xticks(x,[s['kind'].replace('_',' ')+'\n'+str(s['pairs'])+' dependent pairs' for s in summaries]);ax.set_ylim(0,1);ax.set_ylabel('Mean pinned MiniLM cosine');ax.set_title('Neural language proximity across source labels');ax.legend();ax.spines[['top','right']].set_visible(False);fig.tight_layout()
    for ext in ['png','svg','pdf']:
        p=out/('semantic-pilot-contrast.'+ext);fig.savefig(p,dpi=160);r['figures'].append({'file':p.name,'sha256':A.sha(p),'bytes':p.stat().st_size,'title':'Neural contrast with length and pooling controls','alt':'Same20messages, full coverage, no inference of shared entities; wholetext,300token and equalchunk means acrossdependent pair categories.'})
    plt.close(fig);A.write_json(out/'provenance-private.json',{'pilot_dir':str(pilot_dir),'pilot_analysis_sha256':r['pilot_analysis_sha256'],'input_records':list(records.values()),'model_directory':str(model),'model_manifest_sha256':encoder.binding['model_manifest_sha256'],'vectors_sha256':A.sha(out/'vectors-private.npz')})
    if A.sha(Path(__file__))!=code:raise ValueError('Code changed during inference')
    A.write_json(out/'semantic-pilot.json',r);A.write_json(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'semantic-pilot.json','sha256':A.sha(out/'semantic-pilot.json'),'bytes':(out/'semantic-pilot.json').stat().st_size}]+r['figures']});print(json.dumps({'totals':r['totals'],'pair_summary':summaries,'sha256':A.sha(out/'semantic-pilot.json')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();study(a.pilot,a.model,a.output)
