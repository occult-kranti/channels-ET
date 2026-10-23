#!/usr/bin/env python3
"""Render the documented evidence transformations, not a hypothetical dataset."""
import json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch

p=pathlib.Path(__file__).resolve().parents[1];r=p.parents[2]
a=json.load(open(r/'research/continuation/analysis/results.json'));q=json.load(open(r/'research/expansion/qa/summary.json'));m=json.load(open(r/'research/continuation/models/benchmark-results.json'));base=json.load(open(r/'dist/analysis/data.json'))
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none','font.size':10})
fig,ax=plt.subplots(figsize=(10,4.4));ax.set_xlim(0,10);ax.set_ylim(0,4.4);ax.axis('off')
blue='#35688a';gold='#b58a42';ink='#25313b';edge='#c8cfd3'
def box(x,y,w,h,text,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.03,rounding_size=.04',facecolor='white',edgecolor=color,linewidth=1.1));ax.text(x+w/2,y+h/2,text,ha='center',va='center',color=ink,linespacing=1.5)
def arrow(x,y,xx,yy):ax.add_patch(FancyArrowPatch((x,y),(xx,yy),arrowstyle='-|>',mutation_scale=10,color='#7b8790',linewidth=1))
box(.1,3,2.8,1.0,f"Public upload index\n{a['coverage']['uploads']} retained IDs",blue)
box(3.55,3,2.9,1.0,f"Retained text layers\n{base['coverage']['titleCount']} eligible titles\n{a['coverage']['captionDocuments']} caption derivatives",blue)
box(7.1,3,2.8,1.0,'Matched diagnostics\n25 uploads\n14 publishers',blue)
arrow(2.95,3.5,3.48,3.5);arrow(6.5,3.5,7.03,3.5)
box(.1,1.65,2.8,1.0,f"AI-generated digests\n{q['coverage']['digestVideos']} total; {q['coverage']['videosWithQACandidates']} with Q&A",gold)
box(3.55,1.65,2.9,1.0,f"Typed Q&A candidates\n{q['coverage']['qaCandidates']} records\none practitioner context",gold)
box(7.1,1.65,2.8,1.0,f"Source-proxy guard\n{a['lexicalGraph']['benchmarkGuard']['sourceGroups']} groups\nnot verified sessions",gold)
arrow(2.95,2.15,3.48,2.15);arrow(6.5,2.15,7.03,2.15)
box(2.2,.15,6.9,1.0,f"Local CPU pilot: {m['split']['trainExamples']} train examples; {m['split']['testQuestions']} held-out questions + {m['split']['controls']} controls\n{len(m['arms'])} arms; 50 retained responses; strict marker ≠ semantic refusal",blue)
arrow(8.5,1.6,8.5,1.2)
ax.text(.1,.68,'Separate source types;\nexplicit transformations',ha='left',va='center',fontsize=9,color='#53606a')
out=p/'generated/figures';out.mkdir(parents=True,exist_ok=True)
fig.savefig(out/'evidence-flow.pdf',bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None});fig.savefig(out/'evidence-flow.png',bbox_inches='tight',dpi=160);plt.close(fig)
print('Evidence-flow figure generated from current source counts')
