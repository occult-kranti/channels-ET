import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import contextual_terms as C


class ContextualTermTest(unittest.TestCase):
    def test_mask_preserves_original_character_spans_and_whole_name_boundaries(self):
        source='A Sam Smith message: Sam Smithson says not yet.'
        masked=C.positioned_mask(source,['Sam Smith'])
        self.assertEqual(len(masked),len(source))
        self.assertEqual(masked,'A           message: Sam Smithson says not yet.')
        self.assertEqual(masked.index('not'),source.index('not'))

    def test_two_distinct_bounded_samples_for_every_multi_occurrence_case(self):
        self.assertEqual(C.occurrence_indices(0),[])
        self.assertEqual(C.occurrence_indices(1),[0])
        for n in range(2,100):
            indices=C.occurrence_indices(n)
            self.assertEqual(len(set(indices)),2)
            self.assertTrue(0<=indices[0]<indices[1]<n)

    def test_subword_targets_exclude_special_tokens_and_neighbors(self):
        encoded=SimpleNamespace(ids=[7,8,9,10,11],offsets=[(0,1),(2,5),(5,8),(9,10),(11,12)])
        self.assertEqual(C.target_window(encoded,2,8,radius=1),(0,4,2,4))

    def test_clipped_context_retains_target_at_source_start_and_end(self):
        encoded=SimpleNamespace(ids=[7,8],offsets=[(0,3),(4,8)])
        self.assertEqual(C.target_window(encoded,0,3),(0,2,1,2))
        self.assertEqual(C.target_window(encoded,4,8),(0,2,2,3))
        with self.assertRaises(ValueError):C.target_window(encoded,10,12)


if __name__=='__main__':unittest.main()
