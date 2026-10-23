#!/usr/bin/env python3
"""Close the final paper gate without repeating unchanged model inference."""
from pathlib import Path
from pypdf import PdfReader
import json, hashlib, datetime
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
A, B = (ROOT / 'research/paper/rounds' / f'round{x}' for x in (5, 6))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(name, passed):
    checks.append({'check': name, 'pass': bool(passed)})
check('Expected final PDF SHA', sha(B/'main.pdf') == 'c9e7b736f1604b1801b3dfe48919a7e4604343c92a7a29fde79c9574b7ac9716')
check('Expected final body SHA', sha(B/'body.tex') == 'b1d4d9628029c2f113a63051354d4ece525081c8121fedb464c067c1b21f6c21')
check('Only Aluna listing attribution changed in body', (B/'body.tex').read_text().replace('The Aluna Ash listing contained only one entry;', 'Aluna Ash supplied only one entry;') == (A/'body.tex').read_text())
check('Only Rystrom command grouping changed in bibliography', (B/'references.bib').read_text().replace(r'Rystr{\o}m', r'Rystr\o m') == (A/'references.bib').read_text())
check('Main TeX byte-identical', (A/'main.tex').read_bytes() == (B/'main.tex').read_bytes())
af = {str(p.relative_to(A/'generated')): p for p in (A/'generated').rglob('*') if p.is_file()}
bf = {str(p.relative_to(B/'generated')): p for p in (B/'generated').rglob('*') if p.is_file()}
check('Generated file inventory identical', set(af) == set(bf))
for name in sorted(af):
    check('Generated artifact byte-identical: ' + name, af[name].read_bytes() == bf[name].read_bytes())
pa, pb = PdfReader(A/'main.pdf'), PdfReader(B/'main.pdf')
check('Both PDFs contain 12 pages', len(pa.pages) == 12 and len(pb.pages) == 12)
changed = [i for i, (x, y) in enumerate(zip(pa.pages, pb.pages), 1) if x.extract_text() != y.extract_text()]
check('Only expected PDF pages have textual changes', changed == [4, 10])
render = Path('/workspace/scratch/9ec421627a96/paper_review/method_round6')
receipt = {
    'round': 6,
    'stage': 'final-frozen-manuscript-method-gate',
    'reviewer': '/root/method_panel',
    'reviewedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [B/'main.pdf', B/'main.tex', B/'body.tex', B/'references.bib', B/'generated/paper-results.json', B/'generated/chunk-weighting.json', B/'generated/chunk-weighted-embeddings.npz', ROOT/'dist/analysis/data.json']},
    'visuallyReviewedFinalPages': [4, 10],
    'visualEvidence': {str(p): sha(p) for p in sorted(render.glob('*.png'))},
    'priorVisualReview': 'Round-5 pages 4–9 and all four figures; final generated figures are byte-identical and PDF text outside pages 4/10 is unchanged.',
    'checks': checks,
    'checkCount': len(checks),
    'failures': sum(not c['pass'] for c in checks),
    'verdict': 'PASS — final methods and numerical/claim invariance gate closed; no open blocking finding.',
    'verificationScope': 'All 29 generated files compared byte-for-byte with independently checked round-5 artifacts. No redundant encoder inference or new analysis run.',
    'reviewSequence': [
        {'round': 4, 'pdfSha256': 'a395941231d063d3faab18f0ea90766438ed9c1135a612102b92f1edb6ee9bc1', 'outcome': 'Required figure and methods corrections.'},
        {'round': 5, 'pdfSha256': 'b009dbb772b562494d27251239334c42a70934424ac74bc2c5230f06f7bc2be0', 'outcome': 'Corrections closed; 231 independent derivative checks passed.'},
        {'round': 6, 'pdfSha256': sha(B/'main.pdf'), 'outcome': 'Final freeze and actual changed pages checked; numerical and substantive result claims invariant.'}
    ],
    'limitationsRetained': ['Exploratory purposive sample; no global count or population inference.', 'No independent raw-text inference replay by this reviewer; derived vectors and statistics independently verified.', 'No human validation, authorship approval, venue acceptance or submission is claimed.']
}
assert receipt['failures'] == 0, [c for c in checks if not c['pass']]
(OUT/'round6-final-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'checks': len(checks), 'failures': receipt['failures'], 'generatedFilesUnchanged': len(af), 'pdfSha256': sha(B/'main.pdf')}))
