#!/usr/bin/env python3
"""Independent release checks for source lineage and cross-artifact consistency."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ATLAS = HERE.parents[1]


def read(path):
    return json.loads(path.read_text())


def verify():
    checks = []
    def check(condition, label):
        checks.append({'check': label, 'passed': bool(condition)})
    candidates = read(HERE/'qa/qa-candidates.json')['records']
    summary = read(HERE/'qa/summary.json')
    plan = read(HERE/'acquisition/collection-plan.json')
    source_rows = []
    source_video_ids = set()
    for path in sorted((REPO/'data/digests').glob('*.json')):
        doc = read(path)
        if doc.get('qa_topics'):
            source_video_ids.add(path.stem)
        source_rows.extend(doc.get('qa_topics', []))
    check(len(candidates) == len(source_rows), 'All retained digest Q&A entries represented exactly once')
    check(len({r['id'] for r in candidates}) == len(candidates), 'Stable candidate IDs unique')
    errors = []
    for row in candidates:
        path = (REPO/row['sourcePath']).resolve()
        if not path.is_relative_to(REPO):
            errors.append(row['id']); continue
        blob = path.read_bytes()
        node = json.loads(blob)
        try:
            for part in row['sourcePointer'].strip('/').split('/'):
                node = node[int(part)] if isinstance(node, list) else node[part]
            matches = (hashlib.sha256(blob).hexdigest() == row['sourceSha256']
                       and node['question'] == row['question']
                       and node['answer_gist'] == row['answerGist'])
        except (KeyError, IndexError, ValueError, TypeError):
            matches = False
        if not matches:
            errors.append(row['id'])
    check(not errors, f'Every candidate resolves to exact source bytes and JSON pointer ({len(candidates)} rows)')
    check(all(r['evidenceType'] == 'ai_digest_paraphrase' for r in candidates), 'Digest provenance retained')
    check(all(r['timestampSeconds'] is None and not r['speakerVerified'] for r in candidates), 'Unavailable timing and speaker evidence remain unavailable')
    check(summary['coverage']['videosWithQACandidates'] == len(source_video_ids), 'Q&A-bearing video denominator matches source files')
    people = {name for r in candidates for name in r['practitionerNames']}
    check(summary['coverage']['practitionersWithQA'] == len(people), 'Practitioner coverage matches candidate attribution')
    check(summary['coverage']['crossPractitionerComparisonAvailable'] == (len(people) > 1), 'Cross-practitioner comparison availability reflects evidence')
    check(plan['units']['keyword_queries'] == len(plan['searches']), 'Planned-query denominator reconciles')
    check(plan['units']['account_routes'] == len(plan['accounts']), 'Planned-account denominator reconciles')
    check(all(r['status'] == 'planned' for r in plan['searches']), 'Plan rows are not represented as executed results')
    with sqlite3.connect(HERE/'qa/qa-candidates.sqlite') as db:
        check(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity check')
        check(db.execute('SELECT count(*) FROM qa_candidates').fetchone()[0] == len(candidates), 'SQLite and JSON candidate counts agree')
    result = read(HERE/'analysis/results.json')
    baseline = read(ATLAS/'dist/analysis/data.json')
    counts = collections.Counter(v['channelId'] for v in baseline['videos'] if v.get('channelId'))
    c = result['concentration']
    check(c['attributedUploads'] == sum(counts.values()), 'Attributed upload denominator independently reconciled')
    top = sum(sorted(counts.values(), reverse=True)[:10])/sum(counts.values())
    check(abs(c['top10Share']-top) < 1e-12, 'Top-ten concentration independently reproduced')
    check(result['source']['sha256'] == hashlib.sha256((ATLAS/'dist/analysis/data.json').read_bytes()).hexdigest(), 'Analysis pinned to exact retained source snapshot')
    check(result['coverage']['uploads'] == len(baseline['videos']), 'Analysis upload denominator reconciles')
    paper_manifest = read(HERE/'paper/input-manifest.json')
    stale = [name for name, expected in paper_manifest['inputs'].items()
             if hashlib.sha256((ATLAS/name).read_bytes()).hexdigest() != expected]
    check(not stale, 'Manuscript inputs match current source/result bytes: '+(', '.join(stale) or 'no stale inputs'))
    old_pdf = ATLAS/'dist/analysis/channeling-atlas-paper.pdf'
    check(hashlib.sha256(old_pdf.read_bytes()).hexdigest() == 'c9e7b736f1604b1801b3dfe48919a7e4604343c92a7a29fde79c9574b7ac9716', 'Original reviewed manuscript PDF preserved')
    public = ATLAS/'dist/expansion'
    if (public/'paper.pdf').exists():
        check((public/'paper.pdf').read_bytes() == (HERE/'paper/channeling-atlas-expansion-paper.pdf').read_bytes(), 'Explorer paper download matches reviewed manuscript')
    if (public/'qa-candidates.sqlite').exists():
        check((public/'qa-candidates.sqlite').read_bytes() == (HERE/'qa/qa-candidates.sqlite').read_bytes(), 'Explorer SQLite download matches source database')
    return {'status': 'PASS' if all(x['passed'] for x in checks) else 'FAIL',
            'checks': checks, 'checkCount': len(checks), 'candidateRowsResolved': len(candidates),
            'sourceMismatches': errors, 'scope': 'Source lineage and artifact consistency; not caption/audio accuracy, human validation or semantic agreement.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(result['status'] != 'PASS')
