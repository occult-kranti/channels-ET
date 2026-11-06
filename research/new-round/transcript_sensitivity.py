#!/usr/bin/env python3
"""Descriptive regrouping of existing transcript pair cosine tables; no raw text."""
import csv, hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TABLES=ROOT/'research/transcript-analysis/tables'
OUT=Path(__file__).resolve().parent

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sources_path=TABLES/'sources.csv'; pairs_path=TABLES/'audio-cosine-pairs.csv'
    with sources_path.open(newline='',encoding='utf-8') as f:
        sources={r['sourceId']:r for r in csv.DictReader(f) if r['modality']=='audio_asr'}
    groups={'bashar_same_publisher':[],'bashar_different_publisher':[],'ashtar_other':[],'other':[]}; seen=set(); publishers=set()
    with pairs_path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            a,b=sources[row['source']],sources[row['target']];key=tuple(sorted((a['sourceId'],b['sourceId'])))
            if key in seen or key[0]==key[1]: raise ValueError('Duplicate or self pair')
            seen.add(key); value=float(row['cosine'])
            if a['claimedGroup']==b['claimedGroup']=='Bashar-context':
                same=a['publisher']==b['publisher']; group='bashar_same_publisher' if same else 'bashar_different_publisher'
                if same: publishers.add(a['publisher'])
            elif 'Ashtar' in a['claimedGroup'] or 'Ashtar' in b['claimedGroup']: group='ashtar_other'
            else: group='other'
            groups[group].append(value)
    if len(seen)!=len(sources)*(len(sources)-1)//2: raise ValueError('Incomplete pair table')
    summary={k:{'pairs':len(v),'mean':statistics.mean(v) if v else None,'median':statistics.median(v) if v else None} for k,v in groups.items()}
    same=groups['bashar_same_publisher'];loomeans=[statistics.mean(same[:i]+same[i+1:]) for i in range(len(same))]
    result={'input_files':{str(p.relative_to(ROOT)):sha(p) for p in (sources_path,pairs_path)},'study':'descriptive regrouping of prior audio-ASR lexical cosine results','documents':len(sources),'unique_pairs':len(seen),'same_publisher_count':len(publishers),'groups':summary,'same_publisher_leave_one_pair_out_mean_range':[min(loomeans),max(loomeans)],'limitations':['Convenience sample and pairwise scores are dependent; not a significance test.', 'Publisher, episode, hosts, interview genre and repeated subject matter are confounded.', 'Single Ashtar-context source; 19 Bashar-context sources.', 'Existing ASR is not diarized or human-verified; lexical similarity is not agreement or truth.', 'No YouTube videos were downloaded in this descriptive regrouping.']}
    (OUT/'transcript-sensitivity.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
