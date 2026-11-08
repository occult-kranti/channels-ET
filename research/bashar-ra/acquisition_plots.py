#!/usr/bin/env python3
"""Plot verified acquisition receipts; no speech-content or accuracy inference."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter
import numpy as np


def read(path):
    return json.loads(path.read_text())


def build(ra_path, bashar_path, contexts_path, output):
    ra, bashar, contexts = read(ra_path), read(bashar_path), read(contexts_path)
    collection_path = output / 'collection.json'
    collection = read(collection_path)
    sessions = defaultdict(list)
    for r in ra['records']:
        sessions[r['session_number']].append(r)
    session_rows = [{'session': n, 'retained_segments': len(sessions[n]),
        'duration_seconds': sum(r['retained']['decoded_duration_seconds'] for r in sessions[n]),
        'compact_bytes': sum(r['retained']['bytes'] for r in sessions[n])} for n in range(1, 107)]
    if any('collection_status' in r for r in bashar['records']):
        clips = [{'source_format': r['source_format'], 'audio': r['audio_artifact'],
            'duration_seconds': r['audio_duration_seconds']} for r in bashar['records'] if r['collection_status'] == 'retrieved']
    else:
        clips = [r for r in bashar['records'] if r['status'] == 'completed']
    assert len(clips) == collection['corpora']['bashar']['official_audio_retained']
    assert len(ra['records']) == collection['corpora']['ra']['compact_audio_retained']
    folder = output / 'collection-figures'
    folder.mkdir(exist_ok=True)
    figures = []
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.spines.top': False, 'axes.spines.right': False,
        'svg.hashsalt': 'bashar-ra-acquisition', 'savefig.facecolor': 'white'})
    def save(fig, name, caption):
        for extension in ('png', 'svg', 'pdf'):
            path = folder / f'{name}.{extension}'
            fig.savefig(path, dpi=170, bbox_inches='tight')
            figures.append({'file': path.name, 'caption': caption, 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={'height_ratios': [1, 1.25]})
    axes[0].bar([r['session'] for r in session_rows], [r['duration_seconds']/3600 for r in session_rows], color='#28666f', width=.85)
    axes[0].set(xlabel='Canonical Ra session number', ylabel='Retained audio hours',
        title='Published original-recording segments, retained as full-length Opus copies', xlim=(.2,106.8))
    axes[0].set_xticks([1,10,20,30,40,50,60,70,80,90,100,106])
    groups = defaultdict(list)
    groups['Related interviews / commentary'].extend(r['audio_duration_seconds']/60 for r in contexts['records'])
    format_labels = {
        'official_channeling_excerpt': 'Official channeling excerpts',
        'official_translated_channeling_excerpt': 'Translated excerpts',
        'official_qa_excerpt': 'Official Q&A excerpts',
        'official_greeting': 'Official greetings',
        'official_promotional_or_product_video': 'Official promotion / product',
    }
    for r in clips:
        fmt = r.get('source_format', 'unspecified')
        groups[format_labels.get(fmt, fmt.replace('official_', '').replace('_', ' ').capitalize())].append(r['duration_seconds']/60)
    for i, (name, values) in enumerate(groups.items()):
        offsets = np.linspace(-.13,.13,len(values)) if len(values)>1 else [0]
        axes[1].scatter(values, np.full(len(values), i) + offsets, color='#925130' if i else '#384f59', s=25, alpha=.72)
        axes[1].plot([np.median(values)], [i], marker='|', markersize=20, color='black', markeredgewidth=2)
    axes[1].set_yticks(range(len(groups)), [f'{name} (n={len(v)})' for name, v in groups.items()])
    axes[1].set(xscale='log', xlabel='Media duration in minutes · logarithmic scale',
        title='Bashar source formats differ substantially in duration; black marks are medians')
    axes[1].xaxis.set_major_locator(FixedLocator([5, 10, 20, 60, 120]))
    axes[1].xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:g}'))
    axes[1].grid(axis='x', alpha=.2)
    fig.tight_layout(h_pad=2)
    save(fig, 'recording-duration-coverage',
        'Top: summed decoded durations of retained Ra segments per canonical session; source gaps and missing historical recordings are not filled. Bottom: each admitted Bashar publication is a point, using retained-media duration metadata and grouped by source format; black marks show medians. Official excerpts are not full sessions. The logarithmic duration axis exposes the recording-length difference; this is acquisition metadata, not speech-rate or content analysis.')
    labels = ['Ra: compact Opus copies', 'Ra: preserved original pilot',
        'Bashar-related: 19 retained contexts', f'Official Bashar: {len(clips)} admitted publications']
    values = [ra['retained_bytes'], collection['corpora']['ra']['media_bytes'] - ra['retained_bytes'],
        sum(r['audio_bytes'] for r in contexts['records']), sum(r['audio']['bytes'] for r in clips)]
    counts = [len(ra['records']), 1, len(contexts['records']), len(clips)]
    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.barh(labels, np.array(values)/1e9, color=['#28666f','#6f9b9e','#925130','#c38a56'])
    ax.invert_yaxis()
    ax.set(xlabel='Retained compressed-audio bytes / 1,000,000,000 (decimal GB)',
        title='Audio representations retained in the private workspace')
    ax.set_xlim(0, max(values)/1e9*1.33)
    for bar, value, count in zip(bars, values, counts):
        ax.text(bar.get_width()+.025, bar.get_y()+bar.get_height()/2,
            f'{value/1e9:.3f} GB · {count:,} files', va='center')
    fig.tight_layout()
    save(fig, 'compressed-audio-storage',
        'Compressed admitted audio only; excludes model weights, metadata, PCM derivatives and any retained-but-unadmitted boundary files. The preserved Ra pilot and its compact copy are two files from one source, not independent recordings. Opus is a lossy derivative; original source MP3 bytes were verified before conversion. Decimal GB is used.')
    collection['figures'] = figures
    collection['audio_summary_by_ra_session'] = session_rows
    collection['collection_plot_inputs'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in [('ra_audio_manifest', ra_path), ('official_bashar_audio_manifest', bashar_path), ('retained_bashar_contexts', contexts_path)]}
    collection_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'figures': len(figures), 'ra_sessions': len(session_rows), 'official_audio_publications': len(clips)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ra', type=Path, required=True)
    p.add_argument('--bashar', type=Path, required=True)
    p.add_argument('--contexts', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    build(a.ra, a.bashar, a.contexts, a.output)
