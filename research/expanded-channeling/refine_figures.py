#!/usr/bin/env python3
"""New visual-only edition: move the similarity colorbar outside both matrices."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def revise(src,dst):
    if dst.exists():raise ValueError('Choose new edition')
    dst.mkdir(parents=True,mode=0o700)
    for p in src.iterdir():
        if p.is_file():shutil.copy2(p,dst/p.name)
    r=json.loads((src/'analysis.json').read_text());short=['Ra','Bashar contexts','Bashar excerpts','Promotions','Greetings','Tracy captions','Magenta PDFs']
    fig,axes=plt.subplots(1,2,figsize=(13,6));fig.subplots_adjust(left=.12,right=.87,bottom=.27,top=.91,wspace=.68)
    for ax,key,title in zip(axes,['matrix','window_matrix'],['Entire retained text','Centered600-token span']):
        vals=np.array(r['similarities'][key],dtype=float);im=ax.imshow(vals,vmin=0,vmax=1,cmap='viridis');ax.set_xticks(range(7),short,rotation=55,ha='right');ax.set_yticks(range(7),short);ax.set_title(title)
        for i in range(7):
            for j in range(7):ax.text(j,i,'—' if np.isnan(vals[i,j]) else f'{vals[i,j]:.2f}',ha='center',va='center',color='white' if vals[i,j]<.5 else 'black',fontsize=8)
    cbax=fig.add_axes([.90,.30,.015,.55]);fig.colorbar(im,cax=cbax,label='Mean TF-IDF cosine')
    for ext in ['svg','png','pdf']:
        p=dst/('joint-similarity.'+ext);fig.savefig(p,dpi=160)
        row=next(x for x in r['figures'] if x['file']==p.name);row.update(sha256=sha(p),bytes=p.stat().st_size)
    plt.close(fig)
    r['visual_revision']={'prior_analysis_sha256':sha(src/'analysis.json'),'renderer_sha256':sha(Path(__file__)),'scope':'Visual-only colorbar placement fix after image inspection. All numerical models, matrices and interpretations unchanged.'};write(dst/'analysis.json',r);shutil.copy2(Path(__file__),dst/'executed-refine-figures.py')
    m=json.loads((dst/'output-manifest.json').read_text())
    for x in m['public_allowlist']:
        p=dst/x['file'];x.update(sha256=sha(p),bytes=p.stat().st_size)
    m['private_outputs']+=['executed-refine-figures.py'];write(dst/'output-manifest.json',m);print(json.dumps({'status':'complete','sha256':sha(dst/'analysis.json')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();revise(a.source,a.output)
