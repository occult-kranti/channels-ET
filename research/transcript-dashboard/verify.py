#!/usr/bin/env python3
"""Verify exact public source joins, accounting units and protected prior releases."""
import argparse,hashlib,json,math,sqlite3,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist/transcripts');args=parser.parse_args();out=args.output
data=json.loads((out/'data.json').read_text());manifest=json.loads((HERE/'inputs.json').read_text());checks=[]
def check(ok,label):
    assert ok,label
    checks.append(label)
for item in manifest['inputs']:
    raw=(ROOT/item['source']).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    check(digest==item['sha256'],'Reviewed source pin: '+item['source'])
    check((out/item['target']).read_bytes()==raw,'Published metadata/figure byte equality: '+item['target'])
    if item.get('key'):
        value=data
        for k in item['key'].split('.'):value=value[k]
        check(value==json.loads(raw),'Interactive result binding: '+item['key'])
a=data['analysis'];sources=a['sources'];by_id={s['sourceId']:s for s in sources};audio=[s for s in sources if s['modality']=='audio_asr'];authored=[s for s in sources if s['modality']=='publisher_text']
check(len(by_id)==36 and len(audio)==20 and len(authored)==16,'Unique analytical document grain20ASR/16authored')
check(len({s['publisher']for s in audio})==14,'Audio publishers are14, not20mediums')
check(sum('Bashar' in s['practitionerContext']for s in audio)==19,'Audio context imbalance19Bashar/1comparison retained')
check(sum(s['tokenCount']for s in audio)==a['summary']['audioCommonTokens']==226138,'ASR common analytical token denominator')
check(sum(s['tokenCount']for s in authored)==a['summary']['authoredCommonTokens']==13556,'Authored common analytical token denominator')
check(sum(s['words']for s in audio)==226093 and sum(s['words']for s in authored)==13656,'Whitespace word denominators remain separate from common/receipt counts')
check(all(not s['speakerVerified']and not s['youtubeEditionVerified']for s in sources),'Source labels do not certify speaker or video-edition identity')
for corpus,docs in [('audio',audio),('authored',authored)]:
    f=a['tfidf'][corpus];ids=f['sourceIds'];matrix=f['cosine'];check(set(ids)=={s['sourceId']for s in docs},'Separate fit source IDs: '+corpus)
    check(len(matrix)==len(ids)and all(len(r)==len(ids)for r in matrix),'Cosine dimensions: '+corpus)
    check(all(abs(matrix[i][j]-matrix[j][i])<1e-10 and 0<=matrix[i][j]<=1+1e-10 for i in range(len(ids))for j in range(len(ids))),'Symmetric bounded cosine matrix: '+corpus)
    check(all(abs(matrix[i][i]-1)<1e-9 for i in range(len(ids))),'Cosine diagonal is self-similarity: '+corpus)
    display=f['displayTermWeights'];check({r['sourceId']for r in display}==set(ids)and all(len(r['weights'])==len(f['terms'])==40 for r in display),'Exact fixed display-vocabulary weights: '+corpus)
    check(all(abs(sum(r['weights'][i]for r in display)/len(ids)-t['weight'])<1e-7 for i,t in enumerate(f['terms'])),'Mean display TF-IDF reproduces fitted ranking: '+corpus)
    t=a['topics']if corpus=='audio'else f['topics'];check({r['sourceId']for r in t['weights']}==set(ids)and all(len(r['weights'])==t['selectedK']and abs(sum(r['weights'])-1)<1e-8 for r in t['weights']),'Topic shares normalized within own fit: '+corpus)
    c=a['clusters']if corpus=='audio'else f['clusters'];check({r['sourceId']for r in c['labels']}==set(ids),'Cluster labels remain scoped to their fit: '+corpus)
for r in a['lexicons']['themeRates']:
    check(r['tokenDenominator']==by_id[r['sourceId']]['tokenCount'],'Lexical-rate denominator: '+r['sourceId'])
    check(all(abs(r['rates'][k]-v/r['tokenDenominator']*1000)<1e-9 for k,v in r['counts'].items()),'Keyword-count rates retain exact zeros: '+r['sourceId'])
