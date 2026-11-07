"""Synthetic provenance and method tests; fixtures are not acquired recordings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name('analyze.py')
spec = importlib.util.spec_from_file_location('batch_analyze', MODULE)
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

BASE_TEXT = ('Freedom means a choice to allow conscious awareness. Energy and fear are discussed as ideas, '
             'not established facts about any entity or disease. This dialogue includes family love, a physical body, '
             'a spiritual soul and questions about religion. What does freedom mean?')


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='batch-analysis-synthetic-')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False) + '\n')

    def fixture(self, name='one', text=BASE_TEXT, lang='en', media=None):
        sid = 'fixture:' + name
        base = self.root / name; base.mkdir()
        original = base / 'synthetic.media'; original.write_bytes(media or ('synthetic only ' + name).encode())
        proof = base / 'proof.json'
        original_ref = {'status': 'verified', 'kind': 'video', 'source_id': sid, 'local_path': str(original), 'bytes': original.stat().st_size, 'sha256': a.sha256(original)}
        self.write(proof, {'fixture_only': True, 'verified_artifacts': [original_ref]})
        derived = base / 'processing'; derived.mkdir()
        segments = [{'start_seconds': 0., 'end_seconds': 20., 'text': text}]
        seg_path = derived / 'segments.json'
        self.write(seg_path, {'schema_version': 1, 'source_id': sid, 'transcript_source': 'machine ASR; unverified', 'text': text, 'segments': segments})
        source = {**original_ref, 'fixture_only': True, 'provider': 'publisher_video', 'medium_id': 'synthetic-creator', 'channel_id': 'synthetic-account', 'title': name,
                  'source_language': lang, 'duration_seconds': 300., 'verification_receipt': {'path': str(proof), 'sha256': a.sha256(proof)}}
        source.pop('status')
        binding = {'schema_version': 1, 'source': source, 'script_sha256': 'a' * 64, 'asr': {'requested': True, 'model': {'files_sha256': 'b' * 64}}}
        receipt = {'schema_version': 1, 'kind': 'source-bound-audio-analysis', 'status': 'completed', 'source_id': sid, 'provider': 'publisher_video',
                   'binding': binding, 'binding_sha256': a.object_hash(binding), 'decoded_duration_seconds': 300., 'audio_metrics': {},
                   'asr': {'segments': 1, 'whitespace_word_count': len(text.split()), 'language_reported': lang, 'language_plan': {'source_language': lang}},
                   'verified_artifacts': [original_ref, {'status': 'verified', 'kind': 'transcript', 'source_id': sid, 'local_path': str(seg_path), 'bytes': seg_path.stat().st_size, 'sha256': a.sha256(seg_path)}]}
        receipt_path = derived / 'receipt.json'; self.write(receipt_path, receipt)
        run_path = base / 'audio-run.json'
        run = {'schema_version': 1, 'batch_id': name, 'records': [{'source_id': sid, 'status': 'completed', 'provider': 'publisher_video', 'receipt_path': str(receipt_path), 'receipt_sha256': a.sha256(receipt_path)}]}
        self.write(run_path, run)
        return {'run_path': run_path, 'run': run, 'receipt_path': receipt_path, 'receipt': receipt, 'segment_path': seg_path, 'proof_path': proof, 'original': original}

    def refresh_receipt(self, f):
        f['receipt']['binding_sha256'] = a.object_hash(f['receipt']['binding'])
        self.write(f['receipt_path'], f['receipt'])
        f['run']['records'][0]['receipt_sha256'] = a.sha256(f['receipt_path'])
        self.write(f['run_path'], f['run'])

    def load(self, *fixtures):
        return a.load_documents([f['run_path'] for f in fixtures], allow_test_fixtures=True)

    def test_fixture_refused_as_actual_source(self):
        f = self.fixture()
        with self.assertRaisesRegex(ValueError, 'Synthetic'):
            a.load_documents([f['run_path']])

    def test_proof_fixture_marker_cannot_be_erased_from_bound_source(self):
        f = self.fixture(); f['receipt']['binding']['source'].pop('fixture_only'); self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'Synthetic acquisition'):
            a.load_documents([f['run_path']])
        docs, _, _, _ = self.load(f)
        self.assertTrue(docs[0]['summary']['fixture_only'])

    def test_synthetic_results_cannot_be_published_as_actual(self):
        f = self.fixture(); result = a.analyse([f['run_path']], self.root / 'output', figures=False, allow_test_fixtures=True)
        with self.assertRaisesRegex(ValueError, 'Synthetic results'):
            a.public_projection(result)

    def test_public_projection_is_explicit_not_a_recursive_private_dump(self):
        # This empty structural fixture is not a study record or an acquired video.
        result = a.analyse([], self.root / 'empty-structure', figures=False, allow_test_fixtures=True)
        result['private_path'] = '/private/hidden'
        result['question_candidates'] = ['Never publish this fabricated excerpt']
        result['excluded'] = [{'private_path': '/private/not-public'}]
        projected = a.public_projection(result)
        serialized = json.dumps(projected)
        self.assertNotIn('/private/', serialized)
        self.assertNotIn('fabricated excerpt', serialized)
        self.assertNotIn('question_candidates', projected)
        self.assertNotIn('excluded', projected)

    def test_public_export_rejects_changed_memory_result(self):
        private = self.root / 'empty-structure'
        result = a.analyse([], private, figures=False, allow_test_fixtures=True)
        result['counts']['distinct_retained_recordings'] = 99
        with self.assertRaisesRegex(ValueError, 'differs from the retained'):
            a.export_public(private, self.root / 'public', result)

    def test_public_export_rejects_changed_private_analysis(self):
        private = self.root / 'empty-structure'
        result = a.analyse([], private, figures=False, allow_test_fixtures=True)
        result['counts']['distinct_retained_recordings'] = 99
        self.write(private / 'analysis.json', result)
        with self.assertRaisesRegex(ValueError, 'byte count|hash'):
            a.export_public(private, self.root / 'public', result)

    def test_public_export_rejects_changed_bound_figure(self):
        private = self.root / 'empty-structure'
        result = a.analyse([], private, figures=False, allow_test_fixtures=True)
        p = private / 'recording-coverage.png'; p.write_bytes(b'SYNTHETIC TEST FILE ONLY')
        result['figures']['artifacts'] = [{'file': p.name, 'caption': 'Synthetic test only'}]
        self.write(private / 'analysis.json', result)
        manifest = json.loads((private / 'output-manifest.json').read_text())
        for row in manifest['files']:
            if row['file'] == 'analysis.json':
                row.update(bytes=(private / 'analysis.json').stat().st_size, sha256=a.sha256(private / 'analysis.json'))
        manifest['files'].append({'file': p.name, 'bytes': p.stat().st_size, 'sha256': a.sha256(p)})
        self.write(private / 'output-manifest.json', manifest)
        p.write_bytes(b'TAMPERED SYNTHETIC FILE')
        with self.assertRaisesRegex(ValueError, 'byte count|hash'):
            a.export_public(private, self.root / 'public', result)

    def test_receipt_tampering_refused(self):
        f = self.fixture(); f['receipt_path'].write_text('{}')
        with self.assertRaisesRegex(ValueError, 'receipt hash'):
            self.load(f)

    def test_original_bytes_tampering_refused(self):
        f = self.fixture(); f['original'].write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'byte count|hash'):
            self.load(f)

    def test_transcript_tampering_refused(self):
        f = self.fixture(); f['segment_path'].write_text('{}')
        with self.assertRaisesRegex(ValueError, 'byte count|hash'):
            self.load(f)

    def test_acquisition_proof_tampering_refused(self):
        f = self.fixture(); f['proof_path'].write_text('{}')
        with self.assertRaisesRegex(ValueError, 'proof hash'):
            self.load(f)

    def test_binding_change_refused(self):
        f = self.fixture(); f['receipt']['binding']['source']['source_language'] = 'ja'
        self.write(f['receipt_path'], f['receipt']); f['run']['records'][0]['receipt_sha256'] = a.sha256(f['receipt_path']); self.write(f['run_path'], f['run'])
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.load(f)

    def test_identity_and_counts_refused(self):
        f = self.fixture(); f['receipt']['asr']['segments'] = 2; self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'completion counts'):
            self.load(f)
        f['receipt']['asr']['segments'] = 1; f['receipt']['source_id'] = 'fixture:wrong'; self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'identity/status'):
            self.load(f)

    def test_proof_declared_context_cannot_be_erased(self):
        f = self.fixture(); proof = json.loads(f['proof_path'].read_text()); proof['verified_artifacts'][0]['medium_id'] = 'other-context'; self.write(f['proof_path'], proof)
        f['receipt']['binding']['source']['verification_receipt']['sha256'] = a.sha256(f['proof_path']); self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'proof metadata'):
            self.load(f)

    def test_same_source_deduplicated(self):
        f = self.fixture(); docs, excluded, aliases, audit = self.load(f, f)
        self.assertEqual((len(docs), len(excluded), len(aliases)), (1, 0, 1))
        self.assertEqual(aliases[0]['reason'], 'duplicate_source_record')

    def test_byte_identical_sources_are_not_independent_recordings(self):
        f = self.fixture('one', media=b'same synthetic media'); g = self.fixture('two', media=b'same synthetic media')
        docs, _, aliases, _ = self.load(f, g)
        self.assertEqual(len(docs), 1); self.assertEqual(aliases[0]['retained_as'], 'fixture:one')

    def test_non_english_not_fitted_or_counted_with_english_dictionary(self):
        f = self.fixture('one'); g = self.fixture('japanese', lang='ja')
        docs, _, _, _ = self.load(f, g)
        self.assertFalse(docs[1]['summary']['english_lexical_eligible'])
        self.assertIsNone(a.keyword_counts(docs[1]))
        fit = a.fit_lexical(docs); self.assertEqual(fit['status'], 'insufficient_English_documents')
        self.assertEqual(fit['documents'], 1)

    def test_unknown_language_assumption_visible(self):
        f = self.fixture(); f['receipt']['binding']['source']['source_language'] = 'unknown'; self.refresh_receipt(f)
        docs, _, _, _ = self.load(f)
        self.assertIn('assumption', docs[0]['summary']['english_eligibility_basis'])

    def test_invalid_source_language_does_not_become_an_english_assumption(self):
        f = self.fixture(); f['receipt']['binding']['source'].update(source_language='unknown', source_language_status='invalid'); self.refresh_receipt(f)
        docs, _, _, _ = self.load(f)
        self.assertFalse(docs[0]['summary']['english_lexical_eligible'])
        self.assertEqual(docs[0]['summary']['english_eligibility_basis'], 'invalid_or_conflicting_source_language')

    def test_audio_metrics_must_match_retained_artifact(self):
        f = self.fixture(); p = f['receipt_path'].parent / 'audio-metrics.json'; self.write(p, {'rms_dbfs': -20.})
        f['receipt']['verified_artifacts'].append({'status': 'verified', 'source_id': 'fixture:one', 'kind': 'analysis', 'local_path': str(p), 'bytes': p.stat().st_size, 'sha256': a.sha256(p)})
        self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'metric summary'):
            self.load(f)

    def test_explicit_timing_repair_is_disclosed_and_absence_is_unknown(self):
        f = self.fixture(); docs, _, _, _ = self.load(f)
        self.assertEqual(docs[0]['summary']['asr_timing_quality']['status'], 'not_reported_by_original_processing_script')
        f['receipt']['asr'].update(timestamp_policy='terminal_end_clipped_to_decoded_duration',
            timestamp_anomaly_count=1, timestamp_repaired_segment_count=1, timestamp_maximum_adjustment_seconds=7.3646875,
            text_changed_by_repair=False, terminal_text_alignment_unverified=True)
        self.refresh_receipt(f); docs, _, _, _ = self.load(f)
        quality = docs[0]['summary']['asr_timing_quality']
        self.assertEqual(quality['timestamp_repaired_segment_count'], 1)
        self.assertAlmostEqual(quality['timestamp_maximum_adjustment_seconds'], 7.3646875)
        self.assertFalse(quality['text_changed_by_repair'])
        self.assertTrue(quality['terminal_text_alignment_unverified'])
        self.assertIn('does not verify', quality['scope'])

    def test_invalid_timing_diagnostic_is_not_published_as_number(self):
        with self.assertRaisesRegex(ValueError, 'nonnegative integers'):
            a.timing_quality({'timestamp_anomaly_count': True})
        with self.assertRaisesRegex(ValueError, 'finite number'):
            a.timing_quality({'timestamp_maximum_adjustment_seconds': float('nan')})
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            a.timing_quality({'timestamp_repair_script_sha256': '/private/not-a-hash'})

    def test_timing_code_identity_requires_bound_retained_artifact(self):
        f = self.fixture(); f['receipt']['asr']['timestamp_repair_script_sha256'] = 'c' * 64
        f['receipt']['binding']['postprocessing'] = {'script_sha256': 'c' * 64}
        self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'retained artifact'):
            self.load(f)

    def test_explicit_repaired_machine_variant_requires_full_bound_policy(self):
        f = self.fixture()
        doc = json.loads(f['segment_path'].read_text())
        doc['transcript_source'] = 'machine ASR; unverified; final segment endpoint clipped to recording boundary'
        self.write(f['segment_path'], doc)
        for row in f['receipt']['verified_artifacts']:
            if row['local_path'] == str(f['segment_path']):
                row.update(bytes=f['segment_path'].stat().st_size, sha256=a.sha256(f['segment_path']))
        self.refresh_receipt(f)
        with self.assertRaisesRegex(ValueError, 'source/type'):
            self.load(f)
        hashes = []
        for name in ['synthetic-execution.py', 'synthetic-repair.py', 'synthetic-helper.py']:
            p = f['receipt_path'].parent / name; p.write_text('# SYNTHETIC FIXTURE ' + name)
            hashes.append(a.sha256(p))
            f['receipt']['verified_artifacts'].append({'status': 'verified', 'source_id': 'fixture:one', 'kind': 'source-metadata',
                'local_path': str(p), 'bytes': p.stat().st_size, 'sha256': hashes[-1]})
        f['receipt']['binding'].update(script_sha256=hashes[0], postprocessing={'method': 'explicit_terminal_end_clip_v1', 'script_sha256': hashes[1], 'helper_sha256': hashes[2]})
        f['receipt']['asr'].update(timestamp_policy='terminal_end_clipped_to_decoded_duration', timestamp_anomaly_count=1,
            timestamp_repaired_segment_count=1, timestamp_maximum_adjustment_seconds=7.3646875, text_changed_by_repair=False,
            terminal_text_alignment_unverified=True, asr_execution_script_sha256=hashes[0], timestamp_repair_script_sha256=hashes[1],
            timestamp_repair_helper_sha256=hashes[2])
        self.refresh_receipt(f)
        docs, _, _, _ = self.load(f)
        self.assertEqual(docs[0]['summary']['transcript_source'], doc['transcript_source'])
        self.assertTrue(docs[0]['summary']['asr_timing_quality']['terminal_text_alignment_unverified'])

    def test_question_is_candidate_not_verified_answer(self):
        f = self.fixture(); docs, _, _, _ = self.load(f)
        rows = a.question_candidates(docs[0]); self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['speaker'], 'unassigned')
        self.assertFalse(rows[0]['following_context_is_verified_answer'])
        self.assertEqual(rows[0]['question_type'], 'unclassified_rhetorical_or_dialogue')

    def test_dictionary_exact_forms_and_denominator(self):
        f = self.fixture(text=BASE_TEXT + ' FREEDOM freedom! freedoms notfree.')
        docs, _, _, _ = self.load(f); result = a.keyword_counts(docs[0])
        count = docs[0]['tokens'].count('freedom')
        self.assertEqual(result['freedom']['mentions'], count)
        self.assertAlmostEqual(result['freedom']['per_1000_regex_tokens'], count * 1000 / len(docs[0]['tokens']))

    def test_single_source_no_comparison_or_nmf(self):
        f = self.fixture(); result = a.analyse([f['run_path']], self.root / 'output', figures=False, allow_test_fixtures=True)
        self.assertEqual(result['kind'], 'synthetic_fixture_analysis')
        self.assertEqual(result['counts']['distinct_retained_recordings'], 1)
        self.assertIsNone(result['lexical']['raw']['cosine_matrix'])
        self.assertEqual(result['lexical']['raw']['nmf']['status'], 'not_fitted')
        self.assertEqual(result['dependency_scope'], 'one_creator_context_repeated_recordings')
        self.assertEqual(result['counts']['verified_questions_or_answers'], 0)
        with self.assertRaisesRegex(ValueError, 'new empty'):
            a.analyse([f['run_path']], self.root / 'output', figures=False, allow_test_fixtures=True)

    def test_negation_control_exposes_lexical_failure(self):
        control = a.negation_control()
        self.assertTrue(control['synthetic_control_not_corpus_data'])
        self.assertAlmostEqual(control['cosine_similarity'], 1)
        self.assertIn('not agreement', control['interpretation'])

    def test_name_mask_does_not_normalize_unknown_spellings(self):
        self.assertEqual(a.mask_names('Adamus Shaumbra shambra free'), '  shambra free')

    def test_name_mask_preserves_every_other_character(self):
        self.assertEqual(a.mask_names('Adamus: café, isn’t naïve; circle!\n'), ': café, isn’t naïve; !\n')

    def test_identical_text_is_flagged_across_different_source_wrappers(self):
        fs = [self.fixture(str(i)) for i in range(2)]
        result = a.analyse([f['run_path'] for f in fs], self.root / 'output', figures=False, allow_test_fixtures=True)
        self.assertEqual(len(result['identical_transcript_text_groups']), 1)
        self.assertEqual(len(result['identical_transcript_text_groups'][0]['source_ids']), 2)
        self.assertNotEqual(result['documents'][0]['transcript_sha256'], result['documents'][1]['transcript_sha256'])
        self.assertEqual(result['documents'][0]['transcript_text_sha256'], result['documents'][1]['transcript_text_sha256'])

    def test_four_distinct_documents_fit_and_keep_one_creator_scope(self):
        extras = [' astronomy planet orbit star cosmic telescope universe solar', ' nutrition food vegetables cooking garden vegetable kitchen meal',
                  ' family love friendship partner marriage parent child caring', ' mathematics integer proof geometry algebra sum fraction theorem']
        fs = [self.fixture(str(i), text=BASE_TEXT + extra * 6) for i, extra in enumerate(extras)]
        docs, _, _, _ = self.load(*fs); result = a.fit_lexical(docs)
        self.assertEqual(result['status'], 'descriptive_fit_complete')
        self.assertEqual(result['nmf']['status'], 'exploratory_fit_complete')
        self.assertEqual(len(result['cosine_matrix']), 4)
        self.assertTrue(all(abs(result['cosine_matrix'][i][i] - 1) < 1e-12 for i in range(4)))
        self.assertTrue(all(0 <= value <= 1 for row in result['cosine_matrix'] for value in row))
        self.assertTrue(all(abs(result['cosine_matrix'][i][j] - result['cosine_matrix'][j][i]) < 1e-12 for i in range(4) for j in range(4)))

    def test_repeated_identical_text_does_not_manufacture_nmf_topics(self):
        fs = [self.fixture(str(i)) for i in range(4)]
        docs, _, _, _ = self.load(*fs); result = a.fit_lexical(docs)
        self.assertEqual(result['nmf']['status'], 'not_fitted')

    def test_csv_formulas_are_inert(self):
        p = self.root / 'safe.csv'; a.csv_file(p, ['title', 'number'], [{'title': '=1+1', 'number': -1.5}])
        self.assertIn("'=1+1,-1.5", p.read_text())

    def test_symlinks_refused(self):
        f = self.fixture(); link = self.root / 'alias.json'; link.symlink_to(f['run_path'])
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            a.load_documents([link], allow_test_fixtures=True)

    def test_incomplete_run_is_excluded_without_media_claim(self):
        p = self.root / 'run.json'; self.write(p, {'schema_version': 1, 'records': [{'source_id': 'fixture:failed', 'status': 'failed'}]})
        docs, excluded, _, _ = a.load_documents([p]); self.assertEqual(docs, [])
        self.assertEqual(excluded[0]['reason'], 'not_completed_ASR')


if __name__ == '__main__':
    unittest.main()
