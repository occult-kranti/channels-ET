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
harvest_view = ROOT / 'research/harvest/dashboard/harvest.js'
if harvest_view.exists():
    shutil.copyfile(harvest_view, OUT / 'harvest.js')

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
    'harvest': {'run': read(ROOT / 'research/harvest/summary.json'),
                'inventory': read(ROOT / 'research/harvest/inventory/summary.json'),
                'jobs': read(ROOT / 'research/harvest/jobs.json'),
                'attempts': read(ROOT / 'research/harvest/attempts.json'),
                'saved': read(ROOT / 'research/harvest/artifacts.json'),
                'channels': read(ROOT / 'research/harvest/inventory/channel-routes.json'),
                'rootProbe': read(ROOT / 'research/harvest/access/preflight-2026-10-23-revision5.json'),
                'publisherAudio': read(ROOT / 'research/harvest/publisher_sources/publisher-summary.json'),
                'asr': read(ROOT / 'research/harvest/asr/summary.json'),
                'accessRepair': {
                    'watchProbe': read(ROOT / 'research/access-repair/diagnostics/revision6-watch-probe.json'),
                    'proxyResponse': read(ROOT / 'research/access-repair/diagnostics/revision6-proxy-response.json'),
                    'browser': read(ROOT / 'research/access-repair/browser/verification-receipt.json'),
                    'primarySources': read(ROOT / 'research/access-repair/primary-sources/expanded-metadata.json'),
                    'athinaPublisher': read(ROOT / 'research/access-repair/athina/publisher_sources/publisher-summary.json'),
                    'athinaExecution': read(ROOT / 'research/access-repair/athina/asr/adapter-execution.json'),
                    'athinaAsr': read(ROOT / 'research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json'),
                }},
    'acquisition': None,
    'artifacts': [],
    'figures': [],
}

# Keep the interactive status payload compact. Full input/provenance and lease
# details remain in the separately downloadable, byte-bound job manifest.
harvest_jobs = bundle['harvest']['jobs']
if harvest_jobs and isinstance(harvest_jobs.get('records'), list):
    view_fields = ('id', 'kind', 'target_id', 'source_url', 'status', 'attempt_count',
                   'cursor_start', 'listing_end', 'complete_returned_public_listing_tree',
                   'error_class', 'error', 'updated_at', 'next_action')
    view_records = []
    for row in harvest_jobs['records']:
        record = {key: row[key] for key in view_fields if key in row}
        item = row.get('input') or {}
        record['input'] = {key: item[key] for key in ('title', 'publisher', 'people', 'entities') if key in item}
        result = row.get('result') or {}
        if row.get('kind') == 'channel':
            record['result'] = {key: result[key] for key in ('complete_returned_public_listing_tree', 'cursor_start', 'listing_end') if key in result}
        view_records.append(record)
    bundle['harvest']['jobs'] = {'schema_version': harvest_jobs.get('schema_version'),
                                 'projection': 'Dashboard operation fields; full source and lease provenance in harvest-jobs.json',
                                 'records': view_records}

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
    ('research/access-repair/diagnostics/revision6-watch-probe.json', 'access-repair-watch-probe.json', 'Revision 6 ordinary watch-page probe', 'One dated source probe; proxy tunnel denied before origin TLS'),
    ('research/access-repair/diagnostics/revision6-proxy-response.json', 'access-repair-proxy-response.json', 'Revision 6 proxy response diagnostic', 'Sanitized CONNECT status and response metadata; no alternate route'),
    ('research/access-repair/browser/verification-receipt.json', 'access-repair-browser-verification.json', 'Verified browser trust-repair controls', 'Allowed HTTPS controls and unrelated-certificate rejection; no browser profile'),
    ('research/access-repair/primary-sources/expanded-metadata.json', 'access-repair-primary-sources.json', 'Primary publisher text-source metadata', 'Daniel RSS items and Paul publisher PDF metadata; full text stays local'),
    ('research/access-repair/athina/publisher_sources/publisher-summary.json', 'access-repair-athina-audio.json', 'Separate Athina creator-audio receipt', 'One original creator RSS audio file; metadata and retained-byte hash only'),
    ('research/access-repair/athina/asr/adapter-execution.json', 'access-repair-athina-asr-execution.json', 'Separate Athina ASR execution receipt', 'Isolated follow-up branch; original 19-episode cohort unchanged'),
    ('research/access-repair/athina/asr/310c6d538a438cee6ba4-receipt.json', 'access-repair-athina-asr.json', 'Separate Athina full-audio ASR receipt', 'Machine transcript hashes and counts; no raw speech or transcript text'),
    ('research/harvest/summary.json', 'harvest-summary.json', 'Latest exported harvest run', 'Dated operation states, saved bytes and access outcomes'),
    ('research/harvest/jobs.json', 'harvest-jobs.json', 'Harvest job ledger', 'Recorded queues, attempts and terminal job states'),
    ('research/harvest/attempts.json', 'harvest-attempts.json', 'Harvest operation attempts', 'Worker leases; each operation can issue zero or several HTTP requests'),
    ('research/harvest/artifacts.json', 'harvest-artifacts.json', 'Saved raw-file manifest', 'Hashes and local-only paths; excludes raw media and captions'),
    ('research/harvest/inventory/summary.json', 'harvest-inventory-summary.json', 'Indexed source inventory summary', 'Offline extraction; does not establish source availability'),
    ('research/harvest/inventory/videos.jsonl', 'harvest-video-inventory.jsonl', 'Complete indexed video inventory', 'Source-linked metadata; indexed does not mean downloaded'),
    ('research/harvest/inventory/channel-routes.json', 'harvest-channel-routes.json', 'Complete literal account-route inventory', 'Explicit route provenance and known source edges'),
    ('research/harvest/inventory/edges.jsonl', 'harvest-source-edges.jsonl', 'Inventory source edges', 'Explicit source membership; no display-name identity merges'),
    ('research/harvest/inventory/queries.jsonl', 'harvest-query-inventory.jsonl', 'Distinct source search queries', 'Recorded query references; not executed search results'),
    ('research/harvest/inventory/inventory.sqlite', 'harvest-inventory.sqlite', 'Source inventory database', 'Metadata, provenance and explicit edges; SQLite'),
    ('research/harvest/access/preflight-2026-10-23-revision5.json', 'harvest-root-access-probe.json', 'Dated root watch-page access probe', 'One ordinary watch-page request; not all-video collection attempts'),
    ('research/harvest/publisher_sources/publisher-summary.json', 'harvest-publisher-audio.json', 'Independent publisher audio inventory', 'Original RSS enclosures; YouTube edition equivalence not established'),
    ('research/harvest/asr/summary.json', 'harvest-asr-summary.json', 'Automatic publisher-audio transcription receipts', 'Machine ASR metadata; no raw transcript text or human validation'),
    ('research/harvest/ACQUISITION-REPORT.md', 'harvest-acquisition-report.md', 'Acquisition supplement report', 'Dated source-acquisition report; retained manuscript remains separate'),
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
