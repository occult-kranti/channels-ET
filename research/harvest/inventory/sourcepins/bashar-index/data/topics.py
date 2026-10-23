#!/usr/bin/env python3
"""Topic analysis over the Bashar digest corpus.
Outputs: /home/claude/bashar/analysis/analysis.json and videos.json
"""
import json, glob, re, collections, math, os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans

R = '/home/claude/bashar/research'
OUT = '/home/claude/bashar/analysis'
RNG = 42

TAGS = ["formula_excitement","beliefs_emotions_fear","parallel_realities_shifting","physical_vs_higher_mind",
"permission_slips_tools","et_contact_disclosure_2027","essassani_hybrids_other_civilizations","earth_shift_timelines_ascension",
"abundance_money_career","relationships_family_sexuality","health_body_healing_death","time_simultaneity_reincarnation",
"channeling_mechanics_darryl","consciousness_oversoul_higherself","synchronicity_dreams_meditation","politics_society_economy_ai",
"physics_energy_frequency_dimensions","spirituality_god_love_service","ancient_history_atlantis_orion_sirius","misc_life_guidance"]
TAG_LABEL = {
"formula_excitement":"Follow your excitement / The Formula",
"beliefs_emotions_fear":"Beliefs, emotions & fear",
"parallel_realities_shifting":"Parallel realities & shifting",
"physical_vs_higher_mind":"Physical mind vs higher mind",
"permission_slips_tools":"Permission slips & tools",
"et_contact_disclosure_2027":"ET contact, disclosure & 2027",
"essassani_hybrids_other_civilizations":"Essassani, hybrids & other civilizations",
"earth_shift_timelines_ascension":"Earth's shift, timelines & ascension",
"abundance_money_career":"Abundance, money & career",
"relationships_family_sexuality":"Relationships, family & sexuality",
"health_body_healing_death":"Health, body, healing & death",
"time_simultaneity_reincarnation":"Time, simultaneity & reincarnation",
"channeling_mechanics_darryl":"Channeling mechanics & Darryl",
"consciousness_oversoul_higherself":"Consciousness, oversoul & higher self",
"synchronicity_dreams_meditation":"Synchronicity, dreams & meditation",
"politics_society_economy_ai":"Politics, society, economy & AI",
"physics_energy_frequency_dimensions":"Energy, frequency & dimensions",
"spirituality_god_love_service":"Spirituality, God, love & service",
"ancient_history_atlantis_orion_sirius":"Ancient history: Atlantis, Orion, Sirius",
"misc_life_guidance":"Practical life guidance (misc)"}

# ---------- load ----------
manifest = {}
for fn in ['manifests/official_videos.jsonl','manifests/full_sessions.jsonl','manifests/podcast_videos.jsonl']:
    for line in open(os.path.join(R,fn)):
        line=line.strip()
        if not line: continue
        o=json.loads(line)
        manifest.setdefault(o['video_id'],{}).update({k:v for k,v in o.items() if v not in (None,'')})
podcasts = json.load(open(os.path.join(R,'manifests/podcasts.json')))
pod_by_vid = {}
for p in podcasts:
    u = p.get('youtube_url') or ''
    m = re.search(r'v=([A-Za-z0-9_-]{11})', u)
    if m: pod_by_vid[m.group(1)] = p

digests = []
for f in sorted(glob.glob(os.path.join(R,'digests/*.json'))):
    d = json.load(open(f)); digests.append(d)

def clean_title(t):
    t = re.sub(r'\[(Full|FULL|NEW|Full Episode)\]\s*','',t)
    t = re.sub(r'#1080p','',t)
    t = re.sub(r'\|\s*Bashar - Darryl Anka \d{4} Full Episode.*$','',t)
    t = re.sub(r'\|\|.*$','',t)
    t = re.sub(r'\s+',' ',t).strip(' |-')
    return t

