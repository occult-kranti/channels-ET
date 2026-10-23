#!/usr/bin/env python3
"""Independently bind a named final paper/package to their public copies.

File, schema and arithmetic checks do not replace visual or human validation.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import zipfile

H = pathlib.Path(__file__).resolve().parent
R = H.parents[2]
C = H.parent
P = C / 'paper'
D = R / 'dist/research'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pdf-sha256', required=True)
parser.add_argument('--zip-sha256', required=True)
args = parser.parse_args()
checks = []
hashes = {}


def digest(path):
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes[str(path.relative_to(R))] = value
    return value


def ck(ok, label, actual=None, expected=None):
    checks.append({'check': label, 'passed': bool(ok), 'actual': actual, 'expected': expected})


def eq(a, b, label):
    ck(a == b, label, a, b)


pdf = P / 'channels-et-paper.pdf'
package = P / 'channels-et-source.zip'
eq(digest(pdf), args.pdf_sha256, 'explicitly named definitive PDF')
eq(digest(package), args.zip_sha256, 'explicitly named definitive source ZIP')
eq(digest(D / 'paper.pdf'), args.pdf_sha256, 'public paper bytes identical')
eq(digest(D / 'source.zip'), args.zip_sha256, 'public source ZIP bytes identical')
info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
pages = int(re.search(r'^Pages:\s*(\d+)', info, re.M)[1])
eq(pages, 16, 'sixteen actual PDF pages')
text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
reading_text = subprocess.check_output(['pdftotext', str(pdf), '-'], text=True)
normalized = ' '.join(re.sub(r'(?<=[A-Za-z])-\s*\n\s*(?=[A-Za-z])', '', reading_text).split())
for phrase in ['6 change primary theme', '0/9 parseable outputs', '60 to 58 among 949',
               '5/12 exact answer', '6/12 dictionary concordance', 'always-yes result',
               '10 are exact contiguous', '5 of those exceed eight words', '2 nonexact',
               'twenty single-candidate and twelve paired',
               'All paired answer-agreement fields remain undetermined',
               'not a conventional factual RAG benchmark', 'first-in-field claim']:
    ck(phrase in normalized, 'actual PDF claim/caveat retained: ' + phrase)

with zipfile.ZipFile(package) as archive:
    names = archive.namelist()
    eq(len(names), len(set(names)), 'ZIP contains no duplicate member names')
    ck(all(not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in names), 'ZIP member paths bounded')
    for name in names:
        source = P / ('vendor/' + name if name in ['aaai2027.sty', 'aaai2027.bst'] else name)
        ck(source.is_file(), 'ZIP source file present ' + name)
        if source.is_file():
            eq(hashlib.sha256(archive.read(name)).hexdigest(), digest(source), 'ZIP member equals current source ' + name)

bundle_path = D / 'data.json'
bundle = json.loads(bundle_path.read_text())
digest(bundle_path)
for item in bundle['artifacts']:
    public = D / item['path']
    eq(digest(public), item['sha256'], 'public advertised artifact hash ' + item['path'])
    eq(public.stat().st_size, item['bytes'], 'public advertised artifact bytes ' + item['path'])
    if item.get('source'):
        eq(digest(R / item['source']), item['sha256'], 'public source equality ' + item['path'])
for public_key, file in {'optionOrder': 'option-order-results.json',
                         'annotationComparison': 'annotation-comparison.json',
                         'newFamilyLabels': 'qwen35-content-label-results.json',
                         'lexiconSensitivity': 'conditional-lexicon-sensitivity.json',
                         'contentLabels': 'content-label-results.json'}.items():
    path = C / 'models' / file
    eq(bundle[public_key], json.loads(path.read_text()), 'public bundle current diagnostic ' + public_key)
    digest(path)
for file in ['app.js', 'index.html', 'styles.css']:
    eq(digest(D / file), digest(C / 'dashboard' / file), 'public UI equals reviewed source ' + file)

register = json.loads((H / 'source-register.json').read_text())
eq(register['source_count'], 18, 'targeted fresh register has eighteen sources')
eq(digest(R / register['prior_register']['path']), register['prior_register']['sha256'], 'prior twenty-eight-source register preserved')
venue = json.loads((H / 'venue-check.json').read_text())
eq(digest(P / 'vendor/aaai2027.sty'), venue['style_sha256'], 'fresh official style exact')
bibkeys = re.findall(r'@\w+\s*\{\s*([^,]+),', (P / 'references.bib').read_text())
eq(len(bibkeys), len(set(bibkeys)), 'no duplicate BibTeX keys')
cites = set()
for path in [P / 'body.tex', *sorted((P / 'generated').glob('*.tex'))]:
    for group in re.findall(r'\\cite\w*(?:\[[^\]]*\])?\{([^}]+)\}', path.read_text()):
        cites.update(key.strip() for key in group.split(','))
eq(sorted(cites - set(bibkeys)), [], 'every cited key resolves in current bibliography')

fail = [x for x in checks if not x['passed']]
report = {'round': 12, 'status': 'FAIL' if fail else 'PASS', 'checks': len(checks), 'failures': fail,
          'explicit_pdf_sha256': args.pdf_sha256, 'explicit_source_zip_sha256': args.zip_sha256,
          'pages': pages, 'public_artifact_count': len(bundle['artifacts']),
          'source_zip_members': len(names), 'bibtex_entries': len(bibkeys), 'cited_keys': len(cites),
          'extracted_pdf_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
          'file_sha256': hashes, 'network_or_inference_runs': 0,
          'scope': 'Independent final-byte and selected actual-PDF-text/source/citation audit; no browser, new rendering, human review or source-study replication claimed.',
          'all_checks': checks}
(H / 'independent-release-bindings.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks', 'failures', 'pages', 'public_artifact_count', 'source_zip_members', 'bibtex_entries', 'cited_keys']}, indent=2))
raise SystemExit(bool(fail))
