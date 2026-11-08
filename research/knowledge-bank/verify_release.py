#!/usr/bin/env python3
"""Verify the static knowledge-bank artifact joins using only the standard library."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
from urllib.parse import urlsplit

from verify_analysis import verify as verify_analysis
from verify_contextual_terms import verify as verify_contextual_terms
from verify_asr_sensitivity import verify as verify_asr_sensitivity


def require(condition, message):
    if not condition: raise ValueError(message)


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-8)


def safe_file(directory, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name, 'Unsafe public path')
    target = (directory / p).resolve()
    require(target.is_relative_to(directory.resolve()) and target.is_file(), 'Missing/outside public artifact')
    return target


def checked(directory, ref):
    path = safe_file(directory, ref['file']); raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'Artifact hash/size differs: ' + ref['file'])
    if path.suffix == '.json':
        require(b'/workspace/' not in raw and b'channels-et-private' not in raw and b'private_evidence_text' not in raw, 'Private source content/path in public JSON')
    return raw


def knowledge_checks(k, analysis, database):
    sources = {x['source_id']: x for x in k['sources']}
    require(len(sources) == len(k['sources']) == k['coverage']['source_frame_documents'], 'Knowledge source count differs')
    require(sum(x['words'] for x in sources.values()) == k['coverage']['source_frame_words'], 'Knowledge word count differs')
    require(set(sources) == {x['source_id'] for x in analysis['documents']}, 'Analysis/knowledge source sets differ')
    for d in analysis['documents']:
        s = sources[d['source_id']]
        require(d['text_sha256'] == s['body_sha256'] and d['text_artifact_sha256'] == s['text_artifact_sha256'], 'Knowledge/analysis source edition differs')
        require(urlsplit(s['source_url']).scheme in ('http', 'https'), 'Unsafe source URL')
        require(s['speaker_identity_verified'] is False, 'Unsupported speaker verification claim')
    questions = {x['question_id']: x for x in k['questions']}
    cards = {x['card_id']: x for x in k['cards']}
    require(len(questions) == len(k['questions']) == k['coverage']['questions'], 'Question count differs')
    require(len(cards) == len(k['cards']) == k['coverage']['cards'], 'Card count differs')
    kinds = Counter(q['question_type'] for q in questions.values())
    require(kinds['analyst_constructed'] == k['coverage']['analyst_questions'], 'Analyst question count differs')
    require(kinds['documentary_printed_paraphrase'] == k['coverage']['documentary_questions'], 'Documentary paraphrase count differs')
    supports = 0
    for card in cards.values():
        require(card['source_id'] in sources and card['question_id'] in questions, 'Unbound card')
        require(card['paraphrase'].strip() and card['qualifying_note'].strip(), 'Missing card content/qualification')
        require(card['annotation']['human_validated'] is False, 'Unsupported human validation claim')
        require(card['supports'], 'Card lacks source support')
        for s in card['supports']:
            supports += 1; source = sources[s['source_id']]
            require(s['source_id'] == card['source_id'], 'Card support references a different source')
            require(s['body_sha256'] == source['body_sha256'] and s['text_artifact_sha256'] == source['text_artifact_sha256'], 'Support source hash differs')
            require(0 <= s['start_character'] < s['end_character'] and s['words'] > 0, 'Invalid support bounds')
    relations = Counter()
    for c in k['comparisons']:
        require(c['left_card_id'] in cards and c['right_card_id'] in cards and c['question_id'] in questions, 'Unbound comparison')
        require(cards[c['left_card_id']]['question_id'] == cards[c['right_card_id']]['question_id'] == c['question_id'], 'Comparison uses different questions')
        require(c['identity_equivalence'] is False and c['qualification'], 'Unqualified identity/equivalence claim')
        relations[c['relation']] += 1
    require(len(k['comparisons']) == k['coverage']['comparisons'], 'Comparison count differs')
    require(all(relations.get(key, 0) == value for key, value in k['coverage']['relation_counts'].items()), 'Relation tally differs')
    nodes = {n['id'] for n in k['graph']['nodes']}
    require(len(nodes) == len(k['graph']['nodes']), 'Duplicate graph node')
    for e in k['graph']['edges']:
        require(e['source'] in nodes and e['target'] in nodes, 'Dangling knowledge-graph edge')
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as con:
        require(con.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Question database integrity failure')
        require(not con.execute('PRAGMA foreign_key_check').fetchall(), 'Question database foreign-key failure')
        for table, expected in [('sources', len(sources)), ('questions', len(questions)), ('cards', len(cards)),
                ('comparisons', len(k['comparisons'])), ('supports', supports), ('graph_nodes', len(nodes)), ('graph_edges', len(k['graph']['edges']))]:
            require(con.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] == expected, 'Database/JSON count differs: ' + table)
        for sid, body_hash in con.execute('SELECT source_id,body_sha256 FROM sources'):
            require(sources[sid]['body_sha256'] == body_hash, 'Database source binding differs')
        for cid, text, conditions, time_scope, note in con.execute('SELECT card_id,paraphrase,conditions,time_scope,qualifying_note FROM cards'):
            require((text, conditions, time_scope, note) == tuple(cards[cid][key] for key in ('paraphrase', 'conditions', 'time_scope', 'qualifying_note')), 'Database card differs from JSON')
        tables = {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(not {'source_bodies', 'evidence_spans', 'private_evidence'} & tables, 'Private evidence table in public database')
    require(b'/workspace/' not in database.read_bytes() and b'private_evidence_text' not in database.read_bytes(), 'Private data marker in public database')
    return {'sources': len(sources), 'questions': len(questions), 'cards': len(cards), 'comparisons': len(k['comparisons']), 'supports': supports, 'graph_nodes': len(nodes), 'graph_edges': len(k['graph']['edges'])}


def retrieval_checks(r, knowledge, knowledge_sha, directory):
    require(r['input_bindings']['knowledge']['sha256'] == knowledge_sha, 'Retrieval uses a different knowledge edition')
    sources = {s['source_id'] for s in knowledge['sources']}; queries = {q['query_id']: q for q in r['queries']}
    require(len(queries) == r['coverage']['queries'] == 4, 'Frozen retrieval query count differs')
    require(r['coverage']['sources'] == len(sources), 'Retrieval source universe differs')
    require(r['coverage']['card_sources'] == len({c['source_id'] for c in knowledge['cards']}), 'Card index source count differs')
    seen = set()
    for row in r['results']:
        key = (row['model'], row['condition'], row['query_id']); require(key not in seen, 'Duplicate retrieval result'); seen.add(key)
        ranked = row['ranked_sources']; ids = [x['source_id'] for x in ranked]
        require(len(ids) == len(set(ids)) and set(ids) <= sources, 'Invalid source ranks')
        require([x['rank'] for x in ranked] == list(range(1, len(ranked) + 1)), 'Nonsequential ranks')
        relevant = set(queries[row['query_id']]['known_relevant_source_ids']); require(relevant <= sources, 'Unknown known-support label')
        ranks = [ids.index(sid) + 1 for sid in relevant if sid in ids]; first = min(ranks) if ranks else None
        require(row['first_known_support_rank'] == first and close(row['reciprocal_rank'], 1 / first if first else 0), 'Retrieval reciprocal rank differs')
        require(close(row['known_support_index_coverage'], len(ranks) / len(relevant)), 'Retrieval source coverage differs')
        for k, value in row['hit_at_k'].items(): require(value == int(bool(set(ids[:int(k)]) & relevant)), 'Known-support hit differs')
    for s in r['summary']:
        rows = [x for x in r['results'] if x['model'] == s['model'] and x['condition'] == s['condition']]
        require(len(rows) == s['queries'] == 4, 'Retrieval summary count differs')
        require(close(statistics.mean(x['reciprocal_rank'] for x in rows), s['mean_reciprocal_rank']), 'Retrieval mean differs')
        for key, value in s['known_support_hit_rate'].items(): require(close(statistics.mean(x['hit_at_k'][key] for x in rows), value), 'Retrieval mean hit differs')
    require(len(r['results']) == 40 and len(r['summary']) == 10, 'Executed retrieval condition frame differs')
    require(r['naive_fusion_coverage_bias']['all_covered_sources_outrank_all_uncovered_by_construction'] is True, 'Naive coverage bias disclosure missing')
    require(r['protocol_amendments'] and any(c['role'] == 'post_hoc_sensitivity' for c in r['conditions']), 'Post-hoc repair disclosure missing')
    for c in r['encoding_coverage']: require(c['truncated_content_wordpieces'] == 0 and c['processed_content_wordpieces'] == c['content_wordpieces'], 'Truncated retrieval encoding')
    for fig in r['figures']: checked(directory, {**fig, 'file': 'figures/' + fig['file']})
    return {'queries': len(queries), 'conditions': len(r['summary']), 'rankings': len(r['results'])}


def asr_checks(a):
    clips = a['clips']; summary = a['summary']
    require(a['measurement']['accuracy_measured'] is False, 'Unsupported speech-accuracy claim')
    require(len(clips) == summary['paired_windows'] == 16 and len({c['clip_id'] for c in clips}) == 16, 'Paired window count differs')
    require(len({c['source_audio_sha256'] for c in clips}) == summary['recordings'] == 8, 'Recording count differs')
    require(len({c['context'] for c in clips}) == summary['source_contexts'], 'Context count differs')
    require(close(sum(c['duration_seconds'] for c in clips), summary['unique_audio_seconds']) and summary['unique_audio_seconds'] == 480, 'Benchmark duration differs')
    by_source = defaultdict(list)
    for c in clips:
        require(0 <= c['start_seconds'] < c['end_seconds'] <= c['recording_duration_seconds'], 'Window outside recording')
        require(close(c['end_seconds'] - c['start_seconds'], c['duration_seconds']), 'Window duration differs')
        by_source[c['source_audio_sha256']].append(c)
        for prefix in ('baseline', 'upgraded'):
            require(close(c[prefix + '_real_time_factor'], c[prefix + '_inference_seconds'] / c['duration_seconds']), 'Window real-time factor differs')
        require(0 <= c['symmetric_normalized_word_edit_distance'] <= 1 and 0 <= c['token_set_jaccard'] <= 1, 'Invalid disagreement measure')
    for rows in by_source.values():
        rows.sort(key=lambda c: c['start_seconds']); require(all(a['end_seconds'] <= b['start_seconds'] for a, b in zip(rows, rows[1:])), 'Overlapping benchmark windows')
    for prefix in ('baseline', 'upgraded'):
        p = a[prefix + '_performance']
        require(sum(c[prefix + '_words'] for c in clips) == p['recognized_whitespace_words'], 'Recognized word count differs')
        require(close(statistics.median(c[prefix + '_real_time_factor'] for c in clips), p['median_real_time_factor']), 'Median real-time factor differs')
        require(p['workers'] == 2 and p['cpu_threads_per_worker'] == 1 and 0 < p['actual_inference_overlap_seconds'] <= p['outer_stage_wall_seconds'], 'Parallel execution accounting differs')
    require(close(statistics.median(c['symmetric_normalized_word_edit_distance'] for c in clips), summary['median_symmetric_normalized_word_edit_distance']), 'Median ASR disagreement differs')
    require(sum(c['baseline_negation_cues'] != c['upgraded_negation_cues'] for c in clips) == summary['windows_with_negation_count_difference'], 'Negation cue count differs')
    return {'paired_windows': len(clips), 'audio_seconds': summary['unique_audio_seconds'], 'accuracy_measured': False}


def full_asr_checks(full, sensitivity, analysis):
    rows, summary = full['documents'], full['summary']
    require(len(rows) == summary['recordings'] == summary['full_text_editions_retranscribed'] == 4, 'Full ASR recording count differs')
    counterparts = {r['counterpart_source_id']: r for r in rows}
    require(len(counterparts) == len(rows) and len({r['source_id'] for r in rows}) == len(rows), 'Duplicate full ASR edition')
    baseline = {r['source_id']: r for r in analysis['documents']}
    require(set(counterparts) == {r['source_id'] for r in sensitivity['records']}, 'Full/sensitivity source frame differs')
    require(full['provenance']['private_manifest_sha256'] == sensitivity['bindings']['new_manifest_sha256'], 'Full/sensitivity producer binding differs')
    for row in rows:
        coverage = row['coverage']; old = baseline[row['counterpart_source_id']]
        require(row['source_id'] != row['counterpart_source_id'] and row['old_text_artifact_sha256'] == old['text_artifact_sha256'], 'Full ASR replaced or mismatched its old edition')
        require(row['old_words'] == old['words'], 'Full ASR old word count differs')
        require(row['sample_count'] == coverage['input_samples'] == coverage['covered_samples'], 'Incomplete full ASR sample coverage')
        require(row['chunks'] == coverage['chunk_count'] == math.ceil(row['sample_count'] / 480000), 'Full ASR chunk count differs')
        require(all(coverage[k] is True for k in ('contiguous', 'starts_at_zero', 'ends_at_sample_count', 'all_encoder_exhausted')), 'Full ASR coverage guard failed')
        require(close(row['duration_seconds'], row['sample_count'] / 16000) and close(row['last_chunk_seconds'], (row['sample_count'] - (row['chunks'] - 1) * 480000) / 16000), 'Full ASR tail/duration differs')
        require(0 <= row['empty_text_chunks'] <= row['chunks'] and row['accuracy_verified'] is False and row['speaker_role'] == 'unknown', 'Unsupported full ASR accuracy/speaker claim')
    for key, field in [('chunks', 'chunks'), ('covered_samples', 'sample_count'), ('new_words', 'new_words'), ('old_words', 'old_words'), ('empty_text_chunks', 'empty_text_chunks')]:
        require(summary[key] == sum(r[field] for r in rows), 'Full ASR summary differs: ' + key)
    require(close(summary['covered_audio_seconds'], sum(r['duration_seconds'] for r in rows)), 'Full ASR summed duration differs')
    require(summary['new_audio_downloads'] == 0 and summary['old_editions_preserved'] is True, 'Full ASR acquisition/edition scope differs')
    for row in sensitivity['records']:
        other = counterparts[row['source_id']]
        for key in ('old_words', 'new_words', 'sample_count', 'audio_sha256', 'canonical_s16_pcm_sha256', 'model_f32_pcm_sha256', 'old_text_artifact_sha256', 'new_text_artifact_sha256', 'new_asr_receipt_sha256'):
            require(row[key] == other[key], 'Full/sensitivity edition mismatch: ' + key)
        require(row['new_edition_id'] == other['source_id'] and row['chunk_count'] == other['chunks'], 'Full/sensitivity edition ID/count differs')
    p = full['performance']
    require(p['workers'] == 2 and p['cpu_threads_per_worker'] == 1 and 0 < p['actual_inference_overlap_seconds'] <= p['stage_wall_seconds'], 'Full ASR concurrency accounting differs')
    return {**summary, 'accuracy_measured': False}


def verify(site):
    directory = Path(site).resolve() / 'dist/knowledge-bank'
    manifest = json.loads((directory / 'manifest.json').read_text()); modules = {}
    for key, descriptor in manifest['modules'].items():
        modules[key] = json.loads(checked(directory, descriptor))
    require({'analysis', 'knowledge', 'asr', 'literature', 'experiments', 'retrieval', 'contextual_terms', 'full_asr', 'asr_sensitivity'} <= modules.keys(), 'Required accepted release modules missing')
    for artifact in manifest['artifacts']: checked(directory, artifact)
    analysis_check = verify_analysis(directory)
    kcheck = knowledge_checks(modules['knowledge'], modules['analysis'], safe_file(directory, 'questions.sqlite'))
    rcheck = retrieval_checks(modules['retrieval'], modules['knowledge'], manifest['modules']['knowledge']['sha256'], directory)
    acheck = asr_checks(modules['asr'])
    contextual_check = verify_contextual_terms(directory) if 'contextual_terms' in modules else None
    sensitivity_check = verify_asr_sensitivity(directory) if 'asr_sensitivity' in modules else None
    full_check = full_asr_checks(modules['full_asr'], modules['asr_sensitivity'], modules['analysis'])
    require(len({x['id'] for x in modules['literature']['records']}) == len(modules['literature']['records']), 'Duplicate literature identity')
    require(all(x['status'] in ('executed', 'partially_executed', 'proposed', 'deferred') for x in modules['experiments']['experiments']), 'Unrecognized experiment execution status')
    return {'status': 'passed', 'analysis': analysis_check, 'knowledge': kcheck, 'retrieval': rcheck, 'asr': acheck,
        'contextual_terms': contextual_check, 'asr_sensitivity': sensitivity_check, 'full_asr': full_check,
        'scope': 'Static source/artifact joins, database and accounting; independent source readings, model/output checks and refits are separately documented.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--site', type=Path, required=True)
    print(json.dumps(verify(p.parse_args().site)))
