from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from .data_loader import load_records, records_to_index_frame
from .features import build_feature_outputs
from .ml import run_models
from .reporting import write_report


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    n_points: int = 256,
    min_points: int = 20,
    normalization: str = "max_abs",
    skip_models: bool = False,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(input_path)
    index = records_to_index_frame(records)
    features, clean, curves, control = build_feature_outputs(
        records,
        min_points=min_points,
        n_points=n_points,
        normalization=normalization,
    )
    model_report = pd.DataFrame() if skip_models else run_models(features, curves, output_dir)

    index.to_csv(output_dir / "dados_brutos_indexados.csv", index=False)
    clean.to_csv(output_dir / "dados_limpos.csv", index=False)
    features.to_csv(output_dir / "atributos_voltamogramas.csv", index=False)
    curves.to_csv(output_dir / "curvas_interpoladas.csv", index=False)
    control.to_csv(output_dir / "controle_qualidade.csv", index=False)
    model_report.to_csv(output_dir / "relatorio_modelos.csv", index=False)
    write_report(input_path, output_dir, index, features, control, model_report)

    return {
        "records_loaded": len(records),
        "valid_records": int((control["status"] == "valido").sum()) if not control.empty else 0,
        "output_dir": str(output_dir),
    }
