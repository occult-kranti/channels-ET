#!/usr/bin/env python3
"""Bind the final manuscript, unchanged figures and numerical receipts to sources.

This source-only check does not run model inference or import any producer.
Run after the manuscript owner has completed its final build.
"""
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAPER = ROOT / 'research/continuation/paper'
checks = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, label):
    checks.append({'check': label, 'passed': bool(condition)})


results_hash = sha(HERE / 'results.json')
verification = json.loads((HERE / 'generated/verification.json').read_text())
check(verification['status'] == 'PASS' and verification['resultsSha256'] == results_hash,
      'Core numerical verification binds to current results')
reproduction = json.loads((HERE / 'generated/reproduction.json').read_text())
check(reproduction['status'] == 'PASS' and reproduction['currentResultsSha256'] == results_hash,
      'Generic reproduction receipt binds to current results')
for item in reproduction['files']:
    check(item['identical'] and sha(HERE / item['path']) == item['sha256'] == item['reproducedSha256'],
          'Current numerical reproduction binding: ' + item['path'])

audits = {}
for name in ['benchmark-audit', 'model-diagnostics-audit', 'prompt-sensitivity-audit']:
    path = HERE / (name + '.json')
    audit = json.loads(path.read_text())
    check(audit['status'] == 'PASS' and audit['passed'] == audit['checks'], name + ' passes')
    for relative, expected in audit['inputs'].items():
        check(sha(ROOT / 'research/continuation/models' / relative) == expected,
              name + ' current input: ' + relative)
    audits[name] = {'sha256': sha(path), 'checks': audit['checks'], 'passed': audit['passed']}

manifest_path = PAPER / 'input-manifest.json'
manifest = json.loads(manifest_path.read_text())
for relative, expected in manifest['inputs'].items():
    check(sha(ROOT / relative) == expected, 'Final manuscript input: ' + relative)
for required in [
    'research/continuation/analysis/results.json',
    'research/continuation/models/option-order-results.json',
    'research/continuation/models/conditional-lexicon-sensitivity.json',
    'research/continuation/models/qwen35-content-label-results.json',
    'research/continuation/models/annotation-comparison.json',
]:
    check(required in manifest['inputs'], 'Final manuscript manifest includes ' + required)

previous = json.loads((HERE / 'generated/round11-receipt.json').read_text())
figures = []
for item in previous['figures']:
    identifier = item['id']
    path = HERE / 'generated/figures' / (identifier + '.pdf')
    current_hash = sha(path)
    check(current_hash == item['pdfSha256'], 'Figure unchanged since round 11: ' + identifier)
    check(current_hash == sha(PAPER / 'generated/figures' / (identifier + '.pdf')),
          'Manuscript figure exact source copy: ' + identifier)
    figures.append({'id': identifier, 'pdfSha256': current_hash, 'unchangedSinceRound11': True})

paper_path = PAPER / 'channels-et-paper.pdf'
info = subprocess.run(['pdfinfo', str(paper_path)], capture_output=True, text=True, check=True).stdout
pages = int(next(line.split(':', 1)[1] for line in info.splitlines() if line.startswith('Pages:')))
check(pages > 0, 'Final manuscript PDF has readable pages')
receipt = {
    'round': 12,
    'scope': 'Independent current source bindings and numerical reproduction; no semantic, human or physical validation.',
    'status': 'PASS' if all(row['passed'] for row in checks) else 'FAIL',
    'checks': len(checks),
    'passed': sum(row['passed'] for row in checks),
    'failed': [row for row in checks if not row['passed']],
    'resultsSha256': results_hash,
    'coreVerification': {'sha256': sha(HERE / 'generated/verification.json'), 'checks': verification['checks'], 'passed': verification['passed']},
    'numericalReproduction': {'sha256': sha(HERE / 'generated/reproduction.json'), 'identicalFiles': len(reproduction['files']), 'currentBindingVerified': reproduction['currentResultsSha256'] == results_hash and all(sha(HERE / item['path']) == item['sha256'] == item['reproducedSha256'] for item in reproduction['files'])},
    'modelAudits': audits,
    'paper': {'path': str(paper_path.relative_to(ROOT)), 'sha256': sha(paper_path), 'pages': pages, 'inputManifestSha256': sha(manifest_path)},
    'figures': figures,
    'details': checks,
}
output = HERE / 'generated/final-source-consistency.json'
output.write_text(json.dumps(receipt, indent=2))
print(json.dumps({key: value for key, value in receipt.items() if key not in ['details', 'figures', 'modelAudits']}))
raise SystemExit(receipt['status'] != 'PASS')
