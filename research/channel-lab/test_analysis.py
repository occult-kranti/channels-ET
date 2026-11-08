import sys
from pathlib import Path
import unittest
import tempfile
import hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import analyze_corpus as A
import analyze_witness as portable


class AnalysisContractTest(unittest.TestCase):
    def test_zero_features_are_missing_not_fabricated_cosines(self):
        m,available=A.matrix_for(np.array([[1.,0.],[0.,0.],[0.,1.]]))
        self.assertEqual(available.tolist(),[True,False,True])
        self.assertTrue(np.isnan(m[1]).all() and np.isnan(m[:,1]).all())
        self.assertEqual(m[0,0],1);self.assertEqual(m[0,2],0)

    def test_short_bodies_keep_the_exact_common_source_universe(self):
        text='Not every short text supplies a date.'
        value,span=A.bounded(text)
        self.assertEqual(value,text);self.assertTrue(span['short_body_retained'])
        ids=['a','b','c'];left=np.array([[1,.9,.8],[.9,1,.7],[.8,.7,1.]])
        right=left.copy();right[1,:]=np.nan;right[:,1]=np.nan
        r=A.sensitivity(left,right,ids,['one','one','two'])
        self.assertEqual(r['eligible_sources'],2)
        self.assertEqual(r['rows'][0]['full_ids'],['c']);self.assertEqual(r['rows'][0]['jaccard'],1)
        self.assertIsNone(r['rows'][1]['jaccard'])

    def test_mask_preserves_offsets_negation_and_name_boundaries(self):
        source='Sam Smith is not Sam Smithson.';result=A.masked(source,['Sam Smith'])
        self.assertEqual(len(result),len(source));self.assertIn('not Sam Smithson',result)
        self.assertIn('not',A.words(result))

    def test_nmf_scale_fix_preserves_product_and_removes_arbitrary_factor_scaling(self):
        h=np.array([[2.,0.,1.],[0.,3.,1.]]);w=np.array([[1.,2.],[3.,4.]])
        expected=w@h;h2=h*np.array([5.,.2])[:,None];w2=w/np.array([5.,.2])[None,:]
        A.canonicalize_factors(h,w);A.canonicalize_factors(h2,w2)
        np.testing.assert_allclose(w@h,expected);np.testing.assert_allclose(h,h2);np.testing.assert_allclose(w,w2)
        np.testing.assert_allclose(np.linalg.norm(h,axis=1),1)

    def test_deterministic_neighbors_and_singleton_group_denominators(self):
        m=np.eye(3);ids=['z','b','a'];self.assertEqual(A.neighbors(m,ids)[0],[2,1])
        means,counts=A.group_matrix(m,['one','two','two'],['one','two'])
        self.assertIsNone(means[0][0]);self.assertEqual(counts,[[0,2],[2,1]])

    def test_mutual_graph_counts_and_unavailable_nodes(self):
        m=np.array([[1,.9,np.nan],[.9,1,np.nan],[np.nan,np.nan,np.nan]])
        result=A.graph_summary(m,['a','b','c'])
        self.assertEqual(result['available_nodes'],2)
        self.assertEqual(result['knn_trials'][0]['edges'],1)
        self.assertEqual(result['knn_trials'][0]['largest_component'],2)

    def test_portable_witness_preserves_original_and_numeric_values(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
            root=Path(temp);source=root/'old';source.mkdir()
            core=source/'core-vectors.npz';values=np.array([[.2,.3],[.4,.5]])
            np.savez(core,features=np.array(['alpha','beta'],dtype=object),semantic=values)
            before=hashlib.sha256(core.read_bytes()).hexdigest()
            receipt=portable.convert(source,root/'portable','test-analysis')
            self.assertEqual(hashlib.sha256(core.read_bytes()).hexdigest(),before)
            self.assertTrue(receipt['all_array_values_identical'])
            with np.load(root/'portable'/'core-vectors.npz',allow_pickle=False) as output:
                self.assertEqual(output['features'].tolist(),['alpha','beta'])
                np.testing.assert_array_equal(output['semantic'],values)
            with self.assertRaises(FileExistsError):portable.convert(source,root/'portable','test-analysis')


if __name__=='__main__':unittest.main()
