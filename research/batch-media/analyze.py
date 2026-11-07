#!/usr/bin/env python3
"""Private, receipt-bound descriptive analysis of actual batch ASR outputs.

No acquisition, model inference, speaker assignment or outcome validation occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import shutil
import warnings
from urllib.parse import urlsplit, urlunsplit

SCHEMA = 1
MAX_DOCUMENTS = 2000
MAX_JSON_BYTES = 64 * 1024**2
MAX_FEATURES = 10000
MAX_CORPUS_CHARACTERS = 20_000_000
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:_.-]{0,159}$')
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
HASH = re.compile(r'^[0-9a-f]{64}$')
PROVIDERS = {'youtube', 'publisher_video', 'publisher_rss'}
KEYWORDS = {
    'freedom': ['free', 'freedom', 'liberty', 'sovereign', 'sovereignty'],
    'enlightenment': ['enlightened', 'enlightenment', 'awakening', 'awakened', 'realization'],
    'energy': ['energy', 'energies', 'energetic', 'frequency', 'frequencies', 'vibration', 'vibrations'],
    'fear': ['fear', 'fears', 'afraid', 'anxiety', 'anxious', 'worry', 'worried'],
    'choice': ['choice', 'choices', 'choose', 'choosing', 'decision', 'decisions', 'allow', 'allowing'],
    'consciousness': ['consciousness', 'conscious', 'awareness', 'aware', 'mind', 'minds'],
    'relationships': ['relationship', 'relationships', 'love', 'loved', 'loving', 'family', 'families', 'friend', 'friends'],
    'body': ['body', 'bodies', 'physical', 'health', 'healing', 'disease', 'illness', 'breath', 'breathing'],
    'religion': ['religion', 'religions', 'religious', 'god', 'gods', 'church', 'churches', 'prayer', 'prayers'],
    'metaphysics': ['soul', 'souls', 'spirit', 'spirits', 'angel', 'angels', 'dimension', 'dimensions', 'reincarnation'],
}
# Fixed named vocabulary; spelling variants are not silently corrected into these.
NAME_MASK = ['adamus', 'shaumbra', 'geoffrey', 'hoppe', 'linda', 'saint', 'germain', 'crimson', 'circle']
LIMITATIONS = [
    'These are unverified ASR versions of downloaded recordings, not human reference transcripts.',
    'Presenter, facilitator and audience speech may mix. No diarization assigns any turn to a person or claimed entity.',
    'One creator or one course series is one dependent source context, not independent cross-medium corroboration.',
    'ASR errors, names, language, recurring introductions, editing and recording length affect word counts and similarities.',
    'A keyword match records a word form, including negated, quoted, hypothetical and rhetorical uses; it is not a belief or topic label.',
    'TF-IDF cosine measures word use, not agreement, semantic equivalence, truth, prediction accuracy or extraterrestrial origin.',
    'NMF components, where fitted, are exploratory lexical patterns in this selected sample; no validated topics or optimal topic count are claimed.',
    'Publisher text and ASR of the same performance are alternative versions of one source and are not pooled as independent documents.',
    'Quiet-window fractions and ASR VAD durations do not measure speaking time, emotion or spiritual states.',
    'Reported timestamp repairs are disclosed per recording; clipping an endpoint does not validate the terminal words or their audio alignment.',
]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def encoded(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def object_hash(obj):
    return hashlib.sha256(encoded(obj).encode()).hexdigest()


def private_path(value, *, exists=True):
    if not isinstance(value, (str, Path)) or not str(value) or '\0' in str(value):
        raise ValueError('A local private path is required')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Private paths must be absolute and cannot traverse parents')
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Symlink routes are not admitted')
        marker = parent / '.git'
        if marker.exists() and not (marker.is_dir() and not any(marker.iterdir())):
            raise ValueError('Raw text and private analysis must stay outside Git checkouts')
    if exists and not path.is_file():
        raise ValueError('Expected retained file is missing')
    return path


def read_json(path, *, bound=MAX_JSON_BYTES):
    path = private_path(path)
    if path.stat().st_size > bound:
        raise ValueError('JSON input exceeds declared byte bound')
    return json.loads(path.read_text(encoding='utf-8'))


def finite_number(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' must be a finite number')
    if value < 0 or (positive and value <= 0):
        raise ValueError(label + ' is outside its supported range')
    return value


def verify_file(artifact, *, source_id=None, cache=None):
    if not isinstance(artifact, dict) or artifact.get('status') != 'verified':
        raise ValueError('An actual verified artifact receipt is required')
    path = private_path(artifact.get('local_path'))
    if source_id is not None and artifact.get('source_id') != source_id:
        raise ValueError('Artifact source identity differs from receipt')
    size, expected = artifact.get('bytes'), artifact.get('sha256')
    if isinstance(size, bool) or not isinstance(size, int) or size < 1 or not isinstance(expected, str) or not HASH.fullmatch(expected):
        raise ValueError('Artifact byte/hash binding is invalid')
    stat = path.stat()
    if stat.st_size != size:
        raise ValueError('Artifact byte count changed')
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
    actual = cache.get(key) if cache is not None else None
    if actual is None:
        actual = sha256(path)
        if cache is not None:
            cache[key] = actual
    if actual != expected:
        raise ValueError('Artifact hash changed')
    return path


def tokens(text):
    return [word.casefold().replace('’', "'") for word in TOKEN.findall(text)]


def safe_source_url(value):
    parts = urlsplit(str(value or ''))
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        return None
    # Source-page identity only; signed/tracking query strings are never projected.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def english_eligibility(source, asr):
    declared = source.get('source_language', 'unknown')
    reported = asr.get('language_reported')
    plan = asr.get('language_plan') or {}
    def base(value):
        return value.lower().split('-')[0] if isinstance(value, str) else None
    declaration_state = source.get('source_language_status')
    if declaration_state in {'invalid', 'conflicting'}:
        return False, 'invalid_or_conflicting_source_language'
    known = base(declared) not in {None, '', 'unknown', 'und'}
    if known and base(declared) != 'en':
        return False, 'declared_non_english_source'
    if base(reported) != 'en':
        return False, 'ASR_did_not_report_English'
    if known:
        return True, 'metadata_declared_English_not_human_verified'
    if plan.get('automatic_language_detection') is True:
        return True, 'model_detected_English_not_human_verified'
    return True, 'English_assumption_with_unknown_source_language_not_human_verified'


def timing_quality(asr):
    fields = ('timestamp_policy', 'timestamp_anomaly_count', 'timestamp_repaired_segment_count',
              'timestamp_maximum_adjustment_seconds', 'text_changed_by_repair', 'terminal_text_alignment_unverified',
              'asr_execution_script_sha256', 'timestamp_repair_script_sha256', 'timestamp_repair_helper_sha256')
    values = {key: asr.get(key) for key in fields}
    for key in ('timestamp_anomaly_count', 'timestamp_repaired_segment_count'):
        value = values[key]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError('Timing diagnostic counts must be nonnegative integers')
    value = values['timestamp_maximum_adjustment_seconds']
    if value is not None:
        finite_number(value, 'Timing maximum adjustment')
    for key in ('text_changed_by_repair', 'terminal_text_alignment_unverified'):
        if values[key] is not None and not isinstance(values[key], bool):
            raise ValueError('Timing diagnostic flags must be boolean or unreported')
    policy = values['timestamp_policy']
    if policy is not None and (not isinstance(policy, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,160}', policy)):
        raise ValueError('Timing policy must be a bounded identifier')
    for key in ('asr_execution_script_sha256', 'timestamp_repair_script_sha256', 'timestamp_repair_helper_sha256'):
        if values[key] is not None and (not isinstance(values[key], str) or not HASH.fullmatch(values[key])):
            raise ValueError('Timing source code binding must be a SHA-256 digest')
    values.update(status='reported_by_processing_receipt' if any(value is not None for value in values.values()) else 'not_reported_by_original_processing_script',
                  scope='Receipt-reported processing diagnostic; a clipped endpoint does not verify terminal words or audio alignment.')
    return values


def load_documents(run_paths, *, allow_test_fixtures=False):
    documents, excluded, aliases, audit, seen, media_seen, cache = [], [], [], [], {}, {}, {}
    input_rows = 0
    corpus_characters = 0
    for supplied in run_paths:
        run_path = private_path(supplied)
        run_bytes = run_path.read_bytes()
        if len(run_bytes) > 4 * 1024**2:
            raise ValueError('Run manifest exceeds 4 MiB')
        run = json.loads(run_bytes)
        if not isinstance(run, dict) or run.get('schema_version') != SCHEMA or not isinstance(run.get('records'), list):
            raise ValueError('Expected a versioned audio-run records manifest')
        audit.append({'run_path': str(run_path), 'sha256': hashlib.sha256(run_bytes).hexdigest(), 'batch_id': run.get('batch_id')})
        input_rows += len(run['records'])
        if input_rows > MAX_DOCUMENTS:
            raise ValueError('At most 2,000 input records are supported per analysis')
        for row in run['records']:
            if not isinstance(row, dict):
                raise ValueError('Run record must be an object')
            sid = row.get('source_id')
            if not isinstance(sid, str) or not IDENTIFIER.fullmatch(sid):
                raise ValueError('Run source identity is missing or unbounded')
            if row.get('status') != 'completed':
                excluded.append({'source_id': sid, 'reason': 'not_completed_ASR', 'status': row.get('status')})
                continue
            receipt_path = private_path(row.get('receipt_path'))
            if sha256(receipt_path) != row.get('receipt_sha256'):
                raise ValueError('Audio receipt hash changed')
            receipt = read_json(receipt_path, bound=2 * 1024**2)
            if receipt.get('kind') != 'source-bound-audio-analysis' or receipt.get('status') != 'completed' or receipt.get('source_id') != sid:
                raise ValueError('Completed source-bound audio receipt identity/status differs')
            binding = receipt.get('binding')
            if not isinstance(binding, dict) or object_hash(binding) != receipt.get('binding_sha256'):
                raise ValueError('Audio processing binding changed')
            source = binding.get('source')
            if not isinstance(source, dict) or source.get('source_id') != sid:
                raise ValueError('Bound source identity differs')
            if source.get('fixture_only') is True and not allow_test_fixtures:
                raise ValueError('Synthetic fixtures are not actual source recordings')
            provider = source.get('provider')
            if provider not in PROVIDERS or receipt.get('provider') != provider or row.get('provider') != provider:
                raise ValueError('Source provider differs across processing chain')
            proof_ref = source.get('verification_receipt') or {}
            proof_path = private_path(proof_ref.get('path'))
            if sha256(proof_path) != proof_ref.get('sha256'):
                raise ValueError('Original acquisition proof hash changed')
            proof = read_json(proof_path, bound=4 * 1024**2)
            source_entries = [a for a in proof.get('verified_artifacts', []) if a.get('source_id') == sid and a.get('local_path') == source.get('local_path') and a.get('sha256') == source.get('sha256')]
            if len(source_entries) != 1 or source_entries[0].get('bytes') != source.get('bytes') or source_entries[0].get('kind') != source.get('kind'):
                raise ValueError('Original acquisition proof does not bind one exact source')
            fixture_known = any(obj.get('fixture_only') is True for obj in (run, row, receipt, source, proof, source_entries[0]))
            if fixture_known and not allow_test_fixtures:
                raise ValueError('Synthetic acquisition/provenance fixtures are not actual source recordings')
            for field in ('provider', 'medium_id', 'channel_id', 'source_language', 'source_language_status', 'context_associations'):
                if field in source_entries[0] and source.get(field) != source_entries[0][field]:
                    raise ValueError('Original source proof metadata differs or was erased')
            verify_file(source_entries[0], source_id=sid, cache=cache)
            artifacts = receipt.get('verified_artifacts')
            if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 20:
                raise ValueError('Completed receipt artifacts are missing or unbounded')
            for artifact in artifacts:
                path = verify_file(artifact, source_id=sid, cache=cache)
                if str(path) != source.get('local_path') and not path.is_relative_to(receipt_path.parent):
                    raise ValueError('Derived artifact leaves its processing output directory')
            metric_refs = [a for a in artifacts if a.get('kind') == 'analysis' and Path(a['local_path']).name == 'audio-metrics.json']
            if len(metric_refs) > 1 or (metric_refs and read_json(metric_refs[0]['local_path']) != receipt.get('audio_metrics')):
                raise ValueError('Audio metric summary differs from retained metric artifact')
            originals = [a for a in artifacts if a.get('local_path') == source.get('local_path') and a.get('sha256') == source.get('sha256') and a.get('bytes') == source.get('bytes')]
            if len(originals) != 1:
                raise ValueError('Completed ASR receipt does not retain its exact original source')
            candidates = [a for a in artifacts if a.get('kind') == 'transcript' and Path(a['local_path']).name == 'segments.json']
            if len(candidates) != 1:
                raise ValueError('Exactly one completed machine segment document is required')
            segment_ref = candidates[0]
            segment_doc = read_json(segment_ref['local_path'])
            transcript_label = segment_doc.get('transcript_source')
            repair_asr = receipt.get('asr') or {}
            repaired_machine = (transcript_label == 'machine ASR; unverified; final segment endpoint clipped to recording boundary'
                                and repair_asr.get('timestamp_policy') == 'terminal_end_clipped_to_decoded_duration'
                                and repair_asr.get('timestamp_repaired_segment_count') == 1
                                and repair_asr.get('text_changed_by_repair') is False
                                and repair_asr.get('terminal_text_alignment_unverified') is True
                                and (binding.get('postprocessing') or {}).get('method') == 'explicit_terminal_end_clip_v1'
                                and all(repair_asr.get(k) for k in ('asr_execution_script_sha256', 'timestamp_repair_script_sha256', 'timestamp_repair_helper_sha256')))
            if segment_doc.get('source_id') != sid or not (transcript_label == 'machine ASR; unverified' or repaired_machine):
                raise ValueError('Segment source/type differs; publisher references are not ASR documents')
            segments = segment_doc.get('segments')
            if not isinstance(segments, list) or len(segments) > 200000 or not isinstance(segment_doc.get('text'), str):
                raise ValueError('Segment document is invalid or unbounded')
            duration = finite_number(receipt.get('decoded_duration_seconds'), 'Decoded duration', positive=True)
            texts, previous_start = [], -1.0
            for segment in segments:
                if not isinstance(segment, dict) or not isinstance(segment.get('text'), str):
                    raise ValueError('ASR segment text is invalid')
                start = finite_number(segment.get('start_seconds'), 'Segment start')
                end = finite_number(segment.get('end_seconds'), 'Segment end')
                if start < previous_start or end < start or end > duration + 2:
                    raise ValueError('ASR segment timing is inconsistent')
                previous_start = start
                texts.append(segment['text'])
            text = '\n'.join(texts)
            if text != segment_doc['text']:
                raise ValueError('Segment text is not identical to the retained plain text')
            asr = receipt.get('asr')
            if not isinstance(asr, dict) or asr.get('segments') != len(segments) or asr.get('whitespace_word_count') != len(text.split()) or not binding.get('asr', {}).get('requested'):
                raise ValueError('ASR completion counts/configuration differ from retained text')
            postprocessing = binding.get('postprocessing') or {}
            for name, expected in (('asr_execution_script_sha256', binding.get('script_sha256')),
                                   ('timestamp_repair_script_sha256', postprocessing.get('script_sha256')),
                                   ('timestamp_repair_helper_sha256', postprocessing.get('helper_sha256'))):
                if asr.get(name) is not None and (asr[name] != expected or not any(a.get('sha256') == expected for a in artifacts)):
                    raise ValueError('Reported timing/execution code is not bound to its retained artifact')
            fingerprint = (source['sha256'], segment_ref['sha256'])
            if sid in seen:
                if seen[sid] != fingerprint:
                    raise ValueError('Same source ID has conflicting media/transcript versions; choose one explicitly')
                aliases.append({'source_id': sid, 'reason': 'duplicate_source_record', 'retained_as': sid})
                continue
            seen[sid] = fingerprint
            if source['sha256'] in media_seen:
                aliases.append({'source_id': sid, 'reason': 'exact_source_media_bytes_already_included', 'retained_as': media_seen[source['sha256']]})
                continue
            media_seen[source['sha256']] = sid
            corpus_characters += len(text)
            if corpus_characters > MAX_CORPUS_CHARACTERS:
                raise ValueError('Private corpus exceeds 20 million characters; split the declared batch')
            eligible, language_reason = english_eligibility(source, asr)
            doc_tokens = tokens(text)
            if not text.strip() or len(doc_tokens) < 30:
                excluded.append({'source_id': sid, 'reason': 'fewer_than_30_regex_tokens_in_completed_ASR'})
                continue
            metrics = receipt.get('audio_metrics') or {}
            summary = {'source_id': sid, 'provider': provider, 'medium_id': source.get('medium_id'), 'channel_id': source.get('channel_id'),
                       'title': source.get('title') or sid, 'published_date': source.get('published_date'), 'source_url': safe_source_url(source.get('source_url')),
                       'source_sha256': source['sha256'], 'source_bytes': source['bytes'], 'audio_receipt_sha256': row['receipt_sha256'],
                       'processing_binding_sha256': receipt['binding_sha256'], 'transcript_sha256': segment_ref['sha256'],
                       'transcript_source': transcript_label,
                       'transcript_text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                       'executed_audio_script_sha256': binding.get('script_sha256'), 'asr_model_files_sha256': (binding.get('asr', {}).get('model') or {}).get('files_sha256'),
                       'decoded_duration_seconds': duration, 'source_duration_seconds': source.get('duration_seconds'),
                       'whitespace_word_count': len(text.split()), 'regex_token_count': len(doc_tokens), 'segment_count': len(segments),
                       'source_language': source.get('source_language', 'unknown'), 'source_language_status': source.get('source_language_status'), 'asr_language': asr.get('language_reported'),
                       'asr_timing_quality': timing_quality(asr),
                       'english_lexical_eligible': eligible, 'english_eligibility_basis': language_reason,
                       'quiet_sample_fraction': metrics.get('quiet_sample_fraction'), 'rms_dbfs': metrics.get('rms_dbfs'),
                       'near_full_scale_sample_fraction': metrics.get('near_full_scale_sample_fraction'),
                       'vad_duration_seconds': asr.get('duration_after_vad_seconds'), 'speaker_scope': source.get('speaker_scope') or 'Unknown; no diarization',
                       'context_associations': source.get('context_associations', []), 'attribution_status': source.get('attribution_status', 'unverified'),
                       'claimed_entity_label': source.get('claimed_entity_label'), 'human_transcript_validation': False, 'fixture_only': fixture_known}
            documents.append({'summary': summary, 'text': text, 'tokens': doc_tokens, 'segments': segments})
    return documents, excluded, aliases, audit


def keyword_counts(doc):
    if not doc['summary']['english_lexical_eligible']:
        return None
    counts = Counter(doc['tokens'])
    denominator = len(doc['tokens'])
    return {group: {'mentions': sum(counts[word] for word in vocabulary),
                    'per_1000_regex_tokens': sum(counts[word] for word in vocabulary) * 1000 / denominator}
            for group, vocabulary in KEYWORDS.items()}


def question_candidates(doc):
    result = []
    segments = doc['segments']
    for i, segment in enumerate(segments):
        if '?' not in segment['text'] and '？' not in segment['text']:
            continue
        following = segments[i + 1] if i + 1 < len(segments) else None
        result.append({'source_id': doc['summary']['source_id'], 'segment_index': i, 'start_seconds': segment['start_seconds'],
                       'end_seconds': segment['end_seconds'], 'candidate_text': segment['text'],
                       'following_segment_context': following, 'kind': 'ASR_punctuation_question_candidate',
                       'question_type': 'unclassified_rhetorical_or_dialogue', 'speaker': 'unassigned',
                       'following_context_is_verified_answer': False, 'human_checked': False})
    return result


def mask_names(text):
    # Preserve every other character: this sensitivity changes only named forms,
    # rather than also normalizing punctuation, accents or apostrophes.
    return TOKEN.sub(lambda match: '' if match.group().casefold() in NAME_MASK else match.group(), text)


def fit_lexical(documents, *, mask=False):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import NMF
    from sklearn.exceptions import ConvergenceWarning
    selected = [d for d in documents if d['summary']['english_lexical_eligible']]
    ids = [d['summary']['source_id'] for d in selected]
    result = {'status': 'insufficient_English_documents', 'source_ids': ids, 'documents': len(ids), 'name_mask_applied': mask,
              'top_terms': {}, 'cosine_matrix': None, 'nmf': {'status': 'not_fitted', 'reason': 'requires_at_least_four_distinct_English_documents'}}
    if len(selected) < 2:
        return result
    texts = [mask_names(d['text']) if mask else d['text'] for d in selected]
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True, min_df=1,
                                 max_features=MAX_FEATURES, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']+\b")
    try:
        matrix = vectorizer.fit_transform(texts)
        matrix.sort_indices()
    except ValueError:
        result['status'] = 'empty_or_invalid_vocabulary'
        return result
    names = vectorizer.get_feature_names_out()
    similarities = np.clip(cosine_similarity(matrix), 0.0, 1.0)
    result.update(status='descriptive_fit_complete', vocabulary_features=len(names), cosine_matrix=similarities.tolist())
    for i, sid in enumerate(ids):
        row = matrix.getrow(i)
        order = np.argsort(row.data)[::-1][:15]
        result['top_terms'][sid] = [{'term': str(names[row.indices[j]]), 'weight': float(row.data[j])} for j in order]
    unique_rows = {hashlib.sha256(row.indices.tobytes() + row.data.tobytes()).hexdigest() for row in (matrix.getrow(i) for i in range(matrix.shape[0]))}
    k = min(3, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if len(selected) >= 4 and len(unique_rows) >= 4 and k >= 2:
        model = NMF(n_components=k, init='nndsvda', random_state=42, max_iter=1000)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            weights = model.fit_transform(matrix)
        result['nmf'] = {'status': 'exploratory_fit_complete', 'components': k, 'random_state': 42,
                         'iterations': model.n_iter_, 'max_iter': 1000, 'convergence_warning': any(isinstance(w.message, ConvergenceWarning) for w in caught),
                         'reconstruction_error': float(model.reconstruction_err_), 'scope': 'Components describe lexical variation; no optimal topic count, validated topic labels or independent creator sample is established.',
                         'component_terms': [[str(names[j]) for j in np.argsort(component)[::-1][:12]] for component in model.components_],
                         'document_weights': [{'source_id': sid, 'weights': [float(v) for v in row]} for sid, row in zip(ids, weights)]}
    return result


def negation_control():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    texts = ['aliens exist', 'aliens do not exist']
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True,
                                 token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']+\b")
    matrix = vectorizer.fit_transform(texts)
    return {'synthetic_control_not_corpus_data': True, 'texts': texts, 'cosine_similarity': min(1.0, max(0.0, float(cosine_similarity(matrix)[0, 1]))),
            'features': list(vectorizer.get_feature_names_out()), 'interpretation': 'Opposite statements collapse after this lexical preprocessing; a high corpus cosine is not agreement.'}


def csv_file(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')) else value) for key, value in row.items()})


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def make_figures(output, result):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return {'status': 'matplotlib_unavailable', 'artifacts': []}
    rows = result['documents']
    if not rows:
        return {'status': 'no_documents', 'artifacts': []}
    if len(rows) > 40:
        return {'status': 'skipped_more_than_40_documents_full_tables_retained', 'artifacts': []}
    artifacts = []
    labels = [f"{i + 1}. {row['title'][:44]}" for i, row in enumerate(rows)]
    def save(fig, name, caption):
        fig.tight_layout()
        for ext in ('png', 'svg'):
            path = output / f'{name}.{ext}'
            fig.savefig(path, dpi=160, metadata={'Title': caption})
            artifacts.append({'file': path.name, 'caption': caption})
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, max(3.2, len(rows) * .48)))
    axes[0].barh(labels, [r['decoded_duration_seconds'] / 60 for r in rows], color='#337e9e')
    axes[0].set_xlabel('Decoded recording minutes'); axes[0].invert_yaxis()
    axes[1].barh(labels, [r['whitespace_word_count'] for r in rows], color='#69589c')
    axes[1].set_xlabel('ASR whitespace words'); axes[1].invert_yaxis()
    fig.suptitle('Actual recordings and unverified machine-text volume')
    save(fig, 'recording-coverage', 'Source duration and ASR volume have different units; recognized words are not verified speech counts.')
    english = [r for r in rows if r['english_lexical_eligible']]
    if english:
        groups = list(KEYWORDS)
        matrix = np.array([[r['keyword_counts'][g]['per_1000_regex_tokens'] for g in groups] for r in english])
        fig, ax = plt.subplots(figsize=(11, max(3.1, len(english) * .48)))
        im = ax.imshow(matrix, aspect='auto', cmap='YlGnBu', vmin=0)
        ax.set_xticks(range(len(groups)), groups, rotation=40, ha='right')
        ax.set_yticks(range(len(english)), [r['title'][:48] for r in english])
        ax.set_title('Declared word-form groups per 1,000 ASR regex tokens')
        fig.colorbar(im, ax=ax, label='Mentions per 1,000 regex tokens')
        save(fig, 'keyword-rates', 'Exact dictionary mentions, including negated or quoted uses; rates do not establish topic validity or belief.')
    if result['lexical']['raw']['cosine_matrix'] is not None:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
        ids = result['lexical']['raw']['source_ids']
        short = [str(next(i + 1 for i, r in enumerate(rows) if r['source_id'] == sid)) for sid in ids]
        for ax, mode, title in zip(axes, ('raw', 'name_masked'), ('Original ASR vocabulary', 'Fixed proper-name mask')):
            data = result['lexical'][mode]['cosine_matrix']
            if data is None:
                ax.text(.5, .5, 'Vocabulary unavailable', ha='center'); continue
            im = ax.imshow(data, cmap='viridis', vmin=0, vmax=1)
            ax.set_xticks(range(len(ids)), short); ax.set_yticks(range(len(ids)), short)
            ax.set_xlabel('Recording number'); ax.set_ylabel('Recording number'); ax.set_title(title)
            fig.colorbar(im, ax=ax, label='TF-IDF cosine')
        fig.suptitle('Within-sample lexical similarity — not agreement')
        save(fig, 'lexical-similarity', 'Dependent recording comparisons; proper-name removal is a sensitivity check, not control for genre or speaker identity.')
    return {'status': 'complete', 'artifacts': artifacts}


def analyse(run_paths, output, *, figures=True, allow_test_fixtures=False):
    output = private_path(output, exists=False)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty private output directory; existing evidence is never overwritten')
    documents, excluded, aliases, audit = load_documents(run_paths, allow_test_fixtures=allow_test_fixtures)
    questions = []
    for doc in documents:
        doc['summary']['keyword_counts'] = keyword_counts(doc)
        candidates = question_candidates(doc)
        doc['summary']['punctuation_question_candidates'] = len(candidates)
        questions.extend(candidates)
    raw, masked = fit_lexical(documents), fit_lexical(documents, mask=True)
    contexts = Counter(d['summary']['medium_id'] or 'unresolved' for d in documents)
    transcript_counts = Counter(d['summary']['transcript_text_sha256'] for d in documents)
    result = {'schema_version': SCHEMA, 'kind': 'synthetic_fixture_analysis' if any(d['summary']['fixture_only'] for d in documents) else 'actual_batch_ASR_descriptive_analysis',
              'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'analysis_script_sha256': sha256(Path(__file__)),
              'documents': [d['summary'] for d in documents], 'excluded': excluded, 'aliases_not_counted_again': aliases,
              'counts': {'distinct_retained_recordings': len(documents), 'provider_recordings': dict(Counter(d['summary']['provider'] for d in documents)),
                         'creator_contexts': dict(contexts), 'creator_context_count': len(contexts),
                         'unresolved_creator_context_recordings': contexts.get('unresolved', 0),
                         'english_lexical_documents': sum(d['summary']['english_lexical_eligible'] for d in documents),
                         'decoded_seconds': sum(d['summary']['decoded_duration_seconds'] for d in documents),
                         'asr_whitespace_words': sum(d['summary']['whitespace_word_count'] for d in documents),
                         'punctuation_question_candidates': len(questions), 'verified_questions_or_answers': 0},
              'dependency_scope': 'one_creator_context_repeated_recordings' if len(contexts) == 1 and 'unresolved' not in contexts else 'multiple_or_unresolved_contexts_not_independence_verified',
              'identical_transcript_text_groups': [{'text_sha256': h, 'source_ids': [d['summary']['source_id'] for d in documents if d['summary']['transcript_text_sha256'] == h]} for h, count in transcript_counts.items() if count > 1],
              'keyword_codebook': {'groups': KEYWORDS, 'mode': 'exploratory_exact_casefolded_word_forms', 'denominator': 'Unicode regex tokens with internal apostrophes; not whitespace words', 'scope': 'English-eligible documents only; dictionary mentions are not validated topics and groups are not a complete semantic inventory.'},
              'lexical': {'raw': raw, 'name_masked': masked},
              'methods': {'representation': 'English stop words, word unigrams/bigrams, sublinear TF, L2 normalization, min_df=1, max_features=10000',
                          'proper_name_mask': NAME_MASK, 'mask_scope': 'Fixed exact word forms; unrecognized ASR spellings remain. Calendar/genre/series context is not removed.',
                          'question_extraction': 'Every ASR segment containing ? or fullwidth ？; retain following segment as context, never automatically as an answer.',
                          'versions': {name: importlib.metadata.version(name) for name in ('scikit-learn', 'numpy')}},
              'synthetic_method_diagnostic': negation_control(), 'limitations': LIMITATIONS,
              'inference': {'empirical_p_values': None, 'confidence_intervals': None, 'human_ASR_accuracy': None, 'cross_medium_validation': False}}
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(output / 'provenance-private.json', {'run_inputs': audit, 'scope': 'Private upstream locations; not for public release'})
    write_json(output / 'question-candidates-private.json', {'scope': 'Unverified ASR punctuation candidates, not a verified Q&A database', 'records': questions})
    fields = ['source_id', 'provider', 'medium_id', 'channel_id', 'title', 'published_date', 'decoded_duration_seconds', 'whitespace_word_count', 'regex_token_count', 'source_language', 'asr_language', 'english_lexical_eligible', 'quiet_sample_fraction', 'rms_dbfs', 'punctuation_question_candidates', 'transcript_sha256']
    csv_file(output / 'recordings.csv', fields, result['documents'])
    keyword_rows = [{'source_id': r['source_id'], 'group': group, **values} for r in result['documents'] if r['keyword_counts'] is not None for group, values in r['keyword_counts'].items()]
    csv_file(output / 'keyword-counts.csv', ['source_id', 'group', 'mentions', 'per_1000_regex_tokens'], keyword_rows)
    for label, fit in result['lexical'].items():
        if fit['cosine_matrix'] is not None:
            with (output / f'similarity-{label}.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream); writer.writerow(['source_id', *fit['source_ids']])
                for sid, values in zip(fit['source_ids'], fit['cosine_matrix']): writer.writerow([sid, *values])
    result['figures'] = make_figures(output, result) if figures else {'status': 'disabled', 'artifacts': []}
    write_json(output / 'analysis.json', result)
    artifacts = [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha256(p), 'contains_transcript_excerpts': p.name == 'question-candidates-private.json'} for p in sorted(output.iterdir()) if p.is_file()]
    write_json(output / 'output-manifest.json', {'schema_version': SCHEMA, 'analysis_script_sha256': sha256(Path(__file__)), 'files': artifacts,
                                               'privacy': 'Output is private. Full/excerpted text and upstream paths require separate release review. No raw transcript bodies are in analysis.json or numerical CSVs.'})
    return result


PUBLIC_DOCUMENT_FIELDS = (
    'source_id', 'provider', 'medium_id', 'channel_id', 'title', 'published_date', 'source_url',
    'source_sha256', 'source_bytes', 'audio_receipt_sha256', 'processing_binding_sha256',
    'transcript_sha256', 'transcript_text_sha256', 'transcript_source', 'executed_audio_script_sha256', 'asr_model_files_sha256',
    'decoded_duration_seconds', 'source_duration_seconds', 'whitespace_word_count', 'regex_token_count',
    'segment_count', 'source_language', 'source_language_status', 'asr_language', 'english_lexical_eligible',
    'asr_timing_quality',
    'english_eligibility_basis', 'human_transcript_validation', 'keyword_counts', 'punctuation_question_candidates',
)


def public_projection(result):
    """An explicit numerical/short-term allowlist; no raw excerpts or private paths."""
    if result.get('kind') != 'actual_batch_ASR_descriptive_analysis' or any(d.get('fixture_only') for d in result['documents']):
        raise ValueError('Synthetic results cannot be released as an actual recording analysis')
    keys = ('schema_version', 'created_at', 'analysis_script_sha256', 'counts', 'dependency_scope',
            'keyword_codebook', 'lexical', 'methods', 'synthetic_method_diagnostic', 'limitations', 'inference')
    projected = {key: result[key] for key in keys}
    projected.update(kind='public_actual_batch_ASR_descriptive_analysis',
                     documents=[{key: d.get(key) for key in PUBLIC_DOCUMENT_FIELDS} for d in result['documents']],
                     release_scope='Numerical aggregates, source-page metadata and short algorithmic lexical terms; no question excerpts, transcript bodies or private archive locations.')
    return projected


def export_public(private_output, public_output, result):
    """Prepare reviewable static files; this never pushes or deploys the website."""
    private_output = private_path(private_output / 'analysis.json').parent
    retained = read_json(private_output / 'analysis.json')
    if encoded(retained) != encoded(result):
        raise ValueError('Public projection differs from the retained private analysis')
    manifest = read_json(private_output / 'output-manifest.json')
    if manifest.get('analysis_script_sha256') != retained.get('analysis_script_sha256'):
        raise ValueError('Private analysis code binding differs from its output manifest')
    expected_files = manifest.get('files')
    if not isinstance(expected_files, list) or len(expected_files) > 100:
        raise ValueError('Expected a bounded private output manifest')
    def verified_output(name):
        matches = [row for row in expected_files if isinstance(row, dict) and row.get('file') == name]
        if len(matches) != 1:
            raise ValueError('Public source is not uniquely bound by its private output manifest')
        entry = matches[0]
        path = verify_file({**entry, 'status': 'verified', 'local_path': private_output / name})
        return path, entry
    verified_output('analysis.json')
    public_output = Path(public_output)
    if not public_output.is_absolute() or '..' in public_output.parts or any(p.is_symlink() for p in (public_output, *public_output.parents)):
        raise ValueError('Public aggregate destination must be absolute and cannot traverse symlinks/parents')
    if public_output.exists() and any(public_output.iterdir()):
        raise ValueError('Public aggregate destination must be new and empty')
    projected = public_projection(result)
    projected['private_analysis_sha256'] = sha256(private_output / 'analysis.json')
    projected['private_output_manifest_sha256'] = sha256(private_output / 'output-manifest.json')
    projected['figures'] = []
    public_output.mkdir(parents=True, exist_ok=True)
    for item in result['figures']['artifacts']:
        name = item['file']
        if name not in {f'{stem}.{ext}' for stem in ('recording-coverage', 'keyword-rates', 'lexical-similarity') for ext in ('png', 'svg')}:
            raise ValueError('Unrecognized figure is excluded from public projection')
        source, expected = verified_output(name)
        target = public_output / 'figures' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != expected['bytes'] or sha256(target) != expected['sha256']:
            raise ValueError('Public figure copy differs from its verified private source')
        projected['figures'].append({'file': 'figures/' + name, 'caption': item['caption'], 'bytes': target.stat().st_size, 'sha256': sha256(target)})
    write_json(public_output / 'analysis.json', projected)
    manifest = {'schema_version': SCHEMA, 'analysis_script_sha256': sha256(Path(__file__)),
                'private_analysis_sha256': projected['private_analysis_sha256'],
                'files': [{'file': str(p.relative_to(public_output)), 'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in sorted(public_output.rglob('*')) if p.is_file()],
                'scope': projected['release_scope']}
    write_json(public_output / 'release-manifest.json', manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', required=True, type=Path, help='Repeat for exact completed audio-run.json files')
    parser.add_argument('--output', required=True, type=Path, help='New empty private output directory outside Git')
    parser.add_argument('--no-figures', action='store_true')
    parser.add_argument('--public-output', type=Path, help='Optional explicit new destination for allowlisted static aggregates/figures; never raw text')
    args = parser.parse_args()
    result = analyse(args.run, args.output, figures=not args.no_figures)
    if args.public_output:
        export_public(args.output, args.public_output, result)
    print(json.dumps({'status': 'complete', 'recordings': result['counts']['distinct_retained_recordings'], 'english_documents': result['counts']['english_lexical_documents'],
                      'creator_contexts': result['counts']['creator_context_count'], 'lexical_status': result['lexical']['raw']['status'], 'new_downloads_by_analysis': 0}))


if __name__ == '__main__':
    main()
