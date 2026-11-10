#!/usr/bin/env python3
"""Build a self-contained, deterministic public metadata bundle; raw corpus excluded."""
import argparse, hashlib, io, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
FILES=('dataset.json','documents.jsonl','editions.jsonl','media.jsonl','youtube-accounts.jsonl','youtube-videos.jsonl','youtube-account-video-links.jsonl','channels.csv','schema.json')
VERSION='2026-11-08'
FRAME_SHA='3eb35b14a9067e9e162862ed030c15d5b7646a38b3060ac85686f4604eb2c9c4'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()

def package(out):
    out.mkdir(parents=True,exist_ok=True);source=ROOT/'dist/dataset-submission';dataset=json.loads((source/'dataset.json').read_text())
    if dataset['frame_sha256']!=FRAME_SHA:raise ValueError('Frozen frame changed; explicit package migration required')
    members={name:(source/name).read_bytes()for name in FILES}
    for name,raw in members.items():
        if any(marker in raw for marker in [b'/workspace/',b'/dev/shm/',b'/tmp/',b'"text":']):raise ValueError('Private content in metadata: '+name)
    rights='''# Rights and access\n\nThe repository MIT license applies to curator-written code, documentation and derived data covered by that license. See LICENSE.txt. Source-provided titles, short labels, URLs, metadata and attribution are preserved for provenance; their inclusion does not transfer ownership of the sources.\n\nNo license is granted here for third-party audio, video, transcripts, captions, books, artwork or full publisher-written messages. Those materials are excluded from this public metadata bundle. Full media/text is retained in a private research archive pending documented, source-specific redistribution rights. Fields such as source_license=not_established_for_redistribution describe this unresolved source-content state; they do not license the source.\n\nA source being publicly accessible, downloadable, mirrored, or linked from YouTube does not create a redistribution license. Publisher-page audio/text cooccurrence does not establish audiovisual equivalence or word alignment. Requests for correction, source removal or permission evidence should identify the source_id, edition_id and source URL through the repository issue tracker.\n\nRepository: https://github.com/occult-kranti/channels-ET\nPrivate raw archive repository: access and transfer status are reported separately; this package does not imply public raw availability.\n'''
    readme='''# Channeling discourse dataset — public metadata release\n\nVersion: 2026-11-08. This downloadable package contains public metadata and provenance, not the full-text/media corpus. The frozen selected frame has 683 publication/body units, 694 edition-lineage rows and 1,599,556 selected words. There are 26 publisher contexts and 14 source-attributed creator contexts. The discovery inventory contains 2,812 observed YouTube IDs and 297 account references; no complete lifetime upload denominator was observed. Zero YouTube downloads are attributed to this inventory.\n\n## Files\n\n- dataset.json: self-contained summary, document metadata, publisher-context coverage, edition lineage, joined media metadata, caveats and input bindings.\n- documents.jsonl: one selected publication/body record per line; full text is excluded.\n- editions.jsonl: all 694 accepted edition records, including 11 unselected alternatives.\n- media.jsonl: 533 physically retained encoded media linked to selected publications; source hashes and relationships, not file bytes. Ra segment archives are a separate collection denominator.\n- youtube-accounts.jsonl, youtube-videos.jsonl, youtube-account-video-links.jsonl: all discovery observations and source-bound links; unresolved routes remain unresolved.\n- channels.csv: publisher-context denominators, not a verified YouTube uploader census; blank lifetime totals mean unknown.\n- schema.json: observation units, normalization, identity rules and public/private separation.\n- DATASHEET.md and RIGHTS.md: collection, scope, limitations, sensitive-content considerations and rights.\n- deposit-metadata.json: repository deposit draft; authors, author identifiers and DOI remain explicitly unresolved. It is not a completed DOI registration.\n- checksums.txt: SHA-256 hashes for every other member.\n\n## Integrity and use\n\nRun `sha256sum -c checksums.txt` after extraction. Read JSONL line by line with any JSON parser; the bundle requires no downloader or local model. Full private source-bound texts and the searchable SQLite database are excluded. The selected frame SHA-256 is 3eb35b14a9067e9e162862ed030c15d5b7646a38b3060ac85686f4604eb2c9c4.\n\nDo not interpret publisher context as speaker identity, a claimed entity as authenticated, written editions as verbatim speech, or topic similarity as identity/causal evidence. ASR word error rate is unmeasured. Unknown date/total fields are not zero. Two new OmNa editions were joined to existing articles only after exact individual-URL and whitespace-folded body equality; all alternatives remain preserved.\n\nSource and build code: https://github.com/occult-kranti/channels-ET/tree/main/research/dataset-submission\nDashboard: https://occult-kranti.github.io/channels-ET/dist/dataset-submission/\n'''
    metadata={'metadata_status':'draft_not_deposited','resource_type':'dataset','title':'A Source-Bound Dataset of Publisher-Attributed Channeling Discourse',
        'version':VERSION,'publication_date':VERSION,'creators':[],'creators_status':'TBD: author names, order, affiliations and ORCIDs require author confirmation before deposit',
        'doi':None,'doi_status':'TBD: no DOI registered or reserved by this build','related_identifiers':[{'identifier':'https://github.com/occult-kranti/channels-ET','relation':'isSupplementTo','scheme':'url'}],
        'description':'Public metadata and provenance for 683 selected publication/text units, 694 textual editions and 1,599,556 selected words; 2,812 observed YouTube IDs and 297 account references. Third-party full text and media excluded.',
        'language':'eng','keywords':['computational social science','dataset provenance','YouTube metadata','channeling discourse','transcript origins','edition reconciliation'],
        'access_right':'open_for_this_metadata_bundle_only','license':'MIT for curator-derived data/code covered by repository license; source content excluded',
        'license_source_url':'https://github.com/occult-kranti/channels-ET/blob/main/LICENSE',
        'source_content_access':'private; source-specific redistribution rights unresolved','source_content_license':None,
        'conference_submission_status':'working dataset-paper draft; no submission or acceptance claim',
        'frozen_frame_sha256':FRAME_SHA,'counts':dataset['summary'],
        'required_before_repository_deposit':['Confirm all authors, order, affiliations and ORCIDs','Confirm source-content exclusions and metadata rights description','Select archive/community and register or reserve actual DOI','Record actual public archive URL and verify downloaded checksums']}
    members.update({'README.md':readme.encode(),'DATASHEET.md':Path(__file__).with_name('DATASHEET.md').read_bytes(),'RIGHTS.md':rights.encode(),
        'LICENSE.txt':(ROOT/'LICENSE').read_bytes(),'deposit-metadata.json':encode(metadata)})
    checks=''.join(sha(raw)+'  '+name+'\n' for name,raw in sorted(members.items()))
    members['checksums.txt']=checks.encode()
    zipname='channeling-discourse-metadata-'+VERSION+'.zip';buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,raw)
    zipraw=buf.getvalue()
    with zipfile.ZipFile(io.BytesIO(zipraw))as z:
        if z.testzip()is not None:raise ValueError('ZIP CRC validation failed')
        for name,raw in members.items():
            if z.read(name)!=raw:raise ValueError('ZIP member mismatch')
    outputs={zipname:zipraw,'metadata-deposit-draft.json':encode(metadata),'metadata-datasheet.md':members['DATASHEET.md'],
             'metadata-rights.md':members['RIGHTS.md'],'metadata-README.md':members['README.md'],
             'metadata-checksums-'+VERSION+'.txt':checks.encode()}
    outputs['metadata-release-'+VERSION+'.json']=encode({'schema_version':1,'version':VERSION,'frame_sha256':FRAME_SHA,
        'scope':'Public metadata only; excludes full source bodies and media','bundle':{'file':zipname,'bytes':len(zipraw),'sha256':sha(zipraw)},
        'members':[{'file':n,'bytes':len(raw),'sha256':sha(raw)}for n,raw in sorted(members.items())],
        'doi':None,'doi_status':'TBD_not_registered','authors_status':'TBD_before_deposit','validation':'ZIP CRC, exact member bytes and SHA256 checksums verified'})
    refs=[]
    for name,raw in outputs.items():(out/name).write_bytes(raw);refs.append({'file':name,'bytes':len(raw),'sha256':sha(raw)})
    (out/'output-manifest.json').write_bytes(encode({'schema_version':1,'producer':'dataset_public_package','frame_sha256':FRAME_SHA,'public_allowlist':refs}))
    print(json.dumps({'output':str(out),'public_artifacts':len(refs),'bundle_bytes':len(zipraw),'bundle_sha256':sha(zipraw),'members':len(members)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('/workspace/channels-et-private/dataset-submission-2026-11/dataset-public'));package(p.parse_args().out)
