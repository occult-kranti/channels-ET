#!/usr/bin/env python3
"""Four publication-ready diagnostics from executed continuation outputs."""
import collections,json,pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=pathlib.Path(__file__).resolve().parent;R=json.loads((HERE/'results.json').read_text());OUT=HERE/'generated/figures';OUT.mkdir(exist_ok=True)
BLUE='#2D6289';GOLD='#AD7928';INK='#26343C';GRAY='#7F8E99'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':INK,'text.color':INK,'axes.edgecolor':'#AAB2B8','pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'channels-ET-continuation','savefig.facecolor':'white'})
captions=[]
def export(fig,key,title,caption):
    for ext in ['pdf','svg','png']:
        kw={'bbox_inches':'tight'}
        if ext=='pdf':kw['metadata']={'CreationDate':None,'ModDate':None}
        if ext=='svg':kw['metadata']={'Date':None}
        if ext=='png':kw['dpi']=180
        fig.savefig(OUT/(key+'.'+ext),**kw)
    captions.append({'id':key,'title':title,'caption':caption,'paths':{e:'research/continuation/analysis/generated/figures/'+key+'.'+e for e in ['pdf','svg','png']}});plt.close(fig)

pairs=json.loads((HERE/'generated/question-neighbor-pairs.json').read_text());fig,ax=plt.subplots(figsize=(8.2,4.3))
for same,color,label in [(True,GOLD,'Same quarantine source group'),(False,BLUE,'Different quarantine source groups')]:
    pp=[p for p in pairs if p['sameQuarantineGroup']==same];ax.scatter([p['questionCosine'] for p in pp],[p['answerCosine'] for p in pp],s=30,c=color,alpha=.8,label=f'{label} (n={len(pp)})',edgecolors='white',linewidths=.4)
exact=[p for p in pairs if p['sameNormalizedQuestion']];ax.scatter([p['questionCosine'] for p in exact],[p['answerCosine'] for p in exact],s=60,facecolors='none',edgecolors=INK,linewidths=.7,label='Exact normalized question wording')
ax.set(xlim=(.38,1.025),ylim=(-.02,.8),xlabel='Question-paraphrase TF–IDF cosine',ylabel='Answer-gist TF–IDF cosine');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.20),frameon=False,fontsize=9);ax.grid(color='#EEF1F3',lw=.7);ax.set_axisbelow(True);fig.tight_layout();export(fig,'question-answer-alignment','Question and answer lexical resemblance','127 cross-upload question neighbors at cosine≥.40 among 949 digest candidates. Independent question and answer TF–IDF vocabularies; neither score measures answer agreement. Quarantine groups use conservative lexical-source links, not verified original sessions. Pair entries share candidates/uploads and are dependent; the source-derived question wording can itself be normalized by the digest generator.')

graph=R['lexicalGraph']['thresholdRows'];fig,axes=plt.subplots(1,2,figsize=(8.5,3.8));x=[r['minimumQuestionCosine'] for r in graph]
axes[0].plot(x,[r['edges'] for r in graph],'-o',color=BLUE,label='Question-neighbor edges');axes[0].plot(x,[r['linkedCandidates'] for r in graph],'-s',color=GOLD,label='Candidates in non-singleton components');axes[0].set(ylabel='Count',xlabel='Minimum question cosine',ylim=(0,195));axes[0].legend(loc='upper right',frameon=False,fontsize=8.5)
axes[1].plot(x,[r['largestComponentCandidates'] for r in graph],'-o',color=BLUE);axes[1].set(xlabel='Minimum question cosine',ylabel='Candidates in largest lexical component',ylim=(0,17));axes[1].set_yticks([0,3,6,9,12,15])
for ax in axes:ax.set_xticks(x);ax.grid(axis='y',color='#EEF1F3',lw=.7);ax.set_axisbelow(True)
fig.tight_layout();export(fig,'lexical-graph-stability','Lexical-neighbor connectivity depends on the cutoff','Graph vertices are 949 digest question candidates; edges connect different uploads meeting each lexical cosine threshold. Isolated candidates remain in the denominator. At .40, 178 candidates participate in non-singleton components and the largest contains 15 candidates; components are lexical neighborhoods, not validated semantic topics or independent source families.')

rr=R['representationNuisance']['pairRows'];fig,axes=plt.subplots(1,2,figsize=(8.5,4.1))
for same,col,mark,label in [(False,BLUE,'o','Different publishers'),(True,GOLD,'s','Same publisher')]:
    pp=[p for p in rr if p['samePublisher']==same];axes[0].scatter([p['titleCosine'] for p in pp],[p['captionCosine'] for p in pp],s=16 if not same else 30,c=col,marker=mark,alpha=.65,label=f'{label} (n={len(pp)})');axes[1].scatter([p['titleRankResidual'] for p in pp],[p['captionRankResidual'] for p in pp],s=16 if not same else 30,c=col,marker=mark,alpha=.65)
