#!/usr/bin/env python3
"""Refresh approved paper figures/metadata; never rewrite manuscript claims."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--expect-sha256', required=True)
    parser.add_argument('--review-status', choices=['draft', 'accepted-model-agent-audit'], default='draft')
    args = parser.parse_args()
    source = args.analysis.resolve()
    if digest(source) != args.expect_sha256:
        raise SystemExit('Analysis hash does not match the explicitly selected snapshot.')
    data = json.loads(source.read_text())
    figures = []
    for item in data['figures']:
        name = item['file']
        if Path(name).name != name:
            raise SystemExit('Figure filenames must be plain basenames.')
        if Path(name).suffix not in {'.png', '.pdf'}:
            continue
        path = source.parent / name
        if digest(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise SystemExit(f'Figure evidence mismatch: {name}')
        figures.append(item)
    if not figures:
        raise SystemExit('No verified paper figures found.')
    root = Path(__file__).resolve().parent
    snapshot_path = root / 'snapshot.json'
    snapshot = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {}
    snapshot.update({
        'schema_version': 1,
        'status': args.review_status,
        'analysis_run': source.parent.name,
        'analysis_sha256': digest(source),
        'analysis_script_sha256': data['analysis_script_sha256'],
        'primary_documents': data['counts']['primary_session_documents'],
        'primary_whitespace_words': sum(x['primary_session_whitespace_words'] for x in data['counts']['corpora'].values()),
        'neural_model': data['semantic']['model'],
        'semantic_processing': data['semantic']['processing'],
        'semantic_primary_content_wordpieces': sum(x['processed_content_wordpieces'] for x in data['semantic']['coverage']),
        'semantic_primary_chunks': sum(x['chunks'] for x in data['semantic']['coverage']),
        'semantic_qa_content_wordpieces': data['semantic']['qa']['processed_content_wordpieces'],
        'software_versions': data['methods']['versions'],
        'figures': figures,
        'human_reviewed': False,
        'human_authorship': 'TBD',
    })
    (root / 'figures').mkdir(exist_ok=True)
    for item in figures:
        shutil.copyfile(source.parent / item['file'], root / 'figures' / item['file'])
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + '\n')
    print(f'Verified and copied {len(figures)} figures from {source.parent.name}.')
    print('Review all manuscript numbers, interpretations and supplementary metadata before building or publishing.')


if __name__ == '__main__':
    main()
