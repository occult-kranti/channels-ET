#!/usr/bin/env python3
"""Render fixed paper figures from the public, hash-bound snapshot; no model fitting."""
import json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=pathlib.Path(__file__).resolve().parent;S=json.loads((P/'snapshot.json').read_text());F=P/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
groups=S['graph']['groups'];fig,ax=plt.subplots(figsize=(10.5,8));y=list(range(len(groups)));ax.barh([z-.17 for z in y],[g['direct_claim_medium_records'] for g in groups],height=.32,color='#356d85',label='Direct-attribution human records');ax.barh([z+.17 for z in y],[g['new_attributed_message_mediums'] for g in groups],height=.32,color='#b36a48',label='Mediums represented in new text pilot');ax.set_yticks(y,[g['label'] for g in groups]);ax.invert_yaxis();ax.set_xlabel('Descriptive record count (not independent origins)');ax.set_xticks(range(0,12));ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='lower right',frameon=False);ax.set_title('Attributed labels extend far beyond observed cross-medium text',loc='left',pad=16,fontweight='bold');fig.tight_layout();
for ext in ['png','pdf']:fig.savefig(F/('claim-coverage.'+ext),dpi=180,bbox_inches='tight')
plt.close(fig)
med=['medium-darryl-anka','medium-andrew-elan','medium-tyler-ellison','medium-daniel-scranton','medium-lyssa-royal-holt'];entities=['et-bashar-darryl','et-bashar-andrew','et-elan-andrew','et-ryokah-tyler','et-ashanti-daniel','et-phc7-daniel','et-arcturian-daniel','et-sasha-lyssa'];families=['bashar','sassani','pleiadian','arcturian'];mx={m:(0,8-i*1.7) for i,m in enumerate(med)};ex={e:(1,8-i) for i,e in enumerate(entities)};gx={g:(2,y) for g,y in zip(families,[7.6,5.4,2.5,.8])};labels={'et-bashar-darryl':'Bashar (Darryl attribution)','et-bashar-andrew':'Bashar (Andrew attribution)','et-elan-andrew':'Elan','et-ryokah-tyler':'RYOKAH','et-ashanti-daniel':'Ashanti','et-phc7-daniel':'Pleiadian High Council of Seven','et-arcturian-daniel':'9D Arcturian Council','et-sasha-lyssa':'Sasha'};fig,ax=plt.subplots(figsize=(12,6));selected=[e for e in S['graph']['edges'] if e['medium_id'] in med and e['channellee_id'] in entities];assert len(selected)==8
for e in selected:
 x1,y1=mx[e['medium_id']];x2,y2=ex[e['channellee_id']];ax.plot([x1+.22,x2-.28],[y1,y2],color='#356d85',alpha=.65,lw=1.6,zorder=1)
for g in groups:
 key=g['id'].removeprefix('et-group-')
 if key not in families:continue
 for eid in g['channellee_ids']:
  if eid in ex:
   x1,y1=ex[eid];x2,y2=gx[key];ax.plot([x1+.29,x2-.24],[y1,y2],color='#b36a48',ls='--',alpha=.65,lw=1.5,zorder=1)
for m,(x,y) in mx.items():ax.text(x,y,S['graph']['medium_names'][m].replace(' (Elan Interactions)',''),ha='center',va='center',bbox={'boxstyle':'round,pad=.5','facecolor':'#e7f0f4','edgecolor':'#356d85'},zorder=2)
for e,(x,y) in ex.items():ax.text(x,y,labels[e],ha='center',va='center',fontsize=9,bbox={'boxstyle':'round,pad=.5','facecolor':'white','edgecolor':'#888'},zorder=2)
for g,(x,y) in gx.items():ax.text(x,y,{'bashar':'Shared name: Bashar','sassani':'Sassani / Essassani\nvocabulary','pleiadian':'Pleiadian labels','arcturian':'Arcturian labels'}[g],ha='center',va='center',bbox={'boxstyle':'round,pad=.5','facecolor':'#faeee6','edgecolor':'#b36a48'},zorder=2)
for x,t in [(0,'PUBLISHER-ATTRIBUTED PERSON'),(1,'SOURCE-SPECIFIC LABEL'),(2,'COMPARISON GROUP')]:ax.text(x,9,t,ha='center',fontsize=9,fontweight='bold')
ax.set_xlim(-.42,2.42);ax.set_ylim(-.1,9.5);ax.axis('off');fig.text(.5,.02,'Solid: publisher attribution. Dashed: analytic grouping; no shared speaker identity or independent origin established.',ha='center',fontsize=9);fig.tight_layout(rect=[0,.05,1,1]);
for ext in ['png','pdf']:fig.savefig(F/('typed-network-example.'+ext),dpi=180,bbox_inches='tight')
plt.close(fig)