def parse_year(d):
    """Return (year, reliable:boolean, basis)"""
    note = ' '.join(str(d.get(k,'')) for k in ('researcher_note','notes','digest_note','topic_percentages_note'))
    unreliable = bool(re.search(r'unreliable|older session|circa|re-?upload of a much older|likely an older|2016 material|not the date', note, re.I))
    sde = str(d.get('session_date_or_event') or '')
    vid = d['video_id']
    if vid in pod_by_vid and pod_by_vid[vid].get('date'):
        mp = re.search(r'(19[89]\d|20[0-2]\d)', str(pod_by_vid[vid]['date']))
        if mp:
            return int(mp.group(1)), True, 'podcast episode date'
    m = re.search(r'(19[89]\d|20[0-2]\d)', sde)
    if m and not unreliable and not re.search(r'title says|per title|title:', sde, re.I):
        return int(m.group(1)), True, 'stated in session'
    man = manifest.get(vid,{})
    for k in ('upload_date','session_date'):
        if man.get(k):
            mm = re.search(r'(19[89]\d|20[0-2]\d)', str(man[k]))
            if mm and not unreliable:
                return int(mm.group(1)), True, k
    if m:
        return int(m.group(1)), False, 'title date (unreliable)'
    return None, False, 'unknown'

def content_type(d):
    vid = d['video_id']; man = manifest.get(vid,{})
    fmt = d.get('format','')
    ch = (man.get('channel') or d.get('author') or '')
    official = man.get('official_channel') or ch.strip().lower() in ('bashar channeled by darryl anka','bashar communications')
    if fmt == 'interview with Darryl Anka' or vid in pod_by_vid:
        return 'Interview with Darryl Anka'
    if official:
        return 'Official highlight clip'
    if d.get('approx_word_count',0) >= 8000:
        return 'Full session (re-upload)'
    return 'Clip / excerpt'

TERM_NORMALIZE = [
 (r'\bpermission slips?\b','permission_slip'),
 (r'\bhigher minds?\b','higher_mind'),
 (r'\bphysical minds?\b','physical_mind'),
 (r'\bhigher self\b','higher_self'),
 (r'\bparallel (realit(?:y|ies)|earths?|versions?)\b','parallel_reality'),
 (r'\bhighest excitement\b','highest_excitement'),
 (r'\bstate of being\b','state_of_being'),
 (r'\bhybrid (children|kids|races?|civilizations?)\b','hybrid_children'),
 (r'\bopen contact\b','open_contact'),
 (r'\bfirst contact\b','first_contact'),
 (r'\bcontact fulcrum\b','contact_fulcrum'),
 (r'\bcore beliefs?\b','core_belief'),
 (r'\bfive laws\b','five_laws'),
 (r'\ball that is\b','all_that_is'),
 (r'\bstory tree\b','story_tree'),
 (r'\bfear[- ]based beliefs?\b','fear_based_belief'),
 (r'\bfree will\b','free_will'),
 (r'\bcollective consciousness\b','collective_consciousness'),
 (r'\bpositive synchronicit(?:y|ies)\b','positive_synchronicity'),
 (r'\bnegative synchronicit(?:y|ies)\b','negative_synchronicity'),
 (r'\bfollow(?:ing)? your excitement\b','follow_your_excitement'),
 (r'\bthe formula\b','the_formula'),
 (r'\bthe shift\b','the_shift'),
 (r'\bnew earth\b','new_earth'),
 (r'\bfourth density\b','fourth_density'),
 (r'\bthird density\b','third_density'),
 (r'\bpast li(?:fe|ves)\b','past_life'),
 (r'\bnear[- ]death\b','near_death'),
 (r'\bsocial experiment\b','social_experiment'),
 (r'\binterstellar alliance\b','interstellar_alliance'),
 (r'\bsacred circuitry\b','sacred_circuitry'),
 (r'\bvortex array\b','vortex_array'),
 (r'\bzero point\b','zero_point'),
 (r'\bunconditional love\b','unconditional_love'),
 (r'\bartificial intelligence\b','ai'),
 (r'\bgovernments?\b','government'),
 (r'\bextraterrestrials?\b','extraterrestrial'),
 (r'\bsynchronicities\b','synchronicity'),
 (r'\bbeliefs\b','belief'), (r'\bdefinitions\b','definition'), (r'\brealities\b','reality'),
 (r'\bvibrations\b','vibration'), (r'\bfrequencies\b','frequency'), (r'\bcivilizations\b','civilization'),
 (r'\btimelines\b','timeline'), (r'\bcycles\b','cycle'), (r'\bsouls\b','soul'), (r'\bhybrids\b','hybrid'),
]
def normalize(text):
    t = text.lower()
    for pat,rep in TERM_NORMALIZE:
        t = re.sub(pat, rep, t)
    return t

