import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_unit_error_impact_demo import ROOT, run_demo


class UnitErrorImpactDemoTests(unittest.TestCase):
    def test_incompatible_unit_is_rejected_and_corrected_csv_is_processed(self):
        source = ROOT / "examples/impact"
        with tempfile.TemporaryDirectory() as temporary:
            result = run_demo(
                source / "unit_error_curve.csv",
                source / "unit_error_metadata.json",
                Path(temporary) / "impact-output",
            )
            self.assertTrue(result["fault"]["validation_rejected_input"])
            self.assertIn("incompativel com current_density: mA", result["fault"]["error"])
            self.assertEqual(result["correction"]["canonical_signal_unit"], "A/m2")
            self.assertEqual(result["correction"]["status"], "valido")
            self.assertFalse(result["independent_dataset"])
            saved = json.loads((Path(temporary) / "impact-output/impact_demo.json").read_text())
            self.assertEqual(saved, result)
            self.assertTrue((Path(temporary) / "impact-output/corrected_features.csv").is_file())


if __name__ == "__main__":
    unittest.main()