axes[0].set(xlabel='Masked title cosine',ylabel='Masked caption cosine',xlim=(-.05,.85),ylim=(-.05,.9),title=f"Raw Spearman ρ = {R['representationNuisance']['rawTitleCaptionRankCorrelation']:.3f}");axes[1].set(xlabel='Title rank residual',ylabel='Caption rank residual',title=f"Partial rank association = {R['representationNuisance']['partialRankCorrelation']:.3f}");fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,-.04),ncol=2,frameon=False,fontsize=9)
for ax in axes:ax.grid(color='#EEF1F3',lw=.7);ax.set_axisbelow(True)
fig.tight_layout();export(fig,'caption-duration-controls','Representation association after length conditioning','Identical 25 uploads from 14 publishers yield 300 dependent pairs (11 within, 289 between). Right: title/caption rank residuals after separate linear projection on ranked absolute log duration ratio, mean log duration and absolute log caption word-count ratio. Their Pearson correlation defines the reported partial rank association. This is descriptive conditioning, not causal mediation; publisher-omission partial correlations range −.026 to .207, not a confidence interval.')

groups=R['lexicalGraph']['benchmarkGuard']['groups'];sizes=collections.Counter(g['uploadCount'] for g in groups);fig,axes=plt.subplots(1,2,figsize=(8.5,3.9));xs=sorted(sizes);axes[0].bar(xs,[sizes[x] for x in xs],color=BLUE,width=.6);axes[0].set(xlabel='Uploads in conservative quarantine group',ylabel='Source groups',xticks=xs,ylim=(0,max(sizes.values())+5))
for x in xs:axes[0].text(x,sizes[x]+.8,str(sizes[x]),ha='center')
vals=[[p['answerCosine'] for p in pairs if p['sameQuarantineGroup']==v] for v in [True,False]];bp=axes[1].boxplot(vals,tick_labels=[f'Same group\nn={len(vals[0])} pairs',f'Different groups\nn={len(vals[1])} pairs'],patch_artist=True,widths=.5)
for patch,col in zip(bp['boxes'],[GOLD,BLUE]):patch.set_facecolor(col);patch.set_alpha(.8)
for line in bp['medians']:line.set_color(INK)
axes[1].set(ylabel='Answer-gist lexical cosine',ylim=(-.02,.82));axes[1].grid(axis='y',color='#EEF1F3',lw=.7);axes[1].set_axisbelow(True);fig.tight_layout();export(fig,'source-leakage-guard','Conservative source grouping changes the compared pairs','67 Q&A-bearing uploads form 55 conservative quarantine groups. Links use any exact normalized question, any question cosine≥.80, or at least three cross-upload question pairs≥.40. These are leakage guards, not established recording identities. Among 127 question-neighbor pairs, 70 are within a quarantine group and 57 cross groups. Boxplots are empirical distributions with dependent pairs, not confidence intervals or measured agreement.')

