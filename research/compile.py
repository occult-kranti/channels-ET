import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
names=['history_ra','bashar','athina_ryok','lesser_known','emerging','forums','supplement','recent_profiles']
data={k:[] for k in ['profiles','events','sources','communityItems','videoItems','entities','insights']}
for name in names:
    part=json.loads((ROOT/'research'/f'{name}.json').read_text())
    for key in data:
        data[key].extend(part.get(key,[]))
# Exclude an anticipated occurrence from the documentary timeline; discuss the forecast in an insight.
data['events']=[e for e in data['events'] if not str(e.get('type','')).startswith('Future claim')]
for i,event in enumerate(data['events']):
    event['id']=event.get('id',f'event-{i+1:02}')
    event['datePrecision']=event.get('datePrecision','range' if '–' in str(event['date']) else {4:'year',7:'month',10:'day'}.get(len(str(event['date'])),'as recorded'))
data['events'].sort(key=lambda e:str(e.get('date','9999'))[:10])
# Preserve source identity while collapsing exact URL repeats.
by_url={};aliases={};sources=[]
for source in data['sources']:
    key=source['url'].rstrip('/')
    if key in by_url:
        aliases[source['id']]=by_url[key]['id']
        prior=by_url[key]
        if source.get('notes') and source['notes'] not in prior.get('notes',''):prior['notes']=prior.get('notes','')+' '+source['notes']
    else:
        by_url[key]=source;sources.append(source)
data['sources']=sources
for source in data['sources']:
    for key in ['ref','webRef','retrievalRef']:source.pop(key,None)
    source['accessed']='2026-10-22'
    if source['id']=='ba-youtube-2027':
        source['notes']='Indexed upload metadata and the complete 22-second automatic-caption transcript were read. Captions describe an official introduction within two years; no audiovisual review. Automatic rendering of group names is uncertain and not silently corrected. Original session date remains unresolved.'

def refs(ids):return list(dict.fromkeys(aliases.get(x,x) for x in ids))
for key in ['profiles','events','communityItems','videoItems','insights']:
    for item in data[key]:item['sourceIds']=refs(item.get('sourceIds',[]))
# Correct fields to describe attributed origin rather than project branding.
pmap={p['id']:p for p in data['profiles']}
pmap['ar-athina-ashtar']['origin']='Ashtar is framed as a galactic guide; one interview description links him with the Pleiadians. No single homeworld is established here.'
pmap['ar-ryok']['origin']='Ellison links the guide with the Sassani civilization and describes the current Ryokah form as nonphysical.'
# Do not imply verification of a legacy source that is absent from this source ledger.
pmap['lk-lyssa']['caveats']=[x for x in pmap['lk-lyssa']['caveats'] if not x.startswith('A legacy biography')]
# Keep single-source portraits compact, including their repeated timeline labels.
pmap['hr-bailey-profile']['summary']='An earlier corpus attributed to a spiritual teacher; its publishing organization began in 1922.'
pmap['hr-bailey-profile']['claims']=['The tradition attributes the books to telepathic collaboration.']
pmap['hr-bailey-profile']['origin']='Lucis Trust describes a Tibetan teacher, not an ET species.'
pmap['lk-rob']['summary']='The E.T. Whisperer presents multiple attributed guides through trance channeling.'
pmap['lk-rob']['claims']=['Presents Treb, Aridif and Metatron as distinct guides.']
pmap['lk-rob']['caveats'][1]='The Deneb/Pleiadian combination is retained as lore; those are distinct astronomical references.'
pmap['lk-lee']['summary']='A channeling archive of messages, books and commercial spiritual offerings.'
pmap['lk-lee']['claims']=['Carroll describes himself as Kryon’s original channel.']
pmap['lk-paul']['summary']='An author and workshop teacher presenting channeled books and intuitive readings.'
pmap['lk-paul']['claims']=['Attributes books to The Guides and describes intuitive readings involving living people.']
# One public appearance per media URL.
data['videoItems']=list({v['url']:v for v in data['videoItems']}.values())
for i,v in enumerate(data['videoItems']):v['id']=f'media-{i+1:02}'
for v in data['videoItems']:
    if v['url']=='https://www.youtube.com/watch?v=bq1bcqM120M':
        v['notes']='Access: upload metadata and complete automatic captions for the 22-second clip reviewed; no audiovisual review. The captions discuss official introduction within two years. Group-name transcription is uncertain. Upload date is not a verified original session date.'
