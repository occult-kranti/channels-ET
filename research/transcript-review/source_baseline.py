#!/usr/bin/env python3
"""Independent receipt-to-byte baseline; publishes metadata only, never source text."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RAW=Path('/workspace/channels-et-raw').resolve()

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def source_file(path,expected):
    path=Path(path)
    assert not path.is_symlink() and path.resolve().is_relative_to(RAW), 'Private source escaped the retained raw root'
    data=path.read_bytes();assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'], 'Source byte/hash mismatch'
    return data

def build():
    paths={
        'asr19':ROOT/'research/harvest/asr/summary.json',
        'asr1':ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json',
        'primary':ROOT/'research/access-repair/primary-sources/expanded-metadata.json',
    }
    records=load(paths['asr19'])['records']+[load(paths['asr1'])]
    docs=[];issues=[];checked_files=0
    for receipt in records:
        outputs={r['name']:r for r in receipt['outputs']};directory=Path(receipt['transcriptDirectory'])
        blobs={name:source_file(directory/name,row) for name,row in outputs.items()};checked_files+=len(blobs)
        text=blobs['transcript.txt'].decode();segments=[json.loads(line) for line in blobs['segments.jsonl'].splitlines() if line.strip()]
        assert len(segments)==receipt['segments'] and len(text.split())==receipt['words']
        assert text=='\n'.join(r['text'] for r in segments)+'\n', 'ASR flat text/segment join differs'
        ids=[r['id'] for r in segments];assert len(ids)==len(set(ids)), 'Repeated segment ID'
        invalid=[r['id'] for r in segments if not all(isinstance(r[k],(int,float)) and not isinstance(r[k],bool) and math.isfinite(r[k]) for k in ('start','end')) or r['start']<0 or r['end']<r['start']]
        assert not invalid,'Invalid segment timing'
        starts=[r['start'] for r in segments];assert starts==sorted(starts),'Nonmonotonic ASR starts'
        overlaps=sum(segments[i]['start']<segments[i-1]['end'] for i in range(1,len(segments)))
        duration=receipt['sourceAudioDurationSeconds'];last_end=max(r['end'] for r in segments)
        if last_end>duration+1:issues.append({'source_id':receipt['sourceId'],'type':'ASR_end_exceeds_recorded_audio_by_more_than1s','delta_seconds':last_end-duration})
        docs.append({'source_id':receipt['sourceId'],'corpus':'asr','context':'ashtar_single_creator_episode' if receipt['sourceId'].startswith('athina-') else 'bashar_related_publisher_episode',
                     'words':len(text.split()),'segments':len(segments),'audio_seconds':duration,'last_segment_end':last_end,'adjacent_segment_overlaps':overlaps,
                     'source_audio_sha256':receipt['sourceAudioSha256'],'text_sha256':outputs['transcript.txt']['sha256'],
                     'segments_sha256':outputs['segments.jsonl']['sha256'],'text_bytes':len(blobs['transcript.txt']),
                     'human_reviewed':receipt['humanReviewed'],'speaker_diarization_performed':receipt['speakerDiarizationPerformed']})
    primary=load(paths['primary'])
    for index,row in enumerate(primary['daniel']['items']):
        text=source_file(row['text']['raw_local_path'],row['text']).decode();checked_files+=1
        reported_words=len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b",text))
        assert reported_words==row['text']['word_count']
        docs.append({'source_id':f'daniel-item-{index:02d}','corpus':'authored','context':'full_rendered_RSS_item_including_promotion_footer',
                     'words':len(text.split()),'source_reported_regex_words':reported_words,'text_sha256':row['text']['sha256'],'text_bytes':row['text']['bytes']})
    row=primary['paul'];text=source_file(row['text']['raw_local_path'],row['text']).decode();checked_files+=1
    reported_words=len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b",text));assert reported_words==row['text']['word_count']
    docs.append({'source_id':'paul-birmingham-pdf','corpus':'authored','context':'publisher_issued_spiritual_Guides_transcript_not_biological_ET',
                 'words':len(text.split()),'source_reported_regex_words':reported_words,'pages':row['pages'],'text_sha256':row['text']['sha256'],'text_bytes':row['text']['bytes']})
    assert len({r['source_id'] for r in docs})==len(docs)
    asr=[r for r in docs if r['corpus']=='asr'];authored=[r for r in docs if r['corpus']=='authored']
    return {'schema_version':1,'status':'passed_with_recorded_observations','method':'Independent stdlib receipt/file hashing, text/segment exact joins and source-level totals; no author helper imported',
            'input_pins':{str(p.relative_to(ROOT)):sha(p) for p in paths.values()},'private_files_checked':checked_files,
            'summary':{'asr_recordings':len(asr),'asr_words':sum(r['words'] for r in asr),'asr_segments':sum(r['segments'] for r in asr),
                       'unique_audio_seconds':sum(r['audio_seconds'] for r in asr),'asr_word_min':min(r['words'] for r in asr),'asr_word_max':max(r['words'] for r in asr),
                       'asr_word_median':statistics.median(r['words'] for r in asr),'authored_publications':len(authored),'authored_words':sum(r['words'] for r in authored),
                       'daniel_RSS_words':sum(r['words'] for r in authored if r['source_id'].startswith('daniel-')),'paul_PDF_words':len(text.split()),
                       'authored_source_reported_regex_words':sum(r['source_reported_regex_words'] for r in authored)},
            'word_count_method':'words=Unicode whitespace split for every document; authored source_reported_regex_words separately replays collector regex',
            'observations':issues,'documents':docs,'raw_text_published':False,'network_requests':0,'new_llm_or_asr_inference':False}

if __name__=='__main__':
    report=build();(HERE/'source-baseline.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'private_files_checked':report['private_files_checked'],'summary':report['summary'],'observations':report['observations']},indent=2))
