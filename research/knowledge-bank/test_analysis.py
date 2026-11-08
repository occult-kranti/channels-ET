import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).parent))
import analyze as A


class MethodsTest(unittest.TestCase):
    def test_phrase_mask_preserves_negation_and_substantive_words(self):
        text="The Council of Contact says don't fear contact; contact is not guaranteed."
        result=A.mask_text(text,['Council of Contact'])
        self.assertIn("don't",result);self.assertIn('not',result)
        self.assertIn('fear contact',result);self.assertNotIn('Council of Contact',result)

    def test_phrase_mask_handles_number_and_article_order(self):
        value=A.mask_text('The Galactic Council of 9 and Galactic Council discuss council.',
            ['Galactic Council','Galactic Council of 9'])
        self.assertNotIn('9',value);self.assertIn('discuss council',value)

    def test_centered_span_keeps_interstitial_number_for_mask(self):
        text='start ' * 20 + 'Galactic Council of 9 reports that contact is not assured. ' + 'end '*20
        span=A.centered(text,20)
        self.assertIsNotNone(span);self.assertEqual(len(A.TOKEN.findall(span)),20)
        self.assertNotIn('9',A.mask_text(span,['Galactic Council of 9']))
        self.assertIsNone(A.centered('too short',300))

    def test_neighbors_exclude_self_and_break_ties_by_id(self):
        ids=['z','a','b'];m=np.array([[1,.2,.2],[.2,1,.4],[.2,.4,1]])
        self.assertEqual(A.nearest(m,ids,2),[['a','b'],['b','z'],['a','z']])
        self.assertAlmostEqual(A.jaccard(['a','b'],['b','c']),1/3)

    def test_pair_categories_do_not_make_same_label_same_medium(self):
        left={'medium_id':'m1','comparison_label':'arcturian'}
        right={'medium_id':'m2','comparison_label':'arcturian'}
        self.assertEqual(A.pair_kind(left,right),'cross_medium_same_comparison_label')
        right['comparison_label']='pleiadian'
        self.assertEqual(A.pair_kind(left,right),'cross_medium_other_label')

    def test_projection_normalization_is_translation_scale_invariant(self):
        x=np.array([[0,1],[2,3],[5,4]],dtype=float)
        self.assertTrue(np.allclose(A.norm_coords(x),A.norm_coords(4*x+200)))
        self.assertTrue(np.isfinite(A.norm_coords(np.ones((3,2)))).all())

    def fake_encoder(self):
        encoder=object.__new__(A.FrozenMiniLM)
        class Tokenizer:
            def encode(self,text,add_special_tokens=False):
                return type('Ids',(),{'ids':[200+int(t) for t in text.split()]})()
        class Session:
            def run(self,unused,inputs):
                ids=inputs['input_ids'];array=np.stack([ids.astype(float),np.ones_like(ids)],axis=-1)
                return [array]
        encoder.tokenizer=Tokenizer();encoder.session=Session();encoder.input_names={'input_ids','attention_mask'}
        return encoder

    def test_encoding_complete_unequal_chunks_and_l2(self):
        encoder=self.fake_encoder();text=' '.join(['1']*240+['900']*3)
        weighted,equal,coverage=encoder.encode([('fixture',text)])['fixture']
        self.assertEqual(coverage['chunks'],2);self.assertEqual(coverage['processed_content_wordpieces'],243)
        self.assertEqual(coverage['truncated_content_wordpieces'],0)
        self.assertAlmostEqual(np.linalg.norm(weighted),1)
        self.assertGreater(np.linalg.norm(weighted-equal),1e-4)

    def test_encoding_rejects_duplicate_ids_and_empty_text(self):
        encoder=self.fake_encoder()
        with self.assertRaises(ValueError):encoder.encode([('x','1'),('x','2')])
        with self.assertRaises(ValueError):encoder.encode([('x','')])

    def test_tampered_model_manifest_is_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            import json
            p=Path(temp);(p/'manifest.json').write_text(json.dumps({'model':A.MODEL,'revision':A.REVISION,
                'files':[{'path':'model.onnx','bytes':3,'sha256':'0'*64}]}))
            (p/'model.onnx').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'Model artifact changed'):A.FrozenMiniLM(p)


if __name__=='__main__':unittest.main()
