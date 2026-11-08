#!/usr/bin/env python3
"""Reconcile retained public account references without inventing channel completeness."""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

VIDEO = re.compile(r'^[A-Za-z0-9_-]{11}$')
UC = re.compile(r'^UC[A-Za-z0-9_-]{22}$')
BASHAR = re.compile(r'\bbashar\b|darryl\s+anka', re.I)
TABS = {'videos', 'shorts', 'streams', 'featured', 'about', 'community', 'playlists', 'live'}
SCHEMA = 'youtube-archive-inventory/1'


def sha(data): return hashlib.sha256(data).hexdigest()
def stable(kind, key): return kind + '-' + sha(key.encode())[:20]
def dumps(obj): return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
def unique(items): return sorted(set(x for x in items if x is not None))


def route(url):
    """Literal route identity only: no accent folding, nickname or custom/user alias merge."""
    if not isinstance(url, str): return None
    try:
        p = urlparse(url.strip()); host = (p.hostname or '').lower()
    except ValueError: return None
    if host not in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}: return None
    parts = [unquote(x) for x in p.path.split('/') if x]
    while len(parts) > 1 and parts[-1].lower() in TABS: parts.pop()
    if not parts: return None
    if any(re.search(r'[&=<>?/\\#\s]',part) for part in parts): return None
    if parts[0].startswith('@') and len(parts) == 1 and len(parts[0]) > 1:
        key = 'handle:' + parts[0].lower(); typ = 'handle'; value = parts[0]
    elif len(parts) == 2 and parts[0] == 'channel' and UC.fullmatch(parts[1]):
        key = 'channel:' + parts[1]; typ = 'channel_id'; value = parts[1]
    elif len(parts) == 2 and parts[0] in {'user', 'c'}:
        key = parts[0] + ':' + parts[1].lower(); typ = 'legacy_custom_route'; value = '/'.join(parts)
    elif len(parts) == 1 and parts[0].lower() not in {'watch', 'results', 'playlist', 'feed', 'shorts', 'embed', 'live', 'channel', 'redirect', 'signin'}:
        key = 'legacy:' + parts[0].lower(); typ = 'legacy_custom_route'; value = parts[0]
    else: return None
    return {'key': key, 'type': typ, 'value': value, 'url': 'https://www.youtube.com/' + '/'.join(parts)}


def video_id(url):
    if not isinstance(url, str): return None
    try: p = urlparse(url); host = (p.hostname or '').lower()
    except ValueError: return None
    parts = [x for x in p.path.split('/') if x]
    value = None
    if host in {'youtu.be', 'www.youtu.be'} and parts: value = parts[0]
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'www.youtube-nocookie.com', 'youtube-nocookie.com'}:
        if p.path == '/watch': value = parse_qs(p.query).get('v', [None])[0]
        elif len(parts) >= 2 and parts[0] in {'shorts', 'embed', 'live'}: value = parts[1]
    return value if value and VIDEO.fullmatch(value) else None


def walk_urls(value, pointer=''):
    if isinstance(value, dict):
        for key, child in value.items(): yield from walk_urls(child, pointer + '/' + str(key).replace('~','~0').replace('/','~1'))
    elif isinstance(value, list):
        for i, child in enumerate(value): yield from walk_urls(child, pointer + '/' + str(i))
    elif isinstance(value, str):
        for match in re.finditer(r'https?://[^\s<>"\]\)]+', value):
            yield match.group(0).rstrip('.,;'), pointer


def shared_page_evidence(video_pages, account_pages):
    return bool({p for p in video_pages if p} & {p for p in account_pages if p})