def doc_text(d):
    parts = [clean_title(d['title'])]*2
    parts.append(d.get('opening_summary',''))
    for q in d.get('qa_topics',[]) or []:
        parts.append(q.get('question','')); parts.append(q.get('answer_gist',''))
    w = {'high':3,'medium':2,'low':1}
    for kt in d.get('key_terms',[]) or []:
        parts += [kt.get('term','')]*w.get(kt.get('freq','low'),1)
    def s(x):
        if isinstance(x, dict): return ' '.join(str(v) for v in x.values())
        return str(x)
    parts += [s(x) for x in (d.get('tools_or_exercises',[]) or [])]
    parts += [s(x) for x in (d.get('named_entities',[]) or [])]
    return '|||'.join(normalize(s(p)) for p in parts)

STOP = set(ENGLISH_STOP_WORDS) | {'bashar','darryl','anka','question','questioner','audience','person','people','thing','things','like','really','just','way','okay','yes','session','video','clip','transcript','interview','says','said','host','ask','asks','asked','answer','explains','explain','discusses','discussion','talk','talks','describes','channel','channeled','channeling','channeler','episode','highlights','full','part','new','year','years','world','life','human','humans','humanity','earth','experience','experiences','time','make','makes','let','know','need','want','use','say','doesn','don','isn','way','one','also','simply','idea','ideas','sense','create','creates','creating','creation','reality','realities'}

docs = []
videos = []
for d in digests:
    y, rel, basis = parse_year(d)
    vid = d['video_id']; man = manifest.get(vid,{})
    ct = content_type(d)
    videos.append({
        'video_id': vid,
        'title': clean_title(d['title']),
        'raw_title': d['title'],
        'url': man.get('url') or d.get('url') or f'https://www.youtube.com/watch?v={vid}',
        'channel': man.get('channel') or d.get('author') or '',
        'official': bool(man.get('official_channel')) or (man.get('channel','').lower()=='bashar channeled by darryl anka'),
        'content_type': ct,
        'format': d.get('format'),
        'year': y, 'year_reliable': rel, 'year_basis': basis,
        'session_date_or_event': d.get('session_date_or_event'),
        'approx_word_count': d.get('approx_word_count'),
        'opening_summary': d.get('opening_summary'),
        'qa_topics': d.get('qa_topics') or [],
        'topic_percentages': d.get('topic_percentages'),
        'key_terms': d.get('key_terms') or [],
        'quotes': [q for q in (d.get('quotes') or []) if len(str(q.get('quote','')).split())<=32][:8],
        'predictions_and_dates': d.get('predictions_and_dates') or [],
        'tools_or_exercises': d.get('tools_or_exercises') or [],
        'named_entities': d.get('named_entities') or [],
        'researcher_note': d.get('researcher_note') or d.get('notes') or d.get('digest_note') or '',
        'show': pod_by_vid.get(vid,{}).get('show') or man.get('show') or '',
        'podcast_date': pod_by_vid.get(vid,{}).get('date'),
    })
    docs.append(doc_text(d))

N = len(docs)
print('docs', N)

# ---------- TF-IDF (custom analyzer: n-grams only within segments) ----------
tokre = re.compile(r"[a-z_][a-z_']{2,}")
def analyzer(doc):
    out=[]
    for seg in doc.split('|||'):
        toks=[t for t in tokre.findall(seg) if t not in STOP]
        out+=toks; out+=[a+' '+b for a,b in zip(toks,toks[1:])]
    return out
vec = TfidfVectorizer(analyzer=analyzer, min_df=2, max_df=0.8, sublinear_tf=True)
X = vec.fit_transform(docs)
terms = np.array(vec.get_feature_names_out())
print('vocab', X.shape)

# ---------- Clustering 1: session archetypes from topic mix ----------
TPm = np.array([[v['topic_percentages'].get(t,0) for t in TAGS] for v in videos], float)
TPm = TPm / TPm.sum(1, keepdims=True) * 100
F = np.sqrt(TPm)
arch_search={}
best=None
for kk in range(3,8):
    km_ = KMeans(kk, n_init=50, random_state=RNG).fit(F)
    s_ = silhouette_score(F, km_.labels_)
    arch_search[kk]={'silhouette':round(float(s_),3),'sizes':np.bincount(km_.labels_,minlength=kk).tolist()}
    if kk==5: best=(s_,kk,km_.labels_)
