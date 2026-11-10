"""Publication-scale vector figures, with the exact same values as dashboard exports."""
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize

COLORS=['#31558c','#d56a39','#3b8977','#9b6389','#aa8a31','#5c889b','#b44f4f','#657f3d']

def short(name):
    return (name.replace(' publisher episodes','').replace(' publisher texts','')
            .replace(' guest publisher context','').replace('Bashar / Darryl Anka','Bashar')
            .replace('with ','').replace(' podcast',''))[:42]

def plot_all(data,public,records):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':10,
        'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42,
        'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,
        'savefig.facecolor':'white'})
    out=Path(public)/'figures';out.mkdir(exist_ok=True);descriptors=[]
    def finish(fig,name,title,caption):
        fig.savefig(out/(name+'.pdf'),bbox_inches='tight')
        fig.savefig(out/(name+'.svg'),bbox_inches='tight')
        fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight')
        plt.close(fig)
        descriptors.append({'file':'figures/'+name+'.svg','pdf':'figures/'+name+'.pdf',
                            'png':'figures/'+name+'.png','title':title,'caption':caption})
    profiles=sorted(data['channel_profiles'],key=lambda p:(p['documents'],p['channel_id']))
    origin_order=sorted(data['summary']['origin_strata']); origin_color={o:COLORS[i%len(COLORS)] for i,o in enumerate(origin_order)}
    fig,axes=plt.subplots(1,2,figsize=(8.2,7.1),gridspec_kw={'width_ratios':[1.7,1]})
    base=np.zeros(len(profiles)); y=np.arange(len(profiles))
    for origin in origin_order:
        v=np.array([p['origin_strata'].get(origin,0) for p in profiles]);axes[0].barh(y,v,left=base,color=origin_color[origin],label=origin.replace('_',' '));base+=v
    axes[0].set_yticks(y,[short(p['channel_name'])+(' *' if p['documents']<5 else '') for p in profiles])
    for j,p in enumerate(profiles):axes[0].text(p['documents']+2,j,str(p['documents']),va='center',fontsize=6.5)
    axes[0].set_xlim(0,max(base)*1.14);axes[0].set_xlabel('Selected source units');axes[0].set_title('A. Observed corpus concentration')
    axes[0].legend(loc='upper right',bbox_to_anchor=(1,.72),fontsize=6,frameon=True,facecolor='white',edgecolor='none')
    lengths=[[r['words'] for r in records if r['text_origin']==o] for o in sorted(data['summary']['text_origins'])]
    ol=sorted(data['summary']['text_origins'])
    origin_short={'linked_publisher_caption':'Linked captions','local_asr':'Local ASR','machine_asr':'Legacy ASR',
        'platform_auto_caption':'Platform captions','publisher_labeled_transcript_pdf':'Publisher PDF',
        'publisher_transcript':'Publisher transcript','publisher_written':'Written message','retained_local_asr':'Retained ASR'}
    axes[1].boxplot(lengths,tick_labels=[origin_short.get(x,x) for x in ol],orientation='horizontal',showfliers=False,patch_artist=True,
                    boxprops={'facecolor':'#cfdae8'},medianprops={'color':'#b64c32'})
    axes[1].set_xscale('log');axes[1].set_xlabel('Words per selected text\n(log scale)');axes[1].set_title('B. Text-length variation')
    axes[1].grid(axis='x',alpha=.2)
    fig.tight_layout(w_pad=3)
    finish(fig,'corpus-profile','Corpus concentration and text origin',
        'Counts refer to selected source/publication units, not all channel uploads. * marks contexts with fewer than five documents. Boxes show median and interquartile range, whiskers1.5×IQR; outliers hidden. Text origin is a confound, not a quality ranking.')
    ordered=sorted(data['channel_profiles'],key=lambda p:(-p['documents'],p['channel_id']))
    A=np.array([[t['weight'] for t in p['topics']] for p in ordered])
    fig,ax=plt.subplots(figsize=(8.2,6.8));im=ax.imshow(A,aspect='auto',vmin=0,vmax=1,cmap='YlGnBu')
    ax.set_yticks(range(len(ordered)),[short(p['channel_name'])+f" (n={p['documents']})" for p in ordered])
    ax.set_xticks(range(len(data['topics'])),[t['topic_id']+'\n'+'\n'.join(t['label'].split(' / ')[:2]) for t in data['topics']],rotation=35,ha='right')
    for i in range(len(ordered)):
        for j in range(A.shape[1]):
            if A[i,j]>=.2:ax.text(j,i,f'{A[i,j]:.2f}',ha='center',va='center',fontsize=6,color='white' if A[i,j]>.6 else '#152536')
    ax.set_title('Mean exploratory NMF mixture by publisher context');fig.colorbar(im,ax=ax,label='Mean normalized document weight',shrink=.7);fig.tight_layout()
    finish(fig,'topic-contexts','Exploratory topic mixtures',
        'Eight fixed NMF components, seeded random initialization11, masked full-text TF-IDF. Labels are top terms. Each selected source has equal weight within its context. Low-n rows do not support generalization; seed and balanced-fit sensitivity are exported.')
    order=data['channel_similarity']['order'];lookup={p['channel_id']:p for p in ordered}
    ix=[order.index(p['channel_id']) for p in ordered if p['documents']>=5]
    C=np.array([[float('nan') if x is None else x for x in row] for row in data['channel_similarity']['values']])
    fig,ax=plt.subplots(figsize=(7.5,6.5));m=C[np.ix_(ix,ix)];im=ax.imshow(m,vmin=0,vmax=1,cmap='magma')
    labels=[short(lookup[order[i]]['channel_name'])+f" (n={lookup[order[i]]['documents']})" for i in ix]
    ax.set_xticks(range(len(ix)),labels,rotation=55,ha='right');ax.set_yticks(range(len(ix)),labels)
    for i in range(len(ix)):
        for j in range(len(ix)):ax.text(j,i,f'{m[i,j]:.2f}',ha='center',va='center',fontsize=6,color='white' if m[i,j]<.5 else '#17232d')
    ax.set_title('Mean source-pair TF-IDF cosine: contexts with ≥5 sources');fig.colorbar(im,ax=ax,label='Cosine (0–1)',shrink=.7);fig.tight_layout()
    finish(fig,'similarity-contexts','Context similarities with dependent-pair denominators',
        'All admitted cross-context source pairs are averaged. Diagonal cells use distinct unordered within-context pairs; self pairs removed. Only contexts with at least five sources are plotted; all26contexts and pair counts remain in JSON/CSV. Similarity is not agreement.')
    rows=data['sensitivity']['rows']; names={'identity_mask':'Identity masking','centered_300_word_window':'300-word length control','balanced_idf':'Balanced-context IDF','bounded_lexical_vs_MiniLM':'Lexical vs MiniLM (300 words)'}
    fig,axes=plt.subplots(1,2,figsize=(8.2,3.7));xx=np.arange(len(rows));w=.35
    axes[0].barh(xx-w/2,[r['mean_jaccard'] for r in rows],height=w,color=COLORS[0],label='Source macro')
    axes[0].barh(xx+w/2,[r['channel_macro_jaccard'] for r in rows],height=w,color=COLORS[1],label='Context macro')
    axes[0].set_yticks(xx,[names[r['analysis']] for r in rows]);axes[0].invert_yaxis();axes[0].set_xlim(0,1);axes[0].set_xlabel('Mean top5 neighbor-set Jaccard');axes[0].legend(frameon=False,fontsize=7,loc='lower right')
    axes[0].set_title('A. Representation choices change neighbors')
    ee=data['enrichment'];kk=list(ee)
    axes[1].barh(range(len(kk)),[ee[k]['macro_group_excess'] for k in kk],color=[COLORS[i] for i in range(len(kk))])
    axes[1].set_yticks(range(len(kk)),[k.replace('_',' ') for k in kk]);axes[1].axvline(0,color='#777',lw=.7)
    axes[1].set_xlabel('Same-group neighbor fraction\n− availability baseline');axes[1].set_title('B. Descriptive group enrichment');fig.tight_layout(w_pad=1.7)
    finish(fig,'sensitivity','Length, attribution, representation and context controls',
        'All top5 comparisons use the same eligible source universe. Jaccard=intersection/union. Enrichment subtracts(count(group)−1)/(N−1), then averages within groups and equally across groups. Pairs and groups are dependent; these are descriptive controls, not causal tests.')
    pts=np.array([[d['x'],d['y']] for d in data['documents']]);index={d['source_id']:i for i,d in enumerate(data['documents'])}
    fig,ax=plt.subplots(figsize=(8.2,5));segments=[pts[[index[e['source']],index[e['target']]]] for e in data['graph']['edges']]
    ax.add_collection(LineCollection(segments,colors='#929fac',linewidths=.25,alpha=.25))
    largest={p['channel_id']:i for i,p in enumerate(ordered[:7])}
    for g,i in largest.items():
        take=[j for j,d in enumerate(data['documents']) if d['channel_id']==g]
        ax.scatter(pts[take,0],pts[take,1],s=9,alpha=.68,color=COLORS[i],label=short(lookup[g]['channel_name']))
    take=[j for j,d in enumerate(data['documents']) if d['channel_id'] not in largest]
    ax.scatter(pts[take,0],pts[take,1],s=11,alpha=.6,color='#999',label='Other observed contexts')
    ax.legend(fontsize=7,loc='center left',bbox_to_anchor=(1,0.5),frameon=False);ax.set_xlabel('Centered TF-IDF SVD coordinate1');ax.set_ylabel('Centered TF-IDF SVD coordinate2')
    ax.set_title('Mutual5-neighbor source network in a lossy 2D display');fig.tight_layout()
    finish(fig,'network','Source similarity network',
        f"{len(data['graph']['edges'])} undirected mutual5 edges, no minimum cosine threshold. Colors are observed publisher contexts, not beings or social relationships. SVD display coordinates do not preserve all cosine distances; exact edges and metrics are exported.")
    fig,axes=plt.subplots(1,2,figsize=(8.2,3.7));origins=sorted({d['text_origin'] for d in data['documents']})
    for j,o in enumerate(origins):
        ix=[i for i,d in enumerate(data['documents']) if d['text_origin']==o]
        axes[0].scatter(pts[ix,0],pts[ix,1],s=8,alpha=.6,color=COLORS[j%8],label=o.replace('_',' '))
    axes[0].legend(fontsize=5,loc='best',frameon=False);axes[0].set_title('A. Same source projection, colored by origin')
    cc=data['sensitivity']['cluster_trials']
    for seed,style in [(11,'o-'),(23,'s--'),(47,'^:')]:
        r=[x for x in cc if x['seed']==seed];axes[1].plot([x['k'] for x in r],[x['cosine_silhouette_svd50'] for x in r],style,lw=1,label=f'seed {seed}')
    axes[1].axvline(8,color='#777',lw=.8);axes[1].set_xlabel('Illustrative KMeans component count');axes[1].set_ylabel('Cosine silhouette (50D SVD)');axes[1].set_title('B. Component-count sensitivity');axes[1].legend(fontsize=7,frameon=False)
    for ax in axes:ax.grid(alpha=.15)
    fig.tight_layout()
    finish(fig,'projection','Text-origin and clustering diagnostics',
        'KMeans uses normalized50D SVD features. The display uses2D SVD. Main k=8 is an illustrative fixed choice, not a validated true doctrine count; seed and alternative-k diagnostics remain visible.')
    return descriptors
