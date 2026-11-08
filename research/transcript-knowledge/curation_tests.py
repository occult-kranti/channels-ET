#!/usr/bin/env python3
"""Exercise edition, provenance, privacy and denominator failures using a real release."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile

from curation_build import binding, check_support, read_bound, support
from verify_curated import FRAME, verify_data


def run(release, registry_path):
    data = json.loads((release/'curated.json').read_text())
    registry = json.loads(registry_path.read_text())
    profiles = {'bindings': {'frame_sha256': FRAME}, 'profiles': registry['documents']}
    passed = ['accepted_actual_release']
    verify_data(data, profiles, registry)

    def rejects(name, mutation):
        changed = deepcopy(data); mutation(changed)
        try:
            verify_data(changed, profiles, registry)
        except (ValueError, KeyError):
            passed.append(name)
        else:
            raise AssertionError('Invalid release accepted: ' + name)

    rejects('different_selected_edition', lambda x: x['cards'][0].update(selected_edition_id='changed-edition'))
    rejects('missing_answer', lambda x: x['cards'][0].update(paraphrase=''))
    rejects('missing_qualification', lambda x: x['cards'][0].update(qualifying_note=''))
    rejects('card_to_other_source_support', lambda x: x['cards'][0].update(supports=x['cards'][1]['supports']))
    rejects('invented_documentary_question', lambda x: x['questions'][0].update(question_type='documentary_printed_paraphrase'))
    rejects('external_question_forged_body_offset', lambda x: next(q for q in x['questions'] if q['question_id']=='q-lyssa138-qa-01')['documentary_binding'].update(start_character=0))
    rejects('human_accuracy_claim', lambda x: x['cards'][0]['annotation'].update(human_validated=True))
    rejects('raw_evidence_leak', lambda x: x['evidence'][0].update(text='retained source words'))
    rejects('private_path_leak', lambda x: x['context_notes'][0].update(summary='/workspace/private-transcript.txt'))
    rejects('duplicate_card_count', lambda x: x['cards'].append(deepcopy(x['cards'][0])))
    rejects('cross_context_evidence', lambda x: x['context_notes'][0].update(evidence_ids=x['context_notes'][1]['evidence_ids']))
    rejects('overclaimed_context_count', lambda x: x['context_notes'][0].update(unreviewed_source_units=999))
    rejects('doubled_reading_total', lambda x: x['coverage'].update(new_unique_words_read=22580))
    rejects('public_word_budget_drift', lambda x: x['coverage'].update(public_word_budget=4501))
    rejects('offset_exceeds_body', lambda x: x['evidence'][0].update(end_character=999999999))
    rejects('repeated_unmerged_interval', lambda x: x['reading_coverage'][0]['new_intervals'].extend([[1, 2], [1, 2]]))

    text = 'Alpha beta gamma.'
    record = {'source_id': 'synthetic', 'body_sha256': 'a'*64, 'text_artifact': {'sha256': 'b'*64}}
    item = support(record, text, 0, len(text))
    check_support(item, record, text)
    try:
        check_support(item, record, 'Alpha zeta gamma.')
    except ValueError:
        passed.append('same_length_exact_span_tampering')
    else:
        raise AssertionError('Same-length span tampering accepted')
    with tempfile.TemporaryDirectory(prefix='curation-test-', dir='/dev/shm') as work:
        path = Path(work)/'input.json'; path.write_text('{"a":1}')
        ref = binding(path); read_bound(ref); path.write_text('{"a":2}')
        try:
            read_bound(ref)
        except ValueError:
            passed.append('same_length_frozen_input_tampering')
        else:
            raise AssertionError('Same-length frozen input tampering accepted')
    return {'status': 'passed', 'checks': len(passed), 'cases': passed,
            'scope': 'Schema/provenance failure controls; semantic fidelity has an independent bounded source audit.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release', required=True, type=Path)
    p.add_argument('--registry', required=True, type=Path)
    a = p.parse_args(); print(json.dumps(run(a.release, a.registry)))