sil,k,labels = best   # k=5 chosen: best balance of separation (sil≈0.35) and interpretability; k=6/7 only split off 2–3-doc clusters
print('archetype k', k, 'sil', round(float(sil),3), arch_search)

# ---------- Clustering 2 (diagnostic): vocabulary-only KMeans on TF-IDF ----------
from sklearn.preprocessing import normalize as l2n
text_search={}
for kk in range(4,8):
    km_ = KMeans(kk, n_init=30, random_state=RNG).fit(l2n(X))
    text_search[kk]={'silhouette':round(float(silhouette_score(X, km_.labels_, metric='cosine')),3),'sizes':np.bincount(km_.labels_,minlength=kk).tolist()}
print('text-only clustering', text_search)

clusters=[]
for c in range(k):
    members=[i for i in range(N) if labels[i]==c]
    cen = np.asarray(X[members].mean(0)).ravel()
    top = [terms[j].replace('_',' ') for j in cen.argsort()[::-1][:12]]
    tagmean = {t: float(np.mean([TPm[i][TAGS.index(t)] for i in members])) for t in TAGS}
    toptags = sorted(tagmean.items(), key=lambda x:-x[1])[:5]
    types = collections.Counter(videos[i]['content_type'] for i in members)
    # order members by distance to centroid in F space
    cF = F[members].mean(0); members.sort(key=lambda i: float(((F[i]-cF)**2).sum()))
    clusters.append({'id': c, 'top_terms': top, 'size': len(members), 'members': [videos[i]['video_id'] for i in members],
                     'top_tags': [{'tag':t,'label':TAG_LABEL[t],'mean_pct':round(v,1)} for t,v in toptags],
                     'content_types': dict(types), 'mean_words': int(np.mean([videos[i]['approx_word_count'] or 0 for i in members]))})
# name archetypes from their dominant tags
def name_cluster(c):
    t0=c['top_tags'][0]['tag']; t1=c['top_tags'][1]['tag']; p0=c['top_tags'][0]['mean_pct']
    if c['size']>=N*0.4: return 'The long-form mix (full sessions & interviews)'
    names={'et_contact_disclosure_2027':'Contact & disclosure','beliefs_emotions_fear':'Belief work, the Formula & tools',
           'physical_vs_higher_mind':'Mind, parallel realities & time','parallel_realities_shifting':'Mind, parallel realities & time',
           'essassani_hybrids_other_civilizations':'Other civilizations & cosmology','time_simultaneity_reincarnation':'Mind, parallel realities & time',
           'consciousness_oversoul_higherself':'Consciousness & the higher self','formula_excitement':'Belief work, the Formula & tools'}
    return names.get(t0, TAG_LABEL[t0])
for c in clusters: c['name']=name_cluster(c)
# ensure unique names
seen=collections.Counter()
for c in clusters:
    seen[c['name']]+=1
    if seen[c['name']]>1: c['name']+=f" ({seen[c['name']]})"

# ---------- 2-D map ----------
svd = TruncatedSVD(n_components=min(30, N-1), random_state=RNG)
Z = svd.fit_transform(X)
try:
    tsne = TSNE(n_components=2, perplexity=8, metric='cosine', init='pca', random_state=RNG, learning_rate='auto')
    P2 = tsne.fit_transform(Z)
    map_method='t-SNE (perplexity 8, cosine) over 30-d LSA of TF-IDF vocabulary'
except Exception as e:
    print('tsne failed', e)
    P2 = PCA(2, random_state=RNG).fit_transform(Z); map_method='PCA(2) over LSA'
P2 = (P2 - P2.min(0)) / (P2.max(0)-P2.min(0)+1e-9)

# ---------- per-doc top terms ----------
for i,v in enumerate(videos):
    row = X[i].toarray().ravel()
    top = row.argsort()[::-1][:10]
    v['top_tfidf_terms'] = [terms[j].replace('_',' ') for j in top if row[j]>0]
    v['cluster'] = int(labels[i])
    v['map_xy'] = [round(float(P2[i,0]),4), round(float(P2[i,1]),4)]

