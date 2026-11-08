#!/usr/bin/env python3
"""Freeze diverse source/windows before new retrieval rankings are inspected."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path('/workspace/channels-et-private')
REUSE = ['c-contact-physical', 'c-timing-pamela', 'c-mediation-jeshua',
         'c-mediation-andromedan', 'c-practice-daniel', 'c-care-mary-boundaries',
         'c-lyssa138-qa-01', 'c-lyssa138-qa-03']


def sha(raw): return hashlib.sha256(raw).hexdigest()
def binding(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def loader():
    spec = importlib.util.spec_from_file_location('curation_source_loader', ROOT/'research/channel-lab/sources.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def window(text):
    words = list(re.finditer(r'\S+', text))
    if len(words) <= 700:
        return 0, len(text), 'complete_body_at_most_700_words'
    question = text.find('?', words[len(words)//4].start())
    if question >= 0:
        pivot = next((i for i, m in enumerate(words) if m.end() > question), len(words)//2)
        first = max(0, min(len(words)-600, pivot-80))
        basis = 'first_question_mark_after_first_quarter;80_words_before_then_up_to600_total'
    else:
        first = (len(words)-600)//2
        basis = 'no_question_mark_after_first_quarter;central600_word_window'
    return words[first].start(), words[min(first+600, len(words))-1].end(), basis


def select(output):
    if output.exists(): raise ValueError('Use a fresh immutable selection directory')
    frame_path = PRIVATE/'channel-lab-2026-11/frame-02/frame.json'
    old_readings = PRIVATE/'channel-lab-2026-11/readings/release-02/readings.json'
    old_knowledge = PRIVATE/'knowledge-bank-2026-11/knowledge/release-02/knowledge.json'
    frame = json.loads(frame_path.read_text()); readings = json.loads(old_readings.read_text())
    knowledge = json.loads(old_knowledge.read_text()); records = frame['records']
    prior_read_ids = {x['source_id'] for x in readings['source_bindings']}
    read_channels = {x['channel_id'] for x in readings['source_bindings']}
    choices = []
    for channel in sorted({r['channel_id'] for r in records}-read_channels):
        row = min((r for r in records if r['channel_id'] == channel), key=lambda r: (r['words'], r['source_id']))
        choices.append((row, 'Previously unrepresented reading context; shortest selected body, then canonical source ID'))
    ra = min((r for r in records if r['channel_id'] == 'ra-law-of-one' and r['source_id'] not in prior_read_ids),
             key=lambda r: r['selected_edition_id'])
    choices.append((ra, 'First not-previously-read Ra session by stable selected edition ID; documentary question/response control'))
    bashar = min((r for r in records if r['channel_id'] == 'bashar-official' and r['source_id'] not in prior_read_ids
                  and not re.search(r'\b(join|register|tickets?|buy)\b', r['title'], re.I)),
                 key=lambda r: (r['words'], r['source_id']))
    choices.append((bashar, 'Shortest not-previously-read official publication excluding explicit Join/Register/Ticket/Buy title cues'))
    if len(choices) != 19 or len({r['source_id'] for r, _ in choices}) != 19:
        raise ValueError('Expected nineteen prospective source windows')
    reused = []; dispositions = []
    for card in knowledge['cards']:
        matches = [r for r in records if card['source_id'] in set(r['legacy_source_ids']+[r['selected_edition_id']])]
        exact = len(matches) == 1 and all(s['body_sha256'] == matches[0]['body_sha256']
                                        and s['text_artifact_sha256'] == matches[0]['text_artifact']['sha256']
                                        for s in card['supports'])
        selected = card['card_id'] in REUSE
        if selected and not exact: raise ValueError('Chosen previous card does not bind the exact selected edition')
        dispositions.append({'legacy_card_id': card['card_id'], 'exact_edition_eligible': exact,
                             'selected': selected, 'reason': 'Fixed eight-card diversity subset; original full bank remains available'})
        if selected:
            reused.append({'legacy_card_id': card['card_id'], 'canonical_source_id': matches[0]['source_id'],
                           'body_sha256': matches[0]['body_sha256'],
                           'text_artifact_sha256': matches[0]['text_artifact']['sha256']})
    source = loader(); selected = []; evidence = []
    for i, (record, reason) in enumerate(choices, 1):
        text = source.body(record['text_artifact'], record['body_transform'])
        if sha(text.encode()) != record['body_sha256']: raise ValueError('Selected body changed')
        start, end, basis = window(text); span = text[start:end]
        item = {'reading_id': f'new-reading-{i:02d}', 'source_id': record['source_id'],
                'selected_edition_id': record['selected_edition_id'], 'channel_id': record['channel_id'],
                'channel_name': record['channel_name'], 'title': record['title'], 'source_url': record['source_url'],
                'document_kind': record['document_kind'], 'text_origin': record['text_origin'],
                'body_sha256': record['body_sha256'], 'text_artifact_sha256': record['text_artifact']['sha256'],
                'body_words': record['words'], 'start_character': start, 'end_character': end,
                'span_sha256': sha(span.encode()), 'words': len(span.split()),
                'selection_reason': reason, 'window_rule': basis,
                'question_punctuation_may_be_automatic_or_rhetorical': True}
        selected.append(item); evidence.append({**item, 'text': span})
    plan = {'schema_version': 1, 'status': 'frozen_before_new_rankings',
            'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'source_bindings': {'frame': binding(frame_path), 'previous_readings': binding(old_readings),
                                'previous_knowledge': binding(old_knowledge)},
            'selected_windows': selected, 'legacy_cards_selected': reused, 'legacy_reuse_dispositions': dispositions,
            'new_readings_planned': len(selected), 'maximum_cards': 27, 'public_analyst_word_budget': 4500,
            'rankings_inspected': False, 'evaluation_queries_authored_by_this_lane': False,
            'scope': 'Purposive bounded AI readings; prior exact-edition annotations stay distinct from new inspections. No entire-corpus manual-reading claim.',
            'producer_sha256': sha(Path(__file__).read_bytes())}
    output.mkdir(parents=True)
    (output/'selection.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
    (output/'windows-private.json').write_text(json.dumps({'selection_sha256': sha((output/'selection.json').read_bytes()),
                                                          'windows': evidence}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'readings': len(selected), 'selected_words': sum(x['words'] for x in selected),
                      'legacy_cards': len(reused), 'selection_sha256': sha((output/'selection.json').read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    select(parser.parse_args().output)