if R.get('benchmarkAudit',{}).get('status')=='PASS':
    arms=R['benchmarkAudit']['arms'];names={'lexical_retrieval':'Lexical extractive','qwen_base_closed':'Qwen base · closed','qwen_base_rag':'Qwen base · train-only RAG','qwen_lora_closed':'Qwen LoRA · closed','qwen_lora_rag':'Qwen LoRA · train-only RAG'}
    fig,axes=plt.subplots(1,2,figsize=(9.2,4.2),sharey=True,gridspec_kw={'width_ratios':[1.35,1]});ys=np.arange(len(arms));jitter=np.linspace(-.13,.13,8);diag={a['id']:a for a in R.get('modelDiagnosticsAudit',{}).get('metricSensitivity',[])}
    for y,arm in zip(ys,arms):
        scores=[x['score'] for x in arm['perQuestionTokenF1']];axes[0].scatter(scores,y+jitter,c=GRAY,s=20,alpha=.75);axes[0].scatter([arm['meanTokenF1']],[y],marker='D',c=BLUE,s=44,zorder=4)
        if arm['id'] in diag:
            a=diag[arm['id']]
            for offset,count,col,label in [(-.13,a['strictMarkerOutputs'],GOLD,'Literal underscore marker'),(.13,a['posthocRefusalPhraseOutputs'],BLUE,'Post-hoc refusal phrase')]:
                axes[1].barh(y+offset,count,color=col,height=.24,label=label if y==0 else '_nolegend_');axes[1].text(count+.06,y+offset,f'{count}/2',va='center',fontsize=8.5)
        else:
            axes[1].barh(y,arm['controlStrictMarkerOutputs'],color=GOLD,height=.45);axes[1].text(arm['controlStrictMarkerOutputs']+.07,y,f"{arm['controlStrictMarkerOutputs']}/2",va='center',fontsize=10)
    axes[0].set_yticks(ys,[names[a['id']] for a in arms]);axes[0].invert_yaxis();axes[0].set(xlim=(-.01,.48),xlabel='Token F1 to held-out AI digest gist',title='Eight held-out questions per arm');axes[1].set(xlim=(0,2.55),xticks=[0,1,2],xlabel='Control outputs matching the stated rule',title='Two unsupported control prompts');axes[1].tick_params(axis='y',left=False)
    for ax in axes:ax.grid(axis='x',color='#EEF1F3',lw=.7);ax.set_axisbelow(True)

    if diag:fig.legend(*axes[1].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,-.04),ncol=2,frameon=False,fontsize=9)
    fig.tight_layout();export(fig,'model-reconstruction-controls','Lexical reconstruction and strict control-marker compliance','Actual Qwen2.5-0.5B CPU pilot: eight held-out digest questions and two deliberately unsupported controls per arm. Left dots are individual token-F1 values, diamonds are arithmetic means; no uncertainty interval or reliable ranking is implied. Gold counts literal INSUFFICIENT_EVIDENCE; when blue bars are present, they count a broader post-hoc refusal phrase rule defined after inspecting outputs. Spaced refusals score zero under the gold rule. Neither rule is human refusal accuracy. Train-only RAG excludes held-out source groups and target answers; low overlap is sparse-source transfer, not a test of ordinary answer-present RAG quality. LoRA training used 48 examples, 12 optimizer steps and 270,336 trainable parameters; no GPU comparison was executed.')

if 'commonSupportStandardization' in R['questionAnswerAlignment']:
    support=R['questionAnswerAlignment']['commonSupportStandardization'];bins=support['bins'];fig,axes=plt.subplots(1,2,figsize=(9.3,4.1),gridspec_kw={'width_ratios':[1.1,1.25]});x=np.arange(len(bins))
    for j,b in enumerate(bins):
        if not b['commonSupport']:axes[0].axvspan(j-.48,j+.48,color='#F0F1F2',zorder=0)
    axes[0].bar(x-.17,[b['withinPairs'] for b in bins],width=.34,color=GOLD,label='Same quarantine group');axes[0].bar(x+.17,[b['crossPairs'] for b in bins],width=.34,color=BLUE,label='Different quarantine groups');axes[0].set_xticks(x,[f"{b['lowerInclusive']:.1f}–\n{min(b['upperExclusive'],1):.1f}" for b in bins]);axes[0].set(xlabel='Question-cosine bins (grey: no shared support)',ylabel='Question-neighbor pairs',ylim=(0,43))
    labels=['All neighbor pairs','Common bins, unweighted','Common bins, standardized'];within=[support['originalWithinAnswerCosine']['mean'],support['unweightedSharedSupportWithinMean'],support['standardizedWithinMean']];cross=[support['originalCrossAnswerCosine']['mean'],support['unweightedSharedSupportCrossMean'],support['standardizedCrossMean']]
    for y,w,c in zip(range(3),within,cross):
        axes[1].plot([c,w],[y,y],color='#B9C1C7',lw=1);axes[1].scatter([w],[y],color=GOLD,s=45,zorder=3);axes[1].scatter([c],[y],color=BLUE,s=45,zorder=3);axes[1].text(w+.012,y,f'{w:.3f}',va='center',fontsize=9);axes[1].text(c+.010,y,f'{c:.3f}',ha='left',va='center',fontsize=9)
    axes[1].set_yticks(range(3),labels);axes[1].invert_yaxis();axes[1].set(xlabel='Mean answer-gist TF–IDF cosine',xlim=(0,.365));axes[1].grid(axis='x',color='#EEF1F3',lw=.7);axes[1].set_axisbelow(True);fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,-.07),ncol=2,frameon=False,fontsize=9);fig.tight_layout();export(fig,'question-cosine-common-support','Prompt-similarity support and standardized lexical contrast','127 question-neighbor pairs: 70 within and 57 across quarantine groups. Only the .40–<.70 bins have both strata, retaining 93 pairs (36 within, 57 cross);34 higher-similarity within-group pairs are excluded. Standardized means apply identical pooled-bin weights .5806/.2796/.1398 to the separate group means. The remaining .2972 versus .0442 contrast is descriptive; quarantine construction, within-bin topic/length differences and pair dependence prevent a causal reuse or answer-agreement interpretation. Grey bins have no cross-stratum support; missing means are null, not zero.')

(HERE/'generated/figure-captions.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2));print(f'Exported {len(captions)} figures as PDF/SVG/PNG')
