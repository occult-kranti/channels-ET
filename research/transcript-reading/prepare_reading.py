#!/usr/bin/env python3
"""Verify retained sources and prepare a finite private reading packet; no network."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = Path('/workspace/channels-et-raw/transcript-reading')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
def words(text): return len(text.split())

def prepare():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    old_asr = ROOT/'research/harvest/asr/summary.json'
    new_asr = ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json'
    old_audio = ROOT/'research/harvest/publisher_sources/publisher-summary.json'
    new_audio = ROOT/'research/access-repair/athina/publisher_sources/publisher-summary.json'
    primary = ROOT/'research/access-repair/primary-sources/expanded-metadata.json'
    sources = {r['source_id']:r for filename in (old_audio,new_audio) for r in read(filename)['records']}
    documents, windows, checks, segments_by_source = [], [], [], {}
    asr = [(r,old_asr) for r in read(old_asr)['records']] + [(read(new_asr),new_asr)]
    for receipt, receipt_path in asr:
        sid=receipt['sourceId']; audio=sources[sid]; directory=Path(receipt['transcriptDirectory'])
        for output in receipt['outputs']:
            p=directory/output['name']; assert p.stat().st_size==output['bytes'] and sha(p)==output['sha256'], str(p)
            checks.append({'path':str(p),'sha256':output['sha256'],'bytes':output['bytes']})
        assert audio['sha256']==receipt['sourceAudioSha256']
        segments=[json.loads(line) for line in (directory/'segments.jsonl').read_text().splitlines() if line]
        segments_by_source[sid]=segments
        full=(directory/'transcript.txt').read_text(); total=receipt['sourceAudioDurationSeconds']
        doc={'sourceId':sid,'modality':'audio_asr','title':audio['episode_title'],'publisher':audio['publisher_name'],
             'practitionerContext':'Athina Król / Ashtar-attributed creator episode' if sid.startswith('athina-') else 'Darryl Anka / Bashar-related publisher context',
             'sourceUrl':receipt['sourceUrl'],'sourceReceipt':str(receipt_path.relative_to(ROOT)),
             'sourceAudioSha256':receipt['sourceAudioSha256'],'transcriptSha256':sha(directory/'transcript.txt'),
             'segmentsSha256':sha(directory/'segments.jsonl'),'words':words(full),'durationSeconds':total,
             'segmentCount':len(segments),'humanReviewed':False,'speakerVerified':False,'videoEditionVerified':False,
             'wordCountMethod':'Python str.split whitespace tokens for both full text and reading coverage'}
        documents.append(doc)
        first=min(s['start'] for s in segments); last=max(s['end'] for s in segments)
        bounds=[('beginning',first,first+30),('middle',max(first,total*.5-15),total*.5+15),('ending',max(first,last-30),last)]
        q=[]
        for i,s in enumerate(segments):
            t=s['text'].strip(); match=re.search(r'\b(?:how|why|what|when|where|can|could|do|does|would|is|are)\b',t,re.I)
            if not match or s['start']<90 or s['start']>last-60: continue
            score=3*('?' in t)+2*bool(re.match(r'^(?:so[, ]+|and[, ]+|but[, ]+)?(?:how|why|what|when|where|can|could|do|does|would|is|are)\b',t,re.I))
            score+=sum(bool(re.search(r'\b'+term+r'\b',t,re.I)) for term in ('belief','reality','contact','fear','consciousness','channel','human','love'))
            if score: q.append((score,-s['start'],i))
        if q:
            index=max(q)[2]; s=segments[index]; bounds.append(('query_rich',s['start'],min(last,s['start']+60)))
        for kind,start,end in bounds:
            selected=[s for s in segments if s['end']>start and s['start']<end]
            if not selected:continue
            text=' '.join(s['text'].strip() for s in selected)
            windows.append({'windowId':sid+':'+kind,'sourceId':sid,'kind':kind,'startSeconds':selected[0]['start'],
                            'endSeconds':selected[-1]['end'],'segmentIds':[s['id'] for s in selected],
                            'firstSegmentId':selected[0]['id'],'lastSegmentId':selected[-1]['id'],
                            'words':words(text),'textSha256':hashlib.sha256(text.encode()).hexdigest(),
                            'selectionMethod':'fixed temporal window' if kind!='query_rich' else 'deterministic question-marker and topic-keyword score; purposeful, not representative',
                            'text':text})
    metadata=read(primary)
    for item in metadata['daniel']['items']:
        f=item['text']; sid=f"daniel-item-{item['item_index']:02d}"; path=Path(f['raw_local_path']); text=path.read_text()
        assert path.stat().st_size==f['bytes'] and sha(path)==f['sha256']; checks.append({'path':str(path),**{k:f[k] for k in ('sha256','bytes')}})
        documents.append({'sourceId':sid,'modality':'publisher_text','title':item['title'],'publisher':'Daniel Scranton',
                          'practitionerContext':'Daniel Scranton / publisher-attributed message','sourceUrl':item['url'],
                          'sourceReceipt':str(primary.relative_to(ROOT)),'transcriptSha256':f['sha256'],'words':words(text),
                          'durationSeconds':None,'humanReviewed':False,'speakerVerified':False,'videoEditionVerified':False,
                          'sourceCategories':item['categories_as_published'],
                          'wordCountMethod':'Python str.split whitespace tokens for both full text and reading coverage'})
        # First 350 words usually include the publisher-attributed message. Promotions may remain.
        tokens=list(re.finditer(r'\S+',text)); end=tokens[min(250,len(tokens))-1].end()
        excerpt=text[:end]
        windows.append({'windowId':sid+':opening_250_words','sourceId':sid,'kind':'opening_250_words','startChar':0,'endChar':end,
                        'words':words(excerpt),'textSha256':hashlib.sha256(excerpt.encode()).hexdigest(),
                        'selectionMethod':'first250whitespace words of retained publisher RSS text, including any title/promotions','text':excerpt})
    item=metadata['paul'];f=item['text'];path=Path(f['raw_local_path']);text=path.read_text();sid=item['source_id']
    assert path.stat().st_size==f['bytes'] and sha(path)==f['sha256'];checks.append({'path':str(path),**{k:f[k] for k in ('sha256','bytes')}})
    documents.append({'sourceId':sid,'modality':'publisher_text','title':item['title'],'publisher':'Paul Selig',
                      'practitionerContext':'Paul Selig / spiritual Guides comparison','sourceUrl':item['requested_url'],
                      'sourceReceipt':str(primary.relative_to(ROOT)),'transcriptSha256':f['sha256'],'words':words(text),
                      'durationSeconds':None,'humanReviewed':False,'speakerVerified':False,'videoEditionVerified':False,
                      'wordCountMethod':'Python str.split whitespace tokens for both full text and reading coverage'})
    # The four-page publisher PDF text is short enough to inspect in full.
    windows.append({'windowId':sid+':full_text','sourceId':sid,'kind':'full_text','startChar':0,'endChar':len(text),
                    'words':words(text),'textSha256':hashlib.sha256(text.encode()).hexdigest(),
                    'selectionMethod':'full retained four-page publisher PDF extraction','text':text})
    for target in read(HERE/'targeted-windows.json')['windows']:
        sid=target['sourceId']; selected=[s for s in segments_by_source[sid] if target['firstSegmentId']<=s['id']<=target['lastSegmentId']]
        text=' '.join(s['text'].strip() for s in selected)
        windows.append({'windowId':sid+':'+target['kind'],'sourceId':sid,'kind':target['kind'],
                        'startSeconds':selected[0]['start'],'endSeconds':selected[-1]['end'],
                        'segmentIds':[s['id'] for s in selected],'firstSegmentId':selected[0]['id'],'lastSegmentId':selected[-1]['id'],
                        'words':words(text),'textSha256':hashlib.sha256(text.encode()).hexdigest(),
                        'selectionMethod':target.get('selectionMethod','post-hoc targeted NMF-term inspection')+'; '+target['reason'],'text':text})
    write(HERE/'documents.json',{'schemaVersion':1,'documents':documents})
    write(PRIVATE/'reading-packet.json',{'schemaVersion':1,'windows':windows})
    write(HERE/'source-manifest.json',{'schemaVersion':1,'scope':'all20ASR outputs and16authoredtextfilesverified before sampling',
          'receiptPins':{str(p.relative_to(ROOT)):sha(p) for p in (old_asr,new_asr,old_audio,new_audio,primary)},'privateFiles':checks,
          'preparedAt':datetime.now(timezone.utc).isoformat()})
    write(HERE/'reading-windows.json',{'schemaVersion':1,'windows':[{k:v for k,v in w.items() if k!='text'} for w in windows],
                                    'readStatus':'prepared_not_yet_claimed_read'})
    print(json.dumps({'documents':len(documents),'windows':len(windows),'packetWords':sum(w['words'] for w in windows),'privatePacket':str(PRIVATE/'reading-packet.json')}))

if __name__=='__main__':prepare()
