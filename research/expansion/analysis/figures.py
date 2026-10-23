#!/usr/bin/env python3
"""Publication figure exports from reviewed expansion results, with source rows."""
import argparse, json, pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only',nargs='+',help='Regenerate only the named figure IDs, retaining the complete caption manifest.')
ARGS=parser.parse_args()
HERE=pathlib.Path(__file__).resolve().parent
D=json.loads((HERE/'results.json').read_text())
OUT=HERE/'generated/figures';OUT.mkdir(parents=True,exist_ok=True)
BLUE='#2D6289';GOLD='#AD7928';GRAY='#AEB7BD';INK='#26343C'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'axes.edgecolor':'#AAB2B8','axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':INK,'text.color':INK,'xtick.color':INK,'ytick.color':INK,'savefig.facecolor':'white','figure.facecolor':'white','pdf.fonttype':42,'svg.fonttype':'none'})
captions=[]
def export(fig,name,title,caption):
    if ARGS.only is None or name in ARGS.only:
        fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
        fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
        fig.savefig(OUT/(name+'.png'),bbox_inches='tight',dpi=180)
    captions.append({'id':name,'title':title,'caption':caption,'paths':{ext:'research/expansion/analysis/generated/figures/'+name+'.'+ext for ext in ['pdf','svg','png']}})
    plt.close(fig)

# Missingness: all bars share the upload denominator rather than changing cohorts.
rows=D['coverage']['missingness'];fig,ax=plt.subplots(figsize=(8.5,3.5));y=np.arange(len(rows));av=np.array([r['available'] for r in rows]);na=np.array([r['unavailable'] for r in rows]);ax.barh(y,av,color=BLUE,label='Available in retained evidence');ax.barh(y,na,left=av,color='#E4E8EB',label='Unavailable / outside eligible pilot');ax.set_yticks(y,[r['measure'] for r in rows]);ax.invert_yaxis();ax.set_xlim(0,925);ax.set_xlabel('Indexed uploads (same denominator: 925)');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=2,frameon=False,fontsize=9)
for i,r in enumerate(rows):ax.text(r['available']+7 if r['available']<850 else r['available']-8,i,str(r['available']),va='center',ha='left' if r['available']<850 else 'right',color=INK if r['available']<850 else 'white',fontweight='bold')
fig.tight_layout();export(fig,'coverage','Retained evidence coverage','Counts share the 925-upload index denominator. English caption pilot coverage is a selected analysis subset, not an estimated availability rate. Known duration means positive duration; date means exact indexed date.')

# Concentration curve over ranked publishing groups; not a platform census.
ranks=D['publisherRanks'];fig,ax=plt.subplots(figsize=(8.3,3.8));ax.plot([0]+[r['rank'] for r in ranks],[0]+[r['cumulativeUploadShare'] for r in ranks],color=BLUE,lw=2);ax.plot([0,len(ranks)],[0,1],color=GRAY,ls='--',lw=1,label='Equal account representation');ax.scatter([10,20],[ranks[9]['cumulativeUploadShare'],ranks[19]['cumulativeUploadShare']],color=GOLD,zorder=5)
for k in [10,20]:ax.annotate(f"Top {k}: {ranks[k-1]['cumulativeUploadShare']:.1%}",(k,ranks[k-1]['cumulativeUploadShare']),xytext=(k+8,ranks[k-1]['cumulativeUploadShare']-.04),fontsize=10)
ax.set(xlim=(0,len(ranks)),ylim=(0,1.02),xlabel='Publishing-account groups, ordered by indexed upload count',ylabel='Cumulative share of attributed uploads');ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(loc='lower right',frameon=False);fig.tight_layout();export(fig,'concentration','Concentration of indexed uploads','886 attributed uploads across 180 nonempty publishing-account groups; 39 unresolved uploads are excluded from this account concentration denominator and retained elsewhere. Empty account routes are excluded. This is index composition, not YouTube-wide concentration.')

# Direct median/IQR display avoids suggesting a normal distribution or population CI.
s=D['captionSelection']; keys=['captionPilotKnownDuration','otherUploadsInPilotAccountsKnownDuration','otherIndexedKnownDuration']; labels=['English caption pilot','Other uploads in pilot accounts','All other indexed uploads'];fig,ax=plt.subplots(figsize=(8.3,3.4))
for i,(key,label) in enumerate(zip(keys,labels)):
    r=s[key];col=GOLD if i==0 else BLUE;ax.plot([r['q1'],r['q3']],[i,i],lw=7,color=col,solid_capstyle='butt');ax.scatter([r['median']],[i],s=55,facecolor='white',edgecolor=INK,zorder=3);ax.text(50,i,f"median {r['median']:.1f}m; n={r['n']}",va='center',fontsize=10)
