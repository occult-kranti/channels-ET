#!/usr/bin/env python3
"""Reconcile accepted editions into one reproducible publication/body frame.

No acquisition or inference. Full text is loaded from verified private artifacts;
only metadata is exported. Run with the existing analysis virtual environment.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import urlsplit, urlunsplit, unquote, quote

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path('/workspace/channels-et-private')
NORMALIZATION = 'Unicode NFKC, outer whitespace stripped; no internal whitespace/case change'


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def read_json(p): return json.loads(Path(p).read_text())
def write_json(p, data): Path(p).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
def slug(s): return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()).strip('-')
def normalize(s): return unicodedata.normalize('NFKC', s).strip()


def artifact(p):
    p = Path(p); raw = p.read_bytes()
    return {'path': str(p), 'bytes': len(raw), 'sha256': sha_bytes(raw)}


def check_artifact(ref):
    raw = Path(ref['path']).read_bytes()
    if sha_bytes(raw) != ref['sha256'] or ('bytes' in ref and len(raw) != ref['bytes']):
        raise ValueError('Artifact changed: ' + ref['path'])
    return raw


def body(ref, transform):
    raw = check_artifact(ref)
    text = json.loads(raw)['text'] if transform.startswith('json_text') else raw.decode('utf-8')
    if transform.endswith('_html_clean'):
        text = html.unescape(re.sub(r'<[^>]*>', '', text))
    return normalize(text)


def module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


def canonical_url(value):
    """Conservative document URL normalization; caller must reject container URLs."""
    if not value: return None
    p = urlsplit(value)
    if p.scheme not in {'http', 'https'} or not p.hostname: raise ValueError('Non-public URL')
    path = re.sub(r'%[0-9a-fA-F]{2}', lambda m: m[0].upper(), p.path)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path.rstrip('/') or '/', p.query, ''))


def date_value(v):
    if not v: return None
    try: return dt.datetime.fromisoformat(v.replace('Z', '+00:00')).isoformat() if 'T' in v else dt.date.fromisoformat(v).isoformat()
    except ValueError:
        try: return parsedate_to_datetime(v).isoformat()
        except (ValueError, TypeError): return None


def context(channel, name, creator, publisher, publisher_url=None):
    return {'channel_id': channel, 'channel_name': name, 'creator_id': 'creator-' + slug(creator),
            'creator_name': creator, 'publisher_id': 'publisher-' + slug(publisher),
            'publisher_name': publisher, 'publisher_url': publisher_url}


TRACY = context('tracy-kumbera', 'Tracy Kumbera publisher episodes', 'Tracy Kumbera', 'Your MultiDimensional Journey with Tracy Kumbera', 'https://www.tracykumbera.com/')
OMNA = context('natalie-glasson-omna', 'Natalie Glasson / OmNa', 'Natalie Glasson', 'OmNa', 'https://omna.org/')


def candidate(sid, text, ref, transform, cohort, ctx, **meta):
    text = normalize(text)
    if body(ref, transform) != text: raise ValueError('Accepted loader transformation differs: ' + sid)
    r = {'edition_id': sid, 'cohort': cohort, 'title': sid, 'source_url': None,
         'publication_url': None, 'publication_id': None, 'recording_family_id': None,
         'audio_sha256': None, 'media_artifact': None, 'duration_seconds': None,
         'publication_date': None, 'publication_date_raw': None,
         'document_kind': 'machine_transcript', 'text_origin': 'machine_asr',
         'coverage_scope': 'full_selected_text_edition_not_accuracy_validation',
         'attribution_scope': 'source_context_only; speakers_and_claimed_identity_unverified',
         'speaker_role': 'unknown', 'claimed_label': None, 'language': 'en',
         'language_eligible': True, 'language_basis': 'English admission inherited from accepted cohort; not a new human language audit',
         'text_artifact': {k: ref[k] for k in ('path', 'bytes', 'sha256') if k in ref},
         'body_transform': transform, 'body_sha256': sha_bytes(text.encode()), 'words': len(text.split()),
         'priority': 50, 'legacy_source_ids': [sid], **ctx, **meta}
    r['publication_url'] = canonical_url(r['publication_url'])
    if r.get('media_artifact'):
        r['media_artifact']={k:v for k,v in r['media_artifact'].items() if k in {'path','sha256','bytes','role'}}
    return r


def gather(work):
    editions, inputs, dispositions = [], [], []
    joint = module('channel_joint', 'research/expanded-channeling/analyze.py')
    docs, audit, _ = joint.load_accepted(); inputs += audit['inputs']
    originals = {}
    for p, _ in joint.MANIFESTS:
        originals.update({r['source_id']: r for r in read_json(p)['records']})
    guest = {r['source_id']: r for r in read_json(ROOT/'research/harvest/publisher_sources/publisher-summary.json')['records']}
    for d in docs:
        s = d['summary']; sid = s['source_id']; old = originals[sid]; g = s['group_id']
        url = old.get('download_url') or old['source_url']; puburl = url
        audio = old.get('audio_artifact') or next((e for e in old.get('evidence', []) if e.get('role') in {'source_audio','audio'}), None)
        if g == 'ra_published':
            ctx = context('ra-law-of-one', 'Ra Lightly Edited sessions', 'Carla L. Rueckert / L/L Research session context', 'L/L Research / Law of One', 'https://www.lawofone.info/')
        elif g.startswith('official_'):
            ctx = context('bashar-official', 'Bashar Communications official Vimeo', 'Darryl Anka', 'Bashar Communications', 'https://www.bashar.org/')
        elif g == 'bashar_context':
            p = guest[sid]; puburl = p['enclosure_url']; url = p.get('episode_url') or puburl
            ctx = context('guest-' + slug(p['publisher_name']), p['publisher_name'] + ' — guest context', 'Darryl Anka (guest context; mixed speakers)', p['publisher_name'], p['feed_url'])
        elif g == 'tracy_kumbera': ctx = TRACY
        else: ctx = context('magenta-pixie', 'Magenta Pixie publisher PDFs', 'Magenta Pixie', 'Magenta Pixie', 'https://www.magentapixie.com/')
        written = g in {'ra_published', 'magenta_pixie'}
        editions.append(candidate(sid, d['text'], old['text_artifact'], 'json_text_html_clean' if old.get('source_format') == 'srt' else 'json_text',
            'accepted_joint292', ctx, title=s['title'], source_url=url, publication_url=puburl,
            publication_id=old.get('session_id') or old.get('publication_family_id'), recording_family_id=old.get('duplicate_family_id'),
            publication_date=date_value(s.get('published_at')), publication_date_raw=s.get('published_at'),
            document_kind='publisher_transcript' if written else ('interview_asr' if g == 'bashar_context' else 'caption_or_asr'),
            text_origin=s['text_origin'], duration_seconds=s.get('duration_seconds') or old.get('audio_duration_seconds'),
            media_artifact=audio, audio_sha256=audio.get('sha256') if audio else None,
            language_basis=old.get('language_basis') or 'Accepted English published edition',
            coverage_scope=old.get('coverage_scope') or old.get('coverage_basis') or old.get('text_scope'),
            claimed_label='Ra' if g == 'ra_published' else ('Bashar context' if g.startswith('official_') or g == 'bashar_context' else None),
            speaker_role='publisher_printed_roles_unverified' if g == 'ra_published' else 'unknown', priority=30))
    collected = module('channel_collected', 'research/expanded-channeling/analyze_collected_audio.py')
    base = PRIVATE/'expanded-channeling-2026-11/completion/coordinated-council-01/inputs'
    docs, audios, audit = collected.load(base/'acquisition.json', [base/'merged-asr.json'], work)
    inputs += audit['inputs']; dispositions += audit['dispositions']
    refs = {r['source_id']: r['text_artifact'] for r in audit['verified_texts']}
    for a in audios.values():
        refs.update({r['source_id']: r['text_artifact'] for r in (a.get('caption_link') or {}).get('records', [])})
    for d in docs:
        s = d['summary']; a = audios[s['publication_id']]; src = a['source']; sid = s['source_id']
        ctx = TRACY if s['group_id'] == 'tracy_kumbera_publisher' else OMNA if s['group_id'] == 'tr-medium-natalie-glasson' else context('multidimensional-soul', 'Multidimensional Soul publisher interviews', 'Akanksshaa (host context; guests unresolved)', 'Multidimensional Soul', 'https://akanksshaa.podbean.com/')
        editions.append(candidate(sid, d['text'], refs[sid], 'json_text_html_clean', 'completed_publisher228', ctx,
            title=s['title'], source_url=s['source_url'], publication_url=s['source_url'], publication_id=s['publication_id'],
            recording_family_id=s['exact_original_family_id'], audio_sha256=a['audio']['sha256'], media_artifact=a['audio'],
            duration_seconds=s['duration_seconds'], publication_date=date_value(s['publication_date']), publication_date_raw=s['publication_date_raw'],
            date_status=s['date_status'], text_origin=s['text_origin'], document_kind='publisher_caption' if s['text_origin']=='linked_publisher_caption' else 'machine_transcript',
            legacy_source_ids=list(filter(None, [sid, a['source_id'], s['publication_id'], s.get('previous_study_source_id')])), priority=20,
            linked_written_artifact_sha256=src.get('linked_written_text', {}).get('sha256')))
    knowledge = module('channel_knowledge', 'research/knowledge-bank/knowledge_sources.py')
    kp = PRIVATE/'knowledge-bank-2026-11/knowledge/frame-01.json'; kd, kf = knowledge.load_frame(kp); inputs.append(artifact(kp))
    for d in kd:
        s=d['record']; medium=s['medium']; sid=s['source_id']; written=s['document_kind']=='publisher_written_message'
        if medium == 'Tracy Kumbera': ctx=TRACY
        elif medium == 'Natalie Glasson': ctx=OMNA
        elif medium == 'Pamela Aaralyn': ctx=context('guest-inspire-nation-show-with-michael-sandler', 'Inspire Nation Show with Michael Sandler — guest context', medium, 'Inspire Nation Show with Michael Sandler', 'https://inspirenation.libsyn.com/')
        else:
            pub = {'Pamela Rose Kribbe':'Jeshua.net', 'Lyssa Royal Holt':'Lyssa Royal Holt / Royal Priest Research', 'Daniel Scranton':'Daniel Scranton'}[medium]
            ctx=context(slug(medium), medium + ' publisher texts', medium, pub, urlunsplit((*urlsplit(s['source_url'])[:2], '/', '', '')))
        extra={}
        if medium == 'Pamela Aaralyn':
            pp=PRIVATE/'council-study-2026-11/media/new-text-manifest.json'; p=read_json(pp)['documents'][0]; inputs.append(artifact(pp))
            extra={'media_artifact':p['audio_artifact'], 'audio_sha256':p['audio_artifact']['sha256'], 'duration_seconds':6897.456}
        editions.append(candidate(sid, d['text'], s['text_artifact'], 'plain_text' if written else 'json_text', 'knowledge25', ctx,
            title=s['title'], source_url=s['source_url'], publication_url=s['source_url'], publication_id=s.get('publication_family_id'),
            document_kind=s['document_kind'], text_origin='publisher_written' if written else 'machine_asr',
            claimed_label=s['claimed_label'], attribution_scope=s['attribution_scope'], coverage_scope=s['text_scope'],
            publication_date=date_value(s['published_at']), publication_date_raw=s['published_at'],
            priority=5 if written else 40, **extra))
    legacy = module('channel_legacy', 'research/transcript-analysis/build.py')
    ld, _ = legacy.get_sources(); ep=ROOT/'research/access-repair/primary-sources/expanded-metadata.json'; expanded=read_json(ep); inputs.append(artifact(ep))
    for d in ld:
        sid=d['sourceId']
        if not (sid.startswith('daniel-item-') or sid.startswith('athina-') or sid=='paul-birmingham-pdf'): continue
        meta={}; puburl=d['sourceUrl']
        if sid.startswith('daniel-item-'):
            item=next(i for i in expanded['daniel']['items'] if i['item_index']==int(sid.rsplit('-',1)[1])); f=item['text']; pubdate=item['publication_timestamp']
            ctx=context('daniel-scranton', 'Daniel Scranton publisher texts', 'Daniel Scranton', 'Daniel Scranton', 'https://danielscranton.com/')
            coverage='Full retained RSS rendition including promotions/footer; overlaps a body-only pilot by publication URL'
        elif sid=='paul-birmingham-pdf':
            f=expanded['paul']['text'];pubdate='2017-07-15';puburl=expanded['paul']['source_link_provenance']['publisher_page_url']
            ctx=context('paul-selig', 'Paul Selig publisher transcript', 'Paul Selig', 'Paul Selig', 'https://paulselig.com/')
            coverage='Four-page publisher transcript extraction; no audio alignment verified'
        else:
            receipt=read_json(ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json');f=next(f for f in receipt['outputs'] if f['name']=='transcript.txt');f={**f,'raw_local_path':str(Path(receipt['transcriptDirectory'])/'transcript.txt')}
            pubdate='2023-02-06T12:29:30+11:00';puburl='https://athinakrol.podbean.com/e/ashtar-live-channelling-meet-your-guides-episode-on-soul-purpose-earth-s-vibrational-shifts/'
            ctx=context('athina-krol', 'Spirit Channel with Athina Król', 'Athina Król', 'Spirit Channel with Athina Król', 'https://athinakrol.podbean.com/')
            coverage='Full decoded audio ASR; recognition accuracy and roles unverified'
            meta={'audio_sha256':d['sourceAudioSha256'], 'media_artifact':{'path':'/workspace/channels-et-raw/primary-audio/'+sid+'.mp3','sha256':d['sourceAudioSha256']}, 'duration_seconds':d['durationSeconds']}
        editions.append(candidate(sid,d['text'],{'path':f['raw_local_path'],'bytes':f['bytes'],'sha256':f['sha256']},'plain_text','legacy_primary17',ctx,
            title=d['title'],source_url=puburl,publication_url=puburl,publication_id=sid,
            document_kind=d['modality'],text_origin='machine_asr' if d['modality']=='audio_asr' else 'publisher_written',
            claimed_label=d['claimedGroup'],coverage_scope=coverage,publication_date=date_value(pubdate),publication_date_raw=pubdate,priority=35,**meta))
    batch=module('channel_batch','research/batch-media/analyze.py')
    pp=next(Path('/workspace/channels-et-raw/batch-2026-11/cloud-archive').glob('*/derived_analysis*/**/provenance-private.json'))
    runs=read_json(pp)['run_inputs'];inputs.append(artifact(pp))
    for r in runs:
        if artifact(r['run_path'])['sha256']!=r['sha256']:raise ValueError('Crimson accepted run changed')
    bd, excluded, aliases, audit=batch.load_documents([r['run_path'] for r in runs]);dispositions+=excluded+aliases
    refs={}; media={}
    for r in runs:
        inputs.append(artifact(r['run_path']))
        for row in read_json(r['run_path'])['records']:
            if row['status']!='completed':continue
            receipt=read_json(row['receipt_path']);refs[row['source_id']]=next(a for a in receipt['verified_artifacts'] if a.get('kind')=='transcript' and Path(a['local_path']).name=='segments.json');media[row['source_id']]=receipt['binding']['source']
    for d in bd:
        s=d['summary'];sid=s['source_id'];f=refs[sid];m=media[sid]
        if not s['english_lexical_eligible']: raise ValueError('Non-English accepted Crimson row')
        editions.append(candidate(sid,d['text'],{'path':f['local_path'],'bytes':f['bytes'],'sha256':f['sha256']},'json_text','crimson10',context('crimson-circle','Crimson Circle — Freedom Series','Geoffrey Hoppe','Crimson Circle','https://www.crimsoncircle.com/'),
            title=s['title'],source_url=s['source_url'],publication_url=s['source_url'],publication_id=sid,
            document_kind='video_asr',text_origin='machine_asr',audio_sha256=s['source_sha256'],media_artifact={'path':m['local_path'],'sha256':m['sha256'],'bytes':m['bytes']},
            duration_seconds=s['decoded_duration_seconds'],publication_date=date_value(s['published_date']),publication_date_raw=s['published_date'],
            claimed_label=s.get('claimed_entity_label'),language_basis=s['english_eligibility_basis'],priority=20))
    return editions, inputs, dispositions


def reconcile(editions):
    parent=list(range(len(editions))); links=[]; keys={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,r in enumerate(editions):
        for field in ('body_sha256','publication_url','publication_id','recording_family_id','audio_sha256'):
            value=r.get(field)
            if not value:continue
            # Legacy publication/family IDs are only guaranteed within a collection.
            # Global byte hashes and explicit individual URLs provide cross-context joins.
            key=(field, r['channel_id'], value) if field in {'publication_id','recording_family_id'} else (field,value)
            if key in keys:
                j=keys[key];a,b=find(i),find(j)
                if a!=b:parent[a]=b
                links.append({'left_edition_id':editions[j]['edition_id'],'right_edition_id':r['edition_id'],'basis':field,'value':value})
            else:keys[key]=i
    groups=defaultdict(list)
    for i,r in enumerate(editions):groups[find(i)].append(r)
    records=[];alternates=[]
    for members in groups.values():
        members.sort(key=lambda r:(r['priority'],r['edition_id'],r['cohort']));pick=members[0]
        urls=sorted({r['publication_url'] for r in members if r.get('publication_url')})
        # Identity stable against edition changes: publication identity, not selected body.
        key=urls[0] if urls else min(r['edition_id'] for r in members)
        sid='doc-'+sha_bytes(key.encode())[:20]
        r={k:v for k,v in pick.items() if k not in {'priority','cohort','edition_id','legacy_source_ids'}}
        media=next((x for x in members if x.get('media_artifact')),None)
        r.update(source_id=sid,selected_edition_id=pick['edition_id'],cohorts=sorted({x['cohort'] for x in members}),
            legacy_source_ids=sorted({v for x in members for v in x['legacy_source_ids']}),
            publication_urls=urls,edition_count=len({(x['edition_id'],x['text_artifact']['sha256']) for x in members}),
            body_normalization=NORMALIZATION,selection_rule='Lowest declared edition priority: inspected body-only written > linked captions > baseline ASR; original cohort ASR retained for Crimson.',
            speaker_identity_verified=False,audio_alignment_verified=False)
        r['original_contexts']=[{'channel_id':c,'creator_id':cr,'publisher_id':p} for c,cr,p in sorted({(m['channel_id'],m['creator_id'],m['publisher_id']) for m in members})]
        r['cross_context_alias']=len({m['channel_id'] for m in members})>1
        r['claimed_labels']=sorted({m['claimed_label'] for m in members if m.get('claimed_label')})
        if media:
            for k in ('media_artifact','audio_sha256','duration_seconds','recording_family_id'):
                if not r.get(k):r[k]=media.get(k)
        r['media_sha256']=r.get('audio_sha256')
        r['media_hash_kind']='encoded_video_file' if r['document_kind']=='video_asr' else 'encoded_audio_file' if media else None
        if r['media_hash_kind']=='encoded_video_file':r['audio_sha256']=None
        r['recording_id']=('media-sha256:' if r['media_hash_kind']=='encoded_video_file' else 'audio-sha256:')+r['media_sha256'] if r.get('media_sha256') else None
        r['media_state']='retained_video' if r['document_kind']=='video_asr' else 'retained_audio' if media else 'not_joined_in_this_frame'
        r['text_state']='available_selected_edition';r['analysis_state']='eligible_frozen_frame'
        r['mask_phrases']=sorted({x for m in members for x in [m['creator_name'],m['channel_name'],m.get('claimed_label')] if x})
        records.append(r)
        seen=set()
        for x in members:
            ek=(x['edition_id'],x['text_artifact']['sha256'])
            if ek in seen:continue
            seen.add(ek)
            alternates.append({'source_id':sid,'edition_id':x['edition_id'],'selected':ek==(pick['edition_id'],pick['text_artifact']['sha256']),
                'cohort':x['cohort'],'text_artifact_sha256':x['text_artifact']['sha256'],'body_sha256':x['body_sha256'],'words':x['words'],
                'text_origin':x['text_origin'],'publication_url':x['publication_url'],'publication_id':x['publication_id'],
                'audio_sha256':None if x['document_kind']=='video_asr' else x['audio_sha256'],
                'media_sha256':x['audio_sha256'],'media_hash_kind':'encoded_video_file' if x['document_kind']=='video_asr' else 'encoded_audio_file' if x['audio_sha256'] else None,
                'claimed_label':x['claimed_label'],'channel_id':x['channel_id'],
                'reason':'Exact publication/body/audio linkage; alternative edition is not an independent observation'})
    records.sort(key=lambda r:(r['channel_id'],r['source_id']))
    for i,r in enumerate(records):r['row_index']=i
    return records,alternates,links


def public_record(r):
    out={k:v for k,v in r.items() if k not in {'text_artifact','media_artifact','body_transform'}}
    out['text_artifact']={k:v for k,v in r['text_artifact'].items() if k!='path'}
    if r.get('media_artifact'):out['media_artifact']={k:v for k,v in r['media_artifact'].items() if k in {'sha256','bytes','role'}}
    return out


def channels(records):
    groups=defaultdict(list)
    for r in records:groups[r['channel_id']].append(r)
    result=[]
    for cid,rows in sorted(groups.items()):
        s=rows[0]; audio=sum(bool(r.get('media_sha256')) for r in rows)
        result.append({'channel_id':cid,'display_name':s['channel_name'],'type':'modeled_publisher_context',
            'creator_names':sorted({r['creator_name'] for r in rows}),'publisher_names':sorted({r['publisher_name'] for r in rows}),
            'publisher_url':s['publisher_url'],'youtube_handle':None,'youtube_url':None,'uploaded_total':None,
            'counts':{'canonical_text_units':len(rows),'selected_words':sum(r['words'] for r in rows),'retained_recording_units_joined':audio,
                'downloaded_youtube_videos':0,'analyzed_text_units':None},
            'count_basis':'Distinct reconciled source units; lifetime uploads unknown; modeling completion is separate analysis output.',
            'coverage_status':'retained_primary_text','source_ids':[r['source_id'] for r in rows]})
    mappings={'subscription-athinakrol':'athina-krol','subscription-magentapixie':'magenta-pixie','subscription-tracykumbera':'tracy-kumbera','subscription-akanksshaa':'multidimensional-soul'}
    for rel in ['first14.json','second14.json']:
        for x in read_json(ROOT/'research/subscription-screening'/rel)['channels']:
            if x['status']!='include':continue
            result.append({'channel_id':x['id'],'display_name':x['name'],'type':'screened_youtube_account_reference',
                'youtube_handle':x['handle'],'youtube_url':x['channel_url'],'uploaded_total':None,
                'linked_publisher_channel_ids':[mappings[x['id']]] if x['id'] in mappings else [],
                'counts':{'downloaded_youtube_videos':0,'canonical_text_units':0,'analyzed_text_units':0},
                'coverage_status':'screened_reference_not_separate_model_observation','source_ids':[],
                'count_basis':'Screening metadata only. Linked publisher records are not proven YouTube editions or added again.'})
    historical=read_json(ROOT/'dist/analysis/data.json')
    with (ROOT/'dist/analysis/caption-documents.csv').open(encoding='utf-8-sig') as stream:
        old_counts=Counter(r['channelId'] for r in csv.DictReader(stream))
    for x in historical['channels']:
        if x['id'] not in old_counts:continue
        result.append({'channel_id':'historical-'+x['id'],'display_name':x['name'],'type':'historical_caption_metadata_only',
            'youtube_url':x['url'],'youtube_handle':None,'uploaded_total':None,'coverage_status':'historical_body_unavailable_excluded_from_new_models',
            'source_ids':[],'counts':{'historical_indexed_uploads':x['videoCount'],'historical_analyzed_caption_documents':old_counts[x['id']],
                'canonical_text_units':0,'analyzed_text_units':0,'downloaded_youtube_videos':0},
            'count_basis':'Historical metadata only; old private caption bodies not retained here. Not lifetime upload totals or new analyses.'})
    return result


def load_frame(frame_path):
    """Return [{record,text}] in frozen row order; verify every selected body."""
    frame=read_json(frame_path); out=[]
    for i,r in enumerate(frame['records']):
        if r['row_index']!=i:raise ValueError('Frame row order changed')
        text=body(r['text_artifact'],r['body_transform'])
        if sha_bytes(text.encode())!=r['body_sha256'] or len(text.split())!=r['words']:raise ValueError('Selected body changed')
        out.append({'record':r,'text':text})
    if len(out)!=frame['coverage']['documents'] or len({d['record']['source_id'] for d in out})!=len(out):raise ValueError('Frame identity/count differs')
    return out


def verify_registry(root):
    """Stdlib-only public release gate. Does not claim to validate unavailable bodies."""
    p=Path(root);p=p/'registry.json' if p.is_dir() else p
    raw=p.read_text();data=json.loads(raw);docs=data['documents'];coverage=data['coverage']
    if any(x in raw for x in ('/workspace/','/dev/shm/','/tmp/','"text":')):raise ValueError('Private path/body leaked')
    ids={r['source_id'] for r in docs}
    if len(ids)!=len(docs) or len(docs)!=coverage['documents']:raise ValueError('Document denominator/identity differs')
    if [r['row_index'] for r in docs]!=list(range(len(docs))):raise ValueError('Row order differs')
    if sum(r['words'] for r in docs)!=coverage['words']:raise ValueError('Word denominator differs')
    if len({r['body_sha256'] for r in docs})!=len(docs):raise ValueError('Exact body duplicate remains')
    if coverage['youtube_uploaded_total'] is not None:raise ValueError('Unknown upload total must remain null')
    channels=data['channels'];cids={c['channel_id'] for c in channels}
    if len(cids)!=len(channels) or any(c['uploaded_total'] is not None for c in channels):raise ValueError('Channel identity/upload-total error')
    if any(r['channel_id'] not in cids for r in docs):raise ValueError('Unknown source channel')
    for c in channels:
        if set(c['source_ids']) != {r['source_id'] for r in docs if r['channel_id']==c['channel_id']}:raise ValueError('Channel membership differs')
    by=defaultdict(list)
    for a in data['alternate_editions']:
        if a['source_id'] not in ids:raise ValueError('Orphan edition')
        by[a['source_id']].append(a)
    for r in docs:
        selected=[a for a in by[r['source_id']] if a['selected']]
        if len(selected)!=1 or selected[0]['edition_id']!=r['selected_edition_id'] or selected[0]['body_sha256']!=r['body_sha256']:raise ValueError('Selected edition differs')
        if not re.fullmatch('[a-f0-9]{64}',r['body_sha256']) or not r['language_eligible']:raise ValueError('Invalid hash/language admission')
        if r['media_hash_kind']=='encoded_video_file' and r['audio_sha256'] is not None:raise ValueError('Video bytes mislabeled audio')
    return {'documents':len(docs),'words':coverage['words'],'channel_rows':len(channels),'status':'passed_public_metadata_checks'}


def build(output):
    output=Path(output)
    if output.exists():raise ValueError('Use a fresh output directory; editions are immutable')
    if not (str(output).startswith('/dev/shm/') or output.resolve().is_relative_to(PRIVATE)):raise ValueError('Private/RAM output required')
    with tempfile.TemporaryDirectory(prefix='channel-lab-load-',dir='/dev/shm') as tmp:
        editions,inputs,dispositions=gather(Path(tmp))
    inputs += [artifact(ROOT/p) for p in ['research/subscription-screening/first14.json','research/subscription-screening/second14.json','dist/analysis/data.json','dist/analysis/caption-documents.csv']]
    records,alternates,links=reconcile(editions)
    coverage={'candidate_edition_rows':len(editions),'documents':len(records),'words':sum(r['words'] for r in records),
        'unique_edition_artifacts':len(alternates),'collapsed_candidate_rows':len(editions)-len(records),
        'modeled_channel_contexts':len({r['channel_id'] for r in records}),
        'candidate_cohort_counts':dict(Counter(r['cohort'] for r in editions)),
        'primary_channel_counts':dict(Counter(r['channel_id'] for r in records)),
        'language_eligible_documents':sum(r['language_eligible'] for r in records),
        'cross_context_exact_alias_groups':sum(r['cross_context_alias'] for r in records),
        'screened_account_references':12,'historical_caption_channel_references':17,'youtube_uploaded_total':None,'youtube_downloads':0}
    frame={'schema_version':'channel-lab-frame-1','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':'All enumerated accepted English retained cohorts; finite convenience frame, not all channel uploads.',
        'coverage':coverage,'inputs':inputs,'records':records,'alternate_editions':alternates,'merge_links':links,
        'upstream_dispositions':dispositions,'source_script_sha256':artifact(__file__)['sha256']}
    public={'schema_version':'channel-lab-registry-1','generated_at':frame['generated_at'],'coverage':coverage,
        'documents':[public_record(r) for r in records],'channels':channels(records),'alternate_editions':alternates,'merge_links':links,
        'upstream_dispositions':dispositions,'input_bindings':[{'sha256':r['sha256'],'bytes':r.get('bytes'),'artifact_name':Path(r['path']).name} for r in inputs],
        'limitations':['English eligibility inherited from named accepted cohorts, not a fresh human language audit.',
            'Source context and printed claimed labels are not authenticated speaker identities.',
            'Exact publication/body/audio aliases are collapsed; unresolved reprints and shared historical sessions may remain.',
            'Full corpus and private paths are not exported. Retention is managed cloud workspace, not permanent ChatGPT storage.',
            'Publications, text editions, source recordings and uploaded YouTube videos are distinct counting units.',
            'Ra linked archival audio is tracked separately upstream; this frame does not assert text-to-audio alignment.',
            'Mask phrases are source-local labels/names, not an exhaustive identity vocabulary.']}
    output.mkdir(parents=True);write_json(output/'frame.json',frame);write_json(output/'registry.json',public)
    load_frame(output/'frame.json')
    verify_registry(output)
    manifest={'schema_version':1,'frame':{**artifact(output/'frame.json'),'file':'frame.json'},
        'public_allowlist':[{k:v for k,v in {**artifact(output/'registry.json'),'file':'registry.json'}.items() if k!='path'}]}
    write_json(output/'output-manifest.json',manifest)
    print(json.dumps({'output':str(output),'coverage':coverage,'frame_sha256':manifest['frame']['sha256']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();build(args.output)
