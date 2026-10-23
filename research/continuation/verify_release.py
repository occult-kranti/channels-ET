#!/usr/bin/env python3
"""Check current source, packaged adapter, figures, manuscript and public byte closure."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PUBLIC = ROOT / 'dist/research'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    checks = []

    def check(ok, name):
        checks.append({'check': name, 'passed': bool(ok)})

    manifest = json.loads((HERE / 'paper/input-manifest.json').read_text())
    for name, expected in manifest['inputs'].items():
        check(sha((ROOT / name).read_bytes()) == expected, 'Paper source hash: ' + name)
    artifacts = json.loads((HERE / 'paper/artifact-manifest.json').read_text())
    for name, key in [('channels-et-paper.pdf', 'pdf_sha256'), ('channels-et-source.zip', 'source_zip_sha256')]:
        check(sha((HERE / 'paper' / name).read_bytes()) == artifacts[key], 'Paper artifact: ' + name)
    with zipfile.ZipFile(HERE / 'paper/channels-et-source.zip') as archive:
        for name in archive.namelist():
            source = HERE / 'paper' / name
            if name in ('aaai2027.sty', 'aaai2027.bst'):
                source = HERE / 'paper/vendor' / name
            check(source.is_file() and source.read_bytes() == archive.read(name), 'Manuscript ZIP member equals source: ' + name)
    bundle = json.loads((PUBLIC / 'data.json').read_text())
    for entry in bundle['artifacts']:
        blob = (PUBLIC / entry['path']).read_bytes()
        check(sha(blob) == entry['sha256'] and len(blob) == entry['bytes'], 'Public download binding: ' + entry['path'])
        check(blob == (ROOT / entry['source']).read_bytes(), 'Public download equals source: ' + entry['path'])
    for name in ('index.html', 'app.js', 'styles.css'):
        check((PUBLIC / name).read_bytes() == (HERE / 'dashboard' / name).read_bytes(), 'Public interface: ' + name)
    for figure in json.loads((HERE / 'analysis/generated/figure-captions.json').read_text()):
        for extension in ('pdf', 'svg', 'png'):
            name = figure['id'] + '.' + extension
            check((PUBLIC / 'figures' / name).read_bytes() == (HERE / 'analysis/generated/figures' / name).read_bytes(), 'Public figure: ' + name)
        name = figure['id'] + '.pdf'
        check((HERE / 'paper/generated/figures' / name).read_bytes() == (HERE / 'analysis/generated/figures' / name).read_bytes(), 'Manuscript analysis figure: ' + name)
    for name in ('concentration', 'caption-selection', 'keyword-duration'):
        check((HERE / 'paper/generated/figures' / ('retained-' + name + '.pdf')).read_bytes() == (ROOT / 'research/expansion/analysis/generated/figures' / (name + '.pdf')).read_bytes(), 'Manuscript retained figure: ' + name)
    package = json.loads((HERE / 'models/adapter-package.json').read_text())
    adapter_zip = HERE / 'models' / package['archive']
    check(sha(adapter_zip.read_bytes()) == package['sha256'], 'Released adapter ZIP')
    with zipfile.ZipFile(adapter_zip) as archive:
        for row in package['files']:
            check(sha(archive.read(row['file'])) == row['sha256'], 'Released adapter member: ' + row['file'])
        provenance = json.loads(archive.read('training-source-manifest.json'))
    for key, name in [('sourceQaSha256', ROOT / 'research/expansion/qa/qa-candidates.json'), ('splitSha256', HERE / 'models/split.json'), ('protocolSha256', HERE / 'models/protocol.json')]:
        check(provenance[key] == sha(name.read_bytes()), 'Adapter source binding: ' + key)
    split = json.loads((HERE / 'models/split.json').read_text())
    check(not {r['sourceGroupId'] for r in split['train']} & {r['sourceGroupId'] for r in split['test']}, 'Train/test quarantine groups disjoint')
    for row in provenance['train']:
        check(sha((ROOT / row['sourcePath']).read_bytes()) == row['sourceSha256'], 'Adapter input digest: ' + row['candidateId'])
    embedded_sources = {
        'analysis/results.json': 'analysis', 'models/predictions.json': 'predictions',
        'models/posthoc-diagnostics.json': 'modelDiagnostics', 'models/content-label-results.json': 'contentLabels',
        'models/current-family-smoke.json': 'currentFamily', 'models/option-order-results.json': 'optionOrder',
        'models/option-order-protocol.json': 'optionOrderProtocol', 'models/option-order-predictions.json': 'optionOrderPredictions',
        'models/annotation-comparison.json': 'annotationComparison', 'models/conditional-lexicon-sensitivity.json': 'lexiconSensitivity',
        'models/qwen35-content-label-results.json': 'newFamilyLabels',
        'models/qwen35-content-label-predictions.json': 'newFamilyLabelPredictions',
        'models/qwen35-content-label-protocol.json': 'newFamilyLabelProtocol',
    }
    for name, key in embedded_sources.items():
        check(bundle[key] == json.loads((HERE / name).read_text()), 'Embedded dashboard result: ' + name)
    reproduction = json.loads((HERE / 'analysis/generated/reproduction.json').read_text())
    check(reproduction['status'] == 'PASS' and reproduction['currentResultsSha256'] == sha((HERE / 'analysis/results.json').read_bytes()), 'Current numerical reproduction receipt')
    for row in reproduction['files']:
        check(row['identical'] and row['sha256'] == row['reproducedSha256'] == sha((HERE / 'analysis' / row['path']).read_bytes()), 'Current reproduced output: ' + row['path'])
    failures = [r for r in checks if not r['passed']]
    receipt = {'status': 'FAIL' if failures else 'PASS', 'checks': len(checks), 'failures': failures,
               'pdfSha256': artifacts['pdf_sha256'], 'sourceZipSha256': artifacts['source_zip_sha256'],
               'dashboardDataSha256': sha((PUBLIC / 'data.json').read_bytes()),
               'scope': 'Source and byte consistency; does not replay inference, verify claim truth, certify human review or establish hosted deployment.',
               'details': checks}
    (HERE / 'release-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'details'}, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
