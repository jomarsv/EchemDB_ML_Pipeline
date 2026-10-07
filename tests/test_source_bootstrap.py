import unittest

import numpy as np

from scripts.bootstrap_source_uncertainty import sample_source_indices, score


class SourceBootstrapTests(unittest.TestCase):
    def test_metrics_use_fixed_binary_class_labels(self):
        result = score(np.array(["Ag", "Ag", "Au", "Au"]),
                       np.array(["Ag", "Au", "Au", "Au"]))
        self.assertAlmostEqual(result["accuracy"], 0.75)
        self.assertAlmostEqual(result["balanced_accuracy"], 0.75)
        self.assertAlmostEqual(result["macro_f1"], (2 / 3 + 0.8) / 2)

    def test_resampling_keeps_doi_curves_together_and_class_stratified(self):
        strata = {"Ag": ["ag1", "ag2"], "Au": ["au1", "au2"]}
        rows = {"ag1": np.array([0, 1]), "ag2": np.array([2]),
                "au1": np.array([3, 4, 5]), "au2": np.array([6])}
        sampled = sample_source_indices(strata, rows, np.random.default_rng(17))
        counts = np.bincount(sampled, minlength=7)
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[3], counts[4])
        self.assertEqual(counts[4], counts[5])
        self.assertEqual(counts[0] + counts[2], 2)
        self.assertEqual(counts[3] + counts[6], 2)


if __name__ == "__main__":
    unittest.main()
