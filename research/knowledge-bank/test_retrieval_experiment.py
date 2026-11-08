import copy
import unittest

import retrieval_experiment as R


class RetrievalAuditTests(unittest.TestCase):
    def test_complete_nonoverlapping_source_chunks(self):
        text = '  ' + '\n '.join('word' + str(i) for i in range(365)) + ' \n'
        docs = [{'record': {'source_id': 'test-source', 'words': 365}, 'text': text}]
        rows = R.source_chunks(docs)
        self.assertEqual([r['words'] for r in rows], [180, 180, 5])
        self.assertEqual(' '.join(r['text'] for r in rows).split(), text.split())
        self.assertTrue(all(a['end_character'] <= b['start_character'] for a, b in zip(rows, rows[1:])))

    def test_cards_do_not_index_question_or_evidence_payload(self):
        card = {'card_id': 'c', 'source_id': 's', 'question': 'UNIQUE_QUERY_LEAK',
            'question_id': 'QUERY_ID_LEAK', 'paraphrase': 'The practice is optional.',
            'conditions': 'Only if wanted.', 'time_scope': 'No fixed date.',
            'qualifying_note': 'Unverified source claim.', 'supports': [{'text': 'PRIVATE_EVIDENCE'}]}
        plain = R.card_units([card], {'s'}, False)[0]['text']
        rich = R.card_units([card], {'s'}, True)[0]['text']
        self.assertEqual(plain, card['paraphrase'])
        self.assertIn('No fixed date.', rich)
        for value in ('UNIQUE_QUERY_LEAK', 'QUERY_ID_LEAK', 'PRIVATE_EVIDENCE'):
            self.assertNotIn(value, rich)

    def test_duplicate_and_unbound_cards_rejected(self):
        c = {'card_id': 'c', 'source_id': 's', 'paraphrase': 'A test statement.'}
        with self.assertRaises(ValueError): R.card_units([c, c], {'s'}, True)
        with self.assertRaises(ValueError): R.card_units([c], {'different'}, True)

    def test_source_max_and_deterministic_ties(self):
        rows = [{'source_id': 'b'}, {'source_id': 'a'}, {'source_id': 'b'}]
        self.assertEqual(R.aggregate_scores(rows, [.1, .8, .8]), [('a', .8), ('b', .8)])

    def test_metrics_are_known_support_ranks_not_precision(self):
        m = R.rank_metrics([('unjudged1', .9), ('unjudged2', .8), ('known', .7)], ['known'])
        self.assertEqual(m['hit_at_k'], {'1': 0, '3': 1, '5': 1})
        self.assertAlmostEqual(m['reciprocal_rank'], 1 / 3)
        self.assertEqual(m['known_support_index_coverage'], 1)

    def test_missing_card_source_remains_missing(self):
        m = R.rank_metrics([('a', .8)], ['b'])
        self.assertIsNone(m['first_known_support_rank'])
        self.assertEqual(m['reciprocal_rank'], 0)
        self.assertEqual(m['known_support_index_coverage'], 0)

    def test_rrf_uses_ranks_and_preserves_source_union(self):
        fused = R.fused_ranking([('a', .99), ('b', .2)], [('b', -.1)])
        self.assertEqual([s for s, _ in fused], ['b', 'a'])
        self.assertAlmostEqual(fused[0][1], 1 / 62 + 1 / 61)

    def query_fixture(self):
        text = 'There is no fixed date.'
        body_hash = R.sha(text.encode()); artifact_hash = 'a' * 64
        docs = [{'record': {'source_id': 's', 'body_sha256': body_hash,
            'text_artifact': {'sha256': artifact_hash}}, 'text': text}]
        q = {'query_id': 'q', 'query': 'Is there a definite time?', 'known_relevant_source_ids': ['s'],
            'supports': [{'source_id': 's', 'body_sha256': body_hash, 'text_artifact_sha256': artifact_hash,
                'char_start': 0, 'char_end': len(text), 'span_sha256': body_hash, 'words': 5,
                'private_evidence_text': text, 'private_path': '/private/fixture'}]}
        return {'frame_sha256': 'frame', 'queries': [q]}, docs

    def test_candidate_repair_keeps_uncovered_top5_and_raw_tail(self):
        left = [('s' + str(i), 1 - i / 30) for i in range(25)]
        right = [('s' + str(i), 1 - i / 30) for i in range(8, 22)]
        ranked = R.candidate_fusion(left, right)
        ids = [x[0] for x in ranked]
        self.assertEqual(len(ids), 25)
        self.assertEqual(set(ids), {x[0] for x in left})
        self.assertLess(ids.index('s0'), ids.index('s21'))
        self.assertEqual(ids[-3:], ['s22', 's23', 's24'])

    def test_naive_full_list_fusion_has_the_declared_coverage_bias(self):
        left = [('s' + str(i), 1 - i / 30) for i in range(25)]
        right = [('s' + str(i), 1 - i / 30) for i in range(11, 25)]
        ids = [sid for sid, _ in R.fused_ranking(left, right)]
        self.assertTrue(set(ids[:14]) == {sid for sid, _ in right})

    def test_frozen_query_support_tampering_rejected(self):
        audit, docs = self.query_fixture()
        R.validate_queries(audit, docs, 'frame')
        wrong = copy.deepcopy(audit); wrong['queries'][0]['supports'][0]['char_end'] -= 1
        with self.assertRaises(ValueError): R.validate_queries(wrong, docs, 'frame')
        with self.assertRaises(ValueError): R.validate_queries(audit, docs, 'other-frame')

    def test_public_query_is_strict_allowlist(self):
        audit, _ = self.query_fixture(); public = R.sanitize_query(audit['queries'][0])
        self.assertNotIn('private_evidence_text', public['supports'][0])
        self.assertNotIn('private_path', public['supports'][0])


if __name__ == '__main__':
    unittest.main()
