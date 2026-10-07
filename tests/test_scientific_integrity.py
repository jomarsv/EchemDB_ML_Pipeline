import json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
import numpy as np
import pandas as pd
from echemdb_ml_pipeline.features import (
    FEATURE_VERSION, NUMERIC_FEATURES, _convert_signal, _unit_for_column,
    _derivative_features, _half_width, _peak_features, build_feature_outputs,
)
from echemdb_ml_pipeline.schema import CurveRecord
from echemdb_ml_pipeline.inference import extract_uploaded_curves
from scripts.create_test_split import source_split
from serve_app import Handler


def record():
    x = np.linspace(0, 2, 101)
    return CurveRecord("fixture", "fixture", "10.1/fixture", "Pt", "acid", "CV",
        units={"t_unit": "s", "E_unit": "V", "j_unit": "mA cm-2"},
        frame=pd.DataFrame({"E": x, "j": x ** 2 + 1}), potential_col="E",
        signal_col="j", signal_kind="current_density")


def upload_payload():
    r = record()
    return {"rows": r.frame.to_dict("records"), "defaults": {
        "tipo_sinal": r.signal_kind, "unidade_potencial_usada": "V",
        "unidade_sinal_usada": "mA cm-2", "grupo_origem": r.doi}}


class ScientificIntegrity(unittest.TestCase):
    def test_exact_unit_lookup(self):
        r = record()
        r.units = {"t_unit": "s", "I_unit": "A"}
        self.assertEqual(_unit_for_column(r, "I"), "A")

    def test_density_units(self):
        for unit, factor in [("mA cm-2", 10), ("uA cm-2", .01),
                             ("mA/cm\u00b2", 10), ("A/m2", 1),
                             ("A cm-2", 10000), ("\u00b5A/cm\u00b2", .01)]:
            with self.subTest(unit=unit):
                values, canonical = _convert_signal(pd.Series([1.]), unit, "current_density")
                self.assertAlmostEqual(values.iloc[0], factor)
                self.assertEqual(canonical, "A/m2")

    def test_current_units_and_unknown_rejection(self):
        values, unit = _convert_signal(pd.Series([1000.]), "mA", "current")
        self.assertEqual((values.iloc[0], unit), (1., "A"))
        for unit in [None, "s", "A", "original_s", "A cm2"]:
            with self.subTest(unit=unit), self.assertRaises(ValueError):
                _convert_signal(pd.Series([1.]), unit, "current_density")

    def test_second_derivative_nonuniform(self):
        x = np.array([0., .1, .5, 1., 2.])
        result = _derivative_features(x, x*x)
        self.assertAlmostEqual(result["derivada2_media"], 2.)
        self.assertAlmostEqual(result["derivada2_desvio"], 0.)
        self.assertEqual(len(NUMERIC_FEATURES), 23)
        self.assertNotIn("inclinacao_media", NUMERIC_FEATURES)

    def test_no_derivative_across_plateau_or_reversal(self):
        result = _derivative_features(np.array([0., 1, 2, 2, 1, 0]), np.array([0., 1, 2, 100, 99, 98]))
        self.assertEqual(result["derivada1_media"], 1.)
        self.assertEqual(result["derivada2_media"], 0.)

    def test_local_peak_width(self):
        x = np.arange(11.)
        y = np.array([0., 4, 0, 0, 0, 0, 0, 0, 0, 4, 0])
        self.assertAlmostEqual(_half_width(x, y, 1, "max"), 1.)

    def test_peak_direction(self):
        x = np.linspace(0, 1, 101)
        y = np.exp(-((x-.5)/.1)**2)
        positive = _peak_features(x, y)
        negative = _peak_features(x[::-1], -y)
        self.assertAlmostEqual(positive["E_pico_anodico"], .5)
        self.assertTrue(np.isnan(positive["E_pico_catodico"]))
        self.assertAlmostEqual(negative["E_pico_catodico"], .5)
        self.assertTrue(np.isnan(negative["E_pico_anodico"]))

    def test_training_inference_parity_and_clean_roundtrip(self):
        features, clean, _, _ = build_feature_outputs([record()], 20, 256, "max_abs")
        actual = extract_uploaded_curves(**upload_payload())[0]
        expected = features.iloc[0]
        for name in NUMERIC_FEATURES:
            np.testing.assert_allclose(float(actual[name]) if actual[name] is not None else np.nan,
                                       expected[name], equal_nan=True, err_msg=name)
        self.assertEqual(actual["hash_curva"], expected.hash_curva)
        roundtrip = extract_uploaded_curves(clean.to_dict("records"))[0]
        self.assertEqual(actual["hash_curva"], roundtrip["hash_curva"])

    def test_upload_rejects_undeclared_and_conflicting_units(self):
        payload = upload_payload()
        with self.assertRaises(ValueError):
            extract_uploaded_curves(payload["rows"])
        payload["rows"][0]["unidade_sinal_usada"] = "A/m2"
        payload["rows"][1]["unidade_sinal_usada"] = "mA/cm2"
        with self.assertRaisesRegex(ValueError, "inconsistente"):
            extract_uploaded_curves(**payload)

    def test_source_disjoint_split_preserves_schema(self):
        frame = pd.DataFrame([{
            "versao_atributos": FEATURE_VERSION, "grupo_origem": f"https://doi.org/10.1/{i//2}",
            "tipo_sinal": "current_density", "classe_alvo": ["Pt", "Au"][i%2],
            "hash_curva": str(i), "extra": i,
        } for i in range(40)])
        train, test = source_split(frame)
        self.assertFalse(set(train.grupo_origem) & set(test.grupo_origem))
        self.assertEqual(len(train)+len(test), 40)
        self.assertEqual(list(test.columns), list(frame.columns))

    def test_http_extraction_and_rejection(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT / "app")))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/features"
            def post(payload):
                return urlopen(Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}), timeout=10)
            with post(upload_payload()) as response:
                self.assertEqual(json.load(response)["rows"], extract_uploaded_curves(**upload_payload()))
            with self.assertRaises(HTTPError) as error:
                post({"rows": upload_payload()["rows"]})
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
