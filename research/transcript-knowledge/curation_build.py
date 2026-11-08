#!/usr/bin/env python3
"""Join bounded AI readings to immutable canonical editions; export paraphrases only."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from curation_select import binding, loader, sha


def require(value, message):
    if not value:
        raise ValueError(message)


def read_bound(ref):
    raw = Path(ref['path']).read_bytes()
    require(sha(raw) == ref['sha256'] and len(raw) == ref['bytes'], 'Frozen input changed')
    return json.loads(raw)


def portable(ref):
    return {k: ref[k] for k in ('bytes', 'sha256')}


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def word_count(text, intervals):
    """Count canonical whitespace tokens touched by merged character intervals once."""
    ranges = merge(intervals)
    return sum(any(m.start() < end and m.end() > start for start, end in ranges)
               for m in re.finditer(r'\S+', text))


def support(record, text, start, end, role='unknown'):
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(text), 'Invalid support bounds')
    span = text[start:end]
    digest = sha(span.encode())
    key = json.dumps([record['source_id'], record['body_sha256'], start, end, role], separators=(',', ':'))
    return {'evidence_id': 'e-' + sha(key.encode())[:24], 'source_id': record['source_id'],
            'text_artifact_sha256': record['text_artifact']['sha256'], 'body_sha256': record['body_sha256'],
            'start_character': start, 'end_character': end, 'span_sha256': digest,
            'words': len(span.split()), 'role': role, 'audio_alignment_verified': False}


def check_support(item, record, text):
    expected = support(record, text, item['start_character'], item['end_character'], item['role'])
    for key in ('source_id', 'text_artifact_sha256', 'body_sha256', 'span_sha256', 'words'):
        require(item[key] == expected[key], 'Evidence mismatch: ' + key)
    return expected


def public_words(data):
    values = []
    for q in data['questions']:
        values.extend(q.get(k, '') for k in ('question', 'selection_basis'))
    for c in data['cards']:
        values.extend(c.get(k, '') for k in ('paraphrase', 'conditions', 'time_scope', 'qualifying_note'))
    for n in data['context_notes']:
        values.extend(n.get(k, '') for k in ('summary', 'conditions', 'coverage_scope'))
    return sum(len(s.split()) for s in values)


def build(selection_path, annotations_path, output):
    require(not output.exists(), 'Use a fresh immutable release directory')
    selection = json.loads(selection_path.read_text())
    annotation = json.loads(annotations_path.read_text())
    require(sha(selection_path.read_bytes()) == annotation['selection_sha256'], 'Annotation selection differs')
    require(not annotation['rankings_inspected'] and not annotation['human_validated'] and annotation['audio_listened_seconds'] == 0,
            'Unsupported validation or blinded-selection claim')
    frame = read_bound(selection['source_bindings']['frame'])
    old = read_bound(selection['source_bindings']['previous_knowledge'])
    prior = read_bound(selection['source_bindings']['previous_readings'])
    records = {r['source_id']: r for r in frame['records']}
    require(len(records) == len(frame['records']), 'Repeated canonical source')
    source = loader(); texts = {}

    def body(sid):
        if sid not in texts:
            r = records[sid]; texts[sid] = source.body(r['text_artifact'], r['body_transform'])
            require(sha(texts[sid].encode()) == r['body_sha256'] and len(texts[sid].split()) == r['words'], 'Canonical body differs')
        return texts[sid]

    evidence = {}; private_evidence = {}; new_intervals = defaultdict(list); prior_intervals = defaultdict(list)
    legacy_intervals = defaultdict(list); new_supports = {}; prior_supports = defaultdict(list)

    def add(item):
        sid = item['source_id']; check_support(item, records[sid], body(sid))
        eid = item['evidence_id']
        if eid in evidence:
            require(evidence[eid] == item, 'Evidence ID collision')
        evidence[eid] = item
        private_evidence[eid] = {**item, 'text': body(sid)[item['start_character']:item['end_character']]}
        return item

    selected = {w['reading_id']: w for w in selection['selected_windows']}
    require(len(selected) == 19 and set(selected) == {a['reading_id'] for a in annotation['readings']} and len(annotation['readings']) == 19,
            'Reading selection incomplete or repeated')
    for w in selected.values():
        sid = w['source_id']; r = records[sid]
        require(r['body_sha256'] == w['body_sha256'] and r['selected_edition_id'] == w['selected_edition_id'], 'New edition mismatch')
        e = support(r, body(sid), w['start_character'], w['end_character'], 'bounded_mixed_or_written_context')
        require(e['span_sha256'] == w['span_sha256'] and e['words'] == w['words'], 'Frozen reading window changed')
        new_supports[w['reading_id']] = add(e)
        new_intervals[sid].append([e['start_character'], e['end_character']])

    for p in prior['source_bindings']:
        sid = p['source_id']; r = records[sid]
        require(r['body_sha256'] == p['body_sha256'] and r['text_artifact']['sha256'] == p['text_artifact_sha256'], 'Prior reading edition mismatch')
        for start, end in p['merged_intervals']:
            e = add(support(r, body(sid), start, end, 'verified_prior_reading_interval'))
            prior_supports[r['channel_id']].append(e['evidence_id'])
            prior_intervals[sid].append([start, end])
        require(word_count(body(sid), prior_intervals[sid]) == p['unique_words_inspected'], 'Prior reading word count differs')

    cards = []; questions = {}; new_notes = {}; external_bindings = []
    for a in annotation['readings']:
        w = selected[a['reading_id']]; sid = w['source_id']; r = records[sid]
        suffix = a['reading_id'].removeprefix('new-reading-'); qid = 'tq-new-' + suffix
        q = {'question_id': qid, 'question_type': a['question_type'], 'question': a['question'], 'topic_id': a['topic_id'],
             'selection_basis': 'AI paraphrase after a prospectively selected bounded reading; not an evaluation query.',
             'informed_by_answer_reading': True, 'extracted_question_id': None, 'documentary_binding': None}
        cs = [new_supports[a['reading_id']]]
        if a['reading_id'] == 'new-reading-18':
            raw = json.loads(Path(r['text_artifact']['path']).read_text())
            qt = next(t for t in raw['turns'] if t['turn_id'] == 'ra:001:0002')
            at = next(t for t in raw['turns'] if t['turn_id'] == 'ra:001:0003')
            locators = []
            for t in (qt, at):
                content = unicodedata.normalize('NFKC', t['text']).strip()
                require(body(sid).count(content) == 1, 'Ra printed turn not uniquely locatable')
                start = body(sid).index(content); end = start + len(content)
                require(w['start_character'] <= start < end <= w['end_character'], 'Printed turn outside read window')
                e = support(r, body(sid), start, end, 'publisher_printed_' + t['role'])
                e['turn_ids'] = [t['turn_id']]; e['printed_question_id'] = t['question_id']; locators.append(add(e))
            cs = [locators[1]]
            q['documentary_binding'] = {'source_id': sid, 'artifact_sha256': r['text_artifact']['sha256'],
                                       'turn_id': qt['turn_id'], 'printed_question_id': qt['question_id'],
                                       'question_evidence_id': locators[0]['evidence_id'],
                                       'response_evidence_ids': [locators[1]['evidence_id']],
                                       'question_role': 'publisher printed Questioner', 'response_role': 'publisher printed Ra; identity unverified'}
            require((locators[0]['start_character'], locators[0]['end_character'], locators[0]['span_sha256']) ==
                    (3323, 3441, '29abd7e26f9eb49a5b48ed64d2a4235aaae82139da58f98da53b725a6239ec16') and
                    (locators[1]['start_character'], locators[1]['end_character'], locators[1]['span_sha256']) ==
                    (3442, 4496, '68ff420e5faeddaecaece428be3458bea2a1b6bd3e79f97f7ef7915bf0f14ec6'),
                    'Independently extracted Ra question/answer locator changed')
            q['extracted_question_id'] = 'tk-37471ef47a29d467a41bbb53'
        questions[qid] = q
        cards.append({'card_id': 'tc-new-' + suffix, 'question_id': qid, 'source_id': sid,
                      'selected_edition_id': r['selected_edition_id'], 'body_sha256': r['body_sha256'],
                      **{k: a[k] for k in ('paraphrase', 'claim_type', 'conditions', 'time_scope', 'qualifying_note')},
                      'supports': cs, 'annotation': {'type': 'new_manual_ai_bounded_reading', 'human_validated': False,
                                                    'rankings_inspected': False, 'audio_listened': False},
                      'legacy_card_id': None, 'parent_binding': None,
                      'index_text_policy': 'Answer paraphrase, conditions and qualifier only; exclude question text.'})
        new_notes[r['channel_id']] = {'summary': a['summary'], 'conditions': a['qualifying_note'],
                                      'evidence_id': new_supports[a['reading_id']]['evidence_id']}

    old_cards = {c['card_id']: c for c in old['cards']}; old_questions = {q['question_id']: q for q in old['questions']}
    old_hash = selection['source_bindings']['previous_knowledge']['sha256']
    for chosen in selection['legacy_cards_selected']:
        oldcard = old_cards[chosen['legacy_card_id']]; sid = chosen['canonical_source_id']; r = records[sid]
        require(r['body_sha256'] == chosen['body_sha256'] and r['text_artifact']['sha256'] == chosen['text_artifact_sha256'], 'Legacy edition mismatch')
        c = deepcopy(oldcard); c['source_id'] = sid
        c['supports'] = []
        for previous in oldcard['supports']:
            s = {**previous, 'source_id': sid}
            e = check_support(s, r, body(sid))
            for key in ('turn_ids', 'start_seconds', 'end_seconds', 'audio_alignment_verified'):
                if key in s: e[key] = s[key]
            c['supports'].append(add(e)); legacy_intervals[sid].append([e['start_character'], e['end_character']])
        c.update(selected_edition_id=r['selected_edition_id'], body_sha256=r['body_sha256'], legacy_card_id=oldcard['card_id'],
                 parent_binding={'sha256': old_hash, 'card_id': oldcard['card_id']},
                 annotation={'type': 'verified_prior_card_reuse', 'human_validated': False, 'rankings_inspected': False,
                             'audio_listened': False, 'original_annotation': oldcard['annotation']})
        cards.append(c)
        q = deepcopy(old_questions[c['question_id']]); q['extracted_question_id'] = None
        q.setdefault('documentary_binding', None)
        if q['documentary_binding']:
            qa_path = Path('/workspace/channels-et-private/expanded-channeling-2026-11/et-sources/normalized-pilot/lyssa138-qa.json')
            qa_ref = binding(qa_path); qb = q['documentary_binding']
            require(qa_ref['sha256'] == qb['artifact_sha256'], 'External documentary question artifact changed')
            qt = next(t for t in json.loads(qa_path.read_text())['turns'] if t['id'] == qb['turn_id'])
            require(sha(qt['question'].encode()) == qb['question_sha256'], 'External printed question bytes differ')
            external_bindings.append({'kind': 'external_publisher_qa', **portable(qa_ref)})
            q['documentary_binding']['legacy_source_id'] = q['documentary_binding']['source_id']
            q['documentary_binding']['source_id'] = sid
            q['documentary_binding']['question_location_scope'] = 'external_publisher_qa_artifact_not_canonical_body'
        questions[q['question_id']] = q

    counts = Counter(r['channel_id'] for r in records.values()); previous_notes = {n['channel_id']: n for n in prior['channel_notes']}
    notes = []; coverage = []; all_read_ids = set(new_intervals) | set(prior_intervals) | set(legacy_intervals)
    for sid in sorted(all_read_ids):
        r = records[sid]; new = merge(new_intervals[sid]); previous = merge(prior_intervals[sid]); legacy = merge(legacy_intervals[sid])
        coverage.append({'source_id': sid, 'selected_edition_id': r['selected_edition_id'], 'body_sha256': r['body_sha256'],
                         'body_words': r['words'], 'body_characters': len(body(sid)), 'new_intervals': new, 'prior_intervals': previous,
                         'legacy_card_intervals': legacy, 'new_unique_words_read': word_count(body(sid), new),
                         'prior_unique_words_read': word_count(body(sid), previous),
                         'legacy_support_words': word_count(body(sid), legacy),
                         'combined_unique_words': word_count(body(sid), new + previous + legacy),
                         'complete_body_newly_read': new == [[0, len(body(sid))]]})
    by_source = {r['source_id']: r for r in coverage}
    for channel in sorted(counts):
        oldnote = previous_notes[channel]; newnote = new_notes.get(channel)
        ids = sorted(sid for sid in all_read_ids if records[sid]['channel_id'] == channel)
        previous_ids = oldnote['reviewed_source_ids']; new_ids = [sid for sid in ids if new_intervals[sid]]
        require(previous_ids or new_ids, 'Context lacks a bounded reading')
        summary = oldnote['summary'] if previous_ids else ''
        conditions = oldnote['conditions'] if previous_ids else ''
        if newnote:
            summary = (summary + ' ' + newnote['summary']).strip()
            conditions = (conditions + ' ' + newnote['conditions']).strip()
        notes.append({'channel_id': channel, 'channel_name': oldnote['channel_name'], 'summary': summary, 'conditions': conditions,
                      'reading_status': 'new_and_prior_readings' if previous_ids and new_ids else 'new_bounded_reading' if new_ids else 'verified_prior_reading_reuse',
                      'source_ids': ids, 'evidence_ids': sorted(set(prior_supports[channel] + ([newnote['evidence_id']] if newnote else []) +
                          [e['evidence_id'] for c in cards if c['legacy_card_id'] and records[c['source_id']]['channel_id'] == channel for e in c['supports']])),
                      'new_unique_words_read': sum(by_source[sid]['new_unique_words_read'] for sid in ids),
                      'prior_unique_words_read': sum(by_source[sid]['prior_unique_words_read'] for sid in ids),
                      'frame_source_units': counts[channel], 'unreviewed_source_units': counts[channel] - len(ids),
                      'coverage_scope': 'Selected text passages; remaining text, other editions and whole-channel prevalence unreviewed.',
                      'prior_summary_binding': {'sha256': selection['source_bindings']['previous_readings']['sha256'], 'channel_id': channel} if previous_ids else None})
    bindings = []
    for sid in sorted(all_read_ids):
        r = records[sid]; u = urlsplit(r.get('publication_url') or r['source_url'])
        bindings.append({'source_id': sid, 'selected_edition_id': r['selected_edition_id'], 'body_sha256': r['body_sha256'],
                         'text_artifact_sha256': r['text_artifact']['sha256'], 'title': r['title'],
                         'source_url': urlunsplit((u.scheme, u.netloc, u.path, '', '')), 'channel_id': r['channel_id'],
                         'body_words': r['words'], 'body_characters': len(body(sid))})
    result = {'schema_version': 1, 'status': 'completed_bounded_curation', 'questions': list(questions.values()), 'cards': cards,
              'context_notes': notes, 'reading_coverage': coverage, 'source_bindings': bindings, 'evidence': list(evidence.values()),
              'bindings': {'frame': portable(selection['source_bindings']['frame']), 'selection': portable(binding(selection_path)),
                           'prior_knowledge': portable(selection['source_bindings']['previous_knowledge']),
                           'prior_readings': portable(selection['source_bindings']['previous_readings']),
                           'annotations': portable(binding(annotations_path)), 'producer': portable(binding(Path(__file__)))},
              'documentary_external_artifacts': list({r['sha256']: r for r in external_bindings}.values()),
              'reuse_dispositions': selection['legacy_reuse_dispositions'],
              'limitations': ['Purposeful short-window selection is not a random sample or an exhaustive interpretation of the corpus.',
                              'Questions were authored after source reading and are not held-out retrieval evaluation queries.',
                              'Interview ASR has unknown voices; questions, quoted dialogue, ads and rhetorical examples can coexist.',
                              'Printed roles establish documentary structure, not purported entity identity or statement truth.',
                              'New and prior AI reading scopes are distinct; no human validation or audio listening is claimed.',
                              'Recurring entities or topics do not establish agreement; changed editions require fresh annotations.',
                              'Character offsets refer to NFKC-normalized canonical text, not timestamps or PDF page coordinates.']}
    result['coverage'] = {'frame_source_units': len(records), 'frame_contexts': len(counts), 'new_readings': len(selected),
                          'new_unique_words_read': sum(r['new_unique_words_read'] for r in coverage),
                          'prior_unique_words_read': sum(r['prior_unique_words_read'] for r in coverage),
                          'legacy_support_words': sum(r['legacy_support_words'] for r in coverage),
                          'combined_unique_words': sum(r['combined_unique_words'] for r in coverage),
                          'sources_with_any_reading_or_legacy_support': len(all_read_ids), 'legacy_cards_reused': 8,
                          'cards': len(cards), 'questions': len(questions), 'context_notes': len(notes),
                          'new_complete_bodies': sum(r['complete_body_newly_read'] for r in coverage),
                          'public_analyst_words': public_words(result), 'public_word_budget': selection['public_analyst_word_budget'],
                          'human_validated': False, 'audio_listened_seconds': 0}
    require(result['coverage']['public_analyst_words'] <= selection['public_analyst_word_budget'], 'Public prose exceeds frozen budget')
    require(len(cards) == 27 and len(notes) == 26, 'Curation denominator differs')
    output.mkdir(parents=True)
    def write(name, value):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    write('curated.json', result)
    write('curated-evidence-private.json', {'selection_sha256': annotation['selection_sha256'],
                                           'annotations_sha256': sha(annotations_path.read_bytes()),
                                           'evidence': list(private_evidence.values())})
    write('output-manifest.json', {'schema_version': 1, 'module': 'curated', 'status': 'completed',
                                   'public_allowlist': [{'file': 'curated.json', **portable(binding(output/'curated.json'))}]})
    print(json.dumps({'output': str(output), **result['coverage'], 'curated_sha256': sha((output/'curated.json').read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--annotations', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); build(args.selection, args.annotations, args.output)
