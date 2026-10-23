#!/usr/bin/env python3
"""Generate paper-ready tables, macros and figures from paper-results.json."""
import pathlib,json,hashlib,textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=ROOT/'research/paper/generated';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
D=json.loads((OUT/'paper-results.json').read_text())
C=D['coverage'];S=D['sensitivity'];L=D['captionLengths'];LO=D['leaveOnePublisherOut']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'axes.titlesize':10,'axes.labelsize':9.5,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'channeling-paper-v1','axes.labelcolor':'#222222','text.color':'#222222','axes.linewidth':.65,'xtick.major.width':.65,'ytick.major.width':.65})
GREEN='#315b4a';GOLD='#a36f36';GRAY='#aeb5af'
def tex(s):
 for a,b in [('\\',r'\textbackslash{}'),('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 return s

def tab(name,cols,heads,rows):
 s='\\begin{tabular}{@{}'+cols+'@{}}\n\\toprule\n'+' & '.join(heads)+r' \\'+'\n\\midrule\n'
 s+='\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n';(OUT/name).write_text(s)
macros={
 'AtlasNIndexed':C['indexedVideos'],'AtlasNDuration':C['durationKnown'],'AtlasNDurationFresh':C['durationFresh'],'AtlasNDurationInherited':C['durationInherited'],'AtlasNExactDates':C['dateKnown'],'AtlasNWatchSuccess':C['watchMetadataSuccesses'],'AtlasNAttributed':C['attributedVideos'],'AtlasNRouteGroups':C['routeGroups'],'AtlasNGroupsWithVideos':C['groupsWithVideos'],'AtlasNGroupsWithDurations':C['groupsWithDurations'],'AtlasNEnglishTitles':C['englishLikelyTitles'],'AtlasNEmbeddedTitles':C['embeddedTitles'],'AtlasNTitlePublishers':C['titleGroupsMinFive'],'AtlasNCaptionAttempted':C['captionAttempted'],'AtlasNCaptionRetrieved':C['captionAvailable'],'AtlasNEnglishCaptionTracks':C['captionEnglish'],'AtlasNCaptionPilot':C['captionPilot'],'AtlasNCaptionPublishers':C['captionPublishers'],'AtlasNCaptionComparisonPublishers':C['captionComparisonPublishers'],'AtlasNCaptionComparisonVideos':C['captionComparisonDocuments'],'AtlasNMatchedEligibleVideos':C['matchedEligibleDocuments'],'AtlasNMatchedContributingVideos':C['matchedContributingDocuments'],'AtlasNMatchedPublishers':C['matchedPublishers'],'AtlasNMatchedPairs':C['matchedPairs'],'AtlasRhoRawMasked':f"{S[0]['rho']:.3f}",'AtlasRhoDeduplicated':f"{S[1]['rho']:.3f}",'AtlasRhoTrimmed':f"{S[2]['rho']:.3f}",'AtlasRhoMatched':f"{S[3]['rho']:.3f}",'AtlasLopoMin':f"{LO['minRho']:.3f}",'AtlasLopoMax':f"{LO['maxRho']:.3f}",'AtlasCaptionWordsMin':L['min'],'AtlasCaptionWordsMax':L['max'],'AtlasCaptionWordsMedian':f"{L['median']:.1f}",'AtlasCaptionWordsTotal':f"{L['sum']:,}",'AtlasTrimNeighborChanges':D['captionTrimNearestNeighborChanges']['changed'],'AtlasWithinMedian':f"{D['withinBetween']['within']['median']:.3f}",'AtlasBetweenMedian':f"{D['withinBetween']['between']['median']:.3f}",
}
(OUT/'results.tex').write_text('% Generated from frozen published snapshot; do not hand-edit.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in macros.items())+'\n')
(OUT/'macro-index.json').write_text(json.dumps(macros,indent=2))
tab('coverage-table.tex','lr',['Measure','Count'],[
 ['Unique indexed videos',C['indexedVideos']],['Public watch metadata retrieved',C['watchMetadataSuccesses']],['Known durations (fresh / inherited)',f"{C['durationKnown']} ({C['durationFresh']} / {C['durationInherited']})"],['Exact publication dates',C['dateKnown']],['Videos attributed to account routes',C['attributedVideos']],['English-likely titles / embedded titles',f"{C['englishLikelyTitles']} / {C['embeddedTitles']}"],['Title publishers with $n\\geq5$',C['titleGroupsMinFive']],['Caption attempts / retrieved tracks',f"{C['captionAttempted']} / {C['captionAvailable']}"],['English caption pilot / publishers',f"{C['captionPilot']} / {C['captionPublishers']}"],['Caption comparison videos / publishers',f"{C['captionComparisonDocuments']} / {C['captionComparisonPublishers']}"],['Matched eligible / contributing videos',f"{C['matchedEligibleDocuments']} / {C['matchedContributingDocuments']}"],['Matched publishers / dependent pairs',f"{C['matchedPublishers']} / {C['matchedPairs']}"],])
tab('duration-table.tex','lrrrrr',['Publisher','Known / indexed','Mean','Median','$Q_1$--$Q_3$','$\\geq30$ min'],[[tex(c['displayName']),f"{c['durationCount']} / {c['videoCount']}",f"{c['meanMinutes']:.1f}",f"{c['medianMinutes']:.1f}",f"{c['q1Minutes']:.1f}--{c['q3Minutes']:.1f}",f"{100*c['longFormatShare']:.0f}\\%"] for c in D['focalDurations']])
tab('sensitivity-table.tex','lrrr',['Comparison','Publishers','Pairs',r'Spearman $\rho$'],[[tex(s['comparison']),s['publishers'],s['pairs'],f"{s['rho']:.3f}"] for s in S])
tab('lopo-table.tex','lrr',['Omitted publisher','Retained pairs',r'Spearman $\rho$'],[[tex(r['omittedPublisher']),r['retainedPairs'],f"{r['rho']:.3f}"] for r in sorted(LO['rows'],key=lambda r:r['rho'])])
tab('caption-length-table.tex','lr',['Caption word-count summary','Tokens'],[['Minimum',L['min']],['25th percentile',f"{L['q1']:.1f}"],['Median',f"{L['median']:.1f}"],['75th percentile',f"{L['q3']:.1f}"],['Maximum',L['max']],['Total',f"{L['sum']:,}"]])
CAPTIONS={}
def save(fig,name,caption):
 fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None,'Creator':'Channeling Atlas paper generator'})
 fig.savefig(FIG/(name+'.png'),bbox_inches='tight',dpi=240)
 plt.close(fig);CAPTIONS[name]=caption
# Two separate eligibility sequences: differing scales are explicit.
fig,axs=plt.subplots(1,2,figsize=(7.15,3.3),gridspec_kw={'width_ratios':[1,1.25]})
for ax,labels,values,title,xmax in [
 (axs[0],['Indexed videos','English-likely titles','Attributed, embedded titles'],[925,742,706],'A. Title sequence',1000),
 (axs[1],['Caption attempts','Retrieved tracks','English tracks','English pilot','Title-matched eligible','Two-video group subset'],[36,34,31,30,25,22],'B. Caption sequence',40)]:
 y=np.arange(len(labels));ax.barh(y,values,color=GREEN,height=.57);ax.set_yticks(y,[textwrap.fill(x,21) for x in labels]);ax.invert_yaxis();ax.set_xlim(0,xmax);ax.set_xlabel('Video records');ax.set_title(title,loc='left',fontweight='bold');ax.grid(axis='x',color='#dddddd',lw=.5);ax.set_axisbelow(True)
 for yy,v in zip(y,values):ax.text(v+xmax*.02,yy,str(v),va='center',fontsize=9)
fig.subplots_adjust(left=.2,right=.95,bottom=.18,top=.9,wspace=1.12)
save(fig,'coverage','Eligibility sequences in the purposive corpus. Axes have different count ranges. The title sequence excludes titles that fail the English-likely gate or lack an uploader attribution. The caption sequence removes two unavailable tracks, three non-English tracks, one additional concordance sample, five videos without eligible matched titles, and three singleton publisher records. The final matched matrix therefore uses22videos from11publishers; the larger matched keyword table uses25videos. These are research-sample filters, not population attrition rates.')
# Six named focal uploader accounts, linear units and explicit IQR.
cs=D['focalDurations'][:6];fig,ax=plt.subplots(figsize=(7.15,3.2));y=np.arange(len(cs));med=np.array([c['medianMinutes'] for c in cs]);q1=np.array([c['q1Minutes'] for c in cs]);q3=np.array([c['q3Minutes'] for c in cs]);ax.errorbar(med,y,xerr=[med-q1,q3-med],fmt='o',color=GREEN,capsize=3,ms=4,label='Median and middle50%');ax.scatter([c['meanMinutes'] for c in cs],y,marker='D',facecolors='none',edgecolors=GOLD,s=25,label='Mean');ax.set_yticks(y,[f"{c['displayName']} (n={c['durationCount']})" for c in cs]);ax.invert_yaxis();ax.set_xlim(left=0);ax.set_xlabel('Observed upload duration (minutes)');ax.grid(axis='x',color='#dddddd',lw=.5);ax.legend(frameon=False,loc='lower right');fig.subplots_adjust(left=.29,right=.97,top=.97,bottom=.19)
save(fig,'duration','Observed durations in six focal uploader samples. Filled points are medians; whiskers span linear25th–75thpercentiles and are not confidence intervals; open diamonds are means. All indexed videos in these six samples have known durations. The official Bashar account and Divine Insights are distinct publishers: their sampled clip/full-session mix differs. The figure does not estimate complete-channel means or compare practitioner session lengths.')
# Actual same-document matched scatter plus publisher-omission sensitivity.
fig,axs=plt.subplots(1,2,figsize=(7.15,3.6),gridspec_kw={'width_ratios':[1,1.12]});ps=D['matched']['pairs'];ax=axs[0];ax.scatter([p['titleCosine'] for p in ps],[p['captionCosine'] for p in ps],s=17,c=GREEN,alpha=.8,edgecolors='white',linewidths=.3);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Matched-title cosine');ax.set_ylabel('Matched-caption cosine');ax.set_title('A. Same-video channel pairs',loc='left',fontweight='bold');ax.text(.04,.93,f"55 pairs; Spearman ρ={D['matched']['rho']:.3f}",transform=ax.transAxes,fontsize=8.5);ax.grid(color='#dddddd',lw=.45);ax.set_axisbelow(True)
short={'Pamela Aaralyn Channeling':'Pamela Aaralyn','Ishuwa Yahyel: First ET Contact':'Ishuwa Yahyel','SOLi School | Lyssa Royal Holt':'Lyssa Royal Holt','Psychic Medium & Trance Channel RIZ & Lady O':'RIZ & Lady O','Bashar Channeled by Darryl Anka':'Bashar (official)'}
lr=sorted(LO['rows'],key=lambda x:x['rho']);ax=axs[1];yy=np.arange(len(lr));ax.scatter([r['rho'] for r in lr],yy,s=23,c=GOLD);ax.axvline(D['matched']['rho'],color=GREEN,ls='--',lw=1);ax.axvline(0,color='#888888',lw=.6);ax.set_yticks(yy,[short.get(r['omittedPublisher'],r['omittedPublisher']) for r in lr]);ax.invert_yaxis();ax.set_xlim(-.1,.45);ax.set_xlabel('Spearman ρ after omission');ax.set_title('B. Omit one publisher',loc='left',fontweight='bold');ax.grid(axis='x',color='#dddddd',lw=.45);ax.set_axisbelow(True)
fig.subplots_adjust(left=.09,right=.99,top=.91,bottom=.2,wspace=1.22)
save(fig,'matched-similarity',f"Matched title and caption comparisons use the same22videos in11publishers, yielding55dependent off-diagonal channel pairs. Left: raw cosines from the same pinned model, applied to different text units; their rank correlation is{D['matched']['rho']:.3f}. Right: each omission removes one publisher and all10incident pairs, leaving45pairs among10publishers. The dashed line is the full-sample correlation. The omission range[{LO['minRho']:.3f},{LO['maxRho']:.3f}] is a descriptive influence range, not a confidence interval or a significance test.")
# Sensitivity rank comparisons plus length distribution.
fig,axs=plt.subplots(1,2,figsize=(7.15,3.25),gridspec_kw={'width_ratios':[1.2,1]});ax=axs[0];ss=S[:3];yy=np.arange(3);ax.scatter([s['rho'] for s in ss],yy,s=32,c=GREEN);ax.set_yticks(yy,['Raw / masked titles\n23 publishers;253pairs','All / deduplicated titles\n23 publishers;253pairs','Full / trimmed captions\n13 publishers;78pairs']);ax.set_xlim(0,1.04);ax.invert_yaxis();ax.set_xlabel('Spearman rank correlation');ax.set_title('A. Method sensitivity',loc='left',fontweight='bold');ax.grid(axis='x',color='#dddddd',lw=.5)
for y0,s in zip(yy,ss):ax.text(s['rho']-.02,y0+.17,f"{s['rho']:.3f}",ha='right',fontsize=9)
ax=axs[1];lengths=sorted(r['words'] for r in L['rows']);ax.scatter(lengths,np.arange(1,len(lengths)+1),s=16,c=GOLD);ax.set_xscale('log');ax.set_xlim(65,12000);ax.set_xticks([100,1000,10000],['100','1,000','10,000']);ax.set_xlabel('Caption word tokens (log scale)');ax.set_ylabel('Ordered caption record');ax.set_yticks([1,10,20,30]);ax.set_ylim(0,31);ax.set_title('B. Caption lengths',loc='left',fontweight='bold');ax.grid(axis='x',color='#dddddd',lw=.5)
fig.subplots_adjust(left=.29,right=.98,top=.9,bottom=.24,wspace=.85)
save(fig,'sensitivity',f"Left: agreement of off-diagonal similarity rankings under specified methodological changes. Comparisons use different cohorts and interventions; these values are not model accuracy or uncertainty estimates. Removing outer10%of caption words from each end retains a high global rank correlation but changes the nearest neighbor of4of13publishers. Right: all30English pilot caption lengths, from{L['min']}to{L['max']}word tokens; median{L['median']:.1f}. The logarithmic horizontal axis accommodates the unequal document lengths. Chunked embedding avoids truncating every recording to its beginning, while equal-video aggregation avoids giving longer recordings greater publisher weight.")
(OUT/'figure-captions.json').write_text(json.dumps(CAPTIONS,ensure_ascii=False,indent=2))
(OUT/'formulas.tex').write_text(r'''% Optional methods fragment; requires amsmath.
Let $\mathbf e_{vc}$ denote the unit-normalized mean-pooled embedding of chunk $c$ in video $v$. The published pilot uses
\begin{align}
\mathbf z_v &= \operatorname{norm}\!\left(C_v^{-1}\sum_{c=1}^{C_v}\mathbf e_{vc}\right), &
\mathbf z_g &= \operatorname{norm}\!\left(n_g^{-1}\sum_{v\in g}\mathbf z_v\right),\\
S^{(T)}_{gh} &= (\mathbf z_g^{(T)})^\top\mathbf z_h^{(T)}, &
S^{(C)}_{gh} &= (\mathbf z_g^{(C)})^\top\mathbf z_h^{(C)}.
\end{align}
Here $T$ and $C$ identify matched titles and captions, and $g,h$ identify uploader groups. Spearman correlation is computed over the shared off-diagonal pairs $g<h$. For publisher $j$, the omission diagnostic removes every pair with $g=j$ or $h=j$ and recomputes the correlation over the remaining45pairs. The minimum and maximum of these11values are a deterministic sensitivity range, not an inferential interval.
''')
files=[OUT/'paper-results.json',OUT/'results.tex']+list(FIG.glob('*'))
(OUT/'artifact-manifest.json').write_text(json.dumps([{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2))
print('Generated macros',len(macros),'tables5, figures4(PDF/PNG)')
