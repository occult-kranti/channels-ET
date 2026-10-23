#!/usr/bin/env python3
"""Independent saved-output and source-pointer audit; no inference/network.

These are schema, provenance and arithmetic checks, not human annotation validity.
"""
import collections
import hashlib
import json
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODELS = ROOT / 'research/continuation/models'
QA = ROOT / 'research/expansion/qa'
checks = []
inputs = {}


def read(path):
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def ck(ok, label, actual=None, expected=None):
    checks.append({'check': label, 'passed': bool(ok), 'actual': actual, 'expected': expected})


def eq(actual, expected, label):
    ck(actual == expected, label, actual, expected)


def approx(actual, expected, label):
    ck(abs(actual - expected) < 1e-6, label, actual, expected)


themes = ['contact_forecast', 'personal_practice', 'cosmology', 'other', 'unclear']
conditionals = ['yes', 'no', 'unclear']


def parse(raw):
    # Decode from the first opening brace independently of the producer parser.
    try:
        obj, end = json.JSONDecoder().raw_decode(raw[raw.index('{'):])
        if not isinstance(obj, dict) or obj.get('theme') not in themes:
            return None
        if obj.get('conditional') not in conditionals or not isinstance(obj.get('evidence'), str):
            return None
        return obj
    except (ValueError, TypeError):
        return None


source = read(QA / 'qa-candidates.json')['records']
byid = {r['id']: r for r in source}
groups = read(MODELS / 'split.json')['videoGroupMap']
original = read(MODELS / 'content-label-predictions.json')['records']
original_result = read(MODELS / 'content-label-results.json')
original_protocol = read(MODELS / 'content-label-protocol.json')
reverse = read(MODELS / 'option-order-predictions.json')['records']
reverse_result = read(MODELS / 'option-order-results.json')
reverse_protocol = read(MODELS / 'option-order-protocol.json')
lexical = read(MODELS / 'conditional-lexicon-sensitivity.json')


def audit_rows(rows, raw_key, parsed_key, span_key, prefix):
    parsed_rows = []
    for row in rows:
        parsed = parse(row[raw_key])
        eq(parsed, row[parsed_key], prefix + ' independently decoded JSON ' + row['id'])
        src = byid[row['id']]
        for key in ['videoId', 'question', 'answerGist', 'sourceUrl', 'sourceSha256', 'sourcePointer']:
            eq(row[key], src[key], prefix + ' source field ' + key + ' ' + row['id'])
        eq(row['sourceGroupId'], groups[src['videoId']], prefix + ' source proxy ' + row['id'])
        eq(row['humanReviewed'], False, prefix + ' no human label ' + row['id'])
        valid_span = bool(parsed and parsed['evidence'] and parsed['evidence'] in src['answerGist']
                          and len(parsed['evidence'].split()) <= 8)
        eq(row[span_key], valid_span, prefix + ' answer-exact short span ' + row['id'])
        ck(0 < row['generatedTokens'] <= 96, prefix + ' token cap ' + row['id'])
        if parsed:
            parsed_rows.append((row, parsed, valid_span))
    return parsed_rows