r=data['reading'];documents=r['documents']['documents'];windows=r['windows']['windows'];window_by_id={w['windowId']:w for w in windows};qa=r['qa']['records'];summary=r['summary']
check({x['sourceId']for x in documents}==set(by_id),'Reader36documents join numerical source IDs exactly')
check(all(x['transcriptSha256']==by_id[x['sourceId']]['transcriptSha256']for x in documents),'Reader and numeric source hashes agree')
check(len(windows)==105 and len(window_by_id)==105 and summary['inspectedWindows']==105,'Unique105sampled-window metadata records')
check(summary['uniqueAsrWordsRead']==11992 and summary['asrWordsTotal']==226093 and abs(summary['asrWordCoverageFraction']-11992/226093)<1e-12,'ASR unique reading coverage5.304percent')
check(summary['uniquePublisherTextWordsRead']==6319 and summary['publisherTextWordsTotal']==13656 and abs(summary['publisherTextWordCoverageFraction']-6319/13656)<1e-12,'Authored unique reading coverage46.273percent')
check(summary['packetWordsRead']==19603 and summary['packetWordCountIncludesOverlappingWindows'],'Packet words do not masquerade as unique coverage')
check(len(qa)==37 and len({q['candidateId']for q in qa})==37,'Separate actual-source database has37typedcandidate records')
check(sum(q['modality']=='audio_asr'for q in qa)==21 and sum(q['candidateKind']=='authored_comparison_prompt'for q in qa)==16,'Question-like ASR candidates remain separate from constructed authored prompts')
for q in qa:
    check(q['sourceTranscriptSha256']==by_id[q['sourceId']]['transcriptSha256'],'Candidate source-text binding: '+q['candidateId'])
    w=window_by_id[q['supportWindowId']];check(w['sourceId']==q['sourceId'],'Candidate exact support-window join: '+q['candidateId'])
    check(not q['humanValidated']and not q['exactQuotePublished']and not q['semanticEquivalenceValidated'],'Candidate paraphrase/validation scope: '+q['candidateId'])
    if q.get('startSeconds')is not None:check(q['startSeconds']>=0 and q['endSeconds']<=by_id[q['sourceId']]['durationSeconds']+1,'Candidate shared audio window remains in source bounds: '+q['candidateId'])
check(len(r['findings']['records'])==6 and all(all(w in window_by_id for w in f['supportWindowIds'])for f in r['findings']['records']),'Six interpretive leads join actual inspected windows')
d=data['distributions'];check(d['summary']['indexedYouTubeIds']==942 and d['summary']['selectedYouTubeIds']==733 and d['summary']['actualYouTubeVideos']==0,'Inherited942/selected733 distinct from actual0YouTubevideos')
for name,rows in d['youtube'].items():
    c=d['attributionCoverage'][name];check(c['assignedUniqueIds']+c['unassignedUniqueIds']==942,'Explicit attribution missingness: '+name)
    check(sum(row['indexed_ids']for row in rows)==c['groupMemberships'],'Overlapping membership denominator: '+name)
    check(all(row['youtube_downloaded_video_files']==row['youtube_downloaded_caption_files']==row['youtube_downloaded_bytes']==0 for row in rows),'No RSS bytes imputed to YouTube associations: '+name)
for name,rows in d['sourceStorage'].items():
    check(sum(x['canonical_source_artifacts']for x in rows)==99 and sum(x['canonical_source_bytes']for x in rows)==1703635307,'Canonical-file partition totals: '+name)
    check(sum(x['source_recordings']for x in rows)==20 and abs(sum(x['recorded_audio_seconds']for x in rows)-81691.621533)<1e-5,'Audio recording/duration partition: '+name)
archive=data['archive']['state'];check(archive==d['localArchive'],'Distribution state joins exact final local archive receipt')
check(archive['actual_local_archive_completed']and archive['hash_verified']and archive['actual_local_files']==200 and archive['actual_local_bytes']==1703879268,'Actual200verifiedlocal copies, not a plan')
check(archive['actual_drive_uploaded_files']==0 and not archive['environment_retention_guaranteed']and not archive['chat_attachment_created'],'Local archive remains distinct from Drive/durable chat storage')
protected=['research/youtube-access/dashboard','research/access-repair','research/harvest/dashboard','research/continuation/dashboard','research/continuation/paper','dist/research/data.json','dist/research/paper.pdf','dist/research/source.zip']
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','0a20688c500ec6b0761f28340590c6beee58941e','--',*protected],cwd=ROOT,text=True).splitlines()
for p in paths:
    expected=subprocess.check_output(['git','rev-parse','0a20688c500ec6b0761f28340590c6beee58941e:'+p],cwd=ROOT,text=True).strip();raw=(ROOT/p).read_bytes();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();check(actual==expected,'Prior held source/artifact byte freeze: '+p)
receipt={'status':'PASS','releaseStatus':data['releaseStatus'],'scope':'Offline source joins and accounting; no source collection or raw text publication','checks':checks,'artifacts':len(manifest['inputs']),'publicDataSha256':hashlib.sha256((out/'data.json').read_bytes()).hexdigest()}
(HERE/'source-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':'PASS','checks':len(checks),'artifacts':len(manifest['inputs'])}))
