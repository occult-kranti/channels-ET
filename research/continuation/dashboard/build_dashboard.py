#!/usr/bin/env python3
"""Build the continuation research UI without copying raw text or model weights."""
from pathlib import Path
import hashlib, json, shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONT = ROOT / 'research/continuation'
OUT = ROOT / 'dist/research'
OUT.mkdir(exist_ok=True)
for name in ('index.html', 'app.js', 'styles.css'):
    shutil.copyfile(HERE / name, OUT / name)

def read(path):
    return json.loads(path.read_text()) if path.exists() else None

def publish(source, target):
    if not source.exists(): return None
    dest = OUT / target
    dest.parent.mkdir(exist_ok=True, parents=True)
    shutil.copyfile(source, dest)
    raw = dest.read_bytes()
    return {'path': target, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

baseline = read(ROOT / 'dist/analysis/data.json')
qa = read(ROOT / 'research/expansion/qa/summary.json')
bundle = {
    'schemaVersion': 1,
    'source': {'repository': 'occult-kranti/channels-ET', 'historicalRepository': 'occult-kranti/bashar-index',
               'baselineSha256': hashlib.sha256((ROOT / 'dist/analysis/data.json').read_bytes()).hexdigest(),
               'unit': 'Curated uploads, publishing groups and derived candidate summaries; not a census of mediums'},
    'baseline': {'coverage': baseline['coverage'], 'channels': baseline['channels'],
                 'captionPilot': baseline['transcripts']['englishPilotCount'], 'qa': qa['coverage'] if qa else None},
    'analysis': read(CONT / 'analysis/results.json'),
    'models': None,
    'modelHardware': read(CONT / 'models/hardware.json'),
    'modelRunStatus': read(CONT / 'models/run-status.json'),
    'modelProtocol': read(CONT / 'models/protocol.json'),
    'predictions': read(CONT / 'models/predictions.json'),
    'modelDiagnostics': read(CONT / 'models/posthoc-diagnostics.json'),
    'contentLabels': read(CONT / 'models/content-label-results.json'),
    'contentLabelPredictions': read(CONT / 'models/content-label-predictions.json'),
    'currentFamily': read(CONT / 'models/current-family-smoke.json'),
    'lengthAudit': read(CONT / 'models/length-audit.json'),
    'optionOrder': read(CONT / 'models/option-order-results.json'),
    'optionOrderProtocol': read(CONT / 'models/option-order-protocol.json'),
    'optionOrderPredictions': read(CONT / 'models/option-order-predictions.json'),
    'annotationComparison': read(CONT / 'models/annotation-comparison.json'),
    'lexiconSensitivity': read(CONT / 'models/conditional-lexicon-sensitivity.json'),
    'newFamilyLabels': read(CONT / 'models/qwen35-content-label-results.json'),
    'newFamilyLabelPredictions': read(CONT / 'models/qwen35-content-label-predictions.json'),
    'newFamilyLabelProtocol': read(CONT / 'models/qwen35-content-label-protocol.json'),
    'acquisition': None,
    'artifacts': [],
    'figures': [],
}

# Only explicit derived result files are eligible for publication. Never glob
# local training corpora, model/checkpoint files or caption directories.
for filename in ('results.json', 'experiment-results.json', 'benchmark-results.json'):
    path = CONT / 'models' / filename
    if path.exists():
        bundle['models'] = read(path)
        publish(path, 'model-results.json')
        break
for filename in ('acquisition-status.json', 'acquisition-summary.json', 'summary.json', 'collection-status.json'):
    path = CONT / 'acquisition' / filename
    if path.exists():
        bundle['acquisition'] = read(path)
        publish(path, 'acquisition-summary.json')
        if bundle['acquisition'].get('candidate_status'):
            inherited = read(ROOT / 'research/expansion/qa/practitioner-coverage.json')
            coverage_by_id = {r['id']: r for r in inherited['records']} if inherited else {}
            records = []
            for row in bundle['acquisition']['candidate_status']:
                old = coverage_by_id.get(row['candidate_id'], {})
                records.append(dict(row, contextEntityLabels=old.get('contextEntityLabels', []),
                                    inheritedQACandidates=old.get('qaCandidateCount'),
                                    inheritedSourceUrl=(old.get('sourceUrls') or [None])[0]))
            bundle['channelProgress'] = {'records': records, 'unit': 'Inherited candidate; per-candidate requests stay distinct from general access probes', 'attributionJoin': 'Exact inherited candidate ID; no inferred speaker or entity joins'}
            (OUT / 'channel-progress.json').write_text(json.dumps(bundle['channelProgress'], ensure_ascii=False, separators=(',', ':')))
        break
for filename in ('channel-progress.json', 'practitioner-progress.json', 'collection-manifest.json'):
    path = CONT / 'acquisition' / filename
    if path.exists():
        bundle['channelProgress'] = read(path)
        publish(path, 'channel-progress.json')
        break
figure_manifest = read(CONT / 'analysis/generated/figure-captions.json')
if figure_manifest:
    for f in figure_manifest:
        path = CONT / 'analysis/generated/figures' / (f['id'] + '.png')
        if path.exists():
            for ext in ('.png', '.pdf', '.svg'):
                publish(path.with_suffix(ext), 'figures/' + f['id'] + ext)
            bundle['figures'].append({'id': f['id'], 'path': 'figures/' + path.name,
                                      'title': f['title'], 'caption': f['caption']})
published_targets = set()
for source, target, label, kind in [
    ('research/continuation/analysis/results.json', 'analysis-results.json', 'Continuation analysis results', 'Derived numeric JSON'),
    ('research/continuation/models/results.json', 'model-results.json', 'Local-model experiment results', 'Executed / failed states and outputs'),
    ('research/continuation/models/benchmark-results.json', 'model-results.json', 'Local-model experiment results', 'Executed / failed states and outputs'),
    ('research/continuation/models/training-receipt.json', 'training-receipt.json', 'Local adapter training receipt', 'Actual steps, parameters and measured run'),
    ('research/continuation/models/predictions.json', 'predictions.json', 'Recorded model predictions', 'Model-generated experimental outputs'),
    ('research/continuation/models/qwen-digest-lora-pilot.zip', 'qwen-digest-lora-pilot.zip', 'Experimental LoRA pilot adapter', 'Requires pinned Qwen base; not a validated domain model'),
    ('research/continuation/models/posthoc-diagnostics.json', 'posthoc-diagnostics.json', 'Post-hoc control and citation diagnostics', 'Exploratory output inspection, original scores preserved'),
    ('research/continuation/models/content-label-results.json', 'content-label-results.json', 'Local model text-label experiment', 'Model/dictionary concordance, not human accuracy'),
    ('research/continuation/models/content-label-predictions.json', 'content-label-predictions.json', 'Raw text-label model outputs', 'Model-generated annotations on digest gists'),
    ('research/continuation/models/current-family-smoke.json', 'current-family-smoke.json', 'Current-family model smoke receipt', 'Separate text-only task, not the five-arm benchmark'),
    ('research/continuation/models/length-audit.json', 'length-audit.json', 'Prompt and generation-length audit', 'Cap hits and truncation states'),
    ('research/continuation/models/option-order-results.json', 'option-order-results.json', 'Annotation option-order sensitivity', 'Paired model-output stability, not human accuracy'),
    ('research/continuation/models/option-order-protocol.json', 'option-order-protocol.json', 'Option-order sensitivity protocol', 'Same cases and budget; only the theme-option order changes'),
    ('research/continuation/models/option-order-predictions.json', 'option-order-predictions.json', 'Original and reversed-option outputs', 'Same 12 source-bound cases, failures retained'),
    ('research/continuation/models/annotation-comparison.json', 'annotation-comparison.json', 'Three-condition annotation diagnostics', 'Exact substrings, word-length compliance and constant-label baseline'),
    ('research/continuation/models/conditional-lexicon-sensitivity.json', 'conditional-lexicon-sensitivity.json', 'Conditional-keyword rule sensitivity', 'Post-hoc lexical comparison on 949 digest answers'),
    ('research/continuation/models/qwen35-content-label-results.json', 'qwen35-content-label-results.json', 'Newer-family digest-label comparison', 'Separate operational condition, no human accuracy'),
    ('research/continuation/models/qwen35-content-label-predictions.json', 'qwen35-content-label-predictions.json', 'Newer-family raw annotation outputs', 'Same 12 source-bound digest cases'),
    ('research/continuation/models/qwen35-content-label-protocol.json', 'qwen35-content-label-protocol.json', 'Newer-family annotation protocol', 'Exact prompt, budget and operational differences'),
    ('research/continuation/models/hardware.json', 'hardware.json', 'Recorded compute environment', 'CPU / CUDA and package versions'),
    ('research/continuation/models/protocol.json', 'model-protocol.json', 'Prospective model-pilot protocol', 'Exploratory, not preregistered'),
    ('research/continuation/models/split.json', 'model-split.json', 'Model pilot source split', 'Quarantine-source grouping and example IDs'),
    ('research/continuation/models/model-metadata.json', 'model-metadata.json', 'Pinned model metadata', 'Public upstream metadata'),
    ('research/continuation/acquisition/acquisition-status.json', 'acquisition-summary.json', 'Acquisition evidence summary', 'Observed access, not live status'),
    ('research/continuation/acquisition/acquisition-summary.json', 'acquisition-summary.json', 'Acquisition evidence summary', 'Observed access, not live status'),
    ('research/continuation/acquisition/corpus-index.sqlite', 'corpus-index.sqlite', 'Source corpus index', 'Metadata and actual transcript-artifact states'),
    ('research/expansion/qa/qa-candidates.sqlite', 'qa-candidates.sqlite', 'Q&A candidate database', 'Derived digest paraphrases, SQLite'),
    ('research/expansion/qa/summary.json', 'qa-summary.json', 'Q&A coverage and methods', '949 inherited digest candidates'),
    ('research/continuation/paper/channels-et-paper.pdf', 'paper.pdf', 'Current working paper PDF', 'Exploratory manuscript'),
    ('research/continuation/paper/channels-et-source.zip', 'source.zip', 'Current manuscript source ZIP', 'Portable manuscript sources'),
]:
    if target in published_targets: continue
    record = publish(ROOT / source, target)
    if record:
        bundle['artifacts'].append(dict(record, label=label, kind=kind, source=source))
        published_targets.add(target)

(OUT / 'data.json').write_text(json.dumps(bundle, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
print(json.dumps({'output': str(OUT), 'hasAnalysis': bundle['analysis'] is not None,
                  'hasModels': bundle['models'] is not None, 'hasAcquisition': bundle['acquisition'] is not None,
                  'artifacts': len(bundle['artifacts'])}))