op = audit_rows(original, 'rawModelOutput', 'parsed', 'evidenceSpanExactAndShort', 'original')
rp = audit_rows(reverse, 'reversedRawOutput', 'reversedParsed', 'reversedEvidenceSpanExactAndShort', 'reversed')
eq(len(original), 12, 'original twelve examples')
eq(len({r['sourceGroupId'] for r in original}), 12, 'twelve distinct source proxies')
eq(collections.Counter(r['dictionaryConditional'] for r in original), {'yes': 6, 'no': 6}, 'purposive six/six indicator sample')
eq([r['id'] for r in original], original_protocol['selectedIds'], 'original selection order')
eq([r['id'] for r in reverse], [r['id'] for r in original], 'same reverse-order source examples')
eq(reverse_protocol['selectedIds'], [r['id'] for r in original], 'reverse protocol selection')
eq(reverse_protocol['originalPredictionsSha256'], inputs['research/continuation/models/content-label-predictions.json'], 'original outputs hash bound before sensitivity')
eq(reverse_protocol['reversedThemeOrder'], list(reversed(themes)), 'theme order exactly reversed')
old_order = 'contact_forecast, personal_practice, cosmology, other, or unclear'
new_order = 'unclear, other, cosmology, personal_practice, or contact_forecast'
eq(reverse_protocol['originalSystemPrompt'].replace(old_order, new_order), reverse_protocol['reversedSystemPrompt'], 'only theme-order prompt text changes')
eq(original_result['parsedRecords'], len(op), 'original parsed denominator')
eq(original_result['themeCounts'], dict(collections.Counter(p['theme'] for r, p, v in op)), 'original theme counts')
eq(original_result['conditionalMethodAgreementCount'], sum(p['conditional'] == r['dictionaryConditional'] for r, p, v in op), 'original dictionary concordance not accuracy')
eq(original_result['sourceSpanExactAndShortCount'], sum(v for r, p, v in op), 'original source-span validity count')
eq(reverse_result['reversedParsedRecords'], len(rp), 'reverse parsed denominator')
eq(reverse_result['reversedThemeCounts'], dict(collections.Counter(p['theme'] for r, p, v in rp)), 'reverse theme counts')
joint = [r for r in reverse if r['originalParsed'] is not None and r['reversedParsed'] is not None]
eq(reverse_result['pairedParsedRecords'], len(joint), 'joint parse denominator retains failures separately')
eq(reverse_result['pairedThemeChangedCount'], sum(r['originalParsed']['theme'] != r['reversedParsed']['theme'] for r in joint), 'paired theme changes')
eq(reverse_result['reversedFirstOptionCount'], sum(p['theme'] == themes[-1] for r, p, v in rp), 'reverse-first option copies')
eq(reverse_result['reversedEvidenceSpanValidCount'], sum(v for r, p, v in rp), 'reverse valid spans')
approx(reverse_result['meanSeconds'], statistics.mean(r['seconds'] for r in reverse), 'reverse saved-output latency mean')
for row, old in zip(reverse, original):
    eq(row['originalParsed'], old['parsed'], 'original labels preserved ' + row['id'])

# Recompute both indicator patterns from the actual released answer gists.
old_re = re.compile(lexical['originalRegex'], re.I)
new_re = re.compile(lexical['stricterRegex'], re.I)
changed = []
for row in source:
    a = bool(old_re.search(row['answerGist']))
    b = bool(new_re.search(row['answerGist']))
    eq(a, 'conditional' in row['answerModalityMarkers'], 'original codebook presence ' + row['id'])
    if a != b:
        changed.append(row['id'])
eq(lexical['n'], len(source), 'sensitivity corpus denominator')
eq(lexical['originalConditionalCount'], sum(bool(old_re.search(r['answerGist'])) for r in source), 'old conditional count')
eq(lexical['stricterConditionalCount'], sum(bool(new_re.search(r['answerGist'])) for r in source), 'narrower conditional count')
eq(lexical['changedCount'], len(changed), 'changed indicator count')
eq([r['id'] for r in lexical['changedRecords']], changed, 'changed IDs exact')
eq(lexical['sourceQaSha256'], inputs['research/expansion/qa/qa-candidates.json'], 'sensitivity input digest')

# Retained interpretation artifacts must resolve to actual digest fields.
single = read(QA / 'close-reading.json')
paired = read(QA / 'pair-close-reading.json')
eq(len(single['records']), 20, 'retained twenty single readings')
eq(len(paired['records']), 12, 'retained twelve paired readings')
eq(single['humanReview'], False, 'single readings not human validation')
eq(paired['humanReview'], False, 'paired readings not human validation')
source_ids = [r['candidateId'] for r in single['records']]
source_ids.extend(r['id'] for r in original)
for pair in paired['records']:
    eq(pair['classification']['answerAgreement'], 'undetermined', 'paired agreement remains unvalidated ' + pair['leftId'])
    for side in ['left', 'right']:
        row = byid[pair[side + 'Id']]
        expected = {k: row[k] for k in ['sourceUrl', 'sourcePath', 'sourceSha256', 'sourcePointer']}
        eq(pair[side + 'Source'], expected, 'paired source locator ' + row['id'])
        source_ids.append(row['id'])
