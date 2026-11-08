import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
import json
import copy
import numpy as np

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import asr_effects as E
import verify_asr_effects as V


def public_fixture():
    change=E.cue_change('not one','not one');pairs=[]
    for i in range(9):
        primary=i<4
        pairs.append({'source_id':f'test-source-{i}','recording_id':'audio-sha256:'+'a'*64,'audio_sha256':'a'*64,
            'old_asr_is_selected_canonical':primary,'old_asr_body_sha256':'b'*64,'selected_body_sha256':'b'*64 if primary else 'c'*64,
            'same_audio_cosines':{'lexical':1.,'semantic':1.},'canonical_cosines':{'lexical':1.,'semantic':1.},
            'same_audio_cue_change':copy.deepcopy(change),'canonical_cue_change':copy.deepcopy(change)})
    near=[{'source_id':f'other-{i}','cosine':1-i*.1} for i in range(5)]
    metric={'k':5,'rows':[{'source_id':p['source_id'],'jaccard':1.,'before':near,'after':near} for p in pairs],
        'mean_jaccard_changed_sources':1.,'mean_jaccard_all_sources':1.,'mean_jaccard_unchanged_sources':1.}
    return {'status':'executed_frozen_space_ASR_sensitivity','coverage':{'changed_sources':9,'candidate_sources':493,
        'full_corpus_reencoded':False,'vocabulary_or_IDF_refit':False,'canonical_frame_changed':False,
        'canonical_ASR_vs_ASR_comparisons':4,'canonical_written_vs_ASR_comparisons':5},'pairs':pairs,
        'neighbors':{'lexical':copy.deepcopy(metric),'semantic':copy.deepcopy(metric)},'figures':[]}


class EffectTests(unittest.TestCase):
    def test_lexical_negation_is_counted_but_not_semantic_judgment(self):
        q=E.cues("No. It isn't not one, but 2031 or three; never none.")
        self.assertEqual(q['negation_cues'],4)
        self.assertEqual(q['number_word_cues'],2)
        self.assertEqual(q['digit_number_cues'],1)

    def test_empty_rates_are_missing(self):
        q=E.cues('');self.assertIsNone(q['negation_per_1000_lexical_tokens'])
        self.assertEqual(q['whitespace_words'],0)

    def test_frozen_vocabulary_cannot_add_new_words(self):
        v=E.frozen_vectorizer(['alpha','beta'],[1.,2.])
        out=v.transform(['alpha newword'])
        self.assertEqual(out.shape,(1,2));self.assertEqual(out.nnz,1)
        self.assertNotIn('newword',v.vocabulary_)

    def test_different_origin_vectors_not_substituted_for_old_asr(self):
        written=np.asarray([[1.,0.]]);old_asr=np.asarray([[0.,1.]]);new=np.asarray([[0.,1.]])
        self.assertEqual(E.selected_cosines(written,new),[0.])
        self.assertEqual(E.selected_cosines(old_asr,new),[1.])

    def test_replacement_can_change_unchanged_source_neighbors(self):
        old=np.asarray([[1.,0.],[.99,.1],[0.,1.],[-1.,0.],[0.,-1.],[.5,.5],[.4,-.8]])
        ids=[f's{i}' for i in range(len(old))];new=np.asarray([[-1.,.01]])
        public,witness=E.neighbor_impact(old,new,[1],ids,k=2)
        self.assertGreater(public['unchanged_sources_with_changed_neighbor_set'],0)
        self.assertEqual(public['changed_sources'],1)
        self.assertTrue(np.allclose(old[1],[.99,.1]))

    def test_stable_tie_break_uses_source_id(self):
        old=np.asarray([[1.,0.],[1.,0.],[1.,0.],[0.,1.]])
        public,_=E.neighbor_impact(old,old[[0]],[0],['self','z','a','far'],k=2)
        self.assertEqual([x['source_id'] for x in public['rows'][0]['before']],['a','z'])
        self.assertEqual(public['rows'][0]['jaccard'],1.)

    def test_duplicate_replacements_rejected(self):
        with self.assertRaises(ValueError):E.neighbor_impact(np.eye(3),np.eye(3)[:2],[0,0],['a','b','c'])

    def test_zero_representation_uses_same_common_universe(self):
        public,witness=E.neighbor_impact(np.eye(4),np.zeros((1,4)),[0],['a','b','c','d'],k=2)
        self.assertEqual(public['available_common_sources'],3)
        self.assertIsNone(public['rows'][0]['jaccard'])
        self.assertEqual(witness['after_neighbors'].shape,(4,2))
        self.assertTrue(np.all(witness['after_neighbors'][0]==-1))

    def test_old_counterpart_must_match_accepted_body_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'text.txt';path.write_text('A &amp; B')
            ref=E.F.artifact(path)
            transform,text=E.old_body(ref,E.hash_text('A & B'))
            self.assertEqual(text,'A & B');self.assertEqual(transform,'HTML_clean_NFKC_strip')
            with self.assertRaises(ValueError):E.old_body(ref,'0'*64)

    def test_public_gate_rejects_tampered_cue_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'asr-effects.json';data=public_fixture();p.write_text(json.dumps(data))
            self.assertEqual(V.verify(tmp)['changed_sources'],9)
            data['pairs'][0]['same_audio_cue_change']['delta']['whitespace_words']=9;p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):V.verify(tmp)

    def test_public_gate_rejects_tampered_jaccard(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=public_fixture();data['neighbors']['lexical']['rows'][0]['jaccard']=0.
            (Path(tmp)/'asr-effects.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):V.verify(tmp)

    def test_public_gate_rejects_private_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=public_fixture();data['leak']='/workspace/private-corpus.txt'
            (Path(tmp)/'asr-effects.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):V.verify(tmp)

    def test_public_gate_accepts_bundled_figure_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'figures').mkdir();figure=root/'figures/chart.svg';figure.write_text('<svg/>')
            data=public_fixture();data['figures']=[E.ref(figure)]
            (root/'asr-effects.json').write_text(json.dumps(data))
            self.assertEqual(V.verify(root)['changed_sources'],9)

    def test_public_gate_rejects_figure_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=public_fixture();data['figures']=[{'file':'../escape.svg','bytes':0,'sha256':'0'*64}]
            (root/'asr-effects.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):V.verify(root)


if __name__=='__main__':unittest.main()
