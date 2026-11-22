"""Reproduce the controlled synthetic unit-metadata fault-injection example."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if not (SOURCE_ROOT / "echemdb_ml_pipeline").is_dir():
    SOURCE_ROOT = ROOT / "runtime" / "src"
sys.path.insert(0, str(SOURCE_ROOT))
from echemdb_ml_pipeline.inference import extract_uploaded_curves


def run_demo(input_csv: Path, metadata_json: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"Choose a fresh output directory: {output_dir}")
    configuration = json.loads(metadata_json.read_text(encoding="utf-8"))
    wrong = configuration["incorrect_defaults"]
    corrected = configuration["corrected_defaults"]
    changed = [key for key in set(wrong) | set(corrected) if wrong.get(key) != corrected.get(key)]
    if changed != ["unidade_sinal_usada"]:
        raise ValueError("The controlled example must change only the signal-unit metadata")

    points = pd.read_csv(input_csv).to_dict(orient="records")
    try:
        extract_uploaded_curves(points, wrong)
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("The intentionally incompatible unit was not rejected")

    features = extract_uploaded_curves(points, corrected)
    if len(features) != 1 or features[0]["numero_pontos"] != len(points):
        raise AssertionError("The corrected single-curve input did not produce one valid feature row")
    feature = features[0]
    if feature["unidade_sinal_usada"] != "A/m2" or feature["status"] != "valido":
        raise AssertionError("Corrected metadata did not produce canonical current-density output")

    output_dir.mkdir(parents=True)
    pd.DataFrame(features).to_csv(output_dir / "corrected_features.csv", index=False)
    result = {
        "status": "passed",
        "scenario": configuration["scenario"],
        "independent_dataset": False,
        "input_csv": input_csv.name,
        "input_sha256": hashlib.sha256(input_csv.read_bytes()).hexdigest(),
        "points": len(points),
        "fault": {
            "declared_signal_type": wrong["tipo_sinal"],
            "incorrect_declared_signal_unit": wrong["unidade_sinal_usada"],
            "validation_rejected_input": True,
            "error": rejection,
        },
        "correction": {
            "changed_field": "unidade_sinal_usada",
            "corrected_declared_signal_unit": corrected["unidade_sinal_usada"],
            "status": feature["status"],
            "canonical_signal_unit": feature["unidade_sinal_usada"],
            "feature_version": feature["versao_atributos"],
            "j_min": feature["j_min"],
            "j_max": feature["j_max"],
            "curve_hash": feature["hash_curva"],
            "features_file": "corrected_features.csv",
        },
        "interpretation": (
            "This controlled example shows rejection of a dimensionally incompatible unit label. "
            "It is synthetic and does not show independent adoption or detection of plausible but incorrect units."
        ),
    }
    (output_dir / "impact_demo.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Synthetic curve CSV.")
    parser.add_argument("--metadata", type=Path, required=True, help="Fault-injection metadata JSON.")
    parser.add_argument("--output", type=Path, required=True, help="New output directory.")
    args = parser.parse_args()
    print(json.dumps(run_demo(args.input, args.metadata, args.output), indent=2))


if __name__ == "__main__":
    main()