for ident in source_ids:
    row = byid[ident]
    path = ROOT / row['sourcePath']
    digest = read(path)
    eq(inputs[row['sourcePath']], row['sourceSha256'], 'retained digest hash ' + ident)
    value = digest
    for key in row['sourcePointer'].strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    eq(value['question'], row['question'], 'digest pointer question ' + ident)
    eq(value['answer_gist'], row['answerGist'], 'digest pointer answer gist ' + ident)

# A newer-family same-item run is audited if present; absence is explicitly pending.
newer_path = MODELS / 'qwen35-content-label-predictions.json'
newer = {'status': 'NOT_YET_PRESENT'}
if newer_path.is_file():
    npred = read(newer_path)['records']
    nresult = read(MODELS / 'qwen35-content-label-results.json')
    nprotocol = read(MODELS / 'qwen35-content-label-protocol.json')
    nvalid = audit_rows(npred, 'rawModelOutput', 'parsed', 'evidenceSpanExactAndShort', 'newer')
    eq([r['id'] for r in npred], [r['id'] for r in original], 'newer same twelve source examples')
    eq(nprotocol['systemPrompt'], reverse_protocol['originalSystemPrompt'], 'newer original label/schema prompt')
    eq(nresult['parsedRecords'], len(nvalid), 'newer parsed count')
    eq(nresult['themeCounts'], dict(collections.Counter(p['theme'] for r, p, v in nvalid)), 'newer theme counts')
    eq(nresult['sourceSpanExactAndShortCount'], sum(v for r, p, v in nvalid), 'newer valid answer spans')
    eq(nresult['conditionalMethodAgreementCount'], sum(p['conditional'] == r['dictionaryConditional'] for r, p, v in nvalid), 'newer dictionary concordance count')
    eq(nresult['conditionalLabelCounts'], dict(collections.Counter(p['conditional'] for r, p, v in nvalid)), 'newer conditional label collapse')
    eq(nresult['primaryThemeDictionaryConcordanceCount'], sum(p['theme'] in r['dictionaryThemeIndicators'] for r, p, v in nvalid), 'newer primary-theme dictionary concordance')
    eq(nresult['generationCapHits'], sum(r['generatedTokens'] == 96 for r in npred), 'newer generation cap hits')
    approx(nresult['meanSeconds'], statistics.mean(r['seconds'] for r in npred), 'newer saved-output latency mean')
    approx(nresult['conditionalMethodAgreementRate'], sum(p['conditional'] == r['dictionaryConditional'] for r, p, v in nvalid) / len(nvalid), 'newer dictionary concordance rate')
    eq(nprotocol['originalPredictionsSha256'], inputs['research/continuation/models/content-label-predictions.json'], 'newer task bound to unchanged baseline records')
    eq(nprotocol['imageOrVideoInputUsed'], False, 'current-family experiment text-only')
    eq(nprotocol['humanGroundTruth'], False, 'current-family no human ground truth')
    eq(nprotocol['sourceTruthValidation'], False, 'current-family no source truth validation')
    newer = {'status': 'AUDITED', 'n': len(npred), 'parsed': len(nvalid),
             'valid_answer_spans': sum(v for r, p, v in nvalid),
             'literal_answer_spans': sum(bool(p['evidence']) and p['evidence'] in r['answerGist'] for r, p, v in nvalid),
             'literal_but_overlength_spans': sum(bool(p['evidence']) and p['evidence'] in r['answerGist'] and len(p['evidence'].split()) > 8 for r, p, v in nvalid),
             'conditional_dictionary_concordance': sum(p['conditional'] == r['dictionaryConditional'] for r, p, v in nvalid),
             'theme_counts': dict(collections.Counter(p['theme'] for r, p, v in nvalid))}
    comparison = read(MODELS / 'annotation-comparison.json')
    eq(comparison['sameSourceIds'], [r['id'] for r in original], 'three-condition source IDs identical')
    for binding in comparison['sourceBindings']:
        path = MODELS / binding['file']
        eq(binding['sha256'], hashlib.sha256(path.read_bytes()).hexdigest(), 'comparison raw-output binding ' + binding['file'])
    sets = {'qwen25_original': op, 'qwen25_reversed': rp, 'qwen35_original': nvalid}
    for condition in comparison['conditions']:
        rows = sets[condition['id']]
        exact = sum(bool(p['evidence']) and p['evidence'] in r['answerGist'] for r, p, v in rows)
        short = sum(len(p['evidence'].split()) <= 8 for r, p, v in rows)
        yes = sum(p['conditional'] == 'yes' for r, p, v in rows)
        agree = sum(p['conditional'] == r.get('dictionaryConditional', r.get('originalDictionaryConditional')) for r, p, v in rows)
        always_yes = sum(r.get('dictionaryConditional', r.get('originalDictionaryConditional')) == 'yes' for r, p, v in rows)
        metrics = {'n': 12, 'parsedRecords': len(rows), 'parseFailures': 12 - len(rows),
                   'sourceSpanExactCount': exact, 'sourceSpanAtMostEightWordsCount': short,
                   'sourceSpanExactAndShortCount': sum(v for r, p, v in rows),
                   'sourceSpanExactButOverLengthCount': exact - sum(v for r, p, v in rows),
                   'sourceSpanNonexactCount': len(rows) - exact, 'conditionalYesCount': yes,
                   'conditionalMethodAgreementCount': agree, 'conditionalParsedDenominator': len(rows),
                   'conditionalAlwaysYesBaselineAgreementCount': always_yes,
                   'allParsedConditionalLabelsYes': yes == len(rows)}
        for key, value in metrics.items():
            eq(condition[key], value, 'three-condition ' + condition['id'] + ' ' + key)
        approx(condition['conditionalMethodAgreementRate'], agree / len(rows), 'three-condition concordance rate ' + condition['id'])
        approx(condition['conditionalAlwaysYesBaselineRate'], always_yes / len(rows), 'three-condition always-yes baseline rate ' + condition['id'])

