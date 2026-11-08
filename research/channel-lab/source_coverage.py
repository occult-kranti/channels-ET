#!/usr/bin/env python3
"""Bind existing public collection ledgers without conflating their counting units."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(root):
    root=Path(root);data=json.loads((root/'collection-coverage.json').read_text())
    registry=json.loads((root/'registry.json').read_text())
    if data['registry_sha256']!=digest(root/'registry.json'):raise ValueError('Collection coverage registry binding differs')
    channels={r['channel_id']:r for r in registry['channels']};seen=set()
    for r in data['channels']:
        cid=r['channel_id']
        if cid in seen or cid not in channels:raise ValueError('Invalid coverage channel')
        seen.add(cid)
        if r['canonical_frame_counts']!=channels[cid]['counts'] or r['uploaded_total'] is not None:raise ValueError('Coverage units/basis differs')
        if not r['source_binding']['url'].startswith('https://occult-kranti.github.io/channels-ET/dist/'):raise ValueError('Unrecognized ledger location')
        if any(not isinstance(v,(int,float)) or v<0 for v in r['upstream_collection_counts'].values()):raise ValueError('Invalid upstream count')
    return {'status':'passed_collection_metadata_checks','contexts':len(seen)}


def build(output):
    output=Path(output);registry=json.loads((output/'registry.json').read_text())
    old_path=ROOT/'dist/bashar-ra/collection.json';pub_path=ROOT/'dist/subscription-audit/acquisition.json'
    old=json.loads(old_path.read_text());pub=json.loads(pub_path.read_text());rows=[]
    def binding(path):
        return {'url':'https://occult-kranti.github.io/channels-ET/'+str(path.relative_to(ROOT)),
                'sha256':digest(path),'bytes':path.stat().st_size}
    ra=old['corpora']['ra'];bashar=old['corpora']['bashar']
    rows.append({'channel_id':'ra-law-of-one','upstream_collection_counts':{
        'retained_linked_audio_segments':ra['audio_downloaded'],'unique_linked_audio_segments':ra['unique_audio_sources'],
        'published_session_texts':ra['transcripts_downloaded'],'retained_audio_files_including_preserved_original':ra['retained_audio_files'],
        'decoded_audio_hours':ra['audio_hours']},'source_binding':binding(old_path),
        'scope':'Audio counts are linked segments, not whole-session recordings. Canonical text frame does not assert word/timestamp alignment; zero direct session-level joins does not mean absent audio.'})
    rows.append({'channel_id':'bashar-official','upstream_collection_counts':{
        'retained_publication_audio_records':bashar['official_audio_retained'],
        'unique_encoded_audio_families':bashar['official_unique_encoded_audio_hashes'],
        'profile_publication_ids_in_selected_census':bashar['official_profile_ids']},'source_binding':binding(old_path),
        'scope':'Official profile census and retained publication/audio-family counts differ from 82 canonical English modeled texts. No YouTube edition equivalence or lifetime all-account census.'})
    mapping={'akanksshaa':'multidimensional-soul','tracykumbera':'tracy-kumbera','natalie glasson / omna':'natalie-glasson-omna'}
    for c in pub['channels']:
        q=c['related_publisher_material']
        rows.append({'channel_id':mapping[c['id']],'upstream_collection_counts':{
            'retained_publication_audio_records':q['current_new_audio_sources_retained'],
            'unique_original_encoded_audio_families':q['current_new_audio_exact_original_families'],
            'retained_audio_bytes':q['current_new_audio_retained_bytes'],
            'decoded_audio_seconds':q['current_new_audio_decoded_seconds'],
            'accepted_local_asr_editions':q['current_new_audio_local_asr'],
            'publisher_caption_links':q['current_new_audio_caption_linked'],
            'written_message_links':q['current_new_audio_written_message_linked']},
            'source_binding':binding(pub_path),'scope':q['scope']})
    by={c['channel_id']:c for c in registry['channels']}
    for r in rows:
        r['canonical_frame_counts']=by[r['channel_id']]['counts'];r['uploaded_total']=None
    result={'schema_version':1,'registry_sha256':digest(output/'registry.json'),
        'counting_rule':'Parallel denominators from explicitly bound ledgers; never add them as distinct media or divide them into a lifetime-completion percentage.',
        'channels':rows,'limitations':['Rows without upstream_collection_counts are unknown, not zero.',
            'Retained archive, direct text/media joins, modeled canonical texts and YouTube uploads are separate units.',
            'Publicly accessible independent publisher material is not counted as a YouTube download.']}
    target=output/'collection-coverage.json'
    if target.exists():raise ValueError('Coverage editions are immutable; use a fresh directory')
    target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    manifest=output/'output-manifest.json';m=json.loads(manifest.read_text())
    m['public_allowlist'].append({'file':target.name,'bytes':target.stat().st_size,'sha256':digest(target)})
    manifest.write_text(json.dumps(m,separators=(',',':'))+'\n')
    verify(output)
    print(json.dumps({'file':str(target),'sha256':digest(target),'contexts':len(rows)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);build(p.parse_args().output)