pmap['ba-bashar']['caveats']=[x if not x.startswith('Video catalog') else 'Most video entries were reviewed through descriptions or metadata; one 22-second clip’s automatic captions were read. No audiovisual review.' for x in pmap['ba-bashar']['caveats']]

def entity(id,name,classification,description,ids,caveat):
    return {'id':id,'name':name,'classification':classification,'description':description,'profileIds':ids,'sourceIds':refs([s for pid in ids for s in pmap[pid]['sourceIds']]),'caveats':[caveat]}
data['entities']=[
entity('ent-confederation','Ra, Hatonn & Q’uo','Collectives and collaborative principle','L/L Research presents a related Confederation cosmology. Q’uo is described as involving Hatonn, Latwii and Ra.',['hr-ra','hr-hatonn','hr-quo'],'This is an internal relationship in one archive, rather than three independent confirmations.'),
entity('ent-ashtar','Ashtar','Shared named guide / commander','The name appears in Van Tassel’s older text and in Król’s contemporary material. These are separate human-source records.',['hr-ashtar','ar-athina-ashtar'],'Name matching does not demonstrate the same speaker, a direct influence, or a common extraterrestrial origin.'),
entity('ent-sassani','Essassani / Sassani narratives','Claimed hybrid ET civilization','Bashar, Elan and Ryokah are associated with related civilization labels by their respective publishers.',['ba-bashar','ar-ryok','em-elan'],'The descriptions vary; this grouping compares narratives and is not a biological taxonomy.'),
entity('ent-pleiadian','Pleiadian-associated sources','Star-associated collectives and guides','Sasha, Kennedy’s collective and Gauthier’s Aridif receive different descriptions despite a shared Pleiadian label.',['lk-lyssa','lk-wendy','lk-rob'],'A shared astronomical name does not establish that the guides are identical or that a civilization has been detected.'),
entity('ent-arcturian','The Arcturian Council','Claimed nonphysical collective','Scranton presents a ninth-dimensional Council associated with Arcturus, alongside many other sources.',['lk-daniel'],'Dimension labels are spiritual terminology in these materials, not measured spatial coordinates.'),
entity('ent-sirian','Adronis','Claimed Sirian consciousness','Johnson associates Adronis with Sirius A; his public descriptions vary in claimed density.',['lk-brad'],'Developmental levels and star origins remain statements within the channeling account.'),
entity('ent-yahyel','Ishuwa / Yahyel','Claimed humanlike ET civilization','Swanson describes Ishuwa as a Yahyel explorer and heart-language translator.',['lk-shaun'],'The narrative is distinct from independent investigation of the Phoenix Lights.'),
entity('ent-guides','Nonphysical teachers & guides','Not specifically extraterrestrial','Seth, Abraham, Selig’s Guides and VERONICA are presented as nonphysical teachers or collectives.',['hr-seth','lk-esther','lk-paul','em-april'],'These sources should not be automatically turned into an ET-species list.'),
entity('ent-angelic','Kryon & esoteric masters','Angelic / esoteric framing','Carroll presents Kryon as angelic; Bailey’s work describes the Tibetan as a spiritual teacher.',['lk-lee','hr-bailey-profile'],'These are different traditions and claimed identities, grouped only to distinguish their framing from ET narratives.'),
entity('ent-mediumship','Sanaya & deceased-person mediumship','Collective guides and afterlife claims','Giesemann combines messages attributed to Sanaya with claimed contact involving deceased loved ones.',['lk-suzanne'],'Personal testimony and practitioner claims of evidence do not alone verify an afterlife.'),
entity('ent-unspecified','Ocyphius & Sylvester','Claimed entities; origin unresolved','Swainhart’s public materials identify these guides without establishing a species or homeworld in the records reviewed.',['em-roxanne'],'An unresolved origin is retained rather than filled in from audience speculation.')
]
data['insights']+= [
{'title':'Begin with Ra. Keep the earlier history.','body':'Ra session 1 is dated January 15, 1981. Van Tassel’s text carries an Ashtar message dated July 18, 1952. The timeline therefore places Ra within a longer modern history, rather than calling it the beginning of channeling.','sourceIds':['hr-ra-1','hr-ashtar-original']},
{'title':'Even official chronologies can disagree','body':'Current Bashar material gives 1983, while a legacy official page gives 1984. Kennedy’s official biographies give 1994 and 1995. These unresolved differences remain visible in the profiles.','sourceIds':['ba-biography','ba-legacy-history','lk-s03','lk-s04']},
{'title':'A forecast is not a timeline occurrence','body':'Bashar’s May 2025 catalog promotes a probability-framed 2027 contact forecast. At this edition’s October 22, 2026 cutoff, that target is still future. The site records the publication of the forecast and makes no fulfillment judgment.','sourceIds':['ba-2027-session','ba-2027-live']},
{'title':'Forum reception is mixed','body':'Selected WizardForums and BALG threads contain source-verification questions, practical appreciation and criticism. They document particular conversations, not a representative survey or a verdict on authenticity.','sourceIds':['fo-s07','fo-s11','fo-s12']}
]
for insight in data['insights']:insight['sourceIds']=refs(insight['sourceIds'])
data['meta']={
 'title':'Channeling Atlas','date':'2026-10-22','edition':'Research edition 01',
 'scope':'A curated public-source atlas of channelers, mediums, claimed entities and spiritual-healing narratives. Ra is the entry point, with earlier historical context and a focus on Bashar, Athina Król / Ashtar and Tyler Ellison / Ryokah.',
 'method':[
  'Start with each practitioner’s own archive, biography or public recording index; use forums for reception and discovery, not as proof of identity.',
  'Separate the human channeler, attributed speaker, claimed origin and type of claim. Preserve spelling changes and unresolved identities.',
  'Label dates by their basis: retrospective experience, dated session, publication, upload, institutional event or community discussion. A date is not proof of the claimed source.',
  'Retain conflicts and unknown dates. Do not infer an onset from a copyright, an experience total, or a recently uploaded old recording.',
  'Link source records and access notes from profiles and timeline entries. Primary means close to the claim, not independently verified.',
  'Compare alternative explanations without diagnosing individual practitioners. Personal usefulness, source identity and medical efficacy require different evidence.'
 ],
 'limits':[
  'This is a bounded research edition, not an exhaustive census of all channelers or healers. Discovery favors English-language indexed material.',
  'Only publicly available material was used. Public advertisements for private sessions are included; closed groups, paid recordings, private client records and private communications were not accessed.',
  'YouTube research used metadata, creator descriptions, official catalogs and linked records. One 22-second Bashar clip’s complete automatic captions were read. Other full transcripts were not reviewed; caption export was unavailable for the selected Athina and Ryok videos. No audiovisual playback was reviewed. Each media entry states the access level.',
  'Several L/L Research pages blocked full-page retrieval; those records rely on indexed official extracts. This is not a fresh complete audit of all Ra audio or transcripts.',
  'Forum samples are not representative of whole communities. Relative Reddit ages were not converted into invented exact publication dates. Some WizardForums outgoing links required login.',
  'The source set does not independently establish extraterrestrial or spirit identities, paranormal mechanisms, healing efficacy or promised financial outcomes. The site documents attributed claims.',
  'Current prices, session availability and membership offerings were not audited. Historical amounts in thread titles remain historical claims.'
 ],
 'dateLegend':{'Reported onset':'Retrospective practitioner account, not a contemporaneously verified contact','Dated session':'Date carried by an archive or recording record','Publication / upload':'When a record appeared; may differ from the performance','Community discussion':'When a particular thread or comment appeared','Unresolved':'No defensible exact date established'}
}
# Preserve a separate forecast register in the downloadable data.
data['forecasts']=[{'target':'2027','claim':'Probability-framed open-contact forecast','status':'Future at 2026-10-22 cutoff; no fulfillment judgment','sourceIds':['ba-2027-session','ba-2027-live']},{'target':'2027–2030','claim':'Acceleration narrative in an Athina Król / Ashtar interview description','status':'Future at 2026-10-22 cutoff; description reviewed, full recording unreviewed','sourceIds':['ar-athina-ortiz']}]
from extend_youtube import enrich
data=enrich(data)
from extend_discovery import enrich_discovery
data=enrich_discovery(data)
(ROOT/'dist'/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:len(data[key]) for key in ['profiles','events','sources','communityItems','videoItems','entities','insights']}))