# ---------- topic share aggregates ----------
wc = np.array([v['approx_word_count'] or 1000 for v in videos], dtype=float)
TP = np.array([[v['topic_percentages'].get(t,0) for t in TAGS] for v in videos], dtype=float)
TP = TP / TP.sum(1, keepdims=True) * 100
overall_w = (TP * wc[:,None]).sum(0) / wc.sum()
overall_u = TP.mean(0)
share_overall = [{'tag':t,'label':TAG_LABEL[t],'weighted_pct':round(float(overall_w[i]),1),'unweighted_pct':round(float(overall_u[i]),1),
                  'docs_with_10pct': int((TP[:,i]>=10).sum()), 'docs_present': int((TP[:,i]>0).sum())} for i,t in enumerate(TAGS)]
share_overall.sort(key=lambda x:-x['weighted_pct'])

def group_share(mask):
    if mask.sum()==0: return None
    w = wc[mask]; m = (TP[mask]*w[:,None]).sum(0)/w.sum()
    return {t: round(float(m[i]),1) for i,t in enumerate(TAGS)}
by_type = {}
for ct in sorted(set(v['content_type'] for v in videos)):
    mask = np.array([v['content_type']==ct for v in videos])
    by_type[ct] = {'n': int(mask.sum()), 'share': group_share(mask)}
by_year = {}
years = [v['year'] for v in videos]
for y in sorted(set(y for y in years if y)):
    mask = np.array([(v['year']==y and v['year_reliable']) for v in videos])
    if mask.sum()>=3:
        by_year[str(y)] = {'n': int(mask.sum()), 'share': group_share(mask)}
# era buckets for reliable-year docs
def era(y):
    if y is None: return None
    if y<=2019: return '≤2019'
    if y<=2023: return '2020–2023'
    return '2024–2026'
by_era={}
for e in ['≤2019','2020–2023','2024–2026']:
    mask = np.array([(era(v['year'])==e and v['year_reliable']) for v in videos])
    if mask.sum()>=3: by_era[e] = {'n': int(mask.sum()), 'share': group_share(mask)}

# ---------- key term frequency ----------
W8 = {'high':3,'medium':2,'low':1}
tf = collections.Counter(); df = collections.Counter()
for v in videos:
    seen=set()
    for kt in v['key_terms']:
        t = re.sub(r'\s+',' ', str(kt.get('term','')).strip().lower().strip('"\'.'))
        t = re.sub(r'^(the|a|an) ','',t)
        if not t or len(t)<3: continue
        tf[t]+=W8.get(kt.get('freq','low'),1)
        if t not in seen: df[t]+=1; seen.add(t)
term_table = [{'term':t,'docs':df[t],'weighted':tf[t]} for t in df]
term_table.sort(key=lambda x:(-x['docs'],-x['weighted']))
term_table = term_table[:80]

# ---------- named entities & tools ----------
ent = collections.Counter(); ent_docs=collections.Counter()
ENT_ALIAS = {'sassani':'Sassani/Essassani','essassani':'Sassani/Essassani',"e'sassani":'Sassani/Essassani','essassani (sassani)':'Sassani/Essassani',
 'greys':'Greys/Zeta','grays':'Greys/Zeta','zeta reticuli':'Greys/Zeta','zetas':'Greys/Zeta','zeta':'Greys/Zeta','the greys':'Greys/Zeta',
 'yahyel':'Yahyel','ya-yel':'Yahyel',"ya'yel":'Yahyel','pleiadians':'Pleiadians','pleiadian':'Pleiadians','pleiades':'Pleiadians',
 'anunnaki':'Anunnaki','annunaki':'Anunnaki','orion':'Orion','orions':'Orion','sirius':'Sirius','sirians':'Sirius','lyra':'Lyra/Lyrans','lyrans':'Lyra/Lyrans',
 'arcturians':'Arcturians','arcturus':'Arcturians','atlantis':'Atlantis','lemuria':'Lemuria','mu':'Lemuria','shalanaya':'Shalanaya','shalinaya':'Shalanaya',
 'darryl anka':'Darryl Anka','darryl':'Darryl Anka','sedona':'Sedona','roswell':'Roswell','willa hillicrissing':'Willa Hillicrissing','willa':'Willa Hillicrissing',
 'interstellar alliance':'Interstellar Alliance','the interstellar alliance':'Interstellar Alliance','hybrid children':'Hybrid children','hybrids':'Hybrid children',
 'oversoul':'Oversoul','higher mind':'Higher mind','all that is':'All That Is','the one':'All That Is','god':'God','yeshua':'Jesus/Yeshua','jesus':'Jesus/Yeshua','christ':'Jesus/Yeshua',
 'seth':'Seth','ai':'AI','artificial intelligence':'AI','epsilon':'Epsilon/Epiphany/Eclipse','epiphany':'Epsilon/Epiphany/Eclipse','eclipse':'Epsilon/Epiphany/Eclipse',
 'sasquatch':'Sasquatch/Bigfoot','bigfoot':'Sasquatch/Bigfoot','mars':'Mars','moon':'Moon','sun':'Sun','venus':'Venus','earth':'Earth','gaia':'Earth','humanity':'Humanity','humans':'Humanity',
 'first contact':'First Contact (film)','first contact documentary':'First Contact (film)','vega':'Vega','andromeda':'Andromeda','andromedans':'Andromeda','reptilians':'Reptilians','draco':'Reptilians','tall whites':'Tall Whites','nordics':'Nordics'}
