#!/usr/bin/env python3
"""Post-panel sensitivity: remove complete council titles before token masking."""
import argparse,hashlib,importlib.util,json,re,shutil
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
spec=importlib.util.spec_from_file_location('pilot',Path(__file__).with_name('analyze_pilot.py'));P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
PATTERNS=[r'\b(?:the\s+)?pleiadian\s+high\s+council\s+of\s+(?:seven|7)\b',r'\b(?:the\s+)?(?:9d\s+|9th\s+dimensional\s+)?arcturian\s+council\b',r'\bthe\s+seven\s+pleiadians\b']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def revise(src,dst):
 if dst.exists():raise ValueError('New edition required')
 r=json.loads((src/'new-message-pilot.json').read_text());provenance=json.loads((src/'provenance-private.json').read_text());records={x['source_id']:x for x in provenance['records']};mask=set(r['transformations']['source_name_mask_tokens']);texts=[];removals=[]
 for d in r['documents']:
  rec=records[d['source_id']];p=P.A.artifact(rec['text_artifact'],private=True);text=p.read_text();count=0
  for pattern in PATTERNS:text,n=re.subn(pattern,' ',text,flags=re.I);count+=n
  texts.append(' '.join(t for t in P.A.tokens(text) if t not in mask and t not in P.A.FILLERS));removals.append({'source_id':d['source_id'],'removed_title_phrases':count})
 vec=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=12000,stop_words=sorted(set(ENGLISH_STOP_WORDS)-{'no','not','nor','never'}));X=vec.fit_transform(texts);cos=cosine_similarity(X);index={d['source_id']:i for i,d in enumerate(r['documents'])};summaries=[]
 for kind in sorted(set(p['comparison_kind'] for p in r['pairs'])):
  pairs=[p for p in r['pairs'] if p['comparison_kind']==kind];summaries.append({'kind':kind,'pairs':len(pairs),'original_mean_cosine':float(np.mean([p['cosine'] for p in pairs])),'phrase_mask_mean_cosine':float(np.mean([cos[index[p['source']],index[p['target']]] for p in pairs]))})
 r['phrase_mask_sensitivity']={'method':'Remove exact full council-title phrases before existing partial name-token mask; refit vocabulary/IDF on the same20documents. Models and original pair scores unchanged.','patterns':PATTERNS,'features':len(vec.get_feature_names_out()),'source_ids':[d['source_id'] for d in r['documents']],'removals':removals,'matrix':cos.tolist(),'pair_summary':summaries,'maximum_pair_cosine_change':float(np.abs(cos-np.array(r['matrix'])).max()),'scope':'Conditional preprocessing sensitivity, not validation of entity classes or independent speaker origins.'}
 r['limitations'].append('Original mask removes selected name tokens but retains some council-title/greeting signatures. Exact-title phrase-mask sensitivity is reported separately; it does not refit the displayed original topic components.')
 r['sensitivity_revision']={'prior_pilot_sha256':sha(src/'new-message-pilot.json'),'sensitivity_code_sha256':sha(Path(__file__))}
 dst.mkdir(parents=True,mode=0o700)
 for p in src.iterdir():
  if p.is_file():shutil.copy2(p,dst/p.name)
 shutil.copy2(Path(__file__),dst/'executed-pilot-sensitivity.py')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(10,5));x=np.arange(len(summaries));ax.bar(x-.17,[s['original_mean_cosine'] for s in summaries],.34,label='Partial name-token mask',color='#356e86');ax.bar(x+.17,[s['phrase_mask_mean_cosine'] for s in summaries],.34,label='Plus exact council-title phrases',color='#a65a51');ax.set_xticks(x,[s['kind'].replace('_',' ')+'\n'+str(s['pairs'])+' dependent pairs' for s in summaries]);ax.set_ylabel('Mean full-text TF-IDF cosine');ax.set_title('Does council-title masking change the pattern?');ax.legend();ax.spines[['top','right']].set_visible(False);fig.tight_layout()
 for ext in ['png','svg','pdf']:
  p=dst/('pilot-title-sensitivity.'+ext);fig.savefig(p,dpi=160);r['figures'].append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'title':'Council-title masking sensitivity','alt':'Two preprocessing fits on identical20documents; dependent same-label cross-medium pairs remain descriptive, not independent evidence.'})
 plt.close(fig);write(dst/'new-message-pilot.json',r);manifest=json.loads((dst/'output-manifest.json').read_text());manifest['public_allowlist']=[{'file':'new-message-pilot.json','sha256':sha(dst/'new-message-pilot.json'),'bytes':(dst/'new-message-pilot.json').stat().st_size}]+r['figures'];write(dst/'output-manifest.json',manifest);print(json.dumps({'sha256':sha(dst/'new-message-pilot.json'),'pair_summary':summaries,'maximum_pair_change':r['phrase_mask_sensitivity']['maximum_pair_cosine_change']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();revise(a.source,a.output)