def duration_policy(bashar, durations, included=True, has_account=True):
    vals = sorted(set(float(x) for x in durations if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0))
    minimum = 300 if bashar else 0
    # Zero is a retained missing/unusable-duration cue, not proof of a zero-length upload.
    vals = [v for v in vals if v > 0]
    if not included: status = 'excluded_account'
    elif not has_account: status = 'unassigned_review'
    elif bashar and (not vals or (min(vals) < minimum <= max(vals))): status = 'duration_probe_required'
    elif bashar and max(vals) < minimum: status = 'excluded_duration'
    else: status = 'eligible'
    return {'status': status, 'bashar_attribution': bool(bashar), 'minimum_seconds': minimum,
            'measured_duration_seconds': vals[0] if len(vals) == 1 else None,
            'duration_values': vals, 'count_cap': None,
            'eligibility_kind': 'duration_and_explicit_exclusion_only',
            'content_relevance': 'not_verified_by_inventory',
            'basis': ['historical_metadata_or_publisher_attribution_not_audio_speaker_verification',
                      'Bashar including reposts requires 300 seconds; other material has no duration floor',
                      'Current media duration must be checked before accepting a Bashar download']}


class Inventory:
    def __init__(self, root):
        self.root = Path(root); self.inputs = {}; self.routes = {}; self.videos = {}; self.links = []
        self.bridges = []; self.contexts = {}; self.alias_assertions = []; self.screen = {}; self.historical_routes = {}; self.discovery_summary = None; self.invalid_route_mentions = []; self.publisher_redirect_observations = []

    def read(self, file, lines=False):
        path = Path(file)
        if not path.is_absolute(): path = self.root / path
        raw = path.read_bytes()
        try: label = path.relative_to(self.root).as_posix()
        except ValueError: label = path.name
        sid = stable('input', label + ':' + sha(raw))
        self.inputs[sid] = {'input_id': sid, 'file': label, 'sha256': sha(raw), 'bytes': len(raw),
                            'source_kind': 'retained_artifact', 'new_network_fetch_by_inventory': False}
        return ([json.loads(x) for x in raw.splitlines() if x] if lines else json.loads(raw)), sid

    @staticmethod
    def ref(sid, pointer): return {'input_id': sid, 'locator': pointer}

    def account(self, url, ref, name=None, role=None, include=None, medium=None, labels=None):
        r = route(url)
        if not r: return None
        key = r['key']
        a = self.routes.setdefault(key, {'route': r, 'urls': set(), 'names': set(), 'roles': set(), 'refs': [],
                                          'inclusions': set(), 'mediums': [], 'labels': set(), 'historical_route_ids': set()})
        a['urls'].add(r['url']); a['refs'].append(ref)
        if name: a['names'].add(name)
        if role: a['roles'].add(role)
        if include: a['inclusions'].add(include)
        if medium and medium not in a['mediums']: a['mediums'].append(medium)
        a['labels'].update(labels or [])
        return key

    def video(self, vid, ref, title=None, duration=None, labels=None, status=None):
        if not isinstance(vid, str) or not VIDEO.fullmatch(vid): return None
        v = self.videos.setdefault(vid, {'video_id': vid, 'titles': [], 'duration_observations': [], 'entity_labels': set(),
                                         'source_refs': [], 'historical_metadata_statuses': set(), 'watch_records': [],
                                         'historical_caption_records': []})
        v['source_refs'].append(ref)
        if title and title not in v['titles']: v['titles'].append(title)
        if duration is not None and isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration >= 0:
            item = {'seconds': duration, 'source_ref': ref}
            if item not in v['duration_observations']: v['duration_observations'].append(item)
        v['entity_labels'].update(labels or [])
        if status: v['historical_metadata_statuses'].add(status)
        return v

    def link(self, key, vid, typ, ref):
        if key is not None and vid in self.videos:
            self.links.append({'route_key': key, 'video_id': vid, 'attribution': typ, 'source_ref': ref})

    def scan(self, data, sid):
        for url, pointer in walk_urls(data):
            ref = self.ref(sid, pointer)
            if route(url): self.account(url, ref)
            if video_id(url): self.video(video_id(url), ref)

    def gather(self, discovery=None):
        policy, _ = self.read('research/subscription-screening/collection-policy.json')
        assert policy['minimum_duration_seconds'] == 0 and policy['bashar_minimum_duration_seconds'] == 300
        assert policy['per_channel_count_cap'] is None and policy['jamie_butler_user_excluded'] is True
        prior, sid = self.read('research/harvest/inventory/channel-routes.json')
        for i, x in enumerate(prior['records']):
            ref = self.ref(sid, f'/records/{i}'); key = self.account(x['url'], ref)
            if not key: continue
            self.historical_routes[x['route_id']] = key; self.routes[key]['historical_route_ids'].add(x['route_id'])
            for alias in x.get('explicit_aliases', []):
                self.alias_assertions.append({'route_key':key,'asserted_alias':alias,'source_ref':ref,
                                              'disposition':'not_used_for_identity_merge_without_same_watch_binding'})
        prior, sid = self.read('research/harvest/inventory/videos.jsonl', True)
        for i, x in enumerate(prior):
            ref = self.ref(sid, f'line:{i+1}')
            v = self.video(x['video_id'], ref, x.get('title'), x.get('duration_seconds'), x.get('entity_labels'), x.get('status'))
            for d in x.get('duration_conflict_values', []): self.video(x['video_id'], ref, duration=d)
            v['historical_metadata_statuses'].update(x.get('historical_metadata_statuses', []))
            for rid in x.get('channel_route_ids', []): self.link(self.historical_routes.get(rid), x['video_id'], 'inherited_route_association', ref)
        groups, sid = self.read('research/harvest/inventory/publisher-accounts.json')
        for i, x in enumerate(groups['records']):
            ref = self.ref(sid, f'/records/{i}')
            for rid in x.get('channel_route_ids', []):
                key = self.historical_routes.get(rid)
                if key:
                    self.routes[key]['names'].add(x['name']); self.routes[key]['refs'].append(ref)
        watch, sid = self.read('research/analysis/inputs/fresh_metadata.json')
        for i, x in enumerate(watch):
            ref = self.ref(sid, f'/{i}'); vid = x['video_id']
            v = self.video(vid, ref, x.get('title'), x.get('duration_seconds'), status=x.get('status'))
            obs = {k:x.get(k) for k in ['status','retrieved_at','access_type','channel_id','channel_url','publisher','published_at','uploaded_at','html_sha256']}
            obs['source_ref'] = ref; v['watch_records'].append(obs)
            if x.get('status') != 'success' or not UC.fullmatch(x.get('channel_id') or ''): continue
            ck = self.account('https://www.youtube.com/channel/' + x['channel_id'], ref, x.get('publisher'), 'historical_watch_uploader')
            hk = self.account(x.get('channel_url'), ref, x.get('publisher'), 'historical_watch_uploader')
            self.link(ck, vid, 'historical_watch_uploader', ref)
            if hk and hk != ck: self.bridges.append({'a': ck, 'b': hk, 'video_id': vid, 'source_ref': ref, 'observed_at':x.get('retrieved_at')})
        atlas, sid = self.read('dist/analysis/data.json')
        for i, x in enumerate(atlas['channels']):
            ref = self.ref(sid, f'/channels/{i}')
            urls = unique([x.get('url')] + x.get('aliases', []))
            for url in urls:
                key = self.account(url, ref, x.get('name'), x.get('relationship'))
                if key:
                    self.alias_assertions.append({'route_key':key,'asserted_aliases':urls,'source_ref':ref,
                                                  'disposition':'atlas_group_membership_not_used_as_verified_channel_identity'})
        # Caption analyses are historical references; absent original bodies are not newly retained transcripts.
        import csv, io
        path = 'dist/analysis/caption-documents.csv'; raw = (self.root / path).read_bytes()
        sid = stable('input', path + ':' + sha(raw)); self.inputs[sid]={'input_id':sid,'file':path,'sha256':sha(raw),'bytes':len(raw),'source_kind':'retained_artifact','new_network_fetch_by_inventory':False}
        for i, row in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))):
            vid = next((v for k,v in row.items() if k in {'video_id','videoId','id'} and VIDEO.fullmatch(v or '')), None)
            if vid in self.videos: self.videos[vid]['historical_caption_records'].append({'source_ref':self.ref(sid,f'row:{i+1}'),'retention':'historical_analysis_reference_body_not_retained_here'})
        for file in ['research/subscription-screening/first14.json','research/subscription-screening/second14.json']:
            data, sid = self.read(file)
            for i, x in enumerate(data['channels']):
                ref = self.ref(sid, f'/channels/{i}'); key = self.account(x['channel_url'], ref, x['name'], x.get('research_category'), 'included_screened' if x['status']=='include' else 'excluded',
                    x.get('medium_attribution'), x.get('claimed_entities'))
                self.screen[key]={'status':x['status'],'reason':x['status_reason'],'research_category':x.get('research_category'),'source_ref':ref}
            self.scan(data, sid)
        data, sid = self.read('dist/subscription-audit/data.json')
        mapping = {x['id']:route(x['channel_url'])['key'] for x in data['channels'] if route(x.get('channel_url'))}
        for i,x in enumerate(data['videos']):
            ref=self.ref(sid,f'/videos/{i}'); self.video(x['video_id'],ref,x.get('title'),x.get('duration_seconds'))
            for d in x.get('duration_conflict_values',[]): self.video(x['video_id'],ref,duration=d)
            self.link(mapping.get(x.get('channel_id')),x['video_id'],'screening_route_association',ref)
        data, sid = self.read('research/youtube/focus.json'); mapping={}
        for i,x in enumerate(data['accounts']):
            mapping[x['id']]=self.account(x['url'],self.ref(sid,f'/accounts/{i}'),x.get('title'),x.get('relationship'),'included_research',labels=x.get('entityLabels'))
        for i,x in enumerate(data['videos']):
            vid=video_id(x['url']); ref=self.ref(sid,f'/videos/{i}'); self.video(vid,ref,x.get('title'),labels=x.get('entityLabels'))
            self.link(mapping.get(x.get('accountId')),vid,'research_route_association',ref)
        self.scan(data,sid)
        for file in ['research/expanded-channeling/et-register.json','research/expanded-channeling/traditions-register.json']:
            data,sid=self.read(file); labels={x['id']:x for x in data['channellees']}
            for i,m in enumerate(data['mediums']):
                ref=self.ref(sid,f'/mediums/{i}'); claims=[x for x in data['claims'] if x.get('medium_id')==m['id']]
                label_names=unique(labels[x['channellee_id']]['label'] for x in claims if x.get('channellee_id') in labels)
                cid=stable('context',sid+':'+m['id']); context={'context_id':cid,'legacy_medium_id':m['id'],'name':m['name'],'kind':'source_attributed_medium_context','claimed_labels':label_names,'account_route_keys':[], 'publisher_urls':[], 'source_ref':ref,'identity_truth':'not_authenticated'}
                for j,a in enumerate(m.get('accounts',[])):
                    ar=self.ref(sid,f'/mediums/{i}/accounts/{j}'); key=self.account(a.get('url'),ar,role=a.get('role'),include='included_research',medium={'context_id':cid,'name':m['name'],'basis':'publisher_attribution_not_speaker_authentication'},labels=label_names)
                    if key: context['account_route_keys'].append(key)
                    else: context['publisher_urls'].append(a.get('url'))
                self.contexts[cid]=context
            self.scan(data,sid)
        for file in ['research/council-study/galactic-register.json','research/council-study/contact-register.json','research/subscription-screening/second14-source-inventory.json']:
            data,sid=self.read(file); self.scan(data,sid)
        magenta,sid=self.read('research/subscription-screening/magenta-publisher-video-index.json')
        key=self.account('https://www.youtube.com/@MagentaPixie',self.ref(sid,'/channel_id'),'Magenta Pixie','publisher_linked_collection_context')
        for i,x in enumerate(magenta['videos']):
            ref=self.ref(sid,f'/videos/{i}'); self.video(x['video_id'],ref)
            self.link(key,x['video_id'],'publisher_embed',ref)
        # This context binds a publisher's collection, never upload ownership.
        self.contexts['publisher-magenta-archive']={'context_id':'publisher-magenta-archive','name':'Magenta Pixie publisher video archive','kind':'publisher_embed_collection','publisher_urls':[magenta['seed_url']],'account_route_keys':[key],'claimed_labels':[],'source_ref':self.ref(sid,''),'identity_truth':'embed_is_not_uploader_identity'}
        if discovery:
            baseline_ids = set(self.videos)
            data,sid=self.read(discovery)
            publisher_keys=collections.defaultdict(set)
            publisher_account_pages=collections.defaultdict(set)
            for i,x in enumerate(data.get('account_links',[])):
                ref=self.ref(sid,f'/account_links/{i}'); key=self.account(x.get('url'),ref,role='publisher_linked_route')
                if key:
                    publisher_keys[x['publisher_id']].add(key)
                    publisher_account_pages[(x['publisher_id'],key)].update(e.get('page_url') for e in x.get('evidence',[]))
                else:
                    self.invalid_route_mentions.append({'url':x.get('url'),'source_ref':ref,'disposition':'malformed_or_unsupported_literal_account_route_not_silently_repaired'})
            for i,scope in enumerate(data.get('publisher_scopes',[])):
                pid=scope['publisher_id'];cid='publisher-discovery:'+pid
                self.contexts[cid]={'context_id':cid,'name':pid,'kind':'publisher_embed_collection','publisher_urls':scope.get('seed_urls',[]),'account_route_keys':sorted(publisher_keys[pid]),'claimed_labels':[],'source_ref':self.ref(sid,f'/publisher_scopes/{i}'),'identity_truth':'embed_is_not_uploader_identity','observed_video_ids':[]}
            for i,x in enumerate(data.get('videos',[])):
                vid=x.get('identity') or x.get('video_id'); ref=self.ref(sid,f'/videos/{i}'); self.video(vid,ref)
                video_pages={e.get('page_url') for e in x.get('evidence',[])}
                for key in publisher_keys[x['publisher_id']]:
                    if shared_page_evidence(video_pages, publisher_account_pages[(x['publisher_id'],key)]):
                        self.link(key,vid,'publisher_embed',ref)
                cid='publisher-discovery:'+x['publisher_id']
                context=self.contexts.setdefault(cid,{'context_id':cid,'name':x['publisher_id'],'kind':'publisher_embed_collection','publisher_urls':[],'account_route_keys':sorted(publisher_keys[x['publisher_id']]),'claimed_labels':[],'source_ref':ref,'identity_truth':'embed_is_not_uploader_identity','observed_video_ids':[]})
                context['observed_video_ids'].append(vid)
                context['publisher_urls']=unique(context['publisher_urls']+[e.get('page_url') for e in x.get('evidence',[])])
            html_ids={x.get('identity') or x.get('video_id') for x in data.get('videos',[])}
            redirect_ids=set()
            for i,receipt in enumerate(data.get('page_receipts',[])):
                for j,redirect in enumerate(receipt.get('redirect_chain',[])):
                    vid=video_id(redirect.get('to'))
                    if not vid: continue
                    ref=self.ref(sid,f'/page_receipts/{i}/redirect_chain/{j}')
                    self.video(vid,ref,status='publisher_http_redirect_observed_no_YouTube_request')
                    redirect_ids.add(vid)
                    self.publisher_redirect_observations.append({'video_id':vid,'publisher_id':receipt['publisher_id'],'from_url':redirect.get('from'),'to_url':redirect.get('to'),'http_status':redirect.get('status'),'observed_at':receipt.get('retrieved_at'),'source_ref':ref,'evidence_kind':'HTTP_Location_receipt_not_HTML_body_or_uploader_identity'})
                    cid='publisher-discovery:'+receipt['publisher_id']
                    if cid in self.contexts:self.contexts[cid]['observed_video_ids'].append(vid)
            discovery_ids=html_ids | redirect_ids
            self.discovery_summary={'input_id':sid,'baseline_observed_ids':len(baseline_ids),'distinct_html_embedded_ids':len(html_ids),'distinct_http_redirect_video_ids':len(redirect_ids),'distinct_publisher_observed_ids':len(discovery_ids),'added_to_this_inventory_ids':len(discovery_ids-baseline_ids),'overlap_with_retained_baseline_ids':len(discovery_ids & baseline_ids),'uploader_identity_established':False,'publisher_counts':data.get('counts'),'youtube_downloads_by_discovery':0}
        return self

    def reconcile(self):
        # Only a historical same-watch response can bridge a literal account route to a UC identity.
        destinations=collections.defaultdict(set)
        for b in self.bridges: destinations[b['b']].add(b['a'])
        assignment={k:k for k in self.routes}; identity_links=[]
        for b in self.bridges:
            ok=len(destinations[b['b']])==1 and not b['b'].startswith('channel:')
            if ok: assignment[b['b']]=b['a']
            identity_links.append({**b,'status':'accepted_historical_same_watch_binding' if ok else 'conflicting_or_distinct_uc_identity_not_merged'})
        groups=collections.defaultdict(list)
        for key,canonical in assignment.items(): groups[canonical].append(key)
        key_to_id={key:('yt-'+canonical.split(':',1)[1] if canonical.startswith('channel:') else stable('yt-route',canonical)) for key,canonical in assignment.items()}
        accounts=[]; byid={}
        for canonical,keys in sorted(groups.items()):
            rows=[self.routes[k] for k in keys]; aid=key_to_id[canonical]; screenings=[self.screen[k] for k in keys if k in self.screen]
            names=unique(n for row in rows for n in row['names']); roles=unique(n for row in rows for n in row['roles']); inclusions=set(i for r in rows for i in r['inclusions'])
            excluded=any(x['status']=='exclude' for x in screenings)
            status='excluded' if excluded else ('included_screened' if 'included_screened' in inclusions else ('included_research' if 'included_research' in inclusions else 'candidate_unreviewed'))
            reason='; '.join(unique(x['reason'] for x in screenings)) if screenings else ('Explicit retained research account reference; current uploads not enumerated.' if status=='included_research' else 'Inherited research candidate; account-wide content relevance has not been established.')
            # A mixed/repost publisher does not inherit a blanket threshold from a claimed label.
            bashar_account=any(BASHAR.search(s) for s in names+[r['route']['value'] for r in rows]) and 'reposter' not in roles
            a={'account_id':aid,'channel_id':canonical[8:] if canonical.startswith('channel:') else None,
               'handles':unique(r['route']['value'] for r in rows if r['route']['type']=='handle'),
               'urls':unique(u for r in rows for u in r['urls']),'display_name':names[0] if names else rows[0]['route']['value'], 'name_variants':names,
               'identity_status':'historical_watch_channel_id_and_aliases' if canonical.startswith('channel:') and any(b['a']==canonical for b in self.bridges) else ('literal_channel_id_reference' if canonical.startswith('channel:') else 'unresolved_literal_route'),
               'roles':roles,'medium_attributions':[m for r in rows for m in r['mediums']], 'claimed_labels':unique(n for r in rows for n in r['labels']),
               'inclusion_status':status,'inclusion_reason':reason,'screening':screenings,
               'new_upload_scope_review_required': status == 'candidate_unreviewed',
               'duration_policy':{'minimum_seconds':300 if bashar_account else 0,'bashar_item_minimum_seconds':300,'count_cap':None},
               'source_refs':dedup_refs([ref for r in rows for ref in r['refs']]),
               'legacy_route_ids':unique(x for r in rows for x in r['historical_route_ids']),
               'uploaded_total':None,'all_uploads_are_channeling':False,'observed_video_ids':[],
               'tabs':{tab:{'enumeration_status':'not_enumerated','continuation_exhausted':False,'reported_total':None} for tab in ['videos','shorts','streams']},
               'counts':{'observed_associated_video_ids':0,'historically_verified_uploader_video_ids':0,'newly_downloaded_video_ids':0,'newly_transcribed_video_ids':0,'newly_analyzed_video_ids':0}}
            accounts.append(a); byid[aid]=a
        merged_links={}
        for x in self.links:
            aid=key_to_id[x['route_key']]; key=(aid,x['video_id'],x['attribution'])
            link=merged_links.setdefault(key,{'account_id':aid,'video_id':x['video_id'],'attribution':x['attribution'],'source_refs':[]})
            link['source_refs'].append(x['source_ref'])
        links=[]; associations=collections.defaultdict(set); uploaders=collections.defaultdict(set); allsets=collections.defaultdict(set); uploadsets=collections.defaultdict(set)
        for key,link in sorted(merged_links.items()):
            link['source_refs']=dedup_refs(link['source_refs']); links.append(link); aid,vid,typ=key
            associations[vid].add(aid); allsets[aid].add(vid)
            if typ=='historical_watch_uploader': uploaders[vid].add(aid); uploadsets[aid].add(vid)
        videos=[]
        for vid,v in sorted(self.videos.items()):
            aids=sorted(associations[vid]); ups=sorted(uploaders[vid]); relevant_ids=ups if len(ups)==1 else aids
            included=any(byid[a]['inclusion_status']!='excluded' for a in relevant_ids)
            bashar=any(BASHAR.search(t) for t in v['titles']+list(v['entity_labels'])) or any(byid[a]['duration_policy']['minimum_seconds']==300 for a in relevant_ids)
            durs=[x['seconds'] for x in v['duration_observations']]
            policy=duration_policy(bashar,durs,included=included if relevant_ids else True,has_account=bool(aids))
            videos.append({'video_id':vid,'source_url':'https://www.youtube.com/watch?v='+vid,'title':v['titles'][0] if v['titles'] else None,
                           'title_variants':v['titles'],'duration_seconds':policy['measured_duration_seconds'],'duration_observations':v['duration_observations'],
                           'entity_labels':sorted(v['entity_labels']),'associated_account_ids':aids,'verified_uploader_account_id':ups[0] if len(ups)==1 else None,
                           'uploader_status':'historical_watch_uploader' if len(ups)==1 else ('conflicting_historical_uploader' if ups else 'unknown'),
                           'source_refs':dedup_refs(v['source_refs']),'historical_metadata_statuses':sorted(v['historical_metadata_statuses']),
                           'historical_watch_observations':v['watch_records'],'historical_caption_records':v['historical_caption_records'],
                           'current_access_status':'not_attempted_by_inventory','media_state':'not_downloaded_by_this_inventory',
                           'text_state':'historical_caption_analysis_reference_only' if v['historical_caption_records'] else 'not_established_by_inventory',
                           'speaker_identity':'unknown_not_audio_verified','known_item_scope':'retained_research_reference_not_verified_content','policy_decision':policy})
        for a in accounts:
            aid=a['account_id']; a['observed_video_ids']=sorted(allsets[aid]);a['counts']['observed_associated_video_ids']=len(allsets[aid]);a['counts']['historically_verified_uploader_video_ids']=len(uploadsets[aid])
            a['counts']['policy_eligible_associated_video_ids']=sum(v['policy_decision']['status']=='eligible' for v in videos if aid in v['associated_account_ids'])
        contexts=[]
        for c in self.contexts.values():
            c=dict(c); c['account_ids']=unique(key_to_id[k] for k in c.pop('account_route_keys') if k in key_to_id)
            if 'observed_video_ids' in c:c['observed_video_ids']=unique(c['observed_video_ids'])
            contexts.append(c)
        identity_links=[{**{k:v for k,v in x.items() if k not in {'a','b'}},'channel_account_id':key_to_id[x['a']], 'observed_route':self.routes[x['b']]['route']['url'], 'route_account_id':key_to_id[x['b']]} for x in identity_links]
        aliases=[]
        for x in self.alias_assertions:
            item=dict(x);item['account_id']=key_to_id[item.pop('route_key')];aliases.append(item)
        return {'schema_version':SCHEMA,'generated_from':'retained historical artifacts; optional separately bound publisher discovery',
                'policy':{'count_cap':None,'minimum_duration_seconds':0,'bashar_minimum_duration_seconds':300,'jamie_butler_excluded':True,'audio_first':True,
                          'unknown_duration':'Retain in inventory; Bashar needs duration probe before acceptance.', 'candidate_scope':'Candidate accounts may be enumerated for research; all uploads are not asserted to be channeling.',
                          'observed_inventory_is_complete_census':False},
                'publisher_discovery_join':self.discovery_summary,'publisher_redirect_observations':self.publisher_redirect_observations,
                'accounts':accounts,'videos':videos,'account_video_links':links,'identity_links':identity_links,'publisher_contexts':contexts,
                'unresolved_references':aliases,'invalid_route_mentions':self.invalid_route_mentions,'inputs':sorted(self.inputs.values(),key=lambda x:x['file']),
                'coverage':{'accounts':len(accounts),'literal_routes':len(self.routes),'unique_observed_video_ids':len(videos),
                            'historically_verified_uploader_video_ids':sum(v['uploader_status']=='historical_watch_uploader' for v in videos),
                            'accounts_by_inclusion':dict(collections.Counter(a['inclusion_status'] for a in accounts)),
                            'videos_by_policy':dict(collections.Counter(v['policy_decision']['status'] for v in videos)),
                            'screened_routes':len(self.screen),'screened_included_routes':sum(x['status']=='include' for x in self.screen.values()),
                            'screened_excluded_routes':sum(x['status']=='exclude' for x in self.screen.values()),
                            'observed_lifetime_upload_total':None,'new_downloads_by_inventory':0,'new_transcripts_by_inventory':0,'new_channel_enumerations_by_inventory':0},
                'limitations':['Historical watch metadata can establish historical account identity but not current access or a complete upload census.',
                    'Publisher embeds and inherited route associations do not verify uploader ownership. Per-account associated-ID counts overlap.',
                    'A same-medium claim, matching name, shared claimed entity, or publisher account group is not an account identity join.',
                    'Only observed references are indexed. Videos/shorts/streams pagination remains unknown until a separately recorded successful enumeration.',
                    'Historical caption analyses are references; this inventory does not claim the source captions are retained or freshly analyzed.',
                    'Per-video states describe this inventory operation; other non-YouTube publisher audio archives remain separate acquisition collections.']}


def dedup_refs(items):
    return [json.loads(s) for s in sorted(set(json.dumps(x,sort_keys=True,ensure_ascii=False) for x in items))]


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--output',type=Path,required=True);p.add_argument('--discovery',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if (a.output/'inventory.json').exists(): raise SystemExit('Refusing to overwrite a frozen inventory edition')
    obj=Inventory(a.root).gather(a.discovery).reconcile(); raw=dumps(obj);(a.output/'inventory.json').write_bytes(raw)
    manifest={'schema_version':1,'producer':'research/youtube-archive/inventory.py','producer_sha256':sha(Path(__file__).read_bytes()),'public_allowlist':[{'file':'inventory.json','bytes':len(raw),'sha256':sha(raw)}]}
    (a.output/'output-manifest.json').write_bytes(dumps(manifest)); print(json.dumps({'output':str(a.output),'sha256':sha(raw),'bytes':len(raw),'coverage':obj['coverage']}))
if __name__=='__main__':main()