fail = [c for c in checks if not c['passed']]
report = {'round': 12, 'status': 'FAIL' if fail else 'PASS', 'checks': len(checks), 'failures': fail,
          'network_or_inference_runs': 0, 'inputs_sha256': inputs,
          'decisive': {'original_parsed': len(op), 'reverse_parsed': len(rp), 'joint_parsed': len(joint),
                       'paired_theme_changes': sum(r['originalParsed']['theme'] != r['reversedParsed']['theme'] for r in joint),
                       'reverse_first_option_count': sum(p['theme'] == themes[-1] for r, p, v in rp),
                       'reverse_theme_counts': dict(collections.Counter(p['theme'] for r, p, v in rp)),
                       'original_valid_spans': sum(v for r, p, v in op), 'reverse_valid_spans': sum(v for r, p, v in rp),
                       'old_conditional_count': lexical['originalConditionalCount'], 'narrower_conditional_count': lexical['stricterConditionalCount'],
                       'changed_indicator_ids': changed, 'retained_single_readings': 20, 'retained_pair_readings': 12,
                       'newer_family': newer},
          'limits': ['Saved-output checks do not independently rerun inference.',
                     'Order changes establish local prompt sensitivity; zero reverse-first copies disconfirm only the simple first-option-copying account.',
                     'No human ground truth: dictionary concordance is not accuracy; exact answer spans are grounding/format checks only.',
                     'Different model tokenizers/templates and runtimes prevent a controlled model-size/family causal comparison.',
                     'Retained readings are AI interpretations of AI-generated gists; no transcript/audio/video inspection or speaker validation.'],
          'all_checks': checks}
(HERE / 'independent-label-probes.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checks', 'failures', 'decisive']}, indent=2))
raise SystemExit(bool(fail))
