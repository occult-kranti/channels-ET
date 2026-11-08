"""One-thread, bounded MiniLM encoding with exact input-bound RAM cache witnesses."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'knowledge-bank'))
from analyze import FrozenMiniLM


def sha(raw):return hashlib.sha256(raw).hexdigest()


class LabEncoder(FrozenMiniLM):
    def encode_all(self,records,cache_directory,batch_size=16):
        """Encode all wordpieces; length-sort batches, weighted/equal normalized means."""
        if len({i for i,_ in records})!=len(records):raise ValueError('Duplicate encoding ID')
        directory=Path(cache_directory);directory.mkdir(parents=True,exist_ok=True)
        contract={'model_manifest_sha256':self.binding['model_manifest_sha256'],
                  'chunk_wordpieces':240,'target':'full_last_hidden_state',
                  'chunk_pooling':'attention mean including CLS/SEP, then L2',
                  'document_pooling':'content-token-weighted normalized chunk means, then L2',
                  'batch_size':batch_size,'batch_order':'length descending then input ordinal',
                  'script_sha256':sha(Path(__file__).read_bytes())}
        key=sha(json.dumps({'contract':contract,'inputs':[(i,sha(t.encode())) for i,t in records]},sort_keys=True).encode())
        target=directory/(key+'.npz');meta=directory/(key+'.json');lookup=time.monotonic()
        if target.exists() and meta.exists():
            receipt=json.loads(meta.read_text());raw=target.read_bytes()
            if sha(raw)!=receipt['vectors_sha256']:raise ValueError('RAM vector cache changed')
            if receipt['cache_key']!=key or receipt['contract']!=contract:raise ValueError('RAM cache contract changed')
            v=np.load(target,allow_pickle=False)
            if v['source_ids'].tolist()!=[i for i,_ in records]:raise ValueError('RAM cache row identity changed')
            for name in ('weighted','equal'):
                a=v[name]
                if a.shape!=(len(records),384) or not np.isfinite(a).all():raise ValueError('Invalid cached document vectors')
                norms=np.linalg.norm(a,axis=1);available=np.asarray([r['chunks']>0 for r in receipt['coverage']])
                if not np.allclose(norms[available],1,atol=1e-10) or np.any(norms[~available]!=0):raise ValueError('Invalid cached vector norms')
            return v['weighted'],v['equal'],{**receipt,'reused_exact_cache':True,
                'original_encoding_seconds':receipt['seconds'],'invocation_encoding_seconds':0,
                'cache_lookup_seconds':time.monotonic()-lookup}
        jobs=[];coverage=[]
        for owner,(sid,text) in enumerate(records):
            token_ids=self.tokenizer.encode(text,add_special_tokens=False).ids
            lengths=[]
            for start in range(0,len(token_ids),240):
                part=token_ids[start:start+240];lengths.append(len(part))
                jobs.append((owner,len(jobs),start,part))
            coverage.append({'source_id':sid,'body_sha256':sha(text.encode()),'content_wordpieces':len(token_ids),
                             'chunks':len(lengths),'processed_content_wordpieces':sum(lengths),'truncated_wordpieces':0,
                             'available':bool(token_ids)})
        weighted=np.zeros((len(records),384),dtype=np.float64);equal=np.zeros_like(weighted)
        counts=np.zeros(len(records));weights=np.zeros(len(records))
        chunk_vectors=np.zeros((len(jobs),384),dtype=np.float64)
        chunk_owners=np.zeros(len(jobs),dtype=np.int32);chunk_starts=np.zeros(len(jobs),dtype=np.int32);chunk_lengths=np.zeros(len(jobs),dtype=np.int16)
        jobs.sort(key=lambda j:(-len(j[3]),j[1]));started=time.monotonic();batches=0
        for start in range(0,len(jobs),batch_size):
            rows=jobs[start:start+batch_size];width=max(len(x[3]) for x in rows)+2
            ids=np.zeros((len(rows),width),dtype=np.int64);mask=np.zeros_like(ids)
            for i,(_,_,_,tokens) in enumerate(rows):
                values=[101]+tokens+[102];ids[i,:len(values)]=values;mask[i,:len(values)]=1
            inputs={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
            hidden=self.session.run(None,{k:v for k,v in inputs.items() if k in self.input_names})[0]
            vectors=(hidden*mask[:,:,None]).sum(axis=1)/mask.sum(axis=1)[:,None]
            norms=np.linalg.norm(vectors,axis=1)
            if not np.isfinite(vectors).all() or np.any(norms<1e-12):raise ValueError('Invalid chunk embedding')
            vectors/=norms[:,None]
            for (owner,ordinal,wordpiece_start,tokens),v in zip(rows,vectors):
                weighted[owner]+=v*len(tokens);weights[owner]+=len(tokens)
                equal[owner]+=v;counts[owner]+=1
                chunk_vectors[ordinal]=v;chunk_owners[ordinal]=owner;chunk_starts[ordinal]=wordpiece_start;chunk_lengths[ordinal]=len(tokens)
            batches+=1
            if batches%50==0:print(json.dumps({'stage':'encoding','chunks_done':min(start+batch_size,len(jobs)),'chunks_total':len(jobs)}),flush=True)
        available=counts>0
        weighted[available]/=weights[available,None];equal[available]/=counts[available,None]
        for values in (weighted,equal):
            norms=np.linalg.norm(values[available],axis=1)
            if not np.isfinite(values).all() or np.any(norms<1e-12):raise ValueError('Invalid pooled document embedding')
            values[available]/=norms[:,None]
        np.savez(target,source_ids=np.asarray([i for i,_ in records]),weighted=weighted,equal=equal,
            chunk_vectors=chunk_vectors,chunk_owners=chunk_owners,chunk_starts=chunk_starts,chunk_lengths=chunk_lengths)
        elapsed=time.monotonic()-started
        receipt={'contract':contract,'coverage':coverage,'seconds':time.monotonic()-started,
                 'chunks':len(jobs),'content_wordpieces':int(weights.sum()),'vectors_sha256':sha(target.read_bytes()),
                 'vectors_file':str(target),'cache_key':key,'reused_exact_cache':False,
                 'original_encoding_seconds':elapsed,'invocation_encoding_seconds':elapsed,'cache_lookup_seconds':0}
        meta.write_text(json.dumps(receipt,indent=2)+'\n')
        return weighted,equal,receipt


def profile(model_directory):
    encoder=LabEncoder(model_directory)
    # Synthetic fixed text is a throughput fixture, never an observed corpus record.
    text=('The speaker discusses attention, uncertainty, personal responsibility and the conditions of future contact. '*240)
    ids=encoder.tokenizer.encode(text,add_special_tokens=False).ids[:240]
    reference=None;rows=[]
    for size in (8,16,32):
        started=time.monotonic();vectors=[]
        for start in range(0,32,size):
            matrix=np.tile(np.asarray([101]+ids+[102],dtype=np.int64),(size,1))
            inputs={'input_ids':matrix,'attention_mask':np.ones_like(matrix),'token_type_ids':np.zeros_like(matrix)}
            output=encoder.session.run(None,{k:v for k,v in inputs.items() if k in encoder.input_names})[0]
            vectors.extend(output.mean(axis=1))
        result=np.asarray(vectors)
        if reference is None:reference=result
        rows.append({'batch_size':size,'chunks':32,'content_wordpieces':7680,'seconds':time.monotonic()-started,
                     'maximum_hidden_mean_delta_from_batch8':float(np.max(np.abs(result-reference)))})
    return {'scope':'Synthetic same-length throughput fixture; not corpus analysis or model-quality evidence.',
            'model':encoder.binding,'trials':rows,'threads':1}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=profile(a.profile);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['trials']))
