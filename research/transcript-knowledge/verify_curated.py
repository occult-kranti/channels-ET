#!/usr/bin/env python3
"""Public curation joins and arithmetic checks; exact text is audited privately."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

FRAME = '0d69378f9e9a2280e7ed05981b647fbfe280016380b3072b2b3a320961ae2c8c'
SELECTION = 'a34eecf46cdf7909e5a3b0a69a2fc0b1d340ddf4a02022d879f8174f5e7141ad'
QTYPES = {'analyst_constructed', 'asr_question_candidate', 'rhetorical_or_uncertain', 'documentary_printed_paraphrase'}


def require(value, message):
    if not value: raise ValueError(message)


def unique(rows, key):
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), 'Repeated ' + key)
    return result


def privacy(value):
    if isinstance(value, dict):
        require(not {'text', 'question_text', 'answer_text', 'context_text', 'path'} & value.keys(), 'Raw text or private path field')
        for v in value.values(): privacy(v)
    elif isinstance(value, list):
        for v in value: privacy(v)
    elif isinstance(value, str):
        require(not any(x in value for x in ('/workspace/', '/dev/shm/', '/tmp/')), 'Private path leaked')


def prose_words(data):
    fields = {'questions': ('question', 'selection_basis'),
              'cards': ('paraphrase', 'conditions', 'time_scope', 'qualifying_note'),
              'context_notes': ('summary', 'conditions', 'coverage_scope')}
    return sum(len(row.get(k, '').split()) for table, keys in fields.items() for row in data[table] for k in keys)


def intervals(rows, limit):
    previous = -1
    for pair in rows:
        require(isinstance(pair, list) and len(pair) == 2, 'Malformed interval')
        a, b = pair
        require(type(a) is int and type(b) is int and previous < a < b <= limit, 'Unmerged or invalid reading intervals')
        previous = b


def verify_data(data, profiles, registry):
    privacy(data); cov = data['coverage']
    require(data['schema_version'] == 1 and data['status'] == 'completed_bounded_curation', 'Incomplete curation')
    require(data['bindings']['frame']['sha256'] == FRAME and data['bindings']['selection']['sha256'] == SELECTION,
            'Prospective source frame/selection differs')
    require(profiles['bindings']['frame_sha256'] == FRAME, 'Profile frame differs')
    docs = unique(registry['documents'], 'source_id'); ps = unique(profiles['profiles'], 'source_id')
    require(docs.keys() == ps.keys(), 'Canonical profile denominator differs')
    sources = unique(data['source_bindings'], 'source_id'); reads = unique(data['reading_coverage'], 'source_id')
    require(sources.keys() == reads.keys(), 'Reading and source binding set differs')
    for sid, s in sources.items():
        require(sid in docs, 'Unknown canonical source')
        for k in ('selected_edition_id', 'body_sha256', 'channel_id'):
            require(s[k] == docs[sid][k] == ps[sid][k], 'Selected source edition differs: ' + k)
        require(s['text_artifact_sha256'] == docs[sid]['text_artifact']['sha256'], 'Selected source artifact differs')
        require(s['body_words'] == docs[sid]['words'], 'Selected body word denominator differs')
        r = reads[sid]
        for k in ('selected_edition_id', 'body_sha256', 'body_words', 'body_characters'):
            require(r[k] == s[k], 'Reading binding differs')
        for key in ('new_intervals', 'prior_intervals', 'legacy_card_intervals'): intervals(r[key], s['body_characters'])
        for key in ('new_unique_words_read', 'prior_unique_words_read', 'legacy_support_words', 'combined_unique_words'):
            require(type(r[key]) is int and 0 <= r[key] <= r['body_words'], 'Reading word count out of bounds')
        require(max(r['new_unique_words_read'], r['prior_unique_words_read'], r['legacy_support_words']) <= r['combined_unique_words'] <=
                r['new_unique_words_read'] + r['prior_unique_words_read'] + r['legacy_support_words'], 'Combined overlap denominator invalid')
        require(r['complete_body_newly_read'] == (r['new_intervals'] == [[0, r['body_characters']]]), 'Complete-body scope differs')
    evidence = unique(data['evidence'], 'evidence_id')
    for e in evidence.values():
        s = sources[e['source_id']]
        for key in ('text_artifact_sha256', 'body_sha256'): require(e[key] == s[key], 'Evidence edition differs')
        a, b = e['start_character'], e['end_character']
        require(type(a) is int and type(b) is int and 0 <= a < b <= s['body_characters'], 'Evidence out of bounds')
        require(re.fullmatch('[0-9a-f]{64}', e['span_sha256']) is not None and type(e['words']) is int and e['words'] > 0, 'Invalid span hash/words')
        key = json.dumps([e['source_id'], e['body_sha256'], a, b, e['role']], separators=(',', ':'))
        require(e['evidence_id'] == 'e-' + hashlib.sha256(key.encode()).hexdigest()[:24], 'Evidence identity differs')
        require(e['audio_alignment_verified'] is False, 'Unsupported acoustic alignment')
    cards = unique(data['cards'], 'card_id'); questions = unique(data['questions'], 'question_id')
    legacy = 0; new = 0
    for c in cards.values():
        s = sources[c['source_id']]
        require(c['question_id'] in questions and c['supports'], 'Card lacks question/evidence')
        for k in ('selected_edition_id', 'body_sha256'): require(c[k] == s[k], 'Card edition differs')
        require(c['paraphrase'] and c['conditions'] and c['qualifying_note'], 'Unqualified or missing answer')
        require(not c['annotation']['human_validated'] and not c['annotation']['rankings_inspected'] and not c['annotation']['audio_listened'], 'Unsupported reading claim')
        for e in c['supports']:
            require(e == evidence.get(e['evidence_id']) and e['source_id'] == c['source_id'], 'Card/evidence join differs')
        if c['legacy_card_id']:
            legacy += 1
            require(c['annotation']['type'] == 'verified_prior_card_reuse' and c['parent_binding']['sha256'] == data['bindings']['prior_knowledge']['sha256'] and
                    c['parent_binding']['card_id'] == c['legacy_card_id'], 'Legacy parent binding differs')
        else:
            new += 1
            require(c['annotation']['type'] == 'new_manual_ai_bounded_reading' and c['parent_binding'] is None, 'New card provenance differs')
    for q in questions.values():
        require(q['question_type'] in QTYPES and q['informed_by_answer_reading'] is True, 'Question origin unclear')
        require(any(c['question_id'] == q['question_id'] for c in cards.values()), 'Question has no scoped answer card')
        if q['question_type'] == 'documentary_printed_paraphrase':
            d = q['documentary_binding']; require(d and d['source_id'] in sources, 'Printed question lacks documentary binding')
            if d.get('question_location_scope') == 'external_publisher_qa_artifact_not_canonical_body':
                require('question_evidence_id' not in d and 'start_character' not in d, 'External question assigned canonical-body coordinates')
                require(d['artifact_sha256'] in {x['sha256'] for x in data['documentary_external_artifacts']}, 'External artifact unbound')
            else:
                require(d['question_evidence_id'] in evidence and all(x in evidence for x in d['response_evidence_ids']), 'Documentary turn evidence missing')
        else:
            require(q['documentary_binding'] is None and q['extracted_question_id'] is None, 'Non-documentary question improperly linked')
    contexts = unique(data['context_notes'], 'channel_id'); frame_counts = Counter(d['channel_id'] for d in docs.values())
    require(contexts.keys() == frame_counts.keys(), 'A populated context is missing')
    for channel, n in contexts.items():
        ids = {sid for sid in sources if sources[sid]['channel_id'] == channel}
        require(set(n['source_ids']) == ids and len(n['source_ids']) == len(ids), 'Context source set differs')
        require(n['summary'] and n['conditions'] and n['evidence_ids'], 'Unsupported context note')
        require(all(eid in evidence and evidence[eid]['source_id'] in ids for eid in n['evidence_ids']), 'Context evidence join differs')
        require({evidence[eid]['source_id'] for eid in n['evidence_ids']} == ids, 'Context includes unsupported source')
        require(n['frame_source_units'] == frame_counts[channel] and n['unreviewed_source_units'] == frame_counts[channel] - len(ids), 'Context denominator differs')
        for k in ('new_unique_words_read', 'prior_unique_words_read'):
            require(n[k] == sum(reads[sid][k] for sid in ids), 'Context word count differs')
        has_new = n['new_unique_words_read'] > 0; has_prior = n['prior_unique_words_read'] > 0
        expected = 'new_and_prior_readings' if has_new and has_prior else 'new_bounded_reading' if has_new else 'verified_prior_reading_reuse'
        require(n['reading_status'] == expected, 'Context reading status differs')
    require(cov['frame_source_units'] == len(docs) == 493 and cov['frame_contexts'] == len(contexts) == 26, 'Frame denominator differs')
    require(cov['cards'] == len(cards) == 27 and cov['questions'] == len(questions) == 26, 'Card/question denominator differs')
    require(cov['legacy_cards_reused'] == legacy == 8 and cov['new_readings'] == new == 19, 'New/prior card distinction differs')
    require(cov['context_notes'] == len(contexts) and cov['sources_with_any_reading_or_legacy_support'] == len(reads), 'Reading source/context count differs')
    for k in ('new_unique_words_read', 'prior_unique_words_read', 'legacy_support_words', 'combined_unique_words'):
        require(cov[k] == sum(r[k] for r in reads.values()), 'Reading total differs: ' + k)
    new_spans = [e for e in evidence.values() if e['role'] == 'bounded_mixed_or_written_context']
    require(len(new_spans) == 19 and sum(e['words'] for e in new_spans) == cov['new_unique_words_read'] == 11290, 'Frozen new-window coverage differs')
    require(cov['new_complete_bodies'] == sum(r['complete_body_newly_read'] for r in reads.values()), 'Complete body count differs')
    require(cov['public_analyst_words'] == prose_words(data) <= cov['public_word_budget'] == 4500, 'Public prose budget differs')
    require(cov['human_validated'] is False and cov['audio_listened_seconds'] == 0, 'Unsupported validation coverage')
    require(sum(r['selected'] for r in data['reuse_dispositions']) == legacy and all(r['exact_edition_eligible'] for r in data['reuse_dispositions'] if r['selected']), 'Reuse eligibility differs')
    return {'status': 'passed', 'cards': len(cards), 'questions': len(questions), 'contexts': len(contexts),
            'new_words_read': cov['new_unique_words_read'], 'combined_unique_words': cov['combined_unique_words'],
            'scope': 'Public canonical joins and declared arithmetic; exact span bytes and interpretive fidelity require the separate private audit.'}


def verify(root):
    root = Path(root)
    curated = json.loads((root/'curated.json').read_text())
    profiles = json.loads((root/'profiles.json').read_text())
    registry = json.loads((root.parent/'channel-lab/registry.json').read_text())
    return verify_data(curated, profiles, registry)
