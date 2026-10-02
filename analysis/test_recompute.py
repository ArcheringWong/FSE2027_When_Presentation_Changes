"""Small implementation tests; run with python -m unittest analysis.test_recompute."""
import unittest
import numpy as np
from analysis.recompute import components, python_indexes, ci, assert_expected, persistence_point, characterize, CONDITIONS


class StatisticalFunctions(unittest.TestCase):
    def test_symmetric_contrast_examples(self):
        samples = [dict(P='a',R='a',P_prime='a',R_prime='a'),
                   dict(P='a',R='b',P_prime='a',R_prime='b'),
                   dict(P='a',R='a',P_prime='b',R_prime='b')]
        v = components(samples)
        np.testing.assert_array_equal(v, [[0,0,0,0],[1,1,0,0],[0,0,1,1]])
        np.testing.assert_array_equal((v[:,0]+v[:,1]-v[:,2]-v[:,3])/2,[0,1,-1])

    def test_percentile_interpolation(self):
        np.testing.assert_allclose(ci([0,1,2,3]), [.075,2.925], rtol=0, atol=1e-14)

    def test_reference_check_is_independent(self):
        self.assertEqual(assert_expected({'x':2,'y':3},{'x':2}),1)
        with self.assertRaises(AssertionError):
            assert_expected({'x':2},{'x':3})

    def test_persistence_denominators(self):
        p = persistence_point(np.array([[0,0],[0,1],[1,0],[1,1],[1,1]],dtype=float))
        self.assertEqual(p['recurrence'],2/3)
        self.assertEqual(p['emergence'],1/2)
        self.assertEqual(p['jaccard'],1/2)

    def test_python_random_draw_order(self):
        import random
        sizes={'RCA100':2,'AIOps2025':3}
        indexes=python_indexes(sizes,20260905)
        rng=random.Random(20260905)
        for b in range(2):
            for d in sizes:
                self.assertEqual(indexes[d][b].tolist(),[rng.randrange(sizes[d]) for _ in range(sizes[d])])

    def test_joint_selection_unknown_and_multiple_correct_ids(self):
        rows = []
        for dataset in ('RCA100', 'AIOps2025'):
            for verdicts, scores in [
                (('a','a','a','a'), (True,True,True,True)),
                (('a','b','a','b'), (True,False,True,False)),
                (('a','b','b','a'), (True,False,False,True)),
                (('UNKNOWN','b','UNKNOWN','b'), (False,False,False,False)),
                (('a','b','b','a'), (True,True,True,True)),
            ]:
                rows.append({'dataset':dataset, **dict(zip(CONDITIONS, verdicts)),
                             **{c+'_correct':s for c,s in zip(CONDITIONS,scores)}})
        result = characterize(rows)
        joint = result['joint']['RCA100']
        self.assertEqual((joint['all_four_same'], joint['repeat_stable_cross_view_different'],
                          joint['any_within_view_repeat_change']), (1,2,2))
        self.assertEqual(joint['correctness_exchange_unique_incidents'], 1)
        self.assertEqual(joint['both_wrong'], 1)
        self.assertEqual(joint['involving_unknown'], 1)
        self.assertEqual(result['transitions']['RCA100']['P/R']['correct_to_correct'], 1)
        self.assertEqual(result['transitions']['RCA100']['P/R']['changed_verdict'], 4)


if __name__ == '__main__':
    unittest.main()
