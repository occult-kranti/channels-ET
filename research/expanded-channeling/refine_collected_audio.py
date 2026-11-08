#!/usr/bin/env python3
"""Visual-only caption-provenance wording and dense-axis refinement."""
import argparse,hashlib,json,shutil
from analyze import A,HELPER_SHA
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def refine(src,dst):
 if dst.exists():raise ValueError('Choose new edition')
 dst.mkdir(parents=True,mode=0o700)
 for p in src.iterdir():
  if p.is_file():shutil.copy2(p,dst/p.name)
 r=json.loads((src/'collected-audio-analysis.json').read_text());r['scope']=r['scope'].replace('publisheraudio+machine-text editions','publisher audio with ASR and publisher-caption editions');r['keyword_dictionaries']=A.KEYWORDS;r['keyword_dictionary_helper_sha256']=HELPER_SHA;r['keyword_scope']='Exact dictionary word forms per1000analysis tokens; polysemy, quoted/negated wording and recognition errors remain; no validated belief prevalence.'
 for d in r['documents']:
  d['publication_date_raw']=d.get('publication_date');d['date_status']='publisher_metadata_unverified' if d.get('publication_date') else 'unknown'
  if d['publication_id']=='@tracykumbera:rss:a213ea57efabb655':d['publication_date']=None;d['date_status']='known_unix_epoch_placeholder_not_chronology'
 lex=r['lexical'];fig,axes=plt.subplots(1,2,figsize=(11,5));fig.subplots_adjust(left=.08,right=.87,bottom=.17,wspace=.4)
 for ax,key,idskey,title in zip(axes,['matrix','window_300_matrix'],['source_ids','window_300_source_ids'],['Whole selected text','Centered300-token spans']):
  values=np.array(lex[key]);ids=lex[idskey];im=ax.imshow(values,vmin=0,vmax=1,cmap='viridis');step=max(1,(len(ids)+11)//12);ticks=sorted(set(range(0,len(ids),step))|{len(ids)-1});ax.set_xticks(ticks,[i+1 for i in ticks]);ax.set_yticks(ticks,[i+1 for i in ticks]);ax.set_title(title);ax.set_xlabel('Selected text unit · numbered source table')
 cbax=fig.add_axes([.90,.2,.02,.6]);fig.colorbar(im,cax=cbax,label='TF-IDF cosine')
 for ext in ['png','svg','pdf']:
  p=dst/('collected-similarity.'+ext);fig.savefig(p,dpi=150);f=next(f for f in r['figures'] if f['file']==p.name);f.update(sha256=sha(p),bytes=p.stat().st_size,alt='Whole selected ASR/caption text and centered300token spans, fixed vocabulary and IDF; numbered units identify publisher recording contexts, not claimed entities.')
 plt.close(fig);r['visual_revision']={'prior_analysis_sha256':sha(src/'collected-audio-analysis.json'),'renderer_sha256':sha(Path(__file__)),'scope':'Caption-generation wording, exact existing keyword dictionary, explicit date-status metadata and readable heatmap tick spacing only. All source counts, topic models, clustering and similarities unchanged.'};write(dst/'collected-audio-analysis.json',r);shutil.copy2(Path(__file__),dst/'executed-refine-collected-audio.py');m=json.loads((dst/'output-manifest.json').read_text())
 for f in m['public_allowlist']:
  p=dst/f['file'];f.update(sha256=sha(p),bytes=p.stat().st_size)
 write(dst/'output-manifest.json',m);print(json.dumps({'sha256':sha(dst/'collected-audio-analysis.json')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();refine(a.source,a.output)