for v in videos:
    seen=set()
    for e in v['named_entities']:
        s = str(e).strip(); key = s.lower().strip('.,')
        name = ENT_ALIAS.get(key, s)
        if name in ('Earth','Humanity','Darryl Anka','God','Bashar','Divine Insights','Divine Insights (channel)','Los Angeles','Las Vegas','YouTube','Bashar Communications'): continue
        ent[name]+=1
        if name not in seen: ent_docs[name]+=1; seen.add(name)
entities = [{'entity':e,'docs':ent_docs[e]} for e in ent_docs]
entities.sort(key=lambda x:-x['docs']); entities=entities[:40]
TOOL_MAP = [
 (r'permission slip','Permission slips'),
 (r'formula|highest excitement|excitement kit|act on (your )?(highest )?(excitement|passion)','The Formula / acting on highest excitement'),
 (r'meditat','Meditation'),
 (r'belief|what would i have to believe|definition','Belief investigation ("what would I have to believe?")'),
 (r'visuali|imagin','Visualization / imagination'),
 (r'crystal','Crystal work'),
 (r'synchronicit','Synchronicity tracking'),
 (r'hour of power','The Hour of Power (12 affirmations)'),
 (r'holotope','Holotope meditation'),
 (r'cybo','Cybo (the Essassani game)'),
 (r'1-3-5-7-11|1357','The 1-3-5-7-11 download'),
 (r'story tree','The Story Tree'),
 (r'light language','Light language'),
 (r'social experiment','Interstellar Alliance Social Experiment'),
 (r'ce-?5|contact protocol|protocols of first contact','Contact protocols / CE-5'),
 (r'sacred circuitry','Sacred Circuitry'),
 (r'breath','Breathing exercises'),
 (r'dream','Dream work'),
 (r'affirmation','Affirmations'),
 (r'spiral','The Spiral exercise'),
 (r'gratitude|appreciat','Gratitude / appreciation practice'),
 (r'grounding|nature|walk','Grounding / time in nature'),
 (r'tarot|oracle|divination','Divination tools (tarot etc.)'),
 (r'question|inquiry','Self-inquiry questions'),
 (r'journal|writ','Journaling / writing'),
 (r'ritual','Ritual'),
 (r'channel','Channeling practice'),
 (r'vortex','Vortex / portal work'),
 (r'eclipse|epsilon|epiphany','Epsilon/Epiphany/Eclipse spheres'),
 (r'game','Games / play'),
]
tools = collections.Counter()
for v in videos:
    cats=set()
    for x in v['tools_or_exercises']:
        s = (x.get('tool','') if isinstance(x,dict) else str(x)).lower()
        for pat,name in TOOL_MAP:
            if re.search(pat,s): cats.add(name); break
    for c in cats: tools[c]+=1
tools_table=[{'tool':t,'docs':c} for t,c in tools.most_common(30)]

# ---------- predictions / years ----------
year_docs = collections.Counter(); year_examples = collections.defaultdict(list)
for v in videos:
    seen=set()
    for p in v['predictions_and_dates']:
        s = p if isinstance(p,str) else json.dumps(p, ensure_ascii=False)
        for y in re.findall(r'\b(19[5-9]\d|20[0-9]\d|21\d\d)\b', s):
            y=int(y)
            if y in seen: continue
            seen.add(y); year_docs[y]+=1
            if len(year_examples[y])<4: year_examples[y].append({'video_id':v['video_id'],'text':s[:220]})
