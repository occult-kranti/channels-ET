#!/usr/bin/env python3
"""Generate manuscript evidence from actual retained JSON; no raw source bodies."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
OUT = PAPER / 'generated'
INPUTS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit('Required executed evidence is not available: ' + relative)
    INPUTS[relative] = {'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)}
    return json.loads(path.read_text())


def bind(relative):
    path = ROOT / relative
    INPUTS[relative] = {'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)}


def tex(value):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                    '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
                    '≥': r'\(\geq\)', '≤': r'\(\leq\)', '∞': r'\(\infty\)', '→': r'\(\to\)',
                    '’': "'", '‘': "'", '“': '``', '”': "''", '–': '--', '—': '---', '\u202f': ' ', '\u00a0': ' '}
    return ''.join(replacements.get(c, c) for c in str(value))


def n(value, digits=0):
    return f'{value:,.{digits}f}'


def write(name, body):
    (OUT / name).write_text(body.rstrip() + '\n')


def table(headers, rows, caption, widths=None, label=None):
    specification = widths or ('l' + 'r' * (len(headers) - 1))
    lines = [r'\begin{table*}[t]', r'\centering\small', r'\begin{tabular}{' + specification + '}', r'\toprule',
             ' & '.join(tex(h) for h in headers) + r'\\', r'\midrule']
    lines += [' & '.join(tex(v) for v in row) + r'\\' for row in rows]
    lines += [r'\bottomrule', r'\end{tabular}', r'\caption{' + tex(caption) + '}']
    if label:
        lines.append(r'\label{' + label + '}')
    lines.append(r'\end{table*}')
    return '\n'.join(lines) + '\n'


A = load('research/transcript-analysis/analysis.json')
protocol = load('research/transcript-analysis/protocol.json')
sources = load('research/transcript-analysis/sources.json')
captions = load('research/transcript-analysis/captions.json')
D = load('research/storage-distributions/distributions.json')
summary = A['summary']
assert len(sources) == len(A['sources']) == summary['audioDocuments'] + summary['authoredDocuments']
audio = [r for r in sources if r['modality'] == 'audio_asr']
authored = [r for r in sources if r['modality'] == 'publisher_text']
assert len(audio) == summary['audioDocuments'] == 20 and len(authored) == summary['authoredDocuments'] == 16
assert sum(r['tokenCount'] for r in audio) == summary['audioCommonTokens']
assert sum(r['tokenCount'] for r in authored) == summary['authoredCommonTokens']
assert D['summary']['actualIndependentAudioBytes'] == summary['audioBytes']
assert abs(D['summary']['actualIndependentAudioSeconds'] - summary['audioDurationSeconds']) < 1e-5
by_id = {r['sourceId']: r for r in sources}
assert len(by_id) == len(sources)

# These required artifacts prevent a final manuscript silently substituting a reading plan for results.
R = load('research/transcript-reading/summary.json')
reading_docs = load('research/transcript-reading/documents.json')
codes = load('research/transcript-reading/qualitative-codes.json')
qa = load('research/transcript-reading/qa-candidates.json')
codebook = load('research/transcript-reading/codebook.json')
reading_windows = load('research/transcript-reading/reading-windows.json')
families = load('research/transcript-reading/prompt-family-comparisons.json')
findings = load('research/transcript-reading/interpretive-findings.json')

OUT.mkdir(exist_ok=True)
(OUT / 'figures').mkdir(exist_ok=True)
for fig in A['figures']:
    relative = 'research/transcript-analysis/' + fig['paths'][0]
    bind(relative)
    shutil.copyfile(ROOT / relative, OUT / 'figures' / (fig['id'] + '.pdf'))
from presentation import render as render_presentation
presentation = render_presentation(A, OUT / 'figures')
write('presentation-manifest.json', json.dumps({'source_analysis_sha256': INPUTS['research/transcript-analysis/analysis.json']['sha256'],
      'presentation_script_sha256': sha(PAPER / 'scripts/presentation.py'), 'new_numerical_analysis': False,
      'figures': presentation}, indent=2))


def figure(ident, extra=''):
    caption = captions[ident]
    # Insert typesetting spaces in upstream concise numeric labels without changing their values.
    caption = re.sub(r'(\d)([A-Za-z])', r'\1 \2', caption)
    caption = re.sub(r'([A-Za-z])(\d)', r'\1 \2', caption)
    if ident == 'source-overlay':
        caption = 'Two-component SVD is fitted only to the 20 audio TF-IDF vectors; 16 written documents are projected through the same vocabulary and axes. Shapes distinguish modality and the short context key gives document counts. Only A03/A04 (retail-vocabulary examples) and A18 (the lone Ashtar source) are labeled to avoid crowding; all unchanged coordinates remain in analysis.json. Author, format, length and modality are confounded.'
    if ident == 'theme-overlay':
        extra += ' Short headings follow the complete ten-family codebook order: contact/disclosure, belief/reality/agency, emotion/fear/self-worth, practice/enthusiasm/alignment, ontology/consciousness/dimensions, claimed-entity identity, epistemic validation/skepticism, health/healing, relationships/collective ethics, and commercial promotion.'
    return ('\\begin{figure*}[t]\n\\centering\n\\includegraphics[width=\\textwidth]{generated/figures/' + ident + '.pdf}\n'
            + '\\caption{' + tex(caption + (' ' + extra if extra else '')) + '}\n\\label{fig:' + ident + '}\n\\end{figure*}\n')


values = {'AudioN': len(audio), 'AuthoredN': len(authored), 'AudioHours': n(summary['audioDurationSeconds'] / 3600, 2)}
write('values.tex', '\n'.join('\\newcommand{\\' + key + '}{' + str(value) + '}' for key, value in values.items()))
selected_cluster = next(r for r in A['clusters']['candidates'] if r['k'] == A['clusters']['selectedK'])
cluster_sizes = Counter(r['cluster'] for r in A['clusters']['labels'])
assert sorted(cluster_sizes.values()) == [1, 19]
singleton = next(group for group, count in cluster_sizes.items() if count == 1)
singleton_id = next(r['sourceId'] for r in A['clusters']['labels'] if r['cluster'] == singleton)
assert singleton_id == 'athina-ashtar-20230206-5d144c22'
topic3 = next(r for r in A['topics']['candidates'] if r['k'] == A['topics']['selectedK'])
write('abstract-results.tex',
      f"The selected two-cluster partition isolates the lone Athina recording from the nineteen Bashar-context records "
      f"(cosine silhouette {selected_cluster['cosineSilhouette']:.3f}); stable assignment is therefore not evidence of a validated multi-practitioner taxonomy.")

corpus_rows = [
    ['Publisher audio / unverified ASR', n(len(audio)), n(summary['audioDurationSeconds']/3600, 2) + ' h', n(summary['audioReceiptWords']), n(summary['audioCommonTokens'])],
    ['Authored / publisher text', n(len(authored)), 'not comparable', n(summary['authoredReceiptWords']), n(summary['authoredCommonTokens'])],
]
corpus = table(['Branch', 'Documents', 'Measured duration', 'Receipt words', 'Common tokens'], corpus_rows,
               'Actual analysis branches. Receipt words have different source-specific definitions and must not be pooled as a common denominator. Audio has nineteen Bashar-related source contexts and one Ashtar-attributed creator episode; written material has fifteen Daniel items and one Paul transcript.',
               'p{0.31\\textwidth}rrrr', 'tab:corpus')
corpus += figure('source-coverage')
write('corpus-table.tex', corpus)

tf = protocol['tfidf']
methods = (f"The executed TF--IDF fit uses word unigrams and bigrams, minimum document frequency {tf['minDf']}, "
           f"maximum document frequency {tf['maxDf']:.2f}, and a {tf['maxFeatures']:,}-feature cap. The audio fit retains "
           f"{A['tfidf']['audio']['featureCount']:,} features and the separate authored fit {A['tfidf']['authored']['featureCount']:,}. "
           "The English stoplist is modified to keep negators and exclude a declared spoken-filler list. "
           "This does not make the final vector representation fully negation-preserving: the common audio unigrams "
           "no, not and never are removed by the maximum-document-frequency rule, and nor by the minimum rule; some negated bigrams can remain. "
           "The representation cannot itself establish claim stance or agreement.\n\n"
           "NMF uses random initialization, coordinate descent and at most 1,500 iterations. "
           "Candidate component counts are 2--6, with seeds 11, 23, 47, 71 and 97. "
           "K-means uses 30 initializations for each candidate fit; the same seed set supplies stability diagnostics. "
           f"The source pipeline records {summary['nonoverlappingSegmentChunks']:,} nonoverlapping segment chunks targeting 500 tokens "
           f"and {summary['timeBins']:,} source-time bins. Chunks are metadata and reading aids; NMF and clustering use 20 documents, not 457 independent observations.")
write('methods.tex', methods)

duration = [r['durationSeconds']/60 for r in audio]
storage = D['summary']
archive = D['localArchive']
results = [r'\subsection{Obtained material and source distributions}',
           f"The audio branch contains {len(audio)} recordings from {summary['audioPublishers']} publishing contexts, "
           f"with median duration {statistics.median(duration):.2f} minutes (range {min(duration):.2f}--{max(duration):.2f}). "
           f"Its actual media total is {n(summary['audioBytes'])} bytes and {n(summary['audioDurationSeconds'], 3)} seconds. "
           f"The common tokenizer yields {n(summary['audioCommonTokens'])} audio tokens and {n(summary['authoredCommonTokens'])} written tokens; "
           f"the original receipt totals remain {n(summary['audioReceiptWords'])} and {n(summary['authoredReceiptWords'])} under their separate rules.",
           f"The current index describes {storage['indexedYouTubeIds']:,} YouTube IDs and {storage['literalRoutes']:,} literal routes, "
           f"including {storage['selectedYouTubeIds']:,} IDs selected under the current default collection policy. "
           f"The distributions expose {storage['publisherGroupsWithIndexedIds']:,} publisher groups, "
           f"{storage['practitionerAssociationsWithIndexedIds']:,} practitioner associations, {storage['entityLabelsWithIndexedIds']:,} raw entity labels and "
           f"{storage['civilizationLabelsWithIndexedIds']:,} publisher-declared civilization labels with indexed material. "
           "Those association views overlap; none is a count of independently verified people or civilizations. "
           f"Actual newly saved YouTube videos, caption tracks and bytes are all {storage['actualYouTubeVideos']}.",
           f"The logical storage plan contains {storage['canonicalSourceArtifacts']:,} source artifacts and {storage['canonicalSourceBytes']:,} bytes. "
           f"The completed managed-local archive contains {archive['actual_local_files']:,} independent copied files and {archive['actual_local_bytes']:,} bytes, "
           f"including {archive['metadata_artifacts']:,} sidecar/manifest artifacts. Copies preserve the same observations. "
           "No Drive transfer, permanent external-retention guarantee or downloadable chat attachment is established by that local copy.",
           r'\subsection{Distinctive vocabulary and constructed topics}',
           "The audio-wide mean TF--IDF vocabulary includes " + tex(', '.join(r['term'] for r in A['tfidf']['audio']['terms'][:8])) + ". "
           "Individual source vectors expose another layer: the Align records' top terms include protein, collagen and chocolate. "
           "Those are observable publishing/commercial vocabulary in the unsegmented transcript; treating all distinctive terms as attributed-message content would be unwarranted.",
           f"At the predeclared three-component display, seed-matched mean topic-term cosine is {topic3['matchedTopicCosineMean']:.3f}, "
           f"with minimum {topic3['matchedTopicCosineMin']:.3f}. Higher stability at another component count does not identify a truer ontology. "
           "The components are labeled from their highest-weight terms in Table\\ref{tab:topics}. The second component's workers/jumps/sole vocabulary is a source-inspection target, including possible recognition artifacts, rather than an independently validated conceptual category.",
           figure('audio-topics'), figure('model-diagnostics'),
           r'\subsection{Stable outlier partition and restricted overlays}',
           f"The selected K-means display uses K={A['clusters']['selectedK']} and cosine silhouette {selected_cluster['cosineSilhouette']:.3f}. "
           "Its cluster sizes are nineteen and one: all nineteen Bashar-context recordings occupy one cluster, while the lone Athina record is the other. "
           f"The cross-seed adjusted-Rand mean is {selected_cluster['seedAriMean']:.2f}. "
           "That numerical stability describes the same outlier partition. Source format, length, voice, vocabulary and context are confounded, so it cannot validate practitioner or civilization classes.",
           figure('audio-cosine'), figure('source-overlay'),
           f"The two displayed SVD components explain {sum(A['clusters']['projection']['explainedVarianceRatio'])*100:.2f} percent of the reported transformed-data variance. "
           "The projection is not a faithful map of every pairwise distance. Written points use the audio vocabulary and axes; they are comparison projections rather than evidence from a joint fit. "
           "The separate written NMF display is strongly shaped by author-attributed and publisher vocabulary, as its term table in the appendix shows.",
           r'\subsection{Lexical rates, mention graphs, and publication relations}',
           figure('theme-overlay'), figure('document-network'), figure('civilization-mentions'), figure('audio-time-profiles')]
written_clusters = A['tfidf']['authored']['clusters']
written_selected = next(r for r in written_clusters['candidates'] if r['k'] == written_clusters['selectedK'])
written_paragraph = (f"The separately fitted written clustering selects K={written_clusters['selectedK']} by the same in-sample criterion, "
                     f"but its cosine silhouette is only {written_selected['cosineSilhouette']:.3f}. Cluster sizes are "
                     + ', '.join(str(r['documents']) for r in written_clusters['clusterSizes']) +
                     '. The Paul transcript and the one Thymus-labeled Daniel item are singleton clusters. '
                     'This weak, source-confounded partition is not evidence for six substantive entity or civilization classes; all candidate scores are retained in the appendix.')
results.insert(next(i for i, value in enumerate(results) if value == r'\subsection{Lexical rates, mention graphs, and publication relations}'), written_paragraph)
network = A['networks']['documentSimilarity']
results.append(f"The displayed audio document graph retains {len(network['edges'])} edges under its two-neighbor/threshold rule. "
               "The separate all-pair threshold diagnostic counts 190 possible reused-document pairs. "
               "Its edge counts vary from a complete graph at 0.15 to zero at 0.65; this diagnostic is not the same graph rule as the displayed top-two-neighbor union. "
               "Network density is therefore partly a construction choice, not a measured social connectivity.")
entity = A['networks']['entityMention']['cohorts']
results.append("The strict audio civilization/star-system dictionary returns only two nonzero families: " +
               tex('; '.join(f"{r['id']}: {r['documents']}/{len(audio)} documents, {r['mentions']} mentions" for r in entity['audio_asr']['nodes'])) +
               ". They co-occur in two documents. Missing strict matches do not establish absence of a topic, a correct ASR spelling or an attributed group. "
               "The authored branch has Arcturian/Arcturus matches in six documents, whereas three items carry the corresponding source label. "
               "This is a concrete difference between a source's attributed label and terms appearing in its body. Orion and other names remain potentially astronomical or fictional mentions.")
spelling = A['lexicons'].get('posthocSpellingSensitivity', [])
if spelling:
    results.append('A separately labeled post-hoc spelling sensitivity retains the strict counts and inspects unvalidated variants. ' +
                   ' '.join(tex(r['family']) + f" has {sum(v['strictCanonicalMatches'] for v in r['records'])} strict matches and "
                            f"{sum(v['additionalCandidateMatches'] for v in r['records'])} additional candidate-spelling occurrences across "
                            f"{sum(v['additionalCandidateMatches'] > 0 for v in r['records'])} source documents."
                            for r in spelling) +
                   ' These are ASR-string candidates, not audio-validated corrections or verified identity attributions; the primary dictionary graph is unchanged.')
negation = A['tfidf']['audio'].get('negationDiagnostic')
if negation:
    example = next(r for r in negation['syntheticControls'] if r['cosine'] > 0.99999)
    results.append('An executed synthetic control illustrates a stronger semantic limit: ' + tex(example['left']) + ' and ' + tex(example['right']) +
                   f" have cosine {example['cosine']:.2f} in the actual audio-fitted space. "
                   'They are purpose-built contrasting sentences, not a corpus prevalence or error-rate estimate. Lexical resemblance alone cannot test agreement or safety.')
results += [r'\subsection{Sensitivity and limits of simple removals}']
sens = {(r['name'], r['cohort']): r for r in A['sensitivities']}
assert len(sens) == len(A['sensitivities']), 'Sensitivity name/cohort keys must be unique'
for name, description in [('proper_names_excluded', 'Excluding declared proper-name tokens'), ('commercial_vocabulary_excluded', 'Excluding the declared commercial vocabulary'), ('central80percent_audio_time', 'Restricting ASR to the central 80 percent of audio time')]:
    row = sens[(name, 'audio_asr')]
    results.append(description + f" in the audio-ASR cohort gives pairwise-cosine rank correlation {row['cosinePairRankCorrelation']:.3f} with baseline and preserves "
                   f"{row['nearestNeighborPreservedFraction']*100:.0f} percent of nearest-neighbor choices. "
                   "These are within-corpus perturbation results, not accuracy estimates.")
lopo = sens[('leave_one_publisher_out_nmf_fixed_vocabulary', 'audio_asr')]
written_commercial = sens[('commercial_vocabulary_excluded', 'publisher_text')]
results.append(f"The separate written commercial-vocabulary exclusion gives rank correlation {written_commercial['cosinePairRankCorrelation']:.3f} "
               f"and preserves {written_commercial['nearestNeighborPreservedFraction']*100:.0f} percent of nearest-neighbor choices in that fitted written cohort. "
               "That unchanged result does not show that publisher promotion was absent or successfully removed.")
results.append(f"Across the {len(lopo['records'])} publisher omissions, mean matched topic cosine is {lopo['meanMatchedCosine']:.3f} "
               f"and its minimum is {lopo['minimumMatchedCosine']:.3f}. The original vocabulary and IDF stay fixed, so this isolates a different influence than refitting the entire pipeline. "
               "The high commercial-removal correlation is limited to its declared word list: protein, collagen and other product-specific words remain outside that list. "
               "Central-time restriction and lexical removal do not verify speaker or advertisement removal.")

# The source-specific reading renderer is separate so its schema is explicit and reviewable.
from render_reading import render_reading
reading_results, reading_details = render_reading(R, reading_docs, codes, qa, codebook, by_id, reading_windows, families, findings, tex, table)
results += [r'\subsection{Source-linked readings and question/answer candidates}', reading_results]
write('results.tex', '\n\n'.join(results))
write('reading-details.tex', reading_details)

extended = table(['Audio component', 'Highest-weight terms'],
                 [[r['topicId'], ', '.join(t['term'] for t in r['terms'][:8])] for r in A['topics']['terms']],
                 'NMF display components from 20 ASR documents, reference seed 11. Labels are top-term summaries; component weights are not speech-time proportions.',
                 'lp{0.74\\textwidth}', 'tab:topics')
extended += table(['Written component', 'Highest-weight terms'],
                  [[r['topicId'], ', '.join(t['term'] for t in r['terms'][:8])] for r in A['tfidf']['authored']['topics']['terms']],
                  'Separate sixteen-document written fit. Source-attributed names and promotional wording can structure its components.', 'lp{0.74\\textwidth}')
extended += table(['K', 'NMF error', 'Topic cosine mean', 'Topic cosine min', 'Cluster silhouette', 'ARI mean'],
                  [[r['k'], n(r['reconstructionError'], 3), n(r['matchedTopicCosineMean'], 3), n(r['matchedTopicCosineMin'], 3),
                    n(next(v for v in A['clusters']['candidates'] if v['k'] == r['k'])['cosineSilhouette'], 3),
                    n(next(v for v in A['clusters']['candidates'] if v['k'] == r['k'])['seedAriMean'], 3)] for r in A['topics']['candidates']],
                  'All five audio candidate model sizes. Reconstruction, numerical stability and semantic validity are separate criteria.')
extended += table(['Written K', 'Cosine silhouette', 'Seed ARI mean', 'Seed ARI min'],
                  [[r['k'], n(r['cosineSilhouette'], 4), n(r['seedAriMean'], 3), n(r['seedAriMin'], 3)] for r in written_clusters['candidates']],
                  'Separate sixteen-document written K-means diagnostic. Selected K=6 has weak silhouette and two singletons; these are not validated semantic classes.')
extended += table(['ID', 'Publisher/context', 'Minutes', 'Receipt words', 'Common tokens'],
                  [[r['shortId'], r['publisher'], n(r['durationSeconds']/60, 2), n(r['receiptWordCount']), n(r['tokenCount'])] for r in audio],
                  'All twenty audio documents. Short IDs identify the same records in the plots and public sources.json; hosts/guests/ads are unsegmented.',
                  'lp{0.43\\textwidth}rrr')
extended += table(['Publisher', 'Recordings', 'Audio hours', 'Source artifacts', 'Source bytes'],
                  [[r['label'], r['source_recordings'], n(r['recorded_audio_seconds']/3600, 2), r['canonical_source_artifacts'], n(r['canonical_source_bytes'])]
                   for r in D['sourceStorage']['byPublisher']],
                  'Actual logical source storage by publisher. Artifact counts include derivative/text/metadata files; they do not count independent recordings.',
                  'p{0.43\\textwidth}rrrr')
extended += table(['Omitted publisher', 'Omitted documents', 'Matched topic cosine'],
                  [[r['excludedPublisher'], r['excludedDocuments'], n(r['matchedTopicCosine'], 3)] for r in lopo['records']],
                  'Fixed-vocabulary publisher-omission diagnostic. Values are influences within this corpus, not confidence bounds.', 'p{0.56\\textwidth}rr')
extended += table(['Index association', 'Assigned IDs', 'Unassigned IDs', 'Memberships'],
                  [[key.replace('by', '', 1), row['assignedUniqueIds'], row['unassignedUniqueIds'], row['groupMemberships']]
                   for key, row in D['attributionCoverage'].items()],
                  'Attribution coverage among 942 indexed IDs. Overlapping memberships do not increase distinct upload counts, and unassigned does not mean no relevant practitioner/entity/civilization.',
                  'p{0.45\\textwidth}rrr')
write('extended-tables.tex', extended)

reproduction = ("The paper reads the executed transcript-analysis, transcript-reading and storage-distribution JSON artifacts. "
                "Primary analysis units are whole source documents; chunk metadata and time bins are not independent model observations. "
                "ASR uses Systran/faster-whisper-tiny.en, revision beginning 0d3d19a32d33 (the full commit and official file hashes are retained in the model manifest), "
                "with faster-whisper v1.2.1, CTranslate2 v4.8.3 and PyAV v16.1.0 on CPU. "
                "The private local archive verifies separate single-link copies; it does not change source IDs or analytical weights. "
                "The public source package compiles without those private files because it includes the frozen generated evidence. "
                "Full analytical reproduction requires the source pipelines and exactly matching private snapshots.")
write('reproducibility.tex', reproduction)

literature = load('research/continuation/literature/source-register.json')
load('research/expansion/literature/scholarly-register.json')
bind('research/continuation/paper/references.bib')
bind('research/continuation/paper/vendor/aaai2027.sty')
bind('research/continuation/paper/vendor/aaai2027.bst')
assert (PAPER / 'references.bib').read_bytes() == (ROOT / 'research/continuation/paper/references.bib').read_bytes()
for name in ['aaai2027.sty', 'aaai2027.bst']:
    assert (PAPER / name).read_bytes() == (ROOT / 'research/continuation/paper/vendor' / name).read_bytes()
selected_keys = {'ribeiro2021youniverse', 'boesinger2024tube2vec', 'chen2026digital', 'ota2025pathways', 'wahbeh2023answers', 'wahbeh2026records', 'anastasia2020qualitative'}
lit_rows = [[r['key'], r['fresh_access_depth']] for r in literature['sources'] if r['key'] in selected_keys]
write('literature-access.tex', table(['Reference key', 'Retained inspected access'], lit_rows,
      'Source-reading records reused from the previous verified release. This manuscript does not claim fresh retrieval or full reading of every paper.',
      'p{0.27\\textwidth}p{0.64\\textwidth}'))
write('review-status.tex', 'The protocol specifies three iterative agent rounds covering first complete implementation, corrections and final artifact closure. Dated external review receipts identify the actual candidate hashes and completed stages.')
write('review-ledger.tex', 'Review receipts live in the manuscript review directory and the independent transcript-review workstream. Final closure binds the definitive PDF and source ZIP externally to avoid circular self-certification. Earlier receipts certify only their named artifacts. Human peer review remains pending.')
for relative in ['research/transcript-analysis/build.py', 'research/transcript-reading/prepare_reading.py', 'research/storage-distributions/build_distributions.py',
                 'research/transcript-analysis/source-manifest.json', 'research/transcript-reading/source-manifest.json',
                 'research/cloud-archive/archive-state.json', 'research/cloud-archive/verification.json']:
    bind(relative)
for path in [PAPER / name for name in ['main.tex', 'body.tex', 'appendices.tex', 'references.bib', 'aaai2027.sty', 'aaai2027.bst', 'build.sh', 'README.md', 'protocol.json']] + sorted((PAPER / 'scripts').glob('*.py')):
    bind(str(path.relative_to(ROOT)))
(PAPER / 'input-manifest.json').write_text(json.dumps({'schemaVersion': 1, 'scope': 'Actual inputs of this generated manuscript candidate; no raw source bodies included.',
    'files': [INPUTS[k] for k in sorted(INPUTS)]}, indent=2) + '\n')
print(json.dumps({'status': 'generated_from_executed_evidence', 'inputs': len(INPUTS), 'audio_documents': len(audio), 'written_documents': len(authored), 'copied_figures': len(A['figures'])}))
