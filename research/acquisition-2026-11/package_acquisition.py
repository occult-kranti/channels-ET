#!/usr/bin/env python3
"""Package the public metadata/hash acquisition workbench (no media bodies)."""
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'research/acquisition-2026-11'
DEST = ROOT / 'dist/research/acquisition-2026-11'
FILES = [
    'all-candidates.json', 'chunks/manifest.json', 'acquisition-ledger.json', 'summary.json', 'asr-summary.json',
    'asr-code-editions.json',
    'verification.json', 'verification-reuse.json', 'reference-summary.json',
    'channel-reference.csv', 'video-reference.csv',
    'analysis/analysis.json', 'analysis/protocol.json', 'analysis/non-bashar-public.sqlite',
    'analysis/non-bashar-public.csv', 'analysis/sources-index.csv', 'analysis/common-questions.csv',
    'analysis/manual-review.json', 'analysis/qualitative-synthesis.md', 'analysis/verification.json',
    'analysis/gate-status.json',
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_public_bytes(path):
    data = path.read_bytes()
    configured = [os.environ.get(name) for name in
                  ('CHANNELS_ET_RAW_ROOT', 'CHANNELS_ET_AUDIT_ROOT', 'CHANNELS_ET_MODEL_CACHE')]
    markers = [b'/' + b'mnt/agents/', b'/' + b'workspace/', b'/' + b'home/', b'/' + b'Users/']
    markers += [value.encode() for value in configured if value]
    for marker in markers:
        if marker in data:
            raise RuntimeError(f'Workstation path leaked into public artifact {path.name}: {marker!r}')


def public_json(source, target):
    """Copy JSON without workstation-local paths or private storage locations."""
    private_keys = {'codePath', 'modelCacheVerification'}
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in private_keys}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, str):
            raw_prefix = '/' + 'mnt/agents/channels-et-raw/'
            repo_prefix = '/' + 'mnt/agents/output/app/'
            return (value.replace(raw_prefix, 'private-research://')
                         .replace(repo_prefix, ''))
        return value
    payload = clean(json.loads(source.read_text()))
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def main():
    current_verification = json.loads((SRC / 'analysis/verification.json').read_text())
    current_gate = json.loads((SRC / 'analysis/gate-status.json').read_text())
    candidates = json.loads((SRC / 'all-candidates.json').read_text())
    candidate_ids = sorted(row['video_id'] for row in candidates)
    expected_gate_hash = hashlib.sha256('\n'.join(candidate_ids).encode()).hexdigest()
    if (current_verification.get('nFailed') != 0 or current_gate.get('ready') is not True
            or current_gate.get('candidateVideos') != len(candidate_ids)
            or current_gate.get('candidateIdsSha256') != expected_gate_hash):
        raise RuntimeError('Refusing to package an unverified or ungated analysis corpus')
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = []
    for rel in FILES:
        source = SRC / rel
        if rel == 'analysis/non-bashar-public.sqlite' and not source.exists():
            # CI materializes this binary from public CSV/JSON into dist first.
            source = DEST / rel
        if not source.exists():
            raise FileNotFoundError(source)
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            if source.suffix == '.json':
                public_json(source, target)
            else:
                shutil.copyfile(source, target)
        assert_public_bytes(target)
        manifest.append({'path': rel, 'bytes': target.stat().st_size, 'sha256': sha256(target)})
    source_figures = SRC / 'analysis/figures'
    destination_figures = DEST / 'figures'
    figure_names = ({p.name for p in source_figures.glob('*') if p.is_file()} |
                    {p.name for p in destination_figures.glob('*') if p.is_file()})
    for name in sorted(figure_names):
        figure = source_figures / name
        if not figure.exists():
            figure = destination_figures / name
        if figure.suffix not in ('.svg', '.png') or not figure.exists():
            continue
        target = destination_figures / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if figure.resolve() != target.resolve():
            shutil.copyfile(figure, target)
        assert_public_bytes(target)
        manifest.append({'path': f'figures/{name}', 'bytes': target.stat().st_size,
                         'sha256': sha256(target)})
    summary = json.loads((SRC / 'reference-summary.json').read_text())
    asr = json.loads((SRC / 'asr-summary.json').read_text())
    analysis = json.loads((SRC / 'analysis/analysis.json').read_text())
    analysis_verification = json.loads((SRC / 'analysis/verification.json').read_text())
    terminal = analysis['validation']['terminalStateCounts']
    channels = list(csv.DictReader((SRC / 'channel-reference.csv').open()))
    videos = list(csv.DictReader((SRC / 'video-reference.csv').open()))
    reconciliation = summary['accountReconciliation']
    rows = []
    for channel in channels:
        rows.append('<tr>' + ''.join(f'<td>{html.escape(str(channel[key]))}</td>'
                    for key in ['display_name', 'observed_videos', 'eligible_videos',
                                'selected_default_videos', 'audio_downloaded_videos',
                                'asr_completed_videos', 'analysis_completed_videos',
                                'analysis_excluded_videos', 'route_limit_held_videos']) + '</tr>')
    unattributed = [v for v in videos if not v['associated_account_ids']]
    un_values = [
        'Unattributed video records', len(unattributed),
        sum(v['eligibility'] == 'eligible' for v in unattributed),
        sum(v['selection'] == 'selected_default' for v in unattributed),
        sum(v['audio_status'] == 'completed' for v in unattributed),
        sum(v['asr_status'] == 'completed' for v in unattributed),
        sum(v['analysis_status'] == 'analysis_completed' for v in unattributed),
        sum(v['analysis_status'].startswith('analysis_excluded_') for v in unattributed),
        sum(v['analysis_status'] == 'analysis_held_route_limit_over_150_minutes' for v in unattributed),
    ]
    rows.append('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in un_values) + '</tr>')
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Channels ET — Acquisition workbench</title>
<style>
body{{font:15px/1.55 system-ui,sans-serif;margin:0;background:#101820;color:#e5edf3}}
main{{max-width:1500px;margin:auto;padding:24px}}h1{{font-size:30px}}h2{{font-size:20px}}
.notice{{border-left:4px solid #e0b34c;padding:12px 16px;background:#182a35;margin:16px 0}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px}}
.metric{{background:#17232d;border:1px solid #31424f;border-radius:5px;padding:12px}}
.metric strong{{display:block;font-size:22px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #31424f;padding:7px;text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:#1b2a35}}.table-wrap{{overflow-x:auto}}a{{color:#73d5ff}}
small{{color:#a9bdc9}}</style></head><body><main>
<p><a href="../index.html">← Evidence workspace</a></p>
<h1>Acquisition workbench · November 2026</h1>
<p>Observed public metadata and hash registries for the non-Bashar YouTube acquisition and ASR analysis. No media or full transcript bodies are published here.</p>
<div class="notice"><strong>State discipline:</strong> completed audio, ASR, analysis, exclusions and publication rights are separate. Uploader ≠ practitioner ≠ claimed entity. No claimed entity origin or truth is inferred. Raw recordings and full third-party transcripts remain private research storage. Converter-assisted acquisition may be subject to YouTube and provider terms; public availability and technical feasibility do not establish permission to download or redistribute.</div>
<div class="metrics">
<div class="metric"><strong>{summary['observedVideos']}</strong>Observed video records</div>
<div class="metric"><strong>{summary['observedAccounts']}</strong>Observed accounts</div>
<div class="metric"><strong>{summary['audioStatusCounts'].get('completed', 0)}</strong>Audio downloads completed</div>
<div class="metric"><strong>{terminal['totalCandidates']}</strong>Acquisition candidates</div>
<div class="metric"><strong>{summary['audioStatusCounts'].get('excluded_under_300', 0)}</strong>Under-300 exclusions</div>
<div class="metric"><strong>{asr['counts'].get('completed', 0)}</strong>Self-run ASR completed</div>
<div class="metric"><strong>{asr['counts'].get('excluded_language_mismatch', 0)}</strong>Language exclusions</div>
<div class="metric"><strong>{terminal['held']}</strong>Route-limit holds</div>
<div class="metric"><strong>{analysis['nDocuments']}</strong>Included analysis documents</div>
<div class="metric"><strong>{analysis['qa']['totalUnits']}</strong>Literal Q&A units</div>
</div>
<h2>Decisive totals</h2>
<ul>
<li>Audio bytes: <strong>{summary['audioBytes']:,}</strong></li>
<li>Audio duration: <strong>{summary['audioDurationSeconds']:,.3f} seconds</strong></li>
<li>ASR words: <strong>{summary['asrWords']:,}</strong>; ASR segments: <strong>{summary['asrSegments']:,}</strong></li>
<li>Candidate accounting: <strong>{terminal['analyzed']} analyzed + {terminal['excluded']} excluded + {terminal['held']} held = {terminal['totalCandidates']}</strong>. No pending candidate is counted as analyzed.</li>
<li>Analysis: {analysis_verification['nPassed']}/{analysis_verification['nChecks']} checks; NMF stability {analysis['nmf']['seedStabilityMeanBestMatchCosine']}; max KMeans silhouette {max(x['silhouetteMean'] for x in analysis['kmeansDiagnostics']['sweep']):.4f}; no cluster structure claimed.</li>
<li>Question families: {analysis['qa']['commonQuestionFamilies']['nFamilies']} token-keyed; {analysis['qa']['commonQuestionFamilies']['nSharedAcrossVideos']} recurring across videos. Stopword-only rows are family-less.</li>
</ul>
<h2>Downloads and registries</h2>
<ul>
<li><a href="all-candidates.json">Candidate registry</a> · <a href="video-reference.csv">Per-video reference CSV</a></li>
<li><a href="channel-reference.csv">Per-channel reference CSV</a></li>
<li><a href="reference-summary.json">Reference summary JSON</a></li>
<li><a href="acquisition-ledger.json">Acquisition ledger</a> · <a href="summary.json">Acquisition summary</a> · <a href="asr-summary.json">ASR summary</a> · <a href="verification.json">Full audio verification</a> · <a href="verification-reuse.json">Current consistency verification</a></li>
<li><a href="asr-code-editions.json">ASR code-edition provenance</a> (legacy snapshot gaps are explicit) · <a href="chunks/manifest.json">Compressed source-chunk manifest</a></li>
<li><a href="analysis/non-bashar-public.sqlite">Public Q&A database (SQLite)</a> · <a href="analysis/non-bashar-public.csv">Q&A CSV</a></li>
<li><a href="analysis/sources-index.csv">Source index</a> · <a href="analysis/common-questions.csv">Question families</a> · <a href="analysis/manual-review.json">AI review registry</a></li>
<li><a href="analysis/analysis.json">Aggregate analysis</a> · <a href="analysis/qualitative-synthesis.md">Qualitative synthesis</a> · <a href="analysis/verification.json">Analysis verification</a></li>
<li><a href="manifest.json">Artifact manifest with hashes</a></li>
</ul>
<h2>Channel coverage</h2>
<p><small>Observed inventory is not a full upload census; uploaded_total is null. Account rows count memberships, not unique-video totals. The 302 named rows contain {reconciliation['namedAccountVideoMemberships']} memberships; the separate unattributed row contains {reconciliation['unattributedVideoRecords']} records. {reconciliation['multiAccountVideos']} multi-account videos contribute {reconciliation['extraMembershipsFromMultiAccountVideos']} extra memberships. Reconcile as {reconciliation['namedAccountVideoMemberships']} + {reconciliation['unattributedVideoRecords']} − {reconciliation['extraMembershipsFromMultiAccountVideos']} = {reconciliation['uniqueVideoRecords']} unique videos. Audio, ASR and analysis counts need the same multi-account deduplication.</small></p>
<div class="table-wrap"><table><thead><tr><th>Channel</th><th>Observed</th><th>Eligible</th><th>Selected</th><th>Audio</th><th>ASR</th><th>Analysis</th><th>Excluded</th><th>Held</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p><small>Generated from hash-verified public artifacts. Raw media and full transcript bodies are not linked.</small></p>
</main></body></html>'''
    (DEST / 'index.html').write_text(page)
    assert_public_bytes(DEST / 'index.html')
    manifest.append({'path': 'index.html', 'bytes': (DEST / 'index.html').stat().st_size,
                     'sha256': sha256(DEST / 'index.html')})
    (DEST / 'manifest.json').write_text(json.dumps({'schemaVersion': 1, 'artifacts': manifest}, indent=2) + '\n')
    print(json.dumps({'destination': str(DEST), 'artifacts': len(manifest)}, indent=2))


if __name__ == '__main__':
    main()
