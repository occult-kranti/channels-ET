"""Paper-sized presentation derivatives, using only frozen numerical results."""
import hashlib
from collections import Counter
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def render(result, output):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.labelsize': 10,
                         'axes.titlesize': 10, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
                         'legend.fontsize': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False})
    sources = result['sources']
    audio = [r for r in sources if r['modality'] == 'audio_asr']
    written = [r for r in sources if r['modality'] == 'publisher_text']
    colors = {'Bashar-context': '#246a8d', 'Ashtar-attributed creator episode': '#bd6a13',
              'Arcturian Council (source label)': '#6b5ba7', 'The Creators (source label)': '#9a657d',
              'Saint Germain (source label)': '#7b8242', 'Ashanti (source label)': '#a84e42',
              'Thymus (source label)': '#477e71', 'Spiritual Guides (comparison)': '#6a6a6a'}
    groups = {'Bashar-context': 'Bashar ASR (19)', 'Ashtar-attributed creator episode': 'Ashtar ASR (1)',
              'Arcturian Council (source label)': 'Arcturian text (3)', 'The Creators (source label)': 'Creators text (6)',
              'Saint Germain (source label)': 'Germain text (4)', 'Ashanti (source label)': 'Ashanti text (1)',
              'Thymus (source label)': 'Thymus text (1)', 'Spiritual Guides (comparison)': 'Guides text (1)'}
    actual_groups = Counter(r['claimedGroup'] for r in sources)
    groups = {key: value[:value.rfind('(')] + '(' + str(actual_groups[key]) + ')' for key, value in groups.items()}
    saved = []

    def emit(name, fig, note):
        path = output / (name + '.pdf')
        fig.savefig(path, bbox_inches='tight', metadata={'Creator': 'Channels ET paper presentation derivative', 'CreationDate': None, 'ModDate': None})
        plt.close(fig)
        saved.append({'id': name, 'paper_pdf_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'presentation_changes': note, 'new_numerical_analysis': False})

    fig, ax = plt.subplots(1, 2, figsize=(6.8, 3.8), gridspec_kw={'width_ratios': [1.15, 1]}, layout='constrained')
    names = ['Bashar-context\naudio', 'Athina/Ashtar\naudio', 'Daniel authored\nRSS', 'Paul publisher\ntext']
    counts = [sum(r['claimedGroup'] == 'Bashar-context' for r in audio),
              sum(r['claimedGroup'] == 'Ashtar-attributed creator episode' for r in audio),
              sum('Daniel Scranton' in r['practitionerContext'] for r in written),
              sum('Paul Selig' in r['practitionerContext'] for r in written)]
    ax[0].barh(names, counts, color=['#246a8d', '#bd6a13', '#9a657d', '#6a6a6a'])
    ax[0].set_xlim(0, 22); ax[0].set_xticks([0, 10, 20]); ax[0].set_xlabel('Source documents')
    for i, v in enumerate(counts): ax[0].text(v + .25, i, str(v), va='center', fontsize=10)
    ax[1].boxplot([[r['tokenCount'] for r in audio], [r['tokenCount'] for r in written]], tick_labels=['ASR', 'Written'])
    ax[1].set_ylabel('Common tokens/document'); ax[1].ticklabel_format(axis='y', style='plain')
    emit('source-coverage', fig, 'Wrapped context labels, paper-width axes and larger text; identical source/token arrays.')

    labels = np.array([r['cluster'] for r in result['clusters']['labels']])
    order = np.lexsort((np.arange(len(audio)), labels))
    sim = np.array(result['tfidf']['audio']['cosine'])
    fig, ax = plt.subplots(figsize=(6.8, 6), layout='constrained')
    im = ax.imshow(sim[np.ix_(order, order)], vmin=0, vmax=1, cmap='Blues')
    ax.set_xticks(range(20), [audio[i]['shortId'] for i in order], rotation=90)
    ax.set_yticks(range(20), [audio[i]['shortId'] for i in order]); ax.set_title('Audio-source TF-IDF cosine')
    fig.colorbar(im, ax=ax, label='Cosine', fraction=.04)
    emit('audio-cosine', fig, 'Same matrix/order; paper-sized ID labels and colorbar.')

    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    projections = result['clusters']['projection']
    for docs, rows, marker in [(audio, projections['audio'], 'o'), (written, projections['publisherComparison'], '^')]:
        position = {r['sourceId']: (r['x'], r['y']) for r in rows}
        for doc in docs:
            point = position[doc['sourceId']]
            ax.scatter(*point, color=colors[doc['claimedGroup']], marker=marker, s=45, edgecolors='white', linewidth=.5)
            if doc['shortId'] in {'A03', 'A04', 'A18'}:
                ax.annotate(doc['shortId'], point,
                            xytext=(-20, 14) if doc['shortId'] == 'A04' else (8, 8),
                            ha='right' if doc['shortId'] == 'A04' else 'left',
                            textcoords='offset points', fontsize=10, arrowprops={'arrowstyle': '-', 'lw': .6})
    ax.set_xlabel('Audio-fitted SVD component 1'); ax.set_ylabel('Audio-fitted SVD component 2')
    handles = [Line2D([0], [0], color='none', marker='o' if 'ASR' in groups[g] else '^',
                      markerfacecolor=c, markersize=6, label=groups[g]) for g, c in colors.items()]
    fig.legend(handles=handles, ncol=3, loc='lower center', fontsize=9, frameon=False)
    fig.subplots_adjust(bottom=.30, left=.13, right=.98, top=.97)
    emit('source-overlay', fig, 'Identical source coordinates/colors; compact context key, shapes and three highlighted outlier/retail IDs replace crowded all-point text. All coordinates remain in source JSON.')

    weights = np.array([r['weights'] for r in result['topics']['weights']])
    fig, ax = plt.subplots(figsize=(6.8, 5.8), layout='constrained'); bottom = np.zeros(20)
    for j, color in enumerate(['#246a8d', '#bd6a13', '#6b5ba7']):
        ax.barh(range(20), weights[:, j], left=bottom, color=color, label=f'Topic {j+1}'); bottom += weights[:, j]
    ax.set_yticks(range(20), [r['shortId'] for r in audio]); ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.set_xlabel('Normalized fitted component weight'); ax.legend(ncol=3, loc='lower left', bbox_to_anchor=(0, 1), frameon=False)
    emit('audio-topics', fig, 'Same20x3 weights; short topic key refers to adjacent top-term table, removing a width-expanding legend.')

    rows = result['lexicons']['groupRates']; keys = list(result['lexicons']['themeDefinitions'])
    values = np.array([[r['equalDocumentMeanRates'][key] for key in keys] for r in rows])
    short = ['Contact', 'Belief', 'Emotion', 'Practice', 'Ontology', 'Entity', 'Evidence', 'Health', 'Social', 'Promo']
    fig, ax = plt.subplots(figsize=(6.8, 4), layout='constrained')
    im = ax.imshow(values, cmap='YlGnBu', aspect='auto', vmin=0)
    ax.set_yticks(range(len(rows)), [groups[r['group']] for r in rows]); ax.set_xticks(range(len(keys)), short, rotation=50, ha='right')
    for i in range(len(rows)):
        for j in range(len(keys)):
            ax.text(j, i, f'{values[i,j]:.1f}', ha='center', va='center', fontsize=9,
                    color='white' if values[i,j] > .6*values.max() else '#202020')
    fig.colorbar(im, ax=ax, label='Mean hits /1,000 tokens', fraction=.035)
    emit('theme-overlay', fig, 'Same8x10 rates/order; short context/theme keys and9pt cell values, with full definitions in manuscript.')

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.4), layout='constrained')
    for modality, ax in zip(['audio_asr', 'publisher_text'], axes):
        graph = result['networks']['entityMention']['cohorts'][modality]
        nodes = graph['nodes']; theta = np.linspace(0, 2*np.pi, len(nodes), endpoint=False) + np.pi/2
        positions = {r['id']: np.array([np.cos(t), np.sin(t)]) for r, t in zip(nodes, theta)}
        for edge in graph['edges']:
            p, q = positions[edge['source']], positions[edge['target']]
            ax.plot([p[0], q[0]], [p[1], q[1]], color='#a2afb9', lw=1.3)
            mid = (p+q)/2; ax.text(*mid, f"{edge['documents']} doc" + ('s' if edge['documents'] != 1 else ''),
                                 ha='center', va='center', fontsize=10, bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 2})
        for node in nodes:
            p = positions[node['id']]; ax.scatter(*p, s=70+node['documents']*20, color='#246a8d' if modality == 'audio_asr' else '#9a657d')
            label = node['id'].split(' / ')[0] + f"\nn={node['documents']}"
            ax.annotate(label, p, xytext=(0, 14 if p[1] >= 0 else -27), textcoords='offset points', ha='center', fontsize=10)
        ax.set_xlim(-1.6, 1.6); ax.set_ylim(-1.6, 1.65); ax.axis('off')
        ax.set_title(('Audio ASR' if modality == 'audio_asr' else 'Written') + f" (n={graph['denominatorDocuments']})")
    emit('civilization-mentions', fig, 'Same nonzero nodes/edges/counts; compact schematic positions, shortened family names and10pt count labels. No zero-hit node or unvalidated spelling is added.')

    fig, axes = plt.subplots(1, 3, figsize=(6.8, 3.2), layout='constrained')
    topics = result['topics']['candidates']; clusters = result['clusters']['candidates']; ks = [r['k'] for r in topics]
    for ax, vals, title, color in zip(axes, [[r['reconstructionError'] for r in topics], [r['matchedTopicCosineMean'] for r in topics],
                                          [r['cosineSilhouette'] for r in clusters]], ['Reconstruction', 'Seed-matched cosine', 'Cosine silhouette'], ['#246a8d', '#6b5ba7', '#bd6a13']):
        ax.plot(ks, vals, 'o-', color=color); ax.set_title(title, fontsize=9); ax.set_xlabel('Candidate K'); ax.set_xticks(ks)
    axes[1].set_ylim(0, 1); axes[2].set_ylim(0, .27)
    emit('model-diagnostics', fig, 'Same candidate scalar metrics; compact titles replace long vertical labels and paper-width fonts are enlarged.')

    fig, axes = plt.subplots(1, 3, figsize=(6.8, 3.1))
    profiles = {r['sourceId']: r['bins'] for r in result['lexicons']['timeProfiles']}
    for key, ax, title in zip(['contact_disclosure', 'belief_reality_agency', 'practice_enthusiasm_alignment'], axes,
                             ['Contact', 'Belief/agency', 'Practice']):
        for group in ['Bashar-context', 'Ashtar-attributed creator episode']:
            docs = [r for r in audio if r['claimedGroup'] == group]
            vals = np.array([[profiles[r['sourceId']][i]['rates'][key] or 0 for i in range(10)] for r in docs])
            ax.plot(np.arange(10)*10+5, vals.mean(axis=0), 'o-', markersize=3, color=colors[group], label=groups[group])
        ax.set_title(title); ax.set_xlim(0, 100); ax.set_xticks([0, 50, 100]); ax.set_xlabel('Audio time (%)')
    axes[0].set_ylabel('Hits /1,000 tokens'); fig.legend(*axes[0].get_legend_handles_labels(), ncol=2, loc='upper center', frameon=False)
    fig.subplots_adjust(top=.78, bottom=.19, left=.10, right=.99, wspace=.40)
    emit('audio-time-profiles', fig, 'Same midpoint-bin equal-document profiles; short titles, three x ticks and a shared readable legend.')
    return saved
