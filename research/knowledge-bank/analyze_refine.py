#!/usr/bin/env python3
"""Refine portable figure keys and explanatory prose without changing numerical results."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import textwrap


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def numeric_projection(r):
    r=copy.deepcopy(r)
    for key in ('scope','limitations','figures','visual_revision'):r.pop(key,None)
    for key in ('lexical','semantic'):r['transformations'].pop(key,None)
    for x in r['pair_summary']:x.pop('scope',None)
    for key in ('method','alignment','scope'):r['projections'].pop(key,None)
    for key in ('selection','scope'):r['term_overlay'].pop(key,None)
    r['topics'].pop('selection',None)
    for x in r['clusters'].values():
        x.pop('algorithm',None);x.pop('selection',None)
    r['synthetic_controls'].pop('scope',None)
    for x in r['hypotheses']:
        x.pop('operationalization',None);x.pop('limitation',None)
    return hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def draw_maps(r,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    groups=sorted({d['medium_id'] for d in r['documents']})
    palette=['#176d80','#ae5837','#6555a5','#438b68','#a5781d','#ae4f7a']
    colors={g:palette[i] for i,g in enumerate(groups)};names={d['medium_id']:d['medium_name'] for d in r['documents']}
    fig,axes=plt.subplots(1,2,figsize=(14,11.5))
    fig.subplots_adjust(left=.08,right=.86,bottom=.45,top=.91,wspace=.3)
    for ax,key,title in zip(axes,['lexical','semantic_aligned'],['Lexical SVD (2D)','Neural PCA (2D), display orientation aligned']):
        points={d['source_id']:d for d in r['projections'][key]}
        for g in groups:
            docs=[d for d in r['documents'] if d['medium_id']==g]
            ax.scatter([points[d['source_id']]['x'] for d in docs],[points[d['source_id']]['y'] for d in docs],s=40,color=colors[g],label=names[g])
        ax.set(title=title,xlabel='Normalized display coordinate 1',ylabel='Normalized display coordinate 2')
        ax.set_aspect('equal',adjustable='datalim');ax.margins(.12)
    axes[1].legend(fontsize=8,loc='upper left',bbox_to_anchor=(1,1))
    fig.suptitle('The same 25 source editions in lexical and neural representation spaces',fontsize=15,y=.97)
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    # Deterministic collision-avoiding label offsets; source coordinates never move.
    for ax,key in zip(axes,['lexical','semantic_aligned']):
        used=[];points={d['source_id']:d for d in r['projections'][key]}
        for i,doc in enumerate(r['documents']):
            p=points[doc['source_id']];candidate=None
            for radius in (5,11,18,27,38,52,70):
                for angle in (45,-45,135,-135,0,90,180,-90):
                    dx=radius*np.cos(np.radians(angle));dy=radius*np.sin(np.radians(angle))
                    ann=ax.annotate(str(i+1),(p['x'],p['y']),xytext=(dx,dy),textcoords='offset points',fontsize=7,
                        ha='center',va='center',bbox={'facecolor':'white','edgecolor':'none','alpha':.84,'pad':.4},
                        arrowprops={'arrowstyle':'-','color':'#8b8b8b','lw':.5} if radius>11 else None)
                    box=ann.get_window_extent(renderer).expanded(1.12,1.12)
                    if not any(box.overlaps(old) for old in used):candidate=(ann,box);break
                    ann.remove()
                if candidate:break
            if candidate:used.append(candidate[1])
    p=r['projections'];lexvar=sum(p['variance']['lexical_svd_explained']);semvar=sum(p['variance']['semantic_pca_explained'])
    notes=(f"Displayed variance: lexical {lexvar:.1%}; neural {semvar:.1%}. Neighborhood trustworthiness (k=5): "
        f"{p['trustworthiness_k5']['lexical']:.3f} and {p['trustworthiness_k5']['semantic']:.3f}, respectively.\n"
        'Procrustes rotates/reflects the neural display only. Distances are lossy and do not measure agreement or entity identity.')
    fig.text(.08,.405,notes,fontsize=9,va='top')
    for i,d in enumerate(r['documents']):
        col=i//9;row=i%9
        title=textwrap.shorten(d['title'],width=53,placeholder='…')
        label=f"{i+1:>2}. {d['medium_name']} — {title}"
        fig.text(.04+col*.325,.335-row*.034,textwrap.fill(label,width=61),fontsize=7.1,va='top',linespacing=1.12)
    fig.text(.04,.018,'Key preserves numbered edition identities; exact titles, source URLs and hashes remain in the companion analysis JSON.',fontsize=8)
    figures=[]
    for ext in ('png','svg','pdf'):
        file=out/('representation-maps.'+ext);fig.savefig(file,dpi=160,bbox_inches='tight')
        figures.append({'file':file.name,'sha256':sha(file),'bytes':file.stat().st_size,
            'title':'Lexical and neural source-context maps with portable source key',
            'alt':'Two lossy 2D maps of the same 25 editions with embedded source key and unchanged coordinates. Colors identify six medium contexts. Label offsets prevent collisions; neural display orientation is rotated/reflected only. Variance and trustworthiness are disclosed.'})
    plt.close(fig);return figures


def readable_labels(r,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    replacements=[]
    def save(fig,stem):
        old={f['file']:f for f in r['figures']}
        for ext in ('png','svg','pdf'):
            p=out/(stem+'.'+ext);fig.savefig(p,dpi=160,bbox_inches='tight')
            replacements.append({**old[p.name],'bytes':p.stat().st_size,'sha256':sha(p)})
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,5));x=np.arange(len(r['documents']));rows=r['neighbors']['rows']
    ax.plot(x,[v['jaccard'] for v in rows],'o-',label='Lexical ↔ neural',color='#176d80')
    ax.plot(x,[v['window_jaccard'] for v in rows],'s-',label='Neural whole ↔ centered 300 tokens',color='#ae5837')
    ax.plot(x,[v['name_mask_semantic_jaccard'] for v in rows],'^-',label='Neural masked ↔ unmasked',color='#6555a5')
    ax.set_xticks(x,[str(i+1) for i in x]);ax.set(ylim=(-.05,1.05),xlabel='Source edition number, companion map key / JSON source order',
        ylabel='Top-five neighbor-set Jaccard',title='Retrieval neighborhoods change with representation and text selection')
    ax.legend(fontsize=9);ax.grid(alpha=.15);save(fig,'neighbor-stability')
    t=r['term_overlay'];fig,ax=plt.subplots(figsize=(15,5));im=ax.imshow(t['matrix'],aspect='auto',cmap='viridis',vmin=0)
    ax.set_xticks(range(len(t['terms'])),t['terms'],rotation=60,ha='right');ax.set_yticks(range(len(t['groups'])),[g['label']+' (n='+str(g['documents'])+')' for g in t['groups']])
    ax.set_title('Source-context overlay of observed lexical features');fig.colorbar(im,ax=ax,label='Mean L2 document TF-IDF weight');fig.tight_layout()
    save(fig,'term-source-overlay')
    fig,axes=plt.subplots(1,2,figsize=(12,5));summary=r['pair_summary'];x=np.arange(len(summary))
    for j,(key,title) in enumerate([('lexical_cosine','TF-IDF'),('semantic_cosine','MiniLM')]):
        axes[j].bar(x-.18,[s[key] for s in summary],.36,label='Whole text',color='#176d80')
        w='window_lexical_cosine' if j==0 else 'window_semantic_cosine'
        axes[j].bar(x+.18,[s[w] for s in summary],.36,label='Centered 300 tokens',color='#ae5837')
        axes[j].set_xticks(x,[s['kind'].replace('_',' ')+'\n'+str(s['pairs'])+' pairs' for s in summary],rotation=20,ha='right',fontsize=8)
        axes[j].set_title(title);axes[j].set_ylim(0,1);axes[j].set_ylabel('Descriptive mean cosine');axes[j].legend(fontsize=8)
    fig.suptitle('Source context, printed comparison labels and length sensitivity');fig.tight_layout();save(fig,'source-label-contrast')
    return replacements


def refine(parent,out):
    parent=Path(parent);out=Path(out)
    if out.exists() or not out.resolve().is_relative_to(Path('/workspace/channels-et-private/knowledge-bank-2026-11')):
        raise ValueError('Fresh private output directory required')
    original=json.loads((parent/'analysis.json').read_text());r=copy.deepcopy(original)
    for f in r['figures']:
        path=parent/f['file']
        if sha(path)!=f['sha256'] or path.stat().st_size!=f['bytes']:raise ValueError('Parent figure changed')
    out.mkdir(parents=True,mode=0o700)
    for f in r['figures']:
        if not f['file'].startswith('representation-maps.'):shutil.copy2(parent/f['file'],out/f['file'])
    r['scope']='Separate fixed 25-edition knowledge-bank comparison; earlier corpora and weights are unchanged. Similarity describes representation-dependent language proximity, never answer agreement.'
    r['transformations']['lexical']='Unicode letter/apostrophe tokens; unigrams/bigrams; sublinear TF; smoothed IDF; L2 normalization; min_df=1; max_features=12000; English stop list retains no/not/nor/never.'
    r['transformations']['semantic']='The same complete-phrase mask, followed by the pinned model tokenizer; function words retained and every nonoverlapping 240-wordpiece chunk encoded.'
    for s in r['pair_summary']:s['scope']='Dependent descriptive pair mean. Broad civilization labels and named personalities are different comparison levels; neither authenticates a shared identity.'
    r['projections']['method']='Lexical uncentered TruncatedSVD with two components and neural centered PCA with two components, independently fitted. Coordinates are centered and scaled to RMS radius 1.'
    r['projections']['alignment']='Orthogonal Procrustes rotates or reflects the displayed neural 2D points toward the lexical 2D points. This changes display orientation only; it does not align latent meanings.'
    r['projections']['scope']='The 2D positions are lossy visualization coordinates. Consult explained variance, neighborhood trustworthiness and full-space cosines. No belief, historical or physical geometry is inferred.'
    r['term_overlay']['selection']='Union of the top six mean TF-IDF features per medium, in alphabetic medium-ID order, capped at 30. Descriptive selection, not independently tested markers.'
    r['term_overlay']['scope']='Mean L2-normalized document TF-IDF weights per source context. These lexical feature vectors are not neural word embeddings. Exact printed phrases are masked, but unlisted name variants remain; words such as arcturian and council can retain identity information.'
    r['topics']['selection']='Three fixed exploratory display factors; not an optimized or validated doctrine count.'
    for c in r['clusters'].values():
        c['algorithm']='KMeans on L2-normalized document representations, n_init=10.'
        c['selection']='Three fixed exploratory display clusters; not selected as optimal or validated doctrine categories.'
    r['synthetic_controls']['scope']='Five constructed stress-case statements, not observed channeling passages or an accuracy benchmark. A high cosine can coexist with opposite polarity or changed conditional scope.'
    descriptions=[('Inspect dependent pair means and cluster adjusted Rand indices against medium and comparison labels; there is no identified causal contrast.',
        'The six-medium frame is unequal, several labels occur in only one medium, and written/ASR formats and dates are mixed.'),
        ('Top-five neighbor-set Jaccard and the rank correlation of all 300 pairs, using fixed source IDs.',
         'Neighbor agreement is representation consistency, not answer accuracy.'),
        ('Whole text versus a centered 300-token span; masked versus unmasked names; weighted versus equal chunk pooling.',
         'Centered spans are not random or representative excerpts; length cannot be isolated causally from content.'),
        ('Five constructed statements, kept separate from the 25 observed source editions.',
         'One illustrative negation/condition stress case; no measured contradiction-detection accuracy.')]
    for h,(operationalization,limitation) in zip(r['hypotheses'],descriptions):h.update(operationalization=operationalization,limitation=limitation)
    r['limitations']=[
        'Purposive English accessible-source editions, not a representative sample of religions, all channels or authenticated beings.',
        'All 25 text editions reuse previously retained material; overlapping older frame counts cannot be added as new observations.',
        'Four ASRs have unknown utterance roles and unmeasured recognition accuracy. A full mixed interview is not pure Council speech.',
        'Written and machine-text formats, medium, date, length and shared vocabulary are confounded.',
        'Pair observations are dependent. Descriptive means and exploratory clusters do not establish significance or probabilities.',
        'Broad civilization comparisons and identical printed personality names are different source claims; neither verifies identity or independent origin.',
        'Pinned MiniLM is a lightweight reproducible baseline, not a current SOTA claim. No new weights or neural word embeddings are trained.',
        'Only complete listed name phrases are masked. Unlisted aliases, shortened names, inflections and contextual identity cues remain.',
        'Cosines, coordinates and nearest neighbors are not common answers or contradictions; source-reading questions and cards form that separate layer.',
        'The five constructed control statements are explicitly synthetic and excluded from corpus and reading denominators.']
    replacements=draw_maps(r,out)+readable_labels(r,out)
    names={x['file'] for x in replacements}
    r['figures']=[x for x in r['figures'] if x['file'] not in names]+replacements
    before=numeric_projection(original);after=numeric_projection(r)
    if before!=after:raise ValueError('Numerical/source projection changed during visual refinement')
    r['visual_revision']={'parent_analysis_sha256':sha(parent/'analysis.json'),'refiner_sha256':sha(Path(__file__)),
        'unchanged_numerical_and_source_projection_sha256':before,'scope':'Source-key/label-offset figure revision and explanatory prose only; no source, vector, score, coordinate, cluster or hypothesis-result refit.'}
    write(out/'analysis.json',r);(out/'executed-refiner.py').write_bytes(Path(__file__).read_bytes())
    write(out/'refinement-private.json',{'parent':str(parent),'parent_analysis_sha256':sha(parent/'analysis.json'),
        'numeric_projection_before':before,'numeric_projection_after':after})
    write(out/'output-manifest.json',{'complete':True,'public_allowlist':[{'file':'analysis.json','sha256':sha(out/'analysis.json'),
        'bytes':(out/'analysis.json').stat().st_size}]+r['figures']})
    print(json.dumps({'status':'refined_without_refit','analysis_sha256':sha(out/'analysis.json'),'numerical_projection_sha256':before}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();refine(a.parent,a.output)
