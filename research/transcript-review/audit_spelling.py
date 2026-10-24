#!/usr/bin/env python3
"""Post-hoc exact-string retrieval sensitivity; variants are not verified identities."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
FAMILIES={'Essassani_Sassani_strict':['essassani','sassani','essassanis'],
          'Essassani_Sassani_posthoc_strings':['esasani','sasani'],
          'Ashtar_strict':['ashtar'],'Ashtar_posthoc_strings':['ashta','ashtalt','ashtara','ashtah']}
def normal(s):return unicodedata.normalize('NFKC',s).lower()
def build():
    receipts=json.loads((ROOT/'research/harvest/asr/summary.json').read_text())['records']+[json.loads((ROOT/'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json').read_text())]
    rows=[]
    for label,terms in FAMILIES.items():
        for term in terms:
            matches=[];documents=[]
            for receipt in receipts:
                directory=Path(receipt['transcriptDirectory']);text=(directory/'transcript.txt').read_text();pattern=r'\b'+re.escape(term)+r'\b'
                hits=len(re.findall(pattern,normal(text)))
                if not hits:continue
                documents.append(receipt['sourceId']);segments=[json.loads(x) for x in (directory/'segments.jsonl').read_text().splitlines() if x]
                for segment in segments:
                    count=len(re.findall(pattern,normal(segment['text'])))
                    if count:matches.append({'sourceId':receipt['sourceId'],'segmentId':segment['id'],'startSeconds':segment['start'],'endSeconds':segment['end'],'occurrences':count,'segmentTextSha256':hashlib.sha256(segment['text'].encode()).hexdigest()})
            rows.append({'family':label,'exact_string':term,'pattern':r'\b'+re.escape(term)+r'\b','occurrences':sum(r['occurrences'] for r in matches),
                         'document_count':len(documents),'sourceIds':documents,'segment_anchors':matches})
    return {'schema_version':1,'scope':'Post-hoc exact string retrieval sensitivity prompted by observed ASR spellings; no changes to strict preregistered dictionaries',
            'variant_identity_equivalence_verified':False,'audio_accuracy_checked':False,'speaker_identity_verified':False,
            'rows':rows,'new_network_requests':0,'new_llm_or_asr_inference':False,'raw_source_text_published':False}
if __name__=='__main__':
    result=build();(HERE/'spelling-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('family','exact_string','occurrences','document_count')} for r in result['rows']],indent=2))
