#!/usr/bin/env python3
"""Publish a portable explorer from the retained evidence and expansion outputs."""
from pathlib import Path
import hashlib, json, shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'dist/expansion'
OUT.mkdir(exist_ok=True)
for name in ('index.html', 'styles.css', 'app.js'):
    shutil.copyfile(HERE / name, OUT / name)
snapshot = json.loads((ROOT / 'dist/analysis/data.json').read_text())
data = {
    'meta': {
        'title': 'Channeling Atlas · Evidence explorer',
        'evidenceCutoff': snapshot['meta']['checkedAt'],
        'baselineSha256': hashlib.sha256((ROOT / 'dist/analysis/data.json').read_bytes()).hexdigest(),
        'classification': 'Public-source convenience sample; model-generated digest paraphrases',
    },
    'coverage': snapshot['coverage'], 'channels': snapshot['channels'],
    'videos': snapshot['videos'], 'topics': snapshot['topics'],
    'transcripts': {k: v for k, v in snapshot['transcripts'].items() if k in ('attempted', 'available', 'englishPilotCount', 'rows', 'selection', 'method')},
}
(OUT / 'evidence.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
expansion = ROOT / 'research/expansion'
qa_path = expansion / 'qa/qa-candidates.json'
summary_path = expansion / 'qa/summary.json'
if qa_path.exists() and summary_path.exists():
    raw = json.loads(qa_path.read_text())
    summary = json.loads(summary_path.read_text())
    theme_labels = {t['id']: t['label'] for t in summary['themes']}
    qa = {'meta': raw['meta'], 'coverage': summary['coverage'], 'themes': summary['themes'], 'sensitivity': summary.get('sensitivity', {}), 'pairPreview': {'source': 'summary.questionPairs', 'sourcePreviewCount': len(summary['questionPairs']), 'fullPairCount': summary['coverage']['questionSimilarityPairsAt040'], 'displayedCount': min(10, len(summary['questionPairs']))}, 'records': [], 'pairs': []}
    for q in raw['records']:
        qa['records'].append({
            'id': q['id'], 'videoId': q['videoId'], 'url': q['sourceUrl'],
            'question': q['question'], 'answer': q['answerGist'],
            'themes': sorted({theme_labels.get(t, t) for t in q['questionThemes'] + q['answerThemes']}),
            'publisher': q['publisherName'], 'publisherId': q['publisherId'],
            'practitioner': ', '.join(q['practitionerNames']),
            'entityStatus': 'Entity label is contextual; speaker not verified',
            'timestamp': q['timestampSeconds'], 'evidenceType': q['evidenceType'],
            'sourcePath': q['sourcePath'], 'sourcePointer': q['sourcePointer'],
            'sourceSha256': q['sourceSha256'], 'speakerVerified': q['speakerVerified'],
            'humanReviewed': q['humanReviewed'],
        })
    qa['pairs'] = [{'questionA': p['leftQuestion'], 'questionB': p['rightQuestion'],
                    'similarity': p['questionCosine'], 'answerCosine': p['answerCosine'],
                    'leftId': p['leftId'], 'rightId': p['rightId'],
                    'leftVideoId': p['leftVideoId'], 'rightVideoId': p['rightVideoId'],
                    'answerAgreement': p['answerAgreement'],
                    'originalSessionIndependence': p['originalSessionIndependence']}
                   for p in summary['questionPairs']]
    (OUT / 'qa.json').write_text(json.dumps(qa, ensure_ascii=False, separators=(',', ':')))
    for name in ('summary.json', 'practitioner-coverage.json', 'close-reading.json', 'question-pairs.json', 'pair-close-reading.json'):
        if not (expansion / 'qa' / name).exists(): continue
        shutil.copyfile(expansion / 'qa' / name, OUT / ('qa-' + name))
    for name in ('qa-candidates.csv', 'question-pairs.csv', 'qa-candidates.sqlite'):
        if (expansion / 'qa' / name).exists():
            shutil.copyfile(expansion / 'qa' / name, OUT / name)
for source, target in [('collection-plan.json', 'collection-plan.json'), ('identity-map.json', 'identity-map.json'), ('acquisition-summary.json', 'acquisition-status.json'), ('preflight-initial.json', 'acquisition-preflight.json'), ('practitioner-frame.json', 'practitioner-frame.json')]:
    path = expansion / 'acquisition' / source
    if path.exists(): shutil.copyfile(path, OUT / target)
analysis_path = expansion / 'analysis/results.json'
if analysis_path.exists():
    analysis = json.loads(analysis_path.read_text())
    figures = []
    figures_dir = expansion / 'analysis/generated/figures'
    captions_path = expansion / 'analysis/generated/figure-captions.json'
    if captions_path.exists():
        (OUT / 'figures').mkdir(exist_ok=True)
        for figure in json.loads(captions_path.read_text()):
            path = figures_dir / (figure['id'] + '.png')
            if not path.exists(): continue
            for suffix in ('.png', '.pdf', '.svg'):
                if path.with_suffix(suffix).exists(): shutil.copyfile(path.with_suffix(suffix), OUT / 'figures' / path.with_suffix(suffix).name)
            figures.append({'path': 'figures/' + path.name, 'title': figure['title'], 'alt': figure['title'], 'caption': figure['caption']})
    analysis['figures'] = figures
    (OUT / 'diagnostics.json').write_text(json.dumps(analysis, ensure_ascii=False, separators=(',', ':')))
for source, target in [('channeling-atlas-expansion-paper.pdf', 'paper.pdf'), ('channeling-atlas-expansion-source.zip', 'source.zip')]:
    path = expansion / 'paper' / source
    if path.exists(): shutil.copyfile(path, OUT / target)
print(json.dumps({'published': str(OUT), 'videos': len(data['videos']), 'accounts': len(data['channels'])}))