predictions = [{'year':y,'docs':year_docs[y],'examples':year_examples[y]} for y in sorted(year_docs)]

# ---------- tag co-occurrence lift ----------
B = (TP>=10).astype(float)
p = B.mean(0)
lift = np.zeros((len(TAGS),len(TAGS)))
for i in range(len(TAGS)):
    for j in range(len(TAGS)):
        pij = (B[:,i]*B[:,j]).mean()
        lift[i,j] = pij/(p[i]*p[j]) if p[i]>0 and p[j]>0 else 0
pairs=[]
for i in range(len(TAGS)):
    for j in range(i+1,len(TAGS)):
        co = int((B[:,i]*B[:,j]).sum())
        if co>=4: pairs.append({'a':TAG_LABEL[TAGS[i]],'b':TAG_LABEL[TAGS[j]],'co_docs':co,'lift':round(float(lift[i,j]),2)})
pairs.sort(key=lambda x:-x['lift'])

# ---------- what people ask (Q&A classification) ----------
QKEYS = {
 'relationships_family_sexuality': r'relationship|partner|marriage|married|wife|husband|family|parent|mother|father|child|children|kids|son|daughter|love life|dating|sex|twin flame|soulmate|friend',
 'health_body_healing_death': r'health|heal|illness|disease|cancer|pain|body|diet|food|sleep|addiction|alcohol|drug|smok|die|death|dying|suicide|depress|anxiety|weight|medic|autism|adhd',
 'abundance_money_career': r'money|abundance|financ|job|career|business|work\b|income|wealth|rich|poor|debt|afford|profession|success',
 'et_contact_disclosure_2027': r'contact|disclosure|ufo|uap|alien|extraterrestrial|\bet\b|\bets\b|2027|ship|craft|sighting|landing',
 'essassani_hybrids_other_civilizations': r'essassani|sassani|hybrid|yahyel|pleiad|anunnaki|orion|sirius|grey|zeta|reptilian|civilization|your world|your planet',
 'parallel_realities_shifting': r'parallel|shift|timeline|version of',
 'physical_vs_higher_mind': r'higher mind|physical mind|higher self|ego',
 'beliefs_emotions_fear': r'belief|fear|worth|doubt|guilt|shame|anger|negative|trust|confiden|self-esteem|insecur|worry',
 'formula_excitement': r'excite|passion|purpose|formula|follow|what should i do|next step|calling|path',
 'time_simultaneity_reincarnation': r'past life|past lives|reincarnat|incarnat|previous life|time travel|future self|simultaneous',
 'consciousness_oversoul_higherself': r'oversoul|soul|consciousness|spirit guide|guides|angel|all that is|source',
 'synchronicity_dreams_meditation': r'synchronic|dream|meditat|sign|coincidence|vision|psychic|intuition|telepath',
 'politics_society_economy_ai': r'government|politic|president|election|econom|collapse|war|society|technolog|\bai\b|artificial|robot|internet|climate|school|education system',
 'ancient_history_atlantis_orion_sirius': r'atlantis|lemuria|pyramid|ancient|egypt|history of|origin of human|dinosaur|maya',
 'earth_shift_timelines_ascension': r'ascension|density|dimension|new earth|the shift|2012|2033|2050|frequency of the planet',
 'permission_slips_tools': r'permission slip|tool|technique|exercise|practice|ritual|crystal|affirmation',
 'channeling_mechanics_darryl': r'channel|darryl|how do you|trance|medium',
 'spirituality_god_love_service': r'\bgod\b|religion|jesus|christ|buddha|prayer|spiritual|unconditional love|forgive|service',
 'physics_energy_frequency_dimensions': r'energy|frequenc|vibration|quantum|physics|gravity|light speed|electr|magnet',
}
qcount = collections.Counter(); qexamples = collections.defaultdict(list); nq=0
for v in videos:
    for q in v['qa_topics']:
        text = (q.get('question') or ''); nq+=1
        tl = text.lower(); hit=None
        for tag,pat in QKEYS.items():
            if re.search(pat, tl): hit=tag; break
        hit = hit or 'misc_life_guidance'
        qcount[hit]+=1
        if len(qexamples[hit])<5: qexamples[hit].append({'video_id':v['video_id'],'question':text})
questions = [{'tag':t,'label':TAG_LABEL[t],'count':qcount[t],'pct':round(100*qcount[t]/max(nq,1),1),'examples':qexamples[t]} for t in TAGS]
questions.sort(key=lambda x:-x['count'])

