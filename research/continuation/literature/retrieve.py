#!/usr/bin/env python3
"""Bounded authoritative method-source retrieval; raw copyrighted fulltexts local only."""
import concurrent.futures,datetime,hashlib,json,pathlib,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parent;CACHE=pathlib.Path('/workspace/channels-et-private/literature');CACHE.mkdir(parents=True,exist_ok=True)
SOURCES=[
 ('youniverse-page','https://ojs.aaai.org/index.php/ICWSM/article/view/18125'),
 ('tube2vec-page','https://ojs.aaai.org/index.php/ICWSM/article/view/31450'),
 ('religious-youtube-page','https://ojs.aaai.org/index.php/ICWSM/article/view/42649'),
 ('japanese-pathways-page','https://ojs.aaai.org/index.php/ICWSM/article/view/35965'),
 ('channelers-answers-page','https://journalofscientificexploration.org/index.php/jse/article/view/2907'),
 ('channeled-qualitative-page','https://noetic.org/publication/a-qualitative-exploratory-analysis-of-channeled-content/'),
 ('et-semantic-page','https://noetic.org/publication/semantic-structure-and-correspondence-in-prospective-trance-channeled-communications-attributed-to-extraterrestrial-intelligences/'),
 ('et-qualitative-page','https://noetic.org/publication/qualitative-structure-and-meaning-in-prospective-trance-channeled-communications-attributed-to-extraterrestrial-intelligences/'),
 ('et-records-page','https://journalofscientificexploration.org/index.php/jse/article/view/3817'),
 ('rag-original-pdf','https://arxiv.org/pdf/2005.11401'),
 ('realm-page','https://proceedings.mlr.press/v119/guu20a.html'),
 ('ragas-page','https://aclanthology.org/2024.eacl-demo.16/'),
 ('ares-page','https://aclanthology.org/2024.naacl-long.20/'),
 ('lost-middle-page','https://aclanthology.org/2024.tacl-1.9/'),
 ('icwsm-2027','https://www.icwsm.org/2027/'),
 ('icwsm-2027-guidelines','https://www.icwsm.org/2027/formatting-guidelines/'),
 ('crossref-ft-rag','https://api.crossref.org/works?query.title=Fine-Tuning%20or%20Retrieval%20Comparing%20Knowledge%20Injection%20in%20LLMs&rows=5'),
 ('crossref-domain-channel','https://api.crossref.org/works?query.title=channeling%20content%20qualitative%20Wahbeh&rows=8'),
]
def get(pair):
 id,url=pair;r={'id':id,'url':url,'attempted_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ChannelingAtlasResearch/1.0'}),timeout=35) as response:
   b=response.read();r.update(status='retrieved',http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  (CACHE/id).write_bytes(b)
 except Exception as e:r.update(status='failed',error_type=type(e).__name__,error=str(e)[:250])
 return r
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rs=list(ex.map(get,SOURCES))
 (ROOT/'retrieval-initial.json').write_text(json.dumps({'scope':'Targeted scholarly/software/venue primary sources, not systematic review. Fresh attempts after observed network-policy change. Retrieval not equivalent to reading. Raw documents outside checkout.','sources':rs},indent=2))
 print(json.dumps([{'id':x['id'],'status':x['status'],'bytes':x.get('bytes'),'error':x.get('error')} for x in rs],indent=2))