ax.set_yticks(range(3),labels);ax.invert_yaxis();ax.set(xlim=(0,79),xlabel='Upload duration, minutes (line: empirical IQR; point: median)');fig.tight_layout();export(fig,'caption-selection','Duration of the selected caption pilot','Positive-duration uploads only: caption pilot n=30, other uploads within pilot publishing accounts n=430, all other indexed uploads n=851. The two comparator sets overlap. Bars are empirical interquartile ranges, not confidence intervals. No selection mechanism or population inference is estimated.')

# Fixed band order, same color limits for every overlapping dictionary indicator.
rr=D['keywordByDuration'];topics=list(dict.fromkeys(r['topic'] for r in rr));bands=list(dict.fromkeys(r['band'] for r in rr));A=np.array([[next(r['share'] for r in rr if r['topic']==t and r['band']==b) for b in bands] for t in topics]);fig,ax=plt.subplots(figsize=(8.5,5.5));im=ax.imshow(A,cmap='Blues',vmin=0,vmax=max(.4,float(A.max())),aspect='auto');ax.set_xticks(range(len(bands)),[f"{b}\nn={next(r['eligibleTitles'] for r in rr if r['band']==b)}" for b in bands]);ax.set_yticks(range(len(topics)),topics);ax.set_xlabel('Positive-duration bands among English-likely eligible titles')
for i in range(A.shape[0]):
    for j in range(A.shape[1]):ax.text(j,i,f'{A[i,j]:.0%}',ha='center',va='center',color='white' if A[i,j]>.24 else INK)
cb=fig.colorbar(im,ax=ax,fraction=.035,pad=.04);cb.ax.yaxis.set_major_formatter(PercentFormatter(1));cb.set_label('Titles with ≥1 keyword match');fig.tight_layout();export(fig,'keyword-duration','Title keyword indicators by duration band','702 English-likely eligible titles with positive measured duration. Cells are title-level shares matching at least one transparent topic regex; categories overlap and are unvalidated. Length bands are not manually verified upload-format labels. Titles describe publishing language, not necessarily speech or answers.')

# Within/between empirical pair distributions, never pairwise confidence intervals.
pairs=[]
import csv
with (HERE/'generated/matched-embedding-pairs.csv').open() as f:pairs=list(csv.DictReader(f))
fig,axes=plt.subplots(1,2,figsize=(8.5,4.0),sharey=True)
for ax,key,label in zip(axes,['title','caption'],['Masked title vectors','Masked caption vectors']):
    data=[[float(r['cosine']) for r in pairs if r['representation']==key and r['samePublisher']==str(val)] for val in [True,False]]
    bp=ax.boxplot(data,tick_labels=[f'Same publisher\nn={len(data[0])} pairs',f'Different publishers\nn={len(data[1])} pairs'],patch_artist=True,widths=.5,showfliers=True)
    for patch,col in zip(bp['boxes'],[GOLD,BLUE]):patch.set_facecolor(col);patch.set_alpha(.8)
    for med in bp['medians']:med.set_color(INK)
    ax.set_title(label);ax.set_ylim(-.06,1.03);ax.grid(axis='y',color='#EBEEF0',lw=.7);ax.set_axisbelow(True)
axes[0].set_ylabel('Cosine similarity');fig.tight_layout();export(fig,'publisher-similarity','Publisher association in matched text representations','Identical 25 uploads from 14 publishing accounts support both panels; 11 accounts have within-account pairs and three are singletons. Boxplots show empirical medians/IQRs and whiskers at 1.5 IQR, not confidence intervals. Pair scores share uploads and are dependent. Vectors are retained MiniLM derivatives; no new model execution or speech validation.')

fig,axes=plt.subplots(1,2,figsize=(8.5,3.8),sharey=True)
for ax,k,label in zip(axes,['matchedTitle','matchedCaption'],['Masked titles','Masked captions']):
    r=D['embeddingWithinBetween'][k];ax.hist(r['permutationValues'],bins=30,color=BLUE,alpha=.85);ax.axvline(r['meanDifference'],color=GOLD,lw=2,label=f"Observed {r['meanDifference']:.3f}");ax.set_title(label);ax.set_xlabel('Mean within − mean between cosine');ax.legend(loc='upper center',frameon=True,facecolor='white',edgecolor='none',framealpha=1,fontsize=9);ax.set_xlim(min(r['permutationValues'])-.02,max(r['meanDifference'],max(r['permutationValues']))+.02)
axes[0].set_ylabel('Shuffled-label reference draws');fig.tight_layout();export(fig,'negative-control','Publisher-label negative control','2,000 fixed-seed publisher-label permutations on the same 25 vectors preserve publisher group sizes and destroy their observed associations. The reference is a descriptive diagnostic, not a population p-value, semantic validity test, or experimental effect. Cosine scales differ between title and caption representations.')

(HERE/'generated/figure-captions.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2))
print(f'Exported {len(captions) if ARGS.only is None else len([c for c in captions if c["id"] in ARGS.only])} figures in PDF/SVG/PNG')
