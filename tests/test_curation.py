import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from curate_scientific_inputs import classify_duplicates, reference_policy, source_gaps


class CurationTests(unittest.TestCase):
    def test_missing_and_conflicting_references_are_quarantined(self):
        for axis, figure in [('RHE', 'SHE'), ('unknown', ''), ('SCE', '')]:
            self.assertEqual(reference_policy(axis, figure, 'doi')[0], 'quarantine_reference')

    def test_quasi_references_stay_source_specific(self):
        self.assertNotEqual(reference_policy('Ag', 'Ag', 'one')[2],
                            reference_policy('Ag', 'Ag', 'two')[2])
        self.assertNotEqual(reference_policy('Ag', 'Ag', 'one')[2], 'Ag/AgCl')

    def test_no_unverified_reference_conversion(self):
        self.assertIn('requires', reference_policy('RHE', 'RHE', 'doi')[1])
        self.assertIn('requires', reference_policy('SCE', 'SCE', 'doi')[1])

    def test_all_duplicate_members_flagged_not_missing_hashes(self):
        frame = pd.DataFrame({'hash_curva': ['same', 'same', 'other', '', None]})
        self.assertEqual(classify_duplicates(frame).tolist(), [True, True, False, False, False])

    def test_source_counts_do_not_count_curves_or_holdout_as_new_sources(self):
        frame = pd.DataFrame({'partition': ['development'] * 2 + ['held_out'],
                              'tipo_sinal': ['current_density'] * 3,
                              'reference_stratum': ['SCE'] * 3, 'classe_alvo': ['Co'] * 3,
                              'id_entrada': ['a', 'b', 'c'], 'source_group': ['one', 'one', 'two']})
        result = source_gaps(frame).set_index('partition')
        self.assertEqual(result.loc['development', 'independent_sources'], 1)
        self.assertEqual(result.loc['development', 'additional_sources_needed'], 3)


if __name__ == '__main__':
    unittest.main()
