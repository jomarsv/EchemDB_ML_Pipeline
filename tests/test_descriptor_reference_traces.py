"""Analytical reference traces independent of the batch/API parity check."""
import unittest

import numpy as np
import pandas as pd

from echemdb_ml_pipeline.features import _peak_features, build_feature_outputs
from echemdb_ml_pipeline.schema import CurveRecord


def make_record(name, potential, signal, potential_unit="V", signal_unit="A/m2"):
    return CurveRecord(
        entry_id=name,
        reference="SCE",
        doi="10.0000/reference-trace",
        material_electrode=None,
        electrolyte=None,
        experiment_type="synthetic reference trace",
        units={"E": potential_unit, "j": signal_unit},
        frame=pd.DataFrame({"E": potential, "j": signal}),
        potential_col="E",
        signal_col="j",
        signal_kind="current_density",
    )


def extract(name, potential, signal, potential_unit="V", signal_unit="A/m2"):
    records = [make_record(name, potential, signal, potential_unit, signal_unit)]
    features, *_ = build_feature_outputs(records, min_points=20, n_points=20, normalization="none")
    return features.iloc[0]


class AnalyticalDescriptorReferenceTests(unittest.TestCase):
    def test_known_branch_peaks_and_signed_area_after_unit_conversion(self):
        # Each branch is a parabola sampled symmetrically around its known vertex.
        # On the forward branch, j=1-(E-0.2)^2; on reverse, j=-1+(E+0.2)^2.
        forward_v = np.linspace(-1.0, 1.0, 101)
        reverse_v = np.linspace(1.0, -1.0, 101)[1:]
        forward_j = 1.0 - (forward_v - 0.2) ** 2
        reverse_j = -1.0 + (reverse_v + 0.2) ** 2
        e_v = np.concatenate((forward_v, reverse_v))
        j_a_m2 = np.concatenate((forward_j, reverse_j))

        # Independent arithmetic-series evaluation of the 200 trapezoids
        # (including the acquisition-order join) gives 2.5072 A*V/m2.
        expected_area = 2.5072

        row = extract("two-branch", e_v * 1000, j_a_m2 / 10, "mV", "mA/cm2")
        self.assertAlmostEqual(row["E_pico_anodico"], 0.2, places=12)
        self.assertAlmostEqual(row["j_pico_anodico"], 1.0, places=12)
        self.assertAlmostEqual(row["E_pico_catodico"], -0.2, places=12)
        self.assertAlmostEqual(row["j_pico_catodico"], -1.0, places=12)
        self.assertAlmostEqual(row["area_liquida"], expected_area, places=12)
        self.assertEqual(row["unidade_potencial_usada"], "V")
        self.assertEqual(row["unidade_sinal_usada"], "A/m2")

    def test_monotonic_trace_has_no_internal_peak_and_reports_nan(self):
        # Analytic integral of j=2E+1 over E in [-1,1] is exactly 2 A*V/m2.
        e_v = np.linspace(-1.0, 1.0, 41)
        j_a_m2 = 2.0 * e_v + 1.0
        row = extract("no-peak", e_v, j_a_m2)
        self.assertAlmostEqual(row["area_liquida"], 2.0, places=12)
        for column in ("E_pico_anodico", "j_pico_anodico", "E_pico_catodico",
                       "j_pico_catodico", "separacao_picos", "razao_picos"):
            self.assertTrue(np.isnan(row[column]), column)

    def test_reversing_acquisition_order_reverses_signed_area(self):
        e_v = np.linspace(-1.0, 1.0, 41)
        j_a_m2 = 2.0 * e_v + 1.0
        forward = extract("forward", e_v, j_a_m2)
        reverse = extract("reverse", e_v[::-1], j_a_m2[::-1])
        self.assertAlmostEqual(forward["area_liquida"], 2.0, places=12)
        self.assertAlmostEqual(reverse["area_liquida"], -2.0, places=12)

    def test_peak_position_and_width_sensitivity_to_heuristic_settings(self):
        potential = np.linspace(-1.0, 1.0, 201)
        signal = np.exp(-((potential - 0.23) / 0.16) ** 2) + 0.02 * np.sin(14 * np.pi * potential)
        estimates = [
            _peak_features(potential, signal, smoothing_window=window,
                           prominence_fraction=prominence)
            for window in (5, 9, 15, 21)
            for prominence in (0.10, 0.15, 0.20)
        ]
        positions = np.array([item["E_pico_anodico"] for item in estimates])
        widths = np.array([item["largura_pico_anodico"] for item in estimates])
        self.assertTrue(np.isfinite(positions).all())
        self.assertTrue(np.isfinite(widths).all())
        self.assertLessEqual(float(np.ptp(positions)), 0.04)
        self.assertLessEqual(float(np.ptp(widths)), 0.08)
        self.assertLessEqual(float(np.max(np.abs(positions - 0.23))), 0.04)


if __name__ == "__main__":
    unittest.main()
