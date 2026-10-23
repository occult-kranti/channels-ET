#!/usr/bin/env python3
"""Retrieve bounded public method documents; release hashes, not full copyrighted texts."""
import concurrent.futures,datetime,hashlib,json,pathlib,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=pathlib.Path('/workspace/channeling-atlas-private/literature'); CACHE.mkdir(parents=True,exist_ok=True)
SOURCES=[
 ('yt-dlp-readme','https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/README.md'),
 ('yt-dlp-license','https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/LICENSE'),
 ('transcript-api-readme','https://raw.githubusercontent.com/jdepoix/youtube-transcript-api/master/README.md'),
 ('transcript-api-license','https://raw.githubusercontent.com/jdepoix/youtube-transcript-api/master/LICENSE'),
 ('faster-whisper-readme','https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/README.md'),
 ('faster-whisper-license','https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/LICENSE'),
 ('bertopic-readme','https://raw.githubusercontent.com/MaartenGr/BERTopic/master/README.md'),
 ('bertopic-license','https://raw.githubusercontent.com/MaartenGr/BERTopic/master/LICENSE'),
 ('keybert-readme','https://raw.githubusercontent.com/MaartenGr/KeyBERT/master/README.md'),
 ('keybert-license','https://raw.githubusercontent.com/MaartenGr/KeyBERT/master/LICENSE'),
 ('youniverse-paper','https://ojs.aaai.org/index.php/ICWSM/article/download/18125/17928'),
 ('tube2vec-paper','https://ojs.aaai.org/index.php/ICWSM/article/download/31450/33610/35506'),
 ('topic-twaddle','https://aclanthology.org/2021.naacl-main.300/'),
 ('youtube-search-docs','https://developers.google.com/youtube/v3/docs/search/list'),
 ('youtube-playlist-docs','https://developers.google.com/youtube/v3/docs/playlistItems/list'),
]
def get(pair):
 id,url=pair;r={'id':id,'url':url,'attempted_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ChannelingAtlasMethodsResearch/1.0'})
  with urllib.request.urlopen(req,timeout=30) as response:
   b=response.read();r.update(status='retrieved',http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  (CACHE/id).write_bytes(b)
 except Exception as exc:r.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:300])
 return r
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(get,SOURCES))
 (ROOT/'retrieval-receipt.json').write_text(json.dumps({'note':'Public URLs only; no cookies, credentials, rotating proxies or disabled TLS. Local cache not released. Retrieved is not equivalent to fully read.','sources':rows},indent=2))
 print(json.dumps([{'id':r['id'],'status':r['status'],'bytes':r.get('bytes'),'error':r.get('error')} for r in rows],indent=2))
