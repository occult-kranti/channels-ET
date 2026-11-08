#!/usr/bin/env python3
"""Fixed-query source/card retrieval audit; not a reproduction of sleep training."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from knowledge_sources import load_frame
from analyze import FrozenMiniLM

FROZEN_QUERY_SHA256 = '84634a835af5e0e074caa258c0e98bb0426691dc4dee37c5c70549692f9b4263'
SETTINGS = {
    'source_chunk_whitespace_words': 180, 'overlap_words': 0,
    'lexical_fit': 'source chunks only; cards and queries transformed without refitting',
    'lexical_ngram_range': [1, 2], 'lexical_max_features': 20000,
    'lexical_sublinear_tf': True, 'lexical_smooth_idf': True,
    'source_score': 'maximum unit cosine; length/card multiplicity remains a confound',
    'hybrid': 'reciprocal rank fusion of raw-source and qualified-card source ranks',
    'rrf_constant': 60, 'top_k': [1, 3, 5], 'shuffle_seed': 739,
    'shuffle_repetitions': 199,
    'candidate_fusion_top_k': 5,
    'tuning': 'Initial four conditions fixed before rankings; a fixed top5 fusion is added after the first results as a disclosed reviewer-driven design repair. No query/card changes or search over k.',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), {'file': Path(path).name, 'bytes': len(raw), 'sha256': sha(raw)}


def source_chunks(docs):
    rows = []
    for d in docs:
        text = d['text']; r = d['record']; words = list(re.finditer(r'\S+', text))
        for i in range(0, len(words), SETTINGS['source_chunk_whitespace_words']):
            part = words[i:i + SETTINGS['source_chunk_whitespace_words']]
            start, end = part[0].start(), part[-1].end(); body = text[start:end]
            rows.append({'unit_id': 'raw:' + r['source_id'] + ':' + str(i),
                'source_id': r['source_id'], 'text': body, 'start_character': start,
                'end_character': end, 'words': len(part), 'span_sha256': sha(body.encode())})
        assert sum(x['words'] for x in rows if x['source_id'] == r['source_id']) == r['words']
    return rows


def natural(value):
    if isinstance(value, str): return value.strip()
    if isinstance(value, list): return ' '.join(natural(x) for x in value)
    if value is None: return ''
    raise ValueError('Card text fields must be natural-language strings or lists')


def card_units(cards, known_sources, qualified):
    rows = []; seen = set()
    for c in cards:
        if c['card_id'] in seen or c['source_id'] not in known_sources:
            raise ValueError('Duplicate card or unknown source')
        seen.add(c['card_id'])
        parts = [natural(c['paraphrase'])]
        if qualified:
            parts.extend(natural(c.get(k)) for k in ('conditions', 'time_scope', 'qualifying_note'))
        text = ' '.join(x for x in parts if x)
        if not text: raise ValueError('Empty card answer')
        rows.append({'unit_id': ('qualified:' if qualified else 'answer:') + c['card_id'],
            'source_id': c['source_id'], 'text': text, 'words': len(text.split()),
            'span_sha256': sha(text.encode()), 'card_id': c['card_id']})
    return rows


def validate_queries(audit, docs, frame_sha):
    if audit['frame_sha256'] != frame_sha:
        raise ValueError('Queries refer to a different frame')
    bodies = {d['record']['source_id']: d for d in docs}; seen = set()
    for q in audit['queries']:
        if q['query_id'] in seen or not q['query'].strip(): raise ValueError('Invalid query ID/text')
        seen.add(q['query_id'])
        relevant = q['known_relevant_source_ids']
        if not relevant or len(set(relevant)) != len(relevant) or not set(relevant) <= bodies.keys():
            raise ValueError('Invalid known-support labels')
        supported = set()
        for s in q['supports']:
            d = bodies[s['source_id']]; record = d['record']
            if s['body_sha256'] != record['body_sha256'] or s['text_artifact_sha256'] != record['text_artifact']['sha256']:
                raise ValueError('Changed query-support source')
            start, end = s['char_start'], s['char_end']
            if not 0 <= start < end <= len(d['text']): raise ValueError('Invalid query support range')
            body = d['text'][start:end]
            if sha(body.encode()) != s['span_sha256'] or len(body.split()) != s['words']:
                raise ValueError('Query evidence span differs')
            supported.add(s['source_id'])
        if not set(relevant) <= supported: raise ValueError('Relevance label lacks checked support')


def aggregate_scores(units, values):
    scores = {}
    for row, score in zip(units, values, strict=True):
        if not np.isfinite(score): raise ValueError('Nonfinite retrieval score')
        sid = row['source_id']; scores[sid] = max(scores.get(sid, -float('inf')), float(score))
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def fused_ranking(left, right):
    scores = {}
    for ranked in (left, right):
        for rank, (sid, _) in enumerate(ranked, 1):
            scores[sid] = scores.get(sid, 0.) + 1. / (SETTINGS['rrf_constant'] + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def candidate_fusion(left, right):
    """Post-hoc design repair: fuse top5 candidates, then append untouched raw tail."""
    k = SETTINGS['candidate_fusion_top_k']
    ranked = fused_ranking(left[:k], right[:k])
    present = {sid for sid, _ in ranked}
    return ranked + [(sid, 0.) for sid, _ in left if sid not in present]


def rank_metrics(ranking, known):
    ids = [sid for sid, _ in ranking]
    if len(ids) != len(set(ids)): raise ValueError('Repeated ranked source')
    ranks = [ids.index(sid) + 1 for sid in known if sid in ids]
    first = min(ranks) if ranks else None
    return {'first_known_support_rank': first, 'reciprocal_rank': 1 / first if first else 0.,
        'hit_at_k': {str(k): int(any(sid in known for sid in ids[:k])) for k in SETTINGS['top_k']},
        'known_support_index_coverage': sum(sid in ids for sid in known) / len(known)}


def sanitize_query(q):
    out = {k: q[k] for k in ('query_id', 'query', 'known_relevant_source_ids', 'question_family',
        'source_family_ids', 'reference_kind', 'relevance_scope', 'rationale') if k in q}
    fields = ('source_id', 'body_sha256', 'text_artifact_sha256', 'char_start', 'char_end', 'span_sha256', 'words')
    out['supports'] = [{k: s[k] for k in fields} for s in q['supports']]
    return out


def run(frame_path, knowledge_path, query_path, model_path, output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(Path('/workspace/channels-et-private')):
        raise ValueError('Use a fresh private output directory')
    code_sha = sha(Path(__file__).read_bytes())
    docs, frame = load_frame(frame_path)
    frame_binding = read_json(frame_path)[1]
    knowledge, knowledge_binding = read_json(knowledge_path)
    audit, audit_binding = read_json(query_path)
    if audit_binding['sha256'] != FROZEN_QUERY_SHA256 or len(audit['queries']) != 4:
        raise ValueError('The four prospectively frozen audit queries are required')
    validate_queries(audit, docs, frame_binding['sha256'])
    source_ids = {d['record']['source_id'] for d in docs}
    if {s['source_id'] for s in knowledge['sources']} != source_ids:
        raise ValueError('Knowledge bank and raw frame differ')
    for s in knowledge['sources']:
        d = next(d for d in docs if d['record']['source_id'] == s['source_id'])
        if s['body_sha256'] != d['record']['body_sha256']: raise ValueError('Knowledge source hash differs')
    raw = source_chunks(docs)
    answers = card_units(knowledge['cards'], source_ids, False)
    qualified = card_units(knowledge['cards'], source_ids, True)
    if not answers: raise ValueError('No cards to compare')
    groups = {'raw_source': raw, 'answer_cards': answers, 'qualified_cards': qualified}
    queries = audit['queries']; query_texts = [q['query'] for q in queries]
    stop = sorted(set(ENGLISH_STOP_WORDS) - {'no', 'not', 'nor', 'never'})
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, smooth_idf=True,
        max_features=20000, stop_words=stop, token_pattern=r"(?u)\b\w[\w'’]*\b")
    vectorizer.fit([x['text'] for x in raw])
    lexical_queries = vectorizer.transform(query_texts)
    lexical = {name: cosine_similarity(lexical_queries, vectorizer.transform([x['text'] for x in units]))
        for name, units in groups.items()}
    encoder = FrozenMiniLM(model_path)
    all_units = [x for units in groups.values() for x in units]
    embeddings = encoder.encode([(x['unit_id'], x['text']) for x in all_units] +
        [('query:' + q['query_id'], q['query']) for q in queries])
    query_vectors = np.stack([embeddings['query:' + q['query_id']][0] for q in queries])
    neural = {name: cosine_similarity(query_vectors, np.stack([embeddings[x['unit_id']][0] for x in units]))
        for name, units in groups.items()}
    rows = []; ranked_by = {}
    for model, matrices in [('tfidf', lexical), ('minilm', neural)]:
        for qi, q in enumerate(queries):
            ranks = {name: aggregate_scores(units, matrices[name][qi]) for name, units in groups.items()}
            ranks['hybrid_rrf'] = fused_ranking(ranks['raw_source'], ranks['qualified_cards'])
            ranks['hybrid_top5_rrf'] = candidate_fusion(ranks['raw_source'], ranks['qualified_cards'])
            for condition, ranking in ranks.items():
                ranked_by[(model, condition, q['query_id'])] = ranking
                rows.append({'model': model, 'condition': condition, 'query_id': q['query_id'],
                    **rank_metrics(ranking, q['known_relevant_source_ids']),
                    'ranked_sources': [{'source_id': sid, 'score': score, 'rank': i + 1}
                        for i, (sid, score) in enumerate(ranking)]})
    conditions = list(groups) + ['hybrid_rrf', 'hybrid_top5_rrf']; summaries = []
    rng = np.random.default_rng(SETTINGS['shuffle_seed']); ordered_ids = sorted(source_ids)
    permutations = [dict(zip(ordered_ids, rng.permutation(ordered_ids), strict=True))
        for _ in range(SETTINGS['shuffle_repetitions'])]
    for model in ('tfidf', 'minilm'):
        for condition in conditions:
            selected = [r for r in rows if r['model'] == model and r['condition'] == condition]
            random_hits = []
            for mapping in permutations:
                hits = []
                for q in queries:
                    ranked = [(mapping[sid], score) for sid, score in ranked_by[(model, condition, q['query_id'])]]
                    hits.append(rank_metrics(ranked, q['known_relevant_source_ids'])['hit_at_k']['1'])
                random_hits.append(float(np.mean(hits)))
            summaries.append({'model': model, 'condition': condition, 'queries': len(selected),
                'mean_reciprocal_rank': float(np.mean([r['reciprocal_rank'] for r in selected])),
                'known_support_hit_rate': {str(k): float(np.mean([r['hit_at_k'][str(k)] for r in selected])) for k in SETTINGS['top_k']},
                'known_support_index_coverage': float(np.mean([r['known_support_index_coverage'] for r in selected])),
                'shuffled_source_assignment': {'repetitions': len(random_hits), 'mean_hit_at_1': float(np.mean(random_hits)),
                    'descriptive_2_5_to_97_5_percentiles': np.quantile(random_hits, [.025, .975]).tolist(),
                    'scope': 'Source IDs randomly reassigned over this25-source frame; negative control, not an inferential null, p-value or confidence interval.'}})
    tokenizer = vectorizer.build_analyzer(); vocab = vectorizer.vocabulary_
    index_coverage = []
    for name, units in groups.items():
        terms = [t for x in units for t in tokenizer(x['text'])]
        index_coverage.append({'condition': name, 'units': len(units),
            'sources': len({x['source_id'] for x in units}),
            'words': sum(x['words'] for x in units), 'utf8_bytes': sum(len(x['text'].encode()) for x in units),
            'lexical_analyzed_term_occurrences': len(terms),
            'lexical_out_of_vocabulary_occurrences': sum(t not in vocab for t in terms),
            'units_by_source': {sid: sum(x['source_id'] == sid for x in units) for sid in ordered_ids}})
    encoded_coverage = [{'unit_id': sid, **value[2]} for sid, value in embeddings.items()]
    if any(c.get('truncated_content_wordpieces', 0) for c in encoded_coverage): raise ValueError('Truncated encoding')
    result = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'status': 'executed', 'title': 'Source evidence versus consolidated cards: fixed-query retrieval audit',
        'scope': 'Four independently authored source-informed queries frozen before card/ranking inspection. Descriptive known-support retrieval, not blind/human accuracy or a reproduction of Google sleep training.',
        'coverage': {'sources': len(source_ids), 'source_words': frame['coverage']['words'], 'queries': len(queries),
            'cards': len(answers), 'card_sources': len({x['source_id'] for x in answers}), 'source_chunks': len(raw)},
        'settings': SETTINGS, 'input_bindings': {'frame': frame_binding, 'knowledge': knowledge_binding, 'queries': audit_binding},
        'conditions': [
            {'id': 'raw_source', 'label': 'Raw source chunks', 'role': 'initial_fixed_diagnostic'},
            {'id': 'answer_cards', 'label': 'Answer-only cards', 'role': 'initial_fixed_ablation'},
            {'id': 'qualified_cards', 'label': 'Qualified cards', 'role': 'initial_fixed_diagnostic'},
            {'id': 'hybrid_rrf', 'label': 'Naive full-list fusion (coverage biased)', 'role': 'diagnosed_negative_control'},
            {'id': 'hybrid_top5_rrf', 'label': 'Top5 fusion + raw tail (post-hoc repair)', 'role': 'post_hoc_sensitivity'}],
        'protocol_amendments': [{'stage': 'After first executed run; before corrected run',
            'parent_result_sha256': '787b3c6787a47eb4c56e4aefe49074942a0700dd95b7ab11bcce5840dcfc5660',
            'reason': 'Independent reviewer derived a structural coverage bias without inspecting rankings. Root had already executed the initial conditions, so this change is explicitly post-hoc.',
            'change': 'Retain naive full-list fusion and add a single fixed top5-candidate RRF followed by raw-source tail. No query wording, relevance labels, card text or representation parameters changed.',
            'scope': 'Design repair and sensitivity, not held-out evidence that a tuned retriever generalizes.'}],
        'naive_fusion_coverage_bias': {
            'raw_sources': len(source_ids), 'card_sources': len({x['source_id'] for x in qualified}),
            'worst_covered_rrf_bound': 1 / (60 + len(source_ids)) + 1 / (60 + len({x['source_id'] for x in qualified})),
            'best_uncovered_rrf_bound': 1 / 61,
            'all_covered_sources_outrank_all_uncovered_by_construction':
                1 / (60 + len(source_ids)) + 1 / (60 + len({x['source_id'] for x in qualified})) > 1 / 61,
            'interpretation': 'Full-list RRF with this incomplete card index is structurally coverage-biased regardless of query meaning; its failures do not establish a general defect in hybrid retrieval or consolidation.'},
        'script_sha256': code_sha, 'model': encoder.binding,
        'queries': [sanitize_query(q) for q in queries], 'results': rows, 'summary': summaries,
        'index_coverage': index_coverage, 'encoding_coverage': encoded_coverage,
        'limitations': [
            'Only four purposive AI-authored queries and source-informed known supports; this is neither human ground truth nor a representative evaluation.',
            'Unlisted sources are unjudged, not irrelevant. Hit rate and reciprocal rank concern only the declared known supporting sources.',
            'Card authors saw source answers. Cards cover a selected subset and may have been written for related analyst questions, despite independent query freezing.',
            'The answer-only card ablation intentionally omits separate qualifiers from the retrieval text; the full knowledge database always retains them.',
            'Source maxima favor documents with more chunks; card maxima favor sources with more cards. Index sizes, formats and source coverage differ.',
            'TF-IDF is fitted on raw-source chunks only. Card paraphrases can contain out-of-vocabulary terms; MiniLM is an older cached baseline, not a current SOTA claim.',
            'Retrieving a source does not establish that a generated answer would retain its negation, conditions or time scope. No automated answer generation is evaluated.',
            'Naive full-list fusion mechanically promotes every card-covered source over uncovered sources. The top5 candidate fusion is a disclosed post-hoc repair, not a held-out improvement claim.',
            'Shuffle ranges are descriptive negative controls, not significance tests. No search over fusion settings or changes to frozen queries/cards were made.',
            'This is source-bound index consolidation. No language-model parameters, Google memory experts or synthetic-dream training are implemented.'
        ], 'figures': []}
    output.mkdir(parents=True, mode=0o700)
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = ['Raw source', 'Answer cards', 'Qualified cards', 'Naive fusion', 'Top5 repair*']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    colors = ['#236b83', '#b26549', '#47765b', '#756188', '#986b27']
    for ax, model in zip(axes, ('tfidf', 'minilm')):
        for i, condition in enumerate(conditions):
            selected = [r for r in rows if r['model'] == model and r['condition'] == condition]
            offsets = np.linspace(-.15, .15, len(selected))
            ax.scatter(i + offsets, [r['reciprocal_rank'] for r in selected], color=colors[i], s=35, alpha=.8)
            ax.plot([i - .23, i + .23], [np.mean([r['reciprocal_rank'] for r in selected])] * 2, color=colors[i], linewidth=3)
        ax.set_xticks(range(len(labels)), labels, rotation=20, ha='right'); ax.set_ylim(-.025, 1.05)
        ax.set_title('TF-IDF' if model == 'tfidf' else 'Pinned MiniLM'); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel('Reciprocal rank of first known supporting source')
    fig.suptitle('Four fixed queries: dots are individual queries, lines are means')
    fig.text(.5, .01, '*Post-hoc fixed design repair. Unequal coverage/curation confound results; no general accuracy or sleep-training claim.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, .95))
    for extension in ('png', 'svg', 'pdf'):
        p = output / ('retrieval-audit.' + extension); fig.savefig(p, dpi=150)
        result['figures'].append({'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes()),
            'title': 'Fixed-query retrieval audit', 'alt': 'Per-query known-support reciprocal ranks for raw source, answer cards, qualified cards, naive full-list fusion and a post-hoc top5 repair, under TF-IDF and MiniLM. Four purposive queries; no general accuracy inference.'})
    plt.close(fig)
    if sha(Path(__file__).read_bytes()) != code_sha: raise ValueError('Executed code changed')
    (output / 'executed-retrieval-experiment.py').write_bytes(Path(__file__).read_bytes())
    (output / 'retrieval.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    allowlist = [{'file': 'retrieval.json', 'bytes': (output / 'retrieval.json').stat().st_size,
        'sha256': sha((output / 'retrieval.json').read_bytes())}] + result['figures']
    (output / 'output-manifest.json').write_text(json.dumps({'complete': True, 'public_allowlist': allowlist}, indent=2) + '\n')
    print(json.dumps({'coverage': result['coverage'], 'summary': summaries, 'sha256': allowlist[0]['sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frame', 'knowledge', 'queries', 'model', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args(); run(a.frame, a.knowledge, a.queries, a.model, a.output)