# ---------- headline numbers ----------
n_full = sum(1 for v in videos if v['content_type']=='Full session (re-upload)')
n_int = sum(1 for v in videos if v['content_type']=='Interview with Darryl Anka')
n_off = sum(1 for v in videos if v['content_type']=='Official highlight clip')
n_clip = sum(1 for v in videos if v['content_type']=='Clip / excerpt')
top3 = share_overall[:3]
docs_2027 = year_docs.get(2027,0)
docs_2026 = year_docs.get(2026,0)
docs_2033 = year_docs.get(2033,0)
total_words = int(wc.sum())
head = {
 'n_docs': N, 'n_full_sessions': n_full, 'n_interviews': n_int, 'n_official_clips': n_off, 'n_clips': n_clip,
 'approx_words_analyzed': total_words, 'n_questions': nq,
 'top3': top3, 'top3_combined_pct': round(sum(t['weighted_pct'] for t in top3),1),
 'docs_mentioning_2027': docs_2027, 'docs_mentioning_2026': docs_2026, 'docs_mentioning_2033': docs_2033,
 'n_clusters': k, 'silhouette': round(float(sil),3), 'k_search': {str(kk):v for kk,v in arch_search.items()}, 'text_only_clustering': {str(kk):v for kk,v in text_search.items()},
 'map_method': map_method,
 'terms_in_most_docs': [t['term'] for t in term_table[:10]],
 'most_asked': questions[:5],
}

analysis = {
 'generated': '2026-09-11',
 'method': {
  'corpus': 'Structured digests generated from public YouTube auto-transcripts via youtubetotranscript.com (one digest per video), plus podcast metadata. Each digest holds a summary, Q&A gists, key terms, ≤30-word quotes and an LLM-estimated topic mix over 20 fixed tags.',
  'document_text': 'title ×2 + opening summary + every Q&A question and answer gist + key terms repeated by frequency bucket (high×3, medium×2, low×1) + tools + named entities; multi-word Bashar terms fused into single tokens.',
  'vectorizer': 'TF-IDF, unigrams+bigrams, min_df=2, max_df=0.8, sublinear tf, English + custom stop words.',
  'clustering': f'Session archetypes: k-means (50 restarts, seed {RNG}) on the square-rooted 20-tag topic mix of each video; k=5 chosen for the best balance of silhouette ({sil:.2f}) and interpretability (k=6–7 only split off 2–3-video clusters). Diagnostic: k-means on TF-IDF vocabulary alone gives silhouette 0.01–0.05 for k=4..7 — Bashar\'s vocabulary is nearly the same in every recording, so vocabulary alone barely separates sessions.',
  'map': map_method,
  'topic_share': 'Weighted mean of per-video topic percentages, weights = approximate transcript word count (so full sessions count more than short clips). Unweighted mean also reported.',
  'caveats': ['Topic percentages are model estimates from auto-transcripts, not hand coding.', 'Sample is skewed to what is on YouTube in 2024–2026 (re-uploads, highlight clips, interviews); it is not a random sample of 40 years of sessions.', 'Many re-upload titles carry invented dates; year-based views use only videos with a reliable date.', 'Interviews with Darryl Anka are in his voice, not Bashar\'s, and are flagged separately.']
 },
 'tags': [{'tag':t,'label':TAG_LABEL[t]} for t in TAGS],
 'headline': head,
 'share_overall': share_overall,
 'share_by_type': by_type,
 'share_by_year': by_year,
 'share_by_era': by_era,
 'clusters': clusters,
 'terms': term_table,
 'entities': entities,
 'tools': tools_table,
 'predictions': predictions,
 'tag_pairs': pairs[:25],
 'questions': questions,
}
json.dump(analysis, open(os.path.join(OUT,'analysis.json'),'w'), ensure_ascii=False, indent=1)
json.dump(videos, open(os.path.join(OUT,'videos.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(head, ensure_ascii=False, indent=1)[:3000])
for c in clusters: print(c['id'], c['size'], c['top_terms'][:8], [t['label'] for t in c['top_tags'][:2]])
print('by_year', {y:v['n'] for y,v in by_year.items()}, 'by_era', {e:v['n'] for e,v in by_era.items()})
print('by_type', {t:v['n'] for t,v in by_type.items()})
